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
5. 当前实际绑定的实施计划；明确需求或轻量任务没有计划时不猜测路径、不强制补建。
6. 当前已选定的唯一任务进度入口；控制器未覆盖时临时引用平台任务记录与真实回执，不另建状态副本。

只读审核仅取证与会话交付，不写文件、不运行验证、不转正或归档。差异取证遵循实际工具权限，不为检查 Git 绕过分析角色的终端限制；现有真实回执可供审查，不能由审核自动启动测试。

## Review Checklist

### Correctness
- [ ] Does the code implement what was requested?
- [ ] Are edge cases and error paths handled?
- [ ] Are there off-by-one, null, or type errors?
- [ ] Does the logic match the stated acceptance criteria?

### Testing
- [ ] 需要验证的实施任务是否取得当前阶段的真实回执？只读审核不因此强制运行测试，历史通过不替代受影响证据。
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
- 审核发现随当前交付保留；需要持久化时按实际授权和产物职责路由，只读审核不写文件，不另建进度账本。
- 按当前阶段契约核对实现、证据与未完成义务；缺必需证据不登记完成，条件接受不能豁免必需验收，阶段交付不等于全计划完成。
