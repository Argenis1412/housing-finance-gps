# Housing Finance GPS — Current Context

> Last updated: November 10, 2026
> Read [AGENTS.md](../../AGENTS.md) before this document. This file describes
> current repository reality, not future intent and not implementation history.

## Current project state

- **Product:** A private Brazilian housing decision-support tool comparing
  SAC or Price financing, consortium scenarios, and renting while
  accumulating capital.
- **Implemented capabilities:** SAC and Price financing, including explicit
  centavo-safe v3 settlement and fixed monthly fees; retained v1/v2/v3 financing
  replay; a neutral 60-month comparison ledger; rent-plus-investment; and
  synthetic consortium v1 with explicit contemplation, waiting costs and
  dedicated in-memory replay. Minimum synthetic comparison creates explicit
  in-memory simulation evidence for SAC/Price v3, retained rent v1 and one
  consortium scenario, with shared-basis admission, mandatory constraints,
  exact-cent tied groups and aggregate replay.
  Comparison v2 additionally binds one explicit 60-month income/external-expense
  profile to funded financing v4, rent v2 and consortium v2 successors, retaining
  closed-cash comparison v1 unchanged. Resources precede obligations; surplus
  stays cash and shortfalls exclude without automatic redemption or credit.
  Milestone 0 documentation readiness is complete, including governance,
  provenance, financial contracts, and the synthetic regression reference.
- **API boundary:** A bounded FastAPI v1 endpoint exposes ephemeral SAC or
  Price v3 calculation projections under the
  [financing projection contract](../specifications/fastapi-v1-financing-projection.md).
  A separate
  [comparison creation contract](../specifications/comparison-application-api-ui-v1.md)
  exposes transient v2 simulations with typed presentation results and a local
  Next.js entry/review/result flow. A separate explicit local SQLite boundary
  saves complete v2 evidence, lists, reopens readonly results without execution
  and deletes individual records under the
  [persistence contract](../specifications/local-comparison-persistence-v1.md).
  No HTTP replay is exposed.
  Historical replay remains a domain capability.
- **Validation:** A locked Python 3.13 development environment, Ruff, strict
  Pyright, pytest, deterministic Hypothesis properties, HTTP/OpenAPI contract
  tests, and a domain coverage gate are configured in GitHub Actions.
- **Remaining boundaries:** Remote private operation,
  real-proposal consortium admission, eligibility rules and comparison
  beyond the admitted synthetic contracts remain unimplemented.
  Only rent invests; this increment does not establish household affordability
  or complete M4. Insurance and nonzero
  financing indexation remain unsupported. This state summary does not declare
  the financing milestone complete or validate the private reference case.
- **Local persistence status:** PR #56 merged and closed issue #55. The
  post-merge lifecycle passed with a temporary synthetic SQLite database.
  Fault injection reproduced an integrity failure when SQLite truncated a
  saved record at a literal NUL. The audit cycle is at four of five behavioral
  merges (#50, #52, #54, and #56). The audit is due after the fifth merge.
- **Current priority:** Reject NUL-truncated reads of saved comparison evidence.

## Approved direction

- The financial engine is deterministic, authoritative, and written in pure
  Python.
- FastAPI exposes typed and versioned JSON contracts.
- Next.js and TypeScript provide a polished, accessible, independently
  deployable frontend.
- SQLite stores explicitly saved synthetic comparisons through versioned local migrations.
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
| `docs/adr/` | Accepted architecture decisions and their rationale. |
| `application/financing_projection.py` | Framework-independent use case selecting the fixed v3 financing projection. |
| `application/comparison_simulation.py` | Explicit transient v2 creation and sealed presentation projection with injected metadata. |
| `application/saved_comparisons.py` and `infrastructure/sqlite_comparisons.py` | Immutable evidence codec, transactional saved use cases, SQLite adapter and explicit migration. |
| `api/` | Separate financing projection and comparison creation schemas, resource admission and safe error families. |
| `web/` | Local Next.js/TypeScript declaration/review/result UI, generated consumer types and synthetic browser tests. |
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
| `domain/rent_plus_investment.py` | Compatible live dataclass adapter over retained rent normalization and postings. |
| `domain/rent_replay_v1.py` | Retained rent v1 authority preserving cash failure timing and shared rent projection. |
| `domain/comparison.py` and `domain/comparison_v1.py` | Explicit immutable synthetic simulation creation, version-owned comparison and aggregate replay under the [minimum contract](../specifications/minimum-comparison-v1.md). |
| `domain/comparison_v2.py`, `domain/monthly_resources_v1.py` and funded child successors | Common-profile admission, origin equality, funded postings, cash feasibility and aggregate successor replay under the [monthly-resource contract](../specifications/common-monthly-resources-v1.md). |
| `domain/consortium/` | Synthetic v1 proposal/scenario boundary, classified monthly postings, common ledger projections and dedicated retained replay. |
| `tests/` | Synthetic regression, boundary, replay, domain-property, HTTP/OpenAPI, and dependency-boundary tests. |
| `.claude/` | Claude-specific adapters that defer to repository-owned rules. |
| `.project/` | Optional mechanical review-plan gate artifacts. |
| `scripts/` | Optional workflow enforcement scripts; not application code. |

Real financial and identifying data remain prohibited from source control.

## Active architecture invariants

The project-level invariants are defined in [AGENTS.md](../../AGENTS.md).
This file records current application state and must not duplicate or weaken
those rules.

## QA status

The configured tools and locked versions are owned by `pyproject.toml` and
`uv.lock`; the CI sequence is owned by `.github/workflows/validation.yml`.

- The current synthetic validation baseline is 666 fast Python tests, four slow
  tests and 36 frontend tests, with 98% combined domain coverage (95% gate).
- Ruff checks Python lint rules. Automated formatting is not configured.
- Pyright runs in strict mode over `domain/`, `application/`, `api/`,
  `infrastructure/`, the migration command and `tests/`.
- The synthetic-only pytest suite covers independent financial checkpoints,
  typed unsupported cases, schedule and ledger identities, deterministic and
  immutable results, historical versioned replay, and v3 centavo settlement.
- Hypothesis properties run deterministically without an example database or
  deadline. The exhaustive small-principal v3 matrix is marked `slow` and
  excluded from default local runs. Unregistered test markers fail collection.
- HTTP/OpenAPI tests validate v3 projection parity, deterministic responses,
  public errors, resource limits, the schema, and dependency boundaries.
- GitHub Actions runs independent `validation` and `financing_matrix` jobs on
  pushes to `main` and pull requests targeting `main`. The fast `validation`
  job runs lint, types, and tests with branch instrumentation over `domain/`,
  then enforces Coverage.py's combined total threshold of 95%. The matrix job
  runs all `slow` tests without coverage instrumentation. `application/`,
  `infrastructure/` and `api/` have tests but are outside the measured source scope.

Configured commands:

```text
uv sync --frozen
uv run ruff check .
uv run pyright
uv run coverage run --branch --source=domain -m pytest -q -m "not slow"
uv run coverage report --fail-under=95
uv run pytest -q -m slow
```

For an uninstrumented fast run, use `uv run pytest -q`. Run only the matrix
with `uv run pytest -q -m slow`, or the complete suite with
`uv run pytest -q -m ""`.

OpenAPI-to-TypeScript generation, frontend lint/types/build and synthetic
Chromium browser tests are configured under `web/` and the additional `web` CI
job. Run `npm ci`, `npm run contract:check`, `npm run lint`,
`npm run typecheck`, `npm run build` and `npm test` there; install Chromium with
`npx playwright install chromium` first. The existing backend job commands and
95% domain coverage gate remain unchanged. Dependency review and secret scanning
remain unconfigured. The broader selected baseline
is recorded in the
[synthetic regression reference and QA baseline](../specifications/milestone-0-synthetic-reference-and-qa.md).
Concrete deferred QA findings are recorded in [discoveries.md](discoveries.md).

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
