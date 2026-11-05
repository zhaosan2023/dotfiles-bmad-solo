# 外部参考资料与理论基准 (External References)

本目录归档项目所依赖或借鉴的外部核心学术文献、技术标准与规范。

---

## 1. FastCode 论文

- **文件路径**: [FastCode-arXiv-2603.01012v2.pdf](FastCode-arXiv-2603.01012v2.pdf)
- **论文题目**: *FastCode: Fast and Cost-Efficient Code Understanding and Reasoning*
- **作者机构**: Zhonghang Li, Zongwei Li, Yuxuan Chen, Han Shi, Jiawei Li, Jierun Chen, Haoli Bai, Chao Huang (The University of Hong Kong, Huawei Noah's Ark Lab)
- **arXiv 链接**: [arXiv:2603.01012v2 [cs.SE]](https://arxiv.org/abs/2603.01012)
- **代码仓库**: [https://github.com/HKUDS/FastCode](https://github.com/HKUDS/FastCode)
- **归档日期**: 2026-10-29

### 方法借鉴与证据限制

- 本工程借鉴探索与消费分离、轻量导航和问题相关正文选择；方法映射见[历史架构分析](../../_bmad-output/analysis/ANALYSIS-20261029-fastcode-scouting-architecture.md)，本轮未重新研读全文或核验出版元数据。
- [Schema 3.0 决策的理论边界](../../_bmad-output/adrs/ADR-20261030-harel-fastcode-schema-v3.md:222)明确双重表示及层次化抽象属于设计启发，不证明完整论文算法、运行时目标解析或状态图语义已经实现。
- 本工程的正文、完整请求、解码帧和累计传输限额属于项目契约，不是论文给出的统一 100 KB 保证；不同计量层不得混称。
- 历史容量失败不等于已证明的并发死锁。新表示、预算或期限是否解决具体失败，须关联对应版本的真实运行证据。
- 性能目标属于工程观测指标；两篇资料不能推出预检必须在固定秒数内完成。

## 2. Harel 层次化抽象资料

- [本地资料](statement_harl87.md)保留原始文件名，供相关决策按需引用。
- 聚类与视距缩放用于设计启发；函数聚合不是完整状态图语义实现，也不是耗时或并发安全保证。
- 本轮仅整理定位和措辞，不重新验证全文、作者信息、外部网址或实验结论。

### 关联分析文档
- 详细研读与算法映射报告参见：[_bmad-output/analysis/ANALYSIS-20261029-fastcode-scouting-architecture.md](../../_bmad-output/analysis/ANALYSIS-20261029-fastcode-scouting-architecture.md)

---

## 3. Sparks of Weight-Space Programming (Astra 权重空间编程)

- **本地资料**: [astra-weight.md](astra-weight.md)
- **核心来源**: MIT CSAIL 研究博客 (*Sparks of Weight-Space Programming*)
- **在线链接**: [https://rikiyat.github.io/blog/weight-space-programming/](https://rikiyat.github.io/blog/weight-space-programming/)
- **理论借鉴**:
  - 阐明前沿大模型利用确定性 Python REPL 探针（SVD / 范数）直接推演连续权重结构并完成 0.016% 定点外科手术的机制；
  - 建立“探针侦察 (Probing) $\rightarrow$ 拓扑追踪 (Tracing) $\rightarrow$ 最小充分定点操作 (Action)”的通用范式，与 FastCode 及 solo-distill-mcp 的 AST 结构蒸馏形成数学对偶；
  - 区分物理 KV Cache 前缀复用与认知回音室自激（Self-Conditioning），为无状态清洁上下文（Clean-Context）提供证据背书。

---

## 4. RSIHub 与智能体宪法（AGENTS.md）演化体系

- **本地资料**: [RSIhub-agent-paper.md](RSIhub-agent-paper.md)
- **主论文来源**: *RSIHub: A Composable Framework for Agent-Evolution Methods* ([arXiv:2610.32253v1](https://arxiv.org/abs/2610.32253))
- **代码仓库**: [https://github.com/simple-agent-lab/RSIHub](https://github.com/simple-agent-lab/RSIHub)
- **理论借鉴**:
  - 策略与评估彻底解耦（Policy-Runtime Decoupling），7 阶段生命周期槽位（Select $\rightarrow$ Rollout $\rightarrow$ Analyze $\rightarrow$ Mutate $\rightarrow$ Guardrail $\rightarrow$ Evaluate $\rightarrow$ Absorb）；
  - 数据三阶隔离（Train / Gate / Sealed）与表面白名单检查（CHECKSURFACE），防范模型自我欺骗与盲测集（Held-out）退化；
  - 支撑 AGENTS.md 自动演化的 6 篇核心前沿顶会/arXiv 文献（ACE ICLR 2026、Configuration Smells arXiv:2606.15828、Evaluating AGENTS.md arXiv:2602.11988、AGIT-Template arXiv:2611.02383、AHE arXiv:2604.25850、Agent READMEs arXiv:2511.12884）；
  - 奠定 Tmux 4+1 多角色物理隔离架构（Orchestrator, Scout, Coder, Breaker, Curator），根除多轮交互中的 Prompt Caching 击穿与 Lint Leakage 坏味道。
