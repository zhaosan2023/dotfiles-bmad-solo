"""只读发现已有 Roo 扩展存储；显式目标由调用者优先处理。

存储命中不证明扩展正在运行，不创建配置或从插件镜像推断 IDE 模式。
"""
from pathlib import Path

from asset_safety import AssetError, checked_path


STORAGE_SUFFIX = "User/globalStorage/rooveterinaryinc.roo-cline"
KNOWN_STORAGES = (
    f".antigravity-ide-server/data/{STORAGE_SUFFIX}",
    f".antigravity-server/data/{STORAGE_SUFFIX}",
    f".vscode-server/data/{STORAGE_SUFFIX}",
    f".vscode-server-insiders/data/{STORAGE_SUFFIX}",
    f".config/Code/{STORAGE_SUFFIX}",
    f".config/Antigravity IDE/{STORAGE_SUFFIX}",
    f".config/Antigravity/{STORAGE_SUFFIX}",
)


def discover_mode_targets(root: Path) -> tuple[str, ...]:
    """发现标准 Linux 宿主和已有本机配置布局；不递归扫描整个用户目录。"""
    root = checked_path(root)
    candidates = set(KNOWN_STORAGES)
    config = checked_path(root / ".config")
    if config.is_dir():
        for storage in config.glob(f"*/{STORAGE_SUFFIX}"):
            candidates.add(storage.relative_to(root).as_posix())
    selected = []
    for relative in sorted(candidates):
        storage = checked_path(root / relative)
        if not storage.exists():
            print(f"跳过模式候选（存储目录不存在）：{relative}/settings")
            continue
        if not storage.is_dir():
            raise AssetError(f"Roo 存储路径不是目录：{relative}")
        target = f"{relative}/settings/custom_modes.yaml"
        checked_path(root / target)
        selected.append(target)
        print(f"模式候选待预检：{relative}/settings")
    return tuple(selected)
