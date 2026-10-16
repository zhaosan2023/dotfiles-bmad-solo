"""计划内类型化任务清单的只读投影；不建立第二份进度或勾选任务。

清单以唯一 bmad-tasks JSON 围栏保存在获准计划中。只有精确匹配
当前任务验证契约且证据仍有效的完成项可用于依赖就绪判断。
未采用该契约的计划不静默迁移；平台记录仍是其临时进度入口。
本模块不提供账号隔离、宿主权限保证或完整 frontmatter 校验。
"""
from __future__ import annotations

import json
from pathlib import Path
import re

import bmad_execution as execution
from bmad_supervisor import SupervisorError, contained_path, workspace_path


MAX_PLAN_BYTES = 1024 * 1024
MAX_TASKS = 256
MAX_VIEW_LINES = 80
MAX_VIEW_BYTES = 16384
TASK_BLOCK = re.compile(r"^```bmad-tasks\n(.*?)^```[ \t]*$", re.M | re.S)
IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
TASK_FIELDS = {"task_id", "title", "depends_on", "status", "verification", "verdict_file"}
VERIFY_FIELDS = {"operation", "environment_file", "directory", "pattern",
                 "minimum_tests", "required_tests", "inputs"}
SOURCE_STATES = {"PENDING", "BLOCKED", "SUSPENDED", "COMPLETED"}


def text(value, label, maximum=2048):
    if (not isinstance(value, str) or not value.strip()
            or len(value.encode("utf-8")) > maximum
            or any(ord(char) < 32 or ord(char) == 127 for char in value)):
        raise SupervisorError(f"{label}必须是预算内的非空单行文本")
    return value


def identifier(value, label):
    if not isinstance(value, str) or IDENTIFIER.fullmatch(value) is None:
        raise SupervisorError(f"{label}非法")
    return value


def relative_file(value, label):
    text(value, label)
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or value in {".", ""}:
        raise SupervisorError(f"{label}必须是工作区内明确相对路径")
    return value


def string_list(values, label, maximum=256):
    if (not isinstance(values, list) or len(values) > maximum
            or any(not isinstance(item, str) for item in values)
            or len(set(values)) != len(values)):
        raise SupervisorError(f"{label}必须是有界、无重复的文本列表")
    for value in values:
        text(value, label)
    return values


def validate_verification(value):
    if not isinstance(value, dict) or set(value) != VERIFY_FIELDS:
        raise SupervisorError("任务验证契约字段缺失或包含未覆盖操作")
    if value["operation"] != "unit-test":
        raise SupervisorError("状态投影当前仅覆盖类型化 Python 单测，不回退其他操作")
    relative_file(value["environment_file"], "环境记录")
    relative_file(value["directory"], "测试目录")
    pattern = text(value["pattern"], "测试模式", 256)
    if not pattern.endswith(".py") or "/" in pattern or "\\" in pattern:
        raise SupervisorError("测试模式必须是单层 Python 文件匹配")
    if type(value["minimum_tests"]) is not int or value["minimum_tests"] < 1:
        raise SupervisorError("测试下限必须大于零")
    string_list(value["required_tests"], "必需测试")
    string_list(value["inputs"], "显式实现输入", execution.MAX_EVIDENCE_FILES)
    for item in value["inputs"]:
        relative_file(item, "显式实现输入")


def validate_contract(data):
    if (not isinstance(data, dict)
            or set(data) != {"schema_version", "plan_id", "tasks"}
            or type(data["schema_version"]) is not int
            or data["schema_version"] != 1):
        raise SupervisorError("类型化任务清单 schema 无效；不自动迁移旧计划")
    identifier(data["plan_id"], "计划标识")
    tasks = data["tasks"]
    if not isinstance(tasks, list) or not tasks or len(tasks) > MAX_TASKS:
        raise SupervisorError("任务清单必须非空且不超过任务数量预算")
    by_id = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != TASK_FIELDS:
            raise SupervisorError("任务字段缺失或存在未支持字段")
        key = identifier(task["task_id"], "任务标识")
        if key in by_id:
            raise SupervisorError("任务标识重复")
        text(task["title"], "任务标题")
        string_list(task["depends_on"], "任务依赖")
        for dependency in task["depends_on"]:
            identifier(dependency, "依赖标识")
        if not isinstance(task["status"], str) or task["status"] not in SOURCE_STATES:
            raise SupervisorError("任务源状态无效")
        validate_verification(task["verification"])
        if task["verdict_file"] is not None:
            relative_file(task["verdict_file"], "验收回执")
        if task["status"] == "COMPLETED" and task["verdict_file"] is None:
            raise SupervisorError("模型勾选不能产生完成事实；完成项缺少真实回执")
        by_id[key] = task
    for key, task in by_id.items():
        if key in task["depends_on"] or any(dep not in by_id for dep in task["depends_on"]):
            raise SupervisorError("任务自依赖或依赖目标不存在")
    visiting, visited = set(), set()

    def visit(key):
        if key in visiting:
            raise SupervisorError("任务依赖存在循环")
        if key in visited:
            return
        visiting.add(key)
        for dependency in by_id[key]["depends_on"]:
            visit(dependency)
        visiting.remove(key)
        visited.add(key)

    for key in by_id:
        visit(key)
    return by_id


def load_plan(workspace: Path, relative: str):
    root = workspace_path(workspace)
    path = contained_path(root, relative)
    if not path.is_file() or path.stat().st_size > MAX_PLAN_BYTES:
        raise SupervisorError("计划缺失、不是普通文件或超出读取预算")
    identity = execution.environment.fingerprint(path)
    with path.open("rb") as stream:
        payload = stream.read(MAX_PLAN_BYTES + 1)
    if len(payload) > MAX_PLAN_BYTES:
        raise SupervisorError("计划在读取期间超出预算")
    content = payload.decode("utf-8")
    # 仅提取计划身份的明确 YAML 子集；完整授权和元数据由阶段接管校验。
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise SupervisorError("计划缺少 frontmatter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise SupervisorError("计划 frontmatter 不完整") from exc
    identities = [line for line in lines[1:end] if re.match(r"^plan_id\s*:", line)]
    if len(identities) != 1:
        raise SupervisorError("计划标识缺失或重复")
    raw = identities[0].split(":", 1)[1].strip()
    if raw.startswith('"'):
        plan_id = json.loads(raw)
    elif raw.startswith("'") and raw.endswith("'"):
        plan_id = raw[1:-1]
    else:
        plan_id = raw
    identifier(plan_id, "frontmatter 计划标识")
    blocks = list(TASK_BLOCK.finditer(content))
    if len(blocks) != 1 or content.count("```bmad-tasks") != 1:
        raise SupervisorError("须先明确采用唯一类型化任务清单；未迁移计划仍使用平台记录")
    data = json.loads(blocks[0].group(1), object_pairs_hook=execution.unique_object)
    validate_contract(data)
    if data["plan_id"] != plan_id:
        raise SupervisorError("任务清单与绑定计划标识不一致")
    if execution.environment.fingerprint(path) != identity:
        raise SupervisorError("计划在读取期间变化；停止对账")
    return data, path, identity


def completed_evidence(root, task):
    checked = execution.check_evidence(workspace=root, verdict_file=task["verdict_file"])
    if checked["status"] != "PASS":
        raise SupervisorError(checked["reason"])
    verdict, _ = execution.read_receipt(root, task["verdict_file"])
    verification = task["verification"]
    result = verdict["result"]
    expected_result = {key: verification[key] for key in
                       ("directory", "pattern", "minimum_tests", "required_tests")}
    if any(result.get(key) != value for key, value in expected_result.items()):
        raise SupervisorError("回执不匹配当前任务的必需验证选择")
    if (verdict["evidence_before"]["inputs"] != verification["inputs"]
            or verdict["environment_manifest"]["relative_path"] != verification["environment_file"]):
        raise SupervisorError("回执不匹配当前任务的实现覆盖或环境契约")
    return checked


def render_state(*, workspace: Path, plan_file: str,
                 maximum_lines=MAX_VIEW_LINES, maximum_bytes=MAX_VIEW_BYTES):
    """返回完整有界视图；超预算阻塞，不截掉未完成事项或写入进度。

    完成项查询会复核现有环境身份，不执行业务测试。当前清单仅
    精确绑定验证选择，尚无计划/任务专属签名或账号防篡改保证。
    """
    try:
        if (type(maximum_lines) is not int or not 1 <= maximum_lines <= MAX_VIEW_LINES
                or type(maximum_bytes) is not int or not 256 <= maximum_bytes <= MAX_VIEW_BYTES):
            raise SupervisorError("状态视图预算无效或超过硬上限")
        root = workspace_path(workspace)
        data, path, identity = load_plan(root, plan_file)
        by_id = validate_contract(data)
        effective, reasons = {}, {}
        for key, task in by_id.items():
            effective[key] = task["status"]
            if task["status"] == "COMPLETED":
                try:
                    completed_evidence(root, task)
                except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
                    effective[key] = "BLOCKED"
                    reasons[key] = str(exc)
        # 原完成项的依赖亦须有效；无效证据沿依赖传播，不推进下游。
        changed = True
        while changed:
            changed = False
            for key, task in by_id.items():
                if effective[key] == "COMPLETED" and any(
                    effective[dep] != "COMPLETED" for dep in task["depends_on"]
                ):
                    effective[key] = "BLOCKED"
                    reasons[key] = "完成项依赖尚未通过当前证据核验"
                    changed = True
        ready = [key for key, task in by_id.items()
                 if effective[key] == "PENDING" and all(
                     effective[dep] == "COMPLETED" for dep in task["depends_on"])]
        lines = [f"计划：{data['plan_id']}", f"来源：{plan_file}",
                 "边界：只读候选投影；不自动迁移平台进度，不保证账号防篡改"]
        for key, task in by_id.items():
            state = "READY" if key in ready else effective[key]
            dependencies = ",".join(task["depends_on"]) or "无"
            line = f"{key} [{state}] {task['title']} | 依赖：{dependencies}"
            if task["verdict_file"] is not None:
                line += f" | 回执：{task['verdict_file']}"
            if key in reasons:
                # 不把环境错误等任意正文注入默认状态视图。
                line += " | 原通过证据无效，按回执定位核对"
            lines.append(line)
        view = "\n".join(lines) + "\n"
        if len(lines) > maximum_lines or len(view.encode("utf-8")) > maximum_bytes:
            raise SupervisorError("全部任务无法在状态预算内完整表示；未输出截断视图，未丢弃未完成事项")
        if execution.environment.fingerprint(path) != identity:
            raise SupervisorError("状态查询期间绑定计划变化；停止对账")
        status = "BLOCKED" if "BLOCKED" in effective.values() else (
            "COMPLETED" if all(value == "COMPLETED" for value in effective.values()) else
            "SUSPENDED" if not ready and "SUSPENDED" in effective.values() else "READY")
        return {"operation": "render-state", "status": status,
                "reason": (
                    "存在阻塞任务或完成项证据失效；不推进依赖，按任务回执定位核对"
                    if status == "BLOCKED" else ""
                ),
                "plan_id": data["plan_id"], "plan_file": plan_file,
                "view": view, "view_lines": len(lines),
                "view_bytes": len(view.encode("utf-8")), "tasks_total": len(by_id),
                "unfinished_count": sum(value != "COMPLETED" for value in effective.values()),
                "ready_tasks": ready, "business_reexecuted": False, "state_saved": False,
                "evidence_boundary": "仅当前类型化单测契约的候选投影；不证明全计划、宿主或远程完成"}
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        return {"operation": "render-state", "status": "BLOCKED",
                "reason": str(exc), "plan_file": plan_file,
                "business_reexecuted": False, "state_saved": False,
                "evidence_boundary": "缺必要契约、证据或预算；不迁移、不勾选、不保存第二份进度"}
