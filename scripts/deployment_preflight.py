"""只读迁移范围检查：列出所有冲突，不将诊断结果作为接管授权。

复用严格所有权校验；不创建目录、锁、缓存或事务，不推断旧镜像所有权。
"""
from dataclasses import dataclass
import json
import os

from asset_safety import (
    AssetError, checked_path, parse_modes, require_unchanged, snapshot,
)
from deploy_managed import load_manifest, prepare, _under, _unique_object
from managed_files import plan_files
from managed_modes import merge_modes


@dataclass(frozen=True)
class PreflightReport:
    scope: tuple[str, ...]
    errors: tuple[str, ...]
    adopt_files: tuple[str, ...]
    adopt_modes: tuple[str, ...]

    def print(self):
        print("只读迁移范围预检；未写入，以下清单不授予接管、删除或迁移权限。")
        for item in self.scope:
            print(f"  {item}")
        print(f"待授权同路径文件：{len(self.adopt_files)} 个")
        for relative in self.adopt_files:
            print(f"  文件接管待授权：{relative}")
        print(f"待授权同标识模式：{len(self.adopt_modes)} 个")
        for specification in self.adopt_modes:
            print(f"  模式接管待授权：{specification}")
        for error in self.errors:
            print(f"  阻塞：{error}")
        print("未纳入来源或历史所有权的旧资产保留；未验证 Roo 运行时加载。")


def inspect_migration(root, state, files, modes, *, adopt_files=frozenset(),
                      adopt_modes=None):
    """聚合全部目标的范围和阻塞，再用完整 prepare 复核交叉目标约束。

    显式授权只用于普通部署调用；--preflight 入口禁止携带授权。
    未授权内容即使与来源完全相同，也列为待授权而非自动接管。
    """
    root, state = checked_path(root), checked_path(state)
    adopt_modes = {} if adopt_modes is None else adopt_modes
    manifest_path = state / "ownership.json"
    manifest_before = snapshot(manifest_path)
    old = load_manifest(manifest_before.content)
    scope, errors, pending_files, pending_modes = [], [], [], []
    observed = {manifest_path: manifest_before}
    scope.append("所有权记录：" + (
        "缺失；旧资产不能自动视为受管" if manifest_before.content is None
        else "存在；逐目标核验摘要"
    ))
    file_paths = set(files) | set(old["files"])
    mode_paths = set(modes) | set(old["modes"])
    for relative in sorted(file_paths | mode_paths):
        try:
            target = _under(root, relative)
            if (target == state or target.is_relative_to(state)
                    or state.is_relative_to(target)):
                raise AssetError("目标与部署状态目录重叠")
            before = snapshot(target)
            observed[target] = before
            if relative in file_paths:
                if relative in mode_paths:
                    raise AssetError("普通文件和模式配置目标重叠")
                owned = {relative: old["files"][relative]} if relative in old["files"] else {}
                desired = {relative: files[relative]} if relative in files else {}
                if desired and before.content is not None and not owned:
                    equal = before == files[relative]
                    scope.append(f"同路径未受管文件（{'内容及权限相同' if equal else '内容或权限不同'}）：{relative}")
                    if relative not in adopt_files:
                        pending_files.append(relative)
                elif not desired:
                    scope.append(f"历史受管文件拟退役（仍须摘要匹配）：{relative}")
                else:
                    action = "拟新增" if before.content is None else (
                        "无需改写" if before == files[relative] else "拟更新受管文件"
                    )
                    scope.append(f"{action}：{relative}")
                plan_files({relative: before}, desired, owned,
                           adopt={relative} if relative in adopt_files else frozenset())
            else:
                existing = {} if before.content is None else parse_modes(before.content)
                current = {mode["slug"] for mode in existing.get("customModes", [])}
                desired_content = modes.get(relative)
                desired = set() if desired_content is None else {
                    mode["slug"] for mode in parse_modes(desired_content)["customModes"]
                }
                owned = old["modes"].get(relative, {})
                collisions = current & desired - set(owned)
                for slug in sorted(collisions - set(adopt_modes.get(relative, ()))):
                    pending_modes.append(f"{relative}={slug}")
                personal = sorted(current - desired - set(owned))
                scope.append(f"模式目标：{relative}；来源模式={','.join(sorted(desired)) or '无'}；保留个人模式={','.join(personal) or '无'}；待接管同标识={','.join(sorted(collisions)) or '无'}")
                merge_modes(before.content, desired_content, owned,
                            uninstall=relative not in modes,
                            adopt=adopt_modes.get(relative, frozenset()))
        except (AssetError, OSError) as exc:
            errors.append(f"{relative}：{exc}")

    # 未完成事务在只读预检阶段就阻塞，不等到创建锁或状态目录之后。
    journals = sorted(state.glob("transaction-*"))
    for directory in journals:
        try:
            directory = checked_path(directory)
            if not directory.is_dir():
                raise AssetError("事务路径不是目录")
            path = directory / "transaction.json"
            record = snapshot(path)
            observed[path] = record
            if record.content is None:
                raise AssetError("备份准备未完成，缺少事务日志")
            data = json.loads(record.content, object_pairs_hook=_unique_object)
            if not isinstance(data, dict) or data.get("status") not in {"COMMITTED", "ROLLED_BACK"}:
                raise AssetError("事务未完成或恢复受阻，先对账")
        except (AssetError, OSError, ValueError, TypeError) as exc:
            errors.append(f"{directory.name}：{exc}")
    # 仅盘点部署涉及的资产容器；未知旧文件一律保留，不读其正文或跟随链接。
    # 不扫描用户目录其余部分，也不把来源缺失的旧文件加入删除计划。
    known = file_paths | mode_paths
    containers = (
        ".gemini/config/plugins/bmad-suite", ".gemini/config/rules",
        ".roo/rules", ".roo/rules-ana-architect", ".roo/rules-bmad-engineer",
    )

    def inventory(directory):
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            path = directory / entry.name
            relative = path.relative_to(root).as_posix()
            if entry.is_dir(follow_symlinks=False):
                inventory(checked_path(path))
            elif relative not in known:
                scope.append(f"未受管旧资产保留（不接管、不删除）：{relative}")

    for relative in containers:
        try:
            directory = checked_path(root / relative)
            if directory.is_dir():
                inventory(directory)
        except (AssetError, OSError) as exc:
            errors.append(f"旧资产盘点受阻：{relative}：{exc}")
    try:
        prepare(root, state, files, modes,
                adopt_files=adopt_files, adopt_modes=adopt_modes)
    except (AssetError, OSError) as exc:
        message = str(exc)
        if not any(message in error for error in errors):
            errors.append(message)
    for path, expected in observed.items():
        try:
            require_unchanged(path, expected)
        except (AssetError, OSError) as exc:
            errors.append(str(exc))
    if sorted(state.glob("transaction-*")) != journals:
        errors.append("预检期间事务集合发生变化，须重新核验")
    return PreflightReport(tuple(scope), tuple(errors),
                           tuple(pending_files), tuple(pending_modes))
