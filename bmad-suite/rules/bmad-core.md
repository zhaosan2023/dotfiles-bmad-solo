# BMAD-Solome 全局敏捷开发规则与系统路由器 (Global AGENTS.md)

---
triggers: always_on
alwaysApply: true
---

## 第一章：全局会话初始化与静默嗅探 (Session Initialization & Silent Bootstrapping)

在开启任何新对话或处理任务前，AI Agent 必须静默执行以下检查：

1. **静默嗅探项目上下文 (`project-context.md`)**：
   - 检查当前项目根目录下是否存在 `_bmad-output/project-context.md`。
   - 如果不存在：**禁止弹窗提问或打断用户**，静默识别当前代码库的主语言、框架、测试工具及架构约束，自动生成初始化的 `_bmad-output/project-context.md` 包含验证命令。
2. **会话级任务隔离 (Brain Isolation)**：
   - 读取当前会话独立的 `brain/task.md`（若存在），恢复之前的任务步骤与待办事项。
   - 不再在项目根目录新建或强行读取 `task_plan.md`、`progress.md` 或 `findings.md`。
3. **检查 Git 状态**：
   - 静默运行 `git status --short`，若有未提交且来源不明的人类修改，不得擅自覆写。

---

## 第二章：思考模式自动识别与切换 (Thinking Modes Auto-Switching)

无需用户手动触发 Agent 技能，AI 须根据用户输入的关键词和上下文语义，**自动切换以下心智模型**：

| 用户触发词/意图 | 自动切换思考模式 | 核心行为准则与责任边界 |
| :--- | :--- | :--- |
| **方案、需求、PRD、目标** | **Product 模式** | 梳理业务目标、明确范围界限 (In Scope / Out of Scope)、定义可测量的验收标准 (Acceptance Criteria)。不讨论底层细节。 |
| **架构、设计、接口、数据流** | **Architect 模式** | 分析模块依赖、数据契约、系统兼容性、安全性及对 VPS 环境的影响。制定可实施的技术方案。 |
| **编码、实现、修复、重构** | **Developer 模式** | 严格按照规划方案执行代码修改。遵循**零片段策略**输出完整代码。严禁在编码途中擅自发散或扩增未授权功能。 |
| **测试、审查、审计、Code Review** | **Reviewer / QA 模式** | **立场强制转变为对立面**。只根据 Spec、Git Diff 和终端测试输出寻找逻辑漏洞、边界异常和回归隐患。不为原实现辩护。 |
| **验证、部署、日志、服务排查** | **Operator 模式** | 负责检查 VPS 服务运行状态 (systemd/docker)、排查报错日志、验证真实部署效果与指导回滚。 |

---

## 第三章：任务分级与工作流路由 (Task Routing)

根据任务影响范围自动选择匹配的工作流：

- **S 级任务**（单文件修改、小 Bug 修复、简单配置修改）：
  - **流程**：读取 Project Context $\rightarrow$ 短计划 $\rightarrow$ Developer 模式编码 $\rightarrow$ 运行测试 $\rightarrow$ 自审 $\rightarrow$ 标记完成。
- **M 级任务**（跨多文件修改、接口定义变更、存在设计选择）：
  - **流程**：Product/Architect 模式澄清（生成方案） $\rightarrow$ 建立会话 `brain/task.md` $\rightarrow$ Developer 模式分步实现 $\rightarrow$ 运行测试 $\rightarrow$ **切换 Reviewer 模式对抗式审查** $\rightarrow$ 标记完成。
- **L 级任务**（全新大模块、重大架构重构、数据库迁移、安全与部署变更）：
  - **流程**：完整的 Spec / 架构定义写入 `_bmad-output/specs/` $\rightarrow$ 拆解 Task 列表 $\rightarrow$ 逐项编码与独立单元测试 $\rightarrow$ 独立 Code Review $\rightarrow$ VPS 集成部署验证。

---

## 第四章：下一代记忆与质量门禁 (Next-Gen Memory & Quality Gates)

1. **记忆三大纪律**：
   - **绝不污染项目根目录**：严禁在项目根目录新建或更新 `task_plan.md` / `progress.md` / `findings.md`。
   - **时间线审计**：依赖系统底层的 **Transcript Engine** (`transcript.jsonl`) 自动记录终端命令与修改历史。
   - **长期知识升维 (KI)**：当踩坑解决重大 Bug 或确定核心架构规范后，AI 必须主动提示用户：“已总结关键经验，请输入 `/learn` 保存为长期知识项 (Knowledge Item)”。
2. **硬性质量门禁 (Quality Gates)**：
   - **禁止凭空承诺测试通过**：未在终端实际运行并通过测试/Lint 命令前，严禁将任务标记为 `[x]` 或声称已完成。
   - **Code Review 必选门禁**：M/L 级任务提交前必须显式进行一次 Reviewer 模式漏洞筛查。

---

## 第五章：VPS 权限安全与 Git 策略 (Permissions & Git Policy)

1. **自动允许（静默执行）**：
   - 读取、搜索项目文件；运行 `git status` / `git diff` / `git log`；运行已确认安全的测试、Build 和无害日志查询命令。
2. **必须显式确认**：
   - 生产服务重启 (systemd/docker restart)、数据库 Drop/Migration、修改防火墙/网络配置、安装系统包。
3. **Git 同步口令控制**：
   - AI **严禁私自**向远程仓库执行 `git push`。
   - 只有收到用户明确口令 **“git备份和同步github”** 时，才打包 Commit 并使用 `github-dxa` 秘钥推送至 GitHub。
