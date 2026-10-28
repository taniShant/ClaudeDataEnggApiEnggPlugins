---
description: "Pattern for loading chain checkpoints at phase boundaries — checkpoint data serves as source of truth for prior-phase decisions (table list, load_type, table_type, PKs, partition columns, tenancy) with fallback to full session files."
owner: "Samir Chaudhari <samir.chaudhari@barclays.com>"
review_cadence: quarterly
last_reviewed: 2026-07-08
---

# Chain Checkpoint Loading Pattern

> **Applies to:** Generator commands (de-gen-config, de-gen-transform, de-gen-wrapper, de-gen-mesh, de-gen-dtxog, de-gen-bundle, de-gen-driver, de-gen-ddl, de-gen-tests) when chain checkpoints exist.

## Pattern

Chain checkpoints are compact metadata snapshots written at phase boundaries. They survive context compaction and provide reliable prior-phase decisions.

**Loading rules:**

1. If the relevant checkpoint exists in `session_state.chain_checkpoints.{checkpoint_key}`:
   - Use checkpoint data for table list, load_type, table_type, PKs, partition_col, tenancy — do NOT re-parse full session files for these values
   - The checkpoint is the **source of truth** for prior-phase decisions

2. If checkpoint does NOT exist (standalone command execution):
   - Fall back to reading full session files (`mapping_parsed.json`, `intent_identification.json`, etc.)

3. If `session_state.auto_chain.enabled == true`:
   - Also load `session_state.chain_checkpoints.post_intent` for reliable context recovery (provides per-table intent summary that survives context compaction)

## Checkpoint Keys by Phase

| Phase | Checkpoint Key | Provides |
|-------|---------------|----------|
| Post-parsing | `post_parse` | table list, source/target DB, column count, domain knowledge path |
| Post-intent | `post_intent` | load_type, table_type, grain, PK, partition per table |
| Post-transform | `post_transform` | files generated, transformation_steps, platform, status |
| Post-generation | `post_generation` | all artifact statuses, file paths |

## What Still Needs Full File Reads

Even with checkpoints available, some commands need specific data not in the checkpoint:
- `column_mappings` (from `mapping_parsed.json`) — needed for config filter extraction, DDL column defs, transform generation
- `transformation_steps` (from `mapping_parsed.json`) — needed for transform generation
- `crypto_flags` (from `session/crypto_flags.json`) — needed when `has_crypto == true`
