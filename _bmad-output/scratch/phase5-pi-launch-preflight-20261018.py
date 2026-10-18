"""独立启动前只读核验；不加载凭据、不联网、不启动模型、不写计划。"""
import ast
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_agent_backend as agent
import bmad_context_inputs as inputs
import bmad_loop as loop
from bmad_supervisor import SupervisorError

PLAN = "_bmad-output/pending_implementation_plan.md"
REQUEST = "_bmad-output/scratch/phase5-pi-headless-request-20261018.json"
CONFIG = "_bmad-output/scratch/phase5-pi-backend-20261018.json"
STARTUP_BYTES = 131072


def require(condition, message):
    if not condition:
        raise SupervisorError(message)


def main():
    try:
        require(Path.cwd().resolve() == ROOT, "工作目录不是授权工作区")
        current = loop.status(ROOT)
        require(current.get("writer_active") is False, "已有活动写入者；禁止启动")
        require(current.get("cleanup_ok") is True and current.get("finished_at"),
                "前序任务缺少最终清理证据")
        final = loop.read_record(ROOT, current["final_receipt"])
        require(all(final.get(key) == current.get(key) for key in
                    ("run_id", "status", "cleanup_ok", "finished_at", "final_receipt")),
                "前序最终回执与当前记录不一致")
        raw, _, _ = inputs.read_snapshot(ROOT, CONFIG, 16384)
        config = json.loads(raw, object_pairs_hook=agent.execution.unique_object)
        agent.validate_pi_config(config)
        require(config["backend"] == "pi-agent" and config["api_timeout_seconds"] == 360,
                "后端或会话预算不匹配")
        require(config["pi"]["model"] == "gpt-6.1-sol"
                and config["pi"]["tools"] == ["read", "edit", "write"]
                and config["credential_environment"] == "BMAD_PI_API_KEY"
                and config["pi"]["no_progress_rounds"] == 6,
                "模型、工具、凭据变量或熔断契约不匹配")
        spec = loop.LoopSpec(
            workspace=ROOT, plan_file=PLAN, request_file=REQUEST,
            backend="pi-agent", backend_config=CONFIG,
            maximum_rounds=30, maximum_calls=30, timeout_seconds=600,
            no_progress_rounds=6, maximum_model_requests=30,
            maximum_data_bytes=15000000, startup_bytes=STARTUP_BYTES,
            output_bytes=131072, runtime_directory=".bmad-runtime",
            save_progress=True,
        )
        spec.validate()
        assembled = inputs.assemble_plan_input(
            workspace=ROOT, plan_file=PLAN, request_file=REQUEST,
            maximum_bytes=STARTUP_BYTES)
        require(assembled["task_id"] == "P5-PI-HEADLESS", "就绪任务不匹配")
        startup = json.loads(assembled["payload"])
        require(startup["state_projection"]["plan_id"] == "BMAD-ANTI-BUREAUCRACY-20261012-01",
                "计划标识不匹配")
        envelope = {
            "schema_version": 1, "protocol": agent.PROTOCOL,
            "session_id": "0" * 32,
            "plan_id": startup["state_projection"]["plan_id"],
            "task_id": assembled["task_id"], "startup": startup,
            "recent_verification": None,
        }
        envelope_bytes = len((json.dumps(envelope, ensure_ascii=True, sort_keys=True) + "\n").encode())
        require(envelope_bytes + (startup["observed_host_bytes"] or 0) <= STARTUP_BYTES,
                "实际驱动外层输入超过启动预算；不得裁掉必要材料")
        for relative in ("bmralph-suite-v5/scripts/bmad_pi_evidence.py",
                         "bmralph-suite-v5/tests_pi/test_pi_headless_evidence.py"):
            ast.parse((ROOT / relative).read_bytes(), filename=relative)
        print(json.dumps({
            "status": "PASS", "ready_task": assembled["task_id"],
            "envelope_bytes": envelope_bytes, "startup_byte_limit": STARTUP_BYTES,
            "maximum_model_requests": 30, "maximum_data_bytes": 15000000,
            "timeout_seconds": 600, "session_timeout_seconds": 360,
            "no_progress_rounds": 6, "runtime_started": False,
            "credentials_read": False,
            "evidence_boundary": "只读启动契约、当前依赖证据及输入预算核验；不证明实际模型调用、工具权限或断开推进",
        }, ensure_ascii=False), flush=True)
        return 0
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)[:512],
                          "runtime_started": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
