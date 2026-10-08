---
plan_id: "REPLACE_WITH_UNIQUE_PLAN_ID"
status: DRAFT
scenario: structural
impact_tier: M
requires_adr: true
adr_file: null
verification_type: config_syntax
verification_command: null
verification_command_status: PLANNED_NOT_YET_CREATED
authorization: "仅方案草稿；实施须明确授权"
session_id: null
---

# Implementation Plan

## 契约实例化与授权

- 本模板不是可执行计划。交付前填写唯一计划标识、实际 ADR 引用和适配场景的限时验证命令；不得直接执行占位内容。
- 场景可选 algo、structural、bugfix、ops；影响级别可选 S、M、L；验证类型可选 unit_test、config_syntax、diff_cleanliness。
- requires_adr 为 true 时，adr_file 必须指向真实关联 ADR；为 false 时使用 null。未知会话标识保持 null，不编造。
- verification_command_status 必须反映验证资产是否已经存在；尚未创建时保持 PLANNED_NOT_YET_CREATED，创建并检查后才标记 AVAILABLE。AVAILABLE 不代表测试已通过。
- 记录当前用户授权及其与立项时授权的区别；读取计划、达到可行阈值或模板状态均不能自行扩大授权。

## 摄入路由与执行绑定

- 用户显式指定计划时只读取该候选，跳过默认暂存入口；指定文件缺失或非法时报告阻塞，不静默替换。
- 无显式路径时才探测默认暂存计划；相关且有效才绑定，无关计划不抢占。
- 默认入口缺失是正常状态，按意图发现归档候选、请求选择、空闲或提出新方案；不自动执行最新归档。明确的小修复及运维任务可走轻量路径。
- 分别处理文件缺失、权限拒绝、磁盘错误和格式损坏。历史计划默认只读，恢复须明确授权、建立保留来源的新执行实例并重新验证，不继承旧绿灯。
- 只读任务仅取证和会话交付，不写文件、不运行验证、不转正或归档。
- 执行时记录绑定路径、计划标识、当前内容指纹及阶段；修改前复核未被替换，合法更新后记录新指纹。指纹保存在独立执行记录中，避免计划自引用摘要。
- 状态：INTAKE → READ_ONLY / IDLE / NEEDS_SELECTION / READY；获准实施后 READY → EXECUTING → VERIFYING → COMPLETED → ARCHIVED。失败进入 BLOCKED，明确暂停进入 SUSPENDED，获准恢复后重新校验再进入 READY。

## Goal
[Brief description of the objective]

## Non-goals
[What is explicitly NOT being done]

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Architecture Baseline
- **Relevant components**: 
- **Applicable invariants**: 
- **Relevant ADRs**: 
- **Existing patterns to preserve**: 

## Impact Analysis
- **Interfaces**: 
- **Data ownership**: 
- **Dependencies**: 
- **Runtime and deployment**: 
- **Security and NFRs**: 

## Epic 1: <architecture-aligned outcome>

### Story 1.1: <independently verifiable behavior>
- **Acceptance criteria**:
- **Affected components**:
- **Architecture invariants**:
- **Dependencies**:
- **Risks**:

#### Task 1.1.1: <task name>
- **Files expected to change**:
- **Coherent code change**:
- **Verification to run**:
- **Evidence to produce**:

## Validation Matrix
[How will this be verified overall?]

- 按阶段列出实际验证命令、前置依赖、验收断言和失败用例；尚未创建的验证资产明确列为待实现。
- 所有命令串行、前台同步运行，封闭标准输入；探测、验证、构建分别采用 15s、30s、600s 进程级超时，非交互选项按命令实际支持选择。
- 每阶段记录工作目录、命令、退出状态、关键输出及目标；失败、超时或缺依赖即阻塞，不推进下一阶段，不降低断言标准。
- 仅运行与本次改动相关的验证；配置与隔离分发测试不等于业务单测。静态权限用例和参考路由模型不证明目标 Roo 的运行时行为。
- 如要求运行时验收，记录真实版本、有效配置、用户输入、工具请求及结果；证据缺失时保留阻塞，不以静态测试替代。

## 完工与绑定式归档

- 对账实现差异、相关验证证据和架构边界；仅全部必需门禁通过后完成任务。
- 仅 requires_adr 为 true 且全部必需验收通过时转正关联 ADR；其他任务与旧 ADR 保持独立。
- 工程阶段仅将已经验证的事实及真实溯源写入项目事实基线，不把提案或静态测试外推为运行时事实。
- 只归档实际绑定的活动计划，不固定清空默认暂存入口；无绑定计划的轻量任务不执行归档。
- 归档目标包含时间与计划标识且不得覆盖；先确认目标完整保存，再复核源标识与指纹未变化并处理活动副本。归档失败保留源文件，历史输入和其他暂停任务保持独立。

## Rollback Plan
[How to revert if things go wrong]

## Open Questions
> [!WARNING]
> [Any open questions that need user input before execution]

## Approval Status
- [ ] Waiting for user approval
