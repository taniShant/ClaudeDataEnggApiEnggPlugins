---
name: telemetry-contract
description: "Telemetry Contract — defines the event schema, emission patterns, and observability standards for all Detox agents and scripts. Aligned to BUK OTel-native log schema."
user-invocable: false
source: barclays-claude-code-plugins/plugins/tooling/barclays-buk-detox/skills/observability/telemetry-contract/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When observe-opal platform ships, or on OTel spec change
status: Full
---

# Telemetry Contract

## Purpose

Define the telemetry emission contract for all Detox pipeline stages. This skill teaches agents how to emit structured observability events that comply with the BUK OTel-native log schema (see `barclays-buk-standards:observability`).

## Inputs

- `job_id` — pipeline run identifier (8 hex chars from pipeline_state)
- `phase` — current pipeline phase number (1-9)
- `event_type` — the event being emitted (see Event Types below)
- `attributes` — key-value pairs specific to this event

## Event Types

| Event Type | When Emitted | Severity |
|---|---|---|
| `pipeline.started` | Orchestrator begins after preflight | INFO |
| `pipeline.completed` | Orchestrator finishes successfully | INFO |
| `pipeline.failed` | Orchestrator fails (any critical phase) | ERROR |
| `phase.started` | Any phase transitions to in_progress | INFO |
| `phase.completed` | Any phase transitions to completed | INFO |
| `phase.failed` | Any phase transitions to failed | ERROR |
| `phase.skipped` | Any phase transitions to skipped | INFO |
| `command.invoked` | Any /barclays-buk-detox:* command is parsed | INFO |
| `fix.applied` | A CWE fix succeeds | INFO |
| `fix.failed` | A CWE fix fails | WARN |
| `fix.retried` | A fix enters retry | WARN |
| `validation.pass` | Semgrep rescan passes for a file | INFO |
| `validation.fail` | Semgrep rescan fails for a file | WARN |
| `test.generated` | Security test file generated | INFO |
| `test.passed` | Generated test passes execution | INFO |
| `test.failed` | Generated test fails execution | WARN |
| `error.occurred` | Structured error from any script | ERROR |
| `selfcheck.result` | Agent self-check outcome at run end | INFO |

## Event Schema (OTel-Native)

Every event emitted by Detox is a single JSON line conforming to:

```json
{
  "Timestamp": "2026-08-27T14:30:00.123Z",
  "SeverityText": "INFO",
  "SeverityNumber": 9,
  "Body": "Human-readable event description",
  "TraceId": "<job_id zero-padded to 32 hex chars>",
  "SpanId": "<md5(job_id-phase-N)[:16]>",
  "Resource": {
    "service.name": "detox",
    "service.version": "<read from .claude-plugin/plugin.json>",
    "deployment.environment": "local|ci"
  },
  "Attributes": {
    "detox.event_type": "<from table above>",
    "detox.job_id": "<8 hex chars>",
    "detox.phase": <1-9>,
    "detox.user.name": "<resolved identity>",
    "detox.repo_name": "<target repository>",
    "detox.command": "<invoked command>",
    "detox.model": "<model used>",
    ...additional domain-specific attributes...
  }
}
```

## Steps to Emit Telemetry

1. **Construct the event** following the schema above
2. **Call the deterministic script**:
   > `{python}` = the verified Python 3 command (`python3`, `py -3` or `python`) from the calling agent's Python Interpreter rule. Detox never installs Python — if none is available, STOP.
   ```bash
   echo '{"action": "emit", "event": {"event_type": "...", "job_id": "...", ...}}' | {python} $PLUGIN_DIR/scripts/telemetry/telemetry.py
   ```
3. **Handle failure gracefully**: If telemetry emission fails, log to stderr and continue. NEVER block the pipeline.

## Trace/Span ID Generation

- **TraceId**: `job_id.ljust(32, '0')[:32]` — all events in one pipeline run share the same TraceId
- **SpanId**: `hashlib.md5(f"{job_id}-phase-{phase}".encode()).hexdigest()[:16]` — unique per phase

## Output Format

The telemetry script returns:
```json
{"status": "success", "event_id": "<12-char hex>", "log_path": "~/.detox/telemetry/events.jsonl"}
```

On failure:
```json
{"status": "error", "error": "<reason>", "event_id": "<12-char hex>"}
```

## Error Handling

- **Emission failure** (disk full, permissions): Log warning to stderr, continue pipeline execution
- **Invalid event data**: Log warning, skip emission, continue
- **File rotation** (>50MB): Automatically rotates to `events.{timestamp}.jsonl`

Telemetry emission uses the `emit_telemetry_event()` helper in `scripts/utils/common.py` which wraps all errors in try/except and never raises.

## Storage

- **Location**: `~/.detox/telemetry/events.jsonl` (granular events) and `runs.jsonl` (run summaries)
- **Format**: Append-only JSONL (one JSON object per line)
- **Locking**: `fcntl.LOCK_EX` for write safety
- **Rotation**: At 50MB, auto-renamed to `events.{timestamp}.jsonl`

## Privacy Rules

Per `barclays-buk-standards:observability` sensitive data rules, telemetry MUST NEVER contain:
- Personal Account Numbers (PAN)
- Sort codes
- National Insurance numbers
- Dates of birth
- Customer email addresses
- Full customer names

Only git config data (user.name, user.email) and CI metadata are captured — these are operational identity, not customer PII.

## Validation Criteria

- All required fields present in every emitted event
- TraceId is exactly 32 hex characters
- SpanId is exactly 16 hex characters
- SeverityNumber matches SeverityText mapping
- No sensitive data in any Attributes value
- Emission failure does not affect pipeline exit code

## Agent Self-Check

At the end of every pipeline run, verify:

- [ ] Telemetry emitted at pipeline start (`pipeline.started`)
- [ ] Telemetry emitted at each phase transition (automatic when phase status is set via `pipeline_state.py update`)
- [ ] Fix/test results recorded in `{repo}/.detox/state.json` via `pipeline_state.py append`
- [ ] Telemetry emitted at pipeline end (success or failure)
- [ ] Identity captured and stored on pipeline state
- [ ] No sensitive data in telemetry attributes
- [ ] Emission failures did not block pipeline execution
- [ ] Run summary recorded to `runs.jsonl` via `run_recorder.py` with `job_id` + `state_path` (no `state_incomplete` flag)
