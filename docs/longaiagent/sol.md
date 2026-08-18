建议将 dotfiles-bmad-solo 升级为“架构驱动的主动工程闭环”，而不是继续增加角色或长提示词。核心流程应从当前的“识别模式 → 执行 → Review”，改成“重建工程状态 → 架构判断 → 选择动作 → 执行 → 独立验证 → 状态回写”，并允许 Agent 判断下一步应当编码、实验、拆分任务、修改架构还是请求人工决策。

Key findings

当前仓库已经具备 S/M/L 分级、Product/Architect/Developer/Reviewer/Operator 模式、渐进加载和完成门禁，但这些机制主要是任务路由，不是架构控制。

最关键的缺口有四个：

Architect 只在特定阶段或关键词下出现，没有在编码前主动审查任务与架构的关系。
Developer 被要求“遵循架构”，但没有机器可检查的架构契约，也没有明确的 PASS/WARN/BLOCK 门禁。
调试和重复失败没有触发架构重审，容易持续局部打补丁。
测试结果没有回写为带范围和可信度的工程状态，容易把“局部通过”误记为“系统完成”。

因此，应在现有单入口 /bmad-solo 内增加横向控制面，不需要恢复几十个独立 Skill。

Confirmed facts

基于当前仓库快照，可以确认：

config/AGENTS.md 已经定义 S/M/L 任务分级和五种思考模式。
SKILL.md 的路由过程主要是读取上下文、任务分级、加载模式、选择 procedure、执行和 Review。
mode-architect.md、mode-developer.md、mode-reviewer.md 内容非常简短，尚不足以约束复杂的架构推理、算法设计和调试行为。
capability-map.md 引用了多个 procedure，但当前 references/procedures/ 中只看到：
architecture-decision.md
build.md
code-review.md
build.md 依赖目标项目中的 _bmad/scripts/render_skill.py；当前安装脚本主要链接 GEMINI.md、AGENTS.md 和 skills/，因此需要确认目标项目是否一定存在该脚本。
_bmad-output/project-context.md 当前包含字面量 \N，不是正常换行，且内容过于简略，无法承担架构事实基线。
当前完成门禁检查实现、Diff、测试和验收标准，但没有检查：
架构不变量；
组件边界；
数据所有权；
算法复杂度预算；
未批准的架构偏移；
工程状态是否与代码事实一致。
What remains inference

以下是从附件论文及三个 solution 迁移出的工程假设，而不是已经被该仓库实验证明的结论：

结构化架构契约会比纯 Markdown 提示更稳定。
Preflight/Midflight/Postflight 门禁会减少架构偏移和返工。
将实现和架构验证分开，可能降低同一 Agent 的确认偏误。
显式保存失败假设、证据和开放义务，可能减少重复调试。
采用 Architecture-Grounded Active State Loop 后，编码质量可能提高，但 token、时间和人工介入成本也会增加。

这些假设必须通过真实任务对照验证。

What the evidence suggests
1. 将 BMAD-Solo 升级为 AGAS Loop

建议采用：

Architecture-Grounded Active State Loop，简称 AGAS。

目标流程：

TEXT
用户任务
  ↓
读取规范状态 + 实际代码状态 + 当前任务状态
  ↓
Architecture Preflight
  ↓
选择下一种高层动作
  ├─ implement
  ├─ experiment
  ├─ reframe
  ├─ split-task
  ├─ update-architecture
  └─ escalate
  ↓
计划与技术执行
  ↓
测试、静态检查、Benchmark、Diff
  ↓
Architecture Postflight + State Reconciliation
  ↓
独立 Reviewer
  ↓
工程状态回写
  ↺

关键变化是：Story 或任务不再默认进入编码。

2. 增加三层工程状态

建议目标项目使用以下结构：

TEXT
_bmad-output/
├── project-context.md
├── architecture-contract.yaml
├── engineering-state.yaml
├── verification-evidence.jsonl
├── decisions/
│   └── ADR-*.md
└── tasks/
    └── TASK-*.yaml

brain/
├── task.md
└── implementation_plan.md

职责划分：

project-context.md
已验证的技术栈、命令、服务和部署事实。
architecture-contract.yaml
应该遵守的规范状态。
engineering-state.yaml
代码和运行证据证明的实际状态。
verification-evidence.jsonl
追加式测试、Benchmark、检查和失败证据。
tasks/TASK-*.yaml
当前任务的假设、失败、义务和下一动作。
brain/*
当前会话内的执行清单，不作为长期事实来源。

必须明确分开：

TEXT
Normative state：系统应该是什么
Actual state：当前代码实际上是什么
Believed state：Agent 当前相信什么
Unknown state：尚无证据确认什么

当规范和代码冲突时，不能简单规定“始终以代码为准”或“始终以文档为准”，而应输出 ARCHITECTURE_DRIFT。

3. 新增架构契约

建议增加模板：

YAML
version: 1
last_verified_at: null

components:
  - id: example-domain
    responsibilities: []
    owns_data: []
    allowed_dependencies: []
    forbidden_dependencies: []

invariants:
  - id: ARCH-INV-001
    statement: "Domain layer must not depend on infrastructure"
    severity: block
    scope: ["example-domain"]
    verification:
      - type: dependency-check
        command: null

interfaces: []

data_ownership: []

nfr_budgets:
  latency_p95_ms: null
  memory_mb: null
  throughput_rps: null
  consistency: null

algorithm_constraints:
  determinism: null
  exactness: null
  complexity_limit: null
  fallback_policy: null

change_policy:
  requires_adr:
    - public-interface-change
    - data-ownership-change
    - dependency-direction-change
    - transaction-boundary-change
  requires_human_approval:
    - security-boundary-change
    - destructive-migration

每条不变量必须有：

唯一 ID；
适用范围；
严重级别；
验证方法；
允许例外的 ADR 流程。

没有验证方法的不变量，只能作为人工 Review 项，不能伪装成已自动执行的门禁。

4. 新增 Active Engineering State
YAML
task_id: TASK-001
goal: ""
risk_level: medium

architecture_baseline:
  contract_version: 1
  relevant_adrs: []
  relevant_invariants: []

affected_scope:
  components: []
  interfaces: []
  data: []
  runtime_paths: []

claims:
  - id: CLAIM-001
    statement: ""
    status: hypothesis
    scope: local
    evidence: []

failed_attempts: []

open_obligations: []

conflicts: []

next_action:
  type: architecture-preflight
  reason: "Architecture fit has not been evaluated"

retry_state:
  same_hypothesis_failures: 0
  same_patch_class_failures: 0

Claim 状态建议限制为：

verified：有直接证据。
accepted：已正式决定，但尚未运行验证。
hypothesis：待验证假设。
local-only：仅在特定模块、样例或环境成立。
refuted：被证据否定。
stale：依赖的代码或架构已经变化。

这样可以直接防止“单测通过等于系统完成”。

5. 改造路由器

SKILL.md 的路由逻辑建议改成：

TEXT
1. 读取项目规则、project-context 和 Git 状态。
2. 确认架构契约；不存在时执行 architecture-baseline。
3. 重建当前任务的 Active Engineering State。
4. 根据实际影响面而不是关键词进行 S/M/L 分级。
5. 执行 Architecture Preflight。
6. 根据判定选择 implement、experiment、reframe、
   split-task、update-architecture 或 escalate。
7. 只有 PASS 或已记录缓解措施的 WARN 可以进入 Build。
8. 执行期间遇到重审事件，立即运行 Architecture Recheck。
9. 实现后运行行为验证和架构验证。
10. 从代码和验证证据重建状态，不直接相信 Agent 的完成总结。
11. 切换独立 Reviewer 进行 Architecture Drift Review。
12. 所有开放义务关闭后才允许声明完成。
6. 使用风险驱动门禁

不要让所有小修改都运行完整架构流程。

S 级快速门禁

只有同时满足以下条件才属于 S 级：

修改局限于一个已有组件；
不修改公共接口；
不新增依赖；
不改变数据所有权；
不涉及并发、事务、缓存或安全；
不改变性能关键路径；
不修改部署或运行时拓扑。

只要任一项不满足，至少升级为 M 级。

M/L 级完整门禁

必须输出：

TEXT
Architecture verdict: PASS | WARN | BLOCK | UNKNOWN

Affected components:
Applicable invariants:
Governing ADRs:
Assumptions:
Conflicts:
Required verification:
Required action:

判定语义：

PASS：未发现冲突，可以编码。
WARN：存在可接受风险，必须记录缓解和验证。
BLOCK：违反硬性不变量，禁止编码。
UNKNOWN：证据不足，先做 spike、实验或 Benchmark。
7. 给算法任务增加架构适配契约

当任务涉及搜索、调度、优化、缓存、批处理、并发、性能或复杂数据处理时，自动触发 algorithm-fit。

必须回答：

算法属于哪个组件？
输入输出语义是什么？
谁拥有输入和中间状态？
是否跨越现有 port、service 或 repository？
时间、空间、I/O 和网络复杂度预算是什么？
是否要求确定性、幂等性或精确结果？
失败、超时和部分结果如何映射为系统语义？
如何回退和回滚？
用什么 oracle 验证正确性？
Benchmark 能证明什么，不能证明什么？

建议产物：

TEXT
_bmad-output/tasks/TASK-001-algorithm-contract.md

契约不完整时，Agent 只能做实验，不能直接提交生产实现。

8. 把调试改造成架构感知诊断

新增 architecture-debug.md：

TEXT
观察症状
  ↓
确认可重复条件
  ↓
定位被违反的外部契约
  ↓
定位相关架构不变量
  ↓
提出至少两个可证伪假设
  ↓
执行最小区分实验
  ↓
判定问题层级
  ├─ 局部实现缺陷
  ├─ 接口契约冲突
  ├─ 数据所有权错误
  ├─ 算法假设错误
  ├─ 架构已陈旧
  └─ 需求与架构冲突

以下情况必须触发 Architecture Recheck：

同类修复连续失败两次；
为通过测试引入特殊分支；
修改公共接口；
新增跨层依赖；
绕过已有 adapter、port 或 service；
修改缓存、事务、并发或一致性策略；
算法复杂度或数据模型发生变化；
单测通过但集成测试持续失败；
实现计划与原方案明显偏离。
9. 改造 Code Review 完成条件

最终完成条件应由：

TEXT
测试通过

升级为：

TEXT
行为正确
AND 验收标准满足
AND 架构不变量未被破坏
AND 算法/NFR 预算有证据
AND 工程状态已从仓库事实重建
AND 未批准偏差为零
AND 开放义务已关闭或明确移交

State Reconciliation 只能输出：

CONSISTENT
CONDITIONALLY_CONSISTENT
STALE_STATE
ARCHITECTURE_DRIFT
UNAPPROVED_DEVIATION
INSUFFICIENT_EVIDENCE
10. 建议的仓库文件改动
TEXT
config/skills/bmad-solo/
├── SKILL.md                              # 修改路由主循环
├── references/
│   ├── capability-map.md                 # 增加架构闭环能力
│   ├── mode-architect.md                 # 扩充判断责任
│   ├── mode-developer.md                 # 加入门禁和重审触发器
│   ├── mode-reviewer.md                  # 加入架构漂移审查
│   ├── contracts/
│   │   ├── architecture-contract.template.yaml
│   │   ├── engineering-state.template.yaml
│   │   └── algorithm-contract.template.md
│   └── procedures/
│       ├── architecture-baseline.md
│       ├── architecture-preflight.md
│       ├── implementation-plan.md
│       ├── algorithm-fit.md
│       ├── build.md
│       ├── architecture-recheck.md
│       ├── architecture-debug.md
│       ├── state-reconcile.md
│       ├── correct-course.md
│       └── code-review.md
└── scripts/
    ├── validate-references.py
    └── validate-contract.py

capability-map.md 应至少增加：

Capability	Mode	Trigger	Required output
architecture-baseline	Architect	缺少或架构状态陈旧	Architecture Contract
architecture-preflight	Architect	所有 M/L 编码任务	PASS/WARN/BLOCK/UNKNOWN
algorithm-fit	Architect	算法或 NFR 敏感任务	Algorithm Contract
architecture-recheck	Architect	关键变更或重复失败	Updated verdict
architecture-debug	Architect/Developer	非单纯局部缺陷	Hypothesis log
state-reconcile	Reviewer	实现完成后	Consistency verdict
correct-course	Architect/Product	BLOCK 或架构漂移	ADR、拆分或升级决定
Conflicting evidence or uncertainty
附件论文是长程数学研究案例，不是软件工程对照实验，因此只能支持设计方向，不能证明该改造一定提高编码质量。
更严格的架构门禁可能提高质量，也可能导致小任务过度设计。
YAML 文件本身不能保证正确；如果状态来自错误的 Agent 总结，只会把短期错误固化为长期错误。
同一模型即使切换到 Reviewer 模式，也不是真正独立验证。条件允许时，应使用新会话、不同上下文或确定性工具。
当前仓库部分 procedure 依赖目标项目的 _bmad/scripts。是否保留该依赖，取决于 BMAD-Solo 是完整 BMAD 的附加层，还是需要独立运行。
当前没有改造前后的实际任务数据，因此效果证据不足。
Open questions

正式实施前，需要确定：

BMAD-Solo 是否必须脱离完整 _bmad 项目独立运行？
架构契约是由 Agent 自动生成，还是首次生成后必须人工确认？
哪些 BLOCK 允许 Agent 自动创建 ADR，哪些必须询问用户？
Reviewer 是否可以使用独立会话或不同模型？
主要目标是绿地项目、既有项目，还是两者都支持？
是否接受在目标项目中生成 _bmad-output/architecture-contract.yaml 等状态文件？
是否需要把确定性检查接入 CI，而不只依赖 Agent 遵守提示词？
Sources worth trusting most

按可信度排序：

2608.11195v2.pdf：用于理解主动状态、研究判断、技术执行、验证和人工纠偏的原始机制。
当前仓库中的 GEMINI.md、config/AGENTS.md、SKILL.md、mode 和 procedure 文件：用于判断系统当前真实能力。
opus_solution.md、fable_solution.md、sol_solution.md：作为论文到 AI coding 的工程迁移分析，不应当作实证结果。
改造后真实运行的测试、Diff、Benchmark、架构检查和任务返工数据：这是最终判断方案是否有效的最强证据。
Recommended next step

建议先实现一个 P0 最小版本，不要一次加入所有流程。

P0：先修复结构性问题
修复 _bmad-output/project-context.md 的字面量 \N。
检查 capability-map.md 引用的每个 procedure 是否真实存在。
检查 build.md 依赖的 _bmad/scripts/render_skill.py 是否始终可用。
扩充三个 mode 文件，明确架构判断、执行边界和验证责任。
在 SKILL.md 中加入“规范状态/实际状态冲突不得静默处理”。
P1：加入最小架构闭环

只增加四个文件：

TEXT
architecture-contract.template.yaml
engineering-state.template.yaml
architecture-preflight.md
state-reconcile.md

只修改三个节点：

TEXT
任务开始 → Architecture Preflight
编码执行 → 关键事件触发 Recheck
完成之前 → State Reconciliation
P2：加入算法和调试增强

增加：

TEXT
algorithm-fit.md
architecture-debug.md
correct-course.md

连续两次同类失败后强制停止局部修补，并重新审查：

问题定义；
组件边界；
数据所有权；
接口契约；
算法假设；
NFR 预算。
P3：做对照评估

选择 10–20 个真实任务，对比：

原始 BMAD-Solo；
BMAD-Solo + AGAS。

记录：

未批准架构偏差数量；
Review 阶段才发现的跨层问题；
重复调试次数；
Story/任务 reopen 次数；
NFR 回归数量；
错把局部结果当作全局完成的次数；
token 和执行时间增量；
人工介入次数及原因。
Summary

dotfiles-bmad-solo 当前解决了“如何根据任务路由到不同模式”，但还没有解决“每次行动是否仍符合架构，以及新证据是否改变了下一步”的问题。

最有效的升级不是再增加一个 Architect Agent，而是加入四项核心能力：

将架构文档编译为可检查的 architecture-contract.yaml；
在编码前和重大变化后运行 Architecture Conflict Gate；
用 Active Engineering State 保存事实、假设、失败、证据和开放义务；
完成前从代码与真实验证结果重建状态，并检查架构漂移。

这样才能让架构从“上游读过的一份文档”，变成控制 plan、编码、算法、调试和 Review 的运行时系统。