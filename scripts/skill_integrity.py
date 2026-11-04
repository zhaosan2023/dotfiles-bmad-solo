"""安装来源的技能快照门禁；不加载或执行所选标签包中的校验脚本。

v4.3 起声明的发布须满足当前双技能契约；旧发布与缺声明来源保持
既有兼容边界，不因此获得新的完整性或运行时通过声明。
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

from asset_safety import AssetError, checked_path
from release_version import parse_release


TRUSTED_VALIDATOR = (
    Path(__file__).absolute().parents[1]
    / "bmad-suite-v4/skills/bmad/scripts/validate-solo-package.py"
)


def validate_source_skills(source, sources):
    """只消费采集快照；校验实现固定来自本部署入口所属仓库。"""
    declaration = sources.get("VERSION")
    if declaration is None:
        return None
    version = parse_release(declaration.content)
    if int(version.split(".")[1]) < 3:
        return None
    path = checked_path(TRUSTED_VALIDATOR)
    if not path.is_file():
        raise AssetError("当前部署入口缺少可信技能校验实现；停止部署")
    specification = importlib.util.spec_from_file_location(
        "_bmad_install_skill_integrity", path,
    )
    if specification is None or specification.loader is None:
        raise AssetError("无法加载当前部署入口的技能校验实现；停止部署")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    assets = {
        name.removeprefix("skills/"): value.content
        for name, value in sources.items() if name.startswith("skills/")
    }
    try:
        return module.validate_assets(Path(source) / "skills", assets)
    except (module.PackageError, UnicodeError, yaml.YAMLError) as exc:
        raise AssetError(f"发布 {version} 的技能完整性预检失败：{exc}") from exc
