# BMAD-Solo Capability Map

| Capability | Mode | Trigger condition | Procedure | Required output |
|---|---|---|---|---|
| clarify-requirements | Product | 验收标准不明确 | procedures/clarify-requirements.md | Acceptance Criteria |
| create-product-brief | Product | 新产品或大功能 | procedures/create-product-brief.md | Product Brief |
| architecture-decision | Architect | 存在多个重大技术方案 | procedures/architecture-decision.md | ADR |
| implementation-plan | Architect | M/L 级任务准备实现 | procedures/implementation-plan.md | brain/implementation_plan.md |
| build | Developer | 约束与计划已充分 | procedures/build.md | Code + Tests |
| code-review | Reviewer | 出现代码 Diff | procedures/code-review.md | Review findings |
| test-design | Reviewer | 高风险或复杂行为 | procedures/test-design.md | Test matrix |
| diagnose-runtime | Operator | 服务异常或用户要求查日志 | procedures/diagnose-runtime.md | Diagnosis |
| deploy | Operator | 用户明确授权部署 | procedures/deploy.md | Deployment evidence |
