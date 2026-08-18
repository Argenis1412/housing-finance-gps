# ADR-0004: Keep financial calculation authority in the backend contract

- **Status:** Accepted
- **Date:** 2026-08-18
- **Owners:** Project maintainers
- **Related work item:** Issue #5

## Context

The frontend and backend are separately deployable. If the frontend recreates financial calculations, it can diverge from the pure Python domain and show numbers that cannot be reproduced through the authoritative engine. The vision requires a versioned API and prohibits authoritative frontend formulas.

## Decision drivers

- One authoritative financial result for every normalized input.
- Contract compatibility between independently deployed frontend and backend.
- Clear ownership of validation, safe errors, and presentation.

## Considered options

1. Duplicate simple financial formulas in TypeScript for responsiveness.
2. Share calculation logic across Python and TypeScript.
3. Keep all authoritative financial calculation in the backend and expose versioned contracts to a presentation-only frontend.

## Decision

Adopt option 3. The pure Python domain and backend contract own calculation, financial validation, schedule generation, comparison metrics, ranking, and unsupported-case outcomes. The frontend collects inputs, renders backend results, formats values, and validates presentation state only. Future TypeScript types are generated from or validated against the versioned backend contract.

## Consequences

### Positive

- No client-side calculation can silently diverge from the engine.
- API contract tests can protect the deployment boundary.
- Results remain traceable to engine and ruleset versions.

### Negative

- The frontend depends on backend responses for authoritative result updates.
- API availability and contract compatibility become explicit quality concerns.

### Neutral or operational

- The initial OpenAPI tooling choice is deferred to the QA/toolchain work item.
- Formatting and non-financial form validation remain frontend responsibilities.

## Compatibility and migration

None. No API or frontend implementation exists.

## Verification

- Review the financial contract for backend-only formula ownership.
- Later add API schema compatibility tests and a static/frontend review that rejects authoritative financial formulas outside the backend.

## Deferred decisions

- Exact OpenAPI-to-TypeScript generation tool.
- Endpoint shape, authentication, deployment, and browser interaction details.
