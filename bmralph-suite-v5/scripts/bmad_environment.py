"""L0 已准备环境登记与 L1 只读复核；不安装依赖、不隐式启动容器。

当前仅覆盖显式选择的 native-python 后端。登记不是环境准备成功的
替代证据，也不证明容器、GCC/musl、网络隔离或账号权限隔离。
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

from bmad_supervisor import SupervisorError, contained_path, runtime_path, save_receipt


SCHEMA_VERSION = 1
BACKEND = "native-python"
PROBE_TIMEOUT = 15
NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
PROBE_CODE = (
    "import importlib.metadata as m, json, platform, sys; "
    "names=json.loads(sys.argv[1]); "
    "print(json.dumps({'version':list(sys.version_info[:3]),"
    "'implementation':platform.python_implementation(),"
    "'platform':platform.platform(),"
    "'dependencies':{name:m.version(name) for name in names}},sort_keys=True))"
)


class EnvironmentNotReady(SupervisorError):
    """缺少依赖、身份变化或缺少 L0 登记；L1 必须阻塞。"""


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EnvironmentNotReady(f"环境记录重复键：{key}")
        result[key] = value
    return result


def fingerprint(path: Path) -> dict:
    """程序自动核验文件身份；不要求模型手工同步指纹。"""
    actual = path.resolve(strict=True)
    if not actual.is_file():
        raise EnvironmentNotReady(f"环境资产不是普通文件：{path}")
    before = actual.stat()
    digest = hashlib.sha256()
    with actual.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    after = actual.stat()
    identity = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)
    if identity(before) != identity(after):
        raise EnvironmentNotReady(f"环境资产在探测中变化：{path}")
    return {"path": str(actual), "sha256": digest.hexdigest(),
            "mode": after.st_mode & 0o777}


def validate_names(values, label: str) -> tuple[str, ...]:
    if not isinstance(values, (tuple, list)) or any(
        not isinstance(value, str) or not NAME_PATTERN.fullmatch(value)
        for value in values
    ):
        raise EnvironmentNotReady(f"{label}必须是明确的名称列表")
    if len(values) > 64 or len(set(values)) != len(values):
        raise EnvironmentNotReady(f"{label}超出数量限制或包含重复项")
    return tuple(values)


def probe(python: str, dependencies=(), executables=()) -> dict:
    """串行、限时、封闭输入地探测现有环境；没有安装或联网分支。"""
    if not isinstance(python, str) or not python or "\x00" in python:
        raise EnvironmentNotReady("必须显式指定现有 Python 解释器")
    dependencies = validate_names(dependencies, "依赖")
    executables = validate_names(executables, "工具")
    location = shutil.which(python)
    if location is None:
        raise EnvironmentNotReady(f"解释器未发现：{python}")
    interpreter = fingerprint(Path(location))
    environment = dict(os.environ)
    environment.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1",
                       PIP_NO_INPUT="1", PIP_DISABLE_PIP_VERSION_CHECK="1")
    try:
        result = subprocess.run(
            [interpreter["path"], "-I", "-B", "-c", PROBE_CODE,
             json.dumps(dependencies)],
            stdin=subprocess.DEVNULL, capture_output=True, text=True,
            env=environment, timeout=PROBE_TIMEOUT, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EnvironmentNotReady(f"环境探测失败或超时：{exc}") from exc
    if result.returncode != 0:
        # 不回显任意环境错误正文，避免无界输出或凭据泄漏。
        raise EnvironmentNotReady(
            f"环境未就绪：解释器或明确依赖探测退出 {result.returncode}；未安装依赖"
        )
    try:
        details = json.loads(result.stdout, object_pairs_hook=unique_object)
    except (ValueError, TypeError) as exc:
        raise EnvironmentNotReady("解释器环境探测结果非法") from exc
    if (not isinstance(details, dict)
            or set(details) != {"version", "implementation", "platform", "dependencies"}
            or not isinstance(details["version"], list)
            or len(details["version"]) != 3
            or any(type(part) is not int for part in details["version"])
            or not isinstance(details["implementation"], str)
            or not isinstance(details["platform"], str)
            or not isinstance(details["dependencies"], dict)
            or set(details["dependencies"]) != set(dependencies)
            or any(not isinstance(value, str) or not value
                   for value in details["dependencies"].values())):
        raise EnvironmentNotReady("解释器环境探测字段不满足契约")
    if tuple(details["version"]) < (3, 10, 0):
        raise EnvironmentNotReady("当前 V5 原语要求 Python 3.10 或更高版本")
    tools = {}
    for name in executables:
        executable = shutil.which(name)
        if executable is None:
            raise EnvironmentNotReady(f"环境未就绪：工具未发现 {name}；未安装工具")
        tools[name] = fingerprint(Path(executable))
    # 前后核验解释器，避免将探测期间的替换登记为稳定环境。
    if fingerprint(Path(location)) != interpreter:
        raise EnvironmentNotReady("解释器在环境探测期间变化")
    return {"schema_version": SCHEMA_VERSION, "backend": BACKEND,
            "python": interpreter, "details": details, "executables": tools,
            "evidence_boundary": (
                "现有本机解释器、包版本及明确工具的身份登记；"
                "不证明包全部源码未变、容器或系统权限隔离"
            )}


def validate_manifest(data: dict) -> None:
    required = {"schema_version", "backend", "python", "details",
                "executables", "evidence_boundary"}
    if (not isinstance(data, dict) or set(data) != required
            or type(data["schema_version"]) is not int
            or data["schema_version"] != SCHEMA_VERSION
            or data["backend"] != BACKEND):
        raise EnvironmentNotReady("环境记录无效或后端尚未实现；不回退到其他环境")
    python = data["python"]
    details = data["details"]
    if (not isinstance(python, dict)
            or set(python) != {"path", "sha256", "mode"}
            or not isinstance(python["path"], str)
            or not Path(python["path"]).is_absolute()
            or not isinstance(details, dict)
            or set(details) != {"version", "implementation", "platform", "dependencies"}
            or not isinstance(details["dependencies"], dict)
            or not isinstance(data["executables"], dict)
            or not isinstance(data["evidence_boundary"], str)):
        raise EnvironmentNotReady("环境记录结构损坏")
    validate_names(list(details["dependencies"]), "依赖")
    validate_names(list(data["executables"]), "工具")


def register(workspace: Path, relative: str, python: str,
             dependencies=(), executables=()) -> dict:
    """L0 显式登记现有环境一次；目标已存在即拒绝，不覆盖旧登记。"""
    path = contained_path(workspace, relative)
    if path == workspace.resolve():
        raise EnvironmentNotReady("环境记录必须是独立文件")
    runtime_path(workspace, str(Path(relative).parent))
    if path.exists() or path.is_symlink():
        raise EnvironmentNotReady("环境记录已存在；拒绝覆盖，变化后使用新的明确登记")
    data = probe(python, dependencies, executables)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    contained_path(workspace, relative)
    save_receipt(path, data)
    return data


def check(workspace: Path, relative: str) -> dict:
    """L1 只读复核；缺依赖或环境变化明确阻塞，不写入、不隐式修复。"""
    path = contained_path(workspace, relative)
    if not path.is_file() or path.stat().st_size > 65536:
        raise EnvironmentNotReady("环境记录缺失或超出预算；须先显式完成 L0 登记")
    original = path.read_bytes()
    try:
        expected = json.loads(original, object_pairs_hook=unique_object)
    except (ValueError, UnicodeError) as exc:
        raise EnvironmentNotReady("环境记录无法解析") from exc
    validate_manifest(expected)
    actual = probe(expected["python"]["path"],
                   tuple(expected["details"]["dependencies"]),
                   tuple(expected["executables"]))
    if actual != expected:
        raise EnvironmentNotReady("环境身份发生变化；受影响旧证据失效，须明确重新登记")
    if path.read_bytes() != original:
        raise EnvironmentNotReady("环境记录在复核期间变化")
    return {"status": "PASS", "backend": BACKEND,
            "environment": expected, "installation_count": 0,
            "evidence_boundary": expected["evidence_boundary"]}
