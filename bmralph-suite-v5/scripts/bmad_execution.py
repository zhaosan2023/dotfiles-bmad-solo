"""已覆盖的类型化单测闭环：环境复核、监督执行、真实结果与证据失效。

不接收 Shell 或任意命令；仅覆盖 native-python unittest。
进程回执与验收回执分开保存，辅助写入成功不覆盖真实失败。
测试目录及显式输入构成证据覆盖范围；不保证隐式导入、同账号
防篡改、恶意测试隔离、竞态专项或尚未实现的容器后端。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import bmad_environment as environment
from bmad_supervisor import (
    RunSpec, SupervisorError, contained_path, run, runtime_path,
    save_receipt, workspace_path,
)
from bmad_test_runner import selected_directory


RUNNER = Path(__file__).resolve().with_name("bmad_test_runner.py")
PREFIX = b"BMAD_TEST_RESULT "
MAX_EVIDENCE_FILES = 4096
MAX_EVIDENCE_BYTES = 128 * 1024 * 1024
MAX_RESULT_BYTES = 65536
MAX_RECEIPT_BYTES = 8 * 1024 * 1024
CONTROLLER_FILES = (
    "bmad_execution.py", "bmad_environment.py", "bmad_supervisor.py",
    "bmad_test_runner.py",
)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SupervisorError(f"验证结果包含重复键：{key}")
        result[key] = value
    return result


def collect_evidence(workspace: Path, directory: str,
                     inputs: tuple[str, ...]) -> dict:
    """程序核验显式范围；目录新增、删除、内容和权限变化均失效。"""
    root = workspace_path(workspace)
    target = selected_directory(root, directory)
    if not isinstance(inputs, tuple) or any(
        not isinstance(item, str) or not item for item in inputs
    ) or len(inputs) > MAX_EVIDENCE_FILES or len(set(inputs)) != len(inputs):
        raise SupervisorError("证据输入必须是数量有界、无重复的显式相对文件路径")
    files = set()
    for path in target.rglob("*"):
        if "__pycache__" in path.relative_to(target).parts:
            continue
        if path.is_symlink():
            raise SupervisorError("测试证据目录不得包含软链接")
        if path.is_file():
            files.add(path)
        elif not path.is_dir():
            raise SupervisorError("测试证据目录存在非普通资产")
        if len(files) > MAX_EVIDENCE_FILES:
            raise SupervisorError("证据文件数量超出预算；未静默丢弃")
    for relative in inputs:
        path = contained_path(root, relative)
        if not path.is_file():
            raise SupervisorError(f"显式证据输入不是现有普通文件：{relative}")
        files.add(path)
    if len(files) > MAX_EVIDENCE_FILES:
        raise SupervisorError("证据文件数量超出预算")
    total = 0
    records = {}
    for path in sorted(files):
        before = path.stat()
        total += before.st_size
        if total > MAX_EVIDENCE_BYTES:
            raise SupervisorError("证据字节数超出预算；未静默丢弃")
        actual = environment.fingerprint(path)
        records[path.relative_to(root).as_posix()] = {
            "sha256": actual["sha256"], "mode": actual["mode"]
        }
    return {"directory": directory, "inputs": list(inputs),
            "files": records, "runner": environment.fingerprint(RUNNER),
            "controller": {
                name: environment.fingerprint(RUNNER.with_name(name))
                for name in CONTROLLER_FILES
            }}


def test_result(log_path: Path, *, workspace: Path, directory: str,
                pattern: str, minimum_tests: int,
                required_tests: tuple[str, ...]) -> dict:
    """读取完整日志而非有界摘要；缺失、重复或异常结果全部失败关闭。"""
    payload = None
    with log_path.open("rb") as stream:
        # 每块有界读取，超长单行不导致无界内存分配。
        at_line_start = True
        while True:
            line = stream.readline(MAX_RESULT_BYTES + 1)
            if not line:
                break
            if at_line_start and line.startswith(PREFIX):
                if len(line) > MAX_RESULT_BYTES or not line.endswith(b"\n"):
                    raise SupervisorError("测试结果行超过预算或不完整")
                if payload is not None:
                    raise SupervisorError("测试结果重复，不能唯一裁决")
                payload = line[len(PREFIX):]
            at_line_start = line.endswith(b"\n")
    if payload is None:
        raise SupervisorError("缺少真实测试结果；进程退出零不能替代测试证据")
    try:
        data = json.loads(payload, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise SupervisorError("真实测试结果无法解析") from exc
    if not isinstance(data, dict):
        raise SupervisorError("测试结果不是对象")
    expected = {
        "workspace": str(workspace), "directory": directory,
        "pattern": pattern, "minimum_tests": minimum_tests,
        "required_tests": list(required_tests),
    }
    for field, value in expected.items():
        if data.get(field) != value:
            raise SupervisorError(f"测试结果与当前目标不匹配：{field}")
    counts = ("discovered", "matched_files", "tests_run", "failures", "errors",
              "skipped", "expected_failures", "unexpected_successes")
    if any(type(data.get(field)) is not int or data[field] < 0 for field in counts):
        raise SupervisorError("测试结果计数无效")
    if (data.get("status") != "PASS"
            or data.get("missing_required_tests") != []
            or data["discovered"] < minimum_tests
            or data["matched_files"] < 1
            or data["tests_run"] != data["discovered"]
            or any(data[field] != 0 for field in counts[3:])):
        raise SupervisorError("真实测试失败、零命中、必需项缺失或跳过")
    return data


def unit_test(*, workspace: Path, environment_file: str, directory: str,
              pattern: str, minimum_tests: int = 1,
              required_tests: tuple[str, ...] = (),
              inputs: tuple[str, ...] = (),
              runtime_directory: str = ".bmad-runtime", deadline=None,
              cancel_requested=None) -> dict:
    """单测类型化操作；返回独立验收结果，不更新计划或建立进度账本。"""
    root = workspace_path(workspace)
    target = selected_directory(root, directory)
    if (not isinstance(pattern, str) or not pattern.endswith(".py")
            or any(char in pattern for char in ("/", "\\", "\x00", "\n", "\r"))
            or len(pattern) > 256):
        raise SupervisorError("必须明确选择单层 Python 测试文件模式")
    if type(minimum_tests) is not int or minimum_tests < 1:
        raise SupervisorError("测试下限必须大于零")
    if (not isinstance(required_tests, tuple) or len(required_tests) > 256
            or any(not isinstance(item, str) or not item.strip()
                   or len(item) > 512 or any(char in item for char in "\x00\n\r")
                   for item in required_tests)
            or len(set(required_tests)) != len(required_tests)):
        raise SupervisorError("必需测试标识非法或重复")
    runtime = runtime_path(root, runtime_directory)
    control = runtime_path(root, ".bmad-control")
    if runtime.is_relative_to(target) or control.is_relative_to(target):
        raise SupervisorError("证据或控制目录不得位于选中测试目录，避免自证回环")
    manifest_path = contained_path(root, environment_file)
    if not manifest_path.is_file():
        raise environment.EnvironmentNotReady("须先显式登记 L0 环境")
    manifest_before = environment.fingerprint(manifest_path)
    ready = environment.check(root, environment_file)
    before = collect_evidence(root, directory, inputs)
    argv = [ready["environment"]["python"]["path"], "-B", str(RUNNER),
            "--workspace", str(root), "--directory", directory,
            "--pattern", pattern, "--minimum-tests", str(minimum_tests)]
    for identifier in required_tests:
        argv.extend(("--required-test", identifier))
    process = run(RunSpec(
        operation="unit-test", argv=tuple(argv), workspace=root,
        runtime_directory=runtime_directory,
        target=f"{directory}:{pattern}", tier="verify",
        deadline=deadline, cancel_requested=cancel_requested,
    ))
    reason = process["reason"]
    result = None
    after = None
    if process["process_status"] == "PASS":
        try:
            result = test_result(
                root / process["log_path"], workspace=root, directory=directory,
                pattern=pattern, minimum_tests=minimum_tests,
                required_tests=required_tests,
            )
            after = collect_evidence(root, directory, inputs)
            if after != before:
                raise SupervisorError("相关实现、测试或运行器变化；本次通过证据失效")
            if environment.fingerprint(manifest_path) != manifest_before:
                raise SupervisorError("环境登记变化；本次通过证据失效")
            checked = environment.check(root, environment_file)
            if checked["environment"] != ready["environment"]:
                raise SupervisorError("验证期间环境变化；本次通过证据失效")
        except (OSError, ValueError, ImportError) as exc:
            reason = str(exc)
    verdict = {
        "schema_version": 1, "operation": "unit-test",
        "status": "PASS" if process["process_status"] == "PASS" and not reason else "BLOCKED",
        "reason": reason, "process_receipt": process["receipt_path"],
        "cwd": str(root), "target": process["target"],
        "result": result, "evidence_before": before,
        "evidence_after": after, "environment": ready["environment"],
        "environment_manifest": {"relative_path": environment_file,
                                 "identity": manifest_before},
        "process_identity": environment.fingerprint(root / process["receipt_path"]),
        "log_identity": environment.fingerprint(root / process["log_path"]),
        "evidence_boundary": (
            "选中测试目录、显式实现输入、运行器与已登记环境；"
            "不覆盖未声明导入、包全部源码、同账号防篡改或宿主隔离"
        ),
    }
    path = root / process["receipt_path"]
    verdict_path = path.with_name(path.stem + ".verdict.json")
    verdict["verdict_path"] = verdict_path.relative_to(root).as_posix()
    # 保存失败抛出异常，不能返回通过；不覆写过程回执或再次执行测试。
    save_receipt(verdict_path, verdict)
    return verdict


def read_receipt(workspace: Path, relative: str) -> tuple[dict, dict]:
    """有界读取现有回执并复核读取期间的版本；不写入或执行测试。"""
    path = contained_path(workspace, relative)
    if not path.is_file() or path.stat().st_size > MAX_RECEIPT_BYTES:
        raise SupervisorError("回执缺失、不是普通文件或超过读取预算")
    before = environment.fingerprint(path)
    with path.open("rb") as stream:
        payload = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(payload) > MAX_RECEIPT_BYTES:
        raise SupervisorError("回执在读取期间超过预算")
    if environment.fingerprint(path) != before:
        raise SupervisorError("回执在读取期间变化")
    try:
        data = json.loads(payload, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise SupervisorError("回执无法解析或包含重复字段") from exc
    if not isinstance(data, dict):
        raise SupervisorError("回执不是对象")
    return data, before


def check_evidence(*, workspace: Path, verdict_file: str) -> dict:
    """查询已保存通过证据是否仍适用；不重跑业务、不保存第二份状态。

    环境复核只探测现有解释器和依赖，不安装。程序身份比较能发现
    当前覆盖范围的变更，但同账号可改写全部证据，不称防篡改保证。
    旧回执缺少必要字段时阻塞，不能补造或继承其通过状态。
    """
    try:
        return _check_evidence(workspace=workspace, verdict_file=verdict_file)
    except (OSError, ValueError, ImportError, KeyError, TypeError) as exc:
        return {
            "operation": "check-evidence", "status": "BLOCKED",
            "verdict_path": verdict_file, "reason": str(exc),
            "business_reexecuted": False,
            "evidence_boundary": "必要证据缺失、损坏或变化；未改写旧回执，不保证同账号防篡改",
        }


def _check_evidence(*, workspace: Path, verdict_file: str) -> dict:
    root = workspace_path(workspace)
    verdict, verdict_identity = read_receipt(root, verdict_file)
    if (type(verdict.get("schema_version")) is not int
            or verdict["schema_version"] != 1
            or verdict.get("operation") != "unit-test"
            or verdict.get("cwd") != str(root)
            or verdict.get("verdict_path") != verdict_file
            or verdict.get("status") != "PASS"
            or verdict.get("reason") != ""):
        raise SupervisorError("回执不是当前工作区的完整单测通过证据")
    before = verdict.get("evidence_before")
    if not isinstance(before, dict) or before != verdict.get("evidence_after"):
        raise SupervisorError("原验证期间的证据不一致或缺失")
    directory = before.get("directory")
    inputs = before.get("inputs")
    result = verdict.get("result")
    manifest = verdict.get("environment_manifest")
    if (not isinstance(directory, str) or not directory
            or not isinstance(inputs, list)
            or not isinstance(result, dict)
            or not isinstance(manifest, dict)):
        raise SupervisorError("回执缺少明确验证目标、输入或环境记录")
    pattern = result.get("pattern")
    minimum = result.get("minimum_tests")
    required = result.get("required_tests")
    if (not isinstance(pattern, str) or not pattern.endswith(".py")
            or any(char in pattern for char in ("/", "\\", "\x00", "\n", "\r"))
            or len(pattern) > 256
            or type(minimum) is not int or minimum < 1
            or not isinstance(required, list) or len(required) > 256
            or any(not isinstance(item, str) or not item.strip()
                   or len(item) > 512 or any(char in item for char in "\x00\n\r")
                   for item in required)
            or len(set(required)) != len(required)):
        raise SupervisorError("保存的测试选择契约非法")
    process_relative = verdict.get("process_receipt")
    if not isinstance(process_relative, str):
        raise SupervisorError("缺少真实进程回执定位")
    process, process_identity = read_receipt(root, process_relative)
    if process_identity != verdict.get("process_identity"):
        raise SupervisorError("真实进程回执变化或缺少身份记录")
    if (type(process.get("schema_version")) is not int
            or process["schema_version"] != 1
            or process.get("operation") != "unit-test"
            or process.get("cwd") != str(root)
            or process.get("receipt_path") != process_relative
            or type(process.get("returncode")) is not int
            or process["returncode"] != 0
            or process.get("process_status") != "PASS"
            or process.get("reason") != ""
            or process.get("cleanup_ok") is not True
            or process.get("timed_out") is not False
            or process.get("cancelled") is not False
            or process.get("timeout_seconds") != 30):
        raise SupervisorError("真实进程回执未满足退出、超时或清理门禁")
    environment_relative = manifest.get("relative_path")
    if not isinstance(environment_relative, str):
        raise SupervisorError("缺少明确环境记录定位")
    environment_path = contained_path(root, environment_relative)
    if environment.fingerprint(environment_path) != manifest.get("identity"):
        raise SupervisorError("环境登记变化或缺少原身份；旧通过证据失效")
    checked = environment.check(root, environment_relative)
    if checked["environment"] != verdict.get("environment"):
        raise SupervisorError("现有环境与验证环境不一致；旧通过证据失效")
    expected_argv = [checked["environment"]["python"]["path"], "-B", str(RUNNER),
                     "--workspace", str(root), "--directory", directory,
                     "--pattern", pattern, "--minimum-tests", str(minimum)]
    for identifier in required:
        expected_argv.extend(("--required-test", identifier))
    target = f"{directory}:{pattern}"
    if (process.get("argv") != expected_argv
            or process.get("target") != target or verdict.get("target") != target):
        raise SupervisorError("保存的命令、目标与验证选择不一致")
    log_relative = process.get("log_path")
    if not isinstance(log_relative, str):
        raise SupervisorError("缺少完整日志定位")
    log_path = contained_path(root, log_relative)
    if environment.fingerprint(log_path) != verdict.get("log_identity"):
        raise SupervisorError("完整日志变化或缺失；旧通过证据失效")
    actual_result = test_result(
        log_path, workspace=root, directory=directory, pattern=pattern,
        minimum_tests=minimum, required_tests=tuple(required),
    )
    if actual_result != result:
        raise SupervisorError("日志中的真实测试结果与验收回执不一致")
    if collect_evidence(root, directory, tuple(inputs)) != before:
        raise SupervisorError("相关实现、测试或控制器变化；旧通过证据失效")
    # 查询结束时复核读过的证据，发现并发替换即阻塞，不覆盖外部修改。
    identities = (
        (contained_path(root, verdict_file), verdict_identity),
        (contained_path(root, process_relative), process_identity),
        (environment_path, manifest["identity"]),
        (log_path, verdict["log_identity"]),
    )
    if any(environment.fingerprint(path) != identity for path, identity in identities):
        raise SupervisorError("查询期间必要证据变化；停止对账")
    return {
        "operation": "check-evidence", "status": "PASS", "reason": "",
        "verdict_path": verdict_file, "process_receipt": process_relative,
        "target": target, "business_reexecuted": False,
        "evidence_boundary": verdict["evidence_boundary"],
    }
