---
document_id: BMAD-GOVERNANCE-04
schema_version: "1.0-draft"
status: PROPOSED
language: zh-CN
owner: 项目维护者
scope: CS/SR 接受、关键控制点、职责分离与失败保护
runtime_verified: false
---

# 模块四：内控关键控制点与职责分离

质量与内控嵌入贡献生产、审查和依赖释放的流程边界。
机械验证与独立监督审查必须同时成立，终止或文件保存成功不等于贡献接受。

## 1. 双重门禁公式

[AutoSwarm 原文公式](../../docs/Ralph-Wiggum-Loop/autoswarm.md:185)将贡献检查与审查批准合取。
本规范采用委托指定的简记，其中下标时间表示当前有效契约和候选：

$$a_t(g) = C_g(z_g) \wedge R_g(g)$$

- g：当前 Task Unit，不是角色或整个会话。
- z_g：当前候选结果、必要证据、假设与限制组成的审查包。
- C_g：贡献规格 CS 的完整判定，包括内容要求与全部必需机械检查。
- R_g：具有所需独立性和批准权限的 Supervisor 审查结论。
- a_t(g)：当前贡献是否接受；只有两个条件都为真时才为 1。
- 未知、缺证据、过期或未审查不能当成真值；评估未完成时保持 UNKNOWN。
- 机械检查只是 C_g 的必要组成，不自动证明业务内容或架构正确。

[原文允许免审查贡献](../../docs/Ralph-Wiggum-Loop/autoswarm.md:473)；本规范按委托收紧，不设置免 SR 通道。
依赖释放只消费当前接受结果，失败或取消的终止结果不能充当成功输入。

## 2. 门禁判定表

| CS | SR | 接受 | 后续动作 |
|---|---|---|---|
| PASS | APPROVED | true | 核对版本、权限与父目标后释放精确依赖 |
| FAIL | 任意 | false | 保留现场，预算内修正，不推进依赖 |
| PASS | REJECTED | false | 按具体审查发现退回修正 |
| UNKNOWN/BLOCKED | 任意 | false | 补齐必需证据或解除阻塞 |
| PASS | UNKNOWN/BLOCKED | false | 等待真实审查，不以自审冒充 |
| STALE | 任意 | false | 重验受影响检查并重审当前候选 |

CS/SR 通过不自动授权部署、ADR 转正、公共事实登记或归档。
父任务须对已接受子贡献重新整合验收，子项通过不等于整体完成。

## 3. 流程内关键控制点

| 控制点 | 控制要素 | 控制程序 | 失败保护 |
|---|---|---|---|
| KCP-INTAKE | 身份、契约、阶段、输入与真实授权 | 接管边界定位来源，核对必需输入接受条件 | 停止相关副作用，不抢占旧任务 |
| KCP-PRODUCE | 允许路径、所有权、保护资产与预算 | 获准入口执行最小连贯改动 | 保留既有修改，不越权修复 |
| KCP-VERIFY | 当前候选、环境、检查集与原始结果 | 受控运行逐项收集回执 | 超时、零命中、必需跳过不得通过 |
| KCP-REVIEW | 父目标、CS 覆盖、影响边界与独立性 | Supervisor 核对原件并签章 | 不接受自批或证据不适用 |
| KCP-RELEASE | 当前双重接受、依赖与消费范围 | 权威入口核对后释放指定输入 | 不因消息到达或结束状态放行 |
| KCP-PUBLISH | 稳定知识与相应写入授权 | 定向更新公共领域规范 | 不登记未验证事实或全量流水 |
| KCP-ARCHIVE | 全任务完成、授权与源版本 | 防覆盖保存、完整性与源复核 | 失败或源变化保留源 |

[内控依据](../../docs/Ralph-Wiggum-Loop/service-process-IT-quality-engage.md:49)要求控制要素与程序构筑在流程中。
控制强度按业务风险确定，但不得删去本任务已声明的必需门禁。

## 4. 机械验证回执路径与生产者

当前机械判定入口为[回执路径示意](../../verification/TU-DEMO-001.verdict.json)。
实际文件名遵循任务模板中的命名规则，示意链接不是已存在回执。
原始运行材料位于根级验证区的任务标识与运行标识目录；失败运行也要保留。

- 回执由实际执行器或获准验证工具生成，不由模型事后编造成功 JSON。
- 若只能获得平台命令回执，引用真实平台记录，披露没有标准回执生成器。
- 标准生成器未实现时不能声称格式化回执或硬门禁已经落地。
- 当前入口只定位一个候选的机械判定，重试历史保存在不同运行目录。
- 更新当前入口必须保留旧原件并取得授权，不能覆盖唯一失败证据。
- 一个检查集包含多次运行时逐项绑定原始回执，不能拼接不同候选的成功项。

## 5. 机械回执完整示例

以下为无执行事实的待填示例；null、空检查集与 UNKNOWN 必须导致不放行。

```json
{
  "schema_version": "1.0-draft",
  "task_id": "DEMO-001",
  "instance_id": null,
  "contract_version": "1",
  "candidate_version": null,
  "verification_set_id": null,
  "generated_by": null,
  "generated_at": null,
  "source_receipt_refs": [],
  "environment": {
    "cwd": ".",
    "environment_ref": null,
    "tool_versions_ref": null
  },
  "required_check_ids": ["KCP-01"],
  "checks": [
    {
      "check_id": "KCP-01",
      "criterion_refs": ["CS-01"],
      "required": true,
      "run_id": null,
      "command": null,
      "operation_ref": null,
      "cwd": ".",
      "timeout_seconds": 30,
      "started_at": null,
      "ended_at": null,
      "exit_code": null,
      "timed_out": null,
      "collected_count": null,
      "skipped_required": null,
      "required_observations": ["actual_exit", "applicable_result"],
      "observations_ref": null,
      "cleanup_required": false,
      "cleanup_ok": null,
      "raw_receipt_ref": null,
      "result": "UNKNOWN"
    }
  ],
  "mechanical_status": "UNKNOWN",
  "limitations": ["示例未执行，不是 CS 完整判定或 SR 批准"]
}
```

- 命令与受控操作至少一种必须有真实来源，类型化入口优先但不能虚构可用性。
- 必需检查集合必须与契约一致，缺项、重复冲突或不适用结果不得通过。
- 保真判定须分别核对预先固定且非空的不变量、必要调用边及支持闭包集合，覆盖率均为 100%；不因软目标削减分母。
- 预算遥测须完整包含阶段耗时、唯一正文块数、目标、精确单帧及累计字节、告警、策略、协商能力与真实结果；必需遥测缺失不通过。
- 纯软目标超限仅 Warning，不判 FAIL；完整内容经协商大帧或分片重组认证交付可通过。权限、来源、输入、解压、硬截止、取消、缺片、篡改和实际写出故障仍拒绝。
- 测试必须有实际收集与必要断言；配置检查或获准文档差异审查等非测试允许收集数为 null，不用保存日志成功代替目标验收。
- 清理不适用时声明无需清理；适用而结果未知时 BLOCKED。
- 退出零仍需满足命令特定的必需输出，空输出不一律成功或失败。
- 本示例只记录 mechanical_status，不以它代替完整 CS 或独立 SR。

## 6. 职责分离强度

- 生产职责：形成和修正候选，不能批准自身的独立 SR。
- 验证职责：从真实执行生成机械证据，禁止补写未执行成功。
- 审查职责：核对原件、语义适配、保护边界与已声明标准。
- 批准职责：在明确权限内接受贡献，不扩大为部署或公共登记许可。
- 单会话上下文切片只提供流程上的角色分离，称为 context_only。
- 另一真实审查主体并能核对原件称为 separate_actor，仍需核验身份来源。
- 更强凭据或执行域隔离需额外运行证据，不因不同名字或会话宣称成立。
- 最小独立性由契约明确；本模块模板默认 separate_actor，不能静默降级。

同一模型换提示词的自审可作为补充，但不足以满足独立主体要求。
没有所需主体时阻塞相关接受，不阻止已获准的文档保存。

## 7. Supervisor 独立审查签章

审查材料保存于与候选绑定的运行目录，真实审查主体生成以下结构。
签章是可审计审查记录；没有认证机制时不得称为密码学签名或防篡改保证。

```yaml
schema_version: "1.0-draft"
review_id: null
task_id: DEMO-001
instance_id: null
contract_version: "1"
candidate_version: null
mechanical_verdict_ref: "verification/TU-DEMO-001.verdict.json"
reviewer:
  actor_id: null
  role: Supervisor
  identity_source_ref: null
  independence: separate_actor
  authority_source_ref: null
reviewed_artifact_refs: []
criterion_results:
  - criterion_id: CS-01
    decision: UNKNOWN
    evidence_refs: []
findings: []
parent_objective_assessment: UNKNOWN
decision: UNKNOWN
approval_scope: contribution_acceptance_only
accepted_output_refs: []
limitations: []
signed_at: null
attestation_ref: null
```

- actor_id、身份来源、授权来源、候选与审查原件缺失时不得 APPROVED。
- 每条发现必须对应标准、资产与修正要求，拒绝“感觉不对”等无定位意见。
- 简要审查依据允许保存，不要求也不传播内部思维链。
- 身份声明、内容摘要与同账号可写记录不构成独立认证。

## 8. 驳回、现场保护与回退

1. 固定被拒候选与原始回执定位，登记具体标准及失败事实。
2. 撤销受影响结果的消费资格，不删除原候选或唯一失败现场。
3. 普通失败在当前权限与预算内回到修正，产生新候选再验证和审查。
4. 缺依赖、超时、零命中、必需跳过、权限拒绝或证据缺失进入 BLOCKED。
5. 明确暂停进入 SUSPENDED；取消或不可修复失败保留终止结果且不接受。
6. 已被下游消费的结果失效时，冻结受影响下游，定位其影响和修正范围。
7. 回退仅执行已授权、已定位、能保护用户资产的恢复方案。
8. 不用全库重置、整目录删除或降低断言替代失败分析；恢复未知则阻塞。

## 9. 证据失效与执行约束

- 接管、契约变化与阶段边界核对绑定，不逐修改手工同步摘要指纹。
- 候选、测试、契约或环境变化只重验受影响证据，重新审查接受适用性。
- 已核验且覆盖当前操作的控制器使用类型化入口；否则披露覆盖缺口。
- 获准工程命令串行、前台同步、封闭标准输入，等待真实退出回执。
- 探测 15 秒、验证 30 秒、构建 600 秒，采用进程级超时和必要强杀宽限。
- 工具提前返回不是进程退出；不启动未经授权的后台任务或联网安装。
- 状态保存不触发业务重测，规范提案不提供已实现的硬拒绝保证。

## 10. 门禁验收与交付边界

- 必须分别覆盖正常接受、机械失败、审查驳回与过期证据拒绝。
- 必须覆盖缺身份、缺必需项、超时及清理未知，不以空集默认通过。
- 必须区分阶段通过、父目标完成、转正与归档的独立授权。
- 本次不执行上述运行验收，不创建真实回执或冒写审查签章。

返回[全局索引](00-governance-index.md)，衔接[宿主适配](05-host-adaptation.md)。
