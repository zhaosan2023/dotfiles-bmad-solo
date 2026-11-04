"""从已核验的套件快照构造 Cline 原生技能与全局路由资产，不读写部署目标。

仅负责静态适配；调用方仍须明确目标授权，并使用受管事务处理资产。
本模块不启动 Cline，不保证技能自动触发、模式绑定或程序权限隔离。
原始套件保持不变；安装专用的技能包校验器留在原始套件中，不作为
Cline 运行技能分发，因为其默认目录与内部校验契约使用原始套件布局。
"""
from __future__ import annotations

from pathlib import Path
import re

import yaml

from asset_safety import AssetError, Snapshot
from managed_files import validate_relative_path, validate_snapshot
from skill_integrity import validate_source_skills


SKILL_PREFIX = ".cline/skills/"
ROUTER_SOURCE = "cline/templates/bmad-router.md"
ROUTER_TARGET = ".cline/rules/bmad-router.md"
ENTRY_DIRECTORIES = {"bmad": "bmad-solo", "ana-solo": "ana-solo"}
INSTALL_ONLY = "skills/bmad/scripts/validate-solo-package.py"
LINKS = re.compile(rb"\]\((\.\./bmad/[^)\s]+)\)")


def cline_router(value: Snapshot, sources):
    """仅适配套件链接；全局副本相对规则目录，项目私有导航仍相对工作区。

    引用必须来自同批冻结快照，保留片段和行定位，不补读磁盘来源。
    """
    def replace(match):
        destination = match.group(1).decode("utf-8")
        relative = destination.removeprefix("bmad-suite-v4/")
        physical = re.sub(r":\d+$", "", relative.split("#", 1)[0])
        validate_relative_path(physical)
        if physical not in sources:
            raise AssetError(f"Cline 路由引用的套件资产缺失：{physical}")
        if physical.startswith("skills/"):
            parts = physical.split("/", 2)
            if (len(parts) != 3 or parts[1] not in ENTRY_DIRECTORIES
                    or physical == INSTALL_ONLY):
                raise AssetError(f"Cline 路由引用未分发技能：{physical}")
            target = "../skills/" + ENTRY_DIRECTORIES[parts[1]] + "/" + parts[2]
        else:
            target = "../../.gemini/config/plugins/bmad-suite/" + physical
        return ("](" + target + relative[len(physical):] + ")").encode("utf-8")

    content = re.sub(rb"\]\((bmad-suite-v4/[^)\s]+)\)", replace, value.content)
    return Snapshot(content, value.mode)


def cline_skill_files(source: Path, sources):
    """消费完整、冻结的源快照，返回相对于部署根的文件映射。

    必须先通过当前部署入口的可信技能门禁；旧来源不能因适配获得
    v4.3 的完整性声明。Cline 的目录名与入口 name 必须完全一致，
    因此仅在分发副本中将 bmad 目录映射为 bmad-solo，同时适配
    ana-solo 指向该目录的 Markdown 链接，保留片段与行定位。
    全局路由同批映射到 .cline/rules；所有其他运行资源保留原字节与权限，
    不读取源目录来补齐快照，不在此执行写入或宿主激活。
    """
    if not isinstance(sources, dict):
        raise AssetError("Cline 技能来源必须为完整源快照映射")
    for relative, value in sources.items():
        validate_relative_path(relative)
        validate_snapshot(value, allow_missing=False)
    if validate_source_skills(source, sources) is None:
        raise AssetError("Cline 原生技能适配需要已声明且通过完整性门禁的 v4.3 或更新来源")

    files = {}
    for relative, value in sources.items():
        if not relative.startswith("skills/") or relative == INSTALL_ONLY:
            continue
        parts = relative.split("/", 2)
        if len(parts) != 3 or parts[1] not in ENTRY_DIRECTORIES:
            raise AssetError(f"Cline 技能来源包含未支持的技能目录：{relative}")
        directory = ENTRY_DIRECTORIES[parts[1]]
        destination = SKILL_PREFIX + directory + "/" + parts[2]
        validate_relative_path(destination)
        content = value.content
        if relative.endswith(".md"):
            content = LINKS.sub(
                lambda match: b"](../bmad-solo/" + match.group(1)[8:] + b")",
                content,
            )
        files[destination] = Snapshot(content, value.mode)

    for directory in ENTRY_DIRECTORIES.values():
        relative = SKILL_PREFIX + directory + "/SKILL.md"
        value = files.get(relative)
        if value is None:
            raise AssetError(f"Cline 原生技能缺少入口：{relative}")
        lines = value.content.decode("utf-8").splitlines()
        # 上游快照门禁已检查 YAML 唯一键、正文及入口身份；这里检查宿主约束。
        header = yaml.safe_load("\n".join(lines[1:lines.index("---", 1)]))
        if header["name"] != directory:
            raise AssetError(f"Cline 技能名称与目录不一致：{relative}")
        if len(header["description"]) > 1024:
            raise AssetError(f"Cline 技能描述超过 1024 字符：{relative}")
    router = sources.get(ROUTER_SOURCE)
    if router is None:
        raise AssetError(f"Cline 全局路由缺少来源：{ROUTER_SOURCE}")
    files[ROUTER_TARGET] = cline_router(router, sources)
    return files
