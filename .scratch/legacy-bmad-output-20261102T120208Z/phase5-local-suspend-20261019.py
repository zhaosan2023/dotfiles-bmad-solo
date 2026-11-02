"""按当前用户授权暂停唯一未完成任务；不测试、不启动模型、不提交。

复用既有写租约及计划原子保存原语，仅改变暂停状态，不修改验收、
完成证据或其他任务。行政暂停没有独立类型化入口，本操作回执仅
记录真实保存结果，不另建任务进度，也不宣称同账号防篡改。
"""
import copy
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_context_inputs as inputs
import bmad_loop as loop
import bmad_plan_adapter as adapter
import bmad_state as state
from bmad_supervisor import SupervisorError, save_receipt, utc_now

PLAN = "_bmad-output/pending_implementation_plan.md"
ADR = "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
PLAN_ID = "BMAD-ANTI-BUREAUCRACY-20261012-01"
TASK = "P5-PI-HEADLESS"


def require(condition):
    if not condition:
        raise SupervisorError("暂停边界不满足；停止操作并保留已有成果")


def main():
    saved = False
    try:
        require(Path.cwd().resolve() == ROOT)
        current = loop.status(ROOT)
        require(current.get("writer_active") is False
                and current.get("cleanup_ok") is True
                and current.get("status") == "BLOCKED")
        adr_raw, _, adr_identity = inputs.read_snapshot(ROOT, ADR, 131072)
        require(adr_raw.decode("utf-8").splitlines().count("- Status: PROPOSED") == 1)
        with loop.writer_lease(ROOT):
            current = loop.status(ROOT)
            require(current.get("cleanup_ok") is True
                    and current.get("status") == "BLOCKED")
            data, _, identity = state.load_plan(ROOT, PLAN)
            tasks = state.validate_contract(data)
            require(data["plan_id"] == PLAN_ID
                    and TASK in tasks
                    and tasks[TASK]["status"] == "PENDING"
                    and tasks[TASK]["verdict_file"] is None)
            updated = copy.deepcopy(data)
            for task in updated["tasks"]:
                if task["task_id"] == TASK:
                    task["status"] = "SUSPENDED"
            fresh_adr, _, fresh_adr_identity = inputs.read_snapshot(ROOT, ADR, 131072)
            require(fresh_adr == adr_raw and fresh_adr_identity == adr_identity)
            adapter._save_plan(ROOT, PLAN, identity, updated, ())
            saved = True
            after, _, _ = state.load_plan(ROOT, PLAN)
            require(after == updated)
            receipt = "_bmad-output/verification/phase5-resume-20261018/local-suspend-" + uuid.uuid4().hex + ".json"
            result = {
                "operation": "local-suspend", "status": "PASS",
                "saved_at": utc_now(), "plan_file": PLAN, "plan_id": PLAN_ID,
                "task_id": TASK, "source_status": "SUSPENDED", "verdict_file": None,
                "authorization": "2026-10-19 用户仅授权本地证据交付，暂停独立Pi重试；保留全部改动和未完成事项，不提交、不启动远程任务，ADR保持PROPOSED。",
                "previous_run_id": current.get("run_id"),
                "previous_final_receipt": current.get("final_receipt"),
                "cleanup_ok": True, "task_progress_saved": True,
                "business_reexecuted": False, "runtime_started": False,
                "committed": False, "adr_accepted": False, "plan_archived": False,
                "evidence_boundary": "仅受限行政暂停及原子保存；不改变历史失败、不重新验证业务、不证明真实Pi或断开推进。"
            }
            save_receipt(ROOT / receipt, result)
        final = loop.status(ROOT)
        require(final.get("writer_active") is False and final.get("cleanup_ok") is True)
        print(json.dumps({"status": "PASS", "operation_receipt": receipt,
                          "task_status": "SUSPENDED", "task_progress_saved": saved,
                          "writer_active": False, "cleanup_ok": True,
                          "business_reexecuted": False, "runtime_started": False},
                         ensure_ascii=False), flush=True)
        return 0
    except (OSError, ValueError, ImportError, KeyError, TypeError):
        print(json.dumps({"status": "BLOCKED", "task_progress_saved": saved,
                          "reason": "暂停、绑定或回执保存未全部确认；保留成果，不重启、不回滚。",
                          "runtime_started": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
