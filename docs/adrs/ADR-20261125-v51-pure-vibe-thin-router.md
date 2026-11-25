---
adr_id: "ADR-20261125-V51-PURE-VIBE-THIN-ROUTER"
status: PROPOSED
date: "2026-11-25"
owner: "项目维护者"
supersedes: "ADR-20261116-BMAD-V5-IN-CONTEXT-PUSH"
supersedes_scope: "在设计上替代 ADR-20261116 中已过时的‘客户端严禁携带 tools 字段 / text_xml_bridge’、‘向业务仓库注入 .cline/rules/active-context.md’、‘清单中枚举具体工具名’及‘锁文件置于 ~/.cline/’条款；不追改 ADR-20261116 历史 ACCEPTED 记录"
task_file: "specs/tasks/TU-20261119-v5-distill-governance.md"
analysis_file: "docs/analysis/ANALYSIS-20261119-aurora2api-tool-loop-compiler.md"
scenario: structural
impact_tier: M
runtime_verified: false
session_id: "5b7d8929-8847-4221-afcb-69890d9cc80c"
authorization: "2026-11-25 用户指令：'/ana-solo 补建'（批准保存 PROPOSED ADR 并绑定至当前 Task Unit，不自动转正、不更新事实基线）"
---

# ADR-20261125：BMAD-Solo V5.1 纯 Vibe 薄路由、零工具协议干预与独立受管生命周期

- **状态**：`PROPOSED`（待独立审查 SR 验收及另行转正授权）
- **日期**：2026-11-25
- **决策所有者**：项目维护者
- **关联任务契约**：[TU-20261119-v5-distill-governance.md](../../specs/tasks/TU-20261119-v5-distill-governance.md)
- **前置分析依据**：[ANALYSIS-20261119-aurora2api-tool-loop-compiler.md](../analysis/ANALYSIS-20261119-aurora2api-tool-loop-compiler.md) 及 2026-11-25 跨仓库只读取证与 DM/DR 裁决
- **替代关系**：仅在设计上替代 [ADR-20261116-bmad-v5-in-context-push-architecture.md](ADR-20261116-bmad-v5-in-context-push-architecture.md) 的旧通信协议、工具名枚举与工作区规则注入条款；不修改历史记录，不涉及 [ADR-20261028](ADR-20261028-adaptive-backpressure-and-lossless-distillation.md) 的自适应背压原则。

---

## 1. 背景与一手取证事实 (`[FACT]`)

1. **V5.0 规则与 `aurora2api` 线上工具协议正面冲突**：
   - 70% API 网关侧（`/home/veryfd/project/aurora2api`）已完成 `TU-20261119` 协议编译器闭环并演进至 `ADR-20261123` 严格定界流式透传（`internal/api/chat.go:854-886, 1192-1195, 2349-2353` 与 `internal/upstream/studioglobal/payload.go:172-190`）：上游 Web 模型必须通过 `<tool_call>{"name":"...","arguments":{...}}</tool_call>` 发起调用，且网关取消自主纠偏重发（无合法 `<tool_call>` 直接返回 `finish_reason: "stop"`）。
   - 旧版 V5.0（`dist/bmad-core.md`）中“严禁使用 XML 标签包装工具”“严禁在普通正文中输出 XML 标签或纯文本 JSON”及硬编码工具名（`<read_file>`、`ask_question`、`submit_and_exit`）与网关指令直接矛盾，易压制上游模型输出导致工具幻觉或停机。
2. **多版本混杂与 Cline 自动发现污染**：
   - 现场取证核实 `~/project/aurora2api` 曾同时并存 5 份 V4/V5 规则文件（全局 `bmad-core.md` + 工作区 `active-context.md`、`bmad-core.md`、`bmad-router.md`、`.clinerules`）以及两套自动扫描的 `.cline/skills/{ana-solo,bmad-solo}` 旧 V4 技能包。
   - 旧 `scripts/dispatch_v5.sh` 缺乏 `--uninstall` 精确卸载与明确健康度判定，且在 `~/.cline/` 下创建 `.bmad_dispatch.lock`。
3. **宿主隔离与通用性硬约束**：
   - Antigravity-Gemini 原生模型下 V4（`~/.gemini/config/plugins/bmad-suite/`）运行顺畅，V5 试点期间必须 100% 物理隔离 `~/.gemini/`；
   - dotfiles-V5.1 方法论核心必须保持**宿主无关（不区分 Agent）**，仅在部署适配层优先服务 Cline，待稳定后再扩展至其他宿主。

---

## 2. 架构决策

### 决策一：三层彻底解耦与“纯 Vibe 零工具名”铁律
- **API 网关层（`aurora2api`）**：独占 `<tool_call>` 协议编译、定界解析与流式生命周期；
- **客户端 Agent 与上游 Model**：直接基于实时声明的 Tool Schema 自主协商工具与 MCP 工具选择（dotfiles 不做工具/MCP 路由优选，不附工具调用示例）；
- **dotfiles-V5.1 方法论层**：全部采用自然语言意图（Vibe 语言），**零具体工具名、零 XML/JSON 传输编码禁令、零网关后缀耦合**，只定义模式职责、读写路径边界、证据纪律与背压熔断。

### 决策二：Plan / Act 绝对路径薄链接强分离与读写路径边界
- 全局常驻资产压缩为极简薄路由（`~535 tokens`），不同时常驻两套完整长规则：
  - **Plan 模式 → 按需冷加载 `ana-solo.md`**：负责三遍阅读、证据分层、DM/DR 与获准文档结晶；允许读取当前 Linux `$USER` 权限可访问的任意指定路径（不绕过客户端审批）；纯咨询仅会话交付；获准结晶仅写入目标项目文档治理路径（`docs/analysis/ANALYSIS-YYYYMMDD-<topic>.md`、`docs/adrs/ADR-YYYYMMDD-<topic>.md` 初始 `PROPOSED`、`specs/tasks/TU-<task_id>.md`，显式路径优先），绝不触碰生产代码、测试代码、构建配置、`docs/project-context.md`、终端与 Git 写操作；若当前宿主 Plan 模式无写能力则诚实降级为会话输出正文。
  - **Act 模式 → 按需冷加载 `bmad-solo.md`**：专职消费明确需求或已获准计划，实施代码修改与本地验证，不与文档结晶混在同一模式；Preflight 指针检查仅对存在 `specs/tasks/_active.md` 的仓库生效，普通业务仓库不误阻塞；遵守五条终端执行不变量、四类场景安全阀、真实回执与连续 2 次同根因熔断。
- 规则正文显式禁止模型在对话中新建、修改、删除或切换 `.clinerules`、`.cline/rules/`、`~/.cline/rules/` 及 `~/.local/share/bmad-solo/` 下的规则文件。

### 决策三：独立 XDG 受管核心、Cline 单一薄入口与零工作区注入
采用独立于任何 Agent 自动扫描目录的 XDG 受管安装根：
```text
~/.local/share/bmad-solo/v5/          # 非任何 Agent 自动发现目录
├── manifest.json                     # 唯一所有权与正文 SHA-256 指纹真理源 (0600)
├── deploy.lock                       # 排他锁（移出 ~/.cline/）
├── backups/                          # 受管备份快照
└── skills/                           # 绝对路径薄链接目标 (0444 只读)
    ├── ana-solo.md
    └── bmad-solo.md

~/.cline/rules/bmad-v5-router.md      # Cline 唯一受管薄入口 (0644 兼容 UI 开关)
```
- **零工作区规则注入**：V5.1 默认绝不向任何业务仓库写入 `.cline/rules/active-context.md` 或 `.cline/rules/bmad-core.md`，从根源消除跨项目多版本混杂。
- **物理冻结 `~/.gemini/`**：部署、体检与卸载逻辑硬编码拒绝读写任何包含 `.gemini` 的路径。

### 决策四：`manifest.json` 精确卸载与明确健康度判定
- **`--uninstall`**：严格基于 `manifest.json` 校验正文 SHA-256 后精确移除受管资产与空目录；用户手工修改过的文件拒绝静默删除（除非显式 `--force`）；零触碰第三方规则、业务仓库文件与 `~/.gemini/`。
- **`--doctor [--workspace <path>]`**：输出确定裁决及退出码——`HEALTHY (0)`、`DEGRADED (0)`、`UNINSTALLED (0)`、`BROKEN (1)`、`CONFLICT (2)`；将 Cline UI 的 `disabled: true` YAML frontmatter 开关与规则正文 SHA-256 分离校验，避免切换 UI 开关误报篡改；同时扫描全局与目标工作区的 `.clinerules`、`.cline/rules/`、`.cline/skills/` 冲突与 `~/.gemini/` 泄露。

---

## 3. 被否候选与 DM 理由

| 被否候选 | 否决依据（硬门禁 / DM 取舍） |
| :--- | :--- |
| 复用 `~/.gemini/config/plugins/bmad-suite/skills/` 作为薄链接源 | 违反 Gemini V4 物理隔离硬门禁（G3），V5 迭代或卸载风险波及 Antigravity-Gemini 生产环境。 |
| 将 V5 技能放入 `~/.cline/skills/` | 违反防自加载硬门禁（G2），会被 Cline `Skills` 面板自动扫描发现并触发 `use_skill` 冲突。 |
| 薄链接直接指向开发仓库 `bmad-suite-v4/skills/` | 违反独立卸载与版本稳定门禁（G1/G3），与开发分支及 V4 源码耦合，切分支即导致漂移。 |
| 为 Cline Plan 模式单独开发专属文档写入 MCP | 违反“dotfiles-V5.1 不区分 Agent”架构原则，且 Cline Plan 是否放行 MCP 属宿主私有能力边界。 |
| 在 dotfiles 内编写工具/MCP 优选指引与参数示例 | 违反零工具名与宿主无关约束，与客户端动态 Schema 漂移并挤占首轮上下文注意力。 |

---

## 4. 架构不变量与 DR 反向审查边界

### 核心不变量
1. **零工具名与零协议词不变量**：`dist/v5/` 全部生成资产及伴随 V5 配置须通过细粒度正反静态断言及删正文/注毒变异测试。
2. **宿主隔离不变量**：V5 生命周期工具在任何模式下绝不向 `~/.gemini/` 写入文件，也不自动向业务仓库注入工作区规则。
3. **单一真相源不变量**：受管所有权只由 `~/.local/share/bmad-solo/v5/manifest.json` 裁决，卸载与健康度不得靠猜测文件名推断。
4. **文档槽位分离不变量**：`_active.md` 只做活动焦点薄指针，Task Unit 绑定执行计划与 `adr_file`，ADR 保存架构裁决，`docs/project-context.md` 仅在整体验收通过并另获授权后登记稳定事实。

### DR 反例与最小可逆接缝
- **反例 1（Cline UI 开关修改 frontmatter）**：已通过 `bmad-v5-router.md` 保持 `0644` 与 frontmatter/正文哈希分离校验化解。
- **反例 2（特定客户端拦截工作区外绝对路径读取）**：若某宿主强拦截 `~/.local/share/bmad-solo/v5/skills/*.md` 读取，可平滑将纯 Vibe 正文单文件内联进同一受管入口 `bmad-v5-router.md`，`manifest.json`、卸载与 `--doctor` 无需重构。
- **反例 3（Cline 原生 Plan 模式无本地写能力）**：由 `ana-solo.md` 的能力自适应条款诚实降级为会话输出完整结晶正文，不伪造落盘，也不迫使 V5.1 绑定特定客户端补丁。

---

## 5. 转正条件与证据边界

- 本 ADR 当前保持 **`PROPOSED`**；具体验证命令、退出码与隔离测试回执由绑定的 [TU-20261119-v5-distill-governance.md](../../specs/tasks/TU-20261119-v5-distill-governance.md) 承载，不在此处镜像执行流水。
- 仅当全部必需验证门禁（`KCP-01` ~ `KCP-05`）通过、取得独立审查（SR）接受结论并获得用户明确转正授权后，方可更新为 `ACCEPTED`；事实基线 `docs/project-context.md` 另获授权后登记。
