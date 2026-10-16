"""已核验 V5 来源的独立运行候选副本；创建不启动或激活任何程序。

副本留在授权任务工作区，来源租约由调用方持有。运行调用方必须
另管进程、取消及清理生命周期；本模块不解决清理未知时的租约释放，
不提供同账号防篡改保证，也不自动启用候选或热替换已加载程序。
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import uuid

import bmad_context_inputs as inputs
import bmad_execution as execution
import bmad_suite_source as source
from bmad_supervisor import (
    SupervisorError, contained_path, exclusive_file, runtime_path, save_receipt,
    utc_now, workspace_path,
)


PREFIX = ".bmad-control/run-copies"
REQUIRED_RUNTIME = source.REQUIRED | {
    "scripts/bmad-loop.py", "scripts/bmad_loop.py",
    "scripts/bmad_agent_backend.py", "scripts/bmad_plan_adapter.py",
    "scripts/bmad_context.py", "scripts/bmad_context_inputs.py",
    "scripts/bmad_environment.py", "scripts/bmad_execution.py",
    "scripts/bmad_state.py", "scripts/bmad_supervisor.py",
    "scripts/bmad_test_runner.py", "scripts/bmad_run_copy.py",
    "scripts/bmad_task_run.py",
}
FIELDS = {
    "schema_version", "operation", "created_at", "copy_id", "suite_directory",
    "deployment_root", "suite_id", "source_commit", "source_kind",
    "source_dirty", "files", "agent_started", "activation_authorized",
    "evidence_boundary",
}


def copy_locations(root, receipt_file):
    match = re.fullmatch(re.escape(PREFIX) + r"/([0-9a-f]{32})/binding\.json", receipt_file)
    if match is None:
        raise SupervisorError("运行副本须使用任务工作区内明确的实例回执")
    relative = PREFIX + "/" + match.group(1) + "/suite"
    # 加载只读取既有副本；不能用禁止向当前程序根写入的接口验证读取。
    # 创建路径仍由 prepare_run_copy 单独执行 runtime_path 写入边界检查。
    return match.group(1), relative, contained_path(root, relative)


def physical_files(directory):
    """有界枚举，不忽略额外文件、链接、缓存或特殊资产。"""
    found = set()
    pending = [directory]
    directories = 0
    while pending:
        parent = pending.pop()
        if parent.is_symlink() or not parent.is_dir():
            raise SupervisorError("运行副本目录缺失或通过软链接")
        directories += 1
        if directories > source.MAX_FILES:
            raise SupervisorError("运行副本目录数量超预算")
        for path in parent.iterdir():
            if path.is_symlink():
                raise SupervisorError("运行副本不得包含软链接")
            if path.is_dir():
                pending.append(path)
            elif path.is_file():
                found.add(path.relative_to(directory).as_posix())
                if len(found) > source.MAX_FILES:
                    raise SupervisorError("运行副本文件数量超预算")
            else:
                raise SupervisorError("运行副本不得包含特殊资产")
    return found


@dataclass(frozen=True)
class RunCopy:
    workspace: Path
    receipt_file: str
    data: dict
    receipt_identity: dict

    @property
    def suite_root(self):
        return contained_path(self.workspace, self.data["suite_directory"])

    @property
    def entrypoint(self):
        return self.suite_root / "scripts/bmad-loop.py"

    def check(self):
        """阶段边界只读复核；不重新复制、恢复、激活或执行测试。"""
        raw, _, identity = inputs.read_snapshot(
            self.workspace, self.receipt_file, execution.MAX_RECEIPT_BYTES)
        if (identity != self.receipt_identity
                or json.loads(raw, object_pairs_hook=execution.unique_object) != self.data):
            raise SupervisorError("运行副本绑定回执变化；停止而非接受新候选")
        if physical_files(self.suite_root) != set(self.data["files"]):
            raise SupervisorError("运行副本物理文件集合变化；保留修改并阻断")
        budget = [0]
        for relative, expected in sorted(self.data["files"].items()):
            _, observed = source.read_asset(self.suite_root, relative, budget)
            if observed["record"] != expected:
                raise SupervisorError("绑定运行副本变化；禁止热替换：" + relative)
        _, _, final_identity = inputs.read_snapshot(
            self.workspace, self.receipt_file, execution.MAX_RECEIPT_BYTES)
        if final_identity != self.receipt_identity:
            raise SupervisorError("副本核验期间绑定回执变化")

    def require_source(self, binding):
        """核验候选与当前持租约来源精确对应；不接受陈旧或混版副本。

        调用方须持续持有来源读取租约。本检查不获取租约、不启动
        候选，也不以来源一致性代替受管进程的取消和清理证据。
        """
        binding.check()
        self.check()
        snapshot = binding._snapshot
        expected_files = {
            relative: snapshot["files"][source.PLUGIN + "/" + relative]["record"]
            for relative in snapshot["source_files"]
        }
        expected = {
            "deployment_root": str(binding.deployment_root),
            "suite_id": snapshot["suite_id"],
            "source_commit": snapshot["source_commit"],
            "source_kind": snapshot["source_kind"],
            "source_dirty": snapshot["source_dirty"],
            "files": expected_files,
        }
        if any(self.data[key] != value for key, value in expected.items()):
            raise SupervisorError("运行副本与当前来源绑定不一致；不启用陈旧或混版候选")
        binding.check()

    def require_current_program(self, program_directory):
        """运行入口须来自此副本；不将分发源码进程伪称为隔离执行。"""
        self.check()
        if Path(program_directory).resolve(strict=True) != self.suite_root / "scripts":
            raise SupervisorError("当前程序不是绑定运行副本；不得热切换或混用版本")


def load_run_copy(*, workspace, receipt_file):
    root = workspace_path(workspace)
    identifier, relative, _ = copy_locations(root, receipt_file)
    raw, _, identity = inputs.read_snapshot(root, receipt_file, execution.MAX_RECEIPT_BYTES)
    data = json.loads(raw, object_pairs_hook=execution.unique_object)
    if (not isinstance(data, dict) or set(data) != FIELDS
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["operation"] != "prepare-isolated-run-copy"
            or data["copy_id"] != identifier or data["suite_directory"] != relative
            or data["suite_id"] != source.IDENTITY["suite_id"]
            or not isinstance(data["deployment_root"], str)
            or not Path(data["deployment_root"]).is_absolute()
            or not isinstance(data["source_commit"], str)
            or re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", data["source_commit"]) is None
            or data["source_kind"] not in {"worktree", "commit_cache"}
            or type(data["source_dirty"]) is not bool
            or (data["source_kind"] == "commit_cache" and data["source_dirty"])
            or data["agent_started"] is not False
            or data["activation_authorized"] is not False):
        raise SupervisorError("运行候选回执缺失、身份不匹配或越过激活边界")
    source.validate_records(data["files"])
    if not REQUIRED_RUNTIME.issubset(data["files"]):
        raise SupervisorError("运行副本缺少自包含循环及验证资产")
    candidate = RunCopy(root, receipt_file, data, identity)
    candidate.check()
    return candidate


def prepare_run_copy(*, workspace, binding):
    """调用方须持来源读取租约；只创建候选，不执行候选或释放租约。

    拷贝失败保留新实例及诊断，不覆盖任何旧副本。启用与升级另由
    获准运行入口核验停止、清理、候选验证及授权边界。
    """
    root = workspace_path(workspace)
    if root.is_relative_to(binding.suite_root):
        raise SupervisorError("候选运行副本不得写入套件分发源")
    binding.check()
    snapshot = binding._snapshot
    relatives = snapshot["source_files"]
    if not REQUIRED_RUNTIME.issubset(relatives):
        raise SupervisorError("绑定来源缺少自包含循环资产；不混入其他版本补齐")
    identifier = uuid.uuid4().hex
    receipt_file = PREFIX + "/" + identifier + "/binding.json"
    _, relative, _ = copy_locations(root, receipt_file)
    directory = runtime_path(root, relative)
    if directory.is_relative_to(binding.suite_root):
        raise SupervisorError("运行副本与分发源重叠")
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    records = {}
    budget = [0]
    for asset in sorted(relatives):
        payload, observed = source.read_asset(binding.suite_root, asset, budget)
        original = snapshot["files"][source.PLUGIN + "/" + asset]
        if observed != original:
            raise SupervisorError("复制期间绑定来源变化；不接受修改后的候选")
        destination = contained_path(directory, asset)
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor = exclusive_file(destination, observed["record"]["mode"])
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            os.fchmod(stream.fileno(), observed["record"]["mode"])
            stream.flush()
            os.fsync(stream.fileno())
        records[asset] = observed["record"]
    binding.check()
    data = {
        "schema_version": 1, "operation": "prepare-isolated-run-copy",
        "created_at": utc_now(), "copy_id": identifier,
        "suite_directory": relative, "deployment_root": str(binding.deployment_root),
        "suite_id": snapshot["suite_id"], "source_commit": snapshot["source_commit"],
        "source_kind": snapshot["source_kind"], "source_dirty": snapshot["source_dirty"],
        "files": records, "agent_started": False, "activation_authorized": False,
        "evidence_boundary": "已核验分发来源的物理运行候选；不启动、不热替换、不证明清理生命周期、账号隔离或宿主运行能力",
    }
    save_receipt(contained_path(root, receipt_file), data)
    return load_run_copy(workspace=root, receipt_file=receipt_file)
