# Local Comparison Application, API and UI v1

> Accepted Track C contract, Issue #53; [ADR-0012](../adr/0012-local-comparison-application-boundary.md).

## Purpose and boundaries

B adds a local, synthetic input -> review -> comparison -> understanding flow
over [comparison v2](common-monthly-resources-v1.md). Python remains authoritative.
There are exactly four alternatives and one objective: maximize net worth at
month 60, after mandatory constraints. Only rent invests. No new financial
rule, private-case validation, persistence, export/import or HTTP replay exists.

The existing `POST /api/v1/financing/calculations` remains an ephemeral v3
projection, with its original response/errors and 8 KiB/256 KiB limits.
It is never converted into a comparison or simulation implicitly.

## Explicit creation and lifetime

`POST /api/v1/comparison/simulations` creates a v2 simulation envelope internally.
The framework-independent application supplies a fresh opaque snapshot and UTC
timestamp through injectable factories, calls the retained factory once, and
projects its sealed outcome. It does not calculate totals, metrics or groups.
The full envelope exists only during execution; no replay claim or retrieval
identifier is returned. The typed result exists in browser memory until editing
or reload. No storage, cookies, analytics, body logs or financial URL parameters
are used. Responses use `Cache-Control: no-store`.

Same inputs and injected metadata produce the same result. Ordinary repeated
creation uses fresh metadata and identical financial output. Snapshot metadata
does not authenticate facts and never replaces source dates or classifications.

## Request and expected semantic structures

The outer object has exactly `comparison`, containing exactly six required
fields: `shared`, `constraints`, `financing`, `rent`, `consortium` and
`monthly_resources`. Each value accepts recursive closed JSON. Domain-owned
structure and semantic validation are intentionally not duplicated in Pydantic:
a malformed child may exclude that alternative while other alternatives run.
Unknown consortium clauses must reach retained support rejection.

Expected objects are the complete existing inputs, including their support
declarations/default declarations. This HTTP operation does not fill omissions:

| Field | Expected content and ownership |
| --- | --- |
| `shared` | Exactly opening cash, property price, starting rent, rent-adjustment value/convention and first adjustment month from [minimum comparison](minimum-comparison-v1.md). |
| `constraints` | Explicit minimum liquidity and maximum monthly housing outflow. |
| `financing` | All `FinancingRequest` fields, shared by SAC/Price: cash, price, down payment, principal, term, rate/convention, fixed fee and optional rule/support declarations. |
| `rent` | All `RentPlusInvestmentRequest` fields: common cash/rent terms, investment allocation, mandatory contribution, net return/convention and support declarations. |
| `consortium` | All `ConsortiumRequest` fields: letter/term, classified full schedule, support declarations, explicit scenario/contemplation/purchase, price/top-up, waiting rows and requested features. |
| `monthly_resources` | Closed basis/scope and exactly 60 ordered rows, both component arrays, six fields per component, explicit classifications/source dates/references and projected assumption references. |

Exact field contracts and financial precedence remain owned by the linked
specifications and [financial contracts](financial-contracts.md). All monetary
and rate values are strings. Existing input limits (18 integer digits for money,
12 rate decimals, contractual terms 1..600) remain comparison-owned. The term
cap does not apply to the first rent-adjustment month. No totals override exists.

## Representation and resource admission

Accept UTF-8 JSON in any key order or whitespace. Before ordinary FastAPI parsing,
reject duplicate keys anywhere, floating/exponent JSON number tokens, nonfinite
constants, integers outside ±(2^53-1), unpaired surrogates and nesting above 64.
Monetary/rate strings are preserved. The application canonicalizes the admitted
object using the pinned existing codec; the client need not submit canonical JSON.

The new operation alone has a 1,048,576-byte request limit and 4,194,304-byte
serialized result limit. Overflow never truncates evidence or rows. Representation
failures create no domain artifact. Global semantic failures may be sealed
internally but expose no partial result or metadata.

## Response and failure families

HTTP 200 returns `api_version=v1`, `kind=simulation_result`, aggregate versions,
snapshot, UTC/timezone, declared inputs, normalized common inputs/classifications,
conventions, the full derived monthly profile, child versions/classifications
where available, alternatives, status, objective, groups and limitations.
The horizon/reference basis are explicit in normalized rule conventions.

Complete alternatives contain the original metrics, every constraint violation,
61 ledger rows and 60 housing outflows. Failed children contain only strategy,
`domain_failure` and safe failure data, never partial metrics/rows. Failure data
uses stable code and fixed Portuguese message; only an exact known cash diagnostic
can add month/phase. Absent classifications are omitted rather than invented.
Required observed `assumption_reference=null` remains explicit.

Calculated money is an exact canonical two-decimal string with no integer-digit
cap beyond the body budget. Do not reuse projection's 22-digit output schema.

| HTTP | Code/meaning |
| --- | --- |
| 200 | `compared`, `single_eligible` or `no_eligible`; local exclusions remain data. |
| 413 | `request_too_large`. |
| 422 | Representation/global domain failure, or `response_too_large`. |
| 500 | `internal_error`, never a financial exclusion. |

Global errors contain only `api_version`, `code` and safe `message_pt_br`.
The new error family applies in middleware, request validation, execution and
serialization. Legacy projection errors remain unchanged. Unexpected exceptions
are handled before they can expose input-bearing tracebacks.

## Version and consumer boundary

| Authority | Schema | Engine | Ruleset |
| --- | --- | --- | --- |
| Aggregate | comparison-simulation-v2 | comparison-monthly-resources-v2 | comparison-ruleset-v2 |
| SAC/Price | financing-replay-v4 | financing-monthly-resources-v4 | financing-ruleset-v3 |
| Rent | rent-plus-replay-v2 | rent-plus-monthly-resources-v2 | rent-plus-ruleset-v2 |
| Consortium | consortium-replay-v2 | consortium-monthly-resources-v2 | consortium-ruleset-v2 |

The UI verifies HTTP/API, aggregate and all child tuples plus the structures it
renders. Unknown tuples, malformed/illegible bodies and client byte overflow
produce a transport/contract state, never an eligibility statement. Types are
generated offline from OpenAPI and checked for drift. Financial values use
string-only localization without Number conversion, rounding or reranking.

## Input, review and result UI

User declarations begin blank. Common values are collected once and copied
unchanged into child requests. Principal, down payment, letter and top-up stay
separate explicit declarations. Fixed supported conventions and no-request
declarations are visible and confirmed, never hidden financial assumptions.

The profile starts with 60 incomplete months. Both arrays must be declared;
empty arrays require an explicit action. Copying a component upserts the same
identity on the same side, preserves other identities and rejects opposite-side
reuse anywhere in the profile. Schedule copies replace all four declared amounts;
waiting copies replace the selected amounts. All copies preview existing/new
declarations and require confirmation. No recurrence, percentage, residual,
adjusted rent, date or classification is inferred. Individual editing is available.

Review displays declarations/provenance and conventions, without frontend totals
or a preview calculation endpoint. Edits invalidate review/result, cancel pending
requests and prevent stale responses from rendering. Retry is explicit; timeout
is 30 seconds. Reload loses state and is explained before input.

The result preserves fixed strategy order and exact tied groups. It highlights
only the first eligible group under the fixed objective; one eligible is not
claimed superior to exclusions. No eligible is a normal explained outcome.
Show cost, cash, liquid assets, credit right, debt, equity, net worth, minimum
liquidity/maximum outflow and all attaining months; complete monthly tables and
common-resource provenance remain inspectable. Limitations and only-rent-invests
are adjacent to the highlight. No M4/MVP or household affordability claim.

## Visual and operational defaults

Source Sans 3 is local. Palette: white #FFFFFF, mist #EDF3F7, ink #17324D,
action #205A86, confirmation #246648, error #9D3545. Use a four-column comparison
matrix, right-aligned exact amounts, and a 60-month declaration navigation strip.
Mobile presents the same metric sequence per strategy. Semantic controls,
keyboard focus, error summary and text statuses accompany color. No chart library.

Next.js and FastAPI bind to loopback. A same-origin rewrite forwards the sole
comparison operation to 127.0.0.1:8000. No auth/remote deployment is introduced.
Backend CI jobs and the 95% domain coverage gate are retained; an additional web
job runs contract generation checks, lint/types/build and synthetic Chromium
desktop/mobile tests. Real financial data is forbidden from fixtures and logs.

Persistence, export/import, replay HTTP, remote access, financial previews,
sensitivity, break-even, optimization, polish and private validation are deferred.
