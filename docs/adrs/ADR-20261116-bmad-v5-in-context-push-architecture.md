---
adr_id: "ADR-20261116-BMAD-V5-IN-CONTEXT-PUSH"
status: ACCEPTED
supersedes: null
supersedes_scope: "正式推进 V5 架构演进，设计上替代 V4 薄路由被动外链拉取与网关正则伪造 tool_calls 条款；不修改 V4 历史 ACCEPTED 记录"
contract_version: "2"
task_file: null
analysis_file: "docs/analysis/ANALYSIS-20261116-bmad-v5-in-context-push-architecture.md"
scenario: structural
impact_tier: M
runtime_verified: "verified (gateway: ~/project/aurora2api SSE pass-through; host: Cline claude-opus-5.5 dual-layer injection verified)"
session_id: "dcafc95e-1444-4582-8ca2-3b69a0cf8a2c"
authorization: "2026-11-16 用户指令：'good, 按建议路径执行' 批准转正"
acceptance_basis: "上游网关 aurora2api 经源码核验与流式直通实测闭环；Cline (Claude Opus 5.5) 宿主完成 Phase 1 静态内核 (bmad-core.md, 1306 tokens) 与 Phase 2 动态任务上下文 (active-context.md, 1182 tokens) 的双层宿主物理注入验证 (VERIFIED_PASS)，双层总背压 ~2488 tokens (<2%)。"
---

# ADR-20261116：BMAD-Solo V5 In-Context Push 架构与动静解耦治理

- 状态：**ACCEPTED (已通过上游网关与 Cline 宿主双层物理核验转正)**。
- 日期：2026-11-16。
- 决策所有者：项目维护者。
- 绑定分析报告：[ANALYSIS-20261116-BMAD-V5-IN-CONTEXT-PUSH](../analysis/ANALYSIS-20261116-bmad-v5-in-context-push-architecture.md)。
- 授权说明：本 ADR 已经完成网关流式直通实测与 Cline 宿主双层物理回执核验，经用户明确指令正式批准转正。

---

## 1. 背景与核心问题

1. **V4 被动外链拉取的冷启动断裂**：  
   V4 依赖 `.clinerules` 中的相对路径（如 `[方法论](.cline/skills/ana-solo/SKILL.md)`）。在普通业务项目中，由于该目录物理缺失且模型无法自发跨目录寻址，导致模型首轮彻底失明。
2. **网关暴力正则路线破产**：  
   自定义 API 网关（aurora2api）试图通过正则拦截模型的“无法访问本地文件”拒答词，并强行合成 OpenAI 格式的 `tool_calls`。在 20KB+ 复杂长上下文中，正则逻辑频繁崩溃并引发调用死循环。
3. **协议演进与双轨现实**：  
   - Cline v3.35+ 官方引入了 Native Tool Calling API，支持由模型选择结构化工具并由客户端执行；
   - 在自定义逆向网关或剥离了 `tools` 字段的特定 Provider 环境下，模型输出纯文本 XML 标签仍作为一种可选的文本桥接兼容路径；
   - 本案致力于彻底消除网关层的伪造与篡改，将调用契约清晰划分为“原生工具调用”与“可选文本桥”，控制权收口至本地宿主。

---

## 2. 决策内容

### 决策一：采用动静解耦的 In-Context Push 架构与宪法-探针正交原则
彻底放弃“运行期动态跨目录寻址”，转向动静二分架构，并确立“元规则宪法 vs 运行时探针”正交原则：
1. **静态固定治理内核（元规则宪法）**：静态层是智能体的行为宪法与思维框架，负责三遍阅读、证据分层（FACT vs UNKNOWN）、背压熔断与边界门禁。由 `dotfiles-bmad-solo` 在构建期将 `ana-solo` 与 `bmad-solo` 核心宪法编译提纯为零外部依赖的内联文件，受管分发至全局 `~/.cline/rules/bmad-core.md`。安装状态（`ASSET_INSTALLED`）、宿主加载（`HOST_LOADED`）与请求注入（`CONTEXT_INJECTED`）分别独立记录。**全局治理内核是 V5 的立足基石，必须作为 Tier 4 降级就绪资产先行实施。**
2. **运行时工具探针（代码级执行）**：Cline 的 `search_codebase`、`read_files` 等 SDK 工具是运行期由模型按需调用的主动取证探针，负责具体的符号检索、代码定位与证据发现。探针不能代替宪法（否则引发越权与发散），宪法亦不替代探针（静态规则不承载仓库业务细节）；静态宪法规范探针的使用边界与证据纪律，探针为宪法提供真实的物理证据，两者正交互补。
3. **动态任务上下文**：当前工作区的项目事实基线、当前权威计划及按需文档，由宿主适配器在任务开始时动态组装后推入模型请求。在未获宿主扩展点证据前，动态推送保持 `BLOCKED`，系统处于 **Tier 4 降级治理模式（治理规则可用，动态项目上下文不可用）**。

### 决策二：确立文档关联清单（Context Manifest v1.1）为一等架构资产
文档治理关系不得停留在提示词口头说明中。在 `specs/governance/v5-context-manifest.yaml` 中显式定义机器可读的契约：
- **来源定义**：通过 `_active.md` 唯一选定活动任务，多候选冲突时硬阻断；`approved_plan` 必须校验任务绑定、批准状态与非过期证据；
- **双轨工具模式解耦**：明确区分 `native_tool_calling`（原生 API 路径）与 `text_xml_bridge`（可选文本桥路径），严禁混为一谈；
- **工具策略边界**：以 `policy_allowed_tools` 与 `policy_prohibited_tools` 声明策略意图（非物理沙盒）；文件修改推荐差分补丁 `apply_patch`，新文件允许全量 `editor`；
- **交互与门禁工具角色规范**：
  - `ask_question`：Plan 中 $\le 2$ 个澄清问题作为推荐软目标；Act 中遇未授权风险**首次立即询问**，连续 2 次同根因失败触发熔断请示；
  - `submit_and_exit`：明确定义为客户端会话关闭动作，**本身不充当物理质量门禁**；质量门禁必须由宿主独立验证回执判定（代码任务绑定 `EXECUTED_PASS`，文档任务绑定 `DIFF_CLEANLINESS_PASS`）。

### 决策三：网关重构为“双轨正交代理（Orthogonal Dual-Track Proxy）”
消除“纯透传”与“服务端搜索”的概念张力，基于 `~/project/aurora2api` 源码物理取证落实契约：
1. **客户端本地工具流**：网关执行纯文本被动透传（Pass-Through，对应 `internal/handler/chat_handler.go:208-250` 的 `StreamCompletion`），流式优先传输，绝不通过正则解析或拦截模型的 XML 文本，绝不伪造 `tool_calls`。**重要契约约束**：客户端请求严禁携带 `tools: [...]` 字段，否则会触发网关强制关闭流式 (`original_request.Stream = false`) 并进入脆弱的纠错死循环。
2. **服务端原生检索流**：经 `internal/upstream/studioglobal/registry_routing.go:27-55` 确证，Model ID 携带 `:academic` / `:factcheck` 后缀时，网关启用后端检索增强；检索状态实时通过 SSE `ReasoningText` (`delta.reasoning_content`) 推送，结果强制封装为带 `[EXTERNAL_RESEARCH_REFERENCE]` 标签与时效元数据的外部参考材料，**显式声明“非本地工具执行回执”**，消除模型语义混淆。

### 决策四：破壁垫片降级为可选协议说明，剔除越权话术
废除包含“fully authorized”的激进垫片。若实测证明特定模型/Provider 组合确有需要，仅作为**可选通信声明垫片**，仅陈述文本流标签通信机制，严禁声明越权指令，严格受制于活动模式与用户授权。

### 决策五：Cline 宿主物理核验前置门禁与四级集成阶梯
针对 Cline 运行时扩展能力的未知性，确立四级阶梯：
- **Tier 1 (优先)**：受支持的官方扩展接口（Extension API Hook）；
- **Tier 2 (备选)**：经验证可传入动态上下文的 CLI/SDK 模式；
- **Tier 3 (后备)**：最小受控 fork 或上游 PR；
- **Tier 4 (兜底防御与明确降级)**：在未取得 Tier 1~3 物理证据前，**动态 Context Push 保持 BLOCKED 状态**；仅交付全局静态规则分发，进入“治理规则可用、动态项目上下文不可用”的降级模式，绝不自嗨冒充动态注入完成。

---

## 3. 负向边界（绝对禁令）

1. **严禁网关伪造**：网关不得通过正则解析 assistant 文本来合成 `tool_calls`。
2. **严禁臆造参数**：不得在提示词或垫片中为 Cline 工具发明不存在的参数。
3. **严禁概念混淆**：不得将“安装了全局规则”宣称为“已实现工作区上下文自动推送”。
4. **严禁越权赋权**：`intent_triggers` 仅用于工作流候选识别，绝对不能作为跳过用户审批直接进入 Act 实施的依据。
5. **严禁静默删词**：Token 预算是软约束。严格遵循 ADR-20261028，严禁为迎合 Token 预算静默删去否定项、责任归属或失败门禁。
6. **严禁静默回退任务**：活动任务指针缺失或非法时，严禁静默激活历史或归档任务。

---

## 4. 架构不变量 (Invariants)

- **公共契约不变**：`/ana-solo`（只读分析结晶）与 `/bmad-solo`（批准工程交付）的核心入口语义与状态水印契约保持不变。
- **数据真理源单一**：`bmad-suite-v4`（或统一指定的版本目录）为唯一真理源，`dist/` 编译物与客户端挂载点均为只读派生构件。
- **执行以真实回执为准**：模型自述或调用 `submit_and_exit` 不等于质量合格。状态推进与门禁判定必须以宿主核验的测试或差分真实回执（Receipt）为准。
- **保真优先于预算**：预算目标 $1,200 \sim 1,500$ Tokens 仅作为规划观测值，超出时优先采用分阶段挂载，不得破坏三遍阅读与背压矩阵。

---

## 5. 受管分发与安全回退契约

### 5.1 受管分发事务
分发模块（`scripts/dispatch_v5.sh`）遵循防御性事务原则：
1. **加锁与原子替换**：对目标文件加锁，通过临时文件写入后原子重命名（Atomic Rename）生效，避免编辑器热重载或并发冲突；
2. **事务记录**：保存分发前的原始指纹、权限模式与备份摘要至事务日志。

### 5.2 安全回退流程
严禁无差别 `rm -f` 与强制覆盖 `mv -f`。回退流程必须遵循：
1. **身份核验**：检查目标文件是否仍匹配 V5 分发时的摘要特征，若已被用户手动修改，则停止自动回退并报警提示；
2. **安全恢复**：仅还原由本次事务安全创建的备份；若备份缺失或被污染，不执行危险覆盖，转交人工介入；
3. **撤销链接**：仅移除确认为本分发器建立的全局软链接或受管资产；
4. **回执确认**：输出真实文件状态对账清单，不使用未经实测的极端性能口号。
