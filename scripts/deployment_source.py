"""将物理套件源映射为受管部署输入；只读，不探测 IDE 或写入目标。

拒绝链接、特殊文件及不完整套件；源快照与目标路径分离。
调用者负责目标授权、版本选择、部署锁和提交前源快照复核。
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

from asset_safety import AssetError, checked_path, parse_modes, require_unchanged, snapshot
from managed_files import validate_relative_path, validate_snapshot


REQUIRED_FILES = (
    "plugin.json",
    "rules/bmad-constitution.md",
    "rules/bmad-core.md",
    "roo/rules/01-bmad-constitution.md",
    "roo/rules/02-bmad-core.md",
    "roo/rules-ana-architect/01-ana-solo-core.md",
    "roo/rules-bmad-engineer/01-bmad-engineer-core.md",
    "roo/settings/custom_modes.yaml",
)


def collect_source(source: Path, mode_targets: tuple[str, ...]):
    """返回普通文件映射、模式合并输入以及源快照。

    目标路径相对于后续部署根目录；本函数不赋予写入这些路径的权限。
    现阶段仅接受包含 Roo 资产的套件，无 Roo 源的降级失败关闭。
    """
    source = checked_path(source)
    if not source.is_dir():
        raise AssetError("套件源必须是已经存在的物理目录")
    if not isinstance(mode_targets, tuple):
        raise AssetError("模式目标必须为显式路径元组")
    for relative in mode_targets:
        validate_relative_path(relative)
    if len(set(mode_targets)) != len(mode_targets):
        raise AssetError("模式目标重复")

    sources = {}

    def walk(directory):
        with os.scandir(directory) as entries:
            children = sorted(entries, key=lambda entry: entry.name)
        for entry in children:
            path = checked_path(Path(entry.path))
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                walk(path)
            elif stat.S_ISREG(info.st_mode):
                relative = path.relative_to(source).as_posix()
                validate_relative_path(relative)
                value = snapshot(path)
                validate_snapshot(value, allow_missing=False)
                sources[relative] = value
            else:
                raise AssetError(f"源包含非普通文件：{path}")

    walk(source)
    missing = set(REQUIRED_FILES) - set(sources)
    if missing:
        raise AssetError("套件缺少必需资产，拒绝不完整部署：" + ", ".join(sorted(missing)))
    if ".manifest.json" in sources:
        raise AssetError("套件源包含部署生成的清单，拒绝混入目标状态")

    mode_source = sources["roo/settings/custom_modes.yaml"].content
    mode_data = parse_modes(mode_source)
    if set(mode_data) != {"customModes"} or not mode_data["customModes"]:
        raise AssetError("源模式必须只包含非空 customModes 列表")

    files = {}
    for relative, value in sources.items():
        files[f".gemini/config/plugins/bmad-suite/{relative}"] = value
    for name in ("bmad-constitution.md", "bmad-core.md"):
        files[f".gemini/config/rules/{name}"] = sources[f"rules/{name}"]
    for relative, value in sources.items():
        if any(relative.startswith(f"roo/{directory}/") for directory in (
            "rules", "rules-ana-architect", "rules-bmad-engineer"
        )):
            files[f".roo/{relative.removeprefix('roo/')}"] = value
    if set(mode_targets) & set(files):
        raise AssetError("模式合并目标与普通文件部署目标重叠")
    modes = {relative: mode_source for relative in mode_targets}
    return files, modes, sources


def verify_source(source: Path, sources):
    """复核已采集文件内容与权限；不声称提供源目录整体原子快照。"""
    source = checked_path(source)
    for relative, expected in sources.items():
        validate_relative_path(relative)
        require_unchanged(source / relative, expected)
