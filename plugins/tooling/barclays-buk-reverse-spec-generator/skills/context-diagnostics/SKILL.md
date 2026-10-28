---
name: context-diagnostics
description: >
    Context consumption and token budget diagnostics for reverse-spec-generator.
    Provides phase-by-phase token estimation, budget dashboards, and optimization
    hints. Activated by --diagnostics flag. Informational only — does not change
    functional behavior.
user-invocable: false
---

# Context Diagnostics

> **Source:** Reverse Spec Generator — Observability Design (internal)
> **Owner:** Preetha Ramaswamy / BUK Quality Engineering
> **Review trigger:** When plugin skill sizes change significantly or token heuristic needs recalibration
> **Status:** Active

---

## Quick Start

```
Command: Any (activated by --diagnostics flag)
Agent: reverse-spec-generator-agent or status-agent
Load: Loaded when --diagnostics flag is passed to any command
Use: Token budget estimation, phase-by-phase context consumption, optimization hints
Model: N/A (informational overlay, not generation)
```

---

## 1. Activation

Emit diagnostics when the user's prompt contains `--diagnostics` or the word "diagnostics".

- If `--diagnostics` is absent, produce **no** diagnostic output (zero overhead).
- If both `--trace` and `--diagnostics` are present, emit both: trace markers (`[ctx:in]`/`[ctx:out]`) interleaved with diagnostics dashboards at phase boundaries.
- Diagnostics are **informational only** — they do not change the agent's functional behavior or outputs.

---

## 2. Token Estimation Heuristic

The agent cannot access the tokenizer directly. Use this approximation:

```
estimated_tokens = lines × 10
```

Rationale: average code/prose line is ~40 characters; Claude tokenises at ~4 characters/token → ~10 tokens/line.

**Rules:**
- Label every estimate with `~` prefix (e.g., `~1,900 tokens`)
- Include a footer note: `Heuristic: ~10 tokens/line. Actual tokenisation varies by content.`
- For files read via the Read tool, use the line count from the tool result
- For bulk scanning, use `find <path> -name "*.ext" | xargs wc -l` via Bash to get line counts efficiently

---

## 3. Phase 1: PLUGIN OVERHEAD

Emit **immediately** after loading skills (Step 1 in the agent workflow), before any user files are read.

**Pre-computed sizes** (update when plugin files change significantly):

| Component | Lines | Est. Tokens |
|---|---|---|
| agent system prompt | 179 | ~1,900 |
| skill: bdd-specification | 186 | ~1,740 |
| skill: spec-generation-patterns | 254 | ~1,970 |
| skill: convergence-loop | 255 | ~2,460 |
| command definition (generate-spec) | 242 | ~1,960 |
| **Plugin overhead total** | **1,116** | **~10,030** |

**Output template:**

```
╔═ CONTEXT DIAGNOSTICS ════════════════════════════════════════════╗
║ Phase 1: PLUGIN OVERHEAD                                         ║
║                                                                  ║
║  Component                          Lines    Est. Tokens         ║
║  agent system prompt                  179       ~1,900           ║
║  skill: bdd-specification             186       ~1,740           ║
║  skill: spec-generation-patterns      254       ~1,970           ║
║  skill: convergence-loop              255       ~2,460           ║
║  command: generate-spec               242       ~1,960           ║
║                                     ─────     ────────           ║
║  Plugin overhead total:             1,116      ~10,030           ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## 4. Phase 2: SOURCE SCAN

Emit **after** globbing/discovering source files and counting lines, before extraction begins.

**Procedure:**
1. Glob SOURCE_PATH for files matching the detected language extension
2. Count total files found
3. Get line counts per file (use Bash `wc -l` for efficiency on directories with >5 files)
4. Sort files by line count descending
5. Compute running total = plugin overhead + source tokens

**Output template:**

```
╔═ CONTEXT DIAGNOSTICS ════════════════════════════════════════════╗
║ Phase 2: SOURCE SCAN                                             ║
║                                                                  ║
║  Path:  <SOURCE_PATH>                                            ║
║  Files: <count> (.<ext>)                                         ║
║  Lines: <total_lines>                                            ║
║  Est. tokens: ~<total_lines × 10>                                ║
║                                                                  ║
║  Top 5 largest:                                                  ║
║    <filename>  <lines> lines  ~<tokens> tok                      ║
║    <filename>  <lines> lines  ~<tokens> tok                      ║
║    <filename>  <lines> lines  ~<tokens> tok                      ║
║    <filename>  <lines> lines  ~<tokens> tok                      ║
║    <filename>  <lines> lines  ~<tokens> tok                      ║
║                                                                  ║
║  Running total: ~<overhead + source> tokens                      ║
║                                                                  ║
║  <optimization hints if any — see Section 7>                     ║
╚══════════════════════════════════════════════════════════════════╝
```

If fewer than 5 files, show all. If only 1 file, omit the "Top 5" section.

---

## 5. Phase 3: EXTRACTION SUMMARY

Emit **after** extraction is complete, before writing the .spec file.

**Output template:**

```
╔═ CONTEXT DIAGNOSTICS ════════════════════════════════════════════╗
║ Phase 3: EXTRACTION                                              ║
║                                                                  ║
║  Entities: <n> | Behaviors: <n> | Rules: <n> | Constraints: <n>  ║
║  Source utilization: <total_items> items from <lines> lines       ║
║                      (<percentage>% density)                      ║
╚══════════════════════════════════════════════════════════════════╝
```

Density = `(total_items / total_source_lines) × 100`, rounded to 1 decimal place.

---

## 6. Phase 4: FINAL SUMMARY

Emit **after** the .spec file is written and validated.

**Output template:**

```
╔═ CONTEXT DIAGNOSTICS ════════════════════════════════════════════╗
║ Phase 4: FINAL SUMMARY                                           ║
║                                                                  ║
║  Input consumed:                                                 ║
║    Plugin overhead:    ~<overhead_tokens> tokens                  ║
║    Source files:       ~<source_tokens> tokens                    ║
║    State file:         ~<state_tokens> tokens (<detail>)          ║
║    TOTAL INPUT:        ~<total_tokens> tokens                    ║
║                                                                  ║
║  Output produced:                                                ║
║    <module>.spec: <lines> lines (~<tokens> tokens)               ║
║                                                                  ║
║  Ratio: <ratio>:1 (input:output)                                 ║
║                                                                  ║
║  <status line — see below>                                       ║
║  <optimization warnings if any — see Section 7>                  ║
║                                                                  ║
║  Heuristic: ~10 tokens/line. Actual tokenisation varies.         ║
╚══════════════════════════════════════════════════════════════════╝
```

**Status line logic:**
- Total < 50,000 tokens → `Status: ✓ Within typical budget`
- Total 50,000–100,000 tokens → `Status: ⚡ Moderate — extraction quality may decrease for later files`
- Total > 100,000 tokens → `Status: ⚠ HIGH — model context window likely truncating source material`

**State file detail:**
- No `.convergence.yaml` → `(none — first run)`
- Exists → `(iteration <n>, <pct>% converged)`

---

## 7. Optimization Hints

Emit hints inline within the relevant phase dashboard when thresholds are exceeded:

| Condition | Phase | Hint Text |
|---|---|---|
| Source directory has > 20 files | 2 | `⚠ HINT: <n> files found. Consider narrowing to a subdirectory or single module.` |
| Total source lines > 5,000 | 2 | `⚠ HINT: <n> lines exceeds 5,000-line threshold. Consider splitting into multiple /generate-spec runs.` |
| Any single file > 1,000 lines | 2 | `⚠ HINT: <filename> is <n> lines. Large files reduce extraction quality — consider splitting.` |
| Total context > 50,000 tokens | 4 | `⚠ NOTE: Approaching model context limits. Later source files may receive less attention.` |
| Total context > 100,000 tokens | 4 | `⚠ WARNING: Likely exceeds effective context window. Results may be incomplete. Narrow scope.` |
| Spec output > 500 lines | 4 | `⚠ HINT: Generated spec is <n> lines. Consider splitting by entity or subdomain.` |
| Input:output ratio > 100:1 | 4 | `⚠ HINT: High ratio (<n>:1). Most source material did not contribute to spec. Check confidence threshold.` |

---

## 8. Output Format Rules

- Use double-line box-drawing characters (`╔ ╗ ╚ ╝ ║ ═`) for diagnostics dashboards
- This distinguishes them from trace output (which uses single-line `┌ ┐ └ ┘ │ ─`)
- Left-align text within the box with 2-space indent
- Right-align numeric columns
- Truncate filenames longer than 40 characters with `...` prefix
- Print each dashboard as a single uninterrupted block (no interleaved tool calls)

---

## 9. Composability with --trace

When both `--trace` and `--diagnostics` are active:

1. Phase 1 dashboard prints after the initial `[ctx:in]` skill-loading trace lines
2. Phase 2 dashboard prints after the source file `[ctx:in]` trace lines
3. Phase 3 dashboard prints after extraction (no trace lines at this point)
4. Phase 4 dashboard prints after the `[ctx:out]` write trace lines

When only `--diagnostics` is active:
- No `[ctx:in]`/`[ctx:out]`/`[ctx:hook]` markers appear
- Only the 4 phase dashboards are printed

---

## 10. Agent Self-Check

Before finishing, verify:

- [ ] Phase 1 was emitted immediately after skill loading
- [ ] Phase 2 was emitted after source scan, before extraction
- [ ] Phase 3 was emitted after extraction, before writing .spec
- [ ] Phase 4 was emitted after .spec file was written
- [ ] All token estimates use `~` prefix
- [ ] Running totals are cumulative (each phase includes prior phases)
- [ ] Optimization hints were evaluated against Section 7 thresholds
- [ ] Footer heuristic note is present in Phase 4
- [ ] Diagnostics did NOT change the functional output (same .spec regardless of flag)
