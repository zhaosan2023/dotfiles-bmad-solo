---
name: bmad-build
description: >
  Implements code changes following the project's existing architecture,
  patterns and conventions. Self-contained — does not depend on _bmad/scripts
  or external renderers.
---

# Build Procedure

## Prerequisites

- Task goal and constraints are understood.
- For M/L tasks: Architecture Preflight verdict is PASS or accepted WARN.
- For M/L tasks: Implementation plan exists and is approved.

## Execution Loop

1. **Load task state.** Read `brain/task.md` (if exists) and the current
   implementation plan. Identify the next open task or obligation.

2. **Select one task.** Pick the smallest open task unit. State:
   - Files expected to change.
   - Architecture invariant being preserved.
   - Evidence to produce (test output, lint result, etc.).

3. **Implement.** Make the smallest coherent code change that completes
   this task unit. Follow zero-fragment strategy — output complete files,
   not snippets.

4. **Verify.** Run the narrowest relevant verification:
   - Unit tests for the changed module.
   - Lint / type check if applicable.
   - Build check if structural changes were made.

5. **Record evidence.** Note actual command output. Do not claim tests
   passed without running them.

6. **Check recheck triggers.** If any of these occurred during this step,
   pause and run Architecture Recheck before continuing:
   - Public interface changed.
   - New cross-layer dependency introduced.
   - Data ownership, caching, transaction, or concurrency changed.
   - Implementation plan materially deviated.
   - Same class of fix failed twice.

7. **Update task state.** Mark the current task unit as complete in
   `brain/task.md`. Record any new findings or risks in `brain/task.md`.
   If findings represent cross-session architectural lessons, trigger
   `record-findings` per the Output Routing table in `bmad-core.md`.

8. **Continue or return.** If more task units remain and no recheck
   triggered, go to step 2. Otherwise, return to the router for
   State Reconciliation and Review.

## Constraints

- Do not implement the entire plan in one pass then check architecture.
- Do not bypass existing interfaces to make tests pass.
- Do not record unexecuted tests as verification evidence.
- Do not lower acceptance criteria during implementation.
- Do not modify architecture contracts to unblock your own code.
- If the plan becomes infeasible, stop and return to Architect mode.
