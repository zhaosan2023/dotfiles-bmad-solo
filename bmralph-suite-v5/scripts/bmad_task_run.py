"""本阶段的隔离运行边界与持久清理记录；不启动或恢复 Agent。

仅写授权工作区内的合成部署根。共享租约释放后，未完成记录仍由
公共部署入口阻断；记录不是任务进度，也不提供同账号防篡改保证。
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import uuid

import bmad_context_inputs as inputs
import bmad_execution as execution
import bmad_run_copy as copies
import bmad_suite_source as source
from bmad_supervisor import (
    SupervisorError, contained_path, save_receipt, workspace_path,
)

RECORD_DIRECTORY = ".bmad-solo-deployment/task-runs"
MAX_RECORD_BYTES = 16384
MAX_RECORDS = 128
FIELDS = {"schema_version", "run_id", "workspace", "run_copy_file",
          "status", "cleanup_ok", "final_receipt"}
STATES = {"EXECUTING", "BLOCKED", "SUSPENDED", "COMPLETED"}


def entries(root):
    directory = contained_path(root, RECORD_DIRECTORY)
    try:
        info = directory.lstat()
    except FileNotFoundError:
        return []
    if not stat.S_ISDIR(info.st_mode):
        raise SupervisorError("任务清理记录路径不是物理目录；停止对账")
    names = []
    with os.scandir(directory) as iterator:
        for entry in iterator:
            names.append(entry.name)
            if len(names) > MAX_RECORDS:
                raise SupervisorError("任务清理记录超过读取预算；停止对账")
            if re.fullmatch(r"[0-9a-f]{32}\.json", entry.name) is None:
                raise SupervisorError("任务清理目录包含未知资产；保留并停止对账")
    return sorted(names)


def read_record(root, relative):
    raw, _, identity = inputs.read_snapshot(root, relative, MAX_RECORD_BYTES)
    data = json.loads(raw, object_pairs_hook=execution.unique_object)
    name = Path(relative).name
    if (not isinstance(data, dict) or set(data) != FIELDS
            or type(data["schema_version"]) is not int or data["schema_version"] != 1
            or data["run_id"] != name[:-5]
            or not isinstance(data["workspace"], str)
            or not Path(data["workspace"]).is_absolute()
            or not isinstance(data["run_copy_file"], str)
            or re.fullmatch(r"\.bmad-control/run-copies/[0-9a-f]{32}/binding\.json",
                            data["run_copy_file"]) is None
            or not isinstance(data["status"], str) or data["status"] not in STATES
            or type(data["cleanup_ok"]) is not bool):
        raise SupervisorError("任务清理记录契约非法；停止对账")
    receipt = data["final_receipt"]
    if receipt is not None:
        source.relative_path(receipt)
    return data, identity


def require_clean_records(root):
    names = entries(root)
    observed = {}
    for name in names:
        relative = RECORD_DIRECTORY + "/" + name
        data, identity = read_record(root, relative)
        if (data["status"] == "EXECUTING" or data["cleanup_ok"] is not True
                or data["final_receipt"] is None):
            raise SupervisorError("前序任务清理未知或尚未结束；禁止启动，不恢复旧进程")
        observed[relative] = (data, identity)
    if entries(root) != names:
        raise SupervisorError("核验期间任务清理记录集合变化；停止对账")
    for relative, expected in observed.items():
        if read_record(root, relative) != expected:
            raise SupervisorError("核验期间任务清理记录变化；停止对账")
    return names


def sync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


class TaskRun:
    def __init__(self, workspace, binding, candidate):
        self.workspace = workspace
        self.binding = binding
        self.candidate = candidate
        self.root = binding.deployment_root
        self.run_id = uuid.uuid4().hex
        self.relative = RECORD_DIRECTORY + "/" + self.run_id + ".json"
        self.expected = None

    def check(self):
        self.candidate.require_source(self.binding)
        self.candidate.require_current_program(Path(__file__).resolve().parent)
        if self.expected is not None:
            if read_record(self.root, self.relative) != self.expected:
                raise SupervisorError("当前任务清理记录变化；保留修改并停止对账")

    def begin(self):
        self.check()
        names = require_clean_records(self.root)
        if len(names) >= MAX_RECORDS:
            raise SupervisorError("任务清理记录容量耗尽；不删除历史证据或启动新调用")
        directory = contained_path(self.root, RECORD_DIRECTORY)
        directory.mkdir(mode=0o700, exist_ok=True)
        contained_path(self.root, RECORD_DIRECTORY)
        sync_directory(directory.parent)
        data = {
            "schema_version": 1, "run_id": self.run_id,
            "workspace": str(self.workspace),
            "run_copy_file": self.candidate.receipt_file,
            "status": "EXECUTING", "cleanup_ok": False, "final_receipt": None,
        }
        save_receipt(contained_path(self.root, self.relative), data)
        sync_directory(directory)
        self.expected = read_record(self.root, self.relative)
        if self.expected[0] != data:
            raise SupervisorError("启动前任务清理记录不一致；不调用 Agent")
        self.check()

    def finish(self, record):
        """仅在最终回执已保存且全部受管调用已返回后记录结果。

        失败、未知清理或写入异常均保留阻断；不会探测旧 PID、删除
        记录、恢复进程或将终态名称当作业务通过。
        """
        if self.expected is None:
            raise SupervisorError("任务尚无持久启动记录；不能确认清理")
        if (record.get("run_id") != self.run_id
                or record.get("status") not in STATES
                or record["status"] == "EXECUTING"
                or type(record.get("cleanup_ok")) is not bool):
            raise SupervisorError("最终回执与持久任务实例不匹配")
        final, _, _ = inputs.read_snapshot(
            self.workspace, record["final_receipt"], execution.MAX_RECEIPT_BYTES)
        if json.loads(final, object_pairs_hook=execution.unique_object) != record:
            raise SupervisorError("最终循环回执不一致；保留清理未知阻断")
        self.check()
        data = dict(self.expected[0], status=record["status"],
                    cleanup_ok=record["cleanup_ok"], final_receipt=record["final_receipt"])
        target = contained_path(self.root, self.relative)
        temporary = target.with_name(".pending-" + uuid.uuid4().hex + ".json")
        # 临时文件或目录同步失败均保留诊断并阻断，不自动清理未知记录。
        save_receipt(temporary, data)
        self.check()
        contained_path(self.root, self.relative)
        os.replace(temporary, target)
        sync_directory(target.parent)
        self.expected = read_record(self.root, self.relative)
        if self.expected[0] != data:
            raise SupervisorError("任务清理终态保存不一致；停止对账")


@contextmanager
def bound_run(*, workspace, deployment_root, run_copy_file):
    root = workspace_path(workspace)
    deployment = workspace_path(deployment_root)
    if not deployment.is_relative_to(root):
        raise SupervisorError("本阶段只允许授权工作区内合成部署根；不写真实宿主状态")
    if root.is_relative_to(deployment / source.PLUGIN):
        raise SupervisorError("任务工作区不得位于套件分发源")
    with source.bound_suite(deployment_root) as binding:
        candidate = copies.load_run_copy(workspace=root, receipt_file=run_copy_file)
        candidate.require_source(binding)
        candidate.require_current_program(Path(__file__).resolve().parent)
        require_clean_records(binding.deployment_root)
        yield TaskRun(root, binding, candidate)
