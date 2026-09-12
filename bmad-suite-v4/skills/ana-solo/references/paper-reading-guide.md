# Academic Paper & Technical Spec Reading Guide (Three-Pass Approach)

Based on S. Keshav's classic *Three-Pass Approach*, adapted for engineering decision-making.

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
3. **Evidence Verification**:
   - Trace the causal chain from input data → processing pipeline → output metrics.

---

## 🧠 Pass 3: Virtual Re-Implementation & Adversarial Critique
**Goal**: Virtually re-implement the paper mentally from scratch. Find every hidden pitfall.

1. **Virtual Implementation**:
   - Mentally reconstruct the system from the description.
   - Where would your code get stuck? What parameters, hyperparameters, or edge cases did the authors omit?
2. **Top-3 Hidden Assumptions**:
   - What unstated conditions make this work (e.g., unlimited memory, zero clock skew, single-node failure limits)?
3. **Top-3 Failure Scenarios**:
   - Under what production conditions will this design fail catastrophically?
4. **Focal Points for Engineering Adoption**:
   - Identify the exact formulas, invariants, and state transitions needed if adopting this into production code.
