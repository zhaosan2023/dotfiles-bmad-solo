# The 4 Anti-Paralysis Convergence Locks

## The Threat: Analysis Paralysis & Endless Optimization
AI-assisted technical analysis frequently collapses into infinite cycles of:
- "We could also handle this 0.001% edge case..."
- "What if we add one more layer of indirection for future extensibility?"
- "Let's redesign the whole architecture to make it more elegant."

本参考用于停止不再改变当前决策的发散，不以固定数量或强制实施代替判断。遵循顶层分析权限：不使用终端、不创建或执行探针、不写生产文件。只读任务仅会话交付；必要实测明确问题、范围、环境前提与验收，交给获准工程入口，不自动启动。

---

## Lock 1: The Non-Goals Lock (Scope Capping)
- 第一遍明确必要非目标，不固定数量，不为了凑条目增加无关约束。
- 非目标用于界定当前裁决范围；合理澄清不被机械拒绝，实质性目标变化交回用户确认。

## Lock 2: The Hard Gates Cut (Instant Disqualification)
- 按实际权限、兼容性、资源、时间与必要不变量筛选候选，不把偏好的实施方式预设为硬门禁。
- 排除已证实违反必要约束的候选；未知不写成通过，缺必需证据只阻塞依赖它的裁决。
- 比较足以支持当前决策的候选，不固定候选数量；评分须有依据，证据不足时定性比较，不编造权重或分数。

## Lock 3: Novelty Exhaustion (Diminishing Returns Cutoff)
- 新增阅读或审查不再改变当前决策时停止发散，不重复同一风险的措辞变体。
- 保留未知、反证与必要下一步；信息耗尽不等于方案可行，也不豁免必需证据，不固定审查轮数。

## Lock 4: Minimal Sufficient Solution Verdict (The Stop-and-Ship Gate)
- 依据足以支持当前范围的可行、条件可行或拒绝结论时交付，停止无关优化；虚拟推演不冒充实测。
- 条件可行须明确尚未满足的条件及受影响义务，补齐必需证据前不推进依赖。
- 可行结论不等于实施授权。只读任务不持久化或附自动执行要求；获准结晶按分析报告、PROPOSED ADR 与计划的职责路由。
- 需要记录进度时只使用当前已选唯一任务入口；控制器未覆盖时引用平台任务记录与真实回执并披露缺口，不猜测状态文件路径、不另建镜像账本。
