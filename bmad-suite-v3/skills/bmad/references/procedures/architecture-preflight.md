---
name: bmad-architecture-preflight
description: >
  Evaluate a task against the architecture contract before implementation begins.
---

# Architecture Preflight Procedure

## Objective
Run a conflict gate to ensure a proposed task is architecturally safe to implement. This is a mandatory step before any M/L task coding begins.

## Process

1. **Load Context**: Read the task goal, `_bmad-output/architecture/architecture-contract.yaml` (if exists), and relevant project code.
2. **Analyze Impact**: Determine exactly what the task will touch (components, interfaces, dependencies, data ownership).
3. **Check Invariants**: Compare the impact against the architecture contract.
4. **Determine Verdict**: Output the verdict and required next action.

## Preflight Report Format

Output exactly this structure:

```markdown
## Architecture Preflight

- **Task**: [Task ID/Name]
- **Task Level**: [S/M/L]
- **Architecture Sensitivity**: [A0/A1/A2/A3]
- **Affected Components**: [List]
- **Governing Decisions (ADRs)**: [List]
- **Applicable Invariants**: [List]
- **Conflicts**: [List hard or soft conflicts]
- **Missing Evidence**: [List what is unknown]

### Verdict: [PASS | WARN | BLOCK | UNKNOWN]

**Required Next Action**: [implement | experiment | update plan | create ADR | split task | escalate]
```

## Verdict Rules

- **PASS**: No conflicts found, key assumptions have evidence. Proceed to plan/implement.
- **WARN**: Acceptable architecture debt or risk. Must record mitigation in task state before proceeding.
- **BLOCK**: Violates a hard invariant. **DO NOT BEGIN CODING.** The plan must be modified, an ADR created, or the user asked for a decision.
- **UNKNOWN**: Insufficient evidence to judge. **DO NOT ASSUME PASS.** Run an experiment, spike, or benchmark first.
