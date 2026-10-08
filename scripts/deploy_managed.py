"""受管部署协调器：统一预检、合并、持锁和记录所有权。

仅支持显式传入的文件集合及模式目标；目标发现和版本选择由入口负责。
清单路径和日志位于独立状态目录，不从目标现有内容推断所有权。
"""
from __future__ import annotations

import json
from pathlib import Path
import uuid

from asset_safety import (
    AssetError, Snapshot, checked_path, check_writable_parent,
    deployment_lock, require_unchanged, snapshot,
)
from asset_transaction import TargetChange, commit_changes
from managed_files import plan_files, validate_relative_path
from managed_modes import merge_modes


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AssetError(f"清单存在重复键：{key}")
        result[key] = value
    return result


def load_manifest(content):
    if content is None:
        return {"schema_version": 1, "files": {}, "modes": {}}
    try:
        result = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, ValueError) as exc:
        raise AssetError(f"部署清单损坏：{exc}") from exc
    if (not isinstance(result, dict)
            or set(result) != {"schema_version", "files", "modes"}
            or type(result["schema_version"]) is not int
            or result["schema_version"] != 1
            or not isinstance(result["files"], dict)
            or not isinstance(result["modes"], dict)):
        raise AssetError("部署清单结构或版本不受支持")
    return result


def _under(root, relative):
    validate_relative_path(relative)
    path = checked_path(root / relative)
    if not path.is_relative_to(root) or path == root:
        raise AssetError(f"目标越界：{relative}")
    return path


def prepare(root, state_dir, files, modes, *, uninstall=False,
            adopt_files=frozenset(), adopt_modes=None):
    """只读生成全部目标变更；缺失父目录在这里不创建。

    files 为相对路径到源快照的映射，modes 为相对路径到源 YAML 字节的映射。
    模式接管授权按目标路径分别指定，避免授权无意扩散到其他 IDE。
    """
    root = checked_path(root)
    state_dir = checked_path(state_dir)
    if not root.is_dir():
        raise AssetError("部署根目录必须已存在")
    if state_dir.exists() and not state_dir.is_dir():
        raise AssetError("部署状态路径必须是目录")
    check_writable_parent(state_dir / "ownership.json")
    if not state_dir.is_relative_to(root) or state_dir == root:
        raise AssetError("状态目录必须位于部署根目录内且不能等于根目录")
    if not isinstance(files, dict) or not isinstance(modes, dict):
        raise AssetError("源文件和模式目标必须为映射")
    if uninstall and (files or modes or adopt_files or adopt_modes):
        raise AssetError("卸载不得同时提供源资产或接管授权")
    adopt_modes = {} if adopt_modes is None else adopt_modes
    if not isinstance(adopt_modes, dict) or not set(adopt_modes).issubset(modes):
        raise AssetError("模式接管授权包含未知目标")
    manifest_path = state_dir / "ownership.json"
    manifest_before = snapshot(manifest_path)
    old = load_manifest(manifest_before.content)
    file_paths = set(files) | set(old["files"])
    mode_paths = set(modes) | set(old["modes"])
    if file_paths & mode_paths:
        raise AssetError("普通文件与模式配置不能共享同一目标")
    all_paths = file_paths | mode_paths
    targets = {relative: _under(root, relative) for relative in all_paths}
    for path in targets.values():
        if (path == state_dir or path.is_relative_to(state_dir)
                or state_dir.is_relative_to(path)):
            raise AssetError("受管目标不能与部署状态目录重叠")
        check_writable_parent(path)
        if any(parent in targets.values() for parent in path.parents):
            raise AssetError("目标存在文件与目录冲突")
    current = {relative: snapshot(targets[relative]) for relative in file_paths}
    file_plan = plan_files(current, files, old["files"],
                           adopt=adopt_files, uninstall=uninstall)
    changes = [TargetChange(targets[item.relative_path], item.before, item.after)
               for item in file_plan.changes]
    new_modes = {}
    mode_snapshots = {}
    for relative in sorted(mode_paths):
        before = snapshot(targets[relative])
        mode_snapshots[relative] = before
        retiring = uninstall or relative not in modes
        merged = merge_modes(before.content, modes.get(relative),
                             old["modes"].get(relative, {}),
                             uninstall=retiring,
                             adopt=adopt_modes.get(relative, frozenset()))
        if not retiring:
            new_modes[relative] = merged.owned
        # 保留既有模式配置文件及其第三方字段；不删除整个配置文件。
        after = Snapshot(merged.content, before.mode if before.mode is not None else 0o600)
        if before != after:
            changes.append(TargetChange(targets[relative], before, after))
    new = {"schema_version": 1, "files": file_plan.owned, "modes": new_modes}
    if new != old or manifest_before.content is None:
        content = (json.dumps(new, ensure_ascii=False, sort_keys=True, indent=2)
                   + "\n").encode("utf-8")
        changes.append(TargetChange(manifest_path, manifest_before, Snapshot(content, 0o600)))
    # 无变更的受管目标也纳入提交前复核，不能漏掉幂等资产的外部编辑。
    changed = {item.path for item in changes}
    for relative, path in sorted(targets.items()):
        if path not in changed:
            # 保留合并校验时的快照，不能重新读取并把外部编辑接受为基线。
            before = current[relative] if relative in current else mode_snapshots[relative]
            changes.append(TargetChange(path, before, before))
    if manifest_path not in {item.path for item in changes}:
        changes.append(TargetChange(manifest_path, manifest_before, manifest_before))
    return tuple(changes)


def deploy(root, state_dir, files, modes, *, dry_run=False, uninstall=False,
           adopt_files=frozenset(), adopt_modes=None):
    """首次部署先只读预检，再准备状态目录；模拟执行不创建目录、锁或日志。

    对未完成批次失败关闭，保留备份，禁止新部署覆盖恢复证据。
    普通异常自动恢复文件；强制终止后的恢复需独立审核日志，不能自动重放。
    """
    root = checked_path(root)
    state_dir = checked_path(state_dir)
    options = dict(uninstall=uninstall, adopt_files=adopt_files, adopt_modes=adopt_modes)
    if dry_run:
        return prepare(root, state_dir, files, modes, **options)
    if not state_dir.is_relative_to(root) or state_dir == root:
        raise AssetError("状态目录必须位于部署根目录内且不能等于根目录")
    if not state_dir.exists():
        # 首次安装也必须在创建状态目录前完成全目标只读预检。
        # 此预检不授予提交权限；获得锁后重新读取所有权和目标状态。
        prepare(root, state_dir, files, modes, **options)
        missing = []
        parent = state_dir
        while not parent.exists():
            missing.append(parent)
            parent = parent.parent
        for directory in reversed(missing):
            try:
                checked_path(directory).mkdir(mode=0o700)
            except FileExistsError:
                # 另一个首次安装进程可能已经创建目录；仍须核验链接和类型。
                if not checked_path(directory).is_dir():
                    raise AssetError(f"状态目录创建冲突：{directory}")
    if not checked_path(state_dir).is_dir():
        raise AssetError("部署状态路径必须是物理目录")
    with deployment_lock(state_dir / "deployment.lock"):
        for directory in sorted(state_dir.glob("transaction-*")):
            directory = checked_path(directory)
            record = snapshot(directory / "transaction.json")
            if record.content is None:
                raise AssetError(f"存在未完成的备份准备目录，先对账：{directory}")
            try:
                status = json.loads(record.content, object_pairs_hook=_unique_object)["status"]
            except (ValueError, KeyError, TypeError) as exc:
                raise AssetError(f"事务日志损坏：{directory}") from exc
            if status not in {"COMMITTED", "ROLLED_BACK"}:
                raise AssetError(f"存在尚未完成恢复的事务：{directory}")
        changes = prepare(root, state_dir, files, modes, **options)
        # 幂等返回也必须复核预检快照，不能漏报预检后的外部修改。
        for change in changes:
            require_unchanged(change.path, change.before)
        if all(change.before == change.after for change in changes):
            return None
        created = []
        try:
            # 所有输入及目标预检完成后才创建缺失目录，不修改已有目录权限。
            for change in changes:
                missing = []
                parent = change.path.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    checked_path(directory).mkdir(mode=0o700)
                    created.append(directory)
            return commit_changes(changes, (root,),
                                  state_dir / f"transaction-{uuid.uuid4().hex}")
        except Exception:
            # 仅清理由本批次创建且仍为空的目录，绝不递归删除。
            for directory in reversed(created):
                try:
                    checked_path(directory).rmdir()
                except (OSError, AssetError):
                    pass
            raise
