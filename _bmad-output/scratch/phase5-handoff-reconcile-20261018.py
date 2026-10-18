"""本轮受限依赖验证和启动接管；不启动模型、不提交、不读取凭据。

使用既有类型化单测和计划适配原语。未覆盖的行政恢复临时引用操作回执，
不创建第二份任务进度；只恢复获准 HEADLESS 任务，不制造完成状态。
每次调用只执行一个验证组，终端调用方须串行、限时并封闭标准输入。
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_execution as execution
import bmad_loop as loop
import bmad_plan_adapter as adapter
import bmad_state as state
from bmad_supervisor import SupervisorError, contained_path, save_receipt

PLAN = "_bmad-output/pending_implementation_plan.md"
PLAN_ID = "BMAD-ANTI-BUREAUCRACY-20261012-01"
ADR = "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
OUT = "_bmad-output/verification/phase5-20261018"
GROUPS = {
    "P3-PLAN": ("P3-PLAN",),
    "P3-BACKEND": ("P3-BACKEND", "P3-OFFLINE", "P4-BUDGET"),
    "P4-BATCH": ("P4-BATCH",),
    "P4-ISOLATION": ("P4-ISOLATION",),
    "P5-PI-DRIVER": ("P5-PI-DRIVER",),
}
COMPLETED = tuple(key for members in GROUPS.values() for key in members)
HEADLESS = "P5-PI-HEADLESS"
SUPPORT = {
    "private-config": ("test_private_config.py", 18),
    "pi-budget": ("test_pi_budget.py", 10),
    "pi-transport": ("test_pi_transport.py", 12),
    "pi-activation": ("test_pi_activation.py", 10),
    "controller-assets": ("test_controller_asset_scope.py", 1),
    "supervisor": ("test_supervisor_guards.py", 1),
}
SUPPORT_INPUTS = ["bmralph-suite-v5/scripts/" + name for name in (
    "bmad-loop.py", "bmad_loop.py", "bmad_agent_backend.py",
    "bmad_supervisor.py", "bmad_private_config.py", "bmad_pi_budget.py",
    "bmad_pi_transport.py", "bmad_execution.py", "bmad_environment.py",
    "bmad_plan_adapter.py", "bmad_context_inputs.py", "bmad_context.py",
)]


def require(condition, message):
    if not condition:
        raise SupervisorError(message)


def load():
    require(Path.cwd().resolve() == ROOT, "工作目录不是授权工作区")
    data, _, identity = state.load_plan(ROOT, PLAN)
    tasks = state.validate_contract(data)
    require(data["plan_id"] == PLAN_ID, "计划标识变化")
    require(set(tasks) == set(COMPLETED + (HEADLESS,)), "任务集合变化；停止接管")
    content = contained_path(ROOT, PLAN).read_text()
    require('adr_file: "' + ADR + '"' in content.split("---", 2)[1], "关联 ADR 变化")
    require("- Status: PROPOSED" in contained_path(ROOT, ADR).read_text().splitlines(),
            "关联 ADR 不再为 PROPOSED")
    require("### 2026-10-18 独立循环接管授权" in content, "缺少本轮明确授权契约")
    require(all(tasks[key]["status"] == "COMPLETED" for key in COMPLETED),
            "原完成任务源状态变化")
    require(tasks[HEADLESS]["status"] == "SUSPENDED"
            and tasks[HEADLESS]["verdict_file"] is None,
            "目标不是获准暂停且无回执的任务；不重复恢复")
    current = loop.status(ROOT)
    require(current.get("writer_active") is False, "存在活动写入者；停止接管")
    require(current.get("cleanup_ok") is True and bool(current.get("finished_at")),
            "前序运行缺少真实终结清理证据")
    terminal = loop.read_record(ROOT, current["final_receipt"])
    require(all(terminal.get(key) == current.get(key) for key in
                ("run_id", "status", "cleanup_ok", "finished_at", "final_receipt")),
            "历史最终回执与当前查询不一致")
    return data, tasks, identity


def selection(tasks, group):
    if group in GROUPS:
        first = tasks[group]["verification"]
        require(all(tasks[key]["verification"] == first for key in GROUPS[group]),
                "共享组验证对象不完全一致；不得复用回执")
        return copy.deepcopy(first)
    pattern, minimum = SUPPORT[group]
    path = contained_path(ROOT, "bmralph-suite-v5/tests/" + pattern)
    tree = ast.parse(path.read_bytes())
    identifiers = [Path(pattern).stem + "." + node.name + "." + method.name
                   for node in tree.body if isinstance(node, ast.ClassDef)
                   for method in node.body if isinstance(method, ast.FunctionDef)
                   and method.name.startswith("test_")]
    require(len(identifiers) >= minimum, "必需测试数量不足")
    return {
        "operation": "unit-test", "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests", "pattern": pattern,
        "minimum_tests": len(identifiers), "required_tests": identifiers,
        "inputs": SUPPORT_INPUTS,
    }


def matches(record, verification):
    result = record.get("result")
    before = record.get("evidence_before")
    manifest = record.get("environment_manifest")
    return (record.get("status") == "PASS" and isinstance(result, dict)
            and isinstance(before, dict) and isinstance(manifest, dict)
            and all(result.get(key) == verification[key] for key in
                    ("directory", "pattern", "minimum_tests", "required_tests"))
            and before.get("inputs") == verification["inputs"]
            and manifest.get("relative_path") == verification["environment_file"])


def candidate(verification):
    directory = contained_path(ROOT, OUT)
    if not directory.exists():
        return None
    paths = sorted(directory.glob("run-*.verdict.json"),
                   key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        record, _ = execution.read_receipt(ROOT, relative)
        if matches(record, verification):
            checked = execution.check_evidence(workspace=ROOT, verdict_file=relative)
            if checked["status"] == "PASS":
                return relative
    return None


def verify(group):
    _, tasks, identity = load()
    verification = selection(tasks, group)
    previous = candidate(verification)
    if previous is not None:
        print(json.dumps({"status": "PASS", "group": group, "verdict_file": previous,
                          "business_reexecuted": False}, ensure_ascii=False), flush=True)
        return
    verdict = execution.unit_test(
        workspace=ROOT, environment_file=verification["environment_file"],
        directory=verification["directory"], pattern=verification["pattern"],
        minimum_tests=verification["minimum_tests"],
        required_tests=tuple(verification["required_tests"]),
        inputs=tuple(verification["inputs"]), runtime_directory=OUT,
    )
    process, _ = execution.read_receipt(ROOT, verdict["process_receipt"])
    print(json.dumps({"status": verdict["status"], "group": group,
                      "verdict_file": verdict["verdict_path"],
                      "returncode": process["returncode"], "cleanup_ok": process["cleanup_ok"],
                      "timed_out": process["timed_out"], "reason": verdict["reason"],
                      "log_summary": process["summary"],
                      "tests_run": verdict["result"]["tests_run"] if verdict["result"] else None},
                     ensure_ascii=False), flush=True)
    require(verdict["status"] == "PASS", "验证未通过；保留回执，不推进")
    require(load()[2] == identity, "验证期间计划变化；停止接管")


def adopt():
    data, tasks, identity = load()
    files = {}
    for group, members in GROUPS.items():
        relative = candidate(selection(tasks, group))
        require(relative is not None, "缺少当前精确通过证据：" + group)
        for key in members:
            files[key] = relative
            proposed = copy.deepcopy(tasks[key])
            proposed["verdict_file"] = relative
            state.completed_evidence(ROOT, proposed)
    for group in SUPPORT:
        require(candidate(selection(tasks, group)) is not None,
                "缺少本轮必要实现验证：" + group)
    require(load()[2] == identity, "证据核验期间计划变化；停止接管")
    with loop.writer_lease(ROOT):
        fresh, _, source_identity = state.load_plan(ROOT, PLAN)
        require(fresh == data and source_identity == identity, "保存前计划变化")
        refreshed = adapter.refresh_completed(
            workspace=ROOT, plan_file=PLAN, verdict_files=files, expected_identity=identity)
        updated, _, refreshed_identity = state.load_plan(ROOT, PLAN)
        require(refreshed["plan_identity"] == refreshed_identity, "刷新保存结果不一致")
        expected = copy.deepcopy(data)
        for task in expected["tasks"]:
            if task["task_id"] in files:
                task["verdict_file"] = files[task["task_id"]]
        require(updated == expected, "刷新出现范围外修改；停止接管")
        next(task for task in expected["tasks"] if task["task_id"] == HEADLESS)["status"] = "PENDING"
        adapter._save_plan(ROOT, PLAN, refreshed_identity, expected,
                           tuple(task for task in expected["tasks"] if task["status"] == "COMPLETED"))
        saved, _, _ = state.load_plan(ROOT, PLAN)
        require(saved == expected, "暂停恢复保存不一致；不覆盖外部修改")
        projection = adapter.query(workspace=ROOT, plan_file=PLAN)
        require(projection["status"] == "READY" and projection["ready_tasks"] == [HEADLESS],
                "恢复后依赖未就绪；禁止启动")
    relative = OUT + "/handoff-adopt-" + uuid.uuid4().hex + ".json"
    receipt = {
        "operation": "authorized-refresh-and-resume", "status": "PASS", "plan_id": PLAN_ID,
        "plan_file": PLAN, "refreshed_verdicts": files, "resumed_task": HEADLESS,
        "source_status": "SUSPENDED", "saved_status": "PENDING", "verdict_file": None,
        "runtime_started": False, "adr_accepted": False, "plan_archived": False,
        "evidence_boundary": "行政恢复尚无产品入口；复用内部保存原语，引用平台及本操作回执",
    }
    save_receipt(contained_path(ROOT, relative), receipt)
    print(json.dumps({"status": "PASS", "operation_receipt": relative,
                      "ready_tasks": projection["ready_tasks"], "runtime_started": False},
                     ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("operation", choices=("verify", "adopt"))
    parser.add_argument("--group", choices=tuple(GROUPS) + tuple(SUPPORT))
    args = parser.parse_args()
    try:
        if args.operation == "verify":
            require(args.group is not None, "必须明确一个验证组")
            verify(args.group)
        else:
            require(args.group is None, "行政恢复不接受验证组")
            adopt()
        return 0
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:512],
                          "runtime_started": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
