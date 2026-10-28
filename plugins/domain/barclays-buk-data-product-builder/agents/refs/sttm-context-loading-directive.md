---
description: "Protocol for STTM agents to load shared context from sttm-system-context — specifies which sections to load (Mapping Columns, Source Volumetrics, Key Constraints) and which to skip."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-25
---

# STTM System Context Loading Directive

> All STTM agents must follow this protocol when loading shared context from
> `sttm-system-context.md`. This avoids duplicating context that is already
> provided by agent-specific prompts or passed as structured input.

## Loading Protocol

Load from `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-system-context.md` — ONLY these sections:
- §"16 Mapping Columns" (column A–P table)
- §"10 Source Volumetrics Columns" (column A–J table)
- §"Key Constraints" (7 bullet points)

Do NOT load: §"What is an STTM", §"Classification Model", §"Column Resolution Records",
§"JSON-First Philosophy", §"Interview Delivery", §"Multi-Table Structured Format",
§"Evidence Precedence" (already in agent-specific prompts or passed as structured input).
