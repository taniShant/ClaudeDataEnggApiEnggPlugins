# barclays-buk-strangler-refactoring-strangler-discover-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-strangler-refactoring-strangler-discover-v1` |
| Plugin name | `barclays-buk-strangler-refactoring` |
| Component type | skill-user-only |
| Owner | Preetha Ramaswamy |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-strangler-refactoring@barclays-cio-buk |
| Native command | `/barclays-buk-strangler-refactoring:strangler-discover` |
| Skill name | `strangler-discover` |

## Description

Discover monolithic classes/modules and assess complexity for strangler pattern refactoring.

## When to use

Use when you have a large monolithic class (ideally >500 lines) that you want to assess for strangler pattern refactoring — this capability identifies domain boundaries, calculates complexity metrics, and discovers API patterns to inform a decomposition plan, but it does NOT perform the actual refactoring or proceed to the analysis phase.

## Inputs

- TARGET_FILE (required, positional): Path to the monolithic class file to analyze (e.g., `src/main/java/.../AppPolicyRefactoringServiceImpl.java`); must be a code file (.java, .py, .ts, etc.), not a config file (.json, .xml)
- --jira JIRA_ID (optional): JIRA ticket ID for tracking, must match format `^[A-Z]+-[0-9]+$` (e.g., HPTRX-9196); auto-detected from current Git branch name if not provided
- --quick (optional flag): Reduces thoroughness from "very thorough" to "medium" for faster, less detailed discovery
- --dry-run (optional flag): Previews the discovery scope (target analysis, phases, workers, cost estimate, potential issues) without executing anything or creating any artifacts

## Preconditions

- TARGET_FILE must exist on disk (absolute or relative path, resolved against cwd)
- TARGET_FILE must be a source code file (.java, .py, .ts, etc.) — config files like .json/.xml are rejected
- File should be >500 lines for meaningful strangler pattern analysis (a warning is emitted if <500 lines)
- Git context must be available (used for branch detection and JIRA ID inference)
- The `.claude/` directory must be writable (state file and artifacts are created there)
- The `logs/` directory must be writable (or creatable) for forge.log output

## Expected outputs

- `.claude/forge-state.json`: FORGE v2 state file tracking discovery phase completion and resume capability
- `.claude/STRANGLER_DISCOVERY_CACHE.json`: Intermediate cache containing full AST parse results (produced by Worker 1A, consumed by Workers 1B and 1C)
- `.claude/STRANGLER_DISCOVERY.md`: Final discovery report aggregating structure analysis, domain boundaries, and complexity metrics
- `.claude/STRANGLER_API_PATTERNS.md`: Discovered project conventions including naming patterns, DI style, and test framework usage
- `logs/forge.log`: Timestamped execution log with agent identifiers and START/COMPLETE markers
- In --dry-run mode: only a formatted preview is printed to stdout (file analysis, phases, artifacts list, cost estimate, potential issues); no files are created or modified

## Exclusions

- Does NOT perform actual refactoring, code extraction, or file modifications to the target codebase
- Does NOT proceed to Phase 2 (analysis) — that is a separate command in the strangler workflow
- Does NOT implement discovery logic inline; all analysis is delegated to an orchestrator which spawns specialized workers
- Does NOT modify the TARGET_FILE or any source code files
- Does NOT create Git branches or commits directly (branch creation is handled by the orchestrator in Phase 0)
- In --dry-run mode: does NOT create state files, spawn workers, generate artifacts, or write log files

## Verification

After successful execution, verify that `.claude/STRANGLER_DISCOVERY.md` and `.claude/STRANGLER_API_PATTERNS.md` exist and contain meaningful domain boundary groupings, complexity metrics, and project convention details for your target file. Check `logs/forge.log` for a `[COMPLETE]` entry from the strangler-discover agent, and confirm `.claude/forge-state.json` reflects discovery phase completion. For --dry-run mode, verify that the preview output was displayed and that no files were created in `.claude/` or `logs/`.
