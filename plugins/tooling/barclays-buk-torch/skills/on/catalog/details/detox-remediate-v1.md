# detox-remediate-v1

| Field | Value |
| --- | --- |
| Capability ID | `detox-remediate-v1` |
| Plugin name | `detox` |
| Component type | skill-user-only |
| Owner | Barclays BUK |
| Action scope | externally-consequential |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-detox@barclays-cio-buk |
| Native command | `/barclays-buk-detox:remediate` |
| Skill name | `remediate` |

## Description

Run the full CWE remediation pipeline — parse SAST/threat model reports, apply fixes, validate with Semgrep, create PR

## When to use

Use this capability when you have a Wiz SAST JSON report or a Markdown threat model containing CWE vulnerabilities and want to automatically apply fixes, validate them with Semgrep, and create a PR. Do not use it for general code review, linting, or security analysis without a Wiz report. Do not use it when the report is not in Wiz JSON or Markdown threat model format. Do not use it when you want only a scan result without code changes.

## Inputs

- `wiz_report_path` — absolute path to a Wiz SAST JSON report file (`.json`); at least one of `wiz_report_path` or `threat_model_path` must be provided
- `threat_model_path` — absolute path to a Markdown threat model report; at least one of `wiz_report_path` or `threat_model_path` must be provided
- `repo_url` — (optional) HTTPS URL of the target repository to clone; if omitted, the pipeline uses the current working directory as the target repo
- `dry_run` — (optional, default `false`) when `true`, simulates all stages without making commits or creating a PR; useful for previewing what would be fixed
- `config` — (optional) override map for pipeline settings: `pipeline.max_retries` (default 2), `pipeline.skip_validation` (default false), `pipeline.skip_tests` (default false), `claude.max_budget_usd` (default 1.00), `claude.timeout_seconds` (default 300)

## Preconditions

- `barclays-buk-detox` plugin installed via `/plugin install barclays-buk-detox@barclays-cio-buk`
- At least one of `wiz_report_path` or `threat_model_path` must point to an existing, readable file
- Target repository must be a git repo with a writable working tree; if `repo_url` is provided, `GIT_PAT` environment variable must be set for HTTPS clone authentication
- Semgrep must be available in `PATH` (used for post-fix validation rescans unless `pipeline.skip_validation: true`)
- `glab` CLI must be available in `PATH` and authenticated (used for PR creation in Stage 7)

## Expected outputs

- **Fixed source files** committed to a remediation branch (`remediate/cwe-{job_id}`) as atomic per-vulnerability commits
- **PR created** against the target repository with a summary table of vulnerabilities fixed, validation status per fix, and links to any corrective action documents
- **Corrective action documents** written to the `output/` directory for findings classified as `infra_config`, `manual`, or `hybrid` (where the code portion was fixed but non-code actions remain)
- **Jira ticket content** (optional) — `jira-ticket-generator` skill within the pipeline can produce a Jira ticket body for dependency and manual findings when integrated
- **Security test files** generated per remediated finding by the `security-test-generator` sub-skill and included in the remediation branch
- **RemediationJob JSON summary** printed on completion: job ID, final status, vulnerability count, success count, PR URL

## Exclusions

- Does not make architectural decisions — CWE-specific fix patterns are applied as minimal diffs; broader design choices remain with the engineer
- Does not handle report formats other than Wiz JSON and Markdown threat models; non-Wiz SAST formats (e.g., raw Semgrep JSON, Snyk reports) are not supported
- Does not fix vulnerabilities outside the supported CWE catalogue (see `skills/remediation-cwe/`); unsupported CWEs fall back to the generic handler or are flagged for manual review
- Does not merge the PR automatically; all created PRs require human review and approval
- Does not modify infrastructure, Terraform, Kubernetes, or external repository files directly; `infra_config` and `hybrid` findings are documented as corrective actions only
- Does not fix `DEPENDENCY` findings (CVE-based package upgrades); these are logged for separate ticket creation

## Verification

Confirm the pipeline completed by checking the printed summary for `status: completed` and a non-null `mr_url`. Open the created PR and verify the summary table lists at least one fix with `Validated: true`. If the Flags section shows `needs_manual_review` items, review the corrective action documents in the `output/` directory before merging. For `dry_run` runs, confirm `status: completed` and that no commits or PR were created.
