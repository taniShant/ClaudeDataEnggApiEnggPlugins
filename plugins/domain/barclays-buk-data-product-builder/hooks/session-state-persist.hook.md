# Hook: session-state-persist

**Trigger**: After every gate resolution or generation step

**Purpose**: Write session state to disk atomically. Ensure no in-memory changes are lost between commands.

---

## Trigger Events

Persist is triggered after:
1. G1 answer processed (platform set)
2. G0.5 answer processed (domain knowledge loaded or skipped)
3. G1.5 answer processed (data product type set + 5 routing fields)
4. G3 answer processed (any S3 location value provided)
5. G4 answer processed (source classification completed)
6. G5 answer processed (any placeholder resolved)
7. G5-grain answer processed (intent fields resolved)
8. Any plugin command completes (artefact generated)
9. `/validate` completes (validation results updated)
10. Auto-chain halts (auto_chain halt state persisted)
11. `/resume` completes or re-halts (auto_chain state updated)

---

## Write Sequence

1. Read current `session/session_state.json` (or empty object if not yet created)
2. Merge updated fields into existing state
3. Write to `session/session_state.json` — atomic write (write to temp, then rename)
4. If write fails: log WARNING to `session/audit_log.jsonl` with error details; continue session (do not halt)

---

## Fields Persisted

All fields in `session/session_state.json`:
- `session_id`, `created_at`
- `platform`, `data_product_type`, `target_account`, routing fields
- `tenancy_name`, `mapping_excel_path`, `domain_knowledge_path`, `domain_knowledge_text`
- `gates_resolved[]`, `open_placeholders[]`
- `artefact_status{}`, `crypto_flags{}`
- `mesh_json_s3_locations{}`
- `auto_chain{}` (enabled, halted_at_step, halted_at_command, halt_reason, halted_at_timestamp, completed_steps[], report_generated)
- `intent_overrides_applied` (boolean)

---

## Failure Behaviour

If disk write fails or JSON corruption is detected:
- Log to audit: `{"event": "session_state_persist_error", "error": "...", "timestamp": "...", "trigger": "post_tool_use"}`
- Hook exits with code 1 — the PostToolUse hook caller is notified of the failure
- Corruption detection uses Python JSON validation (graceful skip if Python unavailable)
- On next persist attempt: retry the failed write

---

## Audit Entry Format

```json
{
  "timestamp": "2026-06-03T14:30:22Z",
  "event": "session_state_persisted",
  "trigger": "gate_resolved",
  "gate": "G1",
  "session_id": "de_20260603_143022"
}
```
