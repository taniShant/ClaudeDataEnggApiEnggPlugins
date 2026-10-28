# Plugin Test Report

**Plugin:** barclays-buk-oracle-to-postgres-app-migration
**Version:** 1.0.0
**Author:** Mohan Singh <mohan.singh1@barclays.com>
**Path:** buk/plugins/migration/barclays-buk-oracle-to-postgres-app-migration
**Date:** 2026-09-24

---

## STRUCTURE TESTS (40 pts)

| Check | Result | Points |
|-------|--------|--------|
| Manifest valid JSON (plugin.json) | ✅ Parses cleanly, all required fields present (name, description, version, author, dependencies) | +15 |
| All referenced files exist | ✅ 5 agent files, 1 command file, 2 skill SKILL.md files, 3 lessons_learnt support files, README.md | +15 |
| Naming conventions | ✅ Agent files: lowercase-hyphens ✓ · Command files: lowercase-hyphens ✓ · Skill files: SKILL.md (uppercase) ✓ | +10 |

**Score: 40/40**

---

## CONTENT TESTS (40 pts)

| Check | Result | Points |
|-------|--------|--------|
| Agent frontmatter complete (name, description, model, tools, capabilities) | ✅ All 5 agents have: name, description, model, tools, owner, capabilities. 4/5 agents have skills references. | +10 |
| Agent capabilities present | ✅ auto-decision-agent: 5 · orchestrator-agent: 7 · push-agent: 6 · validation-agent: 8 · worker-agent: 6 | +5 |
| Agent body size | ⚠️ auto-decision-agent: 125 lines (UNDER 200 min) · orchestrator-agent: 924 lines (OVER 400 max) · push-agent: 258 ✓ · validation-agent: 262 ✓ · worker-agent: 291 ✓ | +3 |
| Skill Quick Start / reference section present | ✅ domain-reference: Overview + Agent Self-Check ✓ · forge-patterns: Quick Reference + Agent Self-Check ✓ | +10 |
| Skill name valid (< 64 chars) | ✅ domain-reference: 16 chars ✓ · forge-patterns: 14 chars ✓ | +5 |
| Command has options table + example output | ✅ Options table with 8 rows ✓ · Usage examples ✓ · Error message templates ✓ · allowed-tools declared ✓ | +5 |
| Agent description < 1024 chars | ✅ All 5 agents under limit ✓ | — |

**Score: 38/40** (−2: 2 agents outside 200–400 line range)

---

## SCHEMA COMPLIANCE (10 pts)

| Check | Result | Points |
|-------|--------|--------|
| commands field structure valid | ✅ Frontmatter: description, argument-hint, allowed-tools all present | +3 |
| agents field structure valid | ✅ All agents: name, description, model, tools, capabilities present in frontmatter | +3 |
| hooks.json | ⚠️ No hooks.json file (hooks defined inline in command for --full-automation mode) | +1 |
| author field valid | ✅ name: Mohan Singh · email: mohan.singh1@barclays.com | +2 |

**Score: 9/10** (−1: hooks not in separate file)

---

## BUK COMPLIANCE (10 pts)

| Check | Result | Points |
|-------|--------|--------|
| barclays-buk- prefix | ✅ Plugin name: barclays-buk-oracle-to-postgres-app-migration | +2 |
| barclays-buk-standards dependency | ✅ dependencies: ["barclays-buk-standards"] | +3 |
| Skills: frontmatter complete | ✅ Both skills have name, description, user-invocable fields | +2 |
| Source attribution header | ✅ domain-reference: MCA Core Engineering — Oracle-to-PostgreSQL Migration Runbook · forge-patterns: FORGE Standard v1.0 — BUK CIO Marketplace | +2 |
| Self-check checklist | ✅ domain-reference: 17 checklist items · forge-patterns: 12 checklist items | +1 |

**Score: 10/10**

---

## Quality Score: 97/100

## Status: PRODUCTION READY ✅

---

## Detailed Findings

### ⚠️ MINOR: auto-decision-agent body is 125 lines (below 200 minimum)

- **File:** `agents/auto-decision-agent.md`
- **Impact:** Agent may lack sufficient instruction depth
- **Fix:** Consider expanding decision scenarios or adding more common migration edge cases

### ⚠️ MINOR: orchestrator-agent body is 924 lines (above 400 maximum)

- **File:** `agents/oracle-to-postgres-app-orchestrator-agent.md`
- **Impact:** Very large agent — may hit context limits in smaller models; increases token cost per invocation
- **Fix:** Consider extracting Phase 3 sub-phase details into a separate skill or reference document

### ⚠️ MINOR: No standalone hooks.json file

- **File:** (missing)
- **Impact:** Automation hooks are defined inline in the command file, which works but doesn't follow the separate hooks.json convention
- **Fix:** Consider extracting hooks to a hooks.json file

---

## Strengths

- ✅ Excellent domain-reference skill with comprehensive Oracle→PostgreSQL conversion tables
- ✅ Pilot-informed red flags (#9 insertable=false, #10 H2 limitations) show real-world iteration
- ✅ Lessons learnt directory with per-run notes and recurring patterns — exemplary knowledge capture
- ✅ All 12 FORGE patterns implemented and documented
- ✅ Anti-hallucination protocol in push agent
- ✅ 10 validation red flags (exceeds minimum 5)
- ✅ Scope boundary blocks in every agent
- ✅ Principles compliance notes in every agent
- ✅ Command has full error message templates
- ✅ README.md is comprehensive with architecture diagram, phase table, pilot summary, and FORGE compliance checklist
