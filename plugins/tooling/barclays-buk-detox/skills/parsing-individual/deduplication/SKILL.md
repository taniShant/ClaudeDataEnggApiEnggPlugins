---
name: deduplication
description: "Vulnerability Deduplication — Deduplicate findings by composite key using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/parsing_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Vulnerability Deduplication
## Quick Start

This skill provides deduplication logic for vulnerability findings, implemented as a deterministic Python script.

```
# Loaded by detox-parser-agent during the Parse Reports phase.
# Deduplicates findings from Wiz JSON and Markdown threat model formats.
```



## Purpose

Deduplicate vulnerability findings from multiple sources by matching on the composite key `(file_path, line_number, cwe_id)`. When duplicates are detected, merge metadata using the highest-severity strategy.

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/parsers/deduplicate_findings.py`. No LLM reasoning is required — deduplication is pure key matching and merge logic.

### Inputs

- **vulnerabilities** (required, JSON array): A normalized array of `Vulnerability` objects. All findings should already be normalized (by the vulnerability_normalizer skill) before deduplication. The array may contain findings from threat model reports, WIZ scanners, or both.
- **merge_strategy** (optional, string): Controls how duplicates are merged. One of:
  - `"highest_severity"` (default): Keep the entry with the highest severity as the base and merge fields from other duplicates.
  - `"most_complete"`: Keep the entry with the most non-null fields as the base.
  - `"first_seen"`: Keep the first entry encountered as the base (preserves original ordering priority).

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{
  "vulnerabilities": [...],
  "merge_strategy": "highest_severity"
}' | {python} $PLUGIN_DIR/scripts/parsers/deduplicate_findings.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `vulnerabilities` | Yes | list[object] | Array of Vulnerability objects to deduplicate |
| `merge_strategy` | No | string | `highest_severity` (default), `most_complete`, or `first_seen` |

## Deduplication Algorithm

3. **Group findings by deduplication key**. Create groups where each group contains all findings that share the same `(file_path, line_number, cwe_id)` key. Findings with any `null` key field each form their own singleton group (they cannot be deduplicated).

4. **Merge each group into a single finding**. For groups with more than one finding, merge as follows:

### Step 4a: Select the base finding

   According to the `merge_strategy`:

   - **highest_severity** (default): Select the finding with the highest severity as the base. Severity order from highest to lowest: `critical` > `high` > `medium` > `low` > `info`. If multiple findings share the highest severity, prefer the one from `wiz` source (WIZ findings typically have more precise location data). If still tied, use the first encountered.

   - **most_complete**: Count non-null fields for each finding. Select the one with the highest count as the base. Ties broken by highest severity, then by source preference (`wiz` > `threat_model`), then by first encountered.

   - **first_seen**: Use the first finding in the array as the base.

### Step 4b: Merge metadata from non-base findings into the base

   For each field, apply the following merge rules:

   - **id**: Keep the base finding's `id`. Append the other finding IDs to a new `merged_ids` list in the output.
   - **cwe_id**: Already identical (part of the dedup key). Keep as-is.
   - **title**: Keep the longer (more descriptive) title between the base and duplicate findings.
   - **description**: Keep the longer description. If the duplicate's description contains substantially different information (more than 50% of its content is not a substring of the base), append the duplicate's unique content separated by `"\n\n[Additional context from {source}]: "`.
   - **severity**: Always keep the HIGHEST severity across all duplicates, regardless of merge strategy. This is a safety-first policy: `critical` > `high` > `medium` > `low` > `info`.
   - **source**: If duplicates come from different sources, set to the base's source. Record all sources in a `merged_sources` list.
   - **file_path**: Already identical (part of the dedup key). Keep as-is.
   - **line_number**: Already identical (part of the dedup key). Keep as-is.
   - **code_snippet**: Prefer whichever is non-null. If both are non-null, keep the longer one.
   - **remediation_type**: Keep the base finding's value. If the duplicate has a different value, prefer `code_fix` over `infra_config` over `dependency` over `manual` (more actionable types take priority).
   - **tool_name**: Keep the base finding's value. Record all tool names in a `merged_tools` list if they differ.
   - **rule_id**: Keep the base finding's value. If the base has no `rule_id` but a duplicate does, use the duplicate's value.
   - **confidence**: Keep the HIGHEST confidence score across all duplicates.

### Step 4c: Add merge metadata

   For each merged finding (where the group had more than one entry), add the following metadata fields to the output object:

   - `merged_ids`: Array of `id` values from all findings that were merged into this one (excluding the base finding's own id).
   - `merged_sources`: Array of unique `source` values across all findings in the group (e.g., `["threat_model", "wiz"]`).
   - `merged_tools`: Array of unique `tool_name` values across all findings in the group (e.g., `["claude_threat_model", "wiz"]`).
   - `merge_count`: Integer count of how many findings were merged (including the base, so minimum 2 for a merged finding).

   For singleton groups (no duplicates found), do NOT add these fields.

5. **Preserve original ordering**. The output array should maintain the order of first appearance. Specifically, each merged finding appears at the position of the earliest-encountered finding in its group.

6. **Produce a deduplication summary** as a JSON object appended to the output for observability:

## Output Schema

```json
{
  "status": "success",
  "vulnerabilities": [...],
  "summary": {
    "input_count": 15,
    "output_count": 11,
    "duplicates_removed": 4,
    "merge_groups": [
      {"kept_id": "wiz-1", "merged_id": "wiz-2", "key": {"file_path": "...", "line_number": 42, "cwe_id": "CWE-89"}}
    ]
  }
}
```

## Deduplication Rules

- **Composite key**: `(file_path, line_number, cwe_id)` — all three must be non-null and exact match.
- **Findings with null keys**: Cannot be deduped — always included in output.
- **Merge behavior**: Severity only goes UP (never downgraded). Longer description wins. Code snippet fills if missing. Higher confidence wins.
- **Ordering**: Preserves first-seen order.

## Output Format

Return a JSON object with two top-level keys:

```json
{
  "vulnerabilities": [
    {
      "id": "wiz-abc123",
      "cwe_id": "CWE-89",
      "title": "SQL Injection in user login query",
      "description": "The login function constructs SQL queries using string concatenation with unsanitized user input from the username field, allowing an attacker to inject arbitrary SQL.\n\n[Additional context from threat_model]: The threat model identifies this as exploitable via the public login API endpoint without authentication.",
      "severity": "critical",
      "source": "wiz",
      "file_path": "src/auth/login.py",
      "line_number": 42,
      "code_snippet": "query = f\"SELECT * FROM users WHERE username = '{username}'\"",
      "remediation_type": "code_fix",
      "tool_name": "wiz",
      "rule_id": "python-sql-injection-fstring",
      "confidence": 1.0,
      "merged_ids": ["tm-1"],
      "merged_sources": ["wiz", "threat_model"],
      "merged_tools": ["wiz", "claude_threat_model"],
      "merge_count": 2
    },
    {
      "id": "tm-2",
      "cwe_id": "CWE-326",
      "title": "Weak TLS configuration in load balancer",
      "description": "The load balancer is configured to accept TLS 1.0 and 1.1, which are deprecated.",
      "severity": "high",
      "source": "threat_model",
      "file_path": "infra/terraform/lb.tf",
      "line_number": 15,
      "code_snippet": null,
      "remediation_type": "infra_config",
      "tool_name": "claude_threat_model",
      "rule_id": null,
      "confidence": 0.8
    }
  ],
  "summary": {
    "input_count": 3,
    "output_count": 2,
    "duplicates_removed": 1,
    "merge_groups": [
      {
        "key": ["src/auth/login.py", 42, "CWE-89"],
        "merged_ids": ["tm-1", "wiz-abc123"],
        "kept_id": "wiz-abc123"
      }
    ]
  }
}
```

**Success indicator**: The output is valid JSON with both `vulnerabilities` (array) and `summary` (object) keys. The `output_count` equals the length of the `vulnerabilities` array. The `input_count` minus `duplicates_removed` equals `output_count`.

**Failure indicator**: Findings were dropped that were not true duplicates, or true duplicates remain in the output, or the severity downgraded during merge.

## Error Handling

On failure, returns `{"status": "error", "error": "message", "stage": "input_validation"}`.
