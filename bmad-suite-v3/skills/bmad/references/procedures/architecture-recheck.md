---
name: bmad-architecture-recheck
description: >
  Re-evaluate architecture alignment when boundaries change or repeated failures occur during implementation.
---

# Architecture Recheck Procedure

## Objective
Pause implementation and return to Architect mode when conditions change, to prevent local patching from breaking system architecture.

## Triggers

This procedure is invoked automatically during implementation if ANY of the following occur:
1. A public interface is changed.
2. A new dependency or cross-layer call is introduced.
3. Data ownership, persistence, caching, concurrency, or transaction behavior changes.
4. The implementation materially deviates from the approved plan.
5. The same class of fix or test fails twice consecutively.
6. Tests pass locally but integration obligations remain open.

## Process

1. **Stop Coding**: Do not attempt another local fix.
2. **Analyze the Drift**: 
   - What was the original assumption?
   - What new fact triggered the recheck?
   - Does this new fact violate the architecture contract?
3. **Determine Resolution**:
   - Do we need to update the plan?
   - Do we need to split the task?
   - Is an ADR required?
   - Is the architecture contract stale?
   - Do we need user decision?
4. **Output Verdict**: Output the new Architecture Preflight verdict (PASS/WARN/BLOCK/UNKNOWN).

If the new verdict is **BLOCK**, you must switch to the `correct-course` procedure.
