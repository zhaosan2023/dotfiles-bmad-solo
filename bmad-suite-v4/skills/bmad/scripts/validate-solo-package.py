#!/usr/bin/env python3
"""只读校验两个技能入口及套件内引用；不执行技能、目标代码或安装依赖。

仅证明静态资产完整性，不证明宿主加载、技能调用或上游同步。
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
import stat
import sys
from urllib.parse import unquote, urlsplit

import yaml


DEFAULT_SUITE = Path(__file__).absolute().parents[3]
ENTRY_NAMES = {
    "bmad/SKILL.md": "bmad-solo",
    "ana-solo/SKILL.md": "ana-solo",
}
REQUIRED_REFERENCES = (
    "bmad/references/capability-map.md",
    "bmad/references/governance-contract.md",
    "bmad/references/mode-analyst.md",
    "bmad/references/mode-product.md",
    "bmad/references/mode-architect.md",
    "bmad/references/mode-developer.md",
    "bmad/references/mode-reviewer.md",
    "bmad/references/mode-operator.md",
    "bmad/references/templates/implementation-plan.template.md",
    "bmad/references/templates/task-unit.template.md",
    "ana-solo/references/convergence-locks.md",
    "ana-solo/references/decision-matrix.md",
    "ana-solo/references/paper-reading-guide.md",
)
REQUIRED_PROCEDURES = (
    "algorithm-fit", "architecture-baseline", "architecture-debug",
    "architecture-decision", "architecture-preflight", "architecture-recheck",
    "brownfield-distill-governance", "build", "code-review", "correct-course",
    "record-findings", "state-reconcile", "three-pass-analysis",
)
LINKS = re.compile(r"\[[^\]\n]*\]\(([^)\n]+)\)")
FORBIDDEN_DEPENDENCIES = re.compile(
    r"_bmad-solo-source/|legacy-skills/|bmad-method-source/|"
    r"_bmad/scripts/|_bmad/core/|bmm/config\.yaml|"
    r"render_skill\.py|resolve_customization\.py|customize\.toml"
)


class PackageError(ValueError):
    """资产、入口或引用不满足静态完整性契约。"""


class UniqueLoader(yaml.SafeLoader):
    """拒绝技能入口中重复或合并后重复的 YAML 键。"""


def unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise PackageError("技能 frontmatter 包含不可哈希的键") from exc
        if duplicate:
            raise PackageError(f"技能 frontmatter 重复键：{key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping,
)


def physical_path(path):
    """检查已有父目录及目标本身，不通过解析软链接改变来源。"""
    path = Path(os.path.abspath(path))
    for component in (*reversed(path.parents), path):
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise PackageError(f"技能资产路径包含符号链接：{component}")
    return path


def read_assets(root):
    assets = {}

    def walk(directory):
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda item: item.name)
        for entry in entries:
            path = directory / entry.name
            info = entry.stat(follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode):
                walk(path)
            elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                assets[path.relative_to(root).as_posix()] = path.read_bytes()
            else:
                raise PackageError(f"技能包包含链接或非普通资产：{path}")

    walk(root)
    if not assets:
        raise PackageError("技能包为空，不能通过完整性校验")
    return assets


def entry_header(text, relative):
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        raise PackageError(f"技能入口缺少 frontmatter：{relative}")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise PackageError(f"技能入口缺少 frontmatter 结束符：{relative}") from exc
    data = yaml.load("\n".join(lines[1:end]), Loader=UniqueLoader)
    if not isinstance(data, dict):
        raise PackageError(f"技能 frontmatter 必须为映射：{relative}")
    for key in ("name", "description"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise PackageError(f"技能入口缺少有效 {key}：{relative}")
    if data["name"] != ENTRY_NAMES[relative]:
        raise PackageError(f"技能入口身份不匹配：{relative}")
    if not any(line.strip() for line in lines[end + 1:]):
        raise PackageError(f"技能入口缺少正文：{relative}")


def local_reference(root, relative, destination, documents, assets):
    """按引用文件解析位置；片段不证明存在，只校验文件及显式行定位。"""
    destination = destination.strip()
    if destination.startswith("<") and destination.endswith(">"):
        destination = destination[1:-1]
    parts = urlsplit(destination)
    if parts.scheme in {"http", "https"}:
        if FORBIDDEN_DEPENDENCIES.search(unquote(destination)):
            raise PackageError(f"技能引用旧上游资产：{relative} -> {destination}")
        return False
    path = unquote(destination.split("#", 1)[0])
    # 先剥离带扩展名文件的行定位，避免把 missing.md:1 误识别为 URI。
    # 真正的 URI 前缀仍保留，后续继续拒绝 file、ssh 等不支持的协议。
    located = re.fullmatch(r"(.+\.[A-Za-z0-9_-]+):(\d+)", path)
    if located:
        path, line = located.groups()
        line = int(line)
    else:
        line = None
    local_parts = urlsplit(path)
    if local_parts.scheme or local_parts.netloc or "?" in destination:
        raise PackageError(f"不支持的技能资产引用：{relative} -> {destination}")
    if not path:
        return False
    if Path(path).is_absolute() or "\\" in path or any(char.isspace() for char in path):
        raise PackageError(f"技能引用路径非法：{relative} -> {destination}")
    target = Path(os.path.abspath(root / Path(relative).parent / path))
    if not target.is_relative_to(root):
        raise PackageError(f"技能引用越出技能包：{relative} -> {destination}")
    key = target.relative_to(root).as_posix()
    if key not in assets:
        raise PackageError(f"技能引用资产缺失：{relative} -> {destination}")
    if line is not None:
        if key not in documents or not 1 <= line <= len(documents[key].splitlines()):
            raise PackageError(f"技能引用行定位无效：{relative} -> {destination}")
    return True


def validate_suite(suite):
    suite = physical_path(suite)
    root = physical_path(suite / "skills")
    if not root.is_dir():
        raise PackageError("缺少技能目录")
    return validate_assets(root, read_assets(root))


def validate_assets(root, assets):
    """校验调用方已采集的字节快照；不读取磁盘、不执行候选包脚本。

    root 仅用于引用位置的词法解析；物理来源和快照复核由采集方负责。
    """
    root = Path(os.path.abspath(root))
    if not isinstance(assets, dict) or not assets:
        raise PackageError("技能包为空，不能通过完整性校验")
    for name, content in assets.items():
        if (not isinstance(name, str) or not name or Path(name).is_absolute()
                or ".." in Path(name).parts or "\\" in name
                or not isinstance(content, bytes)):
            raise PackageError("技能资产快照必须为包内相对路径与字节映射")
    required = set(ENTRY_NAMES) | set(REQUIRED_REFERENCES) | {
        f"bmad/references/procedures/{name}.md" for name in REQUIRED_PROCEDURES
    }
    missing = required - set(assets)
    if missing:
        raise PackageError("缺少必需技能资产：" + ", ".join(sorted(missing)))
    documents = {
        name: content.decode("utf-8")
        for name, content in assets.items() if name.endswith(".md")
    }
    for relative in required:
        if not documents[relative].strip():
            raise PackageError(f"必需技能资产为空：{relative}")
    for relative in ENTRY_NAMES:
        entry_header(documents[relative], relative)
    references = 0
    for relative, content in sorted(documents.items()):
        forbidden = FORBIDDEN_DEPENDENCIES.search(content)
        if forbidden:
            raise PackageError(f"技能文档引用旧上游依赖：{relative}：{forbidden.group()}")
        for destination in LINKS.findall(content):
            references += int(local_reference(root, relative, destination, documents, assets))
    capability = documents["bmad/references/capability-map.md"]
    procedures = set(re.findall(r"procedures/[\w-]+\.md", capability))
    if not procedures:
        raise PackageError("能力映射零命中，不能通过完整性校验")
    for procedure in procedures:
        key = "bmad/references/" + procedure
        if key not in documents or not documents[key].strip():
            raise PackageError(f"能力映射流程缺失或为空：{procedure}")
    if not references:
        raise PackageError("技能包没有可核对的本地引用")
    return {
        "scope": "static_skill_assets",
        "entries": len(ENTRY_NAMES),
        "documents": len(documents),
        "assets": len(assets),
        "local_references": references,
        "mapped_procedures": len(procedures),
        "runtime_verified": False,
        "upstream_sync_verified": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="只读检查两个技能入口及技能包静态完整性")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE,
                        help="已有物理套件目录；默认检查本脚本所属套件")
    arguments = parser.parse_args(argv)
    try:
        report = validate_suite(arguments.suite)
    except (PackageError, OSError, UnicodeError, yaml.YAMLError) as exc:
        print(f"技能完整性校验失败：{exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    print("静态技能完整性通过；未验证宿主加载、技能调用或上游同步。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
