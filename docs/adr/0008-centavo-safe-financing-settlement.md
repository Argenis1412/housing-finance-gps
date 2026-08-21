# ADR-0008: Define centavo-safe financing settlement and fee availability

- **Status:** Accepted
- **Date:** 2026-08-20
- **Owners:** Project maintainers
- **Related work item:** Issue #36

## Context

Retained v1 and v2 SAC and Price evaluators can post an amortization larger
than the remaining posted principal for accepted low-centavo inputs. Their
historical traces can therefore contain a negative principal balance before
their final settlement row. The live v1 Price path can raise while attempting
to post interest from that negative balance.

ADR-0007 admitted a fixed monthly fee only through v2 entry points and its
v2 replay handler. A centavo-safe successor must support the same admitted
fee without creating two incompatible authorities for fee availability.

## Decision

This ADR supersedes ADR-0007 as the policy for future fixed-monthly-fee
availability. ADR-0007 remains the historical record of the retained v2
contract: v2 envelopes, evaluator, entry points, outputs, and replay behavior
remain unchanged.

For an explicitly selected v3 contract, this ADR amends ADR-0005's
absent-clause and explicit-zero preservation requirement only where that
requirement would force v3 to reproduce v1 or v2 settlement. The ADR-0005
requirement remains unchanged for retained v1 and v2 entry points, outputs,
envelopes, and replay; all other ADR-0005 admission requirements remain in
force for v3.

The fixed monthly fee is admitted through explicit version-owned entry points
and replay handlers only:

- v1 retains its historical positive-fee `unsupported_contract_clause`;
- v2 retains the fixed-fee semantics and identifiers defined by ADR-0007; and
- v3 admits the same non-negative, exact-two-fraction nominal BRL fee under
  the settlement policy in this ADR.

Version selection occurs before request normalization and is never inferred
from financial values. Fee absence and `fee_amount="0.00"` are financially
equivalent within the selected version. No envelope, live result, or request
is automatically migrated or reinterpreted as another version.

The v3 identifiers are:

- `contract_schema_version=financing-replay-v3`;
- `engine_version=financing-centavo-safe-v3`; and
- `ruleset_version=financing-ruleset-v2`.

For each non-final v3 schedule row, calculate and post interest from the
opening posted balance, calculate the selected SAC or Price regular
amortization, then post:

```text
amortization = min(
    regular_amortization,
    max(opening_principal_balance - R$0.01, R$0.00),
)
```

Recalculate payment from posted interest, the capped amortization, and the
separate fixed fee. The final row amortizes its complete opening balance,
closes at R$0.00, and posts the fee. Every v3 schedule has exactly
`term_months` rows. The v3 comparison ledger is derived only from those posted
values and never records a negative financing principal balance.

The v3 evaluator owns parsing, validation, normalization, calculation,
canonical outcome generation, and ledger construction. It does not repair or
transform a v1 or v2 trace.

## Consequences

### Positive

- New v3 financing calculations settle safely without shortening a contract.
- Fee availability has one current policy while historical v2 evidence stays
  executable and immutable.
- The selected replay handler remains the sole authority for its version.

### Negative

- A v3 calculation may intentionally differ from v2 for a fee-free or
  explicit-zero request when the centavo reserve applies.
- The retained v1/v2 defect remains visible in historical replay rather than
  being silently corrected.

### Neutral or operational

- The v3 fee retains v2 ownership: it is paid monthly, separately classified,
  reduces cash through payment, and contributes to nonrecoverable housing
  cost.
- The common ledger remains neutral and owns only derived identities.

## Compatibility and migration

Historical v1 and v2 envelopes must remain byte-equivalent and replay through
their existing handlers. A v3 envelope uses only the v3 schema/engine/ruleset
tuple. Unknown or mixed version tuples fail as `incompatible_contract_version`.
There is no persistence migration, API migration, or automatic recalculation.

## Verification

- Preserve byte-sensitive v1/v2 envelope regressions for successes, failures,
  and the low-centavo counterexamples.
- Verify v3 SAC and Price schedules for the low-centavo boundary, positive
  fee, absent fee, and explicit-zero fee.
- Cover one to fifty centavos, terms one to sixty, rates `0.0000` and
  `0.0001`, and fee absent or R$0.01 with schedule and ledger identities.
- Verify v3 codec, replay dispatch, tamper failure, term-one, and term-600
  boundaries.

## Deferred decisions

- Variable or indexed fees, insurance, transaction costs, taxes, indexation,
  extraordinary amortization, and eligibility rules.
- Persistence migrations and public API contracts.
