# Hook: crypto-flag-propagate

> **Type:** Documentation (orchestration logic — not an executable hook)

**Trigger**: After `/parse-mapping` completes (crypto_flags.json written)

**Purpose**: Propagate crypto flags from `session/crypto_flags.json` to all downstream generation agents. Ensure crypto UDFs are injected into transform files (both platforms) and dtxog crypto config is added (Glue only).

---

## Propagation Rules

### When `any_column_crypto_flagged = false`

No action. Crypto is entirely optional — if not present in mapping document transformation logic, the crypto flow is skipped completely. All downstream agents receive `no_crypto = true` signal.

### When `any_column_crypto_flagged = true`

Propagate via session state (agents read `crypto_flags.json` on their next invocation):

1. **transform-generator-agent** (both platforms):
   - Reads `protegrity_de_mappings[]` from `intent_identification.json`
   - Inject detokenization `spark.sql()` calls before transformation for `operation=detokenize` columns
   - Inject tokenization `spark.sql()` calls after transformation for `operation=tokenize` columns
   - Enforce `spark.sql()` only — never DataFrame API

2. **glue-dtxog-agent** (Glue only):
   - Select `dtxog_config_byoc_crypto_*.template.json` instead of standard template
   - Add `crypto_dpaas` block with `enable_crypto_api: "true"`
   - Auto-assemble `custom_de_list` from all extracted DE names
   - Add crypto SparkConf to `xtra-args.sparkConf`
   - Add `package-file` per env

3. **databricks-artefact-agent** (Databricks only):
   - Crypto UDFs in `transform.py` only
   - **No crypto config file generated** — Databricks crypto credential management is outside plugin scope

---

## Refusal Check

For each column with `extraction_failed: true`:
- Log REFUSAL: "Column `{col}` is flagged for crypto but DE name cannot be extracted from transformation logic. Crypto artefact generation refused for this column."
- Flag in `session/audit_log.jsonl` with `event: crypto_refusal`
- Do NOT emit placeholder for this column; do NOT generate partial crypto logic
- Other non-failed crypto columns proceed normally

---

## custom_de_list Assembly

The `custom_de_list` for dtxog config is auto-assembled from all unique DE names extracted across all flagged columns with `extraction_failed: false`:

```python
de_names = [col['de_name'] for col in crypto_flags.columns.values() 
            if col['is_crypto'] and not col['extraction_failed'] and col['de_name']]
custom_de_list = str(sorted(set(de_names)))  # e.g. "['UK_TOK_FT_L0R0_UNC_DE']"
```

This is NEVER a placeholder — it is always deterministically assembled from the mapping document.

---

## Audit Log

```json
{
  "timestamp": "...",
  "event": "crypto_flags_propagated",
  "any_column_crypto_flagged": true,
  "crypto_columns": ["account_number", "sort_code"],
  "de_names_extracted": ["UK_TOK_FT_L0R0_UNC_DE"],
  "refusals": [],
  "platform": "glue"
}
```
