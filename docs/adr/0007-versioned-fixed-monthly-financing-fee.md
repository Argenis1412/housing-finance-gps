# ADR-0007: Admit a versioned fixed monthly financing fee

- **Status:** Superseded by ADR-0008
- **Date:** 2026-08-19
- **Owners:** Project maintainers
- **Related work item:** Issue #31

## Context

SAC and Price historically support a fixed-principal, effective-monthly-rate
contract. A non-zero `fee_amount` is rejected under v1 and that rejection is
part of retained replay evidence. A fixed monthly fee changes cash, payment,
and non-recoverable housing cost while leaving principal and interest
semantics unchanged.

## Decision

Admit the fee only through explicit v2 live entry points and a versioned replay
handler. The existing v1 entry points and evaluator remain unchanged. Version
selection occurs before normalization and is never inferred from financial
values.

The admitted fee is a non-negative nominal BRL amount with exactly two
fractional digits, posted once in contractual months `1..term_months`. It is
separate from principal, interest, amortization, property value, and
liabilities. Total payment is interest plus amortization plus fee; cash is
reduced by that posted amount; non-recoverable housing cost is interest plus
fee. Aggregate postings use `ROUND_HALF_UP`.

The v2 identifiers are:

- `contract_schema_version=financing-replay-v2`;
- `engine_version=financing-fixed-principal-v2`;
- `ruleset_version=financing-ruleset-v1`.

The v2 evaluator owns version-specific parsing, validation, normalization,
calculation, and canonical outcome generation. Live v2 entry points project
that outcome and do not implement separate formulas. Replay selects the
handler before interpreting request or outcome contents. Unknown handlers,
invalid evidence, and mismatches fail as `incompatible_contract_version`.

## Compatibility

v1 absence and explicit zero retain their historical shape and values. A v1
positive fee remains `unsupported_contract_clause`. v2 absence and
`fee_amount="0.00"` have identical v2 financial values and always include a
versioned zero `fee` field. v1 and v2 result types are not structurally
interchangeable.

Negative or malformed fees return `invalid_input`. Variable, indexed,
insurance, transaction-cost, extraordinary-amortization, tax, eligibility,
and other variants remain unadmitted.

## Consequences

The new behavior requires independent synthetic references, v1 regression
replay, v2 codec tests, and explicit live entry-point tests. No external data,
ruleset change, persistence migration, API, frontend, or CI change is part of
this admission.
