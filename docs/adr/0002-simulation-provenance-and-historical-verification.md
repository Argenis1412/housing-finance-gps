# ADR-0002: Bind private envelopes to immutable, root-cosigned attestations

- **Status:** Accepted
- **Date:** 2026-08-18
- **Owners:** Project maintainers
- **Related work item:** Issue #3

## Context

The three simulation identifiers are necessary but do not prove which private
normalized input, convention, trace, or output was validated. A Git keyring
cannot be its own root of trust, and using the current keyring for historical
verification would permit retrospective invalidation after ordinary rotation.

## Decision drivers

- Preserve reproducible, immutable validation lineage.
- Keep private data and secrets outside Git.
- Prevent self-authorization through a mutable current keyring.
- Preserve historical verification across routine key rotation.

## Considered options

1. Store a plain opaque commitment in Git.
2. Trust the current Git keyring when verifying attestations.
3. Use canonical private envelopes, local HMAC commitments, immutable
   root-signed keyring manifests, and root-cosigned attestations.

## Decision

Adopt option 3. Private envelopes use RFC 8785 canonical JSON and are bound
locally with HMAC-SHA-256 using a per-case 256-bit secret. An offline root key
trusted outside Git signs immutable validator-keyring manifests and co-signs
accepted attestations. Every attestation identifies its exact manifest digest.

Historical verification uses the captured manifest and root co-signature, not
the current keyring. The complete protocol is in
[reference-case governance](../specifications/reference-case-governance.md).

## Consequences

### Positive

- Validator authorization is anchored outside the mutable Git content.
- Historical attestations survive routine rotation and retirement.
- Git exposes lineage without exposing private envelopes.

### Negative

- Local operational key handling is required.
- External reviewers can verify authorization and lineage but not private
  envelope contents.

### Neutral or operational

- Validator-key compromise blocks future signatures; it does not rewrite
  root-cosigned historical evidence.
- Root-key compromise has an explicit successor-root or compromised-status
  path.

## Compatibility and migration

None. No persisted simulations or provenance artifacts exist yet.

## Verification

- Review the JCS, HMAC, manifest, signature, rotation, and revocation rules.
- Later add deterministic test vectors before any cryptographic implementation.
- Confirm attestation verification always uses the referenced immutable
  manifest.

## Deferred decisions

- Concrete schema fields for application persistence.
- Key generation, storage, backup, and rotation tooling.
- Automated CI verification and trusted timestamp infrastructure.
