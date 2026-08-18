# Housing Finance GPS — Technical Product Vision

> Status: approved direction for specification and implementation
> Initial market context: Brazil
> Primary user: one real family member, represented by an anonymized reference case
> Product language for the first release: Portuguese (Brazil)
> Documentation and source-code language: English
> Revision date: August 17, 2026
> Working name: **Housing Finance GPS**

## 1. Executive decision

Housing Finance GPS is no longer being developed as a commercial B2C or B2B2C hypothesis.

The project has two goals:

1. **A strong technical portfolio project:** a deterministic, auditable, versioned, and thoroughly tested financial calculation engine built with explicit engineering discipline.
2. **A useful private decision-support tool:** an application that helps one real family member compare buying a home now with financing, entering a consortium, or continuing to rent while accumulating capital in Brazil.

The reference case is the acceptance anchor for the MVP. It replaces market surveys, acquisition experiments, and willingness-to-pay gates. The project is successful when it produces a correct, reproducible, understandable, and practically useful comparison for that case.

The product does not attempt to predict the future or identify a universally correct choice. It makes assumptions visible, calculates their consequences, and shows which variables can change the conclusion.

The financial engine is authoritative. A language model may explain approved engine output only after the engine and the reference case have been validated.

## 2. Why this project should exist

A household deciding whether to buy a home receives fragmented information:

- a bank simulates its own financing offer;
- a consortium administrator presents its own plan;
- a real-estate seller is rewarded when a purchase closes;
- investment tools focus on returns rather than housing decisions;
- isolated calculators rarely compare liquidity, risk, housing costs, debt, and accumulated capital on the same timeline.

The user needs one transparent comparison of three strategies:

1. buy now with SAC or Price financing;
2. join a consortium using the terms of a real proposal and explicit contemplation scenarios;
3. continue renting and accumulate capital.

The comparison must include cash flow, liquidity, debt, estimated home equity, financial assets, total housing cost, and uncertainty over a user-selected horizon.

## 3. Product promise

> Compare housing strategies using reproducible calculations, visible assumptions, versioned rules, and understandable trade-offs.

The product may state that an alternative performs better under a selected objective and scenario. It must not claim that an option is universally best or certain to produce a specific future outcome.

The product must never promise:

- guaranteed approval of financing, FGTS use, a subsidy, or a consortium bid;
- guaranteed property appreciation or investment returns;
- a predictable consortium contemplation date;
- the highest possible future net worth;
- a substitute for a binding bank or consortium proposal;
- legal, tax, investment, or regulated financial advice.

## 4. User and reference case

### 4.1 Primary user

The MVP is designed for one family member who is actively deciding whether to buy a home or continue renting. The person's real situation is represented by an anonymized, versioned reference case.

The MVP is not designed for a market segment, professional buyer, financial adviser, broker, bank, or consortium seller.

After the reference case succeeds, the application may be tested privately with a small invited group. That later testing does not change the MVP acceptance criteria.

### 4.2 Reference-case record

The real reference case is a private, local-only acceptance record. It must
not enter source control, CI inputs, logs, public fixtures, or shared exports.
The owner retains the complete private record and can reproduce its validated
result locally under the governance contract in
[reference-case governance](../specifications/reference-case-governance.md).

The private record contains:

- household net income;
- essential and discretionary monthly expenses;
- current rent and expected rent adjustment;
- emergency reserve and minimum acceptable reserve;
- available down payment;
- FGTS balance if applicable;
- target property price and location;
- expected time in the property;
- maximum acceptable monthly housing cost;
- financing proposal terms when available;
- consortium proposal terms when available;
- capital return assumptions;
- base, favorable, and adverse scenarios;
- expected outputs independently reviewed for the supported calculations.

The repository contains only a redacted validation attestation and synthetic
regression fixtures. Those artifacts may identify contract and version
metadata, but never real financial values, direct identifiers, proposal
documents, or combinations that can re-identify the household.

## 5. MVP scope

### 5.1 Required capabilities

#### Minimum financial profile

- household net income;
- recurring expenses;
- current rent;
- savings capacity;
- emergency reserve;
- available down payment and applicable FGTS balance;
- target property value;
- intended ownership horizon;
- maximum acceptable monthly housing cost;
- user-selected objective and non-negotiable constraints.

#### Financing simulator

- SAC amortization;
- Price amortization;
- principal, term, rate convention, and periodicity;
- nominal and effective rate handling;
- insurance, fees, taxes, and other user-provided contractual costs;
- applicable indexation when explicitly supported;
- optional extraordinary amortization;
- complete monthly schedule;
- debt balance and cumulative cost at every period;
- inverse calculation from a maximum safe payment when feasible.

#### Simplified consortium model

- credit letter value;
- term and installment schedule;
- administration fee;
- reserve fund and insurance when present;
- monetary correction rule supplied by the proposal;
- user-funded bid and embedded bid when supported;
- housing cost while waiting for contemplation;
- early, intermediate, and late contemplation scenarios;
- cash flow, liquidity, and estimated net worth for every scenario.

The MVP does not assign probabilities to contemplation dates and does not label one date as the expected or most likely outcome.

#### Rent-and-accumulate model

- starting rent;
- rent adjustment assumption;
- initial invested capital;
- monthly contribution capacity;
- net capital return assumption;
- taxes and costs only when explicitly modeled;
- liquidity and accumulated capital over time;
- optional future purchase with a larger down payment after a defined period.

#### Three-strategy comparator

The comparator must place financing, consortium, and rent plus capital accumulation on a consistent monthly timeline and use the same:

- currency and rounding rules;
- time horizon;
- inflation convention;
- nominal or real-value convention;
- treatment of cash that remains available;
- property-value assumption;
- transaction-cost assumptions.

#### Sensitivity analysis

- base, favorable, and adverse named scenarios;
- editable projected assumptions;
- one-variable-at-a-time sensitivity around the base case;
- identification of the variables with the largest effect;
- explicit thresholds at which the ordering of two alternatives changes;
- loss-of-income or reduced-savings stress case.

#### Explainable result

- concise summary of all supported alternatives;
- monthly cash-flow timeline;
- outstanding debt;
- financial assets;
- estimated home equity;
- total estimated net worth;
- minimum liquidity and reserve months;
- cumulative housing cost;
- break-even points when they exist;
- excluded or infeasible alternatives and the failed constraints;
- assumptions most capable of changing the result;
- missing information and unsupported rules;
- engine, ruleset, and data-snapshot identifiers.

#### Saved and reproducible simulations

- save a simulation locally in the application;
- export the complete calculation input and output as JSON;
- import a supported JSON simulation;
- duplicate a simulation and change one or more assumptions;
- preserve historical results rather than silently recalculating them;
- compare a historical run with a new run.

### 5.2 Explicitly out of scope

- market validation and economic gates;
- B2B2C distribution or professional outreach;
- professional-buyer profiles and prospect filtering;
- pricing, subscriptions, commissions, lead generation, or monetization;
- bank-account or open-finance integrations;
- automated banking, credit, property, or consortium integrations;
- PDF ingestion, OCR, or automatic document extraction;
- complete FGTS, MCMV, tax, state, or municipal rule coverage;
- credit approval or credit scoring;
- recommendations for specific securities or investment products;
- execution of investments or financial transactions;
- property-price prediction;
- probabilistic simulation of a complete consortium group;
- Monte Carlo simulation presented as scientific certainty;
- native mobile applications;
- microservices, Kubernetes, Terraform, Redis, or Celery without a measured need;
- multi-agent AI architecture;
- retrieval-augmented generation, embeddings, or a vector database for the MVP;
- multilingual product support in the first release;
- public launch or commercial operation.

## 6. Product principles

1. The engine calculates; the language model only explains approved output.
2. Every result exposes the assumptions that produced it.
3. Observed data, contractual data, rules, and projected assumptions remain distinct.
4. Uncertainty is expressed with ranges and scenarios, not false precision.
5. Liquidity and resilience are shown alongside estimated net worth.
6. A simulation is never presented as an offer, approval, or guarantee.
7. The same inputs and versions produce the same output.
8. Historical results are immutable.
9. Unsupported rules fail explicitly instead of being approximated silently.
10. A comparison may be objective-dependent; there is no universal winner.
11. The user can understand why a result changed.
12. Only the minimum necessary personal data is requested.
13. No number may be invented by the frontend or by a language model.
14. Tests protect identifiable financial guarantees and decisions, not a test-count target.

## 7. User experience

### 7.1 UX goal

The application must feel calm, clear, and trustworthy. It should guide a non-specialist through a consequential decision without presenting a wall of financial terminology.

The default experience is progressive:

1. define the household and safety constraints;
2. enter the property and current rent;
3. add the available financing and consortium terms;
4. review observed data and projected assumptions separately;
5. calculate the three strategies;
6. explore scenarios and break-even variables;
7. save or export the comparison.

### 7.2 Interaction requirements

- responsive desktop and mobile-web layouts;
- keyboard-accessible controls;
- visible focus states and semantic form labels;
- inline validation in plain Portuguese;
- currency, rate, and period formatting appropriate for Brazil;
- sensible defaults that are always visible and editable;
- a review step before calculation;
- no hidden advanced assumptions;
- charts accompanied by tables or textual summaries;
- color never used as the only status signal;
- loading, empty, validation, unsupported-case, and failure states designed explicitly;
- no conversational chatbot as the primary navigation model.

### 7.3 Result presentation

The result page should contain:

1. a plain-language summary;
2. three comparable strategy cards;
3. a timeline chart;
4. net-worth, liquidity, cumulative-cost, and monthly-burden views;
5. scenario controls;
6. a break-even and dominant-variables section;
7. assumptions, rules, limitations, and version details;
8. save, duplicate, and export actions.

The interface may highlight an alternative only as “best under the selected objective and current assumptions.” It must keep the trade-offs of the other alternatives visible.

## 8. Architecture

The system uses a separately deployable Next.js frontend and a modular FastAPI backend. The backend contains the pure financial domain and remains a modular monolith.

```text
User
  |
  v
Next.js web application
  - TypeScript
  - accessible forms and result views
  - charts and scenario controls
  - no financial calculations
  |
  | versioned JSON over HTTPS
  v
FastAPI application
  - API contracts and validation
  - application use cases
  - deterministic financial engine
  - scenario comparison
  - rules and data provenance
  - persistence
  - explanation adapter, added later
  |
  v
SQLite for the private MVP
```

### 8.1 Frontend

- Next.js with TypeScript;
- React server and client components selected according to interaction needs;
- schema-derived or shared contract types generated from OpenAPI;
- accessible component primitives rather than a custom component framework;
- a restrained visual system with reusable design tokens;
- a charting library selected in an ADR after checking accessibility and bundle cost;
- browser tests for the reference-case journey;
- no duplicated financial formulas.

The frontend and API may be deployed independently. Deployment details and providers are implementation decisions documented separately.

### 8.2 Backend

- Python and FastAPI;
- typed request and response contracts;
- application services that orchestrate use cases;
- pure domain functions without network, database, clock, locale, environment, or framework dependencies;
- explicit dependency direction from API and infrastructure toward the domain;
- SQLite persistence for the private MVP;
- migration tooling from the first persisted schema;
- structured logs without sensitive financial values.

PostgreSQL may replace SQLite only when a concrete concurrency, deployment, or operational requirement justifies it.

### 8.3 Proposed module boundaries

```text
domain/
  money/
  financing/
    sac/
    price/
    fees_and_insurance/
    extra_amortization/
  housing/
    rent_projection/
    ownership_costs/
    property_value/
  capital/
    accumulation/
    liquidity/
  consortium/
    proposal/
    installments/
    correction/
    contemplation_scenarios/
  rules/
    fgts/
    supported_case/
  scenarios/
    assumptions/
    constraints/
    comparison/
    sensitivity/

application/
  simulations/
  scenarios/
  exports/

api/
  routes/
  schemas/
  error_mapping/

infrastructure/
  persistence/
  versioning/
  clock/
  logging/
```

## 9. Financial engine design

### 9.1 Domain contract

The engine accepts validated, typed inputs and returns structured results. It does not know about HTTP, UI components, databases, charts, or natural-language explanations.

The initial supported financial conventions and common ledger are defined in
[Milestone 0 financial contracts](../specifications/financial-contracts.md).

All financial calculations must declare:

- monetary unit;
- rate convention;
- compounding frequency;
- period boundaries;
- rounding mode and rounding point;
- nominal or real-value treatment;
- tax and fee treatment;
- supported and unsupported conditions.

Money is represented with `Decimal` or integer minor units. Binary floating-point values must not be authoritative financial amounts.

### 9.2 Main outputs

- monthly strategy cash flow;
- financing principal, interest, insurance, fees, and debt balance;
- consortium installments, correction, bid, and waiting-period housing cost;
- rent and capital contributions;
- financial asset balance;
- estimated property value and home equity;
- total estimated net worth;
- cumulative housing cost;
- minimum liquidity;
- emergency-reserve coverage in months;
- break-even dates or an explicit statement that none exists in the horizon;
- feasibility and constraint violations;
- sensitivity direction and magnitude;
- auditable comparison trace.

### 9.3 Versioning and reproducibility

Every simulation stores three independent identifiers:

- `engine_version`: semantic version of the calculation behavior;
- `ruleset_version`: version of the supported FGTS, MCMV, and other decision rules;
- `data_snapshot_id`: exact external or manually supplied values, sources, and effective dates.

It also stores:

- complete normalized inputs;
- projected assumptions and tested ranges;
- currency;
- timezone;
- rounding convention;
- calculation timestamp supplied through an explicit clock boundary;
- output and comparison trace.

A new engine version never rewrites a historical result. A user may recalculate a copied simulation with current versions and compare the two runs.

Changes that alter results require regression cases, a changelog entry, and a semantic-versioning decision. A change in an external value is a new data snapshot and is not automatically a new engine version.

Private reference-case validation adds a provenance boundary: the complete
reproducible envelope stays local, while Git stores only a redacted,
root-cosigned attestation. The attestation records the immutable validator
keyring manifest used at acceptance; it does not expose or permit external
reconstruction of private inputs. See
[reference-case governance](../specifications/reference-case-governance.md).

### 9.4 Input classification

| Category | Example | Required treatment |
|---|---|---|
| User-provided fact | income, rent, available down payment | Confirmed by the user and timestamped. |
| Contractual value | CET, insurance, term, consortium fee | Linked to the proposal date and entered manually. |
| Observed external datum | published inflation index | Source, period, retrieval date, and snapshot. |
| Rule | supported FGTS condition | Source, effective date, scope, and ruleset version. |
| Projected assumption | future rent adjustment or property appreciation | Editable range, rationale, and sensitivity. |

A known contractual CET is not a projected assumption. A future property-appreciation rate is.

## 10. Strategy comparison

### 10.1 Objectives and constraints

The user selects one primary objective:

- preserve minimum liquidity;
- keep monthly housing cost below a limit;
- minimize cumulative housing cost;
- minimize debt exposure;
- maximize estimated net worth at a selected horizon;
- buy as early as possible without violating safety constraints.

Mandatory constraints are evaluated before objective scoring. An alternative that violates a non-negotiable reserve or payment constraint is reported as infeasible and cannot win by compensating with another metric.

### 10.2 Comparison rules

- all alternatives use the same horizon and shared macro assumptions;
- no commercial relationship affects the calculation or presentation;
- excluded alternatives and failed constraints remain visible;
- ties and tie-breaking rules are explicit and stable;
- Pareto-dominated alternatives cannot outrank alternatives that are no worse on every selected criterion;
- the result includes the actual trace used to compare alternatives;
- the explanation is reconstructed from that trace.

### 10.3 Break-even analysis

The application should identify decision boundaries such as:

- the ownership horizon after which buying overtakes renting under the selected metric;
- the property-appreciation assumption required to change the ordering;
- the net capital return required to change the ordering;
- the rent-adjustment threshold that changes the ordering;
- the contemplation period or bid size that changes the consortium result.

If no boundary exists inside the supported range, the application states that explicitly.

## 11. Consortium modeling boundary

Consortium is a first-class comparison strategy but a deliberately simplified model.

The engine models contractual cash flows and user-selected contemplation scenarios. It does not simulate the behavior of an entire group, predict lottery outcomes, or infer a probability distribution without validated data.

The supported scenarios are:

- **early contemplation:** a user-specified early month and bid;
- **intermediate contemplation:** a user-specified middle month and bid;
- **late contemplation:** a user-specified late month or end-of-term condition.

Every result must distinguish:

- values before contemplation;
- values at contemplation;
- values after contemplation;
- rent or other housing costs paid while waiting;
- capital consumed by the bid;
- remaining liquidity;
- monetary correction assumptions;
- unsupported contractual clauses.

## 12. Supported rules

The MVP implements only the FGTS or MCMV rule needed by the reference case, if such a rule is required for the actual decision.

That implementation must declare:

- jurisdiction and program;
- source document;
- effective date;
- applicability conditions;
- tested reference case;
- known exclusions;
- explicit unsupported-case behavior.

The user interface must not imply general Brazilian eligibility coverage. Inputs outside the documented rule scope return a typed “unsupported rule” result and require manual confirmation with the responsible institution.

## 13. Explanation layer and AI

### 13.1 Deterministic explanation first

The MVP initially uses deterministic templates derived from structured engine output. Templates may explain:

- why an alternative is feasible or infeasible;
- which objective caused an alternative to be highlighted;
- major differences in cost, liquidity, debt, and estimated net worth;
- dominant assumptions and break-even thresholds;
- missing data and model limitations.

### 13.2 Language-model phase

A language model may be added only after:

- the reference-case outputs are approved;
- the engine contract is stable;
- deterministic explanation templates exist;
- numeric grounding can be tested automatically;
- the application has a safe fallback when the provider is unavailable.

The language model receives a bounded structured payload. It may reorder or simplify approved facts for clarity, but it may not:

- calculate or alter a financial value;
- add an unsupported recommendation;
- change feasibility, scoring, ranking, or constraints;
- invent a source, rule, probability, or missing input;
- hide uncertainty or failed constraints;
- claim approval, certainty, or professional authority.

Every number in generated text must be traceable to a permitted field in the engine response. If the AI layer fails validation, the deterministic explanation is shown.

## 14. API and contract principles

- the API is versioned from its first public frontend integration;
- request and response models reject ambiguous units and rate conventions;
- API errors use stable machine-readable codes and safe user-facing messages;
- the frontend generates or validates TypeScript types from the OpenAPI contract;
- contract tests protect the frontend/backend boundary;
- calculation endpoints are idempotent for the same normalized input and versions;
- stored simulation identifiers do not expose personal information;
- imported JSON is schema-versioned and validated before use;
- breaking contract changes require an explicit migration path or major version.

## 15. Data protection and trust

Although the MVP is private and non-commercial, it handles sensitive household financial information.

The MVP must:

- minimize collected data;
- avoid names, CPF, account numbers, and addresses unless strictly required;
- keep real personal data out of logs, analytics, fixtures, and source control;
- define local retention and deletion behavior;
- allow export and deletion of saved simulations;
- separate anonymized reference fixtures from live user records;
- avoid sending personal data to an AI provider by default;
- document any deployment environment that can access saved simulations;
- use transport encryption outside local development;
- keep secrets outside the repository.

The real reference case is governed separately from synthetic regression data.
Its complete envelope, commitment secret, and signing private keys remain
outside the repository. Redacted attestations and signed keyring manifests are
the only reference-case provenance artifacts permitted in Git. This boundary
does not claim that an external reviewer can reconstruct private inputs.

The product must clearly state that it is a decision-support simulation and not a binding offer or regulated professional recommendation.

## 16. Engineering discipline

### 16.1 Architecture decision records

Material decisions require short ADRs. The initial ADR set should cover:

1. pure deterministic engine and dependency boundaries;
2. money, rate, period, and rounding conventions;
3. Next.js frontend and FastAPI backend separation;
4. OpenAPI contract and TypeScript type strategy;
5. SQLite persistence and migration boundary;
6. simulation, engine, ruleset, and snapshot versioning;
7. comparison objectives, constraints, and trace;
8. consortium scenario model;
9. reference-case governance and anonymization;
10. deterministic explanation before language-model integration.

### 16.2 Continuous integration

Every pull request must run:

- formatting and linting;
- static type checking for Python and TypeScript;
- domain unit tests;
- property-based and invariant tests;
- API contract and integration tests;
- frontend component tests where behavior warrants them;
- one browser-level reference-case smoke test;
- migration checks once persistence exists;
- dependency and secret scanning appropriate to the repository.

CI must be deterministic and must not call live financial, banking, consortium, or AI services.

### 16.3 Test strategy

The test suite protects financial guarantees, not an arbitrary number of tests.

Required categories include:

- independently calculated SAC and Price reference schedules;
- complete amortization-table reconciliation;
- zero rate, minimum term, full payoff, insufficient income, and invalid-input boundaries;
- property-based tests across valid ranges;
- debt-balance and cash-flow invariants;
- historical numeric regression fixtures;
- deterministic and idempotent comparison output;
- invariance to input ordering for equivalent alternatives;
- absolute exclusion after mandatory-constraint failure;
- Pareto-dominance behavior;
- stable ties and explicit tie-breaking;
- monotonic and metamorphic behavior where financially valid;
- continuity around ordinary thresholds and explicit tests for legitimate rule discontinuities;
- consortium early, intermediate, and late scenarios;
- unsupported-rule behavior;
- JSON export/import round trips;
- API schema compatibility;
- UI reference-case flow;
- generated-explanation numeric grounding when AI is introduced.

Coverage is measured and reported. The critical financial domain requires branch coverage high enough that every identified rule, invariant, and failure path is exercised. A percentage alone cannot approve a release.

### 16.4 Semantic versioning

The project uses semantic versioning for released application behavior.

- patch: defect correction that restores documented behavior without intentionally changing valid historical results;
- minor: backward-compatible capability or newly supported rule;
- major: intentional breaking contract or calculation-semantics change.

Calculation-affecting changes must identify whether they change `engine_version`, `ruleset_version`, `data_snapshot_id`, or more than one.

## 17. MVP acceptance criteria

The MVP is accepted only when all of the following are true:

1. The anonymized reference case can be completed through the Next.js interface without direct database or code manipulation.
2. SAC and Price schedules match independently calculated references within documented rounding tolerances.
3. Financing, consortium, and rent-plus-accumulation strategies reconcile monthly cash flow and balances over the complete horizon.
4. Early, intermediate, and late consortium scenarios remain visibly distinct and carry no invented probabilities.
5. Base, favorable, and adverse scenarios can be reproduced from saved inputs.
6. Mandatory liquidity and payment constraints exclude infeasible alternatives before comparison.
7. The result shows cost, debt, liquidity, financial assets, estimated home equity, and estimated net worth on a consistent timeline.
8. At least one dominant variable or explicit “no boundary in tested range” result is shown for each relevant pairwise comparison.
9. Every result contains `engine_version`, `ruleset_version`, and `data_snapshot_id`.
10. Exported JSON can reproduce the same normalized result with the same versions.
11. Unsupported FGTS, MCMV, consortium, or contractual conditions fail visibly and safely.
12. No authoritative financial calculation exists in the frontend.
13. The complete CI suite passes without live external-service dependencies.
14. The primary user can identify the main trade-offs and explain at least one assumption that could change the ordering of the alternatives.
15. The application provides deterministic explanations without requiring a language model.

## 18. Delivery roadmap

### Milestone 0 — Contracts and reference case

- establish private reference-case governance and redacted provenance;
- define supported inputs and outputs;
- define monetary, rate, period, and rounding conventions;
- create the initial ADRs;
- independently calculate SAC and Price references;
- define acceptance tolerances;
- define the simulation JSON schema and version identifiers;
- establish Python, TypeScript, and CI foundations.

**Exit:** the financial and technical contracts are reviewable before implementation.

### Milestone 1 — Financing engine

- money and rate primitives;
- SAC and Price schedules;
- fees, insurance, and supported indexation;
- extraordinary amortization if required by the reference case;
- financing reference tests and invariants;
- FastAPI calculation endpoint.

**Exit:** financing calculations reconcile with independent reference cases.

### Milestone 2 — Rent and capital accumulation

- rent projection;
- net capital accumulation;
- liquidity and reserve calculation;
- future-purchase option if needed;
- shared timeline and value conventions.

**Exit:** buying with financing and continuing to rent can be compared reproducibly.

### Milestone 3 — Simplified consortium

- proposal input contract;
- installments, fees, correction, and bids;
- early, intermediate, and late contemplation scenarios;
- waiting-period housing costs;
- unsupported-clause handling.

**Exit:** the three strategies share one auditable comparison timeline.

### Milestone 4 — Comparison and sensitivity

- objectives and mandatory constraints;
- auditable comparison trace;
- base, favorable, and adverse scenarios;
- one-variable sensitivity;
- break-even thresholds;
- historical numeric regression suite.

**Exit:** the engine explains what changes the result without natural-language AI.

### Milestone 5 — Product interface

- Next.js design system and application shell;
- guided financial-profile flow;
- proposal and assumption forms;
- review-before-calculate step;
- strategy cards, charts, tables, and limitations;
- responsive and accessible interaction states;
- end-to-end reference-case test.

**Exit:** the primary user can complete and understand the reference case without developer assistance.

### Milestone 6 — Persistence and private release

- SQLite persistence and migrations;
- save, duplicate, delete, import, and export;
- historical-run comparison;
- deployment documentation for frontend and backend;
- privacy and recovery checks;
- private MVP release.

**Exit:** the real decision can be revisited safely as proposals or assumptions change.

### Milestone 7 — Optional AI explanation

- bounded explanation payload;
- provider abstraction;
- structured output validation;
- numeric grounding checks;
- deterministic fallback;
- side-by-side evaluation against the template explanation.

**Exit:** AI is retained only if it improves understanding without reducing correctness, privacy, reliability, or traceability.

## 19. Success measures

### Engineering success

- reference results remain reproducible;
- identified financial invariants are continuously protected;
- no silent unsupported-rule behavior;
- no unexplained numeric difference across versions;
- calculation changes are traceable to code, rules, or data;
- frontend and backend remain contract-compatible;
- CI and release artifacts demonstrate the quality claims.

### User success

- the primary user completes the comparison;
- the primary user distinguishes simulation from offer or guarantee;
- the primary user understands the principal trade-offs;
- the primary user identifies at least one variable that could change the decision;
- the primary user can revisit the result when a real proposal changes;
- the tool reduces uncertainty without pretending to eliminate it.

There are no acquisition, conversion, revenue, pricing, professional-channel, or market-size success metrics in this project direction.

## 20. Main risks and mitigations

| Risk | Impact | Initial mitigation |
|---|---:|---|
| Incorrect financial calculation | Very high | Independent reference cases, invariants, property tests, versioned regressions, and documented rounding. |
| Inconsistent comparison conventions | Very high | Shared timeline, currency, inflation, liquidity, and transaction-cost contracts. |
| Consortium false precision | High | User-defined scenarios, no probabilities, visible correction and waiting costs. |
| Unsupported rule treated as supported | Very high | Narrow ruleset scope and typed fail-closed results. |
| Reference case overfitting | High | Boundary, property, metamorphic, and additional synthetic cases. |
| Misleading universal winner | High | Objective-dependent result, mandatory constraints, trade-offs, and break-even analysis. |
| Sensitive-data exposure | Very high | Anonymization, minimization, safe logs, deletion, and no real data in source control. |
| Frontend invents or changes numbers | Very high | Backend-authoritative contract and no frontend financial formulas. |
| Scope expansion | High | Milestone gates and explicit exclusions. |
| AI-generated financial claims | Very high | AI postponed, grounded structured payload, validation, and deterministic fallback. |
| Attractive UI hides weak calculations | High | Engine milestones and reference validation precede product-interface completion. |
| Two-deployment operational complexity | Medium | Versioned API, automated deployments, health checks, and documented compatibility. |

## 21. Decisions to resolve through ADRs or the reference case

- exact monetary rounding points for each financing schedule;
- rate conversion and day/month convention for supported proposals;
- reference-case horizon;
- property acquisition, ownership, and sale costs included initially;
- exact consortium proposal fields required by the real case;
- applicable FGTS or MCMV rule, if any;
- supported property-value and capital-return conventions;
- objective and mandatory constraints used by the primary user;
- charting and accessible-component libraries;
- OpenAPI-to-TypeScript workflow;
- frontend and backend deployment providers;
- local or hosted persistence for the private release;
- retention period for saved simulations;
- whether extraordinary amortization is required before MVP acceptance.

These are implementation decisions, not reasons to revive market validation or expand the product into a commercial platform.

## 22. Official reference sources

Official sources are starting points. Every implemented datum or rule must record its applicable document, effective date, scope, and snapshot. A link alone is not a versioned rule.

- [Banco Central do Brasil Open Data](https://dadosabertos.bcb.gov.br/)
- [CAIXA Housing Simulator](https://simuladorhabitacao.des.caixa.gov.br/)
- [CAIXA Housing Finance and FGTS](https://www.caixa.gov.br/voce/habitacao/financiamento-de-imoveis/Paginas/default.aspx)
- [CAIXA Housing Finance FAQ](https://www.caixa.gov.br/voce/habitacao/perguntas-frequentes-novos-financiamentos/Paginas/default.aspx)
- [Tesouro Direto methodology and documents](https://www.tesourodireto.com.br/)
- [IBGE SIDRA](https://sidra.ibge.gov.br/)
- [FGV IBRE price indexes](https://portalibre.fgv.br/)
- [Brazilian Data Protection Authority — data-subject rights](https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares)

## 23. Final direction

Build a small, highly reliable financial decision engine first. Use one real, anonymized housing decision to define acceptance, but protect the engine from overfitting through independent references, invariants, boundaries, and property-based tests.

Then build a polished and intuitive Next.js interface that makes the engine understandable. Keep FastAPI and the pure Python domain authoritative. Add persistence only when the simulation contract is stable. Add language-model explanations only after deterministic explanations and numerical grounding are proven.

The portfolio value is not that the application uses AI. It is that the project demonstrates disciplined modeling of a consequential real-world decision: explicit assumptions, deterministic calculations, narrow rule coverage, reproducible versions, adversarial tests, accessible interaction design, and honest treatment of uncertainty.

---

This document defines a private technical product and decision-support tool. It is not legal, tax, investment, credit, or regulated financial advice.
