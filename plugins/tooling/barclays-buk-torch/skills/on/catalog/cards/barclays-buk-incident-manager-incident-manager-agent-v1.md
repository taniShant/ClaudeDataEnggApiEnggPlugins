# barclays-buk-incident-manager-incident-manager-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-incident-manager-incident-manager-agent-v1` |
| Plugin name | `barclays-buk-incident-manager` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | read-only |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-incident-manager@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `INCIDENT_DESCRIPTION` — free-text description of the incident or alert
- `LOG_PATH` — path to log files or a log extract; pass `"none"` if unavailable
- `SERVICE_NAME` — name of the affected service
- `TIMELINE_START` — start of the incident window in ISO 8601 format
- `TIMELINE_END` — end of the incident window in ISO 8601 format, or `"ongoing"`
- `OUTPUT_PATH` — absolute path where the RCA document will be written (e.g. `/path/to/rca.md`)

## Preconditions

- At least `INCIDENT_DESCRIPTION` and `SERVICE_NAME` must be provided; the agent can proceed without logs but will flag gaps
- `barclays-buk-incident-manager` plugin installed via `/plugin install barclays-buk-incident-manager@barclays-cio-buk`

## Expected outputs

- `rca.md` written to `OUTPUT_PATH` — structured RCA document containing: incident timeline, impact assessment (services, customers, data), root cause analysis (immediate cause, contributing factors, systemic root cause), security implications, prioritised remediation actions table (immediate / short-term / long-term), and lessons learned

## Exclusions

- Does not modify code, configuration, or infrastructure — read-only analysis only
- Does not implement remediation actions or trigger follow-on workflows
- Does not perform live service monitoring or real-time alerting
- Does not replace a formal security incident response process; security escalation decisions remain with the Security team

## Verification

Confirm the RCA completed by opening `OUTPUT_PATH/rca.md` and checking that the **Root Cause Analysis** and **Remediation Actions** sections are populated. A successful run will include at least one entry in the remediation table with a priority, action, owner, and target date. If the Flags section reports that `LOG_PATH` was `"none"`, manually confirm the timeline reconstruction assumptions are acceptable before acting on the remediation plan.
