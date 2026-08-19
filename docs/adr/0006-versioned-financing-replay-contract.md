# ADR-0006: Define verifiable versioned financing replay

- **Status:** Accepted
- **Date:** 2026-08-19
- **Owners:** Project maintainers
- **Related work item:** Issue #23

## Context

ADR-0005 requires any future financing extension that changes a posting or
result to preserve replay of prior simulations. The repository has no runtime
simulation envelope, persistence layer, replay dispatcher, or selected version
values. SAC and Price currently reject a positive `fee_amount` during
normalization with `unsupported_contract_clause`.

Retaining a stored historical output is not replay: it cannot demonstrate that
the historical schema, parser, normalization boundary, and calculator still
produce the sealed success or failure. Ignoring a positive fee while replaying
the current engine would turn its historical typed rejection into a successful
calculation and violate the supported-contract boundary.

## Decision drivers

- Preserve historical successes and typed failures as reproducible behavior.
- Make semantic drift or a missing historical evaluator fail safely.
- Keep envelope dispatch separate from the pure strategy-owned financial
  calculations.

## Considered options

1. Treat a stored result as a replay result.
2. Reexecute only the current parser and calculator for every historical
   request.
3. Define a versioned immutable envelope and reexecute the historical handler
   before accepting a replay result.

## Decision

Adopt option 3. `SimulationReplayEnvelope` is the only object eligible for
future replay. It is immutable and contains:

- `contract_schema_version`;
- the selected strategy;
- the complete canonical raw request;
- `engine_version`, `ruleset_version`, and `data_snapshot_id`; and
- one sealed outcome: either a success with canonical normalized input and
  output trace, or a failure with its typed code and canonical safe detail.

The envelope's raw request and outcome use the RFC 8785 canonical JSON form
already required for private reproducible envelopes by ADR-0002. When an
envelope is retained as private evidence, the existing ADR-0002 HMAC
commitment binds the entire canonical envelope, including its versions and
outcome. This decision creates no persistence or cryptographic implementation.

Historical-result retrieval may return a sealed outcome for audit, but it is
not a replay. Verifiable replay must:

1. select the historical schema and parser from the envelope's
   `contract_schema_version` and `engine_version` before normalization;
2. select the matching historical calculator for the envelope's strategy;
3. execute the canonical raw request without substituting current semantics;
   and
4. compare the execution with the sealed outcome exactly.

Exact comparison requires the same success or failure category. For a success,
it also requires identical canonical normalized input and output trace. For a
failure, it requires the same typed code and canonical safe detail. If the
required schema or handler is unavailable, or if equivalence cannot be proven,
the replay operation returns `incompatible_contract_version`; it never returns
the stored outcome as a successful replay.

The replay boundary owns version-to-handler selection. `domain/financing`
continues to own each selected handler's pure financing semantics and schedule
transitions. `domain/ledger.py` remains neutral and owns neither dispatch nor
financing-clause semantics.

Until a later admission assigns and implements version values, the pre-fee
financing behavior remains historical: a positive `fee_amount` is
`unsupported_contract_clause`; absence and the accepted explicit-zero fee
declaration retain their current successful behavior. A historical envelope
recording that failure must replay the failure, never ignore the positive fee.

## Consequences

### Positive

- Historical evidence and executable replay have distinct, testable meaning.
- A missing historical evaluator or semantic drift cannot silently pass as a
  replay result.
- Future fee admission has a defined boundary for preserving the existing
  positive-fee rejection.

### Negative

- Every future calculation-affecting release needs retained schema and handler
  compatibility, not only stored outputs.

### Neutral or operational

- This decision defines a future contract only; it creates no current runtime
  selector, schema, persistence artifact, version value, or public API.
- Observed external data remain subject to their independent
  `data_snapshot_id` treatment.

## Compatibility and migration

No current API, persistence, simulation envelope, domain behavior, or stored
simulation changes. A future replay implementation must reject an envelope it
cannot interpret safely with `incompatible_contract_version`. It may not map a
legacy positive-fee request to a fee-free success.

## Verification

- Review envelope fields, canonicalization, and ownership against ADR-0002,
  ADR-0003, ADR-0005, and the product versioning contract.
- Before implementation, test historical successful and failed envelopes,
  missing schemas or handlers, and semantic-output mismatch as explicit replay
  outcomes.
- Verify a future fee implementation retains absent and explicit-zero behavior
  and preserves the legacy positive-fee rejection under its historical engine
  handler.

## Deferred decisions

- Runtime envelope storage, dispatcher registration, serialization code, and
  cryptographic tooling.
- Concrete schema and version values, migration policy, and public replay API.
- Fixed monthly financing-fee admission and implementation.
- Insurance, nonzero indexation, transaction costs, extraordinary
  amortization, taxes, and eligibility-rule support.
