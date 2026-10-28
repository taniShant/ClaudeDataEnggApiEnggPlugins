---
name: pr-body-generator
description: "MR Body Generator — Generate the Markdown body content for a merge request that summarizes all CWE remediation changes made during a session. The MR body includes a summary table listing each finding with its CWE, affecte"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/git_ops/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# PR Body Generator
## Quick Start

This skill provides git operation patterns (commits, PR creation, branch management) used by the detox pipeline.

```
# Loaded by detox-orchestrator-agent during the Create PR phase.
# Handles atomic commits per CWE fix and PR body generation.
```



## Purpose

Generate the Markdown body content for a merge request that summarizes all CWE remediation changes made during a session. The MR body includes a summary table listing each finding with its CWE, affected file, severity, fix status, and validation result; a corrective actions section for findings that require manual follow-up; a Semgrep rescan summary showing validation results; and an auto-generated footer. This content is consumed by the `pr_creator` skill when creating the actual merge request.

## Inputs

- **remediation_results** (required, list[JSON object]): An array of remediation result objects, one per vulnerability processed. Each object must contain:
  - `vulnerability_id` (string, required): Unique identifier for the finding.
  - `cwe_id` (string, optional): CWE identifier (e.g., `CWE-89`).
  - `title` (string, required): Short title of the vulnerability.
  - `severity` (string, required): One of `critical`, `high`, `medium`, `low`, `info`.
  - `remediation_type` (string, required): One of `code_fix`, `infra_config`, `dependency`, `manual`.
  - `status` (string, required): One of `fixed`, `partially_fixed`, `not_fixed`, `deferred`, `skipped`, `not_applicable`, `unexploitable`.
  - `file_path` (string, optional): Path to the affected file (relative to repo root).
  - `validation_verdict` (string, optional): Rescan verdict: `PASS`, `PARTIAL`, `FAIL`, `ERROR`, or `N/A`.
  - `fix_description` (string, optional): Brief description of the fix applied.
- **corrective_actions** (optional, list[JSON object]): An array of corrective action references for non-code-fix findings. Each object should contain:
  - `vulnerability_id` (string): Reference to the finding.
  - `cwe_id` (string, optional): CWE identifier.
  - `title` (string): Title of the finding.
  - `responsible_team` (string): Team assigned to remediate.
  - `target_timeline` (string): Expected remediation timeline.
  - `document_ref` (string, optional): Reference to the corrective action document.
- **exploitability_assessments** (optional, list[JSON object]): An array of findings assessed as not applicable or likely unexploitable by exploitability analysis. These items were NOT remediated and need verification-and-suppression by the application team. Each object should contain:
  - `vulnerability_id` (string): Reference to the finding.
  - `cwe_id` (string, optional): CWE identifier.
  - `title` (string): Title of the finding.
  - `verdict` (string): Either `not_applicable` or `likely_unexploitable`.
  - `confidence` (float): Assessment confidence (0.0 to 1.0).
  - `evidence_summary` (string): One-line summary of the exploitability evidence (e.g., "Library not in dependency tree" or "enableDefaultTyping() not called in 247 source files").
  - `document_ref` (string, optional): Reference to the corrective action document in `corrective_actions_output/`.
- **rescan_summary** (optional, JSON object): Aggregate Semgrep rescan results containing:
  - `total_rescanned` (integer): Number of files rescanned.
  - `passed` (integer): Number that passed validation.
  - `partial` (integer): Number with partial resolution.
  - `failed` (integer): Number that failed validation.
  - `errors` (integer): Number that encountered scan errors.
  - `skipped` (integer): Number not rescanned (e.g., infra_config findings).
- **repo_name** (optional, string): Repository name for display.
- **branch_name** (optional, string): Branch name for reference.
- **template_path** (optional, string): Absolute path to a custom PR body template. Defaults to `templates/pr_body_template.md`.

## Steps

1. **Validate inputs.**
   - Confirm `remediation_results` is a non-empty list.
   - Confirm each result has the required fields: `vulnerability_id`, `title`, `severity`, `remediation_type`, `status`.
   - Fill missing optional fields with defaults: `validation_verdict` defaults to `N/A`, `file_path` defaults to "N/A".

2. **Load the PR body template.**
   - Use `Read` to load the template from `template_path` (default: `templates/pr_body_template.md`).
   - If the template file does not exist, fall back to the built-in structure defined in this skill.

3. **Generate the summary table.**
   - Create a Markdown table with the following columns:
     - **CWE**: The CWE identifier (or "N/A").
     - **File**: The affected file path (relative to repo root, or "N/A").
     - **Severity**: The severity level, with an emoji indicator for quick visual scanning:
       - `critical`: `CRITICAL`
       - `high`: `HIGH`
       - `medium`: `MEDIUM`
       - `low`: `LOW`
       - `info`: `INFO`
     - **Status**: The fix status (`Fixed`, `Partially Fixed`, `Not Fixed`, `Deferred`, `Skipped`).
     - **Validated**: The validation verdict (`PASS`, `PARTIAL`, `FAIL`, `ERROR`, `N/A`).
   - Sort the table rows by severity (critical first), then by CWE ID numerically.
   - Example row: `| CWE-89 | src/db/queries.py | HIGH | Fixed | PASS |`

4. **Generate the corrective actions section.**
   - If `corrective_actions` is provided and non-empty, create a section titled "Corrective Actions Required".
   - For each corrective action, include:
     - Finding title and CWE ID.
     - Responsible team.
     - Target timeline.
     - Reference to the corrective action document (if available).
   - Format as a Markdown table with columns: CWE | Finding | Responsible Team | Timeline | Reference.
   - If `corrective_actions` is empty or not provided, include a brief note: "No corrective actions required. All findings were addressed through code changes."

4b. **Generate the exploitability assessments section.**
   - If `exploitability_assessments` is provided and non-empty, create a section titled "Exploitability Assessments — Verify & Suppress".
   - Explain that these findings were assessed as not applicable or likely unexploitable and were NOT remediated. The application team should verify each assessment and suppress in the scanner configuration.
   - Format as a Markdown table with the following columns:
     - **CWE**: The CWE identifier.
     - **Finding**: The finding title.
     - **Verdict**: `Not Applicable` or `Likely Unexploitable`.
     - **Confidence**: The confidence level (e.g., `High (0.92)`).
     - **Evidence**: One-line evidence summary.
     - **Reference**: Link to the corrective action document.
   - Sort by verdict (Not Applicable first, then Likely Unexploitable), then by confidence (lowest first — lowest confidence needs verification most).
   - If `exploitability_assessments` is empty or not provided, omit this section entirely. Do NOT include a "no assessments" placeholder.

5. **Generate the Semgrep rescan summary section.**
   - If `rescan_summary` is provided, create a section titled "Semgrep Rescan Summary".
   - Present the statistics:
     - Total files rescanned.
     - Passed / Partial / Failed / Error / Skipped counts.
     - Overall pass rate as a percentage.
   - Format as a compact Markdown list or small table.
   - If `rescan_summary` is not provided, derive a basic summary from the `validation_verdict` fields in `remediation_results`:
     - Count each verdict type across all results.
     - Present as a simplified summary.

6. **Generate the auto-generated footer.**
   - Include a footer line indicating the PR was generated automatically:
     ```
     ---
     *This merge request was auto-generated by the CWE Remediation Agent. All fixes should be reviewed before merging.*
     ```
   - Include the generation timestamp in ISO 8601 format.

7. **Assemble the full PR body.**
   - Combine all sections in order:
     1. Summary heading and one-line overview (e.g., "This PR remediates X vulnerability findings across Y files.").
     2. Summary table.
     3. Exploitability assessments section (only if `exploitability_assessments` is non-empty).
     4. Corrective actions section.
     5. Semgrep rescan summary.
     6. Auto-generated footer.
   - If a template was loaded, populate its placeholders:
     - `{{SUMMARY_TABLE}}`: The generated summary table.
     - `{{CORRECTIVE_ACTIONS}}`: The corrective actions section.
     - `{{RESCAN_SUMMARY}}`: The Semgrep rescan summary.
     - `{{FOOTER}}`: The auto-generated footer.

8. **Return the result.**
   - Output the full PR body as a Markdown string within the structured JSON result.

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "pr_body": "<string: the full Markdown PR body content>",
  "statistics": {
    "total_findings": 15,
    "fixed": 12,
    "partially_fixed": 1,
    "not_fixed": 0,
    "deferred": 1,
    "skipped": 1,
    "not_applicable": 0,
    "unexploitable": 0,
    "corrective_actions_count": 2,
    "exploitability_assessments_count": 0,
    "rescan_pass_rate_percent": 92.3
  },
  "metadata": {
    "template_used": "<string: path to template or 'built-in'>",
    "generated_at": "2026-04-29T15:00:00Z"
  }
}
```

On failure, return:

```json
{
  "status": "failed",
  "error": "<string: human-readable description of what went wrong>"
}
```

### Success Indicators

- `status` is `"success"`.
- `pr_body` is a non-empty Markdown string.
- No placeholder tokens (e.g., `{{SUMMARY_TABLE}}`) remain in the body.
- The summary table has one row per finding in `remediation_results`.

### Failure Indicators

- `status` is `"failed"`.
- `error` describes the reason.

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| **Empty remediation results** | `remediation_results` is an empty list | Fail with error: "No remediation results provided. Cannot generate PR body." |
| **Missing required fields in a result** | A result lacks `vulnerability_id`, `title`, `severity`, `remediation_type`, or `status` | Skip the malformed entry. Add a note in the PR body: "Warning: X findings could not be included due to missing data." |
| **Template file not found** | `Read` returns file-not-found error | Log a warning and use the built-in structure. Do not fail. |
| **Corrective actions reference a vulnerability not in results** | `vulnerability_id` mismatch | Include the corrective action anyway with a note that the finding was not in the results set. |
| **Rescan summary counts do not match results count** | Sum of rescan categories does not equal `total_rescanned` | Present the data as-is with a note about the discrepancy. |
| **MR body exceeds GitLab limit (1048576 characters)** | Length check after assembly | Truncate the summary table to show only `critical` and `high` severity findings in full. Summarize `medium`, `low`, and `info` as aggregate counts. Add a note: "Full details available in the remediation summary document." |

## Constraints

- **Read-only**: This skill MUST NOT modify any files in the repository. It only reads the template and produces output.
- **No git operations**: This skill does not interact with git. It only generates content for the PR body.
- **No external calls**: Do not make API calls or network requests. All data comes from inputs.
- **GitLab Markdown compatibility**: The output must render correctly on GitLab. Use GitLab Flavored Markdown (GLFM) syntax for tables, task lists, and code blocks.
- **Character limit awareness**: GitLab MR description maximum is 1,048,576 characters. The skill should still aim for conciseness but has more room than GitHub.
- **No sensitive data**: Do not include credentials, tokens, API keys, or secrets in the PR body. Redact any sensitive data from code snippets or descriptions.
- **Idempotent**: Given the same inputs, the skill must produce the same output, except for the generation timestamp.
- **Tool usage**: Use only `Read` (to load the template). No other tools are needed.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
