# Validator: placeholder-completeness-validator

**Purpose**: Check that no unresolved blocking `{{placeholder}}` tokens remain in FINAL output artefacts. Track all placeholders in `session/placeholders.json`.

**Severity**: 
- Blocking placeholders unresolved → DRAFT_UNVALIDATED (halt generation)
- Non-blocking placeholders unresolved → DRAFT_UNVALIDATED (warn, continue)

**Platform**: Glue + Databricks

**Integration**: Works with `placeholder-auto-resolver.helper.md` (Phase 2 implementation)

---

## Placeholder Format

All placeholders use the format: `{{snake_case_descriptive_name}}`

Examples:
- `{{sms_secret_name}}`
- `{{change_request_no}}`
- `{{itsi_dev}}`
- `{{dda_catalog}}`
- `{{expected_completion_sla}}`
- `{{tenancy_name}}`

---

## Blocking vs Non-Blocking Placeholders (Phase 2: Auto-Resolved)

| Placeholder | Blocking? | Auto-Resolution | Failure Behavior |
|---|---|---|---|
| `{{itbs}}` | **YES** | Pre-resolved by glue-mesh-agent (Phase M) | ⛔ If still unresolved at validation time, route to `/gen-mesh` first |
| `{{sms_secret_name}}` | **YES** | Construct: sms-crypto-{tenancy_short_name} | ⛔ HALT if tenancy invalid |
| `{{custom_de_list}}` | **YES** | Extract from crypto_flags.json | ⛔ HALT if empty + crypto cols exist |
| `{{compid_prd}}` | No — advisory | Lookup ops skill (tenancy → compid) | ⚠️ SKIP if not found (non-blocking) |
| `{{change_request_no}}` | No — advisory | User session input | ⚠️ SKIP if not provided |
| `{{expected_completion_sla}}` | No — advisory | Domain knowledge lookup | ⚠️ SKIP if not found |

---

## Validation Logic (Phase 2: Auto-Resolve or HALT)

### STEP 1: Pre-Generation Preparation
1. Identify placeholders required by template
2. Invoke `placeholder-auto-resolver.helper.md` BEFORE rendering
3. Fail-fast: HALT if blocking placeholder cannot be resolved

### STEP 2: Post-Generation Validation
1. Scan each generated file for pattern `\{\{[a-z_]+\}\}`
2. For each match:
   - If blocking placeholder + unresolved: ⛔ HALT (should not happen; pre-generation check failed)
   - If non-blocking placeholder + unresolved: ⚠️ WARN (mark file DRAFT_UNVALIDATED)
   - If resolved: Continue validation
3. Update `session/placeholders.json` with all found placeholders + resolution status

### STEP 3: Mark Artefact Status
- If all blocking placeholders resolved: ✅ VALIDATED
- If any blocking placeholder unresolved: ⛔ DRAFT_UNVALIDATED + HALT
- If only non-blocking placeholders unresolved: ⚠️ DRAFT_UNVALIDATED (warn, continue)

**Reference**: See `placeholder-auto-resolver.helper.md` for detailed resolution logic

---

## ITSI / Tagging Value Validation (Databricks Only)

### Purpose

Detect ITSI cross-tenancy contamination: when the LLM fills ITSI gaps with plausible values from other tenancies instead of emitting placeholders.

### Severity: BLOCKING

### Validation Logic

1. **Extract ITSI values from generated artefacts:**
   - Scan all job YAMLs (`generated/databricks/jobs/**/*.yml`) for `APP:ApplicationService` tag value
   - Scan `databricks.yml` for any ITSI-pattern values (`SNSVC\d+`)
   - Collect all found ITSI values → `found_itsi_set`

2. **Resolve expected ITSI from databricks-tenancy registry:**
   - Look up `session_state.tenancy_name` in `databricks-tenancy` skill
   - Extract ITSI column value for the matched tenancy → `expected_itsi`
   - If registry returns null/empty/TBD → `expected_itsi = null`

3. **Cross-reference:**
   - If `expected_itsi` is null AND `found_itsi_set` is non-empty:
     - → BLOCK: "ITSI values found in artefacts but registry has no ITSI for this tenancy. Likely cross-tenancy contamination."
   - If `expected_itsi` is non-null AND any value in `found_itsi_set` ≠ `expected_itsi`:
     - → BLOCK: "ITSI mismatch — artefacts contain `{wrong_itsi}` but tenancy registry expects `{expected_itsi}`. Cross-tenancy contamination detected."
   - If all values match OR no ITSI values found (all placeholders) → PASS

### Fail Action

BLOCK:
```
❌ ITSI Cross-Tenancy Contamination Detected!
   Session tenancy: {tenancy_name}
   Expected ITSI (from registry): {expected_itsi or "NOT AVAILABLE — should be placeholder"}
   Found in artefacts: {found_itsi_set}
   
   The ITSI value(s) in generated artefacts do not match the tenancy registry.
   This likely means values were copied from a different tenancy's context.
   
   Fix: Re-run /gen-bundle to regenerate with correct ITSI or {{app_service_tag}} placeholder.
```

---

## Pass Condition

Zero `{{placeholder}}` tokens in the file.

## Fail Action

Mark file as DRAFT_UNVALIDATED. List all open placeholders:
```
⚠️ {filename} contains open placeholders:
  {{sms_secret_name}}  — crypto secret name (required for deployment)
  {{change_request_no}} — CR number (required for PROD)
```

## session/placeholders.json Structure

```json
{
  "placeholders": [
    {
      "name": "sms_secret_name",
      "artefact_file": "fdp_mortgage_db_fdp_mortgage_case_dtxog.json",
      "field_path": "dtxog.app_details.env.dev.crypto_dpaas.secret_name",
      "reason": "Crypto secret name not provided via G5",
      "blocking": true
    }
  ]
}
```
