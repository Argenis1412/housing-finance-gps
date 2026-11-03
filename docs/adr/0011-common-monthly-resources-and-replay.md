# ADR-0011: Bind common monthly resources to funded successor replay

- **Status:** Accepted
- **Date:** 2026-11-03
- **Owners:** Project maintainers
- **Related work item:** Issue #51

## Context and decision drivers

ADR-0010 delivered synthetic closed-initial-cash comparison A and required a
separately approved monthly-resource increment before B. Adding an income
field alone cannot distinguish taxes already netted, external expenses,
strategy payments, transfers and cash feasibility. Overlaying resources on
old ledgers cannot repair their early failures and would reinterpret history.

The user approved explicit income/expense composition, whole-balance funding,
monthly equality at origin, resources before obligations, cash-only shortfall
coverage and mandatory declared contributions. Independent AC challenge and
adversarial plan review preceded explicit implementation approval.

## Considered options

1. One fixed income amount or caller-supplied net budget: insufficient evidence
   for origin equality and double-counting diagnosis.
2. Adapt old completed ledgers: cannot preserve cash-failure timing or history.
3. Bind one full profile to separately versioned funded successor evaluators.

## Decision

Adopt option 3 under the
[common monthly resources contract](../specifications/common-monthly-resources-v1.md).
Net income is after incident taxes/contributions, before expenses and strategy
flows. Explicit income components and external expenses define all 60 months;
the backend derives signed net resources. No reserve masquerades as an expense,
no additional portion is withheld, and no fixed profile or defaults are inferred.

One profile binds composition, values, classifications, provenance, conventions
and period to SAC, Price, rent and consortium. After common resources, execute
obligations and then the full declared rent contribution. Return uses opening
invested assets. Surplus stays non-interest-bearing cash, with rent's investment
asymmetry explicit. Cash shortfall excludes without redemption, credit,
contribution reduction or fabricated partial outcomes. Closing liquidity and
housing-outflow constraints remain separate.

New authorities use pinned pure contractual helpers, not historical ledger
execution. Deliberate private-helper coupling is version-pinned and verified
by import and dependency tests. Each successor owns admission and funded
execution; aggregate replay owns complete successor outcome equivalence.
All profile admission precedes feasibility. Planned versus consumed evidence
remains distinct. Integer-cent balances and an explicit precision28 contractual
context preserve determinism without caller Decimal settings.

## Consequences

### Positive

- Equality is verifiable by monthly values, composition and conventions, rather
  than merely a matching snapshot or equal net totals.
- Conservation and failures can be independently checked under funded cash flow.
- Historical simulations and callable contracts remain unchanged.

### Negative

- Explicit monthly components/provenance require more input than one budget.
- Declarations cannot detect semantic aliases or authenticate source facts.
- Retained successor modules and pinned private dependencies require maintenance.
- Only rent invests; this is still bounded synthetic comparison, not complete M4.

### Neutral and operational

- Exactly 15 planned files; at most eight new Python modules (five production,
  three tests), 12 new classes, 48 new public production module-level names,
  two additive factories/calculations and no new dependencies. Four new frozen
  input classes; existing callable signatures remain unchanged.
  Delivered counts: 15 files, eight new Python modules, five new classes and
  32 new public production module-level names (imports, fields and methods
  excluded, following ADR-0010).
- No retained evaluator/test/fixture, HTTP/application, standalone child
  dispatcher, dependency or QA/CI changes. No mechanical plan gate activation.
- The prior audit remains recorded; #50 is merge 1 of the next five-PR cycle.

## Compatibility and migration

Comparison schema/engine/ruleset become comparison-simulation-v2 /
comparison-monthly-resources-v2 / comparison-ruleset-v2. Child successor tuples
are financing-replay-v4 / financing-monthly-resources-v4 / financing-ruleset-v3;
rent-plus-replay-v2 / rent-plus-monthly-resources-v2 / rent-plus-ruleset-v2; and
consortium-replay-v2 / consortium-monthly-resources-v2 / consortium-ruleset-v2.
Ruleset increments identify changed funding/feasibility. Contractual v3 finance
settlement and v1 rent/consortium support stay pinned.

Full-tuple dispatch precedes interpretation. V1 aggregate, financing v1/v2/v3,
rent v1 and consortium v1 replay remain available without migration, injected
zeros or latest fallback. New child versions are aggregate evidence only;
existing standalone replay and the ephemeral HTTP projection remain unchanged.

## Verification

Independent monthly references and cash/net-worth conservation; negative and
variable profiles; opening/expense/obligation/contribution shortfall phases;
exact-zero/cent boundaries; cash versus investment liquidity; consortium
60/61 transitions; v3 settlement parity; full-profile admission precedence;
component/provenance/posting/metric/version tampering; complete prechange v1
envelope hashes; immutable/context-independent results; independent diff review
and full configured QA including unchanged historical tests and fixtures.

## Deferred decisions

B application/API/simple UI requires its own contract and approval after this
increment's validation. Sensitivity, break-even, optimization, polish,
persistence, real proposals, private reference validation, further financial
clauses and automatic redemption/credit/investment policies remain outside.
