---
name: remediation-summary
description: "Remediation Summary — Generate a comprehensive remediation summary document that provides a complete overview of all actions taken during a CWE remediation session. The summary covers what was successfully fixed through au"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/documentation/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Remediation Summary
## Quick Start

This skill provides documentation generation patterns for remediation reports and corrective action docs.

```
# Loaded by detox-report-agent and detox-orchestrator-agent during the Document and Report phases.
# Generates executive-level remediation reports and JIRA tickets.
```



## Purpose

Generate a comprehensive remediation summary document that provides a complete overview of all actions taken during a CWE remediation session. The summary covers what was successfully fixed through automated code changes, what requires manual action (with references to corrective action documents and Jira tickets), aggregate statistics on the remediation effort, and forward-looking recommendations. This document serves as the primary artifact for security review, audit trails, and management reporting.

## Inputs

- **remediation_results** (required, list[JSON object]): An array of remediation result objects, one per vulnerability processed. Each object must contain:
  - `vulnerability_id` (string, required): Unique identifier for the finding.
  - `cwe_id` (string, optional): CWE identifier (e.g., `CWE-89`).
  - `title` (string, required): Short title of the vulnerability.
  - `severity` (string, required): One of `critical`, `high`, `medium`, `low`, `info`.
  - `remediation_type` (string, required): One of `code_fix`, `infra_config`, `dependency`, `manual`.
  - `status` (string, required): One of `fixed`, `partially_fixed`, `not_fixed`, `deferred`, `skipped`.
  - `file_path` (string, optional): Path to the affected file.
  - `validation_verdict` (string, optional): Rescan verdict if applicable: `PASS`, `PARTIAL`, `FAIL`, `ERROR`, or `N/A`.
  - `fix_description` (string, optional): Brief description of the fix applied.
  - `corrective_action_doc` (string, optional): Reference to a generated corrective action document.
  - `jira_ticket_ref` (string, optional): Reference to a generated Jira ticket.
- **repo_name** (required, string): Name of the repository being remediated.
- **branch_name** (required, string): Name of the remediation branch (e.g., `remediate/cwe-79-89-20260429-143000`).
- **base_branch** (optional, string): The base branch the remediation was branched from. Defaults to `main`.
- **session_start_time** (optional, string): ISO 8601 timestamp of when the remediation session began.
- **session_end_time** (optional, string): ISO 8601 timestamp of when the remediation session ended.

## Steps

1. **Validate inputs.**
   - Confirm `remediation_results` is a non-empty list.
   - Confirm each result has the required fields: `vulnerability_id`, `title`, `severity`, `remediation_type`, and `status`.
   - Confirm `repo_name` and `branch_name` are non-empty strings.
   - If any result is missing optional fields, fill with sensible defaults (e.g., `validation_verdict` defaults to `"N/A"`).

2. **Calculate aggregate statistics.**
   - **Total findings processed**: Count of all results.
   - **By status**:
     - `fixed`: Successfully remediated and validated.
     - `partially_fixed`: Fix applied but validation showed partial resolution.
     - `not_fixed`: Attempted but fix was unsuccessful or validation failed.
     - `deferred`: Intentionally deferred to a future sprint.
     - `skipped`: Not attempted (e.g., duplicate, out of scope).
   - **By remediation type**: Count of `code_fix`, `infra_config`, `dependency`, `manual`.
   - **By severity**: Count of `critical`, `high`, `medium`, `low`, `info`.
   - **Fix rate**: Percentage of findings with status `fixed` out of total findings.
   - **Validation summary**: Count of each validation verdict (`PASS`, `PARTIAL`, `FAIL`, `ERROR`, `N/A`).

3. **Generate the "What Was Fixed" section.**
   - List all findings with status `fixed` or `partially_fixed`.
   - For each, include: vulnerability ID, CWE ID, title, file path, severity, and a brief description of the fix.
   - Organize by severity (critical first, then high, medium, low, info).
   - Format as a Markdown table with columns: CWE | File | Severity | Fix Description | Validated.

4. **Generate the "What Needs Manual Action" section.**
   - List all findings with status `not_fixed`, `deferred`, or `skipped`, as well as those with `remediation_type` of `infra_config`, `dependency`, or `manual`.
   - For each, include: vulnerability ID, CWE ID, title, severity, remediation type, reason for manual action, and a reference to the corrective action document or Jira ticket if available.
   - Format as a Markdown table with columns: CWE | Title | Severity | Type | Action Required | Reference.

5. **Generate the statistics section.**
   - Present the aggregate statistics computed in step 2 in a clear, scannable format.
   - Include a quick summary line: e.g., "12 of 15 findings fixed (80% fix rate). 3 findings require manual action."
   - Present detailed breakdowns as Markdown tables or bullet lists.

6. **Generate the recommendations section.**
   - Based on the results, produce 3 to 5 actionable recommendations:
   - If there are unresolved `dependency` findings, recommend a dependency update sprint or tool integration (e.g., Dependabot, Renovate).
   - If there are unresolved `infra_config` findings, recommend an infrastructure security review.
   - If there are unresolved `manual` findings, recommend a security architecture review session.
   - If the fix rate is below 70%, recommend investigating why fixes failed and whether skill coverage needs expansion.
   - If any validation verdicts are `FAIL` or `ERROR`, recommend manual code review for those specific files.
   - If all findings are `fixed` with `PASS` validation, recommend scheduling regular automated rescans to prevent regression.

7. **Assemble the full summary document.**
   - Combine all sections into a single Markdown document with the following structure:
     1. Title and metadata (repo name, branch, date, session duration).
     2. Executive summary (1-3 sentences).
     3. Statistics overview.
     4. What was fixed (detailed table).
     5. What needs manual action (detailed table).
     6. Recommendations.
     7. Footer with generation timestamp and tool attribution.

8. **Return the result.**
   - Output the full summary document and the computed statistics as structured JSON.

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "document": "<string: the full Markdown remediation summary>",
  "statistics": {
    "total_findings": 15,
    "by_status": {
      "fixed": 10,
      "partially_fixed": 2,
      "not_fixed": 1,
      "deferred": 1,
      "skipped": 1
    },
    "by_remediation_type": {
      "code_fix": 10,
      "infra_config": 2,
      "dependency": 2,
      "manual": 1
    },
    "by_severity": {
      "critical": 2,
      "high": 5,
      "medium": 6,
      "low": 2,
      "info": 0
    },
    "fix_rate_percent": 80.0,
    "validation_summary": {
      "PASS": 10,
      "PARTIAL": 2,
      "FAIL": 1,
      "ERROR": 0,
      "N/A": 2
    }
  },
  "metadata": {
    "repo_name": "org/repo",
    "branch_name": "remediate/cwe-79-89-20260429-143000",
    "base_branch": "main",
    "generated_at": "2026-04-29T15:00:00Z",
    "session_duration_minutes": 45
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
- `document` is a non-empty Markdown string with all sections populated.
- `statistics` contains accurate counts that are internally consistent (e.g., `total_findings` equals the sum of all `by_status` counts).

### Failure Indicators

- `status` is `"failed"`.
- `error` describes the reason for failure.

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| **Empty remediation results** | `remediation_results` is an empty list | Fail with error: "No remediation results provided. Cannot generate summary." |
| **Missing required fields in a result** | A result lacks `vulnerability_id`, `title`, `severity`, `remediation_type`, or `status` | Skip the malformed result. Include it in an "Errors" section of the summary noting which results could not be processed. Continue processing valid results. |
| **Unrecognized status value** | Status is not one of `fixed`, `partially_fixed`, `not_fixed`, `deferred`, `skipped` | Treat as `skipped` and note the unrecognized value in the summary. |
| **Unrecognized severity value** | Severity is not one of `critical`, `high`, `medium`, `low`, `info` | Treat as `medium` and note the assumption. |
| **Statistics do not sum correctly** | Internal consistency check fails | Log a warning in the metadata. Do not fail -- present the best-effort statistics. |
| **Session times not provided** | `session_start_time` or `session_end_time` is absent | Omit session duration from the summary. Use current timestamp for the "generated at" field. |

## Constraints

- **Read-only**: This skill MUST NOT modify any files in the repository. It produces output only.
- **No external calls**: Do not make API calls, network requests, or interact with any external service. All data comes from the provided inputs.
- **Accurate statistics**: The statistics section must reflect the actual data. Never fabricate, estimate, or round numbers misleadingly. Percentages should be rounded to one decimal place.
- **No sensitive data**: Do not include credentials, tokens, or secrets in the summary. If code snippets in the results contain sensitive data, omit or redact them.
- **Consistent formatting**: The output must be valid Markdown. Tables must have proper alignment. Lists must use consistent formatting.
- **Idempotent**: Given the same inputs, the skill must produce the same output, except for the `generated_at` timestamp.
- **Tool usage**: No tools are required. All processing is done in-memory on the provided inputs.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
