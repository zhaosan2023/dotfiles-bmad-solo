---
name: ana-solo
description: >
  BMAD-Solo Dedicated Deep Analysis Channel (V4).
  Synthesizes Mary (strategic analyst), Keshav Three-Pass (divergent deconstruction),
  and Deep Recon (convergent evidence & requirement matching) with 4 anti-paralysis locks.
  Use via /ana-solo when deep evaluation, literature deconstruction, or multi-option
  selection is required before committing to architecture and code.
---

# /ana-solo: BMAD Dedicated Deep Analysis Channel

## Objective

Deliver decision-grade, deeply grounded analysis without succumbing to endless optimization loops or shallow summaries. 

`/ana-solo` is an explicit, high-intensity analysis channel. It transforms complex inputs (academic papers, RFCs, architectural proposals, competing technology stacks) into **converged, actionable verdicts** that hand off directly to `/bmad-solo` for implementation.

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

## Supported Analysis Shapes

When invoked, `/ana-solo` identifies or asks for the user's intent:

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

## The 4 Anti-Paralysis Convergence Locks

Every `/ana-solo` run strictly enforces these 4 stopping gates to prevent infinite discussion:

1. **Lock 1 (Non-Goals Lock)**: Must declare at least 3 explicit `Out-of-Scope` items in the first pass.
2. **Lock 2 (Hard Gates Cut)**: Eliminate any option conflicting with team skills, budget, or timeline immediately.
3. **Lock 3 (Novelty Exhaustion)**: When a round of probing produces no new load-bearing architectural fact, halt analysis immediately.
4. **Lock 4 (Minimal Sufficient Verdict)**: When a solution is deemed `FEASIBLE`, stop seeking perfection. Transition immediately to `/bmad-solo`.

---

## Terminal Execution Penta-Invariants (Anti-Hang & Single-Flight Shield)

Whenever `/ana-solo` executes system exploration, log inspection, or diagnostic commands, it MUST strictly adhere to `bmad-constitution.md` and enforce the following five invariants without exception:

1. **Single-Flight Monad Lock (单飞排队强锁)**:
   - **Strictly Forbidden**: NEVER launch a new `run_command` while ANY background task is still running or uncollected.
   - If a background task is pending, you must wait for its completion callback, monitor it via `manage_task(status)`, or actively terminate it via `manage_task(kill)` before initiating any new command. Zero task collisions allowed!
2. **Universal Bounded Timeout (零例外全量超时)**:
   - **Strictly Forbidden**: NEVER execute any naked terminal command. ALL commands (including `docker inspect`, `docker ps`, `git status`, `ls`, etc.) MUST be explicitly prepended with `timeout 15s <cmd>` (or `timeout 30s <cmd>` for heavy database/build tasks). No command is exempt!
3. **Foreground Synchronization Lock (前台同步强锁)**:
   - For all exploratory and diagnostic commands, **`WaitMsBeforeAsync` MUST be set to `10000ms` (10 seconds)**.
   - NEVER use 5000ms or lower for fast inspection tasks to eliminate in-flight event drop deadlocks.
4. **Fail-Closed Stdin (输入封闭公理)**:
   - All terminal commands must append `< /dev/null` and pass non-interactive flags (e.g. `git --no-pager`, `DEBIAN_FRONTEND=noninteractive`).
5. **Tool Orthogonality Axiom (VFS Monopoly / 工具正交公理)**:
   - **Strictly Forbidden**: NEVER write or execute multi-line python code via `python3 -c "..."` in `run_command`.
   - **Strictly Forbidden**: NEVER use shell redirection (`cat << 'EOF'`, `echo >`) to write files.
   - For file reading and inspection, ALWAYS use native tools (`view_file`, `grep_search`).
   - If complex data parsing or database inspection is required, **first write a clean scratch script** to `<appDataDir>/brain/<conversation-id>/scratch/` via `write_to_file`, then execute it cleanly via `timeout 30s python3 scratch/script.py < /dev/null`.

---

## Handoff to `/bmad-solo` (Execution Bridge)

Every completed analysis produces:
1. A persistent report at `_bmad-output/analysis/ANALYSIS-YYYYMMDD-[topic].md`.
2. A clear verdict: `FEASIBLE` | `CONDITIONALLY_FEASIBLE` | `REJECT`.
3. A copy-pasteable execution handoff block:

```markdown
### Handoff to /bmad-solo

To proceed to engineering implementation, simply run `/bmad-solo` with:
"Implement approved proposal from _bmad-output/analysis/ANALYSIS-YYYYMMDD-[topic].md"
```
