建议把 dotfiles-bmad-solo 从“按模式路由后执行编码”升级为“架构驱动的主动工程状态循环”。关键不是增加一段“请先考虑架构”的提示词，而是让 Agent 在编码前判断架构冲突、执行中重新评估、验证后回写事实，并能自主选择
实现 / 实验 / 重构问题 / 更新架构 / 请求人工决策
。

当前最优先还不是添加新功能，而是先修复现有 Skill 的不完整依赖和路由断点；否则新增架构流程也可能根本无法稳定运行。以下给出可直接落地到仓库的改造方案，但本回答未直接修改或提交远程仓库。

Key findings
1. 当前系统有 Architect 模式，但没有架构控制循环

当前流程主要是：

TEXT
识别任务等级
→ 选择 Product / Architect / Developer
→ 加载 Procedure
→ 编码
→ Review

这只能保证“复杂任务可能经过 Architect”，不能保证：

每次实现前都检查任务与架构是否冲突。
Developer 修改公共接口、数据流或依赖方向后重新进入 Architect 判断。
连续调试失败时停止局部修补并重审架构假设。
测试通过后区分“局部行为正确”与“系统义务已经完成”。
新发现的事实、反例和失败原因进入下一轮规划。

因此，当前 Architect 更像一个阶段或角色，而不是执行过程中的控制面。

2. 当前核心模式文件不足以驱动高质量架构推理

现有 mode-architect.md 和 mode-developer.md 只有职责边界和典型能力的简短定义，没有规定：

如何从代码重建真实架构。
如何识别受影响组件和依赖方向。
如何提取架构不变量。
如何判断任务和架构冲突。
如何约束算法的组件位置、复杂度、数据所有权和失败语义。
什么情况下停止编码并返回架构层。

Agent 因而仍可能从任务文本直接跳到实现。

3. 当前 Procedure 注册表与实际文件不一致

capability-map.md 注册了需求澄清、产品简报、实施计划、测试设计、运行诊断、部署等多个 Procedure，但当前 procedures/ 目录只包含：

architecture-decision.md
build.md
code-review.md

这意味着路由器可能选择一个不存在的 Procedure。

4. 核心 Procedure 不是完全自包含的

当前 build.md 要求目标项目存在：

TEXT
_bmad/scripts/render_skill.py

而 architecture-decision.md、code-review.md 还依赖 customization resolver、memlog、step files、配置文件等 BMAD 基础设施。

但 bs.sh 的定位是把 BMAD-Solo 作为全局配置安装到 Antigravity，使其服务于任意项目。目标项目未必包含完整 _bmad/scripts，因此可能出现：

TEXT
正确路由到 build
→ 目标项目没有 _bmad/scripts/render_skill.py
→ 按 Procedure 要求立即 HALT

这是必须先处理的 P0 问题。

5. project-context.md 不能承担主动工程状态

当前 project-context.md 只保存项目级稳定背景，而且内容还是单行带字面 \N 的文本。即使修正格式，它仍不适合保存：

当前任务目标。
已验证事实和待证实假设。
局部成立的结论。
失败尝试及其架构含义。
未完成验证义务。
当前架构冲突。
下一步高层动作。

project-context.md 应继续保存稳定事实，任务级动态状态需要独立文件。

Confirmed facts

基于当前仓库主分支内容，可以确认：

仓库采用一个 bmad-solo Skill 作为统一入口。
SKILL.md 已具备 S/M/L 分类、渐进加载、Developer 后切换 Reviewer 等基础路由。
AGENTS.md 已经定义 Product、Architect、Developer、Reviewer、Operator 五种模式。
M/L 任务要求跟踪任务状态和执行 Code Review。
当前 Completion Gate 包含实现、Diff 审查、真实验证输出、验收标准和风险报告。
现有架构 Procedure 已经提出 architecture spine、稳定 AD ID、继承父级架构不变量等有价值的概念。
但主路由没有把 architecture spine 转化为每轮编码必须检查的冲突门禁。
capability map 指向的多个 Procedure 当前不存在。
build.md 依赖目标项目中的完整 BMAD 渲染脚本。
project-context.md 当前不能提供有效的任务级架构状态。
What remains inference

以下属于从附件方法论迁移到 AI Coding 的工程推论，尚未经过该仓库的 A/B 实验验证：

结构化架构契约会比纯 Markdown 上下文更稳定。
编码前的架构冲突门禁会减少返工和跨层依赖。
主动工程状态可以减少长任务中的状态失真。
两次同类失败后触发问题重构，通常优于继续局部修补。
独立的 Architecture Review 会提高架构一致性。
Algorithm–Architecture Contract 能降低算法在生产规模、并发和数据所有权上的错误。

另一个证据限制是：附件 PDF 本身未能在本次会话中成功建立检索索引。因此，对论文机制的使用主要来自三份附件 solution 的一致解读，而不是本次重新逐页核验论文原文。

What the evidence suggests

建议将新机制命名为：

TEXT
Architecture-Grounded Active Engineering Loop
简称 AGAEL

完整控制循环如下：

TEXT
任务输入
  ↓
重建真实工程状态
  ↓
架构影响分析
  ↓
高层工程判断
  ├─ clarify：澄清目标
  ├─ discover：检查代码事实
  ├─ experiment：先做实验或 benchmark
  ├─ plan：生成架构约束下的计划
  ├─ implement：进入编码
  ├─ reframe：重新定义问题
  ├─ update-architecture：更新 ADR/架构
  └─ escalate：请求人工决策
  ↓
技术执行
  ↓
行为验证 + 架构验证
  ↓
证据回写与状态校正
  ↺
一、建议的目标目录结构
TEXT
config/skills/bmad-solo/
├── SKILL.md
├── references/
│   ├── capability-map.md
│   ├── active-engineering-loop.md
│   ├── mode-product.md
│   ├── mode-architect.md
│   ├── mode-developer.md
│   ├── mode-reviewer.md
│   ├── mode-operator.md
│   └── procedures/
│       ├── inspect-project.md
│       ├── establish-architecture-baseline.md
│       ├── architecture-gate.md
│       ├── implementation-plan.md
│       ├── algorithm-fit.md
│       ├── build.md
│       ├── debug.md
│       ├── verify.md
│       ├── reconcile-state.md
│       └── code-review.md
├── templates/
│   ├── architecture-contract.yaml
│   ├── active-engineering-state.yaml
│   ├── implementation-plan.md
│   └── architecture-review.md
└── scripts/
    ├── validate-solo-package.py
    └── validate-engineering-state.py

项目运行时生成：

TEXT
_bmad-output/
└── architecture/
    ├── architecture-contract.yaml
    └── adr/

brain/
├── task.md
├── active-engineering-state.yaml
└── implementation_plan.md

低风险 S 任务不强制生成全部文件，避免小改动被过度设计。

二、修改 SKILL.md：加入不可跳过的控制循环

建议在现有 Routing 后增加：

MD
## Mandatory Engineering Control Loop

Before editing code:

1. Reconstruct the relevant actual state from code, configuration,
   tests, Git diff and verified project context.
2. Identify affected components, interfaces, data ownership,
   dependency directions and quality budgets.
3. Run the Architecture Conflict Gate.
4. Select exactly one next high-level action:
   clarify, discover, experiment, plan, implement, reframe,
   update-architecture, or escalate.
5. Enter implementation only when the verdict is PASS or an
   explicitly accepted WARN.

During implementation, repeat the Architecture Conflict Gate when:

- a public interface changes;
- a new dependency or cross-layer call is introduced;
- data ownership, persistence, caching, concurrency or transaction
  behavior changes;
- the implementation plan materially changes;
- the same class of fix fails twice;
- tests pass locally but integration obligations remain open.

After implementation:

1. Verify behavior and architecture independently.
2. Reconcile claims against actual evidence.
3. Mark each obligation verified, local-only, refuted or still open.
4. Update active engineering state.
5. Run adversarial review before declaring completion.

同时把 Completion Gate 扩展为：

MD
A task is complete only when:

- acceptance criteria are satisfied;
- applicable architecture invariants are preserved;
- every hard verification obligation has evidence;
- local-only results are not represented as global completion;
- architecture deviations have an ADR or explicit approval;
- active engineering state matches the actual code and test results;
- remaining unknowns and risks are reported.
三、建立机器可检查的架构契约

建议模板：

YAML
schema_version: 1

baseline:
  git_head: ""
  dirty_worktree: false
  generated_from:
    - code
    - tests
    - project-context
    - architecture-docs

components:
  - id: example-domain
    responsibility: ""
    owns_data: []
    allowed_dependencies: []
    forbidden_dependencies: []

invariants:
  - id: ARCH-INV-001
    statement: "Domain code must not depend on infrastructure frameworks"
    severity: hard
    scope: []
    rationale: ""
    verification:
      method: dependency-check
      command: ""

interfaces:
  - id: API-001
    producer: ""
    consumers: []
    compatibility_policy: backward-compatible

data_ownership:
  - resource: ""
    owner: ""
    writers: []
    readers: []

quality_budgets:
  latency_p95_ms: null
  memory_mb: null
  throughput_per_second: null
  availability: null

algorithm_constraints:
  exactness: required
  determinism: unspecified
  complexity_limit: ""
  fallback_policy: ""
  observability_required: true

change_policy:
  requires_adr:
    - public-interface-change
    - dependency-direction-change
    - data-ownership-change
    - consistency-model-change
  requires_human_approval:
    - security-boundary-change
    - destructive-migration

关键规则是：

文档描述“规范上应该是什么”。
代码和测试描述“实际上是什么”。
两者不一致时不得静默选择其中之一。
实际状态优先用于判断当前行为，但差异必须记录为 drift。
陈旧架构契约必须标记 stale，不能继续作为确定事实。
四、建立主动工程状态
YAML
schema_version: 1
task_id: ""
task_level: M
status: judging

goal:
  outcome: ""
  acceptance_criteria: []
  non_goals: []

baseline:
  architecture_version: ""
  git_head: ""
  relevant_adrs: []

impact:
  components: []
  interfaces: []
  data: []
  runtime: []
  security: []

claims:
  - id: CLAIM-001
    statement: ""
    status: hypothesis
    scope: production
    evidence: []

constraints:
  - id: ARCH-INV-001
    severity: hard
    status: applicable

open_obligations:
  - id: OBL-001
    statement: ""
    verification_method: ""
    status: open

failed_attempts:
  - approach: ""
    hypothesis: ""
    result: ""
    evidence: []
    lesson: ""
    repeat_class: ""

architecture_verdict:
  status: UNKNOWN
  conflicts: []
  accepted_warnings: []

next_action:
  type: discover
  reason: ""

claims.status 只允许：

TEXT
verified
accepted
hypothesis
local-only
refuted
stale

这直接防止：

TEXT
单测通过
→ 被记录成系统正确

小样本 benchmark 有效
→ 被记录成满足生产规模

当前模块可运行
→ 被记录成跨模块集成完成
五、实现 Architecture Conflict Gate

每次进入编码前必须输出：

TEXT
Architecture verdict: PASS | WARN | BLOCK | UNKNOWN

Affected:
- components
- interfaces
- dependency directions
- data ownership
- NFR budgets

Applicable invariants:
- ARCH-INV-...

Conflicts:
- hard conflicts
- soft conflicts
- unresolved assumptions

Required action:
- implement
- experiment
- update plan
- create ADR
- split task
- request human decision

判定语义：

PASS：没有发现冲突，关键假设已有依据。
WARN：存在可接受的架构债务，必须记录后继续。
BLOCK：违反 hard invariant，禁止直接编码。
UNKNOWN：证据不足，先检查代码、运行实验或 benchmark。

UNKNOWN 不能自动当作 PASS。

六、算法任务必须生成 Algorithm–Architecture Contract

以下条件任意一个成立时触发：

任务涉及性能优化。
需要搜索、调度、缓存、批处理、图算法或并发。
数据量会影响算法选择。
算法修改可能改变确定性、排序或一致性。
存在多个复杂度明显不同的候选方案。
算法需要跨组件读取或修改状态。

输出至少包含：

MD
## Problem contract

- Exact objective:
- Input semantics:
- Output semantics:
- Edge cases:

## Architectural placement

- Owning component:
- Allowed dependencies:
- Data owner:
- State lifecycle:

## Correctness

- Invariants:
- Exact or approximate:
- Determinism:
- Idempotency:

## Resource fit

- Expected input scale:
- Time complexity:
- Space complexity:
- I/O and network budget:

## Failure behavior

- Timeout:
- Partial failure:
- Retry semantics:
- Fallback:
- Rollback:

## Verification

- Reference implementation:
- Property tests:
- Benchmark:
- Production observability:

没有明确组件位置、复杂度预算和验证方式时，不应直接进入实现。

七、把 Build 改造成架构约束下的微循环

当前 build.md 不应继续强依赖目标项目中的 _bmad/scripts/render_skill.py。建议重写为自包含 Procedure：

TEXT
1. Load active engineering state.
2. Confirm Architecture verdict is PASS or accepted WARN.
3. Select the smallest open obligation.
4. State:
   - files to change;
   - invariant being preserved;
   - evidence to produce.
5. Make the smallest coherent change.
6. Run the narrowest relevant verification.
7. Record evidence.
8. Re-run the gate if a recheck trigger occurred.
9. Continue only if the active state still matches reality.

如果确实希望继续使用完整 BMAD renderer，则应把所需 scripts、steps、customize 文件全部打包进 bmad-solo，而不是假设任意目标项目都会提供它们。

八、调试流程从“修改报错行”升级为“定位被破坏的契约”

新增 debug.md：

TEXT
观察到的症状
→ 被违反的外部契约
→ 本应阻止它的架构不变量
→ 失败进入系统的边界
→ 最小可证伪假设
→ 区分性实验
→ 修复正确层级
→ 验证
→ 状态回写

失败分类：

需求或意图错误。
Spec 错误。
架构错误或架构已经陈旧。
算法假设错误。
局部实现错误。
测试错误。
环境错误。

以下情况必须重新进入 Architect 判断：

同一类假设连续失败两次。
修复要求新增跨层调用。
为通过测试需要绕过公共接口。
修改缓存、事务、并发或数据所有权。
单测通过但集成测试持续失败。
局部修复造成其他组件回归。
实现依赖于架构从未保证的前提。
九、Code Review 增加架构追踪，而不只检查代码质量

Reviewer 必须检查：

每项验收标准是否有证据。
每项 hard invariant 是否仍成立。
是否出现未声明的新依赖。
算法是否位于正确组件。
数据写入者是否符合 ownership。
公共接口是否产生未记录变更。
测试通过能证明什么、不能证明什么。
是否把 local-only 结论升级成了 verified。
调试中发现的新事实是否已经回写。
架构契约是否已因代码变化而陈旧。

建议最终判定：

TEXT
APPROVE
APPROVE_WITH_DEBT
CHANGES_REQUIRED
ARCHITECTURE_DECISION_REQUIRED
INSUFFICIENT_EVIDENCE
Conflicting evidence or uncertainty
当前 BMAD-Solo 并非完全没有架构能力；已有 Architect 模式、architecture spine 和 Review 门禁。问题更准确地说是“架构没有持续参与每轮行动判断”。
更严格的架构门禁会增加 token、执行时间和文件数量，因此不能对所有 S 任务执行完整流程。
架构契约本身可能过时。如果 Agent 无条件信任旧契约，结构化状态反而会让错误持续更久。
同一 Agent 完成实现和架构审查仍可能存在确认偏误。高风险 L 任务最好使用新上下文或独立 Reviewer。
附件论文是数学研究长程案例，不是 BMAD-Solo 软件工程对照实验，因此不能声称上述改造必然提升质量。
现有仓库只有少量提交和有限的自动化测试基础，目前不足以量化改造收益。
Open questions

落地前需要明确以下政策：

架构契约自动更新权限

Agent 只能提出修改？
还是允许低风险情况下自动更新？
哪些变更必须人工批准？

状态保存位置

继续使用 brain/ 保存任务状态？
还是全部放入 _bmad-output/engineering-state/？

独立审查方式

同一模型的新上下文。
不同模型。
静态检查脚本加 Reviewer。
三者组合。

门禁强度

S：内存中的轻量影响检查。
M：持久化 active state 和 architecture gate。
L：完整契约、ADR、独立审查和人工批准。

建议默认采用以上分级，避免所有任务都被重流程拖慢。

Sources worth trusting most

按可信度和用途排序：

dotfiles-bmad-solo 当前主分支源码：判断现状、缺失文件、依赖关系和实际路由行为的第一手依据。
2608.11195v2.pdf：长期状态、研究判断、技术执行和人类纠偏机制的第一手理论来源；但本次未能重新建立全文检索。
opus_solution.md、fable_solution.md、sol_solution.md：三份解读在主动状态、架构门禁、算法契约和状态回写方面高度一致，但仍属于二手解释。
后续真实 BMAD-Solo A/B 测试：判断这些改造是否实际提高编码质量的最终依据。
Recommended next step

建议分三个提交完成，不要一次重写全部系统。

Commit 1：修复基础可执行性
修复 project-context.md 的格式。
检查 capability-map.md 中每个 Procedure 是否真实存在。
删除不存在的映射，或补齐对应文件。
重写 build.md，消除对目标项目 _bmad/scripts 的隐式依赖。
检查 architecture-decision.md 和 code-review.md 的 scripts、steps、config 是否全部打包。
增加 validate-solo-package.py，验证所有相对路径都能解析。

验收标准：

TEXT
capability-map 中不存在失效路径
所有 Procedure 在普通非 BMAD 项目中可加载
核心 Build 不因缺少 _bmad/scripts 而直接 HALT
Commit 2：加入最小架构闭环

只新增四项：

architecture-contract.yaml
active-engineering-state.yaml
architecture-gate.md
reconcile-state.md

并修改：

SKILL.md
mode-architect.md
mode-developer.md
build.md
code-review.md

第一版不需要复杂自动分析器，先让 Agent 稳定执行：

TEXT
编码前 Gate
重大变化后 Recheck
编码后 Reconcile
Review 时检查架构漂移
Commit 3：建立情景测试和质量评估

至少加入以下测试场景：

单文件低风险修复，不触发重型架构流程。
任务要求 Controller 直接访问数据库，Gate 返回 BLOCK。
性能优化任务，触发 Algorithm–Architecture Contract。
同类修复连续失败两次，切换为 reframe。
代码与架构文档冲突，状态标记为 stale。
公共 API 或数据所有权变化，要求 ADR。
单测通过但系统义务未关闭，不允许标记完成。

建议用 10–20 个真实任务比较原版和增强版：

Review 阶段才发现的架构冲突数。
Story 返工和 reopen 次数。
同类调试失败循环数。
未声明的跨层依赖数。
算法违反 NFR 的次数。
架构契约误报和错误阻塞率。
Token、时间和人工介入成本。
Summary

当前 dotfiles-bmad-solo 已经解决了“一个入口自动路由多个角色”的问题，但没有解决“Agent 如何自主从架构出发选择下一步并持续执行”的问题。现有架构能力属于阶段性输入，还不是贯穿规划、编码、调试和审查的运行时控制面。

最小有效改造是：

先修复不存在的 Procedure 和不完整的 BMAD 脚本依赖。
把架构文档编译成可检查的 architecture contract。
为 M/L 任务维护 active engineering state。
编码前强制输出 PASS/WARN/BLOCK/UNKNOWN。
算法任务必须绑定组件位置、数据所有权、复杂度和 NFR。
重复失败或边界变化时自动返回 Architect 判断。
验证后更新事实、假设、失败和开放义务。
只有“行为正确、架构一致、证据充分、状态准确”同时成立时才能完成任务。

这样改造后，BMAD-Solo 才会从“路由 Agent 去写代码”升级为“由架构约束持续指导计划、实验、实现、调试和验证”。