---
name: bmad-solo
description: >
  Automatically routes software tasks through Product, Architect,
  Developer, Reviewer/QA, and Operator modes. Use for non-trivial
  planning, implementation, review, diagnosis, and deployment tasks.
---

# BMAD-Solo Router

## Objective

Complete the user's task through one continuous AI session.
Do not simulate a multi-agent meeting and do not ask the user to select
an internal BMAD workflow unless a material product decision is required.

## Routing

1. Read project rules and verified project context.
2. Classify the task as S, M, or L.
3. Determine the current phase from task state and missing output.
4. Load only the relevant mode reference.
5. Select procedures from `references/capability-map.md`.
6. Execute within the selected mode's boundary.
7. After implementation, switch to Reviewer/QA.
8. Enter Operator only when runtime work is needed.
9. Respect all confirmation and safety boundaries.

## Progressive loading

Do not load every reference.

- Product: `references/mode-product.md`
- Architect: `references/mode-architect.md`
- Developer: `references/mode-developer.md`
- Reviewer/QA: `references/mode-reviewer.md`
- Operator: `references/mode-operator.md`

Load one procedure at a time from `references/procedures/`.

## Completion gate

A code task is complete only when:

- relevant implementation is finished;
- Diff has been reviewed;
- relevant verification has real output;
- acceptance criteria are checked;
- unverified items and risks are reported.
