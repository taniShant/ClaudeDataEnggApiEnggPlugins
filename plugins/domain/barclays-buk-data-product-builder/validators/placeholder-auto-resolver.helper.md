# Placeholder Auto-Resolver (Phase 2 Implementation)

**Purpose**: Auto-resolve blocking and non-blocking placeholders using reference tables. HALT only if blocking placeholder cannot be resolved.

**Invoked by**: All `/gen-*` commands (wrapper, dtxog, transform, driver, ddl, mesh, config, tests)

**Output**: Updated artefacts with resolved placeholders; HALT message if blocking placeholder fails

**Platform**: Glue + Databricks

---

## Phase 1: Classify Placeholders

**Blocking Placeholders** (halt generation if unresolved):

| Placeholder | Value Source | Priority | Notes |
|---|---|---|---|
| `{{sms_secret_name}}` | Construct: `sms-crypto-{tenancy_short_name}` | 1 (required if crypto) | Crypto config only |
| `{{custom_de_list}}` | Extract from `crypto_flags.json` | 1 (required if crypto) | Crypto columns only |

**Pre-Resolved Placeholders** (already resolved in templates, not auto-resolved):

| Placeholder | Value Source | Usage | Notes |
|---|---|---|---|
| `{{itbs}}` | Mesh JSON template | Mesh JSON generation | Already resolved via glue-mesh-agent (Phase M); NOT a Phase 2 placeholder |

**Non-Blocking Placeholders** (skip if unresolved; continue):

| Placeholder | Value Source | Priority |
|---|---|---|
| `{{change_request_no}}` | User input (advisory) | 3 |
| `{{expected_completion_sla}}` | Domain knowledge or advisory | 3 |
| `{{compid_prd}}` | ops skill (tenancy → compid) | 2 (optional) |

---

## Phase 2: Load Reference Tables

### Reference Table 1: ops skill — ITSI & Netcool Mapping

**Location**: `skills/service-management/SKILL.md` (ITSI & Netcool Components)

**Format**:
```
Tenancy         │ dev ITSI      │ uat ITSI      │ prd ITSI      │ prd Netcool Compid
────────────────┼───────────────┼───────────────┼───────────────┼──────────────────
complaints      │ SNSVC0069877  │ SNSVC0069872  │ SNSVC0069873  │ BUKFDPCONSCOMP
customer        │ SNSVC0070020  │ SNSVC0070017  │ SNSVC0069880  │ BUKFDPCONSCUST
fdpmortgage     │ SNSVC0072836  │ SNSVC0072837  │ SNSVC0073328  │ FDPBUKMORT
...
```

**How to Parse**:
1. Extract tenancy from `session_state.tenancy_name`
2. Get environment from context (dev/sit, uat, prd)
3. Look up row matching tenancy
4. Get ITSI code for environment or Netcool compid for prd

### Reference Table 2: Tenancy Skill Registry

**Location**: `skills/tenancy-summary/SKILL.md`

**Format**: Known tenancies list with feature team names

**How to Validate**:
1. Extract tenancy from `target_database` (e.g., `fdp_uk_complaints_db` → `complaints`)
2. Search `skills/tenancy-summary/SKILL.md` tenancy registry
3. If found: tenancy is valid
4. If NOT found: HALT (invalid tenancy → user must fix mapping)

### Reference Table 3: Tenancy Short Names

**Location**: `skills/tenancy-summary/SKILL.md` tenancy registry (column: "Feature Team Name")

**Examples**:
- `complaints` → `fdpcomplaints` → SMS secret: `sms-crypto-complaints`
- `fdpmortgage` → `fdpmortgage` → SMS secret: `sms-crypto-fdpmortgage`
- `cdpcustomer` → `cdpcustomer` → SMS secret: `sms-crypto-cdpcustomer`

---

## Phase 3: Auto-Resolution Logic

### STEP 1: Load Session Context

```
tenant = session_state.tenancy_name
environment = {dev, uat, prd}  # from context
crypto_enabled = (crypto_flags.json has crypto columns)
de_list = crypto_flags.json.custom_de_list  # from Phase 1
```

### STEP 2: Resolve Blocking Placeholders

**Note**: `{{itbs}}` is pre-resolved in mesh JSON template (not a Phase 2 placeholder)

#### Resolution 1: {{sms_secret_name}} (Crypto Secret Name)

```
ATTEMPT:
  1. Check if tenancy is valid (from `skills/tenancy-summary/SKILL.md` registry)
  2. Construct secret name: sms-crypto-{tenancy_short_name}
  3. INJECT into artefact
     → Replace all {{sms_secret_name}} with constructed name
     → Continue

FAILURE HALT:
  IF tenancy NOT found in tenancy skill:
    ⛔ HALT
    Message: "Cannot resolve {{sms_secret_name}} (invalid tenancy).
              Target database uses unknown tenancy.
              REQUIRED ACTION:
              1. Verify target_database in mapping matches known tenancies
              2. Valid prefixes: fdp_*, cdp_*, bdp_*
              3. Valid tenancies: [list from `skills/tenancy-summary/SKILL.md`]
              4. Fix mapping and re-run"
```

#### Resolution 2: {{custom_de_list}} (Protegrity Data Elements)

```
ATTEMPT:
  1. Load crypto_flags.json
  2. Extract all DE names from crypto_flags.custom_de_list
  3. Format as comma-separated list or JSON array (per template)
  4. INJECT into artefact
     → Replace {{custom_de_list}} with resolved list
     → Continue

FAILURE HALT:
  IF crypto_flags.custom_de_list is EMPTY but crypto columns exist:
    ⛔ HALT
    Message: "Crypto columns detected but {{custom_de_list}} is empty.
              Protegrity Data Elements were not extracted during parsing.
              REQUIRED ACTION:
              1. Verify crypto columns have complete UDF patterns:
                 cloud_api_udf_{DE_NAME}_(un)protect({column})
              2. Examples: cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_protect(account_number)
              3. Update mapping and re-run /parse-mapping"
```

### STEP 3: Resolve Non-Blocking Placeholders

#### Resolution 3: {{expected_completion_sla}} (Advisory, optional)

```
ATTEMPT:
  1. Check domain_knowledge_text for "sla" or "completion" mention
  2. If found: Extract SLA value
     → INJECT into artefact
     → Continue
  3. If NOT found: SKIP (non-blocking)
     → Leave {{expected_completion_sla}} as-is
     → Continue (no halt)
```

#### Resolution 4: {{change_request_no}} (Advisory, optional)

```
ATTEMPT:
  1. Check session_state for user-provided CR number
  2. If found: INJECT into artefact
     → Replace {{change_request_no}} with CR number
     → Continue
  3. If NOT found: SKIP (non-blocking)
     → Leave {{change_request_no}} as-is
     → Continue (no halt)
```

---

## Phase 4: Handle Failures

### Blocking Placeholder Failure

**When**: {{itbs}}, {{sms_secret_name}}, or {{custom_de_list}} cannot be auto-resolved

**Action**: ⛔ **HALT** (stop generation)

**Message Format**:
```
⛔ HALT — G5: Placeholder Auto-Resolution Failed

Placeholder: {{placeholder_name}}
Reason: {specific reason}

REQUIRED ACTION:
  1. {Fix option 1}
  2. {Fix option 2}
  3. Re-run: {command}

Reference:
  ITSI codes: skills/service-management/SKILL.md (ITSI & Netcool Components)
  Tenancies: `skills/tenancy-summary/SKILL.md`
```

### Non-Blocking Placeholder Failure

**When**: {{change_request_no}}, {{expected_completion_sla}}, {{compid_prd}} cannot be resolved

**Action**: ⚠️ **WARN** (continue; mark as DRAFT_UNVALIDATED)

**Behavior**:
- Leave placeholder as-is
- Mark artefact as DRAFT_UNVALIDATED
- Log to audit trail: "Placeholder {{name}} unresolved; artefact is draft"
- Continue generation

---

## Phase 5: Update session/placeholders.json

**After Resolution**:

```json
{
  "placeholders": [
    {
      "name": "itbs",
      "blocking": true,
      "resolved": true,
      "resolved_value": "SNSVC0069873",
      "resolved_at": "2026-06-09T10:30:00Z",
      "resolution_method": "auto-lookup from SKILL.md"
    },
    {
      "name": "change_request_no",
      "blocking": false,
      "resolved": false,
      "resolved_value": null,
      "reason": "User did not provide; left as placeholder"
    }
  ]
}
```

---

## Phase 6: Integration with /gen-* Commands

### Pre-Generation (Before Generating Artefact)

```
STEP 0: Check if blocking placeholders will be needed
  → Read template to identify required placeholders
  → Pre-load SKILL.md and `skills/tenancy-summary/SKILL.md` reference tables
  → Pre-attempt resolution (fail fast if blocking resolves to null)
```

### Post-Generation (After Template Rendering)

```
STEP X: Resolve all placeholders in rendered artefact
  1. Scan for pattern: \{\{[a-z_]+\}\}
  2. For each match:
     → If blocking: Attempt resolve; HALT if fails
     → If non-blocking: Attempt resolve; SKIP if fails
  3. Update placeholders.json
  4. Mark artefact status:
     → If all blocking resolved: VALIDATED
     → If any blocking unresolved: DRAFT_UNVALIDATED
```

---

## Implementation Checklist (Phase 2)

### Commands to Update:

- [ ] `/gen-wrapper` (Glue only)
  - Placeholders: {{itbs}}, {{sms_secret_name}} (if crypto)
  - Add: Auto-resolve logic post-generation
  
- [ ] `/gen-dtxog` (Glue only)
  - Placeholders: {{itbs}}, {{sms_secret_name}}, {{custom_de_list}} (if crypto)
  
- [ ] `/gen-mesh` (Glue only)
  - Placeholders: {{itbs}}
  
- [ ] `/gen-transform` (Both platforms)
  - Placeholders: {{custom_de_list}} (if crypto, Glue only)
  
- [ ] `/gen-config` (Glue only)
  - Placeholders: {{sms_secret_name}} (if crypto)
  
- [ ] `/gen-driver` (Databricks only)
  - Placeholders: {{custom_de_list}} (if crypto)
  
- [ ] `/gen-ddl` (Databricks only)
  - Placeholders: {{compid_prd}}
  
- [ ] `/gen-tests` (Both platforms)
  - Placeholders: {{custom_de_list}} (if crypto)

### Validators to Update:

- [ ] `placeholder-completeness-validator.md`
  - Update "Validation Logic" section
  - Reference this auto-resolver doc
  - Document HALT vs SKIP behavior

---

## Reference: HALT Message Templates

### Template for {{sms_secret_name}} Failure

```
⛔ HALT — G5: Cannot Resolve {{sms_secret_name}}

Analysis:
  Tenancy: {tenancy}
  Expected format: sms-crypto-{tenancy_short_name}
  Error: Invalid tenancy (not in tenancy skill registry)

REQUIRED ACTION:
  1. Verify target_database uses valid tenancy
  2. Valid format: fdp_*/cdp_*/bdp_*/shared_fdp_*/shared_cdp_*/shared_bdp_* prefix
  3. Valid tenancies: [list]
  4. Fix mapping and re-run: /parse-mapping

Reference: `skills/tenancy-summary/SKILL.md`
```

### Template for {{custom_de_list}} Failure

```
⛔ HALT — G5: {{custom_de_list}} Is Empty

Analysis:
  Crypto columns detected: YES
  Protegrity Data Elements extracted: NONE
  Error: DE extraction failed during /parse-mapping

REQUIRED ACTION:
  1. Verify transformation logic has complete UDF patterns
  2. Expected: cloud_api_udf_{DE_NAME}_(un)protect({column})
  3. Examples:
     - cloud_api_udf_UK_TOK_ACCT_L0R0_NUM_DE_protect(account_number)
     - cloud_api_udf_US_TOK_CC_L6R4_NUM_DE_unprotect(card_num)
  4. Update mapping and re-run: /parse-mapping

Reference: `skills/tenancy-summary/SKILL.md` Protegrity Data Elements section
```

---

## Success Criteria (Phase 2 Validation)

✅ All blocking placeholders auto-resolved without user prompt  
✅ Non-blocking placeholders skipped gracefully (no HALT)  
✅ Clear HALT messages when auto-resolution fails  
✅ Reference tables (SKILL.md, `skills/tenancy-summary/SKILL.md`) loaded correctly  
✅ session/placeholders.json updated with resolution status  
✅ All `/gen-*` commands use auto-resolver  
✅ End-to-end test: `/init --platform glue --full-automation` → ZERO prompts
