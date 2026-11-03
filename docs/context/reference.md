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
| Broader QA toolchain | Repository | Expected | Formatting, OpenAPI-to-TypeScript generation, frontend tests, browser tests, dependency review, and secret scanning remain deferred. See [current QA status](CONTEXT.md#qa-status) for configured checks. |

Concrete QA discoveries and their next decisions are recorded in
[discoveries.md](discoveries.md). The dated audits below retain their
historical observations; they do not describe the current validation baseline.

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

### November 3, 2026 — Five behavioral pull requests after consortium v1

- **Trigger and baseline:** The agreed count is #32, #37, #38, #40 and #48.
  Tooling-only #35/#46 and documentation deliveries are excluded. No audit
  after #48 was recorded on clean main at `30ee36d`. This audit precedes
  Issue #49 comparator behavior.
- **Review-track fit:** Financial fee admission, centavo settlement, the first
  public financial boundary and consortium replay warranted Track C. Domain
  assurance remained bounded tooling; its discovered settlement defect was
  separated into its own financial work item rather than hidden by tests.
- **Reviewer signal:** Retained discussions show useful corrections to payment
  definitions, settlement assertions, schedule length and explicit strategy
  dispatch. PR #48 contains an automatic-review skip notice; retained GitHub
  evidence cannot establish every independent review or quantify reviewer noise.
- **Deferred discoveries:** The matrix-runtime concern was addressed by #46
  without dropping cases. The TestClient/httpx deprecation warning is now
  reproduced. The combined coverage gate still measures only `domain/`.
  Those latter findings remain deferred; this audit authorizes no fixes.
- **QA determinism and usefulness:** Frozen environment, Ruff and strict
  Pyright pass. The fast branch-instrumented run passes 258 tests; the separate
  matrix passes four tests; combined domain coverage displays 97% against 95%.
  Hypothesis remains deterministic. Local sandbox subprocess restrictions
  required rerunning Pyright and HTTP tests outside that restriction, without
  configuration changes. These are local results, not claims about remote CI.
- **Documentation ownership:** Current state, process, product scope, decisions
  and discoveries retain separate canonical owners. Historical discovery
  entries remain intact; current QA commands stay owned by CONTEXT and CI.
- **Next boundary:** Issue #49 is synthetic closed-cash comparison only.
  A separately approved monthly-resources increment must precede family-use
  application/API/UI delivery. No income field or financial extension is
  admitted by this audit.

### August 19, 2026 — Five behavioral pull requests

- **Review-track fit:** PRs #12, #16, #18, #20, and #26 changed deterministic
  financial behavior, financial boundaries, or historical replay. Their Track C
  classification matched the documented risk.
- **Reviewer signal:** The retained merge history records review-driven fixes
  for SAC decimal-context isolation, Price rational half-cent coverage,
  rent input and discovery boundaries, and replay fail-closed behavior. The
  repository does not retain complete reviewer-thread data, so it cannot
  quantify reviewer noise or compare findings against all non-findings.
- **Deferred discoveries:** `docs/context/discoveries.md` has no entries.
  Deferred financial clauses remain explicitly owned by ADR-0005 and ADR-0006
  rather than being accumulated as unowned discoveries.
- **QA determinism and usefulness:** The synthetic-only standard-library suite
  passes 45 tests with the documented offline command. At the time of this
  audit, no lint or CI was configured; Issue #27 subsequently added a minimal
  pinned Ruff check and read-only validation workflow without expanding
  financial coverage.
- **Documentation ownership:** Current QA counts diverged across the README,
  current context, and Milestone 0 baseline. Issue #27 synchronizes them to
  the observed 45-test result and records configured-tool ownership.
