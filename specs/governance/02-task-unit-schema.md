---
document_id: BMAD-GOVERNANCE-02
schema_version: "1.0-draft"
status: PROPOSED
language: zh-CN
owner: 项目维护者
scope: Task Unit 契约、活动入口与归档
runtime_verified: false
---

# 模块二：核心工件规范与完整模板

Task Unit 将一项可交付贡献绑定到父目标、生产责任、接受条件及下游用途。
任务目录承载契约；真实运行状态只由一个已核验的权威入口管理。

## 1. 目标目录与资产分工

以下是目标布局；治理领域规范与任务生命周期分离，示例不证明控制器或验证资产已实现。

```text
specs/
├── governance/                  # 独立领域规范：索引及五个模块
└── tasks/
    ├── _active.md               # 单焦点身份与契约定位，不复制进度
    ├── TU-<task_id>.md           # 有活动任务时保存当前贡献契约
    └── archive/
        └── <UTC时间>-<task_id>-<instance_id>/
            └── TU-<task_id>.md   # 获准完成归档的完整契约
verification/
├── TU-<task_id>.verdict.json     # 当前机械判定的定位入口
└── tasks/<task_id>/<run_id>/     # 独立保存原始回执与审查材料
```

- Task Unit 是一等公民，不再把孤立输出目录作为新任务运行中心。
- 公共领域规范仍归领域所有，不把稳定接口定义复制进每个任务。
- 实测证据归根级验证区，不与长期测试源码混存。
- 治理文档不是活动 Task Unit，不参与业务完成归档。
- 旧任务、旧事实和原始证据迁移须另获清单授权，不凭目录提案删除。

## 2. 身份、版本与责任

- 任务标识由受控分配方生成，在项目范围唯一且不可复用给不同贡献。
- 标识仅允许字母、数字、连字符和下划线；禁止路径分隔符与路径穿越。
- 实例标识区分执行和恢复；历史重放必须建立保留来源的新实例。
- 契约版本在输入、输出、验收或授权边界实质变化时更新。
- 候选版本标识本次产物；同一契约可存在多个拒绝后的候选。
- 生产责任与监督责任明确列出；未知真实身份使用 null。
- 角色标签不等于可认证的审查人身份，也不增加宿主权限。

## 3. 必需 Frontmatter 字段

| 字段 | 类型与必需内容 | 拒绝条件 |
|---|---|---|
| task_id | 非空受限字符串，绑定任务文件 | 重复、非法字符或身份不匹配 |
| parent_objective | 映射：目标标识、结果与来源 | 无法追溯客户目标 |
| inputs | 列表：来源、版本、必需性与消费条件 | 必需来源缺失或尚未接受 |
| cs_specification | 映射：范围、产物、标准、证据与用途 | 只有模糊目标，无可判定贡献 |
| kcp_verification | 映射：关键点、验证项、环境与入口状态 | 把未创建命令标为可用 |
| sod_review | 映射：生产者、审查者、独立性与批准范围 | 生产者冒写独立批准 |
| gate_status | 映射：状态来源、版本及 CS/SR 接受快照 | 以手工快照替代真实权威判定 |

- 七项均必须存在；空值只允许在明确定义的尚未实例化位置。
- 未知不默认为通过，空列表不等于没有必要验证。
- 必需验证项必须逐项列出，禁止用笼统的“全部测试”代替。
- 文本中的验收编号须与验证项和审查发现对应。

## 4. 标准 Task Unit 完整模板

下列是一份完整的待实例化 Markdown 示例，不是已授权执行的任务。
示例中的空值必须在对应阶段补齐；未补齐的必需入口保持 BLOCKED。

```markdown
---
schema_version: "1.0-draft"
task_id: DEMO-001
instance_id: null
contract_version: "1"
candidate_version: null
status: READY
session_id: null
scenario: structural
impact_tier: M
parent_objective:
  objective_id: CUSTOMER-OBJECTIVE-001
  expected_result: "由客户确认的单项业务结果"
  source_ref: null
inputs:
  - input_id: IN-01
    artifact_ref: null
    required: true
    contract_version: null
    candidate_version: null
    consumption_condition: ACCEPTED_CURRENT
cs_specification:
  scope: "本 Task Unit 的唯一贡献范围"
  excludes: ["未经授权的生产部署"]
  outputs:
    - output_id: OUT-01
      artifact_ref: null
      ownership: responsible_actor
      intended_consumer: parent_objective
  acceptance_criteria:
    - criterion_id: CS-01
      requirement: "结果满足明确业务验收，不损害保护资产"
      evidence_required: true
  supporting_evidence: [mechanical_verdict, supervisory_review]
  assumptions: []
  limitations: []
  downstream_use: "仅当前候选获双重接受后作为正式输入"
kcp_verification:
  environment_ref: null
  checks:
    - check_id: KCP-01
      criterion_refs: [CS-01]
      required: true
      verification_type: config_syntax
      command: null
      command_status: UNAVAILABLE
      cwd: "."
      timeout_seconds: 30
      required_observations: [actual_exit, applicable_result]
  verdict_ref: "verification/TU-DEMO-001.verdict.json"
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

# Task Unit：待实例化的单项贡献

## 客户结果与验收

- 父目标：填写可定位来源，不复制整个上级任务。
- 成功条件：填写可以检查的结果与保护边界。
- 当前授权：填写真实批准来源、阶段及允许操作。

## 贡献与交接

- 必须交付：对应输出编号与贡献标准。
- 必须证据：对应关键控制点和监督审查要求。
- 下游用途：说明谁消费什么，以及何时允许消费。
- 已知限制：保留影响用途的假设、缺口和风险。

## 实施与验证契约

- 最小实施范围：列出目标资产与必要调用方边界。
- 环境前提：列出依赖、隔离、超时及清理要求。
- 入口就绪条件：命令或类型化入口真实可用且获准。
- 停止条件：缺权限、缺依赖、超时、零命中或必要证据缺失。

## 结果与来源导航

- 候选产物：引用当前候选，不粘贴整个实现。
- 机械证据：引用真实运行回执，不手填成功结果。
- 监督审查：引用真实审查身份、发现及签章。
- 未完成事项：从唯一权威记录定位，不复制逐轮流水。
- 恢复来源：仅恢复任务填写原始实例与授权来源。
```

## 5. 字段实例化与状态单源

- 模板 READY 仅为示意；实例化时缺必需输入或授权必须登记 BLOCKED。
- 实际进度若由已核验控制器覆盖，使用其任务记录，状态卡由程序生成。
- 没有覆盖时临时使用平台任务记录，明确没有程序强制或防篡改保证。
- 契约头部状态与门禁字段仅为带来源的边界快照，不手工逐轮同步。
- 权威记录变化后旧快照不得用于放行；消费者必须定位真实来源。
- 计划和 ADR 不保存逐轮流水；实例化契约不是新建第二份账本。
- 接管、契约变化和阶段边界校验身份与版本，不逐修改手工计算指纹。

## 6. 单焦点活动入口

目标活动入口[位置](../tasks/_active.md)采用下述薄指针结构，启用须另获授权；空闲时身份与任务引用均为 null，不把归档任务列为执行焦点。

```yaml
schema_version: "1.0-draft"
active_task_id: DEMO-001
instance_id: null
task_ref: "specs/tasks/TU-DEMO-001.md"
contract_version: "1"
authority_ref: null
```

- 活动入口只绑定一个焦点，不保存任务正文、验证结果或重复检查单。
- 控制器覆盖时由控制器输出；平台过渡期作为获准焦点绑定，不承载进度。
- 焦点变更先停止原任务副作用，确认无未知在途动作并保留未完成事项。
- 活动入口缺失是正常空闲状态，不盲读默认旧任务或最新归档。
- 显式指定任务优先；缺失或非法时阻塞相关任务，不能静默替换。
- 恢复暂停任务须有明确授权，不因活动指针改变获得恢复许可。

## 7. 完工与归档

1. 全部必需 CS/SR 与父目标验收通过，才登记贡献完成。
2. 稳定知识写入公共领域规范须另获相应写入授权。
3. 归档须确认整项绑定任务完成且当前授权允许归档。
4. 采用时间、任务及实例标识组成不覆盖的目标目录。
5. 完整保存契约及所需证据导航，取得成功回执后复核源身份和内容版本。
6. 目标完整性未知、保存失败或源变化时保留源，进入相关 BLOCKED。
7. 复核通过且获准处理源后才能退役活动引用，不固定清空旧默认入口。
8. 历史恢复创建新实例并重验，归档通过记录不能继承为新执行绿灯。

本次不实际创建活动入口、任务实例或归档；目录迁移详见[宿主模块](05-host-adaptation.md)。
门禁字段、机械回执与审查签章的对应关系见[模块四](04-kcp-sod-gates.md)。
返回[全局索引](00-governance-index.md)。
