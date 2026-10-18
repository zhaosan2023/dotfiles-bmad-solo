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
import stat
import sys
import time
import uuid

import bmad_context as context
import bmad_context_inputs as inputs
import bmad_environment as environment
import bmad_execution as execution
from bmad_supervisor import PI_AGENT_TIMEOUT_SECONDS, TIERS, RunSpec, SupervisorError, contained_path, run, runtime_path, save_receipt

FIELDS = {"schema_version", "backend", "protocol", "runtime_kind", "source", "version",
          "driver_file", "credential_environment", "authorized", "authorization",
          "new_session", "headless", "api_timeout_seconds"}
PREFIX = b"BMAD_AGENT_RESULT "
PROTOCOL = "bmad-headless-json-v1"
RESULT_FIELDS = {"schema_version", "session_id", "plan_id", "task_id", "status"}
RESULT_STATES = {"OK", "AUTH_FAILED", "PERMISSION_DENIED", "NETWORK_ERROR"}
PI_FIELDS = FIELDS | {"pi"}
PI_SOURCE = "https://github.com/earendil-works/pi"
PI_PACKAGE = "@earendil-works/pi-coding-agent"
PI_VERSION = "1.3.0"
PI_TOOLS = {"read", "bash", "edit", "write", "grep", "find", "ls"}
PI_RECORD_BYTES = 131072
PI_STREAM_BYTES = 8 * 1024 * 1024


def load(root, relative, backend):
    raw, path, identity = inputs.read_snapshot(root, relative, 16384)
    config = json.loads(raw, object_pairs_hook=execution.unique_object)
    fields = PI_FIELDS if isinstance(config, dict) and config.get("runtime_kind") == "pi-agent" else FIELDS
    if (not isinstance(config, dict) or set(config) != fields
            or type(config["schema_version"]) is not int or config["schema_version"] != 1
            or config["backend"] != backend or config["protocol"] != PROTOCOL):
        raise SupervisorError("无头驱动契约不完整或后端不匹配；不回退其他引擎")
    if config["authorized"] is not True or not isinstance(config["authorization"], str) or not config["authorization"].strip():
        raise SupervisorError("无头驱动未授权；不启动、不安装或询问凭据")
    if config["new_session"] is not True or config["headless"] is not True:
        raise SupervisorError("必须明确采用新会话与无头驱动；声明不替代真实运行时证据")
    if config["runtime_kind"] not in {"isolated-fixture", "roo-cli", "pi-agent"}:
        raise SupervisorError("运行时种类未覆盖；不静默换引擎")
    if config["backend"] in {"roo-cli", "pi-agent"} and config["runtime_kind"] == "isolated-fixture":
        raise SupervisorError("真实后端不得声明为隔离夹具绕过运行时门禁")
    if config["backend"] == "pi-agent" and config["runtime_kind"] != "pi-agent":
        raise SupervisorError("Pi 后端必须绑定真实 Pi 类别；不换引擎")
    if config["runtime_kind"] == "pi-agent":
        validate_pi_config(config)
    for field in ("source", "version"):
        if not isinstance(config[field], str) or not config[field].strip() or len(config[field].encode("utf-8")) > 2048:
            raise SupervisorError("须明确运行时来源和版本；不推断本机或远程事实")
    value = config["api_timeout_seconds"]
    cap = PI_AGENT_TIMEOUT_SECONDS if config["runtime_kind"] == "pi-agent" else TIERS["verify"]
    if type(value) not in {int, float} or not math.isfinite(value) or not 0.05 <= value <= cap:
        raise SupervisorError("驱动会话进程时限超出对应后端上限；旧字段不证明单次模型请求时限")
    credential = config["credential_environment"]
    if not isinstance(credential, str) or re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,127}", credential) is None:
        raise SupervisorError("须明确凭据环境变量名称；不读取 IDE 认证文件")
    # 仅检查存在性；值不写入命令、输入、摘要或回执。
    if not os.environ.get(credential, "").strip():
        raise SupervisorError("独立运行时凭据缺失；认证未就绪，阻断并保留现场")
    driver_raw, driver, driver_identity = inputs.read_snapshot(root, config["driver_file"], 131072)
    if driver.suffix != ".py" or not driver_raw.strip():
        raise SupervisorError("当前无头协议只调用明确的非空 Python 适配驱动")
    if config["runtime_kind"] == "pi-agent" and driver.resolve() != Path(__file__).resolve():
        raise SupervisorError("Pi 薄驱动必须绑定本模块；不加载第三方适配变体")
    return config, {path: identity, driver: driver_identity}


def validate_pi_config(config):
    """仅固定版本原生 JSON 单次调用；不接受任意附加 CLI 参数。"""
    if (not isinstance(config, dict) or set(config) != PI_FIELDS
            or config.get("backend") not in {"headless", "pi-agent"}
            or config.get("runtime_kind") != "pi-agent"
            or type(config.get("schema_version")) is not int or config["schema_version"] != 1
            or config.get("protocol") != PROTOCOL
            or config.get("authorized") is not True
            or not isinstance(config.get("authorization"), str) or not config["authorization"].strip()
            or config.get("new_session") is not True or config.get("headless") is not True
            or config.get("source") != PI_SOURCE or config.get("version") != PI_VERSION):
        raise SupervisorError("Pi 来源、固定版本、新会话或授权契约不匹配")
    options = config["pi"]
    if (not isinstance(options, dict)
            or set(options) not in (
                {"executable", "provider", "model", "tools", "no_progress_rounds"},
                {"executable", "provider", "model", "tools", "no_progress_rounds", "gateway"})
            or options["executable"] != "/usr/local/bin/pi"
            or type(options["no_progress_rounds"]) is not int
            or options["no_progress_rounds"] not in {3, 6}):
        raise SupervisorError("Pi 参数组不完整；仅接受既有 3 轮或本次获准 6 轮无进展熔断")
    if "gateway" in options:
        gateway = options["gateway"]
        if (not isinstance(gateway, dict)
                or gateway != {"base_url": "http://127.0.0.1:8080/v1",
                               "api": "openai-completions"}):
            raise SupervisorError("Pi 网关必须绑定已获准的回环地址及流式协议")
    for field in ("provider", "model"):
        value = options[field]
        if (not isinstance(value, str) or not value or len(value.encode("utf-8")) > 256
                or value.startswith(("-", "@")) or any(char.isspace() for char in value)
                or "\x00" in value):
            raise SupervisorError("Pi 提供方和模型须明确且不能注入参数")
    tools = options["tools"]
    if (not isinstance(tools, list) or not tools or any(not isinstance(tool, str) for tool in tools)
            or len(set(tools)) != len(tools) or not set(tools) <= PI_TOOLS):
        raise SupervisorError("Pi 仅接受明确的原生工具白名单；不加载扩展或 MCP")
    credential = config["credential_environment"]
    if (not isinstance(credential, str) or len(credential) > 128
            or re.fullmatch(r"[A-Z][A-Z0-9_]*_(?:API_KEY|AUTH_TOKEN|OAUTH_TOKEN)", credential) is None):
        raise SupervisorError("Pi 须明确独立提供方凭据变量名；不接管 IDE 登录态")
    timeout_dimensions(config, time.monotonic() + TIERS["verify"])


def pi_arguments(config, request_file):
    """只组装参数，不启动进程；请求文件包含受预算约束的本轮输入。"""
    validate_pi_config(config)
    request = Path(request_file)
    if not request.is_absolute() or "\x00" in str(request):
        raise SupervisorError("Pi 请求须为监督器生成的绝对文件路径")
    options = config["pi"]
    return (options["executable"], "--print", "--mode", "json", "--no-session",
            "--no-extensions", "--no-mcp", "--no-skills", "--no-prompt-templates",
            "--no-themes", "--no-context-files", "--no-approve", "--offline",
            "--provider", options["provider"], "--model", options["model"],
            "--tools", ",".join(options["tools"]), "--", "@" + str(request))


def require_pi_writer(root, owner_pid, expected_threshold=3):
    """复核写租约及配置绑定阈值；默认保留历史三轮调用契约。"""
    if type(expected_threshold) is not int or expected_threshold not in {3, 6}:
        raise SupervisorError("Pi 阈值仅接受既有 3 轮或本次获准 6 轮")
    lock = contained_path(root, ".bmad-control/loop-writer.lock")
    info = lock.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SupervisorError("Pi 必须继承现有工作区写租约")
    with Path("/proc/locks").open("rb") as stream:
        payload = stream.read(1024 * 1024 + 1)
    if len(payload) > 1024 * 1024:
        raise SupervisorError("写租约内核证据超预算；不启动 Pi")
    identity = (os.major(info.st_dev), os.minor(info.st_dev), info.st_ino)
    owned = False
    for line in payload.decode("ascii").splitlines():
        fields = line.split()
        if len(fields) < 6 or fields[1:4] != ["FLOCK", "ADVISORY", "WRITE"]:
            continue
        device = fields[5].split(":")
        if len(device) == 3 and fields[4] == str(owner_pid):
            owned |= (int(device[0], 16), int(device[1], 16), int(device[2])) == identity
    after = lock.lstat()
    if not owned or (after.st_dev, after.st_ino) != (info.st_dev, info.st_ino):
        raise SupervisorError("Pi 调用者未持有当前工作区写租约；拒绝并发或脱锁调用")
    raw, _, _ = inputs.read_snapshot(root, ".bmad-control/loop-current.json", 128 * 1024)
    current = json.loads(raw, object_pairs_hook=execution.unique_object)
    if (not isinstance(current, dict) or current.get("status") != "EXECUTING"
            or type(current.get("no_progress_rounds")) is not int
            or current["no_progress_rounds"] != expected_threshold):
        raise SupervisorError(f"Pi 须由现有监督器绑定 {expected_threshold} 轮无进展阈值；不自建重试循环")


def pi_result_from_log(path, expected, workspace):
    """只裁决原生协议生命周期；模型文本及完成口令不参与业务判分。"""
    session = None
    assistant_ended = False
    settled = False
    total = 0
    with path.open("rb") as stream:
        while True:
            line = stream.readline(PI_RECORD_BYTES + 1)
            if not line:
                break
            total += len(line)
            if len(line) > PI_RECORD_BYTES or total > PI_STREAM_BYTES or not line.endswith(b"\n"):
                raise SupervisorError("Pi JSONL 不完整或超过协议读取预算")
            try:
                record = json.loads(line, object_pairs_hook=execution.unique_object)
            except (ValueError, UnicodeError) as exc:
                raise SupervisorError("Pi JSONL 非法；不回显协议或诊断正文") from exc
            if not isinstance(record, dict) or not isinstance(record.get("type"), str) or settled:
                raise SupervisorError("Pi 协议记录非法或结束后仍有活动")
            kind = record["type"]
            if session is None:
                if (kind != "session" or type(record.get("version")) is not int
                        or record["version"] != 3 or record.get("cwd") != str(workspace.resolve())):
                    raise SupervisorError("Pi 新会话头缺失或工作区不匹配")
                try:
                    session = str(uuid.UUID(record["id"]))
                except (KeyError, ValueError, TypeError, AttributeError) as exc:
                    raise SupervisorError("Pi 会话标识非法") from exc
                continue
            if kind == "session":
                raise SupervisorError("Pi 不得在一次调用中切换或恢复会话")
            if kind == "message_end":
                message = record.get("message")
                if not isinstance(message, dict):
                    raise SupervisorError("Pi 消息结束记录不完整")
                if message.get("role") == "assistant":
                    if message.get("stopReason") not in {"stop", "toolUse"}:
                        raise SupervisorError("Pi 模型响应失败、取消或未完整结束")
                    assistant_ended = True
            if (kind == "extension_error"
                    or kind == "auto_retry_end" and record.get("success") is not True
                    or kind == "message_update" and isinstance(record.get("assistantMessageEvent"), dict)
                    and record["assistantMessageEvent"].get("type") == "error"):
                raise SupervisorError("Pi 协议报告运行失败；不能被随后文本覆盖")
            if kind == "agent_settled":
                if record.get("aborted") is not False or not assistant_ended:
                    raise SupervisorError("Pi 取消或缺少完整模型响应；不产生调用通过")
                settled = True
    if session is None or not settled:
        raise SupervisorError("Pi 缺少完整新会话及 settled 生命周期；退出零或完成口令无效")
    return {"schema_version": 1, **expected, "status": "OK", "pi_session_id": session}


def _pi_exec(config, request_relative, owner_pid, transport_relative=None):
    """监督器子进程内 exec 原版 Pi；保留同组清理，不另开进程组。"""
    root = Path.cwd().resolve()
    validate_pi_config(config)
    if owner_pid != os.getppid():
        raise SupervisorError("Pi 启动父进程不匹配")
    require_pi_writer(root, owner_pid, config["pi"]["no_progress_rounds"])
    credential = config["credential_environment"]
    if not os.environ.get(credential, "").strip():
        raise SupervisorError("独立运行时凭据缺失；不读取认证文件")
    request = contained_path(root, request_relative)
    raw, _, _ = inputs.read_snapshot(root, request_relative, context.MAX_STARTUP_BYTES)
    envelope = json.loads(raw, object_pairs_hook=execution.unique_object)
    if envelope.get("protocol") != PROTOCOL:
        raise SupervisorError("Pi 输入协议不匹配")
    executable = Path(config["pi"]["executable"]).resolve(strict=True)
    package = executable.parents[2]
    metadata = json.loads((package / "package.json").read_bytes(), object_pairs_hook=execution.unique_object)
    if (metadata.get("name") != PI_PACKAGE or metadata.get("version") != PI_VERSION
            or metadata.get("repository", {}).get("url") != "git+" + PI_SOURCE + ".git"
            or executable != package / "dist/bundle/cli.js"):
        raise SupervisorError("Pi 安装身份或固定版本变化；不切换运行时")
    private = request.parent / ("pi-config-" + uuid.uuid4().hex)
    private.mkdir(mode=0o700)
    child_key = os.environ[credential]
    if "gateway" in config["pi"]:
        if not isinstance(transport_relative, str):
            raise SupervisorError("Pi 网关运行必须接入任务期计量转发，不允许直连绕过预算")
        transport_raw, transport_path, transport_identity = inputs.read_snapshot(
            root, transport_relative, 4096)
        binding = json.loads(transport_raw, object_pairs_hook=execution.unique_object)
        if (not transport_path.is_relative_to(request.parent)
                or transport_identity["mode"] != 0o600
                or not isinstance(binding, dict)
                or set(binding) != {"schema_version", "base_url", "token", "model", "provider"}
                or type(binding["schema_version"]) is not int or binding["schema_version"] != 1
                or binding["model"] != config["pi"]["model"]
                or binding["provider"] != config["pi"]["provider"]
                or not isinstance(binding["base_url"], str)
                or re.fullmatch(r"http://127\.0\.0\.1:[1-9][0-9]{0,4}/v1", binding["base_url"]) is None
                or not 1 <= int(binding["base_url"].split(":")[2].split("/")[0]) <= 65535
                or not isinstance(binding["token"], str)
                or re.fullmatch(r"[0-9a-f]{64}", binding["token"]) is None):
            raise SupervisorError("Pi 内部转发绑定非法；不回显配置或令牌")
        child_key = binding["token"]
        save_receipt(private / "models.json", {"providers": {
            config["pi"]["provider"]: {
                "baseUrl": binding["base_url"], "api": "openai-completions",
                "apiKey": "${" + credential + "}",
                "models": [{"id": config["pi"]["model"]}],
            }
        }})
        save_receipt(private / "settings.json", {
            "retry": {"enabled": False, "maxRetries": 0,
                      "provider": {"maxRetries": 0}},
            "cacheWarming": "off",
        })
    elif transport_relative is not None:
        raise SupervisorError("未配置网关的 Pi 不接受转发绑定")
    child_environment = {"PATH": "/usr/local/bin:/usr/bin:/bin",
                         "PI_CODING_AGENT_DIR": str(private), "PI_OFFLINE": "1",
                         "PI_SKIP_VERSION_CHECK": "1", "PI_TELEMETRY": "0",
                         credential: child_key}
    # stderr 不混入 JSONL，更不回显提供方可能包含敏感信息的诊断。
    descriptor = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(descriptor, 2)
    finally:
        os.close(descriptor)
    os.execve(config["pi"]["executable"], pi_arguments(config, request), child_environment)


def timeout_dimensions(config, batch_deadline):
    """兼容旧字段，但只将其解释为驱动会话进程时限。

    未接通真实运行时的单次模型请求限时，不以外层进程限时冒充。
    显式 Pi 驱动获准使用至多 360 秒会话；其他驱动仍为 30 秒。
    批次截止时间只能缩短会话，探测及验证工具上限保持不变。
    """
    limit = config["api_timeout_seconds"]
    cap = PI_AGENT_TIMEOUT_SECONDS if config.get("runtime_kind") == "pi-agent" else TIERS["verify"]
    if (type(limit) not in {int, float} or not math.isfinite(limit)
            or not 0.05 <= limit <= cap):
        raise SupervisorError("驱动会话时限非法或超过对应后端上限")
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
           feedback=None, maximum_bytes=context.DEFAULT_STARTUP_BYTES, network_budget=None):
    """启动一个新驱动进程，保存完整回执；任何非零退出严判阻断。"""
    root = environment.contained_path(workspace, ".").resolve()
    is_pi = config.get("runtime_kind") == "pi-agent"
    if is_pi:
        validate_pi_config(config)
        require_pi_writer(root, os.getpid(), config["pi"]["no_progress_rounds"])
        if not os.environ.get(config["credential_environment"], "").strip():
            raise SupervisorError("独立运行时凭据缺失；不启动 Pi 或读取认证文件")
        if contained_path(root, config["driver_file"]).resolve() != Path(__file__).resolve():
            raise SupervisorError("Pi 薄驱动绑定变化；不启动其他驱动")
    use_transport = is_pi and "gateway" in config["pi"]
    if use_transport:
        from bmad_pi_budget import PiNetworkBudget
        if not isinstance(network_budget, PiNetworkBudget):
            raise SupervisorError("Pi 网关调用缺少任务期共享真实请求与数据预算")
    elif network_budget is not None:
        raise SupervisorError("网络预算只能接入明确配置的 Pi 网关路径")
    timeouts = timeout_dimensions(config, deadline)
    if cancel_requested() or time.monotonic() >= timeouts["agent_session_deadline"]:
        raise SupervisorError("调用前已取消或批次预算耗尽；不创建新会话请求")
    session = uuid.uuid4().hex
    startup = json.loads(assembled["payload"])
    if is_pi:
        view = startup["state_projection"].get("view")
        if not isinstance(view, str) or len(view.splitlines()) > 80:
            raise SupervisorError("Pi 必须接收完整的至多 80 行短状态卡")
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
    argv = (ready["environment"]["python"]["path"], "-B",
            str(contained_path(root, config["driver_file"])), "--request-file",
            request.relative_to(root).as_posix())
    if is_pi:
        argv += ("--pi-exec", "--owner-pid", str(os.getpid()), "--pi-config",
                 json.dumps(config, ensure_ascii=True, sort_keys=True))
    transport_record = None
    previous_request_count = network_budget.requests if use_transport else 0

    def execute(arguments, cancellation):
        return run(RunSpec(
            operation="agent-call", argv=arguments,
            workspace=root, runtime_directory=runtime_directory,
            target="agent:" + expected["plan_id"] + ":" + expected["task_id"], tier="verify",
            deadline=timeouts["agent_session_deadline"],
            cancel_requested=cancellation,
            agent_runtime_kind="pi-agent" if is_pi else None,
        ))

    if use_transport:
        from bmad_pi_transport import PiTransport
        binding_path = runtime / ("pi-transport-input-" + session + ".json")
        transport = PiTransport(
            budget=network_budget, credential=os.environ[config["credential_environment"]],
            model=config["pi"]["model"], session_deadline=timeouts["agent_session_deadline"])
        try:
            with transport:
                save_receipt(binding_path, {
                    "schema_version": 1, "base_url": transport.base_url, "token": transport.token,
                    "model": config["pi"]["model"], "provider": config["pi"]["provider"],
                })
                argv += ("--pi-transport-file", binding_path.relative_to(root).as_posix())
                process = execute(argv, lambda: cancel_requested()
                                  or transport.snapshot()["status"] == "BLOCKED")
        finally:
            if binding_path.exists():
                binding_path.unlink()
        transport_record = transport.snapshot()
    else:
        process = execute(argv, cancel_requested)
    reason = process["reason"]
    category = "PROCESS_ERROR"
    data = None
    try:
        log_path = contained_path(root, process["log_path"])
        data = pi_result_from_log(log_path, expected, root) if is_pi else result_from_log(log_path, expected)
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
    if transport_record is not None:
        if not transport_record["cleanup_ok"]:
            reason, category = "Pi 转发清理未知；禁止后续调用", "CLEANUP_UNKNOWN"
        elif (transport_record["status"] != "READY"
              or transport_record["network_budget"]["status"] != "READY"):
            reason, category = "Pi 实际 HTTP 路径失败或预算耗尽；保留成果", "NETWORK_ERROR"
        elif not any(event["outcome"] == "COMPLETE"
                     and event["request_number"] > previous_request_count
                     for event in transport_record["network_budget"]["events"]):
            reason, category = "Pi 缺少实际完整流式请求证据", "NETWORK_ERROR"
    status = "PASS" if process["process_status"] == "PASS" and not reason and data and category == "OK" else "BLOCKED"
    return {"operation": "agent-call", "status": status, "reason": reason,
            "category": category, **expected, "process_receipt": process["receipt_path"],
            "returncode": process["returncode"],
            "cleanup_ok": process["cleanup_ok"] and (
                transport_record is None or transport_record["cleanup_ok"]),
            "transport": transport_record,
            "cancelled": process["cancelled"], "timed_out": process["timed_out"],
            "runtime_kind": config["runtime_kind"], "timeout_dimensions": timeouts,
            "pi_session_id": data.get("pi_session_id") if is_pi and data else None,
            "evidence_boundary": "驱动调用事实；协议结束或退出零不证明业务完成、宿主权限或远程断开；业务须独立验证"}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--pi-exec", action="store_true", required=True)
    parser.add_argument("--request-file", required=True)
    parser.add_argument("--owner-pid", type=int, required=True)
    parser.add_argument("--pi-config", required=True)
    parser.add_argument("--pi-transport-file")
    arguments = parser.parse_args()
    try:
        _pi_exec(json.loads(arguments.pi_config, object_pairs_hook=execution.unique_object),
                 arguments.request_file, arguments.owner_pid, arguments.pi_transport_file)
    except (OSError, ValueError, KeyError, TypeError):
        # 不输出配置、提供方诊断、环境值或协议原文。
        print("Pi 薄驱动启动前提不满足；失败关闭", file=sys.stderr, flush=True)
        sys.exit(1)
