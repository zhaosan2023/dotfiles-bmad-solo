# ANALYSIS-20260912-Git-Branch-Tag-Versioning

## 1. 现状解构：为什么 GitHub 上分支和 Tag 会让人困惑？

### 1.1 Git Commit 图谱全貌
```text
* 009444b (HEAD -> main, origin/main) docs: update copyright holder in LICENSE to zhaosan2023 [当前 V4]
* fe94ed2 docs: add MIT license and ana-solo license selection analysis [引入 V4 & V3 目录]
* 27998e3 feat(bmad-solo): implement findings routing strategy (Option C)
* 2972319 (v3-agaels) feat: upgrade to BMAD-Solo V3 (AGAEL/AGAS) architecture loop [V3 历史节点]
* 099a498 (tag: v2.0.0, origin/v2-stable, v2-stable) feat: migrate to Plugin architecture (V2) [V2 历史节点]
* 7a59b19 (tag: v1.0.0-skill-based) chore: backup before plugin refactoring [V1 历史节点]
```

### 1.2 为什么 GitHub 界面会显示成截图那样？
1. **分支视角（Screenshot 1）**：
   - `main`：是 GitHub 的默认分支（Default branch），当前代码实际上已经包含了 V4（`bmad-suite-v4` 并且 `bs.sh` 默认安装 V4）。
   - `v2-stable`：过去在完成 V2 插件架构迁移（`099a498`）时，创建并推送了这个分支。因为远程分支存在，GitHub 将其识别为 `Active branches`。
   - **缺失点**：V3 发布时仅在本地建了 `v3-agaels`，未推送到远程，也未创建类似 `v3-stable` 的分支。
2. **Tag/Release 视角（Screenshot 2）**：
   - 只有 `v1.0.0-skill-based` 和 `v2.0.0`。
   - **缺失点**：从 `099a498` 演进到 V3 (`2972319`) 和 V4 (`009444b`) 时，**没有在 Git 中打上对应的 Release Tag**。因此在 GitHub 的 Releases/Tags 页面看起来项目停滞在 V2。

---

## 2. 4 Anti-Paralysis Locks（收敛锁）

- **Lock 1 (Non-Goals Lock)**:
  - Non-Goal 1: 不重写已有的 Git 历史（保持 commit sha 稳定性）。
  - Non-Goal 2: 不删除现有代码仓库中的向后兼容目录（`bmad-suite-v3` 继续作为备用保留在主分支）。
  - Non-Goal 3: 不引入复杂的 Git-Flow / 多人协作冲突机制（当前为 dotfiles/solo 单人高效演进模式）。
- **Lock 2 (Hard Gates Cut)**:
  - 必须确保 `main` 分支在克隆后开箱即用就是 V4。
  - 必须让任何人浏览 GitHub Releases/Tags 时能明确看到 V3 和 V4 的发布版本。
- **Lock 3 (Novelty Exhaustion)**:
  - 分支和标签的语义已明确，不再做过度架构设计，聚焦版本对齐。
- **Lock 4 (Minimal Sufficient Verdict)**:
  - 评定为 `FEASIBLE`。

---

## 3. 方案选型矩阵（Decision Matrix）

用户诉求：**主版本为 V4，V3 与 V2 作为遗留历史版本**。

| 方案 | 分支结构 | Tag 标记 | 维护成本 | GitHub 视觉清晰度 | 结论 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **方案 A：单主干 + 全版本 Tag 归档（推荐）** | 仅保留 `main` 作为活动主分支，清理或保留 `v2-stable` | `v1.0.0`, `v2.0.0`, `v3.0.0`, `v4.0.0` | 极低（只需维护 main） | ★★★★★ (Releases 极为清晰) | **最优选** |
| **方案 B：多 stable 分支维护** | `main`(V4), `v3-stable`, `v2-stable` | `v1.0.0`, `v2.0.0`, `v3.0.0`, `v4.0.0` | 中等（需维护多个 stable 分支） | ★★★☆☆ (分支列表繁杂) | 次选 |

### 核心建议（方案 A+B 渐进式）：
1. **立即补齐 Release Tags**：
   - 在 Commit `2972319` 打 Tag `v3.0.0`，标注为 `BMAD-Solo V3 (AGAEL/AGAS Baseline)`。
   - 在当前 HEAD (`009444b`) 打 Tag `v4.0.0`，标注为 `BMAD-Solo V4 (Analyst Closed-Loop + /ana-solo)`。
2. **分支对齐**：
   - 保持 `main` 为默认分支（当前激活的主版本 V4）。
   - 如果希望保留 V3 的分支镜像，可将本地 `v3-agaels` 推送为 `origin/v3-stable`；或者只保留 Tag，删除冗余分支以保持 GitHub 界面清爽。

---

## 4. 结论与执行动作（Verdict & Action Plan）

- **裁决状态**: `FEASIBLE`
- **执行命令集**:
  ```bash
  # 1. 给 V3 历史节点打 Tag 并推送到 GitHub
  git tag -a v3.0.0 2972319 -m "release: BMAD-Solo V3 (AGAEL/AGAS Architecture Loop)"
  git push origin v3.0.0

  # 2. 给当前 V4 主版本打 Tag 并推送到 GitHub
  git tag -a v4.0.0 009444b -m "release: BMAD-Solo V4 (Analyst Closed-Loop Gate + /ana-solo)"
  git push origin v4.0.0

  # 3. (可选) 推送 v3-stable 历史分支，与 v2-stable 保持对称
  git branch v3-stable 2972319
  git push origin v3-stable
  ```

### Handoff to /bmad-solo
Ready for branch & tag reconciliation execution.
