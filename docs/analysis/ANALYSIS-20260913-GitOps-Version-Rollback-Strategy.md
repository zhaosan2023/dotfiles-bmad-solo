# ANALYSIS-20260913-GitOps-Version-Rollback-Strategy

> **分析类型**：候选方案选型与架构决策矩阵（Candidate Selection & Decision Matrix）  
> **议题**：BMAD-Solo 主版本持续演进与小版本（V4.0 vs V4.1）优雅回退机制  
> **核心诉求**：日常无感（main/v4 永远最新）、云端单一真实源（摆脱本地临时备份）、回退专业传统（不产生目录膨胀，不让 `bs.sh` 参数爆炸）。

---

## 1. 现状解构与痛点剖析（Keshav Pass 1 & Pass 2）

### 1.1 为什么"本地临时快照（.bak）"不是正统解法？
在上一轮排障中建立的 `bmad-suite-v4.bak.20260913` 仅是单次操作的物理防险垫（Safety Cushion），属于**本地易失性临时产物**。
- **违背 GitOps 公理**：代码与配置的唯一真实源（Single Source of Truth, SSOT）必须是 Git 远程仓库（GitHub）。
- **VPS 易失性**：一旦 VPS 宕机、重置或更换开发机，本地 `.bak` 物理蒸发，无法达成分布式韧性。

### 1.2 为什么"在脚本中增加 `bs.sh v4.0`、`bs.sh v4.1`"是设计反模式？
如果每修一个 Bug、打一个 Patch，就在仓库里复制一个 `bmad-suite-v4.1/`、`bmad-suite-v4.2/` 目录，并让 `bs.sh` 增加对应的参数分支：
1. **目录碎片化爆炸**：一年内会有几十个目录，99% 的文件代码是重复冗余的。
2. **认知负荷倒灌**：用户在日常使用时只关心“用 V4 的最新稳定版”，强迫用户输入 `v4.1` 或记忆当前小版本号，严重破坏了极简体验。
3. **架构语义混淆**：
   - **大版本（Major: V2 / V3 / V4）**：代表**架构范式的根本跃迁**（如 V2 插件网关、V3 AGAEL 架构环、V4 双通道与收敛锁）。大版本并存并由 `bs.sh v3` / `bs.sh v4` 切换具有极高的业务合理性。
   - **小版本/补丁（Minor/Patch: V4.0 / V4.1）**：代表**同一架构基准上的时间线演进**。在专业软件工程中，时间线演进必须由 **Git Tag / Commit** 管理，绝不应该实体化为文件系统目录。

### 1.3 软链接体系的核心机理（The Invariant）
当前系统的安装原理是：
$$\text{IDE 规则链} \longrightarrow \text{Symlink} \longrightarrow \text{本地 Git 仓库/bmad-suite-v4/}$$
**关键事实**：无论 Git 本地仓库处于哪个 Commit 或 Tag，只要工作区的文件内容发生改变，软链接的目标文件即刻同步改变。IDE 重启或执行 `Reload Window` 即可生效。

---

## 2. 4 Anti-Paralysis Convergence Locks（收敛锁）

- **Lock 1 (Non-Goals Lock)**：
  - 严禁在仓库根目录下增设 `bmad-suite-v4.0`、`bmad-suite-v4.1` 等实体目录。
  - 严禁要求用户日常维护或输入小版本号参数。
  - 不引入大型包管理器（如 npm / pip 复杂发布流），保持纯 Bash + Git 的轻量极简。
- **Lock 2 (Hard Gates Cut)**：
  - 必须 100% 依赖 GitHub 远程仓库，实现跨机器、重装 VPS 后的 0 损耗秒级还原。
  - 日常使用必须保持 `git pull` + `./bs.sh`（或无需重新运行脚本）即为最新版。
- **Lock 3 (Novelty Exhaustion)**：
  - 业界通用 dotfiles（如 oh-my-zsh, doom-emacs, astronvim）的回退模式已高度成熟，直接提炼最优解，停止过度发明轮子。
- **Lock 4 (Minimal Sufficient Verdict)**：
  - 判定为 `FEASIBLE`。形成清晰的标准作业程序（SOP）与极简脚本扩展。

---

## 3. 候选方案选型矩阵（Decision Matrix）

针对“日常无感最新，回退一键切 Tag”，设计三种主流专业方案：

| 维度 | 方案 A：Git 原生 Tag 检出法 (Pure Git Checkout) | 方案 B：`bs.sh` 封装版本管理器 (Smart GitOps Installer) | 方案 C：多工作区并行法 (Git Worktree) |
| :--- | :--- | :--- | :--- |
| **日常使用体验** | ★★★★★<br>`git pull` 即可，完全无感 | ★★★★★<br>`./bs.sh` 默认永远最新 | ★★★☆☆<br>需维护不同路径 |
| **回退操作难度** | ★★★★☆<br>`git checkout v4.0.0` 一行命令，需理解 detached HEAD | ★★★★★<br>`./bs.sh --tag v4.0.0`<br>全自动处理，小白友好 | ★★☆☆☆<br>需创建 worktree 并重新建软链 |
| **灾难恢复能力** | ★★★★★<br>GitHub 单一真实源 | ★★★★★<br>GitHub 单一真实源 | ★★★★★<br>GitHub 单一真实源 |
| **仓库与目录整洁度** | ★★★★★<br>零多余文件 | ★★★★★<br>零多余文件 | ★★★☆☆<br>本地存在多个挂载目录 |
| **返回最新操作** | ★★★★☆<br>`git checkout main` | ★★★★★<br>`./bs.sh` 即刻回最新主线 | ★★★☆☆<br>需切换路径 |
| **综合裁决** | **推荐（极客基线）** | **最推荐（终极工程体验）** | 排除（重型不适合个人 dotfiles） |

---

## 4. 推荐落地方案：方案 A + 方案 B 渐进双模架构

为了让用户既能享受 **Git 原生命令的透明性**，又能享受 **一键脚本的高级封装与安全感**，推荐如下架构：

```
                    ┌──────────────────────────────┐
                    │      GitHub Remote (SSOT)    │
                    │  Tags: v4.0.0, v4.1.0...     │
                    │  Branch: main (Always Latest)│
                    └──────────────┬───────────────┘
                                   │ git clone / git pull
                                   ▼
                   ┌────────────────────────────────┐
                   │   本地 Git 仓库 (工作区)        │
                   │   /home/veryfd/dotfiles-bmad...│
                   └───────────────┬────────────────┘
                        │                     ▲
   日常正常演进 (无感): │                     │ 异常回退/排查:
   默认跟踪 main 分支   │                     │ ./bs.sh --tag v4.0.0
   (始终保持 V4 最新状态)│                     │ 或 git checkout v4.0.0
                        ▼                     │
               ┌──────────────────┐           │
               │ bmad-suite-v4/   ├───────────┘
               └────────┬─────────┘
                        │
                        ▼ (软链接 ln -s)
       ~/.gemini/config/plugins/bmad-suite
```

### 4.1 核心流程 1：日常无感使用（Zero Friction）
- **本地已有仓库时**：
  ```bash
  cd ~/dotfiles-bmad-solo
  git pull
  # 完事！因为 ~/.gemini 是软链接，代码已直接更新为 V4 最新版，直接在 IDE Reload 即可。
  ```
- **全新 VPS 或重装系统时**：
  ```bash
  git clone git@github.com:zhaosan2023/dotfiles-bmad-solo.git
  cd dotfiles-bmad-solo
  ./bs.sh
  # 完事！自动挂载 main 分支上的最新 V4 版本。
  ```

### 4.2 核心流程 2：精准回退与排障（Rollback Flow）
当你突然发现最新版有奇怪问题，想切回 V4.0.0 时：

#### 途径 1：纯 Git 原生命令（专业极客流）
```bash
cd ~/dotfiles-bmad-solo

# 1. 查看历史 Release Tags
git tag -l -n1

# 2. 一秒检出到历史稳定 Tag（工作区文件自动全部变成 v4.0.0 状态）
git checkout v4.0.0

# 3. 验证完若想切回最新版：
git checkout main
```

#### 途径 2：通过 `bs.sh` 扩展参数（零心智负担流）
增强 `bs.sh` 脚本，赋予其安全的 GitOps 探针：
- `./bs.sh --version-info`：打印当前 Git 所在分支、Commit、匹配的 Tag，清晰知晓当前运行的是哪个小版本。
- `./bs.sh --tag <tag>`：自动执行 `git checkout <tag>` 并刷新规则链接，友好提示已降级至指定历史版本。
- `./bs.sh` / `./bs.sh --latest`：自动检出回到 `main` 分支最新状态。

---

## 5. 结论与实施裁决（Verdict & Action Plan）

- **裁决状态**：`FEASIBLE`（架构完备，立即可落地）。
- **收益**：
  1. 彻底移除易失的本地 `.bak` 依赖，版本回退 100% 托管于 GitHub。
  2. 根目录保持极简（只有一套 `bmad-suite-v4`），无任何冗余目录。
  3. 日常不用关心小版本号，开箱即用最新；需要回退时一条命令无损切换。

### Handoff to /bmad-solo

To proceed to engineering implementation, simply run `/bmad-solo` with:
"Implement approved GitOps tag switcher and version-info enhancements in bs.sh from _bmad-output/analysis/ANALYSIS-20260913-GitOps-Version-Rollback-Strategy.md"
