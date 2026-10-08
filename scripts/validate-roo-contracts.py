#!/usr/bin/env python3
"""校验配置与计划的静态契约；不执行计划命令，不证明 Roo 运行时行为。"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shlex
import sys

import yaml


class ContractError(ValueError):
    """输入不满足静态契约。"""


class UniqueLoader(yaml.SafeLoader):
    """拒绝重复键，包括合并键展开后的重复。"""


def unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise ContractError("YAML 键必须可哈希") from exc
        if duplicate:
            raise ContractError(f"YAML 重复键：{key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping
)

ROOT = Path(__file__).resolve().parents[1]
MODE_PATH = "bmad-suite-v4/roo/settings/custom_modes.yaml"
TEMPLATE_PATH = "bmad-suite-v4/skills/bmad/references/templates/implementation-plan.template.md"
DEFAULT_PLAN = "_bmad-output/pending_implementation_plan.md"
RULE_PATHS = (
    "bmad-suite-v4/roo/rules/02-bmad-core.md",
    "bmad-suite-v4/roo/rules-ana-architect/01-ana-solo-core.md",
    "bmad-suite-v4/roo/rules-bmad-engineer/01-bmad-engineer-core.md",
)
SKILL_PATHS = (
    "bmad-suite-v4/skills/bmad/SKILL.md",
    "bmad-suite-v4/skills/ana-solo/SKILL.md",
)
FIELDS = {
    "plan_id", "status", "scenario", "impact_tier", "requires_adr",
    "adr_file", "verification_type", "verification_command",
    "verification_command_status", "authorization", "session_id",
}
STATES = {
    "DRAFT", "READY_FOR_IMPLEMENTATION", "INTAKE", "READ_ONLY", "IDLE",
    "NEEDS_SELECTION", "READY", "EXECUTING", "VERIFYING", "COMPLETED",
    "ARCHIVED", "BLOCKED", "SUSPENDED",
}
ALLOWED_PATHS = (
    "_bmad-output/adrs/ADR-20261008-topic.md",
    "_bmad-output/analysis/report_1.md",
    "_bmad-output/archive/plans/plan-20261008-topic.md",
    "_bmad-output/pending_implementation_plan.md",
)
DENIED_PATHS = (
    "bs.sh", "src/app.py", ".roomodes", "README.md",
    "_bmad-output/project-context.md",
    "_bmad-output/adrs-extra/test.md",
    "_bmad-output/adrs/nested/test.md",
    "_bmad-output/adrs/../project-context.md",
    "_bmad-output/adrs/../../src/app.md",
    "_bmad-output/adrs/%2e%2e/project-context.md",
    "_bmad-output/adrs/test.md.bak",
    "_bmad-output/adrs/test.md\n",
    "../_bmad-output/adrs/test.md",
    "prefix/_bmad-output/adrs/test.md",
    "/_bmad-output/adrs/test.md",
    "_bmad-output\\adrs\\test.md",
)


def require(condition, message):
    if not condition:
        raise ContractError(message)


def load_yaml(text):
    value = yaml.load(text, Loader=UniqueLoader)
    require(isinstance(value, dict), "YAML 顶层必须为映射")
    return value


def frontmatter(text):
    lines = text.splitlines()
    require(bool(lines) and lines[0] == "---", "缺少 frontmatter 起始分隔符")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ContractError("缺少 frontmatter 结束分隔符") from exc
    return load_yaml("\n".join(lines[1:end]))


def project_file(root, relative):
    require(isinstance(relative, str) and bool(relative), "引用路径必须是非空字符串")
    path = Path(relative)
    require(not path.is_absolute() and ".." not in path.parts,
            f"引用必须位于项目内：{relative}")
    resolved = (root / path).resolve(strict=True)
    require(resolved.is_relative_to(root.resolve()), f"引用越过项目边界：{relative}")
    require(resolved.is_file(), f"引用不是普通文件：{relative}")
    return resolved


def validate_modes(data):
    modes = data.get("customModes")
    require(isinstance(modes, list) and bool(modes), "customModes 必须为非空列表")
    by_slug = {}
    for mode in modes:
        require(isinstance(mode, dict), "模式必须为映射")
        slug = mode.get("slug")
        require(isinstance(slug, str) and bool(re.fullmatch(r"[a-z0-9-]+", slug)),
                "模式标识非法")
        require(slug not in by_slug, f"重复模式标识：{slug}")
        for key in ("name", "roleDefinition", "customInstructions"):
            require(isinstance(mode.get(key), str) and bool(mode[key].strip()),
                    f"{slug} 缺少 {key}")
        groups = mode.get("groups")
        require(isinstance(groups, list), f"{slug} groups 必须为列表")
        names = []
        for group in groups:
            if isinstance(group, str):
                name = group
            else:
                require(isinstance(group, list) and len(group) == 2,
                        f"{slug} 权限组元组非法")
                name, options = group
                require(name == "edit" and isinstance(options, dict),
                        f"{slug} 不支持的权限组选项")
                require(isinstance(options.get("fileRegex"), str), "缺少编辑路径正则")
            require(name in {"read", "edit", "browser", "command", "mcp"},
                    f"未知权限组：{name}")
            require(name not in names, f"重复权限组：{name}")
            names.append(name)
        by_slug[slug] = mode
    require(set(by_slug) == {"ana-architect", "bmad-engineer"}, "源模式标识集合不符合契约")
    analyst = by_slug["ana-architect"]["groups"]
    require(len(analyst) == 3 and "read" in analyst and "browser" in analyst,
            "分析模式只允许读取、受限编辑和浏览")
    edits = [item for item in analyst if isinstance(item, list) and item[0] == "edit"]
    require(len(edits) == 1, "分析模式必须配置唯一受限编辑组")
    pattern = re.compile(edits[0][1]["fileRegex"])
    for path in ALLOWED_PATHS:
        require(pattern.search(path) is not None, f"正则拒绝正常产物路径：{path!r}")
    for path in DENIED_PATHS:
        require(pattern.search(path) is None, f"正则允许禁止路径：{path!r}")
    require(by_slug["bmad-engineer"]["groups"] == ["read", "edit", "command"],
            "工程权限必须为读取、编辑和终端")


def validate_plan(data, root, template=False):
    require(FIELDS <= data.keys(), f"缺少计划字段：{sorted(FIELDS - data.keys())}")
    require(isinstance(data["plan_id"], str) and bool(data["plan_id"].strip()), "计划标识为空")
    choices = {
        "status": STATES,
        "scenario": {"algo", "structural", "bugfix", "ops"},
        "impact_tier": {"S", "M", "L"},
        "verification_type": {"unit_test", "config_syntax", "diff_cleanliness"},
        "verification_command_status": {"PLANNED_NOT_YET_CREATED", "AVAILABLE"},
    }
    for key, values in choices.items():
        require(isinstance(data[key], str) and data[key] in values, f"非法字段：{key}")
    require(type(data["requires_adr"]) is bool, "requires_adr 必须为布尔值")
    require(isinstance(data["authorization"], str) and bool(data["authorization"].strip()),
            "授权说明不能为空")
    require(data["session_id"] is None or (
        isinstance(data["session_id"], str) and bool(data["session_id"].strip())),
        "会话标识必须为非空字符串或 null")
    if template:
        require(data["status"] == "DRAFT", "模板必须保持 DRAFT")
        return
    require(bool(re.fullmatch(r"[A-Za-z0-9_-]+", data["plan_id"]))
            and "REPLACE_WITH" not in data["plan_id"], "计划标识非法或未实例化")
    if data["requires_adr"]:
        project_file(root, data["adr_file"])
    else:
        require(data["adr_file"] is None, "无需 ADR 时引用必须为 null")
    command = data["verification_command"]
    require(isinstance(command, str) and bool(command.strip()), "验证命令不能为空")
    tokens = shlex.split(command)
    require(len(tokens) >= 5 and tokens[0] == "timeout"
            and tokens[1] in {"15s", "30s", "600s"}, "验证命令缺少分级超时")
    require(tokens[-2:] == ["<", "/dev/null"], "验证命令须封闭标准输入")
    # 仅做契约形状校验，不执行命令，也不宣称这是 Shell 安全解析器。


def validate_repository(root, explicit_plan=None):
    validate_modes(load_yaml(project_file(root, MODE_PATH).read_text(encoding="utf-8")))
    validate_plan(frontmatter(project_file(root, TEMPLATE_PATH).read_text(encoding="utf-8")),
                  root, template=True)
    for path, name in zip(SKILL_PATHS, ("bmad-solo", "ana-solo")):
        data = frontmatter(project_file(root, path).read_text(encoding="utf-8"))
        require(data.get("name") == name, f"原生入口标识错误：{path}")
        require(isinstance(data.get("description"), str), f"入口缺少描述：{path}")
    for path in RULE_PATHS:
        require(bool(project_file(root, path).read_text(encoding="utf-8").strip()),
                f"规则文件为空：{path}")
    if explicit_plan is not None:
        plan = project_file(root, explicit_plan)
    elif (root / DEFAULT_PLAN).exists() or (root / DEFAULT_PLAN).is_symlink():
        plan = project_file(root, DEFAULT_PLAN)
    else:
        plan = None
    if plan is not None:
        data = frontmatter(plan.read_text(encoding="utf-8"))
        validate_plan(data, root)
        if data["verification_command_status"] == "PLANNED_NOT_YET_CREATED":
            print("注意：计划验证资产仍标记待创建；本次静态检查不代表阶段验收完成。")
    else:
        print("默认活动计划不存在：正常生命周期状态；未选择或执行归档。")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--plan", help="显式计划路径；缺失时失败，不降级替换")
    args = parser.parse_args(argv)
    try:
        validate_repository(args.root, args.plan)
    except (ContractError, OSError, UnicodeError, yaml.YAMLError, re.error, ValueError) as exc:
        print(f"FAIL：{exc}", file=sys.stderr)
        return 1
    print("PASS：配置和元数据静态契约有效；未验证 Roo 运行时权限或模型行为。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
