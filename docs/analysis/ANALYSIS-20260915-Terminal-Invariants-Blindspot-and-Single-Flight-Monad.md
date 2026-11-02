# ANALYSIS-20260915-Terminal-Invariants-Blindspot-and-Single-Flight-Monad

> **分析类型**：终端守恒律盲区审计与单任务并发碰撞深度解构（Invariants Blindspot & Single-Flight Monad Deconstruction）  
> **现场现场**：`orignalscanner` 项目，会话 `5d10c7c5-b05a-4cb8-9eb6-0eaeca3d4110`  
> **用户疑问**：“深度解构一下 我们的三铁律是否没有涵盖这个命令? 我看到其他后台执行的命令都自动加了定时器顺利执行退出了”  
> **裁定结果**：`FEASIBLE` (精准捕获两大盲区：**无例外 timeout 遗漏** + **并发多任务抢占导致的孤儿任务遗留**，提出单飞强锁与自动回收律)

---

## 一、战略执行摘要 (Executive Verdict)

用户的疑问极其尖锐且完全命中靶心！

我们在逐行复盘 `5d10c7c5` 全量日志（247 帧 Trajectory）后证实：
**其他后台命令（如 `task-142`, `task-198`, `task-227`）全部按照闭环逻辑挂载了 `schedule` 定时器并顺利退出，唯独 `task-129`（即 `docker inspect`）被遗弃在底部状态栏。**

这证明我们现有的《终端三守恒律》存在两大隐性盲区：
1. **盲区一：轻量探测命令的“超时豁免”侥幸心理**：大模型认为 `docker inspect` 是极快只读命令，擅自漏掉了 `timeout 15s` 前缀；
2. **盲区二：并发任务抢占与孤儿遗留漏洞 (Task Collision & Orphan Trap)**：在前一个重度任务 `task-123` 尚未结束时，Agent 并行发起了 `docker inspect`（生成 `task-129`）；此时 `task-123` 突然完成并唤醒 Agent，Agent 瞬间切去处理 `task-123` 的长篇数据，导致 `task-129` 成为**完全失去托管、无人认领的“幽灵孤儿任务”**！

---

## 二、Keshav Three-Pass: 深度解构 (Divergent Deconstruction)

### Pass 1: 5C Baseline (概念基线)
- **Category (范畴)**：Agent 执行引擎与异步命令生命周期管理状态机（Task Lifecycle & Concurrency Invariants）。
- **Context (场景)**：在涉及容器、数据查询等多步骤复杂诊断时，Agent 频繁发起后台任务。
- **Correctness (正确性)**：三守恒律设计了“单命令”的防护（WaitMsBeforeAsync、timeout、stdin），但**缺乏“多命令交织时的并发约束（Concurrency Control）”**。
- **Contributions (教训与价值)**：必须将“单命令三守恒律”升级为**“终端任务单飞公理 (Single-Flight Terminal Monad)”**：
  - 严禁并发！在前置后台任务未返回前，禁止发起任何新命令。
  - 零例外！任何命令（包括 `docker inspect`、`ls`、`ps`）无条件前缀 `timeout 15s`。
  - 自动清理！任何后台任务必须显式托管，发现孤儿立即自动 `manage_task(kill)`。

---

### Pass 2: Causal & Evidence Firewall (帧级时间线对比证据)

通过提取 `5d10c7c5` 的全量任务生命周期表，真相一目了然：

```text
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                           全量后台任务生命周期对照表 (Task Audit Table)                  │
├──────────┬─────────────────────────────────────┬──────────────────┬─────────────────────┤
│ 任务 ID  │ 命令摘要                             │ 定时器 / 托管状态 │ 系统退出与通知结果  │
├──────────┼─────────────────────────────────────┼──────────────────┼─────────────────────┤
│ task-99  │ docker cp deep_dive.py ...          │ 显式 status 轮询  │ ✅ Step 104 正常退出 │
│ task-112 │ docker cp check_duplicate.py ...    │ 显式 status 轮询  │ ✅ Step 119 正常退出 │
│ task-123 │ docker cp deep_dive.py (大查询) ... │ 显式 status 轮询  │ ⚠️ Step 130 突然唤醒 │
├──────────┼─────────────────────────────────────┼──────────────────┼─────────────────────┤
│ task-129 │ docker inspect orignal_scanner ...  │ ❌ 无定时器/未认领│ 💥 被 task-123 撞飞  │
│          │ (在 task-123 运行中违规并行插入)    │ (Orphaned Task)  │ 永久遗留成为幽灵 UI │
├──────────┼─────────────────────────────────────┼──────────────────┼─────────────────────┤
│ task-142 │ docker cp check_605162_history.py   │ ✅ schedule(20s)  │ ✅ Step 151 正常退出 │
│ task-189 │ docker cp test_chanlun_now.py       │ 显式 status 轮询  │ ✅ Step 192 正常退出 │
│ task-198 │ docker cp check_historical_context  │ ✅ schedule(15s)  │ ✅ Step 209 正常退出 │
│ task-216 │ docker cp check_historical_context  │ 显式 status 轮询  │ ✅ Step 219 正常退出 │
│ task-227 │ docker cp check_1d_both.py          │ ✅ schedule(20s)  │ ✅ Step 236 正常退出 │
└──────────┴─────────────────────────────────────┴──────────────────┴─────────────────────┘
```

#### 致命碰撞案发现场（Step 122 ~ 131）

1. **Step 122 (03:37:35 UTC)**: Agent 发起重度查询 `deep_dive.py`，进入后台成为 `task-123`；
2. **Step 125 (03:37:43 UTC)**: Agent 心想：“趁 `task-123` 正在跑，我顺便 inspect 一下 docker 网络吧”；
3. **Step 128 (03:37:43 UTC)**: Agent 违反单任务原则，并发调用 `docker inspect ...`（未带 `timeout 15s`！）；
4. **Step 129 (03:37:45 UTC)**: IDE 检测到已有后台任务在运行，立即将该命令也打包为后台 `task-129`；
5. **Step 130 (03:37:49 UTC)——【致命交叉】**: `task-123` 执行完毕，向系统推送高优先级 `SYSTEM_MESSAGE`；
6. **Step 131 (03:37:55 UTC)**: Agent 被 `task-123` 唤醒，全神贯注分析返回的 K 线数据，**彻底遗忘了刚刚启动的 `task-129`**！
7. **结果**：`task-129` 虽然在 Linux 物理层面 0.05 秒就跑完了，但因为系统事件队列被 `task-123` 抢占，IDE 状态机未将其标记为 Finished，导致其在 UI 底部栏形成“永久悬挂”。

---

### Pass 3: Virtual Re-Implementation: 为什么其他命令能正常退出？

正如用户所观察到的：
- **`task-142`, `task-198`, `task-227` 是串行单任务执行的**。
- 当这些任务被推入后台时，Agent 遵从了平台托管模式：
  1. 调用 `schedule(DurationSeconds='20', TimerCondition='task-xxx')` 挂载定时看门狗；
  2. 任务完成通知到达后，Agent 立即调用 `manage_task(Action='kill', TaskId='timer-xxx')` 销毁看门狗；
  3. 任务生命周期首尾闭合，状态机正常流转为 `DONE`。

唯独 `docker inspect`（`task-129`）是在“双任务交叠”的缝隙中诞生的私生子，导致它成为了唯一的牺牲品。

---

## 三、Deep Recon: 漏洞根因与规约缺陷定位

对比现行 `bmad-constitution.md` 与 `ana-solo/SKILL.md`，我们发现了两处规约盲区：

### 缺陷 1：缺少“禁止并发终端任务（No Concurrent Tasks）”刚性门禁
- 现行规则只规定了单条命令怎么跑（WaitMsBeforeAsync、timeout、stdin），但**没有规定“当前有后台任务正在执行时，严禁发起新命令”**。
- 大模型出于“并行加速”的小聪明，在前一个任务等待中发起第二条命令，直接撞碎了 IDE 单通道消息队列。

### 缺陷 2：“轻量命令”的超时防线失守
- 在 `ana-solo/SKILL.md` 中写道：“Lightweight exploration: timeout 15s <cmd>”。
- 因为用了“轻量”二字，大模型把 `docker inspect` 视为“超轻量”，认为不需要加 `timeout 15s`。
- 必须废除任何主观修饰词，改用**全称量词——“ALL terminal commands MUST prepend timeout 15s/30s without exception”**。

---

## 四、加固修复蓝图：从“三守恒律”升级为“五大执行铁律”

将现有的终端守恒律全面升级为**《终端执行五大守恒铁律 (Terminal Execution Penta-Invariants)》**：

```markdown
### 终端执行五大守恒铁律 (Penta-Invariants)

1. 【单飞排队强锁 (Single-Flight Lock)】:
   - 严禁并发！在一个后台任务（Task）未明确结束或被 kill 之前，绝对严禁发起任何新的 run_command。
   - 若前序任务无必要继续等待，必须先执行 manage_task(Action='kill') 主动清场，再发起新命令。

2. 【零例外有界超时 (Universal Timeout)】:
   - 严禁任何命令裸奔！无论是 docker inspect, docker ps, git status, ls 还是复杂脚本，一律必须显式前缀 timeout 15s（重度任务 timeout 30s）。绝无任何“轻量命令”例外！

3. 【前台同步强锁 (Foreground Sync Lock)】:
   - WaitMsBeforeAsync 一律锁定为 10000ms（10秒）。

4. 【输入封闭公理 (Fail-Closed Stdin)】:
   - 所有终端命令尾部必须追加 < /dev/null，严禁交互式挂起。

5. 【工具正交公理 (Tool Orthogonality)】:
   - 严禁在终端拼接多行 python -c 或 cat << 'EOF'，复杂数据探测必须通过 write_to_file 编写 scratch 脚本。
```

---

## 五、Handoff to /bmad-solo

如需立即将上述《五大守恒铁律》固化进核心规则与技能文件，并同步更新全局物理镜像，可直接调用：
> `/bmad-solo 将 _bmad-output/analysis/ANALYSIS-20260915-Terminal-Invariants-Blindspot-and-Single-Flight-Monad.md 批准的五大守恒铁律注入 bmad-constitution.md、bmad-core.md 与 ana-solo/SKILL.md，并执行 ./bs.sh 同步物理镜像`
