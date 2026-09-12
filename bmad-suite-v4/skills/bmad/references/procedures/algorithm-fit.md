---
name: bmad-algorithm-fit
description: >
  Establish an Algorithm-Architecture Contract for complex tasks.
---

# Algorithm-Architecture Fit Procedure

## Objective
Ensure that non-trivial algorithmic work, performance optimizations, and complex data flows explicitly state their boundaries, budgets, and failure semantics before coding begins.

## Triggers
This procedure is required for tasks involving:
- Search, scheduling, optimization, caching, batch processing, concurrency.
- Tasks explicitly stating complexity or performance improvements.
- Operations that cross component boundaries or affect data consistency.

## Process
1. **Analyze Constraints**: Read the task requirements and project context.
2. **Determine Budgets**: Establish time, space, and I/O budgets for the algorithm.
3. **Determine Semantics**: Define exactness, idempotency, and failure/retry semantics.
4. **Draft Contract**: Create the contract at `_bmad-output/tasks/[TASK-ID]-algorithm-contract.md`.

## Output Template

Ensure the output contract follows `references/contracts/algorithm-contract.template.md` exactly, answering every section. If information is missing to complete the contract, you MUST switch to experiment/spike mode to find the answers. DO NOT begin production implementation with an incomplete algorithm contract.
