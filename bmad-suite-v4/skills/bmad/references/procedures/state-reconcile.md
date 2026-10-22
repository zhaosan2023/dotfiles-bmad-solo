---
name: bmad-state-reconcile
description: >
  Reconcile claimed task state against actual code and verification evidence before declaring completion.
---

# State Reconciliation Procedure

## Objective
对照当前获准阶段的实现、验收与真实回执，防止虚假完成。阶段交付不等于全计划完成；只读审核仅会话交付，不因此写文件、运行验证、转正或归档。本流程不扩大授权，也不触发无关业务重测。

## Process

1. **Gather Evidence**: 
   - Read the user's original goal and acceptance criteria.
   - 读取当前已选定的唯一任务进度入口；控制器未实现或未覆盖时引用平台任务记录与真实回执，并披露缺口，不猜测应用目录或另建状态账本。
   - Read the Architecture Contract.
   - 在当前权限允许时审查相关差异，不为获取 Git 证据绕过分析模式的终端限制。
   - 对需要验证的工程任务，核对真实命令、工作目录、退出结果、关键输出及目标；只读任务不强制运行测试。静态契约或隔离分发通过不证明真实宿主加载、权限执行或远程自主运行。

2. **Reconcile**: Compare the claims against the hard evidence.
   - Did the test output actually confirm the claim?
   - Is the change within the approved architectural boundaries?
   - Are there any unapproved deviations?
   - 当前阶段的全部必需义务是否满足？后续阶段、待授权事项与其他暂停任务是否完整保留且未被登记为完成？

3. **Determine Verdict**:

Output ONE of the following verdicts:

- CONSISTENT：当前获准阶段的全部必需验收均有有效证据，允许交付该阶段，不自动完成全计划。
- CONDITIONALLY_CONSISTENT：明确尚未满足的条件、未完成义务及其影响；不得豁免必需验收或作为完成绿灯。
- STALE_STATE：任务视图或契约与实际候选不一致，停止对账；仅在授权内修正对应入口，不建立镜像账本。
- ARCHITECTURE_DRIFT：存在未经批准的架构偏移，不登记完成、不推进依赖。
- UNAPPROVED_DEVIATION：实现超出授权范围，不登记完成、不推进依赖，保留现场与已有改动。
- INSUFFICIENT_EVIDENCE：缺少当前阶段必需证据，保持阻塞，不以历史通过、零命中或日志保存成功替代。

只有当前阶段全部必需门禁通过才可交付该阶段。全计划完成、ADR 转正、事实登记、提交、推送及归档另按实际契约与各自授权处理。
