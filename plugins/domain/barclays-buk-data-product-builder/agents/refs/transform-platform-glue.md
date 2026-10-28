---
description: "AWS Glue-specific TargetWriter integration — defines initialization pattern for parameter parsing and SourceReader instantiation in Glue pipeline transforms."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# TargetWriter Usage (Glue Platform)

This reference defines the TargetWriter integration pattern for AWS Glue transforms.

## TargetWriter Initialization and Usage

```python
# In transform class __init__
self.param      = [p.strip() for p in param.split(',')] if isinstance(param, str) else param
self.table_type = self.param[1] if len(self.param) > 1 else None
self.start_date = self.param[2] if len(self.param) > 2 else None
self.end_date   = self.param[3] if len(self.param) > 3 else None

self.reader = SourceReader(
    spark=spark,
    glue_read_table=glue_read_table,
    glue_read_icb_table=glue_read_icb_table,
    config=config,
    param=self.param,
    current_business_date=current_business_date,
)
# In __init__ (NOT load):
self.writer = TargetWriter(
    spark=spark,
    config=config,
    param=self.param,
    current_business_date=current_business_date,
    primary_key_cols=config.get("cdc", {}).get("primary_key_cols", []),
    partition_col="{partition_col}",
    cdc_exclude_cols=config.get("cdc", {}).get("exclude_cols", []),
    snapshot_mode=config.get("cdc", {}).get("snapshot_mode", False),
)

# In load() method:
self.writer.write(transformed_df)
```

## CDC Config Resolution (Phase 2.5 Step B)

- Priority 1: `mapping_parsed.json` → `cdc_exclude_cols_hint` (from Additional Context). If non-null → use it, skip domain knowledge.
- Priority 2 (fallback): `scoped_domain_knowledge` → look for explicit cdc_exclude_cols list (only when hint is null)
- Write extracted values into the `"cdc"` section of config.json: `"primary_key_cols"` and `"exclude_cols"`
- Example (mapping hint): Additional Context has `cdc_exclude:source_extract_timestamp,batch_id` → config.json `"cdc": {"exclude_cols": ["source_extract_timestamp", "batch_id"]}`
- Example (domain knowledge fallback): domain knowledge says "exclude source_extract_timestamp and batch_id from CDC" → config.json `"cdc": {"exclude_cols": ["source_extract_timestamp", "batch_id"]}`
- If NEITHER mapping hint NOR domain knowledge has CDC exclusions → `"exclude_cols": []` (empty list)
- NEVER hardcode CDC params directly in transform code — they live in config

## Rolling Deletion — `_rolling_delete()`

```
_rolling_delete() → None
    Post-write deletion of rows matching config['rolling_deletion']['predicate'].
    Called automatically at the end of write(). No-op for SCD2 tables or when config absent.
    Interpolates {current_business_date} from self.current_business_date.isoformat().
    Applicable to: Transactional, NonTransactional_SCD1.
```

The transform does not call `_rolling_delete()` — it is invoked internally by `TargetWriter.write()` after the main write strategy completes. Config structure:

```json
{
  "rolling_deletion": {
    "enabled": true,
    "predicate": "dw_bus_dt < CAST('{current_business_date}' AS DATE) - INTERVAL 90 DAY"
  }
}
```

---

> **Note**: The constructor signatures and method APIs shown above are illustrative summaries. The **authoritative source** is the actual utility code at `${CLAUDE_PLUGIN_ROOT}/templates/glue/generic_components/reader.py` and `writer.py`. Read those files in the GATHER phase (STEP 0.55) for exact signatures, return types, and available methods.
