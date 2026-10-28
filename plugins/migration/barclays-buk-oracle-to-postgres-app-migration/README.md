# Oracle-to-PostgreSQL Application Migration Plugin

FORGE-compliant plugin for migrating Spring Boot applications from Oracle to PostgreSQL database connectivity.

## What It Does

Clones a Git repository, modifies the Spring Boot application in-place (driver, dialect, properties, entities, config, tests), generates validation tests, produces audit reports, commits, pushes, and creates a GitLab Merge Request.

## Command

```bash
/oracle-to-postgres-app-migration PROJECT_PATH --jira JIRA_ID [--git-url GIT_URL] [--full-automation]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `PROJECT_PATH` | Yes | Path to project (`.` or absolute) |
| `--jira JIRA_ID` | Yes | JIRA ticket ID (e.g., COREENGDEV-1038) |
| `--git-url GIT_URL` | No | Git SSH URL to clone fresh |
| `--full-automation` | No | Enable enforced automation mode |

## Architecture

```
┌─ COMMAND LAYER (thin)
│  /oracle-to-postgres-app-migration  ──►  orchestrator-agent
│
├─ ORCHESTRATOR LAYER (hub)
│  ┌─ oracle-to-postgres-app-orchestrator-agent
│  │  State: .claude/oracle-to-postgres-app-state.json
│  │  Log:   logs/oracle-to-postgres-app.log
│  │
│  │  Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Quality Gate
│  │
│  ├─ WORKER LAYER (spokes)
│  │  oracle-to-postgres-app-worker-agent
│  │    Phase: dependencies | properties | entities | config | tests
│  │    3-8 files per batch, disjoint domains
│  │
│  ├─ GATEKEEPER LAYER (read-only)
│  │  oracle-to-postgres-app-validation-agent
│  │  10 red flags → APPROVED or REJECTED
│  │
│  └─ PUSH LAYER (external I/O)
│     oracle-to-postgres-app-push-agent
│     Anti-hallucination protocol
│     git push + glab mr create
│
└─ SKILLS LAYER (ground truth)
   domain-reference/SKILL.md (type mappings, conversion rules, pitfalls)
   forge-patterns/SKILL.md (12 FORGE patterns reference)
```

## Phase Flow

| Phase | Name | Gate | What Happens |
|-------|------|------|--------------|
| 0 | Setup & Clone | Hard | Clone repo, create branch, init workspace |
| 1 | Baseline | Soft | Run existing tests, record pass/fail counts |
| 2 | Analysis | Hard | Detect all Oracle-specific code/config |
| 3 | Migration | Hard | Update deps, properties, entities, config, tests |
| 4 | Validation Tests | Hard | Generate PostgresMigrationValidationTest.java |
| 5 | Validate | Hard | Compile + test + fix loop (max 5 iterations) |
| 6 | Reports | Soft | Generate migration-report.md, fixes-report.md |
| Push | Commit & MR | — | Stage, commit, push, create GitLab MR |

## Quality Gate

All three conditions must pass before push:
1. All phases (0-6) completed or skipped
2. Validation agent returns APPROVED (no Oracle remnants)
3. Tests pass (or match baseline failure count)

## Validation Red Flags

1. Oracle driver remains in build.gradle
2. Oracle JDBC URL in properties
3. OracleDialect in Java code
4. Oracle imports (`import oracle.*`)
5. Oracle SQL syntax in main code
6. State file phases incomplete
7. Migration reports missing
8. Branch name missing JIRA ID
9. `insertable = false` with `@CreationTimestamp` / `@UpdateTimestamp` (pilot finding — breaks on PostgreSQL)
10. Migration report missing H2 limitation warning (pilot finding — H2 masks critical issues)

## Output

- Feature branch: `{JIRA_ID}/oracle-to-postgres-app`
- Merge Request on GitLab
- Reports in `.oracle-to-postgres/`:
  - `migration-report.md` — full summary for MR reviewers

## Key Conventions

- **Nexus**: Resolve versions from `https://nexus.barcapint.com/nexus/content/`
- **GitLab**: Source control on `app.gitlab.barcapint.com`
- **Branch**: `${JIRA_ID}/oracle-to-postgres-app`
- **Commit**: `${JIRA_ID} | Oracle to Postgres app migration by oracle-to-postgres-app-migration plugin`
- **CRITICAL**: Always append `?currentSchema={SCHEMA}` to PostgreSQL JDBC URLs

## FORGE Compliance

This plugin implements all 12 FORGE patterns:
- Pattern 1: Thin command (parse/validate/delegate only)
- Pattern 2: Orchestrator-worker hierarchy
- Pattern 3: Phase-gated execution with hard/soft gates
- Pattern 4: Stateful resumption via JSON state file
- Pattern 5: Parallel batching for Phase 3 sub-tasks
- Pattern 6: Autonomous decision-making (7-rule framework)
- Pattern 7: Read-only validation agent (10 red flags — 8 baseline + 2 pilot-informed)
- Pattern 8: Dedicated push agent with anti-hallucination
- Pattern 9: Scope enforcement in every agent
- Pattern 10: Reference-doc-driven (domain-reference skill)
- Pattern 11: Structured logging with real timestamps
- Pattern 12: Task-based progress tracking

## Pilot Summary

### mca-eps-selfservice-locator (COREENGDEV-1038)

- **Date:** 2026-06-19
- **Complexity:** Low (2 entities, 1 config class, 12 Oracle references in 8 files)
- **Result:** Migration completed — unit tests PASS, integration tests PASS, Oracle remnant scan CLEAN

**What was iterated as a result of the pilot:**

| Issue Discovered | Change Made |
|---|---|
| `@Column(insertable = false)` with `@CreationTimestamp` breaks PostgreSQL INSERT — NOT caught by H2 tests | Added explicit entity rule in worker agent; added Red Flag #9 in validation agent; added self-check item in domain-reference skill |
| H2 PostgreSQL mode masks schema routing, timestamp insertion, and constraint issues | Added mandatory ⚠️ H2 Test Limitations section to migration report template; added Red Flag #10 in validation agent |
| Spring Cloud Config Server: only DATASOURCE profile files were copied to new folder, missing DEVICES/MENU | Added analysis scan for `spring.profiles.active` and config server pattern; added flag and report checklist item |
| Post-deployment: Oracle driver still connected via config server override | Added post-deployment verification steps to report template and final summary |
| Post-deployment: Timestamp BC dates from DBA data export format | Added DBA ISO timestamp warning to report template |

**Evidence:** Full per-run notes in `skills/domain-reference/lessons_learnt/mca-eps-selfservice-locator.md`. Recurring patterns extracted to `skills/domain-reference/lessons_learnt/PATTERNS.md`.

---

**Version:** 1.0.0
**Author:** Mohan Singh (mohan.singh1@barclays.com)
