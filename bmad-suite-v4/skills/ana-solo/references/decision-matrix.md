# Candidate Selection & Decision Matrix (The Select Shape)

Inherited from Deep Recon's selection methodology. Use when choosing between 2–5 competing architectural paths, libraries, or technologies.

---

## 1. Requirements Frame
Before researching any candidate, lock the evaluation criteria.

- **Hard Gates (One-Strike Disqualification)**:
  - Must-haves: compliance, existing stack language, strict latency budget, maximum licensing cost, deployment environment.
  - *Rule*: Any candidate violating a hard gate is eliminated immediately.
- **Weighted Preferences**:
  - Nice-to-haves: developer ergonomic, community size, documentation, release velocity.
  - Assign explicit percentage weights (total 100%).

---

## 2. Candidate Screening (Cut to 3–5)
- Assemble candidates: Category leader, established challenger, lightweight alternative, optional wildcard.
- Apply hard gates. Record which candidates were eliminated and why.
- Screen strictly to 2–4 finalists. Never evaluate 10 candidates simultaneously.

---

## 3. Weighted Scoring Matrix

| Criterion | Weight | Candidate A (Score 1–5) | Candidate B (Score 1–5) | Candidate C (Score 1–5) |
|---|---|---|---|---|
| Hard Gate: Compatibility | Mandatory | Pass | Pass | Fail (Eliminated) |
| Performance / Throughput | 30% | 4 (1.2) | 5 (1.5) | - |
| Operational Complexity | 25% | 4 (1.0) | 2 (0.5) | - |
| Community & Health | 20% | 5 (1.0) | 4 (0.8) | - |
| Migration & Exit Cost | 25% | 4 (1.0) | 3 (0.75) | - |
| **Weighted Total** | **100%** | **4.2** | **3.55** | **Eliminated** |

*Note: Cite exact evidence or source benchmark for any contested score.*

---

## 4. Verdict & Reversibility Hedge

Output exactly:
1. **The Pick**: Clear winner with highest weighted score and zero hard gate failures.
2. **The Runner-Up**: Second place candidate.
3. **Trigger Conditions for Pivot**: Under what exact condition (e.g., traffic exceeds 100k QPS, or team hires Rust engineers) should the team pivot to the runner-up?
4. **Cheapest Reversibility Hedge**: What simple abstraction layer or seam will allow switching without rewriting the application?
