# ADR-20260918-bmad-v42-adaptive-backpressure-and-adr-governance: BMAD-Solo V4.2 场景自适应背压与 ADR 治理架构

- **Status**: PROPOSED
- **Session ID**: `892c0a41-bc8b-4af4-a8c6-e2dd0a979660`
- **Date**: 2026-09-18
- **Decision Owner**: `/ana-solo`
- **Topic**: 架构收敛治理、防任务幻觉、消除分析碎片、自适应门禁与实证背压

---

## 1. Context (背景与业务动力)

在既有 BMAD-Solo 与 `/ana-solo` 的长期运行中暴露了三大致命隐患：
1. **分析文件爆炸（Sprawl）**：频繁的日常咨询与轻量分析无序落盘了 20+ 个 `ANALYSIS-*.md` 碎片文件，缺乏统一收敛枢纽。
2. **执行期任务幻觉（Hallucination）**：`/bmad-solo` 直接以杂乱的聊天流或草稿为依据，在下游复杂计算与算法型项目中极易虚构并不存在的任务和过拟合策略。
3. **僵化流水线与形式主义卡死**：一刀切的硬编码线性流水线试图对任何任务强推算法审查和单测阻断，导致小 Bug 修复与 GitOps 同步任务被假门禁卡死。
4. **轻量模型不建 Plan**：Gemini 3.8 Flash 等弱约束模型习惯于直接对话输出，忽略调用原生工具建立跟踪计划。

---

## 2. Decision & Rejected Candidates (决策与否决候选)

### 选定决策 (Chosen Decision)
建立 **BMAD-Solo V4.2 架构治理闭环体系**：
1. **瞬态与持久双模分流 (Dual-Mode Triviality Filter)**：
   - Type A 咨询/排查走 Ephemeral 模式，严禁落盘任何文件（0 污染）。
   - Type B 重大方案结晶输出一流公民 ADR 与 `pending_implementation_plan.md`。
2. **前置双背压阀门 (Dual Pre-Backpressure Valves)**：
   - 阀门 1（历史不变量冲突拦截）：必须比对 `project-context.md` 中已 Accepted 的 ADR，冲突则阻断，必须显式 `SUPERSEDES`。
   - 阀门 2（单飞挂起拦截）：存在未执行的暂存计划时熔断，防止并发任务漂移。
3. **4 大场景自适应动态安全阀 (Adaptive Gating Engine)**：
   - `algo`（算法高能）：强锁 `algorithm-fit.md` + 延迟预算 + Epic 物理单测阻断 + State-Reconcile。
   - `structural`（架构解耦）：强锁 `architecture-preflight.md` + Epic 物理单测阻断 + State-Reconcile。
   - `bugfix`（缺陷修复）：跳过重型架构门禁，实行精准足迹单测，零 ADR 污染。
   - `ops`（运维协同）：严禁盲测，纯 Git Diff 洁净度审查。
4. **实证背压裁决 (Empirical Gate)**：
   - ADR 转正为 `ACCEPTED` 的唯一标准是物理测试全绿，由编译器/解释器充当最终法官，消除人类肉眼审查 ADR 的心智负担。
5. **跨模型计划锁 (Artifact Monad Lock)**：
   - 强制调用 `write_to_file` 建立 `brain/implementation_plan.md` 与 `brain/task.md`。

### 明确否决的候选方案 (Rejected Candidates)
- **Candidate 1: 单一白板覆写模式 (Single Active Workspace Overwrite)**
  - *否决原因*：当并发发生中断或多主题切换时，单一白板会被直接冲刷覆盖，导致历史推演不可逆丢失，或拼接产生更严重的任务幻觉。
- **Candidate 2: 僵化全量线性流水线 (Monolithic Rigid Cascade)**
  - *否决原因*：改注释跑 Preflight、改配置做 Algorithm-Fit、无测试任务硬推单测阻断，必然导致系统卡死或 AI 被迫伪造测试。
- **Candidate 3: 分析阶段直接写入 project-context.md**
  - *否决原因*：分析角色写入未经验证的猜想，会严重污染执行层的绝对真理基线。

---

## 3. Invariants & Guardrails (核心架构不变量与边界)

1. **真理隔离公理**：`project-context.md` 永远只能记录确定性被执行落地的真实事实，`/ana-solo` 绝不可直接修改。
2. **暂存区垄断公理**：`/bmad-solo` 执行时，必须优先以 `_bmad-output/pending_implementation_plan.md` 为唯一可信契约。
3. **足迹全等公理**：严禁全量测试发现（discover），测试范围严格全等于 Diff 足迹。纯运维协同任务单元测试集合为空集 $\emptyset$。
4. **物理镜像单一事实源**：修改仅在 `bmad-suite-v4` 中进行，通过 `./bs.sh` 同步至宿主机全局 runtime。

---

## 4. Verification Evidence (实证测试闭环)

- **Verification Command**:
  `timeout 30s python3 bmad-suite-v4/skills/bmad/scripts/validate-solo-package.py < /dev/null`
  `timeout 30s ./bs.sh v4 < /dev/null`
- **Pass Threshold**: Package self-contained validation Exit Code 0, Mirror deploy manifest matches local HEAD.
