---
name: bmad-algorithm-fit
description: >
  Establish an Algorithm-Architecture Contract for complex tasks.
---

# Algorithm-Architecture Fit Procedure

## Objective
在获准算法工程阶段，明确受影响算法的边界、预算与失败语义；直接消费仍有效的明确需求或获准契约，不重复完整分析。本流程不扩大实际授权或模式权限。

## Triggers
按核心场景路由选择：仅 `algo` 场景中涉及搜索、调度、优化、缓存、批处理、并发或明确性能约束的工作适用。`structural` 场景使用架构预检；`bugfix` 和 `ops` 不因跨组件或数据一致性要求被机械改路由。

只读任务仅取证与会话交付，不写契约、不运行验证、不转正或归档；分析角色不使用终端、不创建或执行探针。

## Process
1. **Analyze Constraints**: Read the task requirements and project context.
2. **Determine Budgets**: Establish time, space, and I/O budgets for the algorithm.
3. **Determine Semantics**: Define exactness, idempotency, and failure/retry semantics.
4. **Contract Reuse**：复用绑定计划中仍有效的算法契约；确有缺口且已获文档写入授权时才补齐，不为普通任务另建重复工件。

## Output Template

需要输出契约时复用 [算法契约模板](../contracts/algorithm-contract.template.md)，按实际适用范围填写。关键依据不足时仅阻塞依赖该依据的任务；必要实验须明确问题、范围、环境前提与验收，交给获准工程入口，不自动切换模式或启动实验。模式切换、交接及草稿路径不构成执行许可或沙箱证明；缺少必要契约时不推进相关生产实施。
