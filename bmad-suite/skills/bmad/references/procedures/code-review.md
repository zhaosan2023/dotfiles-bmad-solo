---
name: bmad-code-review
description: >
  Adversarial code review with architecture awareness.
  Self-contained — no external script, renderer, or step-file
  dependencies required.
---

# Code Review Procedure

## Objective

Review code changes adversarially. The Reviewer's stance is the
opposite of the Developer's. Do not defend the implementation;
find what is wrong, missing, or fragile.

## Inputs

Read only these sources (do NOT read the Developer's process narrative):

1. User requirements and acceptance criteria.
2. Git Diff of the changes.
3. Test and verification evidence (actual terminal output).
4. Architecture contract (if exists): `_bmad-output/architecture/architecture-contract.yaml`.
5. Implementation plan: `brain/implementation_plan.md`.
6. Active task state: `brain/task.md`.

## Review Checklist

### Correctness
- [ ] Does the code implement what was requested?
- [ ] Are edge cases and error paths handled?
- [ ] Are there off-by-one, null, or type errors?
- [ ] Does the logic match the stated acceptance criteria?

### Testing
- [ ] Were tests actually run (real terminal output exists)?
- [ ] Do tests cover the changed behavior?
- [ ] Are there missing test cases for boundary conditions?
- [ ] Is any test modified to hide a real defect?

### Architecture (M/L tasks)
- [ ] Is the code implemented in the correct component?
- [ ] Are there undeclared new dependencies?
- [ ] Is data written by the correct owner?
- [ ] Are public interfaces changed without approval/ADR?
- [ ] Are dependency directions preserved?
- [ ] Is a local-only result being claimed as system-verified?
- [ ] Has the architecture contract drifted from actual code?

### Security
- [ ] Are there hardcoded secrets, tokens, or credentials?
- [ ] Are user inputs validated and sanitized?
- [ ] Are permissions and access controls correct?

### Maintainability
- [ ] Is the code readable and well-structured?
- [ ] Are existing patterns and conventions followed?
- [ ] Is there unnecessary complexity or over-engineering?
- [ ] Are comments and documentation accurate?

## Verdict

Output one of:

| Verdict | Meaning |
|---|---|
| **APPROVE** | All checks pass, no issues found. |
| **APPROVE_WITH_DEBT** | Minor issues recorded as tech debt, acceptable to merge. |
| **CHANGES_REQUIRED** | Issues must be fixed before completion. |
| **ARCHITECTURE_DECISION_REQUIRED** | Architecture conflict found, needs ADR or user decision. |
| **INSUFFICIENT_EVIDENCE** | Cannot determine correctness — tests missing, no output, or scope unclear. |

## Rules

- Test passing is NOT the end condition for review.
- Do not re-summarize the Developer's explanation as your own finding.
- If claims contradict evidence, flag the contradiction explicitly.
- Debugging findings discovered during review must be recorded.
- For M/L tasks, verify that State Reconciliation was performed.
