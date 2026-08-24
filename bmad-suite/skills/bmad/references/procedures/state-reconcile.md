---
name: bmad-state-reconcile
description: >
  Reconcile claimed task state against actual code and verification evidence before declaring completion.
---

# State Reconciliation Procedure

## Objective
Prevent false completion by ensuring that the AI's claimed state matches the actual repository reality. This is mandatory before marking an M/L task as complete.

## Process

1. **Gather Evidence**: 
   - Read the user's original goal and acceptance criteria.
   - Read the active task state claims (`brain/task.md`).
   - Read the Architecture Contract.
   - Read the Git Diff.
   - Read actual terminal output from tests and verification steps.

2. **Reconcile**: Compare the claims against the hard evidence.
   - Did the test output actually confirm the claim?
   - Is the change within the approved architectural boundaries?
   - Are there any unapproved deviations?
   - Are all open obligations closed?

3. **Determine Verdict**:

Output ONE of the following verdicts:

- **CONSISTENT**: Code, tests, and architecture are in perfect alignment. Safe to complete.
- **CONDITIONALLY_CONSISTENT**: Minor tech debt or deferred obligations, but acceptable to complete. List the conditions.
- **STALE_STATE**: The task state or architecture contract is outdated compared to the code. Must be updated.
- **ARCHITECTURE_DRIFT**: The code violates the architecture contract without an approved ADR. **DO NOT COMPLETE.**
- **UNAPPROVED_DEVIATION**: The implementation bypassed interfaces or changed data ownership without approval. **DO NOT COMPLETE.**
- **INSUFFICIENT_EVIDENCE**: Tests were not run, or output is missing. **DO NOT COMPLETE.**

Only `CONSISTENT` or `CONDITIONALLY_CONSISTENT` allows the task to proceed to final completion.
