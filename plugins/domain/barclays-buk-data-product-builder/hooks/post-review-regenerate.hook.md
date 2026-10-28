# Post-Review Regenerate Hook

**Type:** Documentation (orchestration logic — not an executable hook)

**Triggered by:** `/review` command (Step 3 — Action Matrix)

**Purpose:** Documents the retry logic when `code-review-agent` returns Critical or High severity findings. The originating generator is re-invoked with the finding as context, and the affected file is re-reviewed.

---

## Retry Flow

```
code-review-agent returns finding (Critical or High)
  │
  ├─ Identify originating agent (by file path pattern under generated/):
  │    ├─ generated/glue/transforms/*_transform_day*.py → transform-generator-agent
  │    ├─ generated/databricks/src/Notebooks/{day0|day1}/*/*_transform.py → transform-generator-agent
  │    ├─ generated/glue/wrapper/*_wrapper.py / *_config.json → glue-wrapper-agent
  │    ├─ generated/databricks/src/Notebooks/{day0|day1}/*/*_driver.py → databricks-artefact-agent (artefact_scope: "driver")
  │    ├─ generated/databricks/src/Notebooks/utilities/*_table_creation_utility.py → databricks-artefact-agent (artefact_scope: "ddl")
  │    ├─ generated/glue/mesh/*_mesh.json → glue-mesh-agent
  │    ├─ generated/glue/dtxog/*_dtxog.json → glue-dtxog-agent
  │    └─ generated/*/tests/**/test_*.py / conftest.py → test-generator-agent
  │
  ├─ For cross_artefact_consistency findings (override file-pattern routing):
  │    ├─ Config alias/db/table/filter/source-type → glue-wrapper-agent
  │    ├─ DTXOG S3 path mismatch → glue-dtxog-agent
  │    ├─ Reader/Writer PK/partition mismatch → transform-generator-agent
  │    ├─ Mesh ↔ Transform column mismatch (mesh has extra) → glue-mesh-agent
  │    ├─ Mesh ↔ Transform column mismatch (transform missing) → transform-generator-agent
  │    └─ DDL partition ↔ Transform (Databricks) → transform-generator-agent
  │
  ├─ Re-invoke agent (using the Agent tool) with additional_context:
  │    "REVIEW FINDING (must fix): {description} in {file}:{line}"
  │    For cross-artefact: "CROSS-ARTEFACT FINDING (must fix): {description}"
  │    **ALWAYS INCLUDE:** "STEP 0.5 template read enforced — re-read template before fixing."
  │
  ├─ After re-generation, re-run code-review-agent (using the Agent tool) on affected file ONLY
  │
  └─ Check: finding resolved?
       ├─ YES → continue to next finding
       └─ NO → increment retry counter (max 2 per file)
              ├─ retries < 2 → loop back to re-invoke
              └─ retries >= 2 → HALT with review_status: "REJECTED"
```

---

## Constraints

- **Max retries per file:** 2
- **Scope of re-review:** Only the affected file (not full suite)
- **Halt condition:** Any Critical/High finding unresolved after 2 retries → `agent_status.code_review = "rejected"`, pipeline stops
- **Auto-fixable findings (Medium):** Never trigger this hook — handled inline by `/review` Step 3

---

## Platform Applicability

This hook logic applies identically to both Glue and Databricks platforms. The only difference is which originating agent is re-invoked based on file type.

---

## Template Re-Read Requirement

When re-invoking an agent after code review findings:

1. **Always re-read templates** — Agent must execute STEP 0.5 again before attempting fixes
2. **Reason**: Findings may stem from template drift (agent ignoring template structure in first pass)
3. **Include in context**: Add directive "STEP 0.5 template read enforced" to additional_context
4. **Template wins**: If the fix conflicts with template structure, the template is authoritative

---

## Anti-Hallucination Rules

- NEVER assume a finding is fixed without re-reading the regenerated file
- NEVER skip the re-review step after regeneration
- NEVER increase retry count beyond 2 — HALT is mandatory
- ALWAYS pass the exact finding description (not a paraphrase) as additional_context
- ALWAYS include template re-read directive in additional_context
