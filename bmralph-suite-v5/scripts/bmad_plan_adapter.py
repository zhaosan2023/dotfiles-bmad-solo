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


def load_batch(*, workspace: Path, plan_file: str, batch_file: str,
               initial_request_file: str):
    """读取明确批次授权集合；不把计划散文或全部就绪项当作授权。

    每个任务绑定独立请求文件，任务选择不改写请求中的任务标识。
    返回接管快照，由循环在阶段边界复核；本函数不执行或写进度。
    """
    root = state.workspace_path(workspace)
    raw, path, identity = inputs.read_snapshot(root, batch_file, inputs.MAX_REQUEST_BYTES)
    batch = json.loads(raw, object_pairs_hook=state.execution.unique_object)
    if (not isinstance(batch, dict)
            or set(batch) != {"schema_version", "plan_id", "tasks"}
            or type(batch["schema_version"]) is not int
            or batch["schema_version"] != 1):
        raise SupervisorError("批次契约字段缺失或不支持；不推断执行授权")
    data, _, _ = state.load_plan(root, plan_file)
    tasks = state.validate_contract(data)
    if batch["plan_id"] != data["plan_id"]:
        raise SupervisorError("批次与绑定计划标识不一致")
    entries = batch["tasks"]
    if not isinstance(entries, list) or not 1 <= len(entries) <= 32:
        raise SupervisorError("获准批次须明确列出 1 至 32 个任务")
    requests = {}
    request_paths = set()
    bound = {path: identity}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"task_id", "request_file"}:
            raise SupervisorError("批次任务须仅声明任务标识及必要输入请求")
        key = state.identifier(entry["task_id"], "批次任务标识")
        if key not in tasks or key in requests:
            raise SupervisorError("批次任务不属于绑定计划或重复")
        relative = state.relative_file(entry["request_file"], "批次输入请求")
        if relative in request_paths or relative in {plan_file, batch_file}:
            raise SupervisorError("各批次任务须绑定独立请求，不得与计划或批次契约重叠")
        payload, request_path, request_identity = inputs.read_snapshot(
            root, relative, inputs.MAX_REQUEST_BYTES)
        request = json.loads(payload, object_pairs_hook=state.execution.unique_object)
        if (not isinstance(request, dict) or set(request) != inputs.REQUEST_FIELDS
                or request.get("task_id") != key):
            raise SupervisorError("批次输入请求字段或任务归属不匹配；不改写任务标识")
        requests[key] = relative
        request_paths.add(relative)
        bound[request_path] = request_identity
    if initial_request_file not in request_paths:
        raise SupervisorError("初始请求不属于明确获准批次")
    return requests, bound


def select_batch_task(*, workspace: Path, plan_file: str, requests: dict):
    """仅从获准集合按声明顺序选择当前证据判定就绪的任务。"""
    root = state.workspace_path(workspace)
    data, _, identity = state.load_plan(root, plan_file)
    tasks = state.validate_contract(data)
    if not requests or any(key not in tasks for key in requests):
        raise SupervisorError("获准批次集合为空或已不属于当前计划")
    projection = query(workspace=root, plan_file=plan_file)
    if projection["status"] not in {"READY", "COMPLETED"}:
        raise SupervisorError("批次边界存在阻塞、暂停或失效证据；不推进")
    if state.execution.environment.fingerprint(
            contained_path(root, plan_file)) != identity:
        raise SupervisorError("批次选择期间计划变化；停止对账")
    for key in requests:
        if key in projection["ready_tasks"]:
            return key
    if all(tasks[key]["status"] == "COMPLETED" for key in requests):
        return None
    raise SupervisorError("获准集合没有依赖就绪任务；不执行集合外任务或恢复暂停项")


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
    updated = copy.deepcopy(data)
    for task in updated["tasks"]:
        if task["task_id"] == task_id:
            task.update(status="COMPLETED", verdict_file=verdict_file)
    final_identity = _save_plan(root, plan_file, identity, updated, (candidate,))
    return {"task_id": task_id, "verdict_file": verdict_file,
            "plan_identity": final_identity, "task_progress_saved": True,
            "business_reexecuted": False}


def refresh_completed(*, workspace: Path, plan_file: str,
                      verdict_files: dict, expected_identity: dict):
    """显式刷新原完成项的受影响证据；不继承旧绿灯、不执行测试。

    调用方须持工作区写租约。只接受原 COMPLETED 项的新 PASS 回执；
    全部完成项及其依赖重新核验后一次保存，不恢复暂停项或完成新任务。
    """
    root = state.workspace_path(workspace)
    data, _, identity = state.load_plan(root, plan_file)
    if identity != expected_identity:
        raise SupervisorError("刷新前绑定计划变化；保留外部修改，未写回")
    tasks = state.validate_contract(data)
    if (not isinstance(verdict_files, dict) or not verdict_files
            or len(verdict_files) > state.MAX_TASKS):
        raise SupervisorError("证据刷新须明确指定有界的原完成任务及新回执")
    for key, relative in verdict_files.items():
        if (not isinstance(key, str) or key not in tasks
                or tasks[key]["status"] != "COMPLETED"):
            raise SupervisorError("证据刷新仅接受原完成项；不恢复或完成其他任务")
        state.relative_file(relative, "刷新验收回执")
    updated = copy.deepcopy(data)
    for task in updated["tasks"]:
        if task["task_id"] in verdict_files:
            task["verdict_file"] = verdict_files[task["task_id"]]
    by_id = state.validate_contract(updated)
    candidates = tuple(task for task in updated["tasks"]
                       if task["status"] == "COMPLETED")
    for task in candidates:
        if any(by_id[key]["status"] != "COMPLETED" for key in task["depends_on"]):
            raise SupervisorError("刷新目标的完成依赖未满足；不接受历史绿灯")
        state.completed_evidence(root, task)
    final_identity = _save_plan(root, plan_file, identity, updated, candidates)
    return {"refreshed_tasks": list(verdict_files), "plan_identity": final_identity,
            "task_progress_saved": True, "business_reexecuted": False}


def _save_plan(root, plan_file, identity, updated, candidates):
    """共同的版本核验及原子保存；调用方已经核验获准任务状态。"""
    raw, _, source_identity = inputs.read_snapshot(root, plan_file, state.MAX_PLAN_BYTES)
    if source_identity != identity:
        raise SupervisorError("证据核验期间计划变化；未写回")
    content = raw.decode("utf-8")
    block = list(state.TASK_BLOCK.finditer(content))[0]
    state.validate_contract(updated)
    replacement = json.dumps(updated, ensure_ascii=False, indent=2) + "\n"
    output = (content[:block.start(1)] + replacement + content[block.end(1):]).encode("utf-8")
    if len(output) > state.MAX_PLAN_BYTES:
        raise SupervisorError("计划保存超过读取预算；原文件保留")
    path = contained_path(root, plan_file)
    temporary = path.with_name(".bmad-plan-" + uuid.uuid4().hex + ".tmp")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(output)
            os.fchmod(stream.fileno(), int(identity["mode"]))
            stream.flush()
            os.fsync(stream.fileno())
        # 再次复核真实回执；保存状态不是业务重测。
        for candidate in candidates:
            state.completed_evidence(root, candidate)
        path = contained_path(root, plan_file)
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
        return final_identity
    finally:
        if temporary.exists():
            temporary.unlink()
