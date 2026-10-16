"""把明确请求、当前类型化计划与定向源码接入受控输入预算。

只读组装，不启动 Agent、不执行测试、不写入任务进度或日志。
目标、授权和必要约束由调用方明确提供；本模块不替代完整接管校验。
反馈仍是调用方已核验的明确文本，不宣称程序已证明其有效性。
"""
from pathlib import Path
import json

import bmad_context as context
import bmad_state as state
from bmad_supervisor import contained_path, workspace_path


MAX_REQUEST_BYTES = 128 * 1024
MAX_SOURCE_BYTES = 128 * 1024
REQUEST_FIELDS = {
    "goal", "authorization", "task_id", "constraints", "capabilities",
    "code_files", "unfinished_files", "feedback", "observed_host_bytes",
}


def read_snapshot(root, relative, maximum):
    """读取明确的普通文件；限制读取量并复核读取期间的身份。"""
    state.relative_file(relative, "输入来源")
    path = contained_path(root, relative)
    if not path.is_file() or path.stat().st_size > maximum:
        raise context.ContextBlocked("输入来源缺失、不是普通文件或超出读取预算")
    identity = state.execution.environment.fingerprint(path)
    with path.open("rb") as stream:
        payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise context.ContextBlocked("输入来源在读取期间超出预算；未截断")
    if state.execution.environment.fingerprint(path) != identity:
        raise context.ContextBlocked("输入来源在读取期间变化；停止组装")
    return payload, path, identity


def source_list(values, label):
    if (not isinstance(values, list) or len(values) > context.MAX_ITEMS
            or any(not isinstance(item, str) for item in values)
            or len(set(values)) != len(values)):
        raise context.ContextBlocked(f"{label}必须是有界、无重复的明确文件列表")
    for value in values:
        state.relative_file(value, label)
    return values


def assemble_plan_input(*, workspace: Path, plan_file: str, request_file: str,
                        maximum_bytes=context.DEFAULT_STARTUP_BYTES):
    """从真实计划选择一个就绪任务，不接受请求自行提供状态或验证契约。

    请求中的目标、授权、约束和反馈是调用方声明，不是验证事实。
    源码定位必须显式指定；不扫描历史、不自动收集全部工作树。
    已完成依赖复用现有证据查询，不重跑业务；查询未通过即停止。
    """
    context.positive_budget(maximum_bytes, context.MAX_STARTUP_BYTES, "启动输入预算")
    root = workspace_path(workspace)
    payload, request_path, request_identity = read_snapshot(
        root, request_file, MAX_REQUEST_BYTES,
    )
    try:
        request = json.loads(payload, object_pairs_hook=state.execution.unique_object)
    except (ValueError, UnicodeError) as exc:
        raise context.ContextBlocked("输入请求无法解析或包含重复字段") from exc
    if not isinstance(request, dict) or set(request) != REQUEST_FIELDS:
        raise context.ContextBlocked("输入请求字段缺失或包含未支持字段")
    for field in ("goal", "authorization", "task_id"):
        context.nonempty_text(request[field], field)
    state.identifier(request["task_id"], "输入请求任务标识")
    texts = {}
    for field in ("constraints", "capabilities", "feedback"):
        values = request[field]
        if not isinstance(values, list):
            raise context.ContextBlocked(f"{field}必须是明确文本列表")
        texts[field] = tuple(values)
        context.text_items(texts[field], field)
    paths = {
        "code": source_list(request["code_files"], "定向源码"),
        "unfinished_changes": source_list(request["unfinished_files"], "未完成修改"),
    }
    data, plan_path, plan_identity = state.load_plan(root, plan_file)
    tasks = state.validate_contract(data)
    if request["task_id"] not in tasks:
        raise context.ContextBlocked("输入请求任务不属于绑定计划；不替换任务")
    projection = state.render_state(workspace=root, plan_file=plan_file)
    if projection["status"] != "READY":
        raise context.ContextBlocked("当前计划投影未就绪；不恢复阻塞或暂停任务")
    task = tasks[request["task_id"]]
    if task["status"] != "PENDING" or task["task_id"] not in projection["ready_tasks"]:
        raise context.ContextBlocked("所选任务未由当前证据判定为依赖就绪")
    snapshots = [(request_path, request_identity), (plan_path, plan_identity)]
    sources = {}
    total_source_bytes = 0
    for field, relatives in paths.items():
        materials = []
        for relative in relatives:
            if relative not in sources:
                raw, path, identity = read_snapshot(root, relative, MAX_SOURCE_BYTES)
                total_source_bytes += len(raw)
                if total_source_bytes > MAX_SOURCE_BYTES:
                    raise context.ContextBlocked("累计定向源码超过读取预算；未丢弃必要文件")
                try:
                    body = raw.decode("utf-8")
                except UnicodeError as exc:
                    raise context.ContextBlocked("输入来源不是 UTF-8 文本；未猜测修复") from exc
                context.nonempty_text(body, "定向源码内容")
                sources[relative] = body
                snapshots.append((path, identity))
            materials.append(f"来源：{relative}\n{sources[relative]}")
        paths[field] = tuple(materials)
    result = context.assemble_input(
        goal=request["goal"], authorization=request["authorization"],
        task={key: task[key] for key in ("task_id", "title", "verification")},
        state_projection=projection,
        constraints=texts["constraints"], capabilities=texts["capabilities"],
        code=paths["code"], unfinished_changes=paths["unfinished_changes"],
        feedback=texts["feedback"], maximum_bytes=maximum_bytes,
        observed_host_bytes=request["observed_host_bytes"],
    )
    # 明确绑定快照；外部变更不被覆盖，也不能以旧任务选择继续组装。
    if any(state.execution.environment.fingerprint(path) != identity
           for path, identity in snapshots):
        raise context.ContextBlocked("输入组装期间计划、请求或定向源码变化；停止对账")
    result.update(
        plan_file=plan_file, request_file=request_file, task_id=task["task_id"],
        business_reexecuted=False, state_saved=False,
        evidence_boundary=(
            "当前计划任务、就绪投影及明确来源文件的组装期身份核验；"
            "目标、授权、约束和反馈仍须调用方核验，不证明宿主加载或真实新会话"
        ),
    )
    return result
