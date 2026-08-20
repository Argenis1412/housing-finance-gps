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
Price, a neutral 60-month comparison ledger, and rent-plus-investment. Its
synthetic-only test suite is checked in CI.

Comparison contracts beyond the neutral ledger and version envelope, API,
frontend, persistence, dependency toolchains, consortium, eligibility rules,
and real financial data remain unimplemented or out of scope.

See [current context](docs/context/CONTEXT.md) for the exact active priority.

## Planned architecture

- **Frontend:** Next.js and TypeScript, deployed independently.
- **API:** FastAPI with typed, versioned JSON contracts.
- **Domain:** pure Python financial calculations without external calls.
- **Persistence:** SQLite for the private MVP, behind migrations.
- **Explanation:** deterministic templates first; optional grounded LLM
  explanation later.

The frontend never owns authoritative financial formulas.

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

Run the synthetic-only test suite:

```text
uv run pytest -q
```

## Privacy and limitations

No directly identifying personal or financial data belongs in source
control. The application is a private simulation and decision-support tool;
it is not legal, tax, investment, credit, or regulated financial advice.
