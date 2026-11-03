# Minimum Synthetic Comparison v1

> Accepted Track C contract, Issue #49.
> Decision: [ADR-0010](../adr/0010-minimum-comparison-and-simulation-evidence.md).

## Purpose and public boundary

Delivery A is a synthetic closed-initial-cash comparison, not complete M4 or
household affordability. Exactly four alternatives are attempted: SAC v3,
Price v3, rent plus investment and one explicit consortium v1 scenario.
SAC/Price share one financing request. No probabilities, weights, secondary
objectives, monthly resources, borrowing or reinvestment policies are inferred.
Rent alone has explicit investment allocation, contributions and return.
Financing/consortium cash receives no return. These limitations are sealed.

The frozen Python types in domain/comparison.py are SharedComparisonInput,
ComparisonConstraints, ComparisonRequest, ComparisonSimulationEnvelope,
ConstraintViolation, ComparisonMetrics, AlternativeComparison and ComparisonResult.

- calculate_comparison_v1(request, *, data_snapshot_id, calculated_at) explicitly
  creates a simulation and decodes its immutable result or global DomainFailure.
- create_comparison_v1_envelope(*, raw_request_jcs, data_snapshot_id, calculated_at)
  returns evidence sealing a success or canonical semantic global failure.
- replay_comparison(envelope) reexecutes the retained authority and returns the
  verified result or failure; no stored-outcome fallback.

The calculation object has exactly shared, constraints, financing, rent and
consortium. The latter three contain complete existing request fields including
optional fields/default declarations emitted by their dataclasses. Consortium
tuples serialize as arrays. No projection, caller ledger or computed result is
accepted instead. Missing/unknown top-level or shared fields fail globally.

The shared object has exactly comparison_opening_cash (nonnegative BRL),
property_price and starting_monthly_rent (positive BRL),
rent_adjustment_rate_value, rent_adjustment_rate_convention (effective_annual)
and first_rent_adjustment_month (actual integer greater than one).
Constraints has exactly required nonnegative BRL minimum_liquidity and
maximum_monthly_housing_outflow, without financial defaults.
The fixed objective is maximize_net_worth_at_month_60.

## Admission and shared evidence

These limits apply only to new comparison inputs, not historical/live children:

| Input | Representation |
| --- | --- |
| Money | Optional sign, 1..18 ASCII integer digits, exactly two fractional digits |
| Rates | Fixed decimal 0..1, at most 12 fractional digits, no exponent |
| Contractual term_months | Strict integer 1..600 |

Do not cap calculated amounts or apply the term cap to other month fields.
Out-of-envelope child values yield comparison-owned invalid_input admission,
not a claim that their financial rules are unsupported.

Opening cash must match every alternative numerically. Purchase price matches
financing/consortium. Rent terms match the rent alternative; each parseable,
correctly positioned waiting amount matches shared projected rent through
min(contemplation_month,60). Shared projection is independent of investment
viability; it uses retained rent posting semantics without fake cash or
partial failed-alternative output.

Conventions are nominal BRL, centavos, ROUND_HALF_UP and closing months 0..60.
Inflation, appreciation, correction and transaction costs retain current support
exclusions. Full schedules do not assert cash feasibility after 60. New child
execution uses an explicit Decimal context with precision 28 and default traps,
sufficient for exact admitted input relationship sums; posted financial
arithmetic remains version-owned rational/integer arithmetic.

## Creation, metadata and versions

The factory wraps the supplied canonical calculation object in a canonical
request containing exactly comparison and metadata. Metadata has:

- supplied data_snapshot_id matching [A-Za-z0-9][A-Za-z0-9._-]*;
- supplied calculated_at, a valid UTC YYYY-MM-DDTHH:mm:ssZ;
- fixed timezone America/Sao_Paulo, metadata only.

No system clock or timezone conversion is consulted. Header, canonical request
and sealed outcome carry identical metadata, checked on replay. The envelope
fields are contract_schema_version, engine_version, ruleset_version,
data_snapshot_id, calculated_at, timezone, raw_request_jcs and sealed_outcome_jcs.

| Authority | Schema | Engine | Ruleset |
| --- | --- | --- | --- |
| Comparison | comparison-simulation-v1 | comparison-minimum-v1 | comparison-ruleset-v1 |
| Rent | rent-plus-replay-v1 | rent-plus-fixed-cash-v1 | rent-plus-ruleset-v1 |
| SAC/Price | financing-replay-v3 | financing-centavo-safe-v3 | financing-ruleset-v2 |
| Consortium | consortium-replay-v1 | consortium-explicit-schedule-v1 | consortium-ruleset-v1 |

Financing v1/v2 remain historical replay only for new comparison admission.
Comparison pins retained child modules, never live calculators. Rent retains
normalization/calculation separation and early cash-failure order.

Evidence preserves child raw requests/outcomes/versions, normalized shared data,
classifications, assumptions, constraints, conventions and limitations.
Shared target price is projected, financing price contractual, consortium
purchase price projected. Cash/rent retain observed-data classifications while
the reference basis remains explicitly synthetic. Constraints are user choices.

Snapshot metadata is supplied lineage, not authentication. Consistent rewriting
of all evidence is not cryptographically detectable. No persistence, export,
attestation or private-case validation is added.

## Failure precedence

1. Factory rejects malformed, duplicate-key, non-object, noncanonical or
   out-of-codec JSON and invalid metadata with ValueError, without an artifact.
   The pinned closed JCS codec accepts strings, safe integers, booleans, null,
   arrays and objects; it rejects float/nonfinite numbers and unpaired surrogates.
2. Validate global shared data and constraints.
3. Check all well-typed shared projections before child support failures.
   Divergence seals global invalid_input. Missing/illegible child fields instead
   fail that child's admission without hiding other shared mismatches.
4. Explicit structural/numeric preflight precedes retained child evaluation.
   Admission evidence retains original raw input and admission_failure, without
   fabricated child outcomes. Consortium unknown clauses reach its retained
   support rejection. Existing financial failure precedence is preserved.
5. Apply constraints and objective only to complete successful ledgers.

Unexpected execution exceptions propagate during creation, never becoming
financial exclusions. Canonical global semantic failures seal and replay.
Unknown tuples, malformed evidence, failed reexecution or any complete-outcome
mismatch fail replay as incompatible_contract_version, without fallback.

## Constraints, metrics and ordering

Complete ledgers require cash>=0 and liquidity>=floor at closing months 0..60,
and housing cash outflow<=cap at months 1..60. Equality passes.
Housing outflow is full financing payment; consortium contractual payment plus
waiting and posted top-up; or rent only. Investment transfers and noncash events
are excluded. Down payment/allocation at0 use cash/reserve without monthly cap.
Violations list all failed months in constraint order cash, reserve, outflow,
then ascending month.

Alternatives are eligible, constraint_infeasible with metrics/violations, or
domain_failure with safe code/detail and no fabricated metrics/rows.
Trace retains common ledger and housing outflows. Metrics include the final
ledger row (net-worth operands, equity, liabilities and cumulative cost), minimum
liquidity and every attaining month, maximum outflow and every attaining month.

Eligible groups sort by exact integer-cent networth60 descending. Equal scores
tie without tolerance or secondary objective. Stable presentation order is
SAC, Price, rent, consortium. Status is compared, single_eligible or no_eligible;
the last has empty groups. One eligible is not claimed superior to exclusions.
No future contemplation property/top-up or post-60 viability is anticipated.

## Verification and mandatory next gate

Independent small references protect metrics/ties/exclusions; complete hashes
captured before rent extraction prevent circular adapter comparisons.
Admission, cent/horizon boundaries, failure precedence, immutable/context-free
results and exact tamper/version success/failure replay complement existing QA.
Keep M0 fixture bytes, both CI jobs and combined 95% domain coverage unchanged.

Before family-use B, separately define and approve income versus expenses
versus available resources, equality between alternatives, posting order,
surplus, feasibility and versioned child semantics. No fixed-income field is
preapproved. Never overlay resource flows after child ledgers. B requires its
own application/API/Next.js contract and approval, with investment asymmetry
visible beside highlighted results. Sensitivity, break-even, optimization,
private data and additional financial-rule support remain excluded.
