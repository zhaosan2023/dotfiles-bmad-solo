最优方案不是简单“隐藏 49 个 Skill”，也不是把它们粗暴合并成 5 个大 Skill，而是采用 “1 个可发现入口 + 5 种内部思考模式 + N 个按需加载能力模块”。最终 Antigravity 的 / 菜单只保留一个 /bmad-solo 作为人工兜底入口；正常使用时，用户只描述目标，由 AGENTS.md 自动判断任务等级、切换模式并加载对应能力，不需要手动输入任何 BMAD 命令。

Key findings
49 个命令出现并不说明自动路由失败，而是因为它们仍然作为独立 SKILL.md 注册在 Antigravity 的技能目录中。官方机制会把已注册 Skill 自动转换为 Slash Command，因此只修改 gemini-solo-v2.md 无法清理 / 菜单。
图中的方案 1“全部移出 Skills”会失去 Skill 的标准能力发现和渐进加载机制。
方案 2“直接合并成五个大 Skill”容易形成五份超长 Prompt，导致上下文膨胀和能力边界模糊。
方案 3 所依赖的
skills.json exclude
，目前没有足够的官方证据证明 Antigravity IDE 2.1.1 支持，不应作为核心设计。
方案 4 保持原样虽然风险最低，但没有完成 BMAD-Solo 的产品目标。
最佳方案是方案 1 和方案 2 的改良组合：只注册一个路由 Skill，五种模式及原来的工作流全部降级为该 Skill 内部的 references、procedures、templates 和 scripts。
Confirmed facts

Antigravity 将 Skill 定义为包含 SKILL.md 的能力目录，供 Agent 在特定任务中采用。
 对已注册 Skill，Antigravity 会将它们自动暴露为 Slash Command，因此当前 49 个 bmad-* 项目是技能注册结构的直接结果，而不是 GEMINI.md 路由规则能够控制的 UI 行为。

规则与技能是两个不同层面：

GEMINI.md、AGENTS.md 或 Rules：规定 Agent 应当怎样判断、约束和路由任务。
Skills：提供可按需加载的专业执行能力。
Slash Command：是 Antigravity 对已注册 Skill 的用户界面暴露方式。

因此，想减少 Slash Command，必须减少注册目录中的 SKILL.md 数量，而不是只加强“自动切换思考模式”的文字规则。

BMAD 本身将分析、架构、实现等职责分别包装为技能或 Agent；官方仓库中的技能也使用独立 SKILL.md 和相对路径引用配套资源。
 这适合多人角色化 BMAD，但不完全适合您希望的单会话自动执行模式。

What remains inference

以下部分需要在您的 Antigravity IDE 2.1.1 实机验证：

移除或重命名 49 个被索引的 SKILL.md 后，IDE 是否需要重启窗口、重载工作区或重建索引。
全局和项目级技能是否同时存在，导致项目中删除后仍看到同名命令。
Antigravity IDE 是否支持“注册 Skill 但不显示 Slash Command”的隐藏字段。目前证据不足，不建议依赖。
Agent 是否能百分之百自动激活一个描述范围很广的 bmad-solo Skill。规则可以显著加强路由，但自然语言 Agent 路由不可能做到形式系统意义上的绝对确定。

因此建议保留唯一的 /bmad-solo，作为自动路由失败时的人工兜底和诊断入口。

What the evidence suggests
1. 目标架构：One Gateway Skill

建议最终结构：

TEXT
GEMINI.md
AGENTS.md

.agents/
└── skills/
    └── bmad-solo/
        ├── SKILL.md
        ├── references/
        │   ├── mode-product.md
        │   ├── mode-architect.md
        │   ├── mode-developer.md
        │   ├── mode-reviewer.md
        │   ├── mode-operator.md
        │   ├── capability-map.md
        │   └── procedures/
        │       ├── clarify-requirements.md
        │       ├── create-product-brief.md
        │       ├── architecture-decision.md
        │       ├── implementation-plan.md
        │       ├── code-review.md
        │       ├── test-design.md
        │       ├── deploy-check.md
        │       └── ...
        ├── templates/
        │   ├── task.md
        │   ├── implementation-plan.md
        │   └── review-report.md
        └── scripts/
            ├── detect-project.sh
            └── verify-project.sh

_bmad-output/
└── project-context.md

brain/
├── task.md
└── implementation_plan.md

关键约束：

.agents/skills/ 下只保留一个 SKILL.md。
五种模式文件不能再命名为 SKILL.md。
原来 49 个 Skill 中有价值的具体流程移动到 references/procedures/。
Agent Persona、欢迎语、菜单、多人交接仪式不迁移。
脚本、模板和检查清单继续保留。
SKILL.md 只做路由，不承载所有流程正文。

这样 Slash 菜单理论上只剩：

TEXT
/bmad-solo

但普通任务不需要用户调用它。

2. 不要用关键词切换，要用状态机切换

impleplan-solo.md 当前的“看到方案/需求就切 Product，看到架构/设计就切 Architect”过于脆弱。例如“实现这个架构设计”同时命中 Architect 和 Developer。

更可靠的是按当前任务状态和预期产物路由：

TEXT
INTAKE
  ↓
PRODUCT       明确目标、范围、非目标、验收标准
  ↓
ARCHITECT     仅在存在接口、依赖、数据流或不可逆决策时进入
  ↓
DEVELOPER     按已确认约束实现
  ↓
REVIEWER_QA   对 Diff、测试结果和验收标准做对抗式检查
  ↓
OPERATOR      仅在需要运行、日志、发布、迁移或回滚时进入
  ↓
DONE

允许的回退：

TEXT
REVIEWER_QA → DEVELOPER
OPERATOR → DEVELOPER
ARCHITECT → PRODUCT

路由依据应是：

当前任务阶段。
当前缺失的产物。
操作风险和可逆性。
是否涉及外部接口、数据、部署。
最近一次真实验证结果。

关键词只能作为弱信号，不能作为主要规则。

3. 重新定义五种模式边界
模式	负责	不负责	典型能力
Product	目标、范围、用户价值、验收标准	技术实现细节	brainstorming、research、product brief、PRD、story slicing
Architect	接口、依赖、数据流、约束、技术决策	直接大规模编码	architecture、ADR、API design、risk analysis
Developer	最小范围实现、测试、修复	擅自改变需求或架构	build、refactor、bug fix、unit test
Reviewer/QA	对抗式审查、边界、回归、安全、验收	为自己的实现找理由	code review、test design、traceability、security review
Operator	环境、服务、日志、发布、回滚	未授权生产变更	diagnostics、deployment、migration check、rollback

对于横跨多个模式的任务，不要同时“扮演五个人”，而应顺序切换。例如：

TEXT
新增登录限流
→ Product：明确限流对象和验收标准
→ Architect：选择存储位置和多实例一致性策略
→ Developer：实现
→ Reviewer/QA：检查绕过路径、并发和回归
→ Operator：仅在用户授权部署后检查服务与日志
4. 把 49 个 Skill 变成能力注册表

建议创建 references/capability-map.md：

MD
# BMAD-Solo Capability Map

| Capability | Mode | Trigger condition | Procedure | Required output |
|---|---|---|---|---|
| clarify-requirements | Product | 验收标准不明确 | procedures/clarify-requirements.md | Acceptance Criteria |
| create-product-brief | Product | 新产品或大功能 | procedures/create-product-brief.md | Product Brief |
| architecture-decision | Architect | 存在多个重大技术方案 | procedures/architecture-decision.md | ADR |
| implementation-plan | Architect | M/L 级任务准备实现 | procedures/implementation-plan.md | brain/implementation_plan.md |
| build | Developer | 约束与计划已充分 | procedures/build.md | Code + Tests |
| code-review | Reviewer | 出现代码 Diff | procedures/code-review.md | Review findings |
| test-design | Reviewer | 高风险或复杂行为 | procedures/test-design.md | Test matrix |
| diagnose-runtime | Operator | 服务异常或用户要求查日志 | procedures/diagnose-runtime.md | Diagnosis |
| deploy | Operator | 用户明确授权部署 | procedures/deploy.md | Deployment evidence |

路由器只读取注册表，确定需要哪个 procedure 后，再加载对应文件。这样既保留原 BMAD 工作流价值，又不会每次把 49 个流程全部塞入上下文。

5. 唯一入口 Skill 应当很短

.agents/skills/bmad-solo/SKILL.md 的核心可以设计为：

MD
---
name: bmad-solo
description: >
  Automatically routes software tasks through Product, Architect,
  Developer, Reviewer/QA, and Operator modes. Use for non-trivial
  planning, implementation, review, diagnosis, and deployment tasks.
---

# BMAD-Solo Router

## Objective

Complete the user's task through one continuous AI session.
Do not simulate a multi-agent meeting and do not ask the user to select
an internal BMAD workflow unless a material product decision is required.

## Routing

1. Read project rules and verified project context.
2. Classify the task as S, M, or L.
3. Determine the current phase from task state and missing output.
4. Load only the relevant mode reference.
5. Select procedures from `references/capability-map.md`.
6. Execute within the selected mode's boundary.
7. After implementation, switch to Reviewer/QA.
8. Enter Operator only when runtime work is needed.
9. Respect all confirmation and safety boundaries.

## Progressive loading

Do not load every reference.

- Product: `references/mode-product.md`
- Architect: `references/mode-architect.md`
- Developer: `references/mode-developer.md`
- Reviewer/QA: `references/mode-reviewer.md`
- Operator: `references/mode-operator.md`

Load one procedure at a time from `references/procedures/`.

## Completion gate

A code task is complete only when:

- relevant implementation is finished;
- Diff has been reviewed;
- relevant verification has real output;
- acceptance criteria are checked;
- unverified items and risks are reported.
6. AGENTS.md 负责自动入口，而不是重复五种模式全文

项目规则只保留自动触发逻辑：

MD
# BMAD-Solo Project Router

For ordinary questions and trivial edits, respond directly.

For any task involving planning, multi-file changes, architecture,
implementation, debugging, testing, review, deployment, or task
continuation, automatically use the `bmad-solo` skill.

Do not ask the user to choose Product, Architect, Developer,
Reviewer/QA, Operator, or a BMAD workflow. Those are internal modes.

Determine the mode from task state, required output, risk, and
verification status—not from keywords alone.

Task levels:

- S: localized, reversible, no public interface/data/deployment impact.
- M: multi-file or behavior change requiring a short tracked plan.
- L: cross-system, migration, security-sensitive, or hard-to-reverse.

S:
understand → implement → verify → review

M:
clarify → task state → plan when needed → implement → verify → review

L:
requirements → explicit architecture/plan approval → staged
implementation → verification → adversarial review → operation only
with authorization

GEMINI.md 继续只承担您现在定义的全局宪法、安全红线和授权边界，不要把 49 个能力映射再次写进去。

7. 对原 49 个 Skill 做三类迁移

不要机械地把所有 Skill 都保留下来，应先进行清点：

删除

Agent 欢迎语。
多角色菜单。
Party Mode。
模拟角色交接。
与 Solo 路由重复的 Help/Orchestrator。
仅用于让用户选择下一工作流的 Skill。

合并

多个相近的需求澄清流程。
重复的故事创建和任务拆分。
重复的代码审查流程。
快速开发和普通开发中重复的实现规则。

保留为 Procedure

产品研究。
PRD/Brief。
架构决策。
UX 设计检查。
实施计划。
代码实现。
测试设计。
对抗式审查。
安全检查。
部署、诊断和回滚。

最终可能不是 49 个 procedure，而是大约 15–25 个真正独立的能力模块。

Conflicting evidence or uncertainty
skills.json 隐藏方案

目前没有找到足够的官方证据证明可以通过 skills.json 将 Skill 从 Slash 菜单排除，同时保持自动发现。因此该方案属于未经验证的实现假设，不应作为正式架构。

如果实机发现 Antigravity 后续版本确实支持类似：

JSON
{
  "exposeAsSlashCommand": false
}

那么可以重新考虑注册五个模式 Skill 并隐藏它们。但在确认官方 Schema 和实际行为之前，不要创建虚构配置。

是否应该保留五个注册 Skill

五个注册 Skill 比 49 个整洁，但仍有两个问题：

/ 菜单仍会出现五个用户不应该手动选择的内部模式。
单个任务跨模式时，需要上层编排器管理切换，否则五个 Skill 仍然是相互独立的入口。

因此，“五个注册 Skill”可以作为过渡方案，但不是最终最优方案。

Transcript 和 /learn

impleplan-solo.md 建议完全依赖 Transcript 代替任务进度，这不够稳健。Transcript 是审计记录，不是结构化、可恢复的任务状态；长会话恢复时仍应使用精简的 brain/task.md。

同样，/learn 是否存在、保存在哪里以及能否跨 VPS 使用，都必须以当前环境真实能力为准。您在 gemini-solo-v2.md 中规定“只有确认存在才能使用”是正确的，不应让核心流程依赖 /learn。

全局静默初始化

不建议默认对每个打开的项目自动生成 _bmad-output/project-context.md：

可能污染未采用 BMAD-Solo 的仓库。
可能误判构建、测试和部署命令。
与您现有“只有项目明确采用 BMAD-Solo 才创建目录”的规则冲突。

更安全的方式是检测到项目未初始化时，仅在内部标记：

TEXT
BMAD-Solo project context unavailable

第一次遇到 M/L 任务时再询问是否初始化，或者只做只读扫描、先展示候选内容，不直接写文件。

Open questions

实施前只需要确认几个环境事实：

当前 49 个 Skill 来自项目级 .agents/skills/、全局 ~/.gemini/config/skills/，还是两者都有。
Antigravity IDE 删除 Skill 后是否需要 reload window 才更新索引。
49 个目录中哪些属于 Agent 外壳，哪些包含不可替代的脚本、模板和工作流。
AGENTS.md 在当前 Antigravity IDE 中是否被稳定自动加载。
brain/ 是否加入 Git，以及任务完成后采用删除、归档还是保留策略。
Sources worth trusting most
Antigravity 官方 Skills 文档：用于确认 Skill 的标准目录化能力模型。
Antigravity 官方 Plugins & Skills 文档：用于确认注册 Skill 会自动转成 Slash Command。
Antigravity 官方 Rules 文档：用于区分 Rules 与 Skills 的职责。
Antigravity 官方最佳实践：用于确认 GEMINI.md、AGENTS.md 和真实测试验证的定位。
BMAD 官方技能和定制文档：用于提取流程资源，但不必保留原始多 Agent 交互外壳。
Recommended next step

建议先做一个可回滚的试点，不要立即删除原 49 个 Skill。

盘点所有 Skill：
TEXT
skill-name
原始角色
实际能力
依赖脚本/模板
建议：DELETE / MERGE / PROCEDURE
目标模式
创建唯一的：
TEXT
.agents/skills/bmad-solo/SKILL.md

将五种模式和首批 5–10 个高频流程迁入 references/，但不要创建额外 SKILL.md。

将原 49 个 Skill 临时移动到非索引备份目录，例如：

TEXT
_bmad-solo-source/legacy-skills/

不要立即删除，以便比较和回滚。

重载 Antigravity IDE，验证 / 菜单是否只剩 /bmad-solo。

使用以下场景验收：

“修复这个简单错误”：应走 S → Developer → Reviewer。
“设计并实现登录限流”：应走 Product → Architect → Developer → Reviewer。
“检查刚才改动”：应直接进入 Reviewer/QA。
“查看服务为什么启动失败”：应进入 Operator，但不擅自重启。
“部署到生产”：应在执行前请求明确授权。
“继续当前任务”：应读取 brain/task.md，而不是重新规划。
观察自动路由是否稳定。如果稳定，再删除 Legacy Skill；如果不稳定，通过改进 bmad-solo/SKILL.md 的描述和 AGENTS.md 路由规则修复，而不是恢复 49 个 Slash Command。
Summary

最终推荐架构是：

TEXT
全局安全宪法：GEMINI.md
项目自动路由：AGENTS.md
唯一注册入口：bmad-solo/SKILL.md
五种内部模式：references/mode-*.md
具体执行能力：references/procedures/*.md
长期项目事实：_bmad-output/project-context.md
当前任务状态：brain/task.md

这会实现您真正想要的 BMAD-Solo：

用户只说任务，不选角色。
Agent 自动判断 S/M/L。
Agent 按阶段自动切换五种思考模式。
每种模式只加载当前需要的能力。
原 49 个 Skill 的有效内容仍然保留。
Slash 菜单从 49 个降至 1 个。
/bmad-solo 只用于兜底，不是正常工作入口。
对抗式审查、真实验证、安全确认和 Git 边界继续保留。