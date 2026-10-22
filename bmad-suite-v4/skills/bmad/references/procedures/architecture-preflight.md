---
name: bmad-architecture-preflight
description: >
  Evaluate a task against the architecture contract before implementation begins.
---

# Architecture Preflight Procedure

## Objective
在获准工程阶段，针对受影响接口、数据所有权与跨层依赖检查架构约束。按核心场景规则选择，不因任务级别机械覆盖 bugfix 或 ops，不重复已经收敛且仍有效的完整分析。

只读审核仅取证与会话交付，不实施、不运行验证、不持久化、不转正或归档；本流程不增加分析模式的终端权限。

## Process

1. **Load Context**: Read the task goal, `_bmad-output/architecture/architecture-contract.yaml` (if exists), and relevant project code.
2. **Analyze Impact**: Determine exactly what the task will touch (components, interfaces, dependencies, data ownership).
3. **Check Invariants**: Compare the impact against the architecture contract.
4. **Determine Verdict**: Output the verdict and required next action.

## Preflight Report Format

Output exactly this structure:

```markdown
## Architecture Preflight

- **Task**: [Task ID/Name]
- **Task Level**: [S/M/L]
- **Architecture Sensitivity**: [A0/A1/A2/A3]
- **Affected Components**: [List]
- **Governing Decisions (ADRs)**: [List]
- **Applicable Invariants**: [List]
- **Conflicts**: [List hard or soft conflicts]
- **Missing Evidence**: [List what is unknown]

### Verdict: [PASS | WARN | BLOCK | UNKNOWN]

**Required Next Action**: [implement | experiment | update plan | create ADR | split task | escalate]
```

## Verdict Rules

- PASS：未发现冲突且关键前提有依据；仅在实际授权内推进对应阶段，不把预检通过当作执行许可。
- WARN：明确可接受风险及缓解条件；需要记录时使用已选唯一任务入口，只读任务不写文件。
- BLOCK：已证实违反必要不变量，不推进依赖；按冲突选择最小修正或请求关键决策，不强制每次新建 ADR。
- UNKNOWN：缺乏必要依据，不能判为通过；明确问题、实验范围、环境前提与验收后交给获准工程入口，不自动执行实验、不扩大分析权限。仅阻塞依赖该证据的任务。
