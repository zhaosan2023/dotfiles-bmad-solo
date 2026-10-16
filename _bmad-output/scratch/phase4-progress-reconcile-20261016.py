"""本轮显式证据对账；不启动 Agent，不运行测试，不建立第二份任务进度。"""
from pathlib import Path
import json
import sys
import uuid

ROOT = Path.cwd().resolve()
SCRIPTS = ROOT / "bmralph-suite-v5/scripts"
sys.path.insert(0, str(SCRIPTS))

import bmad_loop as loop
import bmad_plan_adapter as adapter
import bmad_state as state
from bmad_supervisor import SupervisorError, contained_path, runtime_path, save_receipt, utc_now

PLAN = "_bmad-output/pending_implementation_plan.md"
ADR = "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
PLAN_ID = "BMAD-ANTI-BUREAUCRACY-20261012-01"
DIRECTORY = "_bmad-output/verification/phase4-20261016"
PLAN_VERDICT = DIRECTORY + "/run-14fce12179244e99b29e4610e69b359d.verdict.json"
BACKEND_VERDICT = DIRECTORY + "/run-b3935e64965447cbbb03c38a36fe608d.verdict.json"
BATCH_VERDICT = DIRECTORY + "/run-631c3f63aeaa4c1a982830b7140525fc.verdict.json"
ISOLATION_VERDICT = DIRECTORY + "/run-92a653bd2b854eb1a4d9989968c7112e.verdict.json"
RELATED_VERDICTS = (
    DIRECTORY + "/run-a5b94b9ecb4d4ca29bdd6e03f8142134.verdict.json",
    DIRECTORY + "/run-f79531dfdb614a04b2133ad30bf1fe7f.verdict.json",
    DIRECTORY + "/run-983c67d23a394af3b49450a2ac048974.verdict.json",
    DIRECTORY + "/run-cd15cc7485b34aaf984ec466bd695ea9.verdict.json",
)


def main():
    receipt = {"operation": "explicit-plan-evidence-reconciliation", "cwd": str(ROOT),
               "argv": [sys.executable, *sys.argv], "python_version": sys.version.split()[0],
               "plan_file": PLAN, "plan_id": PLAN_ID, "adr_file": ADR,
               "started_at": utc_now(), "status": "BLOCKED", "actions": [],
               "business_reexecuted": False, "agent_started": False,
               "evidence_boundary": "仅核验本轮明确回执并更新同一计划的结构化清单；不证明真实 Roo、宿主激活或全计划完成"}
    code = 1
    try:
        with loop.writer_lease(ROOT):
            if contained_path(ROOT, loop.CURRENT).exists():
                previous = loop.read_record(ROOT, loop.CURRENT)
                if previous.get("status") == "EXECUTING" or previous.get("cleanup_ok") is not True:
                    raise SupervisorError("前序清理未知；不恢复旧进程、不对账或推进")
            data, _, identity = state.load_plan(ROOT, PLAN)
            if data["plan_id"] != PLAN_ID:
                raise SupervisorError("计划标识变化；停止对账")
            content = contained_path(ROOT, PLAN).read_text(encoding="utf-8")
            header = content.split("---", 2)[1].splitlines()
            if ('status: READY' not in header or 'scenario: structural' not in header
                    or 'adr_file: "' + ADR + '"' not in header):
                raise SupervisorError("计划元数据或关联提案变化；停止对账")
            if "- Status: PROPOSED" not in contained_path(ROOT, ADR).read_text(encoding="utf-8").splitlines()[:10]:
                raise SupervisorError("关联 ADR 状态变化；不转正、不归档")
            refresh = {"P3-PLAN": PLAN_VERDICT, "P3-BACKEND": BACKEND_VERDICT,
                       "P3-OFFLINE": BACKEND_VERDICT, "P4-BUDGET": BACKEND_VERDICT,
                       "P4-BATCH": BATCH_VERDICT}
            tasks = state.validate_contract(data)
            if (set(tasks) != set(refresh) | {"P4-ISOLATION"}
                    or any(tasks[key]["status"] != "COMPLETED" for key in refresh)
                    or tasks["P4-ISOLATION"]["status"] != "PENDING"):
                raise SupervisorError("本批任务集合或接管状态变化；不恢复或覆盖其他事项")
            # 全部明确证据先只读核验；任何失效均在写回之前阻断。
            for relative in RELATED_VERDICTS:
                checked = state.execution.check_evidence(workspace=ROOT, verdict_file=relative)
                receipt["actions"].append(checked)
                if checked["status"] != "PASS":
                    raise SupervisorError(checked["reason"])
            for key, relative in {**refresh, "P4-ISOLATION": ISOLATION_VERDICT}.items():
                candidate = dict(tasks[key], status="COMPLETED", verdict_file=relative)
                state.completed_evidence(ROOT, candidate)
            refreshed = adapter.refresh_completed(
                workspace=ROOT, plan_file=PLAN, verdict_files=refresh,
                expected_identity=identity)
            receipt["actions"].append({"operation": "refresh-completed", **refreshed})
            identity = refreshed["plan_identity"]
            saved = adapter.complete(workspace=ROOT, plan_file=PLAN, task_id="P4-ISOLATION",
                                     verdict_file=ISOLATION_VERDICT, expected_identity=identity)
            receipt["actions"].append({"operation": "complete-one-task", **saved})
            projection = adapter.query(workspace=ROOT, plan_file=PLAN)
            if (projection["status"] != "COMPLETED" or projection["ready_tasks"] != []
                    or projection["unfinished_count"] != 0 or projection["tasks_total"] != 6):
                raise SupervisorError("对账后本地清单投影不满足阶段边界；不宣称全计划完成")
            receipt.update(status="PASS", reason="本批六项本地清单已核验；原 Epic、AC 与真实运行时门禁仍保留",
                           next_ready_tasks=projection["ready_tasks"],
                           view_lines=projection["view_lines"], view_bytes=projection["view_bytes"],
                           whole_plan_completed=False, real_runtime_verified=False)
            code = 0
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        receipt["reason"] = str(exc)[:512]
    receipt.update(finished_at=utc_now(), returncode=code)
    directory = runtime_path(ROOT, DIRECTORY)
    path = directory / ("progress-reconcile-" + uuid.uuid4().hex + ".json")
    save_receipt(path, receipt)
    print(json.dumps({"status": receipt["status"], "reason": receipt["reason"],
                      "returncode": code, "receipt_path": path.relative_to(ROOT).as_posix(),
                      "actions_saved": len(receipt["actions"]),
                      "next_ready_tasks": receipt.get("next_ready_tasks"),
                      "business_reexecuted": False, "agent_started": False}, ensure_ascii=False), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
