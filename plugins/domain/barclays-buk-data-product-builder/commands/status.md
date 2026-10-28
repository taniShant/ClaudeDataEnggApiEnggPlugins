---
description: Display current session gate status and artefact progress
disable-model-invocation: false
---

# /status

Display the current session state in a human-readable panel. Shows **per-target-table artefact generation status**. Read-only — does not modify any files.

## How It Works

`/status` displays artefact generation progress for **each target table independently**:

- **Glue**: Shows status for each target table's {db}_{table}_wrapper.py, {db}_{table}_config.json, transform files (day0/day1 conditional), dtxog, and DAG under `generated/glue/`
- **Databricks**: Shows status for each target table's {schema}_{table}_transform.py, {schema}_{table}_driver.py, {schema}_{table}_config.yml, and DAG under `generated/databricks/src/Notebooks/`, plus shared utilities (table_creation_utility.py, date_control_insert_utility.py) and databricks.yml bundle
- **Multi-table**: Lists all tables side-by-side with individual completion status

Example multi-target output:
```
TABLE 1: account_wm     ✅ wrapper ✅ config ✅ dtxog ✅ dag
TABLE 2: rates_fees     ✅ wrapper ✅ config ⏳ dtxog — dag
TABLE 3: mortgage_detail ⏳ wrapper — config — dtxog — dag
```

## Usage

```
/status
```

## Output Format

```
═══════════════════════════════════════════════════════
  DE AGENT — SESSION STATUS
  Session: {session_id}    Created: {created_at}
═══════════════════════════════════════════════════════

PLATFORM         {platform or "⛔ NOT SET — run /init and answer G1"}
DATA PRODUCT TYPE {data_product_type or "⛔ NOT SET — answer G1.5"}
TENANCY          {tenancy_name or "⚠️  Not yet resolved"}
TARGET ACCOUNT   {target_account or "—"}

MAPPING EXCEL    {mapping_excel_path or "None"}
DOMAIN KNOWLEDGE {domain_knowledge_path or "None — intent identification will use mapping + G5 questions"}

─── GATES ──────────────────────────────────────────────
G1   Platform          {✅ or ⛔}  {platform or "Awaiting answer"}
G0.5 Domain Knowledge  {✅ or ⚪}  {Provided / Skipped}
G1.5 Data Product Type {✅ or ⛔}  {type or "Awaiting answer"}
G3   Mesh JSON S3      {✅ or ⛔ or N/A} {env summary or "Databricks — not required"}
G4   Classification    ✅            {Completed via local sources (Volumetrics / DK / Mapping)}
G5   Config values     {✅ or ⚠️}   {Resolved / Open: {count} values}

─── ARTEFACTS ──────────────────────────────────────────
{For each artefact in artefact_status:}
  {status_icon}  {filename}    [{VALIDATED / GENERATED / DRAFT_UNVALIDATED}]

─── DAG SCHEDULE (only if dag_spec.json exists) ────────
{If session/dag_spec.json exists:}
  Schedule Type:  {schedule_type}
  Cron:           {cron_expression or "N/A — business_calendar / adhoc"}
  Catchup:        {catchup}
  Skip Holidays:  {skip_bank_holidays}
  Dependencies:   {total dependency count across all tables} external dep(s)
  Sequential:     {sequential_processing}
{If session/dag_spec.json does NOT exist:}
  DAG Schedule:   — Not yet generated (run /gen-dag)

─── OPEN PLACEHOLDERS ───────────────────────────────────
{If none: "None — all values resolved ✅"}
{For each open placeholder:}
  {{placeholder_name}}  in {artefact_file}  — {reason}

─── CRYPTO STATUS ───────────────────────────────────────
{If no crypto: "No crypto columns detected"}
{If crypto: "Crypto active for {N} column(s)"}
  {For each crypto column:}
    {col_name}  {operation}  DE: {de_name or "EXTRACTION FAILED — see refusal"}

─── PYTHON RUNTIME & TEST STATUS ───────────────────────
Python runtime fields — per `agents/refs/python-runtime-contract.md § Session State Fields`.
Python:        {python_path or "NOT AVAILABLE — set PYTHON_PATH"}
{If syntax_check_result == "passed": "Syntax Check:  ✅ Passed"}
{If syntax_check_result == "failed": "Syntax Check:  ⚠️  FAILED — " + syntax_check_failures.length + " file(s) with errors"}
{If syntax_check_result == "skipped_no_python": "Syntax Check:  ⚠️  Skipped (no Python)"}
{If syntax_check_result is null: "Syntax Check:  — Not yet run"}
{If test_execution_result == "passed": "Test Execution: ✅ Passed"}
{If test_execution_result == "failed": "Test Execution: ⚠️  FAILED (non-blocking) — run /run-tests --verbose"}
{If test_execution_result == "skipped_no_python": "Test Execution: ⚠️  Skipped (no Python)"}
{If test_execution_result == "skipped_no_pytest": "Test Execution: ⚠️  Skipped (pytest not installed)"}
{If test_execution_result == "skipped_user_declined": "Test Execution: ⚪ Skipped (user declined)"}
{If test_execution_result == "timeout": "Test Execution: ⚠️  Timed out — run manually"}
{If test_execution_result is null: "Test Execution: — Not yet run"}
{If contract_reconciliation_result == "passed": "Contract Check: ✅ Passed"}
{If contract_reconciliation_result == "failed": "Contract Check: ⚠️  FAILED — review violations before /push"}
{If contract_reconciliation_result == "skipped": "Contract Check: ⚪ Skipped"}
{If contract_reconciliation_result is null: "Contract Check: — Not yet run"}

─── AUTO-CHAIN STATUS (only if full-automation) ─────────
{If auto_chain.enabled == true:}
  Mode:      Full-automation
  Status:    {Running / Halted at step {N}: {command} / Complete}
  {If halted:}
    Halted:    Step {halted_at_step} ({halted_at_command})
    Reason:    {halt_reason}
    Since:     {halted_at_timestamp}
    Report:    {report_generated or "—"}
    Completed: Steps {completed_steps list}
    Fix:       Create session/intent_overrides.json → run /resume
  {If intent_overrides_applied:}
    Overrides: Applied ✅

─── NEXT REQUIRED ACTIONS ───────────────────────────────
{Auto-generated list of what's blocking progress}
{If test_execution_result is null or "failed" AND all gen phases complete:}
  • Consider running /run-tests before /push
{If syntax_check_result == "failed":}
  • Fix syntax errors in listed files before /push (push will be blocked)
```

## Status Icons

- ✅ Complete/Resolved
- ⛔ Blocking gate not resolved
- ⚠️  Warning / partial
- ⚪ Optional / skipped
- 📄 Generated
- ✔️  Validated

## Data Sources (STRICT — no filesystem scanning)

Read ONLY these files — do NOT glob, search, or scan any directories:
1. `session/session_state.json` — all gate, artefact, placeholder, crypto, and table_status data
2. `session/validation_results.json` — validation status (if exists)
3. `session/placeholders.json` — open placeholder details (if exists)
4. `session/dag_spec.json` — DAG schedule and dependency info (if exists)

The `artefact_status` map in session state already contains every generated file path and its status. The `table_status` map contains per-table generation progress.

Do NOT use Glob, find, ls, or directory listing to discover artefacts — trust session state as the single source of truth. If session state is missing or empty, report "No session found — run /init" rather than scanning.

## No Modification

`/status` is read-only. It reads the files listed above. It writes nothing.
