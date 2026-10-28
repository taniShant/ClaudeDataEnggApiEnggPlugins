---
name: block-unsafe-publish
description: Blocks Marquez publication unless upload_flag is explicitly true AND all CRITICAL validations pass.
trigger: before_publish
---

## Safety Gate

This hook intercepts any attempt to publish OpenLineage events to Marquez and enforces two conditions:

1. **Explicit opt-in**: The `upload_flag` parameter must be explicitly set to `true` by the invoker. The agent NEVER auto-publishes.

2. **Critical validation gate**: All CRITICAL validation checks (V01, V02, V03, V04, V05, V06, V12) must pass. If any CRITICAL check fails, publication is blocked regardless of `upload_flag`.


## Blocked Actions

When this hook triggers:
- No HTTP POST requests to any Marquez endpoint
- The agent reports which conditions failed
- All other deliverables (workbook, JSON, validation report) are still generated
- Exit code is set to 1

## Allowed Actions

Publication proceeds only when:
- `upload_flag == true` (explicitly set by user)
- All CRITICAL validation checks pass
- The Marquez endpoint is reachable

## Key Safety Rules

- **No PII in lineage** — only metadata (column names, types, transformation logic)
- **MongoDB key safety** — all dataset/column names sanitised (dots→underscores, brackets/$→removed)
- **SSL handling** — internal certificates verified using the Barclays internal CA bundle (`REQUESTS_CA_BUNDLE` or system trust store).
- **Idempotent** — events can be re-published safely; Marquez deduplicates by runId
