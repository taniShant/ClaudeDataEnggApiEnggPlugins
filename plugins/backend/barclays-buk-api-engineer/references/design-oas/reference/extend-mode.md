# Extend Mode — Reference for Step 3 (used by update-oas-agent)

Referenced by `update-oas-agent` for merge and change-detection logic.

---

## Safety Check (update-oas context)

This file is referenced by `update-oas-agent`. The `spec-path` (existing spec) and the write target are always the same location in update-oas — the agent modifies the spec in-place using Edit for modified files and Write for new files. Never overwrite existing component files that were not named in the operation request.

---

## Endpoint Matching

Normalise all paths before comparing: replace every `{paramName}` with `{*}`.

Examples:
- `/v1/accounts/{accountId}` → `/v1/accounts/{*}`
- `/v1/accounts/{id}` → `/v1/accounts/{*}`
- These are the same endpoint — path param was renamed

Match key = **normalised path + HTTP method**.

---

## Change Type Detection

For each endpoint in `--endpoints`, compare against existing OAS:

| Change type | Detection | Action |
|-------------|-----------|--------|
| New endpoint | Normalised path not in existing OAS | Append — generate all components fresh |
| Field-level change | Same normalised path + method, named in `--endpoints` | Merge — input is source of truth |
| Method change | Same normalised path, different HTTP method | Remove old method, generate new |
| Path param rename | Normalised paths match, param names differ | Merge + rename param everywhere |
| Query/header param change | Same path+method, params differ | Merge params — input is source of truth |
| Endpoint not in `--endpoints` | Path exists in OAS, not named in `--endpoints` | Copy as-is — never modify silently |

---

## Merge Rules (input is source of truth)

Applied when: same normalised path + method, endpoint named in `--endpoints`.

### Request body fields

| Situation | Action |
|-----------|--------|
| Field in input + exists in OAS | Use input version — input wins |
| Field in input + not in OAS | Add it |
| Field in OAS + not in input | Remove it |

### Response schemas

Apply the same merge logic to response body schemas:
- Fields added in input → add to response schema
- Fields removed from input → remove from response schema
- Fields updated in input → use input version

**Non-standard response codes (409, 422, 502, 504):** These are preserved at the `openapi.yaml` path operation level — they are NOT subject to the component-level merge algorithm. The merge algorithm in `component_builder.md` applies only to properties within schema files (`type-{Op}RequestData.yaml` etc.), not to response code entries in `openapi.yaml`. Response code preservation rule: if the existing OAS has a non-standard response code not mentioned in the input, keep it. Only remove a response code if the input explicitly states it should be removed.

### Query and header parameters

| Situation | Action |
|-----------|--------|
| Param in input + exists in OAS | Use input version |
| Param in input + not in OAS | Add it |
| Param in OAS + not in input | Remove it — **except mandatory Barclays standard headers** (see exemptions below) |

**Mandatory header exemptions — never remove from existing OAS even if absent from input:**
- `correlationId` / `Correlation-ID`
- `Authorization`
- `channelId`
- `deviceId`
- `businessId`
- `Cache-Control`
- `sourceSortCode` — only appears in older specs built against a previous reference; not generated in new GREENFIELD specs but must be preserved if present in existing OAS

These come from the reference OAS (`common-libraries/components/headers.yaml`), not from user input documents. If they exist in the existing OAS, preserve them regardless of input.

### Required array changes

When a field moves from optional → required or required → optional:
- Apply input version
- Log the change: `"fieldName: optional → required"` or `"fieldName: required → optional"`

### Field property changes

Track and log individual property changes per field:
- `deprecated` flag added/removed
- `nullable` changed
- `pattern` updated
- `maxLength`/`minLength` changed
- `description` updated

All changes logged in `## Merge Changes` section of generation report.

---

## Method Change

When input specifies `GET /v1/accounts` but existing OAS has `POST /v1/accounts`:

1. Remove `POST` operation from `openapi.yaml` for that path
2. Copy old component files (`type-PostAccounts*.yaml`) to output — flag as `ORPHANED` in report
3. Never silently delete existing files
4. Generate new component files for new method (`type-GetAccounts*.yaml`)
5. If path has no remaining methods → remove path entry from `openapi.yaml`
6. Log: `"/v1/accounts: POST → GET (method changed)"`

---

## Path Param Rename

When `/v1/accounts/{accountId}` (existing) matches `/v1/accounts/{id}` (input):

1. Apply field-level merge as normal
2. Update param name in `openapi.yaml` path key, operation `parameters`, and component file `$ref` paths
3. Log: `"/v1/accounts/{accountId} → /v1/accounts/{id} (path param renamed)"`

---

## Shared $ref Warning

If an existing component file is referenced by multiple endpoints (e.g. `type-CommonAddress.yaml` used by both `POST /v1/accounts` and `GET /v1/customers`):

- Do NOT modify the shared component — modifying it would break other endpoints
- Flag as Red Flag in generation report: `"Shared component {file} — cannot merge safely. Update manually."`
- Apply merge only to endpoint-specific component files

To detect: check if the `$ref` target appears in more than one path's `$ref` chain.

---

## operationId Change Detection

If input derives a different `operationId` than what exists in the OAS (e.g. path renamed from `/v1/accounts/open` to `/v1/accounts`):

- Warn user: `"operationId will change from 'openAccount' to 'postAccounts'. This breaks consumers that reference operationId."`
- Ask: "Proceed with operationId change? [yes/no]"
- If **yes** → use new operationId, rename component files to match new operationId, update all `$ref` paths in `openapi.yaml`
- If **no** → keep existing operationId for this endpoint; use existing component file names unchanged; apply field-level merge to the existing component files only; log as Red Flag: `"operationId kept as '{old}' — new derivation '{new}' was rejected by user"`

---

## nullable: true in Existing OAS

If an existing spec has `nullable: true` on a field (pre-CISO compliance), and the input does not explicitly set `nullable`:
- Do NOT silently overwrite to `nullable: false` — this may break consumer behaviour
- Flag as Red Flag: `"field {name} has nullable: true in existing OAS — CISO mandates false. Verify consumer impact before changing."`
- Apply input version only if the input source explicitly specifies `nullable: false`

---

## Version Prefix Change

If input path has `/v2/accounts` but existing OAS has `/v1/accounts`:
- Different path → treat as **new endpoint** (append)
- Do NOT merge across version boundaries
- Log: `"New endpoint /v2/accounts added. Existing /v1/accounts preserved."`

---

## Tell User Before Writing

`"Merging {METHOD} {path} — {N} fields updated, {M} fields added, {K} fields removed, {P} response fields changed."`

---

## Report All Changes

Log in `## Merge Changes` section of `generation-report.md`:

| Category | Items to log |
|----------|-------------|
| Fields | UPDATED / ADDED / REMOVED — field names + what changed |
| Response fields | Same as above, per response code |
| Non-standard responses kept | Response codes preserved from existing OAS |
| Method changes | `POST → GET` |
| Path param renames | Old → new param name |
| Query/header param changes | Added / removed / updated |
| Required changes | `optional → required` or reverse |
| Orphaned files | Component files no longer referenced |
| Shared $ref warnings | Components that could not be safely merged |
| operationId changes | Old → new, with consumer impact warning |
