# ANALYSIS-20260912-Branch-UX-and-Version-Visibility

## 1. 深度问题诊断（Root Cause Diagnosis）

用户在截图中的疑问：
> "我为什么没有看到任何v4字样的tag, main默认 但我看不到签名不知道它是哪个版本?"

### 1.1 核心原因 1：IDE 弹出的界面是“分支切换器（Checkout Branch）”，并非“Tags 列表”
- 截图中的下拉窗口是 IDE 的 **Git 分支切换菜单**。
- 该菜单的优先级规则是：**只列出本地分支（Local Branches）和远程分支（Remote Branches）**。
- Git 的 Tags（如 `v4.0.0`、`v3.0.0`、`v2.0.0`）默认排在分支列表的最底部，或者只有在搜索框中输入 `v4` 才会过滤显示。

### 1.2 核心原因 2：分支命名的“不对称性认知冲突”（Asymmetric Naming）
当前分支列表呈现如下：
- `main`
- `v3-agaels`
- `v3-stable`
- `v2-stable`

**认知冲突点**：
用户看到 `v2-stable`、`v3-stable` 都在列表中，并且名字里明明白白写着 `v2`、`v3`。然而当前的主版本却叫 `main`，其最新提交说明为 `docs: add git branch and tag versioning analysis`，**没有任何 `v4` 字样**。
这导致用户直觉上产生困惑：“到底哪一个分支是 v4？为什么 v2 和 v3 都有专门的名字，唯独 v4 没有标识？”

---

## 2. 4 Anti-Paralysis Locks（收敛锁）

- **Lock 1 (Non-Goals Lock)**:
  - Non-Goal 1: 不破坏 GitHub 推荐的默认主干名 `main`（继续保持 `main` 为默认分支）。
  - Non-Goal 2: 不修改或删除历史提交历史。
  - Non-Goal 3: 不在每次日常 commit 时都强行打 tag。
- **Lock 2 (Hard Gates Cut)**:
  - 必须在 IDE 分支选择器中能够一眼直接看到 `v4` 相关字样。
  - 必须让仓库根目录具备直观的版本标识（缺少 `README.md` 是一个重要漏洞）。
- **Lock 3 (Novelty Exhaustion)**:
  - 语义对齐已完全收敛，不需要引入复杂发布系统。
- **Lock 4 (Minimal Sufficient Verdict)**:
  - 评定为 `FEASIBLE`。

---

## 3. 改进方案矩阵（Decision Matrix）

| 方案 | 动作 | 效果 | 复杂度 | 推荐度 |
| :--- | :--- | :--- | :--- | :--- |
| **方案 1：创建对称的 `v4-stable` / `v4` 分支（推荐）** | 本地和远程创建 `v4-stable` 分支（指向 `main` 的最新提交） | 在 IDE 分支下拉列表中与 `v2-stable`、`v3-stable` 完全对称，用户一目了然看到 v4 | 极低 | ★★★★★ |
| **方案 2：新增 `README.md` 项目主页** | 在根目录建立 README，写明版本状态表（v4 当前活跃 / v3 历史 / v2 历史） | 进入仓库第一眼就能看到明确的版本定义表格 | 低 | ★★★★★ |
| **方案 3：在 IDE 中搜索验证 Tag** | 仅向用户解释在弹出框中输入 `v4` 可以搜索到 Tag | 治标不治本，分支不对称的心理负担依然存在 | 极低 | ★★☆☆☆ |

---

## 4. 落地建议（Action Plan）

1. **分支对称化**：
   在本地与远程创建 `v4-stable` 分支（与 `main` 完全一致）：
   ```bash
   git branch -f v4-stable main
   git push origin v4-stable
   ```
   *效果*：IDE 分支列表中将整齐展示：
   - `main`
   - `v4-stable` [NEW]
   - `v3-stable`
   - `v2-stable`
   再也不会出现“找不到 v4 分支”的疑惑。

2. **补充 `README.md` 版本说明看板**：
   在根目录建立清晰的项目说明，把当前版本 V4 与历史版本 V3/V2 的关系、安装方式明确写出。
