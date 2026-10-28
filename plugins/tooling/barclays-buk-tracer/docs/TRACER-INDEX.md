# TRACER — Index

**TRACER** = Test Requirements And Coverage Evidence Registry  
**Version:** 1.0.0  
**Dependencies:** `barclays-buk-reverse-spec-generator`, `barclays-buk-standards`

---

## What TRACER Does

TRACER builds and maintains a bidirectional traceability matrix between:
- **Specs** (BDD YAML — what the system should do)
- **Test scenarios** (what is being tested)
- **Test layers** (who owns each test)
- **Test IDs** (concrete references to real tests)

It works in three flows — forward (requirements-first), reverse (code-first), and legacy change (reverse baseline → delta → forward target). These flows are mutually exclusive entry points, not a sequential pipeline.

---

## Commands

| Command | Flow | Use when |
|---------|------|---------|
| `/tracer:trace-forward` | A — Forward | Requirements exist, no code yet |
| `/tracer:trace-reverse` | B — Reverse | Code/tests exist, no specs |
| `/tracer:trace-legacy` | C — Legacy Change | Legacy code + new change request |
| `/tracer:trace-retire` | Retirement | Existing tests to analyse for retirement |
| `/tracer:trace-status` | Read-only | Check current matrix state |

---

## Agents

| Agent | Role |
|-------|------|
| `tracer-orchestrator-agent` | Flow selection, prerequisites, coordination |
| `tracer-spec-agent` | Spec generation (forward or reverse) |
| `tracer-traceability-agent` | Layer attribution, test scan, matrix build |
| `tracer-retirement-agent` | Retirement eligibility, evidence, report |

---

## Skills

| Skill | Purpose |
|-------|---------|
| `tracer_core` | 3 flows, principles, flow selection rules |
| `reverse_spec` | Adapter for `barclays-buk-reverse-spec-generator` |
| `forward_spec` | Spec generation from requirements/stories/ACs |
| `layer_registry` | Pluggable layer model, attribution rules, `layer-registry.yaml` schema |
| `traceability_matrix` | `.tracer.yaml` schema, bidirectional navigation, integrity rules |
| `test_retirement` | Retirement criteria, evidence records, keep decisions |

---

## Output Artefacts

| File | Owner | Purpose |
|------|-------|---------|
| `<module>.spec` | `barclays-buk-reverse-spec-generator` | BDD behavioural spec |
| `<module>.tracer.yaml` | TRACER | Traceability matrix state |
| `layer-registry.yaml` | Project (created once) | Layer definitions |

---

## Key Rules (Non-Negotiable)

1. **Retirement requires proof** — `retirement_status: candidate` only when lower-layer coverage is in the matrix
2. **Retirement ≠ deletion** — retired tests have a permanent evidence record
3. **Every behavior gets a layer** — no unattributed behaviors in the matrix
4. **Flows are mutually exclusive** — do not chain forward → reverse or reverse → forward unless legacy change condition is met
5. **TRACER recommends, humans decide** — never set `retirement_status: retired`

---

## Past Lessons

**Xray shift-left (Products Hub 2.0, 2026-09-16):**
160 Xray device tests analysed. 148 identified as retirable. Core lesson: tests accumulate at expensive layers covering logic that belongs at cheaper layers. TRACER formalises this as evidence, not gut feel.

**Retirement vs deletion confusion:**
Early framing was "delete these tests." Correct framing: map them into the matrix, prove lower-layer coverage, retire with evidence. The evidence record is the value — it prevents future re-accumulation of the same tests.
