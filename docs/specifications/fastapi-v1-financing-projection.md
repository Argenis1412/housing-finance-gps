# FastAPI v1 Financing Calculation Projection Contract

> Status: accepted Track C contract
> Related work item: Issue #39
> Domain authority: [ADR-0004](../adr/0004-backend-authoritative-financial-contracts.md)

## Purpose and boundary

`POST /api/v1/financing/calculations` returns an ephemeral
`calculation_projection` for an explicitly fixed v3 SAC or Price financing
calculation. It is not a `simulation_result` and creates no persisted,
exportable, replayable, comparable, attested, or decision-presented artifact.

The endpoint exposes no `data_snapshot_id`, canonical request, sealed outcome,
timestamp, or persistence identifier. A future explicit simulation-creation
boundary owns the transition to a `simulation_result`, including the complete
version tuple, canonical request, sealed outcome, and `data_snapshot_id`.
There is no implicit transition.

## Version selection

The server selects these identifiers before domain normalization:

| Field | Value |
| --- | --- |
| `api_version` | `v1` |
| `contract_schema_version` | `financing-replay-v3` |
| `engine_version` | `financing-centavo-safe-v3` |
| `ruleset_version` | `financing-ruleset-v2` |

Clients cannot select, infer, migrate, or fall back across these versions.

## Request and success response

The request contains `strategy` (`sac` or `price`) and the closed financing
input owned by the domain. The success response contains the selected strategy,
the version identifiers above, the full contractual schedule, and the month
0 through 60 comparison ledger. All monetary values remain decimal strings.

## Resource admission

The public HTTP boundary, not the domain, enforces:

| Value | Limit |
| --- | --- |
| BRL input | Optional sign, 1–18 integer digits, exactly 2 fractional digits |
| Rate input | Fixed decimal `0..1`, at most 12 fractional digits, no exponent notation |
| Term | Strict integer `1..600` |
| Request body | 8,192 bytes maximum before JSON parsing |
| Serialized success response | 262,144 bytes maximum before return |

The rate and monetary limits are API admission limits only. They do not alter
the deterministic domain contract or historical replay behavior.

## Errors

`ApiErrorV1` contains only a stable machine-readable `code` and a safe
Portuguese `message_pt_br`. Domain diagnostic text is not public API data.

| HTTP status | Code | Meaning |
| --- | --- | --- |
| 409 | `incompatible_contract_version` | The requested contract cannot be interpreted safely. |
| 413 | `request_too_large` | The request body exceeds the public byte limit. |
| 422 | Domain failure code or `invalid_input` | The input is invalid, unsupported, infeasible, or outside the API envelope. |
| 500 | `internal_error` | An unexpected server failure occurred. |

## Dependency direction

The dependency direction is `FastAPI -> application -> domain`. The API owns
HTTP schemas, resource admission, and public error representation. The
application selects the fixed v3 domain entry point. The domain remains pure
and has no FastAPI, HTTP, application, persistence, clock, environment, or
external-service dependency.
