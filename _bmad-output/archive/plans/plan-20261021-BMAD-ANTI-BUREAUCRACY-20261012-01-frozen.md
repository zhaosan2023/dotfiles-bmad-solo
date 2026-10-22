---
plan_id: "BMAD-ANTI-BUREAUCRACY-20261012-01"
status: SUSPENDED
scenario: structural
impact_tier: M
requires_adr: true
adr_file: "_bmad-output/adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md"
verification_type: config_syntax
verification_command: "timeout 30s python3 -B scripts/validate-roo-contracts.py --suite v5 --plan _bmad-output/pending_implementation_plan.md < /dev/null"
verification_command_status: AVAILABLE
authorization: "2026-10-21 当前用户授权未完成冻结保全：完整保留 V5 计划、历史任务状态、关联提案和证据定位；核对保全目标完整保存及源未变化后，才将默认入口交给新的 V4 任务。不是开发完成归档，不转正 ADR，不勾选未完成任务，不继承旧预算或绿灯，不恢复或启动 V5，不删除 V5 源码、测试及回执。当前分析入口仅进行获准文档编辑，不运行终端或验证；文档冻结不证明宿主进程已经停止。另行结晶 V4 返修、版本清理和安装入口重构的分阶段 ADR 与计划，再移交工程入口按当前授权实施。"
session_id: null
---

# 实施计划：BMRalph V5 独立套件、双入口减负与远程自主执行

## 2026-10-21 未完成冻结保全边界

- 当前用户已明确授权未完成冻结保全。本节与头部授权优先于下文各历史阶段的推进、恢复及完成后归档说明；冻结前顶层状态为 BLOCKED，本次暂停为 SUSPENDED，不修改下方八项历史类型化任务的状态、验证对象或回执。
- 本次保全不是开发完成归档。宏观未验收事项、P5-PI-HEADLESS 的暂停及空回执、Phase 6/7 未完成承诺完整保留；关联 ADR 保持 PROPOSED，不继承历史通过结果、认证、预算或执行许可。
- 本文件暂时继续占据默认入口，直到独立保全目标完整保存、回读核对及源版本复核成功。此时不创建覆盖本文件的新 V4 默认计划；任何保全失败均保留源文件。
- 拟议保全目标为 [V5 冻结计划](archive/plans/plan-20261021-BMAD-ANTI-BUREAUCRACY-20261012-01-frozen.md)。该链接只是目标定位，尚未证明文件已创建或保全已完成；完成保全后须将关联 ADR 的任务链接明确改为该历史目标，避免它误指后续 V4 默认计划。
- 下文旧相对链接和验证命令属于原工作区及原计划路径的历史语境。保存历史副本时须保留来源定位并明确这些路径不指向新的 V4 任务，不把历史命令直接执行，也不把失效路径偷偷替换为新证据。
- 用户计划将无人值守工程迁往独立项目 solo-engine；本次仅登记迁移意向及后续资产评估，不访问或写入项目外目录，不创建新仓库、不提交或推送、不迁移凭据，不删除尚未核验保全的资产。
- 当前未取得宿主进程停止或写入租约释放的真实回执。文档状态 SUSPENDED 不等于运行时已停止；工程阶段在部署、版本切换或清理前须核验无在途写入，无法确认时只阻塞相关写入，不启动 V5。
- 冻结前头部授权原文保留如下，以保全历史授权而非继续执行：

> 2026-10-20 紧急纠偏：本次仅修订同一计划与关联 ADR、定义四组件落点并在文档中冻结过度设计路线。覆盖此前刷新后继续实施至归档的本轮推进许可；不修改或删除生产源码和测试，不运行终端或验证，不调用编码模型，不启动后台，不操作 Git，不转正或归档。人类终端显式启动前禁止自动编码；未来启动必须绑定审核后的计划版本、任务集合、写入范围与预算，模式切换、聊天批准、看板重连及文档保存不构成启动。保留原计划标识、历史任务状态、回执和未完成承诺；历史运行预算与绿灯不继承，历史条件归档授权不在本轮行使。

## 契约实例化与授权

- **计划标识**：`BMAD-ANTI-BUREAUCRACY-20261012-01`
- **关联 ADR**：[本任务提案](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)（状态：PROPOSED）。
- **接管契约**：绑定本文件、原计划标识及关联 PROPOSED ADR；最新紧急纠偏授权、ADR 决策 11 和重写后的 Phase 7 为当前契约。Phase 6 未被明确替代的安全约束与未完成事项保留；较早工程和启动授权仅作历史，不自动延续。八项历史类型化任务状态与回执保持不变，原 Epic 与其他未完成承诺保留；本次明确替代的旧 Phase 7 规格及 AC 17–19 见下文对应关系，不把替代写成已完成。未知会话标识保持 null。
- **验证命令契约**：头部静态命令保留，AVAILABLE 仅表示既有入口存在，不表示本次运行或通过。本轮不运行终端、静态检查或业务测试；未来获准工程仅重验受影响证据，不追加与四组件无关的全量回归，不修改证据匹配规则制造通过。
- **当前授权边界**：仅修订本文件和[同一提案](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)，在文档中冻结存储扩张路线；不改动源码、测试、凭据、项目事实、V4 或历史回执，不声称运行入口已停用。此前[接管回执](../.bmad-runtime/phase6-engineering-20261019-1130/intake.json)仅作历史定位，不证明当前无进程。本轮不自动交接实施，不启动、不提交、不恢复、不接受或归档；未来人类显式启动及对应范围、预算是执行前提。
- **历史语境**：Phase 1–4 描述保留为历史局部交付及授权，不覆盖当前窄范围。此前工程接管记录 HEAD 为 11483cf、若干未提交改动及冻结资产差异为空；这些是历史回执描述，本次未检查 Git，不代表当前工作树。旧 Roo 名称和回执不重命名为 Pi 证据；纯文档变化不触发业务重测，实际实现、测试或契约变化后仅重验受影响证据。

## 1. 目标 (Goal)

先删除不必要的工作，再由薄程序承揽机械工作。保留分析入口的三遍阅读、探索、审计及人机目标收敛；工程入口接收明确需求或现成方案，完成小任务与真实验证，不重新生成全部分析。

在原轻量执行控制器设计上补充输入预算、新工程会话、任务期远程循环与必要持久记忆。目标是：人通过本地 IDE 提交已授权任务后，VPS 上独立 Agent 仍能选择任务、自主思考、修改、验证并启动下一轮，不依赖本地客户端在线。

本次仅结晶同一计划与 ADR 的紧急纠偏：以 [`architecture-v5.md`](../docs/Ralph-Wiggum-Loop/architecture-v5.md:8)为架构基准，Phase 7 收敛为状态总线与独立树状看板、进度卡片与文本经验反射、Jev 工具语义门禁、Tmux 四槽位外层编排四个组件。Cline 保留规划候选，不再承担必需统一总控；通用持久决定存储停止扩张。原 Epic 1–7、八项历史任务及回执保留，未替代的 Phase 6 要求仍须完成；旧 Phase 7 和 AC 17–19 的明确替代不表示其已经通过。本轮文档完成不等于工程或全计划完成。

版本放置以 [bmralph-suite-v5](../bmralph-suite-v5/) 为新套件唯一生产源码根目录，现有 [bmad-suite-v4](../bmad-suite-v4/) 作为本任务不修改的对照基线，不宣称整个仓库已冻结或工作树洁净。V5 规则、入口、引用、运行程序和专属测试自包含，禁止运行时回指 V4；仓库根部署基础设施只做兼容性扩展，不承载 V5 任务循环。现有共享文档保留于原路径，不建立镜像计划或 ADR。

## 2. 非目标 (Non-Goals)

1. 不建设泛化多智能体平台、永久调度服务或复杂记忆数据库；仅允许后续获准实现的任务期持久进程。
2. 当前只设计自有网关适配、请求时限及续接契约，不修改网关服务、系统代理或超时常量，不承诺固定提速；后续适配实现和真实调用分别取得授权。
3. 不取消适用于已批准范围的竞态、隔离或集成验证；不临时追加范围外验证阻断交付。
4. 不宣称覆盖宿主原生附件、全部工具旁路或所有版本；不把静态配置视为运行时权限保证。
5. 当前不修改生产代码、测试、V4、项目事实基线或已接受 ADR，不覆盖用户既有改动；不实施、不运行验证、不安装、不准备认证、不真实启动、不提交或回滚、不推送、不部署、不转正、不归档。自动检查点和受控恢复是后续必选交付目标，不是本次操作授权。

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

## Phase 5 契约：Pi 条件选型、最小适配与独立运行门禁

本节替代当前 Epic 5 的 Roo 优先假设，不改写 Phase 3/4 历史验收。选型依据、证据强度矩阵、替代条款及后果见[同一 ADR 的决策 8](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)。Roo 新增独立适配停止，原规则与部署资产保留；Pi 条件优先，Claude Code 仅为待核验兼容候选，不自动回退。

- 当前阶段为现有 Pi 薄驱动的本地证据接管。P5-PI-DRIVER 的原源状态 SUSPENDED 及空回执先保留；六项旧完成证据全部有效刷新后，单独授权受限脚本仅恢复为 PENDING、回执仍为空，再以精确匹配证据程序登记本地完成。P5-PI-HEADLESS 始终 SUSPENDED、回执 null；计划头部 READY 或行政恢复均不授权真实运行。
- 前序接管报告官方 Pi 1.3.0 已安装、入口为 /usr/local/bin/pi；安装及版本查询不证明模型运行，本轮不重装、不更新、不换引擎。后端固定来源、包名、版本和安装路径；真实提供方认证、规则/技能映射、权限、等待/取消/清理、内部请求及用量仍须另获授权实证，不读取凭据正文。
- 实际落点改为[现有后端内薄驱动](../bmralph-suite-v5/scripts/bmad_agent_backend.py:81)，使用固定版本单次 JSON 输出模式和封闭文件输入，不另建生产驱动或永久 RPC 服务。[循环真实门禁](../bmralph-suite-v5/scripts/bmad_loop.py:353)及[入口后端枚举](../bmralph-suite-v5/scripts/bmad-loop.py:19)仍冻结；仅后端支持 Pi 不等于真实接通，不删除门禁、不把真实 Pi 标为夹具。
- 新反例实际位于[现有测试目录中的 Pi 测试](../bmralph-suite-v5/tests/test_pi_backend.py:1)，替代此前独立 tests_pi 目录及独立驱动规划；不迁移既有测试。测试目录集合和实际后端输入变化使六项完成证据失效，按四组原验证对象定向重验并承担成本，不删输入、不降低下限、不修补旧回执、不默认全套重跑。
- P5-PI-DRIVER 绑定当前实际测试标识，下限为 31（不低于原有 27），全部当前反例列为必需；八类原防线逐项映射如下，资产存在不代表已通过。P5-PI-HEADLESS 的未来测试及回执裁决资产仍未创建，不修改其验证契约。完成只由匹配当前 PASS 证据的程序写回，普通文本编辑不得设置 COMPLETED 或填写回执。

### P5-PI-DRIVER 原防线与实际验收映射

| 原验收类别 | 当前实际测试标识（共同前缀为 test_pi_backend） | 行为及边界 |
|---|---|---|
| 未授权运行不得启动 | [PiBackendGuards.test_unapproved_runtime_blocks_invoke_before_request_or_launch](../bmralph-suite-v5/tests/test_pi_backend.py:169)；[test_source_version_authorization_and_runtime_cannot_be_relaxed](../bmralph-suite-v5/tests/test_pi_backend.py:150) | 未授权在请求和进程创建前失败；不只验证配置文字 |
| 真实 Pi 不得声明为夹具 | [PiBackendGuards.test_real_pi_category_cannot_be_loaded_as_isolated_fixture](../bmralph-suite-v5/tests/test_pi_backend.py:188)；[test_frozen_loop_still_rejects_real_pi_without_activation](../bmralph-suite-v5/tests/test_pi_backend.py:422) | 保留真实类别与冻结外层门禁 |
| 每次独立新会话、不得恢复历史 | [PiBackendGuards.test_each_invocation_has_distinct_input_and_only_current_feedback](../bmralph-suite-v5/tests/test_pi_backend.py:326)；[test_argument_allowlist_uses_one_shot_ephemeral_json_and_closed_option_parsing](../bmralph-suite-v5/tests/test_pi_backend.py:116) | 新外层会话及请求，参数排除恢复，反馈不串线；真实 Pi 会话尚未实证 |
| 缺独立凭据不得启动或泄漏秘密 | [PiBackendGuards.test_missing_credentials_blocks_load_before_driver_read_or_launch](../bmralph-suite-v5/tests/test_pi_backend.py:180)；[test_missing_credentials_blocks_invoke_before_request_or_process](../bmralph-suite-v5/tests/test_pi_backend.py:228)；[test_exec_interception_preserves_process_group_and_excludes_inherited_config](../bmralph-suite-v5/tests/test_pi_backend.py:382) | 仅合成凭据；不使用或读取真实认证 |
| 协议失败或非零退出不得变成 OK | [PiBackendGuards.test_nonzero_exit_cannot_be_masked_by_valid_protocol_or_promise](../bmralph-suite-v5/tests/test_pi_backend.py:306)；[test_completion_promise_and_exit_without_protocol_are_rejected](../bmralph-suite-v5/tests/test_pi_backend.py:246)；[test_model_error_abort_missing_settled_or_late_activity_blocks](../bmralph-suite-v5/tests/test_pi_backend.py:266)及其余协议反例 | 完成口令、完整文本或退出零不能替代协议及独立业务验收 |
| 请求、工具、会话及批次时限不混淆 | [PiBackendGuards.test_request_tool_session_and_batch_caps_are_not_conflated](../bmralph-suite-v5/tests/test_pi_backend.py:367)；[test_legacy_timeout_is_not_claimed_as_model_request_timeout](../bmralph-suite-v5/tests/test_pi_backend.py:359) | 保留 15/30/600 秒工具上限及 30 秒驱动，内部模型请求时限明确 UNKNOWN |
| 取消必须等待受管进程清理 | [PiSupervisorDelegationGuards.test_agent_call_interrupt_cleans_same_group_and_preserves_changes](../bmralph-suite-v5/tests/test_pi_backend.py:625)；[test_agent_call_timeout_cleans_same_group_and_preserves_changes](../bmralph-suite-v5/tests/test_pi_backend.py:620) | 实际隔离 Python 同组进程终止、回收及组消失；不是 Pi 实跑，不外推脱组后代 |
| 清理未知禁止下一次调用 | [PiSupervisorDelegationGuards.test_unknown_cleanup_prohibits_next_call_verification_and_restart](../bmralph-suite-v5/tests/test_pi_backend.py:574)；[PiBackendGuards.test_timeout_cancellation_and_unknown_cleanup_override_protocol_ok](../bmralph-suite-v5/tests/test_pi_backend.py:316) | 故障注入后仅一次调用，无验证、无下次调用、无重启；不得仅模拟一次失败代替禁调行为 |

- 四项不变量保留：独立新会话（上述新会话反例）；三轮无进展熔断（[实际禁止第四次隔离调用及依赖推进](../bmralph-suite-v5/tests/test_pi_backend.py:551)，加上[冻结监督器三轮反例](../bmralph-suite-v5/tests/test_pi_backend.py:510)）；既有写租约及同组清理（[租约所有者核验](../bmralph-suite-v5/tests/test_pi_backend.py:207)及上述真实 Python 清理）；外层客观验证（[协议成功不登记业务完成](../bmralph-suite-v5/tests/test_pi_backend.py:239)，失败三轮不写回、不推进依赖）。这些是本地协议与委托原语证据，不是实际 Pi 编码证据。
- 六项旧完成任务的环境、目录、模式、下限、必需测试及实现输入顺序完整取自原 verification 对象：P3-PLAN 18 项；P3-BACKEND/P3-OFFLINE/P4-BUDGET 17 项且仅对象完全一致时共享回执；P4-BATCH 12 项；P4-ISOLATION 7 项。候选均经[completed_evidence](../bmralph-suite-v5/scripts/bmad_state.py:172)精确核验后，持同一写租约与源版本调用[refresh_completed](../bmralph-suite-v5/scripts/bmad_plan_adapter.py:131)一次刷新全部六项。
- 受限恢复没有现成产品接口：草稿仅复用内部[_save_plan](../bmralph-suite-v5/scripts/bmad_plan_adapter.py:167)，在既有写租约下核验计划身份、源版本、P5-PI-DRIVER 确为 SUSPENDED/空回执及其他任务不变，原子保存后核对；不改生产原语，不宣称已有通用恢复能力。恢复后查询依赖就绪，精确协议证据满足后调用[complete](../bmralph-suite-v5/scripts/bmad_plan_adapter.py:100)。任务清单仍是唯一进度；未覆盖行政入口与静态检查临时引用平台真实回执，草稿及回执不是第二份账本。
- P5-PI-DRIVER 仅交付获准薄驱动和协议反例，不证明真实 Agent 编码。P5-PI-HEADLESS 仅交付真实运行回执判定的反例；当前[任务契约](../bmralph-suite-v5/scripts/bmad_state.py:62)只支持 Python 单测，不能把远程两轮塞进 unit-test 假装运行通过。真实两轮仍归 Epic 5、AC 8–10 和验证矩阵 P5，不能由这两项完成替代。
- 后续获准真实接入时，每次业务失败修复创建新 Pi 进程及新会话，保留未提交成果，只携带必要约束、未完成事项和真实失败反馈。当前薄驱动采用单次 JSON 输出模式，以受预算约束的请求文件输入、stdin 封闭，读取 JSONL 生命周期；不是 RPC 会话接入，不建设永久 RPC 服务。Claude Code 与 Pi 使用不同原生协议，兼容仅指映射到同一本地契约，不宣称线协议互换或已有 Claude 适配器；本轮不启动真实 Pi。
- 维持 30 秒驱动进程、15/30/600 秒工具分级、600 秒批次及既有停止等待上限。不把驱动调用数冒充模型请求数，不把用量/价格元数据冒充可强制执行的费用预算；内部请求、重试、工具和费用覆盖未知时明确阻塞或披露。需要扩大上限另获确认。
- 真试跑前一次性确认主机、工作区、来源/版本、显式任务集合与依赖、写入白名单、禁止修改的验收资产、认证方式及变量名称、确切启动/查询/取消/清理命令、各级时间与轮次/调用/费用预算及计量缺口、关闭客户端后新步骤采集、清理未知禁止重启。此前不安装、不准备认证、不启动模型或宿主。
- 客户端断开不是模型服务断网：关闭本地 IDE 后 VPS 到模型服务连接保持可用，以新模型/工具事件及轮次证明自主推进。真正模型网络故障只验证失败关闭、停止新调用、成果保全与清理，不要求无网络继续生成步骤，不改防火墙或 SSH。
- Pi 两轮真实回执是 ADR 接受的必要条件；还须全部适用必需门禁通过且转正获准。ADR 接受不能使原 Epic、宏观 AC 或范围外承诺消失；全部计划事项完成且归档获准前保留活动计划。

### 2026-10-18 接管与当前配置加载阶段

本节及头部授权优先于上述 2026-10-17 的冻结描述；此前授权、完成源记录、全部未完成事项及历史证据仍保留，不继承为真实 Pi 运行通过。

- 当前实施范围：任务启动入口显式接收工作区私有凭据文件路径；运行程序受限加载，不通过工具读取、回显或摄入凭据正文。非秘密后端配置与凭据分离，私有目录排除版本控制；文件拒绝越界、符号链接、权限过宽、重复键、未知键和可执行 Shell 语法。不得加载系统全局配置或 IDE 登录态。
- 安装与部署入口本阶段只读，不自动加载凭据、生成认证或启动模型。只读查询、停止及帮助入口不加载私有凭据；缺失或非法配置失败关闭。加载器只向实际任务调用进程提供指定变量，退出或异常后恢复原环境，不把值写入启动参数、模型输入或回执。
- 后续后端网关配置及私有模型目录须依据固定 Pi 版本真实接口实现；真实调用门禁不得无条件删除。新增加载接口与反例验证不证明认证、模型连通、工具权限、独立循环或客户端断开能力。
- 用户指定的非秘密网关为 http://127.0.0.1:8080/v1，模型为 gpt-6.1-sol，协议为 openai-completions，指定凭据变量为 BMAD_PI_API_KEY。冒烟与循环合计最多 5 次真实模型请求、总时限 60 秒；请求级计量或强制截止尚未覆盖时阻塞真实调用，不使用外层调用预算替代。
- 当前结构化清单不增加人工完成记录；私有配置加载及未覆盖的行政操作暂由平台任务记录引用真实回执，不另建进度账本。实现或测试集合变化后，原完成回执须按原契约核验或定向刷新，不删除旧回执、不降低验收。P5-PI-HEADLESS 保留原暂停记录及空回执，真实运行裁决资产和实测门禁仍待补齐。

### 2026-10-18 独立循环接管授权

本节以当前用户明确确认覆盖前述本轮禁止提交、真实启动及旧预算的限制；历史描述、全部未完成事项和原始回执保留，不继承为本次运行通过。

- 授权审查、定向验证并提交私有配置加载、流式适配及本次启动必需的最小入口与门禁改动；真实凭据不得进入提交。不授权推送、生产部署、ADR 转正或计划归档。
- 授权补齐并恢复 P5-PI-HEADLESS 真实运行回执裁决任务；恢复仅改变暂停状态，不手工登记完成。当前用户进一步明确执行顺序：保留该任务未完成，由后台 Pi 实现唯一裁决器目标，外层控制器执行八项必需单测并保存、写回；当前助手不提前实现完成。必需验收资产、当前依赖证据及启动门禁满足后，使用固定 Pi 1.3.0 的 pi-agent 后端启动 VPS 独立任务期循环，不重复临时网关冒烟。
- 本次预算为任务期总时限 600 秒、最多 30 次真实模型请求、每个 Pi 会话最多 360 秒、15MB 数据预算及 6 轮无进展熔断。15MB 按十进制 15,000,000 字节实施；真实请求及数据量必须在实际调用路径强制限制，外层驱动调用数不得替代真实请求计数。探测、验证、构建工具仍保持 15/30/600 秒上限。
- 唯一任务进度继续使用本计划结构化清单；未覆盖的行政恢复及启动操作临时引用平台真实回执，不另建进度账本。源码、日志和运行回执位于当前授权工作区；不读取或回显真实凭据正文，不改系统全局配置、不替换活动运行资产。
- 仅后台会话、活动写租约及真实运行启动回执核验通过后通知客户端断开。启动成功不证明断开后自主推进；断开试验另以断开后的新模型或工具事件及后续轮次裁决。失败、超时、预算耗尽或清理未知阻塞并保留成果。

## Phase 6 契约：Pi 单框架、确定性上下文重建与可靠后台交付（2026-10-19）

### 当前目标、替代关系与执行阻塞

- 本节是同一计划的当前工程契约，不是新计划。最新授权允许相关本地实现和必要验证；计划头部 BLOCKED 保留真实请求、后台启动及 Git 操作的未决门禁，不改变历史任务状态，也不禁止独立的本地工程推进。
- 当前只聚焦 Pi 编码框架、Ralph 的单目标新会话/外部记忆/客观背压/自动推进、自有网关多 baseline 与 academic、factcheck 模型，以及 Jev 路由。停止新增 Claude Code、Codex、Amp、Roo 独立执行器适配；历史反例、部署兼容及全部未完成承诺保留。
- 独立后台执行和 Task 级本地 Git 检查点均为必选，不以模拟通过、启动成功或延后到不确定阶段替代验收。先证明固定 baseline 的最短断开推进链，再接在线搜索和 Jev；最终组合链仍须验收。
- 2026-10-18 的 600 秒整个任务期、360 秒会话、30 次请求、15,000,000 字节和六轮文件无进展规则只作历史，不自动继承或自动删除。2026-10-19 的预算意图与未决项见下节；缺确认或缺计量时禁止真实启动，不靠沿用旧值或取消门限推进。

### 完整模型选项与固定默认策略（最新用户澄清）

- 用户网关的 baseline、baseline:academic、baseline:factcheck 是三个完整模型选项；academic/factcheck 后缀的网上搜索由网关提供，不拆成独立角色配置，不要求用户重新证明已说明的语义。请求保留实际完整模型 ID，不剥离后缀、不猜造别名。
- 联网研究默认完整 ID 为 gpt-6-astra:academic；事实核验使用获准的对应完整 factcheck 选项，其精确 ID 从非秘密配置核对。普通编码默认 Sonnet 5.5 的 baseline，精确 ID 尚待非秘密配置定位，不把当前工程入口的 academic 选项当作编码 baseline。
- 计划简化优先核对既有 gpt-6.1-sol 候选的完整 ID、能力及授权，不沿用此前无依据的性能排名。窗口、输出上限、编码工具等能力未知时保持未知，不从后缀推导编码权限。
- Jev 是独立的快速结构化决策组件，选择获准模型与后续动作，不替代编码模型、网关研究或客观验收；仅在明确任务/新会话边界选择，会话内模型固定。不可用或输出不合契约时沿预授权固定策略；没有对应预授权则只阻塞该动作，不让新增路由阻塞固定模型闭环。Jev 的真实接口、数据出站和请求预算未核验前不调用。

### 确定性上下文分配与预算候选

- 确定性指输入来源、任务选择、装配边界和重置协议可核验，不表示模型生成确定、每轮必然改善或无需验收。每个工程会话只处理一个明确 Task 的当前局部目标；有效工具往返可在会话内完成，验证失败后的外层修复使用新会话，不把每个 HTTP 重试都当作新工程轮次。
- 必需输入为当前目标/授权/验收、相关 ADR 约束、必要流程与定位、当前源码/差异及最新真实反馈；不摄入完整聊天、全部规则或历史报告。每个候选模型先登记窗口、输出上限、工具与检索能力，再预留工具结果和输出空间；15M Token 不是单轮窗口容量。无法完整装配时停止、报告或经获准拆分，不暗中摘要关键契约。
- 用户提出的候选为单 Task 累计 15,000,000 Token、单次 API 完整请求最多 600 秒、连续六次无有效回复挂起。费用计算与费用优化不列为本轮必需验收；仍须诚实披露未计量费用，不宣称零费用或费用封顶。
- Token 定义、缓存与推理用量口径、失败/断流请求计量、发送前输出预留及网关内部重试覆盖均待确认。baseline 与研究调用应归属同一父 Task 的累计账目；切模型、重开会话、网关重试不重置累计预算。路由调用的独立端点、认证与预算也须显式绑定，不能静默直连外部服务。
- 网络失败计数与业务验证失败计数分离。目标语义是连续失败，而不是六次总调用：有效回复到达时仅清零连续网络计数，继续当前 Task；不登记业务完成、不清零累计 Token、不解除已耗尽预算。新会话或切模型不能绕过尚未恢复的连续失败计数。
- 心跳、HTTP 200、重复字节、错误对象和无完整语义的流片段不算有效完成。完整有效回复与带验证身份的部分续接是否均可清零，仍是未决项；任何部分回复都不得登记 Task 完成。网关三次补全结果是用户报告的目标场景，当前未核验其实现。
- 续接必须区分逻辑请求与物理尝试，具备身份、序号/偏移、去重、结束标识和用量归属；缺契约不得拼接独立生成的回答或执行残缺工具调用。优先让网关在同一逻辑响应内完成恢复，再向 Pi 提供有效协议结果；不取消 EOF/生命周期门禁。
- 请求 600 秒候选是完整请求截止，不因心跳刷新；每次尝试独立受限，逻辑续接、会话、Task 和批次还需总量限制。Task/批次总时限、总尝试/轮次、会话截止与请求截止关系、无进展规则的保留或替代均待批准，不默认无限重试。已验证的凭据失效/权限拒绝立即停止，清理未知禁止下一调用。

### 前后台契约、记忆与安全挂起

- Roo 主窗口/工程交接只提交已批准任务集合；如使用子任务，仅承担一次性启动交接，不在 Roo 子任务内部承载长跑或每轮重开模式。实际启动接口须由目标宿主核验，不假定 Roo 子任务天然能启动独立 Pi。
- 启动器返回绑定工作区、计划、运行副本、独立进程和日志定位的回执后，前台退出执行职责。后续控制器、Pi、认证、验证和预算不依赖客户端或扩展宿主；不自动切视图、不微步轮询、不逐任务弹窗重试。
- Roo 和 Pi 使用同一获准工作区，执行期只有控制器管理的一条写入链；前台只读观察。协作锁不是系统隔离。运行中的控制器继续绑定冻结运行副本；Pi 可以修改获准源码，不能热改正在执行的监督器后继续运行。
- Pi 按需读取本计划和 ADR；可提出授权内任务拆分、定位与必要发现，控制器经契约检查原子写回。目标、授权、验收放宽和 ADR 决策变化回到人工，不因全自动迭代而自动接受。
- 复用[状态投影](../bmralph-suite-v5/scripts/bmad_state.py:189)和[输入接入](../bmralph-suite-v5/scripts/bmad_context_inputs.py:49)，将稳定经验与同义词导航按需装配，失败快照只传定位和最新有效反馈。自动加载关闭时显式接入必要 procedures/skills，不复制文件后假定生效，不增加完整进度日志。
- 状态卡仍为唯一任务清单的程序投影，至多 80 行并受字节预算限制，包含全部未完成项及当前检查点/事故定位；不能只显示就绪任务。现有投影只覆盖类型化清单，不声称已包含全部宏观 Epic。新增任务纳入与未覆盖承诺定位须由迁移契约保证；超限报告预算阻塞，不悄悄遗漏。
- 挂起时停止新请求，取消并确认受管进程结束，保存脱敏现场、任务状态、最终退出回执和事故报告，再释放租约。若清理或写盘未知，保留持久重启阻断；进程死亡导致锁释放不等于可恢复，不强求异常中声称干净退出。
- 事故报告候选文件为[accident_report.json](../.bmad-runtime/accident_report.json)，每次运行实际使用独立子目录而非覆盖全局现场。内容须含版本、计划/运行/任务身份、原因代码、实际网络/验证回执及脱敏错误、最新检查点、修改快照/补丁/新文件清单定位、预算计数、清理与恢复状态、需授权的人工恢复步骤。未执行单测字段保持空值，不编造报错。
- SUSPENDED_FOR_HUMAN 先作为事故原因/显示语义映射到现有 SUSPENDED；新增枚举须先实现版本契约，不直接写入当前清单。恢复只在新工程实例内获准接管和重验，不自动恢复旧进程、补发残缺工具调用或继承旧绿灯。

### Task 本地 Git 检查点事务（必选）

- 保留共享工作区；后续获准接管时使用独立本地任务分支，分支创建/切换、提交和受控恢复须纳入该次授权。禁止强制切换、推送、自动合并主分支、全目录暂存和危险清理。无法安全准备分支时阻塞，不自动另建 worktree 改变用户拓扑。
- 接管记录 HEAD、索引及用户已有修改/新文件，保护凭据、运行证据和非受管资产。已有脏文件与 Task 目标重叠时先取得逐路径处理决定，不能仅靠前后差异推断所有权；存在未知暂存内容时不得直接提交。
- 顺序为冻结本次候选快照 → 独立验收并核对候选未变 → 持久事务准备 → 只提交获准成果 → 保存提交/tree 与验收关联 → 原子完成写回 → 重建状态卡 → 才选择下一任务。绿色仅表示该检查点通过其相关必需验收，不表示全库或全计划通过。
- 事务日志置于受管运行目录，作为恢复证据而非第二份任务进度；提交号不回填到其自身提交内容形成循环。检查点、候选树、任务、验收和源版本须关联，提交身份及 hooks 行为先核验，不以关闭所有 hooks 绕过问题。
- Git 与计划文件不存在一个天然跨介质原子事务：提交失败不完成，提交成功/写回失败时按事务身份对账，不重复提交或自动推进；写回后状态卡失败仍阻断后续。任意中断点均须反例覆盖。
- 修复熔断后先取消并确认清理，保存完整受管差异、未跟踪新文件和必要权限信息的现场，再经预授权选择性恢复上一检查点的受管路径。恢复前比对当前内容与本轮快照，拒绝并发或所有权冲突；禁止 reset --hard、全库 clean 和默认删除用户文件。恢复失败保留现场和阻断，不把恢复成功当成业务完成。

### 优化任务规格与最小实施落点

以下是新增工作的任务规格与依赖，不是第二份进度清单，也不是可直接消费的任务块。当前 schema 仅支持本机 Python 单测和固定字段；不把真实运行任务伪装成 unit-test，不填尚未存在的测试标识或通过回执。工程获准后先实现必要操作契约并将可执行任务迁入下方唯一类型化清单；迁移前平台记录仅跟踪该实施过程，不在此维护状态或勾选。新增验证资产统一为 PLANNED_NOT_YET_CREATED，具体标识、下限和接口以实际资产实例化。

| 任务规格 | 依赖/门禁 | 最小职责与拟议验收 |
|---|---|---|
| P6-CONTRACT | 最新本地工程授权已明确；真实运行预算单独待决 | 对账完整模型选项、固定策略、任务/请求/会话预算和操作 schema；可独立实施本地失败关闭契约，未决不启动相关运行。唯一进度迁移须声明覆盖边界，暂停不自动恢复，历史八项任务状态/回执不改造 |
| P6-GATEWAY | P6-CONTRACT；真实冒烟另获授权 | 绑定模型和协议，分离连接/首字节/事件/完成诊断；覆盖 102 字节提前 EOF、六次连续失败、失败五次后有效回复清零、心跳/重复片段不假通过、有效续接去重、凭据失效停止、实际 Token 计量缺失阻断 |
| P6-DETACHED | 必要网关和清理门禁；非秘密模型配置及试跑授权 | 优先以固定 baseline 和两个微型 Task 证明客户端断开后的新步骤、真实失败→新会话修复→外部通过→下一任务，以及取消/预算停止和重连回执；tmux 存活、源码变化或两个退出零不算通过 |
| P6-MEMORY | P6-CONTRACT；与固定模型链路并行准备 | 按模型容量显式装配定位/流程/稳定经验，跨会话保留最新反馈和未完成修改，状态卡覆盖范围诚实且不遗漏；超限、索引失效、经验冲突不得暗中丢弃约束 |
| P6-CHECKPOINT | P6-CONTRACT；Git 接管及自动提交/恢复授权 | 实现 Task 检查点与受控回溯；保护已有索引/用户修改/新文件，覆盖提交和写回中断、重复接管、快照变更、恢复冲突、秘密不得入提交 |
| P6-ACCIDENT | P6-GATEWAY 与清理原语；恢复范围授权 | 网络/认证/预算/修复卡点生成独立事故现场，未知清理或写盘失败阻断重启；保持既有枚举兼容，人工新实例恢复不继承旧运行状态 |
| P6-MODELS-JEV | 模型注册和 P6-GATEWAY；不阻塞 P6-DETACHED | 注册多个 baseline 与 academic/factcheck；研究模型无编码工具能力时使用只读研究调用，证据与断言不混同。评估固定 Pi 1.3.0 下 Jev 来源、类型化接口、准确性、失败策略及接入落点；候选过滤后推荐，会话内固定模型，人工 pin 优先，未授权候选不调用 |
| P6-INTEGRATED | 上述相关能力及显式集成试跑授权 | 断开后完成固定/获准路由任务、独立验收、检查点、下一任务与事故挂起；研究有来源、不残缺工具调用，所有路由/重试预算归属明确。阶段交付不接受 ADR 或归档全计划 |

### 最小受控改动与证据定位

- 复用而不重建：[循环](../bmralph-suite-v5/scripts/bmad_loop.py:1)与[入口](../bmralph-suite-v5/scripts/bmad-loop.py)、[后端](../bmralph-suite-v5/scripts/bmad_agent_backend.py:82)、[传输](../bmralph-suite-v5/scripts/bmad_pi_transport.py)、[网络预算](../bmralph-suite-v5/scripts/bmad_pi_budget.py:21)、[上下文预算](../bmralph-suite-v5/scripts/bmad_context.py:64)及[输入接入](../bmralph-suite-v5/scripts/bmad_context_inputs.py:49)。职责分别为生命周期/授权、协议与模型选择、流式恢复/诊断、真实计量及必要输入；不是此次可编辑白名单。
- [共享网络预算](../bmralph-suite-v5/scripts/bmad_pi_budget.py:21)已添加显式启用的连续失败计数原语；失败尝试不返还累计请求或字节预算，跨传输会话及模型复用同一预算对象时不重置计数。达到门限后锁定阻断，[传输快照](../bmralph-suite-v5/scripts/bmad_pi_transport.py:340)聚合共享预算阻断并保留原失败诊断。HTTP 200、DONE 或心跳不能自动清零；有效回复确认仅核验当前请求归属与完整传输事实，仍依赖调用方先完成原生回复验收，尚未接入 Agent 原生验收路径或循环操作契约。会话结束的生命周期不能逐一关联会话内物理请求，因此[后端调用门禁](../bmralph-suite-v5/scripts/bmad_agent_backend.py:410)拒绝启用该未接通的连续失败运行策略，在环境复核、会话文件、转发和进程启动前停止；不改变既有未启用门限的固定模型路径，也不授予其新运行权限。相关资产为[预算反例](../bmralph-suite-v5/tests/test_pi_budget.py)、[重试反例](../bmralph-suite-v5/tests/test_pi_retry.py)、[传输诊断反例](../bmralph-suite-v5/tests/test_pi_transport_diagnostics.py)及[后端禁启反例](../bmralph-suite-v5/tests/test_pi_activation.py)。本地显式六次门限夹具不批准真实运行预算，不证明有效语义、续接去重、Token 计量、后台挂起或恢复；默认运行不暗启该门限，实际回执仅由平台任务记录引用。
- [任务运行](../bmralph-suite-v5/scripts/bmad_task_run.py:96)、[计划适配](../bmralph-suite-v5/scripts/bmad_plan_adapter.py:100)、[状态](../bmralph-suite-v5/scripts/bmad_state.py:189)与[真实证据裁决](../bmralph-suite-v5/scripts/bmad_pi_evidence.py)承担清理、事务接管、唯一进度、卡片和真实运行验收。复用现有[来源绑定](../bmralph-suite-v5/scripts/bmad_suite_source.py)、[运行副本](../bmralph-suite-v5/scripts/bmad_run_copy.py)及[监督器](../bmralph-suite-v5/scripts/bmad_supervisor.py)，不降低冻结运行资产边界。
- [模型路由模块](../bmralph-suite-v5/scripts/bmad_model_router.py:1)、[非秘密模型注册表](../bmralph-suite-v5/settings/model-registry.json)及[只读选择入口](../bmralph-suite-v5/scripts/bmad-exec.py:125)已创建；仅核对完整模型选项、显式候选与固定策略，不发送请求、不读取凭据、不改变在途模型，不证明真实 Jev 接入或固定模型后台闭环。未知精确 ID、能力和容量保持空值，候选注册不授予调用权限。
- [显式记忆接入](../bmralph-suite-v5/scripts/bmad_context_inputs.py:71)复用原输入组装：请求可显式指定非秘密索引，绑定计划/Task 身份、源字节与别名，完整装配必要流程、经验和导航；索引失效、冲突或累计字节超限失败关闭，不扫描历史、不裁剪必要条目。[批次接管](../bmralph-suite-v5/scripts/bmad_plan_adapter.py:49)与[循环边界](../bmralph-suite-v5/scripts/bmad_loop.py:422)核验当前及后续任务的只读记忆绑定，变化时不启动调用或推进验证；不冻结获准修改的任务源码。相关资产为[输入反例](../bmralph-suite-v5/tests/test_context_inputs.py)和[记忆边界反例](../bmralph-suite-v5/tests/test_memory_batch.py)。本地证据不证明模型容量、自然语言经验正确、真实 Pi 读取、Token 计量或断开推进；P6-MEMORY 的这些未完成门禁保留，实际回执仅由平台任务记录引用。
- [回执快照校验](../bmralph-suite-v5/scripts/bmad_pi_evidence.py:1)已实现第一版格式兼容；历史字节预算仅是旧格式校验边界，不是 Phase 6 运行授权或 Token 计量。合成快照校验不得登记真实断开、检查点、事故恢复或历史任务完成。
- [事故现场模块](../bmralph-suite-v5/scripts/bmad_accident.py:1)与[本地事故反例](../bmralph-suite-v5/tests/test_accident_guards.py)已创建；仅保存显式非秘密白名单的源码字节、权限、新文件及缺失状态，绑定计划/运行/Task 身份、固定原因、预算计数和回执定位。未执行验证或未知计量保持空值；回执定位不解释业务裁决，不证明清理。现场独立保存，不改唯一任务进度；保存中断保留已写成果，不覆盖用户修改。
- 工作区固定位置的事故阻断已接入[受管循环启动入口](../bmralph-suite-v5/scripts/bmad_loop.py:1)：先保存持久标记再写现场，存在未对账、残缺或伪成功标记时禁止新循环启动，不因更换运行目录绕过，不覆盖或自动解除旧标记。标记创建本身失败且未留下文件时不能保证该标记提供持久阻断，必须停止并保留失败回执；锁释放不证明清理安全。此门禁不取消在途进程、不阻断平台工具旁路，不提供同账号防篡改保证。路径过滤也不能证明任意源码正文没有秘密，调用方仍须核验白名单。自动事故捕获、实际取消清理、挂起及获准新实例恢复仍待接入和分别取证；本地禁启不证明真实后台事故恢复，实际回执仅由平台任务记录引用。
- [检查点候选模块](../bmralph-suite-v5/scripts/bmad_checkpoint.py:1)已实现显式非秘密普通文件冻结和独立单测验收关联；绑定计划、运行、Task、接管源身份及验收输入，保留源码字节与权限，不扫描或推断修改所有权。关联前后核验候选、源码、快照、回执及计划身份；保存或同步失败、期间变化和重复关联均不得返回成功，保留现场供对账，残留关联文件不是可继承的通过证据。[检查点本地反例](../bmralph-suite-v5/tests/test_checkpoint_guards.py:1)覆盖这些边界，实际回执仅由平台任务记录引用。本原语不操作 Git、不写任务进度、不提交或恢复，尚未接入循环检查点事务；索引与分支所有权、持久事务准备、提交/tree 关联、原子完成写回、事故对账和选择性恢复仍未完成，不能用本地候选冻结或验收关联替代真实 Task 检查点证据。Jev 扩展是否必需先核验，不默认另建通用插件或提供方框架。
- 本次允许按实际受影响契约修改相关 V5 实现、测试及必要的[计划模板](../bmralph-suite-v5/skills/bmad/references/templates/implementation-plan.template.md)、[能力导航](../bmralph-suite-v5/skills/bmad/references/capability-map.md)、[流程](../bmralph-suite-v5/skills/bmad/references/procedures/task-loop.md)与入口规则；不顺手重构，不扩大公共部署/V4范围。新增本地模块不表示已经接入真实闭环；验证资产必须实际创建和运行后再登记。
- 依据为用户提供的[确定性内存笔记](../docs/Ralph-Wiggum-Loop/Ralph-Wiggum-Loop.md:49)、[笔记中的 Ralph 自动提交描述](../docs/Ralph-Wiggum-Loop/Ralph-Wiggum-Loop.md:84)及已读 V5 文件。笔记链接不是 Ralph 原始源码审计，底层机制、性能数字和四变体断言不是本次运行事实。Jev 一手资料与替代决策保存于同一 ADR，本计划不镜像研究流水。

### 未决门禁及新会话交接

- 待批准：Token 口径与硬计量、有效回复/部分续接清零定义、Task/会话/批次总时限及总尝试、旧无进展阈值如何替代、模型与研究端点、Jev 独立端点/认证/预算、提交身份/分支/恢复路径、确切宿主启动/停止接口。缺必要信息时只阻塞相关执行，不反复完整重做分析。
- 交接提示：继续同一计划与 PROPOSED ADR，采用新的工程运行实例；仅携带当前目标/授权、必要约束、完整短状态视图、最新差异和事故定位，不回灌聊天。按 P6-CONTRACT → 必要网关本地门禁 → 固定 baseline 闭环准备推进，并独立实施记忆/检查点/事故，再接 Jev 与组合验收。预算未决只阻塞相应真实请求、后台运行和 Git 操作，不阻塞独立本地实现。Phase 6 未被现有控制器覆盖前，平台任务记录是唯一临时实施进度，引用实际回执，不在任务规格表或接管证据另记状态。保留 P5-PI-HEADLESS 暂停及空回执，不自动启动历史任务，不绕过来源、验收、清理、提交或远程授权。

## Phase 7 契约：四组件瘦身、Tmux 四槽位与文本经验接力（2026-10-20 紧急纠偏）

### 当前目标与 Gate #2

- 采用 [`architecture-v5.md`](../docs/Ralph-Wiggum-Loop/architecture-v5.md:1)及[同一 ADR](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)决策 11，不新建计划或提案。本轮仅两份文档修订和关键落点定义，不实施、不运行验证、不启动或自动交接工程。
- 人在 Antigravity IDE 审查计划与差异；规划/研究可以提出方案，但不能自动下发编码。未来必须由人类终端显式启动，绑定审核后的计划版本、任务集合、写入范围和预算；未满足前禁止编码模型调用。聊天批准、模式切换、看板重连、安装或保存文档均不是启动授权。
- 实质性目标、ADR、验收或权限变化暂停受影响执行，经人审核后按新版本重新显式启动；已启动且范围不变的任务期内，普通修复和下一依赖任务自动推进，不要求逐 Task 再次批准。
- 保留 Pi 编码、单写入链、真实验证、预算、候选冻结、检查点与事故资产；不重建控制平台，不继承历史绿灯或预算。计划保持 BLOCKED，ADR 保持 PROPOSED；历史条件归档授权不在本轮执行。

### 冻结资产与旧路线替代

- 在文档中冻结 [`bmad_control_store.py`](../bmralph-suite-v5/scripts/bmad_control_store.py)以及相关 [`test_control_contract.py`](../bmralph-suite-v5/tests/test_control_contract.py)、[`test_control_store.py`](../bmralph-suite-v5/tests/test_control_store.py)扩张路线；相关决定查询不继续扩写，不作为新流水线必需依赖。源码、测试和历史回执原地保留，本轮不删除、不修改、不宣称导入或入口已经禁用。
- 取消通用人工决定数据库、版本历史存储、持久消费中间件及 Cline TUI 统一总控的前置要求。Cline 保留 Slot-1 规划候选；其安装和安全探测证据保留在 ADR 决策 10，不再因外部槽位汇总接口未就绪阻塞独立看板方案。
- 用户报告的 1728 行膨胀、上下文爆炸和 API 错误是纠偏线索，不是本轮重新测量的结果；不以旧局部单测通过证明原路线适合或独立执行已通过。
- 旧 P7-INTAKE 的授权与接管边界纳入未来工程入口；P7-CLINE-PROBE 只保留规划适配必需的安全核验，取消全功能总控探测；P7-CONTROL-CONTRACT、P7-CONTROL-UI、P7-DECISIONS 的通用存储/统一聊天要求由 P7-1 和人工终端启动替代。旧 P7-ROLES-AUDIT 纳入 P7-4，P7-CHECKPOINT-LINK 纳入 P7-2/P7-4，P7-LIVE-INTEGRATED 纳入四组件组合验收，P7-CLOSEOUT 保留为全计划收尾条件，不新增第五个组件。
- AC 17–19 随本次明确架构调整修订为独立看板重连、人工版本启动及审核质疑后人工重启闭环；不将取消的旧界面/存储要求标记完成。原 Epic、其他 AC、八项历史类型化任务状态/回执及未被替代的 Phase 6 承诺保留。

### 四槽位分权

1. Slot-1：Opus 规划与目标协调，Cline CLI 保留适配候选；接收线索、三遍阅读与方案结晶，不直接编码、提交或启动后台。精确模型及接口以后续非秘密配置核验为准。
2. Slot-2：Astra academic 按需研究，保留完整模型 ID 与来源，不修改业务代码或验收，不把外部文本当执行指令。
3. Slot-3：Pi/Sonnet 编码，每 Task 及每次外层修复使用新进程/新会话；只处理当前获准局部目标，不自批、不修改验收，不自行提交完成。
4. Slot-4：独立 Sol，新会话盲审验收、冻结差异、相关源码/接口与真实测试；不读编码聊天、思考或辩解。先独立裁决，再基于同一证据提炼经验，不直接改业务代码或解除门禁。

四槽位是权限与职责划分，不要求四模型常驻；Rich 看板不是第五个 Agent。Tmux 保持任务期进程，不证明机器重启恢复或模型必然继续工作；本地 IDE 关闭后必须用新的真实步骤证明推进。

### 四个原子组件与拟议落点

下表仅保存规格、依赖和验收，不手工记录第二份任务进度。命令名称沿用用户指定的 bin/solo-*，分发源码放在 V5 套件内的 bin 子目录；任务运行文件放在实际获准工作区的 .solo 子目录，不写入套件分发源。本轮不创建这些资产，状态均为 PLANNED_NOT_YET_CREATED，不猜测试标识、可用参数或模型能力。

| 组件 | 拟议落点 | 依赖与最小验收 |
|---|---|---|
| P7-1 状态总线与 TUI 看板 | [`state.json`](../.solo/state.json)、[`solo-board`](../bmralph-suite-v5/bin/solo-board) | 核心快照读写逻辑不超过 50 行，不建设独立存储模块；单编排器写、Rich 看板只读。展示计划/运行身份、当前 Task/轮次、四槽位状态、阻塞原因和证据定位；缺失、损坏或过期显示未知。快照完整替换，重连不写任务或启动模型；不另建队列、聊天历史或授权总账。Rich 依赖在未来获准环境准备阶段确认，测试/运行不隐式联网安装 |
| P7-2 进度卡片与 Harness² 经验反射器 | [`solo-card-gen`](../bmralph-suite-v5/bin/solo-card-gen)、[`experience.md`](../.solo/experience.md)、[任务卡片目录](../.solo/cards/) | 复用既有差异/候选/检查点原语，生成当前 Task 受管文件与接口定位、真实验收及提交关联；不复制全历史、不遗漏关键依赖。Slot-4 在 Task 结束后提炼一条有证据和适用范围的教训，程序去重追加；无新教训不编造。下一新会话顶部注入有界相关规则，不覆盖目标、授权或验收；反射失败不伪造经验，提交/写回失败不推进任务 |
| P7-3 Jev 语义拦截门禁 | [`solo-jev-gate`](../bmralph-suite-v5/bin/solo-jev-gate) | 对接经核验的 pi-jev，目标开启无 UI 阻断配置；精确配置键及固定 Pi 兼容性须核验，不能仅靠声明推定。真实工具执行前覆盖获准写入/命令范围；缺认证、超时、服务失败或非法结果阻断，不静默放行或以普通模型替代。不得出站凭据、完整日志或无关源码；语义门禁不替代硬权限、预算、测试和独立审核 |
| P7-4 Tmux 四槽位外层编排器 | [`solo-orchestrator`](../bmralph-suite-v5/bin/solo-orchestrator) | 依赖 P7-1–3 及必要既有执行防护。人工显式启动后绑定计划版本/范围/预算，选择集合内依赖就绪任务；单 Task 新会话编码→外层真实验证→独立盲审→候选复核→获准检查点/写回→卡片与状态投影→下一 Task。最多三轮包括首次尝试，第三轮失败即挂起，禁止第四次编码调用；取消/预算停止确认受管清理，清理未知禁止重启 |

### 状态与经验的最小数据边界

- 唯一任务进度继续来自本计划清单；[`state.json`](../.solo/state.json)只是可重建显示快照，不是执行权威。运行身份、当前阶段与证据定位可保留，完整任务/依赖回到本计划读取，不能从看板伪造完成或推断执行授权。
- 50 行约束仅适用于快照核心读写逻辑，不是 Rich 界面或既有执行器的总行数；不把复杂存储转移到其他模块规避目标。原子替换提供完整快照，不宣称跨文件事务、同账号防篡改或数据库可靠性。
- 卡片保存当前任务的差异/接口定位和真实结果，不作为第二份进度；下一会话仍按需读取实际源码，不能仅凭导出摘要猜接口。完整失败现场留在既有授权运行目录，默认仅传当前有效反馈与定位。
- [`experience.md`](../.solo/experience.md)只包含非秘密、去重、有适用边界的简短规则，不存日志、聊天、任务进度或授权。首个任务没有经验是正常状态；注入预算受模型容量与既有输入约束控制，经验不能挤掉必需目标、验收和源码。
- 经验在 Task 边界追加并为下一会话重新绑定；本次明确替代将可演进经验永久冻结的旧解释，当前会话仍读取稳定快照。经验冲突不能自动放宽门禁；无需增加经验数据库、独立 Reflector 进程或自动训练循环。
- Harness²／Improvement Harness／Experience Reflector 本轮尚无已核验的一手正文，文本机制是用户指定的设计选择，不登记“论文证明 Markdown 优于数据库”或保证免微调持续提升。保留来源核验未知，不用未经取证的引用编号制造证据。

### 三轮策略与必要防护

- 每 Task 最多三轮编码候选，包括首次尝试；每轮仅一个编码会话，后接相关验证和独立盲审。验证失败或审核驳回占用同一轮数，第三轮失败停止，修复成功不返还已消耗预算；架构图中“大于三轮”的文字不许可第四轮。
- 模型 API 网络重试不是新的工程候选，仍计入获准请求/时间/Token 预算，不重置任务轮数或连续网络失败计数。尚未确认的真实运行预算、计量和生命周期接口保留为启动阻塞，不用固定三轮代替所有预算。
- Jev 必需护栏失效、认证/权限不足、候选变化、验收偷改、必需测试缺失或清理未知均停止对应执行；普通代码失败可在剩余轮数和预算内新会话修复，不推进依赖。
- 检查点复用既有受管白名单、冻结候选与提交/写回关联，不全库暂存、不提交用户已有改动、不强制切换或自动推送。提交成功而写回失败保留现场并阻断，不重复提交或凭看板自动恢复。

### 最小验收与关闭边界

- 后续获准工程只做四组件相关验证：快照/重连无执行副作用；两个依赖 Task 的卡片与有界经验接力；Jev 在无 UI、越界及服务异常下实际阻断；独立审核驳回后新会话修复与第三轮禁止第四次调用。不增加 70 项存储全排列或重新跑无关全套回归，关键失败边界不能因瘦身被删除。
- 实际组合验收仍须人明确启动及预算：两个依赖 Task、外层失败修复、独立审核、真实检查点、客户端关闭后新模型/工具步骤、看板重连及取消/预算停止。模拟、进程存活和状态文件变化不能替代真实运行证据。
- 门禁质疑时展示原因与证据、暂停相关执行，人审查新方案后终端显式启动新版本；不恢复旧编码聊天、不自动重放旧工具副作用，不建立持久审批数据库。
- 八项历史任务状态与回执不变，不解除 P5-PI-HEADLESS 暂停；原 Epic、其他 AC 和未被替代的阶段承诺仍须有覆盖定位。四组件局部完成不接受 ADR、不结束全计划或提前归档。
- 未来全部必需门禁满足且按契约确认后才接受 ADR；全计划完成才行使历史条件归档授权。归档目标含时间和计划标识，防覆盖保存并复核源版本，失败保留源。本轮仅文档结晶，不执行上述验收或归档。

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
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-86dd1a27fb0b47d0ad3b5e86d4cd175e.verdict.json"
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
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-bd674771a61b4302b28a7a9fd85ca7e1.verdict.json"
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
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-bd674771a61b4302b28a7a9fd85ca7e1.verdict.json"
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
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-bd674771a61b4302b28a7a9fd85ca7e1.verdict.json"
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
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-c3965d634e434b14a434a8069042c112.verdict.json"
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
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-fdcdc58716db4d3a879a2f066c2a15b6.verdict.json"
    },
    {
      "task_id": "P5-PI-DRIVER",
      "title": "现有后端内 Pi 薄驱动及本地协议反例；不证明真实独立运行或全计划完成",
      "depends_on": [
        "P4-ISOLATION"
      ],
      "status": "COMPLETED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests",
        "pattern": "test_pi_backend.py",
        "minimum_tests": 31,
        "required_tests": [
          "test_pi_backend.PiBackendGuards.test_argument_allowlist_uses_one_shot_ephemeral_json_and_closed_option_parsing",
          "test_pi_backend.PiBackendGuards.test_argument_injection_extensions_and_relative_request_fail_closed",
          "test_pi_backend.PiBackendGuards.test_source_version_authorization_and_runtime_cannot_be_relaxed",
          "test_pi_backend.PiBackendGuards.test_three_round_binding_rejects_other_thresholds_and_booleans",
          "test_pi_backend.PiBackendGuards.test_unapproved_runtime_blocks_invoke_before_request_or_launch",
          "test_pi_backend.PiBackendGuards.test_missing_credentials_blocks_load_before_driver_read_or_launch",
          "test_pi_backend.PiBackendGuards.test_real_pi_category_cannot_be_loaded_as_isolated_fixture",
          "test_pi_backend.PiBackendGuards.test_load_accepts_only_self_driver_and_preserves_pi_runtime_kind",
          "test_pi_backend.PiBackendGuards.test_existing_writer_lease_is_required_and_owner_is_verified",
          "test_pi_backend.PiBackendGuards.test_outer_threshold_and_execution_state_must_match",
          "test_pi_backend.PiBackendGuards.test_missing_credentials_blocks_invoke_before_request_or_process",
          "test_pi_backend.PiBackendGuards.test_complete_protocol_is_only_call_evidence_not_business_completion",
          "test_pi_backend.PiBackendGuards.test_completion_promise_and_exit_without_protocol_are_rejected",
          "test_pi_backend.PiBackendGuards.test_wrong_workspace_session_id_or_duplicate_session_blocks",
          "test_pi_backend.PiBackendGuards.test_model_error_abort_missing_settled_or_late_activity_blocks",
          "test_pi_backend.PiBackendGuards.test_retry_failure_and_provider_error_cannot_be_overridden",
          "test_pi_backend.PiBackendGuards.test_jsonl_duplicate_keys_truncation_and_record_budget_fail_closed",
          "test_pi_backend.PiBackendGuards.test_unicode_separators_inside_text_do_not_break_jsonl",
          "test_pi_backend.PiBackendGuards.test_nonzero_exit_cannot_be_masked_by_valid_protocol_or_promise",
          "test_pi_backend.PiBackendGuards.test_timeout_cancellation_and_unknown_cleanup_override_protocol_ok",
          "test_pi_backend.PiBackendGuards.test_each_invocation_has_distinct_input_and_only_current_feedback",
          "test_pi_backend.PiBackendGuards.test_state_card_and_input_budget_block_before_launch",
          "test_pi_backend.PiBackendGuards.test_legacy_timeout_is_not_claimed_as_model_request_timeout",
          "test_pi_backend.PiBackendGuards.test_request_tool_session_and_batch_caps_are_not_conflated",
          "test_pi_backend.PiBackendGuards.test_exec_interception_preserves_process_group_and_excludes_inherited_config",
          "test_pi_backend.PiBackendGuards.test_frozen_loop_still_rejects_real_pi_without_activation",
          "test_pi_backend.PiSupervisorDelegationGuards.test_frozen_supervisor_fuses_after_exactly_three_unchanged_failures",
          "test_pi_backend.PiSupervisorDelegationGuards.test_three_unchanged_failures_prohibit_fourth_call_and_dependency_progress",
          "test_pi_backend.PiSupervisorDelegationGuards.test_unknown_cleanup_prohibits_next_call_verification_and_restart",
          "test_pi_backend.PiSupervisorDelegationGuards.test_agent_call_timeout_cleans_same_group_and_preserves_changes",
          "test_pi_backend.PiSupervisorDelegationGuards.test_agent_call_interrupt_cleans_same_group_and_preserves_changes"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_agent_backend.py",
          "bmralph-suite-v5/scripts/bmad_loop.py",
          "bmralph-suite-v5/scripts/bmad_plan_adapter.py",
          "bmralph-suite-v5/scripts/bmad_context_inputs.py",
          "bmralph-suite-v5/scripts/bmad_context.py",
          "bmralph-suite-v5/scripts/bmad_supervisor.py",
          "bmralph-suite-v5/scripts/bmad_environment.py",
          "bmralph-suite-v5/scripts/bmad_execution.py",
          "bmralph-suite-v5/scripts/bmad_task_run.py",
          "bmralph-suite-v5/scripts/bmad_run_copy.py",
          "bmralph-suite-v5/scripts/bmad_suite_source.py",
          "bmralph-suite-v5/scripts/bmad_suite_lease.py",
          "bmralph-suite-v5/scripts/bmad_state.py",
          "bmralph-suite-v5/scripts/bmad-exec.py"
        ]
      },
      "verdict_file": "_bmad-output/verification/phase5-resume-20261018/run-6e4dcb2566144f139158d5a9022a2ccf.verdict.json"
    },
    {
      "task_id": "P5-PI-HEADLESS",
      "title": "Pi 真实运行回执裁决反例；单测通过不等于远程两轮、AC 9 或 P5 通过",
      "depends_on": [
        "P5-PI-DRIVER"
      ],
      "status": "SUSPENDED",
      "verification": {
        "operation": "unit-test",
        "environment_file": ".bmad-control/phase2-environment.json",
        "directory": "bmralph-suite-v5/tests_pi",
        "pattern": "test_pi_headless_evidence.py",
        "minimum_tests": 8,
        "required_tests": [
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_fixture_or_exit_zero_is_not_real_runtime_evidence",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_runtime_version_workspace_and_task_binding_are_required",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_failure_requires_actual_verification_and_new_session_feedback",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_client_disconnect_requires_new_model_or_tool_steps",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_next_task_requires_independent_pass_and_explicit_batch_membership",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_budget_stop_requires_no_new_calls_and_confirmed_cleanup",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_unknown_cleanup_or_usage_never_manufactures_pass",
          "test_pi_headless_evidence.PiHeadlessEvidenceGuards.test_receipt_checker_unit_pass_does_not_accept_adr_or_archive_plan"
        ],
        "inputs": [
          "bmralph-suite-v5/scripts/bmad_pi_evidence.py"
        ]
      },
      "verdict_file": null
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
- [ ] **AC 16 (四槽位分权)**：Opus 协调目标，研究提供证据，Pi/Sonnet 编码，独立 Sol 审核成果与流程合理性；模型、会话和权限绑定可核验，编码者不能自批或修改验收制造通过。
- [ ] **AC 17 (独立看板可重连)**：按最新纠偏替代旧统一总控聊天要求。独立 Rich 树状看板从轻量状态快照及计划定位展示任务、四槽位状态和阻塞原因；缺失/损坏/过期显示未知，电脑或手机重连只读展示，不启动模型、不写任务进度，不要求建设聊天持久中间件。
- [ ] **AC 18 (人工终端版本启动)**：按最新 Gate #2 替代旧通用持久审批要求。人审核计划后在终端显式启动，绑定版本、任务集合、写入范围和预算；重大需求/ADR/验收/权限变化暂停，经人审核后重新显式启动。模型建议、聊天批准、状态快照及看板重连不得授予执行权；重复启动由既有单写入边界拒绝，不自动恢复旧任务。
- [ ] **AC 19 (审核质疑后人工重轨)**：按最新四组件方案调整旧统一总控决定恢复闭环。真实运行中 Sol 质疑门禁时展示原因与证据并暂停相关执行；人审查同一计划/ADR 的新版本后终端显式启动，在新契约下验证与继续。保留原失败，启动不冒充验证通过，经验规则不得自动解除门禁。
- [ ] **AC 20 (完整收尾而非局部归档)**：全部原有及新增必需事项有当前有效证据或明确人工范围决定；ADR 按契约接受，归档保存并复核绑定完整计划，失败保留源，不遗失暂停记录、回执或未完成承诺。

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

当前目标以重写后的 Phase 7 和 ADR 决策 11 为准：人工终端启动、Tmux 四槽位、独立看板、Pi 编码、文本经验、独立审核与 Task 检查点。以下任务 5.1–5.6 保存历史落点与未完成验收；旧一次性交接、兼容引擎或预算不覆盖当前架构与仅文档授权，不作为可直接执行的旧许可。

- **任务 5.1**：核验条件优先候选 Pi Coding Agent 的实际来源、固定版本、独立无头/JSON/RPC 入口、新进程及新会话、等待/取消/清理、独立认证、规则/技能加载、工具权限和用量接口。先定位公开安装资产与一手版本契约，不读凭据；VPS 安装、认证准备和项目外写入另获授权。Roo 独立适配不再新增，Claude Code 仅为待核验兼容候选；不从旧包名或社区文章猜命令，不静默换引擎。选型依据见[同一 ADR 的替代条款](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)。
- **任务 5.2**：复用已交付且冻结的 [V5 循环入口](../bmralph-suite-v5/scripts/bmad-loop.py:12)及独立验证器，不重建循环或永久服务。薄驱动实际已落入[现有后端](../bmralph-suite-v5/scripts/bmad_agent_backend.py:81)，本轮仅其本地交付及定向证据接管；真实运行仍需[循环门禁](../bmralph-suite-v5/scripts/bmad_loop.py:353)等最小解冻的独立授权，不承诺仅改后端即可接通。远程任务期进程及独立认证均在 VPS，客户端只提交和观察；安装、部署或 IDE 重载不启动任务。活动运行绑定已核验来源和隔离运行副本，升级先停止、确认清理、验证候选并获准启用，禁止热改后继续运行。
- **任务 5.3**：每次调用创建新 Pi 进程和新工程会话；失败后只转发必要约束、未提交成果和实际独立验证反馈，不恢复完整聊天。真实失败不推进，预算内修复后独立验证通过并保存唯一任务进度，由原程序从显式获准集合选择下一依赖就绪任务。原生 Pi/Claude Code 协议分别映射本地驱动契约，不将兼容方向写成已实现能力。
- **任务 5.4**：复用时间、轮次、外层调用预算、无进展阈值和退避；核验 Pi 内部模型请求、工具、重试、用量和费用边界，未知项明确披露，不冒充已强制预算。保留既有 30 秒驱动、15/30/600 秒工具分级和 600 秒批次上限；无法完成时停下请求明确调整。API/网络失败与业务失败分开；认证/权限失败、取消或预算耗尽后停止新调用，保留成果，清理未知禁止重启。
- **任务 5.5**：每个工作区一个活动写入者；同机生产服务与编码任务使用独立工作区、受限账号和验证环境。保留失败轮次的未提交修改，获准才提交本任务改动；推送和部署分别授权。
- **任务 5.6**：另获真实试跑授权后验证 Pi 独立至少两轮及完整失败修复、依赖推进链路；关闭本地 IDE 后必须出现新的真实模型/工具步骤及轮次证据，重连可查结果，取消或预算停止等待受管进程真实结束。客户端断开不等于 VPS 模型网络断开；模型网络故障另验失败关闭，不改宿主网络。进程存活、文件变化、两个退出零或回执判定单测不算通过；机器重启、宿主崩溃自动恢复不在首轮范围。Pi 两轮及其余适用必需门禁通过且转正获准后才可接受 ADR；全计划完成并获准前不归档。

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

下列矩阵与命令保存较早工程阶段的验收契约和资产描述，不是当前执行指令；本次仅回读两份文档，不运行静态检查或业务验证。AVAILABLE 不表示依赖就绪、证据仍有效或已通过，历史“未创建/冻结”也不代替当前源码核验。Phase 6 的新增验收与未决门禁见其任务规格；未来工程接管按实际资产、授权及受影响证据实例化，不猜参数、不默认重跑全部历史测试。

| 阶段 | 验证目标 | 拟执行命令或检查 | 资产状态 | 通过判定 |
|---|---|---|---|---|
| P0 | V4 兼容与 V5 静态契约 | 下方显式 `--suite v4`、`--suite v5` 及契约回归命令 | 两版本接口与相关契约测试 AVAILABLE | 两版本分别通过；V4 通过不代替 V5，更不外推为运行时证据 |
| P1 | 环境复用 | 下方环境登记与复核反例；实际接口参数见 V5 验证契约 | 本机 Python 资产 AVAILABLE；固定 GCC/musl 镜像及隔离复用仍待实现 | 验证期间无隐式安装，依赖缺失明确报告；本机登记不替代固定镜像门禁 |
| P2 | 原控制器反例 | 下方监督器、子运行器、单测裁决与保存后证据查询测试，以及本轮受控回滚、进程树补充反例 | 本机相关资产及本轮补充反例 AVAILABLE；容器和脱离会话清理不在本轮覆盖范围 | 真实失败、不命中、取消及相关证据失效正确处理；孤儿主进程退出零或无法确认清理均阻断；局部测试不代替范围外门禁 |
| P3 | 有界状态视图 | 下方状态模块与实际 CLI 反例；参数见 V5 验证契约 | 候选只读投影资产 AVAILABLE；活动计划进度迁移及完整控制器接入未完成 | 行数、字节及 JSON 输出预算有效，未完成事项不丢失；模型勾选不制造完成事实 |
| P4 | 上下文与循环 | 下方上下文预算、计划与定向源码组装、实际 CLI 反例；任务期循环测试待实现 | 本地预算与只读组装资产 AVAILABLE；独立新会话、累计工具结果运行接入及循环资产仍待实现 | 必要输入完整保留，启动与累计输出预算分别有效；本地组装不替代新会话、反馈有效性、宿主自动加载及循环停止门禁 |
| P5 | Pi 真实独立两轮、失败修复及依赖推进 | 任务 5.1 核验固定版本和确切生命周期命令；另获授权后采集客户端关闭后的新步骤 | 前序报告官方 Pi 1.3.0 已安装；现有后端薄驱动与本地反例已存在，当前接管其证据；真实接入冻结，未来回执裁决资产待创建，单测不替代试跑 | 实际独立验证失败→新会话真实反馈修复→业务通过→程序选集合内下一就绪任务；客户端关闭后有新模型/工具步骤；取消/预算停止无新调用并确认清理；全部绑定、范围与预算证据完整 |
| P6 | V5 分发与 V4 兼容 | 任务 7.7 的临时根版本、缓存、回切与保护测试；下方列出套件选择、部署租约、来源绑定、继承锁及版本操作守卫反例命令 | 本地版本选择、运行资产分发、协作租约、V5 来源绑定及同一部署根的版本操作守卫反例资产 AVAILABLE；活动任务与任务期循环接入仍待实现 | 显式版本全链路一致、错误不写入、V4 兼容与用户资产保护；已有部署的版本操作须在共享租约期间失败关闭，并在操作、新版移交及最终部署期间持续持有排他锁。来源绑定须核验 V5 身份、受管物理资产与分发映射，边界变化停止对账，不恢复旧文件。原语验证不替代活动任务接入、事务完成诊断、宿主模式语义、跨部署根保护、在途进程清理或真实宿主加载 |

本地验证接口与历史说明见[类型化验证契约](../bmralph-suite-v5/skills/bmad/references/procedures/verification.md)，实际能力以当前源码为准；其中历史“没有完成写回”等陈述不覆盖现有适配接口。同一活动计划具有唯一结构化清单，六项历史完成源记录保留；状态卡只投影，不在平台记录、ADR 或散文维护第二份任务进度。P5-PI-DRIVER 仅按本轮窄恢复及精确协议证据登记本地完成，P5-PI-HEADLESS 保持 SUSPENDED/空回执，真实门禁未通过。配置语法、专项竞态、固定镜像、容器及真实运行承诺保留，不虚构子命令。静态校验器不检查完整任务块；结构、依赖和完成证据须由状态及适配原语另行核验，其 PASS 也不是全阶段验收。

以下为保留的历史工程命令契约，不默认全部执行。本轮五组类型化单测完整取自对应任务验证对象，四组用于六项完成证据刷新、一组用于 P5 本地交付；各次前台验证分别限时 30 秒，探测 15 秒、stdin 封闭，不隐式安装。只有精确匹配当前证据才能复用，旧回执保留不改；不得以同文件曾全部通过替代契约匹配。全部宏观验收和真实运行授权门禁保留。

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

若后续获准 Pi 接入出现工具适配异常，先停止并保留成果；以下是历史受控恢复范围，不扩大当前冻结与授权：
1. 仅恢复 [V5 套件](../bmralph-suite-v5/)、[公共部署脚本](../scripts/)、[部署入口](../bs.sh)和[安装入口](../install.sh)中本任务获准且经差异核对允许恢复的修改；V4 源目录不在本任务修改范围内。已部署 V5 回切 V4 须另按显式版本选择和受管事务执行，不把源码恢复当作宿主回切完成；
2. 保持用户既有未提交改动与[项目事实基线](project-context.md)不变；
3. 回滚前检查工作树并发修改，确保第三方非受管资产零破坏。
4. 停止远程任务须先取消并确认在途 Agent 与验证进程结束；不得用全目录恢复或自动清理覆盖失败轮次和用户修改。

## 7. 架构引用、修订边界与批准状态

- 当前关联[提案 ADR](adrs/ADR-20261012-bmad-solo-anti-bureaucracy-and-programmatic-guards.md)持续修订，不另建重复方案。提案未生效，旧任务与原待办保持独立。
- [已接受生命周期 ADR](adrs/ADR-20261008-roocode-bmad-v42-lifecycle-and-governance.md:37)的显式任务优先、历史恢复授权、分析权限与受管资产保护继续保留。拟调整的是新任务不默认归档发现、验证与任务状态的存储职责、后台运行的工程适配，不修改其历史接受范围。
- 原“无常驻调度器”细化为不建设永久平台，允许单任务期的持久执行进程；原状态卡权威入口拟改为计划任务清单的程序投影，须同步入口、模板和校验器。
- 当前真实运行门禁：历史薄驱动、源码枚举及安装报告均不证明客户端断开推进、新预算或新增检查点/模型路由通过；本次不重新判断旧回执有效性，也不把历史“仍冻结”文字当成当前源码事实。仅 Pi 编码框架继续演进，其他执行器不新增；预算、宿主接口、验收与清理未就绪时保持阻塞，当前不试跑。
- 基线首行含字面换行转义，历史记录仅作相关事实线索；本次不修复基线格式、不写入新提案为项目事实。
- V5 隔离是本轮新增范围决定；旧文档中的 V4 链接只作为事实参照，新生产实现以 V5 落点为准。独立源码目录不等于独立宿主权限或同根双活；默认激活、插件槽位及版本接口保持上述保守提案，后续不得静默更改。
- [x] 用户授权本任务方案与 ADR 持久结晶。
- [x] 2026-10-16 用户授权 Phase 1 本地工程套件与反例封顶闭环，定向验证及 238 项单测全部通过。
- [x] 2026-10-16 用户授权 Phase 1 成果 Git 提交固化 (34a5c19)。
- [x] 2026-10-16 用户授权 Phase 2 本地任务期循环控制器 (bmad-loop.py)、14 项循环反例断言及规约文档完成与 Git 提交固化 (7268440)。
- [x] 2026-10-16 用户授权 Phase 3 活动计划结构化适配、无头驱动抽象与模拟断网验证完成与 Git 提交固化。
- [x] 2026-10-17 用户授权同一计划及提案的 Pi 条件选型与文档结晶；不等于工程解冻、安装或试跑。
- 2026-10-19 历史授权：当时用户确认没有后台或其他会话写入两份文档，只准最小补丁结晶；该确认不证明当前进程状态，历史工程与启动授权不自动延续。
- 2026-10-20 当前紧急纠偏授权：仅同一计划与 ADR 文档修订、四组件落点定义和存储路线文档冻结；不修改/删除源码或测试、不验证、不自动编码或后台启动、不操作 Git、不转正或归档。人类终端显式启动及对应范围、预算为未来执行前提；文档保存和模式切换不触发工程。
- 前序接管报告官方 Pi 1.3.0 已安装；本轮不重复安装。独立认证准备、真实接入所需冻结文件解冻及宿主激活仍分别待授权。
- [ ] 目标 VPS / 真实 Pi 独立会话试跑授权及预算、操作范围确认。
- Git 分支、提交及选择性恢复：待明确对应操作范围；推送和生产部署仍未授权。
- ADR 接受：全部适用必需门禁通过后按契约另行确认，当前保持 PROPOSED。
- 计划归档：2026-10-20 用户已给予全计划完成后的条件授权；完成前保留活动副本，归档时防覆盖保存并复核源版本。
