# Common Monthly Resources v1

> Accepted Track C contract, Issue #51.
> Decision: [ADR-0011](../adr/0011-common-monthly-resources-and-replay.md).

## Scope and public boundary

Comparison v2 compares exactly SAC, Price, rent plus explicit investment and
one synthetic consortium scenario over closing months 0..60. It extends the
[minimum comparison](minimum-comparison-v1.md) with one shared explicit resource
profile. It does not complete M4, validate the private household, admit real
proposals or change the ephemeral financing HTTP endpoint. Only rent invests;
the evidence exposes that asymmetry beside its other limitations.

`domain/comparison.py` adds four frozen input types: `ResourceComponentInput`,
`ResourceMonthInput`, `CommonMonthlyResourcesInput` and `ComparisonRequestV2`.
The latter has exactly `shared`, `constraints`, `financing`, `rent`, `consortium`
and `monthly_resources`. The first five retain the minimum comparison shapes,
numeric admission, support and shared-basis semantics. Existing functions and
types retain their signatures. Two additive functions use explicit versions:

- `calculate_comparison_v2(request, *, data_snapshot_id, calculated_at)` creates
  evidence and returns the existing immutable result projection or global failure.
- `create_comparison_v2_envelope(*, raw_request_jcs, data_snapshot_id,
  calculated_at)` seals canonical success or global semantic failure.

`replay_comparison` selects the full version tuple before interpreting input.
There is no implicit v1 upgrade or monthly-zero injection. No standalone new
child factories, replay registrations, persistence, export, application or HTTP
contract are added. New child evidence is executed within aggregate replay.

## Income, external expenses and available resources

Household net income means income after incident taxes and contributions but
before household expenses, housing payments and transfers into investment.
These are supplied net values; the backend does not calculate payroll or taxes.
Deductions already netted from income cannot be expenses again.

External expenses are explicitly declared household outflows independent of
which of these four strategies is chosen. Ordinary consumption and independent
commitments may belong here. Rent while renting/waiting, financing payments,
consortium installments/top-up, initial allocations and financial contributions
belong to the strategy and must stay outside this profile. A cash reservation
is not an expense. This contract preserves no additional portion outside the
comparison: the entire derived balance enters each alternative.

For every month, the backend derives, in exact integer centavos:

    income_total = sum(income_components.amount)
    external_expense_total = sum(external_expenses.amount)
    available_resources = income_total - external_expense_total

Available resources may be positive, zero or negative. They are an origin of
funding, not a savings forecast, housing-cost metric or instruction to invest.
The backend accepts neither caller totals nor a separate available-resource
override. No percentage, constant income, implicit recurring component, annual
increase, expense default or household budget rule is inferred.

## Closed profile and provenance

The profile has exactly:

- `income_basis="net_before_household_expenses"`;
- `expense_scope="strategy_independent_excluding_strategy_flows_and_netted_deductions"`;
- `months`, exactly 60 ordered rows, one for each actual integer month 1..60.

Each row has exactly `month`, `income_components` and `external_expenses`.
Both arrays are required; explicitly empty arrays are valid. Each component has
exactly these fields, without optional omissions:

| Field | Admission |
| --- | --- |
| `component_id` | Stable machine identifier identifying the declared flow. |
| `amount` | Nonnegative nominal BRL string; optional sign, 1..18 ASCII integer digits, exactly two fractional digits. Signed zero normalizes to `0.00`. |
| `classification` | `observed_data` or `projected_assumption`. |
| `source_reference` | Supplied machine identifier for the source, never a document or personal identifier. |
| `source_as_of` | Supplied valid UTC `YYYY-MM-DDTHH:mm:ssZ`; no clock lookup or invented date. |
| `assumption_reference` | Required machine identifier for projected values; explicit null for observed values. |

Machine identifiers match `[A-Za-z0-9][A-Za-z0-9._-]*`. Identity is unique within
each month across both arrays and cannot change between income and expense in
later months. Absence from an explicit row is allowed; it does not fill other
rows. Composition order is retained in canonical evidence. All months and
provenance are validated before any cash execution, including a future row
after an otherwise earlier shortfall. Calculated totals are uncapped sums.

Constant and changing profiles both require explicit monthly declarations.
Observed versus projected classification and supplied assumptions are retained,
not inferred from dates. The scope declaration prevents structural confusion;
it cannot recognize that two differently named flows refer to the same real
payment. Callers must classify facts truthfully. Replay proves consistency and
reexecution, not source authenticity or the absence of semantic aliases.

## Equality at origin and differences in consequences

One common profile is accepted by the aggregate and bound in full to each
child. There are no caller-selected profiles per alternative. Equality includes
the values, monthly positions, income basis, expense scope, component identity,
composition, classification, source dates/references and assumptions. Equal
net totals or a shared `data_snapshot_id` alone do not establish equality.

Opening cash, nominal BRL, centavos, `ROUND_HALF_UP`, 60-month horizon, shared
purchase price and rent/waiting terms retain the minimum comparison contract.
Initial allocations, obligations, housing costs, financial transfers, closing
cash, assets and outcomes may differ as consequences of strategy choice.

## Posting order and cash feasibility

Month 0 uses initial cash only: financing pays the down payment and acquires
property/debt; rent allocates its declared initial investment; consortium holds
opening cash. Month 1 income cannot fund an insufficient month-0 allocation.

For each month 1..60:

1. Rent posts return on opening invested assets, retaining that return in the
   investment. Rent adjustment uses retained v1 annual posting semantics.
2. Recognize the common income and external expenses once, before obligations.
   A negative net balance consumes that alternative's accumulated cash.
3. Execute contractual strategy obligations and transitions. Financing uses
   centavo-safe v3 amortization and fees. Consortium retains its classified
   contribution, waiting cost and contemplation/purchase/top-up order, including
   waiting cost in the purchase month. Credit-letter application is noncash.
4. Rent transfers its entire declared contribution after obligations. It earns
   no return retroactively that month. There is no contribution in the other
   strategies. Unused cash remains cash without return in all four.

Only accumulated cash can cover a shortfall. No asset redemption, borrowing,
implicit funding or reduced/suspended contribution is allowed. Positive
financial assets or their current return cannot fund a cash payment.
Cash exactly zero passes. Insufficiency excludes that alternative with
`infeasible_scenario`, no partial ledger, metrics, violations or ranking.
Safe details are exactly `cash is insufficient in month N during PHASE`;
`PHASE` is `opening_allocation`, `external_expenses`, `strategy_obligations` or
`investment_contribution`. No caller text is echoed. This financing cash policy
is new; historical financing negative-cash ledgers remain reproducible.

## Accounting, constraints and ordering

For months 1..60, reconciliation must establish:

    cash change = available_resources - strategy cash outflow - contribution
    net-worth change = available_resources + investment return
                       - nonrecoverable housing cost

External expenses are recognized only through common resources; they are not
housing cost or housing outflow. Down payment, principal, consortium credit
components/top-up and investment transfers retain recoverable classification.
The neutral ledger identities remain unchanged.

Only complete cash-feasible ledgers undergo closing constraints and metrics.
Minimum liquidity is cash plus liquid financial assets at months 0..60; a
liquidity floor is a separate constraint, not a redemption permission. Housing
outflow is full financing payment, rent alone, or consortium payment plus
waiting plus posted top-up at months 1..60. Contributions/external expenses and
noncash events do not enter this cap. Inclusive thresholds, complete ordered
violations and eligible-only exact-cent net-worth-at60 groups retain v1
semantics. Full schedules reconcile contract totals without asserting cash
feasibility or future purchase events beyond month 60.

## Evidence, admission and retained versions

Metadata and the closed JCS codec retain the minimum comparison conventions.
Raw evidence preserves the complete planned profile even on global failure.
Success normalizes components and derives totals; each child has a closed raw
wrapper containing exactly `strategy_input` and `monthly_resources`, its pinned
versions and sealed outcome or admission failure. No profile field is stripped
to coerce historical compatibility. Successful children additionally retain
60 resource postings (opening cash, income, expenses, signed resources,
cash after external expenses and closing cash) and 61 reconciled ledger rows.
Failures retain planned inputs and canonical failure, not fictitious consumed
resource rows. Complete canonical outcomes, including child evidence, totals,
constraints, metrics, groups and limitations, are compared on replay.

| Authority | Schema | Engine | Ruleset |
| --- | --- | --- | --- |
| Comparison | `comparison-simulation-v2` | `comparison-monthly-resources-v2` | `comparison-ruleset-v2` |
| SAC/Price | `financing-replay-v4` | `financing-monthly-resources-v4` | `financing-ruleset-v3` |
| Rent | `rent-plus-replay-v2` | `rent-plus-monthly-resources-v2` | `rent-plus-ruleset-v2` |
| Consortium | `consortium-replay-v2` | `consortium-monthly-resources-v2` | `consortium-ruleset-v2` |

New rulesets identify funding/feasibility policies, not new amortization or
consortium clauses. Successors pin pure normalization/schedule/rent-posting
helpers and build funded ledgers themselves. They never execute a closed-cash
ledger and overlay income afterward. Bounded contractual normalization uses
an explicit Decimal precision 28 context; common sums/balances use integer
centavos. Existing retained modules, standalone dispatchers and fixture bytes
remain unchanged. V1 aggregate and all existing child replay versions continue
without migration or latest-handler fallback.

Failure precedence is representation/metadata, common financial basis and
constraints, entire resource profile, well-typed shared mismatches, child
structural/numeric admission, retained contractual support, successor cash
execution, then closing constraints/grouping. Known failures are sealed;
unexpected execution errors propagate on creation and fail replay closed as
`incompatible_contract_version`. Unknown tuples are rejected before parsing.
Consistently rewriting an entire profile and recalculating creates a different
simulation; neither snapshot IDs nor source references authenticate it.

## Verification and next gate

Independent variable/negative/zero resource references, one-cent shortfalls,
opening-allocation timing, mandatory contributions, cash versus liquid assets,
return timing, consortium transitions, settlement parity and conservation
protect financial semantics. Full-profile precedence, child binding/tampering,
immutable/context-independent evidence, prechange complete v1 envelope hashes
and unchanged historical tests protect replay. Full configured QA retains both
CI jobs, strict types, lint and the combined 95% domain coverage gate.

After this increment is validated, B requires its own application/API/simple
UI contract and approval. No advance approval, M4 completion, sensitivity,
break-even, optimization, polish, persistence or private-case validation follows
from this delivery. PR #50 is behavioral merge 1 of the new five-PR audit cycle;
this increment would become 2 only on merge. No ready/merge is authorized.
