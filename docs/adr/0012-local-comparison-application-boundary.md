# ADR-0012: Expose transient comparison v2 through a local application and UI

- **Status:** Accepted
- **Date:** 2026-11-03
- **Owners:** Project maintainers
- **Related work item:** Issue #53

## Context

Comparison v2 already owns funded synthetic comparison and retained evidence.
The existing financing HTTP operation is only an ephemeral v3 projection.
B needs a useful entry/review/result flow without promoting that projection,
reinterpreting domain failures, or implying persistence or household validation.

## Decision drivers

- Preserve Python authority, retained versions and exact-cent comparison.
- Make origin declarations, exclusions, investment asymmetry and limits visible.
- Keep the first vertical slice local, synthetic and transient.

## Considered options

1. Reuse the projection as a simulation or calculate missing values in the UI.
2. Add persistence, preview calculations and an assisted input schema first.
3. Add an explicit transient creation boundary over the existing v2 request.

## Decision

Adopt option 3 under the [B contract](../specifications/comparison-application-api-ui-v1.md).
The application selects v2, supplies injectable UTC and opaque snapshot metadata,
creates retained evidence once and copies its sealed outcome. Evidence remains
internal and request-scoped; the browser receives a typed presentation result.
Source dates and classifications remain explicit declarations.

One additive HTTP operation preserves global versus individual domain failures.
Its six semantic input fields intentionally accept closed JSON, without schema
coercion, child defaults or clause stripping. New-route-only representation and
resource admission precedes domain execution. Strict result models and consumer
compatibility checks protect the output. Projection v3 keeps its contract.

Next.js collects declarations and renders backend output. Literal bulk copies
require preview/confirmation. The review contains declared inputs only, so no
preview endpoint or frontend financial derivation is needed. Source Sans 3 is
bundled locally; native controls and a comparative matrix avoid a UI framework
or chart dependency. OpenAPI generates TypeScript with openapi-typescript 7.
A named recursive codec alias resolves TypeScript's indexed-union recursion;
it adds no financial typing or validation policy.

## Consequences

### Positive

- Complete synthetic entry/review/comparison flow without financial changes.
- Global admission, local exclusions, ties and historical evidence stay owned
  by the same retained authority.
- Separate deployments remain possible while the first operation is local.

### Negative

- Users explicitly enter complete schedules and waiting costs, including
  adjusted rent values; there is no automatic schedule preparation.
- Refreshing the page loses inputs and results. No public replay is available.
- Permissive input schemas require durable field documentation and domain/API
  parity tests; generated types alone cannot establish semantic validity.

### Neutral or operational

- Loopback FastAPI and Next.js communicate through a same-origin rewrite.
- Snapshots identify a fresh execution, not stored records or authenticated
  facts. Repeated calls have fresh metadata and equal financial output.
- The budget is 44 files, six new Python modules, 30 total code modules,
  28 production classes, 13 direct dependencies, two additive boundaries and
  at most 48 new public Python production symbols. Delivered counts are 43
  files, 17 production classes and 31 new public Python production symbols
  (imports, fields and methods excluded). No domain/fixture changes.
- Independent AC challenge and adversarial plan review preceded explicit
  approval. Independent diff review and configured QA precede delivery.

## Compatibility and migration

No financial tuple changes or historical migration. The new operation pins
comparison-simulation-v2 / comparison-monthly-resources-v2 / comparison-ruleset-v2
and the existing funded children. HTTP remains v1; OpenAPI application metadata
becomes 1.1.0. No projection promotion, persistence or replay registration.

## Verification

Domain/application/HTTP parity, global/local failure precedence, safe JSON
admission and errors, resource boundaries, exact large monetary strings,
projection compatibility, unchanged replay fixtures, generated contract checks,
desktop/mobile synthetic browser journeys, review invalidation and stale-request
protection, followed by the complete configured backend and frontend QA.

## Deferred decisions

Persistence, import/export, replay HTTP, remote private access, assisted financial
previews, charts, financial expansion, private reference validation, sensitivity,
break-even, optimization and polish require separate scope and approval.
This delivery completes neither M4 nor the MVP.
