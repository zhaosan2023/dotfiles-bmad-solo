---
name: bmad-three-pass-analysis
description: >
  Deep structured scheme and proposal deconstruction procedure synthesizing
  Keshav Three-Pass reading, Deep Recon evidence convergence, and 4 anti-paralysis locks.
---

# Three-Pass Scheme Analysis Procedure

## Objective

Prevent both shallow superficial summaries and endless philosophical over-engineering. Deconstruct any technical proposal, paper, or architectural design through divergent structural stress-testing, followed immediately by strict boundary convergence to a minimal sufficient solution.

## Triggers

- 用户要求深入审核技术方案、架构计划或论文，或任务存在尚未收敛的重要设计取舍。
- 明确需求或获准方案的工程接管不重复完整分析；局部修复不强制本流程。
- 本流程不增加权限：分析不使用终端、不创建或执行探针、不写生产文件与项目事实基线。只读任务仅会话交付，不持久化、不验证、不转正或归档。
- 必要实测明确问题、实验范围、环境前提与验收，另交获准工程入口；不自动切换并启动实验，不把草稿路径视为沙箱。

## Process

### 1. Pass 1: Bird's-Eye Qualitative Scan (5C + Non-Goals Lock)
- **Category (类别)**: Architectural refactoring, pipeline migration, new feature subsystem, or academic algorithm? (Map to S/M/L).
- **Context (上下文)**: Dependencies on current codebase, external services, or foundational theories.
- **Correctness (正确性)**: Are initial foundational assumptions plausible?
- **Contributions (增量价值)**: What tangible problem does this actually solve?
- **Clarity (清晰度)**: Is the boundary clearly stated or vague?
- 范围锁：明确必要非目标，不固定条数；实质性目标变化交回人工，不机械锁死合理澄清。

### 2. Pass 2: Evidence & Structural Verification
- **Data Flow & Causality**: Do inputs, transformations, and outputs form a closed causal loop?
- **State Machine / Topology**: Are there orphan states, race windows, or cyclic dependencies?
- 证据分层：区分用户陈述、源码或官方文档事实、真实实测回执、逻辑推断、待验假设、反证与未知；源码存在不等于运行通过，用户体验不等于因果证明。
- 重要数字、接口与效果结论定位依据；无对照测量时不声称提速或智能程度提升，不要求所有假设在结晶前实测。
- 硬门禁：按实际权限、兼容性、资源与时间等必要约束筛选；未知不写成通过，缺必需证据只阻塞依赖它的裁决。

### 3. Pass 3: Virtual Re-Implementation & Implicit Assumption Stress-Test
- **Virtual Implementation Check**: If coding began immediately, where is the exact point the developer would get blocked?
- 关键隐式假设：按实际风险识别必要前提，不固定数量，不为无关极端场景无限补证。
- 反向审查：寻找足以推翻当前方案的真实边界与反例；虚拟推演不冒充物理实测。
- 信息耗尽：新增阅读不再改变当前决策时停止发散，保留未知和必要下一步，不自动判定可行。

### 4. Convergence & Verdict [Lock 4]
Synthesize findings into an actionable verdict. Never leave the output as an open-ended debate.

---

## Output Report Format

下列结构仅供组织证据，按任务裁剪，不固定非目标、假设或失败模式数量。只读审核仅会话交付；只有当前用户授权且平台允许持久写入时，才按核心规则使用分析报告路径。必要决策与执行契约分别放在关联 ADR 与计划，不另建状态账本。

```markdown
# Scheme Analysis: [Topic / Proposal Name]

## 1. Pass 1: 5C Qualitative Baseline
- **Category**: [Type & Level: S/M/L]
- **Context**: [System dependencies & existing constraints]
- **Correctness**: [Plausibility of core hypothesis]
- **Contributions**: [True incremental value vs. overhead]
- **Clarity**: [Boundary clarity score: High / Medium / Low]
- **必要非目标**：[仅列与当前任务相关的排除范围]

## 2. Pass 2: Structural & Evidence Verification
- **Causal Flow / Topology**: [Valid | Gap identified: ...]
- **State & Invariants**: [Clean | Risk: ...]
- **Evidence Backing**: [Verified | Anecdotal | Unsubstantiated]

## 3. Pass 3: Virtual Re-implementation & Stress-Test
- **First Implementation Roadblock**: [Specific file/interface/algorithm hurdle]
- **关键隐式假设**：[必要前提、证据与待验项]
- **相关失败模式与反证**：[足以改变当前裁决的风险，区分推演与实测]

## 4. Convergence & Verdict
- **Recommended Path**: [Chosen minimal sufficient path]
- **Key Trade-off Accepted**: [What is sacrificed for simplicity/speed]
- **Cheapest Reversibility Hedge**: [Seam / abstraction to pivot if wrong]

### Verdict: [FEASIBLE | CONDITIONALLY_FEASIBLE | REJECT]

**必要下一步**：
- 可行：交付当前结论；仅在获准时交接对应工程阶段，不自动实施。
- 条件可行：明确条件、缺失证据及依赖它的未完成事项；只读任务不写文件。
- 拒绝：说明已证实的硬冲突，不推进依赖；需要新的关键取舍时交回用户。
```

---

## Verdict Rules

- 可行：当前范围的必要证据与约束已足以支持结论，停止无关优化；结论不增加实施权限。
- 条件可行：明确尚未满足的条件及适用边界，必要证据补齐前不推进依赖。
- 拒绝：已证实违反必要硬约束，或收益不足以支持影响范围，不进入编码。
- 评分仅用于有依据的存活候选比较；证据不足时采用定性比较，不编造权重、分数或效果承诺。
