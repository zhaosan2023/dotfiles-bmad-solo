---
name: bmad-three-pass-analysis
description: >
  Deep structured scheme and proposal deconstruction procedure synthesizing
  Keshav Three-Pass reading, Deep Recon evidence convergence, and 4 anti-paralysis locks.
---

# Three-Pass Scheme Analysis Procedure

## Objective

Prevent both shallow superficial summaries and endless philosophical over-engineering. Deconstruct any technical proposal, paper, or architectural design through divergent structural stress-testing, followed immediately by strict boundary convergence to a minimal sufficient solution.

## Triggers

- User presents a technical proposal, architectural plan, or academic paper for review.
- An M or L task introduces architectural alternatives, third-party frameworks, or nontrivial design choices.
- Explicitly called via `/ana-solo`.

## Process

### 1. Pass 1: Bird's-Eye Qualitative Scan (5C + Non-Goals Lock)
- **Category (类别)**: Architectural refactoring, pipeline migration, new feature subsystem, or academic algorithm? (Map to S/M/L).
- **Context (上下文)**: Dependencies on current codebase, external services, or foundational theories.
- **Correctness (正确性)**: Are initial foundational assumptions plausible?
- **Contributions (增量价值)**: What tangible problem does this actually solve?
- **Clarity (清晰度)**: Is the boundary clearly stated or vague?
- **[Lock 1 - Non-Goals 铁律]**: Must explicitly state at least **3 items that are Out-of-Scope**. Stop boundary bloat before it begins.

### 2. Pass 2: Evidence & Structural Verification
- **Data Flow & Causality**: Do inputs, transformations, and outputs form a closed causal loop?
- **State Machine / Topology**: Are there orphan states, race windows, or cyclic dependencies?
- **Empirical Evidence**: Are performance, throughput, or benchmark claims supported by real measurements or references? (No naked assertions).
- **Hard Gate Screening [Lock 2]**: Does the proposal violate team stack, time horizons, or unfeasible infrastructure? If yes, cut the violating branch immediately.

### 3. Pass 3: Virtual Re-Implementation & Implicit Assumption Stress-Test
- **Virtual Implementation Check**: If coding began immediately, where is the exact point the developer would get blocked?
- **Top-3 Killer Assumptions (隐式假设挖掘)**: What unstated preconditions does this proposal quietly rely on? (Limit strictly to the top 3 most lethal, ignore trivial ones).
- **Top-3 Failure Modes (破坏性推演)**: What are the 3 most realistic scenarios where this crashes under production load?
- **Novelty Exhaustion Check [Lock 3]**: Has this round revealed new load-bearing facts? If not, halt questioning immediately.

### 4. Convergence & Verdict [Lock 4]
Synthesize findings into an actionable verdict. Never leave the output as an open-ended debate.

---

## Output Report Format

Output exactly this structure (and save to `_bmad-output/analysis/ANALYSIS-YYYYMMDD-[topic].md` if persistent):

```markdown
# Scheme Analysis: [Topic / Proposal Name]

## 1. Pass 1: 5C Qualitative Baseline
- **Category**: [Type & Level: S/M/L]
- **Context**: [System dependencies & existing constraints]
- **Correctness**: [Plausibility of core hypothesis]
- **Contributions**: [True incremental value vs. overhead]
- **Clarity**: [Boundary clarity score: High / Medium / Low]
- **Locked Non-Goals (Out of Scope)**:
  1. [Explicitly not doing X]
  2. [Explicitly not doing Y]
  3. [Explicitly not doing Z]

## 2. Pass 2: Structural & Evidence Verification
- **Causal Flow / Topology**: [Valid | Gap identified: ...]
- **State & Invariants**: [Clean | Risk: ...]
- **Evidence Backing**: [Verified | Anecdotal | Unsubstantiated]

## 3. Pass 3: Virtual Re-implementation & Stress-Test
- **First Implementation Roadblock**: [Specific file/interface/algorithm hurdle]
- **Top-3 Lethal Implicit Assumptions**:
  1. [Assumption 1]
  2. [Assumption 2]
  3. [Assumption 3]
- **Top-3 Failure Modes**:
  1. [Scenario 1]
  2. [Scenario 2]
  3. [Scenario 3]

## 4. Convergence & Verdict
- **Recommended Path**: [Chosen minimal sufficient path]
- **Key Trade-off Accepted**: [What is sacrificed for simplicity/speed]
- **Cheapest Reversibility Hedge**: [Seam / abstraction to pivot if wrong]

### Verdict: [FEASIBLE | CONDITIONALLY_FEASIBLE | REJECT]

**Required Next Action**:
- If `FEASIBLE`: Proceed immediately to `/bmad-solo` Architect Preflight & Task Implementation. No further proposal debates.
- If `CONDITIONALLY_FEASIBLE`: Record mitigations in `brain/task.md` or ADR, then proceed to Preflight.
- If `REJECT`: Hard conflict identified. Halt and request direction or discard candidate.
```

---

## Verdict Rules

- **FEASIBLE**: Proposal solves the core need with manageable complexity. **Stop optimizing.** Hand off to Architect Preflight.
- **CONDITIONALLY_FEASIBLE**: Acceptable with specific hedges or constraints recorded. Proceed to Architect Preflight with mitigations noted.
- **REJECT**: Fails a hard gate, fundamentally breaks architecture invariants, or benefits do not justify the blast radius. DO NOT PROCEED TO CODING.
