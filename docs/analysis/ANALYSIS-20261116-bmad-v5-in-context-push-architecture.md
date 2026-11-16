# ANALYSIS-20261116：BMAD-Solo V5 In-Context Push 架构决策与闭环蓝图

- 报告编号：ANALYSIS-20261116-BMAD-V5-IN-CONTEXT-PUSH
- 日期：2026-11-16
- 状态：**PROPOSED (退回修订状态，网关物理核验闭环，待宿主物理实测后评审)**
- 领域：架构演进 / 动静解耦治理
- 关联 ADR：[ADR-20261116-BMAD-V5-IN-CONTEXT-PUSH](../adrs/ADR-20261116-bmad-v5-in-context-push-architecture.md)

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

## 2. 核心架构目标

1. **零外部依赖冷启动**：将 `ana-solo` 与 `bmad-solo` 提纯为内联规范，安装至全局 `~/.cline/rules/bmad-core.md`，实现任意业务项目即开即用；
2. **动静解耦**：静态层（行为宪法）与动态层（任务上下文）解耦，动态层在未获物理宿主扩展点前显式降级为 Tier 4，绝不自嗨冒充注入；
3. **双轨正交网关**：网关执行纯流式直通，不截断、不伪造 `tool_calls`；冒号后缀（`:academic` / `:factcheck`）作为原生检索增强独立封装；
4. **软背压与可执行门禁**：以 1,200 ~ 1,500 Tokens 为规划观测值，严格执行连续 2 次同根因失败熔断与真实回执放行。

---

## 3. 候选方案收敛与 DM/DR 裁决

对三份专家收敛草案进行硬门禁筛选与决策矩阵（DM）加权评估：

### 3.1 硬门禁筛选 (Hard Gates)
- **G1 (语义保真)**: 遵循 ADR-20261028，不削减责任条款。
- **G2 (动静概念隔离)**: 严禁将全局规则分发冒充为动态 In-Context Push。
- **G3 (双轨检索正交)**: 服务端检索与本地工具严格分流。
- **G4 (工程闭环与负向约束)**: 具备显式 Schema 与明确不采用的设计清单。

| 方案候选 | G1 | G2 | G3 | G4 | 门禁结论 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **O1 (ast-opus-solution)** | PASS | PASS | PASS | FAIL (结构未闭环，缺少负向清单与具体交付物) | 淘汰 |
| **O2 (ast-opus-2-solution)** | PASS | PASS | PASS | PASS (体系完备，具备 11 维验收矩阵) | 通过 |
| **O3 (sonnect-opus-2-solution)** | PASS | PASS | PASS | PASS (负向清单锐利，具备高精度 Schema 与四级集成阶梯) | 通过 |

### 3.2 决策矩阵 (DM) 与 DR 裁决
- **DR 裁决**：**CONFIRMED O3 AS CORE ARCHITECTURE, WITH O2 ACCEPTANCE MATRIX INJECTED**（以 O3 为工程骨架，融合 O2 之验收矩阵，吸收同行评审之双轨协议解耦与防混淆标签）。

---

## 4. 架构全景与动静解耦拓扑

```
                            【用户交互与意图层】
                                      │
                        (Vibe 语言 / 目标诉求输入)
                                      ▼
         ┌────────────────────────────────────────────────────────┐
         │             Cline / Roo / Pi 本地宿主环境               │
         │                                                        │
         │  【受管静态层】 (构建期由 dotfiles-bmad-solo 注入)         │
         │   ├─ ~/.cline/rules/bmad-core.md (固定治理内核)        │
         │   └─ ~/.cline/rules/bridge-shim.md (可选通信声明垫片)   │
         │                                                        │
         │  【动态组装层】 (任务开始时触发 Context Assembler)        │
         │   ├─ 读取工作区根目录与项目基线 (project-context.md)   │
         │   ├─ 锁定 _active.md 唯一活动任务，校验 approved_plan  │
         │   └─ 组装最小必要任务上下文 (Task Context Bundle)        │
         └────────────────────────────┬───────────────────────────┘
                                      │
                      (单次 HTTP/SSE 请求: 纯文本透传)
                                      ▼
         ┌────────────────────────────────────────────────────────┐
         │       自定义 API 网关 (双轨正交代理 / aurora2api)       │
         │                                                        │
         │  1. 本地工具流：纯文本流式透传，严禁正则与 tool_calls 伪造  │
         │  2. 检索增强流：检查 Model ID 后缀：                    │
         │     • 含 :academic / :factcheck -> 激活后端深度检索管线 │
         │       输出封装为 [EXTERNAL_RESEARCH_REFERENCE] 标签    │
         │     • 无后缀 -> 直接转发至上游模型推理                     │
         └────────────────────────────┬───────────────────────────┘
                                      │
                       (SSE 纯文本流，直出标准 XML 标签)
                                      ▼
         ┌────────────────────────────────────────────────────────┐
         │           Cline 宿主流式解析器 (已验证)                 │
         │                                                        │
         │  1. 文本流式拦截 <read_files>, <apply_patch>...        │
         │  2. 驱动本地 I/O / 终端执行，生成物理执行回执 (Receipt)   │
         │  3. 宿主核验回执 (非模型自述)，驱动 V5 状态机推进       │
         └────────────────────────────────────────────────────────┘
```

### 4.1 “元规则宪法 vs 运行时探针”正交原则 (Constitution vs. Runtime Probe)
1. **静态层是“元规则宪法”**：
   - 载体为 `~/.cline/rules/bmad-core.md`，构建期注入宿主全局 Prompt。
   - 规定智能体的行为边界、背压熔断、证据分层（FACT vs UNKNOWN）、三遍阅读纪律及只读/工程模式状态机。
   - 全局治理内核是 V5 的立足基石，具备 Tier 4 降级就绪保障，必须先行实施。
2. **工具是“运行时探针”**：
   - 载体为 Cline 的 `search_codebase`（代码库语义/符号检索）、`read_files`（切片精准阅读）等运行时工具。
   - 探针负责获取具体项目的业务上下文与符号定位，为模型提供物理事实证据。
3. **正交互补，严防混淆**：
   - 探针不能替代宪法：没有宪法约束，模型即使具备高强度的代码搜索能力，也会因缺乏证据纪律而臆造推断、越权修改代码；
   - 宪法不能替代探针：静态宪法严格控制在 1,500 Tokens 以内，绝不承载特定仓库的业务细节，模型在宪法指引下必须自主调用探针进行真实代码取证。

---

## 5. 核心资产规范

### 5.1 文档关联清单规范 (`specs/governance/v5-context-manifest.yaml`)
详见已落盘文件 [v5-context-manifest.yaml](../../specs/governance/v5-context-manifest.yaml)。核心增强特性：
- **来源绑定**：`active_task_pointer` 缺失处理为 `IDLE_OR_REPORT`；`approved_plan` 必须绑定当前唯一活动任务，且校验状态与有效期；
- **双轨解耦**：明确定义 `native_tool_calling` 与 `text_xml_bridge` 两种运行模式；
- **编辑工具策略**：推荐使用差分编辑 `apply_patch`，全量重构允许使用 `editor`；
- **交互与门禁工具角色重构**：
  - `ask_question`：Plan 中 $\le 2$ 个问题作为推荐软目标；Act 中遇未授权风险**首次即询问**，连续 2 次同根因失败触发熔断；
  - `submit_and_exit`：明确作为会话关闭动作，本身不替代物理质量门禁（物理门禁由宿主独立验证测试/差分判定）。

### 5.2 保真提纯编译器规范 (`scripts/distill_v5_kernel.py`)
- **AST 解析**：结构化解析 Markdown 源码，剔除修辞、多余样例与空行。
- **章节映射追踪**：记录源章节到输出条款的映射，词项断言仅作为辅助手段。
- **软背压**：预算目标 1,200 ~ 1,500 Tokens；超限仅警告并建议阶段化拆分，绝对不自动截断规则。

### 5.3 通信声明垫片规范 (`contracts/claude_bridge_shim.md`)
作为可选适配垫片，剔除所有越权暗示：
- 仅陈述纯文本流标签通信协议，受活动模式与用户授权约束；
- 严禁声明“fully authorized”等越权指令。

---

## 6. V5 状态机流转与执行生命周期

```
[Vibe / 目标输入]
   │
   ▼
[INTAKE] ──(纯咨询/审核/探索)──► [READ_ONLY_CONSULTATION: 会话交付, 不落盘]
   │
   │ (需持久分析或获准实施)
   ▼
[CONTEXT_LOADING] ──(缺失项目基线或清单冲突)──► [BLOCKED: 阻断并报错]
   │ (必需上下文组装成功)
   ▼
[ANALYSIS 模式 (/ana-solo)]
   │ 1. 三遍阅读 (Map -> Evidence -> Recon)
   │ 2. 证据分层 (严格标注 FACT / UNKNOWN)
   │ 3. 产出 ADR 候选与 pending plan (会话内提案)
   ▼
[PLAN_READY] ──(未获用户明确批准)──► [PAUSE: 保持只读, 等待授权]
   │
   │ (用户输入明确批准指令，如 /bmad-solo)
   ▼
[APPROVED_IMPLEMENTATION 模式 (/bmad-solo)]
   │ 1. 校验批准计划契约与 Preflight
   │ 2. 执行代码修改 (优先 apply_patch)
   │ 3. 运行本地真实命令验证 (非交互式)
   ▼
[VERIFICATION]
   ├─ 代码任务通过 (EXECUTED_PASS) ──────► [COMPLETE: 允许调用 submit_and_exit]
   ├─ 文档治理任务通过 (DIFF_PASS) ──────► [COMPLETE: 允许调用 submit_and_exit]
   ├─ 同根因连续 2 次失败 ──────────────► [BLOCKED: 熔断并调用 ask_question 询问]
   └─ 用户中途要求暂停 ────────────────► [SUSPENDED: 保存现场状态]
```

---

## 7. Cline 宿主物理核验门槛与四级集成阶梯

```
[开始 Cline 物理集成取证]
               │
               ▼
   【Tier 1: 官方受支持扩展钩子】
   核查源码是否存在 onBeforeRequest 或动态 System Prompt 注入 API
         ├─ [YES] ──► 实现标准 Extension 适配器，达成完全体动态 Push
         └─ [NO]
               ▼
   【Tier 2: 经确认的 CLI/SDK 模式】
   核查 headless / CLI 模式是否支持外部灌入动态上下文文件
         ├─ [YES] ──► 开发基于 CLI 的任务前置装配包装器
         └─ [NO]
               ▼
   【Tier 3: 最小受控 Fork / 上游 PR】
   评估是否向上游 Cline 提 PR 或维护极简透明的 Context 补丁
         ├─ [经评估批准] ──► 维护最小补丁集
         └─ [否决/不可行]
               ▼
   【Tier 4: 兜底防御与明确降级 (Strict Blocker Gate)】
   1. 仅分发全局静态治理内核 (~/.cline/rules/bmad-core.md)
   2. 显式记录：动态 Context Push 处于 BLOCKED 状态
   3. 进入降级模式：治理规则就绪，动态项目上下文不可用
   4. 严禁使用静态规则假装动态上下文已自动注入！
```

---

## 8. 修订后的 11 维全生命周期验收矩阵

| 序号 | 验收领域 | 最低通过判定标准 (Pass Criteria) | 验证手段 |
| :---: | :--- | :--- | :---: |
| **1** | **V4 语义保真** | 源章节到目标条款映射完整，核心规则逐条可追溯，无静默丢失。 | 条款映射矩阵核对 |
| **2** | **文档治理关联** | `v5-context-manifest.yaml` 格式合法，来源（含 `approved_plan`）无空悬引用。 | YAML Schema 校验 |
| **3** | **动静概念隔离** | 安装状态、加载状态与注入状态分别独立产生回执，未实现动态 Hook 时报阻断。 | 分发测试用例 |
| **4** | **可选垫片中立** | 垫片不包含任何工具参数重定义，严禁“fully authorized”等越权用词。 | 文本合规静态扫描 |
| **5** | **隐私与最小注入** | 密钥、凭证、`.git` 及未授权路径被通配符严格排除，不得注入上下文。 | 过滤器单元测试 |
| **6** | **Plan/Act 隔离** | `/ana-solo` 阶段提示词策略禁止写文件；未获批准指令绝不推进至实施。 | 状态机模拟探针 |
| **7** | **执行背压熔断** | 同一根因（由测试用例与错误特征码定义）连续失败 2 次，系统自动中断。 | 异常注入回执检查 |
| **8** | **真实回执驱动** | 模型自述或调用 `submit_and_exit` 不充当质量证明；必须由宿主核验测试/差分通过。 | 回执匹配断言 |
| **9** | **双轨检索正交** | 服务端检索封装为带有 `[EXTERNAL_RESEARCH_REFERENCE]` 的独立代理能力；本地工具纯透传。 | 独立代理与客户端测试 |
| **10** | **受管分发事务** | 支持加锁、原子替换、指纹核验与改动中止，目标被改动时停止回退。 | 回滚幂等性测试 |
| **11** | **版本环境锁定** | 所有运行时验收结果均显式绑定测试环境，不泛化结论。 | 交付报告元数据核对 |

---

## 9. 上游网关 (aurora2api) 源码物理取证与实测结论 (PHYSICAL VERIFIED FACT)

根据用户授权，对 `~/project/aurora2api` (Go 1.23) 进行了代码审计及对本地运行端点 (`http://127.0.0.1:8080`) 的实测验证，取得以下确定性物理事实：

### 9.1 事实一：模型冒号后缀解析机制与事实检索增强 (FACT)
- **源码定位**：`internal/upstream/studioglobal/registry_routing.go:27-55` 及 `registry_config.go`
- **实现逻辑**：
  - 代码通过 `strings.Cut(input, ":")` 将模型名分解为 `base` 与 `suffix`。
  - 支持 `:academic`、`:factcheck` 及 `:coding` 等后缀。
  - 当 Model ID 携带 `:academic` 时，网关绑定预设 `starter-academic-deep-dive-v1`，激活 Perplexity 深度学术搜索源 (`SearchSources: ["academic"]`)。
  - 在 SSE 流式传输中，网关将搜索探针与进度实时封装为 `ReasoningText` (`delta.reasoning_content`) 推送给客户端，正文流式输出学术论文作者与引用。
- **物理实测回执**：
  - 测试命令：`curl -N -s -X POST http://127.0.0.1:8080/v1/chat/completions -H "Content-Type: application/json" -d '{"model": "claude-sonnet-5.5:academic", "messages": [{"role": "user", "content": "Who are the authors of Attention is All You Need?"}], "stream": true}'`
  - 响应结果：4.1 秒内流式输出 `reasoning_content`，随后流式推送标准学术引用（Vaswani et al.），全程无解析错误。

### 9.2 事实二：网关对 `tools` 字段的非流式强行拦截与纠错死循环根因 (FACT)
- **源码定位**：`internal/handler/chat_handler.go:186-206`
  ```go
  toolsEnabled := h.toolCallHandler != nil && h.toolCallHandler.ToolsEnabled(chatReq)
  if toolsEnabled {
      original_request.Stream = false // 强制关闭流式！
      return h.handleToolCalling(c, original_request)
  }
  ```
- **崩溃物理成因**：
  - 只要客户端（如 Cline 开启 Native Tool Calling）在请求中携带 `tools: [...]` 数组，网关即强制将 `Stream` 置为 `false`。
  - 网关在 `handleToolCalling` 中向上游发送请求，然后调用 `toolcall.ParseNegotiatedOutput`，试图用正则/JSON 提取模型输出并伪造成 OpenAI `tool_calls`。
  - 一旦模型输出不匹配或模型拒绝访问本地文件，网关自动在 messages 末尾追加纠错提示并重试（最多 `maxSends` 次）。
  - 在复杂任务与长上下文（20KB+）下，该纠错循环极易耗尽预算引发 `ErrSendBudgetExhausted`，导致客户端出现长达 30~60 秒的无响应超时死锁。这正是 V4 阶段网关假冒 `tool_calls` 崩溃的物理根因！

### 9.3 事实三：无 `tools` 字段时的纯流式直通管道 (FACT)
- **源码定位**：`internal/handler/chat_handler.go:208-250`
- **实现逻辑**：
  - 当客户端请求中**不携带 `tools` 字段**（或 `tools` 为空）时，`toolsEnabled` 为 `false`。
  - 网关完全跳过工具拦截与非流式转换，直接作为纯粹的低延迟 SSE 透传管道 (`StreamCompletion`)。
  - 模型输出的任何 XML 标签（如 `<read_files>`、`<apply_patch>`）均作为纯文本字面量逐 token 实时流出，网关不作任何正则篡改与延迟缓冲。
- **物理实测回执**：
  - 模拟 Cline 发送请求含 XML 标签提示但无 `tools` 参数，网关以 0ms 额外缓冲延迟实时返回完整 XML 标签与文本内容。

---

## 10. 待核验未知与后续工程交接

1. **网关层结论已完全闭环 (CLOSED)**：
   - 上游网关 `aurora2api` 行为已确证：原生支持冒号后缀学术检索，纯文本流式透传极速稳定，但严禁客户端传入 `tools` 字段（否则触发网关强制非流式与纠错死循环）。
   - **Cline 接入定案**：Cline 与 `aurora2api` 配合时，必须运行于 `text_xml_bridge` 模式（或确保请求体不发 `tools: [...]`），以激活纯流式高速通道。
2. **静态层实施就绪 (READY)**：
   - 清单规范与编译器脚本可直接在 `dotfiles-bmad-solo` 内实现与自测；
   - 静态治理内核分发至 `~/.cline/rules/` 具备即时可用性（作为 Tier 4 降级就绪资产）。
3. **剩余唯一待取证项：Cline 宿主物理集成 (PENDING)**：
   - 提取 Cline 源码包，定向检索 `system.ts`、`AssistantMessageParser.ts` 及 API Provider 构建模块；
   - 确认 Cline 在 OpenAI-Compatible Provider 下是否可配置关闭 `tools` 发送，或是否在 custom 模式下原生解析文本 XML 标签；
   - 依据核验回执决定进入 Tier 1、Tier 2 或停留于 Tier 4 阻断状态。
