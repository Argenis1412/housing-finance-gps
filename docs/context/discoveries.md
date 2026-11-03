# Out-of-Scope Discoveries

> Append-only log for technical debt, contradictions, or risks discovered
> while implementing an approved work item but outside that item's scope.

Do not use this file as a backlog for speculative improvements. A discovery
must identify a concrete affected artifact or behavior.

## Entry format

```markdown
### YYYY-MM-DD — Work item and short title

- **Location:** `path/to/file:line` or affected area
- **Discovery:** Concise, evidence-based description
- **Found during:** implementation / diff review / QA
- **Why deferred:** Why it is outside the approved scope
- **Potential impact:** Correctness / security / maintainability / documentation
- **Next decision:** Issue to create, ADR to consider, or evidence still needed
```

If later evidence corrects an entry, append a dated correction. Do not
silently rewrite historical observations.

## Log

### 2026-11-03 — Issue #43: Exhaustive v3 matrix runtime

- **Location:** `tests/test_financing_v3.py:352` and
  `.github/workflows/validation.yml`
- **Discovery:** The exhaustive small-principal matrix evaluates both strategies,
  two rates, principals from one to fifty centavos, terms one to sixty, and
  absent or R$0.01 fees in the ordinary suite. CI runs that suite with branch
  instrumentation in a single job with a 15-minute timeout. The initiating
  review reported that the matrix dominates runtime and cited a successful
  8m 38s CI run; this documentation task did not reproduce or profile that run.
  The claim that the matrix adds no coverage remains unverified; line or
  branch coverage alone also does not establish equivalent financial guarantees.
- **Found during:** documentation review for Issue #43, following the reported
  QA findings.
- **Why deferred:** Test selection, markers, and job separation change tooling
  behavior and are outside this Track A documentation scope.
- **Potential impact:** Maintainability and CI timeout headroom as additional
  financial strategies receive regression tests.
- **Next decision:** Define a bounded Track B CI work item; measure runtime and
  coverage with and without the matrix before choosing job separation and
  preserving its financial guarantees.

### 2026-11-03 — Issue #43: Reported TestClient/httpx deprecation warning

- **Location:** `tests/test_api_financing_v1.py`, `uv.lock`, and the
  Starlette TestClient/httpx dependency boundary.
- **Discovery:** HTTP tests use FastAPI's TestClient, and `uv.lock` includes
  httpx. The initiating review reported a deprecation warning at the Starlette
  TestClient/httpx boundary. This documentation task did not reproduce the
  warning or establish its exact message and originating package version.
- **Found during:** documentation review for Issue #43, following the reported
  QA findings.
- **Why deferred:** Reproducing and resolving a dependency compatibility warning
  is outside the approved documentation changes; no dependency upgrade is
  justified by this entry alone.
- **Potential impact:** Maintainability, test-output noise, and future
  dependency compatibility.
- **Next decision:** Capture the exact warning with the locked environment,
  identify its origin, and assess a targeted fix during dependency review.

### 2026-11-03 — Issue #43: Coverage gate excludes API and application

- **Location:** `.github/workflows/validation.yml`, `application/`, and `api/`.
- **Discovery:** CI invokes `coverage run --branch --source=domain -m pytest -q`
  followed by `coverage report --fail-under=95`. The threshold applies to the
  combined total for `domain/` only. Application and API behavior has tests,
  but neither package is included in the coverage source or gate.
- **Found during:** documentation review for Issue #43 and inspection of the
  configured validation workflow.
- **Why deferred:** Changing measured packages or thresholds changes the QA
  gate and requires a separately scoped behavioral work item.
- **Potential impact:** The existing percentage cannot establish coverage of
  application orchestration, HTTP validation, or public error mapping.
- **Next decision:** Measure application/API coverage and decide whether they
  need an additional gate while preserving the existing domain requirement.
