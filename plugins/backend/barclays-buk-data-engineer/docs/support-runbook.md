# Support Runbook

## Owner

**BUK Data Engineering Practice**

Plugin repository: `barclays-buk-data-engineer`
CODEOWNERS: `@buk-data-engineering-practice`
Security-sensitive files (hooks, schemas): `@buk-data-engineering-practice @buk-security-review`

---

## Support Channel

Support channel: to be defined

For urgent issues affecting production data engineering workflows, escalate via the standard BUK Data Engineering on-call process.

---

## Common Issues and Resolutions

### BLOCKED_SAFETY Response — Destructive SQL

**Symptom:** An agent invocation returns `status: BLOCKED_SAFETY` with `detected_pattern` referencing a SQL operation such as `DROP TABLE`, `TRUNCATE`, or `DELETE_WITHOUT_WHERE`.

**Cause:** The `block-destructive-sql` hook detected a destructive SQL pattern in a Bash tool call.

**Resolution:**
1. Review the `full_statement` field in the blocking finding to confirm this is an intended operation.
2. If the operation is intentional and the environment is dev/test, re-invoke with explicit confirmation set in the session context.
3. If the operation targets staging or production, this cannot be unblocked via the agent. Use the `database-change-adviser` agent to produce a reviewed DDL draft, then execute the DDL manually after appropriate human review and approval.
4. If you believe the block was triggered incorrectly (false positive), raise a bug report (see below).

---

### BLOCKED_SAFETY Response — Secret Detected

**Symptom:** An agent invocation returns `status: BLOCKED_SAFETY` with `pattern_type` referencing a credential pattern such as `AWS_ACCESS_KEY` or `PASSWORD_IN_CONNECTION_STRING`.

**Cause:** The `block-secret-output` hook detected a secret pattern in a proposed file write.

**Resolution:**
1. Do not attempt to locate or reproduce the detected secret. The block is working as intended.
2. Review the generated artefact that triggered the block and replace any hardcoded credentials with:
   - A secret store reference: `{{ secret('name') }}`
   - An environment variable reference: `os.environ['VAR_NAME']`
   - A vault path reference: `vault://barclays/data-eng/credential-name`
3. Re-invoke the agent after correcting the artefact template.
4. If you believe a secret was inadvertently placed in your session context, rotate the credential immediately via the appropriate secrets management process.

---

### Missing Standards — PASS_WITH_WARNINGS or Status Downgrade

**Symptom:** An agent returns `status: PASS_WITH_WARNINGS` with warnings referencing `review_status: placeholder` or `review_status: missing` for one or more standards.

**Cause:** One or more standards referenced by the agent are not yet fully defined in `barclays-buk-standards`. The plugin contains placeholder or missing standard references that have not yet been validated against actual Barclays policy documents.

**Resolution:**
1. Review the `warnings[]` array for the specific `standard_id` values affected.
2. Check the current state of those standards in `barclays-buk-standards`.
3. If the standard is legitimately not yet defined, accept the `PASS_WITH_WARNINGS` status and record the gap in your delivery risk log.
4. To resolve the underlying gap, raise a request with the BUK Data Engineering Practice to complete the standard definition in `barclays-buk-standards`.

---

### Stale Context — Incorrect or Outdated Findings

**Symptom:** Agent output references schema definitions, standards, or configurations that do not reflect the current state of the system.

**Cause:** The agent's source data (MCP server responses, loaded standards) may be stale due to caching or the session having been open for an extended period.

**Resolution:**
1. Start a new session to ensure all source data is freshly retrieved.
2. Confirm that the relevant MCP servers are reachable and returning current data.
3. Check the `evidence_ledger[]` in the result manifest for any entries with `state: stale`. These indicate the specific sources that were out of date.
4. If stale data persists after a new session, check the MCP server cache configuration and TTL settings.

---

### Schema Validation Failures — Malformed Result Manifest

**Symptom:** The `validate-result-manifest` hook appends a warning with `code: MANIFEST_VALIDATION_FAILURE` to the result manifest.

**Cause:** An agent produced a result manifest that does not fully conform to `schemas/result-manifest.schema.json`, or a required field (`request_id`, `agent_version`, `task_type`, `status`, `timestamp`) is missing or malformed.

**Resolution:**
1. Review the `fields_affected` list in the warning to identify which fields are non-conformant.
2. If this is a one-off occurrence, re-invoke the agent.
3. If this occurs consistently for a specific agent, raise a bug report against that agent (see below).
4. If you need to consume the result programmatically despite the validation warning, treat the output as advisory only and do not rely on the non-conformant fields.

---

## Escalation Path

1. **First line:** Check this runbook and the `docs/known-limitations.md` file.
2. **Second line:** Raise a question in the BUK Data Engineering Practice support channel (to be defined).
3. **Third line:** Raise a GitHub issue in the `barclays-buk-data-engineer` repository.
4. **Security issues:** Contact `@buk-security-review` directly. Do not raise security issues as public GitHub issues.

---

## How to Report Bugs

Raise a GitHub issue in the `barclays-buk-data-engineer` repository with the following information:

- Plugin version (`agent_version` from the result manifest)
- Task type and agent invoked
- Reproduction steps (sanitised — remove any sensitive data, credentials, or PII)
- The result manifest output (sanitised)
- Expected behaviour vs actual behaviour
- Environment (dev/test/staging — do not include production-specific details)

Tag the issue with `bug` and assign to `@buk-data-engineering-practice`.

For false positives on safety hooks, tag additionally with `safety-hook` and `@buk-security-review`.
