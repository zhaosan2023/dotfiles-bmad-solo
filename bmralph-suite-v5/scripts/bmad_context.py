"""受控启动输入与累计工具结果的字节预算原语。

仅覆盖显式经过本模块的输入和结果，不拦截宿主附件、自动加载或工具
旁路。未知宿主输入量明确披露；字节近似不是 Token 或费用计量。
本模块不读取历史、不写进度、不执行验证、不授予任务实施权限。
完整输入来源及计划绑定仍由调用方核验；尚非独立 Agent 适配器。
"""
from __future__ import annotations

from dataclasses import dataclass
import json

from bmad_supervisor import SupervisorError


MAX_STARTUP_BYTES = 128 * 1024
DEFAULT_STARTUP_BYTES = 64 * 1024
MAX_TOOL_RESULT_BYTES = 16 * 1024
MAX_CUMULATIVE_TOOL_BYTES = 128 * 1024
MAX_ITEMS = 256


class ContextBlocked(SupervisorError):
    """必要输入无法完整表达或结果超限；不得截掉约束后继续执行。"""


def positive_budget(value, maximum, label):
    if type(value) is not int or not 256 <= value <= maximum:
        raise ContextBlocked(f"{label}必须为 256 至 {maximum} 字节的整数")
    return value


def nonempty_text(value, label):
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        raise ContextBlocked(f"{label}必须是非空且不含 NUL 的文本")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContextBlocked(f"{label}必须是可编码为 UTF-8 的文本") from exc
    return value


def text_items(values, label):
    if not isinstance(values, tuple) or len(values) > MAX_ITEMS:
        raise ContextBlocked(f"{label}必须是数量有界的显式文本元组")
    for value in values:
        nonempty_text(value, label)
    return list(values)


def encode_object(data):
    try:
        payload = json.dumps(
            data, ensure_ascii=False, sort_keys=True, allow_nan=False,
            separators=(",", ":"),
        ) + "\n"
        # 在统一异常边界核验 UTF-8，非法代理字符不得绕过失败关闭。
        payload.encode("utf-8")
        return payload
    except (ValueError, TypeError, OverflowError, RecursionError) as exc:
        raise ContextBlocked("受控输入或工具结果不是可编码为 UTF-8 的有限 JSON 数据") from exc


def assemble_input(*, goal, authorization, task, state_projection,
                   constraints=(), capabilities=(), code=(),
                   unfinished_changes=(), feedback=(),
                   maximum_bytes=DEFAULT_STARTUP_BYTES,
                   observed_host_bytes=None):
    """完整组装一项就绪任务；任何必要部分超预算即阻塞，不裁剪。

    task 仅包含 task_id、title、verification；state_projection 必须是
    调用方取得的当前候选投影。源码材料由调用方定向读取并显式传入，
    本函数不声称验证其真实性、新鲜度或任务授权。反馈也须由调用方
    核验仍有效，不能把历史通过结果当作当前完成证据。
    """
    positive_budget(maximum_bytes, MAX_STARTUP_BYTES, "启动输入预算")
    nonempty_text(goal, "目标")
    nonempty_text(authorization, "授权边界")
    if (not isinstance(task, dict)
            or set(task) != {"task_id", "title", "verification"}
            or not isinstance(task["verification"], dict)):
        raise ContextBlocked("启动输入必须明确包含唯一任务及其验证契约")
    nonempty_text(task["task_id"], "任务标识")
    nonempty_text(task["title"], "任务标题")
    if (not isinstance(state_projection, dict)
            or state_projection.get("operation") != "render-state"
            or state_projection.get("status") != "READY"
            or state_projection.get("business_reexecuted") is not False
            or state_projection.get("state_saved") is not False):
        raise ContextBlocked("缺少当前就绪状态投影；不隐式恢复阻塞或暂停任务")
    view = nonempty_text(state_projection.get("view"), "完整状态视图")
    ready = state_projection.get("ready_tasks")
    if (not isinstance(ready, list)
            or any(not isinstance(item, str) for item in ready)
            or task["task_id"] not in ready):
        raise ContextBlocked("所选任务未由当前投影判定为依赖就绪")
    if (type(state_projection.get("view_lines")) is not int
            or type(state_projection.get("view_bytes")) is not int
            or len(view.splitlines()) > 80
            or state_projection["view_lines"] != len(view.splitlines())
            or state_projection["view_bytes"] != len(view.encode("utf-8"))
            or len(view.encode("utf-8")) > 16384):
        raise ContextBlocked("状态视图计数不一致或超过行数、字节硬上限")
    for field in ("tasks_total", "unfinished_count"):
        if type(state_projection.get(field)) is not int or state_projection[field] < 1:
            raise ContextBlocked("就绪状态缺少必要任务数量信息")
    if state_projection["unfinished_count"] > state_projection["tasks_total"]:
        raise ContextBlocked("未完成任务数量超过任务总数")
    nonempty_text(state_projection.get("plan_id"), "投影计划标识")
    nonempty_text(state_projection.get("plan_file"), "投影计划路径")
    if observed_host_bytes is not None and (
        type(observed_host_bytes) is not int or observed_host_bytes < 0
    ):
        raise ContextBlocked("宿主已观察输入量必须是非负字节数或未知")
    data = {
        "schema_version": 1,
        "measurement": "UTF-8 字节近似；不是 Token 或费用计量",
        "goal": goal,
        "authorization": authorization,
        "task": task,
        "state_projection": state_projection,
        "constraints": text_items(constraints, "必要方案约束"),
        "capabilities": text_items(capabilities, "必要能力与定位"),
        "code": text_items(code, "当前定向源码"),
        "unfinished_changes": text_items(unfinished_changes, "未完成修改"),
        "feedback": text_items(feedback, "最近有效反馈"),
        "observed_host_bytes": observed_host_bytes,
        "host_observation": (
            "未观察宿主自动加载输入；不能声称整个请求受预算约束"
            if observed_host_bytes is None else
            "仅计入调用方明确观察的宿主输入；不证明全部自动加载已覆盖"
        ),
    }
    payload = encode_object(data)
    controlled_bytes = len(payload.encode("utf-8"))
    accounted_bytes = controlled_bytes + (observed_host_bytes or 0)
    if accounted_bytes > maximum_bytes:
        raise ContextBlocked("完整必要启动输入超过预算；未裁剪约束、任务、修改或反馈")
    return {
        "operation": "assemble-input", "status": "READY",
        "payload": payload, "controlled_bytes": controlled_bytes,
        "accounted_bytes": accounted_bytes, "maximum_bytes": maximum_bytes,
        "measurement": "UTF-8 字节近似",
        "host_input_coverage": "UNKNOWN" if observed_host_bytes is None else "PARTIAL_OBSERVATION",
        "evidence_boundary": "仅受控输入组装；不证明来源新鲜度、宿主旁路或真实新会话",
    }


@dataclass
class ToolOutputBudget:
    """单轮累计转发预算；完整结果由调用方在程序侧保存。

    消费完整 JSON 结果及其转义开销，不只计算日志正文。超限后锁定
    阻塞，后续调用不能通过换一个较小结果继续。实例不保存任务进度，
    不改变业务裁决，也不证明未经过此入口的宿主工具结果受到限制。
    """

    maximum_bytes: int = MAX_CUMULATIVE_TOOL_BYTES
    maximum_result_bytes: int = MAX_TOOL_RESULT_BYTES
    accepted_bytes: int = 0
    accepted_calls: int = 0
    blocked: bool = False

    def __post_init__(self):
        positive_budget(self.maximum_bytes, MAX_CUMULATIVE_TOOL_BYTES, "累计工具输出预算")
        positive_budget(self.maximum_result_bytes, MAX_TOOL_RESULT_BYTES, "单次工具输出预算")
        if self.maximum_result_bytes > self.maximum_bytes:
            raise ContextBlocked("单次工具输出预算不得超过累计预算")
        if self.accepted_bytes != 0 or self.accepted_calls != 0 or self.blocked is not False:
            raise ContextBlocked("输出预算须创建新实例，不导入历史计数或通过状态")

    def consume(self, result):
        if self.blocked:
            raise ContextBlocked("本轮工具输出预算已阻塞；不得继续转发")
        try:
            if (not isinstance(result, dict)
                    or not isinstance(result.get("status"), str)
                    or result["status"] not in {"PASS", "BLOCKED", "READY", "SUSPENDED", "COMPLETED"}):
                raise ContextBlocked("工具结果缺少明确裁决；日志保存成功不替代业务结果")
            if result["status"] == "BLOCKED":
                nonempty_text(result.get("reason"), "工具阻塞原因")
            payload = encode_object(result)
            size = len(payload.encode("utf-8"))
            if size > self.maximum_result_bytes:
                raise ContextBlocked("单次完整工具结果超过预算；未截掉失败或证据定位")
            if self.accepted_bytes + size > self.maximum_bytes:
                raise ContextBlocked("累计工具结果超过预算；停止本轮，不静默丢弃或重置计数")
        except ContextBlocked:
            self.blocked = True
            raise
        self.accepted_bytes += size
        self.accepted_calls += 1
        # 不把工具 BLOCKED 改为 PASS；完整传递原业务裁决。
        return payload
