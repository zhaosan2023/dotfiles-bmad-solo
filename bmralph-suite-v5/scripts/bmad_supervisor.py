"""V5 前台执行监督原语；类型化入口负责构造获准操作，不接受 Shell。

本模块负责单飞、进程组超时与清理、完整日志和真实退出回执。
它不提供同账号防篡改、恶意测试沙箱或目标宿主权限保证。
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import math
import signal
import subprocess
import time
from typing import Callable, Iterator
import uuid


SUITE_ROOT = Path(__file__).resolve().parents[1]
TIERS = {"probe": 15, "verify": 30, "build": 600}
PI_AGENT_TIMEOUT_SECONDS = 360
SUMMARY_BYTES = 8192
MAX_LOG_BYTES = 64 * 1024 * 1024


class SupervisorError(ValueError):
    """执行前提或证据不满足要求；不得据此推进任务。"""


@dataclass(frozen=True)
class RunSpec:
    """仅由类型化入口构造；不是面向模型的任意命令接口。"""

    operation: str
    argv: tuple[str, ...]
    workspace: Path
    runtime_directory: str
    target: str
    tier: str
    deadline: float | None = None
    cancel_requested: Callable[[], bool] | None = None
    agent_runtime_kind: str | None = None

    @property
    def timeout_seconds(self) -> int:
        return PI_AGENT_TIMEOUT_SECONDS if self.agent_runtime_kind == "pi-agent" else TIERS[self.tier]

    def validate(self) -> None:
        if self.agent_runtime_kind is not None and (
            self.agent_runtime_kind != "pi-agent" or self.operation != "agent-call"
            or self.tier != "verify" or "--pi-exec" not in self.argv
        ):
            raise SupervisorError("360 秒例外仅用于显式 Pi 驱动；不得扩大探测、测试或其他后端时限")
        if self.deadline is not None and (
            type(self.deadline) not in {int, float} or not math.isfinite(self.deadline)
        ):
            raise SupervisorError("任务截止时间必须为有限的单调时钟值")
        if self.cancel_requested is not None and not callable(self.cancel_requested):
            raise SupervisorError("取消入口必须为程序提供的可调用对象")
        if self.operation not in {"unit-test", "race-test", "config-syntax", "check-env", "agent-call"}:
            raise SupervisorError("未实现的类型化操作")
        if self.tier not in TIERS:
            raise SupervisorError("必须选择探测、验证或构建超时级别")
        if not self.argv or not all(
            isinstance(value, str) and value and "\x00" not in value
            for value in self.argv
        ):
            raise SupervisorError("子进程参数必须为非空字符串数组")
        if not isinstance(self.target, str) or not self.target.strip():
            raise SupervisorError("缺少真实验证目标")
        if "\n" in self.target or "\r" in self.target:
            raise SupervisorError("验证目标不得包含换行")
        if self.operation == "check-env" and self.tier != "probe":
            raise SupervisorError("环境探测必须使用探测级超时")
        if self.operation != "check-env" and self.tier != "verify":
            raise SupervisorError("当前测试和配置操作仅覆盖验证级超时")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def workspace_path(workspace: Path) -> Path:
    original = workspace.absolute()
    if original.is_symlink():
        raise SupervisorError("任务工作区不得是软链接")
    root = original.resolve(strict=True)
    if not root.is_dir():
        raise SupervisorError("任务工作区必须是现有目录")
    return root


def contained_path(workspace: Path, relative: str) -> Path:
    if not isinstance(relative, str) or not relative or "\x00" in relative:
        raise SupervisorError("工作区路径必须是非空字符串")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise SupervisorError("路径必须位于任务工作区内")
    root = workspace_path(workspace)
    candidate = root
    for component in path.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise SupervisorError("工作区路径不得通过软链接")
    if not candidate.resolve().is_relative_to(root):
        raise SupervisorError("路径越过任务工作区")
    return candidate


def runtime_path(workspace: Path, relative: str) -> Path:
    root = workspace_path(workspace)
    directory = contained_path(root, relative)
    if directory == root:
        raise SupervisorError("运行证据必须使用独立子目录")
    # 所有版本套件都是分发源，不能把任务日志混入其中。
    source_names = {"bmad-suite", "bmad-suite-v3", "bmad-suite-v4", "bmralph-suite-v5"}
    parts = directory.relative_to(root).parts
    if directory.is_relative_to(SUITE_ROOT) or any(part in source_names for part in parts):
        raise SupervisorError("任务日志和回执不得写入套件分发源")
    if directory.exists() and not directory.is_dir():
        raise SupervisorError("运行证据目录不是目录")
    return directory


def exclusive_file(path: Path, mode: int = 0o600) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    return os.open(path, flags, mode)


def save_receipt(path: Path, data: dict) -> None:
    """一次性保存回执；不覆盖旧证据，不触发业务重测。"""
    payload = (json.dumps(data, ensure_ascii=True, sort_keys=True) + "\n").encode("utf-8")
    with os.fdopen(exclusive_file(path), "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


@contextmanager
def verification_lock(directory: Path) -> Iterator[None]:
    """单工作区验证锁；仅对遵循此入口的进程生效。"""
    path = directory / "verification.lock"
    flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise SupervisorError("已有验证在途；拒绝并发执行") from exc
        yield
    finally:
        os.close(descriptor)


def group_exists(group: int) -> bool:
    try:
        os.killpg(group, 0)
    except ProcessLookupError:
        return False
    return True


def stop_group(process: subprocess.Popen, grace_seconds: float = 1.0) -> bool:
    """终止整个新建进程组并等待；无法确认组消失时返回失败。"""
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            pass
        end = time.monotonic() + grace_seconds
        while time.monotonic() < end:
            process.poll()
            if not group_exists(process.pid):
                process.wait()
                return True
            time.sleep(0.01)
    process.poll()
    return not group_exists(process.pid)


def bounded_log(path: Path, maximum_bytes: int = SUMMARY_BYTES) -> dict:
    """完整日志不默认摄入；返回显式截断的字节有界视图。"""
    if type(maximum_bytes) is not int or maximum_bytes < 256:
        raise SupervisorError("摘要字节预算至少为 256")
    size = path.stat().st_size
    marker = b"\n[TRUNCATED: complete log retained at receipt log_path]\n"
    with path.open("rb") as stream:
        if size <= maximum_bytes:
            content = stream.read(maximum_bytes)
            truncated = False
        else:
            available = maximum_bytes - len(marker)
            head_bytes = available // 3
            tail_bytes = available - head_bytes
            head = stream.read(head_bytes)
            stream.seek(-tail_bytes, os.SEEK_END)
            content = head + marker + stream.read(tail_bytes)
            truncated = True
    # 解码使用忽略半截 UTF-8，避免替换字符扩大预算；原始日志完整保留。
    text = content.decode("utf-8", errors="ignore")
    return {"text": text, "truncated": truncated,
            "log_bytes": size, "summary_bytes": len(text.encode("utf-8"))}


def run(spec: RunSpec) -> dict:
    """执行并生成事实回执；退出零只表示进程成功，不裁决测试命中。"""
    spec.validate()
    root = workspace_path(spec.workspace)
    directory = runtime_path(root, spec.runtime_directory)
    # 锁的位置由工作区唯一确定，不随调用者选择的证据目录改变。
    control_directory = runtime_path(root, ".bmad-control")
    control_directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    runtime_path(root, ".bmad-control")
    with verification_lock(control_directory):
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        # 创建后复核路径；不宣称对同账号并发目录替换提供原子隔离。
        runtime_path(root, spec.runtime_directory)
        return _run_locked(spec, root, directory)


def _run_locked(spec: RunSpec, root: Path, directory: Path) -> dict:
    identifier = "run-" + uuid.uuid4().hex
    log_path = directory / (identifier + ".log")
    receipt_path = directory / (identifier + ".json")
    started = utc_now()
    begin = time.monotonic()
    reason = ""
    timed_out = False
    cancelled = False
    cleanup_ok = True
    process = None
    returncode = None
    previous_handlers = {}

    def interrupted(signum, frame):
        raise InterruptedError(f"收到取消信号 {signum}")

    try:
        # 只有主线程可以设置处理器；其他调用线程保持现有信号策略。
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                previous_handlers[sig] = signal.signal(sig, interrupted)
            except ValueError:
                break
        with os.fdopen(exclusive_file(log_path), "wb", buffering=0) as log:
            environment = dict(os.environ)
            environment.update(
                PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
                GIT_TERMINAL_PROMPT="0", PIP_NO_INPUT="1",
                PIP_DISABLE_PIP_VERSION_CHECK="1",
            )
            process = subprocess.Popen(
                list(spec.argv), cwd=root, stdin=subprocess.DEVNULL,
                stdout=log, stderr=subprocess.STDOUT, env=environment,
                start_new_session=True, close_fds=True,
            )
            deadline = begin + spec.timeout_seconds
            if spec.deadline is not None:
                deadline = min(deadline, spec.deadline)
            while process.poll() is None:
                if spec.cancel_requested is not None and spec.cancel_requested():
                    cancelled = True
                    reason = "任务期安全停止请求"
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    reason = "进程级超时"
                    break
                if os.fstat(log.fileno()).st_size > MAX_LOG_BYTES:
                    reason = "完整日志超过保留容量；明确停止而非丢弃证据"
                    break
                time.sleep(0.01)
            if reason:
                cleanup_ok = stop_group(process)
            else:
                process.wait()
                if group_exists(process.pid):
                    reason = "主进程退出但存在在途子进程"
                    cleanup_ok = stop_group(process)
            returncode = process.poll()
            if os.fstat(log.fileno()).st_size > MAX_LOG_BYTES and not reason:
                reason = "完整日志超过保留容量"
            os.fsync(log.fileno())
    except (InterruptedError, KeyboardInterrupt) as exc:
        cancelled = True
        reason = str(exc) or "执行被取消"
        if process is not None:
            cleanup_ok = stop_group(process)
            returncode = process.poll()
    except OSError as exc:
        reason = f"执行或日志写入失败：{exc}"
        if process is not None:
            cleanup_ok = stop_group(process)
            returncode = process.poll()
    finally:
        for sig, handler in previous_handlers.items():
            signal.signal(sig, handler)
    if not cleanup_ok:
        reason = (reason + "；" if reason else "") + "无法确认进程组清理完成"
    if returncode != 0 and not reason:
        reason = f"真实子进程退出码 {returncode}"
    try:
        summary = bounded_log(log_path)
    except OSError as exc:
        summary = {"text": "", "truncated": False,
                   "log_bytes": None, "summary_bytes": 0}
        reason = (reason + "；" if reason else "") + f"缺少完整日志证据：{exc}"
    receipt = {
        "schema_version": 1, "run_id": identifier,
        "operation": spec.operation, "target": spec.target,
        "argv": list(spec.argv), "cwd": str(root),
        "started_at": started, "finished_at": utc_now(),
        "elapsed_seconds": round(time.monotonic() - begin, 6),
        "timeout_seconds": spec.timeout_seconds,
        "agent_runtime_kind": spec.agent_runtime_kind,
        "returncode": returncode, "timed_out": timed_out,
        "cancelled": cancelled, "cleanup_ok": cleanup_ok,
        "process_status": "PASS" if returncode == 0 and not reason else "BLOCKED",
        "reason": reason, "log_path": log_path.relative_to(root).as_posix(),
        "receipt_path": receipt_path.relative_to(root).as_posix(),
        "summary": summary,
        "evidence_boundary": "进程退出事实；测试命中及验收由类型化入口另判，同账号文件不保证防篡改",
    }
    save_receipt(receipt_path, receipt)
    return receipt
