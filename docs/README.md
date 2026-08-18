# Documentation Map

This directory separates stable product intent, current state, development
process, and architectural rationale so that one document does not silently
become responsible for all of them.

## Required daily path

1. [Agent contract](../AGENTS.md)
2. [Current context](context/CONTEXT.md)
3. Relevant sections of the [product vision](product/vision.md)
4. [Development workflow](process/development-workflow.md)
5. Relevant [ADRs](adr/README.md) and task-specific documents

## Ownership

| Directory | Content | Update rule |
| --- | --- | --- |
| `product/` | Product purpose, scope, roadmap, and MVP acceptance. | Change only through an explicit product decision. |
| `process/` | Delivery, review, QA, commit, and PR rules. | Change when the engineering process itself changes. |
| `context/` | Current state, historical reference, and discoveries. | Keep current state concise; keep discoveries append-only. |
| `adr/` | Accepted architectural decisions and their rationale. | Add or supersede ADRs; do not silently rewrite accepted history. |

## Anti-duplication rule

Link to a canonical decision instead of copying it. If two documents must
mention the same rule, one owns the full definition and the other contains a
short summary plus a link.
