# Housing Finance GPS — Reference

> Historical context, superseded directions, failed approaches, open design
> questions, and periodic workflow audits. This is not required reading for
> every session.

For current state, see [CONTEXT.md](CONTEXT.md). For raw out-of-scope
discoveries, see [discoveries.md](discoveries.md).

## Superseded product direction

### August 17, 2026 — Commercial validation path retired

The earlier vision treated B2C concierge validation and B2B2C distribution
through financial professionals as gates before product development. That
direction also included professional prospect filters, outreach channels,
economic commitments, pricing constraints, and commercial conflict rules.

The project deliberately stopped pursuing that path. The active goals are:

1. build a technically strong, deterministic financial-engine portfolio
   project;
2. support one real, anonymized family housing decision.

Commercial validation material is historical context, not deferred MVP work.
It must not re-enter planning unless the product direction is explicitly
reopened.

## Known technical debt

| Item | File or area | Severity | Notes |
| --- | --- | ---: | --- |
| No application scaffold | Repository | Expected | Milestone 0 precedes implementation. |
| QA commands not configured | Repository | Expected | Select with the Python and TypeScript toolchains. |
| Git working tree unavailable | Repository | High for delivery workflow | Resolve before enforcing branches, commits, or review-plan admission. |

## Failed approaches

| Date | Approach | Problem |
| --- | --- | --- |
| _None recorded_ | | |

Retired product strategy belongs in “Superseded product direction,” not in
this table unless it failed during implementation.

## Open design questions

The complete pending-decision list lives in the
[product vision](../product/vision.md#21-decisions-to-resolve-through-adrs-or-the-reference-case).
Do not duplicate it here. Add only questions discovered during implementation
that are not already owned by the vision or an ADR.

_None recorded._

## Periodic workflow audits

After every five merged behavioral pull requests, review:

- whether the chosen review tracks match actual risk;
- whether reviewer findings catch correctness problems or create noise;
- whether deferred discoveries are being resolved or merely accumulated;
- whether QA remains deterministic and useful;
- whether documentation ownership is still unambiguous.

Record dated audit results below.

_No audits recorded._
