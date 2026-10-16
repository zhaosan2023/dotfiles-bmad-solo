"""有界本地任务期循环；不是已验证的 Roo/Agent 运行时。

明确采用类型化候选计划和 local-verification 后端；复用 bmad-exec 的
单测执行模块与上下文预算。只运行一个请求指定的任务，不写计划进度，
不恢复聊天、不提交或回滚。真实 Agent、新会话和远程断开门禁尚未覆盖。
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

import bmad_context as context
import bmad_context_inputs as context_inputs
import bmad_environment as environment
import bmad_execution as execution
from bmad_supervisor import (
    SupervisorError, bounded_log, contained_path, runtime_path, save_receipt, utc_now,
    workspace_path,
)


CONTROL = ".bmad-control"
CURRENT = CONTROL + "/loop-current.json"
LOCK = CONTROL + "/loop-writer.lock"
BOUNDARY = (
    "仅本地类型化单测循环；不启动真实 Agent、不迁移活动计划；"
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

    def validate(self):
        if self.backend != "local-verification":
            raise SupervisorError("独立 Agent 接口未核验；只接受显式 local-verification")
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
        for relative in (self.plan_file, self.request_file):
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
    payload, _, _ = context_inputs.read_snapshot(root, relative, 16384)
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


def status(workspace):
    root = workspace_path(workspace)
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
        return _start_locked(spec, root)


def _start_locked(spec, root):
    identifier = uuid.uuid4().hex
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

    def cancelled():
        return interrupted or contained_path(root, stop_relative).exists()

    def on_signal(signum, frame):
        nonlocal interrupted
        interrupted = True

    def guard():
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
        # 绑定契约及程序版本；只在接管和轮次阶段边界核验，不逐修改绑定。
        bound = {}
        for relative in (spec.plan_file, spec.request_file):
            _, path, identity = context_inputs.read_snapshot(root, relative, 1024 * 1024)
            bound[path] = identity
        program_root = Path(__file__).resolve().parent
        for path in program_root.glob("*.py"):
            bound[path] = environment.fingerprint(path)
        previous = None
        while record["rounds"] < spec.maximum_rounds:
            if guard():
                break
            if any(environment.fingerprint(path) != identity for path, identity in bound.items()):
                raise SupervisorError("绑定契约或执行程序在阶段边界变化；停止对账")
            assembled = context_inputs.assemble_plan_input(
                workspace=root, plan_file=spec.plan_file, request_file=spec.request_file,
                maximum_bytes=spec.startup_bytes,
            )
            verification = json.loads(assembled["payload"])["task"]["verification"]
            record["task_id"] = assembled["task_id"]
            if guard():
                break
            current = execution.collect_evidence(
                root, verification["directory"], tuple(verification["inputs"]),
            )
            if previous is None:
                previous = current
            record["rounds"] += 1
            budget = context.ToolOutputBudget(
                maximum_bytes=spec.output_bytes,
                maximum_result_bytes=min(spec.output_bytes, context.MAX_TOOL_RESULT_BYTES),
            )
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
            # 转发完整的有界验证反馈，不仅计量路径；失败定位及真实计数不可丢失。
            feedback = {
                "operation": "unit-test", "status": verdict["status"],
                "reason": verdict["reason"], "target": verdict["target"],
                "verdict_path": verdict["verdict_path"],
                "process_receipt": verdict["process_receipt"],
                "returncode": process["returncode"],
                "tests_run": verdict["result"]["tests_run"] if verdict["result"] else None,
                "log_summary": bounded_log(
                    contained_path(root, process["log_path"]), maximum_bytes=4096,
                ),
            }
            budget.consume(feedback)
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
                record.update(status="COMPLETED", reason="仅请求指定任务的本地验证通过；未写计划或证明全计划完成")
                break
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
    record["finished_at"] = utc_now()
    save_receipt(contained_path(root, final_relative), record)
    save_current(root, record)
    return record
