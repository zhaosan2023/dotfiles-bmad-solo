---
name: bmad-correct-course
description: >
  Resolution process for blocking architecture conflicts and architecture drift.
---

# Correct Course Procedure

## Objective
Resolve situations where implementation is blocked by a hard architecture conflict, or where architecture drift has been detected.

## Process

When triggered by a BLOCK verdict or ARCHITECTURE_DRIFT:

1. **Analyze the Block**: What specifically is the implementation trying to do that the architecture forbids?
2. **Evaluate Options**:
   - **Option A (Modify Implementation)**: Can the same goal be achieved without violating the invariant?
   - **Option B (Split Task)**: Is the task too large? Can we split off the conflicting part?
   - **Option C (Update Architecture)**: Is the invariant outdated or overly restrictive? Can we write an ADR to change it?
3. **Decision**: Choose the best option.
   - If Option A: Update the implementation plan and re-run preflight.
   - If Option B: Re-plan the stories/tasks.
   - If Option C: Trigger `architecture-decision` to draft the ADR, OR ask the user for explicit permission to change the invariant.

**Crucial Rule**: You CANNOT silently ignore the block. You CANNOT silently change a block-level invariant without user approval or an explicit ADR.
