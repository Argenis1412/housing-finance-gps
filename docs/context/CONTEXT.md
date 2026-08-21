# Housing Finance GPS — Current Context

> Last updated: August 19, 2026
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
  dependencies. Issue #36 adds explicit centavo-safe v3 SAC and Price
  settlement while retaining executable v1/v2 replay evidence. No API,
  frontend, or persistence is configured. A locked
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
- **Current priority:** Issue #36 defines centavo-safe v3 financing settlement
  and version-owned fixed-fee availability. Issue #34 remains blocked and must
  be recreated from the resulting `main` after Issue #36 merges. Insurance and
  nonzero indexation remain deferred; any financial or architecture-critical
  work remains Track C approval-gated.

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

The repository contains no FastAPI API, Next.js frontend, database, or
persistence. Comparison contracts
beyond the neutral common ledger and the version envelope, consortium, and
eligibility rules remain unimplemented. Real financial and identifying data
remain prohibited from source control.

## Active architecture invariants

The project-level invariants are defined in [AGENTS.md](../../AGENTS.md).
This file records current application state and must not duplicate or weaken
those rules.

## QA status

The financing domain has a synthetic-only pytest suite: `uv run pytest -q`
passes 66 tests. The suite protects monetary and rate validation,
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

Ruff 0.16.0, Pyright strict checks over `domain/` and `tests/`, and pytest are
locked through `pyproject.toml` and `uv.lock` for Python 3.13. GitHub Actions
runs `uv sync --frozen`, lint, strict type checking, and the synthetic-only
suite with read-only repository permissions. Formatting, contract tests,
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
