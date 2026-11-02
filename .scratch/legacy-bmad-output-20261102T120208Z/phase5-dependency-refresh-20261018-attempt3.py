"""按原验证契约定向刷新依赖；每次仅运行一个组，不启动模型。

保存完成项的新证据引用，不完成或恢复 HEADLESS，不修改验收。
未覆盖的阶段协调临时引用平台回执；计划清单仍是唯一任务进度。
"""
import argparse
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
OUT = "_bmad-output/verification/phase5-handoff-20261018-attempt3"
HEADLESS = "P5-PI-HEADLESS"
GROUPS = {
    "P3-PLAN": ("P3-PLAN",),
    "P3-BACKEND": ("P3-BACKEND", "P3-OFFLINE", "P4-BUDGET"),
    "P4-BATCH": ("P4-BATCH",),
    "P4-ISOLATION": ("P4-ISOLATION",),
    "P5-PI-DRIVER": ("P5-PI-DRIVER",),
}
COMPLETED = {key for members in GROUPS.values() for key in members}
ALLOWED_CHANGES = {
    "bmralph-suite-v5/tests/test_pi_activation.py",
    "bmralph-suite-v5/tests/test_pi_transport_diagnostics.py",
}


def require(condition):
    if not condition:
        raise SupervisorError("绑定、证据或授权边界不匹配")


def load():
    require(Path.cwd().resolve() == ROOT)
    data, _, identity = state.load_plan(ROOT, PLAN)
    tasks = state.validate_contract(data)
    require(data["plan_id"] == PLAN_ID and set(tasks) == COMPLETED | {HEADLESS})
    require(all(tasks[key]["status"] == "COMPLETED" for key in COMPLETED))
    require(tasks[HEADLESS]["status"] == "PENDING"
            and tasks[HEADLESS]["verdict_file"] is None)
    content = contained_path(ROOT, PLAN).read_text()
    require('adr_file: "' + ADR + '"' in content.split("---", 2)[1])
    require("当前助手不提前实现完成" in content)
    require("- Status: PROPOSED" in contained_path(ROOT, ADR).read_text().splitlines())
    current = loop.status(ROOT)
    require(current.get("writer_active") is False
            and current.get("cleanup_ok") is True and bool(current.get("finished_at")))
    final = loop.read_record(ROOT, current["final_receipt"])
    require(all(final.get(key) == current.get(key) for key in
                ("run_id", "status", "cleanup_ok", "finished_at", "final_receipt")))
    return data, tasks, identity


def selection(tasks, group):
    chosen = tasks[group]["verification"]
    require(all(tasks[key]["verification"] == chosen for key in GROUPS[group]))
    return copy.deepcopy(chosen)


def matches(record, chosen):
    result = record.get("result")
    before = record.get("evidence_before")
    manifest = record.get("environment_manifest")
    return (record.get("status") == "PASS" and isinstance(result, dict)
            and isinstance(before, dict) and isinstance(manifest, dict)
            and all(result.get(key) == chosen[key] for key in
                    ("directory", "pattern", "minimum_tests", "required_tests"))
            and before.get("inputs") == chosen["inputs"]
            and manifest.get("relative_path") == chosen["environment_file"])


def reusable(chosen):
    directory = contained_path(ROOT, OUT)
    if not directory.exists():
        return None
    for path in sorted(directory.glob("run-*.verdict.json"),
                       key=lambda item: item.stat().st_mtime_ns, reverse=True):
        relative = path.relative_to(ROOT).as_posix()
        record, _ = execution.read_receipt(ROOT, relative)
        if (matches(record, chosen)
                and execution.check_evidence(workspace=ROOT, verdict_file=relative)["status"] == "PASS"):
            return relative
    return None


def verify(group):
    _, tasks, identity = load()
    chosen = selection(tasks, group)
    old, _ = execution.read_receipt(ROOT, tasks[group]["verdict_file"])
    require(matches(old, chosen) and old["evidence_before"] == old["evidence_after"])
    previous = reusable(chosen)
    if previous is not None:
        print(json.dumps({"status": "PASS", "group": group,
                          "verdict_file": previous, "tests_reexecuted": False},
                         ensure_ascii=False), flush=True)
        return
    before = old["evidence_before"]
    fresh = execution.collect_evidence(ROOT, chosen["directory"], tuple(chosen["inputs"]))
    require(all(before.get(key) == fresh[key] for key in
                ("directory", "inputs", "runner", "controller")))
    old_files, new_files = before["files"], fresh["files"]
    changed = {path for path in set(old_files) | set(new_files)
               if old_files.get(path) != new_files.get(path)}
    require(changed == ALLOWED_CHANGES)
    require(load()[2] == identity)
    verdict = execution.unit_test(
        workspace=ROOT, environment_file=chosen["environment_file"],
        directory=chosen["directory"], pattern=chosen["pattern"],
        minimum_tests=chosen["minimum_tests"],
        required_tests=tuple(chosen["required_tests"]),
        inputs=tuple(chosen["inputs"]), runtime_directory=OUT)
    process, _ = execution.read_receipt(ROOT, verdict["process_receipt"])
    result = verdict.get("result")
    print(json.dumps({
        "status": verdict["status"], "group": group,
        "verdict_file": verdict["verdict_path"],
        "process_receipt": verdict["process_receipt"],
        "returncode": process["returncode"], "cleanup_ok": process["cleanup_ok"],
        "timed_out": process["timed_out"], "cancelled": process["cancelled"],
        "tests_run": result["tests_run"] if result else None,
        "log_summary": process["summary"], "runtime_started": False,
        "plan_saved": False}, ensure_ascii=False), flush=True)
    require(verdict["status"] == "PASS" and process["returncode"] == 0
            and process["cleanup_ok"] is True and process["timed_out"] is False
            and process["cancelled"] is False)
    require(load()[2] == identity)


def adopt():
    data, tasks, identity = load()
    files = {}
    for group, members in GROUPS.items():
        relative = reusable(selection(tasks, group))
        require(relative is not None)
        for key in members:
            files[key] = relative
            candidate = copy.deepcopy(tasks[key])
            candidate["verdict_file"] = relative
            state.completed_evidence(ROOT, candidate)
    require(load()[2] == identity)
    with loop.writer_lease(ROOT):
        fresh, _, fresh_identity = state.load_plan(ROOT, PLAN)
        require(fresh == data and fresh_identity == identity)
        refreshed = adapter.refresh_completed(
            workspace=ROOT, plan_file=PLAN, verdict_files=files,
            expected_identity=identity)
        expected = copy.deepcopy(data)
        for task in expected["tasks"]:
            if task["task_id"] in files:
                task["verdict_file"] = files[task["task_id"]]
        saved, _, saved_identity = state.load_plan(ROOT, PLAN)
        require(saved == expected and saved_identity == refreshed["plan_identity"])
        projection = adapter.query(workspace=ROOT, plan_file=PLAN)
        require(projection["status"] == "READY"
                and projection["ready_tasks"] == [HEADLESS])
        relative = OUT + "/dependency-refresh-" + uuid.uuid4().hex + ".json"
        save_receipt(contained_path(ROOT, relative), {
            "operation": "authorized-completed-evidence-refresh", "status": "PASS",
            "plan_id": PLAN_ID, "plan_file": PLAN, "refreshed_verdicts": files,
            "headless_status": "PENDING", "headless_verdict": None,
            "runtime_started": False, "adr_accepted": False, "plan_archived": False,
            "evidence_boundary": "仅原完成项证据引用刷新；不证明真实Pi运行或客户端断开推进"})
    print(json.dumps({"status": "PASS", "operation_receipt": relative,
                      "ready_tasks": projection["ready_tasks"],
                      "task_progress_saved": True, "runtime_started": False},
                     ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("operation", choices=("verify", "adopt"))
    parser.add_argument("--group", choices=tuple(GROUPS))
    args = parser.parse_args()
    try:
        if args.operation == "verify":
            require(args.group is not None)
            verify(args.group)
        else:
            require(args.group is None)
            adopt()
        return 0
    except (OSError, ValueError, ImportError, KeyError, TypeError):
        print(json.dumps({"status": "BLOCKED", "operation": args.operation,
                          "group": args.group,
                          "reason": "必需绑定、退出或证据核验未通过；暂停并保留成果",
                          "runtime_started": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
