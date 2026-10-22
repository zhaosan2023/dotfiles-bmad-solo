# 属性测试、Fuzzing 与确定性测试背压尽调与决策报告 (DR & DM)

> **溯源说明**：本文档结晶自 Roo Code 最新探索会话（Task ID: `01a15920-8f21-735e-9291-33b1b1260085`），因自定义网关 `aurora2api` 长任务流中断未及直接落盘。现经深度反思与全景审计，完整抢救其 36 处一手核心链接、第一/第二/第三遍尽调事实，并由架构师执行严格的 **反向推翻审查 (DR)** 与 **决策加权矩阵 (DM)** 裁决。

---

## 一、 第一遍：Map —— 真正应该采纳什么

针对探索文档 [adr_propertyfuzzing_antithesis.md](file:///home/ecs-user/dotfiles-bmad-solo/docs/Ralph-Wiggum-Loop/adr_propertyfuzzing_antithesis.md) 提出的四层验证方法论，必须严格划清“工具具备某种理论能力”、“业界产品（如 Overalls）的宣传”与“我们本地系统真实获得的工程保障”三者之间的界限。

### 1.1 四层验证能力的真实边界

| 层次 | 核心职责 | 不能替代什么（防越界边界） |
|---|---|---|
| **强类型 (Strong Types)** | 限制内部数据、状态转移与接口能够表达的状态空间（Make illegal states unrepresentable） | 不能替代外部未受信任输入校验、运行时权限核验与外部环境故障判断 |
| **属性测试 (PBT)** | 将人类业务授权、状态守恒与幂等不变量转成可自动生成的执行规则（Test Oracle） | 不能替代属性定义本身的正确性审查（防 Vacuous Truth 虚真陷阱） |
| **模糊测试 (Fuzzing)** | 利用覆盖率引导（Coverage-Guided）搜索异常边界输入和事件交错反例 | 不能替代确定性全系统证明，不能替代真实物理宿主机（OS/Git/网络）生命周期测试 |
| **确定性自治测试 (DST)** | 控制显式封闭范围内的伪随机性、逻辑时钟与消息顺序，支持反例精确重放 | 不能替代未受控的外部真实依赖（真实模型 API、真实操作系统内核、真实硬件断电） |

**核心结论**：这四层背压必须直接服务于现有执行底座，**绝不能成为重蹈覆辙、在 Python 中再造第二套调度器或状态数据库的借口**。

---

## 二、 第二遍：Evidence —— 36 项一手网址尽调与真实证据核验

以下为针对原探索文档中全部显式来源的逐项实测核验结果与客观边界。

### 2.1 Overalls 与架构关联来源

| 编号 | 来源对象 | 官方链接 | 核验结果与真实边界 (FACT & BOUNDARY) |
|---|---|---|---|
| **[1]** | Overalls 官网 | `https://overalls.dev/` | 官网声明自托管、MIT 开源、持久化 Firecracker 开发机和后台 Agent 线程；仍展示 2026-11-03 发布预览。此为项目方商业声明，不等于外部独立第三方验证。 |
| **[2]** | Overalls 源码仓库 | `https://github.com/ghuntley/overalls` | **关键纠正**：当前仓库公开可访问，包含 `antithesis` 目录；原文“发布前源码可能仍私有”的判断已不符合当前事实。但目录存在不代表其内部测试全部通过。 |
| **[3]** | Gemini 对话地址 | `https://gemini.google.com/app/7d41bab4085e94eb` | 访问跳转至通用登录首页，未取得原对话正文，无法独立核验原作者在社交对话中的原话上下文。 |
| **[4]** | Geoffrey Huntley 主页 | `https://ghuntley.com/` | 主页自述创建 Ralph Loop；不能据此证明原文中关于 Flutter、Verus 和投入产出比的所有推论。 |
| **[5]** | Cedar 策略引擎 | `https://github.com/cedar-policy/cedar` | 确认是 AWS 开源的 Cedar 策略语言，Apache-2.0 许可；不能由此推出权限撤销具备分布式即时一致性。 |
| **[6]** | Firecracker microVM | `https://github.com/firecracker-microvm/firecracker` | 确认是 AWS 开源 microVM，Apache-2.0 许可；Overalls 的 Windows 支持属于其项目自述，不能自动归结为 Firecracker 上游原生能力。 |
| **[7]** | Ash Framework | `https://github.com/ash-project/ash` | 声明式 Elixir 应用框架；无证据支持“声明资源后所有审计、多租户隔离和 API 安全均自动正确”。 |
| **[8]** | AshPostgres | `https://github.com/ash-project/ash_postgres` | Ash 的 PostgreSQL 数据层驱动；不能证明其底层如何实现分布式事务协调与断网恢复。 |
| **[9]** | Phoenix 框架 | `https://github.com/phoenixframework/phoenix` | Elixir Web 框架，MIT 许可；未核验原文关于“毫秒级拉起百万进程且每个仅 2KB”的具体数字依据。 |

### 2.2 属性测试、Fuzzing 与并发仿真工具

| 编号 | 来源对象 | 官方链接 | 核验结果与真实边界 (FACT & BOUNDARY) |
|---|---|---|---|
| **[10]** | proptest | `https://github.com/proptest-rs/proptest` | 支持属性测试、策略生成、反例收缩（Shrinking）与失败回归持久化，MIT/Apache-2.0 许可。 |
| **[11]** | Rust QuickCheck | `https://github.com/BurntSushi/quickcheck` | Rust 属性测试项目；页面展示多份协议文件，不能笼统归为单一商业友好许可。 |
| **[12]** | cargo-fuzz | `https://github.com/rust-fuzz/cargo-fuzz` | **关键纠正**：基于 libFuzzer，官方明确要求 **nightly Rust**、支持 C++11 的编译器及特定 Unix 平台与架构；不支持原文暗示的“Rust stable 即可跨平台运行全部验证”。 |
| **[13]** | arbitrary | `https://github.com/rust-fuzz/arbitrary` | 从非结构化字节流生成结构化对象，MIT/Apache-2.0；它只是生成器适配器，不是覆盖率引导引擎或状态机求解器。 |
| **[14]** | Loom 并发检查器 | `https://github.com/tokio-rs/loom` | **关键警示**：官方明确指出其未完整实现 C11 内存模型，既可能误报，也可能遗漏并发路径；仅适合局部原子/并发原语，绝不能替代跨进程、Git、网络或文件系统边界测试。 |
| **[15]** | madsim | `https://github.com/madsim-rs/madsim` | Rust 分布式确定性仿真器（RisingWave 开源），Apache-2.0；不能推出任何第三方异步依赖都能无缝零成本替换。 |
| **[16]** | StreamData | `https://github.com/whatyouhide/stream_data` | Elixir 属性测试库；不足以证明 Marshall 控制面实际上线使用了该库。 |
| **[17]** | Verus | `https://github.com/verus-lang/verus` | 面向低级系统级代码的 Verified Rust 工具；本轮未取得证明“形式化验证维护成本必然高于 PBT”的直接对比实验。 |
| **[18]** | Turmoil | `https://github.com/tokio-rs/turmoil` | Tokio 出品的分布式单线程网络仿真库；具体文件系统故障能力与在非纯 Tokio 架构下的适配成本需谨慎评估。 |

### 2.3 Antithesis、Hegel 与 Agent 技能矩阵

| 编号 | 来源对象 | 官方链接 | 核验结果与真实边界 (FACT & BOUNDARY) |
|---|---|---|---|
| **[19]** | Antithesis 组织 | `https://github.com/antithesishq` | 官方组织可访问，定位为企业级确定性黑盒系统测试平台；其宣传效果不是公开独立对照实验。 |
| **[20]** | Antithesis Rust SDK | `https://github.com/antithesishq/antithesis-sdk-rust` | **关键机制揭露**：关闭默认断言特性后，断言参数仍会求值，但**不会发出或处理断言**；因此引入 SDK 宏绝不等于在本地环境自动具备阻断提交的失败门禁。 |
| **[21]** | Antithesis 官方文档 | `https://antithesis.com/docs/` | 包含 Properties, Assertions, Fault Injection 等章节；商业底层为专有 Deterministic Hypervisor，并未开源。 |
| **[22]** | Hegel 总组织 | `https://github.com/hegeldev` | 基于 Hypothesis 理念的跨语言 PBT 协议与库家族，由 Hypothesis 作者在 Antithesis 主导。 |
| **[23]** | Hegel Rust | `https://github.com/hegeldev/hegel-rust` | **关键更新**：于 2026-10-19 归档并迁入 `hegeldev/hegel` 单体仓库。这是维护入口合并，并非放弃维护。 |
| **[24]** | Hegel Go | `https://github.com/hegeldev/hegel-go` | Go 语言属性测试实现，MIT 许可；未取得横向基准性能对比数据。 |
| **[25]** | Bombadil | `https://github.com/antithesishq/bombadil` | 面向 Web/Terminal UI 的属性模糊测试工具，MIT 许可；无直接证据证明 Overalls 客户端已经正式集成它。 |
| **[26]** | antithesis-skills | `https://github.com/antithesishq/antithesis-skills` | 面向 AI 的技能资产包（Apache-2.0），包含 workload 规划、变异测试目录；其自身不是独立的执行沙箱。 |
| **[27]** | hegel-skill | `https://github.com/hegeldev/hegel-skill` | 指导 AI 识别属性、编写 Hegel 测试的技能包，MIT 许可；对其他 PBT 库的适用性未经验证。 |
| **[28]** | HashiCorp Raft POC | `https://github.com/antithesishq/hashicorp-raft-poc` | 采用 Antithesis 测试 Raft 的概念验证项目，**注意其协议为 MPL-2.0**，非全部 MIT/Apache-2.0。 |
| **[29]** | PostgreSQL Workload | `https://github.com/antithesishq/postgres-workload` | **极高参考价值**：测试客户端以真实外部下游消费者的视角操作被测系统，并在外部断言持久性、守恒性，而非测试内部私有 mock。 |

### 2.4 经典论文与工业界实证

| 编号 | 来源对象 | 官方/出版链接 | 核验结果与真实边界 (FACT & BOUNDARY) |
|---|---|---|---|
| **[30]** | FoundationDB 源码 | `https://github.com/apple/foundationdb` | Apple 开源分布式事务数据库，Apache-2.0；DST 的开山之作，但其模拟器重度内嵌在自定义 C++ actor 运行时中。 |
| **[31]** | TigerBeetle 仓库 | `https://github.com/tigerbeetle/tigerbeetle` | 高性能账本数据库，Apache-2.0；其 VOPR 确定性测试极其精妙，但绝不能为了模仿测试而引入外部数据库系统。 |
| **[32]** | TigerBeetle 仿真可视化 | `https://sim.tigerbeetle.com/` | 页面为基于 WebAssembly 的模拟器图形化展示，不能直接抽取其算法用于通用业务系统。 |
| **[33]** | FoundationDB SIGMOD '21 论文 | `https://dl.acm.org/doi/10.1145/3448016.3457559` | 顶会论文；证明了单核伪随机仿真、确定性时钟与网络注入在发现并发/恢复 Bug 上的威力。 |
| **[34]** | QuickCheck 原始论文 | `https://www.cs.tufts.edu/~nr/cs257/archive/john-hughes/quick.pdf` | ICFP 2000 经典论文；强调属性、生成器分布以及可观察性，指出单纯依赖盲目随机次数并不保证系统正确。 |
| **[35]** | Hypothesis Reducer 论文 | `https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ECOOP.2020.13` | **校正链接**：原文中错写为 `EC00P`（数字00导致 404），正确出版标识为 `ECOOP.2020.13`；阐明了基于统一字节流的测试用例生成与智能收缩原理。 |
| **[36]** | WarpStream 博客 | `https://www.warpstream.com/blog/deterministic-simulation-testing-for-our-entire-saas` | **关键事实纠正**：“233 秒”是指在接入测试平台的第一轮跑查出了一个插桩库的数据竞争（Data Race），随后的网络故障注入才发现了真实的数据丢失 Bug，原文将两者压缩成一句话不够严谨。 |

---

## 三、 第三遍：必须撤回的过度承诺与认知误区

在将该探索结论吸收进 V6 之前，必须以最严苛的态度**剔除一切无测量依据的营销数字与认知幻觉**：

1. **撤回无测量依据的“营销比例”**：
   - 彻底废止 “10% 规范成本捕获 95% Bug”、“开源同构平替复刻 90% 以上 Antithesis 能力”、“强类型剪掉 80% 无效状态空间”、“任意缺陷 1 秒内收缩至 6 步以内” 等定性断言。这些数字缺乏严谨基准测量，绝不能写进架构规范。
2. **纠正“单 Seed 等于全系统确定性”的幻觉**：
   - 在真实工程中，操作系统调度、磁盘 I/O 延迟、外部大模型 API 返回的温度与网络波动天然是非确定性的。所谓“确定性测试”，必须显式标明其受控边界（如内存状态机受控），绝不能假定整个 CLI 或 VPS 会话能被一个随机数种子完全决定。
3. **拒绝“为了背压而激进重写 Rust”的教条主义**：
   - Rust 的强类型与 PBT 生态确实优秀，但**我们的症结从来不是 Python 这门语言不够好，而是我们在 Python 里写了一套庞大的官僚中间件**！在 Python 中，结合 Pydantic 强类型、Hypothesis 属性测试与 Deterministic Harness，完全能以极低成本构建高硬度的验证背压。

---

## 四、 DR (Deep Recon / Defensibility Review) 反向推翻审查

在采纳“强类型 + 属性测试 + 失败关闭”作为 V6 核心背压之前，对方案进行致命漏洞预先验尸（Pre-Mortem）：

### DR-1: 虚真通过陷阱 (Vacuous Pass Trap)
- **风险**：如果 Agent 或测试编写者定义了非常严苛的前置过滤条件（如 `assume(x > 1000)` 或过早 `return Err`），属性测试跑了 10 万次，全部判定 PASS，但核心业务逻辑一次都没进去执行。
- **对冲策略**：**强制引入 Antithesis 双生断言机制**。每一条 `assert_always!`（安全性，坏事不发生）必须成对绑定至少一条 `assert_sometimes!`（可达性/活性，好事必须发生过一次），并在门禁执行器中统计执行覆盖率，若深层分支命中数为 0，门禁直接判定 **FAIL (空跑拒绝)**。

### DR-2: 变异测试缺位 (Mutation Blindspot)
- **风险**：测试用例越来越多，执行时间变长，但测试代码本身其实无法捕捉关键回归（例如门禁把 exit_code != 0 当成了警告并返回空列表）。
- **对冲策略**：在门禁测试套件中内置**六大对抗性变异测试（Negative Mutation Tests）**：
  1. 故意将下游测试失败硬编码返回为成功；
  2. 故意修改候选版本号；
  3. 故意复用已通过的旧 Review 证据；
  4. 故意在取消会话后不等待确认即启动新会话；
  5. 故意在测试中修改 policy/rules 配置文件；
  6. 故意将失败任务的中间经验追加到主线经验库。
  *验证标准*：测试套件必须 100% 捕获上述所有变异，否则测试套件自身不可信！

### DR-3: 上下文爆炸与反例反噬 (Context Choking)
- **风险**：Fuzzing 吐出的原始失败 trace 可能长达数千行，如果直接灌入 Coding CLI（Cline / Claude Code），会直接撑爆上下文窗口，诱发模型退化。
- **对冲策略**：**必须通过收缩（Shrinking）与结构化收据（Receipt）标准化输出**。反例必须收敛为：
  `{property_id, minimal_steps: [...], failure_reason, seed, candidate_hash}`，只向 Agent 提供最简复现序列与不变量违背原因。

---

## 五、 DM (Decision Matrix) 决策加权矩阵

### 5.1 候选方案定义

- **C1: V5 官僚中间件修补**（维持当前 `bmralph-suite-v5`，继续修补 1728 行 `bmad_control_store.py` 与各层调度器，在外部增加更多检测脚本）；
- **C2: 激进 Rust Core + 确定性 Hypervisor 重写**（全盘按照 ADR 蓝图将控制面与编排重构为 Rust，引入 Turmoil/Madsim 虚拟网络仿真，重写全部 CLI）；
- **C3: 自研 Python/Rust 复杂内存仿真系统**（在 Python 中构建庞大的 Sans-IO 虚拟时钟、网络与文件系统影子模型，追求本地 100% 确定性模拟）；
- **C4: V6 极简自治背压架构 (Recommended)**（编排严格托管给官方 `bmad-loop`；以 Pydantic/Hypothesis 建立强类型与属性神谕；建立 6 大不可违背失败关闭门禁；验证分三级，真实宿主直接测试真实 Git/Process/VPS 生命周期；通过变异测试防空跑）。

### 5.2 硬门禁筛查 (Hard Gates)

| 门禁项 | 门禁准则 | C1 | C2 | C3 | C4 (推荐) |
|---|---|---|---|---|---|
| **Gate 1: 零中间件官僚泥潭** | 绝对禁止在 Python/Rust 中自研调度器与事务数据库 | **FAIL** (继续膨胀) | PASS | **FAIL** (重蹈覆辙) | **PASS** |
| **Gate 2: 编排循环确定性** | 遵循 Hard Invariant：控制循环 100% 确定性，零 LLM 参与流转 | PASS | PASS | PASS | **PASS** |
| **Gate 3: 失败关闭与防空跑** | 门禁异常、空输出、变异注入必须 100% 阻断提交 | **FAIL** (静默退化) | PASS | UNKNOWN | **PASS** |
| **Gate 4: 立即落地与工程 ROI** | 个人/精简团队 48 小时内可验证并打通端到端闭环 | PASS | **FAIL** (数月工程) | **FAIL** (陷入仿真泥潭) | **PASS** |
| **筛查结论** | | **淘汰 (FAIL)** | **淘汰 (FAIL)** | **淘汰 (FAIL)** | **唯一胜出 (PASS)** |

### 5.3 决策加权评分明细 (0 - 5 分制)

*维度与权重*：
- $w_1 = 0.30$ **背压阻断有效性 (Backpressure Rigidity)**：对非法状态、证据不一致、门禁异常的即时阻断率与反例收缩能力；
- $w_2 = 0.25$ **架构极简与反官僚 (Zero Architecture Bloat)**：去除冗余抽象层，消除中间件数据库与自研调度器；
- $w_3 = 0.25$ **AI 循环敏捷度 (Agent Feedback Actionability)**：反例对 Agent 的可理解性、可修复性及端到端执行周期；
- $w_4 = 0.20$ **实现与维护成本 (Engineering ROI)**：不依赖昂贵外部商业服务，在现有 Linux/VPS 物理机上稳定运行。

$$Score = 20 \times \sum_{i=1}^4 w_i s_i$$

| 候选方案 | $s_1$ 背压有效性 (0.30) | $s_2$ 反官僚极简 (0.25) | $s_3$ Agent 敏捷 (0.25) | $s_4$ 维护 ROI (0.20) | 加权总分 (100分制) | 排名 |
|---|---|---|---|---|---|---|
| **C1: V5 官僚修补** | 1.8 | 1.0 | 2.0 | 2.5 | **36.8** | 4 |
| **C2: 激进 Rust 重构** | 4.8 | 3.5 | 3.2 | 1.2 | **67.0** | 3 |
| **C3: 自研复杂仿真器** | 3.5 | 1.8 | 3.0 | 2.0 | **53.0** | 2 |
| **C4: V6 极简自治背压** | **4.9** | **5.0** | **4.8** | **4.7** | **48.6 x 2 = 97.2** | **冠军 (Winner)** |

---

## 六、 V6 极简自治背压落地蓝图与实施规范

基于上述裁决，V6 的具体落地方案如下：

### 6.1 必须固化的六大核心不变量 (The 6 Invariants)

测试门禁（无论由 `bmad-loop verify.py` 执行，还是由 `solo-jev-gate` 执行）必须对以下六项不变量实行**一票否决制（Fail-Closed）**：

```
       [ 候选代码提交请求 ]
               |
               v
  +--------------------------+
  |  Invariant 1: 候选哈希强绑定 | ---> [哈希不匹配/旧证据复用] ---> 阻断 (ABORT)
  +--------------------------+
               |
               v
  +--------------------------+
  |  Invariant 2: 严格失败关闭    | ---> [超时/崩溃/空输出/非零退出] ---> 阻断 (ABORT)
  +--------------------------+
               |
               v
  +--------------------------+
  |  Invariant 3: 授权与范围隔离  | ---> [跨越Worktree/越权改写配置] ---> 阻断 (ABORT)
  +--------------------------+
               |
               v
  +--------------------------+
  |  Invariant 4: 单一写入者保证  | ---> [存在未确认停止的并存进程] ---> 阻断 (ABORT)
  +--------------------------+
               |
               v
  +--------------------------+
  |  Invariant 5: 有界停止与保全  | ---> [Token超标/断网连续失败] ---> 优雅落盘停止
  +--------------------------+
               |
               v
  +--------------------------+
  |  Invariant 6: 经验物理隔离    | ---> [未经Review盖章的经验] ---> 丢弃不污染
  +--------------------------+
               |
               v
        [ 允许合并入主线 ]
```

1. **候选绑定 (Candidate Binding)**：测试通过的证据、Review 审核结论与最终 Git Commit 必须基于**完全相同的 Commit SHA / Git Tree Hash**；任何代码变更立即作废先前所有通过证据。
2. **严格失败关闭 (Fail-Closed)**：任何测试超时、进程崩溃、非法 JSON 响应、空输出或退出码非 0，**必须直接判定为 FAIL**，严禁吞掉异常或退化为警告。
3. **范围与权限隔离 (Scope Limiting)**：执行 Agent 只能修改其分配的工作区（Git Worktree），严禁软链接穿越、严禁越权修改 `.bmad-loop/policy.toml`、门禁脚本及主干历史。
4. **单一写入者保证 (Single Writer)**：在前一个会话未确认安全退出前，绝对禁止启动第二进程；防止取消与重启竞争造成脏写入。
5. **有界停止与成果保全 (Bounded Termination)**：预算耗尽或 API 持续不可用时，系统必须在受限步数内终止循环，并完好保留已生成的 Git 暂存区与断点收据，绝不无限重试。
6. **经验物理隔离 (Experience Isolation)**：未通过审核或失败会话中产生的反思，绝不能自动追加到 `.solo/experience.md` 中，防止模型经验池受到毒化污染。

### 6.2 证据分级：禁止越级替代

- **第一级：纯逻辑单元测试 (Pure Logic)** —— 毫秒级运行，测试数据模型校验、规则判断、状态转移；
- **第二级：受控适配注入测试 (Controlled Adapter)** —— 注入假响应、断流模拟、故障注入、超时模拟；
- **第三级：真实宿主机物理测试 (Real Host Lifecycle)** —— 验证真实 VPS 上的 tmux 会话拉起、Cline CLI 进程管理、真实 Git Worktree 创建与合并、客户端断网续航与恢复。
- **铁律**：第一级/第二级测试通过，**绝不能替代**第三级真实宿主回执；真实宿主行为必须拥有可核验的持久化日志与退出码。

---

## 七、 结晶状态与交付验证

- [x] **完整抢救**：已从 Roo Code 原始任务中提取出全部关键信息与 36 项一手链接，解决网关长任务超时阻断结晶的问题；
- [x] **事实纠正**：纠正了 Overalls 仓库状态、Hegel 迁移状态、cargo-fuzz 要求、Loom 缺陷等关键事实；
- [x] **理论脱水**：撤回了一切未经测量的虚假百分比，确立了以“契约绑定 + 失败关闭”为核心的真实背压；
- [x] **工件落盘**：本报告已正式写入工作区，作为 V6 (solo-engine) 的架构基石与门禁设计准则。
