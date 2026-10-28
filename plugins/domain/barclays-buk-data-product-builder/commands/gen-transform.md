---
description: Generate PySpark transformation scripts per target table
disable-model-invocation: false
---

# /gen-transform — Per-Target-Table Transformation Generation

Generate PySpark transformation scripts for **EACH TARGET TABLE** independently. NOT per-source-table.
- Produces conditional transform files ({{db}}_{{target_table}}_transform_day0.py and/or {{db}}_{{target_table}}_transform_day1.py for Glue)
- NOT per-source-table files
- Conditional generation driven by intent_identifier load_type per target table
- Support for multi-step transformation logic (joins, filters, aggregations, derivations)

## Output

> File naming, conditional generation rules, and class structure: see `transform-generator-agent.md` "Outputs" section (authoritative).

Create directory `generated/glue/transforms/` (Glue) or `generated/databricks/src/Notebooks/{day0|day1}/{target_schema}_{table}/` (Databricks) if it does not exist.
When `data_flow_detection.source_systems` is non-empty (multi-source-system): create `generated/databricks/src/Notebooks/{day0|day1}/{source_system}/{target_schema}_{table}/` instead (Databricks). Glue uses filename suffix only — no additional directories.

Multi-source-system (when `data_flow_detection.source_systems` is non-empty — one transform per source_system, see STEP 0.1):
- Databricks: `generated/databricks/src/Notebooks/{day0|day1}/{source_system}/{target_schema}_{table}/{target_schema}_{table}_transform.py`
- Glue: `generated/glue/transforms/{db}_{table}_{source_system}_transform_{day}.py`

## Usage

```
/gen-transform
```

## Prerequisites

- `session/mapping_parsed.json` exists
- `session/source_table_metadata.json` exists
- `session/intent_identification.json` exists
- `session/crypto_flags.json` exists
- No `extraction_failed: true` crypto columns (those are refused)

**target_schema** (Databricks): = `mapping_parsed.json → target_database` (exact value, no prefix/suffix stripping). Used for class naming: `{target_schema}_{table}_transform`. See `/gen-config` STEP 0.6.

## STEP 0.0 — Chain Mode Output Compression

Apply `commands/refs/chain-mode-compression.md` pattern. Compact return: `[{step}/{total}] ✓ /gen-transform — {N} tables, {M} files ({day0_count} day0, {day1_count} day1) | Checkpoint: post_generation updated`

## STEP 0 — Logging Initialization

Apply `conventions` skill logging pattern, component="de-gen-transform".

---

## STEP 0.1 — Multi-Source-System Awareness

Read `session_state.data_flow_detection`:

- **`source_systems` is non-empty** (i.e., `data_flow_detection.source_systems[]` has 1 or more entries — even a single entry like `["trmph"]` qualifies): This target uses source-system-scoped artifacts. Execute STEPS 1+ in a **loop over source_systems** in `session_state.data_flow_detection.source_systems[]`. For each source_system:
  - Filter manifest path: `session/generated_configs/{schema_or_db}_{table}_{source_system}_filters.json`
  - Source column allowlist: only columns from this source_system's tables (from the per-source-system filter manifest)
  - Locked predicates: only predicates relevant to this source_system
  - Output paths:
    - Databricks: `generated/databricks/src/Notebooks/{day}/{source_system}/{schema}_{table}/{schema}_{table}_transform.py`
    - Glue: `generated/glue/transforms/{db}_{table}_{source_system}_transform_{day}.py`
  - Transform class naming:
    - Databricks: `{schema}_{table}_transform` (same — class is scoped by directory)
    - Glue: `{db}_{table}_{source_system}_transform_{day}`
  - Template variable: `utilities_run_prefix = "../../.."` (3 levels up: `{schema}_{table}/` → `{source_system}/` → `{day}/` → `Notebooks/`)
  - The agent generates a simpler transform (no UNION logic — it's one flow per source_system)

- **`artifact_mode == "combined"`**: Single invocation with all source tables (UNION scenario). Output paths same as default flow. Transform uses `unionByName()` for multi-source merge. Template variable: `utilities_run_prefix = "../.."` (2 levels up: `{schema}_{table}/` → `{day}/` → `Notebooks/`).

- **Otherwise** (`source_systems` is empty and `artifact_mode != "combined"`): Standard single-flow generation (unchanged from today's behavior). Template variable: `utilities_run_prefix = "../.."` (2 levels up: `{schema}_{table}/` → `{day}/` → `Notebooks/`).

---

## STEP 0.12 — Chain Checkpoint Loading (Full-Automation Only)

If `session_state.auto_chain.enabled == true`, load `session_state.chain_checkpoints.post_intent` for reliable context recovery. This provides per-table intent summary (table_type, load_type, grain, PK, partition) that survives context compaction — use as source of truth for prior-phase decisions instead of conversation history.

---

## STEP 0.2 — Config Prerequisite Check

Check for the filter manifest file at `session/generated_configs/{target_schema}_{table}_filters.json` for the current target table.

**If the file exists**: Continue — config has been generated.

**If the file does NOT exist**:
⛔ **HALT** — Config generation is a prerequisite for transform generation.

Display:
```
⛔ Transform generation blocked — filter manifest not found for {table}.
Config must be generated before transforms to ensure:
1. SourceReader filter suppression (transforms won't duplicate config-declared filters)
2. Class naming consistency (wrapper/driver expect matching names)

Run `/gen-config` first, then re-run `/gen-transform`.
```

Do NOT continue with transform generation. This is a safety gate — generating transforms without config produces silently incorrect output.

---

## STEP 0.2b — File I/O Awareness (Conditional)

**Pre-condition:** `session_state.io_mode` ∈ {`file`, `hybrid`}. If `io_mode` is `table` (default) or absent → skip this step entirely.

When file I/O is active, prepare additional context for the transform-generator-agent:

### Inputs Read

1. `session_state.io_mode` — `file` (all sources/targets are file-based) or `hybrid` (mix of table and file)
2. `session_state.source_io` — file source declarations (aliases, paths, columns)
3. `session_state.target_io` — file target declaration (write_mode, partition_by, compression)
4. Filter manifest (`session/generated_configs/{target_schema}_{table}_filters.json`) — `file_sources` block identifies which source aliases are file-based

### Source Column Allowlist Extension

The source column allowlist constructed in STEP 0.4 is extended to include file source columns. File sources from `session_state.source_io.sources[]` contribute their column lists to `source_columns` in `session/source_column_allowlist.json` identically to table sources. No separate handling is needed — STEP 0.4's algorithm already iterates all `source_references[]` regardless of source type.

### Transform Code Generation Guidance

When passing context to the transform-generator-agent, include file I/O awareness:

- For each file source alias (identified via `file_sources` in the filter manifest), the agent emits a comment in the generated transform:
  ```python
  # SourceReader reads parquet from config source.file entry — not duplicated here
  ```
- When `target_io` is present in config, the agent does NOT generate `spark.table()` calls for the target or call any `tableIOUtils` methods — TargetWriter handles file write dispatch automatically via `write()`.
- Source access remains via `self.source_data[alias]` for all sources (file and table alike).

### Context Injection

Inject into agent prompt AFTER source column allowlist block:

```
═══ FILE I/O CONTEXT ═══
io_mode: {io_mode}
file_sources: {file_source_aliases or "none"}
target_io: {present|absent}
NOTE: File sources are in self.source_data[alias] — access identically to table sources.
NOTE: If target_io present, writer.write(df) handles parquet dispatch — no spark.table() for target.
═══ END FILE I/O CONTEXT ═══
```

**Logging**: `"[STEP 0.2b] File I/O awareness — io_mode: {io_mode}, file_sources: {count}, target_io: {present|absent}"`

---

## STEP 0.3 — Scope Domain Knowledge to Target Table

Before passing domain knowledge to the transform-generator-agent, scope it to only the relevant sections for THIS target table. This prevents loading the full domain knowledge file (which can be 1,000+ lines for large domains like fdpukloans) into the agent's context.

**Algorithm:**

1. If `domain_knowledge_text` is NULL or empty → skip (pass `null` to agent)
2. Parse domain knowledge MD for heading-level sections (`### ` headings)
3. Extract ONLY:
   a. Sections whose heading matches `target_table_name` or `target_database` (case-insensitive)
   b. "SCD2 / CDC Configuration" section (included ONLY if `table_type == "NonTransactional_SCD2"` — skip for SCD1 and Transactional)
   c. "Source System Quirks" entries for source databases in THIS table's `source_tables`
   d. Any section explicitly tagged with `applies_to: all` or `applies_to: {this_table}`
4. Pass `scoped_domain_knowledge` (typically 50–150 lines) to the agent
5. If no matching sections found → pass `"No specific domain knowledge for this table"`
6. **Hard cap enforcement:** If `scoped_domain_knowledge` after extraction exceeds 2,000 tokens (~8,000 characters), truncate to the first 2,000 tokens and append:
   ```
   ═══ DOMAIN KNOWLEDGE TRUNCATED — full content in domain_knowledge file ═══
   If needed details were cut, re-read the full file: {domain_knowledge_path}
   ═══
   ```
   This prevents poorly-structured domain knowledge files (missing per-table headings) from injecting 12,500+ tokens into the agent context.

**Savings:** 80–95% reduction for large domains (e.g., fdpukloans: 8.5K → 1K tokens). Hard cap guarantees ≤2,000 tokens regardless of scoping success.

---

## STEP 0.4 — Source Column Allow-List Construction

For the current target table, extract the complete set of allowed source columns from `session/mapping_parsed.json` and structure as a machine-readable constraint block. This is the primary prevention layer against column hallucination.

### Algorithm:

1. From this target table's `column_mappings[]`, collect ALL `source_references[]` entries
2. Group by source table alias (the table name used in config, e.g., "customer_response")
3. Deduplicate column names per alias → sort alphabetically
3.5. **Augment with infrastructure columns**: From `extracted_join_predicates[]` (confidence `"high"` or `"medium"`), add `left_col`/`right_col` to their respective alias column sets. From `extracted_literals[]` (confidence `"high"` or `"medium"`, context `"filter_predicate"` or `"case_when_condition"`), add the `column` to the alias that owns it. This ensures the allowlist permits join-key and filter-column references that don't appear in `source_references`. If `extracted_join_predicates` / `extracted_literals` are null (old mapping), skip — no regression.
4. Also collect all `target_column_name` values → sorted list (for output validation)
5. Write the result to `session/source_column_allowlist.json` (persistent — survives context compaction)

### Output file: `session/source_column_allowlist.json`

```json
{
  "target_table": "customer_survey_wm",
  "source_columns": {
    "customer_response": ["active", "customer_response_date", "customer_response_value_1", "customer_response_value_2", "customer_response_value_3", "customer_survey_id", "customer_survey_sent_date", "question_id", "source_system_key"],
    "question": ["active", "nps_question_indicator", "question_description", "question_id", "question_name"]
  },
  "target_columns": ["question_id", "question_name", "response_date", "response_value", "survey_response_id"],
  "audit_columns": ["eff_start_date", "eff_end_date", "active", "dw_lod_tmp", "dw_upd_lod_tmp"]
}
```

### Audit column allowlist by table_type:

> **Audit columns per table type:** See `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`

Select the correct `audit_columns` set based on `table_type` from `session/intent_identification.json` for the current target table. The JSON example above shows the `NonTransactional_SCD2` case.

### Injection into agent prompt (structured constraint block):

Inject this BEFORE the column_mappings context (so the constraint is established before the agent encounters free-text transformation_logic):

```
═══ STRICT SOURCE COLUMN CONSTRAINTS (runtime error if violated) ═══
customer_response ALLOWS ONLY: active, customer_response_date, customer_response_value_1, customer_response_value_2, customer_response_value_3, customer_survey_id, customer_survey_sent_date, question_id, source_system_key
question ALLOWS ONLY: active, nps_question_indicator, question_description, question_id, question_name
═══ TARGET COLUMNS (final SELECT must produce exactly these + audit cols) ═══
TARGET TABLE ALLOWS ONLY: question_id, question_name, response_date, response_value, survey_response_id
AUDIT COLUMNS (auto-added): eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp
═══ ANY F.col("x") NOT IN THE LISTS ABOVE = GENERATION FAILURE ═══
Intermediate processing columns (withColumn, alias, agg outputs) are PERMITTED — only SOURCE READS are constrained.
If context compaction occurs, re-read session/source_column_allowlist.json before generating code.
```

### Compaction resilience:

- The allow-list is written to disk (`session/source_column_allowlist.json`) — survives context compaction
- The constraint block appears at the START of the agent prompt (before column_mappings)
- A REPEAT reminder is appended at the END of the agent prompt:
  ```
  ═══ REPEAT: Source columns are STRICTLY limited to the allowlist above. Re-read session/source_column_allowlist.json if uncertain. ═══
  ```

### Per-table isolation:

In batch mode, STEP 0.4 runs **per-table** — each table gets its own allowlist derived fresh from mapping_parsed.json. Tables do NOT share allowlists (prevents cross-table column leakage).

---

## STEP 0.41 — Join Predicate & Literal Value Constraint Construction

For the current target table, collect extracted join predicates and literal values from `session/mapping_parsed.json` and format as a machine-readable LOCKED constraint block. This prevents the transform-generator-agent from inferring symmetric join keys or substituting literal values.

### Pre-condition:
- `session/mapping_parsed.json` exists and has been parsed with STEP 2.8 (fields may be null for old sessions — graceful skip)

### Algorithm:

1. From this target table's `column_mappings[]`, collect ALL `extracted_join_predicates[]` entries (skip null)
2. From this target table's `column_mappings[]`, collect ALL `extracted_literals[]` entries (skip null)
3. **Filter**: Only include entries where `confidence` is `"high"` or `"medium"` (low confidence = advisory only)
4. **Deduplicate join predicates**: Same `(left_table, left_col, operator, right_table, right_col)` appearing across multiple columns → keep one entry, note all target columns that reference it
5. **Deduplicate literals**: Same `(column, operator, value)` → keep one entry
6. If ZERO predicates AND ZERO literals after filtering → skip constraint injection. Set `session_state.locked_predicates_count = 0`. CONTINUE to STEP 0.45.
7. Write result to `session/extracted_predicates.json` (persistent — survives context compaction)

### Output file: `session/extracted_predicates.json`

```json
{
  "target_table": "customer_survey_wm",
  "join_predicates": [
    {
      "target_columns": ["survey_response_id", "nps_response_value"],
      "left_table": "customer_response",
      "left_col": "customer_survey_id",
      "operator": "=",
      "right_table": "wm_append_data",
      "right_col": "unique_survey_ref",
      "source_text": "customer_response.customer_survey_id = wm_append_data.unique_survey_ref",
      "confidence": "high"
    }
  ],
  "literals": [
    {
      "target_column": "nps_response_value",
      "column": "nps_question_indicator",
      "operator": "=",
      "value": "Y",
      "source_text": "nps_question_indicator='Y'",
      "context": "filter_predicate",
      "confidence": "high"
    }
  ]
}
```

### Injection into agent prompt (structured constraint block):

Inject this AFTER the source column allow-list block, BEFORE column_mappings context:

```
═══ LOCKED JOIN PREDICATES (semantic relationship fixed — no column substitution) ═══
JOIN 1: customer_response.customer_survey_id = wm_append_data.unique_survey_ref
  Source: "customer_response.customer_survey_id = wm_append_data.unique_survey_ref"
  Used by: survey_response_id, nps_response_value
  ⛔ Both sides are LOCKED. Do NOT swap column names. Do NOT assume symmetric keys.
JOIN 2: customer_response.question_id = question.question_id
  Source: "customer_response.question_id = question.question_id"
  Used by: question_id, question_name
  ⛔ Both sides are LOCKED.
═══ LOCKED LITERAL VALUES (mapping-extracted — no value substitution) ═══
LITERAL 1: nps_question_indicator = 'Y' (context: filter_predicate, target col: "nps_response_value")
  Source: "nps_question_indicator='Y'"
  ⛔ Value 'Y' is LOCKED. Do NOT substitute 'V', 'Yes', 'N', or any other value.
LITERAL 2: status NOT IN ('CLO', 'RED', 'WOF') (context: filter_predicate, target col: "account_status")
  Source: "status NOT IN ('CLO','RED','WOF')"
  ⛔ Values ['CLO', 'RED', 'WOF'] are LOCKED.
═══ ANY GENERATED CODE THAT DEVIATES FROM LOCKED VALUES ABOVE = GENERATION FAILURE ═══
Join predicates: left_table.left_col MUST join to right_table.right_col EXACTLY as stated.
Literal values: comparison/assignment values MUST use the LOCKED value, not an inferred alternative.
If context compaction occurs, re-read session/extracted_predicates.json before generating code.
═══ END LOCKED CONSTRAINTS ═══
```

### Compaction resilience:

- Written to disk (`session/extracted_predicates.json`) — survives context compaction
- Constraint block at START of agent prompt (before column_mappings)
- REPEAT reminder appended at END of agent prompt:
  ```
  ═══ REPEAT: Join predicates and literal values are LOCKED — re-read session/extracted_predicates.json if uncertain. ═══
  ```

### Graceful degradation (backward compatibility):

- If `extracted_join_predicates` and `extracted_literals` fields are absent from `mapping_parsed.json` (old session, parsed before STEP 2.8 existed) → skip this step entirely. Log: `"[STEP 0.41] Skipped — no extracted predicates in mapping (parsed before STEP 2.8). Existing soft rules apply."`
- Transform generation proceeds normally using existing anti-hallucination rules (no regression)

### Per-table isolation:

In batch mode, STEP 0.41 runs **per-table** — each table gets its own `extracted_predicates.json` derived fresh. Tables do NOT share locked predicates.

### State tracking:

Set `session_state.locked_predicates_count = {N}` (number of join predicates locked)
Set `session_state.locked_literals_count = {M}` (number of literal values locked)

---

## STEP 0.45 — Day0 Reference Context for BAU-Only Generation

When `load_type='BAU'` (Day1 only), the transform-generator-agent generates Day1 without a Day0 companion in the same turn. This creates risk of dropping conditional business logic that would normally be present in both files.

### Pre-condition
- `load_type == 'BAU'` for this target table

### Algorithm:

1. Determine Day0 file path based on platform:
   - Glue: `generated/glue/transforms/{db}_{target_table}_transform_day0.py`
   - Databricks: `generated/databricks/src/Notebooks/day0/{target_schema}_{table}/{target_schema}_{table}_transform.py`

2. If the Day0 file exists:
   a. Read the file
   b. Extract the `transformation()` method body (between `def transformation` and `# END GENERATED TRANSFORMATION`)
   c. Inject into agent context as `day0_reference_logic`:
      ```
      ═══ DAY0 REFERENCE (business logic MUST be preserved in Day1) ═══
      The following transformation() body was generated for Day0.
      Day1 business logic (joins, conditionals, column derivations, lookup joins,
      survey type resolution, WM-vs-non-WM branching) MUST be IDENTICAL.
      The ONLY permitted differences:
        (1) Date filter applied by SourceReader (not inline)
        (2) SCD2 audit columns omitted (TargetWriter injects them)
        (3) dw_lod_tmp omitted for NonTransactional_SCD2 (writer injects)
      ═══ DAY0 TRANSFORMATION BODY ═══
      {extracted_transformation_body}
      ═══ END DAY0 REFERENCE ═══
      ```

3. If the Day0 file does NOT exist:
   - Log: `[INFO] No Day0 reference found for BAU-only table {target_table} — generating from mapping context only`
   - Proceed without reference (existing behavior)

### Key properties:
- NON-BLOCKING: If Day0 file is missing, generation proceeds normally
- READ-ONLY: The Day0 file is never modified
- SCOPED: Only the transformation() body is extracted (not imports, class, prepare_sources, load)
- TRUNCATION: If extracted body exceeds 300 lines, include only first 300 with note `# [TRUNCATED — full logic in {file_path}]`

---

## STEP 0.6 — Volumetric Context Extraction (Conditional)

**Pre-condition:** `session_state.source_volumetrics_path` is not null (set by `/parse-mapping` STEP 4.5).

If `source_volumetrics_path` is null → skip this step entirely. Pass `scoped_volumetrics = null` to the agent.

### Algorithm (per target table):

1. Read `session/source_volumetrics.json` (array of `sourceVolumetric` objects)
2. From this target table's `target_table_config.source_tables[]`, collect all `(database, table)` pairs
3. Filter volumetrics entries to only those matching the current target table's source tables (case-insensitive match on `source_database` + `source_table`)
4. If no matching entries → set `scoped_volumetrics = null`; skip remainder
5. Compute aggregate metrics:
   - `total_estimated_size_gb` = sum of `estimated_size_gb` across matched entries
   - `total_daily_increment_size_gb` = sum of `daily_increment_size_gb` across matched entries
6. Classify each matched source table role:
   - Count `source_references` per alias from `column_mappings[]`
   - Alias with MOST references = `MAIN` (do NOT broadcast in transform)
   - Aliases with few references = `LOOKUP` (broadcast candidates)
   - If uncertain → default to `MAIN`

### Output: `scoped_volumetrics` constraint block

Inject into agent context AFTER the source column allowlist block:

```
═══ VOLUMETRIC CONTEXT (apply Phase 5.6 optimization rules) ═══
TOTAL_DAY0_GB: {total_estimated_size_gb}
TOTAL_DAY1_GB: {total_daily_increment_size_gb}

SOURCE TABLE VOLUMETRICS:
  {alias} ({role: MAIN|LOOKUP}): estimated_size_gb={X}, daily_increment_gb={Y}, broadcast_hint={true|false}, table_type={NT|T}, partition_key={key|null}
  {alias} ({role: LOOKUP}): estimated_size_gb={X}, daily_increment_gb={Y}, broadcast_hint={true|false}, table_type={NT|T}, partition_key={key|null}

OPTIMIZATION SIGNALS:
  broadcast_candidates: [{alias1}, {alias2}]  ← LOOKUP tables with broadcast_hint=true OR estimated_size_gb < 0.01
  repartition_needed: {true|false}            ← any source estimated_size_gb > 50
  checkpoint_activation: {true|false}         ← total_day0_gb > 50 OR total_day1_gb > 10
  coalesce_hint: {1|4|none}                   ← based on total output estimate
═══ END VOLUMETRIC CONTEXT ═══
```

### Rules:
- **Per-table scoping**: Each table gets its own `scoped_volumetrics` derived from its source tables only
- **Compaction resilience**: Written to `session/scoped_volumetrics_{target_table}.json` per table (survives context loss)
- **NON-BLOCKING**: If volumetrics file is missing or no matching entries → generation proceeds without volumetric optimizations (existing behaviour)
- **Domain knowledge override**: If domain knowledge explicitly specifies broadcast/repartition/coalesce for a table, domain knowledge takes precedence (noted in the constraint block footer)

**Staging Hint Pass-Through:**
When `mapping_parsed.json` contains `structured_transformation.steps[].staging_hint`, include it in the scoped volumetrics context passed to the transform generator agent. The agent uses it to determine whether to emit active or commented staging blocks.

---

## STEP 0.47 — Resolve Target Column Order Authority

> **SCOPE NOTE:** This step provides column ordering context ONLY. It does not alter the transformation generation logic (joins, filters, derivations, multi-source handling). The resolved order is used exclusively for the final `.select()` statement.

Determine the authoritative column ordering for the final `.select()` in the generated transform. The DDL/mesh schema is the primary authority (since the transform writes INTO that table); fall back to `mapping_parsed.json` if DDL/mesh is not yet generated.

### Algorithm (per target table):

1. **Databricks platform:**
   - Check if Iceberg DDL file exists: `generated/databricks/src/Notebooks/utilities/{target_schema}_{table}_ddl.sql`
   - If YES → parse `CREATE TABLE` statement, extract column names in declaration order (business columns + audit columns)
   - Set `target_column_order = [columns in DDL order]`

2. **Glue platform:**
   - Check if mesh JSON file exists: `generated/glue/mesh/{db}_{target_table}_mesh.json`
   - If YES → parse `fields[]` array, extract column names in array order
   - Set `target_column_order = [columns in mesh fields[] order]`

3. **Fallback (DDL/mesh not yet generated):**
   - Use `column_mappings[]` array order from `session/mapping_parsed.json` for business columns
   - Append audit columns per table_type, same order as DDL/mesh would produce (see `${CLAUDE_PLUGIN_ROOT}/agents/refs/audit-columns-by-table-type.md`)
   - Set `target_column_order = [business columns in mapping order] + [audit columns]`

### Injection into agent prompt:

Inject `target_column_order` as a structured constraint block alongside existing context:

```
═══ TARGET COLUMN ORDER (from DDL/mesh — final SELECT must match this order exactly) ═══
COLUMNS IN ORDER: account_id, customer_name, balance, status, eff_start_date, eff_end_date, active, dw_lod_tmp, dw_upd_lod_tmp
SOURCE: {Iceberg DDL | mesh JSON | mapping_parsed.json fallback}
═══ END TARGET COLUMN ORDER ═══
```

### Per-table isolation:

In batch mode, STEP 0.47 runs **per-table** — each table gets its own resolved column order.

---

## STEP 0.55 — Copy Utility Files (Databricks Only)

**Pre-condition:** `session_state.platform == "databricks"`

If platform is NOT Databricks → skip this step entirely.

Since the generated transform notebooks contain `# MAGIC %run {utilities_run_prefix}/utilities/source_reader` and `# MAGIC %run {utilities_run_prefix}/utilities/target_writer` references (where `utilities_run_prefix` is `../..` for standard or `../../..` for multi-source-system layouts), the target utility files MUST exist in the output directory. Copy them unconditionally at transform generation time so that the `%run` targets are satisfied from this point forward.

**Algorithm:**

1. Ensure directory exists: `generated/databricks/src/Notebooks/utilities/` (create if needed)
2. Copy (static — NO template rendering, NO placeholder substitution):
   - `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/source_reader.py` → `generated/databricks/src/Notebooks/utilities/source_reader.py`
   - `${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/target_writer.py` → `generated/databricks/src/Notebooks/utilities/target_writer.py`
3. Verify BOTH files exist after copy and have size > 0 bytes
4. If copy fails or verification fails → HALT with:
   ```
   ❌ STEP 0.55 FAILED — utility files not copied.
   All generated transforms reference # MAGIC %run {utilities_run_prefix}/utilities/source_reader and # MAGIC %run {utilities_run_prefix}/utilities/target_writer.
   Without these files, every transform will fail with NameError at Databricks runtime.
   Source files expected at: ${CLAUDE_PLUGIN_ROOT}/templates/databricks/generic_components/
   ```

**Idempotency:** If files already exist (e.g., from a prior `/gen-transform` or `/gen-bundle` run), overwrite unconditionally — the plugin templates are the authoritative source.

**Session state update:**
```json
{
  "utility_files_copied": true
}
```

---

## STEP 0.5 / 0.55 — Template & Utility Reading

> Handled by `transform-generator-agent.md` STEP 0.5 (templates) and Reference Files section (utilities). The agent reads templates + SourceReader/TargetWriter source conditionally per platform and load_type. Do NOT duplicate those rules here.

---

## Resume Logic (A2 Feature)

**Before running the transform-generator agent (per table):**

1. Load `session/session_state.json`
2. Check `session.phases["gen_transform"].status`:
   - **If "completed"** → Skip agent; check for already-generated files → load from cache if available
   - **If "in_progress"** → Resume: check which tables already have `{table_name}_transform_day0.py` → skip those; regenerate only missing tables
   - **If "pending"** → Run agent normally for all tables

3. **Per-table check (for resume):**
   - Check if `generated/{platform}/transforms/{db}_{table_name}_transform_day0.py` and `{db}_{table_name}_transform_day1.py` exist
   - If yes → skip; mark as cached
   - If no → regenerate

4. **On entry:**
   - Set `session.phases["gen_transform"].status = "in_progress"`
   - Set `session.phases["gen_transform"].started_at = now()`
   - Save session state

5. **On completion (all tables):**
   - Set `session.phases["gen_transform"].status = "completed"`
   - Set `session.phases["gen_transform"].completed_at = now()`
   - Cache list of generated files
   - Save session state

6. **On error:**
   - Set `session.phases["gen_transform"].status = "failed"`
   - Set `session.phases["gen_transform"].error = error_message`
   - Save session state; propagate error

## Behaviour — Multi-Table Batching (Phase B2)

**NEW**: This command now supports **multiple tables in parallel batches**.

### Multi-Table Execution Flow

- 1 table → single-table mode (backward compatible)
- N tables → batch-parallel mode: batch into groups of 3 (configurable via `session_state.batch_size`), launch parallel `transform-generator-agent` per table (fresh context each), barrier per batch, merge results
- Max concurrent: `min(16, cpu_cores - 2)`
- Each table gets FRESH agent context (no cross-table accumulation) via STEP 0.3 scoping + STEP 0.4 allowlist
- File naming uses `{db}_{table}` for uniqueness (no batch indexing)
- Per-table failure is fault-tolerant: one fails → log error, continue others

---

## Behaviour — Delegate to transform-generator-agent

Delegate to `transform-generator-agent` (using the Agent tool). All generation rules (table types, crypto, column-level, file naming, class structure, guardrails) are defined authoritatively in the agent spec — do NOT duplicate here.

**Context passed to agent (per target table):**
- `mapping_parsed.json` columns for this table (includes `transformation_type`, `default_value`, `key_column`, `structured_transformation`)
- `intent_identification.json` entry for this table
- `crypto_flags.json` relevant columns
- `scoped_domain_knowledge` (from STEP 0.3)
- `source_column_allowlist` constraint block (from STEP 0.4)
- `locked_predicates` constraint block (from STEP 0.41, if extracted predicates exist — null otherwise)
- `day0_reference_logic` (from STEP 0.45, if BAU and Day0 exists)
- `target_column_order` constraint block (from STEP 0.47 — DDL/mesh authority or mapping fallback)
- `scoped_volumetrics` constraint block (from STEP 0.6, if volumetrics available — null otherwise)
- Enrichment columns (Transformation Type, Default Value, Target Table Type, Key Column — always present)

## Placeholder Resolution

**BEFORE Generation**: If crypto enabled, check `crypto_flags.custom_de_list` completeness. If empty + crypto columns exist: ⛔ HALT.

**AFTER Generation**: Scan for `\{\{[a-z_]+\}\}` patterns. Blocking (`{{custom_de_list}}`) → error. Non-blocking (`{{placeholder_column}}`) → mark DRAFT_UNVALIDATED. See `validators/placeholder-auto-resolver.helper.md`.

---

> **Anti-hallucination rules and generation guardrails**: See `transform-generator-agent.md` "Critical Generation Rules" and Phase 2.5.

---

## Driver Generation (Multi-Source-System Mode)

> Driver generation for multi-source-system is handled by `/gen-driver` STEP 0.15. See `commands/gen-driver.md`.

---

## STEP FINAL — Syntax Validation (Non-Blocking)

After all transform files are generated, validate Python syntax using `py_compile` (stdlib — no pip dependencies).

### Pre-conditions

**Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`.
If `python_path == null`: set `syntax_check_result = "skipped_no_python"`, log to audit, CONTINUE.

### If `python_path` available:

For each generated `.py` file produced by this command (all files matching `generated/{platform}/transforms/{db}_{table}_transform_day*.py`):

Run via Bash tool:
```bash
{python_path} -m py_compile "{file_path}" 2>&1
```

**If ALL files pass (exit code 0 for each):**
```
✅ Syntax check passed ({N} files)
```
Set `session_state.syntax_check_result = "passed"`. Set `session_state.syntax_check_failures = null`.

**If ANY file fails:**
```
⚠️ Syntax errors detected (non-blocking):
   • {file_path}: {error message from py_compile}
   ...
```
Set `session_state.syntax_check_result = "failed"`. Set `session_state.syntax_check_failures = ["{file1}", "{file2}", ...]`.

Log to `session/audit_log.jsonl`: `[SYNTAX-CHECK] {result} — {N} files checked, {M} failures`.

**CRITICAL:** Syntax failures do NOT halt the generation pipeline. They are reported for awareness and enforced at `/push` time.

---

## STEP FINAL.1 — Source Column Validation + Self-Heal

After syntax validation passes, run the **source-column-existence-validator** against each generated transform file. This is the deterministic detection layer — catches any invented columns that slipped through the allow-list prevention (Layer 1).

### Pre-conditions

- Syntax check completed (STEP FINAL) — no point validating columns if file doesn't parse
- `session/mapping_parsed.json` exists
- `session/source_column_allowlist.json` exists (written by STEP 0.4)
- **Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`. If `python_path == null`: set `column_validation_result = "skipped_no_python"`, log, CONTINUE.

### Algorithm:

```
MAX_RETRIES = 2

For each generated transform file:
  1. Run validator:
     {python_path} scripts/validate_column_refs.py "{file_path}" "session/mapping_parsed.json" --target-table "{target_table}"
  
  2. If exit code 0 → PASS for this file. Continue to next file.
  
  3. If exit code 1 → violations found. Parse JSON from stdout. Enter retry loop:

     retry_count = 0
     while violations and retry_count < MAX_RETRIES:
         retry_count += 1
         
         logger.warn(f"Column violations found in {file_name} (retry {retry_count}/{MAX_RETRIES})")
         logger.warn(f"Violations: {json(violations)}")
         
         # Self-heal: invoke FRESH agent with targeted fix prompt
         Agent(
           description=f"Fix column violations: {target_table} (retry {retry_count})",
           prompt="""
               COLUMN REFERENCE VIOLATIONS DETECTED in {file_name}.
               
               The following source columns do NOT exist in the mapping document:
               {json(violations)}
               
               Read the correct source columns from: session/source_column_allowlist.json
               
               INSTRUCTIONS:
               1. Read the generated file: {file_path}
               2. Read the allowlist: session/source_column_allowlist.json
               3. For each violation, replace the invented column with:
                  - The correct column from the allowlist (if the intended mapping is clear from context)
                  - F.lit(None).cast("string").alias("{target_col}") with a TODO comment if no clear replacement
               4. Do NOT modify any other logic — fix ONLY the flagged column references
               5. Write the corrected file back to {file_path}
           """,
         )
         
         # Re-validate after fix
         violations = run_validator(file_path, mapping_path, target_table)
     
     # After retry loop:
     if violations:
         failed_files.append(file_path)
         logger.error(f"Column validation FAILED for {file_name} after {MAX_RETRIES} retries")
         logger.error(f"Remaining violations: {json(violations)}")
```

### Post-loop state update:

```
if failed_files is empty:
    session_state.column_validation_result = "passed"
    session_state.column_validation_failures = null
    logger.info(f"✅ Column validation passed ({N} files checked)")
else:
    session_state.column_validation_result = "failed"
    session_state.column_validation_failures = failed_files
    logger.error(f"⚠️ Column validation FAILED — {len(failed_files)} file(s) with unresolved violations")
    # Mark affected files as DRAFT_UNVALIDATED
    for file in failed_files:
        mark_draft_unvalidated(file)
```

Log to `session/audit_log.jsonl`: `[COLUMN-VALIDATION] {result} — {N} files checked, {M} retries, {K} failures`.

### Key properties:

- **Fresh agent per retry**: Each retry agent starts with clean context (~2K tokens) — NO compaction risk
- **Targeted fix only**: Retry prompt says "fix ONLY flagged columns" — prevents cascading changes
- **Disk-backed allowlist**: Agent reads `session/source_column_allowlist.json` from disk — survives any context loss
- **Per-file, not per-batch**: One file's failure doesn't block other files
- **Non-blocking for pipeline**: Generation continues; column validation failures enforced at `/push`
- **Intermediate columns permitted**: Validator's `is_intermediate_column()` check ensures `.withColumn()` / `.alias()` / `.agg()` outputs are NOT flagged

### Column manifest in generated file header:

After validation passes (or after retries), append a source column manifest comment to the generated file's header block:

```python
# =============================================================================
# SOURCE COLUMN MANIFEST (auto-generated — do not edit)
# customer_response: customer_survey_id, question_id, customer_response_date, ...
# question: question_id, question_name, question_description, ...
# =============================================================================
```

This serves as both documentation and a cross-check reference for future validation runs.

---

## STEP FINAL.2 — Write Chain Checkpoint (Context Optimization)

After all transforms are generated and validated (syntax + column validation), write a compact checkpoint for downstream commands (`/gen-driver`, `/gen-ddl`, `/gen-bundle`). This allows them to skip re-parsing full session JSON files (~40 KB) when they only need table metadata.

Set `session_state.chain_checkpoints.post_transform`:

```json
{
  "tables": [
    {
      "target_schema": "{{target_schema}}",
      "table": "{{table_name}}",
      "table_type": "Transactional|NonTransactional_SCD1|NonTransactional_SCD2",
      "load_type": "Day0|BAU|full_then_incremental",
      "primary_keys": ["col1", "col2"],
      "partition_col": "dw_bus_dt|active",
      "crypto_applied": false,
      "files_generated": ["day0/.../transform.py", "day1/.../transform.py"]
    }
  ],
  "platform": "databricks",
  "tenancy_name": "{{tenancy}}",
  "dp_type": "{{fdp|cdp|bdp}}",
  "target_catalog": "{{catalog_name}}",
  "timestamp": "{{ISO 8601}}"
}
```

**Size:** ~500-800 tokens regardless of table count (vs 20-40 KB for full mapping_parsed.json + intent_identification.json).

**Usage by downstream commands:** If `chain_checkpoints.post_transform` exists, use it for table list, load_type, table_type, PKs, partition decisions. Still read `mapping_parsed.json` for column_mappings when needed (DDL column definitions).

Save session state.

---

## STEP FINAL.3 — Join Predicate & Literal Value Fidelity Validation + Self-Heal

After chain checkpoint is written, validate that generated PySpark join conditions and literal values match the locked predicates from `session/extracted_predicates.json`. This is the deterministic detection layer for join/literal hallucination.

### Pre-conditions:

- `session/extracted_predicates.json` exists (written by STEP 0.41) — if NOT: skip with `session_state.join_predicate_fidelity_result = "skipped_no_predicates"`. CONTINUE.
- **Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`. If `python_path == null`: set `join_predicate_fidelity_result = "skipped_no_python"`, log, CONTINUE.
- Column validation (STEP FINAL.1) completed — no point validating predicates if columns are wrong

### Algorithm:

```
MAX_RETRIES = 2

For each generated transform file:
  1. Run validator:
     {python_path} scripts/validate_join_predicates.py "{file_path}" "session/extracted_predicates.json" --target-table "{target_table}"
  
  2. If exit code 0 → PASS for this file. Continue to next file.
  
  3. If exit code 1 → violations found. Parse JSON from stdout. Enter retry loop:

     retry_count = 0
     while violations and retry_count < MAX_RETRIES:
         retry_count += 1
         
         logger.warn(f"Join predicate/literal violations found in {file_name} (retry {retry_count}/{MAX_RETRIES})")
         logger.warn(f"Violations: {json(violations)}")
         
         # Self-heal: invoke FRESH agent with targeted fix prompt
         Agent(
           description=f"Fix join predicate violations: {target_table} (retry {retry_count})",
           prompt="""
               JOIN PREDICATE / LITERAL VALUE VIOLATIONS DETECTED in {file_name}.
               
               The following join conditions or literal values do NOT match the mapping document:
               {json(violations)}
               
               Read the LOCKED constraints from: session/extracted_predicates.json
               
               INSTRUCTIONS:
               1. Read the generated file: {file_path}
               2. Read the locked predicates: session/extracted_predicates.json
               3. For each violation:
                  - JOIN PREDICATE violations: Replace the incorrect join condition with EXACTLY
                    the locked predicate (left_table.left_col OPERATOR right_table.right_col).
                    Do NOT assume symmetric keys. The mapping says A.x = B.y — use EXACTLY that.
                  - LITERAL VALUE violations: Replace the incorrect value with EXACTLY
                    the locked literal value. Do NOT substitute based on column name semantics.
               4. Do NOT modify any other logic — fix ONLY the flagged join/literal references
               5. Write the corrected file back to {file_path}
           """,
         )
         
         # Re-validate after fix
         violations = run_validator(file_path, predicates_path, target_table)
     
     # After retry loop:
     if violations:
         failed_files.append(file_path)
         logger.error(f"Join predicate validation FAILED for {file_name} after {MAX_RETRIES} retries")
         logger.error(f"Remaining violations: {json(violations)}")
```

### Post-loop state update:

```
if failed_files is empty:
    session_state.join_predicate_fidelity_result = "passed"
    session_state.join_predicate_fidelity_violations = null
    logger.info(f"✅ Join predicate fidelity passed ({N} files, {P} predicates, {L} literals checked)")
else:
    session_state.join_predicate_fidelity_result = "failed"
    session_state.join_predicate_fidelity_violations = failed_files
    logger.error(f"⚠️ Join predicate fidelity FAILED — {len(failed_files)} file(s) with unresolved violations")
    # Mark affected files as DRAFT_UNVALIDATED
    for file in failed_files:
        mark_draft_unvalidated(file)
```

Log to `session/audit_log.jsonl`: `[JOIN-PREDICATE-FIDELITY] {result} — {N} files checked, {M} retries, {K} failures`.

### Key properties:

- **Fresh agent per retry**: Each retry starts with clean context — NO compaction risk
- **Targeted fix only**: "fix ONLY flagged join/literal references" — prevents cascading changes
- **Disk-backed predicates**: Agent reads `session/extracted_predicates.json` from disk — survives context loss
- **Per-file, not per-batch**: One file's failure doesn't block other files
- **Non-blocking for pipeline**: Generation continues; fidelity failures enforced at `/push`
- **Gate**: `/push` refuses if `session_state.join_predicate_fidelity_result != "passed"` AND `!= "skipped_no_predicates"`

---

## STEP FINAL.4 — Primary Key Null Risk Validation + Self-Heal

After join predicate validation, validate that generated PySpark transforms do not expose primary key columns to NULL-producing patterns. This is the deterministic detection layer for PK null risk — catches LEFT JOIN nullable sides without coalesce, F.when() chains without .otherwise(), UDF-derived PKs, and unmapped PKs.

### Pre-conditions:

- `session/intent_identification.json` exists with `primary_key_columns` populated — if NOT: skip with `session_state.pk_null_risk_result = "skipped_no_pks"`. CONTINUE.
- **Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`. If `python_path == null`: set `pk_null_risk_result = "skipped_no_python"`, log, CONTINUE.
- Column validation (STEP FINAL.1) completed — no point validating PK null risk if columns are wrong

### Algorithm:

```
MAX_RETRIES = 2

For each generated transform file:
  1. Run validator:
     {python_path} scripts/validate_pk_null_risk.py "{file_path}" "session/mapping_parsed.json" "session/intent_identification.json" --target-table "{target_table}"
  
  2. If exit code 0 → PASS for this file. Continue to next file.
  
  3. If exit code 1 → violations found. Parse JSON from stdout.
     
     # Separate BLOCKING from WARNING violations
     blocking = [v for v in violations if v.severity == "BLOCKING"]
     warnings = [v for v in violations if v.severity == "WARNING"]
     
     # Log warnings (non-blocking) but do not retry for them
     for w in warnings:
         logger.warn(f"⚠️ PK null risk WARNING: {w.issue}")
     
     if not blocking:
         # Only warnings — pass with advisory
         continue to next file
     
     # Enter retry loop for BLOCKING violations only:
     retry_count = 0
     while blocking and retry_count < MAX_RETRIES:
         retry_count += 1
         
         logger.warn(f"PK null risk BLOCKING violations in {file_name} (retry {retry_count}/{MAX_RETRIES})")
         
         # Self-heal: invoke FRESH agent with targeted fix prompt
         Agent(
           description=f"Fix PK null risk: {target_table} (retry {retry_count})",
           prompt="""
               PRIMARY KEY NULL RISK VIOLATIONS DETECTED in {file_name}.
               
               The following PK columns have NULL-producing patterns:
               {json(blocking)}
               
               PK columns from: session/intent_identification.json
               
               INSTRUCTIONS:
               1. Read the generated file: {file_path}
               2. For each violation:
                  - pk_left_join_null_risk: Wrap the PK column reference with
                    F.coalesce(F.col('{pk_col}'), F.lit(<appropriate_default>))
                  - pk_when_without_otherwise: Add .otherwise(F.lit(<appropriate_default>))
                    to the F.when() chain that produces the PK column
                  - pk_not_produced: Add the PK column to the transform output
               3. Do NOT modify any other logic — fix ONLY the flagged PK columns
               4. Write the corrected file back to {file_path}
           """,
         )
         
         # Re-validate after fix
         violations = run_validator(file_path, mapping_path, intent_path, target_table)
         blocking = [v for v in violations if v.severity == "BLOCKING"]
     
     # After retry loop:
     if blocking:
         failed_files.append(file_path)
         logger.error(f"PK null risk validation FAILED for {file_name} after {MAX_RETRIES} retries")
         logger.error(f"Remaining violations: {json(blocking)}")
```

### Post-loop state update:

```
if failed_files is empty:
    session_state.pk_null_risk_result = "passed"
    session_state.pk_null_risk_violations = null
    logger.info(f"✅ PK null risk validation passed ({N} files, {P} PK columns checked)")
else:
    session_state.pk_null_risk_result = "failed"
    session_state.pk_null_risk_violations = failed_files
    logger.error(f"⚠️ PK null risk validation FAILED — {len(failed_files)} file(s) with unresolved violations")
    # Mark affected files as DRAFT_UNVALIDATED
    for file in failed_files:
        mark_draft_unvalidated(file)
```

Log to `session/audit_log.jsonl`: `[PK-NULL-RISK] {result} — {N} files checked, {M} retries, {K} failures`.

### Key properties:

- **Fresh agent per retry**: Each retry starts with clean context — NO compaction risk
- **Targeted fix only**: "fix ONLY flagged PK columns" — prevents cascading changes
- **WARNING vs BLOCKING**: UDF-derived PKs (Check 3) are WARNING only — never block or trigger retry
- **Per-file, not per-batch**: One file's failure doesn't block other files
- **Non-blocking for pipeline**: Generation continues; PK null risk failures enforced at `/push`
- **Gate**: `/push` refuses if `session_state.pk_null_risk_result == "failed"` (any BLOCKING violations remain)

---

## Failure Modes

- ⛔ **{{custom_de_list}} is empty** (crypto enabled but no DE extraction) → HALT (fail fast)
- Any source schema `UNRESOLVED_SOURCE_SCHEMA` → warn; use placeholder column lists
- `extraction_failed: true` crypto column → REFUSE for that column; output partial transform only (other columns proceed)
- Transformation logic references a column not in mapping → log warning; emit `{{placeholder_column}}`
- **Per-target-table failure: One table fails → Log error for that table; continue with others (fault-tolerant)**
- **load_type lookup fails for target table → HALT; do NOT default silently. Provide load_type via intent_identification.json or intent_overrides.json.**
