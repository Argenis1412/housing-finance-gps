# Minimal Local Synthetic Comparison Persistence v1

> Accepted Track C contract, Issue #55; [ADR-0013](../adr/0013-local-comparison-persistence.md).

## Scope and authorities

Add explicit compare-and-save, list, readonly reopening and individual deletion
for the existing four-alternative, 60-month synthetic comparison v2. Preserve
[transient creation](comparison-application-api-ui-v1.md), financing projection
v3 and every retained domain version/fixture. Python remains authoritative.
No financial formula, classification, resource posting, constraint or ranking
changes. Only rent invests; all existing limitations remain visible.

## Complete immutable artifact

Canonical `saved-comparison-v1` records contain exactly `record_schema_version`,
`simulation_id`, `saved_at` and `envelope`. The envelope contains all eight
original `ComparisonSimulationEnvelope` fields, including unchanged canonical
`raw_request_jcs` and `sealed_outcome_jcs`. These include complete parent/child
requests, outcomes or admission failures, composition, provenance, conventions,
constraints, metrics and groups. Never substitute the presentation JSON.

SHA-256 covers the complete UTF-8 canonical wrapper. It detects accidental
corruption; it does not authenticate sources or establish financial replay
agreement. It is not the private-case commitment/attestation protocol in
ADR-0002. The opaque storage ID is independent of backend-supplied snapshot
metadata. Calculation and saving timestamps are separate recorded UTC values.

SQLite schema v1 separates append-only operation UUIDs from immutable records.
Triggers reject updates and deletion of operation markers. Individual deletion
removes the entire record, including checksum and saved metadata, while retaining
only its random UUID. Retention lasts until explicit deletion. Deletion is
logical; no forensic-erasure or external-copy removal guarantee is made.

## Explicit operations

| Operation | Behavior |
| --- | --- |
| `POST /api/v1/comparison/saved-simulations` | Closed object: required canonical UUIDv4 `operation_id` and existing six-field `comparison`. New creation returns 201; identical canonical request under a saved ID returns 200 without evaluation. |
| `GET /api/v1/comparison/saved-simulations` | Only `simulation_id` and `saved_at` index summaries, ordered by saved time descending then ID descending. `limit` defaults to 20, range 1..50; `offset` is 0..2^53-1. `next_offset` is null at the end. Summaries are unverified until opening. |
| `GET /api/v1/comparison/saved-simulations/{simulation_id}` | Read the stored historical result without normalization, calculation or replay. |
| `DELETE /api/v1/comparison/saved-simulations/{simulation_id}` | Delete evidence explicitly; 204 for an existing or already deleted operation, 404 for unknown IDs. |

`operation_id` also becomes the saved `simulation_id`. A different canonical
request under a live ID conflicts (409); a deleted ID returns 410 on create/read.
Global failures never save or reserve an ID. All aggregate successes are
savable, including `no_eligible`, constraint exclusions and child domain failures.

Creation/read return `api_version=v1`, `kind=saved_comparison`, `simulation_id`,
`saved_at` and `result`, the existing typed `ComparisonSimulationResultV1`.
The complete evidence remains backend-local. All responses use `no-store`.

## Atomicity, preparation and integrity

Use per-operation SQLite connections, bound SQL, a five-second busy timeout,
standard rollback journal and `synchronous=FULL` on writes. `BEGIN IMMEDIATE`
serializes ID lookup, evaluation, validation, insertion and deletion. There is
no automatic retry. For a fresh ID, the factory runs once. A retry of a saved
ID reads its evidence without selecting a calculator.

The application takes a framework-independent preparation callback. Before
inserting/committing, the API callback applies typed models, fixed safe messages,
optional-field omission, final serialization and response limits. Any failure
rolls back artifact and ID together. Return those exact bytes after commit.
Lost HTTP confirmation never proves rollback; repeat the same operation ID.

Reading verifies the byte limit, checksum, canonical wrapper, record version,
requested/index/wrapper IDs, index/wrapper saved times, metadata agreement,
aggregate/child tuples and evidence structure. It uses no financial normalizer
or arithmetic validator. Known child admission failures remain distinct from
sealed execution. Supported presentation does not require replay dispatch.
The saved record version pins presentation v1 over comparison v2. Future
changes must retain that decoding/presentation path or fail explicitly.

Unknown record/envelope versions never fall back to latest. Corrupt or
unsupported rows remain listable/deletable and do not block other records.
An unknown database schema blocks all persistence operations because its
layout cannot be assumed. Existing domain replay remains callable in Python;
tests replay recovered envelopes. No replay interface or verification claim
is added to the UI.

## Configuration and migrations

`HFGPS_DB_PATH` is an explicit absolute file path outside the checkout. Reject
both lexical containment and resolved containment, including symbolic links
into the checkout. No default user database is selected. With no configuration,
transient creation/projection remain functional.

Run `uv run python -m scripts.migrate_comparisons` explicitly with that variable
configured. The command creates parent directories and initializes an empty
SQLite database transactionally with `application_id=0x48464750`, `user_version=1`
and the ordered v1 schema statements. Repeating v1 is a no-op. Unknown/future
versions or unrelated nonempty databases are rejected without writes. Failed
initialization leaves no partial schema. There is no downgrade or envelope
rewrite. Runtime opens existing files only; import/app creation/OpenAPI never
create or migrate storage. Browser tests use an isolated temporary database,
ignoring the user's configured file and cleaning it after backend shutdown.

## Admission and safe failures

Preserve strict closed JSON admission, duplicate/numeric/depth/Unicode checks
and a 1,048,576-byte request cap, including trailing-slash POST redirects.
GET/DELETE bodies are not interpreted as creation JSON. The complete saved
response cap is 4,194,304 bytes; canonical stored-record cap is 16,777,216 bytes.
All creation limits are checked before commit; never truncate evidence.

| HTTP | Codes |
| --- | --- |
| 404 / 410 | `simulation_not_found` / `simulation_deleted` |
| 409 | `operation_id_conflict`, `incompatible_storage_version`, `incompatible_contract_version` |
| 413 / 422 | `request_too_large`; global validation/domain errors, `response_too_large`, `evidence_too_large` |
| 503 | `storage_not_configured`, `storage_not_initialized`, `storage_busy`, `storage_unavailable` |
| 500 | `stored_simulation_corrupt`, `internal_error` |

Use fixed Portuguese messages and existing comparison error shape. Never expose
financial inputs, SQL diagnostics, filesystem paths or tracebacks. Unexpected
execution errors are not financial exclusions. Existing endpoint error families
and limits remain unchanged. OpenAPI metadata is 1.2.0; HTTP remains v1.

## Minimum UI lifecycle

Review offers transient compare and explicit compare-and-save. Save disables
conflicting actions while pending. A stable UUID is reused for explicit retries;
network/timeout or illegible confirmation preserves declarations and shows
confirmation pending. Canceling HTTP never claims a canceled database write.
Editing after uncertainty starts another operation; the earlier one may still
appear in saved results. Reload never automatically resubmits.

The saved page lists UTC dates and short IDs, opens the existing readonly result
and confirms individual deletion. It includes loading, empty, error and paging
states with keyboard-accessible native controls. Deletion cancel changes nothing;
confirmed deletion clears viewed evidence. Opening never refills the input form.
Use no financial URL parameters, browser storage, body logs or analytics.

Drafts, saving displayed transient output, duplicate/edit/history comparison,
import/export, replay interfaces, authentication, remote deployment, private-case
validation, sensitivity, break-even, optimization, polish and financial expansion
remain outside this increment. It completes neither M4 nor the MVP.
