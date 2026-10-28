---
name: rescan-validator
description: "Rescan Validator — Run Semgrep and compare before/after findings using the deterministic Python script."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Rescan Validator

## Purpose

Run Semgrep against a file that has been remediated to validate that the applied fix successfully eliminated the originally reported vulnerability. Executes Semgrep in JSON output mode, parses results, compares before-and-after finding counts for the specific CWE, and produces a structured pass/fail verdict.

## Implementation

This skill is implemented as a **deterministic Python script** at `scripts/validators/rescan_validate.py`. No LLM reasoning is required — the comparison logic is mechanical.

## Invocation

> `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.

```bash
echo '{
  "file_path": "/path/to/fixed_file.py",
  "cwe_id": "CWE-89",
  "baseline_findings": {
    "total_count": 3,
    "findings": [{"rule_id": "python-sqli", "line": 42, "message": "Raw SQL"}]
  },
  "semgrep_config": "auto",
  "repo_root": "/path/to/repo"
}' | {python} $PLUGIN_DIR/scripts/validators/rescan_validate.py
```

## Input Schema

| Field | Required | Type | Description |
|---|---|---|---|
| `file_path` | Yes | string | Absolute path to remediated file |
| `cwe_id` | Yes | string | CWE being validated (e.g., `CWE-89`) |
| `baseline_findings` | Yes | object | Pre-fix findings: `{total_count, findings[]}` |
| `semgrep_config` | No | string | Semgrep config (default: `auto`) |
| `repo_root` | No | string | Repository root for context |

## Output Schema

```json
{
  "status": "success",
  "verdict": "PASS",
  "cwe_id": "CWE-89",
  "file_path": "/path/to/file.py",
  "baseline": {"total_count": 3, "findings": [...]},
  "post_fix": {"total_count": 0, "findings": []},
  "comparison": {
    "resolved_count": 3,
    "persistent_count": 0,
    "shifted_count": 0,
    "new_count": 0
  }
}
```

## Verdicts

- **PASS**: All baseline findings resolved, no new findings introduced.
- **PARTIAL**: Some resolved but some persist, or new findings introduced.
- **FAIL**: No findings resolved, or more findings after fix than before.
- **ERROR**: Scan could not complete (semgrep failure, syntax errors).

## Error Handling

On failure, returns `{"status": "error", "error": "message", "stage": "input_validation|file_check|semgrep_check|semgrep_run|semgrep_parse"}`.

## Evidence & Accountability Framework

Semgrep rescan is one component of the broader Evidence & Accountability Framework. The full verification chain is:

| Priority | Method | Script | Confidence | Classification |
|----------|--------|--------|-----------|---------------|
| 1 | **WIZ CLI rescan** | `wiz_rescan.py` + `wiz_delta_comparator.py` | High | **VERIFIED** |
| 2 | **Semgrep rescan** | `rescan_validate.py` (this script) | Medium | **UNVERIFIED** |
| 3 | **Dependency tree** | `dependency_verifier.py` (CWE-937 only) | Low | **UNVERIFIED** |
| 4 | **None** | N/A | None | **UNVERIFIED** |

The `evidence_collector.py` script orchestrates this fallback chain. Each fix receives an evidence record, rendered into the Evidence & Verification section of `DETOX-REMEDIATION-REPORT.md`.

**WIZ CLI is the gold standard** — it's the bank's strategic security scanner. Semgrep validation (this script) is the secondary fallback when WIZ CLI is not installed or not authenticated.

## Constraints

- NEVER modifies the file being scanned (read-only).
- NEVER runs Semgrep with `--autofix`.
- Scans only the single specified file, not the entire repo.
- 120-second timeout on Semgrep execution.
- Line shift tolerance of 10 lines for finding matching.
- CWE matching is case-insensitive.
