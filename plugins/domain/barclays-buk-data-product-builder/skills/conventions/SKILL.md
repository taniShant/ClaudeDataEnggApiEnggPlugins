---
name: conventions
description: "Agent execution policy — scope boundaries (what agents must NOT do), structured logging format, and skill auto-loading mechanics. Loaded by every agent; governs behaviour regardless of domain."
user-invocable: false
owner: "Tom Franklin <tom.franklin@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

**Source:** Tom Franklin | **Owner:** Tom Franklin | **Review:** Quarterly | **Last reviewed:** 2026-07-08

## EXECUTION POLICY (Agent Behaviour Constraints)

> These rules govern HOW agents execute. They are operational policy, not domain knowledge.

## SCOPE BOUNDARY (NON-NEGOTIABLE)

Execute ONLY the steps listed in this document. NOTHING ELSE.

- Do NOT refactor, improve, or "clean up" code outside your listed steps
- Do NOT add steps, features, or fixes not explicitly documented here
- Do NOT modify files outside your phase's responsibility
- Do NOT make "while I'm here" improvements — they are FORBIDDEN
- If you encounter something unexpected → invoke auto-decision-agent with context
- If instructions are ambiguous → invoke auto-decision-agent, do NOT interpret freely

---

## DOMAIN KNOWLEDGE (Logging & Naming Standards)

> Reusable knowledge about how artefacts should implement logging. Framework-agnostic.

## Structured Logging Convention

All agents producing artefacts SHOULD initialize structured logging at:
- Session start (component name, session_id)
- Each artefact generation (table name, phase, outcome)
- Session completion (summary, duration)

#### Python Implementation (Framework-Specific)

> The following is specific to the current Python/PySpark implementation. Adapt for other frameworks.

```python
from utils.structured_logger import StructuredLogger

logger = StructuredLogger(
    session_id=session_state.session_id,
    component="{agent-name}",
    audit_log_path="session/audit_log.jsonl"
)
```

Log at these points:
- Agent start: `logger.debug("Agent started", {...context})`
- Each artefact generated: `logger.debug(f"{artefact} generated", {"file": path, "time_ms": elapsed})`
- Completion: `logger.debug("Agent completed", {...summary})`

---

## MECHANICS (Skill Loading)

## Skill Loading

Each agent's declared skills (in frontmatter `skills: [...]`) are auto-loaded into context.
No explicit "Phase 0" section is needed — skill content is available immediately.
Reference skill data by name in subsequent phases (e.g., "From tenancy skill, look up...").

---

## Agent Self-Check

Before producing output, verify:
1. All referenced skills are declared in your frontmatter
2. Logging events follow the structured logging convention above
3. Outputs are explicitly named and traceable to inputs

## Areas for Specialist Extension

- Custom logging backends (e.g., CloudWatch, Splunk)
- Additional artefact naming patterns for new platform targets
- Skill loading order customisation for complex dependency graphs

## Authoritative Source Registry

Patterns commonly referenced inline by agents. If an agent cites one of these, the authoritative source is the skill listed — inline citations are convenience copies only.

| Pattern | Authoritative Source |
|---------|---------------------|
| Audit column names (eff_start_date, active, dw_lod_tmp) | barclays-buk-data-product-builder:database-naming-standards |
| Active column value ('1' / '0') | barclays-buk-data-product-builder:database-naming-standards |
| S3 path patterns | barclays-buk-data-product-builder:aws-data-products |
| Tenancy names, ITSI codes | barclays-buk-data-product-builder:aws-tenancy / service-management |
| Data product type rules (FDP/CDP/BDP) | barclays-buk-data-product-builder:data-products |
| Database naming conventions (snake_case, prefix rules) | barclays-buk-data-product-builder:database-naming-standards |
