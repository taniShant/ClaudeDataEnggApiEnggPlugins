---
description: |
  Discover monolithic classes/modules and assess complexity for strangler pattern refactoring.
  Thin command: Parse arguments, validate target, delegate to orchestrator. Supports --dry-run for preview.
argument-hint: TARGET_FILE [--jira JIRA_ID] [--quick] [--dry-run]
---

# Strangler Pattern Discovery (FORGE-Compliant)

You are the Strangler Discover Command. Your ONLY job: parse arguments, validate inputs, detect context, spawn the orchestrator (or render dry-run preview).

**STRICT RULES:**
- NEVER implement discovery logic inline — delegate to orchestrator
- NEVER modify files directly — orchestrator delegates to workers
- NEVER add steps or phases not listed in this document
- Parse args, validate, detect context, spawn orchestrator (or dry-run preview) → STOP

---

## Step 1: Parse Arguments

```
FORMAT: TARGET_FILE [--jira JIRA_ID] [--quick] [--dry-run]

POSITIONAL:
  TARGET_FILE     Path to monolithic class (required)
                  - Example: src/main/java/.../AppPolicyRefactoringServiceImpl.java
                  
FLAGS:
  --jira JIRA_ID          JIRA ticket ID (optional, for tracking)
  --quick                 Use medium thoroughness (faster, less detail)
  --dry-run               Preview discovery scope WITHOUT executing
                          - Shows target file analysis (size, methods count, imports)
                          - Lists phases that will execute and workers that will spawn
                          - Estimates time and token cost
                          - Identifies potential issues (file too small, no REST layer)
                          - NO state file created, NO artifacts generated, NO workers spawned
```

**On parse failure:** Log specific error and STOP.

---

## Step 2: Validate TARGET_FILE

- Path can be absolute or relative (resolve to cwd)
- Must exist as a file
- File size: >500 lines recommended (warn if <500)
- Must be code file (.java, .py, .ts, etc., not .json/.xml)

**On validation failure:** Log specific error and STOP.

---

## Step 3: Validate JIRA_ID (if provided)

- Format: `^[A-Z]+-[0-9]+$` (e.g., HPTRX-9196)

**On validation failure:** Log error and STOP.

---

## Step 4: Detect Context

```bash
# Resolve relative path to absolute
TARGET_FILE=$(cd $(dirname {TARGET_FILE}) && pwd)/$(basename {TARGET_FILE})

# Detect if state file exists (resume scenario)
STATE_FILE=".claude/forge-state.json"
if [ -f "$STATE_FILE" ]; then
    echo "Resuming: State file detected"
fi

# Detect Git context
JIRA_ID_FROM_BRANCH=$(git rev-parse --abbrev-ref HEAD | grep -oP '(?<=/|^|-)[A-Z]{2,}-\d+' | head -1)
if [ -z "$JIRA_ID" ] && [ ! -z "$JIRA_ID_FROM_BRANCH" ]; then
    JIRA_ID="$JIRA_ID_FROM_BRANCH"
fi
```

---

## Step 5: Set Up Log

```bash
mkdir -p logs
LOG="logs/forge.log"
[ -f "$LOG" ] && mv "$LOG" "${LOG%.log}_backup_$(date '+%d%m%y_%H%M%S').log"
touch "$LOG"
echo "[$(date '+%d/%m/%y %H:%M:%S')] [AGENT:strangler-discover] [START] TARGET_FILE={TARGET_FILE} JIRA_ID={JIRA_ID}" >> "$LOG"
```

---

## Step 5.5: Dry-Run Preview (--dry-run mode)

**When `--dry-run` is specified**, preview what discovery would do WITHOUT executing:

```
CRITICAL: In dry-run mode:
  ✗ NO state file created
  ✗ NO workers spawned
  ✗ NO artifacts generated
  ✗ NO log files created
  ✓ READ target file (basic analysis only)
  ✓ DISPLAY preview → STOP
```

**Dry-Run Output:**

```
═══════════════════════════════════════════════════════════════
          🔍 DRY-RUN: DISCOVERY PREVIEW
═══════════════════════════════════════════════════════════════

📎 TARGET FILE ANALYSIS
  Path:           {TARGET_FILE}
  Size:           {LINES} lines ({SIZE} KB)
  Language:       {detected: Java/Python/TypeScript}
  Size Warning:   {⚠️ <500 lines — may not benefit from strangler | ✅ OK}

  Quick scan results:
    - Public methods:    ~{N} (grep -c "public.*(" | approximate)
    - Import count:      ~{N}
    - @Autowired fields: ~{N} (or constructor params)
    - Class annotations: {list: @Service, @Component, etc.}
    - Estimated domains: ~{N} (from method name prefix analysis)

───────────────────────────────────────────────────────────────
🔄 PHASES THAT WILL EXECUTE
───────────────────────────────────────────────────────────────

  Phase 0: Validation & Setup
    - Create .claude/forge-state.json
    - Create branch: strangler/{JIRA_ID}
    - Model: fast
    - Duration: ~1 min

  Phase 1: Discovery (4 workers)
    Stage 1 (sequential):
      Worker 1A: Structure Analyzer (cache producer)
        - Model: fast
        - Task: Parse full AST → STRANGLER_DISCOVERY_CACHE.json
        - Duration: ~2-3 min
    Stage 2 (parallel):
      Worker 1B: Domain Boundary Detector (from cache)
        - Model: fast
        - Task: Group methods by domain
        - Duration: ~2-3 min
      Worker 1C: Complexity Metrics (from cache)
        - Model: fast
        - Task: Health score calculation
        - Duration: ~2-3 min
      Worker 1D: API Pattern Inspector (project scan)
        - Model: balanced
        - Task: Discover naming conventions, DI style, test framework
        - Duration: ~3-5 min

───────────────────────────────────────────────────────────────
📁 ARTIFACTS THAT WILL BE CREATED
───────────────────────────────────────────────────────────────

  .claude/forge-state.json              (state file — v2 schema)
  .claude/STRANGLER_DISCOVERY_CACHE.json (intermediate cache)
  .claude/STRANGLER_DISCOVERY.md         (final discovery report)
  .claude/STRANGLER_API_PATTERNS.md      (discovered project conventions)
  logs/forge.log                         (execution log)

───────────────────────────────────────────────────────────────
💰 COST ESTIMATE
───────────────────────────────────────────────────────────────

  Thoroughness: {"very thorough" | "medium" (--quick)}
  Workers: 4 total (1 sequential + 3 parallel)
  Token estimate: ~500-830 tokens (model-aware: all Sonnet)
  Duration estimate: ~6-8 min (Stage 1: 2-3 min + Stage 2: 3-5 min)

───────────────────────────────────────────────────────────────
⚠️  POTENTIAL ISSUES
───────────────────────────────────────────────────────────────

  {IF lines < 500:}
  ⚠️  File has {lines} lines — may not benefit from strangler pattern.
     Consider simpler refactoring (extract method, move class).

  {IF no @Autowired and no constructor params:}
  ⚠️  No dependency injection detected — service boundaries may be unclear.

  {IF no REST annotations (@GetMapping, @PostMapping, etc.):}
  ⚠️  No REST endpoints detected — API pattern inspection may yield limited results.

  {IF all OK:}
  ✅ No issues detected. Discovery should proceed smoothly.

═══════════════════════════════════════════════════════════════
  ℹ️  This is a DRY RUN — no changes were made.
  ➡️  Remove --dry-run to execute: /strangler-discover {TARGET_FILE} {FLAGS}
═══════════════════════════════════════════════════════════════
```

**After dry-run output: STOP.** Do not proceed to Step 6.

---

## Step 6: Delegate to Orchestrator

Spawn the orchestrator via Task tool:

```
Subagent type: general-purpose
Prompt:
---
You are the Strangler Orchestrator. You coordinate all phases of the strangler pattern refactoring workflow.

**Context:**
- Target file: {TARGET_FILE}
- JIRA ID: {JIRA_ID}
- Thoroughness: {"very thorough" if not "--quick" else "medium"}
- Log file: logs/forge.log
- State file: .claude/forge-state.json

**Task:**
1. Read state file if exists, resume from last phase
2. Run Phase 0 (analysis): Validate target, calculate initial metrics
3. Run Phase 1 (discovery): Spawn 3 parallel explore agents to analyze structure, boundaries, complexity
4. Read and aggregate discovery results
5. Update state file with completion
6. Report findings and next step
7. Do not proceed to Phase 2 (analysis) — that's a separate command

**Requirements:**
- Load domain-reference skill ONLY §1-2 (classification, patterns)
- Report token usage and execution time
- Save STRANGLER_DISCOVERY.md artifact
- Log [COMPLETE] to forge.log when done

**Constraints:**
- Execute ONLY what is listed above
- NOTHING ELSE
```

---

## Output

Log completion and report next step to user.
