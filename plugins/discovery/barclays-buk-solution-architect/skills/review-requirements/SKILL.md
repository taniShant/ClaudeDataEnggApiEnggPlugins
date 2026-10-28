---
name: review-requirements
user-invocable: true
description: >
    Review and validate a requirements.json file. Verifies schema, checks
    raw response SHA-256, and prints provenance. Never calls Jira or any LLM.
    Demonstrates deterministic validation in the requirements workflow.
---

# Review Requirements

Validate and review a `requirements.json` file. Verifies schema integrity and raw response hash, then prints provenance and normalised content. This skill is typically invoked during the understand-requirements workflow, or used independently to audit and verify requirements files.

## Quick Start

Provide the full path to the requirements.json file:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/review_requirements.py" \
  --requirements-path /path/to/workspace/requirements/BUKL2CUSX-173655.json \
  --workspace /path/to/workspace
```

## Parameters

- `--requirements-path` (required): Path to requirements.json file to review
- `--workspace` (optional): Workspace directory where raw response is stored. Defaults to `BUK_SA_WORKSPACE` environment variable. If neither is provided, infers from requirements.json location.

## Output

Prints to stderr (progress/status) and stdout (nothing by default).

**On stderr:**
- Schema validation status
- Hash verification status
- Provenance summary (Jira instance, issue key, retrieved timestamp, endpoint, requested fields, raw SHA-256)
- Normalised requirements summary (title, description, type, status, labels, components, linked issues, acceptance criteria)
- Any warnings from normalisation

**Exit code:** 0 on success, 1 on failure

## Validation Checks

✓ File exists and is readable
✓ Valid JSON
✓ Schema version is "1.0"
✓ All required provenance fields present:
  - `type` = "jira"
  - `instance`
  - `issue_key`
  - `retrieved_at` (ISO-8601)
  - `endpoint`
  - `requested_fields`
  - `raw_response_file`
  - `raw_response_sha256`
✓ `requirements` object present with all expected keys
✓ Raw response file exists at recorded location
✓ SHA-256 of raw file matches recorded value (detects tampering)

## Error Handling

| Condition | Action |
|---|---|
| File not found | Exit 1 with "Requirements file not found" |
| Invalid JSON | Exit 1 with JSON error details |
| Unsupported schema version | Exit 1 with version mismatch |
| Missing provenance fields | Exit 1 listing which fields are missing |
| Raw file not found | Exit 1 with file path |
| SHA-256 mismatch | Exit 1 with expected vs computed hash (evidence of tampering) |

## Guarantees

- **No Jira calls**: Uses only local files
- **No LLM involved**: Pure deterministic validation and display
- **Audit-safe**: Detects if raw response has been modified
- **Explicit**: Reports all validation failures; continues only on success

## Notes

This skill validates and displays requirements.json files that are automatically created during the requirements understanding workflow. It can also be used independently to audit and verify requirements files.

Pipeline context:

1. `understand-requirements` orchestration — retrieves (if needed) and normalises requirements
2. `review-requirements` — validate and display provenance (this skill, used within the workflow or independently)
3. (Downstream) Solution Architect agent consumes requirements.json for agentic review

requirements.json can be safely committed to version control (along with raw response file) for auditability. Both files belong to your external workspace, not the source repository.

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] The requirements artefact being reviewed is the intended input for this invocation.
- [ ] The complete supplied requirement set has been considered.
- [ ] Every review finding is grounded in evidence from the supplied requirements.
- [ ] Gaps, ambiguities and unresolved issues are explicitly surfaced rather than silently resolved.
- [ ] No requirement, fact or architectural decision has been invented during the review.