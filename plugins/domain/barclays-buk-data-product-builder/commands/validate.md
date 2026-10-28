---
description: Validate all generated artefacts against platform-specific red flags
disable-model-invocation: false
---

# /validate

Validate all generated artefacts against platform-specific rules. Routes to Glue or Databricks validation agent.

## Usage

```
/validate
```

## Prerequisites

- At least one artefact generated
- Platform locked (G1 resolved)

## Severity Taxonomy

All validators use these canonical severity levels:

| Level | Synonyms | Behaviour |
|---|---|---|
| **BLOCKING** | BLOCK, HALT | Halts the pipeline. Must be resolved before proceeding. |
| **WARNING** | ADVISORY | Logged and reported but does not halt. Pipeline continues. |
| **DRAFT_UNVALIDATED** | _(none)_ | File status marker, not a finding severity. Indicates the artefact has not yet passed validation. |

## Validator Routing Matrix

| Validator | Inline (gen-*/hook) | Batch | Both |
|---|---|---|---|
| crypto-indicator-detector | `/parse-mapping` | Batch 1 | ✓ |
| excel-column-validator | `/parse-mapping` | Batch 2 | ✓ |
| mesh-json-completeness-validator | `/gen-mesh` | Batch 2 | ✓ |
| dtxog-structure-validator | `/gen-dtxog` | Batch 2 | ✓ |
| iceberg-ddl-validator | `/gen-ddl` | Batch 2 | ✓ |
| unity-catalog-validator | — | Batch 2 | |
| scd1-structural-validator | — | Batch 2 | |
| foundation-library-validator | — | Batch 2 | |
| infrastructure-validator | — | Batch 3 | |
| name-origin-validator | hook | Batch 3 | ✓ |
| placeholder-completeness-validator | hook | Batch 3 | ✓ |
| consistency-validator | — | Batch 4 | |
| source-table-type-consistency-validator | — | Batch 4 | |
| cdc-presence-assertion-validator | — | Batch 4 | |
| source-attribution-validator | `/gen-transform` | Batch 4 | ✓ |
| config-transform-alias-validator | — | Batch 4 | |
| contract-reconciliation-validator | — | Batch 4 | |
| code-quality-validator | — | Batch 5 | |
| python-import-validator | — | Batch 5 | |
| pk-null-risk-validator | `/gen-transform` | Batch 5 | ✓ |
| source-column-existence-validator | `/gen-transform` | Batch 5 | ✓ |
| literal-value-fidelity-validator | `/gen-transform` | Batch 5 | ✓ |
| join-predicate-fidelity-validator | `/gen-transform` | Batch 5 | ✓ |
| template-landmark-preservation-validator | hook | Batch 5 | ✓ |
| notebook-format-validator | — | Batch 5 | |
| test-coverage-validator | — | Batch 6 | |
| dag-validation-validator | — | Batch 7 | |

## Behaviour

### Step 0.0 — Chain Mode Output Compression

If `session_state.auto_chain.enabled == true` (full-automation mode):
- **Suppress verbose output:** Do NOT print session_state.json content, per-validator findings details, per-batch progress, or full validation result JSON to conversation.
- **Audit log instead:** Write verbose findings to `session/audit_log.jsonl` and full results to `session/validation_results.json`.
- **Compact return only:** At command completion, emit ONLY:
  ```
  [{step}/{total}] {✓|⚠|✗} /validate — {verdict}: {red_flags} red flags, {warnings} warnings
  ```
- **Halt output:** If REJECTED, emit max 5-line summary of blocking red flags. Full details in `session/validation_results.json`.

---

### Step 0.1 — Chain Checkpoint Loading

Apply `commands/refs/chain-checkpoint-pattern.md`. Checkpoint key: `post_generation` (falls back to `post_intent` if not yet written).

### Step 1: Load Session State

Read `session/session_state.json` to determine platform (glue or databricks).

### Step 2: Batched Validation with Fail-Fast (Context Efficiency)

Validators are grouped into dependency batches. Each batch shares input loading (read once, validate many). Blocking batches halt early to avoid wasting turns on downstream validators when critical issues exist.

**Execution Model:**
- Batches 1-2: run **sequentially** (blocking — fail-fast on any BLOCKING finding)
- Batches 3-5: run **in parallel** (non-blocking — collect all findings)

#### Batch 1 — Crypto Validation (FAIL-FAST)

**Shared input:** `session/crypto_flags.json`, generated files with crypto references

| Validator | Check |
|---|---|
| `crypto-indicator-detector` | DE extraction success, DE pattern format, ProtectorTools package |

**Fail-fast:** If ANY crypto finding is BLOCKING → HALT immediately. Do not run subsequent batches. Crypto issues invalidate all downstream artefacts.

#### Batch 2 — Schema & Structure (FAIL-FAST)

**Shared input:** `session/mapping_parsed.json`, `${CLAUDE_PLUGIN_ROOT}/schemas/mesh_json.schema.json`, `${CLAUDE_PLUGIN_ROOT}/schemas/dtxog_config.schema.json`

| Validator | Check |
|---|---|
| `excel-column-validator` | Required column headers present in mapping |
| `mesh-json-completeness-validator` | Mesh JSON fields match schema (Glue only) |
| `dtxog-structure-validator` | DTXOG config conforms to schema (Glue only) |
| `iceberg-ddl-validator` | Iceberg DDL syntax and column alignment (Databricks only) |
| `unity-catalog-validator` | Unity Catalog FQ name conventions (Databricks only) |
| `scd1-structural-validator` | SCD1 tables have no SCD2 temporal columns |
| `foundation-library-validator` | Foundation library import/usage patterns (Databricks only) |

**Fail-fast:** If ANY structural finding is BLOCKING → HALT. Schema violations mean artefacts are fundamentally malformed.

#### Batch 3 — Infrastructure (parallel, non-blocking)

**Shared input:** `session_state.env_config`, all generated files

| Validator | Check |
|---|---|
| `infrastructure-validator` (Part A) | S3 path patterns, bucket naming |
| `infrastructure-validator` (Part B) | Environment isolation (no cross-env references) |
| `name-origin-validator` | Table/column names trace to mapping document |
| `placeholder-completeness-validator` | All `{{placeholders}}` resolved |

#### Batch 4 — Consistency (parallel, non-blocking)

**Shared input:** `session/mapping_parsed.json`, `session/intent_identification.json`, `session/session_state.json`, `session/source_table_metadata.json`

| Validator | Check | Gate Condition |
|---|---|---|
| `consistency-validator` (Part A) | Glue vs Databricks platform consistency | Always |
| `consistency-validator` (Part B) | DB prefix matching | Always |
| `consistency-validator` (Part C) | Layer rules (BDP→BASE, CDP→BASE violations) | Always |
| `source-table-type-consistency-validator` | Config source grouping matches classification | Always |
| `cdc-presence-assertion-validator` | CDC config completeness | **ONLY if any target table has table_type == "NonTransactional"** — skip for pure Transactional sessions (~3,300 tokens saved) |
| `source-attribution-validator` | Cross-wiring detection | **ONLY if any target table has len(source_tables) > 1** — skip for single-data-flow sessions (~3,100 tokens saved) |
| `config-transform-alias-validator` | Config source aliases match transform references (BLOCK if transform references unknown alias; WARN if config alias unused) | Always |
| `contract-reconciliation-validator` | Runtime API contracts between generic components and generated artefacts (7 checks: API shape, config safety, audit type, day0/day1 contract, constructor kwargs, CDC PK, date_control keys) | **Glue only** — skip for Databricks (has equivalent coverage via foundation-library-validator + R6/R12/R19) |

#### Batch 5 — Code Quality (parallel, non-blocking)

**Shared input:** generated `.py` files

| Validator | Check | Gate Condition |
|---|---|---|
| `code-quality-validator` (Part A) | Unused columns, dead references | Always |
| `code-quality-validator` (Part B) | UDF syntax, crypto call format | Always |
| `pk-null-risk-validator` | PK columns not exposed to NULL-producing patterns (LEFT JOIN nullable side, F.when() without .otherwise(), UDF-derived, unmapped PK) | **ONLY if `session/intent_identification.json` has `primary_key_columns`** — skip if no PKs defined |
| `source-column-existence-validator` | Source columns referenced in transforms exist in mapping | Always |
| `literal-value-fidelity-validator` | Literal values in generated code match mapping transformation_logic | Always |
| `join-predicate-fidelity-validator` | Join conditions in generated code match extracted predicates | **ONLY if `session/extracted_predicates.json` exists** |
| `template-landmark-preservation-validator` | Template structural landmarks preserved in generated output | Always |
| `notebook-format-validator` | Databricks notebook format conventions | **Databricks only** |
| `python-import-validator` | Disallowed platform imports | **Databricks only** — skip for Glue sessions (no wrong-platform imports possible; ~2,800 tokens saved) |

#### Batch 6 — Python Execution Status (INLINE — no agent invocation)

**Implementation:** Batch 6 is executed INLINE by this command (NOT via the validation agent). It performs a pure session state read + string formatting — no agent invocation needed.

Python runtime status — per `agents/refs/python-runtime-contract.md`.

Read `session_state.syntax_check_result` and `session_state.test_execution_result` directly from `session/session_state.json` and format the informational report entries:

| Check | Pass | Warn |
|---|---|---|
| `syntax_check_result == "passed"` | Include: "Syntax: PASSED ({N} files)" | — |
| `syntax_check_result == "failed"` | — | Include: "Syntax: FAILED — {N} files have errors (review before /push)" |
| `syntax_check_result` is null or `"skipped_no_python"` | — | Include: "Syntax: NOT CHECKED — Python unavailable" |
| `test_execution_result == "passed"` | Include: "Tests: PASSED" | — |
| `test_execution_result == "failed"` | — | Include: "Tests: FAILED (non-blocking) — review before /push" |
| `test_execution_result` is null or skipped | — | Include: "Tests: NOT EXECUTED — run /run-tests or ensure Python available" |

**This batch NEVER produces BLOCKING findings.** Syntax errors are enforced at `/push` (Condition 4). Test execution is an advisory signal only.

#### Batch 7 — DAG Validation (parallel with Batches 3-5, non-blocking)

**Gate Condition**: Run ONLY if `session/dag_spec.json` exists (gen-dag was executed). Skip entirely if no DAGs were generated.

**Shared input:** `session/dag_spec.json`, all `generated/{platform}/dags/*.py` files, `session/session_state.json`

| Validator | Check |
|---|---|
| `dag-validation-validator` (R1–R4) | DAG file exists, no placeholders, retries=0, timezone |
| `dag-validation-validator` (R5–R6) | DAG ID convention, Python syntax |
| `dag-validation-validator` (R7–R9) | Sensor config, cross-artefact consistency |

**Blocking findings**: R1 (file missing), R2 (unresolved placeholders), R3 (retries≠0), R4 (wrong timezone), R6 (syntax error) are **BLOCKING** — these are platform mandates and structural requirements.

**Warning findings**: R5 (DAG ID), R7 (sensor timing), R8–R9 (cross-artefact) are **WARNING** — non-blocking but surfaced to the user.

### Platform Routing

**If platform = glue:**
- Run all 5 batches (Batch 2 includes mesh + dtxog validators)
- Source Table Type Validation runs in Batch 4
- Batch 7: DAG validation (if `session/dag_spec.json` exists)

**If platform = databricks:**
- Skip mesh/dtxog validators in Batch 2
- Batch 2 replaces with: Unity Catalog FQ names, Iceberg DDL, foundation library checks
- Batch 4 adds: DDL↔transform partition alignment
- Batch 7: DAG validation (if `session/dag_spec.json` exists)

### Source Table Type Validation (Glue only, in Batch 4)

When `session/source_table_metadata.json` exists (i.e., source classification completed):
- Verify each source in `generated/glue/wrapper/{db}_{table}_config.json` is grouped under the correct type key matching its classification
- Verify filter expressions are consistent with source type (no eff_start_date on Transactional sources)
- BLOCK if any source has no classification (all must be resolved before generation)

### Invoking Validation Agents

Each batch invokes the platform validation agent (using the Agent tool) with:
- `batch_id`: which batch to execute (1-5)
- `shared_input`: pre-loaded data for this batch (loaded ONCE by command, passed to agent)
- `file_paths`: only files relevant to this batch's validators

This prevents the agent from re-reading session metadata for every validator.

**Agent routing**:
- If `session_state.platform == "glue"` → invoke `glue-validation-agent`
- If `session_state.platform == "databricks"` → invoke `databricks-validation-agent`

#### Execution Strategy (Sequential → Parallel)

**Sequential batches (1-2) — fail-fast:**
Invoke the platform validation agent sequentially. After each batch:
- If any BLOCKING finding → HALT immediately; do not invoke subsequent batches.
- If no BLOCKING findings → proceed to next batch.

**Parallel batches (3-5, 7) — concurrent execution:**
After Batches 1-2 pass (no BLOCKING findings), invoke Batches 3, 4, 5, and 7 using concurrent Agent tool calls with `run_in_background: true`:

```
Agent(description="Validation Batch 3 — Infrastructure",
      prompt="batch_id=3, shared_input=..., file_paths=...",
      run_in_background=true)

Agent(description="Validation Batch 4 — Consistency",
      prompt="batch_id=4, shared_input=..., file_paths=...",
      run_in_background=true)

Agent(description="Validation Batch 5 — Code Quality",
      prompt="batch_id=5, shared_input=..., file_paths=...",
      run_in_background=true)

Agent(description="Validation Batch 7 — DAG Validation",
      prompt="batch_id=7, shared_input=..., file_paths=...",
      run_in_background=true)
# ↑ Only if session/dag_spec.json exists; skip otherwise
```

Wait for all to complete, then merge findings into a single result set.

**Batch 6 — inline (no agent invocation):**
Execute directly in command context after Batches 3-5 complete (see Batch 6 section above). Append informational entries to the report without spawning an agent.

### Output Format (Agent Response)

Platform agent returns structured verdict:

```json
{
  "verdict": "APPROVED|REJECTED",
  "red_flags_found": [
    {
      "issue": "Issue description",
      "location": "file:line",
      "severity": "BLOCKING|WARNING",
      "fix": "Remediation steps"
    }
  ],
  "blocking_issues_count": N,
  "warnings": [...],
  "notes": "..."
}
```

### User-Facing Report

```
✅ VALIDATION APPROVED
or
❌ VALIDATION REJECTED — {{blocking_issues_count}} blocking issue(s)
  1. {{issue}} → {{fix}}
  2. {{issue}} → {{fix}}
```

### Update Session State

Update `artefact_status` in `session/session_state.json`:
- If verdict = "APPROVED" → `"VALIDATED"`
- If verdict = "REJECTED" → `"DRAFT_UNVALIDATED"`

## Output Files

- `session/validation_results.json` (updated with verdict)
- `session/audit_log.jsonl` (new entry with agent invocation)

---

## Integration with Push Agent

The `push-agent` quality gate (Condition 2) invokes this command:
- If verdict = "REJECTED": Refuse push; show red flags and fixes
- If verdict = "APPROVED": Continue to Condition 3 (tests)

---

**Last Updated:** 2026-06-09 (FORGE Phase A5.3)
