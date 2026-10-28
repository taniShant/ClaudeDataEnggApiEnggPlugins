---
name: converge
description: Find and reconcile specification↔code divergences. Classifies each divergence by source of truth (spec/code/unknown) and writes persistent state to .convergence.yaml.
agent: reverse-spec-generator-agent
allowed-tools: Read, Glob, Grep
---

# Converge

Find and reconcile divergences between behavioral specifications and code implementations.

## Options

| Option | Type | Required | Default | Description |
|--------|------|----------|---------|-------------|
| `spec_file` | path | yes | — | Path to .spec file to check convergence |
| `source_files` | path(s) | no | auto-detect | Source file(s) to compare against spec |
| `--behavior` | string | no | all | Filter to specific behavior name |
| `--source-of-truth` | enum | no | auto | Force source of truth: `spec`, `code`, or `unknown` |
| `--output` | path | no | `.convergence.yaml` | Path to write convergence state |

## Overview

After creating specifications with `/generate-spec` and refining them with `/amend`, use this command to:

- **Verify code matches spec** - Check that implementation follows the specification
- **Detect spec drift** - Find places where code has changed but spec hasn't
- **Identify issues** - Spot inconsistencies or violations
- **Guide fixes** - Report what needs to change (spec or code)
- **Maintain alignment** - Keep specs and code synchronized over time

## How It Works

1. You provide a `.spec` file
2. The tool scans source code for implementation
3. Each behavior, rule, and constraint is checked
4. Divergences are reported with specifics
5. Recommendations are provided to fix issues

## Divergence Types

### Type 1: Missing Implementation

The spec describes a behavior that isn't in the code.

**Example:**
```yaml
behaviors:
  - name: "rate_limit_enforcement"
    description: "API requests are rate-limited to 100 per minute per user"
    # ... spec details
```

**Report:**
```
MISSING: behavior 'rate_limit_enforcement'
  - Spec says: API requests are rate-limited to 100 per minute per user
  - Code: No rate limiting logic found
  - Action: Implement rate limiting or update spec
```

**Fix options:**
1. Implement the behavior in code
2. Remove from spec if it's not a requirement
3. Document as planned for future release

### Type 2: Code Doesn't Implement Spec

The spec and code both exist, but behavior is different.

**Example:**
```yaml
rules:
  - name: "inactive_user_cannot_login"
    condition: "when user status is inactive"
    action: "then deny login with 403 Forbidden"
```

**Code:**
```python
if user.status == "inactive":
    return {"message": "User not active"}  # Wrong! Should be 403 Forbidden
```

**Report:**
```
DIVERGENCE: rule 'inactive_user_cannot_login'
  - Spec says: return 403 Forbidden
  - Code returns: 200 OK with message
  - Action: Fix code to match spec or update spec
```

### Type 3: Missing Constraint

Code enforces a constraint that isn't documented in spec.

### Type 4: Spec Too Generic

Code behavior is more specific than spec describes.

## Usage

### Check Entire Module

```
/converge
# Spec file: user_service.spec
```

### Check Specific Behavior

```
/converge
# Spec file: user_service.spec
# Behavior: authenticate_user
```

### Check Against Multiple Files

```
/converge
# Spec file: user_service.spec
# Source files: src/auth.py src/user.py src/permissions.py
```

## Convergence Report

```
════════════════════════════════════════════════════════════
  Convergence Report: a-digi-msg-data-mgt.spec
════════════════════════════════════════════════════════════

  Status: 72.7% converged  (iteration 3)
  16 aligned · 2 diverged · 1 missing impl · 3 missing spec

  3 issue(s) found:

  [BEHAVIORS]

  ✗ delete_event_log  [HIGH]
    type   : diverged
    truth  : unknown  (ambiguous → human decision needed)
    detail : XOR guard present in spec, code accepts both params
    action : Review: update code to match spec (if source_of_truth=spec)
             or /amend spec (if source_of_truth=code)

  ✗ get_steps  [HIGH]
    type   : missing_impl
    truth  : spec  (spec leads → update code)
    detail : Behavior defined in spec; no matching implementation found
    action : Implement the behavior in code, or remove from spec

  [RULES]

  ? event_log_delete_scope_xor  [MEDIUM]
    type   : missing_spec
    truth  : code  (code leads → update spec)
    detail : Rule enforced in code; not documented in spec
    action : Add this to the spec via /amend
```

---

## Divergence Classification

Every divergence carries a `source_of_truth` field that drives the correct fix action:

| source_of_truth | Meaning | Fix action |
|---|---|---|
| `spec` | Spec states intent; code must catch up | Implement or fix the code |
| `code` | Code is authoritative; spec is stale | Run `/amend` to update the spec |
| `unknown` | Ambiguous — both exist, differ | Human decision required |

### Source of Truth Heuristic

| Divergence type | Default source_of_truth | Rationale |
|---|---|---|
| `missing_impl` | `spec` | You stated intent in the spec; code hasn't caught up |
| `missing_spec` | `code` | Code did it before the spec was written |
| `diverged` | `unknown` | Both exist and differ — needs judgment |
| `under_spec` | `code` | Code evolved beyond what spec describes |

**Overrides:** If `/amend` was used to modify a behavior after initial extraction, that behavior is automatically marked `source_of_truth: spec` in `.convergence.yaml`. `/converge` honours this override and will not reclassify it.

---

## Convergence State File

Each `/converge` run writes a `.convergence.yaml` alongside the `.spec` file. This is the loop's persistent memory.

**Location:** same directory as the spec, named `<module>.convergence.yaml`

**Contents:**
```yaml
version: "1.0"
spec_file: "a-digi-msg-data-mgt.spec"
module: "a_digi_msg_data_mgt"
last_run: "2026-07-12T14:30:00Z"
iteration_count: 3
convergence_pct: 72.7

summary:
  total_items: 22
  aligned: 16
  diverged: 2
  missing_impl: 1
  missing_spec: 3
  unknown: 0

behaviors:
  get_messages:
    source_of_truth: "code"
    test_status: "passing"
    divergence_status: "aligned"
    last_verified: "2026-07-12"
  delete_event_log:
    source_of_truth: "unknown"
    test_status: "failing"
    divergence_status: "diverged"
    notes: "XOR guard differs between spec and code"
```

**Do not edit this file manually** — use `/amend` to set `source_of_truth` overrides.

---

## Loop Integration

`/converge` is the verify step in the self-verification loop:

```
/generate-spec → /generate-tests → /run-tests → /converge → decision
                                                      │
                          source_of_truth: spec ──────┼──→ fix code → /run-tests
                          source_of_truth: code ──────┼──→ /amend spec
                          source_of_truth: unknown ───┴──→ human review
```

Run `/status` after `/converge` to see overall loop progress and the recommended next action.
