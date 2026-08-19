# Milestone 0 Financial Contracts

> Status: accepted Milestone 0 contract
> Related ADRs: [ADR-0003](../adr/0003-money-rate-period-rounding-and-ledger.md), [ADR-0004](../adr/0004-backend-authoritative-financial-contracts.md)
> Related governance: [reference-case governance](reference-case-governance.md)
> Related issue: #5

## Purpose and scope

This document defines the deterministic financial boundary required before implementation. It specifies the initial supported contract for SAC financing, Price financing, simplified consortium, and rent-plus-investment. It does not implement formulas, define an HTTP schema, or add a reference fixture.

All values that do not meet this contract fail explicitly. No financial rule, proposal clause, rate convention, or cost may be silently approximated.

## Shared value and time conventions

| Concept | Initial contract |
| --- | --- |
| Currency | Brazilian real (BRL). Monetary inputs and outputs are decimal strings with two fractional digits. |
| Rates | Decimal strings. The only supported financing and capital-return convention is an effective monthly rate. Rent adjustment is an effective annual rate. |
| Period | A positive, one-based integer month. Month 0 is a financing purchase event only; it is not a schedule row. |
| Rounding | ROUND_HALF_UP to centavos for each posted monetary ledger value. Posted centavo balances are authoritative for the next period. |
| Comparison horizon | 60 monthly periods. This is distinct from a contractual financing term. |
| Value basis | Nominal BRL. Inflation, property appreciation, and correction require an explicit later contract; the initial supported value is zero where an applicable field exists. |

The engine uses deterministic decimal arithmetic. It does not obtain time, locale, exchange rates, index values, or other values from its environment.

## Common monthly ledger

Each strategy emits one row per comparison month with the following closing balances and classified flows:

| Element | Meaning |
| --- | --- |
| cash | Non-invested available cash after that period's flows. |
| liquid_financial_assets | Financial assets available without a modeled restriction. |
| consortium_credit_right_balance | Non-liquid, proposal-backed credit contributions accumulated before contemplation. |
| property_value | Modeled property value after an ownership event. |
| financing_principal_balance | Unpaid financing principal only. |
| consortium_credit_obligation_balance | Unpaid credit-letter obligation after contemplation only. |
| recoverable_transfer | Cash flow that changes an asset or liability but is not a housing cost. |
| nonrecoverable_housing_cost | Paid rent, interest, administration fee, reserve fund, insurance, or another explicitly classified non-recoverable housing cost. |

The two liability balances are mutually exclusive and exhaustive:

    total_liabilities = financing_principal_balance
                      + consortium_credit_obligation_balance

    net_worth = cash + liquid_financial_assets
              + consortium_credit_right_balance + property_value
              - total_liabilities

    home_equity = property_value - total_liabilities
    liquidity = cash + liquid_financial_assets
    cumulative_housing_cost = sum(nonrecoverable_housing_cost through period t)

Down payments, credit-letter application, principal payments, credit-component payments, and transfers into financial assets are recoverable transfers. They are never cumulative housing cost. Future obligations and future rent are not capitalized into a current ledger row.

## Financing contracts

### Shared financing boundary

SAC and Price use one strategy-neutral request and normalized input boundary.
The boundary owns the common monetary fields, the property-price relationship,
term validation, rate normalization, explicit-zero declarations, and canonical
failure classification. It also owns the immutable contractual-schedule row
and comparison-ledger row shared by both financing systems. A strategy may
expose compatibility aliases or wrappers, but neither financing system owns the
common input contract or imports the other strategy to normalize a request.

### Supported inputs

Both SAC and Price require:

- principal: positive BRL amount;
- term_months: positive integer;
- effective_monthly_rate: decimal rate greater than or equal to zero;
- property_price and cash_down_payment for the month-0 purchase event.

For the initial supported case, property_price equals cash_down_payment plus principal. FGTS, subsidies, transaction costs, taxes, insurance, fees, indexation, non-monthly rates, and extraordinary amortization are unsupported unless documented as zero.

At month 0, cash decreases by cash_down_payment, property_value increases by property_price, and financing_principal_balance becomes principal.

### Authoritative schedule order

For each financing month, the opening balance is the prior posted closing financing_principal_balance.

1. Calculate and post interest from opening balance and effective monthly rate.
2. Determine and post amortization.
3. Post payment as interest plus amortization.
4. Post closing principal as opening balance minus amortization.

Interest is the opening posted balance multiplied by the effective monthly rate,
then rounded. For SAC, regular amortization is the rounded principal divided by
term. For Price, principal and the effective monthly rate are converted from
their accepted decimal representations to exact rational operands. With a
non-zero rate, the regular installment is exactly
`principal * rate / (1 - (1 + rate)^(-term_months))`; with a zero rate, it is
exactly `principal / term_months`. In either Price case, the regular
installment is rounded once to centavos with `ROUND_HALF_UP`. There is no
intermediate Decimal-precision policy for the Price installment.

For Price, each non-final month's posted amortization is the posted regular
installment minus posted interest, and the posted closing principal is the
opening posted principal minus that amortization. In the final month for either
system, amortization equals the opening posted balance and payment equals final
interest plus that balance. The final posted principal balance is exactly 0.00
BRL.

## Simplified consortium contract

### Supported inputs

A consortium scenario requires a proposal-supplied monthly schedule, positive credit_letter, positive term_months, explicit contemplation month, and a property purchase event. Each schedule row classifies every amount as one of:

- credit_component;
- administration_fee;
- reserve_fund;
- insurance;
- cash_bid;
- another explicitly supported non-recoverable cost.

An unclassified amount, embedded bid, probabilistic contemplation date, undocumented monetary-correction clause, or contractual clause with no ledger treatment returns unsupported_contract_clause.

### Credit right and contemplation transition

Before contemplation, a credit_component increases consortium_credit_right_balance only when the proposal explicitly states that the contribution is applicable to the credit letter. The same amount decreases cash as a recoverable transfer. Administration, reserve, insurance, and other classified costs decrease cash and increase cumulative housing cost.

In the contemplation month, after that month's classified contribution is posted:

    property_price = credit_letter + cash_top_up
    property_value increases by property_price
    cash decreases by cash_top_up
    consortium_credit_right_balance becomes 0.00
    consortium_credit_obligation_balance = credit_letter - transferred_credit_right

The transferred credit right may not exceed the credit letter. Later applicable
credit-component payments reduce the consortium credit obligation as
recoverable transfers. A cash_bid is supported only as the cash_top_up in its
contemplation-month row; a cash_bid in another period is infeasible. It is a
recoverable transfer, not a housing cost. The contract does not infer legal
rights, group behavior, or bid success.

## Rent-plus-investment contract

The initial supported rent-plus-investment strategy requires:

- starting_monthly_rent: positive BRL amount;
- effective_annual_rent_adjustment: decimal rate greater than or equal to zero;
- first_rent_adjustment_month: an integer greater than one;
- initial_invested_capital: BRL amount greater than or equal to zero;
- monthly_contribution: BRL amount greater than or equal to zero;
- effective_monthly_net_return: decimal rate greater than or equal to zero.

Rent is a non-recoverable housing cost. Starting_monthly_rent applies before
first_rent_adjustment_month; the effective annual adjustment applies to the
posted rent in that month and every twelve months after it. Monthly return
accrues on opening liquid financial assets before the end-of-month contribution
is added. Taxes, investment-product rules, withdrawal restrictions, and a
future purchase are unsupported until separately contracted.

## Time domains and versions

The common ledger and comparison metrics stop after month 60. Financing schedules continue through term_months only to reconcile principal and financing totals; they do not extend common liquidity, home-equity, net-worth, or cumulative-cost comparisons beyond month 60.

Every eventual simulation envelope retains engine_version, ruleset_version, and data_snapshot_id under the private-reference provenance boundary. The private envelope and redacted attestation rules are owned by [reference-case governance](reference-case-governance.md).

## Failure contract

The future versioned API maps these stable machine-readable categories to safe Portuguese messages:

| Code | Meaning |
| --- | --- |
| invalid_input | A required value, unit, period, sign, or decimal representation is invalid. |
| unsupported_rate_convention | The rate basis or periodicity is not supported. |
| unsupported_rule | A requested FGTS, MCMV, tax, or eligibility rule is outside the supported ruleset. |
| unsupported_contract_clause | A financing or consortium clause lacks a documented ledger treatment. |
| infeasible_scenario | Valid inputs violate an explicit feasibility or balance condition. |
| incompatible_contract_version | The supplied contract or simulation version cannot be interpreted safely. |

## Financing support admission boundary

The implemented SAC and Price boundary supports only the fixed-principal,
effective-monthly-rate case defined above. A positive financing fee, insurance
amount, transaction cost, extraordinary amortization, or requested nonzero
indexation is an `unsupported_contract_clause`; explicit zero declarations
remain accepted exclusions. Nonzero FGTS, subsidy, and tax requests remain
`unsupported_rule`.

Future support for correction or indexation, fees, or insurance requires an
approved ADR before implementation. That ADR must define the contractual
semantics, ledger treatment, posting order and rounding, compatibility effect,
unsupported variants, and independent synthetic references. A deterministic
input representation alone does not admit a financial clause.

Complete observed, contractual, rule, and projected-assumption classification
for the real reference case belongs only to the schema-versioned private
reproducible envelope governed by
[reference-case governance](reference-case-governance.md). The financing
domain does not duplicate that envelope or its provenance contract.

## Frontend boundary

The backend financial domain is authoritative. The frontend may collect inputs, display backend results, format values, and validate presentation state. It may not calculate interest, amortization, corrections, balances, assets, net worth, ranking, sensitivity, or break-even values. Frontend types must be generated from or validated against the versioned backend contract.

## Deferred work

- API wire schemas and OpenAPI generation.
- Comparison contracts beyond the shared financing boundary and the version
  envelope.
- The consortium and rent-plus-investment implementations.
- Property appreciation, inflation, monetary correction, fees, insurance, taxes, and extraordinary amortization.
- FGTS, MCMV, and all other eligibility rules.
- SAC and Price implementations are limited to their accepted contracts and
  the existing `sac_basic`, `price_basic`, and
  `financing_unsupported_clauses` synthetic references. Additional synthetic
  schedule checkpoints, independent reference schedules, and all other
  financial implementations remain deferred.
