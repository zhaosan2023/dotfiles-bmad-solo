"""计算受管文件变更，不执行文件写入或删除。

未知文件保留；首次同路径接管必须获得明确授权。
所有权摘要须来自经部署调用者校验的清单，而不是从当前目标推断。
本模块不提供事务保证：调用者仍须持锁、备份、复核并记录提交和恢复结果。
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import PurePosixPath
import re

from asset_safety import AssetError, Snapshot


@dataclass(frozen=True)
class FileChange:
    relative_path: str
    before: Snapshot
    after: Snapshot


@dataclass(frozen=True)
class FilePlan:
    changes: tuple[FileChange, ...]
    owned: dict[str, dict[str, str | int]]


def validate_relative_path(value: str) -> None:
    """清单采用规范化的 POSIX 相对路径，拒绝含糊或越界路径。"""
    if not isinstance(value, str) or not value:
        raise AssetError("受管文件路径必须是非空字符串")
    if "\\" in value or any(ord(character) < 32 for character in value):
        raise AssetError(f"受管文件路径包含非法字符：{value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in value.split("/")):
        raise AssetError(f"受管文件路径必须是规范相对路径：{value!r}")
    if str(path) != value:
        raise AssetError(f"受管文件路径未规范化：{value!r}")


def validate_snapshot(value: Snapshot, *, allow_missing: bool) -> None:
    if not isinstance(value, Snapshot):
        raise AssetError("文件状态必须为 Snapshot")
    if value.content is None:
        if not allow_missing or value.mode is not None:
            raise AssetError("缺失文件状态非法")
        return
    if not isinstance(value.content, bytes):
        raise AssetError("文件内容必须为字节")
    if type(value.mode) is not int or not 0 <= value.mode <= 0o777:
        raise AssetError("拒绝非法权限或特殊权限位")


def ownership_record(value: Snapshot) -> dict[str, str | int]:
    validate_snapshot(value, allow_missing=False)
    return {
        "sha256": hashlib.sha256(value.content).hexdigest(),
        "mode": value.mode,
    }


def plan_files(
    current: dict[str, Snapshot],
    desired: dict[str, Snapshot],
    owned: dict[str, dict[str, str | int]],
    *,
    adopt: frozenset[str] = frozenset(),
    uninstall: bool = False,
) -> FilePlan:
    """计算全目标预检的一部分，返回确定顺序的变更和新所有权。

    current 必须包含 desired 与 owned 中每个路径的真实快照；
    缺失文件也必须显式传入 Snapshot(None, None)，不能省略探测。
    非受管文件即使内容与源一致，也不会被自动接管。
    用户修改过或删除过的受管文件均阻塞更新与卸载。
    """
    if not all(isinstance(mapping, dict) for mapping in (current, desired, owned)):
        raise AssetError("文件状态、源文件及所有权清单必须为映射")
    if not isinstance(adopt, (set, frozenset)):
        raise AssetError("接管授权必须是明确的相对路径集合")
    for path in {*current, *desired, *owned, *adopt}:
        validate_relative_path(path)
    if uninstall and (desired or adopt):
        raise AssetError("卸载不能同时指定部署源或首次接管授权")
    if not set(adopt).issubset(desired):
        raise AssetError("接管授权包含部署源中不存在的文件")

    required = set(desired) | set(owned)
    if not required.issubset(current):
        raise AssetError("预检缺少目标快照，不能将未探测路径当作缺失")
    for value in current.values():
        validate_snapshot(value, allow_missing=True)
    for value in desired.values():
        validate_snapshot(value, allow_missing=False)

    # 文件路径不能同时用作另一个受管文件的父目录。
    for path in required:
        for parent in PurePosixPath(path).parents:
            if str(parent) in required:
                raise AssetError(f"受管文件与目录路径冲突：{path}")

    for path, record in owned.items():
        if not isinstance(record, dict) or set(record) != {"sha256", "mode"}:
            raise AssetError(f"受管文件所有权记录非法：{path}")
        digest = record["sha256"]
        mode = record["mode"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise AssetError(f"受管文件摘要非法：{path}")
        if type(mode) is not int or not 0 <= mode <= 0o777:
            raise AssetError(f"受管文件权限记录非法：{path}")
        before = current[path]
        if before.content is None:
            raise AssetError(f"受管文件已缺失，需显式对账：{path}")
        if ownership_record(before) != record:
            raise AssetError(f"受管文件已被修改，拒绝覆盖或卸载：{path}")

    for path in desired:
        if current[path].content is not None and path not in owned and path not in adopt:
            raise AssetError(f"首次同路径接管需要明确授权：{path}")

    changes = []
    for path in sorted(required):
        before = current[path]
        after = desired.get(path, Snapshot(None, None))
        if before != after:
            changes.append(FileChange(path, before, after))
    new_owned = {path: ownership_record(value) for path, value in sorted(desired.items())}
    return FilePlan(tuple(changes), new_owned)
