---
user-invocable: false
description: "Dead code removal workflow, confidence-based batching, risk management strategy"
---

# Skill: Arbiter Methodology

## Source Attribution

**Source:** Dead code removal methodology adapted from Arbiter plugin specifications and BUK marketplace conventions.  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Arbiter version major/minor release, or when removal workflow phases change.

## Agent Self-Check

- [ ] Workflow has 7 phases: Preparation, Discovery, Analysis, Baseline, Planning, Execution, Verification
- [ ] Confidence scores used for batching: SAFE (3-4), LIKELY (2-2.9), UNCERTAIN (1-1.9), KEEP (<1)
- [ ] Batch sizes follow: SAFE (5), LIKELY (3), UNCERTAIN (1)
- [ ] Each removal task has 2 gates: compile-check, unit-test-check
- [ ] Rollback strategy documented: auto-rollback on gate failure
- [ ] False positive tracking mechanism in place

---

## 7-Phase Workflow

| Phase | Command | Goal | Output | Duration |
|-------|---------|------|--------|----------|
| **0** | prep | Ensure environment ready | Checklist complete | - |
| **1** | `/arbiter-discover` | Catalog code entities | ARBITER_DISCOVERY.md | ~25min |
| **2** | `/arbiter-analyze` | Build call graph, score confidence | ARBITER_ANALYSIS.md | ~10-15min |
| **3** | `/arbiter-validate --baseline` | Establish baseline metrics | ARBITER_VALIDATION.md | Varies |
| **4** | `/arbiter-plan` | Create removal tasks | ARBITER_PLAN.md | <1min |
| **5** | `/arbiter-remove next` (loop) | Execute tasks, validate | Git commits | Hours-Days |
| **6** | `/arbiter-validate --report` | Final verification, metrics | ARBITER_VERIFY.md | Varies |

---

## Confidence Scoring: Quick Reference

| Tier | Score | Category | Batch Size | Effort/Task | Risk | Validation |
|------|-------|----------|-----------|-------------|------|-----------|
| **4** | 3.0-4.0 | **SAFE** | 5 | 0.5-1h | Low | Compile + unit |
| **3** | 2.0-2.9 | **LIKELY** | 3 | 1-2h | Medium | + integration |
| **2** | 1.0-1.9 | **UNCERTAIN** | 1 | 2-4h | High | + manual review |
| **1** | <1.0 | **KEEP** | 0 | N/A | Critical | Do not remove |

---

## Confidence Deductions Cheat Sheet

| Factor | Deduction | Reason |
|--------|-----------|--------|
| Public visibility | -0.5 | May be called from outside |
| @Deprecated | +0.5 | Explicitly marked for removal |
| Framework annotation (@Service, @Test, etc.) | -0.5 | May be invoked by framework |
| Reflection pattern | -1.0 | Cannot resolve statically |
| Test-only usage | -0.2 | Uncertain if prod-needed |

**Formula:** Start at 4.0, apply deductions, clamp to 0-4.

---

## Risk Management Strategy

### Low Risk (SAFE)
- ✅ Confidence 80-100%
- ✅ No usage found, private, no annotations
- **Mitigation:** Compile + unit tests

### Medium Risk (LIKELY)
- ⚠️ Confidence 60-79%
- ⚠️ Minor deductions, may be indirectly used
- **Mitigation:** Integration tests required

### High Risk (UNCERTAIN)
- 🔴 Confidence 40-59%
- 🔴 Multiple deductions, framework magic possible
- **Mitigation:** Full test suite + manual investigation

### Critical (KEEP)
- ❌ Confidence <40%
- ❌ Too risky; do not remove

---

## Batch Execution Strategy

### Start with SAFE
1. Execute SAFE category first (low risk)
2. Build confidence in process
3. Validate scoring accuracy

### Then LIKELY (if SAFE succeeds)
1. Manual review of LIKELY batch
2. Engineer approves before execution
3. More thorough validation

### Finally UNCERTAIN (if LIKELY succeeds)
1. Research each entity
2. Manual investigation
3. May reclassify as SAFE/LIKELY

---

## Sprint Integration

| Option | Best For | Allocation |
|--------|----------|-----------|
| **Dedicated Sprint** | Large cleanup (50+ items) | Full sprint capacity |
| **Incremental** | Ongoing maintenance | 20% per sprint |
| **Post-Feature** | Keep codebase clean | After feature complete |

**Effort Estimate:** SAFE (1h each) + LIKELY (1.5h each) + UNCERTAIN (3h each)

---

## Validation Gates (Mandatory)

| Gate | Command | Pass Criteria |
|------|---------|---------------|
| **compile** | `gradlew build -x test` | Exit 0, no errors |
| **unit-test** | `gradlew test` | All pass |
| **integration-test** | `gradlew integrationTest` | All pass (LIKELY/UNCERTAIN) |

**Automatic rollback** if any gate fails.

---

## Lessons Learned: False Positive Analysis

If task fails (confidence too high):

**Record:**
1. Entity removed
2. Why confidence was too high
3. Pattern missed
4. Fix for future scoring

**Example:**
```
## False Positive: calculateLegacy()
Confidence: 90% (SAFE)
Actual usage: Spring @Scheduled task
Pattern missed: Method via TaskScheduler registration
Fix: -50% for @EnableScheduling classes
```

---

## Best Practices

✅ **Do:**
- Start with full scan (establish baseline)
- Review confidence scores before planning
- Commit after each successful task
- Maintain clean baseline (all tests passing)
- Consult engineers for @Deprecated code
- Track false positives

❌ **Don't:**
- Skip validation gates
- Remove @Deprecated without consultation
- Batch too many per task
- Proceed with failing baseline
- Remove confidence <40% (KEEP)
- Rush execution

---

## Tools & Dependencies

**Required:**
- Java 17+ (JavaParser)
- Gradle or Maven
- Git (incremental scan, commits)

**Optional:**
- JaCoCo (coverage tracking)
- Checkstyle/PMD (code quality metrics)
- SonarQube (additional analysis)

---

## State File Tracking

```yaml
.arbiter/state/workflow.yaml
- Phase: discovery|analysis|planning|execution|validation
- Tasks: {completed: N, total: N}
- Effort: {completed_hours: N, planned_hours: N}
- Cache: {hits: N, misses: N}
```
