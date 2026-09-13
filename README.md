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

## 🚀 快速开始

项目提供了一键安装脚本 `bs.sh`，默认自动挂载 **V4** 版本的插件与规则到系统环境：

```bash
# 克隆仓库
git clone git@github.com:zhaosan2023/dotfiles-bmad-solo.git
cd dotfiles-bmad-solo

# 默认安装当前主力 V4 版本
./bs.sh

# 如需切换安装历史 V3 基线
./bs.sh v3

# 卸载插件与规则
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
