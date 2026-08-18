建议将仓库升级为 BMAD-Solo V3：Architecture-Grounded Active State Loop（AGAS）。核心不是再增加一个庞大的 Architect Agent，而是让现有 /bmad-solo 在编码前重建工程事实、执行架构冲突门禁，在编码中根据事件重新判断，在完成前独立验证架构并回写证据状态。

当前仓库已经具备单入口、S/M/L 分级和 Product→Architect→Developer→Reviewer 的基本骨架，但架构模式、开发模式和执行流程之间缺少强制闭环。因此 AI 可以“切换到 Architect”，却仍然无法保证后续计划、算法、调试和代码遵守架构。

Key findings
主要问题不是缺少架构文档，而是架构没有控制执行

当前流程大致是：

TEXT
识别任务
→ 选择模式
→ 加载 procedure
→ 编码
→ 测试
→ Review

建议改为：

TEXT
任务进入
→ 从文档、代码和测试重建当前工程状态
→ 判断下一步高层动作
→ Architecture Preflight
   ├─ PASS：进入计划或实现
   ├─ WARN：记录风险后继续
   ├─ BLOCK：停止编码，修改方案、创建 ADR 或请求决定
   └─ INSUFFICIENT_EVIDENCE：先调查，不能假定通过
→ Algorithm/Integration Contract（按风险触发）
→ 小步实现与验证
→ 重大事件后重新执行架构判断
→ 行为验证 + 架构验证
→ 状态与代码对账
→ 对抗式 Review
→ 完成

这对应附件总结出的核心不对称：

局部技术执行正确，不代表任务方向正确；测试通过，也不代表实现位于正确架构边界。

当前仓库存在三个结构性缺口
SKILL.md 已有统一路由，但没有“架构冲突通过后才能实现”的硬门禁。
Architect、Developer 等 mode reference 很薄，无法稳定指导复杂计划、算法设计和架构调试。
当前 procedures 主要覆盖 architecture decision、build 和 code review，缺少状态重建、架构预检、算法契约、架构调试和状态对账。

此外，当前规则之间有潜在冲突：

config/AGENTS.md 倾向于自动生成 _bmad-output/project-context.md。
GEMINI.md 又规定只有项目明确采用 BMAD-Solo 时才创建相关状态目录。

应统一为：普通 S 级任务不产生持久状态；首次 M/L 或架构敏感任务才初始化，并明确告知用户。

Confirmed facts

基于当前仓库快照，可以确认：

仓库已经采用单一 /bmad-solo Gateway Skill。
现有路由包含 Product、Architect、Developer、Reviewer/QA、Operator 五种模式。
已经存在 S/M/L 任务分级、真实测试输出要求、对抗式 Review 和操作安全边界。
GEMINI.md 已经强调代码和终端事实高于过时文档。
brain/task.md 和 _bmad-output/project-context.md 已被设计为任务状态与长期上下文载体。
当前架构信息主要还是自然语言上下文，没有转化为每个编码动作前都必须检查的约束。
当前流程没有明确区分：
已验证事实；
Agent 假设；
只在局部成立的结果；
已被反驳的判断；
因代码变化而过时的状态。
当前 /bmad-solo Completion Gate 偏向“实现、Diff、测试、验收标准”，还没有明确要求“架构一致、状态一致、偏差已批准”。

因此，不建议推翻现有单入口设计，而应在其内部增加一个横向的架构控制面。

What remains inference

以下属于需要通过真实编码任务验证的工程假设，而不是附件论文已经证明的结论：

架构冲突门禁会减少跨层调用和错误组件实现。
Algorithm–Architecture Contract 会改善算法与系统集成质量。
两次失败后重审架构，能减少连续局部打补丁。
结构化状态会比单纯扩充 project-context.md 更可靠。
同一个模型在隔离实现理由后重新 Review，会比普通自审更有效。
增加门禁后的质量收益能够覆盖额外 token 和执行时间。

论文来自长程数学研究案例，并不是 BMAD 软件工程对照实验。因此 AGAS 应作为可衡量的 V3 实验，而不是未经验证地宣称一定提高编码质量。

What the evidence suggests
1. 修改 /bmad-solo 的核心路由

建议将 config/skills/bmad-solo/SKILL.md 的 Routing 改为：

MARKDOWN
## Architecture-grounded routing

1. Read governing rules, project context, task state, and current Git state.
2. Classify task level and architecture sensitivity.
3. Reconstruct relevant engineering facts from code, configuration, tests,
   dependency declarations, and architecture documents.
4. Select the next high-level action:
   investigate | clarify | design | implement | experiment | review |
   reconcile | escalate.
5. Before implementation, run architecture-preflight.
6. Do not implement when the verdict is BLOCK.
7. For algorithmic, cross-boundary, stateful, concurrent, security-sensitive,
   or performance-sensitive work, create an Algorithm–Architecture Contract.
8. Implement in small coherent steps and re-run architecture judgement after
   material changes or repeated failures.
9. Verify behavior and architecture independently.
10. Reconcile claimed state with repository facts before completion.

Completion Gate 改为：

MARKDOWN
A code task is complete only when:

- acceptance criteria are satisfied;
- relevant implementation is complete;
- behavioral verification has real output;
- applicable architecture invariants have evidence;
- no blocking architecture conflict remains;
- deviations are approved and recorded;
- claimed task state matches repository facts;
- Reviewer/QA has inspected the Diff independently;
- unverified obligations and residual risks are reported.
2. 不再只按 S/M/L 路由，增加架构敏感度

代码行数不能判断架构风险。一个两行依赖修改可能比新增几百行内部实现更危险。

建议增加：

等级	条件	要求
A0	局部、可逆、不影响边界	内存中的简短 Preflight
A1	修改公共接口、依赖、数据流或共享状态	持久化 Architecture Impact
A2	跨模块、算法、缓存、事务、并发、性能、安全	完整契约和 Postflight
A3	数据迁移、不可逆架构决策、生产影响	ADR、独立 Review、人工批准

最终路由由两个维度共同决定：

TEXT
Process depth = task size S/M/L + architecture sensitivity A0/A1/A2/A3

例如：

S+A0：直接短计划、实现、测试、Review。
S+A2：虽然改动小，但必须先执行架构门禁。
M+A1：生成任务状态和架构影响。
L+A3：必须先完成架构决策和用户批准。
3. 增加 Active Engineering State

不要继续把所有信息堆入 project-context.md。建议使用以下分层：

TEXT
_bmad-output/
├── project-context.md
├── architecture/
│   ├── architecture-contract.json
│   └── decisions/
├── state/
│   └── active-engineering-state.json
└── evidence/
    └── verification.jsonl

brain/
├── task.md
├── implementation_plan.md
├── architecture-impact.md
└── algorithm-contract.md

职责：

project-context.md：已验证且相对稳定的项目事实。
architecture-contract.json：可检查的组件、依赖、数据和质量约束。
active-engineering-state.json：当前任务的事实、假设、失败和开放义务。
verification.jsonl：实际执行的命令、结果、时间和代码版本。
architecture-impact.md：本任务影响哪些架构边界。
algorithm-contract.md：非平凡算法如何嵌入系统。

第一版建议使用 JSON 而不是 YAML，因为 JSON 可以用 Python 标准库或其他常见工具校验，不需要额外安装 YAML 解析依赖。

4. 为状态结论增加可信度类型

active-engineering-state.json 中的每项结论应包含状态：

JSON
{
  "claims": [
    {
      "id": "CLAIM-01",
      "statement": "重复构图是主要性能瓶颈",
      "status": "hypothesis",
      "scope": "production-like benchmark only",
      "evidence": ["profile-2026-08-17.json"],
      "invalidated_by": []
    }
  ]
}

允许的状态：

verified：有代码、测试、运行输出或正式决策支持。
accepted：已批准，但尚未运行验证。
hypothesis：当前工作假设。
local_only：只在特定组件、样本或环境成立。
refuted：已被证据否定。
stale：其依赖的代码或架构已经变化。
insufficient_evidence：无法判断。

这能直接防止把“单元测试通过”错误记录成“系统目标已经完成”。

5. 增加七个核心 procedure

建议新增：

TEXT
config/skills/bmad-solo/references/procedures/
├── context-reconcile.md
├── architecture-preflight.md
├── architecture-impact.md
├── algorithm-contract.md
├── architecture-debug.md
├── state-reconcile.md
└── architecture-review.md
context-reconcile.md

编码前比较：

用户当前要求；
project-context.md；
架构文档和 ADR；
当前代码与依赖；
Git Diff；
测试和运行输出；
brain/task.md 中的历史状态。

输出：

TEXT
CONSISTENT
STALE_DOCUMENTATION
STALE_TASK_STATE
UNAPPROVED_DEVIATION
CONFLICTING_SOURCES
INSUFFICIENT_EVIDENCE

规则：不能因为文档存在就假定其正确。代码事实优先，但代码偏离架构并不代表架构自动失效。

architecture-preflight.md

必须回答：

MARKDOWN
## Architecture Preflight

- Task:
- Task level:
- Architecture sensitivity:
- Affected components:
- Governing decisions:
- Invariants inspected:
- Public contracts changed:
- Data ownership changed:
- New dependencies:
- Concurrency/transaction impact:
- Security/performance impact:
- Conflicts:
- Missing evidence:
- Verdict: PASS | WARN | BLOCK | INSUFFICIENT_EVIDENCE
- Required next action:

门禁规则：

BLOCK：不得开始编码。
高风险任务出现 INSUFFICIENT_EVIDENCE：先调查。
如果 story 与架构冲突，只能：
修改实现方案；
修改任务范围；
提出 ADR；
请求用户决定。
Developer 不得静默修改架构契约来让自己通过门禁。
algorithm-contract.md

在以下情况下触发：

搜索、优化、调度、分配、排序、路由等非平凡算法；
缓存、并发、批处理、重试和状态机；
声称具有复杂度或性能改进；
依赖特定数据规模或分布；
算法跨越组件边界；
失败会影响一致性、安全或用户数据。

模板：

MARKDOWN
# Algorithm–Architecture Contract

## Problem
- Objective:
- Non-goals:
- Exactness requirement:
- Reference behavior:

## Placement
- Owning component:
- Why this component:
- Allowed dependencies:
- Prohibited dependencies:

## Data
- Inputs and semantics:
- Outputs and semantics:
- Data owner:
- Reads through:
- Writes through:

## Invariants
- Correctness:
- Ordering/tie-breaking:
- Idempotency:
- Consistency:
- Concurrency:

## Budgets
- Expected input scale:
- Time complexity:
- Memory complexity:
- I/O/network budget:

## Failure semantics
- Invalid input:
- Timeout:
- Partial failure:
- Stale data:
- Retry/fallback:

## Verification
- Reference implementation:
- Unit examples:
- Property tests:
- Boundary tests:
- Benchmark:
- Architecture dependency test:

## Unresolved decisions
- ...

缺少 owning component、输入输出语义、不变量、失败语义或验证 oracle 时，不应直接编码。

architecture-debug.md

调试顺序改为：

TEXT
症状
→ 被破坏的外部行为契约
→ 对应架构不变量
→ 至少两个根因假设
→ 每个假设的可证伪检查
→ 运行实验
→ 局部修复、架构修复或重新定义问题

每轮记录：

MARKDOWN
## Hypothesis H-03

- Observation:
- Expected architectural behavior:
- Suspected violation:
- Falsification test:
- Actual result:
- Status: supported | rejected | unresolved
- Next action:

以下事件强制退出普通 patch 循环，重新进入 Architect 模式：

同类修复连续失败两次；
为通过测试新增特殊分支；
绕过已有接口；
新增跨层依赖；
修改公共 API 或数据模型；
改变缓存、事务、并发或数据所有权；
单元测试通过但集成测试持续失败；
性能优化依赖架构未保证的前提。
state-reconcile.md

完成前比较：

TEXT
用户目标
+ Task/Story
+ Architecture Contract
+ 实际代码和依赖
+ Git Diff
+ 测试/Benchmark 输出
+ Agent 声称的完成状态

只能输出：

TEXT
CONSISTENT
CONDITIONALLY_CONSISTENT
STALE_STATE
UNAPPROVED_DEVIATION
INSUFFICIENT_EVIDENCE

只有 CONSISTENT 或明确说明条件的 CONDITIONALLY_CONSISTENT 才能进入最终完成报告。

architecture-review.md

Reviewer 不读取 Developer 为自己辩护的过程叙述，只读取：

用户要求和验收标准；
Architecture Impact；
Algorithm Contract；
Git Diff；
测试和验证证据；
当前架构契约。

检查：

代码是否实现于正确组件；
是否出现未声明依赖；
是否绕过 port、service、repository 或权限边界；
算法是否符合复杂度、数据所有权和失败语义；
是否把局部验证错误泛化为系统完成；
是否存在未经批准的架构偏差。
6. 扩充 mode reference，而不是新增 Slash Command

保持一个 /bmad-solo，不要新增 /architecture-guard 等独立注册 Skill。

mode-architect.md 至少应规定：

Architect 负责选择下一步高层动作，而不只是生成架构文档。
在实现前识别组件、边界、数据流、约束和验证义务。
发现信息不足时可以选择调查或实验，而不是默认输出实现计划。
不得把 Developer 已写出的方案反向包装为架构合理。
架构变化必须通过 ADR 或用户批准。

mode-developer.md 至少应规定：

只能在 Preflight 通过的边界内实现。
每次只完成一个最小连贯步骤。
重大实现变化必须重新执行架构判断。
发现计划不可行时停止并回退，不得静默扩大范围。
调试失败达到阈值时切换到 architecture-debug。

mode-reviewer.md 应增加：

立场和上下文与 Developer 隔离。
测试通过不是 Review 结束条件。
必须检查依赖方向、组件归属和状态一致性。
无证据的完成声明必须标记为 INSUFFICIENT_EVIDENCE。
7. 修改 capability-map.md

建议增加以下映射：

Capability	Mode	Trigger	Output
context-reconcile	Architect	M/L 或上下文冲突	Reconciliation verdict
architecture-preflight	Architect	所有代码任务，深度按风险	PASS/WARN/BLOCK
architecture-impact	Architect	A1–A3	Architecture Impact
algorithm-contract	Architect	算法或 NFR 敏感	Algorithm Contract
build	Developer	Preflight 已通过	Code + tests
architecture-debug	Architect/Developer	重复失败或跨边界修复	Hypotheses + decision
state-reconcile	Reviewer	完成前	State verdict
architecture-review	Reviewer	M/L 或 A1–A3	Architecture findings
code-review	Reviewer	存在 Diff	Code findings
8. 修改 build.md 为微循环
TEXT
读取当前任务状态
→ 确认 Preflight 仍有效
→ 选择一个最小实现步骤
→ 修改代码和测试
→ 执行最相关验证
→ 判断是否触发架构重检
→ 写入证据和新事实
→ 继续下一步或回退 Architect

禁止：

一次性实现完整大方案后才检查架构；
为通过测试绕过既有边界；
把未执行的测试写入验证证据；
在实现中自行降低验收条件；
因为架构契约阻碍编码而直接修改契约。
Conflicting evidence or uncertainty
当前 BMAD-Solo 并非完全缺少架构能力；它已经有 Architect 模式、架构决策 procedure 和项目上下文。更准确的诊断是：缺少运行时架构控制和状态校正。
同一个 AI 顺序切换 Developer 和 Reviewer，不能提供真正的模型独立性。第一版可以通过“新上下文、只读 Diff 与契约、不读取实现辩护”降低确认偏误，但高风险任务仍应由人工或独立会话审查。
更严格的门禁会增加 token 和时间成本，因此不能让普通 A0 小改动生成一套完整文档。
架构契约也可能过时。过时契约比没有契约更危险，所以必须先执行 context reconciliation。
附件论文能支持状态循环、判断与执行分离、失败回写等设计方向，但不能单独证明这些修改会提高 BMAD-Solo 的软件工程效果。
当前抓取到的 project-context.md 内容非常简略，并疑似包含字面转义换行；落地前应在真实工作区检查文件格式。
Open questions

建议先采用以下默认值，避免阻塞 V3 原型：

契约格式：默认 JSON；说明和理由保留 Markdown。
持久化范围：A0 不落盘，A1–A3 才创建任务状态。
架构契约权限：Developer 只读；通过 Architect/ADR 流程修改。
重复失败阈值：同类修复两次失败后强制架构重检。
独立 Review：默认新上下文；A3 要求人类批准。
门禁强度：依赖方向、数据所有权、安全边界和未经批准的公共接口变化属于 blocking。
初始化策略：首次 M/L 或 A1–A3 任务时初始化，而不是打开任意项目就自动写文件。

后续仍需通过试点确定：

Antigravity 是否能可靠地按需加载新增 procedure；
新上下文 Reviewer 如何保留必要证据而不读取 Developer 的解释；
什么样的项目可以自动提取依赖规则；
哪些语言和框架需要额外的确定性架构检查工具。
Sources worth trusting most

本次改造应按以下优先级使用材料：

2608.11195v2.pdf：状态循环、技术执行与高层判断分离、长期状态失真的第一手来源。
当前仓库中的 GEMINI.md、config/AGENTS.md、config/skills/bmad-solo/SKILL.md 和 references：判断真实路由和现有约束的直接依据。
sol_solution.txt、opus_solution.txt、fable_solution.txt：论文到 BMAD-Solo 的工程映射和风险分析。
真实项目代码、依赖图和测试输出：判断架构文档是否仍然有效的最终工程证据。

附件解读适合指导设计，但不能代替在真实项目上的 A/B 验证。

Recommended next step

建议分三个 PR 落地，而不是一次重写整个仓库。

PR 1：建立最小架构闭环

修改：

TEXT
config/AGENTS.md
config/skills/bmad-solo/SKILL.md
config/skills/bmad-solo/references/capability-map.md
config/skills/bmad-solo/references/mode-architect.md
config/skills/bmad-solo/references/mode-developer.md
config/skills/bmad-solo/references/mode-reviewer.md

新增：

TEXT
procedures/context-reconcile.md
procedures/architecture-preflight.md
procedures/state-reconcile.md
templates/architecture-impact.md
templates/active-engineering-state.json

验收：

A0 小任务不会产生不必要文档。
跨模块任务会生成 Architecture Impact。
出现 blocking conflict 时不会进入编码。
完成前会比较声明状态与实际代码。
PR 2：算法与架构调试

新增：

TEXT
procedures/algorithm-contract.md
procedures/architecture-debug.md
procedures/architecture-review.md
templates/algorithm-contract.md
templates/architecture-contract.json

并重写 build.md 为微循环。

验收：

算法任务未声明组件归属和验证 oracle 时不能编码。
连续两次失败后自动退出局部 patch。
公共接口、依赖、缓存、事务或并发变化会触发重检。
Reviewer 能报告“测试通过但架构错误”。
PR 3：确定性工具和实证评估

增加可选检查：

禁止依赖和依赖方向检查；
JSON Schema 校验；
API/schema 兼容性检查；
性能预算；
验证证据记录；
状态文件过期检测。

用 10–20 个真实 Story 对比原版和 AGAS 版，记录：

架构冲突逃逸数量；
未声明跨层依赖数量；
重复调试轮次；
Story reopen 和返工率；
Code Review 才发现的问题；
算法正确性和性能回归；
token、时间和人工介入成本。

成功标准应是：

TEXT
行为正确
AND 架构一致
AND 状态有证据
AND 偏差已批准

而不只是“测试通过”。

本回答没有修改、Commit 或 Push 远程仓库；它给出的是可直接转成 V3 实施 PR 的设计方案。

Summary

dotfiles-bmad-solo 应保留当前“一个入口、单 AI 连续执行”的产品方向，但需要把架构从一种可选思考模式升级为所有重要编码任务的运行时控制面。

最关键的改造是：

从代码事实重建工程状态，而不是盲信历史文档；
在编码前执行 Architecture Preflight；
根据任务规模和架构敏感度控制流程深度；
让算法设计明确绑定组件、数据所有权、复杂度和失败语义；
重复调试失败时回退到架构判断；
在测试之外验证依赖方向、组件归属和架构不变量；
完成前将任务声明、架构契约、实际代码和验证证据进行对账。

这样才能使 AI 不只是“先计划再编码”，而是能够持续判断：现在是否应该编码、应该在哪里编码、当前方案是否仍与整体架构一致，以及已有证据究竟证明了什么。