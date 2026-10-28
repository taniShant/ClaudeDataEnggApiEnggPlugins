---
name: sast-report-parser
description: "Wiz SAST Report Parser — Parse Wiz JSON reports into normalized Vulnerability array using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/parsing_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Wiz SAST Report Parser

## Purpose

Parse Wiz SAST scanner JSON report files into a structured JSON array of normalized vulnerability findings. Handles multiple Wiz JSON schema variants, maps severity levels, normalizes CWE IDs, and classifies remediation types by file extension patterns.

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/parsers/parse_wiz_report.py`. No LLM reasoning is required — field extraction uses priority-ordered lookups.

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{"report_path": "/path/to/wiz-report.json", "repo_root": "/path/to/repo"}' | {python} $PLUGIN_DIR/scripts/parsers/parse_wiz_report.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `report_path` | Yes | string | Absolute path to Wiz JSON report file |
| `repo_root` | No | string | Repository root for relative path resolution |

## Output Schema

```json
{
  "status": "success",
  "vulnerabilities": [
    {
      "id": "wiz-abc123",
      "cwe_id": "CWE-89",
      "title": "SQL Injection in User Query",
      "description": "...",
      "severity": "high",
      "source": "sast",
      "file_path": "src/db.py",
      "line_number": 42,
      "code_snippet": "...",
      "remediation_type": "code_fix",
      "tool_name": "wiz",
      "rule_id": "python-sqli",
      "confidence": 0.9
    }
  ],
  "summary": {
    "total_findings": 5,
    "by_severity": {"critical": 1, "high": 2, "medium": 2},
    "by_remediation_type": {"code_fix": 3, "infra_config": 1, "dependency": 1}
  }
}
```

## Supported Wiz JSON Structures

The script probes for findings in these locations (first match wins):
- `result[]` / `results[]`
- `data.results[]`
- `findings[]` / `issues[]`
- Top-level array (file is a JSON array)

## Error Handling

On failure, returns `{"status": "error", "error": "message", "stage": "input_validation|file_read|json_parse"}`.

## Constraints

- Read-only — does NOT modify the report file.
- Does NOT access repository source code.
- Does NOT fabricate findings.
- Output must be valid JSON parseable by `json.loads()`.
- Severity values: `critical`, `high`, `medium`, `low`, `info`.
- Remediation types: `code_fix`, `infra_config`, `dependency`, `manual`.
