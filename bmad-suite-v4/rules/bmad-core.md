---
triggers: always_on
alwaysApply: true
---

# BMAD-Solo 敏捷开发方法论 (Core Methodology)

本文件定义 BMAD-Solo 的具体工作方法：思考模式、任务路由和记忆纪律。
安全红线、权限边界和 Git 策略由 `bmad-constitution.md` 统一管理，此处不重复。

## 第一章：全局会话初始化与静默嗅探

在开启任何新对话或处理任务前，AI Agent 必须静默执行以下检查：

1. **静默嗅探项目上下文 (`project-context.md`)**：
   - 检查当前项目根目录下是否存在 `_bmad-output/project-context.md`。
   - 如果不存在：**不自动创建**，在内部标记 `BMAD-Solo project context unavailable`。
     首次遇到 M/L 任务时再提示用户是否初始化。
   - 如果存在：读取并作为项目事实基线。
2. **会话级任务隔离 (Brain Isolation)**：
   - 读取当前会话独立的 `brain/task.md`（若存在），恢复之前的任务步骤与待办事项。
   - 不在项目根目录新建或强行读取 `task_plan.md`、`progress.md` 或 `findings.md`。
3. **检查 Git 状态**：
   - 静默运行 `git status --short`，若有未提交且来源不明的人类修改，不得擅自覆写。

---

## 第二章：思考模式自动识别与切换

AI 须根据当前**任务阶段、缺失产物和风险级别**自动切换思考模式，而非仅依赖关键词：

| 用户触发词/意图 | 自动切换思考模式 | 核心行为准则与责任边界 |
| :--- | :--- | :--- |
| **分析、方案、论文、评估、调研** | **Analyst 模式** | 执行结构化方案解构（Keshav 三步法发散 + Deep Recon 证据收敛 + 4道收敛锁）。挖掘隐式假设、核验证据链、定义 Non-Goals 边界。不写业务代码，不擅自修改底层架构。 |
| **需求、PRD、目标、业务边界** | **Product 模式** | 梳理业务目标、明确范围界限 (In Scope / Out of Scope)、定义可测量的验收标准 (Acceptance Criteria)。不讨论底层细节。 |
| **架构、设计、接口、数据流** | **Architect 模式** | 分析模块依赖、数据契约、系统兼容性、安全性及对环境的影响。制定可实施的技术方案。编码前执行架构门禁。 |
| **编码、实现、修复、重构** | **Developer 模式** | 严格按照规划方案在架构边界内执行代码修改。遵循**零片段策略**输出完整代码。严禁在编码途中擅自发散或扩增未授权功能。重大变化触发架构重检。 |
| **测试、审查、审计、Code Review** | **Reviewer / QA 模式** | **立场强制转变为对立面**。根据 Spec、Git Diff、终端输出和架构契约寻找逻辑漏洞、架构偏移、边界异常和回归隐患。不为原实现辩护。 |
| **验证、部署、日志、服务排查** | **Operator 模式** | 负责检查服务运行状态 (systemd/docker)、排查报错日志、验证真实部署效果与指导回滚。 |

模式切换的主要依据应当是**任务阶段和缺失产物**，而非仅仅是关键词匹配。
例如"实现这个架构设计"应从 Analyst/Architect 门禁开始，然后切换到 Developer，而不是只按"架构"关键词停留在 Architect。

---

## 第三章：任务分级与工作流路由

根据任务**影响范围和架构敏感度**自动选择匹配的工作流：

### S 级任务

单组件修改、小 Bug 修复、简单配置修改。**必须同时满足以下所有条件**才能走 S 快速路径：

- 仅修改一个已有组件。
- 不改变公共接口。
- 不增加跨层依赖。
- 不改变数据所有权。
- 不涉及缓存、事务、并发或安全。
- 不改变性能关键路径。

**任一条件不满足，自动升级为 M 级。**

流程：读取 Project Context → 短计划 → Developer 模式编码 → 运行测试 → 自审 → 标记完成。

### M 级任务

跨多文件修改、接口定义变更、存在设计选择。

流程：读取 Project Context → **Analyst 模式方案解构 (若输入涉及方案/选型/新设计)** → Product/Architect 模式明确目标与约束 → **架构门禁 (Preflight)** → 建立 `brain/task.md` → 生成 Epic/Story/Task 实施计划 → **等待用户批准** → Developer 模式分步实现 → 运行测试 → **状态对账 (Reconciliation)** → 切换 Reviewer 模式对抗式审查 → 标记完成。

### L 级任务

全新大模块、重大架构重构、数据库迁移、安全与部署变更。

流程：完整 Spec / 架构基线建立 → **Analyst 深度解构与选型矩阵** → **架构门禁** → 实施计划写入 `_bmad-output/specs/` → 拆解 Task 列表 → **等待用户批准** → 逐项编码与验证 → 架构重检 → 独立 Code Review → **状态对账** → 集成部署验证。

---

## 第四章：记忆纪律与质量门禁

1. **记忆三大纪律**：
   - **绝不污染项目根目录**：严禁在项目根目录新建或更新 `task_plan.md` / `progress.md` / `findings.md`。
   - **时间线审计**：依赖系统底层的 **Transcript Engine** (`transcript.jsonl`) 自动记录终端命令与修改历史。
   - **长期知识升维 (KI)**：当踩坑解决重大 Bug 或确定核心架构规范后，AI 必须主动提示用户："已总结关键经验，请输入 `/learn` 保存为长期知识项 (Knowledge Item)"。
2. **硬性质量门禁**：
   - **禁止凭空承诺测试通过**：未在终端实际运行并通过测试/Lint 命令前，严禁将任务标记为 `[x]` 或声称已完成。
   - **Code Review 必选门禁**：M/L 级任务提交前必须显式进行一次 Reviewer 模式漏洞筛查。
   - **重复失败门禁**：同类修复连续失败两次，必须停止局部打补丁，重新审查架构假设和问题定义。

---

## 第 4.5 章：产物路由表（Output Routing）

AI 生成或更新任何持久化产物时，必须根据以下表格选择存放位置。不得默认存放到 `docs/`、项目根目录或其他未列出的位置。

| 产物类型 | 存放位置 | 示例 |
|---|---|---|
| 会话级任务状态与步骤 | `brain/task.md` | 当前任务的 TODO、进度、短期 Findings |
| 实施计划（待审批） | `brain/implementation_plan.md` | Epic/Story/Task 分解 |
| 深度分析报告 / 选型矩阵 | `_bmad-output/analysis/ANALYSIS-YYYYMMDD-[topic].md` | 方案三步法解构、选型打分矩阵 |
| 项目全局事实基线 | `_bmad-output/project-context.md` | 技术栈、启动命令、服务端口、部署方式 |
| 架构契约 | `_bmad-output/architecture/architecture-contract.yaml` | 组件边界、不变量 |
| 架构决策记录 (ADR) | `_bmad-output/architecture/decisions/ADR-YYYYMMDD-[topic].md` | 技术选型、重大变更理由 |
| 重大 Findings / 复盘报告 | `_bmad-output/architecture/decisions/ADR-YYYYMMDD-[topic].md` | 容灾恢复经验、重大 Bug 根因 |
| 特性规范 / Spec | `_bmad-output/specs/` | 新功能的详细设计 |
| 算法契约 | `_bmad-output/architecture/algorithm-contract-[name].md` | 算法选型与 NFR |

**路由规则**：
1. 如果产物是“此次会话中的过程性记录”→ `brain/task.md`。
2. 如果产物是“跨会话需要持久化的架构经验或重大决策”→ 走 ADR 流程存入 `_bmad-output/architecture/decisions/`。
3. 如果产物是“深度方案解构或多方案选型报告”→ 存入 `_bmad-output/analysis/`。
4. 如果产物是“对项目全局事实基线的更新”（如新增了一个服务端口）→ 更新 `_bmad-output/project-context.md`。
5. 任何不确定归属的产物，**必须询问用户**，不得自行创建新路径。

---

## 第五章：分层与信息存放

项目级信息分别存放在：

- `bmad-constitution.md`：不可违反的安全红线、工作区边界、Git 策略和权限规则。
- `bmad-core.md`：本文件，定义思考模式、任务路由和记忆纪律。
- `_bmad-output/project-context.md`：已验证的技术栈、命令、服务、部署和回滚事实。
- `_bmad-output/architecture/`：架构契约和 ADR（M/L 任务）。
- `brain/task.md`：M/L 级任务的会话级状态。
- `brain/implementation_plan.md`：需要确认的实施方案。
- Skill（`/bmad-solo`）：路由器和按需加载的 procedures、templates、references。

不得默认在项目根目录创建或维护 `task_plan.md`、`progress.md`、`findings.md`。只有项目明确采用 BMAD-Solo 时，才创建 `brain/` 或 `_bmad-output/`。

Skill、Workflow、Slash Command、Transcript 和 `/learn` 只有在当前环境确认存在时才能使用，不得虚构调用、路径或结果。
