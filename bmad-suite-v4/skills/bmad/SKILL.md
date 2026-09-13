---
name: bmad-solo
description: >
  BMAD-Solo V4: Architecture-Grounded Engineering Loop with Analyst Closed-Loop Gate.
  Automatically routes software tasks through Analyst, Product, Architect,
  Developer, Reviewer/QA, and Operator modes with architecture
  conflict gates. Use for planning, implementation, review,
  diagnosis, and deployment tasks.
---

# BMAD-Solo V4 Router

## Objective

Complete the user's task through one continuous AI session.
Do not simulate a multi-agent meeting. Do not ask the user to select
an internal BMAD workflow unless a material product decision is required.
The single AI switches thinking modes by task phase, not by keyword alone.

## Architecture-Grounded Routing

1. Read governing rules (`bmad-constitution.md`, `bmad-core.md`),
   verified project context, and current Git state.
2. If `_bmad-output/project-context.md` does not exist:
   silently scan the codebase and note the gap internally.
   Only create it when the first M/L task requires persistent context.
3. Classify the task by **impact scope** and **architecture sensitivity**:
   - **S**: single component, no public interface / dependency / data change.
   - **M**: multi-file, interface change, design choice, or any S that
     fails the fast-path criteria below.
   - **L**: new major module, architecture refactor, migration, security,
     or deployment change.
4. **S fast-path criteria** — all must hold, otherwise auto-upgrade to M:
   - Modifies only one existing component.
   - Does not change a public interface.
   - Does not add cross-layer dependencies.
   - Does not change data ownership.
   - Does not involve caching, transactions, concurrency, or security.
   - Does not alter a performance-critical path.
5. Determine the current phase from task state and missing output.
6. Load only the relevant mode reference (one at a time).
7. Select procedures from `references/capability-map.md`.
8. Execute within the selected mode's boundary.

## Progressive Loading

Do not load every reference. Load one mode and one procedure at a time.

- Analyst: `references/mode-analyst.md`
- Product: `references/mode-product.md`
- Architect: `references/mode-architect.md`
- Developer: `references/mode-developer.md`
- Reviewer/QA: `references/mode-reviewer.md`
- Operator: `references/mode-operator.md`

Load procedures from `references/procedures/` only when needed.

## Task-Level Workflows

### S Tasks

```
Read project context
→ Short plan (in-memory)
→ Developer mode: implement
→ Run narrowest relevant tests
→ Self-review
→ Mark complete
```

### M Tasks

```
Read project context
→ Analyst mode: Deconstruct proposal / scheme (if task introduces design choices or new schemes)
  (references/procedures/three-pass-analysis.md)
→ Product/Architect: clarify goal, non-goals, and constraints
→ Architecture Preflight (references/procedures/architecture-preflight.md)
  → PASS or accepted WARN only
→ Create brain/task.md
→ Generate implementation plan (Epic → Story → Task)
→ WAIT_FOR_PLAN_APPROVAL
→ Developer mode: implement per task, one at a time
  → On recheck trigger → Architecture Recheck
→ Run tests
→ State Reconciliation (references/procedures/state-reconcile.md)
→ Reviewer mode: adversarial review (including architecture dimensions)
→ Mark complete
```

### L Tasks

```
Read project context
→ Analyst mode: Deep 3-pass deconstruction & option matrix (if multi-option/complex scheme)
→ Product: define scope, acceptance criteria, non-goals
→ Architect: establish or verify architecture baseline
  (references/procedures/architecture-baseline.md)
→ Architecture Preflight
  → PASS or accepted WARN only
→ Full spec/architecture definition → _bmad-output/specs/
→ Generate implementation plan (Epic → Story → Task)
→ WAIT_FOR_PLAN_APPROVAL
→ Developer mode: implement per task
  → On recheck trigger → Architecture Recheck
  → On algorithm/NFR task → Algorithm Fit
    (references/procedures/algorithm-fit.md)
→ Per-task verification with evidence
→ State Reconciliation
→ Independent Reviewer: adversarial review + architecture drift check
→ Integration/deployment verification
→ Mark complete
```

## Architecture Control Points

### Before Implementation
Run `architecture-preflight` for all M/L tasks.
S tasks only if fast-path criteria failed.

### During Implementation
Re-run architecture check when any of these occur:
- Public interface changes
- New dependency or cross-layer call introduced
- Data ownership, caching, transaction, or concurrency behavior changes
- Implementation plan materially changes
- Same class of fix fails twice
- Tests pass locally but integration obligations remain open

See `references/procedures/architecture-recheck.md`.

### Before Completion
Run `state-reconcile` for all M/L tasks.
Compare claimed state against actual code and test evidence.

## Completion Gate

A code task is complete only when:

- Acceptance criteria are satisfied.
- Relevant implementation is finished.
- Behavioral verification has real output strictly congruent with modification footprint (or verified clean diff for pure sync tasks).
- Downstream verification locks (Footprint, Affinity, VFS, Minimal Assertion) and Execution Monad invariants hold.
- Applicable architecture invariants have evidence (M/L).
- No blocking architecture conflict remains (M/L).
- Deviations are approved and recorded (M/L).
- Claimed task state matches repository facts (M/L).
- Reviewer/QA has inspected the Diff independently.
- Unverified obligations and residual risks are reported.
