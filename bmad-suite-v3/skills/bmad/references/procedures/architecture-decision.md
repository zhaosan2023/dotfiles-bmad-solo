---
name: bmad-architecture-decision
description: >
  Produce or update an architecture decision record (ADR).
  Self-contained — does not depend on external scripts.
---

# Architecture Decision Procedure

## Objective
Make a structural decision and record it as an Architecture Decision Record (ADR) that binds future implementation. Use this when there are multiple viable technical paths and the choice has system-wide impact.

## Context

Read the following before starting:
1. `_bmad-output/project-context.md` (if exists)
2. `_bmad-output/architecture/architecture-contract.yaml` (if exists)
3. The specific problem or task description.

## Process

1. **Elicit, don't guess:** If the user hasn't specified the constraints, ask open-ended questions about scale, team, and existing ecosystem. Don't invent constraints.
2. **Weigh alternatives:** Identify at least two viable approaches. Compare them against the project context.
3. **Draft the ADR:** Write a concise ADR document. Focus on *what* is decided and *why*, not a tutorial on the technology.
4. **Save the ADR:** Save the result to `_bmad-output/architecture/decisions/ADR-YYYYMMDD-[topic].md`.

## ADR Format

Use this template for the output:

```markdown
# ADR-[Date]-[Topic]

## Status
Proposed | Accepted | Rejected | Superseded

## Context
What is the problem we are solving? What are the constraints?

## Decision
What is the specific, actionable decision?

## Rationale
Why did we choose this over the alternatives? What trade-offs did we accept?

## Consequences
What becomes easier? What becomes harder? Are there new risks or verification obligations?
```

## Post-Decision
If the decision alters the components, invariants, or data ownership of the system, you must update `_bmad-output/architecture/architecture-contract.yaml` (or note the need to do so if it hasn't been created yet).
