# ADR-0009: Admit explicit consortium schedules and retained v1 replay

- **Status:** Accepted
- **Date:** 2026-11-03
- **Owners:** Project maintainers
- **Related work item:** Issue #47; antecedents #5 and #7

## Context

M0 defines a synthetic consortium credit-right transition but no executable
contract. Real proposals may change installments at contemplation, correct the
letter, refund a reserve, or allocate bids differently. Parseable numbers do
not admit those clauses. The user approved a narrow synthetic first version
after AC challenge and independent adversarial review.

## Decision drivers

- Preserve the common ledger and exact posted-centavo conservation.
- Separate contractual values from projected contemplation and housing costs.
- Reject unsupported clauses without interpreting a real proposal.
- Retain executable historical successes and failures.

## Considered options

1. Infer installments, correction or contemplation dates from generic terms.
2. Add only an ephemeral projection, deferring historical reproduction.
3. Require a complete fixed schedule, explicit scenario, support declarations
   and a dedicated retained in-memory evaluator and replay contract.

## Decision

Adopt option 3 under the [financial contract](../specifications/financial-contracts.md#simplified-consortium-contract).
The supported proposal declares that credit contributions apply to the letter,
correction is zero, reserve payments are nonrecoverable without refund, and
installments do not change upon contemplation. The full schedule must reconcile
to the letter; the engine never repairs it. Administration, reserve and
insurance are supplied amounts, not inferred percentages or legal coverage.

Each execution selects `early`, `intermediate` or `late` and an explicit month.
Labels do not calculate dates or establish ordering between executions. There
are no probabilities or bid-success claims. Purchase follows that month's
contribution and explicit waiting housing cost. Delayed purchase is unsupported.

The new runtime spelling `cash_top_up` refines M0's documentary `cash_bid`,
which described only a purchase-price complement. V1 does not accept that old
key or model an actual bid. This explicitly replaces the old alias and its
out-of-period infeasibility rule for consortium v1; no previous consortium
runtime, wire schema or historical evaluator exists to migrate. The existing
M0 numeric fixture remains unchanged.

One version-owned standard-library evaluator is authoritative for normalization,
the full contractual schedule, 60 monthly postings and the common 61-row ledger.
It uses integer centavos for exact sums and differences of already posted
values, consistent with the `ROUND_HALF_UP` contract. There is no fractional
calculation to round or dependency on the caller's Decimal context. Thin live
projections decode its trace into immutable values and `ComparisonLedgerRow`.
The evaluator retains its codec and accounting identities rather than importing
mutable live helpers. Financing evaluators and interfaces remain unchanged.

V1 versions are `consortium-replay-v1`, `consortium-explicit-schedule-v1`, and
`consortium-ruleset-v1`. A dedicated immutable envelope records canonical raw
input, explicit `data_snapshot_id`, versions and one complete sealed success or
failure. Replay checks the version tuple before parsing, reexecutes the retained
evaluator and compares the complete canonical outcome exactly. Unknown versions,
malformed evidence and mismatches return `incompatible_contract_version`.
Malformed/noncanonical input cannot create an envelope; a canonical object with
invalid domain data can seal `invalid_input`. No stored-outcome fallback exists.

Cash feasibility and emitted balances cover only months 0..60. A later
contemplation creates no earlier property, obligation or top-up. Full-term
component reconciliation does not assert post-horizon cash feasibility or emit
future balance metrics. The snapshot identifier is supplied lineage metadata,
not source authentication. Complete real provenance remains private under the
existing governance contract; this version is a synthetic contract reference.

## Consequences

### Positive

- Exact cash, cost, credit-right and obligation transitions are auditable.
- Unsupported or conditional clauses cannot enter through a precomputed schedule.
- Replay protects successful and failed historical requests.

### Negative

- Most real proposals may remain unsupported.
- Version-owned validation and accounting logic must be retained for replay.

### Neutral or operational

- No HTTP, persistence, signing, comparator, frontend or new dependency.
- No new mechanical review-plan gate or planning report artifact.

## Compatibility and migration

Additive Python consortium boundary only. Existing financing/rent behavior,
replay and public contracts are unchanged. No prior consortium runtime exists.
Later semantic changes require an explicitly admitted successor while retaining
this evaluator. None of these identifiers rebrands the M0 fixture versions.

## Verification

- Exact existing M0 checkpoints and independent early/intermediate/late cases.
- Ledger/cash conservation, term and horizon boundaries, zero/shortfall cash.
- Invalid and unsupported declarations, conditional schedules and unknown keys.
- Context independence, immutability, bounded deterministic properties.
- Exact success/failure replay, canonical codec and tampered/versioned evidence.
- Existing complete QA, unchanged financing matrix and 95% total domain gate.

## Deferred decisions

- Admission of a real proposal, correction, bids, refunds or delayed purchase.
- Comparator M4, sensitivity, frontend, persistence and HTTP exposure.
- Periodic audit after the separately authorized consortium merge, counted as
  fifth after #32, #37, #38 and #40 by explicit user confirmation. Tooling-only
  #35 and #46 are excluded from this agreed count. Run no audit in preparation
  or implementation; record it in the existing reference before M4 behavior.
