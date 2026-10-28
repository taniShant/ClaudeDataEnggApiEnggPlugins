---
name: corrective-action-writer
description: "Corrective Action Writer — Generate a structured corrective action document for vulnerability findings classified as `infra_config`, `manual`, `partially_addressed`, `out_of_repo`, or `hybrid` that cannot be (fully) automatically remediated through code changes alone."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/documentation/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Corrective Action Writer
## Quick Start

This skill provides documentation generation patterns for remediation reports and corrective action docs.

```
# Loaded by detox-report-agent and detox-orchestrator-agent during the Document and Report phases.
# Generates executive-level remediation reports and JIRA tickets.
```



## Purpose

Generate a structured corrective action document for vulnerability findings classified as `infra_config`, `manual`, `partially_addressed`, `out_of_repo`, or `hybrid` that cannot be (fully) automatically remediated through code changes alone. The document explains what the finding is, why it cannot be auto-fixed (or why only a partial code fix was applied), the recommended remediation steps, the responsible team, and a proposed timeline. These documents serve as actionable handoff artifacts for infrastructure, security, and operations teams.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `id` (string, required): Unique identifier for the finding.
  - `cwe_id` (string, optional): CWE identifier (e.g., `CWE-311`).
  - `title` (string, required): Short title of the vulnerability.
  - `description` (string, required): Detailed description of the finding.
  - `severity` (string, required): One of `critical`, `high`, `medium`, `low`, `info`.
  - `source` (string, required): Either `threat_model` or `sast`.
  - `file_path` (string, optional): Path to the affected file or configuration.
  - `line_number` (integer, optional): Line number in the affected file.
  - `remediation_type` (string, required): Must be `infra_config`, `manual`, `partially_addressed`, `out_of_repo`, or `hybrid`.
  - `unaddressed_cwes` (array of strings, optional): For `partially_addressed` items — the CWE IDs that were NOT remediated.
  - `code_fix_applied` (boolean, optional): For `hybrid` items — indicates that a code fix was already applied in the repository.
  - `code_fix_commit_sha` (string, optional): For `hybrid` items — the commit SHA of the code fix that was applied.
  - `code_fix_description` (string, optional): For `hybrid` items — description of the code change that was applied.
  - `infra_actions` (array of strings, optional): For `hybrid` items — infrastructure changes still required (e.g., vault provisioning, load balancer config, DNS changes).
  - `external_repo_actions` (array of objects, optional): For `hybrid` items — changes required in external repositories. Each object contains `repo_name` (string), `description` (string), and `file_path` (string, optional).
- **classification_reasoning** (optional, string): The reasoning from the vulnerability classifier explaining why this finding was classified as non-code-fixable.
- **repo_name** (optional, string): Name of the repository for reference in the document.
- **template_path** (optional, string): Absolute path to a custom corrective action template. Defaults to `templates/corrective_action_template.md`.
- **exploitability_evidence** (optional, JSON object): Exploitability assessment data from the vulnerability classifier. Only provided when `remediation_type` is `not_applicable` or `likely_unexploitable`. Contains:
  - `verdict` (string): One of `not_applicable`, `likely_unexploitable`.
  - `confidence` (float): 0.0 to 1.0.
  - `signals` (array): Array of signal objects, each with `type` (string), `result` (string), `detail` (string).
  - `reasoning` (string): Human-readable explanation of the exploitability verdict.
  - `recommended_action` (string): One of `verify_and_suppress`, `remove_dependency`.

## Steps

1. **Validate inputs.**
   - Confirm `vulnerability` contains the required fields: `id`, `title`, `description`, `severity`, and `remediation_type`.
   - Confirm `remediation_type` is one of: `infra_config`, `manual`, `partially_addressed`, `out_of_repo`, `hybrid`, `not_applicable`, or `likely_unexploitable`. If it is `code_fix` or `dependency`, fail with an error -- those types should not produce corrective action documents.
   - If `cwe_id` is provided, normalize it to the standard format `CWE-<number>` (e.g., `cwe-311` becomes `CWE-311`).

2. **Load the corrective action template.**
   - Use `Read` to load the template from `template_path` (default: `templates/corrective_action_template.md`).
   - If the template file does not exist, fall back to generating the document from the built-in structure defined in this skill.

3. **Determine the affected component.**
   - If `file_path` is provided, use it as the affected component identifier.
   - If `file_path` points to an infrastructure file (e.g., `Dockerfile`, `*.tf`, `docker-compose.yml`, `nginx.conf`, `*.yaml` in `k8s/` or `helm/` directories), label the component type as "Infrastructure Configuration".
   - If `file_path` points to a security configuration (e.g., `web.config`, `.htaccess`, CORS policy files), label the component type as "Security Configuration".
   - If `file_path` is absent, use the `title` and `description` to infer the affected component (e.g., "TLS Configuration", "Session Management", "Access Control Policy").

4. **Determine why the finding cannot be (fully) auto-fixed.**
   - For `infra_config` findings, explain that the fix requires changes to infrastructure, deployment pipelines, cloud provider settings, or server configurations that are outside the scope of application source code.
   - For `manual` findings, explain that the fix requires architectural review, business logic decisions, access control policy changes, or other human judgment that cannot be safely automated.
   - For `partially_addressed` findings, explain that some CWEs for this attack path were remediated but others remain unresolved. List the `unaddressed_cwes` that still need attention and describe what additional work is required.
   - For `out_of_repo` findings, explain that the affected component resides in an external repository or shared library that cannot be modified from this repository. Use the `file_path` and `description` to identify the external component name.
   - For `hybrid` findings, explain that a code fix has been applied in this repository (reference `code_fix_commit_sha` and `code_fix_description`) but the remediation is INCOMPLETE without additional non-code changes. Clearly state:
     - **What was done**: The code fix applied (e.g., "Replaced hardcoded credential with `${DB_PASSWORD}` environment variable reference — commit `def5678`").
     - **What remains — infrastructure**: List each item from `infra_actions` as a required follow-up (e.g., "Provision the `DB_PASSWORD` secret in HashiCorp Vault for SIT, OAT, and Production environments").
     - **What remains — external repositories**: For each entry in `external_repo_actions`, document the target repository name, the specific file/path that needs modification, and a description of the required change.
   - For `not_applicable` findings, explain that the library or component was reported by the scanner but is **NOT present in this project's dependency tree**. The scanner likely detected it in a container base image, parent BOM, or scanning artifact — not in the application's declared dependencies. State clearly: **"This finding does not apply to this project."** Include the evidence from `exploitability_evidence` if provided:
     - Which manifest files were searched (pom.xml, build.gradle, package.json, etc.).
     - That the package was not found in any manifest or lock file.
     - The confidence level of the assessment.
   - Generate the document with the heading: `# ❌ Not Applicable: {{FINDING_TITLE}}`

   - For `likely_unexploitable` findings, explain that the library **IS present** in the project's dependencies but the specific vulnerable API surface (methods, classes, configurations) exploited by the CVE is **never imported or called** in the application code. The CVE is real for the library but is not exploitable in the context of this application's actual usage. Include the evidence from `exploitability_evidence` if provided:
     - Which dangerous APIs were searched for (method names, class names).
     - How many matches were found in application code (expected: zero).
     - How many source files were scanned.
     - How many import statements exist for this package (if zero, state: "The library exists on the classpath but is never imported or used by application code — consider removing it entirely.").
     - The dependency scope (test-only dependencies are lower risk since they are not deployed to production).
   - Always include a defence-in-depth note: "Even though this CVE is not exploitable today, upgrading to a patched version is recommended as a preventive measure during the next planned maintenance window."
   - Generate the document with the heading: `# ⚠️ Likely Unexploitable: {{FINDING_TITLE}}`

   - For both `not_applicable` and `likely_unexploitable` findings, include an **Evidence Table** section in the document body:
     ```markdown
     ## Evidence

     | Signal | Finding | Impact |
     |--------|---------|--------|
     | {signal_type} | {signal_result} | {signal_detail} |
     ```
     Populate the table from `exploitability_evidence.signals` if provided. If `exploitability_evidence` is not provided, generate a minimal evidence section noting that the assessment was based on available pipeline data.
   - If `classification_reasoning` is provided, incorporate it into the explanation.

5. **Generate recommended remediation steps.**
   - Based on the `cwe_id` and `description`, generate 3 to 7 specific, actionable remediation steps.
   - Each step must be concrete (e.g., "Enable TLS 1.2 or higher on the load balancer" not "Improve security").
   - Order steps from most critical to least critical.
   - Include verification steps where applicable (e.g., "Verify the change by running `curl -I https://... | grep Strict-Transport-Security`").
   - If the CWE is not recognized, generate generic steps based on the description and title.
   - For `not_applicable` findings, generate these specific steps:
     1. Verify the library is not in your dependency tree by running the appropriate command for your build system (e.g., `gradle dependencies | grep {package_name}`, `mvn dependency:tree | grep {package_name}`, or `npm ls {package_name}`).
     2. If confirmed absent — suppress this CVE for this project in your scanner (WIZ) configuration and document the suppression justification.
     3. If the library IS found (e.g., as a transitive dependency not visible in the manifest) — re-run the DETOX pipeline to reassess.
   - For `likely_unexploitable` findings, generate these specific steps:
     1. Verify that no code path calls the vulnerable API by running: `grep -rn "{dangerous_api_names}" src/` (list the specific API names from the evidence).
     2. If the library is entirely unused (zero import statements) — remove the dependency from the build file entirely. This is the cleanest fix and eliminates future CVE noise for this package.
     3. If the library IS used but the vulnerable API is not called — suppress the CVE in your scanner configuration and document the justification (e.g., "Application uses only safe API surface of {package}; vulnerable method {method} is never called").
     4. If the vulnerable API IS found after manual review — escalate to Security Engineering for remediation.
     5. Defence-in-depth: consider upgrading to a patched version during the next planned maintenance window regardless of exploitability, to prevent future code changes from introducing the vulnerable pattern.

6. **Determine the responsible team.**
   - Map the finding to a responsible team based on the remediation type and affected component:
     - Infrastructure/deployment files: "Infrastructure / DevOps Team"
     - TLS/SSL/network configuration: "Infrastructure / Network Security Team"
     - Cloud provider settings: "Cloud Operations Team"
     - Access control / authentication: "Security Engineering Team"
     - Business logic / architectural: "Application Architecture Team"
     - `out_of_repo`: "Security Team (Triage Required)" — the external component owner must be identified by the project lead
     - `partially_addressed`: "Application Development Team" (the team owning this repo)
     - `hybrid`: Assign MULTIPLE responsible teams based on the remaining actions:
       - If `infra_actions` are present: "Infrastructure / DevOps Team" (for infrastructure changes)
       - If `external_repo_actions` are present: "External Repository Owner ({repo_name})" for each external repo
       - Always include "Application Development Team" as a coordination point since they applied the code fix
       - List all responsible teams in the document, clearly indicating which team owns which action
     - `not_applicable`: "Security Scanning Team (Triage Required)" — the scanner configuration may need updating to avoid future false flags from container images or parent BOMs. The project lead should confirm the library is truly absent.
     - `likely_unexploitable`: "Application Development Team" — they own the codebase and can verify the assessment, remove unused dependencies, or suppress the finding. If the library is a transitive dependency, the team that owns the parent dependency should also be notified.
     - Unknown or ambiguous: "Security Team (Triage Required)"
   - This is a suggested default. Include a note that the responsible team should be confirmed by the project lead.

7. **Determine the target timeline.**
   - Map severity to a recommended remediation timeline:
     - `critical`: 1-3 business days
     - `high`: 5-7 business days
     - `medium`: 14 business days (2 weeks)
     - `low`: 30 business days (next sprint cycle)
     - `info`: No fixed timeline; address during next planned maintenance.
   - Include the severity-to-timeline mapping rationale in the document.

8. **Populate the template and generate the document.**
   - Fill in all placeholders in the template:
     - `{{FINDING_TITLE}}`: The vulnerability title.
     - `{{CWE_ID}}`: The CWE identifier, or "N/A" if not provided.
     - `{{SEVERITY}}`: The severity level (capitalized).
     - `{{DESCRIPTION}}`: The full description of the finding.
     - `{{AFFECTED_COMPONENT}}`: The affected component path and type.
     - `{{REASON_NOT_AUTO_FIXED}}`: Explanation of why the fix cannot be automated.
     - `{{RECOMMENDED_ACTIONS}}`: Numbered list of recommended remediation steps.
     - `{{RESPONSIBLE_TEAM}}`: The assigned team.
     - `{{TARGET_DATE}}`: The computed target date based on severity.
   - If no template was loaded, construct the document using the standard Markdown structure with the same sections.

9. **Return the generated document.**
   - Output the completed corrective action document as a Markdown string within the structured JSON result.

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "vulnerability_id": "<string>",
  "cwe_id": "<string or null>",
  "severity": "<string>",
  "remediation_type": "<string: infra_config | manual | partially_addressed | out_of_repo | hybrid | not_applicable | likely_unexploitable>",
  "document": "<string: the full Markdown corrective action document>",
  "responsible_team": "<string>",
  "target_timeline": "<string: e.g., '5-7 business days'>",
  "metadata": {
    "template_used": "<string: path to template or 'built-in'>",
    "repo_name": "<string or null>"
  }
}
```

On failure, return:

```json
{
  "status": "failed",
  "error": "<string: human-readable description of what went wrong>",
  "vulnerability_id": "<string or null>"
}
```

### Success Indicators

- `status` is `"success"`.
- `document` contains a well-formed Markdown document with all sections populated.
- No placeholder tokens (e.g., `{{FINDING_TITLE}}`) remain in the document.

### Failure Indicators

- `status` is `"failed"`.
- The `error` field describes the reason for failure.

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| **Missing required vulnerability fields** | Field is absent or empty in the input | Fail with error listing the missing fields. Do not generate a partial document. |
| **Remediation type is `code_fix` or `dependency`** | `remediation_type` value check | Fail with error: "Corrective action documents are only generated for `infra_config`, `manual`, `partially_addressed`, `out_of_repo`, `hybrid`, `not_applicable`, or `likely_unexploitable` findings." |
| **Template file not found** | `Read` returns file-not-found error | Log a warning and fall back to the built-in document structure. Do not fail. |
| **CWE ID not recognized** | CWE not in known mapping | Proceed with generic recommendations derived from the title and description. Add a note in the document. |
| **No file path and no description** | Both fields are absent or empty | Fail with error: "Insufficient information to generate a corrective action document. Provide at least a description." |
| **Severity not recognized** | Severity does not match known values | Default to `medium` and note the assumption in the document. |

## Constraints

- **Read-only on the repository**: This skill MUST NOT modify any files in the repository. It only reads the template and produces output.
- **No code execution**: Do not run any commands against the repository. All logic operates on the provided inputs and template.
- **Template fidelity**: If a custom template is provided, use it exactly as-is -- do not restructure or reorder its sections. Only fill in placeholders.
- **No sensitive data**: Do not include actual credentials, tokens, keys, or secrets in the generated document, even if they appear in the vulnerability description or code snippet. Replace them with `[REDACTED]`.
- **Consistent formatting**: The output document must be valid Markdown. Use heading levels (`##`, `###`) consistently. Use numbered lists for action items.
- **Timeline is advisory**: Always include a note that the target timeline is a recommendation based on severity and should be adjusted per organizational policy.
- **Tool usage**: Use only `Read` (to load the template). No other tools are needed.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
