# Housing Finance GPS — Current Context

> Last updated: August 19, 2026
> Read [AGENTS.md](../../AGENTS.md) before this document. This file describes
> current repository reality, not future intent and not implementation history.

## Current project state

- **Product:** A private Brazilian housing decision-support tool comparing
  SAC or Price financing, consortium scenarios, and renting while
  accumulating capital.
- **Delivery state:** Milestone 0 documentation readiness is complete. PR #12
  merged the first Milestone 1 slice and Issue #11 is closed: SAC is the sole
  implemented financial behavior. No API, frontend, persistence, CI, or
  dependency toolchain is configured.
- **Repository state:** Git is available. Work follows the issue-first,
  issue-numbered-branch, draft-pull-request workflow in the development
  process.
- **Architecture:** Product direction is approved. Reference-case governance,
  simulation provenance, financial conventions, and backend authority are
  documented in ADRs. A synthetic regression reference and a selected,
  unconfigured QA baseline complete Milestone 0 documentation.
- **Current priority:** After this documentation synchronization pull request
  is merged and explicit authorization is received, prepare the Track C
  proposal for “Milestone 1.1 — deterministic Price and comparison-contract
  foundation.” Do not create its branch or implementation files before that
  gate.

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
| `domain/values.py` | Immutable BRL money and rate values plus canonical runtime failures for the implemented domain boundary. |
| `domain/financing/sac.py` | Pure SAC request normalization, contractual schedule, and fixed 60-month comparison ledger. |
| `tests/test_sac_domain.py` | Synthetic-only regression and boundary tests for the SAC implementation. |
| `.claude/` | Claude-specific adapters that defer to repository-owned rules. |
| `.project/` | Optional mechanical review-plan gate artifacts. |
| `scripts/` | Optional workflow enforcement scripts; not application code. |

The repository contains no FastAPI API, Next.js frontend, database,
persistence, CI configuration, or dependency manifest. Price, shared
comparison contracts and version envelope, consortium, rent-plus-investment,
and eligibility rules remain unimplemented. Real financial and identifying
data remain prohibited from source control.

## Active architecture invariants

The project-level invariants are defined in [AGENTS.md](../../AGENTS.md).
This file records current application state and must not duplicate or weaken
those rules.

## QA status

The SAC domain has a standard-library unit-test suite: `uv run --offline
--no-project python -m unittest discover -s tests -t . -v` passes 13
synthetic-only tests. The suite protects monetary and rate validation,
unsupported-case classification, posted-centavo SAC rounding and settlement,
separate schedule and ledger time domains, synthetic fixture checkpoints,
determinism, and immutability.

Linting, formatting, static type checking, contract tests, frontend tests,
browser tests, package pinning, and CI remain unconfigured. Milestone 0
selected and recorded their future baseline in
[synthetic regression reference and QA baseline](../specifications/milestone-0-synthetic-reference-and-qa.md);
configuration remains a future implementation work item.

Until then, documentation changes are validated by checking:

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
