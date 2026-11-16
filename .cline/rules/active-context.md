# BMAD-Solo V5 动态任务上下文 (Active Task Context Bundle)

> **装配时间戳**：`2026-11-16T09:55:04Z`  
> **装配来源**：`specs/governance/v5-context-manifest.yaml` (v1.1)  
> **工作区基线状态**：`LOADED` | **活动任务状态**：`ACTIVE`  
> **定位**：工作区级动态上下文。由 In-Context Push 自动装配，随任务状态动态流转。

---

### 0. 治理导航常驻锚点 (Governance Anchors)
- **治理总索引**：`specs/governance/00-governance-index.md` (全生命周期与业务流规范)
- **架构决策目录**：`docs/adrs/` (架构决策记录，当前已接受 ADR-20261116)
- **任务工件与归档**：`specs/tasks/` (活动 Task Unit 契约与 archive/ 历史归档)
- **项目事实基线**：`docs/project-context.md` (项目级唯一事实基线真理源)
- **探针取证纪律**：只读分析与审计（`/ana-solo`）必须且只能调用只读工具（`read_file`、`search_files`、`list_files`）主动阅读物理证据，严禁无证据凭空推演；实施修改（`/bmad-solo`）使用 `replace_in_file` / `write_to_file`。

---

### 1. 项目事实基线 (Project Context Baseline)
- **基线文件来源**：`docs/project-context.md` (已加载)

# Project Context
- **Project Name:** dotfiles-bmad-solo
- **Primary Purpose:** A quick backup and deployment sync shortcut tool (dotfiles setup with BMAD-Solo support).
- **Language/Stack:** Shell/Markdown
- **Architecture:** Local configuration, Git-based sync.
- **Reference Docs:** Currently stored in project root (e.g., GEMINI.md). Additional reference docs should be placed in `docs/` or `references/` and listed here.
## 2026-10-08：Roo Code 三级生命周期治理与受管部署
- 架构决策见[本任务 ADR](adrs/ADR-20261008-roocode-bmad-v42-lifecycle-and-governance.md:3)，已根据当前用户的人类架构师裁决转正；实施证据及历史授权记录的归档目标为[本任务计划](../specs/tasks/archive/20261102T120208Z-document-closeout/legacy-plans/plan-20261008-roocode-bmad-v42-lifecycle-and-governance.md)。会话标识未知，不编造。
- 规则采用显式计划优先、相关活动计划绑定、归档只读发现与授权恢复的三级路由；默认入口缺失是正常生命周期状态，不自动执行最新归档。实现与阶段验证来源为本任务计划的阶段 1–3 执行记录；不将规则或参考模型视为运行时行为保证。
- 已读取的[模式配置](../bmad-suite-v4/roo/settings/custom_modes.yaml:5)限定分析模式为读取、受限编辑和浏览，不授予终端，编辑路径排除生产文件与本事实基线；工程模式保留终端能力。
- 本轮客户端返回的显式计划配置校验、部署状态诊断及 Git 差异检查均退出 0。部署状态确认 47 个受管文件和 1 个模式目标摘要匹配；此结果不证明当前会话加载，也不证明部署与当前工作树实时同步。
- 本轮[事务复核脚本](../.scratch/legacy-bmad-output-20261102T120208Z/verify-deployment-20261008.py:29)退出 0，确认 49 个事务目标摘要与权限匹配、48 份备份摘要及存储权限匹配，17 项记录为已应用。事务标识为 transaction-4f2bb72068ff4f95a692c03330e4654c，日志 SHA-256 为 68dcd1d2c20725b178351d219b2960b83aac2690701764f2a7b1962baea12054；未执行真实恢复，不保证排除外部并发写入。
- 历史验证溯源：计划阶段 4 记录 19 个隔离分发测试文件共 148 项通过，规则契约另有 20 项通过记录；这些是历史执行记录与当前用户确认，不是本轮重跑结果。
- 验收边界由当前用户于 2026-10-08 明确调整：客户端原生工具拦截委托宿主扩展平台，仓库以已核验的受限模式静态配置及受管部署为交付基线，不要求内部 Agent 自指黑盒探测。阶段 4 据此合格；这不是客户端权限拒绝、配置加载或完整生命周期交互已经验证的声明。
- 受管分发保护第三方资产，使用预检、摘要复核、备份、单文件原子替换及事务记录；不承诺跨目录整体原子性、强制终止后自动恢复或所有 Roo 版本兼容。远程 CI 未由本轮执行。
- 旧 ADR 与旧暂停计划保持独立，本次转正不代表旧任务完成。工作树已有前阶段实现及未跟踪资产；差异检查通过不等于工作树无改动，尚不能声明已提交、推送或最终洁净。

---

### 2. 当前活动任务契约 (Active Task Unit)
- **任务标识**：`TU-20261116-V5-DYNAMIC-ASSEMBLER` (实例: `inst-20261116-v5-dynamic-assembler-01`)
- **当前状态**：`COMPLETED` (待独立审计验收，归档前保留指针寻址) (场景: `structural`, 影响级别: `M`)
- **交付目标**：完成 BMAD-Solo V5 Phase 2 动态任务上下文装配器与工作区自动化注入管线，实现项目基线与单焦点任务契约的自动化组合与 Token 软背压控制
- **贡献范围**：开发动态任务上下文装配器 scripts/assemble_v5_context.py 与单元测试 tests/test_assemble_v5_context.py，实现基于清单驱动的工作区基线提取、单焦点任务计划绑定、敏感信息过滤与工作区级注入 (.cline/rules/active-context.md)
- **严禁事项 (Excludes)**：
  - 直接修改其他项目的业务生产代码
  - 未获授权的 Git 自动提交或推送
  - 覆盖全局 ~/.cline/rules/bmad-core.md
- **验收标准 (Acceptance Criteria)**：
  - CRIT-01: 严格依据 specs/governance/v5-context-manifest.yaml 解析来源、规则与门禁。
  - CRIT-02: 准确读取 docs/project-context.md 提取架构基线；若缺失则报告降级警告（SUSPEND_AND_WARN_DEGRADED）。
  - CRIT-03: 严格通过 specs/tasks/_active.md 唯一锁定活动任务，校验 TU-*.md 存在性与 APPROVED/READY/IN_PROGRESS 状态；空闲时输出明确空闲标识，冲突时硬阻断。
  - CRIT-04: 执行 Token 软背压规划评估（动态上下文目标 800 ~ 1,200 Tokens，超限告警不截断）。
  - CRIT-05: 支持 --inject-workspace 模式，通过原子写方式安全注入到当前工作区 .cline/rules/active-context.md，供 Cline 热加载。
- **法定核验命令 (KCP Verifications)**：
  - [KCP-01] (unit_test): `python3 -m unittest tests/test_assemble_v5_context.py`
  - [KCP-02] (config_syntax): `python3 scripts/assemble_v5_context.py --inject-workspace --dry-run`
