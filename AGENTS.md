# Housing Finance GPS Agent Contract

Read this file before working in the repository. It is the canonical
session contract for AI-assisted work, regardless of the tool being used.

## Required reading order

1. Read `AGENTS.md`.
2. Read `docs/context/CONTEXT.md` for the current repository state.
3. Read `docs/product/vision.md` for product scope and accepted boundaries.
4. Read `docs/process/development-workflow.md` for the applicable delivery
   track and approval gates.
5. Read relevant ADRs and task-specific documentation.
6. Inspect the affected implementation and tests before proposing changes.

Do not treat `docs/context/reference.md` or
`docs/context/discoveries.md` as required daily reading. Consult them when
the task touches a recorded decision, failed approach, or deferred issue.

## Working rules

- Do not invent requirements or broaden the approved scope.
- Implement the smallest correct change that satisfies explicit acceptance
  criteria.
- Preserve public contracts, architecture invariants, and historical
  simulation reproducibility.
- Reuse established patterns before adding dependencies or abstractions.
- Keep diffs focused and record unrelated debt in
  `docs/context/discoveries.md` instead of fixing it opportunistically.
- Write code, documentation, comments, branches, commits, issues, and pull
  requests in English.
- Conversation with the user may follow the language used by the user.
- Do not add AI attribution or `Co-Authored-By` trailers.
- Never commit real names, CPF numbers, addresses, account identifiers,
  proposal documents, or other identifying financial data.

## Approval boundary

For behavioral code, financial rules, public contracts, persistence, or
deployment changes:

1. diagnose the current state;
2. define or confirm acceptance criteria and non-goals;
3. identify affected files, tests, risks, and modification budget;
4. present a plan;
5. wait for explicit approval before implementation.

An explicit request to edit named documentation counts as approval for that
documentation scope only. It does not authorize adjacent code or workflow
changes.

## Architecture invariants

These rules come from the approved product vision and must not change
without an ADR and explicit approval:

1. The Python financial domain is deterministic and authoritative.
2. Domain calculation functions do not depend on HTTP, databases, the
   system clock, locale, environment variables, or external services.
3. The Next.js frontend displays and collects data but does not implement
   authoritative financial formulas.
4. Observed data, contractual data, rules, and projected assumptions remain
   distinct in contracts and stored simulations.
5. Unsupported financial or eligibility rules fail explicitly; they are
   never silently approximated.
6. Historical simulations are immutable and reproducible through
   `engine_version`, `ruleset_version`, and `data_snapshot_id`.
7. Consortium contemplation uses explicit user scenarios without invented
   probabilities.
8. A language model may explain validated engine output but may not
   calculate, rank, alter, or invent financial values.
9. Market validation, B2B2C distribution, monetization, bank integrations,
   and document OCR remain outside the MVP.

## Canonical ownership

- `docs/product/vision.md`: product purpose, scope, architecture direction,
  roadmap, and MVP acceptance.
- `docs/context/CONTEXT.md`: current repository state and one active
  priority.
- `docs/process/development-workflow.md`: development and review process.
- `docs/adr/`: rationale for accepted architectural decisions.
- `docs/context/reference.md`: historical decisions, failed approaches,
  open design questions, and periodic audit results.
- `docs/context/discoveries.md`: append-only log of out-of-scope discoveries.

When documents conflict, stop and report the contradiction. Do not choose a
convenient interpretation silently.
