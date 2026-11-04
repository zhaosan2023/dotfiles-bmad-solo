---
name: bmad-architecture-decision
description: >
  Produce or update an architecture decision record (ADR).
  Self-contained — does not depend on external scripts.
---

# Architecture Decision Procedure

## Objective
对当前尚未收敛且影响架构边界的重要取舍形成有依据的决策提案；不重复已获准方案，不为普通缺陷或运维机械创建 ADR。提案只有满足实际接受契约并获得相应批准后，才能作为正式决策消费。

只读讨论仅取证与会话交付，不写文件、不运行验证、不转正或归档；本规程不增加分析角色的终端权限或项目事实写入权限。

## Context

按实际权限读取当前决策所需材料：
1. 当前用户需求、验收、授权及实际绑定的任务契约；不猜测或恢复其他任务。
2. 目标项目 `docs/project-context.md`；仅其不存在时兼容旧 `_bmad-output/project-context.md`，损坏或来源冲突不静默换源。
3. 目标项目已声明的相关领域规范、机器契约和已接受 ADR。既有 `_bmad-output/architecture/architecture-contract.yaml` 保留消费者兼容，不因新目录规则擅自迁移或忽略。
4. 相关源码与真实证据；结构事实不单独证明历史动机，未知必须保留。

## Process

1. 核对当前问题及影响边界；已有充分需求和获准方案直接消费，只澄清会改变决策的必要缺口，不编造约束。
2. 先排除不满足权限、兼容性和资源等必要条件的候选，再按证据比较可行路径；说明被否候选，不凑固定数量或虚构评分。
3. 起草简明 ADR，保存背景、决策、依据、被否候选、条件、未知与必要验证义务；新提案保持 PROPOSED，不镜像逐轮执行流水。
4. 仅当前授权允许持久结晶时，保存到目标项目 `docs/adrs/ADR-YYYYMMDD-[topic].md`；显式绑定路径优先，既有记录保留原路径，不自动迁移、覆盖或追改历史接受语境。

## ADR Format

Use this template for the output:

```markdown
# ADR-[Date]-[Topic]

## Status
PROPOSED

## Context
What is the problem we are solving? What are the constraints?

## Decision
What is the specific, actionable decision?

## Rationale
Why did we choose this over the alternatives? What trade-offs did we accept?

## Consequences
What becomes easier? What becomes harder? Are there new risks or verification obligations?
```

## Post-Decision
- 变更组件、不变量或数据所有权时，定位受影响的领域规范、机器契约、接口和消费者，列出必要适配；缺格式、权限或证据时保留缺口，不自动改写事实基线或公共规范。
- 仅另获相应写入授权时登记已验证事实或更新正式契约；文档提案保存不证明运行验证、宿主加载或程序门禁通过。
- 仅当前绑定契约要求关联 ADR、全部必需门禁通过且取得转正授权时接受对应提案；缺必需运行时证据保持 PROPOSED，不转正其他任务记录。
