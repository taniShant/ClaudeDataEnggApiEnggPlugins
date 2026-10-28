# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **FORGE-compliant Claude Code plugin** (`mca1-ui-mca2-migration`) that autonomously migrates MCA1 JMVC/BDL UI applications to MCA2 React with Blueprint-React and functional component patterns.

This is a **documentation and agent-definition project** — there is no application source code to build or test. The deliverables are agent definitions (Markdown with YAML frontmatter), skill reference documents, and a command file.

## Plugin Architecture (FORGE Pattern)

The plugin uses a thin-command → orchestrator → worker delegation hierarchy:

```
commands/mca1-migration.md          # Thin command: parse args, validate, delegate
  └── agents/mca1-orchestrator-agent.md  # Hub orchestrator: manage phases, state, spawn workers
        ├── agents/mca1-analysis-agent.md    # Phase 1: read-only scanner → analysis.json
        ├── agents/mca1-transform-agent.md   # Phase 2: file-batch worker (parallel)
        ├── agents/mca1-validation-agent.md  # Phase 3: read-only gatekeeper
        ├── agents/mca1-regression-agent.md  # Phase 4: regression→Cypress E2E (conditional)
        └── agents/auto-decision-agent.md    # Any phase: resolve ambiguity autonomously
```

**State file:** `{PROJECT_PATH}/.claude/mca1-ui-mca2-migration-state.json` — enables resume on re-run.

## Skills (Domain Knowledge)

One skill (`domain-reference`) provides all reference material to agents at runtime:

### Key files in `skills/domain-reference/`

- `SKILL.md` — Phase architecture, BDL→Blueprint mapping table, iron rules, decision rules
- `IMPLEMENTATION_GUIDE.md` — Core implementation guide with 29 documented mistakes (the primary knowledge artifact)
- `guides/BDL_TO_BLUEPRINT_REACT.md` — 41-component mapping index
- `guides/BLUEPRINT_REACT_CORRECT_PATTERNS.md` — Authoritative API usage patterns
- `guides/MIGRATION_GUIDES_INDEX.md` — Master navigation index
- `mappings/` — 23 per-component mapping files (e.g., `BDL_INPUT_MAPPING.md`, `BDL_DIALOG_MAPPING.md`)
- `lessons_learnt/` — Accumulated patterns and example project notes

## Invocation

```bash
/mca1-migration PROJECT_PATH [--jira JIRA_ID] [--additional-input "<text>"] [--full-automation] [--regression-repo "<url>"]
```

The command validates args then spawns `mca1-orchestrator-agent` via the Task tool with `subagent_type: "mca1-ui-mca2-migration:mca1-orchestrator-agent"`.

## Critical Blueprint-React Patterns

These are the most impactful mistakes — any changes must be verified against `skills/domain-reference/IMPLEMENTATION_GUIDE.md`:

- **FormItem** uses a `render` prop function, NOT children wrapping
- **Dialog** uses slot props (`head`, `foot`), NOT `DialogHeader`/`DialogFooter` (they don't exist)
- **Table** uses standard HTML `<table>/<thead>/<tbody>` inside a `<Table>` wrapper, NOT sub-components
- **Icon** MUST have a `size` prop or renders oversized
- **Button** variants: `primary`, `secondary`, `tertiary`, `subtle` (not `contained`, `outlined`, `text`, `ghost`)
- Do NOT create custom CSS modules for Blueprint components — Blueprint handles its own styling
- **MemoryRouter** (not BrowserRouter) for client-side routing

## Validation

Run from the repo root (parent of `plugins/`):

```bash
python3 tests/run_all_tests.py              # All checks
python3 tests/test_marketplace.py           # Marketplace + plugin.json consistency
python3 tests/test_skill_content.py         # Skill YAML frontmatter and content quality
```

## Editing Guidelines

- **Agent files** (`agents/*.md`): YAML frontmatter fields `name`, `model`, `tools` are required. The `name` must match the `subagent_type` suffix used by callers.
- **SKILL.md files**: The YAML frontmatter (`name`, `description`) must remain intact.
- **IMPLEMENTATION_GUIDE.md**: When adding mistakes to `skills/domain-reference/IMPLEMENTATION_GUIDE.md`, follow the existing numbered format and update the count.
- **Mapping files** (`skills/domain-reference/mappings/`): Each file is a standalone BDL→Blueprint-React mapping with before/after examples. File naming: `BDL_<COMPONENT>_MAPPING.md`.
- **`plugin.json`** fields must exactly match the entry in the root `.claude-plugin/marketplace.json`.
- Update `MIGRATION_GUIDES_INDEX.md` when adding new documentation files.
- Cross-references between docs use relative markdown links.
