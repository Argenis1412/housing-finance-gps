# ADR-0003: Define monthly money, rate, rounding, and ledger conventions

- **Status:** Accepted
- **Date:** 2026-08-18
- **Owners:** Project maintainers
- **Related work item:** Issue #5

## Context

The MVP compares strategies with different contractual mechanics. Without one currency, rate, period, rounding, and ledger convention, valid implementations can produce incompatible schedules, cash flow, liquidity, and net-worth outputs. The product vision requires deterministic calculations and a common monthly timeline.

## Decision drivers

- Deterministic reconciliation at centavo precision.
- Comparable monthly strategy outputs.
- Explicit unsupported behavior instead of financial approximation.

## Considered options

1. Allow each strategy to define its own money and rounding behavior.
2. Use binary floating-point values and presentation-only rounding.
3. Use nominal BRL decimal values, effective supported rates, posted centavo balances, and one common ledger.

## Decision

Adopt option 3. Financial contracts use nominal BRL decimal strings, one-based monthly periods, effective monthly financing and capital-return rates, effective annual rent adjustment, and ROUND_HALF_UP posted centavo ledger values. The prior posted balance is authoritative for the next period.

The common ledger defines mutually exclusive financing and consortium credit liabilities, property and credit-right assets, cash, liquid assets, and non-recoverable housing cost. The full contract is in [financial contracts](../specifications/financial-contracts.md).

## Consequences

### Positive

- Reference schedules can use zero-centavo deterministic checkpoints.
- Comparison metrics share one documented accounting identity.
- Unsupported financial conventions fail before producing a result.

### Negative

- Initial coverage is deliberately narrower than real-world proposals.
- Future rate or cost support requires an ADR and regression evidence.

### Neutral or operational

- The 60-month comparison horizon and full financing schedule are separate time domains.

## Compatibility and migration

None. No financial implementation or stored simulation exists.

## Verification

- Review SAC and Price row order against the contract.
- Later add independent reference schedules, invariants, and boundary tests.
- Review ledger conservation around financing purchase and consortium contemplation transitions.

## Deferred decisions

- External rate conversion, correction, taxes, fees, and insurance.
- Property-value assumptions and future-purchase behavior.
- Financial rule coverage beyond the documented initial case.
