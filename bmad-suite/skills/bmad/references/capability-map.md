# BMAD-Solo Capability Map

> Only reference procedures that exist in `procedures/`.
> Capabilities marked `[Commit 2]` or `[Commit 3]` will be added in future commits.

## Active Capabilities

| Capability | Mode | Trigger | Procedure | Required Output |
|---|---|---|---|---|
| architecture-decision | Architect | 存在多个重大技术方案 | procedures/architecture-decision.md | ADR |
| build | Developer | 约束与计划已充分 | procedures/build.md | Code + Tests |
| code-review | Reviewer | 出现代码 Diff | procedures/code-review.md | Review findings |
| architecture-baseline | Architect | 缺少或架构状态陈旧 | procedures/architecture-baseline.md | Architecture Contract |
| architecture-preflight | Architect | 所有 M/L 编码任务 | procedures/architecture-preflight.md | PASS/WARN/BLOCK/UNKNOWN |
| architecture-recheck | Architect | 关键变更或重复失败 | procedures/architecture-recheck.md | Updated verdict |
| state-reconcile | Reviewer | 完成前 | procedures/state-reconcile.md | Consistency verdict |
| algorithm-fit | Architect | 算法或 NFR 敏感任务 | procedures/algorithm-fit.md | Algorithm Contract |
| architecture-debug | Architect/Developer | 重复失败或跨边界修复 | procedures/architecture-debug.md | Hypothesis log + decision |
| correct-course | Architect/Product | BLOCK 或架构漂移 | procedures/correct-course.md | ADR、拆分或升级决定 |
| record-findings | Reviewer/Operator | 重大 Bug 修复完成、容灾恢复或关键经验教训 | procedures/record-findings.md | ADR, project-context 更新, 或 KI |
