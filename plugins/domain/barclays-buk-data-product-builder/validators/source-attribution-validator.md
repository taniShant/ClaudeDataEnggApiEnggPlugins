# Validator: source-attribution-validator

**Purpose**: Verify that source table attribution comments in generated transform files (e.g., `# Source: database.table`) correctly match the `source_references[]` in `mapping_parsed.json`. Catches LLM context confusion where database and table names get cross-wired in multi-source scenarios.

**Severity**: BLOCK on source attribution mismatch (wrong database.table pairing).

**Platform**: Glue + Databricks

---

## Prerequisites

- Generated transform file(s) exist (`generated/{platform}/transforms/` or `generated/databricks/src/Notebooks/`)
- `session/mapping_parsed.json` exists with populated `source_references[]` per column

---

## Invocation

- **Primary**: Called inline by `/gen-transform` STEP FINAL.3 (runs after literal-value-fidelity-validator)
- **Secondary**: Called by `/validate` Batch 4 (runs as part of consistency validation suite)

> **Dual invocation**: Runs inline during `/gen-transform` STEP FINAL.3 (immediate feedback) and in `/validate` Batch 4 (second pass). Both use identical rules.

---

## Checks

### Check 1 — Source Comment Attribution (BLOCKING)

For each source table attribution comment in generated `.py` files:
1. Extract `database.table` pairs from comments matching patterns:
   - `# Source: database_name.table_name`
   - `# Source table: database_name.table_name`
   - `# Read from: database_name.table_name`
   - Comments in `prepare_sources()` method attributing alias to source
2. Build the expected set of `{database}.{table}` pairs from `mapping_parsed.json`:
   - Collect unique `{source_references[].database}.{source_references[].table}` across all columns for this target table
3. Verify each comment-attributed pair exists in the expected set

**BLOCK** if:
- A comment attributes a table to a database that the mapping does NOT specify for that table
- A comment references a `database.table` combination not found anywhere in the mapping's source_references

**Error format:**
```
❌ Source attribution mismatch at line 34
   Comment says: # Source: e_wrong_db.customer_account
   Mapping specifies: e_correct_db.customer_account
   Available source tables from mapping: [e_correct_db.customer_account, e_correct_db.customer_survey]
```

### Check 2 — Config Source Section Alignment (BLOCKING)

Read `*_config.json` (or `*_config.yml`) → extract source table definitions from `source.non-transactional` and `source.transactional` sections.

For each source entry, extract the `"table"` field (format: `"database.table_name"`).

Cross-reference against `mapping_parsed.json` → unique `{database}.{table}` pairs.

**BLOCK** if:
- Config references a `database.table` pair not in the mapping
- Config assigns a table to the wrong database compared to mapping

**Error format:**
```
❌ Config source table mismatch for alias 'customer_response'
   Config says: "table": "e_wrong_db.customer_response"
   Mapping specifies: e_correct_db.customer_response
```

### Check 3 — Alias-to-Source Consistency (WARNING)

Verify that the same alias in config.json maps to the same source table as referenced in the transform file.

**WARN** if:
- Config alias `"acct"` maps to `db_a.account_table` but transform comment for same alias says `db_b.account_table`

---

## Known Exceptions (NOT flagged)

| Category | Examples | Reason |
|----------|----------|--------|
| **Intermediate/derived DataFrames** | `# Derived from join of X and Y` | Multi-source join descriptions are informational |
| **Lookup table comments** | `# Lookup: ref_product (broadcast)` | Lookup reference without full qualification |
| **No source comment present** | Transform has no source attribution comments | Absence of comments is not a violation (Check 1 only validates present comments) |

---

## Extraction Patterns (Regex)

```python
# Comment patterns for source attribution
r'''#\s*(?:Source|Source table|Read from)\s*:\s*(\w+)\.(\w+)'''

# Config.json source table field
r'''"table"\s*:\s*"(\w+)\.(\w+)"'''

# Config.yml source table field
r'''table:\s*["']?(\w+)\.(\w+)["']?'''
```

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/gen-transform` STEP FINAL.3 | After literal-value-fidelity-validator | Run validator → report findings |
| `/gen-config` STEP FINAL.2 | After CDC assertion | Run Check 2 on config file |
| `/validate` Batch 4 | During consistency validation suite | Run all checks → report findings |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `source_attribution_result` | string | STEP FINAL.3 | `"passed"`, `"failed"`, `"skipped"` |
| `source_attribution_violations` | array\|null | STEP FINAL.3 | Array of violation objects, or null if passed |

---

## Pass Condition

All source table attributions (comments and config entries) in generated files correctly match the `database.table` pairs specified in `mapping_parsed.json` → `source_references[]`. Zero cross-wired database assignments.
