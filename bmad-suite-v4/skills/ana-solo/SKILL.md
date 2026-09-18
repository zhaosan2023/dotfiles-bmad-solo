---
name: ana-solo
description: >
  BMAD-Solo Dedicated Deep Analysis Channel (V4.2).
  Synthesizes Mary (strategic analyst), Keshav Three-Pass (divergent deconstruction),
  and Deep Recon (convergent evidence & requirement matching) with 4 anti-paralysis locks,
  first-class ADR lifecycle, and dual-mode triviality filtering.
  Use via /ana-solo when deep evaluation, literature deconstruction, or multi-option
  selection is required before committing to architecture and code.
---

# /ana-solo: BMAD Dedicated Deep Analysis Channel (V4.2)

## Objective

Deliver decision-grade, deeply grounded analysis without succumbing to endless optimization loops or shallow summaries. 

`/ana-solo` is an explicit, high-intensity analysis channel. It transforms complex inputs (academic papers, RFCs, architectural proposals, competing technology stacks) into **crystallized, actionable verdicts and staged implementation plans** that hand off directly to `/bmad-solo` for implementation with zero hallucination.

## Analytical Engine: Tri-Fold Synthesis

```
  ┌────────────────────────────────────────────────────────┐
  │                 Mary Strategic Persona                 │
  │     (Porter Strategic Rigor + Minto Pyramid Principle) │
  └──────────────────────────┬─────────────────────────────┘
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │         Keshav Three-Pass Reading (Divergent)          │
  │  Pass 1: 5C Baseline  •  Pass 2: Causal & Evidence     │
  │  Pass 3: Virtual Re-Implementation & Implicit Pitfalls │
  └──────────────────────────┬─────────────────────────────┘
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │         Deep Recon Decision Engine (Convergent)        │
  │  Evidence Firewall  •  Requirements Frame              │
  │  Hard Gates Screening  •  Decision Scoring Matrix      │
  └──────────────────────────┬─────────────────────────────┘
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │               The 4 Anti-Paralysis Locks               │
  │  Non-Goals Lock  •  Hard Gates Cut                     │
  │  Novelty Exhaustion Stop  •  Minimal Sufficient Verdict│
  └────────────────────────────────────────────────────────┘
```

---

## 1. Triviality Filter: Dual-Mode Routing (防文件堆积与噪音污染)

When `/ana-solo` is invoked, it MUST first classify the request before creating any files:

### Type A: Ephemeral Mode (咨询、探查、日常协同与临时排查)
- **触发场景**：代码解释、日志临时排查、环境状态查看、Git 协同提问、参数微调咨询。
- **行为规范**：
  - **绝对严禁** 在 `_bmad-output/analysis/` 或 `_bmad-output/adrs/` 生成任何持久化 Markdown 文件！
  - 运算与排查依托对话流或临时草稿区 (`<appDataDir>/brain/<conversation-id>/scratch/`)。
  - **零文件污染**，防止零碎咨询稀释或污染工程记忆。

### Type B: Persistent Mode (重大方案解构、跨组件设计、算法策略、技术选型)
- **触发场景**：新模块设计、算法拟合、技术选型、重大重构、文献解构。
- **行为规范**：执行完整分析流程，受控产出结构化 ADR 与暂存计划（见下文）。

---

## 2. Supported Analysis Shapes (Type B)

1. **Shape 1: Proposal & Paper Deep Deconstruction**
   - *Use when*: Evaluating an academic paper, whitepaper, complex RFC, or proposed architecture redesign.
   - *Reference*: `references/paper-reading-guide.md` and `../bmad/references/procedures/three-pass-analysis.md`.
   - *Flow*: 5C qualitative scan → causal evidence verification → virtual re-implementation stress test → top-3 failure modes.

2. **Shape 2: Candidate Selection & Decision Matrix (Select Shape)**
   - *Use when*: Choosing between 2–5 competing technologies, databases, frameworks, or architectural approaches.
   - *Reference*: `references/decision-matrix.md`.
   - *Flow*: Requirements framing (hard gates vs. preferences) → candidate screening (cut non-qualifiers) → criteria scoring → winner pick + runner-up + reversibility hedge.

3. **Shape 3: Requirement Discovery & Scope Elicitation (Deep Recon)**
   - *Use when*: Facing vague, contradictory, or complex business/technical needs.
   - *Reference*: `references/convergence-locks.md`.
   - *Flow*: Evidence grounding → stakeholder voice isolation → mandatory Non-Goals definition → minimal viable boundary.

---

## 3. The 4 Anti-Paralysis Convergence Locks

Every Type B `/ana-solo` run strictly enforces these 4 stopping gates to prevent infinite discussion:

1. **Lock 1 (Non-Goals Lock)**: Must declare at least 3 explicit `Out-of-Scope` items in the first pass.
2. **Lock 2 (Hard Gates Cut)**: Eliminate any option conflicting with team skills, budget, or timeline immediately.
3. **Lock 3 (Novelty Exhaustion)**: When a round of probing produces no new load-bearing architectural fact, halt analysis immediately.
4. **Lock 4 (Minimal Sufficient Verdict)**: When a solution is deemed `FEASIBLE`, stop seeking perfection. Transition immediately to crystallization.

---

## 4. Architectural Backpressure Valves (前置背压阀门)

Before drafting or finalizing any architectural proposal, `/ana-solo` applies two strict backpressure checks:

1. **Valve 1: Invariant Conflict Backpressure (历史不变量冲突拦截)**:
   - Must inspect `_bmad-output/project-context.md` and existing `ACCEPTED` ADRs.
   - If the new proposal violates an established architectural invariant (e.g., latency budget, data ownership), **halt immediately**. The proposal MUST explicitly declare `SUPERSEDES: ADR-xxx` with justification before proceeding.
2. **Valve 2: Single-Flight Staging Backpressure (单飞挂起拦截)**:
   - Check if an unexecuted `_bmad-output/pending_implementation_plan.md` already exists.
   - If an unexecuted plan is present, warn the user and require explicit confirmation before overwriting, preventing multi-task context drift.

---

## 5. Crystallization & Staging Area (方案结晶与防幻觉交付)

When the analysis reaches a `FEASIBLE` verdict, or when the user issues confirmation (e.g. `方案ok`, `结晶`, `确认执行`):

`/ana-solo` **DOES NOT** expect the user to remember complex paths. It automatically and silently completes the following two-part crystallization:

### Part 1: First-Class ADR Record
Outputs the structured decision record to:
`_bmad-output/adrs/ADR-YYYYMMDD-[topic].md` with initial state:
`Status: PROPOSED`

The ADR must contain:
- Context & Business Driver
- Chosen Decision & Explicitly Rejected Candidates (with rationale)
- Invariants & Guardrails (NFR limits)
- Verification Command (`timeout 30s ...`)
- Traceability metadata (Session ID, Date)

And appends an entry to `_bmad-output/analysis/SESSION-INDEX-ALL-CONVERSATIONS.md`.

### Part 2: Pure Execution Staging Plan
Extracts and writes the zero-fluff, non-speculative plan to:
`_bmad-output/pending_implementation_plan.md`

Must include frontmatter fingerprint for `/bmad-solo` adaptive gating:
```yaml
---
scenario: algo | structural | bugfix | ops
impact_tier: S | M | L
requires_adr: true | false
adr_file: "_bmad-output/adrs/ADR-YYYYMMDD-[topic].md"
verification_type: unit_test | config_syntax | diff_cleanliness
verification_command: "timeout 30s pytest tests/test_xxx.py < /dev/null"
---
```

**CRITICAL RULE 1**: `/ana-solo` is strictly forbidden from directly updating `_bmad-output/project-context.md`. Analysis proposals are never treated as execution ground truth until verified and promoted by `/bmad-solo`.

**CRITICAL RULE 2 (Domain Abstraction & Cross-Project Isolation Axiom)**: When crystallizing an ADR or Pending Plan, the AI MUST strictly abstract away conversational anecdotes, private external project names (e.g. downstream apps discussed in chat), and transient ad-hoc examples into domain-neutral architectural archetypes. The architectural assets of a repository must NEVER leak external client project context!

---

## 6. Terminal Execution Penta-Invariants

Whenever `/ana-solo` executes system exploration, log inspection, or diagnostic commands, it MUST strictly adhere to `bmad-constitution.md` and enforce the five invariants:
1. **Single-Flight Monad Lock**: Never launch a command while any background task is still running.
2. **Universal Bounded Timeout**: Tier 1 (15s probe), Tier 2 (30s verify), Tier 3 (600s build).
3. **Foreground Synchronization Lock**: `WaitMsBeforeAsync: 10000ms`.
4. **Fail-Closed Stdin**: Append `< /dev/null` and non-interactive flags.
5. **Tool Orthogonality Axiom**: VFS monopoly; diagnostic scripts write to `scratch/`, never inline `python -c`.

---

## 7. Handoff to `/bmad-solo`

Upon crystallization, conclude with a clean, one-line handoff:

```markdown
### 方案已结晶并建立背压屏障

- **ADR 提案**: `_bmad-output/adrs/ADR-YYYYMMDD-[topic].md` (PROPOSED)
- **待执行暂存计划**: `_bmad-output/pending_implementation_plan.md` (已绑定验证断言)

直接输入 `/bmad-solo 执行` 即可启动场景自适应带测执行。
```
