# 整合 bmad-solo 统一路由模式实现方案

目标：根据 `docs/bmad-solo-files/skillscomb-fable.md` 的架构设计，消除由于注册了 49 个独立 Skill 而导致的 UI 菜单臃肿，将其降维整合为单一的 `/bmad-solo` 入口技能，并通过底层 `AGENTS.md` 和思考模式 (Product, Architect, Developer, Reviewer, Operator) 自动路由调用所需能力。

## User Review Required

> [!WARNING]  
> 此次变更将移动当前的 49 个 `bmad-*` 技能。这意味着在变更应用后，你的 `/` 快捷命令列表里将只会看到 `/bmad-solo` 这一个核心功能。
> 所有的底层逻辑都会被保留，但需要依赖 AI 在理解你任务上下文的基础上，自动从内部 `procedures` 里读取。

> [!IMPORTANT]  
> 原有的技能不会被直接删除，而是会被移动到备用目录 `_bmad-solo-source/legacy-skills/` 中，方便安全回滚和对比验证。

## Open Questions

无明显阻碍点，不过请确认在 IDE 中是否需要重启窗口 (`Reload Window`) 来彻底刷新 Slash Command 的缓存索引。

## Proposed Changes

我们将执行以下目录结构的重构工作：

### 1. 建立统一路由入口 (bmad-solo)
创建一个包含五大模式参考指南和统一路由规则的核心技能包。
#### [NEW] [SKILL.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/SKILL.md)
#### [NEW] [capability-map.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/capability-map.md)
#### [NEW] [mode-product.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/mode-product.md)
#### [NEW] [mode-architect.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/mode-architect.md)
#### [NEW] [mode-developer.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/mode-developer.md)
#### [NEW] [mode-reviewer.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/mode-reviewer.md)
#### [NEW] [mode-operator.md](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/mode-operator.md)

### 2. 转移和降维原有能力 (Procedures)
将核心的执行流程从独立 Skill 转化为普通的 Markdown 手册，存放在 `procedures` 目录下供 AI 按需加载。
#### [NEW] [procedures](file:///home/veryfd/Project/BMAD-METHOD/.agents/skills/bmad-solo/references/procedures) (目录创建)
- 我们将从现有的 49 个技能中，提取关键能力（如 `bmad-build`, `bmad-architecture`, `bmad-code-review`, `bmad-prd` 等）的核心内容，放入 `procedures` 目录下。

### 3. 备份遗留 Skills
将原 `.agents/skills` 下除 `bmad-solo` 之外的所有 `bmad-*` 目录安全迁移。
#### [NEW] [legacy-skills](file:///home/veryfd/Project/BMAD-METHOD/_bmad-solo-source/legacy-skills/) (目录)

## Verification Plan

### Manual Verification
1. 重启你的 Antigravity IDE (Reload Window)。
2. 在对话框输入 `/` 验证原本 40 多个 `bmad-` 快捷命令是否已经消失，只剩下 `bmad-solo`。
3. 提出一个测试需求（例如："在这个项目中加一个简单的重试函数"），观察系统是否能不提示你手动选工具，而是自动走 `Developer -> Reviewer` 流程，并在后台正确应用 `bmad-build` 相应的规则。