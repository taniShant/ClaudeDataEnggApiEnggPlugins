---
description: "Session recovery mechanisms for failed /init attempts — Partial Init Recovery (preferred, detects incomplete session state and resumes via warm-start fast-path) and Git Log Fallback for corrupted or missing session files."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Session Recovery

## Partial Init Recovery (Preferred — Before Git Fallback)

If `session/session_state.json` exists but is incomplete (e.g., `session_id` present but `platform` is null):

1. This indicates a previous `/init` attempt failed mid-execution.
2. The file IS the recovery source — no git log needed.
3. Re-running `/init` with the **same mapping path** triggers the **Warm Start Fast-Path** (see `init.md` Step 0.5): completed steps are detected and skipped, resuming from the first incomplete step.
4. Re-running `/init` with a **different mapping path** triggers fresh init with stale session warning (`init.md` Step 4).

This is the most common recovery scenario — especially on `haiku-default` models where the first `/init` may fail partway through the multi-step chain.

---

## Git Log Fallback (A2 Feature)

**When session state file is completely missing or corrupted beyond JSON parsing:**

If `.de_plugin/sessions/{session_id}/session_state.json` is missing or unreadable:

1. **Attempt recovery** from git commit log:
   ```bash
   git log --grep="session_id:" --oneline | head -20
   ```

2. **Extract phase status** from recent commits:
   ```bash
   git log --format="%B" | grep -A 5 "phase.*status"
   # Find most recent entry for this session
   ```

3. **Reconstruct minimal session state** (best-effort):
   - Extract `session_id`, `mapping_excel_path`, `platform`, `gates_resolved` from commit messages
   - Initialize `phases` block with `status = pending` for unknown phases
   - Set `created_at` from git commit date
   - Mark recovery as non-authoritative: add metadata `recovered_from_git: true`

4. **Prompt user:**
   > "Session state file missing. Recovered from git log (best-effort). Continue with recovered state? [Y/N]"
   - **Y** → Resume with recovered state; user confirms gates and intent
   - **N** → Start new session (will re-ask all gates)

5. **Log recovery event:**
   - Write audit entry: `[RECOVERY] Session recovered from git log; user confirmed state`
   - Save recovered session state as new file

**Limits:**
- Fallback is best-effort only; not a full state recovery
- Only committed phase information is recoverable (in-progress phases may be lost)
- User confirmation required before resuming
