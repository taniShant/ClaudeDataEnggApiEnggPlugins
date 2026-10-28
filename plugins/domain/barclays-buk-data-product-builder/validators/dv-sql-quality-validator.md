# Validator: dv-sql-quality-validator

**Purpose**: Validates that generated DV SQL faithfully implements the validation plan — checking plan-to-SQL coverage, dialect correctness, filter presence, and structural fidelity.

**Severity**: blocker (QUALITY-01, QUALITY-02, QUALITY-05 through QUALITY-09), warning (QUALITY-03, QUALITY-10)

**Platform**: Athena + Databricks (some rules are engine-specific — see rule definitions)

---

## Scope

All `.sql` files in `generated/{platform}/validation/{db}_{table}/` (where `{platform}` is `glue` or `databricks`), cross-referenced against the corresponding validation plan and contract JSONs.

---

## Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `{db}_{table}_validation.sql` | Step 3 output | Rendered validation SQL |
| `{db}_{table}_results_summary.sql` | Step 3 output | Results summary SQL |
| `session/dv_validation_plan_{table}.json` | Step 2 output | Dialect-neutral validation plan |
| `session/dv_validation_contract_{table}.json` | Step 1 output | Normalized validation contract |
| `dv_session_state.json` → `engine` | Step 0 | Engine type (athena \| databricks) |

---

## Algorithm

For each table that passed safety validation (Step 4):

1. **Load context**
   - Read the validation plan JSON — extract `checks[]` array, `table_type`
   - Read the rendered SQL files (`_validation.sql` and `_results_summary.sql`)
   - Read engine from session state

2. **Prepare SQL variants**
   - Raw SQL: used by QUALITY-01, QUALITY-02, QUALITY-03, QUALITY-10 (these inspect comments/headers)
   - Comment-stripped SQL: used by QUALITY-06, QUALITY-07 (same stripping algorithm as `dv-sql-safety-validator` — mask string literals → strip `--` → strip `/* */` → unmask)

3. **Apply quality rules** (from `configs/dv/sql_quality_rules.yaml`)

   For each rule QUALITY-01 through QUALITY-10:
   - Check `engine_scope` — skip rules that don't apply to the current engine
   - Check preconditions (e.g., QUALITY-09 only applies to SCD2 tables)
   - Execute the rule's algorithm against the appropriate SQL variant
   - Collect violations with: `rule_id`, `severity`, `details`, `check_id` (if applicable)

4. **Evaluate results**
   - If any violation has `severity = blocker` → attempt self-heal (see below)
   - If only warnings → log warnings, continue to Step 5
   - If no violations → record `"passed"`

5. **Build coverage summary**
   ```json
   {
     "plan_checks_total": 28,
     "plan_checks_rendered": 28,
     "plan_checks_missing": [],
     "quality_rules_evaluated": 10,
     "quality_rules_passed": 8,
     "quality_rules_warned": 2,
     "quality_rules_failed": 0
   }
   ```

---

## Output

JSON per table:
```json
{
  "table": "mortgage_account",
  "violations": [
    {
      "rule_id": "QUALITY-01",
      "severity": "blocker",
      "details": "Plan check ER-05 not found in rendered SQL — expected comment header '-- ER-05:'",
      "check_id": "ER-05"
    }
  ],
  "coverage_summary": {
    "plan_checks_total": 28,
    "plan_checks_rendered": 27,
    "plan_checks_missing": ["ER-05"],
    "quality_rules_evaluated": 10,
    "quality_rules_passed": 9,
    "quality_rules_warned": 0,
    "quality_rules_failed": 1
  },
  "status": "FAIL"
}
```

Possible `status` values:
- `"PASS"` — zero violations
- `"FAIL"` — one or more blocker violations (after exhausting self-heal retries)
- `"WARNING"` — only warning-level violations (QUALITY-03, QUALITY-10)

---

## Pass Condition

Zero blocker violations across all files for the table.

---

## Fail Action

**Key difference from safety validator**: Quality blocker failures after exhausting self-heal retries do NOT halt the pipeline. The validator sets `dv_quality_validation_result = "failed"` and writes artifacts with a prominent warning. The SQL may be functionally correct even if it does not perfectly match the plan — the user can inspect and decide.

Display all violations grouped by rule category:

```
⚠️ Quality validation: FAILED (1 blocker, 1 warning)

   QUALITY-01 [blocker]: Plan check ER-05 not found in rendered SQL
     File: generated/glue/validation/fdp_uk_mortgage_db_mortgage_account/..._validation.sql
     Expected: Comment header "-- ER-05:" in SQL file

   QUALITY-03 [warning]: Metadata header says ER=7 but plan has 8 ER checks
     File: generated/glue/validation/fdp_uk_mortgage_db_mortgage_account/..._validation.sql

   Quality coverage: 27/28 checks rendered (96.4%)
   ⚠️ Artifacts written with quality warnings — review generated SQL before execution
```

---

## Invocation

- **Primary**: Called inline by `/dv-generate` Step 4b — SQL QUALITY VALIDATION
- **Self-heal**: Up to 2 retries — re-invoke renderer with violation context before accepting failure
- **Ordering**: Runs AFTER safety validation (Step 4) passes, BEFORE artifact write (Step 5)

---

## Self-Heal Retry Logic

When blocker violations are found during `/dv-generate` Step 4b:

1. **First attempt**: Re-invoke the platform renderer agent with:
   - Violation list (specific rule_ids, details, affected check_ids)
   - The validation plan JSON (for reference — which checks should be rendered)
   - Explicit instruction: "Fix the following quality violations. Ensure every plan check_id has a comment header section, use the correct dialect functions/operators, and include all planned filters."
   - The relevant quality rule descriptions from `configs/dv/sql_quality_rules.yaml`
2. **After re-render**: Re-run Step 4 (safety validation) to maintain safety guarantee, then re-run Step 4b (quality validation)
3. **Second attempt**: Same as above if blocker violations persist after first retry.
4. **After 2 retries**: Set `dv_quality_validation_result = "failed"`. **Continue to Step 5** — write artifacts with warning.

---

## Known Non-Violations

| Scenario | Rule | Reason |
|----------|------|--------|
| Check marked NOT_EVALUATED in plan but present in SQL | QUALITY-01 | NOT_EVALUATED checks may still have SQL rendered (to produce a metadata row) |
| Results summary uses check_id in a different case | QUALITY-02 | Case-insensitive matching is applied |
| ER check has `source_filter = "1 = 1"` (no-op) | QUALITY-08 | No-op filters are skipped — no assertion needed |
| Non-SCD2 table without control_date filter | QUALITY-09 | Rule only applies to SCD2 tables |

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/dv-generate` Step 4b | After safety validation passes | Run quality validator → self-heal retry if blocker violations |
| `/dv-generate` Step 5 | Artifact write | Include quality results in session state, manifest, audit log |
| `/dv-report` | Report generation | Read `dv_quality_coverage_summary` from session state (if present) and include in report |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `dv_quality_validation_result` | string \| null | dv-sql-quality-validator | `"passed"` \| `"failed"` \| `"passed_with_warnings"` |
| `dv_quality_violations` | array \| null | dv-sql-quality-validator | Violation objects |
| `dv_quality_coverage_summary` | object \| null | dv-sql-quality-validator | Coverage metrics |

Per-table (in `tables[]` items):

| Field | Type | Set By | Values |
|---|---|---|---|
| `quality_validation_result` | string \| null | dv-sql-quality-validator | `"passed"` \| `"failed"` \| `"passed_with_warnings"` |

---

## Notes

- Quality validation runs only on tables that passed safety validation — if safety failed and halted, quality is not evaluated
- Comment stripping uses the SAME algorithm as `dv-sql-safety-validator` — see that validator for the stripping procedure
- QUALITY-01 through QUALITY-03 read raw SQL (with comments) because they inspect comment headers
- QUALITY-06, QUALITY-07 read comment-stripped SQL to avoid false positives
- QUALITY-05, QUALITY-08, QUALITY-09 read raw SQL (filters and table references may appear in comments but are also in the SQL body — false positives are acceptable for blocker-level checks since self-heal corrects them)
- The quality rules are defined in `configs/dv/sql_quality_rules.yaml` (source of truth for rule IDs, algorithms, severity, engine scope)
