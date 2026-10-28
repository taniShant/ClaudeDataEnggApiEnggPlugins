---
description: Identify table type, load type, grain, and PK per target table
disable-model-invocation: false
---

# /identify-intent

Identify all 6 table-level intent fields using extended priority chain (0→0.5→1→1.5→2→3). **Multi-table support**: Processes each unique target table independently. Produces `session/intent_identification.json` (array, one entry per table).

## Usage

```
/identify-intent
```

## Prerequisites

- `/parse-mapping` completed (includes multi-table detection)
- `/classify-sources` completed (source table type classification)
- `session_state.target_tables[]` populated with unique tables
- `session/source_table_metadata.json` available (produced by `/classify-sources`)

## STEP 0.0 — Chain Mode Output Compression

If `session_state.auto_chain.enabled == true` (full-automation mode):
- **Suppress verbose output:** Do NOT print session_state.json content, per-table intent resolution details, priority chain traversal, or confidence scoring to conversation.
- **Audit log instead:** Write verbose progress entries to `session/audit_log.jsonl` (append-only structured logging).
- **Compact return only:** At command completion, emit ONLY:
  ```
  [{step}/{total}] ✓ /identify-intent — {N} tables resolved, {M} auto-decisions
  Checkpoint: post_intent written
  ```
- **Halt output:** If G5-grain halt or unresolved fields, emit max 5-line halt summary + write `session/intent_resolution_report.md`.

---

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-identify-intent".

---

## STEP 0.5 — Prerequisite Enforcement (HALT on missing)

**Before any processing, verify all prerequisites are satisfied:**

1. **Check `/parse-mapping` completed:**
   - Verify `session/mapping_parsed.json` exists AND `session_state.gates_resolved` contains `"G1.5"`
   - If missing → HALT:
     ```
     ⛔ HALT — Prerequisite Missing: /parse-mapping not completed.
     
     Provide mapping_parsed.json or run /parse-mapping to parse the mapping Excel and resolve data product type.
     ```

2. **Check `/classify-sources` completed:**
   - Verify `session/source_table_metadata.json` exists
   - If missing → HALT:
     ```
     ⛔ HALT — Prerequisite Missing: /classify-sources not completed.
     
     Source table type classification has not been performed. Source table type is a
     key input for intent identification (Priority 1 source for table_type).
     
     Provide source_table_metadata.json or run /classify-sources, then retry /identify-intent.
     ```

3. **Check `session_state.target_tables[]` populated:**
   - If empty or missing → HALT:
     ```
     ⛔ HALT — Prerequisite Missing: No target tables found in session state.
     
     Provide target_tables in session_state.json or run /parse-mapping to detect them from the mapping Excel.
     ```

**All three checks must pass before proceeding.** If any fails, HALT immediately — do NOT silently skip or proceed without the prerequisite data.

---

## STEP 0.1 — Load Intent Overrides (Priority 0)

**Before any intent identification, check for user-supplied overrides:**

1. Check if `session/intent_overrides.json` exists
2. If YES:
   a. Validate against `${CLAUDE_PLUGIN_ROOT}/schemas/intent_overrides.schema.json`
   b. If invalid → WARN and skip overrides (do not halt — fall through to standard resolution)
   c. For each override entry:
      - Match `target_database` + `target_table` against `session_state.target_tables[]`
      - If no match found → WARN: `Override for {db}.{table} does not match any session target — skipping`
      - If match found → Store override fields for Priority 0 application during per-table iteration
   d. Log: `[INFO] Intent overrides loaded: {N} tables, {M} fields total`
   e. Set `session_state.intent_overrides_applied = true`
3. If NO → Continue normally (no overrides)

**Override application during per-table iteration (STEP 1):**
- For each table, BEFORE scanning Priority 1/2/3 sources:
  - Check if an override exists for this table
  - For each field specified in the override → immediately mark as resolved
  - Set `identification_source = "intent_override"` for overridden fields
  - Only UNRESOLVED fields (not in override) proceed through standard 3-source priority
  - Already-resolved fields from standard priority are NOT overridden (override only fills gaps)

**Priority order with overrides:**
```
Priority 0: intent_overrides.json (user-supplied, fills ONLY unresolved fields)
Priority 1: Mapping Document (transformation logic + target table description)
Priority 1.5: Additional Context (load_type keywords)
Priority 2: Domain Knowledge MD
Priority 3: User Prompt
```

---

## STEP 0.2 — Mapping Column Signal Extraction (Priority 0.5)

**Before standard 3-source priority, extract signals from mapping columns 13–16 (always present):**

1. Read `mapping_parsed.json` for `target_table_type` and `key_column` fields (always populated — columns are required).
2. If `target_table_type` is non-null:
   - Read `mapping_parsed.json` → `target_table_type` field (table-level, CamelCase canonical value)
   - Identity map (CamelCase values pass through directly): `"NonTransactional_SCD2"` → `table_type = "NonTransactional_SCD2"`, `"NonTransactional_SCD1"` → `table_type = "NonTransactional_SCD1"`, `"Transactional"` → `table_type = "Transactional"`
   - Legacy fallback (backward compatibility with pre-CamelCase mappings): `"scd2"` → `table_type = "NonTransactional_SCD2"`, `"scd1"` → `table_type = "NonTransactional_SCD1"`, `"transactional"` → `table_type = "Transactional"`
   - If matched → mark `table_type` as RESOLVED at Priority 0.5, confidence: HIGH
   - Set `identification_source = "mapping_column"` for this field
   - Additionally for NonTransactional_SCD1: set `eff_date_source = "none"`, `partition_key_columns = ["dw_lod_tmp"]` (no effective dates in SCD1, no active column)
   - Additionally for NonTransactional_SCD2: check if `eff_start_date` column exists in target columns → set `eff_date_source = "explicit"`; otherwise leave for Priority 1; set `partition_key_columns = ["active"]`
3. If `"Key Column"` present:
   - Collect all columns in `mapping_parsed.json` where `key_column = true`
   - If at least one column found → set `primary_key_columns = [collected columns]`, RESOLVED at Priority 0.5
   - Set `identification_source = "mapping_column"` for this field

4. Check `mapping_parsed.json` → `cdc_type_hint` field (table-level, extracted from Additional Context):
   - If `cdc_type_hint == "snapshot"` → set `snapshot_mode = true`, RESOLVED at Priority 0.5
   - If `cdc_type_hint == "delta"` → set `snapshot_mode = false`, RESOLVED at Priority 0.5
   - If `cdc_type_hint == null` → leave unresolved (fallback to domain knowledge at Priority 1 or default at Priority 2)
   - Set `identification_source = "additional_context"` for this field

5. Check `mapping_parsed.json` → `partition_key_hint` field (table-level, extracted from Additional Context):
   - If `partition_key_hint` is non-null and non-empty array:
     - Validate each column exists in `mapping_parsed.json → columns[].target_column_name`. Discard invalid entries with WARNING.
     - If at least one valid column remains → set `partition_key_columns = partition_key_hint` (validated), RESOLVED at Priority 1.5
     - Set `identification_source = "additional_context"` for this field
   - If `partition_key_hint == null` or all entries invalid → leave unresolved (fallback to domain knowledge at Priority 2 or heuristic/user at Priority 3)

6. Fields resolved by Priority 0.5 / Priority 1.5 are EXCLUDED from standard lower-priority scanning
7. Remaining unresolved fields proceed through Priority 1 → Priority 1.5 → Priority 2 → Priority 3

**`snapshot_mode` fallback resolution (if not resolved at Priority 0.5):**
- **Priority 1 — Domain Knowledge**: If domain knowledge contains `CDC type: full_snapshot` for this table → `snapshot_mode = true`. If `CDC type: delta` or `CDC type: key_without_indicator` → `snapshot_mode = false`.
- **Priority 2 — Default**: `snapshot_mode = false` (delta mode — safe default; absence from source = unchanged)

**Log:**
```
[INTENT] Priority 0.5 — table_type for {db}.{table}: "NonTransactional_SCD2" (source: mapping_column, raw: "NonTransactional_SCD2")
[INTENT] Priority 0.5 — primary_key_columns for {db}.{table}: ["account_id", "source_system_key"] (source: mapping_column, Key Column=Y count: 2)
[INTENT] Priority 0.5 — snapshot_mode for {db}.{table}: true (source: additional_context, cdc_type_hint: "snapshot")
[INTENT] Priority 1.5 — partition_key_columns for {db}.{table}: ["active"] (source: additional_context, partition_key_hint)
```

---

## STEP 0.3 — Scope Domain Knowledge to Target Table (Context Efficiency)

Before passing domain knowledge to the intent-identifier-agent, scope it to only the relevant sections for EACH target table. This prevents loading the full domain knowledge file (which can be 1,000+ lines for large domains like fdpukloans) into the agent's context.

**Algorithm:**

1. If `session_state.domain_knowledge_text` is NULL or empty → skip (pass `null` to agent)
2. Parse domain knowledge MD for heading-level sections (`### ` headings)
3. For each target table, extract ONLY:
   a. Sections whose heading matches `target_table_name` or `target_database` (case-insensitive)
   b. "SCD2 / CDC Configuration" section (always included — shared config relevant to table_type/load_type)
   c. "Source System Quirks" entries for source databases in THIS table's `source_tables`
   d. Any section explicitly tagged with `applies_to: all` or `applies_to: {this_table}`
   e. "Load Type" or "Partition" sections (intent-relevant shared config)
4. Pass `scoped_domain_knowledge` (typically 50–150 lines) to the agent per table
5. If no matching sections found → pass `"No specific domain knowledge for this table"`

**Savings:** 80–95% reduction for large domains (e.g., fdpukloans: 8.5K → 1K tokens per table).

**Log:**
```
[INTENT] STEP 0.3 — Domain knowledge scoped for {db}.{table}: {scoped_lines} lines (original: {total_lines} lines, reduction: {pct}%)
```

---

## Resume Logic (A2 Feature)

**Before running the intent-identifier agent:**

1. Load `session/session_state.json`
2. Check `session.phases["identify_intent"].status`:
   - **If "completed"** → Skip agent; load cached result from `session.phases["identify_intent"].cached_result` → return `intent_identification.json`
   - **If "in_progress"** → Resume from pending intent tables; re-invoke agent for unresolved tables only
   - **If "pending"** → Run agent normally for all tables

3. **On entry:**
   - Set `session.phases["identify_intent"].status = "in_progress"`
   - Set `session.phases["identify_intent"].started_at = now()`
   - Save session state

4. **On completion:**
   - Set `session.phases["identify_intent"].status = "completed"`
   - Set `session.phases["identify_intent"].completed_at = now()`
   - Cache result: `session.phases["identify_intent"].cached_result = intent_identification.json`
   - Save session state

5. **On error:**
   - Set `session.phases["identify_intent"].status = "failed"`
   - Set `session.phases["identify_intent"].error = error_message`
   - Save session state; propagate error

## Mapping Input Projection (Context Efficiency)

When passing `mapping_parsed.json` data to the `intent-identifier-agent`, include ONLY these fields per target table:

**Include:**
- `target_table`, `target_database`
- `columns[].name`, `columns[].type` (for audit column pattern detection — SCD2 vs Transactional)
- `transformation_logic` (for load_type keyword scanning: MERGE, INSERT, APPEND, OVERWRITE)
- `additional_context` (for Priority 1.5 keywords: "Day0", "BAU", "daily", "one-time")
- `source_tables[].database`, `source_tables[].table` (for source_table_type cross-reference with `source_table_metadata.json`)
- `table_description` (for grain hints and purpose context)

**Omit:**
- `columns[].description` (not used for intent identification)
- `columns[].source_column` (detailed source mapping not needed)
- `columns[].business_logic` (per-column rules not needed at intent level)
- Full source column schemas (not needed for intent identification)
- `columns[].nullable`, `columns[].default_value` (not intent-relevant)

**Savings:** ~50–60% mapping context reduction (6.5K → 2.5K tokens typical). Intent identification only needs structural signals (column names/types for audit pattern detection) and text signals (transformation_logic keywords), not full column-level mapping detail.

---

## Intent Fields & Resolution Logic

> **Authoritative source:** `intent-identifier-agent.md` defines the 6 intent fields, 3-source priority chain (Priorities 0–3), signal tables, heuristics (H0–H5), and constraint rules (no default for table_type, no naming heuristic for PK). Do NOT duplicate here.

**Priority chain summary:**
```
Priority 0:   intent_overrides.json (user-supplied fills)
Priority 0.5: Mapping column signals (Target Table Type, Key Column) — see STEP 0.2 above
Priority 1:   Mapping document (transformation logic text scanning)
Priority 1.5: Additional Context (load_type keywords)
Priority 2:   Domain Knowledge MD
Priority 3:   User Prompt
```

## Multi-Table Iteration

For each table in `session_state.target_tables[]`:
1. **Scan** — Apply priority chain to extract 6 intent fields
2. **Check** — If ALL resolved → `intent_resolved = true`, append to output. Else → mark pending.
3. **After all** — If pending tables exist → raise G5-grain HALT. Else → ready for generation.

### G5-grain — HALT If Ambiguous (Zero-Prompt Architecture)

**NO USER PROMPT** — Instead HALT with clear action message.

Triggered **only** when:
- 3-source priority fails to resolve ANY field for table
- Auto-decision rules applied but yield LOW confidence or UNRESOLVED field
- Structural analysis (audit columns) inconclusive
- Transformation logic signals inconclusive
- 7-rule framework cannot definitively resolve field

**HALT Behavior (All Modes — Single and Multi-Table)**:

For each table with unresolved or low-confidence intent:

```
⛔ HALT — G5-grain: Intent Ambiguity (Cannot Auto-Decide)

TABLE: {target_database}.{target_table}
Fields with LOW confidence or UNRESOLVED: {field_list}

Analysis Summary:
  - Audit columns (structural): {H0/H0b result}
  - Transformation logic signals: {found or "none"}
  - Domain knowledge: {provided or "not found"}
  - 7-rule framework: {rule result}

REQUIRED ACTION (Choose One):

Option A — Add Audit Columns:
  For SCD2: eff_start_date, eff_end_date, active, dw_upd_lod_tmp
  For Transactional: dw_bus_dt, dw_lod_tmp

Option B — Add Transformation Logic Signals:
  For SCD2: "MERGE INTO table ON key_cols"
  For Transactional: "INSERT INTO ... SELECT ... GROUP BY"

Option C — Provide Domain Knowledge:
  Create: ${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/{feature_team_name}_knowledge.md
  (Look up Feature Team Name:
    - If platform = Glue → `tenancy` skill Tenancy Registry (match Hive/Iceberg Database column)
    - If platform = Databricks → `databricks-tenancy` skill Tenancy Infrastructure Registry (match Target DB column))
  Include: grain, primary_key, table_type, partition, load_type

NEXT STEPS:
  1. Update mapping Excel or create domain knowledge file
  2. Re-run: /parse-mapping
  3. Re-run: /identify-intent
```

**Multi-Table Notes:**
- If multiple tables have unresolved intent, HALT after first table with full message
- User must fix ALL tables at once (update mapping once; re-run)
- Upon re-run, resume processing from first unresolved table

---

### STEP-REPORT — Intent Resolution Report (Full-Automation Mode Only)

**When:** G5-grain HALT occurs AND `session_state.auto_chain.enabled == true`

**Action:** Generate `session/intent_resolution_report.md` containing per-field analysis.

**Report Structure:**

```markdown
# Intent Resolution Report

Generated: {ISO 8601 timestamp}
Session: {session_id}
Status: HALTED — Missing intent fields

## Unresolved Tables

### 1. {target_database}.{target_table}

| Field | Status | Attempted Sources | Why It Failed |
|-------|--------|-------------------|---------------|
| {field_name} | UNRESOLVED | {sources checked} | {specific reason} |
| {field_name} | RESOLVED (HIGH) | {source that resolved} | — |
| ... | ... | ... | ... |

## How to Fix

**Option 1 (Recommended): Create intent_overrides.json**

Create `session/intent_overrides.json` with the missing values:

{pre-filled JSON template with target_database, target_table, and placeholders for unresolved fields}

Then run: `/resume`

**Option 2: Update mapping Excel**

Add to "Business Logic/Transformation Logic" column:
{specific signals needed based on which fields are missing}

Then run: `/resume --reparse`

**Option 3: Provide domain knowledge**

Create: `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/{feature_team_name}_knowledge.md`
Include:
{specific sections needed for unresolved fields}

Then run: `/resume --reparse`
```

**Per-field "Why It Failed" — populate from auto-decision-agent analysis:**

| Field | Checked Sources | Example Failure Reason |
|-------|----------------|----------------------|
| `primary_key_columns` | mapping (MERGE ON), domain_knowledge, auto-decision | "No MERGE ON pattern in transformation logic; no domain knowledge file found" |
| `partition_key_columns` | mapping (partition signal), domain_knowledge, structural (audit cols) | "No partition column derivable; no SCD2 or transactional audit columns in target schema" |
| `table_type` | structural (H0/H0b), mapping signals, domain_knowledge | "Ambiguous — no SCD2 or transactional audit columns; conflicting name patterns" |
| `load_type` | mapping keywords, additional_context, domain_knowledge | "No Day0/BAU keywords in transformation logic or additional context" |
| `eff_date_source` | mapping (eff_start_date col), domain_knowledge | "NonTransactional but no eff_start_date column found in target schema" |
| `protegrity_de_mappings` | crypto_flags.json | "Crypto signal found but DE name extraction failed (regex no match)" |

**Pre-filled override template (Option 1):**
- Include only fields that are UNRESOLVED for each table
- Use placeholder comments to guide user:
  ```json
  {
    "overrides": [
      {
        "target_database": "fdp_uk_mortgage_db",
        "target_table": "account_wm",
        "primary_key_columns": ["<column_name>", "<column_name>"],
        "partition_key_columns": ["active"]
      }
    ]
  }
  ```
- For `partition_key_columns`: suggest `["active"]` for NonTransactional_SCD2, `["dw_lod_tmp"]` for NonTransactional_SCD1, `["dw_bus_dt"]` for Transactional (if table_type already resolved)
- For `table_type`: include comment explaining the two options

**Report file saved to:** `session/intent_resolution_report.md`
**Session state updated:** `auto_chain.report_generated = "session/intent_resolution_report.md"`

## Behaviour

### Single-Table Scenario
Invoke `intent-identifier` agent (using the Agent tool) to resolve all 6 intent fields using 3-source priority for the single table.

### Multi-Table Scenario (NEW)
When session_state.total_target_tables > 1:

1. **For each table** in session_state.target_tables:
   - Invoke intent-identifier agent (using the Agent tool) scoped to that table only
   - Scan transformation_logic rows for THAT TABLE ONLY
   - Apply 3-source priority
   - Mark intent_resolved=true/false

2. **Collect unresolved tables**:
   - If any table has unresolved or LOW-confidence intent → add to session_state.pending_intent_tables
   - Update session_state.target_tables[i].intent_resolved=false for those tables

3. **Check for ambiguity**:
   - ✅ If ALL tables HIGH/MEDIUM confidence: Generate output (STEP 4)
   - ⛔ If ANY table LOW confidence or UNRESOLVED: HALT with G5-grain message
     - User must fix mapping Excel or provide domain knowledge
     - User re-runs /identify-intent
     - Upon retry: Resume from first unresolved table

4. **Generate output** (if all tables resolved):
   - Array of intent records (one per unique target table)
   - Order matches session_state.target_tables order

---

## Output

Write `session/intent_identification.json` conforming to `${CLAUDE_PLUGIN_ROOT}/schemas/intent_identification.schema.json`.

**Output Format**:
- **Single table**: Array with 1 object
- **Multiple tables**: Array with N objects (one per unique target table)

Include `identification_source` per table: 
- `intent_override` if Priority 0 (intent_overrides.json) resolved the majority of fields
- `mapping_column` if Priority 0.5 (Target Table Type / Key Column) resolved the majority of fields
- `transformation_logic` if Priority 1 resolved all fields
- `additional_context` if Priority 1.5 resolved load_type from Additional Context column
- `domain_knowledge` if Priority 2 resolved remaining fields
- `user_prompt` if Priority 3 resolved remaining fields
- `user_asked` if G5-grain was required

**Example — Single table**:
```json
[
  {
    "target_database": "fdp_uk_complaints_db",
    "target_table": "complaints",
    "table_type": "NonTransactional_SCD2",
    "grain_description": "One row per complaint_id per effective period",
    "primary_key_columns": ["complaint_id"],
    "partition_key_columns": ["active"],
    "eff_date_source": "explicit",
    "load_type": "BAU",
    "identification_source": "transformation_logic"
  }
]
```

**Example — SCD1 table**:
```json
[
  {
    "target_database": "fdp_uk_reference_db",
    "target_table": "country_codes",
    "table_type": "NonTransactional_SCD1",
    "grain_description": "One row per country_code",
    "primary_key_columns": ["country_code"],
    "partition_key_columns": ["dw_lod_tmp"],
    "eff_date_source": "none",
    "load_type": "full_then_incremental",
    "identification_source": "mapping_column"
  }
]
```

**Example — Two tables**:
```json
[
  {
    "target_database": "fdp_uk_complaints_db",
    "target_table": "complaints",
    "table_type": "NonTransactional_SCD2",
    "grain_description": "One row per complaint_id per effective period",
    "primary_key_columns": ["complaint_id"],
    "partition_key_columns": ["active"],
    "eff_date_source": "explicit",
    "load_type": "BAU",
    "identification_source": "transformation_logic"
  },
  {
    "target_database": "fdp_uk_complaints_db",
    "target_table": "complaint_activity",
    "table_type": "Transactional",
    "grain_description": "One row per activity_id",
    "primary_key_columns": ["activity_id"],
    "partition_key_columns": ["dw_bus_dt"],
    "eff_date_source": "none",
    "load_type": "BAU",
    "identification_source": "user_asked"
  }
]
```

### Context Checkpoint Write (Full-Automation Only)

If `session_state.auto_chain.enabled == true`, write `chain_checkpoints.post_intent` to `session/session_state.json`:

```json
{
  "chain_checkpoints": {
    "post_intent": {
      "per_table_summary": [
        {
          "target_database": "<db>",
          "target_table": "<table>",
          "table_type": "NonTransactional_SCD1|NonTransactional_SCD2|Transactional",
          "load_type": "Day0|BAU|full_then_incremental",
          "grain": "<grain_description>",
          "primary_key_columns": ["<col>"],
          "identification_source": "<source>"
        }
      ],
      "all_resolved": true/false,
      "timestamp": "<ISO 8601>"
    }
  }
}
```

## Output Files

- `session/intent_identification.json`
- `session/audit_log.jsonl` (new entry)

---

## load_type Resolution Audit Trail

After intent resolution completes for each table, log a structured entry showing which source resolved `load_type` and whether any override occurred:

**Console output** (always shown):
```
[INTENT] load_type for {db}.{table}: "{resolved_value}" (source: {identification_source})
```

**When Additional Context overrides Priority 1**:
```
[INTENT] load_type for {db}.{table}: "Day0" (source: additional_context, overrode Priority 1: "BAU")
```

**When both Day0 and BAU keywords found (no negation) → full_then_incremental**:
```
[INTENT] load_type for {db}.{table}: "full_then_incremental" (source: additional_context, both Day0+BAU keywords present)
```

**Audit log entry** (append to `session/audit_log.jsonl`):
```json
{
  "timestamp": "...",
  "event": "intent_load_type_resolved",
  "target_database": "{db}",
  "target_table": "{table}",
  "resolved_value": "Day0",
  "identification_source": "additional_context",
  "priority_1_value": "BAU",
  "override_occurred": true,
  "additional_context_keywords_matched": ["Day 0"]
}
```

This audit trail enables debugging when load_type resolution produces unexpected results.
