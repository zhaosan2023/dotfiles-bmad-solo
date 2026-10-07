# BMAD-Solo 敏捷工程循环与自适应安全阀 (Core Methodology)

本文件定义 BMAD-Solo 的核心工程循环与实证背压机制。

## 1. 全局会话静默嗅探
启动任务前静默执行：
1. 嗅探 `_bmad-output/project-context.md` 作为项目架构基线。
2. 嗅探 Git 状态 (`git status --short`)，保护既有未提交代码。
3. 检查暂存区 `_bmad-output/pending_implementation_plan.md`，若存在则作为首要执行契约。

## 2. 4 大场景自适应安全阀 (Scenario-Adaptive Gating)
根据任务类型动态加载对应流程，坚决杜绝形式主义卡死：
- **场景 1: 算法与高能计算型 (`algo`)**：
  强制挂载算法适配检查 (NFR 延迟与内存上限)、架构预检、Epic 物理单测硬门禁、状态对账与 ADR 转正。
- **场景 2: 系统结构与重构型 (`structural`)**：
  跳过算法检查，挂载架构预检、Epic 物理单测硬门禁、状态对账与 ADR 转正。
- **场景 3: 局部缺陷修复型 (`bugfix`)**：
  跳过架构门禁与重型流程，严格执行足迹全等单测 (仅跑改动相关测试)，不建立/不转正 ADR，极速闭环。
- **场景 4: 运维协同与配置型 (`ops`)**：
  严禁运行业务单测！以 Git Diff 洁净度与配置文件语法校验为最小充分通过证据。

## 3. Epic 级物理单测背压阀门 (Physical Test Barrier)
- 实施阶段分 Phase / Epic 逐步推进。
- 每个阶段必须执行指定的物理验证命令 (`timeout 30s <test_cmd> < /dev/null`)。
- **测试红灯时立即停止推进**，原地隔离并修复，严禁在测试失败时声称任务完成。
- 测试绿灯后方可推进下一阶段。

## 4. 完工对账与闭环 (Completion Gate)
- 代码改动、物理测试输出与架构边界三方对账。
- 若涉及 ADR，将状态从 `PROPOSED` 晋升为 `ACCEPTED`。
- 将新增架构事实与溯源指针写入 `_bmad-output/project-context.md`。
- 清理归档 `_bmad-output/pending_implementation_plan.md`。
