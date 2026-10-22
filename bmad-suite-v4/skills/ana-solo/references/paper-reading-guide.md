# Academic Paper & Technical Spec Reading Guide (Three-Pass Approach)

参考 S. Keshav 的三遍阅读方法，服务于当前工程决策；按问题裁剪阅读深度，不要求穷尽所有风险。下文时间仅为人工阅读参考，不是已耗时记录或工具执行预算。

遵循顶层分析权限：不使用终端、不创建或执行探针、不写生产文件。只读任务仅会话交付，不持久化、不运行验证、不转正或归档。必要实测明确问题、范围、环境前提与验收，另交获准工程入口，不自动启动。

---

## 🐦 Pass 1: Bird's-Eye View (5–10 minutes)
**Goal**: Rapidly grasp category, context, and structural integrity. Decide whether the paper is worth a deep dive.

Read: Title, Abstract, Introduction, Section Headings, and Conclusion.
Answer the **5Cs**:
1. **Category (类别)**: What type of paper/document is this? (Empirical measurement, systems prototype, algorithmic proof, survey, or architectural RFC?)
2. **Context (背景)**: Which prior works or existing open-source ecosystems is this grounded in? What theoretical foundations are assumed?
3. **Correctness (正确性)**: Do the initial hypotheses and experimental bounds appear physically sound?
4. **Contributions (贡献)**: What are the genuine, novel contributions (versus cosmetic reframing)?
5. **Clarity (清晰度)**: Is the presentation well-structured, mathematically sound, and readable?

**Pass 1 Decision**:
- `PROCEED`: The paper offers load-bearing techniques applicable to our task.
- `SKIM_ONLY`: Extract only specific formulas or references; do not read deeply.
- `ABANDON`: Flawed assumptions, unreplicable claims, or out-of-scope.

---

## 🔍 Pass 2: Content & Causal Grasp (30–60 minutes)
**Goal**: Grasp main thrust, diagrams, and evidence without drowning in line-by-line mechanical proofs.

1. **Figure & Graph Audit**:
   - Inspect all charts, state diagrams, and benchmark plots.
   - Do axes have proper units and logarithmic/linear scales?
   - Are error bars or statistical significance tests present?
   - Do the curves prove the author's claim, or merely an incidental correlation?
2. **Unread Key References**:
   - List the 1–3 foundational papers cited repeatedly that must be understood to interpret this work.
3. **证据核对**：
   - 追踪输入、处理与输出指标的因果链，区分用户陈述、论文或源码事实、真实实测回执、逻辑推断、反证与未知。
   - 核对重要数字与实验适用范围，不把相关性、论文声明或源码存在当作当前环境实测通过；没有对照测量时不承诺效果。
   - 缺必需证据只阻塞依赖它的裁决，不要求所有假设先实测；比较存活候选，评分须有依据，证据不足则定性比较。

---

## 🧠 Pass 3: Virtual Re-Implementation & Adversarial Critique
目标：虚拟重实现与当前采用决策相关的部分，寻找足以改变裁决的隐式前提和反例；推演不冒充物理实测，不无限补证。

1. **Virtual Implementation**:
   - Mentally reconstruct the system from the description.
   - Where would your code get stuck? What parameters, hyperparameters, or edge cases did the authors omit?
2. **关键隐式假设**：
   - 按实际风险识别未说明的资源、时序、故障与兼容性前提，不固定数量。
3. **相关失败场景与反证**：
   - 定位足以影响采用决策的失败边界，不为无关极端场景扩张范围；新增阅读不再改变裁决时停止，保留必要未知与下一步。
4. **Focal Points for Engineering Adoption**:
   - Identify the exact formulas, invariants, and state transitions needed if adopting this into production code.
