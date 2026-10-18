"""离线诊断阶段边界核验；只输出白名单元数据，不读取日志或凭据。

不发送请求、不启动模型、不执行测试、不修改计划或历史回执。
类型化单测证据查询不等于真实运行通过；历史缺字段保持未知。
"""
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))
import bmad_execution as execution
import bmad_loop as loop
from bmad_supervisor import SupervisorError, contained_path, save_receipt

HISTORY = ".bmad-runtime/loop-746134471c7441c9814dddcb6b8c7181.json"
WRAPPER = ".bmad-runtime/phase5-pi-detached-20261018-attempt2.exit.json"
OUT = "_bmad-output/verification/phase5-diagnostics-20261018"
VERDICTS = (
    ("diagnostics", 12, OUT + "/run-fe08b140a5f84e29a5b1a5b973546927.verdict.json"),
    ("transport-regression", 12, OUT + "/run-54315d31dd3246d8967a130944436a8c.verdict.json"),
    ("activation-integration", 11, OUT + "/run-2926c996cbb743149a1bd69ec93fa0a7.verdict.json"),
)


def require(condition, message):
    if not condition:
        raise SupervisorError(message)


def main():
    phase = "WORKSPACE"
    group = None
    try:
        require(Path.cwd().resolve() == ROOT, "工作目录不匹配")
        phase = "HISTORY_LOAD"
        current = loop.status(ROOT)
        original = loop.read_record(ROOT, HISTORY)
        wrapper = loop.read_record(ROOT, WRAPPER)
        phase = "HISTORY_BINDING"
        require(current.get("final_receipt") == HISTORY,
                "当前运行发生变化；停止阶段交付")
        require(all(current.get(key) == original.get(key) for key in
                    ("run_id", "status", "finished_at", "cleanup_ok")),
                "历史最终回执与当前视图不一致")
        require(current.get("writer_active") is False, "存在活动写入者")
        require(original.get("status") == "BLOCKED"
                and original.get("cleanup_ok") is True
                and original.get("finished_at")
                and original.get("completed_tasks") == []
                and original.get("last_verdict") is None,
                "原失败实例状态或清理边界变化")
        require(wrapper.get("returncode") == 1, "包装退出证据变化")
        phase = "HISTORY_NETWORK"
        network = original["network_budget"]
        require(network["model_request_attempts"] == 1
                and network["data_bytes"] == 59676
                and network["request_bytes"] == 59574
                and network["response_bytes"] == 102,
                "历史计量变化；不得推定无新增请求")
        events = network["events"]
        require(len(events) == 1 and events[0]["http_status"] == 200
                and events[0]["outcome"] == "NETWORK_ERROR"
                and events[0]["finished_at"], "历史结束事件变化")
        transport = original["last_agent"]["transport"]
        require(transport.get("cleanup_ok") is True
                and transport.get("thread_active") is False,
                "受管转发清理未确认")
        verified = []
        for label, expected_count, relative in VERDICTS:
            group = label
            phase = "CURRENT_EVIDENCE_CHECK"
            checked = execution.check_evidence(workspace=ROOT, verdict_file=relative)
            require(checked["status"] == "PASS", "当前证据不可复用：" + label)
            phase = "VERIFICATION_RECEIPTS"
            verdict, _ = execution.read_receipt(ROOT, relative)
            process, _ = execution.read_receipt(ROOT, verdict["process_receipt"])
            result = verdict["result"]
            require(verdict["status"] == "PASS"
                    and process["returncode"] == 0
                    and process["cleanup_ok"] is True
                    and process["timed_out"] is False
                    and process["cancelled"] is False,
                    "验证退出或清理证据不足：" + label)
            require(result["tests_run"] == expected_count
                    and result["skipped"] == 0
                    and result["failures"] == 0
                    and result["errors"] == 0
                    and result["missing_required_tests"] == [],
                    "必需验证未全部通过：" + label)
            verified.append({
                "group": label, "tests_run": expected_count,
                "returncode": process["returncode"],
                "cleanup_ok": process["cleanup_ok"],
                "timed_out": process["timed_out"],
                "cancelled": process["cancelled"], "skipped": result["skipped"],
                "verdict_file": relative, "process_receipt": verdict["process_receipt"],
            })
        record = {
            "operation": "offline-diagnostics-stage-audit", "status": "PASS",
            "runtime_handoff_status": "BLOCKED", "history_receipt": HISTORY,
            "historical_diagnostic_available": isinstance(transport.get("failure"), dict),
            "historical_root_cause": "UNKNOWN",
            "historical_model_request_attempts": network["model_request_attempts"],
            "historical_data_bytes": network["data_bytes"],
            "historical_response_bytes": network["response_bytes"],
            "historical_http_status": events[0]["http_status"],
            "writer_active": current["writer_active"],
            "managed_cleanup_ok": original["cleanup_ok"],
            "groups": verified, "total_tests": sum(item[1] for item in VERDICTS),
            "tests_reexecuted": False, "runtime_started": False,
            "plan_saved": False, "adr_accepted": False, "plan_archived": False,
            "evidence_boundary": "仅离线分类及现有元数据核验；不读取正文、不反推历史根因，不证明真实模型路径、客户端断开或全计划完成；测试用临时回环连接不属于模型请求",
        }
        phase = "AUDIT_SAVE"
        relative = OUT + "/diagnostics-audit-" + uuid.uuid4().hex + ".json"
        save_receipt(contained_path(ROOT, relative), record)
        record["audit_receipt"] = relative
        print(json.dumps(record, ensure_ascii=False), flush=True)
        return 0
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        # 仅固定阶段、已声明验证组和异常大类；不输出异常消息或对象。
        if isinstance(exc, KeyError):
            category = "RECEIPT_FIELD_MISSING"
        elif isinstance(exc, OSError):
            category = "FILE_OR_IO_ERROR"
        elif isinstance(exc, ImportError):
            category = "IMPORT_ERROR"
        elif isinstance(exc, TypeError):
            category = "RECEIPT_TYPE_ERROR"
        else:
            category = "EVIDENCE_OR_BOUNDARY_REJECTED"
        print(json.dumps({"status": "BLOCKED", "operation": "offline-diagnostics-stage-audit",
                          "reason": "阶段边界、退出或当前证据核验未通过；不输出来源正文",
                          "phase": phase, "group": group, "category": category,
                          "runtime_started": False}, ensure_ascii=False), flush=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
