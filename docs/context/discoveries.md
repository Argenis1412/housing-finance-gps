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

_No discoveries recorded._
