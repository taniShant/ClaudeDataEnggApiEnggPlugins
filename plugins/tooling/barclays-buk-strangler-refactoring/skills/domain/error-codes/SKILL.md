---
name: error-codes
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Error Codes — Structured Error Catalog (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** When new error categories are added to the extraction pipeline
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: All (cross-cutting)
Worker: Any agent that encounters an error
Load: referenced inline by all agents for structured error reporting
Use: Log errors as STR-{PHASE}{SEVERITY}{NUMBER} with message and fix
Model: N/A (reference lookup, not generation)
```

# Error Codes — Strangler Refactoring Pipeline

> **Purpose:** Structured error catalog for programmatic error handling. Format: `STR-{PHASE}{SEVERITY}{NUMBER}`

---

## §1 — Error Format

```
STR-{PHASE}{SEVERITY}{NUMBER}

PHASE: 0-8 (pipeline phase) or X (cross-cutting)
SEVERITY: F = Fatal (stops pipeline), E = Error (blocks phase), W = Warning (continues)
NUMBER: 001-999 (sequential within category)
```

---

## §2 — Phase 0-1: Discovery Errors

| Code | Severity | Message | Cause | Remediation | Retry |
|------|----------|---------|-------|-------------|-------|
| STR-0F001 | Fatal | Target file not found | Path invalid or file deleted | Verify path, re-run discover | No |
| STR-0F002 | Fatal | Target file is not source code | Extension not .java | Provide .java file | No |
| STR-0W001 | Warning | Target file under 500 lines | May not benefit from strangler | Continue (file may still be complex) | N/A |
| STR-1E001 | Error | Discovery incomplete | Worker 1A/1B/1C/1D failed | Check logs, retry discovery | Yes |
| STR-1E002 | Error | No API patterns detected | No controllers/REST endpoints found | Verify project has REST layer | Yes |
| STR-1E003 | Error | AST parse failure | Syntax errors in target file | Fix compilation errors first | No |
| STR-1W001 | Warning | No existing tests detected | Test directory empty | Tests will be generated from scratch | N/A |
| STR-1W002 | Warning | Single domain detected | May not need strangler | Consider simpler refactoring | N/A |

---

## §3 — Phase 2-3: Analysis & Planning Errors

| Code | Severity | Message | Cause | Remediation | Retry |
|------|----------|---------|-------|-------------|-------|
| STR-2E001 | Error | Analysis artifacts missing | Phase 1 not complete | Run /strangler-discover first | No |
| STR-2E002 | Error | Pattern detection failed | Code too complex or unusual | Manual planning recommended | No |
| STR-2W001 | Warning | High coupling detected | >10 inter-domain dependencies | Plan will include decoupling steps | N/A |
| STR-3E001 | Error | Plan not approved | User rejected or plan missing | Run /strangler-plan again | Yes |
| STR-3E002 | Error | Planning questions unanswered | Interactive mode, no response | Use --skip-questions for defaults | No |

---

## §4 — Phase 4-5: Task Breakdown & Spec Errors

| Code | Severity | Message | Cause | Remediation | Retry |
|------|----------|---------|-------|-------------|-------|
| STR-4E001 | Error | Task breakdown failed | Plan too vague or contradictory | Revise plan with more detail | Yes |
| STR-4W001 | Warning | Task exceeds 8 methods | Task may be too large | Consider splitting further | N/A |
| STR-GCE001 | Error | God Class Reduction Guard: BLOCKED | health_score < 40 AND total_methods_planned > 8 | Extract single small task first (≤4 methods) to improve health, or use --override-guard | No |
| STR-GCE002 | Error | Spec exceeds god service limit | Proposed service has >15 methods | Re-run `/strangler-tasks` to split this task into smaller services (≤15 methods each), then retry `/strangler-extract` on the resulting sub-tasks | No |
| STR-GCW001 | Warning | Task approaching god service threshold | Task plans >10 methods in single service | Consider splitting task; validation may reject at >15 | N/A |
| STR-GCW002 | Warning | Extraction pressure high | health_score < 60 AND total_tasks > 5 | Execute in phases — extract 1-2 tasks first, re-assess health | N/A |
| STR-5E001 | Error | Spec generation failed | Methods not found in source | Verify task method list matches source | Yes |
| STR-5E002 | Error | Spec not approved | User rejected specification | Modify spec and re-approve | Yes |
| STR-5E003 | Error | Circular dependency in spec | Service A depends on Service B depends on A | Restructure extraction order | No |
| STR-5W001 | Warning | Complex method detected | Method >50 lines, nested logic | Spec may need manual refinement | N/A |
| STR-5W002 | Warning | Shared dependency conflict | Multiple services need same bean | Will use interface injection | N/A |

---

## §5 — Phase 6-7: Test & Code Generation Errors

| Code | Severity | Message | Cause | Remediation | Retry |
|------|----------|---------|-------|-------------|-------|
| STR-6E001 | Error | Test generation failed | Spec incomplete or malformed | Fix spec, regenerate tests | Yes |
| STR-6E002 | Error | Tests don't compile | Missing imports, wrong types | Check spec DTOs and dependencies | Yes |
| STR-6E003 | Error | Coverage tool not available | JaCoCo/coverage plugin not configured in project | Add jacoco plugin to build.gradle or pom.xml | No |
| STR-6W001 | Warning | No error cases in spec | Behavior spec lacks error scenarios | Tests will be less comprehensive | N/A |
| STR-6W002 | Warning | Coverage below 90% after supplements | 2 rounds of supplementary test generation still insufficient | Manual test addition may be needed; proceed with coverage warning | N/A |
| STR-7E001 | Error | Code generation failed | Could not implement spec | Manual implementation needed | Yes (3x) |
| STR-7E002 | Error | Tests still fail after 3 retries | Generated code doesn't satisfy spec | Auto-rollback triggered | No |
| STR-7E003 | Error | Compilation failure | Generated code has syntax errors | Regenerate with fixes | Yes (3x) |
| STR-7W001 | Warning | Fidelity below 90% | Significant refactoring applied | Verify behavior equivalence via tests | N/A |

---

## §6 — Phase 8: Validation & Push Errors

| Code | Severity | Message | Cause | Remediation | Retry |
|------|----------|---------|-------|-------------|-------|
| STR-8E001 | Error | Validation REJECTED | Logic fidelity <85% or anti-patterns | Auto-rollback, review extraction | No |
| STR-8E002 | Error | Push failed | Git error, auth failure, network | Check git status, retry push | Yes |
| STR-8E003 | Error | MR creation failed | glab CLI error, auth expired | Re-authenticate, retry | Yes |
| STR-8W001 | Warning | Fidelity 85-90% | Below ideal but above threshold | Review changes manually | N/A |
| STR-8W002 | Warning | Integration tests skipped | No database or external service | Tests deferred to CI/CD | N/A |

---

## §7 — Cross-Cutting Errors

| Code | Severity | Message | Cause | Remediation | Retry |
|------|----------|---------|-------|-------------|-------|
| STR-XF001 | Fatal | State file corrupted | Invalid JSON, concurrent write | Delete state file, restart | No |
| STR-XF002 | Fatal | Git repository not found | Not in a git repo | Initialize git or cd to repo | No |
| STR-XE001 | Error | State file locked | Another process holds lock | Wait or force-unlock | Yes |
| STR-XE002 | Error | Artifact file missing | Expected file deleted externally | Re-run producing phase | Yes |
| STR-XE003 | Error | Disk space insufficient | Cannot write artifacts | Free disk space | No |
| STR-XW001 | Warning | Resuming from prior session | State file from previous run | Continuing from last checkpoint | N/A |
| STR-XW002 | Warning | Schema migration applied | State file upgraded v1→v2 | Continuing with new schema | N/A |
| STR-PE001 | Error | Parallel wave incomplete | One or more waves did not complete | Check task_states for failures | Yes |
| STR-PE002 | Error | All tasks in wave rolled back | Every task in a wave failed | Review specs and retry | No |
| STR-PW001 | Warning | No independent tasks found | All tasks have dependencies | Falling back to sequential mode | N/A |
| STR-PW002 | Warning | Monolith write lock contention | Multiple tasks queued for delegation | Tasks serialized, no data loss | N/A |

---

## §8 — Error Handling Protocol

### For Fatal Errors (F):
```
1. Log: [ERROR] {code} {message}
2. Transition state machine → FAILED
3. Report to user with remediation steps
4. STOP — do not attempt recovery
```

### For Errors (E):
```
1. Log: [ERROR] {code} {message}
2. If retry eligible: attempt retry (max per code)
3. If retry exhausted: transition → FAILED
4. Report to user
```

### For Warnings (W):
```
1. Log: [WARN] {code} {message}
2. Continue execution
3. Include in final report
```

---

## §9 — Retry Budget

| Phase | Max Retries | Backoff | Notes |
|-------|-------------|---------|-------|
| 1 (Discovery) | 2 | None | Idempotent, safe to retry |
| 5 (Spec) | 2 | None | Regeneration is cheap |
| 6 (Tests) | 2 | None | Regeneration is cheap |
| 7 (Code Gen) | 3 | None | May need different approach each retry |
| 8 (Push) | 3 | 5s linear | Network transient errors |

---

## Agent Self-Check

- [ ] Error code format matches STR-[PHASE][TYPE][CODE] pattern
- [ ] Every error code has a human-readable message and suggested fix
- [ ] No duplicate error codes across phases
- [ ] Phase-specific errors use correct phase prefix (0-8, P for parallel)
- [ ] Fatal errors trigger rollback; warnings log but continue
- [ ] All new error codes added to this catalog (no ad-hoc strings)

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
