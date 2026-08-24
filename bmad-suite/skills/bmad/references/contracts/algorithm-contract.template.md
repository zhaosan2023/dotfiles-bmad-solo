# Algorithm–Architecture Contract

## Problem
- **Objective**: 
- **Non-goals**: 
- **Exactness requirement**: [e.g., must be 100% exact, or approximation acceptable]
- **Reference behavior**: [how do we know it's right?]

## Placement
- **Owning component**: 
- **Why this component**: 
- **Allowed dependencies**: 
- **Prohibited dependencies**: 

## Data
- **Inputs and semantics**: 
- **Outputs and semantics**: 
- **Data owner**: [which component owns the state?]
- **Reads through**: 
- **Writes through**: 

## Invariants
- **Correctness**: 
- **Ordering/tie-breaking**: 
- **Idempotency**: 
- **Consistency**: 
- **Concurrency**: 

## Budgets
- **Expected input scale**: 
- **Time complexity**: 
- **Memory complexity**: 
- **I/O/network budget**: 

## Failure semantics
- **Invalid input**: 
- **Timeout**: 
- **Partial failure**: 
- **Stale data**: 
- **Retry/fallback**: 

## Verification
- **Reference implementation**: 
- **Unit examples**: 
- **Property tests**: 
- **Boundary tests**: 
- **Benchmark**: 
- **Architecture dependency test**: 

## Unresolved decisions
- ...
