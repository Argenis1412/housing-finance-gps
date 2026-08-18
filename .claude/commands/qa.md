---
description: Run the full QA suite and report results in the standard format.
---

Read `docs/context/CONTEXT.md#qa-status` and run every configured QA command
for the affected backend, frontend, contract, and browser layers.

Do not invent commands when a toolchain is not configured. For a
documentation-only change, validate Markdown links, documentation ownership,
unresolved template placeholders, consistency with the product vision, and
the absence of identifying personal data.

Report the results using this exact format:

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

### Documentation validation
PASS / FAIL / NOT APPLICABLE
```

If any check fails, show the full error output and **do not proceed with
the commit**.
