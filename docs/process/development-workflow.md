# Development Workflow — Housing Finance GPS

> Read [AGENTS.md](../../AGENTS.md) first. It defines the session contract,
> approval boundary, and architecture invariants. This document defines how
> changes are delivered.

## 1. Golden rule

Implement the smallest correct change that satisfies approved acceptance
criteria while preserving deterministic financial behavior and reproducible
historical results.

## 2. Start every task

1. Read the work item or request.
2. Read [current context](../context/CONTEXT.md).
3. Read the relevant product-vision sections and ADRs.
4. Inspect the affected files and tests.
5. Classify the change using the delivery tracks below.
6. Identify ambiguities, acceptance criteria, non-goals, risks, and the
   expected validation.

Do not treat a refactor, dependency upgrade, abstraction, or test-count goal
as a work item by itself unless it protects a named guarantee or resolves a
reproducible problem.

## 3. Delivery tracks

### Track A — Documentation or mechanical maintenance

Use for changes that cannot alter runtime behavior, financial meaning, public
contracts, stored data, security, or deployment.

Flow:

```text
inspect -> define exact document scope -> edit -> validate links and
ownership -> report
```

An explicit request to edit the named documentation is sufficient approval
for that scope. Escalate to Track B or C if the documentation change creates
or changes a product or architecture decision.

Maintain `CONTEXT.md` only when current material repository state changes:
the active priority, an implemented capability, a configured validation
baseline, an architecture or contract boundary, or another fact needed to
understand the repository's present state. Do not use it as a per-task or
per-pull-request changelog; routine editorial corrections and ordinary test
reruns do not require an update.

### Track B — Ordinary behavioral work

Use for bounded frontend, API, application-service, or tooling behavior that
does not change financial formulas, rule eligibility, comparison semantics,
stored-data compatibility, security boundaries, or public API compatibility.

Flow:

```text
work item -> clarify -> acceptance criteria -> plan -> approval -> branch ->
implement -> diff review -> tests -> QA -> commit -> push -> draft PR
```

### Track C — Financial or architecture-critical work

Use for:

- money, rate, time, or rounding behavior;
- SAC, Price, consortium, rent, capital, or net-worth calculations;
- eligibility rules and unsupported-case behavior;
- objectives, constraints, ranking, sensitivity, and break-even logic;
- simulation schemas, version identifiers, migrations, and historical
  reproducibility;
- privacy, security, AI grounding, or external-service boundaries;
- breaking or public API changes;
- architecture-invariant changes.

Flow:

```text
work item -> issue clarification -> acceptance criteria -> AC challenge ->
plan -> adversarial review -> explicit approval -> issue-numbered branch ->
implement -> independent diff review -> tests -> full QA -> atomic commits ->
push -> draft PR
```

Track C cannot be downgraded because a diff is small.

## 4. Issue and branch order

Once Git is available, create or confirm the issue before creating its
branch.

Branch format:

```text
<type>/issue-<number>-<slug>
```

Allowed types:

- `feat`
- `fix`
- `docs`
- `refactor`
- `chore`

Never implement directly on the protected default branch. Do not mark a pull
request ready or merge it without explicit user authorization.

## 5. Acceptance criteria

Before planning Track B or C work, define:

```markdown
## Acceptance Criteria

- AC1: Observable and verifiable behavior
- AC2: Observable and verifiable behavior

## Exit Conditions

- Every acceptance criterion is met.
- Required tests and QA pass.
- No unresolved task-derived work remains.

## Out of Scope by Construction

- Artifact or behavior that must not change, with the reason.

## Non-Goals

- Related capability intentionally excluded.

## Open Questions

- Question that would materially change implementation.
```

Acceptance criteria must identify units, rate conventions, rounding,
supported cases, and failure behavior whenever financial outputs are involved.

## 6. Plan contract

An implementation plan must include:

```markdown
## Diagnosis

Evidence-backed current behavior and gap.

## Files to Modify

- Exact paths and why each must change.

## Implementation Plan

1. Ordered, bounded steps.

## Tests and Validation

- Existing tests affected.
- New guarantee or regression each new test protects.
- QA commands to run.

## Risks

- Correctness, compatibility, privacy, and operational risks.

## Modification Budget

- max_files_modified: N
- max_public_api_changes: N
- max_new_dependencies: N
- max_new_modules: N
- max_new_classes: N

## Out of Scope

- Explicit exclusions.
```

If implementation must exceed the approved budget or scope, stop and request
a plan amendment.

## 7. Review roles

Claude-specific role prompts live in `.claude/agents/`, but their conceptual
roles apply regardless of tool:

| Role | When | Responsibility |
| --- | --- | --- |
| Issue clarifier | Before criteria | Find undefined terms, ambiguities, missing interactions, and uncovered cases. |
| AC challenger | Before planning | Find untestable, redundant, or incomplete acceptance criteria. |
| Adversarial reviewer | Before approval | Challenge assumptions, interactions, unnecessary work, and silent-failure paths. |
| Diff reviewer | Before final QA | Compare implementation with the approved plan and identify concrete logic or coverage gaps. |

Reviewers identify risks; they do not automatically expand scope. Act on
findings that affect approved requirements, correctness, privacy, contracts,
or documented invariants. Record unrelated concrete debt in
[discoveries.md](../context/discoveries.md).

## 8. Implementation rules

- Implement only approved scope.
- Keep domain calculations pure and deterministic.
- Do not duplicate financial formulas in the frontend.
- Reuse existing patterns before adding dependencies.
- Do not rewrite adjacent modules without a demonstrated need.
- Keep real personal and proposal data out of source control and logs.
- Treat unsupported rules as typed failures, never estimates.
- Preserve old simulation results and contract versions.
- Make one logical change per commit.

## 9. Testing rules

| Change | Minimum testing requirement |
| --- | --- |
| Documentation only | Link, ownership, placeholder, and consistency checks. |
| Bug fix | Regression test that fails before the fix. |
| New behavior | Tests for the new guarantee and relevant failure path. |
| Financial behavior | Independent reference, invariants, boundaries, and regression coverage as applicable. |
| Public contract | Schema and consumer compatibility tests. |
| Pure refactor | Existing suite passes; add tests only for an identified unprotected guarantee. |

Each new test must protect an identifiable guarantee, decision, boundary, or
regression. Coverage is evidence, not a substitute for reasoning about the
financial state space.

## 10. QA

The concrete commands are owned by
[CONTEXT.md](../context/CONTEXT.md#qa-status) until the toolchains are
configured. Once configured, every required command must pass before commit.

Report results as:

```text
## QA Results

### Backend lint and format
PASS / FAIL / NOT CONFIGURED

### Backend types and tests
PASS / FAIL / NOT CONFIGURED

### Frontend lint and format
PASS / FAIL / NOT CONFIGURED

### Frontend types and tests
PASS / FAIL / NOT CONFIGURED

### Contract and browser tests
PASS / FAIL / NOT CONFIGURED
```

Do not create a commit or claim completion when a required configured check
fails.

## 11. Commit and pull-request rules

Use Conventional Commits in English:

```text
<type>(<scope>): <message>
```

When a commit contains a relevant change, include a brief commit body that
explains what changed and why so its purpose remains understandable without
opening the pull request. Relevant changes include behavior, contracts,
financial rules, privacy, security, data, architecture, and other material
decisions. Purely mechanical or trivial changes may omit the body.

The pull-request description must include:

- summary and motivation;
- exact scope and files changed;
- before and after behavior;
- acceptance-criteria checklist;
- tests and exact results;
- risks, limitations, and follow-up exclusions;
- calculation or contract version impact when applicable.

Open every pull request as a draft when the work is finished. Never mark a
pull request ready or merge it without explicit user authorization; technical
readiness does not grant that authorization.

When work for an issue is complete on its issue-numbered branch, the draft
pull-request description must include that issue's GitHub closing reference,
for example `Closes #123`. The issue remains open while the pull request is a
draft and closes when the pull request is merged. This keeps issue status
current and prevents duplicate work items.

## 12. Optional mechanical review-plan gate

The `.project/review-plan.json` gate is reserved for Track C or other
high-blast-radius work after Git and CI are configured.

When activated:

1. create or confirm the issue;
2. create the issue-numbered branch from the current protected base;
3. make the first commit change only `.project/review-plan.json`;
4. wait for plan admission before implementation;
5. keep every later branch change within admitted paths, operations, and
   budgets;
6. create a new branch and plan if the admitted base changes.

The example contract lives at `.project/review-plan.example.json`, and the
checker lives at `scripts/check_review_plan.py`. The gate is not active merely
because those files exist.

## 13. Periodic audit

After every five merged behavioral pull requests, run the audit described in
[reference.md](../context/reference.md#periodic-workflow-audits).
