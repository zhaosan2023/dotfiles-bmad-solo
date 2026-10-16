"""活动计划薄适配：就绪查询、输入组装、基于真实证据的单任务写回。

仅操作显式采用 bmad-tasks 的获准计划，不解析散文为执行命令、不继承
历史绿灯。任务清单唯一；状态卡只读。协作锁不提供同账号权限隔离。
"""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import uuid

import bmad_context_inputs as inputs
import bmad_state as state
from bmad_supervisor import SupervisorError, contained_path


def query(*, workspace: Path, plan_file: str):
    """完整保留清单任务；超过 80 行或字节上限即阻塞。"""
    return state.render_state(workspace=workspace, plan_file=plan_file)


def assemble(*, workspace: Path, plan_file: str, request_file: str, maximum_bytes: int):
    return inputs.assemble_plan_input(
        workspace=workspace, plan_file=plan_file, request_file=request_file,
        maximum_bytes=maximum_bytes,
    )


def complete(*, workspace: Path, plan_file: str, task_id: str,
             verdict_file: str, expected_identity: dict):
    """调用方须持工作区写租约；仅精确匹配的当前 PASS 证据可写回。

    保存前复核绑定源版本，原子替换只修改唯一任务块，保存后复核。
    不重跑业务测试、不改 frontmatter 完成状态、不触碰其他任务或 ADR。
    同账号在最终检查与替换间写入仍有竞态，不宣称文件系统 CAS。
    """
    root = state.workspace_path(workspace)
    data, path, identity = state.load_plan(root, plan_file)
    if identity != expected_identity:
        raise SupervisorError("完成写回前绑定计划变化；保留外部修改，停止对账")
    tasks = state.validate_contract(data)
    if task_id not in tasks:
        raise SupervisorError("完成目标不属于绑定计划")
    projection = query(workspace=root, plan_file=plan_file)
    if projection["status"] != "READY" or task_id not in projection["ready_tasks"]:
        raise SupervisorError("完成目标不是当前就绪任务；不恢复阻塞或暂停项")
    candidate = copy.deepcopy(tasks[task_id])
    candidate.update(status="COMPLETED", verdict_file=verdict_file)
    state.completed_evidence(root, candidate)
    raw, _, source_identity = inputs.read_snapshot(root, plan_file, state.MAX_PLAN_BYTES)
    if source_identity != identity:
        raise SupervisorError("证据核验期间计划变化；未写回")
    content = raw.decode("utf-8")
    block = list(state.TASK_BLOCK.finditer(content))[0]
    updated = copy.deepcopy(data)
    for task in updated["tasks"]:
        if task["task_id"] == task_id:
            task.update(status="COMPLETED", verdict_file=verdict_file)
    state.validate_contract(updated)
    replacement = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    output = (content[:block.start(1)] + replacement + content[block.end(1):]).encode("utf-8")
    if len(output) > state.MAX_PLAN_BYTES:
        raise SupervisorError("计划保存超过读取预算；原文件保留")
    temporary = path.with_name(".bmad-plan-" + uuid.uuid4().hex + ".tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(output)
            os.fchmod(stream.fileno(), int(identity["mode"]))
            stream.flush()
            os.fsync(stream.fileno())
        # 再次复核真实回执；保存状态不是业务重测。
        state.completed_evidence(root, candidate)
        if state.execution.environment.fingerprint(path) != identity:
            raise SupervisorError("保存前源计划变化；未覆盖外部修改")
        contained_path(root, plan_file)
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        saved, _, final_identity = state.load_plan(root, plan_file)
        if saved != updated or path.read_bytes() != output:
            raise SupervisorError("保存后计划版本不符；停止对账，不恢复旧文件")
        return {"task_id": task_id, "verdict_file": verdict_file,
                "plan_identity": final_identity, "task_progress_saved": True,
                "business_reexecuted": False}
    finally:
        if temporary.exists():
            temporary.unlink()
