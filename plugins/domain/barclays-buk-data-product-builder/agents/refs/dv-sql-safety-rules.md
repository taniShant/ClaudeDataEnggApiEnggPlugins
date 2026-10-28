---
description: "Pointer to DV SQL safety rules — rule definitions and execution algorithm"
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-29
---

# DV SQL Safety Rules — Reference Pointer

This file was consolidated to reduce context window pressure during `/dv-generate` execution.

- **Rule definitions** (SAFETY-01 through SAFETY-10, regex patterns, severity, exceptions): `${CLAUDE_PLUGIN_ROOT}/configs/dv/sql_safety_rules.yaml`
- **Execution algorithm** (comment stripping, validation flow, self-heal retry logic, known exceptions, session state fields, integration points): `${CLAUDE_PLUGIN_ROOT}/validators/dv-sql-safety-validator.md`
