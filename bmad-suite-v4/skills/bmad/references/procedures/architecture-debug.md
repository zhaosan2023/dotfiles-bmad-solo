---
name: bmad-architecture-debug
description: >
  Architecture-aware debugging procedure. Prevents endless local patching by returning to root causes.
---

# Architecture Debug Procedure

## Objective
Shift debugging from "modify the line that threw the error" to "locate the broken contract". This prevents local patches from violating system architecture.

## Process

1. **Observe Symptoms**: Document exactly what is failing (with actual logs/output).
2. **Identify Broken Contract**: Which external behavior contract is being violated?
3. **Identify Relevant Invariant**: Which architectural invariant from the contract governs this area?
4. **Hypothesize**: Propose at least TWO falsifiable hypotheses for the root cause.
5. **Experiment**: Run minimal distinguishing experiments to eliminate hypotheses.
6. **Classify**: Categorize the failure as one of:
   - Local implementation defect
   - Interface contract conflict
   - Data ownership error
   - Algorithm assumption error
   - Stale architecture contract
   - Requirement vs. Architecture conflict
7. **Action**: Only proceed with a local fix if it is classified as a "Local implementation defect". Otherwise, trigger `correct-course`.

## Output Format (Hypothesis Log)

For each hypothesis:
```markdown
## Hypothesis H-[N]
- **Observation**:
- **Expected architectural behavior**:
- **Suspected violation**:
- **Falsification test**:
- **Actual result**:
- **Status**: [supported | rejected | unresolved]
- **Next action**:
```
