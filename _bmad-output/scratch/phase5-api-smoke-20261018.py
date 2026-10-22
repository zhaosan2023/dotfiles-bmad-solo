"""一次性真实 HTTP 冒烟；不是 Pi 运行、循环或客户端断开证据。

显式加载私有凭据，仅向获准本机网关发送一次无工具请求。
不重试、不跟随重定向、不回显凭据或服务端响应正文。
现有控制器未覆盖该网络探测；不更新计划任务或 ADR。
"""
from __future__ import annotations

import argparse
import http.client
import json
import os
from pathlib import Path
import signal
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "bmralph-suite-v5/scripts"))

import bmad_context_inputs as inputs
import bmad_loop as loop
import bmad_private_config as private_config
import bmad_state as state
from bmad_supervisor import (
    SupervisorError, contained_path, runtime_path, save_receipt,
    utc_now, verification_lock,
)

PLAN = "_bmad-output/pending_implementation_plan.md"
ADR = "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
PLAN_ID = "BMAD-ANTI-BUREAUCRACY-20261012-01"
CREDENTIAL = ".bmad-private/credentials.env"
OUTPUT = "_bmad-output/verification/phase5-20261018"
BUDGET = ".bmad-control/phase5-network-budget-20261018.json"
STREAM_BUDGET = ".bmad-control/phase5-network-budget-20261018-stream-window-2.json"
PREVIOUS_RECEIPT = OUTPUT + "/api-smoke-c127ac6bc6a34da1b5b25ad0a4d36117.json"
BASE_URL = "http://127.0.0.1:8080/v1"
MODEL = "gpt-6.1-sol"
MAX_RESPONSE_BYTES = 65536
MAX_SSE_EVENTS = 1024


def validate_sse_response(response, record):
    """有界接收 SSE；必须取得完整文本、stop 与 DONE，不保存响应正文。"""
    content_type = response.getheader("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "text/event-stream":
        raise SupervisorError("流式响应类型不匹配")
    total = 0
    events = 0
    data_lines = []
    text_parts = []
    assistant_seen = False
    finished = False
    stream_id = None
    while True:
        line = response.readline(MAX_RESPONSE_BYTES - total + 1)
        total += len(line)
        record["response_bytes"] = total
        if total > MAX_RESPONSE_BYTES:
            raise SupervisorError("流式响应超过读取预算")
        if not line:
            raise SupervisorError("流式响应提前结束，缺少 DONE")
        if not line.endswith(b"\n"):
            raise SupervisorError("流式响应行不完整")
        line = line[:-1]
        if line.endswith(b"\r"):
            line = line[:-1]
        if line:
            if line.startswith(b":"):
                continue
            field, separator, value = line.partition(b":")
            if value.startswith(b" "):
                value = value[1:]
            if field == b"data":
                data_lines.append(value)
            elif field not in {b"event", b"id", b"retry"}:
                raise SupervisorError("流式响应字段不支持")
            continue
        if not data_lines:
            continue
        events += 1
        record["sse_events"] = events
        if events > MAX_SSE_EVENTS:
            raise SupervisorError("流式事件数量超过预算")
        payload = b"\n".join(data_lines)
        data_lines.clear()
        if payload == b"[DONE]":
            record["stream_done_received"] = True
            valid = assistant_seen and finished and "".join(text_parts).strip() == "BMAD_API_SMOKE_OK"
            record["response_validated"] = valid
            return valid
        decoded = json.loads(payload.decode("utf-8"), object_pairs_hook=state.execution.unique_object)
        if (not isinstance(decoded, dict) or "error" in decoded
                or decoded.get("object") != "chat.completion.chunk"
                or decoded.get("model") != MODEL
                or not isinstance(decoded.get("id"), str) or not decoded["id"]):
            raise SupervisorError("流式响应身份或状态非法")
        if stream_id is None:
            stream_id = decoded["id"]
        elif decoded["id"] != stream_id:
            raise SupervisorError("流式响应标识变化")
        choices = decoded.get("choices")
        if choices == [] and finished and isinstance(decoded.get("usage"), dict):
            continue
        if (not isinstance(choices, list) or len(choices) != 1
                or not isinstance(choices[0], dict) or finished):
            raise SupervisorError("流式响应选择项或结束顺序非法")
        choice = choices[0]
        delta = choice.get("delta")
        if (type(choice.get("index")) is not int or choice["index"] != 0
                or not isinstance(delta, dict)
                or delta.get("tool_calls") or delta.get("function_call")):
            raise SupervisorError("流式响应含非法选择项或工具调用")
        role = delta.get("role")
        if role is not None:
            if role != "assistant":
                raise SupervisorError("流式响应角色不匹配")
            assistant_seen = True
        content = delta.get("content")
        if content is not None:
            if not isinstance(content, str):
                raise SupervisorError("流式文本类型非法")
            text_parts.append(content)
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None:
            if finish_reason != "stop":
                raise SupervisorError("流式响应未正常结束")
            finished = True
            record["stream_stop_received"] = True


class DeadlineReached(TimeoutError):
    pass


class Cancelled(Exception):
    pass


def deadline_handler(signum, frame):
    raise DeadlineReached()


def cancel_handler(signum, frame):
    raise Cancelled()


def bind():
    data, _, identity = state.load_plan(ROOT, PLAN)
    if data["plan_id"] != PLAN_ID:
        raise SupervisorError("绑定计划标识变化")
    plan_raw, _, _ = inputs.read_snapshot(ROOT, PLAN, state.MAX_PLAN_BYTES)
    header = plan_raw.decode("utf-8").split("---", 2)[1]
    if 'adr_file: "' + ADR + '"' not in header:
        raise SupervisorError("关联 ADR 变化")
    adr_raw, _, adr_identity = inputs.read_snapshot(ROOT, ADR, state.MAX_PLAN_BYTES)
    if "- Status: PROPOSED" not in adr_raw.decode("utf-8").splitlines():
        raise SupervisorError("ADR 状态不符合当前授权")
    return identity, adr_identity


def smoke(record, shared_deadline):
    connection = None
    previous_handlers = {}
    name = private_config.CREDENTIAL_NAME
    before = (name in os.environ, os.environ.get(name))
    try:
        with private_config.credential_environment(ROOT, CREDENTIAL):
            record["credential_loaded"] = bool(os.environ.get(name, "").strip())
            remaining = shared_deadline - time.monotonic()
            if remaining <= 0:
                raise DeadlineReached()
            request_limit = min(20.0, remaining)
            for signum, handler in (
                (signal.SIGALRM, deadline_handler),
                (signal.SIGTERM, cancel_handler),
                (signal.SIGINT, cancel_handler),
            ):
                previous_handlers[signum] = signal.signal(signum, handler)
            signal.setitimer(signal.ITIMER_REAL, request_limit)
            connection = http.client.HTTPConnection("127.0.0.1", 8080, timeout=request_limit)
            body = json.dumps({
                "model": MODEL,
                "messages": [{"role": "user", "content": "Reply with exactly: BMAD_API_SMOKE_OK"}],
                "stream": True,
                "max_tokens": 32,
                "n": 1,
            }).encode("utf-8")
            record["http_request_attempts"] = 1
            record["request_started_at"] = utc_now()
            connection.request("POST", "/v1/chat/completions", body=body, headers={
                "Authorization": "Bearer " + os.environ[name],
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Connection": "close",
            })
            response = connection.getresponse()
            record["http_status"] = response.status
            if response.status != 200:
                record["category"] = (
                    "AUTH_FAILED" if response.status in {401, 403} else "HTTP_ERROR"
                )
                return
            valid = validate_sse_response(response, record)
            record["category"] = "OK" if valid else "INVALID_RESPONSE"
            record["status"] = "PASS" if valid else "BLOCKED"
    finally:
        if signal.SIGALRM in previous_handlers:
            signal.setitimer(signal.ITIMER_REAL, 0)
        for signum, previous in previous_handlers.items():
            signal.signal(signum, previous)
        record["environment_restored"] = (name in os.environ, os.environ.get(name)) == before
        if connection is not None:
            try:
                connection.close()
            except OSError:
                record["cleanup_ok"] = False
        if not record["environment_restored"] or not record["cleanup_ok"]:
            record["status"] = "BLOCKED"
            record["category"] = "CLEANUP_FAILED"


def previous_window():
    """核验确切的一次失败尝试；只读旧记录，不继承旧窗口或覆盖证据。"""
    raw_budget, budget_path, budget_identity = inputs.read_snapshot(ROOT, BUDGET, 16384)
    raw_receipt, receipt_path, receipt_identity = inputs.read_snapshot(ROOT, PREVIOUS_RECEIPT, 16384)
    budget = json.loads(raw_budget, object_pairs_hook=state.execution.unique_object)
    receipt = json.loads(raw_receipt, object_pairs_hook=state.execution.unique_object)
    if not isinstance(budget, dict) or not isinstance(receipt, dict):
        raise SupervisorError("前序预算或回执格式非法")
    expected = {"plan_id": PLAN_ID, "workspace": str(ROOT), "base_url": BASE_URL, "model": MODEL}
    if any(budget.get(key) != value or receipt.get(key) != value
           for key, value in expected.items()):
        raise SupervisorError("前序证据目标不匹配")
    if (budget.get("smoke_receipt") != PREVIOUS_RECEIPT
            or type(budget.get("reserved_request_slots")) is not int
            or budget["reserved_request_slots"] != 1
            or receipt.get("operation") != "direct-http-api-smoke"
            or receipt.get("budget_reservation") != BUDGET
            or receipt.get("status") != "BLOCKED"
            or receipt.get("http_status") != 502
            or type(receipt.get("http_request_attempts")) is not int
            or receipt["http_request_attempts"] != 1
            or receipt.get("automatic_retries") != 0
            or receipt.get("tools_enabled") is not False
            or receipt.get("cleanup_ok") is not True
            or receipt.get("environment_restored") is not True
            or receipt.get("pi_runtime_executed") is not False
            or not receipt.get("finished_at")):
        raise SupervisorError("前序失败尝试或清理证据不满足第二窗口边界")
    return {budget_path: budget_identity, receipt_path: receipt_identity}


def main(*, authorized_stream_window_2=False):
    if type(authorized_stream_window_2) is not bool:
        raise SupervisorError("窗口选择必须为显式布尔参数")
    budget_relative = STREAM_BUDGET if authorized_stream_window_2 else BUDGET
    previous_attempts = 1 if authorized_stream_window_2 else 0
    if Path.cwd().resolve() != ROOT:
        raise SupervisorError("工作目录不是获准工作区")
    bindings = bind()
    current = loop.status(ROOT)
    if current.get("writer_active") or current.get("cleanup_ok") is not True:
        raise SupervisorError("存在活动写入者或前序清理未知；不发送请求")
    control = runtime_path(ROOT, ".bmad-control")
    record = {
        "schema_version": 1,
        "operation": "direct-http-api-smoke",
        "status": "BLOCKED",
        "category": "PRECONDITION_FAILED",
        "workspace": str(ROOT),
        "plan_id": PLAN_ID,
        "plan_file": PLAN,
        "adr_file": ADR,
        "base_url": BASE_URL,
        "model": MODEL,
        "api": "openai-completions",
        "request_path": "/v1/chat/completions",
        "credential_file": CREDENTIAL,
        "started_at": utc_now(),
        "http_request_attempts": 0,
        "automatic_retries": 0,
        "redirects_followed": 0,
        "tools_enabled": False,
        "request_stream": True,
        "response_protocol": "SSE",
        "stream_done_received": False,
        "stream_stop_received": False,
        "response_validated": False,
        "cleanup_ok": True,
        "environment_restored": True,
        "plan_progress_saved": False,
        "pi_runtime_executed": False,
        "pi_loop_gate": "BLOCKED",
        "evidence_boundary": (
            "仅验证一次直接 HTTP 请求及显式私有加载；不证明 Pi 配置、"
            "Pi 内部请求预算、网关内部重试、工具权限或客户端断开推进。"
            "占位凭据仅在服务端实际接受且响应校验通过后形成冒烟通过证据。"
        ),
    }
    with loop.writer_lease(ROOT), verification_lock(control):
        if contained_path(ROOT, budget_relative).exists():
            raise SupervisorError("本轮网络预算已有预留；保留原记录，禁止重复启动")
        previous_bound = previous_window() if authorized_stream_window_2 else {}
        if bind() != bindings:
            raise SupervisorError("请求前绑定变化；不发送请求")
        for path, identity in previous_bound.items():
            if state.execution.environment.fingerprint(path) != identity:
                raise SupervisorError("前序证据变化；不发送请求")
        directory = runtime_path(ROOT, OUTPUT)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        receipt_relative = OUTPUT + "/api-smoke-" + uuid.uuid4().hex + ".json"
        shared_started = time.monotonic()
        shared_deadline = shared_started + 60.0
        save_receipt(contained_path(ROOT, budget_relative), {
            "schema_version": 1,
            "record_kind": "network-budget-reservation-not-task-progress",
            "plan_id": PLAN_ID,
            "workspace": str(ROOT),
            "base_url": BASE_URL,
            "model": MODEL,
            "started_at": utc_now(),
            "started_monotonic": shared_started,
            "deadline_monotonic": shared_deadline,
            "maximum_model_request_attempts": 1 if authorized_stream_window_2 else 5,
            "maximum_client_request_attempts_this_window": 1,
            "maximum_cumulative_client_request_attempts": 2 if authorized_stream_window_2 else 1,
            "previous_client_request_attempts": previous_attempts,
            "previous_budget": BUDGET if authorized_stream_window_2 else None,
            "previous_receipt": PREVIOUS_RECEIPT if authorized_stream_window_2 else None,
            "authorization": "新 60 秒窗口，仅一次流式无工具请求，累计至多两次，不重试、不启动循环"
                             if authorized_stream_window_2 else "原单次冒烟授权",
            "total_timeout_seconds": 60,
            "reserved_request_slots": 1,
            "smoke_receipt": receipt_relative,
            "pi_request_enforcement_implemented": False,
            "scope": "仅一次直接 HTTP 冒烟；不授权 Pi 或循环，不覆盖网关内部请求计量",
        })
        record["budget_reservation"] = budget_relative
        record["previous_client_request_attempts"] = previous_attempts
        record["maximum_client_request_attempts_this_window"] = 1
        record["maximum_cumulative_client_request_attempts"] = 2 if authorized_stream_window_2 else 1
        record["previous_receipt"] = PREVIOUS_RECEIPT if authorized_stream_window_2 else None
        record["request_timeout_seconds_cap"] = 20
        try:
            smoke(record, shared_deadline)
        except DeadlineReached:
            record.update(status="BLOCKED", category="TIMEOUT")
        except Cancelled:
            record.update(status="BLOCKED", category="CANCELLED")
        except (OSError, http.client.HTTPException):
            record.update(status="BLOCKED", category="NETWORK_ERROR")
        except (ValueError, KeyError, TypeError):
            record.update(status="BLOCKED", category="INVALID_RESPONSE_OR_CONFIGURATION")
        finally:
            try:
                if (bind() != bindings or any(
                        state.execution.environment.fingerprint(path) != identity
                        for path, identity in previous_bound.items())):
                    record.update(status="BLOCKED", category="BINDING_CHANGED")
            except (OSError, ValueError, KeyError, TypeError, IndexError):
                record.update(status="BLOCKED", category="BINDING_UNAVAILABLE")
            record["cumulative_client_request_attempts"] = previous_attempts + record["http_request_attempts"]
            record["finished_at"] = utc_now()
            record["elapsed_seconds"] = round(time.monotonic() - shared_started, 3)
            record["shared_budget_remaining_seconds"] = max(0.0, shared_deadline - time.monotonic())
            save_receipt(contained_path(ROOT, receipt_relative), record)
    print(json.dumps({
        "operation": record["operation"],
        "status": record["status"],
        "category": record["category"],
        "http_status": record.get("http_status"),
        "http_request_attempts": record["http_request_attempts"],
        "automatic_retries": 0,
        "cleanup_ok": record["cleanup_ok"],
        "environment_restored": record["environment_restored"],
        "receipt": receipt_relative,
        "budget_reservation": budget_relative,
        "previous_client_request_attempts": previous_attempts,
        "cumulative_client_request_attempts": record["cumulative_client_request_attempts"],
        "response_validated": record["response_validated"],
        "stream_stop_received": record["stream_stop_received"],
        "stream_done_received": record["stream_done_received"],
        "pi_runtime_executed": False,
        "pi_loop_gate": "BLOCKED",
    }, ensure_ascii=False), flush=True)
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--authorized-stream-window-2", action="store_true")
    arguments = parser.parse_args()
    try:
        sys.exit(main(authorized_stream_window_2=arguments.authorized_stream_window_2))
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        print(json.dumps({
            "operation": "direct-http-api-smoke", "status": "BLOCKED",
            "category": "PRECONDITION_OR_RECEIPT_FAILURE", "pi_loop_gate": "BLOCKED",
        }), flush=True)
        sys.exit(1)
