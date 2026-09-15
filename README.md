# dotfiles-bmad-solo

[![Version](https://img.shields.io/badge/version-v4.1.0-blue.svg)](https://github.com/zhaosan2023/dotfiles-bmad-solo/releases/tag/v4.1.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

面向 AI 编程助手（Antigravity / Gemini）的 **BMAD-Solo 全流程架构工程循环与深度分析套件**。

---

## 📌 版本架构与分支说明

当前仓库主线默认激活并维护 **V4** 系列版本，同时通过专用稳定分支与 Release Tags 对历史演进版本进行完整归档：

| 版本 | 状态 | 对应分支 | 对应 Tag | 核心特性说明 |
| :--- | :--- | :--- | :--- | :--- |
| **V4.1** | 🟢 **当前主力主版本 (Active)** | `main` / `v4-stable` | `v4.1.0` / `v4.1` | **终端防挂起三守恒律 + 下游 4 道验证收敛锁**<br>• 终端命令执行三守恒律（前台同步强锁 + 有界超时兜底 + 输入封闭），彻底杜绝在途事件丢失死锁与 Stdin 劫持<br>• 下游 4 道验证收敛锁（足迹全等 + 环境亲和 + 工具正交 + 最小充分断言），消除无界测试膨胀与环境盲跑<br>• 继承 V4 全部敏捷角色闭环与 `/ana-solo` 深度通道 |
| **V4.0** | ⚪ **V4 初始基线 (Baseline)** | — | `v4.0.0` / `v4` | **分析师闭环门禁 + 4 大分析收敛防死循环锁**<br>• `/bmad-solo`：全生命周期工程闭环（Analyst / Architect / Dev / Reviewer / QA / Operator）<br>• `/ana-solo`：独立深度分析通道（Keshav 三读法、决策选型矩阵、证据防火墙） |
| **V3** | 🟡 **历史稳定基线 (Legacy)** | `v3-stable` | `v3.0.0` | **AGAEL/AGAS 架构循环**<br>• 架构合同校验机制（Contract Template & Validator）<br>• 任务状态机自闭环与 Course Correction 纠错流程 |
| **V2** | ⚪ **历史稳定基线 (Legacy)** | `v2-stable` | `v2.0.0` | **Plugin 插件化网关架构**<br>• 将孤立的 skills 统一重构为 Gemini 插件规范（`bmad-suite`） |
| **V1** | ⚪ **初始版本 (Archived)** | — | `v1.0.0-skill-based` | 初始的单纯 Skill 脚本集合归档 |

---

## 🚀 快速开始与部署

本项目采用**双层分离物理镜像架构 (Physical Mirror Architecture)**：
无论将仓库克隆在本地何处（如 `~/project/dotfiles-bmad-solo` 或 `~/dotfiles-bmad-solo`），安装引擎均会将插件与规则以**实体物理目录**（通过 `rsync -a --delete`）部署至 `~/.gemini/config/`。这彻底消除了符号链接在 Antigravity 多工作区安全沙箱下的跨域越界权限阻断，确保在任意业务项目（如 `orignalscanner`、`watchhusm` 等）中均能 100% 免鉴权高速直读并遵循终端防挂起守恒律。

### 方式 A：一键远程免克隆安装 (One-Line Quick Bootstrap)

在任意全新主机上运行：

```bash
curl -fsSL https://raw.githubusercontent.com/zhaosan2023/dotfiles-bmad-solo/main/install.sh | bash
```

### 方式 B：本地 GitOps 部署与更新

```bash
# 1. 克隆仓库至任意路径
git clone git@github.com:zhaosan2023/dotfiles-bmad-solo.git ~/project/dotfiles-bmad-solo
cd ~/project/dotfiles-bmad-solo

# 2. 物理部署当前主力 V4 版本（开箱即用）
./bs.sh

# 3. 查看全局安装状态、Commit、时间戳与 Manifest 审计
./bs.sh --status

# 4. 一键从 GitHub 拉取最新提交并自动物理同步到全局
./bs.sh --update

# 5. 查看历史 Release Tags（如 v4.0.0, v4.1.0 等）
./bs.sh --tags

# 6. 精准回退到指定历史小版本并物理激活
./bs.sh --tag v4.1.0

# 7. 随时一键切回 main 主线最新物理镜像
./bs.sh --latest

# 8. 模拟执行（无任何写入副作用）
./bs.sh --dry-run

# 9. 切换安装历史 V3 架构基线
./bs.sh v3

# 10. 卸载全局插件与规则
./bs.sh --uninstall
```

---

## 🛠️ 核心指令一览 (V4)

在 AI 对话中可直接调用以下斜杠指令：

* **`/bmad-solo`**：触发端到端软件工程循环（需求分解 → 架构设计 → 任务拆解 → 单元实现 → 交叉评审 → 诊断验证）。
* **`/ana-solo`**：触发独立深度分析通道，用于论文精读、技术方案多选一决策（Decision Matrix）或复杂需求发掘，严格遵循 4 大收敛锁防思维发散。

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源，版权归属于 [zhaosan2023](https://github.com/zhaosan2023)。
