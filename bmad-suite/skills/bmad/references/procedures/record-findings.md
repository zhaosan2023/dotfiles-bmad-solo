---
name: bmad-record-findings
description: >
  Route and persist important findings, lessons learned, and post-incident
  records to the correct BMAD output location.
---

# Record Findings Procedure

## Trigger
- 重大 Bug 修复完成后需要复盘
- 容灾恢复过程结束
- 发现影响架构的关键经验教训
- Operator 模式下的重大排错结论

## Process

1. **分类 Finding**：
   - 是否涉及架构决策或重大技术选型？→ 走 ADR 流程 (`architecture-decision.md`)
   - 是否是对项目全局事实的更新（如新增端口/服务/依赖）？→ 更新 `_bmad-output/project-context.md`
   - 是否仅与当前会话任务相关？→ 记录在 `brain/task.md`
   - 不确定？→ **停下来询问用户**

2. **生成产物**：按分类结果写入对应位置。

3. **提示 /learn**：如果 Finding 对未来所有会话都有价值，并且已经存入 ADR，提示用户："建议使用 `/learn` 将此经验固化为长期知识项 (KI)。"

## 禁止行为
- 不得将 Findings 放入 `docs/` 或项目根目录的任意 `.md` 文件中。
- 不得将具体事件的复盘报告覆盖或冒充 `project-context.md`。
- 不得在不确定归属时自行创建新目录或文件名。
