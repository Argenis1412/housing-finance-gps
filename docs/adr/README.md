# Architecture Decision Records

ADRs document accepted architecture decisions that are difficult or costly
to reverse. The [product vision](../product/vision.md) identifies the initial
decisions that require ADRs, but it does not replace their implementation
rationale.

## Status values

- `Proposed`
- `Accepted`
- `Superseded by ADR-NNNN`
- `Rejected`

## Naming

```text
NNNN-short-kebab-case-title.md
```

Numbers are sequential and never reused.

## Required content

Use [0000-template.md](0000-template.md). Every accepted ADR states:

- the concrete context and forces;
- the decision;
- alternatives considered;
- positive and negative consequences;
- compatibility or migration impact;
- verification evidence;
- decisions intentionally left open.

## Index

| ADR | Status | Decision |
| --- | --- | --- |
| [ADR-0001](0001-private-reference-case-governance.md) | Accepted | Keep the real acceptance case private and store only redacted provenance in Git. |
| [ADR-0002](0002-simulation-provenance-and-historical-verification.md) | Accepted | Bind private envelopes to root-cosigned, immutable-manifest attestations. |
| [ADR-0003](0003-money-rate-period-rounding-and-ledger.md) | Accepted | Define deterministic financial value conventions and a common ledger. |
| [ADR-0004](0004-backend-authoritative-financial-contracts.md) | Accepted | Keep authoritative financial calculations in the backend contract. |

Do not create speculative ADRs merely to fill the initial list. Write each
record when its decision is required for an approved work item.
