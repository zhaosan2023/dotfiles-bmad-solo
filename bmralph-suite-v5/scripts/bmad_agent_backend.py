"""有界无头驱动协议；不猜测 Roo CLI 参数、不继承 IDE 登录态。

调用显式获准的工作区 Python 适配驱动，文件传递输入、stdin 封闭。
驱动须自行对接已核验运行时；隔离夹具不证明真实 Roo 能力。
Agent 结果只裁决调用状态，业务完成仍由独立类型化验证决定。
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import time
import uuid

import bmad_context as context
import bmad_context_inputs as inputs
import bmad_environment as environment
import bmad_execution as execution
from bmad_supervisor import TIERS, RunSpec, SupervisorError, contained_path, run, runtime_path, save_receipt

FIELDS = {"schema_version", "backend", "protocol", "runtime_kind", "source", "version",
          "driver_file", "credential_environment", "authorized", "authorization",
          "new_session", "headless", "api_timeout_seconds"}
PREFIX = b"BMAD_AGENT_RESULT "
PROTOCOL = "bmad-headless-json-v1"
RESULT_FIELDS = {"schema_version", "session_id", "plan_id", "task_id", "status"}
RESULT_STATES = {"OK", "AUTH_FAILED", "PERMISSION_DENIED", "NETWORK_ERROR"}


def load(root, relative, backend):
    raw, path, identity = inputs.read_snapshot(root, relative, 16384)
    config = json.loads(raw, object_pairs_hook=execution.unique_object)
    if (not isinstance(config, dict) or set(config) != FIELDS
            or type(config["schema_version"]) is not int or config["schema_version"] != 1
            or config["backend"] != backend or config["protocol"] != PROTOCOL):
        raise SupervisorError("无头驱动契约不完整或后端不匹配；不回退其他引擎")
    if config["authorized"] is not True or not isinstance(config["authorization"], str) or not config["authorization"].strip():
        raise SupervisorError("无头驱动未授权；不启动、不安装或询问凭据")
    if config["new_session"] is not True or config["headless"] is not True:
        raise SupervisorError("必须明确采用新会话与无头驱动；声明不替代真实运行时证据")
    if config["runtime_kind"] not in {"isolated-fixture", "roo-cli"}:
        raise SupervisorError("运行时种类未覆盖；不静默换引擎")
    if config["backend"] == "roo-cli" and config["runtime_kind"] == "isolated-fixture":
        raise SupervisorError("真实 Roo 后端不得声明为隔离夹具绕过运行时门禁")
    for field in ("source", "version"):
        if not isinstance(config[field], str) or not config[field].strip() or len(config[field].encode("utf-8")) > 2048:
            raise SupervisorError("须明确运行时来源和版本；不推断本机或远程事实")
    value = config["api_timeout_seconds"]
    if type(value) not in {int, float} or not math.isfinite(value) or not 0.05 <= value <= 30:
        raise SupervisorError("驱动会话进程时限须为 0.05 至 30 秒；旧字段不证明单次模型请求时限")
    credential = config["credential_environment"]
    if not isinstance(credential, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", credential) is None:
        raise SupervisorError("须明确凭据环境变量名称；不读取 IDE 认证文件")
    # 仅检查存在性；值不写入命令、输入、摘要或回执。
    if not os.environ.get(credential, "").strip():
        raise SupervisorError("独立运行时凭据缺失；认证未就绪，阻断并保留现场")
    driver_raw, driver, driver_identity = inputs.read_snapshot(root, config["driver_file"], 131072)
    if driver.suffix != ".py" or not driver_raw.strip():
        raise SupervisorError("当前无头协议只调用明确的非空 Python 适配驱动")
    return config, {path: identity, driver: driver_identity}


def timeout_dimensions(config, batch_deadline):
    """兼容旧字段，但只将其解释为驱动会话进程时限。

    未接通真实运行时的单次模型请求限时，不以外层进程限时冒充。
    批次截止时间只能缩短会话及工具原有上限，不能扩展它们。
    """
    limit = config["api_timeout_seconds"]
    if (type(limit) not in {int, float} or not math.isfinite(limit)
            or not 0.05 <= limit <= TIERS["verify"]):
        raise SupervisorError("驱动会话时限非法或超过既有 30 秒上限")
    if (type(batch_deadline) not in {int, float}
            or not math.isfinite(batch_deadline)):
        raise SupervisorError("批次截止时间须为有限的单调时钟值")
    now = time.monotonic()
    return {
        "model_request_timeout_seconds": None,
        "model_request_timeout_coverage": "UNKNOWN",
        "agent_session_timeout_seconds": limit,
        "agent_session_deadline": min(batch_deadline, now + limit),
        "batch_deadline": batch_deadline,
        "batch_remaining_seconds": max(0.0, batch_deadline - now),
        "tool_timeout_caps_seconds": dict(TIERS),
        "legacy_field": "api_timeout_seconds",
        "evidence_boundary": "旧字段仅限制整个驱动会话进程；未核验或强制执行运行时内部单次模型请求时限",
    }


def result_from_log(path, expected):
    payload = None
    with path.open("rb") as stream:
        at_start = True
        while True:
            line = stream.readline(16385)
            if not line:
                break
            if at_start and line.startswith(PREFIX):
                if payload is not None or len(line) > 16384 or not line.endswith(b"\n"):
                    raise SupervisorError("Agent 结果缺失、重复、超预算或不完整")
                payload = line[len(PREFIX):]
            at_start = line.endswith(b"\n")
    if payload is None:
        raise SupervisorError("Agent 退出或完成口令不能替代结构化驱动回执")
    data = json.loads(payload, object_pairs_hook=execution.unique_object)
    if (not isinstance(data, dict) or set(data) != RESULT_FIELDS
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or not isinstance(data["status"], str) or data["status"] not in RESULT_STATES
            or any(data[key] != value for key, value in expected.items())):
        raise SupervisorError("Agent 回执与当前新会话、计划或任务不匹配")
    return data


def invoke(*, workspace, config, assembled, runtime_directory, deadline, cancel_requested,
           feedback=None, maximum_bytes=context.DEFAULT_STARTUP_BYTES):
    """启动一个新驱动进程，保存完整回执；任何非零退出严判阻断。"""
    root = environment.contained_path(workspace, ".").resolve()
    timeouts = timeout_dimensions(config, deadline)
    if cancel_requested() or time.monotonic() >= timeouts["agent_session_deadline"]:
        raise SupervisorError("调用前已取消或批次预算耗尽；不创建新会话请求")
    session = uuid.uuid4().hex
    startup = json.loads(assembled["payload"])
    expected = {"session_id": session, "plan_id": startup["state_projection"]["plan_id"],
                "task_id": startup["task"]["task_id"]}
    envelope = {"schema_version": 1, "protocol": PROTOCOL, **expected,
                "startup": startup, "recent_verification": feedback}
    context.positive_budget(maximum_bytes, context.MAX_STARTUP_BYTES, "驱动输入预算")
    serialized = (json.dumps(envelope, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
    if len(serialized) + (startup["observed_host_bytes"] or 0) > maximum_bytes:
        raise SupervisorError("完整驱动输入与最近反馈超过启动预算；未裁掉必要约束")
    # L0 环境复核消耗批次预算，但不提前消耗尚未启动的驱动会话预算。
    # 显式选择现有解释器，不安装认证或依赖，不扩大任何超时上限。
    ready = environment.check(root, startup["task"]["verification"]["environment_file"])
    timeouts = timeout_dimensions(config, deadline)
    if cancel_requested() or time.monotonic() >= timeouts["agent_session_deadline"]:
        raise SupervisorError("环境复核后已取消或批次预算耗尽；不创建新会话请求")
    runtime = runtime_path(root, runtime_directory)
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    request = runtime / ("agent-input-" + session + ".json")
    save_receipt(request, envelope)
    process = run(RunSpec(
        operation="agent-call", argv=(ready["environment"]["python"]["path"], "-B",
            str(contained_path(root, config["driver_file"])), "--request-file",
            request.relative_to(root).as_posix()),
        workspace=root, runtime_directory=runtime_directory,
        target="agent:" + expected["plan_id"] + ":" + expected["task_id"], tier="verify",
        deadline=timeouts["agent_session_deadline"],
        cancel_requested=cancel_requested,
    ))
    reason = process["reason"]
    category = "PROCESS_ERROR"
    data = None
    try:
        data = result_from_log(contained_path(root, process["log_path"]), expected)
        category = data["status"]
        if data["status"] != "OK":
            reason = {"AUTH_FAILED": "运行时认证失败；不重试，不推进任务",
                      "PERMISSION_DENIED": "运行时权限拒绝；不重试，不推进任务",
                      "NETWORK_ERROR": "API／网络不可用；保留现场，不冒充业务失败"}[data["status"]]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        reason = reason or str(exc)
    if process["timed_out"]:
        reason, category = "驱动会话进程或批次截止时间耗尽；不推断内部模型请求超时，保留现场", "TIMEOUT"
    if process["cancelled"]:
        reason, category = "明确取消无头调用；保留成果", "CANCELLED"
    if not process["cleanup_ok"]:
        reason, category = "无法确认 Agent 进程组清理；禁止后续验证", "CLEANUP_UNKNOWN"
    if process["returncode"] != 0:
        reason = reason or "Agent 真实退出码非零；不推进任务"
    status = "PASS" if process["process_status"] == "PASS" and not reason and data and category == "OK" else "BLOCKED"
    return {"operation": "agent-call", "status": status, "reason": reason,
            "category": category, **expected, "process_receipt": process["receipt_path"],
            "returncode": process["returncode"], "cleanup_ok": process["cleanup_ok"],
            "cancelled": process["cancelled"], "timed_out": process["timed_out"],
            "runtime_kind": config["runtime_kind"], "timeout_dimensions": timeouts,
            "evidence_boundary": "驱动调用事实；隔离夹具不证明 Roo、新会话权限或远程断开；业务须独立验证"}
