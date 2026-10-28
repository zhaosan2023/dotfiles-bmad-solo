---
schema_version: "1.0-draft"
task_id: "20261028-ADAPTIVE-BACKPRESSURE"
instance_id: null
contract_version: "2"
candidate_version: null
status: COMPLETED
session_id: null
scenario: ops
impact_tier: S
parent_objective:
  objective_id: "ADAPTIVE-BACKPRESSURE-LOSSLESS-DISTILLATION"
  expected_result: "在核心不变量及必要调用边与支持证据无损的前提下消除表示冗余，以保真硬门禁、预算软背压和传输能力协商替代固定配额死锁"
  source_ref: "平台当前用户请求：2026-10-28 /bmad-solo 落盘草案、方案结晶、执行交接三部曲"
inputs:
  - input_id: IN-01
    artifact_ref: "平台当前用户请求及已收敛会话裁决"
    required: true
    contract_version: null
    candidate_version: null
    consumption_condition: "原始文档授权保留为来源；2026-10-28 当前请求另授权 G1 文档治理收口、双门禁登记、ADR 转正和本任务归档，不授权重跑业务测试"
  - input_id: IN-02
    artifact_ref: "docs/analysis/ANALYSIS-20261028-adaptive-backpressure-and-lossless-distillation.md"
    required: true
    contract_version: null
    candidate_version: null
    consumption_condition: "DRAFT 设计输入；接管时核对文件与版本，不继承运行通过"
  - input_id: IN-03
    artifact_ref: "docs/adrs/ADR-20261028-adaptive-backpressure-and-lossless-distillation.md"
    required: true
    contract_version: "2"
    candidate_version: null
    consumption_condition: "关联 ADR 按当前独立用户批准及 G1 差异审查转正；仅接受已确认的离线实现和规范决策，不证明真实宿主或模型消费"
  - input_id: IN-04
    artifact_ref: "specs/governance/02-task-unit-schema.md"
    required: true
    contract_version: "1.0-draft"
    candidate_version: null
    consumption_condition: "本轮已原生读取的 Task Unit 结构规范；不视为运行控制器"
  - input_id: IN-05
    artifact_ref: "docs/paper-analysis/google-ooharness.md"
    required: true
    contract_version: null
    candidate_version: null
    consumption_condition: "论文机制依据；区分原文案例、实证和项目化外推"
  - input_id: IN-06
    artifact_ref: "solo-distill-mcp 目标工作区的当前规则、源码、配置、测试、环境及既有改动"
    required: true
    contract_version: null
    candidate_version: null
    consumption_condition: "第二阶段重新原生读取并核验权限与资产；本轮未接管，不继承旧快照"
cs_specification:
  scope: "结晶跨仓库整改契约；按用户确认的 I1—I3、V1 离线完工回执及本轮 G1 文档差异审查收口，不重跑引擎验证"
  excludes:
    - "本轮实施引擎或运行任何业务测试；G1 规范修改另由当前明确授权覆盖"
    - "未经授权的网络、真实模型调用、依赖安装、宿主激活及后台任务"
    - "覆盖用户既有改动、其他活动计划、旧 ADR 接受记录或冻结评价答案"
    - "未经明确授权的 ADR 转正或归档；本轮仍禁止事实登记、提交和推送"
  outputs:
    - output_id: OUT-01
      artifact_ref: "docs/analysis/ANALYSIS-20261028-adaptive-backpressure-and-lossless-distillation.md"
      ownership: responsible_actor
      intended_consumer: "架构审查及获准工程接管"
    - output_id: OUT-02
      artifact_ref: "docs/adrs/ADR-20261028-adaptive-backpressure-and-lossless-distillation.md"
      ownership: responsible_actor
      intended_consumer: "获准离线实现与规范消费；按独立用户批准转为 ACCEPTED，不证明宿主加载"
    - output_id: OUT-03
      artifact_ref: "specs/tasks/archive/20261028-adaptive-backpressure/TU-20261028-ADAPTIVE-BACKPRESSURE.md"
      ownership: responsible_actor
      intended_consumer: "本任务结项与审计导航；历史恢复须另获授权，不作为活动执行入口"
    - output_id: OUT-04
      artifact_ref: "solo-distill-mcp 工作区的获准源码与相关测试；具体差异在第二阶段接管后定位"
      ownership: responsible_actor
      intended_consumer: "独立消费者、棕地文档入口与监督审查"
    - output_id: OUT-05
      artifact_ref: "平台 2026-10-28 当前用户提供的 solo-distill-mcp 完工回执及独立审查确认；G1 平台差异审查回执"
      ownership: responsible_actor
      intended_consumer: "本轮双门禁结项；跨仓库运行依据为用户提供，本轮未重新执行或独立读取其原始日志"
  acceptance_criteria:
    - criterion_id: CS-01
      requirement: "核心不变量与必要调用边覆盖率 100%，不因块数或字节软目标截断、跳过或删除必需正文、骨架及支持闭包；各覆盖分母预先固定且非空"
      evidence_required: true
    - criterion_id: CS-02
      requirement: "结构化输出 BudgetTelemetry 遥测摘要，完整记录耗时、唯一正文块数、精确单帧及累计字节、目标、告警、策略和真实结果；纯软目标超限仅报 Warning，不抛致命容量异常"
      evidence_required: true
    - criterion_id: CS-03
      requirement: "单帧超过旧 22,016 字节目标时，通过显式大帧协商或分片完整交付；独立消费者重组并认证全部必需信息，未协商能力不得静默越限"
      evidence_required: true
    - criterion_id: CS-04
      requirement: "保留来源、权限、输入、解压、硬截止、取消及实际写出故障保护；缺片、篡改、混合快照、断管和必需证据缺失不被降为普通告警或成功"
      evidence_required: true
    - criterion_id: CS-05
      requirement: "整改覆盖实际 V2 调度、候选、封存、传输、消费者及棕地文档调用链，旧 V1、V2 和场景 B 不静默改义，进展绕过不放行全部噪声"
      evidence_required: true
    - criterion_id: CS-06
      requirement: "在另获规范修改授权后，治理预算、交接、验收、宿主适配及实际冲突分发源与新版契约一致；不以磁盘修改证明宿主有效加载"
      evidence_required: true
  supporting_evidence:
    - mechanical_verdict
    - supervisory_review
    - "独立预期集合与覆盖对账"
    - "原始管道捕获、重组认证及遥测回执"
  assumptions:
    - "目标工程声明 Python 3.12 及以上和标准库运行路径，第二阶段须核验实际环境"
    - "新策略与旧协议显式隔离；真实能力未协商时不可假设无限"
  limitations:
    - "原始 D1 文档阶段不授予后续实施；当前仅按明确 G1 收口授权更新文档，不恢复其他任务"
    - "I1—I3、V1 依据用户提供并确认适用于 CS-01—CS-05 的离线完工回执；本轮没有目标工程命令、版本或原始日志，不虚构其定位"
    - "静态骨架与已知调用边覆盖不证明全项目运行时业务语义"
    - "控制器覆盖未证明；临时使用平台记录，无程序防篡改保证"
  downstream_use: "可作为明确设计交接；正式贡献接受须当前 CS 与独立 SR 同时通过，ADR 转正另需授权"
kcp_verification:
  environment_ref: "I1—I3、V1 为用户确认的 solo-distill-mcp 离线完工范围；本轮 G1 工作区为 dotfiles-bmad-solo，禁止业务重测。以下 KCP-01—06 保留原始待实例化命令，不代表本轮运行"
  checks:
    - check_id: KCP-01
      criterion_refs: [CS-01]
      required: true
      verification_type: related_unit_tests
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, nonzero_collection, no_required_skip, exact_required_coverage, complete_body_and_support_closure]
    - check_id: KCP-02
      criterion_refs: [CS-01, CS-02, CS-05]
      required: true
      verification_type: related_unit_tests
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, nonzero_collection, soft_limit_crossing_success, complete_skeleton_pages, quota_conflict_warning]
    - check_id: KCP-03
      criterion_refs: [CS-02]
      required: true
      verification_type: related_unit_tests
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, nonzero_collection, exact_frame_accounting, complete_telemetry, warning_deduplication, no_stdout_pollution]
    - check_id: KCP-04
      criterion_refs: [CS-01, CS-03]
      required: true
      verification_type: isolated_transport_tests
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, nonzero_collection, incompressible_large_core_delivery, actual_pipe_capture, independent_reassembly_authentication]
    - check_id: KCP-05
      criterion_refs: [CS-04]
      required: true
      verification_type: related_unit_tests
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, nonzero_collection, security_negative_controls, cancellation_and_partial_write_controls, cleanup_known]
    - check_id: KCP-06
      criterion_refs: [CS-01, CS-05]
      required: true
      verification_type: related_unit_tests
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, nonzero_collection, legacy_version_compatibility, progress_bypass_scope, brownfield_complete_rendering]
    - check_id: KCP-07
      criterion_refs: [CS-06]
      required: true
      verification_type: documentation_diff_review
      command: "git --no-pager diff --check"
      command_status: AVAILABLE
      cwd: "."
      timeout_seconds: 15
      required_observations: [actual_exit, applicable_document_diff, affected_reference_and_distribution_consistency]
  verdict_ref: "平台当前用户完工回执及独立确认；G1 差异审查平台回执 call_64e541aa85fb62bd4c35dcac（退出 0），分发源差异工件 cmd-1793175604711.txt"
  evidence_basis:
    KCP-01_to_06: "当前用户确认 CS-01—CS-05：I1—I3 完成，V1 245 项纯离线全绿；36 块/110KB 完整保留；4 帧 61KB 实际管道捕获及负控通过。本轮不重测，原命令仍未在本契约实例化"
    KCP-07: "CS-06 采用当前用户明确批准的文档差异审查出口：六份治理规范、必要分发源、目录和引用一致性；不要求本轮业务、分发运行测试或宿主激活"
sod_review:
  responsible_actor: null
  supervisor_actor: "平台当前用户（自述独立于 solo-distill-mcp 实施者）"
  review_required: true
  minimum_independence: separate_actor
  review_ref: "平台确认回执 call_ab9b1b25eaf98e1c1d648c8c：确认 CS-01—CS-05，G1 差异审查满足 CS-06 后批准整项贡献、ADR 转正与归档"
  authority_source_ref: "2026-10-28 当前用户请求及独立审查确认"
  approval_scope: "本任务离线贡献及 G1 文档治理收口；另明确授权对应 ADR 转正与本任务归档"
gate_status:
  authority_kind: platform
  authority_ref: "本会话平台唯一任务记录、当前用户完工回执与独立确认、G1 原生修改及差异审查回执；无控制器防篡改保证"
  snapshot_contract_version: "2"
  snapshot_candidate_version: null
  cs: PASS
  sr: APPROVED
  accepted: true
  observed_at: null
authorization:
  source_ref: "2026-10-28 当前用户 /bmad-solo 治理四步收口及独立审查确认；原 D1 授权保留为历史输入"
  allowed_paths:
    - "AGENTS.md"
    - "specs/governance/"
    - "specs/tasks/governance/"
    - "specs/tasks/_active.md"
    - "specs/tasks/TU-20261028-ADAPTIVE-BACKPRESSURE.md"
    - "specs/tasks/archive/20261028-adaptive-backpressure/TU-20261028-ADAPTIVE-BACKPRESSURE.md"
    - "docs/analysis/ANALYSIS-20261028-adaptive-backpressure-and-lossless-distillation.md"
    - "docs/adrs/ADR-20261028-adaptive-backpressure-and-lossless-distillation.md"
    - "bmad-suite-v4/ 中确有冲突的预算规则、技能模板和模式指令"
  allowed_operations:
    - "原生读取、精确修改获准文档与受影响引用；保护既有未提交改动"
    - "仅审查 Git 差异与目录拓扑，不运行业务测试、不部署或激活宿主"
    - "据用户确认的离线完工回执和独立批准登记双门禁及定向 ADR 转正"
    - "六份治理文件防覆盖迁移、本任务完整保存及源版本复核后归档"
  phase: "G1 文档治理收口；I1—I3、V1 为用户确认的已完成离线输入，不在本轮重新执行"
  promotion_allowed: true
  archival_allowed: true
requires_adr: true
adr_file: "docs/adrs/ADR-20261028-adaptive-backpressure-and-lossless-distillation.md"
---

# Task Unit：动态背压松绑与无损蒸馏

本契约在 2026-10-28 治理收口边界按当前用户明确授权修订为版本 2、COMPLETED。I1—I3、V1 依据用户提供并独立确认的离线回执，G1 依据本轮原生文档修改与差异审查；不把本轮文档操作冒称引擎重测或真实宿主、模型消费。

## 结项边界与证据适用性

- 当前用户确认：I1—I3 实施完成，V1 245 项纯离线全绿，36 块/110KB 必需内容完整保留，4 帧 61KB 管道捕获和负控通过，适用于 CS-01—CS-05。
- 当前用户作为独立于实施者的审查主体，明确在 G1 差异审查满足 CS-06 后批准整项贡献、ADR 转正和归档；身份来源仅为平台用户确认，不称为密码学签名或独立凭据认证。
- G1 六份领域规范及必要分发源已同步；预算为默认规划目标、纯软超限仅提醒，保真覆盖、遥测、显式能力协商及安全负控要求保留。平台差异审查退出 0 满足本轮获准 CS-06 文档出口，不证明宿主加载。
- KCP-01—06 的 null 命令和 UNAVAILABLE 是原始设计字段，未伪填目标工程入口；结项使用当前用户明确采信的跨仓库回执，不将其称为本会话运行证据。
- 原始工程场景为 structural/M；本次 ops/S 只描述文档治理收口，不豁免 CS-01—CS-05。未知会话、实现者、候选版本、目标 HEAD 和原始运行日志位置不编造。
- 唯一进度入口仍为平台任务记录；本段是有来源的结项边界快照，不是逐轮执行账本。不登记事实基线、不提交、不推送、不部署。
- 下文 D1 与“待授权”段落保留为版本 1 的原始设计与阶段契约，不表示当前仍未获批准；当前接受、授权与证据适用性以上述版本 2 头部及本节为准。

## 1. 客户结果、原始 D1 授权与状态单源

- 客户结果：完整保留核心不变量、骨架、必要调用边和证据闭包，只消除表示冗余。
- 原始 D1 贡献：落盘[分析草案](../../../../docs/analysis/ANALYSIS-20261028-adaptive-backpressure-and-lossless-distillation.md)、[关联 ADR](../../../../docs/adrs/ADR-20261028-adaptive-backpressure-and-lossless-distillation.md)和本任务契约，交付第二阶段指令。
- 原始 D1 不实施引擎、不修改治理规范、不运行新增业务验证，不改旧 ADR、其他计划、活动入口或事实基线；本轮 G1 授权另见版本 2 头部。
- 七项必需 Frontmatter 按[Task Unit 规范](../../../governance/02-task-unit-schema.md:49)实例化；额外身份、授权、版本与阶段字段不扩大权限。
- 任务身份由当前用户指定文件派生，完整标识为 20261028-ADAPTIVE-BACKPRESSURE；未知会话与执行实例保持 null。当前审查主体及授权来源见版本 2 头部，不编造实施者身份。
- 当前唯一进度入口是本会话平台任务记录，真实写入或运行以回执为证。头部是版本 2 结项边界快照，不手工镜像逐轮进度；原始 D1 的 CS/SR UNKNOWN 不作为当前接受结论。
- 原始 D1 不启用任务活动指针；本轮获准创建空闲薄指针，不绑定归档任务、不替换其他活动计划，不继承其他任务或历史验证绿灯。

## 2. CS-01：不变量、骨架与调用边覆盖

验收前固定当前项目、快照、契约版本、授权扫描范围及非空必需集合，分别定义：

1. 业务不变量：否定、条件、所有权、副作用、接口与验收边界，由真实来源和独立审查确认。
2. 结构骨架：授权范围内支持的文件与语法单元，完整登记，不因软目标舍弃排序尾部。
3. 必要调用边：已消歧的静态边及其调用点、条件和支持闭包；动态未知目标保留原因，不伪造确定关系。
4. 支持证据：完整正文、装饰器、父结构、来源坐标、条件、关系及义务支持。
5. 失败与未知：解析失败、不支持资产、缺来源、拒绝项和未完成义务，不隐藏、不计为通过。

各必需集合逐项达到 100% 才满足对应覆盖要求；不得减少分母、把未知改为不适用，或使用模型自报完成代替认证。若验收要求运行时业务语义而仅有静态证据，相应项不通过。

无损约束：不得因 32 块、98,304 正文字节、240,000 骨架字节、16/12/4 管道比例或旧帧目标截断、跳过必需单元。去重及别名必须保留真实所有权和全部支持映射。

## 3. CS-02：预算软背压与遥测

原始设计拟新增 solo-distill-mcp 遥测模块；跨仓库源码路径不随本任务归档伪装为本工作区文件。BudgetTelemetry 的必要输出包括：

- 运行、项目、快照、契约及预算策略身份。
- 扫描、读取、生成、编码、核验、写出和总耗时；测量、估计、未知分开。
- 唯一正文所有者数、骨架数、正文字节、核心字节、编码字节、精确单帧及累计字节。
- 软规划目标、近预算条件、协商硬能力及能力来源。
- 必需覆盖状态、保护集变化、压缩绕过原因、策略与告警。
- 真实写出结果、重组认证和宿主消费状态；未知不能伪填成功。

纯软目标越界仅产生结构化 Warning，按越界或阶段事件去重。不让提醒洪泛污染协议标准输出或耗尽标准错误诊断额度。

后台观测不自动启动后台任务；日志出口失败不删除业务证据，但必需遥测记录无法补齐时 CS-02 不通过。实际写出耗时只能在真实回执之后记录，不改动已封存业务核心。

## 4. CS-03：大帧能力协商与分片

- 使用显式新策略／协议版本，不静默重定义旧协议的返回预算。
- 区分旧软目标、调用者明确硬上限、消费者能力和实际资源上限。未知能力不代表无限容量。
- 支持大帧时发送超过 22,016 字节的完整帧并告警；否则使用双方声明支持的分片调用或通知机制。
- 分片清单和每片绑定项目、快照、契约、包身份、编码、序号、字节及摘要；最后独立核对总片数、总长度和整体内容身份。
- 不为同一请求追加多个未声明的最终响应；独立消费者完成重组、来源和闭包认证后才计完整交付。
- 指针可作定位，但在必需内容尚未获取和认证前不能替代交付成功。
- 管道分片不等于模型输入已扩容，不自动增加外发范围、请求数或时限。

## 5. 验证项对应及场景

| 检查 | 主要目标 | 必需场景 |
|---|---|---|
| KCP-01 | CS-01 | 独立非空预期集合、正文原字节、条件、父结构、调用边和支持闭包 |
| KCP-02 | CS-01/02/05 | 33 个及更多必需节点、超 98,304 字节正文、超 240,000 字节骨架、原借槽冲突成功且提醒 |
| KCP-03 | CS-02 | 精确计量包含身份、转义、换行与摘要自身；告警去重；日志故障与未知状态 |
| KCP-04 | CS-01/03 | 不可压缩必需内容超旧帧目标、大帧与分片路径、实际管道捕获和独立重组 |
| KCP-05 | CS-04 | 来源变化、权限拒绝、畸形输入、解压异常、篡改、缺片、混合快照、取消、断管、部分写出及慢消费 |
| KCP-06 | CS-01/05 | 新关键证据保护与噪声区分、旧版本/场景 B 回归、棕地分卷完整导航 |
| KCP-07 | CS-06 | 另获授权后验证治理预算、交接与接受规则，以及实际冲突的模板和分发消费方 |

独立预期集合与重组验证不得只调用生产选择器或编解码器作为唯一神谕。旧版本应拒绝的负控保留，新版新增软超限正控；不按比例删测试，不改冻结答案，不降低断言。

## 6. 分阶段执行契约与授权边界

### D1：原始文档交付契约

交付三份指定文档及执行接力指令。成功原生写入回执满足文档持久交付条件，不满足未来代码 CS、SR 或 ADR 转正条件。

### I1：目标接管与保真读取（原始实施契约；完工依据见结项边界）

- 用户在 solo-distill-mcp 工作区发起新工程执行请求，显式引用本 TU 和 ADR，指明允许阶段。
- 原生读取目标规则、配置、依赖、相关源码与测试；在获准终端中检查当前改动，保护用户资产。不重复完整分析。
- 先实例化非空必需集合与新版策略，改造 solo-distill-mcp 的正文读取和蒸馏入口，新增遥测模块；具体实现与运行来源为目标工作区真实回执，不由本归档构造源码身份。
- 新策略下移除纯软配额拒绝和必需内容跳过，不删除类型、身份、秘密筛查、来源变化及硬截止检查。
- 保留旧版本，不能为了新策略成功而静默改变全部历史调用行为。

### I2：完整调用链与进展保护（原始实施契约；完工依据见结项边界）

覆盖实际 V2 读取、调度、候选域、核心封存、结构优先交付和棕地渲染链。全骨架先登记后分页，必需闭包不受借槽拒绝；关键进展保护相关证据，不放行全部噪声。

只改三个主要文件不构成 I2 完成；若新增闭包需要范围外资产，先报具体依赖与授权缺口，不顺手重构。

### I3：协商传输与消费者（原始实施契约；完工依据见结项边界）

共同实施版本化能力协商、大帧或分片、独立消费者及精确回执。保留取消、部分写出不重放、解压和身份安全边界。真实宿主加载或模型实验不属于默认许可。

### G1：规范一致性（本轮已获准，文档差异审查出口）

在 dotfiles-bmad-solo 修改[预算规范](../../../governance/01-plan-act-role-embedding.md:118)、[数据交接](../../../governance/03-dataflow-contracts.md:183)、[门禁](../../../governance/04-kcp-sod-gates.md:126)、[宿主适配](../../../governance/05-host-adaptation.md:150)和确有冲突的分发源；不追改历史验收记录。本阶段由当前明确授权完成，验收为文档差异审查，不启动业务测试。

### V1：相关离线验证与独立审查（原始验证契约；本轮采信用户确认回执）

- 原始验证要求创建并定位上述必需测试资产后，绑定准确命令和真实工作区。本轮不重跑，KCP-01—06 原始命令保持 null、UNAVAILABLE；跨仓库结项依据为用户确认回执，不伪造入口。
- 使用实际可用、覆盖本任务且获准的控制器入口；未覆盖时沿用获准受控命令并披露缺口。
- 探测 15 秒、验证 30 秒、构建 600 秒；进程级超时、前台串行、标准输入封闭，等待实际退出。验证按影响范围分组，不盲跑全库。
- 离线使用本地夹具、假网关和已具备依赖，不隐式联网安装、不导入执行待分析项目。
- 保存真实命令、工作目录、退出码、关键输出、候选、测试收集与清理证据；日志位置在真实创建后绑定，不预造回执。
- 缺授权、依赖、入口、必需证据、独立审查身份，或超时、零命中、必需跳过、清理未知，阻塞相应验收。普通失败可在权限和预算内修复，不推进依赖。
- 各阶段出口分别验收；全部必需 CS 与 SR 齐备才讨论贡献接受。需要缩小总任务时必须显式修订契约，不能把未获准 G1 悄悄记为不适用。

## 7. 监督审查与转正边界

- 必需独立性为 separate_actor；当前独立审查者是明确自述独立于实施者的平台用户，身份与批准来源见版本 2 头部，不冒称凭据隔离或认证签名。
- 单模型换角色自审可以补充，但不满足独立 SR，不冒写批准签章。
- SR 核对非空分母、必需内容守恒、调用方影响、软目标与硬能力区分、分片消费、故障负控和证据适用性。
- CS 与 SR 合取后只接受明确贡献；不自动授权宿主部署、ADR 转正、公共事实登记或归档。
- 对应 ADR 按本次独立用户批准及明确转正授权更新为 ACCEPTED；定向替代范围仅为新版固定软配额条款，不取消安全边界、不改历史记录。

## 8. 结果与来源导航

- 设计输入：[分析草案](../../../../docs/analysis/ANALYSIS-20261028-adaptive-backpressure-and-lossless-distillation.md)。
- 决策输入：[关联 ADR](../../../../docs/adrs/ADR-20261028-adaptive-backpressure-and-lossless-distillation.md)。
- 结构与状态规则：[Task Unit 规范](../../../governance/02-task-unit-schema.md:181)、[接受与独立审查](../../../governance/04-kcp-sod-gates.md:136)。
- 文档持久化证据：本会话原生修改与迁移回执；当前工程与 SR 依据见版本 2 头部及结项边界。不虚构标准控制器判定入口、跨仓库命令或认证签名。
- 获准范围已在本次结项边界完成；未来新增验收或历史恢复须另获授权。进度只定位平台唯一任务记录，不在 ADR、分析或本 TU 复制逐轮执行流水。
- 本任务是新整改契约，不是历史任务恢复；跨工作区接管重新核对当前资产及授权，不继承旧绿灯。
