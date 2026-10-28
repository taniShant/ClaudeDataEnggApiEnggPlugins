---
description: Resume auto-chain from halt point after user provides corrections (overrides, mapping fixes, or domain knowledge)
disable-model-invocation: false
argument-hint: [--reparse] [--from <step>]
---

# /resume

Resume the auto-chain pipeline from the exact failure point after the user has provided corrections (intent overrides, mapping updates, or domain knowledge files).

## Usage

```
/resume                  # Resume from last halt point (default)
/resume --reparse        # Re-run /parse-mapping first, then resume
/resume --from <step>    # Resume from specific step number
```

## Arguments

- `--reparse` (optional) — Re-run `/parse-mapping` before resuming. Use when the mapping Excel was updated (e.g., added audit columns, transformation logic, or explicit PK statements).
- `--from <step>` (optional) — Resume from a specific step number (overrides auto-detected halt point). Valid range: 1–11 (Glue) or 1–9 (Databricks).

## Prerequisites

- Session must exist (`session/session_state.json` present and valid)
- Session must have been started with `--full-automation` (`auto_chain.enabled == true`)
- At least one step must have completed (`auto_chain.completed_steps` non-empty)

## Behaviour

### STEP 1 — Load Session State

1. Read `session/session_state.json`
2. Validate `auto_chain` object exists and `auto_chain.enabled == true`
3. If `auto_chain` is null or not present → ERROR:
   ```
   Cannot resume: session was not started in full-automation mode.
   Use --full-automation flag with /init to enable auto-chain.
   ```
4. Load `chain_checkpoints` (if present) for context recovery:
   - `post_parse`: tenancy, DP type, target_tables, optional columns, crypto status
   - `post_classification`: source table types, classification status, classification counts
   - `post_intent`: per-table intent summary (table_type, load_type, grain, PK)
   - `post_generation`: generated files, crypto applied, template versions
   
   These checkpoints provide reliable compact context (~500 tokens) that survives compaction. Use them as the source of truth for prior-phase decisions instead of relying on potentially compacted conversation history.

5. **Checkpoint-to-Command mapping** — when resuming, load the checkpoint from the PRIOR phase:

   | Resuming Command | Load Checkpoint | Provides |
   |---|---|---|
   | `/classify-sources` | `post_parse` | tenancy, target tables, crypto status |
   | `/identify-intent` | `post_parse` + `post_classification` | target tables + source table types |
   | `/gen-transform` | `post_intent` | table_type, load_type, grain, PK per table |
   | `/gen-wrapper` | `post_intent` | table_type, load_type, partition per table |
   | `/gen-mesh` | `post_intent` | table_type, partition, grain per table |
   | `/gen-dtxog` | `post_intent` | table_type, load_type per table |
   | `/gen-dag` | `post_intent` + `post_transform` | schedule, platform, per-table context, generated artefact paths |
   | `/gen-driver` | `post_intent` | table_type, load_type, PK per table |
   | `/gen-ddl` | `post_intent` | table_type, partition per table |
   | `/gen-tests` | `post_intent` | table_type, PK per table |
   | `/validate` | `post_generation` | generated files, crypto applied |
   | `/review` | `post_generation` | generated files list |
   | `/push` | `post_generation` | artefact count, generated files |

### STEP 2 — Determine Resume Point and Phase

**Phase-to-Step Mapping:**

| Steps (Glue) | Steps (Databricks) | Phase | Commands |
|---|---|---|---|
| 1–3 | 1–3 | Phase A: Discovery | parse-mapping, classify-sources, identify-intent |
| 4–6 | 4–5 | Phase B1: Core Generation | gen-mesh, gen-config, gen-transform (Glue) / gen-config, gen-transform (Databricks) |
| 7–9 | 6–9 | Phase B2: Assembly | gen-wrapper, gen-dtxog, gen-dag (Glue) / gen-driver, gen-ddl, gen-bundle, gen-dag (Databricks) |
| 10–12 | 10–11 | Phase C: Quality | gen-tests, review, validate |

**If `--from <step>` specified:**
- Use specified step as resume point
- Validate step number is within platform range (1–12 Glue, 1–11 Databricks)
- Validate step has not already completed (warn if re-running completed step)
- Map step to phase using table above

**If `--reparse` specified:**
- Set resume_from = step 1 (Phase A)
- This re-reads the mapping Excel (picks up user corrections to transformation logic, audit columns, etc.)
- After parse completes, chain continues from `/identify-intent` onwards (still within Phase A)

**Otherwise (default):**
1. Read `auto_chain.halted_at_step` and `auto_chain.halted_at_command`
2. Check if `session/intent_overrides.json` exists:
   - If YES → resume from `/identify-intent` step (applies overrides as Priority 0) — Phase A
   - If NO → resume from halted step (assumes user fixed the root cause externally)
3. Map halted step to phase using table above

**Resume dispatch logic:**
- If resume_from is in Phase A → dispatch Phase A agent with `resume_from_step=N`, then Phase B1 agent, then Phase B2 agent, then Phase C agent
- If resume_from is in Phase B1 → dispatch Phase B1 agent with `resume_from_step=N`, then Phase B2 agent, then Phase C agent
- If resume_from is in Phase B2 → dispatch Phase B2 agent with `resume_from_step=N`, then Phase C agent
- If resume_from is in Phase C → dispatch Phase C agent with `resume_from_step=N` only

### STEP 3 — Validate Correction Available

Before resuming, verify the user has provided a correction:

| Halt Reason | Expected Correction | Validation |
|-------------|-------------------|------------|
| G5-grain (intent ambiguity) | `session/intent_overrides.json` OR updated mapping OR domain knowledge | Check file exists and is valid JSON conforming to schema |
| G5-C crypto halt | Updated mapping (DE name added) | Check crypto_flags.json for `extraction_failed: false` |
| Blocking error | User fix depends on error type | Re-attempt the failed command |
| Validation REJECTED | Code fix applied | Re-run validation |

If intent_overrides.json exists:
1. Validate against `${CLAUDE_PLUGIN_ROOT}/schemas/intent_overrides.schema.json`
2. Validate each override entry matches a known target table in `session_state.target_tables[]`
3. If validation fails → ERROR with specific schema violation message

### STEP 4 — Re-install Automation Hooks

If automation hooks were removed (session interrupted):
1. Re-install `AskUserQuestion` deny hook in `.claude/settings.json`
2. Log: `[AUTO-CHAIN] Automation hooks re-installed for resume`

If hooks still present (session continued):
- Skip — no action needed

### STEP 5 — Execute Chain from Resume Point (Hybrid Phase-Agent Dispatch)

Re-enter the auto-chain using **hybrid phase-Agent() dispatch** (same pattern as `/init` Auto-Chain Pipeline):

1. Display progress banner:
   ```
   ═══════════════════════════════════════════════════════
    AUTO-CHAIN RESUMING from step {N}: {command_name}
   ═══════════════════════════════════════════════════════
    Previously completed: steps {completed_list}
    Intent overrides: {applied_count} table(s) / {field_count} field(s)
    Resume reason: {halt_reason → now resolved}
   ═══════════════════════════════════════════════════════
   ```

2. Dispatch phase agents starting from the phase containing the resume step:
   - Each phase agent receives `resume_from_step: N` in its prompt to skip already-completed commands WITHIN that phase
   - Phase agents read command markdown inline and delegate to leaf agents (NO Skill() calls)
   - Chain mode active — commands emit compact output only (STEP 0.0)
   - After each phase agent returns, verify session state from disk (same post-phase verification as `/init`)
   - Skip phases whose steps are ALL in `auto_chain.completed_steps`

   **Example — halted at step 7 (Glue, Phase B2 /gen-wrapper):**
   ```
   Phase A:  SKIPPED (steps 1-3 already completed)
   Phase B1: SKIPPED (steps 4-6 already completed)
   Phase B2: Agent dispatched with resume_from_step=7
     → Skips no steps (7 is the first B2 step for Glue)
     → Loads: post_intent + post_transform (boundary checkpoints)
     → Reads gen-wrapper.md, gen-dtxog.md, gen-dag.md inline; delegates to leaf agents
   Phase C:  Agent dispatched normally (full execution)
     → Reads gen-tests.md, review.md, validate.md inline; delegates to leaf agents
   ```

3. Apply intent overrides (if resuming at `/identify-intent`):
   - The Phase A agent prompt includes: "Load `session/intent_overrides.json` and pass to intent-identifier-agent as Priority 0 source"
   - Override fields are Priority 0 (highest — see agent spec)
   - Only unresolved fields are overridden; already-resolved fields untouched
   - Set `identification_source = "intent_override"` for overridden fields

4. After each phase agent returns:
   - Read `session/session_state.json` — verify `auto_chain.halted_at_step` is null
   - If halted → display halt banner → STOP (same halt display as `/init`)
   - If success → display phase-level progress → proceed to next phase

### STEP 6 — Post-Resume Completion

On successful completion of remaining chain:

```
═══════════════════════════════════════════════════════
 AUTO-CHAIN COMPLETE (resumed from step {N})
═══════════════════════════════════════════════════════
 Intent overrides applied: {M} table(s) ({K} fields)
 Platform:    {platform}
 Tables:      {T} target tables processed
 Artefacts:   {A} files generated
 Validation:  {verdict}
 Duration:    {X}m {Y}s (resume only)
═══════════════════════════════════════════════════════
```

Update session state:
- Clear `auto_chain.halted_at_step`, `halted_at_command`, `halt_reason`, `halted_at_timestamp`
- Set `intent_overrides_applied = true` (if overrides were used)
- Update `auto_chain.completed_steps` with all remaining steps

### STEP 7 — Re-halt (if new issue encountered)

If the resumed chain encounters a NEW halt condition:
- Apply same halt logic as original chain (display halt message, generate report)
- Update `auto_chain` with new halt state
- User can run `/resume` again after fixing the new issue

---

## Halt Conditions (Same as Auto-Chain)

| Condition | Action |
|-----------|--------|
| BLOCKING error from any command | Display error; halt |
| G5 halt (new grain ambiguity) | Generate updated resolution report; halt |
| G5-C crypto halt | Display crypto issue; halt |
| Validation REJECTED | Display red flag list; halt |
| Critical/High persists after retry | Display findings; halt |

---

## Session State Updates

On resume start:
```json
{
  "auto_chain": {
    "enabled": true,
    "chain_mode": true,
    "halted_at_step": null,
    "halted_at_command": null,
    "halt_reason": null,
    "halted_at_timestamp": null,
    "completed_steps": [1, 2, 3],
    "report_generated": "session/intent_resolution_report.md"
  }
}
```

On successful completion:
```json
{
  "auto_chain": {
    "enabled": true,
    "chain_mode": true,
    "halted_at_step": null,
    "halted_at_command": null,
    "halt_reason": null,
    "halted_at_timestamp": null,
    "completed_steps": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
    "report_generated": null
  },
  "intent_overrides_applied": true
}
```

---

## Audit Log Events

| Event | When |
|-------|------|
| `[AUTO-CHAIN] Resume initiated from step {N}` | Start of /resume |
| `[AUTO-CHAIN] Intent overrides loaded: {M} tables, {K} fields` | Overrides applied |
| `[AUTO-CHAIN] Automation hooks re-installed` | Hooks restored |
| `[AUTO-CHAIN] Resume complete: steps {N}-{M} executed` | Successful completion |
| `[AUTO-CHAIN] Re-halted at step {N}: {reason}` | New halt during resume |

---

## Error Cases

| Error | Message |
|-------|---------|
| No session state | `Cannot resume: no active session found. Run /init first.` |
| Not full-automation | `Cannot resume: session was not started in full-automation mode.` |
| No halt recorded | `Nothing to resume: auto-chain has not halted. All steps completed.` |
| Invalid --from step | `Invalid step number {N}. Valid range: Glue 1-12, Databricks 1-11.` |
| Invalid overrides JSON | `intent_overrides.json validation failed: {schema_error}. Fix and retry.` |
| Override table not found | `Override for {db}.{table} does not match any target table in this session.` |

---

## Examples

```bash
# Simple resume after providing intent overrides
/resume
# → Loads intent_overrides.json, resumes from /identify-intent

# Resume after updating mapping Excel with audit columns
/resume --reparse
# → Re-parses mapping (picks up new columns), then continues chain

# Resume from a specific step (e.g., skip ahead to validation)
/resume --from 11
# → Runs /validate only (useful after manual code fix)

# Resume after crypto halt (DE name added to mapping)
/resume --reparse
# → Re-parses mapping, re-runs crypto detection, continues
```
