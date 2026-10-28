# barclays-buk-accessibility-auditor-accessibility-auditor-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-accessibility-auditor-accessibility-auditor-agent-v1` |
| Plugin name | `barclays-buk-accessibility-auditor` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | read-only |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-accessibility-auditor@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `AUDIT_TARGET` — absolute path to the code or design files to audit
- `PLATFORM` — one of: `sdf`, `mca`, `ios`, `android`, `web`
- `OUTPUT_PATH` — absolute path where the audit report will be written (e.g. `/path/to/accessibility-audit.md`)

## Preconditions

- `AUDIT_TARGET` must contain UI source code or design files; the agent cannot audit an empty or non-UI path
- Platform must be determinable; platform-specific checks (touch target sizes, SDF/MCA component rules) are skipped if unknown
- `barclays-buk-accessibility-auditor` plugin installed via `/plugin install barclays-buk-accessibility-auditor@barclays-cio-buk`

## Expected outputs

- `accessibility-audit.md` written to `OUTPUT_PATH` — scored audit report with per-criterion pass/fail/manual/N-A status, overall verdict (APPROVED | CONDITIONAL | REJECTED), and per-finding remediation guidance

## Exclusions

- Does not modify any source files — read-only audit only
- Does not fix accessibility issues or generate remediation code
- Does not trigger downstream review or deployment workflows
- Does not perform dynamic browser testing; items marked `MANUAL` require human verification

## Verification

Confirm the audit completed by opening `OUTPUT_PATH/accessibility-audit.md` and checking that an **Overall verdict** line is present (APPROVED, CONDITIONAL, or REJECTED), the summary table shows counts for Pass/Fail/Manual, and any failures list specific criterion, file, and remediation guidance. If the file is absent or the verdict line is missing, the agent did not complete successfully.
