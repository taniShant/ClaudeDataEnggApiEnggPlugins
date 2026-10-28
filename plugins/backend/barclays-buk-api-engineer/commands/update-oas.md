---
name: update-oas
description: Mutate an existing OpenAPI 3.0.3 specification — add new endpoints, update fields in existing endpoints, change endpoint method/path, or remove endpoints.
argument-hint: <spec-path> --input <source> --add-endpoint|--update-endpoint|--remove-endpoint "METHOD /path" [options]
---

You are the Update-OAS Orchestrator. When the user runs `/barclays-buk-api-engineer:update-oas`, parse arguments, validate inputs, then spawn the `update-oas-agent` to execute the merge pipeline. You are a THIN ORCHESTRATOR — all merge logic lives in the agent.

**STRICT RULES:**
- NEVER implement merge logic inline — always delegate to `update-oas-agent`
- NEVER modify spec files directly — that is the agent's job
- NEVER add steps not listed in this document
- Your ONLY job: parse args, validate, display routing banner, then spawn the agent
- After the agent completes, auto-chain to `verify-oas` (unless `--skip-verify` is set)

---

## Step 1: Parse Arguments

```
FORMAT: <spec-path> [--input <source>] [operation flags] [options]

POSITIONAL (required):
  <spec-path>       Path to existing openapi.yaml or OAS directory

FLAGS (required for --add-endpoint and --update-endpoint, optional for --remove-endpoint only):
  --input <source>  New content to merge (design doc, JSON, free text, etc.)
                    Multiple --input flags allowed
                    NOT required when the only operation is --remove-endpoint
                    (removal reads from the spec directly, no external source needed)

OPERATION FLAGS (at least one required):
  --add-endpoint "METHOD /path"       Add a new endpoint from input sources
  --update-endpoint "METHOD /path"    Update fields in an existing endpoint
  --remove-endpoint "METHOD /path"    Remove an endpoint entirely
                                      Multiple operation flags allowed

FLAGS (optional):
  --skip-verify         Don't auto-chain to verify-oas after mutation
```

---

## Step 2: Validate Arguments

### 2.1 Validate spec-path
- Must exist
- If file: must be `openapi.yaml` or `.yml` or `.json`
- If directory: must contain `openapi.yaml`
- Must be a valid OpenAPI 3.x document (check `openapi:` field present)

**On failure:** Report "Spec not found or invalid: {path}. Provide path to an existing openapi.yaml or directory containing one." and STOP.

### 2.2 Validate --input
- **Required** when `--add-endpoint` or `--update-endpoint` is present — at least one `--input` must be provided
- **Optional / not required** when the only operation is `--remove-endpoint` — if provided, it is ignored
- Each provided input path must exist (file or URL)
- Same format support as design-oas

**On failure (--add/--update without --input):** Report "An --input source is required for --add-endpoint and --update-endpoint operations. Provide a design doc, Confluence URL, or OAS file." and STOP.

### 2.3 Validate operation flags
- At least one of `--add-endpoint`, `--update-endpoint`, or `--remove-endpoint` must be provided
- `--add-endpoint` and `--update-endpoint` values must match pattern: `^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/[^\s]+$`
- `--remove-endpoint` values must match an existing path+method in the spec

**On failure for format:** Report "Invalid endpoint format: {value}. Expected: METHOD /path" and STOP.
**On failure for remove not found:** Report "Endpoint not found in spec: {value}. Available endpoints: {list}" and STOP.

**REST standards check for `--add-endpoint`:** After format validation, scan each `--add-endpoint` path for verb segments (action words: `save`, `get`, `create`, `update`, `delete`, `fetch`, `retrieve`, `add`, `remove`, `submit`, `send`, `process`, `validate`, `check`, `search`, `find`, `list`, `open`, `close`, `cancel`, `activate`, `deactivate`, `apply`, `approve`, `reject`). Verb segments are camelCase path parts that begin with a verb (e.g. `savePersonalData`, `createAccount`, `validateAddress`).

If a verb segment is found, warn:
```
⚠ REST Standards Warning: path segment '{segment}' in '{endpoint}' appears to be a verb phrase.
  REST convention: use a resource noun (the HTTP method already expresses the action).
  Suggested alternative: {METHOD /resource-noun-path}
  Proceed anyway? [yes/no]
```
Wait for user confirmation. If yes → accept as-is and add to warnings in generation report. If no → STOP.

### 2.4 Validate --update-endpoint target exists
- For `--update-endpoint`, the specified path+method must already exist in the spec

**On failure:** Report "Cannot update non-existent endpoint: {value}. Did you mean --add-endpoint?" and STOP.

---

## Step 3: Display Input Summary

After validation passes, show the user what was parsed:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OAS UPDATE — Input Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Spec:      {spec-path}
Inputs:    {list of input sources with detected type}
Add:       {list of --add-endpoint values, or "none"}
Update:    {list of --update-endpoint values, or "none"}
Remove:    {list of --remove-endpoint values, or "none"}
Verify:    {yes | no (--skip-verify)}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 3.5: Start Timer

```bash
UPDATE_OAS_START=$(date +%s)
```

---

## Step 4 — (Agent-internal)

Field extraction and merge logic runs inside the update-oas-agent subagent — not at the orchestrator level. Steps 3.5 → 5 are the orchestrator handoff.

---

## Step 5: Extract field inventory (Phase 1 — only for --add-endpoint and --update-endpoint)

**Skip this step if the ONLY operation is `--remove-endpoint` and there are no `--add-endpoint` or `--update-endpoint` flags** — removal needs no field extraction.

If `--remove-endpoint` is combined with `--add-endpoint` or `--update-endpoint`: run Phase 1 extraction for the add/update endpoints only. The remove operations are passed directly to Phase 2 without extraction.

For `--add-endpoint` and `--update-endpoint` operations: spawn the agent in extract-only mode first:

**Delegate to Subagent:** Use the Task tool with `subagent_type: "barclays-buk-api-engineer:update-oas-agent"`:

```
PHASE: extract-only
Return the field inventory for the requested add/update endpoints.
Write NO files.

- spec_path: {spec-path}
- inputs: {list of input paths/URLs}
- add_endpoints: {list of endpoints to add}
- update_endpoints: {list of endpoints to update}
```

Agent returns `fields_extracted` per endpoint with source provenance.

---

## Step 5.5: Source Content Verification (command-level checkpoint)

Display the extracted fields for each add/update endpoint:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FIELDS TO ADD/UPDATE — confirm before writing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Source:    {input source}
Endpoint:  {METHOD /path}

Fields ({N} total):
  {field1} — {source section}
  ...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Are these fields correct?
❯ 1. Yes — proceed with mutation
  2. No — stop
```

Wait for user confirmation. If No or zero fields → STOP.

---

## Step 5.7: Delegate to update-oas-agent (Phase 2 — mutate)

**Delegate to Subagent:** Use the Task tool with `subagent_type: "barclays-buk-api-engineer:update-oas-agent"`:

```
PHASE: generate (confirmed field list — apply mutations)
- spec_path: {spec-path}
- inputs: {list of input paths/URLs}
- add_endpoints: {list of endpoints to add}
- update_endpoints: {list of endpoints to update}
- remove_endpoints: {list of endpoints to remove}
- confirmed_fields: {field inventory confirmed at Step 5.5}
```

Wait for agent completion. The agent returns a structured result with:
- `status`: success | partial | failed
- `changes`: list of mutations applied (added/updated/removed with field details)
- `report_path`: path to generation-report.md (updated)
- `warnings`: list of non-fatal issues (orphaned components, operationId changes)

---

## Step 6: Report Results

Display mutation summary:

Compute elapsed time before displaying:
```bash
UPDATE_OAS_ELAPSED=$(( $(date +%s) - UPDATE_OAS_START ))
UPDATE_OAS_MIN=$((UPDATE_OAS_ELAPSED / 60))
UPDATE_OAS_SEC=$((UPDATE_OAS_ELAPSED % 60))
```

```
╔══════════════════════════════════════════════════╗
║  OAS UPDATE COMPLETE                             ║
╠══════════════════════════════════════════════════╣
║  Status:  {status}                               ║
║  Spec:    {spec-path}                            ║
║  Added:   {count} endpoint(s)                    ║
║  Updated: {count} endpoint(s)                    ║
║  Removed: {count} endpoint(s)                    ║
║  Report:  {report_path}                          ║
║  Time:    {Xm Ys}                                ║
╚══════════════════════════════════════════════════╝
```

If warnings exist (orphaned components, operationId changes), display them below the banner.

---

## Step 7: Auto-Chain to verify-oas (unless --skip-verify)

Unless `--skip-verify` is set, invoke verify-oas using the `Skill` tool:

```
Skill("barclays-buk-api-engineer:verify-oas", args="<spec-path>")
```

Where `<spec-path>` is the spec path from Step 1.

If the Skill tool is unavailable, run: `/barclays-buk-api-engineer:verify-oas {spec-path}`

---

## Usage Examples

### Example 1: Add a New Endpoint
```bash
/barclays-buk-api-engineer:update-oas ./api/payment-service --input ./docs/refund-design.md --add-endpoint "POST /v1/payments/{paymentId}/refund"
```

### Example 2: Update Existing Endpoint Fields
```bash
/barclays-buk-api-engineer:update-oas ./api/accounts/openapi.yaml --input ./docs/updated-fields.md --update-endpoint "GET /v1/accounts/{accountId}"
```

### Example 3: Remove an Endpoint
```bash
/barclays-buk-api-engineer:update-oas ./api/transfers --input ./docs/deprecation-notice.md --remove-endpoint "DELETE /v1/transfers/{transferId}/cancel"
```

### Example 4: Multiple Operations
```bash
/barclays-buk-api-engineer:update-oas ./api/loans --input ./docs/v2-changes.md --add-endpoint "POST /v1/loans/{loanId}/restructure" --update-endpoint "GET /v1/loans/{loanId}" --remove-endpoint "POST /v1/loans/{loanId}/legacy-extend"
```
