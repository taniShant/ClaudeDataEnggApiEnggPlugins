---
description: "Single source of truth for load type synonyms and canonical values (Day0, BAU, full_then_incremental) — all agents must reference this file instead of maintaining inline synonym tables."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-25
---

# Load Type Terminology (Canonical Reference)

> **Single source of truth** for load type synonyms and canonical values. All agents
> and commands **must reference this file** rather than inline synonym tables.

## Synonym Groups

| Canonical Value            | Synonyms (case-insensitive)                                              |
|----------------------------|--------------------------------------------------------------------------|
| `Day0`                     | day0, full, retrospective, historical, backfill, initial load            |
| `BAU`                      | bau, day1, incremental, daily, delta                                     |
| `full_then_incremental`    | full_then_incremental                                                    |

## Normalisation Map (Python)

```python
LOAD_TYPE_MAP = {
    'day0': 'Day0', 'full': 'Day0', 'retrospective': 'Day0',
    'historical': 'Day0', 'backfill': 'Day0', 'initial load': 'Day0',
    'bau': 'BAU', 'day1': 'BAU', 'incremental': 'BAU',
    'daily': 'BAU', 'delta': 'BAU',
    'full_then_incremental': 'full_then_incremental',
}
load_type = LOAD_TYPE_MAP.get(load_type.lower(), load_type)
```

## Semantics

- **Day0 (Full Load)**: One-time historical load — all records from source. Generates
  `transform_day0.py`. Typically run once during initial data product setup.
- **BAU (Incremental)**: Ongoing new/changed records only. Generates `transform_day1.py`.
  Run on a scheduled cadence (daily, weekly, etc.).
- **full_then_incremental**: Generates both Day0 and BAU transforms. The data product
  starts with a full historical load, then switches to incremental.
