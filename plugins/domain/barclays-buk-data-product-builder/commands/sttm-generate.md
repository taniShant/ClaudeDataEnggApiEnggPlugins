---
description: Full STTM generation pipeline — ingest, interview, classify, resolve, generate, validate, export
disable-model-invocation: false
---
# /sttm-generate — Generate Source-to-Target Mapping

Generate a complete STTM (Source-to-Target Mapping) from provided inputs.

## Description

This is the primary workflow command. It orchestrates the full 8-step STTM generation pipeline:
INGEST → INTERVIEW → NORMALIZE → CLASSIFY → RESOLVE → GENERATE → VALIDATE → EXPORT

## Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--target` | `input/target_schema.xlsx` | Path to target schema (Excel or markdown) |
| `--code` | `input/code/` | Path to SQL/PySpark code |
| `--product-type` | Auto-detected | Force data product type (skip detection). Options: FDP, CDP, BDP |
| `--table-type` | Auto-detected | Force table type (skip detection). Options: Transactional, NonTransactional_SCD1, NonTransactional_SCD2 |
| `--crypto` | Auto-detected | Force crypto aspect (skip detection). Options: None, Tokenize, Detokenize, Both |
| `--skip-interview` | false | Skip the interview questionnaire (use only evidence from files) |
| `--guided` | true | Enable guided mode for all below-threshold fields |

## Workflow

### Step 0 — RESOLVE PLUGIN ROOT

`${CLAUDE_PLUGIN_ROOT}` is automatically set by the plugin loader. Verify:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` exists

If missing, STOP with: "❌ Plugin root not resolved. Ensure barclays-buk-data-product-builder plugin is loaded."

Verify hard dependencies at the resolved path:
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/scenarios.yaml`
- `${CLAUDE_PLUGIN_ROOT}/configs/sttm/validation_rules.yaml`
- `${CLAUDE_PLUGIN_ROOT}/templates/sttm/mapping_spec.md`

If any missing → **STOP**: "Plugin installation incomplete at ${CLAUDE_PLUGIN_ROOT}. Missing: [list]"

Verify workspace dirs in CWD:
- `input/` — if missing, create it with subdirs (source_metadata, source_dictionary, design_docs, code)
- `output/` — if missing, create it

**Path convention for remainder of this command:**
- Plugin assets: `${CLAUDE_PLUGIN_ROOT}/configs/sttm/`, `${CLAUDE_PLUGIN_ROOT}/templates/sttm/`, `${CLAUDE_PLUGIN_ROOT}/prompts/`, `${CLAUDE_PLUGIN_ROOT}/examples/sttm/`
- User inputs: `input/` (CWD)
- Generated output: `output/` (CWD)

### Step 0A — LOAD OR CREATE SESSION STATE

1. If `output/sttm_session_state.json` exists:
   - Read the session state
   - If `generation_status.overall_status` is `"completed"`:
     - Warn: "⚠️ Previous session {session_id} already completed. Starting fresh pipeline run."
     - Reset all `generation_status` fields to `"pending"`, set `overall_status: "in_progress"`
   - If any step shows `"completed"` and `overall_status` is `"halted"` or `"failed"`:
     - Log: "📋 Resuming session {session_id} from last failed step"
     - Skip steps already marked `"completed"`
   - Update `generation_status.overall_status` → `"in_progress"`
   - Write updated state
2. If `output/sttm_session_state.json` does NOT exist:
   - Create initial state (same structure as `/sttm-init` Step 4) with `overall_status: "in_progress"`
   - Write to `output/sttm_session_state.json`

**On any step failure hereafter:**
- Update the failing step to `"failed"` and `overall_status` to `"halted"`
- Write state before stopping

---

### Step 0B — INTERMEDIATE FILE SETUP

Create `output/.intermediate/` directory for inter-stage data handoff:
```bash
mkdir -p output/.intermediate
```

**File protocol** — stages write results to files; downstream stages read from files instead of passing data inline through orchestrator context:
```
output/.intermediate/
  context_inventory.json       ← Step 1 output (manifest of ingested inputs)
  interview_summary.json       ← Step 2 output (compressed answers)
  classification.json          ← Step 4 output (4-axis classification)
  lineage_cache.json           ← Step 5 output (full lineage + joins + filters)
  batch_{N}_lineage.json       ← Step 6 per-batch lineage subset
  batch_{N}_rows.jsonl         ← Step 6 per-batch generated rows (JSON Lines)
  batch_{N}_volumetrics.json   ← Step 6 per-batch volumetrics
  merged_rows.json             ← Step 6 post-merge (all rows + deduped volumetrics)
  scoped_validation_rules.json ← Step 7 classification-scoped rules
```

This directory is cleaned up after Step 9 export (or retained if `--debug` flag is set).

### Session State Update Protocol

At each step boundary, update `output/sttm_session_state.json`:

| After Step | State Updates |
|---|---|
| Step 1 (INGEST) | `step_1_ingest: "completed"`, `ingestion_status` block, `output_prefix`, `target_database`, `target_tables` |
| Step 2 (INTERVIEW) | `step_2_interview: "completed"` (or `"skipped"` if `--skip-interview`) |
| Step 3 (NORMALIZE) | `step_3_normalize: "completed"` |
| Step 4 (CLASSIFY) | `step_4_classify: "completed"`, `classification` block (4 axes + confidences + timestamp) |
| Step 5 (RESOLVE) | `step_5_lineage: "completed"` |
| Step 6 (GENERATE) | `step_6_rowgen: "completed"` |
| Step 7 (VALIDATE) | `step_7_validate: "completed"`, `validation_result` block (counts + result + timestamp) |
| Step 8–9 (EXPORT) | `step_8_export: "completed"`, `output_files` block, `overall_status: "completed"` |

**On failure at any step**: Set that step to `"failed"`, `overall_status: "halted"`, write state, then STOP.

**On resume**: Steps already marked `"completed"` are skipped; resume from first non-completed step.

---

### Python Availability

Read `python_path` from `output/sttm_session_state.json` — per `agents/refs/python-runtime-contract.md § Invocation Pattern`.
All `python -c` invocations below use `{python_path}`. If `python_path == null`, each invocation follows its fallback behaviour (documented inline).

---

### Step 1.0 — INGESTION COMPLETENESS PROTOCOL (MANDATORY — ALL Input Types)

Before proceeding to Step 2 (INTERVIEW) or any evidence-based decision, the orchestrator MUST verify 100% ingestion of every input file. This is a BLOCKING prerequisite for all downstream steps. **No auto-resolution, no evidence_index building, no classification, no interview skip_if evaluation until ALL inputs are 100% ingested.**

#### 1.0a — File Inventory & Size Assessment

Run a single Bash command to inventory all input files with line counts:

```bash
find input/ -type f ! -name '.gitkeep' -exec wc -l {} + | sort -rn
```

Record in `output/.intermediate/context_inventory.json`:
- `file_path`, `line_count`, `size_bytes`, `file_type` (sql/xlsx/json/md/csv/dm1)
- `total_files`, `total_lines`, `total_bytes`

#### 1.0b — Ingestion Strategy Per File Type (Context-Efficient)

Not all files need full orchestrator reading. Use a tiered strategy:

**TIER 1 — FULL READ (orchestrator reads every line):**
- Target schema (xlsx/md) — ALWAYS full read; every column matters
- Config overrides JSON — small; always full read
- Source metadata JSON files — small; always full read

**TIER 2 — PRE-SCAN + SELECTIVE READ (context-efficient):**
- **SQL/PySpark code files:**
  1. Run Structural Pattern Pre-Scan (Step 1.0c) via Bash — extracts structural summary (UNION count, DELETE count, JOIN count, table refs, params)
  2. Read file in pages IF > 2000 lines; track `lines_read` vs `total_lines`
  3. Use pre-scan results to guide WHERE to focus detailed reading
  4. **NEVER auto-resolve evidence from SQL until all pages read OR pre-scan summary is complete**
- **View definitions:**
  1. Pre-scan for all view names and which are referenced in main SQL
  2. Read ONLY referenced views in full (existing optimization)
  3. Record unreferenced view count for completeness tracking
- **Table definitions (DDL):**
  1. Parse via sqlglot one-liner (existing DDL pre-extraction)
  2. Structured output replaces full-file reading — context efficient
  3. Record table count and column count for completeness tracking

**TIER 3 — SUMMARIZE + INDEX (large files, context-sensitive):**
- **Design documents (markdown):**
  1. Read full document (usually <500 lines)
  2. Extract key-value facts into evidence_index
  3. Drop raw document from context after extraction
- **DM1 models:**
  1. Parse via Python XML; extract entity-relationship structure
  2. Structured output replaces raw XML — context efficient

#### 1.0c — Structural Pattern Pre-Scan (Lightweight, All Code Files)

Before reading any code file in detail, run a structural pattern scan on ALL files in `input/code/`:

If `python_path == null`: use Read/Write tools as fallback.

```python
{python_path} -c "
import re, sys, json, os

# Patterns to detect across all code file types
patterns = {
    'union': r'\bUNION\b',
    'delete': r'\bDELETE\s+FROM\b',
    'update': r'\bUPDATE\b[^;]*\bSET\b',
    'merge': r'\bMERGE\s+INTO\b',
    'rename': r'\bRENAME\s+TABLE\b',
    'semicolons': r';',
    'explicit_join': r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS)\s+(?:OUTER\s+)?JOIN\b',
    'implicit_join': r'\bFROM\b[^;]*,\s*\w+\.\w+',
    'subquery_in_not_in': r'\bNOT\s+IN\s*\(|\bIN\s*\(\s*SELECT\b',
    'exists_not_exists': r'\bNOT\s+EXISTS\s*\(|\bEXISTS\s*\(',
    'parameters': r':\w+',
    'create_table': r'\bCREATE\s+(?:SET\s+|MULTISET\s+)?TABLE\b',
    'drop_table': r'\bDROP\s+TABLE\b',
    'replace_view': r'\bREPLACE\s+VIEW\b',
    'qualify': r'\bQUALIFY\b',
    'zeroifnull': r'\bZEROIFNULL\b',
    'csum': r'\bCSUM\b',
    'file_read': r'spark\.read\.(parquet|format\(.parquet.\))',
    'file_write': r'\.write\.(parquet|format\(.parquet.\))',
    'storage_uri': r's3://|/Volumes/',
}

# Also extract table references from FROM/JOIN clauses
table_ref_pattern = r'(?:FROM|JOIN)\s+(\w+\.\w+)'

for root, _, files in os.walk('input/code/'):
    for fname in sorted(files):
        if fname == '.gitkeep': continue
        fpath = os.path.join(root, fname)
        content = open(fpath, encoding='utf-8', errors='replace').read()
        results = {k: len(re.findall(v, content, re.I|re.S))
                   for k, v in patterns.items()}
        results['total_lines'] = content.count(chr(10)) + 1
        results['total_chars'] = len(content)
        tables = sorted(set(re.findall(table_ref_pattern, content, re.I)))
        results['tables_referenced'] = tables
        results['table_count'] = len(tables)
        params = sorted(set(re.findall(r':(\w+)', content)))
        results['parameters_found'] = params
        results['parameter_count'] = len(params)
        # Detect if target table appears as source (self-referential)
        # Target table name is passed as argument
        if len(sys.argv) > 1:
            target = sys.argv[1].lower()
            results['self_referential'] = any(
                target in t.lower() for t in tables)
        print(json.dumps({'file': fpath, **results}))
" 'TARGET_DB.TARGET_TABLE' > output/.intermediate/code_prescan.json
```

Replace `TARGET_DB.TARGET_TABLE` with the actual `{target_database}.{target_table}` from the target schema.

This pre-scan:
- Completes in <5 seconds regardless of file size
- Provides DEFINITIVE pattern counts BEFORE any detailed reading
- Identifies which files contain which patterns (guides read priority)
- Detects self-referential target patterns
- Inventories all parameters and table references
- Costs ~0 context tokens (runs via Bash, only summary returned)

Record results in `output/.intermediate/context_inventory.json` under `code_prescan` key. These counts are **authoritative** for auto-resolution of pattern-based interview questions (Q1.3 multi-table, Q7.1 UNION, etc.).

#### 1.0d — Self-Referential Target Check

After identifying the target table (from target_schema) and completing the code pre-scan, check if the target table appears as a source:

```bash
grep -i 'FROM.*{target_table}\|JOIN.*{target_table}' input/code/*.sql
```

If found (or `self_referential: true` in code_prescan results), record in `context_inventory.json`:
```json
{
  "self_referential": true,
  "self_ref_files": ["input/code/main.sql"],
  "self_ref_line_count": 3
}
```

**Impact on downstream steps:**
- Source table list: target table MUST also appear as a source entry
- Source Volumetrics: target table needs its own volumetrics entry
- Business Logic: must document the self-read pattern (carry-forward, UNION assembly, etc.)
- Interview: Q1.3 auto-resolution must account for the target-as-source pattern

#### 1.0e — Completeness Verification (GATE)

After all files are processed, verify:
- For every file in inventory: `lines_read == line_count` (or equivalent for binary formats like xlsx)
- For SQL files: pre-scan pattern counts are recorded
- For target schema: `column_count` matches expected (row count - 1)

If ANY file is incompletely read → log `⚠️ WARNING`, re-read missing portions. Do NOT proceed to Step 2 until this gate passes.

Record final status in `output/.intermediate/context_inventory.json`:
```json
{
  "ingestion_complete": true,
  "files_fully_read": "N of M",
  "files_with_warnings": []
}
```

---

### Step 1 — INGEST

Read all available input files:

1. **Target schema** — Read via Bash + openpyxl:
   If `python_path == null`: HALT with error — Python + openpyxl required for Excel operations. See `agents/refs/python-runtime-contract.md § User Remediation`.
   ```
   {python_path} -c "import openpyxl; wb = openpyxl.load_workbook('input/target_schema.xlsx'); ..."
   ```
   OR read markdown target schema via Read tool.
   Extract: Target Database, Table, Column Name, Description, Datatype, Null Flag, Key Column.

#### 1.1 — OUTPUT PREFIX DERIVATION

After reading the target schema, compute the output file naming prefix:

1. Collect all distinct `target_table` values from the extracted target columns
2. Let `target_database` = the target database value from the schema
3. If exactly 1 distinct target table:
     `output_prefix = "{target_database}_{target_table}"`
   Else (multiple target tables):
     `output_prefix = "{target_database}"`
4. Sanitize: lowercase, replace non-alphanumeric/underscore chars with `_`, collapse consecutive underscores, strip leading/trailing underscores
5. Log: `"Output prefix: {output_prefix} ({N} target table(s))"`

Store `output_prefix` and `target_tables` (array of distinct table names) for use in Steps 7, 8B, 9. These values are also written to `output/.intermediate/context_inventory.json` after INGEST (see Context Inventory section).

2. **Source metadata** (if available) — Read JSON/CSV files from `input/source_metadata/`:
   - `table_inventory.json` — source table list
   - `column_metadata.json` — source column details
   - `join_candidates.json` — suggested joins
   - `scd_indicators.json` — SCD signal detection
   - **Profiling data** (if available): Excel workbook (`.xlsx`) in `input/source_metadata/` or `input/profiling/`.
     If absent, flag as "pending user input" and continue — profiling is advisory only, never blocking.

3. **Code artifacts** — Read SQL/PySpark from `input/code/` via Read tool

   **DDL Pre-extraction (Context-Efficient):** If `input/code/` contains DDL-only files (only CREATE TABLE/VIEW, ALTER, DROP — no SELECT, INSERT, MERGE, or CTAS):
   1. Parse DDL via sqlglot to extract table→column mappings:
      If `python_path == null`: skip sqlglot parsing, fall back to LLM interpretation.
      ```python
      {python_path} -c "import sqlglot,json,sys; sql=open(sys.argv[1]).read(); stmts=sqlglot.parse(sql);
      schemas={};
      [schemas.update({str(s.find(sqlglot.exp.Table)): [str(c.find(sqlglot.exp.Column) or c.args.get('this')) for c in s.find_all(sqlglot.exp.ColumnDef)]}) for s in stmts if isinstance(s, sqlglot.exp.Create)];
      json.dump(schemas, open('output/.intermediate/ddl_schemas.json','w'), indent=2);
      print(f'Extracted {len(schemas)} table schemas from DDL')" input/code/ddl_file.sql
      ```
   2. Add extracted schemas to `known_sources[]` as structured metadata
   3. Do NOT pass DDL-only files as code_artifacts to sttm-sql-lineage-agent (saves ~25 KB for DDL-heavy inputs)

4. **Source dictionary** (if available) — Read from `input/source_dictionary/`:
   - `data_dictionary.json`
   - `relationships.json`
   - `model.dm1` (parse via Python XML if present)

5. **Design documents** (if available) — Read markdown from `input/design_docs/`

6. **Config overrides** — Read `input/config_overrides.json` if present

8. **Load configs** — Read `${CLAUDE_PLUGIN_ROOT}/configs/sttm/scenarios.yaml`, `${CLAUDE_PLUGIN_ROOT}/configs/sttm/audit_columns.yaml`

**Targeted template_spec.yaml Loading (Context-Efficient):**
When loading `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml`, read ONLY the section needed for the current step:
- Step 0: Existence check only (no content load)
- Step 1: Read `mapping_columns[].header` and `volumetrics_columns[].header` (~3 KB) — for column name validation
- Step 2: Read `context_management` section only (~2 KB) — for interview delivery settings
- Step 6: Do NOT load — sttm-row-generator-agent has field rules built-in
- Step 9: Read `formatting` section only (~3 KB) — for Excel export formatting
Do NOT load the full 39 KB file at any step. Each section is self-contained.

### Step 2 — INTERVIEW (Phase A)

Unless `--skip-interview` is set:

#### 2.1 — Setup

1. Load `${CLAUDE_PLUGIN_ROOT}/configs/sttm/interview_questionnaire.yaml`
2. Read interview delivery settings from `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` → `context_management.interview_delivery`
3. **Pre-filter questions via Python** to extract only questions whose `skip_if` conditions are NOT met by available inputs. Preserve pass and category membership for each surviving question. This reduces ~1,062 lines of questions to ~200 relevant ones.
4. **Resume check**: If `output/.intermediate/interview_summary.json` exists from a prior run, load it as initial `interview_answers`. Show: `"ℹ Found {count} answers from a previous session. Resuming interview — only unanswered questions will be asked."` Skip questions already answered unless user explicitly requests re-asking.
5. **Resume from pass state:** If `interview_summary.json` contains `pass_metadata`:
   - Read `pass_metadata.passes_completed` → skip all questions in completed passes
   - Read `pass_metadata.current_pass` → start from this pass
   - Read `pass_metadata.current_pass_next_question_id` → skip to this question
   - Display: `"ℹ️ Resuming from Pass {N} — {pass_name} at Q{id}. {answered}/{total} questions answered in this pass."`
6. Initialize: `interview_answers = {}` (or loaded prior answers), `stats = {answered: 0, auto_skipped: 0, dependency_skipped: 0, deferred: 0}`

#### 2.1a — Pass 1.5: Source & Target I/O Mode (Conditional)

Pass 1.5 (Source & Target I/O Mode) questions are included in the interview flow when any of these conditions are true:
- `code_prescan.file_read` count > 0
- `code_prescan.file_write` count > 0
- `config_overrides.source_io` or `config_overrides.target_io` is present

When triggered, Pass 1.5 questions (Q1.5.1 through Q1.5.7) are inserted between Pass 1 (Scope) and Pass 2 (Transformation). Refer to `interview_questionnaire.yaml` for the full question definitions, skip conditions, and answer mappings for Q1.5.1–Q1.5.7.

#### 2.1b — Comprehensive Evidence Scanning

After INGEST, build an `evidence_index` that maps each ingested input type to the facts it can provide. This index is used during `skip_if` evaluation to check ALL declared evidence sources — not just one.

**Evidence index structure:**
- `sql_code` → table references, joins, WHERE clauses, transformations, aggregations, UDFs (already well-covered)
- `code_prescan` → **authoritative pattern counts from Step 1.0c pre-scan**: `union` count, `delete` count, `update` count, `merge` count, `explicit_join` count, `implicit_join` count, `parameters_found[]`, `parameter_count`, `tables_referenced[]`, `table_count`, `self_referential` flag, `rename` count, `semicolons` count. These counts are DEFINITIVE and override any evidence from partial SQL reading.
- `target_excel` → SCD column presence, column names, datatypes, descriptions (already well-covered)
- `design_doc` → load_type, table_type, CDC mechanism, process_frequency, rolling_deletion_predicate, delete handling, partition strategy, upstream dependencies, lookback window, source database, source tables
- `metadata_files` → join candidates (`join_candidates.json`), column relationships (`relationships.json`), SCD indicators (`scd_indicators.json`)
- `config_convention` → audit column patterns, enterprise standards (unchanged)
- `profiling_any` → row counts, size estimates, daily deltas per table (unchanged)
- `ddl_files` → partition clauses, column definitions (unchanged)

**Evaluation protocol:**
1. For each question's `skip_if` entries, evaluate the condition against the declared `evidence_source`
2. Only auto-resolve when evidence is **explicit and unambiguous** — e.g., a design doc must say "table type: SCD2" or "CDC mechanism: timestamp-based", not merely mention those terms in passing
3. When evidence from a lower-priority source (per `precedence.yaml`) contradicts a higher-priority source, do NOT auto-resolve — ask the user
4. Record the actual evidence source that provided the answer in `inferred_answer` provenance metadata

#### 2.1c — Pre-Interview Evidence Summary

After pre-filtering questions (step 2.1.3) and building the evidence index (step 2.1b), present a summary to the user BEFORE asking the first question:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Pre-Interview Evidence Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Evidence ingested:
  📄 SQL code:         {N} files ({lines} lines)
  📋 Target schema:    {column_count} columns
  📝 Design docs:      {doc_count} documents
  📊 Source metadata:  {meta_count} files

Auto-resolved from evidence:
  ✅ {question_id}: {short_question} → {inferred_answer} (from {source})
  ✅ {question_id}: {short_question} → {inferred_answer} (from {source})
  ... (all auto-resolved questions listed)

Remaining: {remaining_count} of {total_applicable} questions
  Pass 1 (Source Scope):   {n}
  Pass 2 (Transformation): {n}
  Pass 3 (Loading):        {n}
  Pass 4 (Refinement):     {n}

Review auto-resolved answers? (y/n)
```

**If user says "y"**, present the auto-resolved answers as a review table:
```
┌─ Auto-Resolved Answers ────────────────────────────────────────────────┐
│  Q#    │ Question (short)          │ Answer              │ Source      │
│────────┼───────────────────────────┼─────────────────────┼────────────│
│  1.1   │ Source database            │ e_loans_db          │ SQL        │
│  1.2   │ Source tables              │ TETLCAAC, TETLTCCC  │ SQL        │
│  4.1   │ Table type                 │ SCD2                │ Target DDL │
│  ...                                                                    │
└─────────────────────────────────────────────────────────────────────────┘

Accept all? (y) | Override a specific answer? (type Q# to override)
```

If user types a question number (e.g., "4.1"), prompt for a new answer. The override replaces the inferred answer with provenance `user_supplied`, confidence 0.95. After overrides, re-evaluate all downstream `depends_on` and `skip_if` conditions — the remaining question count may change.

#### 2.1d — Express Mode

After showing the Pre-Interview Evidence Summary, if the remaining question count is **5 or fewer** AND **none of the remaining questions is a gateway question**, offer Express Mode:

```
━━━━━ Express Mode Available ━━━━━

Only {remaining_count} questions remain after evidence auto-resolution.
Would you like to answer them all at once? (y/n)
```

**If user says "y"**, present all remaining questions in a single form-like block:
```
┌─ Express Mode — {remaining_count} Questions ──────────────────────────┐
│                                                                         │
│  Q{id_1}. {question_text_1}                                            │
│    → {options or answer guidance}                                       │
│    [Default: {default_1} — press Enter to accept]                      │
│                                                                         │
│  Q{id_2}. {question_text_2}                                            │
│    → {options or answer guidance}                                       │
│    [Default: {default_2} — press Enter to accept]                      │
│                                                                         │
│  ... (all remaining questions)                                          │
│                                                                         │
│  Provide answers as: Q#: answer (one per line)                          │
│  Or press Enter to accept all defaults where available.                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Express Mode constraints:**
- Gateway questions are NEVER included — they must always be presented individually because their answers determine downstream question flow. If any remaining question is a gateway, express mode is not offered.
- After express mode answers are collected, validate all answers against `depends_on` chains. If any answer invalidates or activates new questions (e.g., a new `depends_on` is now satisfied), fall back to sequential mode for those new questions only.
- `depends_on` chains within the express set are resolved in question-order (ascending ID): if Q5.11 depends on Q4.1, Q4.1's answer is processed first. If Q5.11 becomes invalid, it is removed from the set and noted: `"Q5.11 skipped — not applicable based on your Q4.1 answer."`
- If user says "n" to express mode, proceed with standard sequential pass execution below.

#### 2.2 — Pass Execution (SEQUENTIAL — CRITICAL)

**Execute the 4 passes in strict sequence. Complete Pass N before starting Pass N+1.**
**Questions are asked ONE AT A TIME. WAIT for the user's response before presenting the next question. NEVER present all questions at once.**

For each pass in order: [`scope`, `transformation`, `loading`, `refinement`]:

**A. Show pass header:**
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 Pass {N} of 4 — {pass_name}
{pass_description}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**B. Evaluate category-level skip conditions** for each category in this pass:
- Check `skip_category_if` against `interview_answers` (e.g., `day0_retrospective` skips if `5.0 == 'Day 1 only'`, `day1_incremental` skips if `5.0 == 'Day 0 only'`)
- If ALL categories in a pass are skipped → show `"Pass {N} — {pass_name}: All questions auto-resolved from evidence. No user input needed."` and proceed to next pass.

**C. For each question in this pass (in questionnaire order), apply this evaluation chain:**

1. **Check `skip_category_if`** — if the question's category has been disabled by a prior gateway answer, skip silently
2. **Check `depends_on`** against `interview_answers` collected SO FAR — if prerequisite answer does not satisfy the condition, skip this question (increment `stats.dependency_skipped`)
3. **Check `skip_if`** against all available evidence using the Comprehensive Evidence Scanning protocol (§2.1b) — evaluate each `skip_if` entry against its declared `evidence_source` in the `evidence_index`. If ANY skip condition is met by ANY declared evidence source, record the `inferred_answer` if one is specified, note the actual source in provenance, and skip (increment `stats.auto_skipped`)
4. **Check `gateway: true`** — if this is a gateway question, present it ALONE using the Gateway Visual Format (see §2.4). WAIT for the user's answer. Record immediately. Evaluate all downstream `depends_on` and `skip_category_if` conditions. Show impact: `"ℹ Based on your answer: {N} downstream questions activated, {M} questions skipped."` Only then proceed.
5. **Check `delivery_group`** — if this question has a `delivery_group` and the next 1-2 questions share the same group, have all survived skip evaluation, none is a gateway, and none has `depends_on` referencing another question in the group, present them together (max 3 questions per group) using the Group Visual Format. WAIT for all answers.
6. **Otherwise** — present as a single question using the Single Question Visual Format. WAIT for the user's answer.
7. **Record answer** in `interview_answers` with provenance `user_supplied`, confidence 0.95
8. **Apply `also_populates_additional_context`** — if present on the question, apply the transform and store the derived value
9. **Re-evaluate downstream** — the answer just given may now satisfy `skip_if` or `depends_on` for subsequent questions

**D0. Persist pass completion:**
- Append current pass name to `pass_metadata.passes_completed`
- Set `pass_metadata.current_pass = null`
- Write updated `interview_summary.json` to disk immediately

**D. After all questions in this pass are processed, show pass summary:**
```
─────────────────────────────────────────────────────────
✓ Pass {N} Complete — {pass_name}
  Answered: {count} questions
  Auto-skipped (evidence): {count} questions
  Skipped (dependency not met): {count} questions
─────────────────────────────────────────────────────────
```

**E0. Initialize next pass state:**
- Set `pass_metadata.current_pass = "{next_pass_name}"`
- Set `pass_metadata.current_pass_next_question_id = "{first_question_id}"`
- Set `pass_metadata.current_pass_questions_answered = 0`
- Write updated `interview_summary.json` to disk immediately

**E. Before starting next pass** (not shown after final pass):
```
Ready to proceed to Pass {N+1} — {next_pass_name}?
(Press Enter to continue, or type 'back' to revisit a question from this pass)
```
If user types 'back', show numbered list of questions answered in the current pass. Allow re-answering. If re-answering a gateway question, trigger full re-evaluation of all dependent questions.

#### 2.3 — Question Visual Formats

All formats include a **progress indicator** showing the current question number out of total remaining (non-skipped) questions. Track `questions_asked` (incremented after each presented question) and `total_remaining` (computed after pre-filtering and updated as gateways activate/skip questions).

**Single question:**
```
┌─ Question {id} ──── {questions_asked} of {total_remaining} remaining ──── Pass {N}/4 ─┐
│                                                                                         │
│  {question_text}                                                                        │
│                                                                                         │
│  [For choice type — show numbered options:]                                             │
│    1. {option_1}                                                                        │
│    2. {option_2}                                                                        │
│    3. {option_3}                                                                        │
│                                                                                         │
│  [If default exists:]                                                                   │
│  Default: {default_value} (press Enter to accept)                                       │
│                                                                                         │
│  [If evidence partially resolves:]                                                      │
│  💡 Evidence: {evidence_description}                                                    │
│     Suggested: {suggestion}                                                             │
│                                                                                         │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

**Gateway question (ALWAYS presented alone, with impact preview):**

Read the `gateway_impact` metadata from the questionnaire YAML for this question. Compute the downstream question count per option by traversing `activates` lists (accounting for questions already resolved by evidence). Present the impact preview BEFORE the options:

```
┌─ ⚑ GATEWAY Question {id} ──── {questions_asked} of {total_remaining} remaining ──── Pass {N}/4 ─┐
│                                                                                                    │
│  {question_text}                                                                                   │
│                                                                                                    │
│  ⚠ Your answer determines which questions follow:                                                 │
│    → "{option_1_short}": {gateway_impact[0].summary}                                              │
│    → "{option_2_short}": {gateway_impact[1].summary}                                              │
│    → "{option_3_short}": {gateway_impact[2].summary}                                              │
│    → "{option_4_short}": {gateway_impact[3].summary}  [if 4 options]                              │
│                                                                                                    │
│    1. {option_1}                                                                                   │
│    2. {option_2}                                                                                   │
│    3. {option_3}                                                                                   │
│    4. {option_4}  [if applicable]                                                                  │
│                                                                                                    │
│  [If default exists:]                                                                              │
│  Default: {default_value} (press Enter to accept)                                                  │
│                                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Grouped questions (2-3 tightly related, same delivery_group):**
```
┌─ Questions {id_a}–{id_c} ──── {questions_asked} of {total_remaining} remaining ──── Pass {N}/4 ─┐
│  {category_name}                                                                                   │
│                                                                                                    │
│  {id_a}. {question_text_a}                                                                        │
│    → {answer guidance / options}                                                                   │
│                                                                                                    │
│  {id_b}. {question_text_b}                                                                        │
│    → {answer guidance / options}                                                                   │
│                                                                                                    │
│  {id_c}. {question_text_c}                                                                        │
│    → {answer guidance / options}                                                                   │
│                                                                                                    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

#### 2.4 — Gateway Questions — Special Handling

Three questions are designated as **gateways** (marked `gateway: true` in the questionnaire YAML):

| Gateway | Question | Downstream Impact |
|---------|----------|-------------------|
| Q1.3 | Single vs multiple tables / UNION | Controls Q1.3b, Q1.4, Q7.1 |
| Q4.1 | SCD type (SCD2/SCD1/Transactional/Snapshot) | Controls Q4.2–4.6 (same pass) + Q5.4, Q5.11, Q5.14, Q5.17, Q5.19a (Pass 3 cross-pass) |
| Q5.0 | Load type scope (Both/Day 0/Day 1) | Controls entire `day0_retrospective` and `day1_incremental` categories |

**Gateway protocol:**
1. Present the gateway question ALONE — never grouped, even if it has a `delivery_group`
2. WAIT for user answer
3. Record the answer immediately in `interview_answers`
4. Evaluate ALL `depends_on` and `skip_category_if` conditions that reference this gateway
5. Update the remaining question list for the current pass AND later passes (for cross-pass gateways like Q4.1)
6. Show impact to user: `"ℹ Based on your answer: {description of what was activated/skipped}"`
7. Only THEN proceed to the next question

#### 2.5 — Special Question Handling

**Join key clarification (Q1.4):**
When presenting Q1.4 to the user, enumerate each table pair discovered in INGEST and ask for the join condition in `{left_table}.{left_column} = {right_table}.{right_column}` format. If the join key column names differ between the two tables (e.g., FRC_RSN_CDE on one side, src_code on the other), both sides MUST be explicitly stated. Do not assume column names match.

**Questions to always ask (never skip regardless of `skip_if`):**
- 5.1 (Day 0 date range) — for initial implementations
- 5.4 (SCD2 reconstruction mode) — for SCD2 tables
- 5.8 (Day 0 quality exclusions)
- 5.15 (delete handling)
- 5.20 (dedup strategy)

**Per-source-table volumetrics (Q5.9a–5.9d):**
These are templated questions repeated per unique source table discovered in Step 1 (INGEST).

**Batch mode selection** — When **2 or more** source tables need volumetric data (i.e., profiling is missing), present a batch mode selector BEFORE individual per-table questions:

```
┌─ Source Table Volumetrics ──── {count} tables need data ──── Pass 3/4 ─┐
│                                                                          │
│  Profiling data available for: {list_with_data}                          │
│  Missing for: {list_needing_data}                                        │
│                                                                          │
│  How would you like to provide volumetric data?                          │
│                                                                          │
│    A. Per-table (detailed — 4 questions per table)                       │
│    B. Same values for all tables (answer 4 questions once)               │
│    C. Mark all as "Unknown" and continue                                 │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

- **Option A**: proceed with per-table block presentation (current behavior, below)
- **Option B**: ask the 4 volumetric questions (5.9a–d) once, then replicate the answers to all tables needing data. Each table gets its own `source_volumetrics[]` entry with the same values. The `broadcast_hint` calculation still runs per-table.
- **Option C**: set all volumetric fields to null with provenance `user_stated_unknown` for all tables, set `broadcast_hint = "N"` for all (conservative default), and continue immediately. No volumetric questions are asked.

When only **1 table** needs data, skip the batch selector and present the per-table block directly.

**Per-table block** (used for Option A, or when only 1 table needs data):

```
┌─ Volumetrics: {source_database}.{source_table} ──── Pass 3 ─┐
│                                                                │
│  No profiling data found for this table.                       │
│  Needed for: broadcast hint, partitioning, capacity planning   │
│                                                                │
│  5.9a. Estimated row count at steady state?                    │
│    → integer or "Unknown"                                      │
│    SQL: SELECT COUNT(*) FROM {db}.{table};                     │
│                                                                │
│  5.9b. Estimated total size in GB?                             │
│    → decimal or "Unknown"                                      │
│                                                                │
│  5.9c. Daily rows added/changed?                               │
│    → integer or "Unknown"                                      │
│                                                                │
│  5.9d. Daily delta size in GB?                                 │
│    → decimal or "Unknown"                                      │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

For each source table: check if profiling data (from Excel report or prior user input) already provides the metric. Skip tables that have complete profiling.

Volumetrics resolution priority:
1. User direct answers (interview/guided mode)
2. Excel profiling report (if provided in `input/source_metadata/` or `input/profiling/`)

When NO profiling is available for a source table:
1. State which metrics are needed and WHY (broadcast hint calculation, partitioning strategy, capacity planning)
2. Recommend specific SQL queries from `profiling_queries.sql` (e.g., Query 1A for column profiling, Query 2A for row counts)
3. Accept user answer or "Unknown" — continue with null + stated assumptions
4. Record collected info in running profiling inventory

Answers are used by the sttm-row-generator-agent to:
- Populate the Source Volumetrics sheet
- Calculate `broadcast_hint` (Y if < 10,000 rows)
- Inform partitioning and batching strategy

#### 2.6 — Edge Cases

- **User answers "Unknown" or skips**: Record answer as `null`, set provenance to `user_supplied` with note `"user_stated_unknown"`. Add the question to deferred list for potential `/sttm-resolve` follow-up. Continue to next question.
- **Gateway answer eliminates downstream questions**: When a gateway answer eliminates questions (e.g., `Q5.0 == 'Day 0 only'` eliminates entire `day1_incremental` category), show: `"ℹ {N} questions skipped based on your answer ({reason})."`
- **Cross-pass dependencies**: Q4.1 (Pass 2) affects Q5.4, Q5.14, Q5.19a (Pass 3). The `interview_answers` store carries across all passes. When entering Pass 3, re-evaluate all `skip_if` and `depends_on` conditions using answers from Passes 1 and 2.
- **All questions in a pass auto-skipped by evidence**: Show `"Pass {N} — {name}: All {count} questions resolved from available evidence. No user input needed."` and proceed to next pass.
- **Partial prior answers (interrupted run)**: If `output/.intermediate/interview_summary.json` exists, load as initial answers. Show found count. Skip questions already answered unless user requests re-asking.
- **Profiling data available for some tables but not others**: Check per-table. Skip volumetric questions for tables with profiling data. Ask only for tables without. Show which are covered vs missing.
- **Default value exists**: Show default prominently with `"(press Enter to accept)"`. Record as `user_supplied` with note `"accepted_default"`.

#### 2.7 — Interview Completion and Handoff

After all 4 passes complete:

1. Show final interview summary:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Interview Complete
  Total questions answered: {count}
  Auto-resolved from evidence: {count}
  Skipped (dependency/scope): {count}
  Deferred to guided mode: {count}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

2. Compress answers per Context Management → Answer Compression rules (compact key:value format, drop question text/options/skip_if, keep only answer value + mapped field)
3. Write compressed answers to `output/.intermediate/interview_summary.json`
4. Proceed to Step 3 — NORMALIZE

If `--skip-interview` is set and no profiling is found, volumetrics fields will be null. Run `/sttm-resolve` post-generation to fill them.

### Step 3 — NORMALIZE

Build Column Resolution Records for each target column:
```json
{
  "target_column": "column_name",
  "target_datatype": "type",
  "target_nullable": "Y/N",
  "candidate_sources": [...],
  "scenario_hints": [...],
  "unresolved": []
}
```

Merge evidence from all ingested sources, applying confidence scores per `${CLAUDE_PLUGIN_ROOT}/configs/sttm/precedence.yaml`.

### Step 4 — CLASSIFY

Spawn `sttm-scenario-classifier-agent` with:
- Target column list (check for SCD indicators)
- SQL patterns detected
- Source database count and layer (raw/FDP/CDP)
- Crypto signals
- Explicit table type declaration
- Database prefix (fdp_/cdp_/bdp_/shared_fdp_/shared_cdp_/shared_bdp_)

The classifier evaluates 4 independent axes and returns:
```json
{
  "classification": {
    "data_product_type": "FDP|CDP|BDP",
    "table_type": "Transactional|NonTransactional_SCD1|NonTransactional_SCD2",
    "crypto_aspect": "None|Tokenize|Detokenize|Both"
  },
  "confidence": { "data_product_type": 0.99, "table_type": 0.95, "crypto_aspect": 0.90 }
}
```

The classifier also produces a 4th axis, `io_mode`, indicating the I/O mode of the data product (`table`, `file`, or `hybrid`). The `io_mode` value is derived from the interview Pass 1.5 answers and `code_prescan` file I/O signals, and is included in the classification output alongside the 3 primary axes. The `io_mode` value is passed to all downstream steps (RESOLVE, GENERATE, VALIDATE, EXPORT).

Accept the classification. If any axis has confidence < 0.7, ask user to confirm that axis.

**Post-Classification Context Drop:**
After classification is determined and written to `output/.intermediate/classification.json`:
The full `scenarios.yaml` content is no longer needed. Subsequent steps reference only the
compact classification object (4 axis values + audit column templates for the resolved type, ~2 KB).
Do NOT re-read `scenarios.yaml` in Steps 5–9.

### Step 5 — RESOLVE (Lineage)

Spawn `sttm-sql-lineage-agent` with:
- All code artifacts
- Target column names
- Known source tables

**Conditional Extension Loading for sttm-sql-lineage-agent (based on Step 1.0c code_prescan + context_inventory):**
When spawning sttm-sql-lineage-agent, include CONDITIONAL extensions based on detected input characteristics:
- If any code_artifact type = "pyspark": include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-lineage-ext-pyspark-handling.md`
- If Teradata dialect detected (QUALIFY, SEL, ZEROIFNULL, NULLIFZERO, OREPLACE, etc.): include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-lineage-ext-teradata-dialect.md`
- **Mandatory multi-step-etl extension loading** — include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-lineage-ext-multi-step-etl.md` when ANY of these conditions are true (from code_prescan):
  - Code artifacts contain 2+ semicolons (original rule)
  - **OR** code_prescan `delete` count > 0 (DELETE FROM detected)
  - **OR** code_prescan `update` count > 0 (UPDATE...SET detected)
  - **OR** code_prescan `merge` count > 0 (MERGE INTO detected)
  - **OR** code_prescan `rename` count > 0 (RENAME TABLE detected)
  - **OR** code_prescan `total_lines` > 500 (conservative: likely multi-statement)
Do NOT load extensions that do not match detected input. This saves 7–50 KB per run.

**View Definition Optimization:** When a view_definitions file exists in `input/code/`:
1. First pass: scan main SQL for referenced view names (FROM/JOIN clauses)
2. Second pass: load ONLY referenced view definitions
3. Python extraction:
   If `python_path == null`: use Read/Write tools as fallback.
   ```python
   {python_path} -c "import re,sys; sql=open(sys.argv[1]).read(); vf=open(sys.argv[2]).read();
   views=re.split(r'(?=(?:CREATE|REPLACE)\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(?:GLOBAL\s+TEMPORARY\s+)?VIEW)', vf, flags=re.I);
   refs=[v for v in views if v.strip() and any(n.lower() in sql.lower() for n in re.findall(r'(?:CREATE|REPLACE)\s+(?:OR\s+REPLACE\s+)?(?:TEMP(?:ORARY)?\s+)?(?:GLOBAL\s+TEMPORARY\s+)?VIEW\s+(\S+)', v, re.I))];
   open('output/.intermediate/referenced_views.sql','w').write('\n'.join(refs));
   print(f'{len(refs)} of {len(views)-1} views referenced')" input/code/main.sql input/code/view_definitions.sql
   ```
4. Pass `output/.intermediate/referenced_views.sql` instead of full view_definitions.sql
This saves ~78 KB when only ~30% of views are referenced.

Merge lineage results with metadata evidence per precedence rules.
For each target column, select the highest-confidence source mapping.

**CRITICAL — Structured Filter Extraction Format:**
The sttm-sql-lineage-agent MUST return `filters_extracted` as a structured object (NOT flat strings):
```json
{
  "where_clauses": ["billing_period = :PREV_BILLING_PERIOD", ...],
  "having_clauses": [...],
  "qualify_clauses": ["CSUM(1, nbr_cardh_acct, time_last_upd DESC) = 1"],
  "per_join_filters": { "table_alias": "filter_expression", ... },
  "per_column_conditions": { "column_name": ["condition1", ...], ... },
  "per_step_filters": {
    "Hist130": { "where": ["billing_period = :PREV_BILLING_PERIOD"], "qualify": ["CSUM(1, nbr_cardh_acct, time_last_upd DESC) = 1"] },
    "Hist140": { "where": [], "group_by": ["account_number"] },
    "Hist150": { "where": ["date_consol BETWEEN :bp_first_day AND :bp_last_day"], "group_by": ["account_number"] }
  }
}
```

When `per_column_conditions` cannot be derived (complex WHERE applies broadly), propagate the full WHERE clause to all columns from that query step as their `Conditions:` suffix.

When `per_step_filters` is populated, the sttm-row-generator-agent uses it to assign the correct filter to each column based on which step produced that column. A column sourced from Hist140 gets Hist140's GROUP BY as its Conditions, not Hist130's WHERE.

**CRITICAL — Preserve JOIN chain and filters:**
The sttm-sql-lineage-agent returns `joins_detected` (full join chain with driver table, join types, join conditions, table conditions) and `filters_extracted` (WHERE/HAVING/QUALIFY/GROUP BY clauses in the structured format above). These structures MUST be preserved in full and passed to Step 6. They are query-level context — not per-column — and are needed by the sttm-row-generator-agent to populate the structured Business Logic format.

**MUST PASS TO STEP 6 (additional SQL edge-case structures):**
- `union_metadata` — when UNION/UNION ALL detected: branch count, per-branch source tables, per-branch join chains
- `merge_metadata` — when MERGE detected: matched/not_matched branch lineage
- `temp_table_chain` — resolved temp table → base table mappings
- `intermediate_steps` — per-step lineage capture for multi-statement ETL (joins, filters, columns_produced, grain_keys, aggregation_semantics, update_semantics, merge_semantics, delete_semantics, filter_provenance, row_operation, columns_dropped)
- `column_lineage_chains` — per-target-column chain through intermediate steps (chain_depth, steps, intermediate_expressions with role, datatype_changes)
- `effective_source_filters` — cumulative filter summary per base source table
- `resolved_variables` — DECLARE/SET variable registry forwarded from sttm-sql-lineage-agent
- `filters_extracted.distinct` — whether SELECT DISTINCT was used
- `filters_extracted.exists_subqueries` — tables from EXISTS/NOT EXISTS subqueries

**SQL edge-case handoff rules:**
- When UNION is detected, the `joins_detected` becomes per-branch — each UNION branch may have its own join chain. Pass the `union_metadata` structure with per-branch join chains.
- When the sttm-sql-lineage-agent processes multi-statement files (temp table chains, INSERT...SELECT), the `temp_table_chain` field maps intermediate tables to their resolved base tables. This must be passed to Step 6 for Source Volumetrics to reference base tables, not temp tables.
- When MERGE is detected, pass `merge_metadata` with branch-specific lineage so the sttm-row-generator-agent can produce Business Logic showing both matched and not-matched paths.

**Multi-statement and PySpark processing:**
- If the code artifacts contain multiple semicolon-separated statements, the sttm-sql-lineage-agent will identify the target statement and use earlier statements (DDL, temp table creation) as context. The agent handles this internally — the orchestrator only needs to ensure ALL code files from `input/code/` are passed.
- For PySpark code, the sttm-sql-lineage-agent extracts source tables from spark.read/spark.table patterns and maps DataFrame methods to SQL equivalents. No special orchestrator handling needed.

**File-based lineage output (when COLUMN BATCHING is active or pre-flight triggers file handoffs):**

After lineage extraction completes, write the full result to `output/.intermediate/lineage_cache.json` via Python one-liner:

If `python_path == null`: use Read/Write tools as fallback.

```python
{python_path} -c "
import json, sys
lineage_data = json.loads(sys.stdin.read())
with open('output/.intermediate/lineage_cache.json', 'w') as f:
    json.dump(lineage_data, f, indent=2)
print(json.dumps({'status': 'cached', 'columns_resolved': len([l for l in lineage_data.get('lineage', []) if l.get('confidence', 0) >= 0.7]), 'columns_unresolved': len(lineage_data.get('unresolved', [])), 'tables_referenced': len(lineage_data.get('tables_referenced', [])), 'joins_detected': len(lineage_data.get('joins_detected', [])), 'file': 'output/.intermediate/lineage_cache.json'}))
"
```

Retain in orchestrator context ONLY the summary (column count, unresolved count, file path). Drop the full lineage array, join chain, and filters from context — they will be read from file by downstream stages.

### Step 6 — GENERATE

**Conditional Extension Loading for sttm-row-generator-agent (based on lineage results):**
When spawning sttm-row-generator-agent, include CONDITIONAL extensions based on lineage results:
- If lineage_cache has non-null `union_metadata` OR `merge_metadata`: include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-rowgen-ext-union-merge-format.md`
- If lineage_cache has non-empty `intermediate_steps[]`: include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-rowgen-ext-multi-step-rendering.md`
When loading `transformation-patterns.md` for sttm-row-generator-agent, include CONDITIONAL pattern extensions:
- If Teradata dialect: include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-pattern-ext-teradata.md`
- If `intermediate_steps` non-empty: include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-pattern-ext-multi-step.md`
- If `classification.crypto_aspect != "None"`: include `${CLAUDE_PLUGIN_ROOT}/agents/refs/sttm-pattern-ext-crypto.md`
Do NOT load extensions that do not match. This saves up to 29 KB per batch × 4 batches = ~116 KB.

**Example Selection (Context-Efficient):**
1. Read `${CLAUDE_PLUGIN_ROOT}/configs/sttm/example_index.yaml` (~2 KB)
2. Check `pattern_overrides` first: if union/multi_step_etl/pyspark/teradata/merge detected, use override
3. Else select ONE output example by `classification.table_type` + `crypto_aspect`
4. Load ONLY the selected output example — input example NOT needed by row-generator
5. Batches 2+: reference "same example as batch 1" — do NOT reload

**View Resolution in Join Chain (MANDATORY):**

Before assembling per-column join chains, resolve all view names in `joins_detected` to their ultimate base tables. This ensures the sttm-row-generator-agent receives base table names for Business Logic rendering — view names must NEVER appear in Driver Table / Join N lines.

1. Build a `view_to_base_table` lookup from `intermediate_steps` in `lineage_cache.json`:
   ```
   For each step where statement_type == 'CREATE_VIEW':
     view_to_base_table[step.temp_table_name] = step.resolves_to_base_tables[0]
   ```
   Example: `{"l_bcs_loaddb.prior_cycle_v": "s_trmfdb.ctcp", "l_bcs_loaddb.charge_off_v": "t_trmfdb.charge_off", "a_trmf_base.account_header": "t_trmfdb.account_header"}`

2. For each entry in `joins_detected`:
   - If `driver_table` is in `view_to_base_table` → replace with the resolved base table
   - For each join in `joins[]` → if `table` is in `view_to_base_table` → replace with the resolved base table
   - Aliases remain unchanged (they are defined by the SQL and used in expressions)

3. Apply BEFORE the per-column join chain assembly below — all downstream logic operates on resolved base table names.

**Join Chain Assembly for Row-Generator (MANDATORY):**

After view resolution, transform `joins_detected[]` (step-level) into per-column `join_chain` objects:

For each target column:
1. Identify which step produced this column — from the lineage entry's `notes` field (e.g., "Via Hist130", "Via Hist140 → temp3_a → temp3 → Hist220")
2. Find the (now view-resolved) `joins_detected` entry for that step
3. Build a per-column `join_chain` object:
   ```json
   {
     "driver_table": "t_trmfdb.account_header",
     "alias": "ach",
     "joins": [
       {"type": "LEFT OUTER JOIN", "table": "s_trmfdb.ctcp", "alias": "pc", "on": "ach.Account_Number = pc.Account_Number"}
     ],
     "driver_conditions": ["billing_period = :PREV_BILLING_PERIOD"]
   }
   ```
4. **Join Relevance Filter:** Include ONLY joins whose tables are referenced in this column's `source_tables`, `source_columns`, or `expression`:
   - Column `credit_limit` has expression `COALESCE(pc.Credit_Limit, prevhist.Credit_Limit)` → include joins for `pc` and `prevhist` only
   - Column `account_number` has expression `ach.Account_Number` → driver-only, no joins needed
   - Column `foreign_cash_value` has expression referencing `c.amt_trans` → include join for `c` only
5. Pass as column-level `join_chain` alongside the lineage entry

Example — `credit_limit` (aliases pc + prevhist referenced, tables resolved to base):
```json
{
  "driver_table": "t_trmfdb.account_header",
  "alias": "ach",
  "joins": [
    {"type": "LEFT OUTER JOIN", "table": "s_trmfdb.ctcp", "alias": "pc", "on": "ach.Account_Number = pc.Account_Number"},
    {"type": "LEFT OUTER JOIN", "table": "l_bcs_loaddb.bc_history_prev", "alias": "prevhist", "on": "ach.account_number = prevhist.account_number"}
  ],
  "driver_conditions": ["billing_period = :PREV_BILLING_PERIOD"]
}
```

Example — `account_number` (driver-only, no joins referenced):
```json
{
  "driver_table": "t_trmfdb.account_header",
  "alias": "ach",
  "joins": [],
  "driver_conditions": ["billing_period = :PREV_BILLING_PERIOD"]
}
```

Spawn `sttm-row-generator-agent` with:
- Target definition (all columns)
- Classification object (all 4 axes + `io_mode`)
- Resolved lineage per column
- **Per-column `join_chain`** (assembled above — relevant joins only, not the full step-level join chain)
- **Filter conditions** (from sttm-sql-lineage-agent's `filters_extracted` — structured format with per_step_filters)
  - CRITICAL: `filters_extracted` MUST be passed even when `joins_detected` is empty (single-source tables). Single-source queries with WHERE/HAVING/QUALIFY filters need `filters_extracted` to populate the `Conditions:` suffix in Business Logic. Omitting `filters_extracted` when `joins_detected` is empty causes all single-source filters to be silently dropped.
- Configuration (SCD, audit, partition, load type)
- Interview answers
- Profiling data (if available)
- **Grain evidence** for auto-derivation in Target Table Description (Column L):
  - `grain_impact` per column (already in lineage entries)
  - `intermediate_steps[].grain_keys[]` (already in intermediate_steps)
  - `aggregation_semantics.group_by_columns[]` (already in intermediate_steps)
  - Target columns with Key Column = "Y" (already in target definition)
  - Interview answer Q3.7 (already in interview_answers)
  
  All grain evidence flows through existing handoff structures — no additional data needs to be passed. The sttm-row-generator-agent applies its §Grain Derivation algorithm during first-row generation.

**File I/O mode handling:** When `io_mode` is `file` or `hybrid`, the row generator receives `source_io` and `target_io` from session state. File-specific source attribution rules apply: column G (Source Database) = `(file:parquet)`, column H (Source Table Name) = absolute storage path (e.g., `s3://raw-bucket/data/customer_events/`), column I (Source Column Name) = 2-part FQN (`{logical_name}.{column}`) where `logical_name` is derived from the path basename. These rules override the standard 3-part fully qualified naming for file-based sources only; table-based sources in hybrid mode continue to use the standard `{database}.{table}.{column}` format. File targets are signalled by `(file:parquet)` suffix in column B (Target Table Name) — the suffix is stripped to yield the clean target table name.

Receive: All 16-field mapping rows (each with `structured_transformation` JSON object) + Source Volumetrics rows + `grain_derivation` metadata.

**`structured_transformation` Handoff (MANDATORY):**
Each mapping row returned by sttm-row-generator-agent includes a `structured_transformation` JSON object built directly from lineage data (see §structured_transformation in sttm-row-generator-agent.md). This object is carried through merge, validation, and export:
- During merge: preserved as-is on each row in `merged_rows.json`
- During validation: available for structural checks (M42-M50 rules can validate against it)
- During export: included in `_sttm.json` output; NOT written to Excel (Excel has only the 16 text columns)
- DE's `/parse-mapping` prefers this object over regex extraction from Business Logic text

**Schema Contract Enforcement (per batch — MANDATORY):**
After receiving rows from sttm-row-generator-agent and BEFORE proceeding to merge or validation, verify the JSON field name contract on every row:

1. **Field name check**: Every row must use exactly the 16 canonical field names defined in `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` → `json_field_schema.canonical_fields`. Wrong field names (e.g., `target_column` instead of `target_column_name`, `target_column_definition` instead of `target_column_description`) must be renamed to the canonical name. Log any renames: `"Schema fix: renamed '{wrong}' to '{canonical}' in {count} rows."`

2. **Null flag normalization**: Every `target_column_null_flag` value must be exactly `"Y"` or `"N"`. Convert:
   - `"NOT NULL"` → `"N"`
   - `"NULL"` → `"Y"`
   - Any other variant → log warning and convert to `"Y"` (conservative default)

3. **Datatype normalization**: Every `target_column_datatype` must be a lowercase Iceberg/Spark type. Apply the `datatype_mapping.teradata` mapping from `template_spec.yaml` if uppercase or platform-specific types are detected. Log any conversions: `"Datatype fix: converted '{source_type}' to '{iceberg_type}' for column '{col}'."`

4. **UTF-8 sanitization**: Scan all text fields for mojibake patterns (`â€"`, `â€™`, `â€œ`, etc.). Replace with ASCII equivalents. Log any fixes.

This enforcement runs per-batch to prevent schema drift between batches (the root cause of Issue #9 in the review).

**Source Volumetrics Skeleton (MANDATORY):**
After receiving rows from sttm-row-generator-agent, verify that `source_volumetrics` is not empty when source tables exist:

1. **Collect all unique source tables** from `tables_referenced` in the lineage cache (from Step 5).
2. **Check**: If `source_volumetrics` is empty (`[]`) but `tables_referenced` has ≥1 entry → this is a generation defect.
3. **Auto-fix**: For every table in `tables_referenced` that is NOT already in `source_volumetrics`, emit a skeleton entry:
   ```json
   {
     "source_database": "<database>",
     "source_table": "<database>.<table>",
     "estimated_rows": null,
     "estimated_size_gb": null,
     "daily_increment_rows": null,
     "daily_increment_size_gb": null,
     "primary_key": null,
     "partition_key": null,
     "table_type": null,
     "broadcast_hint": "N"
   }
   ```
4. **Log**: `"Volumetrics: emitted {count} skeleton entries for source tables missing from row-generator output."`
5. **Rule**: `source_volumetrics: []` is NEVER acceptable when source tables exist. Validation rule F7 catches this, but the auto-fix here prevents it from reaching validation as a defect.

**Multi-step output verification (when intermediate_steps is non-empty):**

After receiving rows from sttm-row-generator-agent, perform these pre-checks before proceeding to validation:

1. **Lineage divider present (M27 pre-check):** The first row with `key_column = "Y"` must have `"Transformation Lineage:"` in its `business_logic` field. If missing, the row-generator fell back to narrative text.
2. **Step format used (M25 pre-check):** Non-key columns where `column_lineage_chains` has `chain_depth > 1` must have `"Step "` prefix in their `business_logic` field.
3. **DELETE/TRUNCATE steps documented (M28 pre-check):** Any DELETE or TRUNCATE operations in `intermediate_steps` must appear in the first key column row's Transformation Lineage block.
4. **Row count = target column count (single-cell rule):** Verify the row-generator produced exactly one row per target column. Multi-step ETL logic MUST be consolidated into single `business_logic` cells — never split into step-per-row. If extra rows were generated (row count > target column count), the agent incorrectly created separate rows for intermediate steps.

If any check fails → log a `⚠️ GENERATION WARNING: Multi-step lineage [check_name] failed — row-generator may have fallen back to narrative or split steps across rows. Formal validation (Step 7) will catch via M25-M33.` Do NOT re-invoke the row-generator agent; proceed to validation which will formally report the issue.

**File-based generation output (when COLUMN BATCHING is active or pre-flight triggers file handoffs):**

Each generation batch writes its output to per-batch files instead of returning inline:
- `output/.intermediate/batch_{N}_rows.jsonl` — generated rows (JSON Lines: one JSON object per line)
- `output/.intermediate/batch_{N}_volumetrics.json` — source volumetrics for tables encountered in this batch

The orchestrator records ONLY "Batch N: X rows written to file" — does NOT accumulate row data in context.

After ALL batches complete, merge via Python:

If `python_path == null`: use Read/Write tools as fallback.

```python
{python_path} -c "
import json, glob
all_rows = []
all_vol = []
for f in sorted(glob.glob('output/.intermediate/batch_*_rows.json*')):
    with open(f) as fh:
        content = fh.read().strip()
        if content.startswith('['):
            all_rows.extend(json.loads(content))
        else:
            for line in content.split('\n'):
                line = line.strip()
                if line:
                    all_rows.append(json.loads(line))
for f in sorted(glob.glob('output/.intermediate/batch_*_volumetrics.json')):
    with open(f) as fh:
        all_vol.extend(json.load(fh))
seen = set()
unique_vol = []
for v in all_vol:
    key = (v.get('source_database',''), v.get('source_table',''))
    if key not in seen:
        seen.add(key)
        unique_vol.append(v)
json.dump({'rows': all_rows, 'source_volumetrics': unique_vol},
          open('output/.intermediate/merged_rows.json', 'w'), indent=2)
print(f'Merged: {len(all_rows)} rows, {len(unique_vol)} volumetrics entries')
"
```

When NOT batching (small tables <50 columns): generation proceeds inline as before — no intermediate files needed.

**Context Hygiene Between Batches:**
After each batch completes and rows are written to file:
1. Record ONLY batch summary: "Batch N: X rows, Y volumetrics entries"
2. Do NOT retain batch lineage subset or row output in working memory
3. Next batch: re-read `batch_{N+1}_lineage.json` from file fresh
4. Interview summary + classification are small (<3 KB) — retain these
5. Conditional extensions: re-evaluate per batch's columns
   (e.g., if batch 3 has no crypto columns, skip crypto-patterns.md for that batch)

**CRITICAL — 3-Part Fully Qualified Source Naming (MANDATORY):**
- Column H (Source Table Name): {database}.{table} format, ALL contributing tables comma-separated
- Column I (Source Column Name): {database}.{table}.{column} format, ALL contributing columns comma-separated
- Column G (Source Database): ALL contributing databases comma-separated
- NEVER use bare table names or 2-part table.column — always 3-part qualified
- Special markers (system)/(derived)/N/A/Hardcoded are the only exceptions

Example: even a direct copy must be `e_loans_tallyman_db.TETLTABA.ACCOUNT_BALANCE_AMOUNT`

**NOTE:** The join_chain and filters are essential for generating correct Business Logic (column J) in structured format. Without them, multi-table transformations will incorrectly default to "Direct mapping".

**ANTI-DUPLICATION:** When multi-table structured format is used, the expression appears ONLY in the `Value:` line — do NOT also prepend it as a leading line before `Driver Table:`. The first line of business_logic must be `Driver Table:` when the structured format applies.

### Step 6B — SCOPE VALIDATION RULES

Before spawning sttm-validation-agent, extract only classification-relevant rules from `${CLAUDE_PLUGIN_ROOT}/configs/sttm/validation_rules.yaml` via Python:

**Always include:** S1-S7, M1-M24, A1-A6, F1-F13 (universal rules)

**SC rules — scoped independently per axis:**
- **table_type axis:**
  - Include SC1-SC4 only when `table_type == NonTransactional_SCD2`
  - Include SC5 only when `table_type == Transactional`
- **crypto_aspect axis:**
  - Include SC6-SC7 when `crypto_aspect != None` (applies to Tokenize, Detokenize, or Both)
  - Include SC8 only when `crypto_aspect == Both`
  - **Note:** Crypto rules are axis-independent — a Transactional table CAN have crypto, so never exclude SC6-SC8 based on table_type
- **Pattern-based cross-axis:**
  - SC9-SC14 are triggered by detected patterns (multi-source, LEFT JOIN, aggregation, UNION, self-join, non-equi JOIN) regardless of classification — include when the relevant pattern is detected in lineage

Write scoped rules to `output/.intermediate/scoped_validation_rules.json`.

**Example scoping outcomes:**
- Transactional + None crypto: excludes SC1-SC4 and SC6-SC8 (~140 lines saved)
- Transactional + Tokenize: excludes SC1-SC4 only; KEEPS SC6-SC7 (~80 lines saved)
- SCD2 + None crypto: excludes SC5 and SC6-SC8; KEEPS SC1-SC4 (~100 lines saved)
- SCD2 + Both crypto: excludes SC5 only; KEEPS SC1-SC4 and SC6-SC8 (~20 lines saved)

### Step 7 — VALIDATE

Spawn `sttm-validation-agent` with:
- Generated rows
- Classification object (all 4 axes)
- Available artifact references
- `scoped_rules_file`: `output/.intermediate/scoped_validation_rules.json` (when file-based handoff is active)

Key validation checks include:
- M15–M19 (multi-table format, join conditions, filter conditions, SQL JOIN alignment)
- M20 (Derived Column Source Transparency) — flags any (derived) rows whose business logic
  references source tables, aggregations, or window functions. Auto-fix not possible;
  routes to guided mode to ask user which source tables contribute.

If BLOCKERS found:
- Report them to user
- Attempt auto-fix for simple issues (e.g., missing Additional Context)
- Re-validate after fixes
- If blockers persist → stop and report

### Step 8A — GUIDED MODE (Phase B)

For any field with confidence < 0.7 in provenance, **or when grain derivation could not reach confidence >= 0.7** (indicated by `grain_derivation.appended == false` and `grain_derivation.grain_columns == []`):
- Present the ambiguity to user
- Show available evidence
- Propose options from `${CLAUDE_PLUGIN_ROOT}/commands/refs/sttm-guided-mode-questions.md`
- **For grain**: use Q11 ("What is the grain of {target_table}?"). Show key columns, grain_impact data, GROUP BY columns, and grain_keys as evidence. On answer, append `Grain: <answer>.` to target_table_description and set provenance method = "user_supplied", confidence = 0.95.
- Accept user answer → update the row
- Re-validate affected rows

### Step 8B — PROVENANCE

Spawn `sttm-provenance-agent` with:
- All generated rows
- Lineage results
- Classification evidence
- Interview answers
- Conflict log

### Step 9 — EXPORT

**Resolve output paths:** Read `output_prefix` and `target_tables` from `output/.intermediate/context_inventory.json` (written after Step 1). Define all output paths using the prefix:
- `STTM_JSON   = "output/{output_prefix}_sttm.json"`
- `STTM_XLSX   = "output/{output_prefix}_sttm.xlsx"`
- `PROV_JSON   = "output/{output_prefix}_provenance.json"`
- `PROV_XLSX   = "output/{output_prefix}_provenance.xlsx"`
- `VAL_REPORT  = "output/{output_prefix}_validation_report.json"`

**Data source for export:**
- If `output/.intermediate/merged_rows.json` exists (file-based handoff was active): read mapping rows and volumetrics from that file + classification from `output/.intermediate/classification.json`
- Otherwise: assemble from in-context data (small-table path, no batching was used)

1. Write `{STTM_JSON}` (canonical JSON with all rows + volumetrics + meta).
   The `_meta` block MUST include `output_prefix` and `target_tables`:
   ```json
   {
     "_meta": {
       "target_database": "fdp_uk_mortgage_db",
       "target_table": "mortgage_account",
       "target_tables": ["mortgage_account"],
       "output_prefix": "fdp_uk_mortgage_db_mortgage_account",
       "classification": { ... },
       ...
     },
     "mapping_rows": [ ... ],
     "source_volumetrics": [ ... ]
   }
   ```
   `target_table` is kept for backward compatibility (set to the first/primary table).
   `target_tables` is the canonical array of all distinct target tables.

   When `io_mode` is not `table`, include file I/O metadata in the `_meta` block:
   ```json
   {
     "_meta": {
       ...
       "io_mode": "file|hybrid",
       "source_io": { "sources": [{"logical_name": "customer_events", "storage_path": "s3://raw-bucket/data/customer_events/", "format": "parquet"}] },
       "target_io": { "logical_name": "customer_events_clean", "format": "parquet", "write_mode": "overwrite" }
     }
   }
   ```
   Omit `io_mode`, `source_io`, and `target_io` from `_meta` when `io_mode == "table"` (default — backward compatible).

   If `intermediate_steps` is non-empty (multi-statement ETL), include a `transformation_lineage` section:
   ```json
   {
     "_meta": { ... },
     "mapping_rows": [ ... ],
     "source_volumetrics": [ ... ],
     "transformation_lineage": {
       "schema_version": "1.1",
       "intermediate_steps": [ ... ],
       "column_lineage_chains": { ... },
       "effective_source_filters": { ... },
       "resolved_variables": { ... }
     }
   }
   ```
   Omit `transformation_lineage` entirely when `intermediate_steps` is empty (single-statement SQL — backward compatible).
2. Write `{PROV_JSON}` (per-field evidence metadata)
3. Write `{VAL_REPORT}` (validation results)
4. Write `{STTM_XLSX}` via Bash + openpyxl (built from scratch — no template file dependency):
   - Create new workbook with "Mapping" sheet + "Source Volumetrics" sheet
   - Write headers at Row 1 with formatting per `templates/mapping_spec.md`
   - Set column widths, freeze panes (A2), tab colors (Blue/Green)
   - Populate mapping data starting at Row 2
   - Populate Source Volumetrics starting at Row 2
   - Save — output has exactly 2 sheets
5. Write `{PROV_XLSX}` via Bash + openpyxl (uses same logic as `/sttm-export`):
   - Read `{PROV_JSON}`
   - Sheet 1 "Field Provenance" (Blue tab): One row per field per target column —
     Target Table, Target Column, Field Name, Value, Confidence, Method, Evidence,
     Source Priority, Artifact Reference, Business Rule Reference
   - Sheet 2 "Business Rules" (Orange tab): Aggregated BR index —
     Rule ID, Target Table, Affected Columns, Rule Description, Source Document
   - Save — separate file from sttm.xlsx for review/validation purposes
6. Write `output/.sttm_manifest.json` — output discovery manifest for downstream commands:
   ```json
   {
     "schema_version": "1.0",
     "output_prefix": "{output_prefix}",
     "target_database": "{target_database}",
     "target_tables": ["{table1}", ...],
     "files": {
       "sttm_json": "{STTM_JSON}",
       "sttm_xlsx": "{STTM_XLSX}",
       "provenance_json": "{PROV_JSON}",
       "provenance_xlsx": "{PROV_XLSX}",
       "validation_report": "{VAL_REPORT}"
     }
   }
   ```

### Step 9B — CLEANUP

Remove intermediate files unless `--debug` flag was set:
```bash
rm -rf output/.intermediate/
```

If `--debug` is set, keep intermediate files and report: "Debug mode: intermediate files preserved at output/.intermediate/"

**Note:** `output/.sttm_manifest.json` and `output/sttm_session_state.json` are NOT deleted during cleanup — they persist for downstream command discovery and session tracking.

### Step 9C — FINAL SESSION STATE UPDATE

Write final session state to `output/sttm_session_state.json`:
- `step_8_export: "completed"`
- `overall_status: "completed"`
- `output_files`: all 5 output file paths
- Preserve all earlier state (classification, validation_result, ingestion_status, etc.)

### Completion

Report to user:
- Classification:
    Data Product Type: {data_product_type}
    Table Type: {table_type}
    Crypto Aspect: {crypto_aspect}
- Rows generated: {count}
- Source tables: {list}
- Validation: {pass}/{warning}/{blocker}
- Output files:
    {STTM_JSON}
    {STTM_XLSX}
    {PROV_JSON}
    {PROV_XLSX}
    {VAL_REPORT}

---

## Context Management (Internal Processing — Does NOT Change Output)

These strategies prevent context overflow on large inputs. Business output is identical with or without them — they only control internal processing efficiency.

### Context Inventory (after Step 1)

After INGEST, produce a manifest and write to `output/.intermediate/context_inventory.json`:
- `target_column_count`: Count of target columns
- `source_table_count`: Count of source tables
- `code_lines`: Total code artifact size (lines)
- `join_count`: Number of joins detected in code (estimated from JOIN keyword count)
- `design_doc_count`: Count of design docs
- `code_chars`: Total code artifact size (characters)
- `code_prescan`: Full structural pattern pre-scan results from Step 1.0c (pattern counts, table refs, parameters, self-referential flag)
- `implicit_join_count`: Count of implicit (comma-separated FROM) joins detected in code pre-scan
- `parameter_inventory`: List of all `:param_name` / `@param_name` references found across code files
- `self_referential`: Boolean — whether the target table also appears as a source in FROM/JOIN clauses
- `output_prefix`: Computed output file prefix from Step 1.1 (e.g., `fdp_uk_mortgage_db_mortgage_account`)
- `target_tables`: Array of distinct target table names (e.g., `["mortgage_account"]`)
- `ingestion_complete`: Boolean — whether the Step 1.0e completeness gate passed
- `file_read_detected`: Boolean (true if `code_prescan.file_read` count > 0)
- `file_write_detected`: Boolean (true if `code_prescan.file_write` count > 0)

**If target columns > 50**: enable COLUMN BATCHING mode for Steps 5 and 6.

### Adaptive Batch Size Calculation (after Context Inventory)

When COLUMN BATCHING is active, calculate the effective batch size using complexity weights from `${CLAUDE_PLUGIN_ROOT}/configs/sttm/template_spec.yaml` → `context_management.adaptive_batching`:

```
effective_batch = base_columns
                  - floor(code_lines / code_lines_divisor)
                  - floor(source_table_count / source_tables_divisor)
                  - floor(join_count / join_count_divisor)
```

Clamp result to `[min_batch_size, max_batch_size]` → `[15, 50]`.

**Example** (the failing 109-column case: 7,769 LOC, 38 source tables, 35 joins):
```
50 - floor(7769/2000) - floor(38/5) - floor(35/3) = 50 - 3 - 7 - 11 = 29
→ effective_batch = 29 → 4 batches of ~27 columns instead of 3 batches of 50/50/9
```

For simple inputs (<2000 LOC, <10 tables, <5 joins): no penalties apply → batch size stays at 50.

Log the calculation: `"Adaptive batch size: {effective_batch} (penalties: code={code_penalty}, tables={table_penalty}, joins={join_penalty})"`

### Pre-Flight Budget Estimation (after Adaptive Batch Size Calculation)

Estimate token requirements before execution to proactively activate context management:

**Token estimation formula:**
```
lineage_cost = 5000 + (code_chars / 3) + (target_column_count * 150)
per_batch_cost = 5000 + 3000 + (effective_batch * 300) + (join_count * 50)
total_gen_cost = per_batch_cost * ceil(target_column_count / effective_batch)
estimated_total = lineage_cost + total_gen_cost + 10000  (validation + export overhead)
```

**Decision thresholds** (based on estimated_total vs available context budget):
- **< 80% budget**: Proceed normally. File-based handoffs are optional (used only if COLUMN BATCHING is already active).
- **80–100% budget**: Force file-based handoffs for ALL stages (lineage, generation, validation). Even sub-50-column tables use file I/O to preserve headroom.
- **> 100% budget**: Force file-based handoffs + reduce batch size further (apply 0.8 multiplier to effective_batch, re-clamp to [15, max]) + log warning to user:
  ```
  ⚠️ Large input detected ({target_column_count} columns, {code_lines} lines of code, {source_table_count} source tables).
  Using aggressive context management. Processing may take longer but output quality is preserved.
  ```

Log estimation: `"Pre-flight estimate: ~{estimated_total} tokens (lineage: {lineage_cost}, generation: {total_gen_cost}, overhead: 10000)"`

### Answer Compression (after Step 2)

After INTERVIEW completes, compress all answers to compact key:value format:
```
{load_type: "incremental", partition_column: "dw_bus_dt", scd_type: "scd2", day0_range: "2024-01-01 to current", dedup: "latest_by_mod_date"}
```
- Drop full question text, options, and skip_if logic
- Keep only: answer value + mapped field
- This compact summary replaces full Q&A for all downstream stages
- Same answers reach downstream — just smaller representation

### Focused Lineage (Step 5 scoping)

Pass to sttm-sql-lineage-agent ONLY:
- Code artifacts (full SQL/PySpark — cannot split)
- Target column names (ALL columns — not batched)
- Known source tables
- `output_file`: `output/.intermediate/lineage_cache.json` (when file-based handoff is active)

Do NOT pass: interview answers, design docs, config files, profiling data (none needed for SQL parsing).

**Single invocation model (replaces per-batch SQL parsing):**
Run sttm-sql-lineage-agent ONCE for ALL target columns. The agent writes full lineage output to `output/.intermediate/lineage_cache.json` and returns only a compact summary. This eliminates redundant SQL parsing across batches (~30K tokens saved for complex inputs).

**If COLUMN BATCHING active:**
Per-batch lineage subsets are extracted from the cache via Python (no additional agent invocations):

If `python_path == null`: use Read/Write tools as fallback.

```python
{python_path} -c "
import json, sys
batch_cols = json.loads(sys.argv[1])  # list of target column names for this batch
with open('output/.intermediate/lineage_cache.json') as f:
    cache = json.load(f)
batch_lineage = [l for l in cache.get('lineage', []) if l.get('target_column') in batch_cols]
batch_data = {
    'lineage': batch_lineage,
    'joins_detected': cache.get('joins_detected', []),
    'filters_extracted': cache.get('filters_extracted', {}),
    'union_metadata': cache.get('union_metadata'),
    'merge_metadata': cache.get('merge_metadata'),
    'temp_table_chain': cache.get('temp_table_chain', []),
    'intermediate_steps': cache.get('intermediate_steps', []),
    'column_lineage_chains': cache.get('column_lineage_chains', {}),
    'effective_source_filters': cache.get('effective_source_filters', {}),
    'resolved_variables': cache.get('resolved_variables', {})
}
batch_num = sys.argv[2]
with open(f'output/.intermediate/batch_{batch_num}_lineage.json', 'w') as f:
    json.dump(batch_data, f, indent=2)
print(f'Batch {batch_num}: {len(batch_lineage)} lineage entries extracted')
" '["col1","col2",...]' N
```

Each batch's sttm-row-generator-agent reads from `batch_{N}_lineage.json` instead of receiving lineage inline. JOIN chain and filters (query-level context) are included in every batch file — they are shared across all batches.

### Scoped Generation (Step 6 scoping)

Pass to sttm-row-generator-agent ONLY:
- Target columns (batch or full)
- Resolved lineage per column (for this batch only — via `lineage_file` when file-based)
- join_chain (full — same for all batches; included in batch lineage file)
- filters_extracted (full — same for all batches; included in batch lineage file)
- Classification object (all 4 axes)
- Interview summary (compact key:value form)
- audit_columns config (from `config/audit_columns.yaml`)

Do NOT pass: full scenarios.yaml (only active scenario section), raw SQL code (lineage already extracted), full precedence.yaml, design docs, profiling beyond what's needed.

**If COLUMN BATCHING active (file-based handoff):**
- Split into batches of `effective_batch` columns (adaptive size from Step 0 calculation)
- For each batch, pass:
  - `lineage_file`: `output/.intermediate/batch_{N}_lineage.json`
  - `output_file`: `output/.intermediate/batch_{N}_rows.jsonl`
  - `volumetrics_file`: `output/.intermediate/batch_{N}_volumetrics.json`
- First batch's first row gets `additional_context`; all subsequent batches set `additional_context = ""`
- Row-generator-agent reads lineage from file, writes rows/volumetrics to file, returns only summary
- After all batches complete: merge via the Python merge script (see Step 6 file-based generation output above)
- Source Volumetrics: accumulated across batch files, deduplicated at merge

### Focused Guided Mode (Step 8A scoping)

- Present maximum 10 unresolved fields per guided mode iteration
- Priority order: BLOCKERs first, then WARNINGs
- Per field: show ONLY that field's evidence (not entire provenance history)
- After resolving a batch of 10: re-check remaining — some may cascade-resolve
- Repeat until all below-threshold fields are resolved or deferred
