# Hook: mapping-change-detector

> **Type:** Documentation (orchestration logic — not an executable hook)

**Trigger**: When a mapping Excel file is re-uploaded or re-referenced mid-session (i.e. `/parse-mapping` called after artefacts already generated)

**Purpose**: Detect that the mapping document has changed; invalidate all downstream artefacts; preserve gate answers (platform, data product type, S3 locations). Never silently reuse stale data.

---

## Detection Logic

When `/parse-mapping` is invoked and `session_state.artefact_status` already contains entries:

1. Check if the Excel path is different from `session_state.mapping_excel_path`
2. If same path: compute a hash/fingerprint of the file content; compare with stored fingerprint
3. If either path or content changed: trigger invalidation

---

## Invalidation Behaviour

When mapping change detected:

### STEP 1 — Alert User

> "⚠️ Mapping document change detected. The following artefacts were generated from the previous mapping and are now stale:
>
> {list of all GENERATED/VALIDATED artefacts}
>
> These will be invalidated. Gate answers (platform, data product type, S3 locations) are preserved.
> Re-run `/parse-mapping` (using the Skill tool) and subsequent generation commands to regenerate from the updated mapping."

### STEP 2 — Invalidate Downstream Artefacts

Clear (do not delete files — mark as STALE in session state):
- `session/mapping_parsed.json` → delete and re-parse
- `session/crypto_flags.json` → clear
- `session/intent_identification.json` → clear
- All entries in `artefact_status` → set to `STALE`
- `open_placeholders` → clear

### STEP 3 — Preserve Gate Answers

Do NOT clear:
- `platform` (G1)
- `data_product_type`, `target_account`, routing fields (G1.5)
- `mesh_json_s3_locations` (G3)
- `domain_knowledge_text` (G0.5)
- `gates_resolved` (all gate answers preserved)

### STEP 4 — Proceed with New Parse

After invalidation, proceed with parsing the new/updated mapping Excel.

---

## Audit Log

```json
{
  "timestamp": "...",
  "event": "mapping_change_detected",
  "previous_path": "...",
  "new_path": "...",
  "artefacts_invalidated": ["mapping_parsed.json", "crypto_flags.json", ...],
  "gates_preserved": ["G1", "G1.5", "G3", "G0.5"]
}
```
