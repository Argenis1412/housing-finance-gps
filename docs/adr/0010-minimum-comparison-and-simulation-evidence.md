# ADR-0010: Bind minimum synthetic comparison to retained simulation evidence

- **Status:** Accepted
- **Date:** 2026-11-03
- **Owners:** Project maintainers
- **Related work item:** Issue #49

## Context

The neutral ledger reconciles identities but does not establish shared inputs,
objective semantics or historical comparison evidence. HTTP financing emits
calculation projections, not simulation results. Consortium has retained
evidence; rent needs retained authority before historical comparison replay.
Current engines consume initial cash without monthly resources.

## Decision drivers

- Preserve child behavior and authoritative deterministic Python calculations.
- Reject inconsistent bases before ranking and expose funding/investment limits.
- Admit explicit in-memory evidence without HTTP or persistence changes.

## Considered options

1. Compare arbitrary ledgers or promote HTTP projections implicitly.
2. Add household income and a full UI before closing comparison semantics.
3. Deliver bounded synthetic evidence/comparison, then separately approve
   monthly resources before the family-use vertical slice.

## Decision

Adopt option 3 under the [minimum comparison contract](../specifications/minimum-comparison-v1.md).
Exactly SAC/Price v3, rent v1 and one explicit consortium v1 scenario share cash,
purchase price and rent/waiting conditions. User cash/reserve/outflow constraints
precede exact-cent networth60 groups. Ties remain equal and exclusions visible.

The explicit factory binds canonical inputs, classifications, assumptions,
child evidence and supplied metadata to a sealed success/failure. Replay
selects versions first and reexecutes the whole outcome, including groups.
The retained authority imports only standard-library facilities and explicitly
pinned retained child evaluators.

Rent moves to retained normalization/calculation with live dataclass adapters
preserving signatures, formulas and early cash failure. Independent waiting-rent
projection never precalculates the legacy path before that failure.
Comparison input admission borrows existing HTTP numerical limits without
narrowing child contracts. Preflight distinguishes admission from unexpected
execution errors; arbitrary evaluator exceptions are not financial exclusions.

## Consequences

### Positive

- Shared bases, constraints, exclusions and ties become reproducible evidence.
- Complete pre-extraction rent references detect semantic drift.
- Python remains authoritative for every metric and objective group.

### Negative

- Closed cash cannot represent general family affordability.
- Only rent invests; its explicit allocation/return influences ranking.
- Retained handlers and schemas must remain available historically.

### Neutral or operational

- No HTTP change, persistence, new dependency or cryptographic trust claim.
- Existing financing/consortium sources and fixture bytes stay unchanged.
- Budget: 14 files, 5 new modules (3 production / 2 tests), 12 new classes, one additive
  Python boundary and at most 32 new public module-level function/class/constant/
  type-alias names defined in the three new production modules, following
  ADR-0009's production API accounting; imports, methods, fields and test
  functions are excluded. Delivered counts are 23 public names and 10 classes.

## Compatibility and migration

Add comparison-simulation-v1/comparison-minimum-v1/comparison-ruleset-v1 and
rent-plus-replay-v1/rent-plus-fixed-cash-v1/rent-plus-ruleset-v1.
Preserve rent callable contracts/failure timing, financing v1/v2/v3 and
consortium v1 replay. No API/persistence migration or implicit projection promotion.

## Verification

Independent exact reference/tie/exclusion cases, complete pre-extraction rent
hashes including invalid/early-failure cases, admission/precedence/horizon
boundaries, context independence, immutable values, metadata/child/metric/group
tampering, exact aggregate replay and unchanged configured full QA.

## Deferred decisions

- Mandatory separate monthly-resources increment before B: income, expenses,
  available resources, posting order, surplus, feasibility and versioned child
  semantics. No ledger overlay or fixed-income field is admitted.
- B application/API/Next.js contract/approval and visible investment asymmetry.
- Sensitivity, break-even, optimization, persistence, real proposals/private case.
