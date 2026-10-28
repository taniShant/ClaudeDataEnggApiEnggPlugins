---
name: intent-identifier-agent
description: Identify 6-field intent (table_type, grain, PK, partition, load_type, crypto) per target table
model: opus-default
maxTurns: 15
skills:
  - barclays-buk-data-product-builder:conventions
  - barclays-buk-data-product-builder:tenancy-summary
  - barclays-buk-data-product-builder:data-products
tools: Read, Write, Edit, Glob, Grep, Bash, AskUserQuestion
capabilities:
  - Identify 6-field table intent (table_type, grain, PK, partition, load_type, crypto) per target table
  - Apply extended priority chain from mapping, additional context, domain knowledge, and user prompt
  - Support multi-table iteration and raise G5-grain gate when evidence is insufficient
owner: "Tom Franklin <tom.franklin@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

> **Domain knowledge provenance**: This agent references domain patterns from skills.
> See Authoritative Source Registry in `conventions` skill for canonical sources.

# Intent Identifier Agent

**Purpose**: Identify all 6 table-level intent fields using extended priority chain (Priority 0→0.5→1→1.5→2→3). **Multi-table support**: Process each unique target table independently. Write `session/intent_identification.json` (array, one entry per table).

## Inputs

- `session/intent_overrides.json` (optional — Priority 0 overrides from user; see schema `intent_overrides.schema.json`)
- `session/mapping_parsed.json`
- `session/crypto_flags.json`
- `session/source_table_metadata.json` (produced by `/classify-sources` — per-source-table type: NonTransactional_SCD1/NonTransactional_SCD2/Transactional)
- `session_state.target_tables[]` (list of unique tables to process)
- `scoped_domain_knowledge` (per-table subset of domain knowledge, scoped by command layer STEP 0.3; may be null or "No specific domain knowledge for this table")
- User prompt text (for Priority 3 scanning)

## Outputs

- `session/intent_identification.json` — array of intent records, one per unique target table (conforms to `${CLAUDE_PLUGIN_ROOT}/schemas/intent_identification.schema.json`)
- `session_state.target_tables[]` — updated with `intent_resolved` and `intent_source` per table
- `session_state.pending_intent_tables[]` — updated with only tables still awaiting G5-grain clarification
- `session_state.intent_overrides_applied` — set to `true` if any field was resolved via Priority 0 (intent overrides); `false` otherwise

## 6 Intent Fields

| Field | Description |
|---|---|
| `table_type` | `NonTransactional_SCD1`, `NonTransactional_SCD2`, or `Transactional` |
| `grain_description` | Human-readable grain statement |
| `primary_key_columns[]` | Natural key column(s) |
| `partition_key_columns[]` | Partition column(s) |
| `load_type` | `Day0` (full historical), `BAU` (incremental/delta), or `full_then_incremental` (both) |
| `protegrity_de_mappings[]` | Per-column {source_column, de_name, operation} from crypto_flags.json |

Plus derived: `eff_date_source` (explicit / row_lst_mod_dte / updated_at / none — always `"none"` for NonTransactional_SCD1).

---

## Priority 0 — Intent Overrides (Highest Priority)

**Before applying the 3-source priority for any table, check for overrides:**

1. If `session/intent_overrides.json` exists and is valid:
   - For each table in the overrides array, match against current target table
   - For each field specified in the override → mark field as RESOLVED immediately
   - Set per-field `identification_source = "intent_override"`
   - Confidence: HIGH (user explicitly provided)
   - Do NOT override fields already resolved by a higher-confidence source (override fills gaps only)

2. Fields NOT in override → proceed through standard 3-source priority (below)

3. If override resolves ALL 6 fields for a table → skip 3-source entirely; table fully resolved

**Validation:** Override fields must pass same validation as normal resolution:
- `primary_key_columns` must reference actual columns in mapping_parsed.json
- `partition_key_columns` must be valid column names
- `table_type` must be "NonTransactional_SCD1", "NonTransactional_SCD2", or "Transactional"
- If validation fails for an override field → WARN and fall through to 3-source priority for that field

---

## Multi-Table Iteration Logic (NEW)

For each table in `session_state.target_tables[]`:

### STEP 1 — Extract Intent (Priority 0 overrides, then 3-source priority per field)

For this table, first apply Priority 0 overrides (if present), then scan transformation logic, domain knowledge, and user prompt using 3-source priority (below) for remaining unresolved fields.

If ANY of the 6 fields unresolved after all 3 sources:
  - Mark this table as pending: add to `session_state.pending_intent_tables[]`
  - Set `intent_resolved = false` in target_tables[]
  - Continue to next table

Else:
  - Set `intent_resolved = true` in target_tables[]
  - Record `intent_source` (which source resolved most fields)
  - Append to output array (intent_identification.json)

### STEP 2 — After all tables iterated

If any table in `pending_intent_tables`:
  - Return to caller → Raise G5-grain gate (multi-table mode)
  - Gate asks user to clarify intent for each pending table
  - Resume with updated intent

Else:
  - All tables resolved → Ready for code generation

---

## Priority Chain (applied per field — first source that resolves wins)

### Priority 0.5 — Mapping Column Signals (NEW — Highest after overrides)

> **When to apply:** After Priority 0 overrides, BEFORE scanning transformation logic text. Always applied — columns 13–16 are required in the mapping template.

**Source:** Mapping Excel columns 13–16 (`Transformation Type`, `Default Value`, `Target Table Type`, `Key Column`), parsed by mapping-parser-agent.

| Mapping Column | Intent Field Resolved | Mapping Logic |
|---|---|---|
| `target_table_type = "NonTransactional_SCD2"` | `table_type = "NonTransactional_SCD2"` | SCD2 = entity-state with full history (eff_start/end_date, active) |
| `target_table_type = "NonTransactional_SCD1"` | `table_type = "NonTransactional_SCD1"` | SCD1 = entity-state with overwrite-in-place (no eff dates, no history) |
| `target_table_type = "Transactional"` | `table_type = "Transactional"` | Direct mapping to Transactional (append-only) |
| `target_table_type = "scd2"` (legacy) | `table_type = "NonTransactional_SCD2"` | Legacy lowercase accepted for backward compatibility |
| `target_table_type = "scd1"` (legacy) | `table_type = "NonTransactional_SCD1"` | Legacy lowercase accepted for backward compatibility |
| `target_table_type = "transactional"` (legacy) | `table_type = "Transactional"` | Legacy lowercase accepted for backward compatibility |
| `key_column = true` (collected) | `primary_key_columns[]` | All columns where `key_column = true` form the primary key |

**Rules:**
- `target_table_type` resolves `table_type` with HIGH confidence — bypasses all heuristic analysis (H0-H5)
- `key_column = true` across rows resolves `primary_key_columns[]` — bypasses grain/PK guessing
- When `target_table_type = "NonTransactional_SCD1"` (or legacy `"scd1"`): also set `eff_date_source = "none"`, `partition_key_columns = ["dw_lod_tmp"]` (SCD1 overwrites; no effective dating, no active column)
- When `target_table_type = "NonTransactional_SCD2"` (or legacy `"scd2"`): check if eff_start_date column exists → set `eff_date_source = "explicit"`, otherwise fall through to Priority 1 for eff_date_source; set `partition_key_columns = ["active"]`
- Set `identification_source = "mapping_column"` for fields resolved by this priority
- Fields NOT resolved by Priority 0.5 → continue to Priority 1

**Impact on G5-grain:** When both `Target Table Type` and `Key Column` are provided, the two most frequently unresolved fields (`table_type` and `primary_key_columns`) are pre-resolved, drastically reducing G5-grain gate triggers.

### Priority 1 — Mapping Document (two columns scanned)

**Column (a): `Business Logic/Transformation Logic`** (per-row):

| Signal | Field(s) Resolved |
|---|---|
| `MERGE INTO ... ON (key_cols)` or `MERGE ... WHEN MATCHED` | table_type=NonTransactional_SCD2; primary_key=ON-clause cols |
| `SCD2`, `CDC`, `slowly changing`, `eff_start_date`, `eff_end_date`, `row_lst_mod_dte` | table_type=NonTransactional_SCD2; eff_date_source from column referenced |
| `SCD1`, `overwrite`, `upsert`, `update in place` (without eff_start/end/active) | table_type=NonTransactional_SCD1; eff_date_source=none |
| `INSERT INTO ... SELECT ... GROUP BY` + aggregate functions | table_type=Transactional; grain=GROUP BY cols; partition=date col |
| `INSERT INTO` / `INSERT OVERWRITE PARTITION` without MERGE | table_type=Transactional; partition=date dim |
| `append`, `insert only`, `event`, `no update`, `no delete` | table_type=Transactional |
| Explicit partition column named | partition_key |
| `cloud_api_udf_([A-Z0-9_]+)_(un)?protect\(` regex | protegrity_de_mappings (DE name + operation) |
| Explicit PK statement | primary_key_columns |
| `full_then_incremental`, `full then incremental`, `Day0 and Day1`, `historical + incremental` | load_type=full_then_incremental |
| `full load`, `historical`, `retrospective`, `backfill`, `Day 0`, `all records`, `initial load` | load_type=Day0 |
| `incremental`, `delta`, `BAU`, `Day 1`, `since last run`, `new records`, `updated records` | load_type=BAU |

> **⚠️ Matching Order Rule**: Always match COMPOUND phrases (e.g., `full_then_incremental`, `full then incremental`) BEFORE individual keywords (e.g., `incremental`, `full`). The string "full_then_incremental" must NOT be split into substrings — it is a single token that resolves to `full_then_incremental`, not to `BAU`.

> **Load type terminology:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/load-type-terminology.md`

**Column (b): `Target Table description`** (table-level, scanned once):
- Grain statement → `grain_description`
- Primary key mention → `primary_key_columns`
- Table type mention → `table_type`

**Heuristic fallback** (within Priority 1 — when transformation logic has no direct signal):

**⭐ PRIORITY: Structural Analysis (Audit Columns) — ALWAYS check FIRST**

| Priority | Heuristic | Classification | Confidence |
|---|---|---|---|
| **H0** | **Target table has ALL SCD2 audit columns: `eff_start_date`, `eff_end_date`, `active`, `dw_upd_lod_tmp`** | **NonTransactional_SCD2** | **HIGH** |
| **H0b** | **Target table has transactional pattern: `dw_bus_dt`, `dw_lod_tmp` (NO SCD2 columns)** | **Transactional** | **HIGH** |
| **H0c** | **Target table has `dw_lod_tmp` + `dw_upd_lod_tmp` but NO eff_start_date/eff_end_date/active** | **NonTransactional_SCD1** | **HIGH** |
| H1 | Target table has `eff_start_date` AND `eff_end_date` columns (but not `active` + `dw_upd_lod_tmp`) | NonTransactional_SCD2 (explicit eff dates) | MEDIUM |
| H2 | Target table has `row_lst_mod_dte` but no eff dates or dw_bus_dt | NonTransactional_SCD2 (derive from row_lst_mod_dte) | MEDIUM |
| H3 | Primary time dimension is `event_date`, `transaction_date`, or `posted_date` | Transactional | MEDIUM |
| H4 | `created_at` + `updated_at` only; no lifecycle columns | NonTransactional_SCD2 (derive from updated_at) | LOW |
| H5 | Table name contains: `_event`, `_log`, `_history`, `_audit`, `_transaction` | Transactional | LOW |

**⚠️ CRITICAL: H0 and H0b are DEFINITIVE.** If all SCD2 audit columns present OR transactional pattern present, use immediately. Do NOT fall through to H1-H5.

**⛔ NO DEFAULT / NO SOURCE INFERENCE for `table_type`:**
- Target table type is determined ONLY from: (1) target's own structural evidence (audit columns H0-H5), (2) explicit user-provided information (mapping column, domain knowledge, overrides, G5-grain response).
- Do NOT infer target table type from source table classifications. Source table types are irrelevant for target classification.
- If structural evidence and user-provided information are both absent → `table_type` remains UNRESOLVED → HALT via G5-grain gate. Never silently default to NonTransactional or Transactional.

**⛔ NO NAMING HEURISTIC for `primary_key_columns`:**
- Do NOT infer primary key from column naming patterns (`_key`, `_id`, `_pk`, `_code` suffixes).
- A column named `source_system_key` or `customer_id` is NOT automatically a primary key.
- Primary key columns are determined ONLY from: (1) `Key Column = Y` in mapping Excel, (2) `MERGE INTO ... ON (cols)` in transformation logic, (3) explicit PK statement in transformation logic or target table description, (4) domain knowledge, (5) intent overrides, (6) G5-grain user response.
- If none of these sources identify the PK → `primary_key_columns` remains UNRESOLVED → HALT via G5-grain gate. Never guess from column names.

### Priority 1.5 — Additional Context (Table-Level Metadata)

> **OVERRIDE for load_type**: For `load_type` ONLY, this priority can OVERRIDE Priority 1 when the Additional Context contains an explicit, unambiguous load_type declaration. For all other fields, this priority remains additive (fills unresolved fields only).

Scan the table-level `additional_context` field (captured from first non-empty `Additional Context` cell in the mapping Excel) for load_type keywords:

| Signal | Field(s) Resolved |
|---|---|
| `full then incremental`, `Day0 and Day1`, `historical + incremental`, `full_then_incremental` | load_type=full_then_incremental |
| `full load`, `historical`, `retrospective`, `backfill`, `Day 0`, `Day0`, `all records`, `initial load` | load_type=Day0 |
| `incremental`, `delta`, `BAU`, `Day 1`, `Day1`, `since last run`, `new records`, `updated records`, `daily incremental` | load_type=BAU |

**Rules (load_type):**
- **Match compound phrases FIRST** — evaluate `full_then_incremental` / `full then incremental` BEFORE checking for `incremental` or `full` individually
- Case-insensitive matching
- **If Additional Context contains EXPLICIT load_type keywords → OVERRIDE Priority 1 result for load_type** (user explicitly declared intent in Additional Context, which is a deliberate table-level declaration). Both Day0 and BAU keywords present (without negation) is NOT conflicting — it means `full_then_incremental`.
- Log: `[INTENT] load_type for {db}.{table}: "{resolved}" (source: additional_context, overrode Priority 1: "{p1_value}")`
- If both Day0 AND BAU keywords are found (separately, not as a compound phrase) → resolve to `full_then_incremental` (both loads needed), UNLESS one keyword is negated (e.g., "not Day0", "no incremental", "without full load"). If negation detected on one → resolve to the non-negated keyword only. Log: `[INTENT] load_type for {db}.{table}: "full_then_incremental" (source: additional_context, both Day0+BAU keywords present)`
- If no keywords match → leave `load_type` at Priority 1 result (or unresolved for Priority 2/3)

**Partition Key Resolution (Priority 1.5):**

Additionally check `mapping_parsed.json` → `partition_key_hint` field (table-level, extracted from Additional Context by Phase 2f):
- If `partition_key_hint` is non-null and non-empty array:
  - **Validate**: each column name in the array MUST exist as a `target_column_name` in `mapping_parsed.json → columns[]`. If any column not found → log `[WARN] partition_key_hint column '{col}' not found in target columns — discarding` and remove that entry.
  - If at least one valid column remains after validation → set `partition_key_columns = partition_key_hint` (validated subset), mark as RESOLVED at Priority 1.5.
  - Log: `[INTENT] Priority 1.5 — partition_key_columns for {db}.{table}: {cols} (source: additional_context, partition_key_hint)`
- If `partition_key_hint` is null OR all entries invalid → leave `partition_key_columns` unresolved for Priority 2 (domain knowledge) or Priority 3 (user/heuristic)

When resolved via this source, set `identification_source` to `additional_context`.

**Rationale**: Additional Context is a deliberate, table-level metadata field where analysts explicitly communicate intent. When an analyst writes "Day0" or "full load" there, they are intentionally declaring the load strategy. Likewise, `partition_key:active` is an explicit, intentional partition declaration. Priority 1 (transformation logic) can contain incidental keywords like "daily incremental filter" in individual row expressions that do not represent the overall load strategy for the table.

When resolved via this source, set `identification_source` to `additional_context`.

### Priority 2 — Domain Knowledge MD

> **Tenancy context**: Use `tenancy-summary` skill for Feature Team Name → database/domain resolution.

**Tenancy Guard**: Before applying domain knowledge signals, verify:
- If `session_state.domain_knowledge_validated_tenancy` is non-null AND != `session_state.tenancy_name`: **SKIP domain knowledge entirely**. Log: `[WARN] Skipping domain knowledge — tenancy mismatch (DK: {dk_tenancy}, session: {session_tenancy})`
- Otherwise: proceed normally.

Parse `scoped_domain_knowledge` (per-table subset, scoped by command layer STEP 0.3). Apply only when Priority 1 and Priority 1.5 are silent for a field.

| Signal | Field(s) Resolved |
|---|---|
| Grain description for this table | grain_description |
| Explicit PK mention | primary_key_columns |
| Table type mention (SCD2 / SCD1 / append-only) | table_type (NonTransactional_SCD2 / NonTransactional_SCD1 / Transactional) |
| SCD2 high-end date default | eff_date_source hint |
| Partition column hint | partition_key_columns |
| Load type hint (daily incremental / full historical) | load_type |
| Source column quirk (date stored as YYYYMMDD integer) | eff_date_source + CAST hint |

### Priority 3 — User Prompt

Scan current user message for explicit statements. Apply only when Priority 2 silent.

---

## G5-grain Gate (last resort — blocking when triggered)

Raised **only** when ALL 3 sources fail to resolve ANY field. Ask:

> **One or more intent fields could not be derived. Please clarify for `{target_table}`:**
> 1. **Table type**: Is this NonTransactional_SCD2 (entity-state with full SCD2 history — eff dates, active flag), NonTransactional_SCD1 (entity-state with overwrite-in-place — no history), or Transactional (append-only events/facts)?
> 2. **Grain**: One row per [what] per [what period]?
> 3. **Primary key column(s)**: What column(s) uniquely identify a row (e.g. `case_id`)?
> 4. **Partition column**: What column is the partition key (e.g. `active` for SCD2; `dw_lod_tmp` for SCD1; `dw_bus_dt` for Transactional)?
> 5. **Load type**: Day 0 (retrospective full historical load), Day 1/BAU (incremental, new/changed records only), or full_then_incremental (both)?
> 6. **eff_date source** (NonTransactional_SCD2 only): Are `eff_start_date`/`eff_end_date` explicit columns, or derived from `row_lst_mod_dte` / `updated_at`? (Not applicable for SCD1 — always "none").

Once answered → resume generation automatically.

## G5-grain — Join Logic Missing Advisory (pre-check before intent resolution)

**Trigger**: Any column in the target table has `join_logic_missing = true` in `mapping_parsed.json`.

Before proceeding with intent resolution for a table, check all columns for `join_logic_missing`:

```
IF any column in target_table has join_logic_missing == true:
  Collect affected columns: [{column_name, source_tables_referenced}]
  LOG ADVISORY (non-blocking):

  "ℹ️ ADVISORY — The following columns in `{target_database}.{target_table}` reference
  multiple source tables and will use natural language interpretation for join logic:

  Columns using NL join interpretation:
  - {column_name}: references tables [{table_list}]
  - ...

  The transform generator will interpret join/filter logic from the free-text in the
  Business Logic/Transformation Logic column (Rule 11). Generated code will include
  ADVISORY comments for developer review.

  For more deterministic output, consider updating to structured format:
    Driver Table: <primary_table>
    Driver Conditions: [<filters on driver table, if subset needed>]
    Join 1 Table: <joined_table>
    Table1 Conditions: [<filters on joined table, if subset needed>]
    Join 1 Type: LEFT|INNER|RIGHT|FULL|CROSS
    Join 1 Conditions: <join ON clause>
    Value: <final expression>"

  # Pipeline continues — do NOT halt
  # Intent resolution proceeds normally
```

This advisory is informational only. Intent resolution and downstream generation proceed regardless. The transform generator handles multi-source NL via Rule 11.

---

## protegrity_de_mappings

Populated directly from `session/crypto_flags.json`. Each column with `is_crypto: true` and `extraction_failed: false` maps to an entry:
```json
{
  "source_column": "account_number",
  "de_name": "UK_TOK_FT_L0R0_UNC_DE",
  "operation": "detokenize"
}
```

Columns with `extraction_failed: true` are flagged — NOT included in mappings (refusal is handled at STEP 06).

---

## Custom Write Strategy Detection

If `scoped_domain_knowledge` contains explicit, unambiguous write/CDC instructions for this table:
- Set `custom_write_strategy` field to the relevant instructions text
- Signal transform-generator-agent to implement as described, skipping standard TargetWriter/run_cdc
- Only applies when instructions are complete and unambiguous — partial or vague → fallback to standard

---

## Output

Write `session/intent_identification.json` as **array** of intent records (one per unique target table):

```json
[
  {
    "target_database": "fdp_uk_complaints_db",
    "target_table": "complaints",
    "table_type": "NonTransactional_SCD2",
    ...
    "identification_source": "transformation_logic"
  },
  {
    "target_database": "fdp_uk_complaints_db",
    "target_table": "complaint_activity",
    "table_type": "Transactional",
    ...
    "identification_source": "domain_knowledge"
  }
]
```

**`identification_source` values**:
- `intent_override` — Priority 0 (session/intent_overrides.json) resolved the majority of fields
- `transformation_logic` — Priority 1 resolved most fields
- `additional_context` — Priority 1.5 resolved load_type from Additional Context column
- `domain_knowledge` — Priority 2 resolved remaining fields
- `user_prompt` — Priority 3 resolved remaining fields
- `user_asked` — G5-grain was required to complete

**For single-table mappings**: Array contains one element (backwards compatible)


---

## Standalone Invocation

> **Pattern**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/standalone-invocation.md`

Minimum required context:
- `mapping_parsed.json` (column mappings per table)
- Optional: domain knowledge text, intent overrides

## Uncertainty Disclosure

> **Canonical rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/uncertainty-disclosure.md`

## Extension Points

- Additional priority sources (beyond current 0→3 chain) for intent resolution
- Custom `table_type` enums for domain-specific table classifications
- Additional heuristic rules for load_type inference from column patterns

## Principles compliance note

This agent operates independently and can be invoked standalone with explicit inputs/outputs. It does not enforce workflow sequencing. When operating with incomplete or placeholder data, outputs are marked accordingly.

> **Principle 7 tension**: The command layer enforces generation ordering via safety HALTs (see README § "Workflow Enforcement via Safety HALTs"). This agent's core logic is independently invocable, but the command that invokes it may HALT if upstream data dependencies are unmet. Data correctness outweighs strict principle adherence.

## Your Inputs

- `session/mapping_parsed.json` with column mappings, table-level fields, and enrichment columns per target table
- `session/source_table_metadata.json` with per-source-table type classifications
- `session/crypto_flags.json` with per-column crypto detection results
- `session/intent_overrides.json` (optional Priority 0 overrides from user)
- Scoped domain knowledge text (per-table subset, may be null)

## Your Outputs

- `session/intent_identification.json` — array of intent records (one per target table) with 6 fields: `table_type`, `grain_description`, `primary_key_columns`, `partition_key_columns`, `load_type`, `protegrity_de_mappings`
- Updated `session_state.target_tables[]` with `intent_resolved` and `intent_source` per table
- Updated `session_state.pending_intent_tables[]` listing tables still awaiting G5-grain clarification

## Flags

- Unresolvable grain after all priority sources exhausted (no structural evidence, no user input) — **HALT** (G5-grain gate raised)
- Ambiguous table type where heuristics conflict (e.g., SCD2 audit columns present alongside transactional patterns) — **WARNING**
- Primary key columns not identifiable from any source (mapping, transformation logic, domain knowledge) — **HALT** (G5-grain gate)
- Intent override field fails validation (e.g., PK references non-existent column) — **WARNING** (falls through to standard priority chain)
