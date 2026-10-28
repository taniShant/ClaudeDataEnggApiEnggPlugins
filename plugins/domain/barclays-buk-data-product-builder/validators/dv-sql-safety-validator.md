# Validator: dv-sql-safety-validator

**Purpose**: Validates all generated DV SQL files contain only read-only SELECT statements with no DDL, DML, dynamic SQL, or catalog mutations.

**Severity**: blocker (SAFETY-01 through SAFETY-06, SAFETY-08 through SAFETY-10), warning (SAFETY-07)

**Platform**: Athena + Databricks

---

## Scope

All `.sql` files in `generated/{platform}/validation/{db}_{table}/` (where `{platform}` is `glue` or `databricks`)

---

## Algorithm

For each SQL file in the generated validation output directory:
1. Read file contents as a single string
2. Strip comments to avoid false positives — **this MUST complete before step 3**. Critical because SCD2 validation comments may reference DML keywords (e.g., `-- This validates the result of a MERGE operation`) which would otherwise trigger SAFETY-02.
   - **String-interior exclusion**: Mask string literals first to prevent `'-- not a comment'` from being mis-stripped
   - **Line comments**: Remove `-- ...` through end of line
   - **Block comments**: Remove `/* ... */` including nested blocks
   - **Unmask**: Restore string literals after comment stripping
3. Apply each safety rule regex pattern (from `configs/dv/sql_safety_rules.yaml`) **against the comment-stripped text only**
4. Collect all violations with: rule_id, severity, line_number, matched_text
5. If any blocker violation found → HALT with violation details
6. If only warning violations → continue with advisory message

### Regex Patterns (derived from sql_safety_rules.yaml)

| Rule | Category | Pattern | Severity |
|---|---|---|---|
| SAFETY-01 | DDL | `/\b(CREATE\|DROP\|ALTER\|TRUNCATE)\b/i` | blocker |
| SAFETY-02 | DML | `/\b(INSERT\|UPDATE\|DELETE\|MERGE)\b/i` | blocker |
| SAFETY-03 | Dynamic SQL | `/\b(EXEC\|EXECUTE\|PREPARE\|CALL)\b/i` | blocker |
| SAFETY-04 | Catalog | `/\b(MSCK\s+REPAIR\|REFRESH\s+TABLE\|ANALYZE\s+TABLE\|COMPUTE\s+STATISTICS)\b/i` | blocker |
| SAFETY-05 | Hardcoded dates | `/DATE\s+'[0-9]{4}-[0-9]{2}-[0-9]{2}'/i` EXCEPT sentinel `'3499-12-31'` | blocker |
| SAFETY-06 | Cross-env | `/\b(prod\|production\|uat\|staging)\b\s*\.\s*[\w]+/i` — dot-qualified identifiers only | blocker |
| SAFETY-07 | Size | Line count > 500 per file | warning |
| SAFETY-08 | SELECT-only | First non-comment, non-whitespace keyword must be `SELECT` or `WITH` | blocker |
| SAFETY-09 | Permissions | `/\b(GRANT\|REVOKE)\b/i` | blocker |
| SAFETY-10 | USE | `/\bUSE\b/i` | blocker |

### SAFETY-05 Sentinel Exception

The date literal `'3499-12-31'` is a known exception — SCD2 active-record checks use this value as the open-ended effective end date. Matches against this specific value are excluded from SAFETY-05 violations.

### SAFETY-06 Dot-Qualifier Constraint

SAFETY-06 matches only when an environment keyword is followed by a dot and an identifier (e.g., `prod.schema.table`). Bare column names like `product_type` or `production_flag` do NOT trigger this rule.

---

## Output

JSON per file:
```json
{
  "file": "generated/glue/validation/customer_db_customer_account/er_01_row_count.sql",
  "violations": [
    {
      "rule_id": "SAFETY-02",
      "severity": "blocker",
      "line": 14,
      "match": "INSERT INTO"
    }
  ],
  "status": "PASS"
}
```

Possible `status` values:
- `"PASS"` — zero violations
- `"FAIL"` — one or more blocker violations
- `"WARNING"` — only warning-level violations (SAFETY-07)

---

## Pass Condition

Zero blocker violations across all files.

---

## Fail Action

HALT `/dv-generate` pipeline. Display all violations grouped by file. The command attempts self-heal (re-invoke renderer with violation context) up to 2 retries before final HALT.

---

## Invocation

- **Primary**: Called inline by `/dv-generate` Step 4 — SQL SAFETY VALIDATION
- **Self-heal**: Up to 2 retries — re-invoke renderer with violation context before final HALT

---

## Self-Heal Retry Logic

When violations are found during `/dv-generate` Step 4:

1. **First attempt**: Re-invoke the platform renderer agent with:
   - Violation list (specific lines, rule_ids, matched text)
   - Explicit instruction: "Remove or replace the violating statement. Generated validation SQL must be SELECT-only. Do NOT use DDL, DML, dynamic SQL, or catalog mutations."
   - The relevant safety rule descriptions from `configs/dv/sql_safety_rules.yaml`
2. **Second attempt**: Same as above if violations persist after first retry.
3. **After 2 retries**: Mark validation as `DRAFT_UNVALIDATED`. Set `session_state.dv_safety_validation_result = "failed"`.

---

## Known Exceptions (NOT flagged as violations)

| Category | Examples | Reason |
|---|---|---|
| **SCD2 sentinel date** | `DATE '3499-12-31'` in WHERE clauses | Standard open-ended effective end date — excluded from SAFETY-05 |
| **DML keywords in comments** | `-- This validates the result of a MERGE operation` | Comment stripping (step 2) removes these before regex matching |
| **Column names containing keywords** | `product_type`, `production_flag`, `update_timestamp` | Word-boundary regex `\b` prevents partial matches on column names; SAFETY-06 requires dot-qualified identifiers |

---

## Integration Points

| Integration | When | Behavior |
|---|---|---|
| `/dv-generate` Step 4 | After SQL file generation | Run validator → self-heal retry if violations |
| `/dv-generate` gate | Before writing final output | Refuse to write if `dv_safety_validation_result` is `"failed"` |

---

## Session State Fields

| Field | Type | Set By | Values |
|---|---|---|---|
| `dv_safety_validation_result` | string \| null | dv-sql-safety-validator | `"passed"` \| `"failed"` |
| `dv_safety_violations` | array \| null | dv-sql-safety-validator | Violation objects |

---

## Notes

- SAFETY-05 allows the sentinel value `'3499-12-31'` as a known exception (SCD2 active-record checks)
- SAFETY-07 (size limit) is WARNING-only — large reconciliation queries for wide tables may legitimately exceed 500 lines
- All patterns are case-insensitive
- Comment stripping is MANDATORY before regex matching — SCD2 validation comments may contain DML keywords that would produce false positives
