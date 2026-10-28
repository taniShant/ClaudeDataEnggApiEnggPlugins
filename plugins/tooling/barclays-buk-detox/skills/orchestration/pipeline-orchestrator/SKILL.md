---
name: pipeline-orchestrator
description: "Pipeline Orchestrator — Orchestrate the full CWE remediation pipeline from repository setup through merge request creation. This skill defines the end-to-end flow that sequences seven discrete stages (`setup_repo`, `parse_rep"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/orchestration/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Pipeline Orchestrator
## Quick Start

This skill provides orchestration patterns for managing the multi-stage detox remediation pipeline.

```
# Loaded by detox-orchestrator-agent to coordinate phase gates, retry logic, and agent delegation.
```



## Purpose

Orchestrate the full CWE remediation pipeline from repository setup through merge request creation. This skill defines the end-to-end flow that sequences seven discrete stages (`setup_repo`, `parse_reports`, `classify`, `apply_fixes`, `validate`, `document_infra`, `create_mr`), manages state transitions via the `RemediationJob` model, enforces severity and remediation-type policies, and coordinates error recovery so that a failure in one stage produces a well-defined outcome rather than an undefined crash.

## Inputs

- **repo_url** (string, optional): HTTPS URL of the target repository to clone and remediate. If omitted, the pipeline assumes the working directory is already the target repo.
- **threat_model_path** (string, optional): Absolute path to a Markdown threat model report. At least one of `threat_model_path` or `wiz_report_path` must be provided.
- **wiz_report_path** (string, optional): Absolute path to a WIZ JSON report. At least one of `wiz_report_path` or `threat_model_path` must be provided.
- **dry_run** (boolean, optional, default `false`): When `true`, the pipeline simulates all stages without cloning, invoking Claude Code, or creating commits/MRs.
- **config** (dict, optional): Override values from `config/default.yaml`. Key sub-keys:
  - `pipeline.max_retries` (int, default `2`): Maximum retry attempts per vulnerability fix.
  - `pipeline.skip_validation` (bool, default `false`): Skip the Semgrep rescan stage.
  - `pipeline.skip_tests` (bool, default `false`): Skip the test-suite run during validation.
  - `claude.model` (string, default `"sonnet"`): Model identifier for Claude Code invocations.
  - `claude.max_budget_usd` (float, default `1.00`): Per-invocation budget cap.
  - `claude.timeout_seconds` (int, default `300`): Timeout per Claude Code invocation.

## Steps

### Stage 1: Repository Setup (`setup_repo`)

1. Transition job status to `CLONING`.
2. If `dry_run` is `true`, log the skip and return immediately.
3. If `repo_url` is provided:
   a. Create a temporary directory via `file_utils.create_temp_dir()`.
   b. Clone the repository using `git_utils.clone_repo(repo_url, repo_dir)`. Authentication uses the HTTPS PAT found in the `GIT_PAT` environment variable.
   c. Record `repo_dir` on the `RemediationJob`.
   d. Create a remediation branch named `remediate/cwe-{job_id}` via `git_utils.create_branch()`.
   e. Record `branch_name` on the `RemediationJob`.
4. If `repo_url` is not provided, log that clone was skipped. The caller is responsible for ensuring the current working directory is the target repo.

**Decision point**: If the clone fails (network error, invalid PAT, nonexistent repo), raise an exception immediately. There is no recovery path -- the entire pipeline fails with status `FAILED`, and the error is recorded on the job.

### Stage 2: Parse Reports (`parse_reports`)

1. Transition job status to `PARSING`.
2. If `threat_model_path` is provided, call `parse_threat_model(Path(threat_model_path))` to produce a list of `Vulnerability` objects. Log the count.
3. If `wiz_report_path` is provided, call `parse_wiz_report(Path(wiz_report_path))` to produce a list of `Vulnerability` objects. Log the count.
4. Merge and deduplicate both lists via `normalize_and_deduplicate(tm_findings, wiz_findings)`. Store the result on `job.vulnerabilities`.
5. Log the total normalized count.

**Decision point**: If both paths are `None`, or if both parsers return zero findings, the pipeline should still proceed (it will simply produce a PR with no fixes). Log a warning but do not treat this as an error.

### Stage 3: Classify Findings (`classify`)

1. Transition job status to `CLASSIFYING`.
2. Partition `job.vulnerabilities` by `remediation_type`:
   - `CODE_FIX` -- vulnerabilities that will be auto-fixed by Claude Code.
   - `HYBRID` -- vulnerabilities that require BOTH a code fix in this repository AND additional changes outside the code (infrastructure changes, external repository changes, or both). The code fix portion proceeds to Stage 4; the remaining non-code actions are documented as a corrective action in Stage 6. Store on `job.hybrid_findings`.
   - `INFRA_CONFIG` -- findings requiring infrastructure or configuration changes. Store these separately on `job.infra_findings` for Stage 6.
   - `DEPENDENCY` -- findings requiring dependency upgrades. These are logged for ticket creation but not auto-fixed.
   - `MANUAL` -- findings that cannot be auto-fixed. Store these on `job.manual_findings` for Stage 6 corrective action generation.
3. Apply severity policy from `config/severity_policy.yaml`:
   - Only `CODE_FIX` and `HYBRID` vulnerabilities whose severity is in the `auto_fix: true` set proceed to Stage 4 (for the code fix portion).
   - Vulnerabilities below the `minimum_confidence` threshold (default `0.5`) are reclassified as `MANUAL`.
4. Log the counts per category.

**Decision point**: If zero `CODE_FIX` and zero `HYBRID` vulnerabilities remain after filtering, skip Stage 4 but continue through Stages 5-7 so that infra documentation and PR creation still happen.

**Hybrid classification criteria** — classify a finding as `HYBRID` when:
- The threat model or WIZ report explicitly references both in-repo code AND infrastructure/external changes for the same attack path.
- A CWE remediation requires a code change (e.g., replacing a hardcoded credential with an env var reference) AND a non-code change (e.g., provisioning the secret in a vault, rotating the credential, or updating an external config repo).
- The fix spans this repository AND an external repository (e.g., update the client code here AND update a shared library or config repo elsewhere).

For `HYBRID` findings, the `Vulnerability` object carries:
- `code_fix_description` (string): What code change to make in this repo.
- `infra_actions` (array of strings, optional): Infrastructure changes required (e.g., "Provision DSS_ADMIN_TOKEN in HashiCorp Vault for all environments").
- `external_repo_actions` (array of objects, optional): Changes required in external repositories. Each object contains `repo_name` (string), `description` (string), and `file_path` (string, optional).

### Stage 4: Apply Fixes (`apply_fixes`)

1. Transition job status to `FIXING`.
2. If `dry_run` is `true`, create a `FixResult` with status `"skipped"` for each vulnerability and return.
3. For each `CODE_FIX` and `HYBRID` vulnerability, in order of descending severity:
   a. Use `FixRouter.get_skill_for_vulnerability(vuln)` to load the CWE-specific skill markdown content.
   b. Use `FixRouter.build_fix_prompt(vuln)` to compose the user prompt containing file path, line number, code snippet, and CWE context. For `HYBRID` findings, the prompt focuses on the `code_fix_description` — only the in-repo code change is applied here.
   c. Invoke Claude Code via `ClaudeCodeInvoker.invoke(skill_content, prompt, working_dir)`.
   d. Parse the Claude Code response to determine which files were modified.
   e. Create an atomic commit for this single fix via `git_utils.commit_fix()`.
   f. Record a `FixResult` on the job with status `"success"`, `files_modified`, and `commit_sha`. For `HYBRID` findings, also set `is_hybrid = true` and `pending_non_code_actions = true` to indicate that additional non-code work remains.
4. If any individual fix invocation fails (timeout, error response, empty response), record a `FixResult` with status `"failed"` and `error_message`. Do NOT abort the entire pipeline -- continue to the next vulnerability.

**Decision point -- retry integration**: After recording a `"failed"` result in step 4, check whether `result.retry_count < max_retries`. If retries remain, delegate to the **retry_strategy** skill (see `skills/orchestration/retry_strategy.md`). The retry strategy composes a new prompt that includes the failure feedback and resubmits. Update the `FixResult` accordingly. See the Retry Strategy skill for full details.

### Stage 5: Validate Fixes (`validate`)

1. Transition job status to `VALIDATING`.
2. If `dry_run` is `true` or `pipeline.skip_validation` is `true`, skip this stage.
3. For each `FixResult` with status `"success"`:
   a. Run `wiz_rescanner.rescan_file(file_path, cwe_id)` against every file in `files_modified`.
   b. If the scan returns `passed: false`, set `result.validation_passed = False`.
   c. If the scan returns `passed: true`, set `result.validation_passed = True`.
4. If validation fails for a fix:
   a. Check whether `result.retry_count < max_retries`.
   b. If retries remain, delegate to the **retry_strategy** skill. The retry prompt includes the Semgrep findings from the failed validation so Claude Code can see exactly what is still wrong.
   c. If no retries remain, set `result.status = "needs_manual_review"`. The fix commit remains in the branch but is flagged in the PR body.
5. If `pipeline.skip_tests` is `false` and `repo_dir` is set, run the full test suite via `test_runner.run_tests(repo_dir)`.
   a. If tests fail, log a warning. Do NOT revert commits -- the PR reviewers will see the test failure.

**Decision point**: Validation failures do not abort the pipeline. Each failing fix is individually flagged while successful fixes proceed to the PR.

### Stage 6: Document Infrastructure, Manual, and Hybrid Findings (`document_infra`)

1. Transition job status to `DOCUMENTING`.
2. If `job.infra_findings` is empty AND `job.manual_findings` is empty AND `job.hybrid_findings` is empty, log the skip and return.
3. For each `INFRA_CONFIG` vulnerability in `job.infra_findings` and each `MANUAL` vulnerability in `job.manual_findings`:
   a. Load the documentation skill from `skills/documentation/`.
   b. Generate a corrective action document describing the finding, recommended remediation steps, and the responsible team.
   c. Write the document to the `output/` directory.
4. For each `HYBRID` vulnerability in `job.hybrid_findings`:
   a. Load the documentation skill from `skills/documentation/`.
   b. Generate a corrective action document with `remediation_type: "hybrid"` that documents:
      - The code fix that WAS applied in this repo (reference the commit SHA from Stage 4's `FixResult`).
      - The infrastructure changes still required (from `infra_actions`).
      - The external repository changes still required (from `external_repo_actions`, including repo name, description, and file path).
   c. Write the document to the `output/` directory.
5. Attach document paths to the job for inclusion in the PR body.

### Stage 7: Create Merge Request (`create_mr`)

1. Transition job status to `CREATING_MR`.
2. If `dry_run` is `true`, or `repo_dir` is `None`, skip this stage.
3. Check that at least one `FixResult` has status `"success"`. If none, skip MR creation and log a message.
4. Build the MR title: `fix: Remediate {N} CWE vulnerabilities`.
5. Build the MR body:
   a. A summary table with columns: Vulnerability ID, CWE, Status, Validated.
   b. A section listing any `needs_manual_review` items with details.
   c. A section listing infra/config corrective action documents if any were generated.
   d. A section noting any `DEPENDENCY` or `MANUAL` items that were not auto-fixed.
6. Push the branch and create the MR via `glab mr create` (using `scripts/git/pr_creator.py`).
7. Record `job.mr_url`.

### Pipeline Completion

1. If all stages completed without raising an exception, transition job status to `COMPLETED`.
2. If any stage raised an unhandled exception, transition job status to `FAILED` and record the error.
3. Print a summary: job ID, final status, vulnerability count, fix count, success count, PR URL.

## Output Format

The pipeline produces a `RemediationJob` object (Pydantic model) containing all state. The key fields are:

```json
{
  "job_id": "a1b2c3d4e5f6",
  "status": "completed",
  "repo_url": "https://app.gitlab.barcapint.com/org/repo.git",
  "repo_dir": "/tmp/cwe-remediation/a1b2c3d4e5f6",
  "branch_name": "remediate/cwe-a1b2c3d4e5f6",
  "vulnerabilities": [
    {
      "id": "vuln-001",
      "cwe_id": "CWE-89",
      "title": "SQL Injection in user search",
      "severity": "critical",
      "remediation_type": "code_fix",
      "file_path": "src/db/queries.py",
      "line_number": 42
    },
    {
      "id": "vuln-002",
      "cwe_id": "CWE-798",
      "title": "Hardcoded credentials in config",
      "severity": "critical",
      "remediation_type": "hybrid",
      "file_path": "src/config/settings.py",
      "line_number": 15,
      "code_fix_description": "Replace hardcoded credential with environment variable reference",
      "infra_actions": ["Provision DB_PASSWORD in HashiCorp Vault for all environments"],
      "external_repo_actions": [
        {
          "repo_name": "org/deployment-config",
          "description": "Add DB_PASSWORD environment variable injection to Kubernetes deployment manifest",
          "file_path": "k8s/overlays/production/deployment.yaml"
        }
      ]
    }
  ],
  "fix_results": [
    {
      "vulnerability_id": "vuln-001",
      "cwe_id": "CWE-89",
      "status": "success",
      "files_modified": ["src/db/queries.py"],
      "commit_sha": "abc1234",
      "validation_passed": true,
      "retry_count": 0,
      "is_hybrid": false
    },
    {
      "vulnerability_id": "vuln-002",
      "cwe_id": "CWE-798",
      "status": "success",
      "files_modified": ["src/config/settings.py"],
      "commit_sha": "def5678",
      "validation_passed": true,
      "retry_count": 0,
      "is_hybrid": true,
      "pending_non_code_actions": true
    }
  ],
  "infra_findings": [],
  "hybrid_findings": [
    {
      "id": "vuln-002",
      "cwe_id": "CWE-798",
      "title": "Hardcoded credentials in config",
      "severity": "critical",
      "code_fix_applied": true,
      "code_fix_commit_sha": "def5678",
      "infra_actions": ["Provision DB_PASSWORD in HashiCorp Vault for all environments"],
      "external_repo_actions": [
        {
          "repo_name": "org/deployment-config",
          "description": "Add DB_PASSWORD environment variable injection to Kubernetes deployment manifest",
          "file_path": "k8s/overlays/production/deployment.yaml"
        }
      ]
    }
  ],
  "manual_findings": [],
  "mr_url": "https://app.gitlab.barcapint.com/org/repo/-/merge_requests/42",
  "created_at": "2026-04-29T12:00:00Z",
  "updated_at": "2026-04-29T12:05:00Z",
  "dry_run": false
}
```

**Success indicator**: `job.status == "completed"` and `job.mr_url` is non-null.

**Partial success indicator**: `job.status == "completed"` but some `fix_results` have `status == "needs_manual_review"`.

**Failure indicator**: `job.status == "failed"`.

## Error Handling

| Failure Mode | Stage | Behavior |
|---|---|---|
| Clone fails (network, auth, nonexistent repo) | Stage 1 | Pipeline aborts. Job status set to `FAILED`. |
| Report file not found or unparseable | Stage 2 | Log error and raise. Pipeline aborts. |
| Zero findings after parsing | Stage 2 | Log warning. Pipeline continues (produces empty PR or skips PR). |
| Single fix invocation fails | Stage 4 | Record `FixResult` with `status="failed"`. Attempt retry per retry_strategy. Continue to next vulnerability. |
| Single fix invocation times out | Stage 4 | Same as above. The timeout is configured via `claude.timeout_seconds`. |
| Semgrep rescan finds remaining findings | Stage 5 | Set `validation_passed=False`. Attempt retry per retry_strategy. If max retries exhausted, set `status="needs_manual_review"`. |
| Test suite fails | Stage 5 | Log warning. Do not revert commits. PR reviewers will see the test failure. |
| Corrective action doc generation fails | Stage 6 | Log error. Continue to Stage 7. |
| MR creation fails (glab CLI error, permissions) | Stage 7 | Log error. Job status set to `FAILED`. The branch still exists with commits for manual recovery. |
| Unhandled exception at any stage | Any | Caught by top-level try/except. Job status set to `FAILED`. Summary is still printed. |

**Recovery principle**: The pipeline is designed to be re-runnable. If it fails partway through, the user can fix the issue (e.g., provide a valid PAT) and rerun. Atomic commits mean partial progress is preserved on the branch.

## Constraints

- **Do not** modify the target repository's existing commits. All changes are made on the remediation branch.
- **Do not** force-push or rewrite history on any branch.
- **Do not** merge the PR automatically. The pipeline creates the PR for human review.
- **Do not** auto-fix vulnerabilities with severity set to `auto_fix: false` in `config/severity_policy.yaml`.
- **Do not** auto-fix vulnerabilities with `confidence < minimum_confidence` (default `0.5`).
- **Do not** process more than one repository per pipeline run. Each invocation handles a single repo.
- **Budget limit**: Each Claude Code invocation is capped at `claude.max_budget_usd` (default `$1.00`). If a single fix exceeds this, the invocation fails and is retried or escalated.
- **Timeout**: Each Claude Code invocation is capped at `claude.timeout_seconds` (default `300`). Exceeded invocations are treated as failures.
- **Retry limit**: No more than `pipeline.max_retries` (default `2`) retry attempts per vulnerability. After exhausting retries, the fix is escalated to manual review.
- **Atomic commits**: Each vulnerability fix must be a separate commit. Do not batch multiple fixes into a single commit.
- **No secrets in output**: Never include PAT values, API keys, or credentials in logs, PR bodies, or corrective action documents.
- **Ordering**: Process vulnerabilities in descending severity order (critical first, then high, medium, low) so that the most important fixes are attempted even if the pipeline is interrupted.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
