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
affordability. Common monthly resources require a separately approved increment
before the family-use vertical slice.

Frontend, persistence, real-proposal consortium admission and eligibility rules
remain unimplemented. The API does not expose replay or create simulation
results. Real financial data remains outside source control. Dependency
review remains deferred.

See [current context](docs/context/CONTEXT.md) for the exact active priority.

## Architecture

- **Frontend:** Next.js and TypeScript, deployed independently.
- **API:** FastAPI with the implemented typed v1 financing projection.
- **Domain:** pure Python financial calculations without external calls.
- **Persistence:** SQLite for the private MVP, behind migrations.
- **Explanation:** deterministic templates first; optional grounded LLM
  explanation later.

The frontend never owns authoritative financial formulas.
The frontend, persistence, and explanation layers remain planned.

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

## Privacy and limitations

No directly identifying personal or financial data belongs in source
control. The application is a private simulation and decision-support tool;
it is not legal, tax, investment, credit, or regulated financial advice.
