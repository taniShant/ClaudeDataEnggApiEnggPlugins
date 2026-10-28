---
name: retry-strategy
description: "Retry Strategy — Define the retry logic that governs what happens when a CWE vulnerability fix attempt fails validation. This skill specifies when to retry, how to compose retry prompts that incorporate failure feedba"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/orchestration/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Retry Strategy
## Quick Start

This skill provides orchestration patterns for managing the multi-stage detox remediation pipeline.

```
# Loaded by detox-orchestrator-agent to coordinate phase gates, retry logic, and agent delegation.
```



## Purpose

Define the retry logic that governs what happens when a CWE vulnerability fix attempt fails validation. This skill specifies when to retry, how to compose retry prompts that incorporate failure feedback from the previous attempt, the maximum number of retries allowed, the backoff and prompt-escalation strategy between attempts, and the criteria for escalating a fix to manual review when automated remediation is exhausted.

## Inputs

- **fix_result** (FixResult, required): The `FixResult` object from the most recent fix attempt. Key fields:
  - `vulnerability_id` (string): Identifier of the vulnerability being fixed.
  - `cwe_id` (string): The CWE identifier (e.g., `CWE-89`).
  - `status` (string): Current status -- will be `"failed"` (fix invocation failed) or `"success"` with `validation_passed: false` (fix applied but Semgrep rescan found remaining issues).
  - `files_modified` (list[string]): Files changed by the previous attempt.
  - `retry_count` (int): Number of retries already attempted (starts at `0`).
  - `error_message` (string, optional): Error details from the failed attempt.
- **vulnerability** (Vulnerability, required): The full `Vulnerability` object for context. Key fields:
  - `cwe_id`, `title`, `description`, `severity`, `file_path`, `line_number`, `code_snippet`.
- **validation_result** (ScanResult, optional): The Semgrep rescan result, if the failure was a validation failure. Key fields:
  - `findings` (list[Vulnerability]): Remaining findings detected after the fix attempt.
  - `raw_output` (string): Raw Semgrep output for inclusion in the retry prompt.
- **original_prompt** (string, required): The prompt that was sent to Claude Code on the previous attempt. Used as the base for composing the retry prompt.
- **original_skill_content** (string, required): The CWE-specific skill markdown that was used as the system prompt. Retained across retries.
- **max_retries** (int, required, default from `config/default.yaml` `pipeline.max_retries`): Maximum number of retry attempts. Default is `2`.
- **working_dir** (Path, optional): The repository working directory for Claude Code invocations.

## Steps

### Step 1: Determine Whether to Retry

Evaluate the following conditions in order. If any condition is met, do NOT retry -- proceed directly to Step 6 (Escalate to Manual Review).

1. **Retry count exhausted**: `fix_result.retry_count >= max_retries`. The fix has already been retried the maximum number of times.
2. **Fundamental incompatibility**: The `error_message` contains indicators that retrying will not help:
   - `"unsupported language"` -- the CWE skill does not support the file's language.
   - `"file not found"` -- the target file no longer exists (perhaps removed by a prior fix).
   - `"permission denied"` -- filesystem permission issue that code cannot resolve.
   - `"budget exceeded"` -- the Claude Code invocation hit its spending cap. Retrying will hit the same cap.
3. **Severity below threshold**: If the vulnerability severity is `"low"` or `"info"`, do not spend retries. Escalate immediately.

If none of the above conditions are met, proceed to Step 2.

### Step 2: Revert the Failed Fix (if applicable)

If the previous attempt modified files but validation failed (i.e., `fix_result.status == "success"` and `fix_result.validation_passed == False`):

1. Use `git checkout -- {file}` for each file in `fix_result.files_modified` to revert to the state before the failed fix attempt.
2. If the fix had been committed, use `git revert --no-edit {commit_sha}` to cleanly undo the commit while preserving history.
3. Log the revert action.

If the previous attempt failed before modifying files (`fix_result.status == "failed"`), no revert is needed.

### Step 3: Classify the Failure Type

Determine the failure type to guide prompt composition:

- **Type A -- Invocation Failure**: `fix_result.status == "failed"`. Claude Code returned an error, timed out, or produced an empty response. The fix was never applied.
- **Type B -- Validation Failure**: `fix_result.status == "success"` and `fix_result.validation_passed == False`. Claude Code produced a fix, but Semgrep rescan found remaining vulnerabilities. The fix was insufficient or incorrect.
- **Type C -- Test Failure**: The fix passed Semgrep validation but the test suite failed, indicating a functional regression introduced by the fix.

### Step 4: Compose the Retry Prompt

Build a new prompt that includes structured feedback from the previous attempt. The prompt structure varies by failure type.

#### Type A -- Invocation Failure Retry Prompt

```
RETRY ATTEMPT {retry_count + 1} of {max_retries}

PREVIOUS ATTEMPT FAILED with error:
{fix_result.error_message}

Please try again with a different approach. The previous attempt encountered the
error shown above. Consider:
- If the error was a timeout, produce a more focused fix targeting only the
  vulnerable code path.
- If the error was an empty response, ensure you make concrete file edits.
- If the error was a parse failure, verify you are producing valid code.

ORIGINAL TASK:
{original_prompt}
```

#### Type B -- Validation Failure Retry Prompt

```
RETRY ATTEMPT {retry_count + 1} of {max_retries}

PREVIOUS FIX ATTEMPT DID NOT PASS VALIDATION.

The previous fix was applied to the following files:
{fix_result.files_modified}

However, Semgrep re-scanning detected the following remaining findings:

--- Semgrep Findings ---
{validation_result.raw_output}
--- End Semgrep Findings ---

Specific remaining issues:
{for each finding in validation_result.findings:}
  - {finding.title} at {finding.file_path}:{finding.line_number}
    CWE: {finding.cwe_id}
    Snippet: {finding.code_snippet}
{end for}

Your previous fix was insufficient. Please analyze the Semgrep findings above
and apply a corrected fix that addresses ALL remaining instances of {vulnerability.cwe_id}.

Common reasons a fix fails validation:
1. The fix addressed one instance but missed others in the same file.
2. The fix used a pattern that Semgrep still flags (e.g., string concatenation
   instead of parameterized queries).
3. The fix introduced new code paths that contain the same vulnerability pattern.

ORIGINAL TASK:
{original_prompt}
```

#### Type C -- Test Failure Retry Prompt

```
RETRY ATTEMPT {retry_count + 1} of {max_retries}

PREVIOUS FIX CAUSED TEST FAILURES.

The previous fix modified these files:
{fix_result.files_modified}

The fix passed Semgrep validation but caused the test suite to fail.

Please apply the security fix again, but this time ensure that:
1. Existing function signatures and return types are preserved.
2. Existing behavior for valid inputs is unchanged.
3. Only the vulnerable code path is modified.
4. If you change how a function processes input, update the corresponding
   test expectations ONLY if the test was explicitly testing the insecure behavior.

ORIGINAL TASK:
{original_prompt}
```

### Step 5: Execute the Retry

1. Increment `fix_result.retry_count` by 1.
2. Invoke Claude Code via `ClaudeCodeInvoker.invoke(original_skill_content, retry_prompt, working_dir)`.
3. If the invocation succeeds:
   a. Record the modified files on the `FixResult`.
   b. Create an atomic commit via `git_utils.commit_fix()` with message: `fix: Retry {retry_count} for {cwe_id} in {file_path}`.
   c. Run Semgrep rescan on the modified files.
   d. If validation passes, set `fix_result.status = "success"` and `fix_result.validation_passed = True`. Return the updated `FixResult`. Done.
   e. If validation fails again, return to Step 1 to evaluate whether another retry is warranted.
4. If the invocation fails:
   a. Update `fix_result.error_message` with the new error.
   b. Return to Step 1 to evaluate whether another retry is warranted.

### Step 6: Escalate to Manual Review

When retries are exhausted or a non-retryable condition is detected:

1. Set `fix_result.status = "needs_manual_review"`.
2. Set `fix_result.error_message` to a summary that includes:
   - The total number of attempts made (`retry_count + 1` including the original).
   - The failure type (A, B, or C) of the final attempt.
   - The specific error or remaining Semgrep findings from the last attempt.
3. If a partially applied fix exists on the branch, leave it in place but clearly flag it in the PR body. Do NOT silently include unvalidated fixes.
4. Log the escalation at `WARNING` level with full context.
5. Return the updated `FixResult`.

## Output Format

The retry strategy returns an updated `FixResult` object. The key fields after retry processing:

```json
{
  "vulnerability_id": "vuln-001",
  "cwe_id": "CWE-89",
  "status": "success | needs_manual_review",
  "files_modified": ["src/db/queries.py"],
  "commit_sha": "def5678",
  "validation_passed": true,
  "retry_count": 1,
  "error_message": null
}
```

When escalated to manual review:

```json
{
  "vulnerability_id": "vuln-001",
  "cwe_id": "CWE-89",
  "status": "needs_manual_review",
  "files_modified": ["src/db/queries.py"],
  "commit_sha": null,
  "validation_passed": false,
  "retry_count": 2,
  "error_message": "Exhausted 3 attempts (1 original + 2 retries). Final failure: Type B -- Semgrep found 1 remaining CWE-89 finding at src/db/queries.py:47."
}
```

**Success indicator**: `fix_result.status == "success"` and `fix_result.validation_passed == True` after a retry.

**Escalation indicator**: `fix_result.status == "needs_manual_review"`.

## Error Handling

| Failure Mode | Behavior |
|---|---|
| Retry invocation times out | Increment `retry_count`. Record timeout in `error_message`. Re-evaluate retry eligibility at Step 1. |
| Retry invocation returns empty response | Treat as Type A failure. Increment `retry_count`. Re-evaluate at Step 1. |
| Git revert fails (Step 2) | Log error at `ERROR` level. Attempt `git checkout -- {files}` as fallback. If that also fails, escalate immediately to manual review -- the repository may be in an inconsistent state. |
| Semgrep rescan itself errors (not a finding, but a tool crash) | Log the Semgrep error. Treat validation as inconclusive. Do NOT count this as a successful validation. Re-evaluate at Step 1 with the same retry count (do not increment -- the fix was not meaningfully tested). |
| Budget exceeded during retry | Do not retry further. Set `error_message` to include the budget cap. Escalate to manual review. |
| File modified by retry no longer exists | Escalate immediately. This indicates a structural problem that automated retries cannot resolve. |
| Conflict between retry fix and another fix already committed | Log the conflict. Escalate to manual review. Two CWE fixes may be interfering with each other and require human judgment to resolve. |

## Constraints

- **Maximum retries**: Never exceed `pipeline.max_retries` (default `2`) per vulnerability. This means at most 3 total attempts (1 original + 2 retries). This limit is absolute and cannot be overridden by the retry logic itself.
- **No infinite loops**: The retry count MUST be incremented on every retry attempt, regardless of outcome. The Step 1 check on `retry_count >= max_retries` guarantees termination.
- **Preserve original skill**: The CWE-specific skill markdown (system prompt) is NOT changed between retries. Only the user prompt is augmented with failure feedback. The skill contains the canonical fix pattern and must remain stable.
- **Atomic commits**: Each retry attempt that modifies files must produce its own commit. Do not amend previous commits. This preserves full audit history of what was tried.
- **No cascading retries**: Retrying one vulnerability's fix must not trigger re-validation of other vulnerabilities' fixes. Each vulnerability's retry loop is independent.
- **Budget awareness**: Each retry consumes budget. The per-invocation cap of `claude.max_budget_usd` applies to each retry invocation individually. The total cost for a single vulnerability can be up to `max_budget_usd * (max_retries + 1)`.
- **Timeout per retry**: Each retry invocation is subject to the same `claude.timeout_seconds` timeout as the original attempt. Retries do not get extended time.
- **No secrets in retry prompts**: Never include PAT values, API keys, or credentials in retry prompts. Semgrep raw output and code snippets are acceptable, but sanitize any environment variable values that might appear in error messages.
- **Severity-aware retry allocation**: Critical and high severity vulnerabilities get the full `max_retries` attempts. Low and info severity vulnerabilities are escalated immediately without retries (see Step 1, condition 3). Medium severity vulnerabilities get full retries.
- **Deterministic ordering**: Retries for a given vulnerability must complete (success or escalation) before the pipeline moves on to the next vulnerability. Do not interleave retries across different vulnerabilities.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
