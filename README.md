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
contracts, a synthetic regression reference, and a selected (but unconfigured)
QA baseline are recorded. PR #12 merged the first Milestone 1 slice: the sole
implemented financial behavior is a pure deterministic SAC domain. It provides
immutable value and failure types, request normalization, a contractual
schedule, and a 60-month comparison ledger. Its 13 synthetic-only
standard-library tests pass.

Price, comparison contracts and their version envelope, API, frontend,
persistence, CI, dependencies, consortium, rent-plus-investment, eligibility
rules, and real financial data remain unimplemented or out of scope.

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

Read [AGENTS.md](AGENTS.md) before modifying the repository. The concrete
Python and TypeScript setup commands will be documented here after the
foundation milestone selects and configures the toolchains. Do not infer
commands from the product vision.

## Privacy and limitations

No directly identifying personal or financial data belongs in source
control. The application is a private simulation and decision-support tool;
it is not legal, tax, investment, credit, or regulated financial advice.
