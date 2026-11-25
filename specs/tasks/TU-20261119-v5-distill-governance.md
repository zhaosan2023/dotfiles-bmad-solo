---
schema_version: "1.0-draft"
task_id: "TU-20261119-V5-DISTILL-GOVERNANCE"
instance_id: "inst-20261119-v5-distill-governance-01"
contract_version: "3"
candidate_version: null
status: READY
session_id: "5b7d8929-8847-4221-afcb-69890d9cc80c"
scenario: structural
impact_tier: M
parent_objective:
  objective_id: "OBJ-20261119-V5-DISTILL-GOVERNANCE"
  expected_result: "完成 dotfiles-bmad-solo V5.1 纯 Vibe 零工具名宿主治理与独立受管生命周期落地：核心方法论安装于非自动发现目录 ~/.local/share/bmad-solo/v5/，优先以单一薄入口 ~/.cline/rules/bmad-v5-router.md 适配 Cline（100% 物理隔离 ~/.gemini/ V4，工作区零注入），实现 manifest.json 精确卸载与明确四态 --doctor 健康检查，彻底消除与 aurora2api <tool_call> 协议冲突并通过隔离全生命周期测试与网关首轮兼容验证"
  source_ref: "docs/analysis/ANALYSIS-20261119-aurora2api-tool-loop-compiler.md + 2026-11-25 用户需求修订与 DM/DR 最终裁决确认"
inputs:
  - "docs/analysis/ANALYSIS-20261119-aurora2api-tool-loop-compiler.md"
  - "docs/adrs/ADR-20261023-cline-native-plan-act-and-backpressure.md"
  - "bmad-suite-v4/cline/templates/bmad-router.md"
  - "bmad-suite-v4/roo/settings/custom_modes.yaml"
  - "bmad-suite-v4/skills/ana-solo/SKILL.md"
  - "bmad-suite-v4/skills/bmad/SKILL.md"
  - "scripts/distill_v5_kernel.py"
  - "scripts/assemble_v5_context.py"
  - "scripts/dispatch_v5.sh"
  - "scripts/deploy_managed.py"
  - "specs/governance/00-governance-index.md"
  - "specs/governance/02-task-unit-schema.md"
  - "specs/governance/05-host-adaptation.md"
  - "specs/governance/v5-context-manifest.yaml"
  - "specs/tasks/TU-20261119-aurora2api-tool-loop-compiler.md"
  - "/home/veryfd/project/aurora2api/internal/api/chat.go (只读协议基线参考，禁止修改)"
  - "/home/veryfd/project/aurora2api/internal/upstream/studioglobal/payload.go (只读协议基线参考，禁止修改)"
cs_specification:
  scope: >
    在 /home/veryfd/dotfiles-bmad-solo 中实现并验证 V5.1（纯 Vibe、零工具名、宿主无关核心、Cline 优先试点、可完美卸载与明确体检）全套本地资产与隔离验证：
    1. 编译蒸馏重构（scripts/distill_v5_kernel.py -> 本地产物 dist/v5/）：
       - 生成 3 份纯 Vibe、零工具名、零底层协议词的受管资产：
         a) dist/v5/bmad-v5-router.md（~400 Tokens 极简全局薄路由：按宿主模式分流 Plan -> ana-solo.md、Act -> bmad-solo.md；绝对路径指向 ~/.local/share/bmad-solo/v5/skills/*.md；禁止模型在对话中创建或修改任何 .clinerules / .cline/rules/ / ~/.cline/rules/ 文件；采用能力自适应纯 Vibe 契约，不耦合特定 Agent/MCP）；
         b) dist/v5/skills/ana-solo.md（Plan 阶段方法论：三遍阅读、证据分层、DM/DR；允许读取 Linux $USER 权限任意指定路径且披露不绕过宿主审批；纯咨询仅会话交付；获准结晶仅写目标项目文档治理路径 docs/analysis/、docs/adrs/[PROPOSED]、specs/tasks/TU-*.md，绝不碰生产代码、基线与终端；若宿主 Plan 模式无写能力则诚实说明并在会话输出完整正文）；
         c) dist/v5/skills/bmad-solo.md（Act 阶段方法论：消费明确需求或获准结晶方案；仅在存在 specs/tasks/_active.md 的仓库核验指针，普通仓库不误阻塞；五条终端执行不变量纯 Vibe 表达、四类场景安全阀、真实回执与 2 次同根因熔断）；
    2. 细粒度双向断言与删正文/注毒变异测试（tests/test_distill_v5_kernel.py）：
       - 拆解 REQUIRED_CLAUSES 逐条独立校验 3 份产物正文（无宽泛 | 逃逸）；
       - 升级 FORBIDDEN_CLAUSES 拦截全部已枚举具体工具名（含尖括号/反引号/裸名）与 XML/JSON/Native Tools/网关后缀协议词；
       - 实现删正文与注毒负向变异测试；
    3. 独立受管生命周期与完美卸载/四态健康检查（scripts/dispatch_v5.sh 及配套管理逻辑）：
       - 采用独立 XDG 受管核心根 <HOME>/.local/share/bmad-solo/v5/（含 manifest.json、deploy.lock、backups/、skills/*.md [0444 只读]），排他锁彻底移出 ~/.cline/；
       - Cline 单一薄入口 <HOME>/.cline/rules/bmad-v5-router.md（0644 保证 Cline UI 开关可用）；绝不向任何业务仓库注入 .cline/rules/*；硬编码拒绝读写 <HOME>/.gemini/；
       - 实现 --uninstall：基于 manifest.json 校验正文 SHA-256（去 frontmatter）后精确移除所有受管文件与空目录，用户手工改过的文件拒删报警（除非显式 --force），不碰第三方文件、业务仓库与 ~/.gemini/；
       - 实现 --doctor [--workspace <path>]：明确输出唯一裁决 HEALTHY(0) / DEGRADED(0) / UNINSTALLED(0) / BROKEN(1) / CONFLICT(2)，分离检测 Cline UI 开关态（disabled frontmatter）与正文 SHA-256 完整性，扫描全局 ~/.cline/rules/、~/.cline/skills/ 及目标工作区 .clinerules / .cline/rules/* / .cline/skills/* 中的 V4/V5 混杂与历史僵尸残留；
       - 支持隔离根目录参数（如 --home-dir <tmp>），供自动化测试全量演练安装/体检/开关切换/篡改检测/冲突检测/回滚/卸载，零触碰真实用户家目录；
    4. 伴随旧资产清理：清理 scripts/assemble_v5_context.py 与 specs/governance/v5-context-manifest.yaml 中的硬编码工具名与 text_xml_bridge 残留（并将工作区规则注入明确标为非默认可选/已停用路径）；
    5. 隔离验收与网关兼容验证：创建并运行 tests/test_dispatch_v5.py 与 tests/test_distill_v5_kernel.py 及既有 tests/test_assemble_v5_context.py；在获准前提下执行 1 次携带新版 dist/v5/bmad-v5-router.md + tools 的 aurora2api 首轮探针验证。
  excludes:
    - "修改、测试或部署 /home/veryfd/project/aurora2api 网关代码、容器或删除其工作区历史文件"
    - "触碰、读取写入或修改 ~/.gemini/ 下的任何 Antigravity-Gemini V4 生产资产"
    - "未经二次明确确认，向真实 ~/.cline/rules/ 或 ~/.local/share/bmad-solo/v5/ 写入、覆盖或卸载任何文件"
    - "在 V5.1 规则正文或薄链接技能中保留任何具体工具名或底层传输格式（XML/JSON/Native Tools/网关后缀）指令"
    - "向任何业务项目注入 .cline/rules/active-context.md 或 .cline/rules/bmad-core.md"
    - "为特定 Agent 单独开发专属 MCP 或绑定 Roo 专用配置"
    - "宣称 Cline 运行时已物理加载生效或 Plan 模式绕过客户端硬权限"
    - "修改 docs/project-context.md 事实基线或篡改已接受的历史 ADR 正文"
    - "自动提交、推送 Git 分支或清理无关未跟踪改动"
  outputs:
    - "scripts/distill_v5_kernel.py"
    - "dist/v5/bmad-v5-router.md"
    - "dist/v5/skills/ana-solo.md"
    - "dist/v5/skills/bmad-solo.md"
    - "scripts/dispatch_v5.sh"
    - "scripts/assemble_v5_context.py"
    - "specs/governance/v5-context-manifest.yaml"
    - "tests/test_distill_v5_kernel.py"
    - "tests/test_dispatch_v5.py"
    - "specs/tasks/TU-20261119-v5-distill-governance.md"
  acceptance_criteria:
    - "CRIT-01: 【纯 Vibe 零工具名与零协议冲突】dist/v5/ 全部 3 份产物、scripts/distill_v5_kernel.py、scripts/assemble_v5_context.py 与 specs/governance/v5-context-manifest.yaml 零具体工具名、零 XML/JSON 传输禁令、零网关后缀耦合，与 aurora2api <tool_call> 协议零冲突。"
    - "CRIT-02: 【Plan/Act 薄链接隔离与读写路径完整】薄路由仅指向 ~/.local/share/bmad-solo/v5/skills/{ana-solo,bmad-solo}.md；清晰界定 $USER 任意路径可读、Plan 仅写文档治理路径且不碰代码/终端（含能力缺失诚实降级）、Act 仅在有 specs/tasks/_active.md 的仓库校验指针、禁止模型自改规则文件。"
    - "CRIT-03: 【细粒度双向断言与变异测试】tests/test_distill_v5_kernel.py 覆盖全部独立正向条款、全部已枚举工具名/协议词反向拦截及删正文/注毒变异测试，退出码为 0。"
    - "CRIT-04: 【独立受管核心、完美卸载与四态健康检查】tests/test_dispatch_v5.py 在隔离临时 HOME 中完整验证：deploy -> doctor HEALTHY(0) -> skills 0444 & router 0644 -> Cline UI disabled:true 切换不误报篡改(DEGRADED 0) -> 正文篡改检出(BROKEN 1) -> V4/V5 多启用规则冲突检出(CONFLICT 2) -> ~/.gemini/ 写保护拒绝 -> --uninstall 零残留清理 -> doctor UNINSTALLED(0)，且全程零触碰真实家目录。"
    - "CRIT-05: 【本地产物隔离与范围纯净】dist/v5/ 产物与生成器一致；真实 ~/.cline/rules/、~/.local/share/bmad-solo/v5/ 与 ~/.gemini/ 未被本阶段修改；改动严格限定在 dotfiles-bmad-solo 获准文件。"
    - "CRIT-06: 【网关首轮兼容实测】向运行中 aurora2api 发送携带新版 dist/v5/bmad-v5-router.md + 标准 tools 的首轮请求，取得真实退出码 0 回执，验证正常产出 tool_calls 与 finish_reason=tool_calls（若网关未运行则如实标记 BLOCKED/UNKNOWN，不编造通过）。"
kcp_verification:
  environment_ref: "Linux / Python 3.11 / bash"
  checks:
    - check_id: KCP-01
      criterion_refs: [CRIT-01, CRIT-02]
      required: true
      verification_type: unit_test
      command: "python3 scripts/distill_v5_kernel.py --dry-run < /dev/null"
      command_status: AVAILABLE
      cwd: "/home/veryfd/dotfiles-bmad-solo"
      timeout_seconds: 30
    - check_id: KCP-02
      criterion_refs: [CRIT-01, CRIT-02, CRIT-03, CRIT-04]
      required: true
      verification_type: unit_test
      command: "python3 -m unittest tests/test_distill_v5_kernel.py tests/test_dispatch_v5.py tests/test_assemble_v5_context.py < /dev/null"
      command_status: PLANNED_NOT_YET_CREATED
      cwd: "/home/veryfd/dotfiles-bmad-solo"
      timeout_seconds: 30
    - check_id: KCP-03
      criterion_refs: [CRIT-04, CRIT-05]
      required: true
      verification_type: config_syntax
      command: "bash scripts/dispatch_v5.sh --help < /dev/null"
      command_status: AVAILABLE
      cwd: "/home/veryfd/dotfiles-bmad-solo"
      timeout_seconds: 15
    - check_id: KCP-04
      criterion_refs: [CRIT-05]
      required: true
      verification_type: diff_cleanliness
      command: "git status --porcelain < /dev/null"
      command_status: AVAILABLE
      cwd: "/home/veryfd/dotfiles-bmad-solo"
      timeout_seconds: 15
    - check_id: KCP-05
      criterion_refs: [CRIT-06]
      required: true
      verification_type: unit_test
      command: "获准工程验收阶段执行：向 http://127.0.0.1:8080/v1/chat/completions 发送携带 dist/v5/bmad-v5-router.md + tools 的首轮请求，断言 HTTP 200 与 finish_reason=tool_calls"
      command_status: PLANNED_NOT_YET_CREATED
      cwd: "/home/veryfd/dotfiles-bmad-solo"
      timeout_seconds: 30
sod_review:
  responsible_actor: "bmad-solo-engineer"
  supervisor_actor: "ana-solo-auditor"
  review_required: true
  minimum_independence: separate_actor
  review_ref: null
  authority_source_ref: "2026-11-25 用户指令：'/ana-solo 1,2'"
  approval_scope: contribution_acceptance_only
gate_status:
  authority_kind: platform
  authority_ref: null
  snapshot_contract_version: "3"
  snapshot_candidate_version: null
  cs: UNKNOWN
  sr: UNKNOWN
  accepted: false
  observed_at: null
authorization:
  source_ref: "2026-11-25 用户指令：'/ana-solo 1,2'（批准写入 DM/DR 最终裁决并解锁 READY；授权随后切入 /bmad-solo 执行本地编译、测试与隔离目录全生命周期验证；未经二次确认禁止覆写真实 ~/.cline/rules/）"
  allowed_paths:
    - "scripts/distill_v5_kernel.py"
    - "scripts/dispatch_v5.sh"
    - "scripts/assemble_v5_context.py"
    - "specs/governance/v5-context-manifest.yaml"
    - "dist/v5/"
    - "tests/test_distill_v5_kernel.py"
    - "tests/test_dispatch_v5.py"
    - "tests/test_assemble_v5_context.py"
    - "specs/tasks/TU-20261119-v5-distill-governance.md"
    - "specs/tasks/_active.md"
  allowed_operations: ["read", "edit", "create", "test_local_isolated"]
  phase: "READY_FOR_BMAD_SOLO_LOCAL_EXECUTION"
  real_host_install_allowed: false
  promotion_allowed: false
  archival_allowed: false
requires_adr: true
adr_file: "docs/adrs/ADR-20261125-v51-pure-vibe-thin-router.md"
---

# TU-20261119-V5-DISTILL-GOVERNANCE：V5.1 纯 Vibe 薄链接治理与独立受管生命周期

- **任务标识**：`TU-20261119-V5-DISTILL-GOVERNANCE`
- **契约版本**：`v3`（2026-11-25 吸纳全部 DM + DR 最终裁决并解锁 `READY`；已绑定架构提案 [ADR-20261125-v51-pure-vibe-thin-router.md](file:///home/veryfd/dotfiles-bmad-solo/docs/adrs/ADR-20261125-v51-pure-vibe-thin-router.md)）
- **当前状态**：`READY`（所有前置架构决策已由 DM + DR 闭环并获用户 `/ana-solo 1,2` 确认，等待切入 `/bmad-solo` 启动本地实施与隔离验证；**二次确认门禁**：未经用户再次确认，绝不覆写真实 `~/.cline/rules/` 或 `~/.local/share/bmad-solo/v5/`）
- **场景**：`structural`
- **影响级别**：`M`
- **历史来源**：[ANALYSIS-20261119-aurora2api-tool-loop-compiler.md](file:///home/veryfd/dotfiles-bmad-solo/docs/analysis/ANALYSIS-20261119-aurora2api-tool-loop-compiler.md)（原始会话 `c7af13a9-8627-487d-995d-3256c0edc997`）
- **最终裁决来源**：2026-11-25 `/ana-solo` 跨仓库取证、Anthropic Advanced Tool Use 边界审计及三门禁 DM + DR 决策（会话 `5b7d8929-8847-4221-afcb-69890d9cc80c`）
- **目标工作区**：`/home/veryfd/dotfiles-bmad-solo`
- **计划绑定**：本 Task Unit 的“执行阶段”章节

---

## 1. 最终 DM + DR 架构裁决记录（已锁定）

### 1.1 工具/MCP 与方法论的严格分层边界
1. **API 网关层（`aurora2api`）**：独占 `<tool_call>{...}</tool_call>` 协议编译、定界解析与流式生命周期；本任务绝不修改网关代码。
2. **Agent + 上游 Model**：直接基于客户端暴露的 Tool Schema 协商选择工具与 MCP 工具；dotfiles-V5.1 **不区分 Agent、零 MCP 耦合、不做工具/MCP 优选引导**。
3. **dotfiles-V5.1 方法论层**：通过**极致做减法**（零工具名、零传输协议词、极简常驻薄路由 + 按 Plan/Act 冷加载）释放首轮上下文注意力，仅以纯 Vibe 语言定义模式职责、读写路径边界、证据纪律与背压熔断。

### 1.2 三大硬门禁（G1–G3）与最终选型（DM 裁决：`RECOMMENDED`）
- **G1（完美卸载 + 清晰健康度）**：必须有 `manifest.json` 驱动的零残留精确卸载与明确四态健康检查（`HEALTHY` / `DEGRADED` / `CONFLICT` / `BROKEN` / `UNINSTALLED`）。
- **G2（免受 Cline 自加载/模型自配置污染，杜绝 V4/V5 混杂）**：现场取证证实 `aurora2api` 曾同时存在 5 份 V4/V5 混杂规则，且 Cline 存在 `Skills` 自动扫描目录。
- **G3（物理隔离 Gemini V4，先优先 Cline 试点跑稳）**：Antigravity-Gemini V4 运行顺畅，严禁触碰 `~/.gemini/`。

**被否候选**：
- ❌ `~/.gemini/config/plugins/bmad-suite/skills/`（违反 G3，污染 Gemini V4）；
- ❌ `~/.cline/skills/`（违反 G2，会被 Cline 原生 `Skills` 面板自动扫描加载）；
- ❌ 直链开发仓库 `bmad-suite-v4/skills/`（违反 G1/G3，与开发分支和 V4 源码强耦合）；
- ❌ 为 Cline Plan 单独造专属写入 MCP（违反“不区分 Agent”原则）。

**最终采纳方案（候选 4）**：
```text
~/.local/share/bmad-solo/v5/          # 宿主无关独立 XDG 受管核心根（不被任何 Agent 自动扫描）
├── manifest.json                     # 唯一所有权与指纹真理源（受管文件列表、正文 SHA-256、版本、宿主挂载）
├── deploy.lock                       # 排他锁（彻底移出 ~/.cline/）
├── backups/                          # 受管备份快照
└── skills/                           # 绝对路径薄链接目标（0444 只读，防模型误改）
    ├── ana-solo.md                   # V5.1 纯 Vibe Plan 分析与文档结晶方法论
    └── bmad-solo.md                  # V5.1 纯 Vibe Act 代码实施与本地验证方法论

~/.cline/rules/bmad-v5-router.md      # Cline 唯一受管薄入口（0644 保证 UI 开关可用，工作区零注入）
```

### 1.3 DR 反向审查与关键防呆修正
1. **UI 开关与篡改检测解耦**：`skills/*.md` 设为 `0444`；`bmad-v5-router.md` 保持 `0644` 以兼容 Cline UI 读写 `disabled: true` frontmatter；`--doctor` 分离检测 `enabled_state`（YAML frontmatter）与 `body_sha256`（剥离 frontmatter 后的正文指纹），避免用户点开关被误报篡改。
2. **禁止模型自改规则**：薄路由正文显式禁止模型在对话中创建或修改 `.clinerules` / `.cline/rules/*` / `~/.cline/rules/*`。
3. **历史残留不越权删业务库文件**：`--doctor --workspace <path>` 检出历史 V4/V5 残留并分红/黄灯清单提示（有启用态冲突报 `CONFLICT`，仅禁用态残留报 `DEGRADED`），绝不擅自删除其他业务仓库文件；同时检测 `~/.cline/rules/bmad-core.md` 旧命名遗留。
4. **宿主 Plan 写入与外路径读取可逆接缝**：规则采用能力自适应纯 Vibe 契约（有写能力就按治理路径落盘，无写能力就诚实输出正文并说明受限）；若后续真实 Cline 会话实测强拦截 `~/.local/share/bmad-solo/v5/skills/*.md` 读取，可平滑将纯 Vibe 正文单文件内联进同一受管入口 `bmad-v5-router.md`，`manifest.json`、卸载与 `--doctor` 零返工复用。

---

## 2. V5.1 纯 Vibe 规则与生命周期契约

### 2.1 三份编译产物规格（`dist/v5/`）
1. **`dist/v5/bmad-v5-router.md`（极简薄路由，目标 ~350–500 Tokens）**：
   - 仅依据本轮宿主明确模式信号分流：Plan → 读取 `~/.local/share/bmad-solo/v5/skills/ana-solo.md`；Act → 读取 `~/.local/share/bmad-solo/v5/skills/bmad-solo.md`；模式信号缺失或冲突时停止副作用操作并说明。
   - 明确禁止模型在对话中新建、修改或启用/禁用任何 `.clinerules`、`.cline/rules/`、`~/.cline/rules/` 规则文件。
   - 零工具名、零 XML/JSON 传输协议词、零网关后缀词。
2. **`dist/v5/skills/ana-solo.md`（Plan 方法论）**：
   - 三遍阅读（Map / Evidence / Recon）与 `[FACT]` / `[UNKNOWN]` 证据分层；
   - DM 候选筛选（硬门禁先行、默认定性、禁止编造权重/分数）与 DR 反向审查（找反例与最小可逆接缝）；
   - 读取边界：允许按需读取 Linux `$USER` 权限可访问的任意指定路径文件（同时声明不绕过宿主审批/沙箱）；
   - 写入边界：纯咨询仅会话交付；获准结晶仅新建或编辑目标项目文档治理路径——`docs/analysis/ANALYSIS-YYYYMMDD-<topic>.md`、`docs/adrs/ADR-YYYYMMDD-<topic>.md`（初始 `PROPOSED`）、`specs/tasks/TU-<task_id>.md`（显式指定路径优先）；绝不碰生产代码、测试代码、构建/部署配置、`docs/project-context.md`、终端与 Git 写操作；宿主 Plan 无写能力时诚实说明并在会话交付完整正文。
3. **`dist/v5/skills/bmad-solo.md`（Act 方法论）**：
   - 直接消费明确需求或已获准结晶计划，不与重型分析结晶混用；
   - Preflight 作用域收敛：仅在存在 `specs/tasks/_active.md` 的仓库先核验指针与绑定契约；普通无 `specs/tasks/` 目录的业务仓库直接按用户明确需求实施，不误触发阻塞；
   - 五条终端执行不变量（纯 Vibe 表达：串行执行、分级超时 `15s/30s/600s`、前台同步看退出码、封闭标准输入 `< /dev/null`、修改文件直接编辑而不用命令行重定向拼代码）；
   - 四类场景安全阀（算法 / 结构 / 缺陷 / 运维——运维严禁启动容器跑业务单测）；
   - 真实回执驱动与连续 2 次同根因失败熔断；不得用文字假装已执行或编造结果。

### 2.2 生命周期命令契约（`scripts/dispatch_v5.sh`）
支持选项：`--deploy`（默认）、`--test`、`--doctor`、`--status`、`--rollback`、`--uninstall`、`--force`、`--home-dir <DIR>`（隔离测试根，默认 `$HOME`）、`--workspace <DIR>`（供 `--doctor` 扫描业务仓库冲突）。
- **硬保护**：脚本显式校验并拒绝任何指向 `<HOME>/.gemini` 的读写操作。
- **状态与退出码（`--doctor`）**：
  - `HEALTHY` -> exit `0`
  - `DEGRADED` -> exit `0`（输出结构化告警列表）
  - `UNINSTALLED` -> exit `0`
  - `BROKEN` -> exit `1`
  - `CONFLICT` -> exit `2`

### 2.3 正反向断言清单（`scripts/distill_v5_kernel.py` + `tests/test_distill_v5_kernel.py`）
- **正向断言（`REQUIRED_CLAUSES`）**：逐条独立验证三份产物的所有核心条款正文（无宽泛 `|` 逃逸）。
- **反向断言（`FORBIDDEN_CLAUSES`）**：拦截所有已枚举具体工具名（`read_file`、`read_files`、`search_codebase`、`search_files`、`list_files`、`apply_patch`、`apply_diff`、`replace_in_file`、`write_to_file`、`execute_command`、`run_commands`、`ask_question`、`ask_followup_question`、`submit_and_exit`、`attempt_completion`）及协议冲突词（`严禁携带.*tools`、`必须使用 XML`、`严禁使用 XML`、`严禁.*纯文本 JSON`、`Text-XML`、`Native Tools`、`:academic`、`:factcheck`、`delta\.reasoning_content`、`docs/plan\.md`）。
- **变异测试**：删正文必触发对应正向条款失败；注毒（含反引号/尖括号变体）必触发对应反向断言失败。

---

## 3. 执行阶段（`/bmad-solo` 获准本地实施路径）

### 阶段 0：基线核验与指针同步
1. 核验 `specs/tasks/_active.md` 与本契约 v3，将 `_active.md` 的 `contract_version` 同步为 `"3"`（不修改其他字段）。
2. 运行 `git status --porcelain < /dev/null` 与分支/HEAD 检查并记录基线；保护全部既有未提交改动，绝不自动 stash/reset/commit。

### 阶段 1：V5.1 编译器与伴随资产重构
1. 重写 `scripts/distill_v5_kernel.py`，支持生成 `dist/v5/bmad-v5-router.md`、`dist/v5/skills/ana-solo.md`、`dist/v5/skills/bmad-solo.md`，并落实逐条正反断言。
2. 清理 `scripts/assemble_v5_context.py` 与 `specs/governance/v5-context-manifest.yaml` 中的硬编码工具名与 `text_xml_bridge` 残留，标明工作区规则注入不再作为 V5.1 默认路径。

### 阶段 2：独立受管生命周期管理器实现（含 `--uninstall` 与 `--doctor`）
1. 升级 `scripts/dispatch_v5.sh`（可调用仓库内标准库 Python 辅助脚本或纯 bash+python3 实现 JSON/SHA-256 处理，不引入第三方依赖），完整实现 `manifest.json` 所有权管理、`<HOME>/.local/share/bmad-solo/v5/deploy.lock` 锁隔离、`skills/*.md` `0444` 保护、`bmad-v5-router.md` `0644`、frontmatter 与正文指纹分离校验、`~/.gemini/` 硬写保护、`--uninstall` 精确卸载与四态 `--doctor [--workspace <path>]`。

### 阶段 3：自动化单元测试、变异测试与隔离全生命周期验收
1. 编写 `tests/test_distill_v5_kernel.py`（逐条正反断言 + 删正文/注毒变异测试）与 `tests/test_dispatch_v5.py`（基于 `tempfile.TemporaryDirectory` 模拟隔离 `HOME` 与虚拟业务工作区，跑通 `deploy` / `doctor HEALTHY` / Cline UI `disabled:true` `DEGRADED` / 正文篡改 `BROKEN` / V4-V5 混杂 `CONFLICT` / `~/.gemini` 保护 / `rollback` / `--uninstall` / `UNINSTALLED` 全链路）。
2. 本地编译生成 `dist/v5/` 产物，串行运行 `KCP-01`、`KCP-02`、`KCP-03`、`KCP-04`，确认全部退出码为 0 且真实家目录零改动。

### 阶段 4：网关兼容探针与审查交接（真实安装需二次确认）
1. 若本机 `aurora2api`（`127.0.0.1:8080`）在运行，执行 `KCP-05` 首轮只读探针请求，收集真实回执确认零工具调用冲突；若未运行则明确标为未执行/`[UNKNOWN]`。
2. 交付全部命令、目录、退出码、差异审查结果及真实家目录零触碰证明；**停止于此，等待用户审阅回执后再二次确认是否正式部署至真实 `~/.local/share/bmad-solo/v5/` 与 `~/.cline/rules/bmad-v5-router.md`**。

---

## 4. 完成与阻塞条件

- 只有 `CRIT-01` 至 `CRIT-06` 均有对应可复核物理回执（或对运行期未知项如实披露并获审阅确认），且未触碰 `~/.gemini/` 与未获二次确认前的真实 `~/.cline/rules/`，方可申请独立审查（SR）验收。
- 任何关键测试失败、隔离边界突破或未获授权触碰真实宿主目录，立即进入 `BLOCKED`。
