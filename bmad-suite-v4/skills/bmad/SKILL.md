---
name: bmad-solo
description: >
  BMAD-Solo V4.2: Adaptive Architecture-Grounded Engineering Loop with Empirical Backpressure.
  Automatically routes software tasks through Analyst, Product, Architect,
  Developer, Reviewer/QA, and Operator modes with scenario-adaptive gates.
  Ingests pending implementation plans, enforces Epic-level test barriers,
  and promotes ADRs to project-context with full traceability.
---

# BMAD-Solo V4.2 Router (Adaptive Empirical Engine)

## Objective

Complete the user's task through one continuous, disciplined AI session.
Do not simulate a multi-agent meeting. Do not force users to memorize internal procedure names.
The AI automatically detects task scenario fingerprints, dynamically mounts corresponding safety valves,
and uses real test feedback as the ultimate arbiter of truth.

---

## 1. 意图、授权与三级计划路由

先判断只读、结晶、实施、继续或重放意图，并核验实际工具权限。读取计划不等于获得执行授权；只读任务仅取证和会话交付，不写文件、不运行验证、不转正或归档。

1. **显式指定优先**：用户指定计划时只读取该候选，跳过默认暂存入口。指定文件缺失或非法时报告可恢复阻塞，可发现候选，不静默替换任务。
2. **活动计划探测**：无显式路径时才探测 `_bmad-output/pending_implementation_plan.md`；相关且有效才绑定，无关计划不抢占，多任务冲突时请求选择。
3. **归档与空闲降级**：默认入口缺失是正常状态，不重复盲读。继续历史任务时检索 `_bmad-output/archive/plans/` 并展示匹配依据，不自动执行最新归档；候选不明时请求选择，无候选时按意图空闲或提出新方案。明确的小修复与运维任务可走轻量路径。
4. **恢复边界**：文件缺失、权限拒绝、磁盘错误和格式损坏分别处理。历史计划默认只读，恢复或重放须显式授权，建立保留来源的新执行实例并重新验证，不继承旧绿灯或覆盖历史输入。
5. **契约绑定**：校验 `plan_id`、`status`、`scenario`、`impact_tier`、`requires_adr`、`adr_file`、`verification_type`、`verification_command`、`verification_command_status`、`authorization` 和 `session_id`。绑定路径、标识、内容指纹与阶段，修改前复核未被替换；本任务合法更新计划后记录新指纹。当前用户授权与立项时授权分别记录，不编造会话标识。
6. **事实与平台适配**：读取 `_bmad-output/project-context.md`；仅在权限和任务允许时执行 `timeout 15s git --no-pager status --short < /dev/null`。使用当前平台实际提供的任务跟踪能力；不强制写入未知的应用目录，不编造会话路径，不绕过工作区边界。

状态契约：`INTAKE → READ_ONLY / IDLE / NEEDS_SELECTION / READY`；获准实施后 `READY → EXECUTING → VERIFYING → COMPLETED → ARCHIVED`。失败进入 `BLOCKED`，明确暂停进入 `SUSPENDED`，获准恢复后重新校验再进入 `READY`。

---

## 2. Scenario-Adaptive Gating Engine (4 大场景自适应动态安全阀)

Never apply a rigid, one-size-fits-all conveyor belt. The router dynamically mounts procedures based on the scenario:

```
                         读取任务指纹 (Scenario Fingerprint)
                                     │
      ┌────────────────┬─────────────┴───────────────┬────────────────┐
      ▼                ▼                             ▼                ▼
【场景 1: 算法型】 【场景 2: 结构型】          【场景 3: 缺陷型】 【场景 4: 运维型】
  (algo)           (structural)                  (bugfix)         (ops)
      │                │                             │                │
  ✔ Algo-Fit       ✘ 跳过 Algo-Fit               ✘ 跳过架构门禁   ✘ 严禁跑业务单测
  ✔ Preflight      ✔ Preflight                   ✔ 仅跑足迹单测   ✔ 仅审 Git Diff
  ✔ Epic 单测阻断  ✔ Epic 单测阻断               ✘ 不建/不转ADR   ✘ 不建/不转ADR
  ✔ 状态对账       ✔ 状态对账                    ✔ QA 极速闭环    ✔ 纯协同闭环
  ✔ ADR 转正       ✔ ADR 转正                    │                │
      │                │                             │                │
      └────────────────┴─────────────┬───────────────┴────────────────┘
                                     ▼
                           【授权与绑定式闭环】
                    仅归档已完成且实际绑定的活动计划
```

### 场景 1：算法与高能计算型 (`scenario: algo`)
- *适用范围*：K线、缠论、相空间动力学、回测微服务、极速监控循环、ClickHouse 批量入库。
- *强制安全阀*：
  1. **挂载 `algorithm-fit.md`**：硬性审查 NFR（单循环延迟上限、内存预算、抗过拟合边界）。严禁无回测依据的参数过拟合！
  2. **挂载 `architecture-preflight.md`**：检查数据流与通道契约。
  3. **启用 Epic 单测物理背压阻断**。
  4. **完工挂载 `state-reconcile.md` 与 ADR 转正**。

### 场景 2：系统结构与重构型 (`scenario: structural`)
- *适用范围*：多模块解耦、公共接口改造、数据迁移、服务分层。
- *强制安全阀*：
  1. **跳过 `algorithm-fit.md`**（零算法开销）。
  2. **挂载 `architecture-preflight.md`**：重点审查数据所有权、公共接口兼容性与跨层调用。
  3. **启用 Epic 单测物理背压阻断**。
  4. **完工挂载 `state-reconcile.md` 与 ADR 转正**。

### 场景 3：局部缺陷修复型 (`scenario: bugfix`)
- *适用范围*：单组件修复、参数微调、前端样式修复（S/M 级小任务）。
- *行为准则*：
  1. **跳过 Preflight、跳过 Algorithm-Fit**（杜绝形式主义卡死）。
  2. **严格执行足迹全等单测 (Footprint Congruent Test)**：仅精准运行与本次改动直接相关的测试，严禁全量盲测。
  3. **不建立、不转正 ADR**：防止日常补丁稀释架构总账。

### 场景 4：运维协同与配置型 (`scenario: ops`)
- *适用范围*：Git 提交推送、`./bs.sh` 镜像分发、配置校验、文档更新。
- *行为准则*：
  1. **严格遵从收敛锁 4**：严禁启动容器执行业务单元测试！
  2. **以 Git Diff 洁净度与配置文件语法校验为最小充分通过证据**。
  3. 杜绝重型架构开销。

---

## 3. Epic Verification Gate (Epic 级物理单测背压阀门)

获准工程实施后，按绑定计划的每个阶段执行以下门禁。根据验证类型和改动范围选择配置校验、隔离分发测试或相关单测，不运行无关业务测试；验证资产尚未创建时先完成其实现，缺失不能记为通过。静态权限用例与参考路由模型不证明目标 Roo 的实际权限执行或模型行为。

1. **Per-Epic Execution**: Implement code changes for Epic N strictly within its boundary.
2. **Physical Test Barrier**:
   - Immediately execute the assigned test command: `timeout 30s <test_cmd> < /dev/null`.
   - **IF TEST FAILS**:
     - **APPLY INSTANT BACKPRESSURE**: Halt immediately!
     - The AI is **strictly forbidden** from marking the task as `[x]`, and **strictly forbidden** from moving to Epic N+1!
     - Must inspect failure output, isolate the regression, and fix it in place until green.
   - **IF TEST PASSES**:
     - Record test evidence, mark Epic N as `[x]`, and safely advance to Epic N+1.

---

## 4. 完工门禁：对账、溯源与绑定式归档

仅获准实施且全部必需验收通过的任务进入完工闭环；只读任务不进入此流程。

1. **状态对账**：按照 `state-reconcile.md` 对照实现差异、验证输出及架构边界。记录命令、工作目录、退出状态、关键输出与目标；条件一致不能豁免未通过的必需门禁。
2. **ADR 转正**：仅绑定计划要求 `requires_adr: true` 且全部必需门禁通过时，将其关联 ADR 从 `PROPOSED` 更新为 `ACCEPTED`。必需目标版本或运行时证据缺失时保持提案，披露阻塞，不转正其他任务的 ADR。
3. **事实更新**：工程阶段仅向 `_bmad-output/project-context.md` 添加已经验证的事实及真实 ADR 溯源；未知会话标识明确记录为未知，不编造，不将静态测试外推为运行时事实。
4. **绑定式归档**：仅处理实际绑定的活动计划，不固定清空默认暂存路径。复核标识与内容指纹，归档目标包含时间和计划标识，禁止覆盖已有记录。先确认目标完整保存，再复核源未被替换并处理活动副本；失败保留源文件。历史输入及其他暂停任务保持独立，无绑定计划的轻量任务不执行归档。

---

## 5. Terminal Execution Penta-Invariants

每条命令遵循当前平台实际支持的终端五大守恒铁律，不照搬其他平台的专用参数：
- **单飞排队**：前序命令返回后才启动下一条，不并发命令，不遗留孤儿任务。
- **分级超时**：探测 15s、验证 30s、构建 600s；使用进程级超时，不能把工具提前返回时间当作进程终止保证。
- **前台同步**：等待真实退出结果，不启动未托管后台进程。
- **输入封闭**：附加 `< /dev/null`，仅选用当前命令实际支持的非交互参数。
- **工具正交**：文件读写使用原生工具；复杂排查脚本先写入项目内草稿区，再限时调用。
