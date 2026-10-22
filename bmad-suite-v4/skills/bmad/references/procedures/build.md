---
name: bmad-build
description: >
  Implements code changes following the project's existing architecture,
  patterns and conventions. Self-contained — does not depend on _bmad/scripts
  or external renderers.
---

# Build Procedure

## Prerequisites

- 当前目标、范围、约束、验收与实际授权明确；直接消费明确需求或获准方案，不重复完整分析。
- 按核心场景与阶段契约判断是否需要架构预检和持久计划，不因 M/L 标签机械要求 bugfix 或 ops 重型规划。
- 只读任务不进入本实施循环，不写文件、不运行验证、不转正或归档。必要实验先核对问题、范围、环境前提与验收，不由模式切换自动启动。

## Execution Loop

1. **接管任务**：读取当前绑定计划和已选定的唯一进度入口，定位获准阶段、依赖及全部未完成义务。控制器未覆盖时临时引用平台任务记录与真实回执并披露缺口，不猜测状态文件路径，不另建进度副本。

2. **Select one task.** Pick the smallest open task unit. State:
   - Files expected to change.
   - Architecture invariant being preserved.
   - Evidence to produce (test output, lint result, etc.).

3. **实施**：保护用户已有改动，完成最小连贯修改。使用实际授予的原生文件工具；已有文件优先精确补丁，新建或明确完整重写时提交完整正文，不用占位内容覆盖文件。

4. **相关验证**：执行当前阶段必需的最小充分验证，覆盖受影响接口、调用方、所有权与副作用边界，不仅限被编辑模块，不盲跑全库。属性测试与缺陷回归及必要集成边界互补，不按比例删测。
   - 环境准备与测试分离，缺依赖阻塞，不在测试中隐式联网安装。
   - 获准终端串行、前台同步、封闭输入；探测、验证、构建分别采用 15 秒、30 秒、600 秒进程级超时，必要强杀宽限期明确，收到真实退出结果后才推进。
   - 非零退出、超时、取消、零命中、必需项跳过、缺证据或清理未知不通过。普通失败可在当前权限与预算内修复，不降低断言，不推进依赖；空输出按操作的必需证据判断。

5. **Record evidence.** Note actual command output. Do not claim tests
   passed without running them.

6. **Check recheck triggers.** If any of these occurred during this step,
   pause and run Architecture Recheck before continuing:
   - Public interface changed.
   - New cross-layer dependency introduced.
   - Data ownership, caching, transaction, or concurrency changed.
   - Implementation plan materially deviated.
   - Same class of fix failed twice.

7. **更新唯一进度入口**：只有当前任务单元全部必需验收通过，才依据真实回执登记完成，保留发现、风险与全部未完成事项。保存进度不触发业务重测，不把日志保存成功当作业务通过；跨会话产物按职责与实际授权路由，不自动转正、登记事实或归档。

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
