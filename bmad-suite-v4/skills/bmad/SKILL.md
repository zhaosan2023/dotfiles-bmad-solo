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

## 1. Input Ingestion & Staging Priority (防任务幻觉前置通道)

At the start of execution (e.g. user invokes `/bmad-solo 执行` or passes a task):

1. **Check Staging Area (`_bmad-output/pending_implementation_plan.md`)**:
   - If present: **Prioritize this file as the primary execution contract!**
   - Read its frontmatter fingerprint (`scenario`, `impact_tier`, `requires_adr`, `verification_command`).
   - Do not rely on conversational brainstorming memory; execute strictly from the crystallized staging plan.
2. **Read Project Truth Baseline**:
   - Ingest `_bmad-output/project-context.md` (Ground Truth) and active Git state (`git status --short`).
3. **Artifact Monad Lock (跨模型计划工具锁)**:
   - For all M/L tier tasks: **The AI MUST call the native IDE tool `write_to_file` to initialize `<appDataDir>/brain/<conversation-id>/implementation_plan.md` and `<appDataDir>/brain/<conversation-id>/task.md` before executing any code changes**.
   - This guarantees that whether running on Gemini 3.8 Flash, Gemini 3.1 Pro, or Claude, the living plan and state machine are visibly tracked in Antigravity.

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
                             【统一清理归档】
                         清空 pending_plan 暂存区
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

During Developer mode implementation of M/L tasks:

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

## 4. Completion Gate: Promotion, Traceability & Great Cleanup

When all planned tasks are implemented and verified:

1. **State Reconciliation (`state-reconcile.md`)**:
   - Verify code footprint, terminal test output, and architectural boundary.
   - Must achieve `CONSISTENT` or `CONDITIONALLY_CONSISTENT`.
2. **ADR Promotion (转正门禁)**:
   - If `requires_adr: true` in the staged plan:
     - Flip the corresponding ADR status in `_bmad-output/adrs/ADR-*.md` from `Status: PROPOSED` to `Status: ACCEPTED`.
3. **Project Context Refresh with Traceability Pointers**:
   - Update `_bmad-output/project-context.md` with the verified new architectural facts.
   - **Mandatory Traceability Footnote**: Each new architectural fact must link back to its origin:
     ```markdown
     - **Traceability**: ADR `_bmad-output/adrs/ADR-YYYYMMDD-[topic].md` (Session ID: `<session-id>`)
     ```
4. **Staging Cleanup & Archival (清空暂存区)**:
   - Move `_bmad-output/pending_implementation_plan.md` to:
     `_bmad-output/archive/plans/plan-<YYYYMMDD-HHMMSS>.md`.
   - Ensure the active workspace remains clean, zero pending debris.

---

## 5. Terminal Execution Penta-Invariants

Enforce the **Terminal Execution Penta-Invariants** (`bmad-constitution.md` 8.5) on every command:
- **Single-Flight Monad Lock**: Never launch a command while any background task is running.
- **Universal Bounded Timeout**: Tier 1 (15s probe), Tier 2 (30s verify), Tier 3 (600s build).
- **Foreground Synchronization Lock**: `WaitMsBeforeAsync: 10000ms`.
- **Fail-Closed Stdin**: Append `< /dev/null` and non-interactive flags.
- **Tool Orthogonality Axiom**: VFS monopoly; diagnostic scripts write to `scratch/`, never inline `python -c`.
