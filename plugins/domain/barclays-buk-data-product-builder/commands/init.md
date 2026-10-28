---
description: Initialize DE session from mapping Excel — invoke when user provides a mapping document or says start/begin pipeline
disable-model-invocation: false
argument-hint: <excel_path> [--platform glue|databricks] [--domain-knowledge <path>] [--full-automation]
---

# /init

Initialise a new DE Agent plugin session. Registers the mapping Excel file, optionally accepts a Domain Knowledge file, creates session state, and sets platform.

## ℹ️ What Gets Generated

This command initializes a session that will generate **per-target-table artefacts**:

- **Single-target mapping** (1 table in Excel) → 1 wrapper+config pair (Glue) or 1 driver+DDL pair (Databricks)
- **Multi-target mapping** (3 tables in Excel) → 3 independent wrapper+config pairs (Glue) or 3 independent driver+DDL pairs (Databricks)

Each target table gets its **own independent artefact set**, not shared or merged. See [/gen-wrapper](/gen-wrapper), [/gen-driver](/gen-driver), [/gen-ddl](/gen-ddl) for per-target output details.

## Usage

```
/init <excel_path> [--platform <glue|databricks>] [--domain-knowledge <dk_path>] [--full-automation]
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `<excel_path>` | Yes | Absolute or relative path to the mapping Excel (.xlsx) file |
| `--platform <glue\|databricks>` | For `--full-automation` | Target platform. If omitted and `--full-automation` not set, user is prompted |
| `--domain-knowledge <dk_path>` | No | Path to the Domain Knowledge .md file for this domain |
| `--full-automation` | No | Enable full-automation mode (auto-decision-agent resolves ambiguities autonomously when possible; asks user when evidence insufficient; requires `--platform`) |

## Full-Automation Mode

When `--full-automation` flag is set:

**Requirements:**
- `--platform` MUST be specified (glue or databricks)
- Ambiguities resolved via auto-decision-agent when evidence is sufficient; asks user when not

**Behavior:**
1. **Platform locked** — No G1 prompt; platform set from `--platform` argument
2. **Auto-decision-agent invoked** for all ambiguities:
   - Applies 7-rule framework (Safety → Patterns → Preserve → Conservative → Compile-First → Tests → Majority)
   - Resolves decisions autonomously when structural evidence or domain knowledge provides sufficient confidence
   - Logs all auto-resolved decisions to `session/audit_log.jsonl`

3. **User is still asked when evidence is insufficient:**
   - `AskUserQuestion` is NOT blocked — even in full-automation mode
   - If auto-decision-agent reaches LOW confidence or UNRESOLVED → asks user for clarification
   - Critical decisions (table_type, source_table_type, crypto operation) with no structural evidence always ask
   - Generating incorrect artefacts silently is worse than pausing to ask one question

4. **Post-execution review recommended:**
   - Check `session/audit_log.jsonl` for any medium-confidence decisions
   - Validate with domain experts if decisions are non-obvious

5. **Fallback behavior:**
   - If auto-decision-agent cannot resolve from rules → asks the user
   - User's answer is logged with `identification_source: "user_asked"`, confidence: HIGH

**Example:**
```bash
/init Mortgage_Mapping.xlsx --platform glue --full-automation
# Platform: glue (locked, no prompt)
# Automation: ON (all gates auto-decided except G5-C crypto halts)
# Result: Fully automated generation

/init Mortgage_Mapping.xlsx --platform databricks --domain-knowledge custom_rules.md --full-automation
# Platform: databricks (locked, no prompt)
# Domain Knowledge: custom_rules.md (auto-loaded)
# Automation: ON
# Result: Fully automated generation with custom domain context
```

---

## Behaviour

0. **Model capability check** (non-blocking warning):
   - If the current session model is `haiku-default` (or any haiku variant), display:
     ```
     ⚠️ Session model is haiku-default. The /init command involves multi-step
     reasoning (JSON write-verify, conditional branching, Python detection)
     that may be unreliable with haiku on first attempt.
     
     Recommended: Use sonnet-default or higher for sessions using this plugin.
     ```
   - If `--full-automation` is set: also write audit entry `{"event": "init_model_warning", "model": "haiku-default", "mode": "full-automation"}` — then continue (do not block automation).
   - In all cases: proceed after displaying the warning. This is advisory only — do not block (Principle 7).

0.5. **Partial state recovery (warm-start fast-path):**
   Before creating a new session, check if `session/session_state.json` exists with partial state from a failed previous attempt:
   - Read `session/session_state.json` (if it exists).
   - If the file exists AND contains a valid `session_id` AND `mapping_excel_path` matches the current `<excel_path>` argument:
     - This is a **warm start** — a previous `/init` for the same mapping failed mid-execution.
     - Identify which steps already completed:
       - `session_id` present → step 3 done
       - `platform` is non-null → step 9/G1 done
       - `python_path` is non-null → step 7 done
       - `domain_knowledge_text` is non-null → step 6 done
       - `auto_chain` is non-null (full-automation) → auto-chain init done
     - Display: `ℹ️ Resuming partial init from previous attempt (session: ${session_id}). Completed: [list]. Resuming from step ${N}.`
     - Write audit entry: `{"event": "init_warm_start", "session_id": "${session_id}", "completed_steps": [...]}`
     - **Skip to the first incomplete step** — do not re-execute completed steps.
   - If the file exists BUT `mapping_excel_path` does NOT match the current `<excel_path>`:
     - This is a **fresh start** for a different mapping. Fall through to step 1 (stale session detection in step 4 handles the warning).
   - If the file does not exist:
     - This is a **cold start**. Proceed to step 1 normally.

1. Validate the Excel file exists and is readable (check file extension is `.xlsx`). Refuse with error if unreadable or not found.
2. **Validate platform argument** (if provided):
   - Accept: `glue`, `databricks`, `1`, `2`, `AWS Glue`, `Databricks`
   - If invalid, log and refuse:
     ```
     [ERROR] Platform validation failed: provided='${platform_arg}', accepted=['glue','databricks','1','2','AWS Glue','Databricks']
     ```
     Write audit entry: `{"event": "init_platform_validation_failed", "provided": "${platform_arg}"}`
   - If `--full-automation` set but `--platform` NOT provided: error and refuse
3. Generate a unique `session_id` (timestamp-based, e.g. `de_20260603_143022`).
4. **Stale session detection** — Before writing, check if `session/session_state.json` already exists:
   - If exists: read the existing file and extract `session_id` and `platform`
   - Display warning:
     ```
     ⚠️ Existing session found: ${existing_session_id} (platform: ${existing_platform})
     This session will be OVERWRITTEN. Previous session state and checkpoints will be lost.
     If you intended to resume the previous session, use /resume instead.
     ```
   - **Interactive mode** (when `--full-automation` is NOT set): Ask user for confirmation before proceeding:
     ```
     Proceed with overwrite? (yes/no)
     ```
     If user responds `no` or equivalent → abort `/init` with message: `Init cancelled. Use /resume to continue the existing session.`
   - **Full-automation mode** (when `--full-automation` IS set): Proceed without confirmation (automation must not block on prompts).
   - Write audit entry: `{"event": "stale_session_overwritten", "old_session_id": "${existing_session_id}", "old_platform": "${existing_platform}", "new_session_id": "${new_session_id}"}`
   - Proceed with overwrite

5. Write initial session state to `session/session_state.json`:
   - `session_id`, `created_at`, `mapping_excel_path`
   - `platform` (from `--platform` or null if user will be prompted)
   - `domain_knowledge_path` (from `--domain-knowledge` or null — auto-discovery deferred to `/parse-mapping`)
   - `domain_knowledge_text` (null — populated during `/parse-mapping`)
   - All gate fields null; `gates_resolved: ['G1']` (if platform provided) or `gates_resolved: []` (if not)
   - **BLOCKING verification (with retry):** After writing, immediately read back `session/session_state.json` and verify `session_id` matches the generated value.
   - If read-back succeeds and `session_id` matches → continue to step 6.
   - If read-back fails or `session_id` mismatch → **retry the write ONCE** (re-write the full session state JSON, then read back again).
   - If retry also fails:
     ```
     [ERROR] Session state write failed after retry — cannot continue. Verify session/ directory exists and is writable.
     ```
     Write audit entry: `{"event": "init_session_write_failed", "expected_session_id": "${session_id}", "retried": true}`
     Stop and return FAILURE. Do NOT proceed to subsequent steps.
6. If `--domain-knowledge` provided: invoke `domain-knowledge-loader` agent (using the Agent tool) to read and store user-provided file. If file unreadable: log WARN and continue (non-blocking).
7. **Python runtime validation** (non-blocking) — follow `agents/refs/python-runtime-contract.md § Detection Algorithm`:
   - Run `python --version` — if exit code 0: store `session_state.python_path = "python"` and `session_state.python_version = "<detected version>"`
   - Else if `PYTHON_PATH` environment variable is set → use that value directly as `python_path`
   - Else run `python3 --version` — if exit code 0: store that path
   - Else run `py --version` — if exit code 0: store `py` (Windows launcher)
   - If all fail: log WARNING and store `python_path = null`:
     ```
     ⚠️ Python not found on PATH.
     Impact:
       • Syntax validation (py_compile) will be SKIPPED on generated .py files
       • Test execution (pytest) will be SKIPPED
       • Test generation and all other artefact generation still works (no Python needed)
     To enable:
       • Ensure 'python' is on PATH (most common)
       • export PYTHON_PATH="/path/to/python"
       • Or add to .claude/settings.json: { "env": { "PYTHON_PATH": "/path/to/python" } }
     ```
   - Store `session_state.python_path` for all downstream Python invocations — downstream commands read this value, never re-probe
   - This check is **non-blocking** — session initialization always continues regardless
8. Write audit log entry to `session/audit_log.jsonl`.
9. **IF `--platform` NOT provided** (interactive mode only): Display Gate G1 question:

---

**Gate G1 — Platform Selection (IF `--platform` NOT provided)**

If user did NOT provide `--platform` argument, display:

```
Which compute platform is this pipeline targeting?

- **1** or **glue** — AWS Glue (DTX/DTXOG framework) — wrapper.py, dtxog config, Mesh JSON
- **2** or **databricks** — Databricks (BUK CDAO standard PySpark `.py` scripts + foundation library) — transform.py, driver.py, Iceberg DDL

Reply with 1/2 or glue/databricks:
```

Wait for user response; validate and set `session_state.platform`.

**IF `--platform` PROVIDED** (at command line or during `/init`):
- No G1 prompt; platform already set
- Add `"G1"` to `gates_resolved` array

---

## About Gate G1.5 (Data Product Type)

**G1.5 is NOT asked during /init.** Instead:

1. DP type is **automatically derived** from the target database prefix during `/parse-mapping`
2. Valid prefixes: `fdp_*` (FDP), `cdp_*` (CDP), `bdp_*` (BDP), `shared_fdp_*` (FDP), `shared_cdp_*` (CDP), `shared_bdp_*` (BDP)
3. Shared-prefix databases resolve to the same parent DP type as their non-shared counterparts (`shared_fdp_*` + `fdp_*` = both FDP, not a mixed error)
4. Invalid prefix (e.g., `stg_`, `tmp_`, `shared_stg_*`) → ERROR; require user to correct mapping Excel
5. Multi-table mapping with MIXED parent DP types (e.g., `fdp_*` and `cdp_*`, or `shared_fdp_*` and `bdp_*`) → ERROR; cannot mix DP types in one session

G1.5 is marked as "RESOLVED" in `gates_resolved` after `/parse-mapping` without any user interaction.

---

## Session State Written

```json
{
  "session_id": "de_<timestamp>",
  "created_at": "<iso8601>",
  "mapping_excel_path": "<path>",
  "domain_knowledge_path": "<path_or_null>",
  "domain_knowledge_text": null,
  "platform": null,
  "gates_resolved": [],
  "open_placeholders": [],
  "auto_chain": null,
  "intent_overrides_applied": false
}
```

**If `--full-automation` flag is set**, also initialize:
```json
{
  "auto_chain": {
    "enabled": true,
    "chain_mode": true,
    "halted_at_step": null,
    "halted_at_command": null,
    "halt_reason": null,
    "halted_at_timestamp": null,
    "completed_steps": [],
    "report_generated": null
  }
}
```

**Auto-chain verification (full-automation only, with retry):**
After writing `auto_chain` to session state, read back `session/session_state.json` and verify:
- `auto_chain.enabled === true` and `auto_chain.chain_mode === true`
- Log: `[INFO] Auto-chain initialized: platform=${platform}, chain_mode=true`
- Write audit entry: `{"event": "auto_chain_initialized", "platform": "${platform}"}`
- If verification fails → **retry the write ONCE** (re-write auto_chain to session state, read back again).
- If retry also fails:
  ```
  [ERROR] Auto-chain initialization failed after retry — auto_chain object not persisted correctly.
  ```
  Write audit entry: `{"event": "auto_chain_init_failed", "platform": "${platform}", "retried": true}`
  Stop and return FAILURE.

> **Note**: Domain knowledge auto-discovery is deferred to `/parse-mapping` (which already reads the full Excel to extract `target_database`). This avoids reading the Excel file twice. If `--domain-knowledge` is explicitly provided, it is loaded immediately during `/init`.

### Override Auto-Discovery

The `--domain-knowledge` path is resolved relative to the user's project directory (or as an absolute path). This takes precedence over auto-discovery from the plugin installation directory (`${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/`).

```bash
/init Mortgage_Mapping.xlsx --domain-knowledge ./my_project_docs/custom_mortgage_rules.md
# → Uses user-provided project-relative path immediately; skips auto-discovery from plugin directory
```

---

## Phase Dispatch (Full-Automation Only)

After ALL `/init` steps (1-9) complete successfully AND `--full-automation` is set:

1. The main conversation MUST read `${CLAUDE_PLUGIN_ROOT}/commands/refs/init-full-automation.md`
2. The main conversation MUST immediately dispatch Phase A (Discovery) agent
3. Phase dispatch is the main conversation's responsibility — it is NOT automatic

**If `/init` fails (any step returns FAILURE):** Session state is NOT created or is incomplete. The user MUST fix the issue and re-run `/init`. Do NOT attempt to dispatch Phase A with missing or partial session state.

### Success Output

```
✓ Session initialized: ${session_id}
  Platform:         ${platform}
  Mapping:          ${mapping_excel_path}
  Domain Knowledge: ${dk_path || 'none'}
  Full-Automation:  ON — Phase A (Discovery) will be dispatched next
```

### Failure Output

```
✗ Session initialization FAILED at step ${N}
  Error: ${error_message}
  Action: Fix the issue and re-run /init
```

---

## On-Demand References

- **Full-Automation mode** (hook lifecycle + auto-chain pipeline): When `--full-automation` is set, after steps 1-9 complete, Read `${CLAUDE_PLUGIN_ROOT}/commands/refs/init-full-automation.md` for the complete execution protocol.
- **Git Log Recovery**: If session state file is lost/corrupted, Read `${CLAUDE_PLUGIN_ROOT}/commands/refs/init-recovery.md` for the fallback recovery protocol.

---

## Anti-Hallucination Rules

- NEVER infer, guess, or display **Data Product Type** (FDP/CDP/BDP) during `/init`. DP type is resolved ONLY during `/parse-mapping` (G1.5) by reading the target database prefix from parsed Excel rows. The filename of the Excel is NOT a valid source.
- NEVER infer, guess, or display **Tenancy** during `/init`. Tenancy is resolved ONLY during `/parse-mapping` Step 2.1 (G0.5) via SKILL.md tenancy registry lookup against the actual `target_database` value.
- Do NOT show "DP TYPE", "TENANCY", or similar lines in `/init` output — these fields are unknown at this stage and must remain unresolved until `/parse-mapping` runs.
- The Excel filename (e.g., "Mortgage_Mapping.xlsx") is NOT a valid source for inferring DP type, tenancy, domain, or any routing field.
- `/init` output must ONLY contain: session ID, mapping file path, platform (if provided or after G1), domain knowledge path (if explicitly provided via `--domain-knowledge`), and next steps.

## Failure Modes

- Excel file unreadable or not found → Refuse with: "Cannot read mapping Excel at `<path>`. Please provide a valid .xlsx file path."
- Auto-discovered domain knowledge file not found → Continue silently (non-blocking); `dk_found: false`
- Domain Knowledge file provided but unreadable → WARN: "Domain Knowledge file unreadable — continuing without it. Intent identification will rely on mapping document and G5 questions."
- Unknown DP type prefix in target_database → Log WARNING, skip auto-discovery, continue
