# ADR-0001: Keep the real reference case private and attest validation in Git

- **Status:** Accepted
- **Date:** 2026-08-18
- **Owners:** Project maintainers
- **Related work item:** Issue #3

## Context

The MVP is accepted against one real family decision. That case contains
sensitive financial facts and potentially re-identifying combinations of
otherwise non-direct data. The repository must not contain real names, CPF
numbers, addresses, account identifiers, proposal documents, or real financial
data. A synthetic fixture alone cannot replace the real acceptance anchor.

## Decision drivers

- Preserve the real acceptance anchor.
- Keep sensitive data outside source control and CI.
- Retain reviewable provenance without promising public reconstruction.

## Considered options

1. Commit a sanitized real fixture.
2. Replace the real case with a synthetic fixture.
3. Keep the real case private and commit only redacted validation provenance.

## Decision

Adopt option 3. The complete real reference case is a local-only private
reproducible export. Git may contain redacted validation attestations and
synthetic regression fixtures only. The full governance contract is
[reference-case governance](../specifications/reference-case-governance.md).

## Consequences

### Positive

- Preserves the real decision as the MVP acceptance anchor.
- Avoids committing sensitive financial data or re-identifying combinations.
- Separates private acceptance evidence from public regression data.

### Negative

- External reviewers cannot independently reconstruct the real case.
- The owner must retain private artifacts and execute local validation.

### Neutral or operational

- Git records validation lineage, not private values.
- Synthetic fixtures remain required for automated regression testing.

## Compatibility and migration

None. No real reference-case artifact has been committed.

## Verification

- Review that tracked artifacts follow the three artifact classes.
- Confirm no real values, identifiers, secrets, or private keys enter Git.
- Verify that the local validation procedure records a redacted attestation.

## Deferred decisions

- Key storage, backup, enrollment, and signature tooling.
- Automated provenance verification.
