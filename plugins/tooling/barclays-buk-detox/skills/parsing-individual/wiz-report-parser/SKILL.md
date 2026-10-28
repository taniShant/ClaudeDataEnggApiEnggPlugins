---
name: wiz-report-parser
description: "Wiz Report Parser — Parse Wiz SAST/SCA JSON report files into a structured JSON array of normalized vulnerability findings conforming to the project's `Vulnerability` data model. This skill handles the Wiz-specific J"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/parsing_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Wiz wiz Report Parser
## Quick Start

This skill provides parsing logic for extracting vulnerability data from wiz reports and threat models.

```
# Loaded by detox-parser-agent during the Parse Reports phase.
# Normalises findings from Wiz JSON and Markdown threat model formats.
```



## Purpose

Parse Wiz scanner JSON report files into a structured JSON array of normalized vulnerability findings conforming to the project's `Vulnerability` data model. This skill handles the Wiz-specific JSON schema, maps Wiz severity levels and rule IDs to the project's canonical format, and extracts all relevant metadata from each finding.

## Inputs

- **report_path** (required, string): Absolute file path to the Wiz wiz JSON report file. The file must have a `.json` extension.
- **repo_root** (optional, string): The root path of the repository being analyzed. Used to resolve or normalize file paths found in the Wiz report.

## Steps

1. **Read the Wiz wiz JSON report** using the Read tool at the file path provided.

2. **Validate the JSON structure**. A valid Wiz wiz report is a JSON object with a top-level `result` (or `results`) array. Each element in this array represents a single finding. If the top-level structure is different, attempt these alternate locations:
   - `data.results[]`
   - `findings[]`
   - Top-level array (the file itself is a JSON array)
   - `issues[]`

   If none of these structures are found, report an error.

3. **Map each Wiz finding to the Vulnerability model**. For each finding object in the results array, extract and transform fields as follows:

   a. **id**: Generate using the format `wiz-{index}` where index is the 1-based position, OR use the Wiz finding ID if available (field: `id`, `finding_id`, or `ruleId`). Prefer the Wiz-native ID for traceability but prefix it: `wiz-{wiz_id}`.

   b. **cwe_id**: Extract from the Wiz finding. Look in these locations in order of priority:
      - `cwe` field (may be `"CWE-89"` or just `"89"` or `89`)
      - `cweId` field
      - `rule.cwe` field
      - `tags` or `labels` array containing a `CWE-\d+` pattern
      - `ruleId` field — some Wiz rule IDs embed CWE references
      - If found as a bare number, normalize to `CWE-###` format (e.g., `89` -> `CWE-89`).
      - If not found, set to `null`.

   c. **title**: Extract from (in order of priority):
      - `title` field
      - `name` field
      - `rule.name` field
      - `rule.title` field
      - `summary` field
      - If none found, construct from the rule ID: `"Wiz finding: {ruleId}"`.

   d. **description**: Extract from (in order of priority):
      - `description` field
      - `details` field
      - `rule.description` field
      - `message` field
      - Concatenate `remediation` or `recommendation` text if present, appending it after a newline separator.
      - If not found, set to empty string `""`.

   e. **severity**: Map Wiz severity values to the canonical severity enum using the mapping below:

      | Wiz Value        | Canonical Value |
      |------------------|-----------------|
      | `CRITICAL`       | `critical`      |
      | `HIGH`           | `high`          |
      | `MEDIUM`         | `medium`        |
      | `LOW`            | `low`           |
      | `INFORMATIONAL`  | `info`          |

      Look for the severity in these fields: `severity`, `risk`, `priority`, `rule.severity`.
      The comparison must be case-insensitive (e.g., `"High"`, `"HIGH"`, `"high"` all map to `high`).
      If no severity is found, default to `medium`.

   f. **file_path**: Extract the affected file path from (in order of priority):
      - `filePath` field
      - `file` field
      - `location.path` field
      - `resource.filePath` field
      - `sourceLocation.file` field
      - If `repo_root` is provided and the path is absolute, make it relative to `repo_root`. If the path is already relative, use it as-is.
      - If not found, set to `null`.

   g. **line_number**: Extract from (in order of priority):
      - `lineNumber` field
      - `line` field
      - `location.startLine` field
      - `sourceLocation.line` field
      - `location.line` field
      - Must be a positive integer. If found as a string, parse to int.
      - If not found, set to `null`.

   h. **code_snippet**: Extract from (in order of priority):
      - `codeSnippet` field
      - `snippet` field
      - `code` field
      - `sourceLocation.snippet` field
      - If not found, set to `null`.

   i. **remediation_type**: Classify based on the file path and rule metadata:
      - `infra_config`: If `file_path` matches `*.tf`, `*.tfvars`, `Dockerfile*`, `docker-compose*`, `*.yaml`/`*.yml` in paths containing `k8s`, `kubernetes`, `helm`, `deploy`, `infra`, `terraform`, `.github/workflows`, or `cloudformation`.
      - `dependency`: If the rule ID or tags contain `dependency`, `CVE-`, `outdated`, `vulnerable-package`, or if `file_path` matches `requirements.txt`, `package.json`, `Gemfile`, `pom.xml`, `go.mod`, `Cargo.toml`, `*.lock`.
      - `code_fix`: If `file_path` matches source code extensions (`.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.cs`, `.c`, `.cpp`, `.rs`, `.php`, `.kt`, `.swift`, `.scala`).
      - `manual`: If the rule metadata includes tags like `design`, `architecture`, `manual-review`, or if no file path is available.
      - Default to `code_fix` if classification is ambiguous.

   j. **source**: Always set to `wiz`.

   k. **tool_name**: Always set to `wiz`.

   l. **rule_id**: Extract the Wiz rule identifier from (in order of priority):
      - `ruleId` field
      - `rule.id` field
      - `ruleID` field
      - `checkId` field
      - If not found, set to `null`.

   m. **confidence**: Extract from the Wiz finding if available (`confidence`, `certainty` fields). If present, normalize to a 0.0-1.0 float:
      - If Wiz provides a string: `"high"` -> `0.9`, `"medium"` -> `0.7`, `"low"` -> `0.5`
      - If Wiz provides a percentage: divide by 100
      - If Wiz provides a 0.0-1.0 float: use directly
      - If not found, default to `0.8`.

4. **Assemble the final JSON array** of vulnerability objects and return it.

## Output Format

Return a JSON array where each element conforms to the `Vulnerability` model schema:

```json
[
  {
    "id": "wiz-abc123",
    "cwe_id": "CWE-502",
    "title": "Insecure Deserialization of User Input",
    "description": "The application deserializes untrusted data using pickle.loads() without validation, allowing remote code execution.",
    "severity": "critical",
    "source": "wiz",
    "file_path": "src/api/handlers.py",
    "line_number": 87,
    "code_snippet": "data = pickle.loads(request.body)",
    "remediation_type": "code_fix",
    "tool_name": "wiz",
    "rule_id": "python-deserialization-pickle",
    "confidence": 0.9
  },
  {
    "id": "wiz-def456",
    "cwe_id": "CWE-798",
    "title": "Hardcoded Credentials in Configuration",
    "description": "Database password is hardcoded in the Terraform configuration file instead of using a secrets manager.",
    "severity": "high",
    "source": "wiz",
    "file_path": "infra/terraform/database.tf",
    "line_number": 23,
    "code_snippet": "password = \"SuperSecret123!\"",
    "remediation_type": "infra_config",
    "tool_name": "wiz",
    "rule_id": "terraform-hardcoded-credentials",
    "confidence": 0.9
  }
]
```

**Success indicator**: The output is valid JSON, is an array (possibly empty if the report contained zero findings), and every object contains at minimum the `id`, `title`, `severity`, `source`, and `tool_name` fields.

**Failure indicator**: The output is not valid JSON, or the report file could not be parsed at all.

## Error Handling

- **File does not exist or is not readable**: Return an error message describing the issue. Do not return a partial result.
- **File is not valid JSON**: Return an error message. Attempt to identify the issue (e.g., truncated file, BOM characters, single quotes instead of double). Do not attempt to repair malformed JSON.
- **JSON structure does not match any known Wiz format**: Return an empty array `[]` and include a warning that the report structure was not recognized. List the top-level keys found for debugging.
- **Individual finding is missing required fields**: Include the finding with `null` for missing optional fields. Only skip a finding entirely if it has no identifiable title, description, or rule ID whatsoever.
- **Unknown severity value**: Log the unrecognized value and default to `medium`. Include the original value in the description for traceability (e.g., append `"[Original severity: IMPORTANT]"`).
- **Malformed CWE reference** (e.g., `"CWE-ABC"`, `"0"`, negative number): Set `cwe_id` to `null`. Do not attempt to guess.
- **Duplicate Wiz finding IDs**: Append a suffix to make unique (e.g., `wiz-abc123`, `wiz-abc123-2`, `wiz-abc123-3`).
- **Very large report (thousands of findings)**: Process all findings. Do not truncate or sample. The downstream pipeline handles prioritization.

## Constraints

- Do NOT modify the Wiz report file. This skill is read-only.
- Do NOT access the repository's source code files. This skill only parses the report content.
- Do NOT fabricate findings that are not present in the Wiz report.
- Do NOT attempt to fix or remediate any vulnerabilities. This skill is parsing only.
- Do NOT re-score severity values from the Wiz report. Apply the mapping as defined, nothing more.
- Output MUST be valid JSON parseable by Python's `json.loads()`.
- Each `id` field MUST be unique within the output array.
- The `source` field MUST always be `wiz`.
- The `tool_name` field MUST always be `wiz`.
- The `severity` field MUST be one of: `critical`, `high`, `medium`, `low`, `info` (lowercase).
- The `remediation_type` field MUST be one of: `code_fix`, `infra_config`, `dependency`, `manual`.
- The severity mapping MUST follow the table in Step 3e above.
- Processing should complete within the Claude Code timeout (300 seconds).

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
