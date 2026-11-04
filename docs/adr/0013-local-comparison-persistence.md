# ADR-0013: Preserve complete synthetic comparison evidence in local SQLite

- **Status:** Accepted
- **Date:** 2026-11-04
- **Owners:** Project maintainers
- **Related work item:** Issue #55

## Context

PR #54 exposes an explicit transient comparison v2 and projects its sealed
outcome for the browser. Reloading loses declarations and results. The public
presentation omits child replay evidence and cannot substitute for the complete
envelope. Saving a displayed transient result would require another evidence
lifecycle or an implicit recalculation.

## Decision drivers

- Preserve complete historical evidence without financial changes.
- Keep creation, storage, retrieval and replay distinct.
- Make local retention, deletion, failure and version handling explicit.

## Considered options

1. Persist presentation JSON or recalculate when saving/opening.
2. Retain backend drafts so users can save after viewing a transient result.
3. Offer explicit compare-and-save at review and immutable local retrieval.

## Decision

Adopt option 3 under the [persistence contract](../specifications/local-comparison-persistence-v1.md).
Store the complete eight-field envelope in a canonical `saved-comparison-v1`
wrapper, with opaque operation ID, UTC saved time and SHA-256 over all wrapper
bytes. Preserve original child evidence and sealed outcomes. The checksum
protects against accidental corruption; ADR-0002 private HMAC commitments and
root-cosigned attestations are not implemented or replaced.

Use standard-library SQLite, explicit transactional schema migrations and an
absolute configured path outside the checkout. Runtime never creates/migrates
storage. A framework-independent application port owns use cases; the API
injects final response preparation inside the write transaction. Success is
returned only after commit, using those exact prepared bytes.

Stable operation UUIDs serialize retries. Deletion removes the complete record
and retains only its random UUID, preventing delayed retry resurrection. There
are no update/rename operations. Reading checks storage integrity, identities,
metadata and supported structures, then copies the sealed presentation without
normalization, calculation or replay. Unknown versions fail explicitly.

## Consequences

### Positive

- Saved results survive restart without changing historical evidence.
- Retry after lost confirmation does not create another execution or record.
- Corruption/incompatibility cannot silently become a financial exclusion.

### Negative

- Saving after viewing a transient result remains unavailable.
- One SQLite writer serializes creation, including evaluation and preparation.
- Logical deletion does not guarantee forensic erasure or delete external copies.
- Supported storage codecs and presentation versions require maintenance.

### Neutral or operational

- Synthetic use only; no private-case validation, authentication or remote use.
- Retention lasts until explicit individual deletion; no automatic purge.
- No dependencies or financial versions change. Four additive HTTP operations,
  one application service boundary and one local migration command are admitted.
- Independent AC challenge and adversarial review preceded user implementation
  approval. Independent diff review and complete configured QA precede delivery.
- Approved ceiling: 33 files, 13 new code modules (nine production/four tests),
  12 production classes, 32 public Python production symbols and zero dependencies.

## Compatibility and migration

Existing projection v3 and transient comparison v2 keep their contracts. HTTP
remains v1; OpenAPI metadata becomes 1.2.0. Initial SQLite schema v1 has an
application identifier and an explicit migration command. Database schema,
record schema and financial tuples are independent. Storage migrations must
never rewrite envelope bytes or select current financial behavior for history.
All prior replay versions and fixtures remain unchanged.

## Verification

Complete envelope byte round-trip and retained replay; no-execution retrieval
and retries; concurrent ID admission; rollback including presenter/commit
failures; corruption/metadata/version checks; migration and path boundaries;
legacy HTTP compatibility; generated consumer checks; desktop/mobile synthetic
save/reopen/delete and lost-confirmation journeys; full backend/frontend QA.

The prior B acceptance baseline was 541 fast Python tests, four slow tests,
24 frontend tests and 98% domain coverage. Planning exercised 131 selected
application/replay tests; neither count substitutes for this increment's full
QA. Independent diff review closed after structural-evidence, historical-error,
filesystem-error and illegible-index-date regressions were added. Final local
QA passes 610 fast Python tests, four slow tests, 34 frontend tests and 98%
domain coverage, plus lint, strict types, OpenAPI/consumer checks and build.

## Deferred decisions

Drafts, saving displayed transient results, duplicate/edit/history comparison,
import/export, replay CLI/HTTP, private attestation, remote operation, recovery
product flows, financial expansion, sensitivity, break-even and optimization.
This increment completes neither M4 nor the MVP.
