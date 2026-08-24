---
name: bmad-architecture-baseline
description: >
  Establish or verify the architecture baseline for a project by extracting
  components, dependencies, and invariants from code, tests, and documents.
---

# Architecture Baseline Procedure

## Objective
Extract a machine-checkable architecture contract from the current project reality. This forms the normative state that subsequent tasks must respect.

## Process

1. **Scan the Project**: Read codebase structure, configuration files, and existing architecture docs.
2. **Identify Components**: Map the major components (e.g., frontend, backend API, domain layer, database adapters).
3. **Map Dependencies**: Determine which components depend on which. Identify allowed and forbidden dependency directions (e.g., domain must not depend on infrastructure).
4. **Identify Data Ownership**: Determine which components own specific data entities and state.
5. **Extract Invariants**: Formulate strict rules (invariants) that must not be broken. Determine a verification method for each.
6. **Generate Contract**: Create or update `_bmad-output/architecture/architecture-contract.yaml` using the contract template.

## Rules
- Do NOT guess. If something is unverified, mark it as `UNKNOWN`.
- Code reality > outdated documentation.
- The first time this contract is generated, it MUST be presented to the user for explicit confirmation before proceeding.
