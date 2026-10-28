---
name: arbiter-remove
agent: arbiter-remove-agent
allowed-tools: [Bash, Read, Write, Edit, Glob]
description: "Execute removal tasks safely with validation gates, automatic rollback, and batch modes (v1.0)"
---

# Remove: Safe Dead Code Removal (v1.0: Batch Support)

Execute removal tasks with pre- and post-removal validation gates, automatic rollback on failure, and batch execution modes for efficient multi-task workflows.

## Arguments (v1.0: Batch Modes)

```
EXECUTION_MODE:       How to execute
  next                Execute single next task (legacy behavior)
  T001                Execute specific task ID
  --all               Execute all remaining tasks, fail on first error (v1.0)
  --until T010        Execute up to task T010, then stop (v1.0)
  --category SAFE     Execute all SAFE tasks, then stop (v1.0)
  --batch 5           Execute next 5 tasks (v1.0)

FLAGS:
  --dry-run           Show what would be removed (no actual changes)
  --no-commit         Skip git commit (testing only)
  --force             Skip confirmation prompts
--technology TECH   Target technology: java | ios (default: auto-detect)
--module MODULE     Target a specific submodule/package (optional)
--scheme SCHEME     Xcode scheme for validation (iOS only)
```

## Technology Routing

| Technology | Agent |
|---|---|
| `java` | arbiter-remove-agent |
| `ios` | arbiter-remove-ios-agent |

If `--technology` is not provided, the technology is auto-detected (`*.xcodeproj`, `*.xcworkspace`, `Package.swift` → ios; `pom.xml`, `build.gradle` → java).

iOS validation: `xcodebuild build` (+ `xcodebuild test` for LIKELY/UNCERTAIN), or `swift build`/`swift test` for Swift packages.

## Example

```
# Legacy style (sequential single tasks)
/arbiter-remove next
/arbiter-remove T001
/arbiter-remove T005 --dry-run

# v1.0 style (batch execution - 90% FEWER commands!)
/arbiter-remove --all            # Execute all tasks (was: call /arbiter-remove next 18x)
/arbiter-remove --category SAFE  # Execute all SAFE tasks first
/arbiter-remove --batch 5        # Execute 5 tasks at a time
/arbiter-remove --until T010     # Execute up to T010

# iOS
/arbiter-remove --technology ios next --dry-run
/arbiter-remove --technology ios --batch 2 --scheme MyApp
/arbiter-remove --technology ios --all --scheme MyApp
```

## Validation Gates (Per Task)

For each removal task:
1. **Compile check:** Code must compile post-removal
2. **Unit test check:** All unit tests must pass
3. **(LIKELY/UNCERTAIN only)** Integration test check

If any gate fails: **automatic rollback** (fail-on-first-error for batch mode).

## Baseline Auto-Establishment (v1.0)

**First task automatically establishes baseline (implicit):**
- Before first task: runs full test suite once, saves baseline
- After each task: compares against baseline for regressions
- No explicit `/arbiter-validate --baseline` command needed

Result: One fewer user command!

## Output

Removal log with:
- Task ID(s) executed, entities removed, status
- Validation results (compile pass/fail, tests pass/fail)
- Git commit SHAs (if successful)
- Rollback messages (if failed)
- Batch summary (for batch modes)

## Batch Execution Behavior

**Default: Fail on first error**
```
/arbiter-remove --all

Task T001: SAFE → Success ✓ (compiled, tests pass)
Task T002: SAFE → Success ✓
Task T003: SAFE → FAILED ✗ (compilation error)

Execution stopped. Fix T003 and retry, or skip to next task.
```

**iOS — isolate and continue:** a failing batch is narrowed down (compiler-error attribution, then bisection); failing entities are restored, the rest is kept, and the run continues with the next batch. All failures are listed at the end; `--stop-on-failure` stops instead. Every outcome is recorded in `.arbiter/swift/OUTCOMES.jsonl`.

## Next Steps

- **After single task:** `/arbiter-remove next` for next task
- **After batch (`--all`):** `/arbiter-status` to see progress
- **After all complete:** `/arbiter-validate --report` for final summary (optional)

## Performance (v1.0 Improvements)

| Workflow | Legacy | v1.0 | Improvement |
|----------|--------|------|-------------|
| Remove 18 tasks | 18 commands | 1 command (`--all`) | 95% fewer |
| Token usage | 13.5K | 8-9K | 35% savings |
| Phases | 6 | 5 (baseline implicit) | -1 phase |
