---
description: "Hook lifecycle and auto-chain pipeline triggered by the --full-automation flag — covers hook installation into settings.json, user-defined hook preservation, and automatic decision-making by auto-decision-agent."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-09-28
---

# Full-Automation: Hook Lifecycle & Auto-Chain Pipeline

## Hook Lifecycle (A4 Feature)

When `--full-automation` flag is set during `/init`:

### Hook Installation (on entry)

1. **Load current `.claude/settings.json`:**
   ```bash
   settings_backup=$(cat .claude/settings.json)
   ```

2. **Detect and parse hooks:**
   - Check for existing `hooks.PreToolUse` entries
   - Preserve any user-defined hooks (non-automation hooks)

3. **Install automation hook:**
   ```json
   {
     "matcher": "AskUserQuestion",
     "condition": "full_automation_enabled",
     "action": "allow",
     "reasoning": "Full-automation mode: auto-decision-agent resolves when possible; asks user when evidence insufficient"
   }
   ```

4. **Merge with existing hooks** (never overwrite):
   - Append automation hook to existing `hooks.PreToolUse` array
   - Save merged settings to `.claude/settings.json`

5. **Store original settings** for rollback:
   ```bash
   session_state.automation_hooks = {
     "installed_at": "2026-06-09T10:30:00Z",
     "original_settings": {{settings_backup}},
     "automation_enabled": true
   }
   ```

### Hook Removal (on exit)

When session ends or `/init` called again without `--full-automation`:

1. **Restore original `.claude/settings.json`:**
   ```bash
   if session_state.automation_hooks.original_settings exists:
     write session_state.automation_hooks.original_settings to .claude/settings.json
   ```

2. **Log cleanup:**
   - Write audit entry: `[CLEANUP] Automation hooks removed; settings restored`

3. **Trap handler for graceful exit:**
   ```bash
   trap restore_automation_hooks EXIT
   ```
   - Ensures hooks removed even if session interrupted
   - Restores default settings state

### Hook Prerequisites

Before full-automation can function correctly:

1. **Hooks MUST be loadable:** Either:
   - Pre-configured in repo-level `.claude/settings.json`, OR
   - Defined in plugin's `hooks/hooks.json` (loaded by Claude plugin system), OR
   - Installed dynamically during `/init` hook lifecycle (above)
2. **Session directory MUST exist and be writable:**
   - Verify `session/` directory exists; create if not
   - Verify write permissions by attempting a test write
3. **Stale session detection:**
   - If `session/session_state.json` already exists from a previous run, warn:
     ```
     ⚠️ Existing session found (${existing_session_id}). This will be OVERWRITTEN by the new session.
     ```
   - Log: `{"event": "stale_session_overwritten", "old_session_id": "${existing_session_id}"}`

### Error Handling

**If hook installation fails:**
- Log error: `"Hook installation failed: {{error}}"`
- Continue session WITHOUT full-automation
- Mark in audit log: `[WARNING] Full-automation requested but hooks installation failed`

**If hook removal fails:**
- Log error: `"Hook removal failed: {{error}}"`
- Manual cleanup required: user must restore `.claude/settings.json`

---

## Auto-Chain Pipeline (Full-Automation Mode ONLY)

> **GUARD:** This entire section applies ONLY when `--full-automation` flag is set. In interactive mode (default), the user invokes each slash command individually at their own pace. Do NOT auto-chain commands in interactive mode.

When `--full-automation` is enabled, after all `/init` steps complete successfully, automatically invoke the remaining pipeline using **hybrid phase-Agent() dispatch**. The user does NOT need to invoke each command individually.

### Phase Dispatch Responsibility

**CRITICAL:** After `/init` Steps 1-9 complete successfully, the main conversation MUST immediately dispatch Phase A (Discovery) agent. This is NOT automatic — if the main conversation does not dispatch Phase A, the auto-chain pipeline will NOT execute.

**Dispatch sequence:**
1. `/init` completes → writes session state with `auto_chain.enabled = true`
2. Main conversation reads this file (`init-full-automation.md`)
3. Main conversation dispatches Phase A agent using the prompt contract below
4. After Phase A returns → main conversation verifies checkpoint → dispatches Phase B1
5. After Phase B1 returns → main conversation verifies checkpoint → dispatches Phase B2
6. After Phase B2 returns → main conversation verifies checkpoint → dispatches Phase C

**If `/init` fails:** Session state is NOT created (or is incomplete). The user MUST fix the issue and re-run `/init`. Do NOT attempt to dispatch Phase A with missing or partial session state.

### Hybrid Phase-Agent Execution (Context-Isolated, No Deep Nesting)

The chain is split into **4 isolated phases** (A, B1, B2, C), each running as a foreground Agent() call with fresh context. Each phase agent executes its commands **inline** by reading command markdown files directly — it does NOT use Skill() to invoke commands (which would create a 3rd nesting level). Phase B (Generation) is split into B1 (Core Generation) and B2 (Assembly) at the `post_transform` checkpoint boundary to prevent context exhaustion on complex multi-table pipelines.

**Why hybrid dispatch:**
- **Context isolation**: Each phase gets a fresh ~200K context budget. Running all 11 commands in one conversation degrades quality by step 7-8.
- **No deep nesting**: Phase agents call leaf agents (e.g., mapping-parser-agent) directly via Agent() — maximum depth is 2. Using Skill() inside Agent() would create depth 3, which causes API dispatch errors.
- **Leaf agents still isolated**: Heavy generation work (transforms, mesh JSON, etc.) runs in leaf Agent() calls with their own context.

**Dispatch model:**
```
Main Conversation (thin coordinator):
├─ Agent("Phase A: Discovery")       ← fresh context
│    reads: parse-mapping.md, classify-sources.md, identify-intent.md (inline)
│    delegates to: mapping-parser-agent, intent-identifier-agent (leaf agents)
├─ [CHECKPOINT: verify post_intent, check halt]
├─ Agent("Phase B1: Core Generation") ← fresh context
│    reads: gen-mesh.md, gen-config.md, gen-transform.md (Glue — inline)
│           gen-config.md, gen-transform.md (Databricks — inline)
│    delegates to: glue-mesh-agent, transform-generator-agent (leaf agents)
├─ [CHECKPOINT: verify post_transform, check halt]
├─ Agent("Phase B2: Assembly")        ← fresh context
│    reads: gen-wrapper.md, gen-dtxog.md, gen-dag.md (Glue — inline)
│           gen-driver.md, gen-ddl.md, gen-bundle.md, gen-dag.md (Databricks — inline)
│    delegates to: glue-wrapper-agent, glue-dtxog-agent, databricks-artefact-agent,
│                  dag-generator-agent (leaf agents)
├─ [CHECKPOINT: verify post_generation, check halt]
└─ Agent("Phase C: Quality")          ← fresh context
     reads: gen-tests.md, validate.md (inline)
     delegates to: test-generator-agent, validation agents (leaf agents)
```

**Nesting depth guarantee:**
| Layer | Example | Depth |
|-------|---------|-------|
| Main conversation → Phase Agent | Agent("Phase A: Discovery") | 1 |
| Phase Agent → Leaf Agent | Agent("mapping-parser-agent") | 2 |
| Leaf Agent (terminal) | Executes, returns result | 2 (max) |

**Critical rule — NO Skill() inside phase agents:**
Phase agents MUST NOT call Skill() to invoke commands. Instead they:
1. Read the command's `.md` file from `${CLAUDE_PLUGIN_ROOT}/commands/`
2. Execute the command's step logic inline (file reads, writes, validations)
3. Delegate heavy work to named leaf agents via Agent() where the command spec says "delegate to" or "invoke agent"

> **Note:** `run_in_background` is used ONLY within individual command logic for multi-table batch parallelism (e.g., generating 3 mesh JSONs concurrently). Phase agents run in foreground (NOT background).

### Chain Tables (Reference)

**Glue chain:**

| Step | Phase | Command | Notes |
|------|-------|---------|-------|
| 1 | A | `/parse-mapping` | Resolves G0.5 (tenancy) + G1.5 (DP type) |
| 2 | A | `/classify-sources` | Classifies source table types (Volumetrics → DK → Mapping) |
| 3 | A | `/identify-intent` | Per-table intent (load type, grain, partition) |
| 4 | B1 | `/gen-mesh` | Mesh JSON per target table |
| 5 | B1 | `/gen-config` | Config + filter manifests per target table |
| 6 | B1 | `/gen-transform` | Day0/Day1 transforms per target table |
| 7 | B2 | `/gen-wrapper` | Wrapper + config per target table |
| 8 | B2 | `/gen-dtxog` | DTXOG orchestration config per target table |
| 9 | B2 | `/gen-dag` | Airflow DAG files — reconciled against wrapper.py + DTXOG |
| 10 | C | `/gen-tests` | Pytest suite (>90% coverage) |
| 11 | C | `/review` | Code review — Critical/High findings trigger one retry |
| 12 | C | `/validate` | 7-batch validation with fail-fast; produces verdict |

**Databricks chain:**

| Step | Phase | Command | Notes |
|------|-------|---------|-------|
| 1 | A | `/parse-mapping` | Resolves G0.5 (tenancy) + G1.5 (DP type) |
| 2 | A | `/classify-sources` | Classifies source table types (Volumetrics → DK → Mapping) |
| 3 | A | `/identify-intent` | Per-table intent (load type, grain, partition) |
| 4 | B1 | `/gen-config` | Config.yml + filter manifests per target table |
| 5 | B1 | `/gen-transform` | PySpark .py transforms per target table |
| 6 | B2 | `/gen-driver` | Driver script per target table |
| 7 | B2 | `/gen-ddl` | Iceberg DDL (Unity Catalog) per target table |
| 8 | B2 | `/gen-bundle` | DABs config, job YAMLs, utility notebooks |
| 9 | B2 | `/gen-dag` | Airflow DAG files — reconciled against job.yml |
| 10 | C | `/gen-tests` | Pytest suite (>90% coverage) |
| 11 | C | `/review` | Code review — Critical/High findings trigger one retry |
| 12 | C | `/validate` | 7-batch validation with fail-fast; produces verdict |

### Phase A — Discovery Agent (Steps 1-3)

**Prompt contract for the Phase A Agent:**

```
You are executing Phase A (Discovery) of the DE pipeline full-automation chain.

**EXECUTION MODEL:** Execute command logic INLINE by reading each command's markdown
file and following its steps directly. Do NOT use Skill() to invoke commands — this
would create nested dispatch errors. You MAY use Agent() to delegate to named leaf
agents (mapping-parser-agent, intent-identifier-agent) as specified in each command's
delegation pattern. Maximum nesting: you are depth 1, leaf agents are depth 2.

1. Read session/session_state.json for session context (platform, mapping_excel_path,
   domain_knowledge_path).

2. Read ${CLAUDE_PLUGIN_ROOT}/commands/parse-mapping.md — execute its steps inline:
   - Delegate Excel parsing to Agent("mapping-parser-agent") where command spec says
     "delegate to mapping-parser-agent". The mapping-parser-agent handles Phases 1–6
     only (header validation, row extraction, table-level fields, crypto detection,
     volumetrics).
   - After completion, check session_state for BLOCKING errors.
   - If halted, write halt state and return immediately.
   - STEP 2.7 (Per-Environment Infrastructure Resolution) is NOT handled by
     mapping-parser-agent — you MUST execute it inline after the agent returns:
     a. Read target_database from session_state (populated by mapping-parser-agent).
     b. Look up target_database against the platform tenancy registry:
        - If platform=databricks → use databricks-tenancy skill; match against
          Target DB column (exact case-insensitive match only).
        - If platform=glue → use aws-tenancy skill; match against
          Hive Database / Iceberg Database columns.
     c. If match found → extract tenancy_name and per-env infrastructure values;
        store in session_state.dbx_config (Databricks) or session_state.env_config
        (Glue) per STEP 2.7 of parse-mapping.md.
     d. If NO match found → BLOCKING: invoke Interactive Infrastructure Collection.
        Read the platform-specific questionnaire:
        - Databricks: ${CLAUDE_PLUGIN_ROOT}/prompts/infrastructure-questionnaire-databricks.md
        - Glue: ${CLAUDE_PLUGIN_ROOT}/prompts/infrastructure-questionnaire-glue.md
        Present questions to user via AskUserQuestion (available at depth 1),
        collect responses, store in session_state.dbx_config / session_state.env_config.
        Do NOT proceed until the questionnaire completes and values are stored.
     e. POST-RESOLUTION ASSERTION (mandatory, both platforms):
        - Databricks: verify ALL of:
          (i)   session_state.dbx_config is non-null
          (ii)  session_state.dbx_config.tenancy_name is set
          (iii) session_state.dbx_config.questionnaire_turns_completed == 5
                (if tenancy_resolution_method == "user_provided", not registry)
          (iv)  session_state.dbx_config.dev.target_catalog is non-null
        - Glue: verify ALL of:
          (i)   session_state.env_config is non-null
          (ii)  session_state.env_config.tenancy_name is set
          (iii) session_state.env_config.questionnaire_turns_completed == 6
                (if tenancy_resolution_method == "user_provided", not registry)
          (iv)  session_state.env_config.dev.s3_bucket is non-null
        If ANY check fails → HALT: "STEP 2.7 infrastructure questionnaire incomplete —
        only {questionnaire_turns_completed}/N turns completed. Re-run /parse-mapping
        or provide missing values via infrastructure questionnaire."

3. Read ${CLAUDE_PLUGIN_ROOT}/commands/classify-sources.md — execute its steps inline:
   - Source classification logic runs inline (no leaf agent needed).
   - After completion, check for halt conditions (unclassified source tables).

4. Read ${CLAUDE_PLUGIN_ROOT}/commands/identify-intent.md — execute its steps inline:
   - Delegate intent identification to Agent("intent-identifier-agent") where command
     spec says "delegate to intent-identifier-agent".
   - IMPORTANT: intent-identifier-agent runs at depth 2 (leaf). It MUST NOT spawn
     auto-decision-agent as a nested Agent() call (would be depth 3 — exceeds limit).
     Instead, intent-identifier-agent reads auto-decision-agent.md inline and applies
     the 7-rule framework directly. If confidence is LOW/UNRESOLVED, it uses
     AskUserQuestion to ask the user (available at depth 2).
   - After completion, check for G5-grain halt, G5-C crypto halt.

Chain mode active — commands emit compact output only (STEP 0.0).

On HALT: Write halt state to session_state.json, return:
  {"status": "HALTED", "step": N, "command": "...", "reason": "..."}
On SUCCESS: Verify post_intent checkpoint written, return:
  {"status": "OK", "tables": N, "auto_decisions": M}
```

**After Phase A Agent returns (main conversation):**
1. Read `session/session_state.json` → verify `auto_chain.halted_at_step` (trust disk over agent output)
2. If halted → display halt banner (see Halt Display section) → STOP
3. Verify tenancy resolution (trust disk over agent output):
   - If `platform == "databricks"` → check ALL of:
     (a) `dbx_config` is non-null
     (b) `dbx_config.tenancy_name` is a non-empty string
     (c) If `tenancy_resolution_method == "user_provided"`:
         `dbx_config.questionnaire_turns_completed == 5` AND
         `dbx_config.dev.target_catalog` is non-null
   - If `platform == "glue"` → check ALL of:
     (a) `env_config` is non-null
     (b) `env_config.tenancy_name` is a non-empty string
     (c) If `tenancy_resolution_method == "user_provided"`:
         `env_config.questionnaire_turns_completed == 6` AND
         `env_config.dev.s3_bucket` is non-null
   - If ANY check fails → proceed to **Fallback Infrastructure Collection** below
4. Verify `chain_checkpoints.post_intent` exists (Phase A completion marker)
5. If all checks pass → display: `[Phase A] ✓ Discovery — {N} tables, intent resolved ({M} auto-decisions)`
6. Proceed to Phase B1

**Fallback Infrastructure Collection (main conversation — if tenancy unresolved after Phase A):**

> This fallback is a safety net. Normally STEP 2.7 runs inside the Phase A agent
> (see step 2 of the prompt contract above). This catches the case where Phase A
> returned without resolving tenancy — e.g. context compaction discarded the STEP 2.7
> instruction or the questionnaire was interrupted mid-flow.

1. Read `session/session_state.json` to get `platform` and `target_database`.
2. Read the platform-specific infrastructure questionnaire:
   - Databricks: `${CLAUDE_PLUGIN_ROOT}/prompts/infrastructure-questionnaire-databricks.md`
   - Glue: `${CLAUDE_PLUGIN_ROOT}/prompts/infrastructure-questionnaire-glue.md`
3. Present the infrastructure questionnaire to the user interactively:
   - Databricks: batched Turn 1–5 flow (Q1 tenancy_name through confirmation summary)
   - Glue: sequential Q1–Q2 + Q3g–Q6g through confirmation summary
4. Store collected values in `session_state.dbx_config` (Databricks) or
   `session_state.env_config` (Glue).
5. POST-RESOLUTION ASSERTION: verify config object is non-null and `tenancy_name`
   is set. If still unresolved after one re-prompt of Q1 → HALT with banner:
   ```
   ═══════════════════════════════════════════════════════
    AUTO-CHAIN HALTED: Infrastructure resolution failed
   ═══════════════════════════════════════════════════════
    Target database '{target_database}' not found in {platform} tenancy registry.
    Infrastructure questionnaire did not complete — tenancy_name is required.

    Fix: Provide tenancy_name, then run /resume
   ═══════════════════════════════════════════════════════
   ```
6. If assertion passes → log: `[FALLBACK] Infrastructure collected at main-conversation level`
7. Proceed to Phase B1.

---

### Phase B1 — Core Generation Agent (Steps 4-6 Glue / 4-5 Databricks)

**Prompt contract for the Phase B1 Agent:**

```
You are executing Phase B1 (Core Generation) of the DE pipeline full-automation chain.

**EXECUTION MODEL:** Execute command logic INLINE by reading each command's markdown
file. Do NOT use Skill(). You MAY use Agent() to delegate to named leaf agents
(glue-mesh-agent, transform-generator-agent) as specified in each command's delegation
pattern.

1. Read session/session_state.json — load chain_checkpoints.post_intent for per-table
   context.
2. Platform: {platform} (from session_state.platform)
3. If resume_from_step is set:
   a. Read auto_chain.completed_steps — skip commands already completed.
   b. Load highest available mid-phase checkpoint:
      post_config > post_intent
4. Read and execute each core generation command's markdown inline, in order:

   [Glue — read from ${CLAUDE_PLUGIN_ROOT}/commands/]:
   gen-mesh.md → gen-config.md → gen-transform.md

   [Databricks — read from ${CLAUDE_PLUGIN_ROOT}/commands/]:
   gen-config.md → gen-transform.md

   For each command:
   - Read the .md file
   - Execute its step logic inline
   - Delegate to leaf agents where command spec says "delegate to {agent-name}"
   - After each command, check session_state for halt conditions

5. Skip any step whose step number is in completed_steps.

Chain mode active — commands emit compact output only (STEP 0.0).

On HALT: Write halt state to session_state.json, return:
  {"status": "HALTED", "step": N, "command": "...", "reason": "..."}
On SUCCESS: Verify post_transform checkpoint written, return:
  {"status": "OK", "tables": N, "files_generated": M}
```

**After Phase B1 Agent returns (main conversation):**
1. Read `session/session_state.json` → verify `auto_chain.halted_at_step` (trust disk over agent output)
2. If halted → display halt banner → STOP
3. Verify `chain_checkpoints.post_transform` exists (Phase B1 completion marker)
4. If all checks pass → display: `[Phase B1] ✓ Core Generation — {N} tables, config + transforms generated`
5. Proceed to Phase B2

---

### Phase B2 — Assembly Agent (Steps 7-9 Glue / 6-9 Databricks)

**Prompt contract for the Phase B2 Agent:**

```
You are executing Phase B2 (Assembly) of the DE pipeline full-automation chain.

**EXECUTION MODEL:** Execute command logic INLINE by reading each command's markdown
file. Do NOT use Skill(). You MAY use Agent() to delegate to named leaf agents
(glue-wrapper-agent, glue-dtxog-agent, databricks-artefact-agent, dag-generator-agent)
as specified in each command's delegation pattern.

1. Read session/session_state.json — load chain_checkpoints.post_intent AND
   chain_checkpoints.post_transform for per-table context and generated artefact paths.
2. Platform: {platform} (from session_state.platform)
3. If resume_from_step is set:
   a. Read auto_chain.completed_steps — skip commands already completed.
   b. Load highest available mid-phase checkpoint:
      post_dag > post_transform
4. Read and execute each assembly command's markdown inline, in order:

   [Glue — read from ${CLAUDE_PLUGIN_ROOT}/commands/]:
   gen-wrapper.md → gen-dtxog.md → gen-dag.md

   [Databricks — read from ${CLAUDE_PLUGIN_ROOT}/commands/]:
   gen-driver.md → gen-ddl.md → gen-bundle.md → gen-dag.md

   For each command:
   - Read the .md file
   - Execute its step logic inline
   - Delegate to leaf agents where command spec says "delegate to {agent-name}"
   - After each command, check session_state for halt conditions

5. Skip any step whose step number is in completed_steps.

Chain mode active — commands emit compact output only (STEP 0.0).

On HALT: Write halt state to session_state.json, return:
  {"status": "HALTED", "step": N, "command": "...", "reason": "..."}
On SUCCESS: Verify post_generation checkpoint written, return:
  {"status": "OK", "files_generated": N, "artefact_count": M}
```

**After Phase B2 Agent returns (main conversation):**
1. Read `session/session_state.json` → verify `auto_chain.halted_at_step` (trust disk over agent output)
2. If halted → display halt banner → STOP
3. Verify `chain_checkpoints.post_generation` exists (Phase B2 completion marker)
4. If all checks pass → display: `[Phase B2] ✓ Assembly — wrappers, orchestration, DAGs generated`
5. Proceed to Phase C

---

### Phase C — Quality Agent (Steps 10-12 Glue / 10-12 Databricks)

**Prompt contract for the Phase C Agent:**

```
You are executing Phase C (Quality) of the DE pipeline full-automation chain.

**EXECUTION MODEL:** Execute command logic INLINE by reading markdown files.
Do NOT use Skill(). You MAY use Agent() to delegate to named leaf agents
(test-generator-agent, code-review-agent, glue-validation-agent /
databricks-validation-agent).

1. Read session/session_state.json — load chain_checkpoints.post_generation for
   artifact context.
2. If resume_from_step is set: skip commands already in completed_steps.

3. Read ${CLAUDE_PLUGIN_ROOT}/commands/gen-tests.md — execute inline:
   - Delegate test generation to Agent("test-generator-agent").
   - After completion, check for halt conditions.

4. Read ${CLAUDE_PLUGIN_ROOT}/commands/review.md — execute inline:
   - Delegate code review to Agent("code-review-agent") with generated file
     paths, mapping, and intent context (fresh leaf agent — clean context).
   - Handle Critical/High findings via isolated per-finding fix agents
     (Phase B of review.md).
   - After completion, check for REJECTED status (Critical findings persist
     after retry → halt).

5. Read ${CLAUDE_PLUGIN_ROOT}/commands/validate.md — execute inline:
   - Delegate validation batches to leaf agents as specified in validate.md.
   - After completion, check for REJECTED verdict.

Chain mode active — commands emit compact output only (STEP 0.0).

On HALT: Write halt state to session_state.json, return:
  {"status": "HALTED", "step": N, "command": "...", "reason": "..."}
On SUCCESS: Return:
  {"status": "OK", "verdict": "APPROVED", "red_flags": 0,
   "warnings": N, "syntax_check": "passed|failed|skipped"}
```

**After Phase C Agent returns (main conversation):**
1. Read `session/session_state.json` → verify validation_results
2. If halted/REJECTED → display halt banner → STOP
3. If success → display post-chain summary

### Halt Conditions

Stop the chain **immediately** if any of these occur (applies at any step):

| Condition | Example | Action |
|-----------|---------|--------|
| BLOCKING error from any command | Excel unreadable, invalid DP type prefix, mixed prefixes | Display error; halt |
| G5 halt (grain ambiguity) | `auto-decision-agent` returns LOW confidence for intent | Display unresolved fields; halt |
| G5-C crypto halt | Crypto flagged but DE name unextractable | Display crypto issue; halt |
| Validation REJECTED | Blocking red flags found by validators | Display red flag list; halt |
| Critical/High persists after retry | `/review` finds Critical issue, regeneration doesn't fix it | Display findings; halt |

**On halt (after any Skill() returns with halt indicators):**

1. **Persist halt state** in `session_state.json` (session-state-persist hook handles atomic write):
   ```json
   {
     "auto_chain": {
       "enabled": true,
       "chain_mode": true,
       "halted_at_step": {N},
       "halted_at_command": "{command_name}",
       "halt_reason": "{halt_reason}",
       "halted_at_timestamp": "{ISO 8601 timestamp}",
       "completed_steps": [{completed_step_numbers}],
       "report_generated": "session/intent_resolution_report.md"
     }
   }
   ```

2. **Generate resolution report** (G5 halts only):
   - If halt is due to G5-grain (intent ambiguity), invoke report generation (see `/identify-intent` STEP-REPORT)
   - Writes `session/intent_resolution_report.md` with per-field analysis and fix options

3. **Display halt banner** (see Halt Display section below)

### Halt Display

When a halt condition is detected (session_state shows `halted_at_step` is non-null), display:

```
═══════════════════════════════════════════════════════
 AUTO-CHAIN HALTED at step {N}: {command_name}
═══════════════════════════════════════════════════════
 Reason: {halt_reason}
 
 📄 Resolution report: session/intent_resolution_report.md
    Open this file to see exactly which fields are missing and how to fix them.
 
 Quick fix: Create session/intent_overrides.json with the missing values,
            then run /resume
 
 Other options:
   /resume --reparse    (if you updated the mapping Excel)
   /resume --from {N}   (resume from specific step)
═══════════════════════════════════════════════════════
```

**Log** to `session/audit_log.jsonl`: `[AUTO-CHAIN] Halted at step {N} ({command}): {reason}`

### Progress Display

Progress is displayed per-phase in the main conversation after each phase boundary checkpoint passes:

```
[Phase A]  ✓ Discovery — 3 target tables, intent resolved (5 auto-decisions)
[Phase B1] ✓ Core Generation — 3 tables, config + transforms generated
[Phase B2] ✓ Assembly — wrappers, orchestration, DAGs generated
[Phase C]  ✓ Quality — APPROVED (0 blocking, 2 warnings)
```

Per-step progress is visible inline as each Skill() command emits its STEP 0.0 compact output. Phase-level summaries are displayed after checkpoint verification passes at each boundary.

### Post-Chain Summary

After successful completion of all four phases, display:

```
═══════════════════════════════════════════════════════
 AUTO-CHAIN COMPLETE
═══════════════════════════════════════════════════════
 Platform:       Glue (DTX-BYOC)
 Tables:         3 target tables processed
 Artefacts:      {N} files generated
 Syntax Check:   {passed | failed (N files) | skipped — no Python}
 Test Execution: {passed | failed (non-blocking) | skipped — no Python}
 Validation:     APPROVED (0 blocking, 2 warnings)
 Auto-decisions: {M} (see session/audit_log.jsonl)
═══════════════════════════════════════════════════════
```

### Context Checkpointing (Inter-Phase Communication)

Checkpoints are the **primary mechanism for inter-phase communication**. Each phase writes checkpoints after its commands complete; the next phase loads them on startup from disk.

**Protocol:**
- After each command, the phase agent writes a structured checkpoint to `session_state.chain_checkpoints` (via session-state-persist hook)
- Each phase agent loads relevant checkpoint sections (~200-500 tokens) at startup from `session/session_state.json`
- Checkpoints are deterministic (written to session state JSON), so they survive both context compaction AND phase boundaries
- Phase isolation means each phase starts with fresh context budget — checkpoints are the compact handoff

**Checkpoint Boundaries:**

| After Step | Checkpoint Key | Written By | Content |
|---|---|---|---|
| `/parse-mapping` | `post_parse` | Phase A | `{tenancy, dp_type, target_tables[], target_database, optional_columns[], source_tables_count, crypto_detected}` |
| `/classify-sources` | `post_classification` | Phase A | `{source_table_types: {table: type}, classification_status: "success", tables_classified_count, volumetrics_count, domain_knowledge_count, mapping_document_count}` |
| `/identify-intent` | `post_intent` | Phase A | `{per_table_intent: [{table, load_type, table_type, grain, pk_cols, partition_col}], all_resolved: bool, auto_decisions_count}` |
| `/gen-config` | `post_config` | Phase B1 | `{config_files: [paths], filter_manifests: [paths], per_table_summary: [...]}` |
| `/gen-transform` | `post_transform` | Phase B1 | `{tables: [{table, load_type, table_type, pk_cols, partition_col, status, files_generated: [paths]}], platform, timestamp}` |
| `/gen-dag` | `post_dag` | Phase B2 | `{dag_count, schedule_type, platform, tables_with_dags[], dag_spec_path, timestamp}` |
| All gen commands | `post_generation` | Phase B2 | `{generated_files: [paths], crypto_applied: [columns], template_versions_used: {}, artefact_count}` |

**Writing checkpoints** (after each command completes within a phase):
```json
session_state.chain_checkpoints.post_parse = {
  "tenancy": "fdpmortgage",
  "dp_type": "FDP",
  "target_tables": ["account_wm", "rates_fees"],
  "target_database": "fdp_uk_mortgage_db",
  "source_tables_count": 5,
  "crypto_detected": true,
  "timestamp": "2026-07-03T10:15:00Z"
}
```

**Reading checkpoints** (at start of each phase agent):
- Phase B1 agent loads `chain_checkpoints.post_intent` on startup
- Phase B2 agent loads `chain_checkpoints.post_intent` + `chain_checkpoints.post_transform` on startup
- Phase C agent loads `chain_checkpoints.post_generation` on startup
- Within a phase, each command also loads its own required checkpoint from disk (defense-in-depth, Principle 4)

**Benefit:** Phase isolation gives each phase fresh context budget. Checkpoints provide compact (~500 token) inter-phase handoff without carrying forward all prior command output.

### Post-Phase Verification (Main Conversation)

After EACH phase Agent() returns, the main conversation MUST:
1. Read `session/session_state.json` from disk (trust disk over agent output)
2. Verify `auto_chain.halted_at_step` is null (not halted)
3. Verify the expected checkpoint exists (e.g., `chain_checkpoints.post_intent` after Phase A, `chain_checkpoints.post_transform` after Phase B1, `chain_checkpoints.post_generation` after Phase B2)
4. Only if both checks pass → proceed to next phase Agent()

This prevents a scenario where a phase agent crashes without properly writing halt state.

### Resumability

If the chain halts mid-execution, the user can:
1. Fix the issue (e.g., correct mapping, add domain knowledge hints, resolve ambiguity)
2. Run `/resume` which dispatches to the correct phase agent starting from the halted step
3. Or run the failed command manually (it will use existing session state)

Session state persists across manual commands — no need to re-run completed steps. Chain checkpoints persist, providing context for phase agents on resume.

**Phase-aware resume:** `/resume` maps the halted step to its phase (A/B1/B2/C) and dispatches the appropriate phase agent with `resume_from_step=N` to skip already-completed commands within that phase.

**Mid-phase checkpoint loading on resume:** When a phase agent is dispatched with `resume_from_step`, it loads not only the prior-phase boundary checkpoint but also any mid-phase checkpoints written before the halt:
- **Phase B1 resumes:** loads `post_intent` (always) + `post_config` (if exists)
- **Phase B2 resumes:** loads `post_intent` (always) + `post_transform` (always — B1 must have completed) + `post_dag` (if exists)
- **Phase C resumes:** loads `post_generation` (always)

Each command independently loads its own required checkpoint from disk on startup (defense-in-depth, Principle 4). The phase-agent-level checkpoint loading provides faster context bootstrapping — it knows which files already exist and which tables have been processed.

### Auto-Chain vs Interactive: Behaviour Comparison

| Aspect | Interactive (default) | Full-Automation (`--full-automation`) |
|--------|----------------------|--------------------------------------|
| Command invocation | User types each slash command | Phase agents execute command logic inline after `/init` |
| Context isolation | Single conversation | Fresh context per phase (4 isolated Agent() calls: A, B1, B2, C) |
| Gate prompts (G1, G5) | User answers | G1 from `--platform`; G5 via `auto-decision-agent` |
| Source type unclassified | User asked for type | `auto-decision-agent` applies fallback heuristics |
| Ambiguities | User asked via AskUserQuestion | `auto-decision-agent` applies 7-rule framework |
| Code review findings | User reviews | Auto-fix Medium; retry Critical once; halt if persists |
| Push to GitLab | `/push` (manual, always) | NOT auto-pushed — user must explicitly push |

**IMPORTANT:** Auto-chain NEVER auto-pushes to GitLab. `/push` always requires explicit user invocation, even in full-automation mode.

> See `${CLAUDE_PLUGIN_ROOT}/agents/refs/tool-invocation-patterns.md` for authoritative tool invocation patterns.

---

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `/init` completes but no phase executes | Main conversation didn't dispatch Phase A | Re-run `/init --full-automation` — ensure the Phase Dispatch Responsibility section is followed |
| Session state shows old session | Previous session not cleared; `/init` write may have failed | Delete `session/` directory, re-run `/init` |
| Hooks not active | `.claude/settings.json` missing or hooks not merged | Check plugin's `hooks/hooks.json` is loaded; verify with `cat .claude/settings.json` |
| Phase A starts but halts immediately | Session state missing required fields | Check `session/session_state.json` has `platform`, `mapping_excel_path`, `auto_chain.enabled` |
| Audit log empty for current date | `/init` failed silently before writing audit entry | Check session state file exists; re-run `/init` with error logging |
| Auto-chain object is null | `--full-automation` flag not processed | Verify command was `/init <path> --platform glue --full-automation` (all 3 args required) |
| Phase B1 completes but B2 times out | Complex DAG assembly (14+ template blocks) or high table count exhausting B2 context | Reduce table count, simplify DAG schedule type, or check domain knowledge scoping |
