# Reference-Case Governance and Provenance

> Status: accepted Milestone 0 contract
> Related ADRs: [ADR-0001](../adr/0001-private-reference-case-governance.md), [ADR-0002](../adr/0002-simulation-provenance-and-historical-verification.md)
> Related issue: #3

## Purpose and boundary

The real family reference case remains the private MVP acceptance anchor. Its
complete inputs and outputs are useful to the owner but are sensitive enough
to remain outside source control. This contract preserves local
reproducibility and Git-visible validation lineage without claiming that a
reviewer can reconstruct private values.

This contract does not create, distribute, or store a real reference case,
cryptographic secret, or private key.

## Artifact classes

| Class | Permitted content | Location and circulation |
| --- | --- | --- |
| `private_reproducible_export` | Complete normalized private envelope and outputs. | Local, owner-controlled storage only. Never Git, CI, logs, fixtures, or shared exports. |
| `redacted_validation_attestation` | Version metadata, commitments, revision lineage, validation status, and signatures. | Versioned in Git. Never includes real financial values, identifiers, proposal documents, or private keys. |
| `synthetic_regression_fixture` | Invented non-identifying inputs and expected outputs. | Versioned in Git and eligible for CI. |

No artifact may be reclassified by removing only names or identifiers. A
private artifact becomes shareable only when it is independently rebuilt as a
synthetic fixture or a redacted attestation under this contract.

## Private reproducible envelope

The private envelope is a schema-versioned JSON document. Before commitment it
is serialized with RFC 8785 JSON Canonicalization Scheme (JCS). It contains:

- `schema_version` and an opaque `reference_case_id`;
- complete normalized inputs and their observed, contractual, rule, or
  projected-assumption classification;
- source provenance, assumptions, currency, timezone, rounding convention,
  comparison horizon, and explicit calculation timestamp;
- `engine_version`, `ruleset_version`, and `data_snapshot_id`;
- calculation trace, normalized output, and validation result.

The envelope does not depend on a system clock, locale, environment variable,
or external service to be reproduced. The timestamp is an explicit recorded
input, not a value obtained during calculation.

## Local commitment

The reference-case owner generates and retains one random 256-bit
`case_commitment_secret` for each `reference_case_id`. The secret is not a
Git artifact and is never logged, exported, or supplied to CI.

```text
HMAC-SHA-256(case_commitment_secret, JCS(private_reproducible_envelope))
```

The same secret is retained across revisions of one reference case. Losing it
prevents local proof that later attestations bind to earlier envelopes. That
case is then marked provenance-unverifiable and a replacement receives a new
opaque `reference_case_id`; history is not overwritten.

## Trust root and immutable keyring manifests

The trust root is an offline Ed25519 root public key whose fingerprint is
configured outside the Git repository by a verifier before validation. The
corresponding root private key remains offline and outside the repository.

An immutable validator-keyring manifest is a JCS JSON document with:

- `manifest_version`, immutable `manifest_digest`, and predecessor digest;
- authorized validator public keys, key IDs, validity intervals, and status;
- root public-key fingerprint;
- key additions, replacements, retirement, and revocation records;
- an Ed25519 root signature over the JCS manifest payload.

The root authorizes every manifest transition. A keyring file or its current
Git state is never trusted by itself. A verifier accepts a manifest only when
its digest matches the referenced content and its root signature verifies
against the preconfigured offline-root public key.

## Redacted validation attestation

An attestation is JCS JSON and contains no real financial input, output,
location, proposal, account, name, CPF, or direct identifier. Its signed
payload contains:

- attestation and envelope schema versions;
- opaque `reference_case_id` and monotonically increasing revision number;
- current and predecessor case-commitment values;
- `engine_version`, `ruleset_version`, and `data_snapshot_id`;
- exact `validator_keyring_manifest_digest` and root fingerprint;
- root-accepted timestamp, validation status, and redacted change reason;
- validator signature and root co-signature over the same canonical payload.

The validator first checks the local envelope commitment. The root then
co-signs the attestation. The root co-signature is the authoritative acceptance
time and binds the attestation to the manifest digest already authorized by
that root.

## Historical verification and key events

To verify an attestation, a verifier:

1. loads the exact manifest identified by `validator_keyring_manifest_digest`;
2. verifies the manifest digest and root signature with the preconfigured root
   public key;
3. verifies that the named validator key was authorized by that immutable
   manifest;
4. verifies validator and root co-signatures over the canonical attestation
   payload.

Verification never substitutes the current keyring for the captured manifest.

- Routine rotation or retirement prevents future validator signatures and does
  not invalidate root-cosigned historical attestations.
- Validator-key compromise prevents future use. Root-cosigned attestations
  accepted before the compromise record remain historical evidence; they are
  not silently deleted or reinterpreted.
- Root-key compromise requires a successor-root transition signed by the
  previous root. If that is impossible, historical artifacts remain immutable
  but their trust status is explicitly reported as compromised.

This design verifies signer authorization and lineage in Git. Only the local
owner holding the commitment secret can verify that an attestation binds to
the private envelope. External reviewers cannot reconstruct or inspect that
envelope.

## Local validation procedure

The owner validates the real case outside the repository:

1. Create or update the private envelope using the approved schema.
2. Canonicalize it with JCS and calculate the HMAC commitment locally.
3. Validate the calculation result against the approved contract.
4. Produce a redacted attestation and obtain validator and root signatures.
5. Commit only the redacted attestation and any root-signed keyring manifest.

Private envelopes, secrets, and private keys remain outside the checkout. CI
receives only synthetic fixtures and redacted attestations.

## Deferred operational work

- Key generation, secure storage, backup, enrollment, and signature tooling.
- Automated cryptographic verification in CI.
- Private-envelope import/export implementation.
- Synthetic reference fixtures and financial calculation contracts.
