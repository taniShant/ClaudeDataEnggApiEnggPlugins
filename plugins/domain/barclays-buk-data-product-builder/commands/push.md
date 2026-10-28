---
description: Push artefacts via quality gates and create merge request
disable-model-invocation: false
argument-hint: "[--jira-id BUKL2CUSX-173655] [--skip-syntax-check]"
---

# /push

Push generated artefacts to remote repository and create merge request. Enforces quality gate checks before push.

## Usage

```bash
/push [--jira-id BUKL2CUSX-173655] [--auto-approve] [--skip-syntax-check]
```

## Arguments

- `--jira-id BUKL2CUSX-173655` (optional) — JIRA ticket ID for commit message and tracking. If omitted, extracted from branch name.
- `--auto-approve` (optional) — Skip user confirmation after validation passes. Useful for CI/CD pipelines.
- `--skip-syntax-check` (optional) — Bypass the syntax check gate when syntax check was never run or was skipped (`null` or `"skipped_no_python"`). Does NOT bypass an explicit `"failed"` result — failures always block. Logged to `session/audit_log.jsonl` for audit trail.

## Prerequisites

- All generation phases complete: parse-mapping, identify-intent, gen-transform, gen-wrapper (Glue) or gen-driver (Databricks), gen-dtxog (Glue), gen-dag (both platforms)
- Platform locked (G1 resolved)
- Branch contains valid JIRA ID or `--jira-id` provided

## Behaviour

### Step 1: Load Session State

```
Loading session state...
```

- Read `session/session_state.json`
- Verify all required fields present (platform, phases, branch info)
- Report error if session corrupted

---

### Step 2: Invoke Push Agent

**Delegate to `push-agent.md`:**

```
Running anti-hallucination verification...
```

#### Verification Checks (5 steps)

1. **Branch name** → Must contain JIRA ID
2. **Remote URL** → Must be `git@app.gitlab.barcapint.com:` (verified with `git remote -v`)
3. **JIRA ID extraction** → From branch or `--jira-id` flag
4. **Build status** → Run tests; all must pass
5. **File modifications** → No secrets, large files, or temp files

**Action on failure:** Report specific verification failure; refuse push

---

### Step 3: Check Quality Gate (Condition 1: Code Review Passed)

**Read `session/code_review_results.json`:**

```
Checking code review status...
```

**Validation:**
- `review_status` must be `"PASS"` — zero Critical AND zero High findings remaining
- If file missing: HALT with error "Code review not run. Execute /review first."
- If `review_status` = `"REJECTED"`: HALT — display remaining Critical/High findings
- If `review_status` = `"FINDINGS"` with only Medium/Low: PASS (auto-fixed or logged)

**Action on failure:** Display unresolved findings; refuse push; instruct user to fix and re-run `/review`

---

### Step 4: Check Quality Gate (Condition 2: Phases Complete)

**Load session_state.phases:**

```
Checking phase status...
  parse_mapping:   ✅ completed
  identify_intent: ✅ completed
  gen_transform:   ✅ completed
  gen_wrapper:     ✅ completed (Glue) or SKIPPED (Databricks)
  gen_dtxog:       ✅ completed (Glue) or SKIPPED (Databricks)
  gen_dag:         ✅ completed or SKIPPED
```

**Validation:**
- For each phase: status must be "completed" OR "skipped" (not "pending", "in_progress", "failed")

**Action on failure:** List incomplete phases; refuse push

---

### Step 5: Check Quality Gate (Condition 3: Validation Approved)

**Platform-aware validation:**

```
Running validation checks...
```

Invoke `/validate` command (which runs batched validation with fail-fast):
- Batch 1 (Crypto) → fail-fast if blocking
- Batch 2 (Schema) → fail-fast if structural issues
- Batches 3-5 (Infra, Consistency, Code Quality) → parallel, collect all findings

Platform-specific checks are handled within the batched flow:
- **Glue**: crypto, schema, S3, layer rules, naming, dependencies
- **Databricks**: Unity Catalog, external locations, foundation library, Iceberg DDL, Python imports

**Pass criteria:** `{ "verdict": "APPROVED" }`

**Action on failure:** List all red flags; refuse push; suggest fixes

Example output:
```
❌ VALIDATION FAILED
Red flags found (3 blocking):
  1. S3 path malformed: dev1-pre-customer01-XXXX (missing account ID)
  2. Database prefix wrong: stg_complaints_db (expected fdp_)
  3. BDP reads BASE layer directly (violation: layer-rule)

Fix these issues and re-run: /push
```

---

### Step 6: Check Quality Gate (Condition 4: Tests Green)

**Step 6.0 — Syntax Check Gate (BLOCKING):**

> Python runtime status — per `agents/refs/python-runtime-contract.md`.

Read `session_state.syntax_check_result`:

- If `"passed"`: continue to Step 6.1.

- If `"failed"`: **BLOCK push unconditionally** (no flag can override). Display:
  ```
  ⛔ Push blocked — syntax errors in generated files:
     {list session_state.syntax_check_failures}
     
     Fix syntax errors and re-run the relevant /gen-* command, then retry /push.
  ```
  Do NOT proceed to Step 6.1.

- If `null` or `"skipped_no_python"`: syntax validation was NEVER successfully performed.
  - If `--skip-syntax-check` flag **provided**:
    - Log to `session/audit_log.jsonl`:
      ```json
      {"event": "SYNTAX_GATE_BYPASSED", "flag": "--skip-syntax-check", "syntax_check_result": "{current_value}", "timestamp": "{ISO 8601}"}
      ```
    - Display warning and continue to Step 6.1:
      ```
      ⚠️ Syntax check gate bypassed (--skip-syntax-check).
         syntax_check_result = "{null|skipped_no_python}"
         No syntax validation was performed on generated files.
         Proceeding at user's explicit request.
      ```
  - If `--skip-syntax-check` flag **NOT provided**: **BLOCK push**. Display:
    ```
    ⛔ Push blocked — syntax check was never run on generated files.
       syntax_check_result = "{null|skipped_no_python}"
       
       Options:
       1. Re-run the relevant /gen-* command with Python available to perform syntax validation.
       2. Use /push --skip-syntax-check to bypass this gate (logged to audit trail).
    ```
    Do NOT proceed to Step 6.1.

**Step 6.1 — Test Execution:**

**Python guard** — follow `agents/refs/python-runtime-contract.md § Guard Pattern`.
If `python_path == null`: set `test_gate = "skipped_no_python"`, log `[PUSH] Test gate skipped — no Python runtime`, CONTINUE (soft pass — push proceeds with explicit warning in the MR description).

**If `python_path` available:**

Determine `test_dir` (Glue: `generated/glue/tests/`, Databricks: `generated/databricks/tests/`).

Run via Bash tool:
```bash
{python_path} -m pytest {test_dir} --tb=short -q 2>&1
```

**Validation:**
- Exit code must be 0
- All tests pass

**Action on failure:**
- Spawn test-fix-agent (max 3 retries)
- If still failing after 3 retries: refuse push; report test failures

---

### Step 6.5: Check Quality Gate (Condition 5: ITSI Integrity)

**Verify ITSI/tagging values are valid before push:**

```
Checking ITSI integrity...
```

**Validation (3 checks):**

1. **Unresolved placeholder check:**
   - Scan all job YAMLs and `databricks.yml` for raw `{{app_service_tag}}` or `{{fin_role_tag}}` placeholders
   - If found: BLOCK push — these MUST be resolved before deployment
   - Display:
     ```
     ⛔ Push blocked — unresolved ITSI/tagging placeholders:
        {list of files containing {{app_service_tag}} or {{fin_role_tag}}}
        
        Resolve these values before pushing:
        1. Check databricks-tenancy registry for your tenancy's ITSI
        2. If ITSI is genuinely unknown, create a JIRA ticket for platform team
        3. Re-run /gen-bundle after ITSI is assigned
     ```

2. **Cross-tenancy contamination check:**
   - Extract all `APP:ApplicationService` values from job YAMLs (pattern: `SNSVC\d+`)
   - Cross-reference against `databricks-tenancy` registry for `session_state.tenancy_name`
   - If any ITSI value matches a DIFFERENT tenancy → BLOCK:
     ```
     ⛔ Push blocked — ITSI cross-tenancy contamination detected:
        Found: {wrong_itsi} (belongs to tenancy: {other_tenancy})
        Expected: {correct_itsi} (for tenancy: {session_tenancy})
        
        Re-run /gen-bundle to regenerate with correct tenancy values.
     ```

3. **Format validation:**
   - `APP:ApplicationService` must match `SNSVC\d+` (plain ITSI, no underscores after digits)
   - `FIN:Role` must match `SNSVC\d+_EDPUC-\d+_.*` pattern
   - If format is wrong → WARN (non-blocking) — suggest consulting `databricks-tenancy` skill

**Pass criteria:** No unresolved placeholders AND no cross-tenancy contamination AND format valid.

---

### Step 6.6: Check Quality Gate (Condition 6: Contract Reconciliation)

**Glue only** — skip for Databricks (equivalent coverage via foundation-library-validator).

Read `session_state.contract_reconciliation_result`:

- If `"passed"`: continue to Step 7.

- If `"failed"`: **BLOCK push**. Display:
  ```
  ⛔ Push blocked — contract reconciliation violations detected:
     {list session_state.contract_reconciliation_violations}
     
     Fix the violations and re-run /gen-wrapper, then retry /push.
  ```
  Do NOT proceed to Step 7.

- If `null` or `"skipped"`: contract reconciliation was not run.
  - Display warning and continue to Step 7:
    ```
    ⚠️ Contract reconciliation not run — consider running /gen-wrapper to validate
       cross-artefact contracts (wrapper ↔ transform ↔ config ↔ generic components).
    ```

---

### Step 7: User Confirmation (unless --auto-approve)

**If any condition failed:**
- Stop here (do not proceed to Step 8)

**If all conditions pass and `--auto-approve` NOT set:**

```
✅ All quality gate checks passed

Ready to push:
  Branch: feature/BUKL2CUSX-173655-customer-complaints
  Remote: git@app.gitlab.barcapint.com:{{gitlab_org}}/{{project_name}}.git
  JIRA:   BUKL2CUSX-173655
  Files:  transform.py, wrapper.py, dtxog_config.json

Continue with push? [Y/n]
```

- Wait for user confirmation
- If user enters `n` or Ctrl+C: cancel push

---

### Step 8: Execute Push (if ALL conditions met)

**Atomic execution — if ANY step fails, ROLLBACK:**

#### 7a: Git Add
```bash
git add -A
```

#### 7b: Git Commit
```bash
git commit -m "[{{jira_id}}] Auto-generated {{artifact_types}}"
```

Example:
```
[BUKL2CUSX-173655] Auto-generated transform.py, wrapper.py, dtxog_config.json
```

#### 7c: Git Push
```bash
git push -u origin {{branch_name}}
```

#### 7d: Create Merge Request
```bash
glab mr create \
  --title "Generated: {{title}}" \
  --description "Automated code generation for {{database}}.{{table}}

Platform: {{platform}}
Data Product Type: {{dp_type}}
Load Type: {{load_type}}

## Artefacts Generated
- {{artefact_list}}

## Testing
All unit tests pass (>90% coverage).

## Deployment
MR requires review before merge to main.
" \
  --target-branch main
```

#### 7e: Update JIRA

Delegate to `barclays-buk-jira:jira-agent` using the `barclays-buk-jira:jira-add-comment` skill:

```
OPERATION:  AddComment
ISSUE_KEY:  {{jira_id}}
ARGS:       "Code generated successfully!\n\nMR: {{mr_url}}\nPlatform: {{platform}}\nFiles: {{artefact_count}}"
```

Best-effort — if `JIRA_AUTH_TOKEN` is not set or the agent is unavailable, log a warning and continue.

---

### Step 9: Success Report

```
✅ Push successful

Commit:  {{commit_sha}}
MR:      {{mr_url}}
JIRA:    {{jira_url}}

Next: Review MR and merge to main after approval
```

---

## Failure & Rollback

If ANY step in the execution fails:

1. **Rollback git state:**
   ```bash
   git reset --soft HEAD~1  # Undo commit; keep staging
   git reset HEAD           # Unstage files
   ```

2. **Report error:**
   ```
   ❌ Push failed at step {{step_name}}
   
   Error: {{error_message}}
   
   Remediation:
   {{suggested_fix}}
   ```

3. **Refuse retry** without user action:
   - Do not automatically retry
   - Ask user to investigate and fix the issue
   - Provide remediation steps

---

## Examples

### Success Case (with auto-approve)
```bash
/push --jira-id BUKL2CUSX-173655 --auto-approve

✅ All quality gate checks passed
✅ Commit successful: abc1234
✅ MR created: https://app.gitlab.barcapint.com/{{gitlab_org}}/{{project_name}}/-/merge_requests/{{mr_id}}
✅ JIRA updated: https://estjira.barcapint.com/browse/BUKL2CUSX-173655
```

### Failure Case (validation rejected)
```bash
/push --jira-id BUKL2CUSX-173655

❌ VALIDATION FAILED
Red flags found (2 blocking):
  1. BDP reads BASE layer directly
  2. Database prefix wrong: stg_complaints (expected bdp_)

Fix issues and retry.
```

### Failure Case (tests failing)
```bash
/push

Running tests...
❌ 3 tests failed

Retrying (1/3)...
❌ Still failing

Retrying (2/3)...
❌ Still failing

Retrying (3/3)...
❌ Still failing

Push blocked: Tests not passing. Fix test failures and retry.
```

---

## Integration Notes

- **Pre-push gate**: Quality Gate (Conditions 1-5) must all pass
- **Atomic operations**: Commit + push + MR + JIRA are all-or-nothing
- **Rollback strategy**: Git state rolled back on any failure; no partial state
- **JIRA sync**: Optional if JIRA unavailable; logs error but doesn't block push

---

**Last Updated:** 2026-06-11 (FORGE Phase A3.2 — added Condition 1: Code Review gate)
