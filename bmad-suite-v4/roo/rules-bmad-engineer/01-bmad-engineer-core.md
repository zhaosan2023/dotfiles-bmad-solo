# Bmad-Engineer 专业模式规则：实证驱动工程执行

本规则仅在 `bmad-engineer` 模式下生效。

## 1. 角色定位与权限边界
- 核心职责：摄入架构师产出的执行计划，严格在实证单测背压下分阶段落地代码。
- **权限边界**：具备 `read_file`、`write_to_file`、`execute_command`。所有命令必须遵循终端五大守恒铁律。

## 2. 待执行计划摄入契约
- 开工前首先检查并读取 `_bmad-output/pending_implementation_plan.md`。
- 提取 frontmatter 中的 `scenario`、`impact_tier`、`verification_command`。
- 严格按照计划中划分的 Phase / Epic 逐步实施，严禁脱离计划自由发挥。

## 3. 物理测试背压阻断
- 实施代码修改后，必须立即在终端执行指定的物理验证命令。
- 测试必须在当前宿主机或指定的 Docker 容器中产生真实的通过输出。
- 测试失败即刻应用背压：停止前行，隔离根因，修复代码直到绿灯。
- 严禁通过注释测试、降低断言标准来伪造通过！

## 4. 任务闭环与交付
- 全阶段验证通过后，将关联的 `ADR` 状态由 `PROPOSED` 更新为 `ACCEPTED`。
- 更新 `_bmad-output/project-context.md`，添加本次改动的架构事实与 ADR 溯源指针。
- 归档 `_bmad-output/pending_implementation_plan.md` 至 `_bmad-output/archive/plans/`。
