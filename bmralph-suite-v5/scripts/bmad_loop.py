"""有界任务期循环：显式计划适配、独立验证及隔离无头驱动。

默认一次启动只驱动请求指定任务；显式批次仅推进获准集合中的就绪
任务，依据真实证据写回唯一清单，状态卡只读。不恢复聊天、不提交或回滚。真实 Roo
运行时、新会话权限及远程断开门禁尚未覆盖，真实后端失败关闭。
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import fcntl
import json
import math
import os
from pathlib import Path
import signal
import stat
import time
import uuid

import bmad_agent_backend as agent_backend
import bmad_plan_adapter as plan_adapter
import bmad_context as context
import bmad_context_inputs as context_inputs
import bmad_environment as environment
import bmad_execution as execution
import bmad_task_run as task_run
from bmad_supervisor import (
    SupervisorError, bounded_log, contained_path, runtime_path, save_receipt, utc_now,
    workspace_path,
)


CONTROL = ".bmad-control"
CURRENT = CONTROL + "/loop-current.json"
LOCK = CONTROL + "/loop-writer.lock"
BOUNDARY = (
    "本地类型化单测与隔离无头驱动；仅显式授权写回计划任务；"
    "不启动未经实证的真实 Roo，不证明全计划或远程断开完成；"
    "协作锁非账号权限隔离；仅清理监督器的新建同组子进程，"
    "脱离会话、容器与宿主崩溃恢复未覆盖"
)


@dataclass(frozen=True)
class LoopSpec:
    workspace: Path
    plan_file: str
    request_file: str
    backend: str
    maximum_rounds: int
    timeout_seconds: float
    no_progress_rounds: int
    retry_delay: float = 0.1
    startup_bytes: int = context.DEFAULT_STARTUP_BYTES
    output_bytes: int = context.MAX_CUMULATIVE_TOOL_BYTES
    runtime_directory: str = ".bmad-runtime"
    save_progress: bool = False
    backend_config: str | None = None
    batch_file: str | None = None
    maximum_calls: int | None = None
    deployment_root: Path | None = None
    run_copy_file: str | None = None

    maximum_model_requests: int | None = None
    maximum_data_bytes: int | None = None

    def validate(self):
        if (self.deployment_root is None) != (self.run_copy_file is None):
            raise SupervisorError("来源隔离须同时指定合成部署根与运行副本绑定回执")
        if type(self.save_progress) is not bool:
            raise SupervisorError("计划进度写回须为显式布尔授权")
        if self.backend not in {"local-verification", "roo-cli", "headless", "pi-agent"}:
            raise SupervisorError("后端未覆盖；不静默更换引擎")
        if self.backend == "pi-agent":
            if (type(self.maximum_model_requests) is not int
                    or not 1 <= self.maximum_model_requests <= 30
                    or type(self.maximum_data_bytes) is not int
                    or not 256 <= self.maximum_data_bytes <= 15_000_000
                    or type(self.no_progress_rounds) is not int
                    or self.no_progress_rounds != 6):
                raise SupervisorError("后端未覆盖获准预算；Pi 必须明确真实请求、数据上限及 6 轮熔断")
        elif self.maximum_model_requests is not None or self.maximum_data_bytes is not None:
            raise SupervisorError("真实网络预算仅支持明确选择的 pi-agent 后端")
        if self.backend == "local-verification" and self.backend_config is not None:
            raise SupervisorError("本地验证后端不接受 Agent 配置")
        if self.backend != "local-verification" and self.backend_config is None:
            raise SupervisorError("无头后端必须提供明确驱动契约；不猜测 Roo 参数")
        if self.batch_file is not None:
            if not self.save_progress or self.backend == "local-verification":
                raise SupervisorError("批次推进须明确授权进度写回并使用获准无头驱动")
        if self.maximum_calls is not None and (
                type(self.maximum_calls) is not int or not 1 <= self.maximum_calls <= 1000):
            raise SupervisorError("模型驱动调用预算须为 1 至 1000；不推断内部模型调用或费用")
        for value in (self.maximum_rounds, self.no_progress_rounds):
            if type(value) is not int or not 1 <= value <= 1000:
                raise SupervisorError("轮次与无进展阈值须为 1 至 1000 的整数")
        for value, minimum, maximum in (
            (self.timeout_seconds, 0.05, 600), (self.retry_delay, 0, 5),
        ):
            if (type(value) not in {int, float} or not math.isfinite(value)
                    or not minimum <= value <= maximum):
                raise SupervisorError("时间预算非法；任务上限 600 秒，退避上限 5 秒")
        context.positive_budget(self.startup_bytes, context.MAX_STARTUP_BYTES, "启动预算")
        context.positive_budget(self.output_bytes, context.MAX_CUMULATIVE_TOOL_BYTES, "累计结果预算")
        root = workspace_path(self.workspace)
        runtime_path(root, self.runtime_directory)
        runtime_path(root, CONTROL)
        relatives = (self.plan_file, self.request_file)
        if self.backend_config is not None:
            relatives += (self.backend_config,)
        if self.batch_file is not None:
            relatives += (self.batch_file,)
        for relative in relatives:
            path = contained_path(root, relative)
            if path.is_relative_to(runtime_path(root, CONTROL)) or path.is_relative_to(
                runtime_path(root, self.runtime_directory)
            ):
                raise SupervisorError("计划和输入请求不得位于循环控制或证据目录")


def lock_identity(descriptor):
    info = os.fstat(descriptor)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise SupervisorError("工作区写租约必须为单硬链接普通文件")
    return info.st_dev, info.st_ino


@contextmanager
def writer_lease(root):
    directory = runtime_path(root, CONTROL)
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = contained_path(root, LOCK)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    try:
        identity = lock_identity(descriptor)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SupervisorError("已有工作区活动写入者；拒绝并发启动") from exc
        yield
        info = path.lstat()
        if (info.st_dev, info.st_ino) != identity:
            raise SupervisorError("写租约文件被替换；停止对账，不恢复旧锁")
    finally:
        os.close(descriptor)


def writer_active(root):
    path = contained_path(root, LOCK)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        identity = lock_identity(descriptor)
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            active = True
        else:
            active = False
        info = path.lstat()
        if (info.st_dev, info.st_ino) != identity:
            raise SupervisorError("查询期间工作区租约被替换")
        return active
    finally:
        os.close(descriptor)


def read_record(root, relative):
    payload, _, _ = context_inputs.read_snapshot(root, relative, 128 * 1024)
    data = json.loads(payload, object_pairs_hook=execution.unique_object)
    if not isinstance(data, dict):
        raise SupervisorError("循环回执不是对象")
    return data


def save_current(root, data):
    # 只有持工作区写租约的启动者可写；原子替换单一程序侧查询视图。
    target = contained_path(root, CURRENT)
    temporary = target.with_name(".loop-current-" + uuid.uuid4().hex + ".json")
    try:
        save_receipt(temporary, data)
        contained_path(root, CURRENT)
        os.replace(temporary, target)
    finally:
        if temporary.exists():
            temporary.unlink()


def status(workspace, plan_file=None):
    root = workspace_path(workspace)
    if plan_file is not None:
        return plan_adapter.query(workspace=root, plan_file=plan_file)
    if not contained_path(root, CURRENT).exists():
        return {"operation": "status", "status": "IDLE", "reason": "尚无任务期回执",
                "evidence_boundary": BOUNDARY}
    record = read_record(root, CURRENT)
    active = writer_active(root)
    record = dict(record, operation="status", writer_active=active)
    if not active and record.get("status") == "EXECUTING":
        record.update(status="BLOCKED", cleanup_ok=False,
                      reason="启动者已退出但缺最终清理回执；不自动恢复")
    return record


def stop(workspace, wait_seconds=15.0):
    if (type(wait_seconds) not in {int, float} or not math.isfinite(wait_seconds)
            or not 0.05 <= wait_seconds <= 15):
        raise SupervisorError("停止等待须为 0.05 至 15 秒")
    root = workspace_path(workspace)
    current = status(root)
    if not current.get("writer_active"):
        if current.get("cleanup_ok") is True or current["status"] == "IDLE":
            return dict(current, operation="stop")
        raise SupervisorError("没有可确认清理完成的活动任务；不依据陈旧 PID 发信号")
    identifier = current.get("run_id", "")
    if not isinstance(identifier, str) or len(identifier) != 32 or any(
        char not in "0123456789abcdef" for char in identifier
    ):
        raise SupervisorError("循环回执缺少合法运行实例标识")
    flag = contained_path(root, CONTROL + "/loop-stop-" + identifier + ".json")
    try:
        save_receipt(flag, {"run_id": identifier, "requested_at": utc_now()})
    except FileExistsError:
        read_record(root, flag.relative_to(root).as_posix())
    end = time.monotonic() + wait_seconds
    while time.monotonic() < end:
        final_path = contained_path(root, current["final_receipt"])
        if final_path.exists() and not writer_active(root):
            final = read_record(root, current["final_receipt"])
            if final.get("run_id") != identifier or final.get("cleanup_ok") is not True:
                raise SupervisorError("停止结果缺少当前实例的真实清理证据")
            return dict(final, operation="stop", writer_active=False)
        time.sleep(0.01)
    raise SupervisorError("停止等待超时；尚未确认在途进程结束，成果及回执保留")


def retryable_failure(root, process, verification):
    """仅完整执行的普通测试失败允许修复；诊断不产生 PASS 证据。"""
    payload = None
    with contained_path(root, process["log_path"]).open("rb") as stream:
        at_start = True
        while True:
            line = stream.readline(execution.MAX_RESULT_BYTES + 1)
            if not line:
                break
            if at_start and line.startswith(execution.PREFIX):
                if (payload is not None or len(line) > execution.MAX_RESULT_BYTES
                        or not line.endswith(b"\n")):
                    raise SupervisorError("失败诊断重复、超预算或不完整；停止而非重试")
                payload = line[len(execution.PREFIX):]
            at_start = line.endswith(b"\n")
    if payload is None:
        raise SupervisorError("缺少真实失败诊断；不把缺证据当作普通代码失败重试")
    data = json.loads(payload, object_pairs_hook=execution.unique_object)
    expected = {key: verification[key] for key in
                ("directory", "pattern", "minimum_tests", "required_tests")}
    counts = ("discovered", "matched_files", "tests_run", "failures", "errors",
              "skipped", "expected_failures", "unexpected_successes")
    if (not isinstance(data, dict) or data.get("workspace") != str(root)
            or any(data.get(key) != value for key, value in expected.items())
            or any(type(data.get(key)) is not int or data[key] < 0 for key in counts)
            or data.get("status") != "BLOCKED" or data.get("missing_required_tests") != []
            or data["discovered"] < verification["minimum_tests"]
            or data["matched_files"] < 1 or data["tests_run"] != data["discovered"]
            or any(data[key] for key in counts[5:])
            or data["failures"] + data["errors"] < 1
            or type(process.get("returncode")) is not int or process["returncode"] == 0):
        raise SupervisorError("验证未完整执行、必需项缺失或跳过；停止而非修复重试")
    return data


def start(spec):
    spec.validate()
    root = workspace_path(spec.workspace)
    # 套件分发源不得作为编码工作区；仓库根可用于获准的工程验证。
    if root.is_relative_to(Path(__file__).resolve().parents[1]):
        raise SupervisorError("任务工作区不得位于套件分发源")
    with writer_lease(root):
        if contained_path(root, CURRENT).exists():
            previous = read_record(root, CURRENT)
            if previous.get("status") == "EXECUTING" or previous.get("cleanup_ok") is not True:
                raise SupervisorError("前序任务缺少最终清理证据；禁止重启，不继承历史绿灯")
        if spec.deployment_root is not None:
            with task_run.bound_run(
                workspace=root, deployment_root=spec.deployment_root,
                run_copy_file=spec.run_copy_file,
            ) as session:
                return _start_locked(spec, root, session)
        return _start_locked(spec, root)


def _start_locked(spec, root, session=None):
    identifier = session.run_id if session is not None else uuid.uuid4().hex
    runtime = runtime_path(root, spec.runtime_directory)
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    final_relative = spec.runtime_directory + "/loop-" + identifier + ".json"
    stop_relative = CONTROL + "/loop-stop-" + identifier + ".json"
    deadline = time.monotonic() + spec.timeout_seconds
    interrupted = False
    handlers = {}
    record = {
        "schema_version": 1, "operation": "start", "run_id": identifier,
        "status": "EXECUTING", "reason": "", "cwd": str(root),
        "backend": spec.backend, "plan_file": spec.plan_file,
        "request_file": spec.request_file, "started_at": utc_now(),
        "rounds": 0, "no_progress_count": 0, "cleanup_ok": True,
        "maximum_rounds": spec.maximum_rounds, "timeout_seconds": spec.timeout_seconds,
        "no_progress_rounds": spec.no_progress_rounds,
        "final_receipt": final_relative, "last_verdict": None,
        "task_progress_saved": False, "evidence_boundary": BOUNDARY,
    }
    record.update(batch_file=spec.batch_file, agent_calls=0,
                  maximum_calls=spec.maximum_calls or spec.maximum_rounds,
                  completed_tasks=[], model_call_count=None, model_cost=None,
                  model_usage_coverage="UNKNOWN")
    network_budget = None
    budget = context.ToolOutputBudget(
        maximum_bytes=spec.output_bytes,
        maximum_result_bytes=min(spec.output_bytes, context.MAX_TOOL_RESULT_BYTES),
    )

    def cancelled():
        return interrupted or contained_path(root, stop_relative).exists()

    def on_signal(signum, frame):
        nonlocal interrupted
        interrupted = True

    def guard():
        if session is not None:
            session.check()
        if cancelled():
            record.update(status="SUSPENDED", reason="明确停止；未提交成果保留")
            return True
        if time.monotonic() >= deadline:
            record.update(status="BLOCKED", reason="任务时间预算耗尽")
            return True
        return False

    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.signal(sig, on_signal)
        save_current(root, record)
        if session is not None:
            session.begin()
            record.update(
                deployment_root=str(session.root),
                run_copy_file=spec.run_copy_file,
                cleanup_record=session.relative,
                source_commit=session.candidate.data["source_commit"],
                source_kind=session.candidate.data["source_kind"],
                source_dirty=session.candidate.data["source_dirty"],
            )
            save_current(root, record)
        # 绑定契约及程序版本；只在接管和轮次阶段边界核验，不逐修改绑定。
        bound = {}
        for relative in (spec.plan_file, spec.request_file):
            _, path, identity = context_inputs.read_snapshot(root, relative, 1024 * 1024)
            bound[path] = identity
        program_root = Path(__file__).resolve().parent
        for path in program_root.glob("*.py"):
            # 回执裁决器是本轮明确授权的离线实现目标，不由活动控制器导入。
            # 其版本由任务 verification.inputs 核验；不热替换任何运行资产。
            if path.name == "bmad_pi_evidence.py":
                continue
            bound[path] = environment.fingerprint(path)
        backend_config = None
        if spec.backend != "local-verification":
            backend_config, backend_bound = agent_backend.load(root, spec.backend_config, spec.backend)
            bound.update(backend_bound)
            if spec.backend == "pi-agent":
                if (backend_config["runtime_kind"] != "pi-agent"
                        or "gateway" not in backend_config["pi"]
                        or backend_config["pi"]["no_progress_rounds"] != spec.no_progress_rounds):
                    raise SupervisorError("Pi 独立入口必须绑定真实类别、获准网关和同一熔断阈值")
                from bmad_pi_budget import PiNetworkBudget
                network_budget = PiNetworkBudget(
                    maximum_requests=spec.maximum_model_requests,
                    maximum_bytes=spec.maximum_data_bytes,
                    deadline=deadline, cancel_requested=cancelled)
                record.update(network_budget=network_budget.snapshot(),
                              model_usage_coverage="PI_TO_GATEWAY_HTTP_BODY_ONLY",
                              model_cost=None)
                save_current(root, record)
            elif backend_config["runtime_kind"] != "isolated-fixture":
                raise SupervisorError("真实 Roo 运行时尚缺来源、版本、权限和独立认证实证；本轮仅授权隔离驱动演练")
        requests = None
        if spec.batch_file is not None:
            requests, batch_bound = plan_adapter.load_batch(
                workspace=root, plan_file=spec.plan_file, batch_file=spec.batch_file,
                initial_request_file=spec.request_file)
            bound.update(batch_bound)
            for relative in requests.values():
                path = contained_path(root, relative)
                if path.is_relative_to(runtime_path(root, CONTROL)) or path.is_relative_to(runtime):
                    raise SupervisorError("批次请求不得位于控制或证据目录")
        active_request = spec.request_file
        acceptance = {}
        if requests is not None:
            data, _, _ = plan_adapter.state.load_plan(root, spec.plan_file)
            tasks = plan_adapter.state.validate_contract(data)
            for key in requests:
                selection = tasks[key]["verification"]
                directory = selection["directory"]
                if directory not in acceptance:
                    acceptance[directory] = execution.collect_evidence(root, directory, ())
                _, path, identity = context_inputs.read_snapshot(
                    root, selection["environment_file"], context_inputs.MAX_REQUEST_BYTES)
                bound[path] = identity
            initial_task = plan_adapter.select_batch_task(
                workspace=root, plan_file=spec.plan_file, requests=requests)
            if initial_task is None:
                raise SupervisorError("获准批次无未完成任务；不创建多余新会话或继承历史运行事实")
            active_request = requests[initial_task]
        previous = None
        recent_feedback = None
        while record["rounds"] < spec.maximum_rounds:
            if guard():
                break
            if any(environment.fingerprint(path) != identity for path, identity in bound.items()):
                raise SupervisorError("绑定契约或执行程序在阶段边界变化；停止对账")
            assembled = plan_adapter.assemble(
                workspace=root, plan_file=spec.plan_file, request_file=active_request,
                maximum_bytes=spec.startup_bytes,
            )
            verification = json.loads(assembled["payload"])["task"]["verification"]
            record["task_id"] = assembled["task_id"]
            if verification["directory"] not in acceptance:
                acceptance[verification["directory"]] = execution.collect_evidence(
                    root, verification["directory"], ())
            if any(execution.collect_evidence(root, directory, ()) != snapshot
                   for directory, snapshot in acceptance.items()):
                raise SupervisorError("绑定验收资产在阶段边界变化；停止而非重新接受修改后验收")
            if guard():
                break
            current = execution.collect_evidence(
                root, verification["directory"], tuple(verification["inputs"]),
            )
            if previous is None:
                previous = current
            record["rounds"] += 1
            if backend_config is not None:
                if record["agent_calls"] >= record["maximum_calls"]:
                    raise SupervisorError("驱动调用预算耗尽；停止新会话，保留未完成成果")
                record["cleanup_ok"] = False
                record["agent_calls"] += 1
                save_current(root, record)
                invoke_options = {"network_budget": network_budget} if network_budget is not None else {}
                agent = agent_backend.invoke(
                    workspace=root, config=backend_config, assembled=assembled,
                    runtime_directory=spec.runtime_directory, deadline=deadline,
                    cancel_requested=cancelled, feedback=recent_feedback,
                    maximum_bytes=spec.startup_bytes, **invoke_options,
                )
                record["last_agent"] = agent
                if network_budget is not None:
                    record["network_budget"] = network_budget.snapshot()
                    record["model_call_count"] = record["network_budget"]["model_request_attempts"]
                record["cleanup_ok"] = agent["cleanup_ok"]
                budget.consume(agent)
                if not agent["cleanup_ok"]:
                    raise SupervisorError("Agent 清理未确认；禁止验证或推进")
                if agent["cancelled"] and agent.get("category") != "NETWORK_ERROR":
                    record.update(status="SUSPENDED", reason="明确取消 Agent；在途进程已结束，成果保留")
                    break
                if agent["status"] != "PASS":
                    raise SupervisorError(agent["reason"])
                if guard():
                    break
                if any(environment.fingerprint(path) != identity for path, identity in bound.items()):
                    raise SupervisorError("Agent 结束时绑定契约或驱动变化；停止对账")
                if any(execution.collect_evidence(root, directory, ()) != snapshot
                       for directory, snapshot in acceptance.items()):
                    raise SupervisorError("Agent 修改了当前或后续任务的绑定验收资产；保留修改但不验证或推进")
            # 执行或回执保存抛出异常时，不能凭默认值宣称进程已清理。
            record["cleanup_ok"] = False
            verdict = execution.unit_test(
                workspace=root, environment_file=verification["environment_file"],
                directory=verification["directory"], pattern=verification["pattern"],
                minimum_tests=verification["minimum_tests"],
                required_tests=tuple(verification["required_tests"]),
                inputs=tuple(verification["inputs"]), runtime_directory=spec.runtime_directory,
                deadline=deadline, cancel_requested=cancelled,
            )
            record["last_verdict"] = verdict["verdict_path"]
            process, _ = execution.read_receipt(root, verdict["process_receipt"])
            record["cleanup_ok"] = process["cleanup_ok"]
            # 非零退出的验收回执不携带通过结果；从完整日志核验普通
            # 失败诊断后转发真实计数，不补造 PASS 或放宽重试门禁。
            diagnostic = verdict["result"]
            if (verdict["status"] != "PASS" and process["cleanup_ok"]
                    and not process["cancelled"] and not process["timed_out"]):
                diagnostic = retryable_failure(root, process, verification)
            # 转发完整的有界验证反馈，不仅计量路径；失败定位及真实计数不可丢失。
            feedback = {
                "plan_id": json.loads(assembled["payload"])["state_projection"]["plan_id"],
                "task_id": assembled["task_id"],
                "operation": "unit-test", "status": verdict["status"],
                "reason": verdict["reason"], "target": verdict["target"],
                "verdict_path": verdict["verdict_path"],
                "process_receipt": verdict["process_receipt"],
                "returncode": process["returncode"],
                "tests_run": diagnostic["tests_run"] if diagnostic is not None else None,
                "log_summary": bounded_log(
                    contained_path(root, process["log_path"]), maximum_bytes=4096,
                ),
            }
            budget.consume(feedback)
            recent_feedback = feedback
            record["forwarded_bytes"] = budget.accepted_bytes
            if not process["cleanup_ok"]:
                raise SupervisorError("无法确认进程组清理；禁止推进或再次启动验证")
            if guard():
                break
            if any(environment.fingerprint(path) != identity for path, identity in bound.items()):
                raise SupervisorError("轮次结束时绑定契约或执行程序变化；不登记完成")
            if process["cancelled"]:
                record.update(status="SUSPENDED", reason="收到停止信号；在途进程已结束，成果保留")
                break
            if process["timed_out"]:
                raise SupervisorError("验证超时；停止任务循环")
            if verdict["status"] == "PASS":
                checked = execution.check_evidence(workspace=root, verdict_file=verdict["verdict_path"])
                if checked["status"] != "PASS":
                    raise SupervisorError(checked["reason"])
                if spec.save_progress:
                    saved = plan_adapter.complete(
                        workspace=root, plan_file=spec.plan_file,
                        task_id=assembled["task_id"], verdict_file=verdict["verdict_path"],
                        expected_identity=bound[contained_path(root, spec.plan_file)],
                    )
                    bound[contained_path(root, spec.plan_file)] = saved["plan_identity"]
                    record["task_progress_saved"] = True
                record["completed_tasks"].append(assembled["task_id"])
                if requests is not None:
                    next_task = plan_adapter.select_batch_task(
                        workspace=root, plan_file=spec.plan_file, requests=requests)
                    if next_task is not None:
                        active_request = requests[next_task]
                        previous = None
                        recent_feedback = None
                        record["no_progress_count"] = 0
                        record["next_task_id"] = next_task
                        save_current(root, record)
                        continue
                record.update(status="COMPLETED", reason=(
                    "明确获准集合的相关验证通过；不证明 Epic 或全计划完成"
                    if requests is not None else
                    "请求指定任务的相关验证通过；不证明 Epic 或全计划完成"
                ))
                break
            # 普通失败诊断已在转发反馈前核验；不重复读取完整日志。
            current = execution.collect_evidence(
                root, verification["directory"], tuple(verification["inputs"]),
            )
            record["no_progress_count"] = record["no_progress_count"] + 1 if current == previous else 0
            previous = current
            if record["no_progress_count"] >= spec.no_progress_rounds:
                record.update(status="BLOCKED", reason="持续无进展熔断；失败成果保留")
                break
            save_current(root, record)
            end = min(deadline, time.monotonic() + spec.retry_delay)
            while time.monotonic() < end and not cancelled():
                time.sleep(min(0.01, max(0, end - time.monotonic())))
        else:
            record.update(status="BLOCKED", reason="最大轮次预算耗尽；未将失败记为完成")
    except (OSError, ValueError, ImportError, KeyError, TypeError, KeyboardInterrupt) as exc:
        record.update(status="BLOCKED", reason=str(exc)[:512] or "任务期操作被中断")
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    if record["status"] == "EXECUTING":
        record.update(status="BLOCKED", reason="缺少最终裁决")
    projection = plan_adapter.query(workspace=root, plan_file=spec.plan_file)
    if "view" in projection:
        record.update(state_card=projection["view"], state_card_lines=projection["view_lines"],
                      state_card_bytes=projection["view_bytes"],
                      unfinished_count=projection["unfinished_count"])
    else:
        record["state_card_reason"] = str(projection.get("reason", "缺少完整状态视图"))[:512]
        if record["status"] == "COMPLETED":
            record.update(status="BLOCKED", reason="必要短状态卡无法完整生成；成果及回执保留")
    if network_budget is not None:
        record["network_budget"] = network_budget.snapshot()
        record["model_call_count"] = record["network_budget"]["model_request_attempts"]
    record["finished_at"] = utc_now()
    save_receipt(contained_path(root, final_relative), record)
    save_current(root, record)
    if session is not None:
        session.finish(record)
    return record
