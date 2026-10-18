"""Pi 试验回执的只读裁决接口，等待获准独立工程会话实现。

本模块不由循环控制器导入，不加载凭据、不联网、不写进度、ADR 或计划。
输入是调用方采集的回执快照；校验快照不提供签名或同账号防篡改保证。
必需反例位于本套件 tests_pi，禁止修改验收资产以制造通过。
"""


def evaluate_trial(evidence, *, expected_workspace, expected_plan_id,
                   authorized_tasks, disconnect_at):
    """根据完整回执裁决；缺证据失败关闭，不把启动当作断开验收。

    独立工程任务须实现 tests_pi/test_pi_headless_evidence.py 的全部约束。
    返回对象至少包含 status、reason、adr_accepted、plan_archived、
    evidence_boundary；任何结果都不得实施 ADR 接受或计划归档。
    """
    return {
        "status": "BLOCKED",
        "reason": "Pi 真实运行回执裁决尚未实现；保留未完成任务",
        "adr_accepted": False,
        "plan_archived": False,
        "evidence_boundary": "未实现；不证明真实 Pi、断开推进或全计划完成",
    }
