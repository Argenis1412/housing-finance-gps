# ADR-0005: Require explicit admission for financing extensions

- **Status:** Accepted
- **Date:** 2026-08-19
- **Owners:** Project maintainers
- **Related work item:** Issue #21

## Context

SAC and Price currently support only the fixed-principal, effective-monthly-rate
contract. Positive financing fees, insurance amounts, and requested nonzero
indexation fail as `unsupported_contract_clause`; the currently accepted
explicit-zero declarations remain exclusions. The rent-plus-investment
foundation and the neutral common ledger are implemented, but they do not
define semantics for additional financing clauses.

The product requires deterministic financial results and reproducible
historical simulations. A future financing clause can change payments, cash,
cumulative housing cost, liabilities, or net worth even when its request shape
does not change. An input representation or an impact assessment alone cannot
admit that behavior safely.

## Decision drivers

- Preserve the supported SAC and Price contract and typed failure boundary.
- Prevent a contractual clause from changing financial results without
  deterministic semantics, ledger treatment, and versioned replay.
- Keep the common ledger neutral while allowing future strategy-owned balance
  transitions.

## Considered options

1. Admit a clause when its input can be parsed deterministically.
2. Require only a documented assessment of its contract and version impact.
3. Require explicit financial semantics, compatibility evidence, versioned
   replay, and approved admission before implementation.

## Decision

Adopt option 3. Fees, insurance, and requested nonzero indexation remain
`unsupported_contract_clause`. Their current explicit-zero declarations remain
accepted exclusions. This ADR admits no new financing behavior.

Before a future financing extension may be implemented, its approved Track C
work item and admission record must define all of the following for each
admitted variant:

- input and output units, the monetary or rate basis, and every applicable
  rate, index, or correction convention; an observed external index must also
  identify its independent source, period, retrieval date, effective date, and
  snapshot;
- contractual periods, effective and anniversary dates, posting order,
  calculation basis, and `ROUND_HALF_UP` centavo posting points;
- whether and how the clause changes cash, a financing balance, property
  value, recoverable transfer, or nonrecoverable housing cost; `domain/ledger.py`
  remains the neutral owner of common rows and derived identities;
- supported ranges and variants, invalid-input boundaries, and typed failures
  for every requested but unadmitted variant; and
- independent synthetic references and deterministic regression evidence for
  each admitted variant.

That work item must demonstrate that SAC and Price preserve current behavior
when the clause is absent and when each currently accepted explicit-zero
declaration is supplied: `transaction_cost_amount="0.00"`,
`fee_amount="0.00"`, `insurance_amount="0.00"`,
`extraordinary_amortization_amount="0.00"`, and
`indexation="documented_zero"`. It must also preserve the typed rejection of
non-admitted variants.

Any admitted clause that changes a posting or result must declare and apply its
required `engine_version` and/or `ruleset_version` impact. The implementation
must preserve replay of simulations produced under prior versions. If an
extension introduces observed external data, it must assess and apply the
required `data_snapshot_id` treatment before calculation. No version change is
made by this documentation-only decision.

The recommended next work item is a separately approved, fees-only Track C
admission proposal. It must meet this ADR before implementation. Insurance and
nonzero indexation remain deferred.

## Consequences

### Positive

- Future clauses cannot silently alter SAC or Price results.
- Existing absent-clause and explicit-zero inputs remain protected
  compatibility cases.
- Historical replay remains an admission requirement when results change.

### Negative

- A future extension requires more evidence than a new input field or a
  ledger classification alone.

### Neutral or operational

- `domain/financing` will own future financing-clause semantics and schedule
  transitions; this ADR does not change that ownership or the ledger owner.
- A future implementation determines its precise version values only through
  its approved admission record.

## Compatibility and migration

No current API, persistence, simulation envelope, domain behavior, or stored
simulation changes. A future admitted extension that changes postings or
results must apply the version and replay requirements in this decision before
it is released.

## Verification

- Review the admission record against every required semantic, ledger,
  compatibility, failure, version, replay, and reference-evidence condition.
- Verify SAC and Price compatibility for absent clauses and all currently
  accepted explicit-zero declarations.
- Verify new admitted variants against independent synthetic references and
  typed failures for unsupported variants.

## Deferred decisions

- The contractual semantics and implementation of financing fees.
- Insurance and nonzero indexation semantics and implementation.
- Transaction costs, extraordinary amortization, taxes, and eligibility-rule
  support.
