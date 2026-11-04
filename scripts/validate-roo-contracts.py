#!/usr/bin/env python3
"""校验配置与计划的静态契约；不执行计划命令，不证明 Roo 运行时行为。"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import shlex
import sys

import yaml

# 兼容 CLI 与按文件加载的静态测试；公共版本映射只从本脚本同目录加载。
SCRIPT_DIRECTORY = Path(__file__).resolve().parent
if str(SCRIPT_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIRECTORY))
from asset_safety import AssetError, checked_path
from suite_versions import suite_spec


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
TASK_TEMPLATE_PATH = "bmad-suite-v4/skills/bmad/references/templates/task-unit.template.md"
# 旧计划仅在新入口不存在时兼容；空闲新入口不能恢复旧计划。
DEFAULT_PLAN = "_bmad-output/pending_implementation_plan.md"
ACTIVE_TASK = "specs/tasks/_active.md"
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
    "docs/adrs/ADR-20261103-topic.md",
    "docs/analysis/ANALYSIS-20261103-topic.md",
    "specs/tasks/TU-DEMO-001.md",
    "_bmad-output/adrs/ADR-20261008-topic.md",
    "_bmad-output/analysis/report_1.md",
    "_bmad-output/archive/plans/plan-20261008-topic.md",
    "_bmad-output/pending_implementation_plan.md",
)
DENIED_PATHS = (
    "bs.sh", "src/app.py", ".roomodes", "README.md",
    "docs/project-context.md",
    "docs/adrs-extra/test.md",
    "docs/adrs/nested/test.md",
    "docs/adrs/../project-context.md",
    "docs/adrs/%2e%2e/project-context.md",
    "docs/analysis/test.md.bak",
    "docs/analysis/test.md\n",
    "../docs/adrs/test.md",
    "prefix/docs/adrs/test.md",
    "/docs/adrs/test.md",
    "docs\\adrs\\test.md",
    "specs/tasks/_active.md",
    "specs/tasks/archive/TU-DEMO-001.md",
    "specs/tasks/TU-DEMO-001.md\n",
    "specs/tasks/TU-../outside.md",
    "specs/governance/00-governance-index.md",
    "specs/business-domain.md",
    "verification/TU-DEMO-001.verdict.json",
    "AGENTS.md",
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
    supplemental = data.get("supplemental_adrs", [])
    require(isinstance(supplemental, list), "补充 ADR 引用必须为列表")
    require(all(isinstance(item, str) and bool(item.strip()) for item in supplemental),
            "补充 ADR 引用必须为非空路径字符串")
    require(len(set(supplemental)) == len(supplemental), "补充 ADR 引用重复")
    require(not supplemental or data["requires_adr"], "无需 ADR 时不得关联补充 ADR")
    require(data["adr_file"] not in supplemental, "补充 ADR 不得重复主 ADR 引用")
    for relative in supplemental:
        project_file(root, relative)
    command = data["verification_command"]
    require(isinstance(command, str) and bool(command.strip()), "验证命令不能为空")
    tokens = shlex.split(command)
    require(len(tokens) >= 5 and tokens[0] == "timeout", "验证命令缺少分级超时")
    duration_index = 2 if tokens[1] == "--kill-after=2s" else 1
    require(tokens[duration_index] in {"15s", "30s", "600s"},
            "验证命令缺少分级超时")
    executable_index = duration_index + 1
    if duration_index == 1 and tokens[executable_index] == "--kill-after=2s":
        executable_index += 1
    require(executable_index < len(tokens) - 2
            and not tokens[executable_index].startswith(("-", "<")),
            "验证命令缺少执行入口或含未支持的超时选项")
    require(tokens[-2:] == ["<", "/dev/null"], "验证命令须封闭标准输入")
    # 仅做契约形状校验，不执行命令，也不宣称这是 Shell 安全解析器。


def validate_task(data, template=False):
    """仅检查任务或模板静态形状，不认证就绪、授权、CS/SR 或执行命令。"""
    require("plan_id" not in data, "任务与旧计划身份不能混合声明")
    required = {
        "task_id", "parent_objective", "inputs", "cs_specification",
        "kcp_verification", "sod_review", "gate_status", "contract_version",
        "instance_id", "status", "authorization", "session_id",
    }
    require(required <= data.keys(),
            f"缺少任务字段：{sorted(required - data.keys())}")
    require(isinstance(data["task_id"], str)
            and bool(re.fullmatch(r"[A-Za-z0-9_-]+", data["task_id"])),
            "任务标识非法")
    if not template:
        require("REPLACE_WITH" not in data["task_id"], "任务标识未实例化")
    require(isinstance(data["contract_version"], str)
            and bool(data["contract_version"].strip()), "任务契约版本为空")
    for field in ("instance_id", "session_id"):
        require(data[field] is None or (
            isinstance(data[field], str) and bool(data[field].strip())),
            f"任务 {field} 必须为非空字符串或 null")
    require(isinstance(data["status"], str)
            and data["status"] in STATES | {"FAILED", "CANCELLED"}, "任务状态非法")
    require(isinstance(data["inputs"], list), "任务 inputs 必须为列表")
    for field in ("parent_objective", "cs_specification", "kcp_verification",
                  "sod_review", "gate_status", "authorization"):
        require(isinstance(data[field], dict) and bool(data[field]),
                f"任务 {field} 必须为非空映射")
    checks = data["kcp_verification"].get("checks")
    require(isinstance(checks, list) and bool(checks), "任务缺少逐项验证契约")
    identifiers = set()
    for check in checks:
        require(isinstance(check, dict), "任务验证项必须为映射")
        identifier = check.get("check_id")
        require(isinstance(identifier, str) and bool(identifier.strip())
                and identifier not in identifiers, "任务验证项标识为空或重复")
        identifiers.add(identifier)
        require(type(check.get("required")) is bool, "验证项 required 必须为布尔值")
        require(isinstance(check.get("command_status"), str)
                and check["command_status"] in {
                    "UNAVAILABLE", "PLANNED_NOT_YET_CREATED", "AVAILABLE",
                }, "任务验证入口状态非法")
        command = check.get("command")
        require(command is None or (isinstance(command, str) and bool(command.strip())),
                "任务验证命令必须为非空字符串或 null")
        if check["command_status"] == "AVAILABLE":
            require(isinstance(command, str) and bool(command.strip()),
                    "可用任务验证入口缺少命令")
    gate = data["gate_status"]
    require(type(gate.get("accepted")) is bool, "任务 accepted 必须为布尔值")
    require(isinstance(gate.get("cs"), str)
            and gate["cs"] in {"UNKNOWN", "PASS", "FAIL"}, "任务 CS 状态非法")
    require(isinstance(gate.get("sr"), str)
            and gate["sr"] in {"UNKNOWN", "APPROVED", "REJECTED"}, "任务 SR 状态非法")
    # 只拒绝自相矛盾的声明；即使三项一致，也不把它认证为真实接受证据。
    if gate["accepted"]:
        require(gate["cs"] == "PASS" and gate["sr"] == "APPROVED",
                "任务接受声明与 CS/SR 不一致")
    if template:
        require(data["status"] == "DRAFT", "任务模板必须保持 DRAFT")
        require(not gate["accepted"] and gate["cs"] == "UNKNOWN"
                and gate["sr"] == "UNKNOWN", "任务模板不得声明接受或通过")
        require(all(check["command_status"] == "UNAVAILABLE"
                    and check["command"] is None for check in checks),
                "任务模板不得声明可用验证命令")


def active_task(root):
    """读取新薄指针；返回 None 表示明确空闲，不向旧默认入口降级。"""
    path = checked_path(root / ACTIVE_TASK)
    data = frontmatter(project_file(root, ACTIVE_TASK).read_text(encoding="utf-8"))
    fields = {"active_task_id", "instance_id", "task_ref", "contract_version", "authority_ref"}
    require(fields <= data.keys(), "单焦点指针缺少必需字段")
    require(data["authority_ref"] is None or (
        isinstance(data["authority_ref"], str) and bool(data["authority_ref"].strip())),
        "单焦点指针授权来源非法")
    if data["active_task_id"] is None:
        require(all(data[field] is None for field in (
            "instance_id", "task_ref", "contract_version",
        )), "空闲指针包含残留任务绑定")
        print("单焦点任务入口明确空闲：未读取旧默认计划，未恢复归档。")
        return None
    identifier = data["active_task_id"]
    require(isinstance(identifier, str)
            and bool(re.fullmatch(r"[A-Za-z0-9_-]+", identifier)), "单焦点任务标识非法")
    relative = f"specs/tasks/TU-{identifier}.md"
    require(data["task_ref"] == relative, "任务引用与单焦点标识不匹配")
    checked_path(root / relative)
    task = project_file(root, relative)
    content = frontmatter(task.read_text(encoding="utf-8"))
    validate_task(content)
    require(content["task_id"] == identifier
            and content["instance_id"] == data["instance_id"]
            and content["contract_version"] == data["contract_version"],
            "单焦点指针与任务身份或契约版本不一致")
    return task


def suite_paths(version):
    """保留旧 V4 常量接口；显式版本仅选择对应资产，不回退。"""
    spec = suite_spec(version)
    require(version == "v4", "静态 Roo 契约仅支持 v4")
    prefix = spec.source_path
    return (
        f"{prefix}/roo/settings/custom_modes.yaml",
        f"{prefix}/skills/bmad/references/templates/implementation-plan.template.md",
        tuple(f"{prefix}/{suffix}" for suffix in (
            "roo/rules/02-bmad-core.md",
            "roo/rules-ana-architect/01-ana-solo-core.md",
            "roo/rules-bmad-engineer/01-bmad-engineer-core.md",
        )),
        tuple(f"{prefix}/skills/{name}/SKILL.md" for name in ("bmad", "ana-solo")),
    )


def validate_repository(root, explicit_plan=None, suite="v4"):
    mode_path, template_path, rule_paths, skill_paths = suite_paths(suite)
    validate_modes(load_yaml(project_file(root, mode_path).read_text(encoding="utf-8")))
    validate_plan(frontmatter(project_file(root, template_path).read_text(encoding="utf-8")),
                  root, template=True)
    task_template_path = (
        f"{suite_spec(suite).source_path}/skills/bmad/references/templates/task-unit.template.md"
    )
    validate_task(frontmatter(project_file(root, task_template_path).read_text(
        encoding="utf-8")), template=True)
    for path, name in zip(skill_paths, ("bmad-solo", "ana-solo")):
        data = frontmatter(project_file(root, path).read_text(encoding="utf-8"))
        require(data.get("name") == name, f"原生入口标识错误：{path}")
        require(isinstance(data.get("description"), str), f"入口缺少描述：{path}")
    for path in rule_paths:
        require(bool(project_file(root, path).read_text(encoding="utf-8").strip()),
                f"规则文件为空：{path}")
    if explicit_plan is not None:
        plan = project_file(root, explicit_plan)
    elif (root / ACTIVE_TASK).exists() or (root / ACTIVE_TASK).is_symlink():
        plan = active_task(root)
    elif (root / DEFAULT_PLAN).exists() or (root / DEFAULT_PLAN).is_symlink():
        print("新任务入口不存在：仅兼容检查旧默认计划，不迁移或恢复历史任务。")
        plan = project_file(root, DEFAULT_PLAN)
    else:
        plan = None
    if plan is not None:
        data = frontmatter(plan.read_text(encoding="utf-8"))
        require(not ("task_id" in data and "plan_id" in data),
                "任务与旧计划身份不能混合声明")
        if "task_id" in data:
            validate_task(data)
            print("Task Unit 静态形状检查完成；未认证授权、CS/SR、控制器或运行时验收。")
        else:
            validate_plan(data, root)
            if data["verification_command_status"] == "PLANNED_NOT_YET_CREATED":
                print("注意：计划验证资产仍标记待创建；本次静态检查不代表阶段验收完成。")
    else:
        print("没有选中的活动任务：正常生命周期状态；未选择或执行归档。")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--plan", help="显式计划或 Task Unit 路径；缺失时失败，不降级替换")
    parser.add_argument("--suite", choices=("v4",), default="v4",
                        help="唯一 V4 静态契约；缺源不回退")
    args = parser.parse_args(argv)
    try:
        validate_repository(args.root, args.plan, args.suite)
    except (AssetError, ContractError, OSError, UnicodeError, yaml.YAMLError, re.error, ValueError) as exc:
        print(f"FAIL：{exc}", file=sys.stderr)
        return 1
    print(f"PASS：{args.suite} 配置和元数据静态契约有效；未验证 Roo 运行时权限或模型行为。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
