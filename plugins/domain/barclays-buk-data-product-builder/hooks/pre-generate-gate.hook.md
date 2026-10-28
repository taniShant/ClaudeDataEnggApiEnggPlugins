# Hook: pre-generate-gate

> **Type:** Documentation (orchestration logic — not an executable hook)

**Trigger**: Before any generation command (`/gen-*`)

**Purpose**: Verify all required gates are resolved before allowing any artefact generation. Prevent partial or premature generation that would produce invalid output.

---

## Checks (in order)

### Check 1 — G1 Resolved (HALT if not)

`session_state.platform` must be non-null.

Error: "Platform not set. Run `/init` or set `session_state.platform` manually (value: 'glue' or 'databricks')."

### Check 2 — G1.5 Resolved (HALT if not)

`session_state.data_product_type` must be non-null.

Error: "Data product type not set. Answer Gate G1.5 (FDP / CDP / BDP) before generating artefacts."

### Check 3 — Mapping Parsed (HALT if not)

`session/mapping_parsed.json` must exist.

Error: "Mapping not parsed. Run `/parse-mapping` or provide `session/mapping_parsed.json` directly."

### Check 4 — Platform-Specific Gates

**For Glue only** — before `/gen-mesh`, `/gen-wrapper`, `/gen-dtxog`:
- `G3` must be in `gates_resolved` (all env S3 locations provided)
- Error: "G3 not resolved. Provide S3 bucket and prefix for all environments (dev/uat/prd) before generating Mesh JSON or Glue artefacts."

### Check 5 — No Blocking Open Placeholders (HALT if found)

`session_state.open_placeholders` must be empty OR all placeholders are non-blocking (advisory only).

Blocking placeholders (halt generation):
- `{{sms_secret_name}}` — crypto active but secret name not provided

Non-blocking placeholders (generation allowed):
- `{{change_request_no}}` — CR number (filled before PROD)
- `{{itsi_dev}}`, `{{itsi_uat}}`, `{{itsi_prd}}` — ITSI values
- `{{expected_completion_sla}}` — SLA time

Error for blocking: "Generation blocked by unresolved required values: {list}. Provide these values before proceeding."

### Check 6 — Crypto Refusal (HALT if extraction_failed)

If any column in `session/crypto_flags.json` has `extraction_failed: true`:
- HALT for that column
- Error: "Column `{col}` is flagged for crypto but the Protegrity DE name cannot be extracted from its transformation logic. Add the full UDF pattern `cloud_api_udf_<DE_NAME>_(un)protect({col})` to the transformation logic column in the mapping document."
- Other non-failed columns may proceed

---

## Behaviour on Pass

All checks pass → allow the generation command to proceed. Log gate check to `session/audit_log.jsonl`.

---

## Behaviour on Fail

Halt the generation command. Display specific error message(s). Do NOT generate partial output. Log failure to `session/audit_log.jsonl`.
