---
description: "Pointer to DV SQL quality rules — rule definitions and execution algorithm"
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-29
---

# DV SQL Quality Rules — Reference Pointer

This file was consolidated to reduce context window pressure during `/dv-generate` execution.

- **Rule definitions** (QUALITY-01 through QUALITY-10, algorithms, severity, engine scope): `${CLAUDE_PLUGIN_ROOT}/configs/dv/sql_quality_rules.yaml`
- **Execution algorithm** (comment stripping, SQL variants, evaluation flow, self-heal retry logic, coverage summary, known non-violations, session state fields, integration points): `${CLAUDE_PLUGIN_ROOT}/validators/dv-sql-quality-validator.md`
