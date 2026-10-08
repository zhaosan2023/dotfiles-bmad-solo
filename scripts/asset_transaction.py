"""受管文件批次提交：先备份、逐文件提交，失败时按真实状态恢复。

调用者必须在整个预检、提交和恢复期间持有同一部署锁。
这不是跨目录原子事务；进程被强制终止时保留日志及备份，供后续恢复。
不防御不遵守锁协议的外部写入者在最终复核后的竞态。
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path

from asset_safety import (
    AssetError, Snapshot, atomic_replace, checked_path,
    check_writable_parent, require_unchanged, snapshot,
)
from managed_files import validate_snapshot


@dataclass(frozen=True)
class TargetChange:
    path: Path
    before: Snapshot
    after: Snapshot


class TransactionError(AssetError):
    """提交失败；日志描述已恢复或需要人工处理的目标。"""


def sync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def apply_snapshot(path: Path, expected: Snapshot, desired: Snapshot) -> None:
    if desired.content is None:
        require_unchanged(path, expected)
        if expected.content is not None:
            checked_path(path).unlink()
            sync_directory(path.parent)
    else:
        atomic_replace(path, desired.content, expected, mode=desired.mode)


def preflight(changes: tuple[TargetChange, ...], allowed_roots: tuple[Path, ...]) -> tuple[TargetChange, ...]:
    """只读检查所有目标；父目录须已存在，目录准备由部署调用者负责。"""
    roots = tuple(checked_path(root) for root in allowed_roots)
    if not roots or any(not root.is_dir() for root in roots):
        raise AssetError("必须提供已经存在的允许写入根目录")
    normalized = []
    seen = set()
    for change in changes:
        path = checked_path(change.path)
        if not any(path != root and path.is_relative_to(root) for root in roots):
            raise AssetError(f"目标超出授权根目录：{path}")
        if path in seen:
            raise AssetError(f"重复提交目标：{path}")
        seen.add(path)
        validate_snapshot(change.before, allow_missing=True)
        validate_snapshot(change.after, allow_missing=True)
        if not path.parent.is_dir():
            raise AssetError(f"目标父目录尚未准备：{path.parent}")
        check_writable_parent(path)
        require_unchanged(path, change.before)
        normalized.append(TargetChange(path, change.before, change.after))
    for path in seen:
        if any(parent in seen for parent in path.parents):
            raise AssetError(f"提交目标存在文件与目录冲突：{path}")
    return tuple(normalized)


def commit_changes(
    changes: tuple[TargetChange, ...],
    allowed_roots: tuple[Path, ...],
    journal_dir: Path,
) -> Path:
    """持锁调用；日志目录必须不存在，父目录必须已经存在。

    完整保存原字节及权限后才开始目标写入；日志也使用原子替换。
    日志目录永久保留，不在失败时删除取证资料。
    无法安全恢复的外部编辑保留原样，并标记恢复受阻。
    """
    changes = preflight(changes, allowed_roots)
    journal_dir = checked_path(journal_dir)
    if journal_dir.exists() or not journal_dir.parent.is_dir():
        raise AssetError("日志目录必须是已有父目录下的全新路径")
    for change in changes:
        if (change.path == journal_dir
                or change.path.is_relative_to(journal_dir)
                or journal_dir.is_relative_to(change.path)):
            raise AssetError("日志目录不能与提交目标重叠")
    check_writable_parent(journal_dir)
    journal_dir.mkdir(mode=0o700)
    sync_directory(journal_dir.parent)
    journal_path = journal_dir / "transaction.json"
    journal_expected = Snapshot(None, None)
    records = []
    state = {"schema_version": 1, "status": "PREPARING", "targets": records}

    def save_state():
        nonlocal journal_expected
        content = (json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        atomic_replace(journal_path, content, journal_expected, mode=0o600)
        journal_expected = Snapshot(content, 0o600)

    # 准备阶段失败时没有目标写入；不尝试删除部分备份。
    for index, change in enumerate(changes):
        backup_name = None
        if change.before.content is not None:
            backup_name = f"{index:06d}.before"
            atomic_replace(journal_dir / backup_name, change.before.content,
                           Snapshot(None, None), mode=0o600)
        records.append({
            "path": str(change.path), "backup": backup_name,
            "before_sha256": change.before.digest,
            "before_mode": change.before.mode,
            "after_sha256": change.after.digest,
            "after_mode": change.after.mode,
            "status": "PREPARED",
        })
    state["status"] = "PREPARED"
    save_state()

    attempted = []
    try:
        # 备份期间发生的任何目标变化都必须在首个目标写入前阻塞。
        for change in changes:
            require_unchanged(change.path, change.before)
        state["status"] = "COMMITTING"
        save_state()
        for index, change in enumerate(changes):
            if change.before == change.after:
                records[index]["status"] = "UNCHANGED"
                continue
            records[index]["status"] = "APPLYING"
            save_state()
            # 先登记尝试，覆盖替换成功但目录同步失败的异常边界。
            attempted.append(index)
            apply_snapshot(change.path, change.before, change.after)
            require_unchanged(change.path, change.after)
            records[index]["status"] = "APPLIED"
            save_state()
        state["status"] = "COMMITTED"
        save_state()
        return journal_path
    except Exception as exc:
        failures = []
        for index in reversed(attempted):
            change = changes[index]
            try:
                actual = snapshot(change.path)
                if actual == change.before:
                    records[index]["status"] = "RESTORED"
                    continue
                if actual != change.after:
                    raise AssetError("目标与提交前后状态均不符，保留外部修改")
                apply_snapshot(change.path, actual, change.before)
                require_unchanged(change.path, change.before)
                records[index]["status"] = "RESTORED"
            except Exception as recovery_exc:
                records[index]["status"] = "RECOVERY_BLOCKED"
                records[index]["error"] = str(recovery_exc)
                failures.append(str(change.path))
        state["status"] = "RECOVERY_BLOCKED" if failures else "ROLLED_BACK"
        state["error"] = str(exc)
        try:
            # 日志替换后同步失败时，先识别真实日志，避免沿用旧快照。
            journal_expected = snapshot(journal_path)
            save_state()
        except Exception as journal_exc:
            failures.append(f"恢复日志写入失败：{journal_exc}")
        detail = "; ".join(failures) if failures else "已恢复本批次尝试修改的目标"
        raise TransactionError(f"提交失败：{exc}；{detail}；日志：{journal_path}") from exc
