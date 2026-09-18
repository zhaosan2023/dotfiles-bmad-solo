# dotfiles-bmad-solo

[![Version](https://img.shields.io/badge/version-v4.2.0-blue.svg)](https://github.com/zhaosan2023/dotfiles-bmad-solo/releases/tag/v4.2.0)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

面向 AI 编程助手（Antigravity / Gemini / Claude）的 **BMAD-Solo 全流程自适应架构工程循环与实证背压治理套件**。

---

## 📌 版本架构与分支说明

当前仓库主线默认激活并维护 **V4.2** 主力版本，同时通过专用稳定分支与 Release Tags 对历史演进版本进行完整归档：

| 版本 | 状态 | 对应分支 | 对应 Tag | 核心特性说明 |
| :--- | :--- | :--- | :--- | :--- |
| **V4.2** | 🟢 **当前主力主版本 (Active)** | `main` / `v4-stable` | `v4.2.0` / `v4.2` | **场景自适应动态安全阀 + 实证测试背压 + 一流 ADR 治理与收敛**<br>• **4 大场景自适应安全阀**（`algo` / `structural` / `bugfix` / `ops`），彻底告别一刀切僵化流水线卡死<br>• **物理单测背压阻断**（Epic 级单测不通过坚决禁止推进，杜绝算法假策略与任务幻觉）<br>• **方案结晶与待办暂存区**（`pending_implementation_plan.md`），隔绝头脑风暴噪音与跨会话漂移<br>• **双模分流与领域隔离**（Type A 瞬态 0 文件污染 vs Type B 持久结晶一流公民 ADR，强隔离外部项目名）<br>• **跨模型计划锁**（Artifact Monad Lock），确保 Flash、Pro、Claude 均能稳定调用原生工具建立跟踪计划 |
| **V4.1** | ⚪ **历史稳定基线** | — | `v4.1.0` / `v4.1` | **终端执行五大守恒铁律 + 下游 4 道验证收敛锁**<br>• 终端命令执行五大守恒铁律（单飞排队强锁 + 零例外全量弹性超时 + 前台同步强锁 + 输入封闭 + 工具正交），彻底杜绝死锁与挂起<br>• 下游 4 道验证收敛锁（足迹全等 + 环境亲和 + 工具正交 + 最小充分断言），消除无界测试膨胀与环境盲跑 |
| **V4.0** | ⚪ **V4 初始基线** | — | `v4.0.0` / `v4` | **分析师闭环门禁 + 4 大分析收敛防死循环锁**<br>• `/bmad-solo`：全生命周期工程闭环（Analyst / Architect / Dev / Reviewer / QA / Operator）<br>• `/ana-solo`：独立深度分析通道（Keshav 三读法、决策选型矩阵、证据防火墙） |
| **V3** | 🟡 **历史稳定基线 (Legacy)** | `v3-stable` | `v3.0.0` | **AGAEL/AGAS 架构循环**<br>• 架构合同校验机制（Contract Template & Validator）<br>• 任务状态机自闭环与 Course Correction 纠错流程 |
| **V2** | ⚪ **历史稳定基线 (Legacy)** | `v2-stable` | `v2.0.0` | **Plugin 插件化网关架构**<br>• 将孤立的 skills 统一重构为 Gemini 插件规范（`bmad-suite`） |
| **V1** | ⚪ **初始版本 (Archived)** | — | `v1.0.0-skill-based` | 初始的单纯 Skill 脚本集合归档 |

---

## 🚀 快速开始与部署

本项目采用**双层分离物理镜像架构 (Physical Mirror Architecture)**：
无论将仓库克隆在本地何处（如 `~/project/dotfiles-bmad-solo` 或 `~/dotfiles-bmad-solo`），安装引擎均会将插件与规则以**实体物理目录**（通过 `rsync -a --delete`）部署至 `~/.gemini/config/`。这彻底消除了符号链接在 Antigravity 多工作区安全沙箱下的跨域越界权限阻断，确保在任意业务项目（如量化计算、Web服务等）中均能 100% 免鉴权高速直读并遵循终端守恒铁律。

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

# 5. 查看历史 Release Tags（如 v4.0.0, v4.1.0, v4.2.0 等）
./bs.sh --tags

# 6. 精准回退到指定历史小版本并物理激活
./bs.sh --tag v4.2.0

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

## 🛠️ 核心指令与人机交互极简指南 (V4.2)

彻底告别繁重的内部 Procedure 名词记忆，人类仅需使用 3 句直觉白话：

### 1. 发散与查漏补缺（拉家常式讨论，0 污染）
* **`/ana-solo [业务问题/架构设想]`**：
  触发独立深度分析通道。日常咨询、排查、探查走 **Ephemeral 模式**，零持久文件落盘，绝不污染工程；遇到重大技术选型时自动加载 Keshav 三读法与决策矩阵推演。

### 2. 成熟收敛，一键结晶（建立前置背压屏障）
* **`/ana-solo 方案ok`**（或输入 `结晶`、`可以了`）：
  系统后台静默自动完成结晶：
  1. 产出一流公民架构决策记录：`_bmad-output/adrs/ADR-*.md` (`Status: PROPOSED`)；
  2. 提取纯净待办暂存区：`_bmad-output/pending_implementation_plan.md`，并自动打上场景指纹（`scenario: algo | structural | bugfix | ops`）与测试命令。

### 3. 一键执行，场景自适应与背压护航
* **`/bmad-solo 执行`**（或输入 `开始`、`按计划做`）：
  执行引擎自动读取暂存计划，动态挂载安全阀：
  * **算法场景 (`algo`)**：强制加载 `algorithm-fit.md`（严防参数过拟合与超限延迟）+ 强制 Epic 物理单测阻断；
  * **结构场景 (`structural`)**：强制加载 `architecture-preflight.md` + 强制 Epic 物理单测阻断；
  * **缺陷场景 (`bugfix`)**：跳过重型架构门禁，实行精准足迹单测，零 ADR 污染；
  * **运维场景 (`ops`)**：严禁盲跑业务单测，以 Git Diff 洁净度与配置语法审查极速闭环。
  * **完工大扫除**：单测全绿后自动将 ADR 转为 `ACCEPTED`，自动在 `project-context.md` 注入溯源指针，自动清空暂存区。

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源，版权归属于 [zhaosan2023](https://github.com/zhaosan2023)。
