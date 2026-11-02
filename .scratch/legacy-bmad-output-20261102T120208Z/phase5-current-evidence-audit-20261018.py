"""本轮只读证据审查：定位可复用回执及受影响组，不测试、不写进度。

只输出任务标识、固定分类、文件定位及计数；不读取凭据或日志正文，
不启动模型，不把历史失败或裁决器占位实现当作完成事实。
"""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_execution as execution
import bmad_loop as loop
import bmad_state as state
from bmad_supervisor import SupervisorError, contained_path

PLAN = "_bmad-output/pending_implementation_plan.md"
PLAN_ID = "BMAD-ANTI-BUREAUCRACY-20261012-01"
ADR = "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
HEADLESS = "P5-PI-HEADLESS"
COMPLETED = {"P3-PLAN", "P3-BACKEND", "P3-OFFLINE", "P4-BUDGET",
             "P4-BATCH", "P4-ISOLATION", "P5-PI-DRIVER"}
OUT = "_bmad-output/verification/phase5-20261018"


def require(condition):
    if not condition:
        raise SupervisorError("绑定、任务集合或清理边界变化；停止审查")


def matches(record, verification):
    result = record.get("result")
    before = record.get("evidence_before")
    manifest = record.get("environment_manifest")
    return (record.get("status") == "PASS"
            and isinstance(result, dict) and isinstance(before, dict)
            and isinstance(manifest, dict)
            and all(result.get(key) == verification[key] for key in
                    ("directory", "pattern", "minimum_tests", "required_tests"))
            and before.get("inputs") == verification["inputs"]
            and manifest.get("relative_path") == verification["environment_file"])


def changed_files(record, verification):
    before = record.get("evidence_before")
    require(isinstance(before, dict))
    fresh = execution.collect_evidence(
        ROOT, verification["directory"], tuple(verification["inputs"]))
    old_files = before["files"]
    new_files = fresh["files"]
    return {
        "changed_files": sorted(path for path in set(old_files) | set(new_files)
                                if old_files.get(path) != new_files.get(path)),
        "runner_changed": before.get("runner") != fresh["runner"],
        "controller_changed": before.get("controller") != fresh["controller"],
    }


def main():
    phase = "BINDING"
    try:
        require(Path.cwd().resolve() == ROOT)
        data, _, identity = state.load_plan(ROOT, PLAN)
        tasks = state.validate_contract(data)
        require(data["plan_id"] == PLAN_ID and set(tasks) == COMPLETED | {HEADLESS})
        require(all(tasks[key]["status"] == "COMPLETED" for key in COMPLETED))
        require(tasks[HEADLESS]["status"] == "PENDING"
                and tasks[HEADLESS]["verdict_file"] is None)
        header = contained_path(ROOT, PLAN).read_text().split("---", 2)[1]
        require('adr_file: "' + ADR + '"' in header)
        require("- Status: PROPOSED" in contained_path(ROOT, ADR).read_text().splitlines())
        current = loop.status(ROOT)
        require(current.get("writer_active") is False
                and current.get("cleanup_ok") is True and bool(current.get("finished_at")))
        final = loop.read_record(ROOT, current["final_receipt"])
        require(all(final.get(key) == current.get(key) for key in
                    ("run_id", "status", "cleanup_ok", "finished_at", "final_receipt")))
        selection = tasks[HEADLESS]["verification"]
        require(selection["directory"] == "bmralph-suite-v5/tests_pi"
                and selection["pattern"] == "test_pi_headless_evidence.py"
                and selection["minimum_tests"] == 8
                and len(selection["required_tests"]) == 8
                and selection["inputs"] == ["bmralph-suite-v5/scripts/bmad_pi_evidence.py"])
        tree = ast.parse(contained_path(ROOT, selection["directory"] + "/" +
                                        selection["pattern"]).read_bytes())
        actual_tests = ["test_pi_headless_evidence." + node.name + "." + method.name
                        for node in tree.body if isinstance(node, ast.ClassDef)
                        for method in node.body if isinstance(method, ast.FunctionDef)
                        and method.name.startswith("test_")]
        require(len(actual_tests) == 8
                and set(actual_tests) == set(selection["required_tests"]))
        phase = "EVIDENCE_QUERY"
        candidates = sorted(contained_path(ROOT, OUT).glob("run-*.verdict.json"),
                            key=lambda path: path.stat().st_mtime_ns, reverse=True)
        groups = []
        selections = {}
        for key, task in tasks.items():
            if key == HEADLESS:
                continue
            token = json.dumps(task["verification"], sort_keys=True)
            selections.setdefault(token, []).append(key)
        for members in selections.values():
            verification = tasks[members[0]]["verification"]
            current_file = tasks[members[0]]["verdict_file"]
            old, _ = execution.read_receipt(ROOT, current_file)
            require(matches(old, verification))
            reusable = None
            checked = execution.check_evidence(workspace=ROOT, verdict_file=current_file)
            if checked["status"] == "PASS":
                reusable = current_file
            else:
                for path in candidates:
                    relative = path.relative_to(ROOT).as_posix()
                    record, _ = execution.read_receipt(ROOT, relative)
                    if matches(record, verification):
                        result = execution.check_evidence(workspace=ROOT, verdict_file=relative)
                        if result["status"] == "PASS":
                            reusable = relative
                            break
            group = {"tasks": members, "pattern": verification["pattern"],
                     "minimum_tests": verification["minimum_tests"],
                     "required_test_count": len(verification["required_tests"]),
                     "current_verdict": current_file,
                     "current_evidence_status": checked["status"],
                     "reusable_verdict": reusable,
                     "verification_needed": reusable is None}
            if checked["status"] != "PASS":
                group.update(changed_files(old, verification))
            groups.append(group)
        require(state.load_plan(ROOT, PLAN)[2] == identity)
        result = {"operation": "current-evidence-read-only-audit", "status": "PASS",
                  "plan_id": PLAN_ID, "headless_source_status": "PENDING",
                  "headless_required_tests": 8, "writer_active": False,
                  "previous_cleanup_ok": True, "groups": groups,
                  "tests_executed": False, "runtime_started": False, "plan_saved": False,
                  "evidence_boundary": "审查完成不等于依赖就绪；仅仍有效的精确回执可复用，缺失组须按原契约定向验证，不改变验收或补造历史回执"}
        payload = json.dumps(result, ensure_ascii=False)
        require(len(payload.encode("utf-8")) <= 16384)
        print(payload, flush=True)
        return 0
    except (OSError, ValueError, ImportError, KeyError, TypeError):
        print(json.dumps({"status": "BLOCKED", "phase": phase,
                          "reason": "绑定或证据审查未完成；不输出来源正文",
                          "tests_executed": False, "runtime_started": False,
                          "plan_saved": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
