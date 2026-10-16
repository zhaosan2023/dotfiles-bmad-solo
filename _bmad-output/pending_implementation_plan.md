---
plan_id: "BMAD-ANTI-BUREAUCRACY-20261012-01"
status: READY
scenario: structural
impact_tier: M
requires_adr: true
adr_file: "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
verification_type: config_syntax
verification_command: "timeout 30s python3 -B scripts/validate-roo-contracts.py --suite v5 --plan _bmad-output/pending_implementation_plan.md < /dev/null"
verification_command_status: AVAILABLE
authorization: "2026-10-16 用户授权继续同一计划补齐 Epic 5：V5 工程实现、对应反例测试、必要计划与提案契约修订及受控本地验证；保护已有修改，保持 V4 只读；不包含系统安装、账号权限调整、真实宿主激活、真实 Agent 启动、远程无人值守试跑、提交、推送、生产部署、ADR 转正及归档；真实运行时试验须另行一次性确认目标、写入范围、认证和预算；既有超时上限不自行提高"
session_id: null
---

# 实施计划：BMRalph V5 独立套件、双入口减负与远程自主执行

## 契约实例化与授权

- **计划标识**：`BMAD-ANTI-BUREAUCRACY-20261012-01`
- **关联 ADR**：[本任务提案](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)（状态：PROPOSED）。
- **接管契约**：绑定本文件、原计划标识及关联 PROPOSED ADR；当前继续实施授权优先于历史阶段说明。Phase 3 三项局部任务保留，下一批仅按下方 Phase 4 本地契约推进，不恢复其他暂停任务或未知清理状态的旧进程。未知会话标识保持 null。
- **验证命令契约**：静态入口已支持显式 `--suite v4` 与 `--suite v5`；头部选择 V5，P0 分别运行两版本检查与相关契约回归。该入口不执行计划命令，不证明运行时权限或模型行为。真实执行结果由当前平台任务记录引用工具回执，不在本计划或 ADR 镜像逐轮流水。
- **当前授权边界**：新生产实现独立放入 [bmralph-suite-v5](../bmralph-suite-v5/)，公共部署设施仅做兼容扩展；工程分发测试仅操作临时部署根。真实宿主激活、远程试跑、提交、推送、生产部署、转正及归档不由本次实施指令隐式授权。
- **历史语境**：文中此前“本次只结晶”“尚未创建”“未运行”描述 2026-10-15 设计基线，不再作为当前编码禁令，也不作为当前实现或验证结果；各阶段资产及命令按实际实现修订，全部验收承诺保留。

## 1. 目标 (Goal)

先删除不必要的工作，再由薄程序承揽机械工作。保留分析入口的三遍阅读、探索、审计及人机目标收敛；工程入口接收明确需求或现成方案，完成小任务与真实验证，不重新生成全部分析。

在原轻量执行控制器设计上补充输入预算、新工程会话、任务期远程循环与必要持久记忆。目标是：人通过本地 IDE 提交已授权任务后，VPS 上独立 Agent 仍能选择任务、自主思考、修改、验证并启动下一轮，不依赖本地客户端在线。

本次执行同一计划，不创建其他任务、不恢复历史计划；按用户确认的既有证据验收本地原语，不继承其他任务的通过状态。原 Epic 1–6 与新增版本隔离、部署兼容工作全部保留；获准实施不表示任何新增验收已通过。Phase 2 远程运行时不在本次授权或阻塞项内，不以本地阶段交付代替全计划完成。

版本放置以 [bmralph-suite-v5](../bmralph-suite-v5/) 为新套件唯一生产源码根目录，现有 [bmad-suite-v4](../bmad-suite-v4/) 作为本任务不修改的对照基线，不宣称整个仓库已冻结或工作树洁净。V5 规则、入口、引用、运行程序和专属测试自包含，禁止运行时回指 V4；仓库根部署基础设施只做兼容性扩展，不承载 V5 任务循环。现有共享文档保留于原路径，不建立镜像计划或 ADR。

## 2. 非目标 (Non-Goals)

1. 不建设泛化多智能体平台、永久调度服务或复杂记忆数据库；仅允许后续获准实现的任务期持久进程。
2. 不修改模型网关、代理协议与超时常量，不承诺把 1 小时固定压缩为 20 分钟。
3. 不取消适用于已批准范围的竞态、隔离或集成验证；不临时追加范围外验证阻断交付。
4. 不宣称覆盖宿主原生附件、全部工具旁路或所有版本；不把静态配置视为运行时权限保证。
5. 不修改 V4 对照源码或已接受 ADR，不覆盖用户既有改动；不执行真实宿主激活、远程启动、提交、推送、生产部署、转正及归档。本次允许计划内生产源码实施及本地相关验证；项目事实仅能按门禁登记已验证内容，不能登记提案或模拟测试为运行时事实。

## 本轮阶段契约：Phase 1 本地交付与后续边界

本节保存授权及验收范围，不保存执行流水或第二份任务进度。下面矩阵的 P0–P6 是验证目标编号，不等同于 Phase 1/Phase 2 生命周期阶段。

- Phase 1 交付范围：Epic 7 的本地版本隔离、来源绑定与锁原语；Epic 2 的本机 Python 类型化执行器及证据裁决；Epic 4 的本地字节预算和输入组装；Epic 3 的本地反例补齐；Epic 6 的范围内阶段报告。
- 既有原语验收依据采用当前用户确认的 231 项专属单测实测通过（退出码 0，57s）和两版本静态契约通过，不默认重复全量测试。相关实现、测试或环境发生变化后，仅重验受影响证据；新增反例必须实际运行。
- 受控回滚门禁：在临时根复用公共事务，恢复本批次的原字节、权限、新建与删除状态；保护第三方、用户既有改动及回滚前/回滚中的并发修改。冲突须保留用户内容、备份与恢复受阻记录，不执行真实工作树回滚。
- 进程树门禁：真实同组孤儿不得因主进程退出零而通过；SIGINT/SIGTERM 中断须阻断并清理同组子进程；无法确认组消失时必须阻断。隔离夹具的 Linux subreaper 只提供可控收养/回收条件，不视为生产监督器已实现收养，也不外推脱离会话、容器或任意后代清理。
- 契约封顶：分别运行显式 V4、V5 计划静态校验及相关契约回归；静态配置操作尚无类型化入口，使用已有获准命令，单测使用已实现的类型化入口。每项保留真实工作目录、退出结果及证据定位。
- Phase 2 非目标：Epic 5 的目标独立运行时、真实新 Agent 会话、任务期循环、认证、远程无人值守试跑及关闭客户端后的推进/重连/停止门禁，真实宿主加载与权限核验均未获本轮授权，不作为 Phase 1 勾选阻塞项。
- 其他未完成承诺继续保留：固定 GCC/musl 镜像及隔离复用、容器清理、配置/专项竞态类型化操作、活动计划进度迁移与循环接入、累计工具预算运行接入、宿主自动加载观察、完整部署/回切兼容与事务诊断、跨部署根保护、实际权限隔离及对照效果测量。原语验收不表示这些承诺通过；它们不属于本轮新增反例与本地原语交付的封顶目标。
- 全计划 AC 继续保持原承诺，不因 Phase 1 交付整体勾选；ADR 保持 PROPOSED，计划保留活动副本。当前平台任务记录仍是唯一临时进度入口，没有程序防篡改保证；不迁移类型化清单、不转正、不归档、不提交、推送或部署。

## Phase 3 契约：循环与真实活动计划对接

- 获准范围：活动计划中的显式结构化任务、就绪查询、单任务输入组装和驱动；从真实验证回执生成至多 80 行且受字节预算约束的状态卡；Roo CLI／无头后端适配边界、凭据存在性探测、认证与退出码严判、API 调用超时；本地模拟断网后当前步骤完成及回执落盘。
- 进度切换：本轮三项子任务采用本文件内唯一结构化清单；仅程序核验真实通过回执后更新对应任务，不由模型手工勾选制造完成事实。状态卡只作投影，平台待办只跟踪实施过程，不镜像该清单的执行进度。原 Epic、AC 和范围外未完成承诺继续保留，三项完成不等于全计划完成。
- 运行时边界：只实现并验证本地驱动抽象及隔离夹具；实际 Roo 的来源、版本、无头参数、新会话、权限和独立认证必须另行实证。不得猜测 Roo 参数、自动安装依赖、继承 IDE 登录态或静默换引擎。缺少真实运行时不阻塞独立的本地适配实现，但真实后端必须失败关闭。
- 验收要求：每项对应反例必须实际运行；完成口令、Agent 退出零、文件变化和日志保存成功均不能代替相关单测通过；外部计划变更、超时、认证失败和清理不明须阻断并保留成果。保存或查询状态不触发业务重测。
- 断网边界：使用隔离夹具模拟连接不可用，不改变宿主网络、防火墙或 SSH；本地当前步骤及回执落盘不证明目标 VPS 关闭 IDE 后真实 Agent 能开始下一轮，不勾选 AC 9 或 P5。
- 历史证据：采用用户确认的 Phase 1／2 既有单测与契约通过作为接管依据，不导入本轮完成回执；实现、契约或环境变化后重验受影响证据。
- 交付边界：不提交、不推送、不生产部署、不转正 ADR、不归档；保留全部范围外未完成事项。
- 本轮结构化清单仅覆盖 Phase 3 三项本地交付，不覆盖原 Epic 和全计划 AC；全部三项完成只表示本轮局部验收完成。后文 Phase 1 的“未迁移”描述保留为历史边界，本轮进度以此清单及当前有效回执为准。
- 计划适配另需运行对应写回反例，监督器改动另需相关回归；下列任务验证不能替代这些阶段门禁。真实 Roo 及远程断开仍未验证，相关原承诺继续保留。

## Phase 4 契约：Epic 5 最小本地工程闭环

- 本批稳定目标：补齐显式获准任务集合的失败反馈、预算内修复及依赖推进；保留 Python 薄控制器和独立验证原语。原 Epic、全部 AC 和范围外承诺不删除、不整体勾选。本节不是全计划散文的无限执行授权。
- 唯一进度仍为下面同一结构化清单。新增项初始为 PENDING，只有程序核验对应真实 PASS 回执后才写回完成；平台待办仅跟踪工程过程。控制器未覆盖的契约修订和配置检查临时引用平台真实回执，不建立第二份任务进度或声称程序防篡改。
- 先复用仍有效的 Phase 3 回执。实现、测试目录、验证选择或环境变化后，按现有证据契约重验受影响项并由程序刷新回执；保存计划和无关文档不触发业务重测。不得删掉现有覆盖输入、降低测试下限或取消必需项来维持旧绿灯。
- P4-BUDGET：纠正将整个驱动进程时限称为单次 API 请求时限的混淆，区分模型请求、工具执行、Agent 会话和批次预算。保留现有 30 秒验证级驱动进程上限、15/30/600 秒工具分级和 600 秒任务期上限；真实 Roo 的单请求及会话参数尚未核验，不编造参数或自行延长上限。涉及既有超时契约扩大时先停下取得明确确认。
- P4-BATCH：批次必须显式列出获准任务标识及各任务必要输入，程序仅从该集合选依赖已由当前有效证据满足的任务。一次启动在预算内继续当前失败任务，单任务独立验证通过并保存后自动选择下一获准任务；集合之外的就绪项不得执行。无头调用零退出、完成口令或文件变化均不代替业务通过。
- 每次修复采用新会话，只携带必要约束、未完成成果和真实失败反馈，不恢复完整聊天。当前任务失败、必需验证零命中或跳过、认证/权限失败、绑定变化、取消、超时及清理不明均禁止推进依赖；无进展及轮次/调用预算耗尽停止新调用并保留成果。没有可靠费用计量时明确报告未覆盖，不声称费用预算已强制生效。
- P4-ISOLATION：接入现有 V5 来源绑定和共享读取租约；本地反例只使用项目内合成部署根，不激活真实宿主。运行中的监督器使用与待修改源码隔离的候选运行副本，记录实际来源绑定并在接管和阶段边界复核；运行期间修改候选源码不得热替换绑定程序。升级须先停止、确认清理、验证候选，再经获准边界启用。
- 租约覆盖全部受管调用及清理确认。清理未知时阻断后续调用和重启，不据旧 PID 恢复；如现有原语不能覆盖所需清理生命周期，明确阻塞该集成，不把释放文件锁当作全部进程结束证据。协作锁和同账号运行副本不等于系统权限隔离。
- 真实运行时门禁保持关闭：当前读取仅定位到 Roo 3.54.0 扩展的版本声明及无头 CLI 变更线索，未取得本机独立入口、新会话、规则/模式加载、独立认证或取消的运行能力证据；不得据此启动、安装、继承 IDE 登录态、猜测 Roo 参数、换引擎或建设 GUI 自动点击桥接。
- 真实试跑前集中列明工作区、写入范围、认证方式、时间、轮次、模型调用/费用预算和停止方式并取得明确授权。关闭客户端后必须有新的真实模型/工具步骤及轮次证据；本地夹具通过、进程存活或文件变化不通过 AC 9 或 P5。
- 本批相关本地反例还须覆盖：未授权任务不选、失败不推进、新会话接收失败退出结果、跨任务反馈不串线、契约变化阻断、预算停止、取消后进程清理、清理未知禁止重启、来源租约及运行副本隔离。通过后仅交付本地阶段，不转正 ADR、不归档、不提交、不推送、不部署，不宣称自主执行或效率提升已实证。

```bmad-tasks
{
  "schema_version": 1,
  "plan_id": "BMAD-ANTI-BUREAUCRACY-20261012-01",
  "tasks": [
    {
      "task_id": "P3-PLAN",
      "title": "活动计划适配、单任务驱动及完整有界状态卡；局部验收不代表全计划完成",
      "depends_on": [],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_loop_guards.py",
        "minimum_tests": 18,
        "required_tests": [
          "test_loop_guards.LoopGuards.test_explicit_progress_write_completes_one_task_and_generates_bounded_card",
          "test_loop_guards.LoopGuards.test_failure_with_progress_permission_does_not_check_off_task",
          "test_loop_guards.LoopGuards.test_plan_query_does_not_create_loop_or_business_receipts",
          "test_loop_guards.LoopGuards.test_cli_output_overflow_exits_nonzero_and_preserves_receipt_locator"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad-loop.py",
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase4-20261016/run-14fce12179244e99b29e4610e69b359d.verdict.json"
    },
    {
      "task_id": "P3-BACKEND",
      "title": "隔离无头驱动抽象、认证与超时失败关闭；真实 Roo 来源、权限及独立认证仍待实证",
      "depends_on": [
        "P3-PLAN"
      ],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_agent_backend.py",
        "minimum_tests": 17,
        "required_tests": [
          "test_agent_backend.AgentBackendGuards.test_missing_credentials_blocks_before_agent_or_business_execution",
          "test_agent_backend.AgentBackendGuards.test_unauthorized_driver_is_never_started",
          "test_agent_backend.AgentBackendGuards.test_authentication_and_permission_failures_stop_without_retry",
          "test_agent_backend.AgentBackendGuards.test_nonzero_exit_cannot_be_overridden_by_valid_ok_result",
          "test_agent_backend.AgentBackendGuards.test_api_timeout_cleans_group_and_preserves_local_artifacts",
          "test_agent_backend.AgentBackendGuards.test_real_roo_without_required_runtime_evidence_fails_closed",
          "test_agent_backend.AgentBackendGuards.test_simulated_disconnection_allows_local_step_and_durable_receipts",
          "test_agent_backend.AgentBackendGuards.test_network_error_blocks_and_keeps_unfinished_changes",
          "test_agent_backend.AgentBackendGuards.test_new_round_receives_actual_failure_feedback_in_new_session",
          "test_agent_backend.AgentBackendGuards.test_timeout_dimensions_do_not_raise_existing_caps",
          "test_agent_backend.AgentBackendGuards.test_real_backend_cannot_be_selected_as_fixture",
          "test_agent_backend.AgentBackendGuards.test_environment_preparation_does_not_consume_unstarted_session_budget",
          "test_agent_backend.AgentBackendGuards.test_environment_preparation_exhausting_batch_does_not_launch_agent"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad-loop.py",
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py",
          "bmralph-suite-v5/scripts/bmad_suite_source.py",
          "bmralph-suite-v5/scripts/bmad_suite_lease.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase4-20261016/run-b3935e64965447cbbb03c38a36fe608d.verdict.json"
    },
    {
      "task_id": "P3-OFFLINE",
      "title": "本地模拟断网与持久回执；原 Epic、全部未验收 AC、真实远程两轮及部署来源租约等范围外承诺保留",
      "depends_on": [
        "P3-BACKEND"
      ],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_agent_backend.py",
        "minimum_tests": 17,
        "required_tests": [
          "test_agent_backend.AgentBackendGuards.test_missing_credentials_blocks_before_agent_or_business_execution",
          "test_agent_backend.AgentBackendGuards.test_unauthorized_driver_is_never_started",
          "test_agent_backend.AgentBackendGuards.test_authentication_and_permission_failures_stop_without_retry",
          "test_agent_backend.AgentBackendGuards.test_nonzero_exit_cannot_be_overridden_by_valid_ok_result",
          "test_agent_backend.AgentBackendGuards.test_api_timeout_cleans_group_and_preserves_local_artifacts",
          "test_agent_backend.AgentBackendGuards.test_real_roo_without_required_runtime_evidence_fails_closed",
          "test_agent_backend.AgentBackendGuards.test_simulated_disconnection_allows_local_step_and_durable_receipts",
          "test_agent_backend.AgentBackendGuards.test_network_error_blocks_and_keeps_unfinished_changes",
          "test_agent_backend.AgentBackendGuards.test_new_round_receives_actual_failure_feedback_in_new_session",
          "test_agent_backend.AgentBackendGuards.test_timeout_dimensions_do_not_raise_existing_caps",
          "test_agent_backend.AgentBackendGuards.test_real_backend_cannot_be_selected_as_fixture",
          "test_agent_backend.AgentBackendGuards.test_environment_preparation_does_not_consume_unstarted_session_budget",
          "test_agent_backend.AgentBackendGuards.test_environment_preparation_exhausting_batch_does_not_launch_agent"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad-loop.py",
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py",
          "bmralph-suite-v5/scripts/bmad_suite_source.py",
          "bmralph-suite-v5/scripts/bmad_suite_lease.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase4-20261016/run-b3935e64965447cbbb03c38a36fe608d.verdict.json"
    },
    {
      "task_id": "P4-BUDGET",
      "title": "分离超时与预算职责并保持既有上限；真实 Roo 参数及会话时限调整仍须核验和授权",
      "depends_on": [
        "P3-OFFLINE"
      ],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_agent_backend.py",
        "minimum_tests": 17,
        "required_tests": [
          "test_agent_backend.AgentBackendGuards.test_missing_credentials_blocks_before_agent_or_business_execution",
          "test_agent_backend.AgentBackendGuards.test_unauthorized_driver_is_never_started",
          "test_agent_backend.AgentBackendGuards.test_authentication_and_permission_failures_stop_without_retry",
          "test_agent_backend.AgentBackendGuards.test_nonzero_exit_cannot_be_overridden_by_valid_ok_result",
          "test_agent_backend.AgentBackendGuards.test_api_timeout_cleans_group_and_preserves_local_artifacts",
          "test_agent_backend.AgentBackendGuards.test_real_roo_without_required_runtime_evidence_fails_closed",
          "test_agent_backend.AgentBackendGuards.test_simulated_disconnection_allows_local_step_and_durable_receipts",
          "test_agent_backend.AgentBackendGuards.test_network_error_blocks_and_keeps_unfinished_changes",
          "test_agent_backend.AgentBackendGuards.test_new_round_receives_actual_failure_feedback_in_new_session",
          "test_agent_backend.AgentBackendGuards.test_timeout_dimensions_do_not_raise_existing_caps",
          "test_agent_backend.AgentBackendGuards.test_real_backend_cannot_be_selected_as_fixture",
          "test_agent_backend.AgentBackendGuards.test_environment_preparation_does_not_consume_unstarted_session_budget",
          "test_agent_backend.AgentBackendGuards.test_environment_preparation_exhausting_batch_does_not_launch_agent"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad-loop.py",
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py",
          "bmralph-suite-v5/scripts/bmad_suite_source.py",
          "bmralph-suite-v5/scripts/bmad_suite_lease.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase4-20261016/run-b3935e64965447cbbb03c38a36fe608d.verdict.json"
    },
    {
      "task_id": "P4-BATCH",
      "title": "显式获准任务集合、新会话失败修复与独立验证通过后的自动依赖推进；仅本地反例",
      "depends_on": [
        "P4-BUDGET"
      ],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_batch_guards.py",
        "minimum_tests": 12,
        "required_tests": [
          "test_batch_guards.BatchGuards.test_failed_verification_retries_same_task_in_new_session",
          "test_batch_guards.BatchGuards.test_pass_automatically_selects_next_authorized_ready_task",
          "test_batch_guards.BatchGuards.test_unlisted_ready_task_is_never_selected",
          "test_batch_guards.BatchGuards.test_feedback_does_not_leak_between_tasks",
          "test_batch_guards.BatchGuards.test_budget_exhaustion_stops_new_calls_and_preserves_changes",
          "test_batch_guards.BatchGuards.test_contract_change_blocks_dependency_progress",
          "test_batch_guards.BatchGuards.test_mismatched_or_duplicate_batch_request_blocks_before_call",
          "test_batch_guards.BatchGuards.test_agent_cannot_modify_acceptance_to_manufacture_pass",
          "test_batch_guards.BatchGuards.test_initial_ready_task_is_selected_by_program_not_request_order",
          "test_batch_guards.BatchGuards.test_future_task_acceptance_change_blocks_before_current_verification",
          "test_batch_guards.BatchGuards.test_skipped_required_test_blocks_without_retry_or_next_task",
          "test_batch_guards.BatchGuards.test_missing_required_test_blocks_without_retry_or_next_task"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad-loop.py",
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_context_inputs.py",
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py",
          "bmralph-suite-v5/scripts/bmad_suite_source.py",
          "bmralph-suite-v5/scripts/bmad_suite_lease.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase4-20261016/run-631c3f63aeaa4c1a982830b7140525fc.verdict.json"
    },
    {
      "task_id": "P4-ISOLATION",
      "title": "来源绑定、读取租约与隔离运行副本接入，取消清理及清理未知禁止重启；不激活真实宿主",
      "depends_on": [
        "P4-BATCH"
      ],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_batch_isolation.py",
        "minimum_tests": 7,
        "required_tests": [
          "test_batch_isolation.BatchIsolationGuards.test_source_lease_covers_calls_and_confirmed_cleanup",
          "test_batch_isolation.BatchIsolationGuards.test_source_change_blocks_without_restoring_assets",
          "test_batch_isolation.BatchIsolationGuards.test_source_edit_does_not_hot_replace_running_copy",
          "test_batch_isolation.BatchIsolationGuards.test_cancel_confirms_all_managed_processes_ended",
          "test_batch_isolation.BatchIsolationGuards.test_unknown_cleanup_blocks_restart",
          "test_batch_isolation.BatchIsolationGuards.test_distribution_entry_cannot_claim_isolated_copy",
          "test_batch_isolation.BatchIsolationGuards.test_isolated_batch_repairs_failure_then_advances_under_same_lease"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad-loop.py",
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_suite_source.py",
          "bmralph-suite-v5/scripts/bmad_suite_lease.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py",
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_context_inputs.py",
          "scripts/asset_safety.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase4-20261016/run-92a653bd2b854eb1a4d9989968c7112e.verdict.json"
    }
  ]
}
```

## 3. 高价值验收指标 (High-Value Acceptance Criteria)

- [ ] **AC 1 (普通测试安装次数为 0)**：实现 L0 环境与 L1 验证分离，测试执行时不发生重复依赖/工具链安装（`apk add` 安装次数为 0）。
- [ ] **AC 2 (模型手工对账次数为 0)**：彻底撤销日常编码的逐修改指纹计算，模型手工维护/同步元数据与 SHA-256 的次数为 0。
- [ ] **AC 3 (状态保存自证回环为 0)**：当前状态由程序从真实命令结果中提取生成；保存状态不触发业务重测，递归复验次数为 0。
- [ ] **AC 4 (短上下文接管且无遗漏)**：接管任务无需全文回灌历史，下一轮默认仅注入当前目标、授权边界、<=80 行有界状态卡与差异定位，未完成事项不丢失。
- [ ] **AC 5 (输出预算真实生效且不掩盖失败)**：原始日志保留在程序端，模型仅接收有界摘要；截断明确标注，测试失败但日志工具成功时整体严判为 RED。
- [ ] **AC 6 (静态契约通过)**：运行下表 P0 的显式 V4、V5 检查及相关契约回归，退出码分别为 0；只证明静态契约，不证明远程运行时。此处保留验收承诺，不镜像平台当前进度。
- [ ] **AC 7 (双入口完整保留)**：分析入口保留三遍阅读和只读边界；工程入口直接消费现成方案；明确小修复不强制 ADR 或完整分析，两个平台的入口与下层流程一致。
- [ ] **AC 8 (上下文按任务重建)**：每轮启动新工程会话，不自动续接旧聊天；受控输入和工具输出遵守预算，相关约束、未完成修改、必要发现和最近有效失败不丢失。行数上限不能替代总输入预算。
- [ ] **AC 9 (断开后自主推进)**：目标 VPS 上运行真实 Agent；关闭本地 IDE 后完成当前步骤并自主启动下一轮。仅循环进程存活、文件变化或清空界面不算通过。
- [ ] **AC 10 (真实反馈与有界停止)**：实际验证失败不得推进任务；普通失败可在预算内自主修复。超时、取消、费用/轮次预算耗尽或持续无进展时明确停止并保留成果，不以完成口令决定成功。
- [ ] **AC 11 (唯一任务进度)**：目标设计使用本计划任务清单作为任务进度唯一载体；状态卡只是程序生成的有界视图，验证回执保存事实，不再人工维护第二份进度。该设计须先在 V5 修订对应规则，不能视为已生效或要求改写 V4。
- [ ] **AC 12 (版本隔离可审核)**：新增生产资产全部落在 [V5 套件](../bmralph-suite-v5/)，本任务不修改 [V4 套件](../bmad-suite-v4/)。V5 可独立采集、校验和部署，运行路径不依赖 V4；原待办按新落点保留，历史证据不移植为 V5 通过记录。
- [ ] **AC 13 (显式版本与更新不串线)**：部署入口支持显式 V5；仓库更新与套件选择分离，更新后的新版入口保留用户指定版本。未指定版本的新安装兼容默认暂保留 V4；已有安装执行无版本更新时，保留受管来源记录中已核验的激活版本，记录缺失、损坏或无法唯一判断时阻塞并要求显式选择，不回退 V4。首次启用 V5 必须显式选择；改变默认须另作明确决定。所选源缺失、参数冲突或标签不含所选套件时停止，不回退到其他套件。
- [ ] **AC 14 (部署与回切可追溯)**：来源清单和状态输出能区分套件身份、主版本、实际源路径、提交及源差异；同提交中的 V4/V5 标签缓存互不误复用。单一部署根默认仅激活一套受管规则，V4→V5→V4 回切保护第三方资产、用户修改和事务恢复证据；不宣称可同根同时激活。
- [ ] **AC 15 (安装不暗启任务)**：安装入口、帮助与状态文案同步版本选择；安装、更新、部署及 IDE 重载均不启动 Ralph，不安装模型认证，不提交、推送或部署业务服务。工程测试仅在临时部署根运行；真实宿主激活与远程试跑另获授权。

## 4. 实施路径与 Epic 划分

### Epic 1: 消除冗余责任与规则去肥增瘦 (Pruning Redundancy & Lean Rules)

#### Story 1.1: 废除高频微步绑定与多文档状态镜像
- **任务 1.1.1**：只读参照 [V4 工程规则](../bmad-suite-v4/roo/rules-bmad-engineer/01-bmad-engineer-core.md:9)，在拟建 [V5 工程规则](../bmralph-suite-v5/roo/rules-bmad-engineer/01-bmad-engineer-core.md)及 V5 下层流程实现对齐；校验集中在接管、契约变化与阶段边界，不重新引入逐修改指纹。V4 已有条款不是 V5 已通过证据，不修改 V4 对照基线。
- **任务 1.1.2**：取消逐轮流水与多文档镜像；将计划分为稳定的目标/验收与可调整的任务清单，任务清单保存唯一进度及必要发现。ADR 只保存决策及依据，程序回执保存真实验证结果。

#### Story 1.2: 规则去肥增瘦与提示词减负
- **任务 1.2.1**：在 V5 实现拟建 [模式配置](../bmralph-suite-v5/roo/settings/custom_modes.yaml)、[分析入口](../bmralph-suite-v5/skills/ana-solo/SKILL.md)与[工程入口](../bmralph-suite-v5/skills/bmad/SKILL.md)，保留双入口与三遍阅读，删除重复宣誓和固定角色会议；不把切换入口视为实施授权。
- **任务 1.2.2**：同步拟建 [V5 Roo 核心规则](../bmralph-suite-v5/roo/rules/02-bmad-core.md)、[V5 原生核心规则](../bmralph-suite-v5/rules/bmad-core.md)与[V5 计划模板](../bmralph-suite-v5/skills/bmad/references/templates/implementation-plan.template.md)，清除固定进度路径、默认全过程持久化和对所有任务强制预检等冲突。新任务不默认搜索归档，不无条件覆盖未完成活动任务。V4 链路保持原语义。

### Epic 2: 轻量执行控制器纵向闭环 (Lightweight Controller Pipeline)

#### Story 2.1: L0/L1 环境与断言执行解耦 (固定运行器)
- **任务 2.1.1**：重构离线隔离脚本，分离 L0 镜像/工具链准备与 L1 测试命令执行。L0 固定环境一次准备完毕，L1 验证直接挂载复用，消除每次运行重复安装 GCC/musl 的开销。
- **任务 2.1.2**：当 L1 缺少依赖时，程序直接报告“环境未就绪（BLOCKED）”，禁止在测试命令中隐式执行网络安装。

#### Story 2.2: 受控操作入口与执行监督器
- **任务 2.2.1**：实现拟建的 [V5 验证执行器](../bmralph-suite-v5/scripts/bmad-exec.py)，为单测、竞态检查和配置语法检查提供类型化操作；参数、可用目标及接口在工程阶段实现，不把拟议操作当成现有能力，不允许借复合命令掩盖失败。明确套件根与任务工作区，不能因脚本移动而把任务源码或日志误定位到套件目录。
- **任务 2.2.2**：在控制器中落实单飞、分级超时（15s/30s/600s）、前台同步、标准输入封闭及容器退出清理。

#### Story 2.3: 有界摘要提取与短状态卡生成
- **任务 2.3.1**：在拟建的 [V5 验证执行器](../bmralph-suite-v5/scripts/bmad-exec.py)中实现完整日志保存及保留策略，日志和回执写入授权任务工作区而非套件分发源。向模型仅输出有界失败定位与真实退出结果。截断明确标注；日志辅助操作成功不能覆盖测试失败，截断本身也不应在完整必需结果已可判定时触发无意义重跑。
- **任务 2.3.2**：程序从任务清单与真实回执生成 <=80 行且受字节预算限制的只读视图，不另存人工状态账本。实际写权限隔离须验证；同账号可编辑文件不称“不可篡改”，模型声明不能替代验证。

### Epic 3: 行为防护反例断言与受控回滚 (Defensive Invariants & Rollback)

#### Story 3.1: 反例测试套件
- **任务 3.1.1**：编写拟建的 [V5 控制器反例测试](../bmralph-suite-v5/tests/test_controller_guards.py)，覆盖以下行为防护反例：
  1. 超长单行、连续小文件以及日志截断时的显式标记检验；
  2. 测试失败但状态生成成功的“整体失败”判定；
  3. 未命中测试或必要项跳过时的阻断检验；
  4. 相关实现、测试或环境变化后，受影响证据失效；保存进度、无关文档编辑不触发业务重测；
  5. 进程超时、中断或清理失败时的阻断推进断言。

#### Story 3.2: 契约回归与受控回滚机制
- **任务 3.2.1**：按任务 7.5 扩展 [静态契约校验器](../scripts/validate-roo-contracts.py)，显式选择套件后校验各版本自身规则、模式和模板；不能把 V5 精简断言施加到 V4。后续工程阶段分别验证 V5 契约与 V4 兼容，本次不声称通过。
- **任务 3.2.2**：确立受控回滚策略：发生回滚时仅恢复本次受管修改，保留历史未提交改动并校验并发变更，拒绝盲目覆盖。本地反例资产见[受控回滚测试](../tests/roo_distribution/test_controlled_rollback.py)，复用公共事务，不新增 V5 跨套件运行依赖；资产存在不表示已通过。进程树补充资产见[孤儿与中断测试](../bmralph-suite-v5/tests/test_process_tree_guards.py)，证据边界按本轮阶段契约执行。

### Epic 4: 共享能力导航与上下文预算

- **任务 4.1**：建立拟建 [V5 能力索引](../bmralph-suite-v5/skills/bmad/references/capability-map.md)，明确本地流程与遗留技能的区别、依赖及可用状态；先接通构建、审查、三遍阅读，不以整库接入为前置条件。V4 只作阅读参照，有价值的必要资产物理纳入 V5，不以软链接或跨版本运行引用替代自包含。
- **任务 4.2**：为相关模块建立最薄代码定位入口，指向实际源码、调用方和测试；优先复用现有搜索，不复制能从代码得知的项目事实，不新建大型索引数据库。
- **任务 4.3**：实现本轮输入组装：唯一任务、相关方案约束、必要能力和索引、当前代码、最近有效反馈。Token 可计数时按 Token，否则披露字节近似；启动输入与累计工具结果分别设预算，并观察宿主自动加载部分。
- **任务 4.4**：文档按决策、导航、状态、证据分层；草稿默认会话交付，获准才持续修订同一计划与 ADR。完整日志、临时脚本和历史不默认摄入；不顺带删除用户旧文件。

### Epic 5: VPS 独立运行时与任务期 Ralph 循环

- **任务 5.1**：在获准工程阶段核验目标 Roo 独立运行时的来源、版本、无头调用、新会话、等待/取消、认证、规则/模式加载及工具权限。Roo CLI 仅为优先候选，不采信历史回答中的发布、归档日期或笔记接口为当前事实；无法独立运行时报告具体阻塞，不静默更换引擎或改成子任务。
- **任务 5.2**：拟建 [V5 循环入口](../bmralph-suite-v5/scripts/bmad-loop.py)，只提供任务启动、状态和停止；复用 V5 验证执行器，不建设永久服务。人预建远程 tmux，会话承载任务期进程；编码 Agent、模型认证及工具执行均在 VPS，客户端只提交和观察。部署入口不启动循环；活动任务绑定已核验套件来源，更新或回切不得在运行中替换其规则和程序，须先停止并确认在途进程结束。
- **任务 5.3**：每轮选一个依赖已满足的任务，调用新工程会话；会话内允许有界的思考—修改—验证—修复。根据真实结果更新任务进度和必要发现，下一轮继续同一未完成任务或选择下一项；不恢复整段旧聊天。
- **任务 5.4**：实现任务时间、轮次、费用或调用预算、无进展阈值和重试退避。API/网络短暂失败与代码失败分别处理；权限拒绝、认证不足、预算耗尽等明确停止，不无人值守反复询问。
- **任务 5.5**：每个工作区一个活动写入者；同机生产服务与编码任务使用独立工作区、受限账号和验证环境。保留失败轮次的未提交修改，获准才提交本任务改动；推送和部署分别授权。
- **任务 5.6**：验证关闭本地 IDE 后完成当前步骤并开始下一轮，重连可查询结果，取消等待进程真实结束。仅 tmux 存活或文件变化不算成功；机器重启、宿主崩溃后自动恢复不在首轮范围。

### Epic 6: 范围内交付与效果测量

- **任务 6.1**：任务清单允许拆分、顺序和实现落点调整；验收放宽、关键决策变化及新增生产操作须明确决定。冻结承诺而非文件字节，不靠改目标制造通过。
- **任务 6.2**：支持阶段或本地范围交付，报告已验证内容和未覆盖部分。非适用项经明确范围调整后不再阻塞；当前必需验证失败不能记为通过。局部交付不标记全计划完成，不自动转正 ADR；新增状态枚举须先与校验器适配。
- **任务 6.3**：对相同目标和相近环境记录总耗时、所有轮次 Token/费用、重复读取/测试、人工中断与交付缺陷；80 行或字符缩减率不是独立质量指标，不承诺固定三倍提速。

### Epic 7: V5 独立放置与部署入口兼容

本 Epic 的最小版本选择、目录与校验能力先于 V5 实施和验收；编号用于保留原任务，不表示排在所有功能之后。

- **任务 7.1**：在获准工程阶段创建 [V5 套件](../bmralph-suite-v5/)，选择性继承必要 V4 资产后独立演进，包含插件描述、规则、模式、双入口、能力导航、引用、运行程序及专属测试。记录迁移映射与必要差异，不复制历史验证绿灯或新增事实镜像；本任务不修改 [V4 套件](../bmad-suite-v4/)。
- **任务 7.2**：扩展 [部署入口](../bs.sh:95)，集中映射主版本与来源目录，新增显式 V5 选择；未指定版本的新安装兼容默认暂保留 V4。已有安装执行无版本更新时，从已核验的受管来源记录解析激活版本；记录缺失、损坏或身份不明时阻塞并要求显式选择，不按默认回切 V4。将主分支更新、标签提交选择与套件选择分开，在更新或切换主分支前确定有效版本意图，新版移交须保留该意图。拒绝多个不同版本、版本与标签契约冲突；选定套件缺失必须停止，V5 禁用 [现有通用套件回退](../bs.sh:324)。帮助不再把 main 无条件描述为最新 V4。
- **任务 7.3**：扩展 [标签缓存](../scripts/tag-cache.py:38)和[来源清单](../scripts/deployment_provenance.py:67)，以实际提交与套件身份联合核验缓存；V4 已有缓存保留兼容，V5 使用独立缓存命名空间，不改写旧缓存标记。标签名只作版本线索，最终验证所选提交内的套件目录与身份；不含 V5 时拒绝，不回退 V4。清单拟增加套件身份、主版本及仓库内源路径；字段与 schema 兼容策略在工程阶段落实，不把仓库提交号当作唯一架构版本。
- **任务 7.4**：复用 [受管源采集](../scripts/deployment_source.py:28)、[部署协调器](../scripts/deploy_managed.py:55)、预检、备份和事务保护。建议首轮保留单一活动插件槽位及现有模式标识以降低迁移风险，V5 展示名称与来源元数据必须明确；同一部署根只激活一套共享规则。换成另一个插件目录本身不能隔离全局规则或模式，不建设同根双活。独立试用使用显式测试部署根，真实宿主隔离与加载仍须核验。回切清理仅涉及所有权已确认且未被用户修改的退役资产，不删除整个插件／规则目录。
- **任务 7.5**：将 [静态契约校验器](../scripts/validate-roo-contracts.py:41)改为显式套件选择，分别校验 V4 与 V5，不因 V5 状态职责调整覆盖 V4 断言。新增接口前不编造可执行参数；V5 接口及专属验证资产完成后，同步本计划头部命令、AC 6 和下方 P0。扩展 [部署状态诊断](../scripts/deployment-status.py:91)，输出已核验来源的套件身份、主版本、源路径、提交与差异，不把默认版本或当前仓库 HEAD 当作已部署版本；旧清单无法唯一判断时报告未知。
- **任务 7.6**：同步 [安装入口](../install.sh:17)与[说明文档](../README.md)，安装和更新传递显式版本，不暗改已有激活版本；未指定版本的新安装按兼容默认 V4。部署只物化资产，不准备模型认证、不自动启动 Ralph、不运行业务部署。
- **任务 7.7**：扩展 [部署兼容测试](../tests/roo_distribution/)，覆盖新安装默认 V4、显式 V5、已激活 V5 的无版本更新及新版移交仍保留 V5、来源身份不明时阻塞、冲突与缺源失败关闭、同提交双套件缓存、旧 V4 标签／清单兼容、V4→V5→V4 回切、第三方及修改资产保护、无副作用预检和事务失败恢复。V5 专属测试置于 [V5 测试目录](../bmralph-suite-v5/tests/)，公共部署测试留在根目录。测试只在临时根操作，不把文件分发通过外推为宿主加载、权限或断开自主执行通过。

## 5. 验证矩阵 (Validation Matrix)

下列命令定义工程阶段验收契约，执行与结果只引用真实回执。AVAILABLE 仅指资产存在，不表示依赖就绪或已通过。目标运行时接口和预算须在获准试跑前确定；不编造可执行的 Roo/Antigravity 参数。

| 阶段 | 验证目标 | 拟执行命令或检查 | 资产状态 | 通过判定 |
|---|---|---|---|---|
| P0 | V4 兼容与 V5 静态契约 | 下方显式 `--suite v4`、`--suite v5` 及契约回归命令 | 两版本接口与相关契约测试 AVAILABLE | 两版本分别通过；V4 通过不代替 V5，更不外推为运行时证据 |
| P1 | 环境复用 | 下方环境登记与复核反例；实际接口参数见 V5 验证契约 | 本机 Python 资产 AVAILABLE；固定 GCC/musl 镜像及隔离复用仍待实现 | 验证期间无隐式安装，依赖缺失明确报告；本机登记不替代固定镜像门禁 |
| P2 | 原控制器反例 | 下方监督器、子运行器、单测裁决与保存后证据查询测试，以及本轮受控回滚、进程树补充反例 | 本机相关资产及本轮补充反例 AVAILABLE；容器和脱离会话清理不在本轮覆盖范围 | 真实失败、不命中、取消及相关证据失效正确处理；孤儿主进程退出零或无法确认清理均阻断；局部测试不代替范围外门禁 |
| P3 | 有界状态视图 | 下方状态模块与实际 CLI 反例；参数见 V5 验证契约 | 候选只读投影资产 AVAILABLE；活动计划进度迁移及完整控制器接入未完成 | 行数、字节及 JSON 输出预算有效，未完成事项不丢失；模型勾选不制造完成事实 |
| P4 | 上下文与循环 | 下方上下文预算、计划与定向源码组装、实际 CLI 反例；任务期循环测试待实现 | 本地预算与只读组装资产 AVAILABLE；独立新会话、累计工具结果运行接入及循环资产仍待实现 | 必要输入完整保留，启动与累计输出预算分别有效；本地组装不替代新会话、反馈有效性、宿主自动加载及循环停止门禁 |
| P5 | 真实远程两轮 | 目标版本及确切启动/停止命令由任务 5.1 补全；人工关闭客户端后观察 | 尚未核验；需要远程试跑授权 | 断开后开始下一轮、实际失败不推进、停止可确认 |
| P6 | V5 分发与 V4 兼容 | 任务 7.7 的临时根版本、缓存、回切与保护测试；下方列出套件选择、部署租约、来源绑定、继承锁及版本操作守卫反例命令 | 本地版本选择、运行资产分发、协作租约、V5 来源绑定及同一部署根的版本操作守卫反例资产 AVAILABLE；活动任务与任务期循环接入仍待实现 | 显式版本全链路一致、错误不写入、V4 兼容与用户资产保护；已有部署的版本操作须在共享租约期间失败关闭，并在操作、新版移交及最终部署期间持续持有排他锁。来源绑定须核验 V5 身份、受管物理资产与分发映射，边界变化停止对账，不恢复旧文件。原语验证不替代活动任务接入、事务完成诊断、宿主模式语义、跨部署根保护、在途进程清理或真实宿主加载 |

本地验证接口与证据边界见[类型化验证契约](../bmralph-suite-v5/skills/bmad/references/procedures/verification.md)。当前接口覆盖本机 Python 单测、明确采用类型化任务清单的候选只读投影及当前就绪任务的只读输入组装；输入组装不启动 Agent、不执行测试、不保存进度，也不证明授权、反馈或宿主自动加载已核验。配置语法、专项竞态、固定镜像及容器操作仍须实现，不虚构子命令。当前活动计划未迁移到类型化任务清单，平台任务记录继续作为唯一临时进度入口，不在本计划镜像进度或导入历史通过记录。

以下命令分别串行执行，仅列已有本地验证资产；AVAILABLE 不表示已通过。实际单测使用类型化入口时必须明确工作区、已有环境登记及验证选择；只读输入组装必须明确采用类型化任务清单的计划与输入请求，不隐式登记环境或迁移活动计划，不执行缺少必需参数的示例。P4 本地预算与输入组装测试已有资产，任务期循环测试尚未创建；P5 真实启动与停止须先核验运行时并取得授权，再补全确切命令。全部验收承诺保留，不以本地测试替代运行时门禁。

拟执行技术命令：

```bash
timeout 30s python3 -B scripts/validate-roo-contracts.py --suite v4 --plan _bmad-output/pending_implementation_plan.md < /dev/null
timeout 30s python3 -B scripts/validate-roo-contracts.py --suite v5 --plan _bmad-output/pending_implementation_plan.md < /dev/null
timeout 30s python3 -B -m unittest discover -s tests/roo_contracts -p 'test*contracts.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_environment_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_supervisor_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_controller_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_execution_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_evidence_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_state_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_exec_cli.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_context_guards.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_context_inputs.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_suite_lease.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s bmralph-suite-v5/tests -p 'test_suite_source.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s tests/roo_distribution -p 'test_suite_source_deployment.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s tests/roo_distribution -p 'test_suite_selection.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s tests/roo_distribution -p 'test_suite_lease_deployment.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s tests/roo_distribution -p 'test_asset_safety_inherited_lock.py' < /dev/null
timeout -k 2s 30s python3 -B -m unittest discover -s tests/roo_distribution -p 'test_version_guard.py' < /dev/null
```

首轮运行时证据仅聚焦三组：断开后推进、新会话必要记忆、真实失败与预算停止。不扩充无关全排列矩阵。保留真实版本、工作目录、运行目标、退出结果和关键输出；完整日志按需读取。

## 6. 受控回滚方案 (Controlled Rollback Plan)

若控制器在目标 Roo 环境出现工具适配异常：
1. 仅恢复 [V5 套件](../bmralph-suite-v5/)、[公共部署脚本](../scripts/)、[部署入口](../bs.sh)和[安装入口](../install.sh)中本任务获准且经差异核对允许恢复的修改；V4 源目录不在本任务修改范围内。已部署 V5 回切 V4 须另按显式版本选择和受管事务执行，不把源码恢复当作宿主回切完成；
2. 保持用户既有未提交改动与[项目事实基线](project-context.md)不变；
3. 回滚前检查工作树并发修改，确保第三方非受管资产零破坏。
4. 停止远程任务须先取消并确认在途 Agent 与验证进程结束；不得用全目录恢复或自动清理覆盖失败轮次和用户修改。

## 7. 架构引用、修订边界与批准状态

- 当前关联[提案 ADR](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)持续修订，不另建重复方案。提案未生效，旧任务与原待办保持独立。
- [已接受生命周期 ADR](adrs/ADR-20261008-roocode-bmad-v42-lifecycle-and-governance.md:37)的显式任务优先、历史恢复授权、分析权限与受管资产保护继续保留。拟调整的是新任务不默认归档发现、验证与任务状态的存储职责、后台运行的工程适配，不修改其历史接受范围。
- 原“无常驻调度器”细化为不建设永久平台，允许单任务期的持久执行进程；原状态卡权威入口拟改为计划任务清单的程序投影，须同步入口、模板和校验器。
- 首轮运行时阻塞：目标 Roo 独立运行时兼容性、独立认证和远程断开行为均未验证；具体 Antigravity Ralph 插件未识别，不作为已可用依赖。
- 基线首行含字面换行转义，历史记录仅作相关事实线索；本次不修复基线格式、不写入新提案为项目事实。
- V5 隔离是本轮新增范围决定；旧文档中的 V4 链接只作为事实参照，新生产实现以 V5 落点为准。独立源码目录不等于独立宿主权限或同根双活；默认激活、插件槽位及版本接口保持上述保守提案，后续不得静默更改。
- [x] 用户授权本任务方案与 ADR 持久结晶。
- [x] 2026-10-16 用户授权 Phase 1 本地工程套件与反例封顶闭环，定向验证及 238 项单测全部通过。
- [x] 2026-10-16 用户授权 Phase 1 成果 Git 提交固化 (34a5c19)。
- [x] 2026-10-16 用户授权 Phase 2 本地任务期循环控制器 (bmad-loop.py)、14 项循环反例断言及规约文档完成与 Git 提交固化 (7268440)。
- [x] 2026-10-16 用户授权 Phase 3 活动计划结构化适配、无头驱动抽象与模拟断网验证完成与 Git 提交固化。
- [ ] 目标 VPS / 真实 Roo 独立会话试跑授权及预算、操作范围确认。
- [ ] 提交推送至远端、生产部署、ADR 转正或计划归档授权。
