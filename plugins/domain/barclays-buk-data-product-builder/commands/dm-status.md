---
description: Display data model agent outputs and what to run next
disable-model-invocation: false
---

# /dm-status

Display the current state of data model development artefacts and suggest the next command to run.

## Usage

```
/dm-status
```

## Behaviour

### Step 1: Scan for Outputs

Check for `dm-output/` directory:
- If `dm-output/` does not exist → report: `"No data model outputs found. Start with /dm-bra to produce a business requirement."`
- If exists → list all subdirectories (each represents a reference/project)

### Step 2: Read Tracking State

For each reference directory found:

1. Check for `dm-session/tracking.json`
   - If exists → read and parse
   - If not → reconstruct state from file presence

2. Check file existence:
   - `dm-output/<ref>/business-requirement.md` → BRA output exists?
   - `dm-output/<ref>/data-model.md` → DM output exists?
   - `dm-output/<ref>/context/` → JIRA context saved?

### Step 3: Display Status

For each reference, display:

```markdown
## Data Model Status: <ref>

| Artefact | Status | Path |
|----------|--------|------|
| Business Requirement | ✅ Produced / ❌ Missing | dm-output/<ref>/business-requirement.md |
| Data Model | ✅ Produced / ❌ Missing | dm-output/<ref>/data-model.md |
| BRA Validation | ✅ APPROVED / ❌ REJECTED / ⏳ Not run | — |
| DM Validation | ✅ APPROVED / ❌ REJECTED / ⏳ Not run | — |
| JIRA Context | ✅ Saved / — N/A | dm-output/<ref>/context/ |

### Commands Run
| # | Command | Timestamp | Status |
|---|---------|-----------|--------|
| 1 | /dm-bra | 2026-09-09T10:30:00Z | success |
| 2 | /dm-model | 2026-09-09T11:00:00Z | success |
```

### Step 4: Suggest Next Step

Based on what's missing, suggest the logical next command:

| Current State | Suggestion |
|---------------|------------|
| No outputs at all | `→ Start: /dm-bra "your business ask" or /dm-bra <JIRA-REF>` |
| BRA exists, no DM | `→ Next: /dm-model dm-output/<ref>/business-requirement.md` |
| BRA exists, DM exists, no BRA validation | `→ Next: /dm-validate dm-output/<ref>/business-requirement.md --type bra` |
| BRA exists, DM exists, no DM validation | `→ Next: /dm-validate dm-output/<ref>/data-model.md --type dm` |
| BRA REJECTED | `→ Action: Fix issues and re-run /dm-bra` |
| DM REJECTED | `→ Action: Fix issues and re-run /dm-model` |
| All APPROVED | `✅ All artefacts produced and validated.` |

---

## Isolation

- Read-only — does not modify any files
- Reads from `dm-output/` and `dm-session/` only
- Never touches `generated/`, `session/`, or any existing plugin state
