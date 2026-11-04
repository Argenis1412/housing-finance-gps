# Housing Finance GPS

Housing Finance GPS is a private decision-support application for comparing
three housing strategies in Brazil:

1. buy now with SAC or Price financing;
2. enter a consortium using explicit contemplation scenarios;
3. continue renting while accumulating capital.

The project has two goals: solve one real, anonymized family decision and
serve as a strong engineering portfolio project. Its core is a deterministic,
auditable, versioned financial engine. AI explanation is optional and comes
only after the calculation engine has been validated.

## Current status

Milestone 0 documentation is ready: governance, provenance, financial
contracts, a synthetic regression reference, and a selected QA baseline are
recorded. The implemented deterministic domain includes SAC,
Price, versioned financing replay, a neutral 60-month comparison ledger,
rent-plus-investment, and synthetic consortium v1 with explicit contemplation
scenarios and in-memory replay. A bounded FastAPI v1 endpoint exposes ephemeral
SAC or Price v3 calculation projections under the
[financing projection contract](docs/specifications/fastapi-v1-financing-projection.md).
Its synthetic-only test suite, including domain properties and HTTP/OpenAPI
contract tests, is checked in CI with a domain coverage gate.

The [minimum synthetic comparison](docs/specifications/minimum-comparison-v1.md)
adds explicit in-memory simulation creation and replay for SAC/Price v3, rent
and one consortium scenario, mandatory constraints and exact-cent tied groups
under a fixed net-worth objective. This closed-cash increment has no monthly
resources; only rent invests. It does not complete M4 or validate household
affordability. The separately versioned
[common monthly resources increment](docs/specifications/common-monthly-resources-v1.md)
adds explicit monthly income/expense composition, resources before obligations,
cash-only feasibility and non-interest-bearing surplus. Funded successors retain
all historical replay; only rent invests.

The [local comparison application](docs/specifications/comparison-application-api-ui-v1.md)
adds explicit transient v2 simulation creation and a Next.js entry/review/result
flow. It collects complete synthetic monthly declarations and displays backend
resources, exclusions, tied groups, metrics and limitations. Transient inputs and results
are memory-only. Explicit [local persistence](docs/specifications/local-comparison-persistence-v1.md)
saves complete synthetic evidence and reopens historical results without calculation.
Real-proposal admission, eligibility expansion and
HTTP replay remain unimplemented. Real financial data remains outside source
control. This delivery does not complete M4 or the MVP.

See [current context](docs/context/CONTEXT.md) for the exact active priority.

## Architecture

- **Frontend:** Next.js and TypeScript, deployed independently.
- **API:** FastAPI with separate v1 financing projection, transient comparison creation and explicit saved-comparison operations.
- **Domain:** pure Python financial calculations without external calls.
- **Persistence:** SQLite for the private MVP, behind migrations.
- **Explanation:** deterministic templates first; optional grounded LLM
  explanation later.

The frontend never owns authoritative financial formulas. Deterministic status
and exclusion text uses backend output; explicit local persistence is available; optional AI remains planned.

## Documentation

- [Product vision](docs/product/vision.md)
- [Current project context](docs/context/CONTEXT.md)
- [Development workflow](docs/process/development-workflow.md)
- [Architecture decisions](docs/adr/README.md)
- [Financial contracts](docs/specifications/financial-contracts.md)
- [Synthetic regression reference and QA baseline](docs/specifications/milestone-0-synthetic-reference-and-qa.md)
- [Historical reference](docs/context/reference.md)
- [Deferred discoveries](docs/context/discoveries.md)

The complete documentation map and ownership rules are in
[docs/README.md](docs/README.md).

## Development

Read [AGENTS.md](AGENTS.md) before modifying the repository.

### Validation

Synchronize the locked development environment:

```text
uv sync --frozen
```

Run Ruff:

```text
uv run ruff check .
```

Run strict Python type checking:

```text
uv run pyright
```

Run the fast synthetic-only test suite (the default excludes `slow` tests):

```text
uv run pytest -q
```

Run only the exhaustive financing matrix:

```text
uv run pytest -q -m slow
```

Run the complete synthetic-only suite, including the matrix:

```text
uv run pytest -q -m ""
```

Unregistered test markers fail collection. CI runs independent `validation`
and `financing_matrix` jobs: the fast suite has domain coverage instrumentation,
and the exhaustive matrix runs without coverage instrumentation.

The configured CI commands, including branch instrumentation and the 95%
total coverage gate over `domain/`, are recorded in
[QA status](docs/context/CONTEXT.md#qa-status).

## Local comparison UI

Use only synthetic data. Start these commands in separate terminals:

```text
uv sync --frozen
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

```text
cd web
npm ci
npm run dev
```

Open http://127.0.0.1:3000. The same-origin rewrite sends comparison requests
only to the local API on port 8000. API documentation is at
http://127.0.0.1:8000/docs. Refreshing loses declarations and transient results;
explicitly saved comparisons remain in the configured local database.

The UI starts blank. Declare every amount, including zeros; use explicit bulk
copies for the 60 resource months and consortium rows, confirm support/scope,
review the declarations and then compare. Waiting costs must match the common
rent projection; this increment does not calculate those inputs for the user.

With Node from `web/.nvmrc`, run frontend checks from `web/`:

```text
npm run contract:check
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm test
```

Regenerate the offline OpenAPI consumer with `npm run contract:generate` after
an approved API schema change. Browser tests use synthetic inputs, the API on
8000 and the production frontend on 3100, leaving a user dev server on 3000 alone.

## Privacy and limitations

No directly identifying personal or financial data belongs in source
control. The application is a private simulation and decision-support tool;
it is not legal, tax, investment, credit, or regulated financial advice.

## Explicit local synthetic persistence

The review step also offers **Comparar e salvar**. It calculates once and
stores the complete evidence; the existing transient compare action is unchanged.
Use **Comparações salvas** to locate readonly results by UTC date and opaque ID,
reopen after restart, or confirm individual deletion. Reopening does not calculate
or verify by replay. Saving an already displayed transient result is unavailable.

Select an absolute database path outside this checkout and initialize it explicitly
before starting the backend, for example:

```bash
export HFGPS_DB_PATH="$HOME/.local/share/housing-finance-gps/synthetic.sqlite3"
uv run python -m scripts.migrate_comparisons
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --no-access-log
```

The server never creates/migrates a database. Without configuration, transient
comparison still works and saved operations report their configuration state.
Use synthetic data only. Retain the file until explicit deletion; deletion removes
application evidence but cannot guarantee forensic erasure or erase external copies.
Only a random operation-ID marker survives individual deletion to reject late retries.
A timeout may occur after commit: consult saved results or repeat the same operation
from the preserved review. Refresh does not automatically submit it again.

The implementation uses standard-library SQLite, schema v1 and SHA-256 corruption
checks, without authentication/private attestation or new replay interfaces. See the
[persistence contract](docs/specifications/local-comparison-persistence-v1.md) and
[ADR-0013](docs/adr/0013-local-comparison-persistence.md) for limits and compatibility.
It does not complete M4 or the MVP.
