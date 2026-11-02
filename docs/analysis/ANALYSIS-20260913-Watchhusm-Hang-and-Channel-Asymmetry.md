# ANALYSIS-20260913-Watchhusm-Hang-and-Channel-Asymmetry

> **分析类型**：项目卡死现场取证与双通道防线盲区溯源（Forensic Investigation & Channel Asymmetry Deconstruction）  
> **现场**：项目 `/home/veryfd/project/watchhusm`，会话 ID `d0428058-ff93-43f6-837d-f330ee11100f`  
> **用户指令**：`/ana-solo 为什么 我这个项目的历史会话是空白?`  
> **卡死现象**：停留在 `I will inspect the task output as soon as it finishes.`，命令 `python3 -c "import sqlite3, glob, os..."` 挂死。

---

## 1. 现场取证与时间线精准还原（Forensic Timeline）

通过对 `d0428058-ff93-43f6-837d-f330ee11100f/.system_generated/logs/transcript_full.jsonl` 的逐帧还原：

```text
[11:26:11 UTC / 19:26:11 本地] 用户发起：/ana-solo 为什么 我这个项目的历史会话是空白?
[11:26:12 UTC] Agent 激活 /ana-solo (读取 skills/ana-solo/SKILL.md)
[11:26:25 ~ 11:27:13 UTC] Agent 执行了 9 条前置探测命令（ls, find 等）
[11:27:13 UTC / 19:27:13 本地] Step 30: Agent 调用 run_command：
   • CommandLine: python3 -c "import sqlite3, glob, os\n\nfiles = glob.glob('/home/veryfd/.gemini/antigravity-ide/conversations/*.db')..."
   • WaitMsBeforeAsync: 5000 (严重缺陷：未遵守 10000ms 强锁！)
[11:27:16 UTC] Step 31: 物理命令在 0.0031 秒（3.1毫秒）内执行完毕并退出
   • 但 IDE 调度器在 5000ms 等待窗口与后台任务转换过程中，产生了在途竞态（In-Flight Event Drop）
   • IDE 错误地将该命令标记为后台孤儿任务 task-31，并丢失了进程已退出的回调事件
[11:27:23 UTC] Step 32: Agent 查询 manage_task(status)，IDE 误报 status=RUNNING
[11:27:25 UTC] Step 34: Agent 查看 task-31.log，内容为 0 字节
[11:27:26 UTC] Step 36: Agent 输出："I will inspect the task output as soon as it finishes."
   • 系统底层 Prompt 严令禁止主动轮询（Do NOT poll or loop on status）
   • Agent 停止一切 Tool 调用，进入无限期静默休眠（Permanent Deadlock）
```

---

## 2. 为什么今天上午的 V4.1 加固没有防御住这个场景？

我们进行了深刻的根因对比：

### 根因一：双通道不对称盲区（The Channel Asymmetry Leak）
- 今天上午，我们将防卡死铁律（终端三守恒律：`WaitMsBeforeAsync: 10000ms`、有界超时、输入封闭、原生文件工具垄断）注入到了：
  1. `bmad-suite-v4/rules/bmad-constitution.md`
  2. `bmad-suite-v4/rules/bmad-core.md`
  3. `bmad-suite-v4/skills/bmad/SKILL.md`（`/bmad-solo` 入口）
- **但是，我们漏掉了 `bmad-suite-v4/skills/ana-solo/SKILL.md`（`/ana-solo` 入口）！**
- 用户在 `watchhusm` 中输入的是 `/ana-solo`。
- IDE 激活的是 `skills/ana-solo/SKILL.md`。而 `ana-solo/SKILL.md` 里只有 Mary 分析法、三读法与 4 道分析收敛锁，**没有任何一条终端命令执行的防挂死约束**！
- 模型在 `/ana-solo` 通道中退化为无防护的原生状态，依然在使用默认的 `WaitMsBeforeAsync: 5000`，依然在 Shell 终端使用 `python3 -c` 拼接长脚本，导致悲剧完美重演！

### 根因二：跨工作区的规则穿透盲区
- 当用户在其他项目（如 `/home/veryfd/project/watchhusm`）打开对话时，如果该项目根目录没有显式的 `GEMINI.md` 或 `.agents/rules/`，且调用的 Skill 未显式加载安全宪法，模型就无法获得最高优先级的指令约束。

---

## 3. 现场问题的答案：为什么 `watchhusm` 历史会话会是空白？

在排查中，我们顺带替用户查明了最初那个问题的物理事实：
1. **历史数据库物理存在**：
   `/home/veryfd/.gemini/antigravity-ide/conversations/` 下共有 6 个数据库涉及 `watchhusm`：
   - `6306e09b-c8ac-4369-818d-512316faaa79.db`（昨日会话）
   - `fd0a8fe1-1edf-45b4-ad79-edb02f6e0746.db`
   - `d62cedcc-e828-4f0e-b383-b2c87af01695.db`
   - 以及与 `orignalscanner` 交叉的会话 `9c000917`、`e7bb533c`。
2. **空白原因**：
   IDE 左侧历史会话栏是通过当前工作区的 URI（`file:///home/veryfd/project/watchhusm`）进行精确哈希匹配过滤的。早期跨项目会话的主工作区绑定为 `orignalscanner`，或者本地元数据索引在 IDE 窗口切换时发生了缓存未刷新，导致界面未正常渲染历史列表。

---

## 4. 彻底解决对策（Convergence & Hardening Plan）

1. **补齐 `/ana-solo` 独立防护盾**：
   立即在 `bmad-suite-v4/skills/ana-solo/SKILL.md` 中强制注入：
   - **终端三守恒律**：所有终端调用必须 `WaitMsBeforeAsync: 10000ms`，包裹 `timeout 15s/30s`，封闭 `< /dev/null`。
   - **工具正交公理**：数据探测严禁在 Shell 跑多行 `python3 -c`，必须走原生 `view_file` 或轻量单行命令。
   - **闭环防休眠锁**：严禁无界等待 background task。
2. **在所有业务项目（如 `watchhusm`）根目录部署轻量 `GEMINI.md`**：
   让任何项目在无需手动 `/bmad-solo` 时，也能自动受全局防挂死宪法保护。
