---
name: jira-ticket-generator
description: "Jira Ticket Generator — Generate structured Jira ticket content for vulnerability findings classified as `dependency` or `manual` that require human-driven remediation tracked through a ticketing workflow. The generated cont"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/documentation/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Jira Ticket Generator
## Quick Start

This skill provides documentation generation patterns for remediation reports and corrective action docs.

```
# Loaded by detox-report-agent and detox-orchestrator-agent during the Document and Report phases.
# Generates executive-level remediation reports and JIRA tickets.
```



## Purpose

Generate structured Jira ticket content for vulnerability findings classified as `dependency` or `manual` that require human-driven remediation tracked through a ticketing workflow. The generated content includes a summary line, a detailed description with technical context, acceptance criteria for verifying the fix, and a priority derived from the vulnerability severity. This skill does not create the Jira ticket directly -- it produces the content that can be copy-pasted or fed into a Jira API integration.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `id` (string, required): Unique identifier for the finding.
  - `cwe_id` (string, optional): CWE identifier (e.g., `CWE-937`).
  - `title` (string, required): Short title of the vulnerability.
  - `description` (string, required): Detailed description of the finding.
  - `severity` (string, required): One of `critical`, `high`, `medium`, `low`, `info`.
  - `source` (string, required): Either `threat_model` or `wiz`.
  - `file_path` (string, optional): Path to the affected file.
  - `line_number` (integer, optional): Line number in the affected file.
  - `remediation_type` (string, required): Expected to be `dependency` or `manual`.
  - `tool_name` (string, optional): Name of the scanner tool that reported the finding.
  - `rule_id` (string, optional): Scanner-specific rule identifier.
- **vulnerabilities_batch** (optional, list[JSON object]): A list of vulnerability objects to generate multiple tickets at once. If provided, `vulnerability` is ignored and each item in the list is processed independently.
- **repo_name** (optional, string): Name of the repository. Used in ticket summary and labels.
- **template_path** (optional, string): Absolute path to a custom Jira ticket template. Defaults to `templates/jira_ticket_template.md`.
- **project_key** (optional, string): Jira project key (e.g., `SEC`). Used to prefix the summary if provided.

## Steps

1. **Validate inputs.**
   - If `vulnerabilities_batch` is provided, confirm it is a non-empty list. Process each vulnerability individually through steps 2-8. Collect all results.
   - If `vulnerability` is provided (single finding), validate that it contains `id`, `title`, `description`, and `severity`.
   - If `remediation_type` is `code_fix`, log a warning -- Jira tickets are typically for `dependency` and `manual` findings -- but proceed anyway, as some organizations track all findings in Jira.

2. **Load the Jira ticket template.**
   - Use `Read` to load the template from `template_path` (default: `templates/jira_ticket_template.md`).
   - If the template file does not exist, fall back to the built-in structure defined in this skill.

3. **Generate the ticket summary.**
   - Format: `[<SEVERITY>] <CWE_ID>: <Title>` (e.g., `[HIGH] CWE-937: Vulnerable Third-Party Component in lodash`).
   - If `cwe_id` is not available, omit it: `[HIGH] Vulnerable Third-Party Component in lodash`.
   - If `project_key` is provided, prepend it: `[SEC] [HIGH] CWE-937: ...`.
   - Truncate to 255 characters maximum (Jira summary limit).

4. **Generate the ticket description.**
   - Structure the description with the following sections in Jira-compatible Markdown or wiki markup:
     - **Finding Details**: Include vulnerability ID, CWE ID, severity, source (threat model or WIZ), scanner tool name, and rule ID.
     - **Description**: The full vulnerability description.
     - **Affected Location**: File path and line number (if available). If not available, state "No specific file location identified."
     - **Context**: Explain why this finding requires manual action:
       - For `dependency` findings: "This finding relates to a vulnerable third-party component. Remediation requires updating or replacing the affected dependency, which may involve compatibility testing and is not safely auto-fixable."
       - For `manual` findings: "This finding requires human review and judgment. It may involve architectural changes, access control redesign, or business logic decisions that cannot be safely automated."
     - **References**: Include a link to the CWE entry (`https://cwe.mitre.org/data/definitions/<number>.html`) if `cwe_id` is provided.

5. **Generate acceptance criteria.**
   - Produce 3 to 5 specific, verifiable acceptance criteria based on the vulnerability type:
   - For `dependency` findings:
     - "The vulnerable dependency has been updated to a version that resolves the reported CVE/CWE."
     - "All automated tests pass after the dependency update."
     - "A dependency scan (e.g., Semgrep, Snyk, Dependabot) confirms no remaining findings for this component."
     - "No breaking changes were introduced by the update, or breaking changes have been addressed."
   - For `manual` findings:
     - "The finding has been reviewed by the security team and a remediation plan is documented."
     - "The remediation has been implemented and verified per the documented plan."
     - "A rescan or manual security review confirms the finding is resolved."
   - Tailor criteria further based on the `cwe_id` and `description` when possible.

6. **Map severity to Jira priority.**
   - Apply the following mapping:
     - `critical` -> `P1 - Critical` (Blocker)
     - `high` -> `P2 - High`
     - `medium` -> `P3 - Medium`
     - `low` -> `P4 - Low`
     - `info` -> `P5 - Informational` (Lowest / Trivial)

7. **Generate labels and components.**
   - Labels (list of strings):
     - Always include: `security`, `cwe-remediation`
     - Include `cwe-<number>` if `cwe_id` is available (e.g., `cwe-937`).
     - Include the `remediation_type` value (e.g., `dependency`, `manual`).
     - Include the severity value (e.g., `high`).
     - If `repo_name` is provided, include `repo:<repo_name>`.
   - Components (list of strings):
     - For `dependency` findings: `["Dependencies", "Security"]`
     - For `manual` findings: `["Security"]`
     - If the `file_path` maps to a known component area (e.g., `src/api/` -> `API`, `src/auth/` -> `Authentication`), include it.

8. **Populate the template and produce the ticket content.**
   - Fill in all placeholders in the template:
     - `{{SUMMARY}}`: The generated summary line.
     - `{{DESCRIPTION}}`: The generated description body.
     - `{{ACCEPTANCE_CRITERIA}}`: The acceptance criteria as a checklist.
     - `{{PRIORITY}}`: The mapped Jira priority.
     - `{{LABELS}}`: Comma-separated list of labels.
     - `{{COMPONENTS}}`: Comma-separated list of components.
   - If no template was loaded, construct the output using the built-in structure.

9. **Return the result.**
   - For single vulnerability input, return one ticket object.
   - For batch input, return an array of ticket objects.

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "tickets": [
    {
      "vulnerability_id": "<string>",
      "summary": "<string: Jira ticket summary line>",
      "description": "<string: full Jira ticket description in Markdown>",
      "acceptance_criteria": [
        "<string: criterion 1>",
        "<string: criterion 2>"
      ],
      "priority": "<string: P1 - Critical | P2 - High | P3 - Medium | P4 - Low | P5 - Informational>",
      "labels": ["<string>"],
      "components": ["<string>"],
      "metadata": {
        "cwe_id": "<string or null>",
        "severity": "<string>",
        "remediation_type": "<string>",
        "source": "<string>"
      }
    }
  ],
  "total_tickets": 1,
  "template_used": "<string: path to template or 'built-in'>"
}
```

On failure, return:

```json
{
  "status": "failed",
  "error": "<string: human-readable description of what went wrong>",
  "failed_ids": ["<string: vulnerability IDs that could not be processed>"]
}
```

### Success Indicators

- `status` is `"success"`.
- Each ticket in `tickets` has a non-empty `summary` and `description`.
- `total_tickets` matches the number of input vulnerabilities.

### Failure Indicators

- `status` is `"failed"`.
- `error` describes the reason for failure.

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| **Missing required vulnerability fields** | Field is absent or empty | Skip the individual ticket and record the vulnerability ID in `failed_ids`. If all tickets fail, return overall failure. |
| **Template file not found** | `Read` returns file-not-found error | Log a warning and fall back to built-in structure. Do not fail. |
| **Summary exceeds 255 characters** | Length check after generation | Truncate intelligently: keep the severity and CWE prefix, truncate the title portion, and append `...`. |
| **Batch input is empty** | `vulnerabilities_batch` is an empty list | Fail with error: "No vulnerabilities provided in batch." |
| **Unrecognized severity** | Severity not in the known mapping | Default to `P3 - Medium` and note the mapping assumption in the ticket description. |
| **CWE ID format is non-standard** | Does not match `CWE-\d+` | Attempt normalization (e.g., `cwe89` -> `CWE-89`, `89` -> `CWE-89`). If normalization fails, set `cwe_id` to null and omit from summary. |

## Constraints

- **Read-only**: This skill MUST NOT create or modify any files in the repository. It only reads the template and produces structured output.
- **No Jira API calls**: This skill generates ticket content only. It does not interact with the Jira API. Integration with Jira is the responsibility of a downstream step or external automation.
- **No sensitive data**: Do not include credentials, tokens, API keys, or secrets in the generated ticket content, even if they appear in the vulnerability description or code snippet. Replace with `[REDACTED]`.
- **Consistent formatting**: All ticket descriptions must use Markdown formatting compatible with Jira's rendering engine. Use headings (`h2.`, `h3.`) or Markdown (`##`, `###`) consistently.
- **Idempotent**: Given the same input, the skill must produce the same output. No randomness or non-deterministic behavior.
- **Batch efficiency**: When processing a batch, do not load the template repeatedly. Load it once in step 2 and reuse for all tickets.
- **Tool usage**: Use only `Read` (to load the template). No other tools are needed.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
