# The 4 Anti-Paralysis Convergence Locks

## The Threat: Analysis Paralysis & Endless Optimization
AI-assisted technical analysis frequently collapses into infinite cycles of:
- "We could also handle this 0.001% edge case..."
- "What if we add one more layer of indirection for future extensibility?"
- "Let's redesign the whole architecture to make it more elegant."

This produces hundreds of lines of speculative markdown, delays delivery, and demoralizes engineering. The 4 Convergence Locks are mechanical guardrails designed to force termination and hand off to code.

---

## Lock 1: The Non-Goals Lock (Scope Capping)
- **Mandate**: In Pass 1 of any analysis, the agent **MUST explicitly state at least 3 Non-Goals (Out of Scope)**.
- **Rule**: If a proposal cannot articulate what it refuses to do, it is incomplete.
- **Enforcement**: Any feature or edge case identified later that falls under a Non-Goal is instantly rejected without debate.

## Lock 2: The Hard Gates Cut (Instant Disqualification)
- **Mandate**: Real-world constraints (team expertise, delivery deadline, hosting budget, existing invariants) are non-negotiable.
- **Rule**: A candidate that fails a hard gate is immediately cut. Do not spend time debating its theoretical elegance.
- **Enforcement**: Cap active candidates at 3–4 maximum.

## Lock 3: Novelty Exhaustion (Diminishing Returns Cutoff)
- **Mandate**: A round of critique or questioning ends the moment it fails to produce a **new, load-bearing architectural fact**.
- **Rule**: If the third or fourth counter-argument is merely a stylistic variation of an already documented risk, halt analysis immediately.
- **Enforcement**: Do not exceed 2 critique rounds on the same component.

## Lock 4: Minimal Sufficient Solution Verdict (The Stop-and-Ship Gate)
- **Mandate**: Software engineering seeks the *minimal sufficient* solution that solves the user's problem within architectural invariants.
- **Rule**: Once an option earns a `FEASIBLE` or `CONDITIONALLY_FEASIBLE` rating, **STOP PROPOSING ENHANCEMENTS**.
- **Enforcement**: Emit the final verdict, record residual trade-offs in `brain/task.md`, and mandate execution:
  ```
  Verdict: FEASIBLE
  Action: Stop analysis. Begin implementation via /bmad-solo.
  ```
