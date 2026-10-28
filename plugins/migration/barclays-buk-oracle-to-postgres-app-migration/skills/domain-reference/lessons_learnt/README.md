# Lessons Learnt — Oracle-to-PostgreSQL Application Migration

## Purpose

This directory captures lessons learned from each migration run. These lessons feed back into the decision-making process — agents consult PATTERNS.md when encountering familiar scenarios.

## Structure

| File | Purpose |
|------|---------|
| `README.md` | This file — structure documentation |
| `PATTERNS.md` | Auto-maintained recurring patterns across all runs |
| `{project-name}.md` | Per-run notes (created at Phase 0, updated each phase) |

## When to Create/Update

- **Phase 0:** Orchestrator creates `{project-name}.md` with project metadata
- **After each phase:** Orchestrator appends phase results and any non-obvious decisions
- **After Phase 5 (Validate):** Record all fixes applied and their root causes
- **After completion:** Orchestrator updates `PATTERNS.md` with new recurring issues

## Entry Format (per-run file)

```markdown
# {Project Name} — Oracle-to-PostgreSQL Migration

**Date:** YYYY-MM-DD
**JIRA:** {JIRA_ID}
**Complexity:** Low/Medium/High
**Oracle References Found:** N in M files

## Phases

### Phase 3: Migration
- {Notable decisions or issues}

### Phase 5: Validate
- **Fix 1:** {Error} → {Root cause} → {Fix applied}

## Lessons
- {Key takeaway for future runs}
```

## PATTERNS.md Format

```markdown
## Pattern: {Short name}
- **Frequency:** N times across M runs
- **Trigger:** {When this occurs}
- **Resolution:** {What to do}
- **Example:** {Project where this was encountered}
```
