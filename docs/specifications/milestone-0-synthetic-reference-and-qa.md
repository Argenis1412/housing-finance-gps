# Milestone 0 Synthetic Regression Reference and QA Baseline

> Status: accepted Milestone 0 documentation baseline
> Related contracts: [financial contracts](financial-contracts.md) and
> [reference-case governance](reference-case-governance.md)
> Related issue: #7

## Purpose and boundary

The [synthetic regression fixture](../fixtures/milestone-0-synthetic-regression.json)
is a public, invented reference for future deterministic validation. It is not
a simulation engine, a proposal, a prediction, or a sanitized family record.
Its numeric values were selected solely to make posted-centavo transitions
reviewable.

The fixture uses the financial contract's nominal-BRL, effective-rate,
one-based-month, 60-month, and `ROUND_HALF_UP` conventions. All expected
amounts are exact decimal-string checkpoints: a future implementation must
match them with zero tolerance after applying the contractual posting order.
The fixture's `engine_version`, `ruleset_version`, and `data_snapshot_id`
identify this contract reference only; they do not claim that an application
engine has been released.

## Synthetic reference contents

All four strategies begin with the same invented `comparison_opening_cash` of
R$20,000.00. The fixture records source *classifications* that a real
simulation would use, but none of its values were observed from a household.

| Fixture | Regression guarantees |
| --- | --- |
| `sac_basic` | Month-0 purchase, fixed R$100.00 SAC amortization, month-12 zero principal, and month-60 comparison balances. |
| `price_basic` | Month-0 purchase, the rounded regular installment, a final settlement that differs from it, month-12 zero principal, and month-60 comparison balances. |
| `consortium_credit_right` | Pre-contemplation credit right, month-4 transfer to property and a R$600.00 residual obligation, a later credit-component reduction, and cleared obligation at month 60. |
| `rent_plus_investment` | Opening-balance investment return, end-of-month contribution, first rent adjustment in month 13, subsequent annual adjustments, and month-60 liquidity and cost. |

`positive_classified_flow_amount` means a positive `recoverable_transfer` or
`nonrecoverable_housing_cost` is a cash outflow in this fixture. Ledger
balances and cash effects remain authoritative; the convention only makes the
fixture's named flows unambiguous.

The full financing schedule is 12 months for the two finance fixtures. Their
ledger balances remain unchanged through comparison month 60 after settlement.
The consortium schedule ends in month 10; its balances likewise remain
unchanged through month 60. The fixture deliberately uses no inflation,
property appreciation, correction, fee beyond the explicit consortium
administration fee, tax, insurance, FGTS, MCMV, bid, or probability.

## Private-reference local validation

The private real case is validated locally and is never represented by this
fixture. The owner must:

1. Prepare the complete private reproducible envelope outside the repository.
2. Check each supported input and output against the accepted financial
   contract and the corresponding deterministic fixture guarantee.
3. Run the future local calculation only with the envelope's recorded
   `engine_version`, `ruleset_version`, and `data_snapshot_id`.
4. Create the JCS/HMAC commitment and obtain the redacted attestation under
   the [governance contract](reference-case-governance.md).
5. Retain the private envelope, commitment secret, outputs, and signatures in
   owner-controlled local storage.

Private envelopes, commitment secrets, private keys, real inputs, real
outputs, proposal documents, and reproducible exports must not enter Git, CI,
logs, fixtures, or shared exports. Git-visible evidence is limited to the
redacted artifact class defined by the governance contract; this PR does not
add one.

## Selected but unconfigured QA baseline

The following tools are selected for a future implementation work item. They
are not installed, pinned, configured, or run by this milestone.

| Area | Selected baseline | Intended guarantee |
| --- | --- | --- |
| Pure Python domain | Python 3.13, `uv`, Ruff, Pyright, pytest, Hypothesis | Deterministic Decimal calculations, invariants, boundary failures, and regression fixtures. |
| FastAPI contract | FastAPI, OpenAPI schema validation, generated or schema-validated consumer types | Versioned request/error/result compatibility. |
| Next.js and TypeScript | Node.js 22 LTS, pnpm, TypeScript, Biome, Vitest | Presentation correctness, type safety, and absence of client-owned financial formulas. |
| Browser | Playwright | Accessible input and result rendering against backend-owned results. |
| Formula-boundary review | Static source review plus API-contract tests | Reject authoritative interest, amortization, balance, ranking, sensitivity, and break-even calculations outside Python. |
| CI | GitHub Actions, dependency review, secret scanning | Repeatable checks using synthetic fixtures only. |

Exact commands, package versions, workflow configuration, API endpoints, and
OpenAPI-to-TypeScript generation tooling remain deferred until their own
approved implementation work item. No QA command is configured at this time.

## Validation requirements for this artifact

- Parse the fixture as JSON.
- Check each expected monetary value is a two-fractional-digit decimal string.
- Check the fixture contains no unresolved placeholders, direct identifiers,
  real proposal material, private export material, or commitment secret.
- Check relative Markdown links and the cross-links to the two accepted
  contracts.
- When application tests exist, make every fixture checkpoint a zero-tolerance
  deterministic regression assertion and add separate tests for all typed
  unsupported-case failures.

## Deferred work

- Executable fixture schema validation and financial regression tests.
- Tool installation, version pinning, scripts, and CI configuration.
- FastAPI, Python-domain, Next.js, TypeScript, persistence, and browser code.
- Any real-case export, signing, encryption, or automated local-validation
  tooling.
