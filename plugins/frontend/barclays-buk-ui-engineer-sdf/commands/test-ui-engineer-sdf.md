---
name: test-ui-engineer-sdf
description: End-to-end test of the SDF ui-engineer agent. Resets the test project, runs the agent against a real Figma URL, and validates output — Figma MCP used, TypeScript gate passed, structural fidelity check ran, visual preview ran.
allowed-tools: Bash, Read, Glob, Grep
---

# /test-ui-engineer-sdf

Runs a full end-to-end test of the SDF ui-engineer agent against a real Figma design.

## Usage

```
/test-ui-engineer-sdf
/test-ui-engineer-sdf --project /path/to/sdf-project
/test-ui-engineer-sdf --figma-url https://www.figma.com/design/...?node-id=...
```

Defaults:
- `--project`: `/Users/$USER/code/philtest3`
- `--figma-url`: Interest Rates screen (node 5240:3126)

---

## What this does

1. **Pre-flight** — verifies Figma MCP is connected (`figma-local` in `/mcp`)
2. **Reset** — runs `reset-test-project.sh` to delete generated screens and restore clean routes/interface
3. **Run agent** — invokes `ui-engineer-sdf-worker-agent` with `TASK_TYPE=screen-composer`
4. **Validate output** — checks all of:
   - `mcpDataUsed: true` in batch result (Figma MCP was actually called)
   - No `curl` to port 3845 in agent logs (no MCP curl bypass)
   - TypeScript gate exit code 0 (or correctly blocked on pre-existing errors)
   - `structural fidelity check complete` in logs (Step 5.8 ran)
   - `visual preview` in flags (Step 5.9 ran or was skipped with reason)
   - Generated screen file exists at expected path
   - Screen file uses `VanillaLayout` root (Iron Rule 1)
   - No hardcoded hex/rgb values in generated file

5. **Report** — pass/fail per check with evidence

---

## Steps

### 1. Parse args

```bash
PROJECT_PATH="${PROJECT_PATH:-/Users/$USER/code/philtest3}"
FIGMA_URL="${FIGMA_URL:-https://www.figma.com/design/R9ESr99z6aOf3M1Xe8ZE2y/Interest-Rates-in-App---Strategic?node-id=5240-3126&m=dev}"
JIRA_ID="TEST-001"
BUK_SCRIPTS="$(dirname "$0")/../../scripts"
LOG_FILE="/tmp/test-ui-engineer-sdf.log"
```

### 2. Pre-flight checks

```bash
# Figma MCP connected?
# (Check via /mcp in this session — if figma-local shows Connected, proceed)

# Project exists?
[ -d "$PROJECT_PATH" ] || { echo "❌ PROJECT_PATH not found: $PROJECT_PATH"; exit 1; }

# Reset script exists?
[ -f "$BUK_SCRIPTS/reset-test-project.sh" ] || { echo "❌ reset-test-project.sh not found"; exit 1; }
```

Tell the user: "Figma MCP must show `figma-local ✔ Connected` in `/mcp` before this test runs. If it doesn't, run `setup-figma-mcp.sh` and restart your session."

### 3. Reset project

```bash
bash "$BUK_SCRIPTS/reset-test-project.sh" "$PROJECT_PATH"
```

Verify reset worked:
```bash
ls "$PROJECT_PATH/src/screens/" | grep -v "^start$\|^second$" | head -5
```

If any non-template screens remain: stop and report.

### 4. Run the agent

Invoke `barclays-buk-ui-engineer-sdf:ui-engineer-sdf-worker-agent` with:

```
PROJECT_PATH:  {PROJECT_PATH}
JIRA_ID:       TEST-001
FIGMA_URL:     {FIGMA_URL}
SCREENS:       none
TASK_TYPE:     screen-composer
ADDITIONAL_INPUT: none
```

Capture the full output to `{LOG_FILE}`.

### 5. Validate output

Run each check and record PASS / FAIL / SKIP with evidence:

| # | Check | How to verify |
|---|---|---|
| 1 | Figma MCP used | `mcpDataUsed: true` in batch result JSON |
| 2 | No curl bypass | `grep "curl.*3845" {LOG_FILE}` returns nothing |
| 3 | Screen file created | `ls {PROJECT_PATH}/src/screens/*/InterestRatesScreen.tsx` |
| 4 | VanillaLayout root | `grep "VanillaLayout" {screen_file}` |
| 5 | No hardcoded colours | `grep -E "#[0-9a-fA-F]{3,6}\|rgb(" {screen_file}` returns nothing |
| 6 | TypeScript gate ran | `grep "tsc gate\|TypeScript gate" {LOG_FILE}` |
| 7 | Structural fidelity ran | `grep "structural fidelity check complete" {LOG_FILE}` |
| 8 | Visual preview ran or skipped with reason | `grep "visual preview\|agent-device" {LOG_FILE}` |
| 9 | No fallback heuristics | `mcpDataUsed: true` and no "fallback heuristics" in flags |

### 6. Report

```
/test-ui-engineer-sdf results
══════════════════════════════════

Project:   {PROJECT_PATH}
Figma URL: {FIGMA_URL}
Status:    PASS ({N}/9) | FAIL ({M} failures)

Checks:
  ✅ 1. Figma MCP used         — mcpDataUsed: true
  ✅ 2. No curl bypass          — no matches for curl.*3845
  ✅ 3. Screen file created     — src/screens/interestRates/InterestRatesScreen.tsx
  ✅ 4. VanillaLayout root      — found on line {N}
  ✅ 5. No hardcoded colours    — clean
  ✅ 6. TypeScript gate ran     — exit 0
  ❌ 7. Structural fidelity ran — not found in logs
  ⚠️  8. Visual preview         — skipped: NO_SIMULATOR
  ✅ 9. No fallback heuristics  — clean

Failures:
  7. Structural fidelity check did not run — Step 5.8 missing from agent output.
     Likely cause: routing table in ui-engineer-sdf-worker-agent.md does not
     include Step 5.8 for TASK_TYPE=screen-composer.
     Fix: update Step 1 routing to include Steps 5.7, 5.8, 5.9.
```

Any FAIL is a blocker — do not mark the test as passing until all 9 checks pass (or check 8 has a documented skip reason).
