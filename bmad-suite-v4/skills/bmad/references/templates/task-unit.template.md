---
schema_version: "1.0-draft"
task_id: REPLACE_WITH_UNIQUE_TASK_ID
instance_id: null
contract_version: "1"
candidate_version: null
status: DRAFT
session_id: null
scenario: structural
impact_tier: M
parent_objective:
  objective_id: null
  expected_result: "待填写当前用户确认的单项结果"
  source_ref: null
inputs: []
cs_specification:
  scope: "待填写本任务的唯一贡献范围"
  excludes: ["未经授权的部署、事实登记、转正与归档"]
  outputs: []
  acceptance_criteria: []
  supporting_evidence: [mechanical_verdict, supervisory_review]
  assumptions: []
  limitations: []
  downstream_use: "仅当前候选满足实际接受契约后作为正式输入"
kcp_verification:
  environment_ref: null
  checks:
    - check_id: KCP-01
      criterion_refs: []
      required: true
      verification_type: config_syntax
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, applicable_result]
  verdict_ref: null
sod_review:
  responsible_actor: null
  supervisor_actor: null
  review_required: true
  minimum_independence: separate_actor
  review_ref: null
  authority_source_ref: null
  approval_scope: contribution_acceptance_only
gate_status:
  authority_kind: platform
  authority_ref: null
  snapshot_contract_version: "1"
  snapshot_candidate_version: null
  cs: UNKNOWN
  sr: UNKNOWN
  accepted: false
  observed_at: null
authorization:
  source_ref: null
  allowed_paths: []
  allowed_operations: []
  phase: null
  promotion_allowed: false
  archival_allowed: false
requires_adr: false
adr_file: null
---

# Task Unit：单项贡献契约模板

本模板是待实例化草稿，不是已授权任务，也不证明验证入口、控制器或独立审查已经可用。不得执行占位内容，静态形状通过不等于任务就绪或验收通过。

## 实例化与兼容边界

- 仅在当前用户授权持久结晶且平台允许时创建任务契约；明确的小修复与只读咨询不强制创建。
- 填写唯一任务标识、真实父目标及来源、允许操作与路径、当前获准阶段、必需输入、产物、验收、逐项验证和审查要求；未知身份与来源保持空值，不编造。
- 新任务采用任务契约格式；既有明确绑定的实施计划保留自身格式，不混合新旧身份、不静默转换或迁移历史任务。
- 使用目标项目已声明的任务目录和命名契约。显式路径优先；单焦点薄指针只定位身份与契约，不保存进度或自动授权实施。已有焦点不能顺手覆盖。
- 必需输入、授权、验证入口或审查条件缺失时阻塞相关实施或接受。可用入口必须绑定实际环境与命令，入口可用不代表执行通过。
- 当前任务进度仅来自已核验且覆盖本任务的控制器任务清单；未实现或未覆盖时临时引用平台任务记录与真实回执。状态卡是只读视图，不另建账本，不宣称已有程序防篡改保证。
- 契约保存目标、授权、阶段和验收，不保存逐轮流水。头部门禁是带来源的边界快照，不能替代真实权威判定。

## 客户结果与验收

- 父目标：填写可定位的当前需求来源与成功结果。
- 必须交付：逐项列出产物、所有权、消费者与用途。
- 贡献标准：列出可以判定的验收、保护资产、限制与必要证据。
- 当前授权：明确允许范围、阶段和禁止事项，不把模式或技能调用当成授权。

## 实施阶段与依赖

- 按当前获准阶段列出连贯改动、必要接口、调用方、所有权和副作用边界。
- 完整保留未完成事项及其必需支持闭包；失败不推进依赖，阶段通过不等于全计划完成。
- 恢复历史任务须明确授权、建立保留来源的新实例，并重新验证受影响证据，不继承旧绿灯。

## 验证与审查契约

- 按场景与实际影响范围列出必需验证项、对应验收编号、环境前提、真实入口、工作目录、超时、观察结果和清理要求；不使用笼统的“全部测试”。
- 只读任务不运行验证。获准工程命令串行、前台同步、封闭标准输入；探测、验证、构建分别为 15 秒、30 秒、600 秒，并使用环境实际支持的进程级超时。
- 非零退出、超时、缺依赖、零命中、必需项跳过或缺证据不能记为通过；空输出按具体操作的必需证据判断。普通失败仅在当前权限与预算内定向修复，不降低断言。
- 在唯一任务记录引用真实命令、工作目录、退出状态、关键输出和目标；不抄入本契约。实现、测试、契约或环境变化后仅重验受影响证据，保存进度不触发业务重测。
- 核对真实审查主体、身份来源、独立性、批准权限和候选版本；角色换名或同会话自审不能冒充独立批准。静态配置与隔离分发不证明宿主加载或程序门禁。

## 接受、登记与归档

- 仅当前契约的必需贡献标准、验证及审查均满足且证据适用时接受指定贡献；缺必需运行时证据保持阻塞。
- 仅关联契约要求、全部必需门禁通过且取得转正授权时接受对应 ADR；新提案保持 PROPOSED，不追改其他任务记录。
- 事实登记、提交、推送、宿主激活、部署和归档分别取得相应授权，不由阶段完成自动触发。
- 仅整项绑定任务完成且获准归档时处理源；目标不得覆盖，完整保存成功后复核源身份与内容版本，失败或源变化则保留源。明确暂停保留全部未完成事项。
