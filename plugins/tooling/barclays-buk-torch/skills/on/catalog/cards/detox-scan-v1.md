# detox-scan-v1

| Field | Value |
| --- | --- |
| Capability ID | `detox-scan-v1` |
| Plugin name | `detox` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | read-only |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-detox@barclays-cio-buk |
| Native command | `/barclays-buk-detox:scan` |
| Skill name | `scan` |

## Description

Run a Semgrep SAST scan on a directory and display findings by CWE and severity

## When to use

Use this capability to run a SAST scan on the current codebase and get a structured vulnerability report grouped by CWE and severity. Typically the first step before running detox-remediate-v1. Do not use it when you already have a Wiz report and want to go straight to fixing; use detox-remediate-v1 directly in that case.

## Inputs

- `TARGET_DIR` — absolute path to the directory to scan; defaults to the current working directory if not specified
- `SEVERITY_FILTER` — (optional) minimum severity to report: `critical`, `high`, `medium`, `low`; if omitted, all severities are shown
- `OUTPUT_FORMAT` — (optional) one of `table` (default) or `json`; `json` output is suitable as input to `detox-remediate-v1`

## Preconditions

- `barclays-buk-detox` plugin installed via `/plugin install barclays-buk-detox@barclays-cio-buk`
- Semgrep must be available in `PATH`; install via `pip install semgrep` or `brew install semgrep`
- Target directory must be a readable path containing source code files

## Expected outputs

- Findings grouped by CWE and severity, with file path, line number, code snippet, and Semgrep rule ID for each finding
- A summary count table: total findings by severity (critical / high / medium / low / info)
- When `OUTPUT_FORMAT=json`: a JSON report conforming to the Wiz report schema understood by `detox-remediate-v1`, suitable for passing directly as `wiz_report_path` to the remediate pipeline

## Exclusions

- Does not modify any files — read-only scan only
- Does not apply fixes; to fix findings, pass the JSON output to `detox-remediate-v1`
- Does not scan infrastructure files (Terraform, Kubernetes YAML) for misconfigurations; scope is source code SAST only
- Semgrep rule coverage is bounded by the detox CWE catalogue; findings outside the catalogue are reported but will be flagged as `manual` if passed to the remediate pipeline

## Verification

Confirm the scan completed by checking the printed summary table for at least one severity row with a non-zero or zero count (an empty result with zero findings is a valid outcome for a clean codebase). If `OUTPUT_FORMAT=json` was used, confirm the output file is valid JSON and the top-level structure is an array of finding objects before passing it to `detox-remediate-v1`.
