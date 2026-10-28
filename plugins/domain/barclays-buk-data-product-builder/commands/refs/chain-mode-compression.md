---
description: "Output suppression rules when chain mode is active — verbose progress redirects to audit logs while conversation output compresses to single-line summaries with checkpoint confirmation."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Chain Mode Output Compression

> **Applies to:** All pipeline commands when `session_state.auto_chain.enabled == true` (full-automation mode).

## Rules

When chain mode is active:

1. **Suppress verbose output:** Do NOT print session_state.json content, per-table generation details, template contents, or intermediate processing to conversation.

2. **Audit log instead:** Write verbose progress entries to `session/audit_log.jsonl` (append-only structured logging).

3. **Compact return only:** At command completion, emit ONLY a single-line summary:
   ```
   [{step}/{total}] ✓ /{command-name} — {brief result summary}
   Checkpoint: {checkpoint_name} written
   ```

4. **Halt output:** If the command fails critically, emit max 5-line halt summary. Full details written to `session/audit_log.jsonl`.

## When Chain Mode is NOT Active

Output normally — show progress, intermediate results, and completion details to the user.
