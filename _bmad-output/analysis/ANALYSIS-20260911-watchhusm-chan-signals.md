# ANALYSIS-20260911-watchhusm-chan-signals

## 1. Executive Summary & Verdict

**Verdict: `CONDITIONALLY_FEASIBLE` (有条件可行，需立即执行双轨解耦与公式收敛)**

### 核心结论与战略定位
`WatchHUSM` 项目通过将**缠论微结构拓扑**（中枢、分型、结构止损）与**非线性动力学相空间分析**（局域 Lyapunov 指数 $\lambda_U$、Hurst 粗糙度 $H$、阻尼动量 $\xi$、内生信息时钟 $\tau$）相结合，具有极高的买方量化工程价值。
然而，**当前系统绝不能作为独立、自动开仓的 Alpha 交易机器人**。其真实且唯一的战略定位是：
> **`缠结构动力学风险覆盖层 (Risk Overlay) + 影子特征候选管道 (Shadow Alpha Feature Pipeline)`**

### 四大高维字段核心病灶诊断 (The Core Malady)
当前系统中 `"P状态 | 寿命 | 匹配度 | 建议"` 在公式转换与实盘可信度上的崩塌，根源在于**物理量纲错配、正交范畴坍塌、先验统计幻觉、以及分析层越权越界**：
1. **寿命 (Lifespan)**：遭遇**量纲湮灭**。将内生信息时钟预算 $B = \tau_{\text{budget}}$ 通过 $k = \operatorname{round}(B)$ 伪装成物理 K 线数，隐含了流动性流速 $g \equiv 1.0$ 的荒谬假设，在主升浪放量 ($g=4$) 时导致持有时间放大 400%，在缩量冰点 ($g=0.25$) 时提前 75% 误杀。
2. **匹配度 (Match Degree)**：遭遇**先验高斯核塌缩**。硬编码先验中心 $(\mu_x=0.5, \mu_\xi=1.0)$，直接计算欧氏距离高斯核，缺乏黎曼度量与样本外（OOS）后验概率校准，却以 `0.95` 等形式输出，赋予交易员虚假的“胜率”认知。
3. **P状态 (P-State)**：遭遇**正交状态范畴坍塌**。将“数据准入(P0)”、“执行与结算约束(P1)”、“相空间硬破位(P2)”、“时钟耗尽(P3)”、“动量衰减(P4)”和“主升跃迁(P5)”混入单标量枚举。在 A 股 $T+1$ 限制下，P2 破位因不可卖被冲刷为 P1，导致**退出锁存义务丢失**。
4. **建议 (Advice)**：遭遇**决策链越界越权**。在未接入真实账户资金、流动性冲击、组合行业暴露及净收益模型的前提下，轻率输出“安全开仓”，产生严重合规风险与回测未来偏差。

---

## 2. Keshav Three-Pass: Deep Deconstruction (深度解构)

### Pass 1: 5C Baseline (概念基线)
- **Category (系统范畴)**：基于因果时序流与离散相空间重构的微结构动力学状态机监控系统。
- **Context (业务场景)**：上游对接行情数据库及缠论选股快照（`fbuylist`），盘中以 1m 推进高频风险行情、60m 推进低频动力学重计算，下游通过 Telegram Bot 输出告警。
- **Correctness (计算保真度)**：虽然修复了数组别名与自除以自身的阻断 Bug，但仍存在内生时间映射到物理时间、高斯核非平稳性以及状态机单标量覆盖的理论缺陷。
- **Contributions (核心价值)**：构建了无量纲偏离度 $x$ 与相速度阻尼 $\xi$；引入局域 Lyapunov 估计量 $\lambda_U$ 刻画拓扑破裂；提出了基于信息流速的内生时间框架。
- **Clarity (语义清晰度)**：严重不足。未将“物理几何测量”、“执行约束”与“投资决策”解耦。

### Pass 2: Causal & Evidence Firewall (因果与证据防火墙)

> **启动 Lock 1: Non-Goals Lock (明确界定 3 项不可逾越的非目标)**
> 1. **非目标 1 (拒绝黑箱化与过早强化学习)**：严禁在基础物理量纲和时钟状态机尚未数学严密前，引入强化学习 (FinRL) 或深度神经网络试图“自动修复”。
> 2. **非目标 2 (拒绝全局李雅普诺夫物理妄念)**：严禁将局域发散率 $\lambda_U$ 宣称为金融资产的“真实物理李氏指数”。金融时间序列是受外生宏观驱动、非平稳、具有跳跃特征的强耗散微观系统。
> 3. **非目标 3 (拒绝未校准状态下的新增风险授权)**：在未建立样本外扣费（佣金、印花税、滑点、T+1锁定、涨跌停）净值检验与 DSR 检验前，严禁授予 WatchHUSM 任何实盘自主开仓权限。

#### 证据防火墙因果核验 (Evidence Checks)
- **因果流速隔离**：动态量比 $vr$ 与流速因子 $g_m$ 必须满足因果律（Causality）：区间 $m$ 的流速必须在区间开始前生效，严禁使用收盘后的日成交量或未来 K 线反向修订已消耗的内生时钟。
- **Fail-Closed 纪律**：当 Hurst 粗糙度不可辨识 ($R^2 < 0.6$ 或 $H \notin (0.1, 0.9)$) 或 Lyapunov 轨迹对不足时，必须输出 `lifetime_status = UNIDENTIFIABLE, tau_budget = null`，严禁回退填充假寿命（如 `8k/2d`）。

### Pass 3: Virtual Re-Implementation: 四大字段隐性坑点剖析

```
                ┌─────────────────────────────────────────────────────────┐
                │                    WatchHUSM 动力学数据流                │
                └────────────────────────────┬────────────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       ▼                                           ▼
          【内生信息流 τ (流速 g)】                   【相空间动力学 (x, ξ, λ_U)】
                       │                                           │
         ┌─────────────┴─────────────┐               ┌─────────────┴─────────────┐
         ▼                           ▼               ▼                           ▼
    ［公式缺陷 1］               ［公式缺陷 2］  ［公式缺陷 3］               ［公式缺陷 4］
   内生时间 τ 坍塌为          标量 P 状态混淆       硬编码静态高斯核             分析层越权生成
   物理 Bar (g≡1 谬误)       退出锁存丢失 (T+1)     伪概率认知摩擦              "安全开仓" 毒性标签
         │                           │               │                           │
         ▼                           ▼               ▼                           ▼
   【寿命: 4x~0.25x 扭曲】      【P状态: 破位逃逸失败】 【匹配度: 0.95 胜率假象】     【建议: 诱导高风险踩坑】
```

#### 1. 寿命 (Lifetime) 公式转换缺陷
- **物理机理**：根据哈密顿摄动与近可积系统发散理论，相空间状态有效寿命取决于误差球半径从初始分辨率 $\epsilon_0 = c_\epsilon 8^{-H}$ 膨胀到破裂半径 $R$ 的发散速度：
  $$\tau_{\text{budget}} = \frac{\ln(R / \epsilon_0)}{\lambda_U}$$
  此 $\tau$ 是**内生交易时间 (Endogenous Time)**：$d\tau = g(t) dt$，其中 $g(t)$ 为微观信息流速（量比或波动率流速）。
- **当前致命转换**：代码中直接执行 `k_bars = int(round(budget))`，且在评估时按物理 Bar 步数扣减：
  $$\text{remain\_k} = \text{locked\_end} - \text{current\_seq}$$
- **灾难后果**：
  - **流动性爆发（主升段 $g \approx 4.0$）**：市场在 1 根 60m Bar 内消耗了 4 个单位的动力学寿命，但系统只扣减 1 根 Bar，导致持仓时间拉长为理论寿命的 **400%**，在动能耗尽后惨遭滞留与高位崩塌。
  - **流动性冰点（震荡洗盘 $g \approx 0.25$）**：价格尚未充分展开信息流，物理时间却已流逝，系统过早触发 P3 超时强平，错失后续行情。

#### 2. 匹配度 (Phase Match) 公式转换缺陷
- **当前代码公式**：
  $$\text{dist}^2 = \left(\frac{x_{\text{slow}} - 0.5}{1.5}\right)^2 + \left(\frac{\xi_{\text{slow}} - 1.0}{1.5}\right)^2$$
  $$\text{match} = \exp\left(-0.5 \cdot \text{dist}^2 \cdot \operatorname{clip}(\sqrt{vr}, 0.5, 2.0)\right) \quad (\text{if } \xi > 0 \text{ else } 0)$$
- **灾难后果**：
  - **先验中心虚构**：凭什么所有股票、所有缠论形态（一买背驰、二买确认、三买中枢突破）的最优动力学中心都刚好是 $x=0.5$（拉伸 0.5 倍 ATR）和 $\xi=1.0$？这完全是未经实证的臆想。
  - **伪置信度认知欺诈**：高斯核输出一个 $[0, 1]$ 之间的标量，Telegram 输出 `0.95`。交易员和跟单程序会下意识将其视作“95% 胜率”或“模型信心 95%”。然而这仅仅是一个几何距离倒数，未经任何 Platt Scaling 或保序回归（Isotonic Regression）校准，与未来实际盈亏（$R_{\text{net}} > 0$）毫无概率同构性。

#### 3. P状态 (P-State) 状态机缺陷
- **当前实现**：单标量枚举 `NONE`, `ENTRY`, `P0`, `P1`, `P2`, `P3`, `P4`, `P5`。
- **灾难后果**：
  - **正交状态坍塌**：在买方量化交易中，“是否有破位退出义务”与“当前账户能否执行（如 A 股 T+1、涨跌停、滑点限制）”是两个绝对正交的维度。
  - **锁存状态丢失**：当某标的触发 P2 破位，但账户由于当日买入不可卖（$T+1$）时，`decide()` 返回 `P1 (锁存P2；可执行数量受限)`。在下游展示或粗粒度接收器中，系统状态变成了 `P1`，导致 P2 风险特征被清洗。一旦次日开盘行情跳空暴跌，系统缺乏不可撤销的持续性退出锁存（Latched Exit Obligation），引发巨大回撤。

#### 4. 建议 (Advice) 应用可信度缺陷
- **当前表现**：直接在消息末尾输出 `"安全开仓"`、`"拓扑破裂；市价平仓"`。
- **灾难后果**：
  - **“安全”二字的毒性**：在量化金融中不存在任何“安全”的买点。实测数据显示，甚至在 $RR=0.7$、动态量比极低时依然能触发“安全开仓”。
  - **越权耦合**：状态机是物理和风险测算器，不是全自动投资组合管理器（Portfolio Manager）。没有结合资金利用率、行业集中度风险、个股流动性容纳度（Capacity），直接发出开仓指令，违反买方风控分层体系。

---

## 3. Strategic Application Value (策略应用价值定位)

### 物理动力学与买方架构的深度交汇
在非线性动力学物理视角下，金融市场可以看作**处于多重分形噪声扰动下的近可积哈密顿系统**。
- **缠论中枢**：构成了相空间中的**拟周期 KAM 环面 (Invariant Tori)** 或吸引子结构；
- **破位与背驰**：代表轨道穿越共振网发生拓扑相变（Arnold 跃迁或逃逸）；
- **动量阻尼比 $\xi$ 与局域 Lyapunov $\lambda_U$**：直接度量了局部流形的发散速度与能量耗散率。

### 价值边界划分

| 维度 | 具备明确价值的应用（Allowed & High Value） | 伪命题/存在重大缺陷的应用（Forbidden & Toxic） |
| :--- | :--- | :--- |
| **风险管理 (Risk Overlay)** | **确定性退出防守**：利用 $\lambda_U > 0.30$ 识别真实拓扑破裂，过滤假摔；利用 $\tau_{\text{rem}} \le 0$ 严格切断时间耗散。 | 用所谓“高胜率”或“相空间完好”去覆盖静态硬止损。 |
| **微结构过滤 (Quality Gate)** | **伪突破过滤器**：利用量比 $vr$、动量方向 $\xi$ 剔除虚假缠结构买点（0.3x 缩量阴跌点火）。 | 将动力学状态直接视作 Alpha 因子进行无约束下注。 |
| **时钟预算 (Clock Budget)** | **内生生命周期约束**：为每笔交易建立基于信息流的风险倒计时，避免资金在死滞标的中虚耗时间成本。 | 将 $\tau$ 转换为静态 K 线数并在日历时间上简单倒数。 |
| **投资指引 (Alpha Generation)** | **影子候选池排序**：作为二次排序特征（`PhaseScore`），为交易员提供拓扑共振参考。 | 在 Bot 侧直接提示“安全开仓”，充当未经审计的买卖决策黑箱。 |

---

## 4. Decision Matrix: 架构演进与字段重构方案决策

为了彻底根治四大字段的缺陷，评估以下三个候选方案：

### 候选方案定义 (Candidates)

- **Candidate A: 纯风险侧车剪枝方案 (Conservative Sidecar Risk Engine)**
  - *思路*：全面放弃 Alpha 幻想，将 WatchHUSM 严格降级为只读风险哨兵。
  - *重构*：彻底移除“开仓建议”与“P5 接力”；`P状态` 仅保留 `NORMAL`, `LATCHED_STOP`, `EXPIRED`；`寿命` 仅展示无量纲剩余预算 $\tau_{\text{rem}}$（不折算物理 Bar）；`匹配度` 改名为 `几何偏离度`（纯物理距离，不归一化到 0-1）；`建议` 仅输出风控指令（`EXIT_MANDATORY`, `HOLD`）。
- **Candidate B: 全量内生测度与校准 Alpha 完备重构方案 (Complete Endogenous Metric & Calibrated Alpha Overhaul)**
  - *思路*：完全践行 `docs/algomath_auditv4fable.md` 的理想化数学体系。
  - *重构*：构建连续因果 rate tape 流速积分引擎；对多市场状态训练保序回归校准模型（输出真正的 $P(\text{Profit} \mid \text{Filled})$）；重构全套事件驱动无未来函数回测系统与 DSR 检验；实现包含 Kelly 风险预算的仓位模块。
- **Candidate C: 双轨解耦架构：硬核风险闭环 + 影子特征流 (Dual-Track Decoupled Architecture) [RECOMMENDED]**
  - *思路*：兼顾买方量化工业落地效率与物理数学严谨性，实行“风险轨道”与“特征轨道”的**绝对双轨隔离**。
  - *重构*：
    1. **风险轨 (Track 1 - 确定性闭环)**：将 P 状态重构为正交位掩码（准入、执行、物理破位独立）；内生寿命引入稳健局部流速预测 $\hat{g}$，显示为 `内生预算 (预估k/d)`，物理投影只读，风险按 $\tau$ 执行；P2 触发即永久锁存，T+1 绝不稀释退出义务。
    2. **特征轨 (Track 2 - 影子与展示)**：匹配度重构为**横截面百分位共振分位数 (`Resonance Index` / `PhaseScore`)**，标明“仅供结构共振排序，非后验胜率”；建议字段降级为客观条件清单：`[准入门禁: 通过/受限] | [风控状态: 正常/破位/超时] | [共振就绪: 5维门禁达标/观望]`，彻底消灭“安全开仓”。

---

### Lock 2: Hard Gates Screening (硬性门禁筛选)

- **HG1: 无未来函数与因果单调性 (No-Lookahead & Causal Monotonicity)**
  时钟累计和流速不得倒灌未来数据；状态锁存必须单调不可逆。
- **HG2: 风险优先与退出不可覆盖 (Risk Precedence & Non-Overridable Exit)**
  模型故障、数据缺失、或高匹配度均绝对不得豁免或覆盖 P2/P3 退出。
- **HG3: 单兵量化工程交付周期 (Solo Engineering Feasibility $\le 2$ Iterations)**
  必须在现有 Python 异步事件循环与 Docker 容器内低风险落地，避免陷入长期算法研发泥潭。

**门禁筛选结果**：
- **Candidate A**：通过 HG1、HG2、HG3。但丢弃了全部潜在 Alpha 排序价值，导致前期在缠论微结构上投入的研究完全无法反哺交易选股。
- **Candidate B**：通过 HG1、HG2。**未通过 HG3 (CUT)**。在单兵架构下，从零构建多状态保序回归校准、完整订单簿回放与实盘仓位分配器需要数月时间，违反 Anti-Paralysis 原则。
- **Candidate C**：**全票通过全部硬门禁**。在现有代码上解耦成本最低，既消灭了数学与可信度风险，又保留了量化选股共振排序功能。

---

### 决策打分矩阵 (Decision Scoring Matrix: A vs C)

权重设置原则：物理量纲严谨性 (25%)、风控闭环与防暴跌 (25%)、工程防未来落地性 (20%)、交易决策信息量 (15%)、人机认知清晰度 (15%)。

| 评估维度 (Dimension) | 权重 (Weight) | Candidate A: 纯风险剪枝 | Candidate C: 双轨解耦架构 (推荐) | 评分理由与事实依据 |
| :--- | :---: | :---: | :---: | :--- |
| **物理量纲严谨性 (D1)** | 25% | 85 (21.25) | **92 (23.00)** | C 方案建立了连续内生时钟与稳健流速投影 $\hat{g}$ 的清晰界限；A 方案仅显示无量纲 $\tau$，交易员无法建立时间直觉。 |
| **风控闭环与防暴跌 (D2)** | 25% | 90 (22.50) | **95 (23.75)** | 两者均实现正交锁存，但 C 方案通过相空间拓扑破裂判据与 P2 永久锁存结合，有效区分假摔与崩塌。 |
| **工程落地可行性 (D3)** | 20% | **95 (19.00)** | 90 (18.00) | A 方案改动代码最少；C 方案需改造 `build_view` 与 `decide` 状态解耦，但完全在当前代码结构承载范围内。 |
| **策略演进与排序价值 (D4)** | 15% | 40 (6.00) | **90 (13.50)** | A 方案无法为交易员提供标的选择依据；C 方案输出横截面百分位 `PhaseScore`，为日内调仓提供客观排序。 |
| **认知清晰度与去伪存真 (D5)**| 15% | 80 (12.00) | **95 (14.25)** | C 方案彻底剥离“安全开仓”与“胜率假象”，代之以透明门禁清单，消除了所有虚假承诺。 |
| **加权总分 (Total Score)** | **100%** | **80.75** | **92.50 (WINNER)** | **Candidate C 显著胜出** |

---

## 5. 胜出方案（Candidate C）高维字段重构蓝图与数学规范

### 1. 「P状态」重构规范：正交状态张量与兼容展示

```
底层存储：正交状态结构体 (Orthogonal State Struct)
{
  "model_status": "IDENTIFIABLE" | "DEGRADED" | "UNIDENTIFIABLE",
  "admission": "ALLOWED" | "REJECTED",
  "execution_constraint": "NONE" | "T_PLUS_1_LOCKED" | "HALTED",
  "risk_latch": "NONE" | "P2_BREAK" | "P3_EXPIRED" | "P4_DISSIPATED",
  "setup_signal": "NONE" | "IGNITION_CANDIDATE" | "RELAY_CANDIDATE"
}
```

- **兼容展示映射契约 (`p_state_display`)**：
  1. 若 `risk_latch == "P2_BREAK"` $\rightarrow$ 统一显示 **`🚨破位`**（无论当前是否有持仓、无论是否 T+1 锁定，严禁退化为 P1）；
  2. 若 `risk_latch == "P3_EXPIRED"` $\rightarrow$ 统一显示 **`⏰超时`**；
  3. 若 `risk_latch == "P4_DISSIPATED"` $\rightarrow$ 统一显示 **`📉耗散`**；
  4. 若 `model_status != "IDENTIFIABLE"` $\rightarrow$ 显示 **`🚫异常`**；
  5. 若无风险锁存且满足点火 5 维物理门禁 $\rightarrow$ 显示 **`🔥点火`**；
  6. 若现价突破中枢目标且 $\lambda_U \le 0.25$ $\rightarrow$ 显示 **`🚀接力`**；
  7. 其他情况 $\rightarrow$ 显示 **`观察`**。

### 2. 「寿命」重构规范：全局内生时钟与稳健物理投影

- **风险执行时钟（唯一权威）**：
  $$\Delta \tau_m = g_m \Delta b_m, \quad \tau_m = \tau_{m-1} + \Delta \tau_m$$
  $$D_{\text{root, new}} = \min(D_{\text{root, old}}, \tau_{\text{asof}} + B_a)$$
  $$B_{\text{remaining}, m} = \max(0, D_{\text{effective}, m} - \tau_m)$$
  $$\text{expired}_m = \mathbf{1}_{\{B_{\text{remaining}, m} \le 0\}}$$
- **展示投影（仅供人类阅读，禁止回写风控字段）**：
  利用最近 $M=12$ 根 5m Bar 的稳健中位数流速 $\hat{g}_{\text{local}} = \operatorname{clip}(\operatorname{median}(g), 0.25, 4.0)$：
  $$k_{\text{est}} = \left\lfloor \frac{B_{\text{remaining}}}{\hat{g}_{\text{local}}} \right\rfloor, \quad d_{\text{est}} = \max\left(1, \left\lceil \frac{k_{\text{est}}}{4} \right\rceil\right)$$
  - **展示格式**：`14k/4d (τ:8.2)`。当模型不可辨识时，坚决输出 `-`，杜绝任何虚构寿命。

### 3. 「匹配度」重构规范：相空间共振指数 (Resonance Index)

- **去概率化声明**：禁止将该字段称为 Confidence、胜率或置信度。统一命名为 **`共振度 (Resonance)`** 或 **`PhaseScore`**。
- **动态标准化公式**：
  $$\text{dist}_{\mathcal{M}} = \sqrt{ \left(\frac{x - \mu_x(t)}{\sigma_x(t)}\right)^2 + \left(\frac{\xi - \mu_\xi(t)}{\sigma_\xi(t)}\right)^2 }$$
  - 其中 $\mu, \sigma$ 由该品种过去 60 根有效微结构的滑动窗口提供，而非全局硬编码；
  - 阻尼惩罚：若 $\xi \le 0$（相空间动能逆转杀跌），共振度直接平滑衰减至 0：
  $$\text{Resonance} = \mathbf{1}_{\{\xi > 0\}} \cdot \exp\left(-0.5 \cdot \text{dist}_{\mathcal{M}} \cdot \sqrt{\operatorname{clip}(vr, 0.5, 2.0)}\right)$$
  - **展示约定**：标明 `0.85 (共振)`，附录声明：*“本数值表示当前相空间与历史有效结构的几何共振度，仅供选股优先序参考，非样本外胜率。”*

### 4. 「建议」重构规范：解耦动作与客观门禁清单

- **全面废除所有承诺性词汇**：坚决移除 `"安全开仓"`、`"建议市价平仓"`。
- **结构化输出契约**：
  - **点火达标（未持仓）**：`满足点火门禁(待仓位核验)`（需同时满足：无风险锁存 + 空间盈亏比 $\ge 1.5$ + 距止损 $\le 2.5\text{ATR}$ + $vr \ge 1.0$ + 日内同向）；
  - **破位状态（有持仓）**：`拓扑破裂(执行清仓义务)`；
  - **破位状态（受限/T+1）**：`拓扑破裂(T+1受限锁定中)`；
  - **价格破位但相空间拓扑完好**：`价格刺破止损(相空间完好;密切观察反抽)`；
  - **超时状态**：`内生寿命耗尽(执行时间止损)`；
  - **常规状态**：`观察`。

---

## 6. The 4 Anti-Paralysis Convergence Locks (反瘫痪收敛闭环)

1. **Lock 1 (Non-Goals Lock) [PASSED]**：已锁死三项非目标（不搞黑箱 RL、不求全局物理李氏指数、不放任未校准自动开仓）。
2. **Lock 2 (Hard Gates Cut) [PASSED]**：已淘汰过度理想化、工程周期超标的 Candidate B。
3. **Lock 3 (Novelty Exhaustion Stop) [PASSED]**：已完全穷尽四大字段在物理数学、数据时钟和状态机层面的 load-bearing 事实，无需进一步理论探寻。
4. **Lock 4 (Minimal Sufficient Verdict) [PASSED]**：选定 Candidate C，给出 `CONDITIONALLY_FEASIBLE`，立即终止纯理论研讨，进入工程交付。

---

## 7. Handoff to `/bmad-solo` (执行桥接)

### 推荐实施任务分解 (Task Breakdown)
- **Phase 1: 字段语义与数学量纲修正 (`watchingbot/integration.py`)**
  - 修正内生时间与物理 Bar 投影计算逻辑，剔除 $k = \operatorname{round}(B)$ 错误；
  - 重写高斯核函数，消除硬编码先验；将 `phase_match` 更名为几何共振指数；
  - 移除所有 `"安全开仓"` 文本，替换为状态门禁字符串。
- **Phase 2: 状态机正交化与 P2 退出锁存加固 (`watchingbot/integration.py` & `core.py`)**
  - 引入正交字段，确保 P2 破位触发时即使 `available_qty == 0` 也保持退出锁存，不可被 P1 覆盖；
  - 编写针对 T+1 跨日破位的防回归单元测试。
- **Phase 3: Telegram 展现层重构 (`watchingbot/core.py`)**
  - 更新表头说明与字段展示格式，对 `寿命` 附带内生预算 $\tau$，对 `建议` 实施合规化展示。

---

### Handoff to /bmad-solo

To proceed to engineering implementation, simply run `/bmad-solo` with:
```text
Implement approved proposal from _bmad-output/analysis/ANALYSIS-20260911-watchhusm-chan-signals.md
```
