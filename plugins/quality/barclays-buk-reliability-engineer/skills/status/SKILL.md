---
name: status
description: >
    Reads .reliability/ state files and reports current observability phase, migration progress,
    and suggested next steps. Makes no changes to the repository.
user-invocable: false
owner: BUK Retail CAPL
review-trigger: When the .reliability/ state file schema changes
---

# Status — Observability Phase and Migration Progress

Read-only. Reports the current observability maturity without running tests or making changes.

---

## Inputs

```
CODE_PATH:  /absolute/path/to/service   (default: current working directory)
```

---

## Output

Console output only — no files created or modified.

---

## Step 1: Read state files

Read the following files if they exist:

1. `.reliability/observability-target.md` — agreed schema, strategy, stack, and phase decisions
2. `.reliability/state.yaml` — per-migration implementation status
3. `.reliability/changelog/` — list of migration files to cross-reference names and descriptions

If none exist, report: "No reliability state found — this service has not had an observability session yet."

---

## Step 2: Determine current phase

Using the state files, determine:
- Which migrations are `implemented` vs `pending`
- Which observability phase the service is currently in (logging / tracing / metrics)
- What remains to complete the current phase

Phase gate (from `barclays-buk-standards:observability`):
- **Logging phase complete** requires migrations 001–005 all `implemented`
- **Tracing phase** begins after logging is complete
- **Metrics phase** begins after tracing is complete

---

## Step 3: Produce status report

```markdown
# Observability Status — [service name or "this service"]

**Current phase:** [Logging | Tracing | Metrics | Not started]
**Phase status:** [Not started | In progress (N/M migrations complete) | Complete]
**Schema:** [from observability-target.md, or "not set"]
**Stack:** [from observability-target.md, or "not detected"]

---

## Migration Progress

| Migration | Title | Status | Implemented |
|-----------|-------|--------|-------------|
| 001 | Structured logging | ✅ Complete / ⏳ Pending / ➖ Not planned | [date or —] |
| 002 | Correlation IDs | ... | |
| 003 | Collector-ready | ... | |
| 004 | Sensitive data guard | ... | |
| 005 | Capability attestation | ... | |
| [NNN] | [title from changelog] | ... | |

---

## Suggested Next Steps

[3–5 numbered options based on current state — never require a specific path]
```

---

## Flags

State any of the following that apply (or "None identified"):

**Missing or ambiguous inputs:**
- No `.reliability/observability-target.md` found — phase and schema information unavailable
- No `.reliability/state.yaml` found — no migration history recorded
- CODE_PATH not provided — scanned current working directory

---

## Agent Self-Check

- [ ] All three state file locations checked (target, state.yaml, changelog/)
- [ ] Current phase determined from migration completion status
- [ ] Migration table populated from state.yaml cross-referenced with changelog/ filenames
- [ ] No files written — status is read-only
