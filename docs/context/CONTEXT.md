# Housing Finance GPS — Current Context

> Last updated: August 22, 2026
> Read [AGENTS.md](../../AGENTS.md) before this document. This file describes
> current repository reality, not future intent and not implementation history.

## Current project state

- **Product:** A private Brazilian housing decision-support tool comparing
  SAC or Price financing, consortium scenarios, and renting while
  accumulating capital.
- **Delivery state:** Milestone 0 documentation readiness is complete. SAC and
  Price are the implemented financing behaviors, delivered through PR #12 /
  Issue #11 and PR #16 / Issue #15 respectively. PR #18 / Issue #17 harden
  their unsupported-clause boundary and synthetic invariants without adding a
  new financial behavior. PR #20 / Issue #19 merge the deterministic
  rent-plus-investment foundation and neutral common-ledger ownership. The
  PR #26 / Issue #25 delivered the retained v1 financing replay evaluator,
  which emits and reexecutes sealed,
  versioned SAC and Price envelopes without live financing or ledger
  dependencies. PR #32 / Issue #31 delivered the v2 fixed-monthly-fee replay
  evaluator and explicit live projections, retaining v1 historical behavior.
  Issue #36 adds explicit centavo-safe v3 SAC and Price settlement while
  retaining executable v1/v2 replay evidence. Issue #34 adds deterministic
  Hypothesis domain properties and a branch-coverage gate without changing
  domain behavior, contracts, or versions. Issue #39 adds one bounded,
  ephemeral FastAPI v1 financing-calculation projection over explicit v3 SAC
  and Price behavior; it does not add simulation creation, persistence,
  replay, or a frontend. A locked
  Python 3.13 development manifest, strict Pyright, pytest, Ruff, and GitHub
  Actions validation are configured.
- **Repository state:** Git is available. Work follows the issue-first,
  issue-numbered-branch, draft-pull-request workflow in the development
  process.
- **Architecture:** Product direction is approved. Reference-case governance,
  simulation provenance, financial conventions, backend authority, and
  verifiable financing-replay admission are documented in ADRs. A synthetic
  regression reference and a selected, partially configured QA baseline complete
  Milestone 0 documentation.
- **Current priority:** Deliver Issue #39's Track C bounded FastAPI v1
  financing-calculation projection. The 95% total Coverage.py gate with branch
  instrumentation over `domain/` remains required. Insurance and nonzero
  indexation remain deferred; any financial or architecture-critical work
  remains Track C approval-gated.

## Approved direction

- The financial engine is deterministic, authoritative, and written in pure
  Python.
- FastAPI exposes typed and versioned JSON contracts.
- Next.js and TypeScript provide a polished, accessible, independently
  deployable frontend.
- SQLite is the planned private-MVP persistence layer.
- The reference case is one real family decision held locally as private
  acceptance evidence; Git contains only redacted provenance and synthetic
  fixtures.
- Deterministic explanations precede any language-model integration.
- The MVP does not pursue commercial validation, distribution, monetization,
  bank integrations, PDF/OCR ingestion, or complete Brazilian rule coverage.

The canonical scope and acceptance criteria are in the
[product vision](../product/vision.md).

## Existing repository map

| Area | Current responsibility |
| --- | --- |
| `docs/product/` | Approved product direction and MVP boundary. |
| `docs/process/` | Development, review, approval, and QA workflow. |
| `docs/context/` | Current state, history, open questions, and discoveries. |
| `docs/adr/` | ADR guidance and future accepted architecture decisions. |
| `application/financing_projection.py` | Framework-independent use case selecting the fixed v3 financing projection. |
| `api/` | FastAPI v1 projection schemas, HTTP resource limits, public error mapping, and route. |
| `domain/values.py` | Immutable BRL money and rate values plus canonical runtime failures for the financing domain. |
| `domain/ledger.py` | Neutral common comparison ledger, derived accounting identities, and exact rational monetary posting. |
| `domain/financing/contracts.py` | Shared financing request, normalization, canonical failures, and immutable contractual schedule rows. |
| `domain/financing/sac.py` | Pure SAC schedule calculation using the shared financing boundary. |
| `domain/financing/price.py` | Pure Price schedule calculation using exact rational installment arithmetic. |
| `domain/financing/replay_v1.py` | Self-contained historical v1 financing evaluator and complete canonical trace projection. |
| `domain/financing/replay_v2.py` | Versioned v2 fixed-fee evaluator, codec validation, and canonical trace authority. |
| `domain/financing/replay_v3.py` | Versioned centavo-safe evaluator, codec validation, and canonical trace authority. |
| `domain/financing/replay.py` | Immutable neutral replay envelope, versioned emission, and fail-closed dispatcher. |
| `domain/financing/v2.py` | Explicit v2 SAC/Price live projections over the retained v2 evaluator. |
| `domain/financing/v3.py` | Explicit v3 SAC/Price live projections over the centavo-safe evaluator. |
| `domain/rent_plus_investment.py` | Pure rent-plus-investment postings, feasibility boundary, and 60-month comparison ledger. |
| `tests/` | Synthetic-only regression and boundary tests for SAC, Price, financing replay, v3 centavo-safe settlement (`tests/test_financing_v3.py`), and rent-plus-investment. |
| `.claude/` | Claude-specific adapters that defer to repository-owned rules. |
| `.project/` | Optional mechanical review-plan gate artifacts. |
| `scripts/` | Optional workflow enforcement scripts; not application code. |

The repository contains a bounded FastAPI v1 calculation-projection API. The
API does not expose replay, while the retained v1, v2, and v3 replay evaluators
remain part of the domain. There is no simulation-creation, persistence, Next.js
frontend, database, or comparison contract beyond the neutral common ledger and
version envelope. Consortium and eligibility rules remain unimplemented. Real
financial and identifying data remain prohibited from source control.

## Active architecture invariants

The project-level invariants are defined in [AGENTS.md](../../AGENTS.md).
This file records current application state and must not duplicate or weaken
those rules.

## QA status

The financing domain has a synthetic-only pytest suite: `uv run pytest -q`
passes 76 tests. The suite protects monetary and rate validation,
unsupported-case classification, posted-centavo SAC rounding and settlement,
Price exact-rational installments, posted-centavo rounding and settlement,
caller-context independence, separate schedule and ledger time domains,
synthetic fixture checkpoints, synthetic unsupported-clause parity, schedule
and ledger invariants, rent-plus month-0 allocation and feasibility,
determinism, immutability, canonical versioned financing replay, full-trace
equivalence, historical positive-fee failure preservation, and the v1
600-month schedule boundary, explicit and cumulative v2 fee posting, v2
financial parity for absent and zero fees, independent SAC and Price centavo
checkpoints, version-specific replay codecs, byte-sensitive v1/v2 envelope
stability, explicit v3 codec and dispatch validation, v3 fee-version
isolation, and the synthetic centavo-safe SAC/Price matrix for principals from
one to fifty centavos, terms one to sixty, rates 0.0000 and 0.0001, and absent
or R$0.01 fixed fees.

Ruff 0.16.0, Pyright strict checks over `domain/` and `tests/`, pytest,
Hypothesis, and Coverage.py are locked through `pyproject.toml` and `uv.lock`
for Python 3.13. Domain properties run deterministically with no example
database or deadline and 24 examples per property. A local targeted run
excluding the exhaustive v3 matrix reported 115 passed tests; the historical
76-test count is not the current suite total. GitHub Actions runs the complete
pytest suite once under branch instrumentation over `domain/`, followed by a
95% total Coverage.py gate. The delivered 97% figure is an observed local
measurement: the initial full instrumented run consumed approximately 21m 13s
CPU (about 2h 32m wall-clock time in the observed desktop session), and
targeted coverage data was appended afterward without repeating the v3 matrix.
The latest successful CI run completed in 8m 38s with a 15-minute job timeout.
Formatting, contract tests,
frontend tests, browser tests, and package/dependency review remain
unconfigured.
Milestone 0 selected and recorded the broader future baseline in the
[synthetic regression reference and QA baseline](../specifications/milestone-0-synthetic-reference-and-qa.md).

Documentation changes are validated by checking:

- Markdown structure and links;
- absence of unresolved template placeholders;
- consistency with the product vision;
- absence of directly identifying personal data.

## Documentation ownership

| Document | Canonical responsibility |
| --- | --- |
| [AGENTS.md](../../AGENTS.md) | Session contract, approval boundary, and cross-cutting invariants. |
| [README.md](../../README.md) | Repository entry point and concise project overview. |
| [vision.md](../product/vision.md) | Product purpose, scope, architecture direction, roadmap, and MVP acceptance. |
| [development-workflow.md](../process/development-workflow.md) | Delivery tracks, reviews, QA, commits, and pull requests. |
| This document | Current repository state and exactly one active priority. |
| [reference.md](reference.md) | Superseded directions, failed approaches, open design questions, and audits. |
| [discoveries.md](discoveries.md) | Append-only out-of-scope discovery log. |
| [ADR index](../adr/README.md) | Architecture decision format, status, and index. |

Completed work updates this file in place. Do not append a changelog here.
