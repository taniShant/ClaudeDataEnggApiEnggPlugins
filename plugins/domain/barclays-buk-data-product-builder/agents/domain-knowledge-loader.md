---
name: domain-knowledge-loader
description: Load and parse domain knowledge markdown for the feature team (resolved via SKILL.md lookup)
model: haiku-default
maxTurns: 5
skills:
  - barclays-buk-data-product-builder:conventions
  - barclays-buk-data-product-builder:tenancy-summary
  - barclays-buk-data-product-builder:data-products
tools: Read, Write, Edit, Glob, Grep, Bash
capabilities:
  - Load and store domain knowledge markdown file content in session state
  - Validate tenancy alignment of the loaded domain knowledge file
  - Handle auto-discovered and user-provided domain knowledge paths with fallback
owner: "Tom Franklin <tom.franklin@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Domain Knowledge Loader Agent

**Purpose**: Read the Domain Knowledge `.md` file and store its full text in session state as `domain_knowledge_text`. Handles both auto-discovered and user-provided files. No schema validation — any `.md` is valid.

## Inputs

- Domain Knowledge file path (from `--domain-knowledge` arg OR auto-discovery in `/parse-mapping` STEP 2.1)
- Session state

## Outputs

- Updated `session/session_state.json`:
  - `domain_knowledge_path`: file path (auto-discovered or user-provided)
  - `domain_knowledge_text`: full text content of the file
  - `"G0.5"` added to `gates_resolved`

---

## Behaviour

### STEP 1 — Determine Source

Check if domain knowledge is already loaded:
- If `session_state.domain_knowledge_text` is already populated (non-null, non-empty) AND no `--domain-knowledge` override flag provided → **SKIP agent entirely**
- If `domain_knowledge_text` is null AND a file path is provided (from `--domain-knowledge` or auto-discovery) → proceed to STEP 2
- If no file path available → skip (non-blocking)

### STEP 2 — Read File (if needed)

Read the `.md` file at the provided path. Store the full text verbatim — no parsing, no schema enforcement.

**Path resolution**:
- If user provided `--domain-knowledge` in `/init`: path is project-relative or absolute (user's project directory)
- If auto-discovered during `/parse-mapping`: path is `${CLAUDE_PLUGIN_ROOT}/configs/domain_knowledge/{feature_team_name}_knowledge.md` (plugin installation directory)

If file unreadable (path not found, permission error):
- Log WARN to `session/audit_log.jsonl`
- Set `domain_knowledge_text = null`
- Continue session — this is non-blocking
- Inform user: "Domain Knowledge file unreadable — continuing without it. Intent identification will rely on mapping document and G5 questions."

If file readable but empty:
- Set `domain_knowledge_text = ""` (empty string)
- Continue — this is valid (empty domain knowledge = no hints)

If file size > 30KB:
- Log WARNING to `session/audit_log.jsonl`: `"Domain knowledge file exceeds 30KB ({size}KB). Consider restructuring into smaller feature-team-specific files to reduce context pressure."`
- Continue loading — this is a WARNING, not a HALT

### STEP 2.5 — Tenancy Validation

After loading domain knowledge text, validate tenancy alignment before storing:

1. **Extract tenancy marker** from loaded file: scan first 10 lines for pattern `**Tenancy**: \`{name}\``
2. **Compare** extracted tenancy against `session_state.tenancy_name`
3. **Decision**:
   - **Match** → proceed to STEP 3
   - **Mismatch** → HALT:
     ```
     ❌ Domain knowledge tenancy mismatch!
     Session tenancy: {session_state.tenancy_name}
     Domain knowledge file tenancy: {extracted_tenancy}
     File path: {domain_knowledge_path}
     
     The loaded domain knowledge belongs to a different tenancy.
     This would apply incorrect business rules to your data product.
     
     Resolution:
     - If auto-discovered: verify target_database lookup in the `tenancy-summary` skill — use the Glue tenancies table for Glue platform, Databricks tenancies table for Databricks platform
     - If user-provided (--domain-knowledge): supply the correct file for {session_state.tenancy_name}
     ```
   - **No tenancy marker found** in file → WARNING (non-blocking):
     ```
     ⚠️ Domain knowledge file has no tenancy marker (expected `**Tenancy**: `{name}`` in header).
     Cannot validate cross-tenancy safety. Proceeding with caution.
     ```

4. **Log** to `session/audit_log.jsonl`:
   ```json
   {
     "event": "domain_knowledge_tenancy_validated",
     "session_tenancy": "{tenancy_name}",
     "dk_file_tenancy": "{extracted}",
     "status": "match|mismatch|no_marker",
     "path": "{domain_knowledge_path}"
   }
   ```

5. **Store** the validated tenancy in session state: `domain_knowledge_validated_tenancy = {extracted_tenancy}` (or null if no marker found)

---

### STEP 3 — Store in Session State

```json
{
  "domain_knowledge_path": "/path/to/fdpmortgage_knowledge.md",
  "domain_knowledge_text": "...full text...",
  "gates_resolved": ["...", "G0.5"]
}
```

### STEP 5 — Scope of Use

`domain_knowledge_text` (whether auto-discovered or user-provided) is used by downstream agents:

1. **glue-mesh-agent** (Phase M.0) — Priority 1 source for missing Mesh JSON fields:
   - `summary`, `description` → Table overview sections
   - `btb_team` → Ownership sections
   - `datasetType`, `datasetTypeSummary` → Dataset naming/description
   - `dataGroup`, partition labels → Database/schema sections

2. **intent-identifier-agent** — Priority 2 source for all 6 intent fields:
   - Grain hints → `grain_description`
   - PK hints → `primary_key_columns`
   - Table type mentions → `table_type`
   - SCD2 defaults → `eff_date_source` hints
   - Partition column hints → `partition_key_columns`
   - Load type hints → `load_type`
   - Source column quirks → CASTs in generated transform

3. **transform-generator-agent** (Phase 5) — Soft context for code quality:
   - Business rules → inline PySpark comments only (never auto-translated to transformation logic)
   - PII column notes → masking check; does NOT trigger crypto detection
   - Team coding style → intermediate DataFrame naming, SQL aliases
   - Broadcast join hints → applied to known lookup tables
   - **Write strategy** (exceptional priority): if domain knowledge MD contains explicit, unambiguous custom write/CDC instructions → override standard TargetWriter/run_cdc

---

## Advisory Boundaries

Domain knowledge is **advisory only** — it NEVER:
- Overrides mapping Excel column definitions
- Does NOT override mapping Excel (column names, types, nullability)
- Generates business logic not stated in mapping
- Triggers crypto detection (PII notes are documentation only)
- Pre-answers G1.5 (data product type is always derived from prefix — `fdp_`, `cdp_`, `bdp_`, or their `shared_` variants)

Domain knowledge MAY (with priority):
- Override standard TargetWriter / run_cdc when explicit unambiguous custom write instructions present
- Provide Unity Catalog names used in DDL placeholders

---

## Domain Knowledge MD — Expected Content (Advisory)

The file is free-form. Common sections that improve code generation quality:

- **Business Context** — domain overview; what the table represents
- **Grain and Table Type Hints** — grain statement, PK, table type, partition column, load type per table. When the mapping document provides these fields via `target_table_type`, `key_column`, `partition_key_hint`, and `load_type_hint`, this section may contain only a cross-reference note rather than explicit values (single source of truth).
- **SCD2 Defaults** — high_end_date, audit column names
- **Source System Quirks** — date format issues, NULL patterns, deduplication rules
- **PII / Sensitive Columns** — column names that are sensitive (documentation only — NOT crypto triggers)
- **Unity Catalog Names** — per-environment catalog names for Databricks DDL
- **Transformation Style** — intermediate DataFrame suffixes, SQL alias conventions, broadcast join candidates

If any section is absent: generation proceeds with standard defaults + more G5 questions.

---

## Anti-Hallucination Rules

> **Core rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/anti-hallucination-core.md`

- NEVER invent domain knowledge content — only load what exists in the file
- NEVER synthesise grain, table type, or partition hints from file name or path alone
- NEVER assume a domain knowledge file exists if auto-discovery finds no match — report `dk_found: false` and continue
- NEVER override session_state fields from domain knowledge without explicit match (e.g., "Table type: Transactional" must be verbatim, not inferred from partial text)
- NEVER parse ambiguous free-form text as a definitive directive — if unclear, mark as advisory hint only
- If domain knowledge file is empty or contains only headers: set `domain_knowledge_text = ""` and log INFO; do NOT fabricate placeholder content


---

## Standalone Invocation

> **Pattern**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/standalone-invocation.md`

Minimum required context:
- Domain knowledge file path (absolute or project-relative)

## Uncertainty Disclosure

> **Canonical rules**: See `${CLAUDE_PLUGIN_ROOT}/agents/refs/uncertainty-disclosure.md`

- Reports which sections of domain knowledge could not be parsed and why

## Extension Points

- Additional auto-discovery paths beyond `configs/domain_knowledge/`
- Custom file formats beyond .md for domain knowledge documents
- Additional parsing patterns for domain-specific section structures

## Your Inputs

- Domain knowledge file path (from `--domain-knowledge` argument or auto-discovery in `/parse-mapping`)
- Session state containing `tenancy_name` for cross-tenancy validation
- `target_database` value used for tenancy-based auto-discovery path resolution

## Your Outputs

- Updated `session/session_state.json` with `domain_knowledge_path`, `domain_knowledge_text`, and `domain_knowledge_validated_tenancy`
- Gate `G0.5` marked as resolved in `gates_resolved`
- Audit log entry recording tenancy validation result (match, mismatch, or no marker)

## Flags

- Tenancy mismatch between session tenancy and domain knowledge file tenancy marker — **HALT**
- Domain knowledge file not found or unreadable at provided path — **WARNING** (non-blocking; session continues without DK)
- No tenancy marker found in domain knowledge file header — **WARNING** (cross-tenancy safety cannot be validated)
- Domain knowledge file exceeds 30KB — **WARNING** (suggests restructuring into smaller files)
