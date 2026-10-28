---
name: model-aware-execution
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Model-Aware Execution — Cost Optimisation Matrix (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** Quarterly or when model tiers or token costs change
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: All (orchestrator-only, not passed to workers)
Worker: Orchestrator (decision logic)
Load: orchestrator loads model-aware-execution §3-5 at startup
Use: select_model_for_worker(phase, worker_id, context) → tier + rationale
Model: N/A (orchestrator uses this to SELECT models for others)
```

# Model-Aware Execution — Optimal Model Selection Per Phase

> **Purpose:** Recommend the optimal Claude model for each pipeline phase and worker type, balancing cost efficiency with task complexity. Lighter models handle mechanical/discovery work; heavier models handle reasoning-intensive code generation and validation.

---

## §1 — Design Principles

```
1. RIGHT MODEL FOR THE JOB — Don't use Opus for grep-like tasks; don't use Haiku for complex code generation.
2. COST-PROPORTIONAL — Token spend should correlate with phase difficulty, not be uniform.
3. FALLBACK-SAFE — If a recommended model isn't available, gracefully fall back to the session default.
4. COMPLEXITY-ADAPTIVE — Use health_score and task complexity from discovery to adjust recommendations.
5. OBSERVABLE — Track model usage per phase for cost analysis and optimization over time.
```

---

## §2 — Model Tier Definitions

| Tier | Model ID | Strengths | Cost | Use When |
|------|----------|-----------|------|----------|
| **Tier 1: Heavy** | `opus` | Complex reasoning, code generation, multi-step logic, architectural decisions | Highest | Code generation (Phase 7A), complex spec generation (health < 50), validation with nuanced judgment |
| **Tier 2: Balanced** | `sonnet` | Good analysis, planning, test generation, pattern recognition, parsing, mechanical tasks | Standard | All other phases — discovery, planning, task breakdown, spec generation, test generation, validation, push |

> **Note:** Haiku (Tier 3) has been removed based on pilot feedback — it produced incorrect results on code parsing and analysis tasks. The pipeline now uses a two-tier Sonnet/Opus split for reliability.

---

## §3 — Phase-to-Model Matrix

### Default Recommendations (No Complexity Override)

| Phase | Worker(s) | Recommended Tier | Rationale |
|-------|-----------|-----------------|-----------|
| 0 | Init/Validation | Tier 2 (Balanced) | File existence check, state setup |
| 1A | Structure Analyzer | Tier 2 (Balanced) | AST parsing, structural extraction — needs accurate code understanding |
| 1B | Domain Boundary Detector | Tier 2 (Balanced) | Pattern matching on method names — needs reliable identification |
| 1C | Complexity Metrics | Tier 2 (Balanced) | Metric computation from source analysis |
| 1D | API Pattern Inspector | Tier 2 (Balanced) | Requires inference across multiple files to identify conventions |
| 2A | Pattern Discovery | Tier 2 (Balanced) | Needs design judgment to recommend extraction patterns |
| 2B | Test Pattern Analyzer | Tier 2 (Balanced) | Scanning test files for conventions — needs accurate parsing |
| 3 | Planning Agent | Tier 2 (Balanced) | Architectural reasoning, trade-off analysis, user interaction |
| 4 | Task Generation | Tier 2 (Balanced) | Structured breakdown from plan |
| 5A | Spec Generator | Tier 2 (Balanced) | Cross-referencing BDD extraction with hexagonal mapping |
| 6A | Test Generator | Tier 2 (Balanced) | Generating tests from spec templates — moderate creativity |
| 6A-supp | Supplementary Tests | Tier 2 (Balanced) | Targeted coverage gap analysis — requires understanding uncovered paths |
| 7A | Code Generator | **Tier 1 (Heavy)** | Complex multi-file code generation, logic extraction, clean code transforms |
| 7B | Test Runner | Tier 2 (Balanced) | Execute commands, parse output, interpret results |
| 7C | Metrics Refresh | Tier 2 (Balanced) | Re-read file and compute updated health metrics |
| 8 | Unified Validator | Tier 2 (Balanced) | Code comparison, pattern detection — moderate judgment |
| Push | Push Agent | Tier 2 (Balanced) | Git commands, MR creation, anti-hallucination checks |

---

## §4 — Complexity-Adaptive Overrides

The default matrix can be overridden based on signals discovered during the pipeline:

### Override Signal: Health Score (LIVE — refreshed per task by Worker 7C)

```
health_score = state.health_scores.current (LATEST value)

Source lifecycle:
  - Initially computed by Worker 1C (Phase 1) → stored in health_scores.baseline
  - REFRESHED by Worker 7C after EACH task extraction → stored in health_scores.current
  - Each subsequent task uses the UPDATED score (not the original Phase 1 value)
  - This enables cascading quality upgrades:
    Task 1 extracts complex methods → health improves 55→62
    Task 2 now sees health=62, not 55 → upgrades no longer applied

IF health_score < 50 (HIGH RISK — very complex monolith):
  Upgrade Phase 5A: Tier 2 → Tier 1 (spec needs deep understanding)
  Upgrade Phase 6A: Tier 2 → Tier 1 (tests need more edge cases for complex code)
  Upgrade Phase 8:  Tier 2 → Tier 1 (validation needs careful judgment)
  
IF health_score >= 50 (MODERATE/LOW RISK):
  No changes — Tier 2 (Sonnet) defaults are appropriate

Threshold crossing example:
  health_scores.baseline = 45 (HIGH RISK → upgrades applied for T001)
  After T001: health_scores.current = 52 (MODERATE → upgrades NO LONGER applied for T002)
  Savings: T002 uses Tier 2 instead of Tier 1 for phases 5/6/8
```

### Override Signal: Task Method Count

```
method_count = number of methods in current task (from STRANGLER_TASKS.md)

IF method_count > 6:
  Upgrade Phase 7A: ensure Tier 1 (complex multi-method extraction)
  
IF method_count <= 2:
  Downgrade Phase 7A: Tier 1 → Tier 2 (simple extraction, doesn't need heaviest model)
```

### Override Signal: Retry Attempt Number (Phase 7)

```
attempt = current retry attempt (1, 2, or 3)

attempt == 1 (Clean extraction):
  Use Tier 1 — needs creativity for clean code transforms

attempt == 2 (Conservative):
  Use Tier 2 — simpler task, less transformation

attempt == 3 (Pure movement):
  Use Tier 2 — straightforward code movement, Sonnet sufficient
```

### Override Signal: Parallel Extraction Mode

```
IF parallel_extraction.enabled == true:
  Consider cost: N tasks × model cost per task
  
  IF total_tasks > 5:
    Keep Phase 6A at Tier 2 (test quality non-negotiable)
    Keep Phase 7A at Tier 1 (code quality non-negotiable)
    Keep Phase 8 at Tier 2 (validation accuracy non-negotiable)
    Note: No downgrades — Sonnet is already the floor tier
```

---

## §5 — Model Selection Algorithm

```python
def select_model_for_worker(phase, worker_id, context):
    """
    Determine optimal model tier for a worker based on phase, complexity, and context.
    
    Args:
        phase: int (0-8)
        worker_id: str (e.g., "1A", "7A", "6A-supp", "7C")
        context: dict containing:
            - health_score: int (0-100, LATEST value from health_scores.current — 
              refreshed after each extraction by Worker 7C, NOT the original Phase 1 value)
            - method_count: int (methods in current task, None if not per-task)
            - attempt: int (1-3, only for Phase 7)
            - parallel_mode: bool
            - total_tasks: int (in parallel batch)
    
    Returns:
        model_tier: "heavy" | "balanced"
        rationale: str (logged for observability)
    
    NOTE: health_score is dynamically refreshed after each task extraction (Worker 7C).
    This means later tasks in a batch may get LIGHTER models if earlier extractions
    improved the monolith health past threshold boundaries (e.g., 45→55 crosses the
    <50 "high risk" threshold, disabling model upgrades for subsequent tasks).
    """
    
    # Step 1: Get default from phase-to-model matrix (§3)
    default_tier = PHASE_MODEL_MATRIX[phase][worker_id]
    
    # Step 2: Apply complexity overrides (§4)
    tier = default_tier
    rationale_parts = [f"default={default_tier}"]
    
    # Health score override
    if context.health_score is not None:
        if context.health_score < 50 and phase in (5, 6, 8):
            tier = upgrade(tier)  # balanced→heavy
            rationale_parts.append(f"upgraded: health_score={context.health_score} (high risk)")
    
    # Method count override (Phase 7 only)
    if phase == 7 and worker_id == "7A":
        if context.method_count is not None:
            if context.method_count > 6:
                tier = "heavy"
                rationale_parts.append(f"forced heavy: method_count={context.method_count}")
            elif context.method_count <= 2:
                tier = downgrade(tier)
                rationale_parts.append(f"downgraded: method_count={context.method_count} (simple)")
    
    # Retry attempt override (Phase 7 only)
    if phase == 7 and worker_id == "7A" and context.attempt:
        if context.attempt == 2:
            tier = "balanced"
            rationale_parts.append("attempt 2: conservative → balanced")
        elif context.attempt == 3:
            tier = "balanced"
            rationale_parts.append("attempt 3: straightforward movement → balanced")
    
    # Parallel mode — no downgrades (Sonnet is the floor tier)
    # Quality is non-negotiable; Haiku removed per pilot feedback
    
    # Step 3: Return result
    rationale = " | ".join(rationale_parts)
    return tier, rationale


def upgrade(tier):
    """balanced → heavy"""
    return {"balanced": "heavy", "heavy": "heavy"}[tier]

def downgrade(tier):
    """heavy → balanced (floor)"""
    return {"heavy": "balanced", "balanced": "balanced"}[tier]
```

---

## §6 — Cost Estimation

### Per-Phase Token Cost by Model Tier

| Phase | Balanced (Tier 2) | Heavy (Tier 1) | Default Selection |
|-------|-------------------|----------------|-------------------|
| 0 | ~50 tokens | ~50 tokens | Balanced |
| 1 (all workers) | ~500 tokens | ~800 tokens | Balanced |
| 2 (all workers) | ~900 tokens | ~1,400 tokens | Balanced |
| 3 | ~1,500 tokens | ~2,500 tokens | Balanced |
| 4 | ~700 tokens | ~1,100 tokens | Balanced |
| 5 (per task) | ~900 tokens | ~1,500 tokens | Balanced |
| 6 (per task) | ~750 tokens | ~1,200 tokens | Balanced |
| 7A (per task) | ~1,400 tokens | ~2,000 tokens | Heavy |
| 7B | ~300 tokens | ~400 tokens | Balanced |
| 7C (per task) | ~150 tokens | ~200 tokens | Balanced |
| 8 (per task) | ~900 tokens | ~1,400 tokens | Balanced |

### Full Pipeline Cost Comparison (Single Task)

| Strategy | Estimated Total | Savings vs All-Heavy |
|----------|----------------|---------------------|
| **All Heavy (Tier 1)** | ~10,900 tokens | — (baseline) |
| **Model-Aware (Sonnet + Opus)** | ~7,150 tokens | **34% savings** |
| **All Balanced (Tier 2)** | ~6,900 tokens | 37% savings (quality risk on Phase 7) |

> **Model-Aware execution saves ~34% token cost vs using Opus uniformly**, while maintaining quality where it matters (Phase 7A code generation stays on Opus). Pilot feedback confirmed that Haiku produced incorrect results; the Sonnet/Opus split provides the right reliability/cost balance.

### Parallel Extraction Cost (5 tasks, 2 waves)

| Strategy | Estimated Total | Notes |
|----------|----------------|-------|
| All Heavy | ~45,000 tokens | Expensive for batch |
| Model-Aware (Sonnet + Opus) | ~30,000 tokens | Opus only for Phase 7A code gen |

---

## §7 — Integration with Orchestrator

### Orchestrator Spawning Protocol (Updated)

When the orchestrator spawns a worker, it now includes the `recommended_model` parameter:

```
# In orchestrator worker spawning:
context = {
    "health_score": state.health_scores.current,  # LATEST value, refreshed by Worker 7C after each extraction
    "method_count": task.methods.length,          # from current task
    "attempt": current_attempt,                   # 1, 2, or 3 (Phase 7 only)
    "parallel_mode": state.parallel_extraction.enabled,
    "total_tasks": state.parallel_extraction.summary.total_tasks
}

model_tier, rationale = select_model_for_worker(phase, worker_id, context)

# Pass to worker prompt:
Worker spawned with:
  - phase: {phase}
  - skill_context: {phase-gated sections}
  - recommended_model: {model_tier}     ← NEW
  - model_rationale: {rationale}        ← NEW (for logging)
```

### Worker Response to recommended_model

Workers do NOT choose their own model — the **calling system** (Claude Code agent spawning) uses the `recommended_model` to set the `model` parameter on the Agent tool call:

```
# Orchestrator spawns worker:
Agent(
  prompt: "You are Worker 7A...",
  model: recommended_model,           ← Set from selection algorithm
  subagent_type: "strangler-worker-agent"
)
```

---

## §8 — Observability & Metrics

### Model Usage Tracking in State File

```json
{
  "model_execution": {
    "strategy": "model-aware",
    "tiers_available": ["heavy (opus)", "balanced (sonnet)"],
    "health_score_used": 62,
    "overrides_applied": [],
    "per_phase": {
      "phase_0": {"model": "balanced", "tokens_used": 50, "time_ms": 1500},
      "phase_1": {
        "1A": {"model": "balanced", "tokens_used": 180, "time_ms": 3800},
        "1B": {"model": "balanced", "tokens_used": 140, "time_ms": 3400},
        "1C": {"model": "balanced", "tokens_used": 130, "time_ms": 3200},
        "1D": {"model": "balanced", "tokens_used": 380, "time_ms": 4500}
      },
      "phase_2": {
        "2A": {"model": "balanced", "tokens_used": 720, "time_ms": 5200},
        "2B": {"model": "balanced", "tokens_used": 480, "time_ms": 4100}
      },
      "phase_3": {"model": "balanced", "tokens_used": 1450, "time_ms": 12000},
      "phase_4": {"model": "balanced", "tokens_used": 550, "time_ms": 4200},
      "phase_5": {"model": "balanced", "tokens_used": 880, "time_ms": 4800},
      "phase_6": {"model": "balanced", "tokens_used": 720, "time_ms": 4200},
      "phase_7A": {"model": "heavy", "tokens_used": 1850, "time_ms": 8500, "attempt": 1},
      "phase_7B": {"model": "balanced", "tokens_used": 300, "time_ms": 3100},
      "phase_7C": {"model": "balanced", "tokens_used": 150, "time_ms": 2800},
      "phase_8": {"model": "balanced", "tokens_used": 890, "time_ms": 4900}
    },
    "totals": {
      "tokens_total": 7870,
      "tokens_saved_vs_all_heavy": 3030,
      "savings_percent": 27.8,
      "time_total_ms": 62200
    }
  }
}
```

### Logging Format

```
[2026-07-15 10:05:12] [MODEL] Phase=1 Worker=1A Tier=balanced Rationale="default=balanced"
[2026-07-15 10:05:12] [MODEL] Phase=1 Worker=1D Tier=balanced Rationale="default=balanced"
[2026-07-15 10:12:30] [MODEL] Phase=7 Worker=7A Tier=heavy Rationale="default=heavy | method_count=5"
[2026-07-15 10:18:45] [MODEL] Phase=7 Worker=7A Tier=balanced Rationale="default=heavy | attempt 2: conservative → balanced"
[2026-07-15 10:22:10] [MODEL] Phase=7 Worker=7A Tier=balanced Rationale="default=heavy | attempt 3: straightforward movement → balanced"
[2026-07-15 10:25:00] [MODEL] SUMMARY tokens_total=7870 savings=27.8% strategy=model-aware
```

---

## §9 — Configuration & Overrides

### User Override via Command Flag

```
/strangler-extract T001 --model-strategy heavy
/strangler-extract T001 --model-strategy balanced
/strangler-extract T001 --model-strategy auto   ← default (model-aware selection)
```

| Strategy | Behavior |
|----------|----------|
| `auto` | Use §5 algorithm (default — recommended) |
| `heavy` | Force Tier 1 (Opus) for all workers (maximum quality, highest cost) |
| `balanced` | Force Tier 2 (Sonnet) for all workers (good balance, recommended floor) |

### Per-Phase Override in State File

Advanced users can pin specific phases to specific tiers by editing `forge-state.json`:

```json
{
  "model_overrides": {
    "phase_7": "heavy",
    "phase_8": "heavy"
  }
}
```

This takes precedence over the algorithm for the specified phases.

---

## §10 — Decision Flowchart

```
START: Orchestrator needs to spawn worker for Phase P, Worker W

  ┌─ Is there a user --model-strategy override?
  │   YES → Use that tier for ALL workers → DONE
  │   NO  ↓
  │
  ├─ Is there a per-phase override in model_overrides?
  │   YES → Use that tier for this phase → DONE
  │   NO  ↓
  │
  ├─ Look up default tier from §3 Phase-to-Model Matrix
  │   → default_tier
  │
  ├─ Is health_score available? (Phase 1C complete)
  │   YES → Apply health_score override (§4)
  │   NO  → Skip (use default)
  │
  ├─ Is this Phase 7?
  │   YES → Apply method_count override (§4)
  │         Apply attempt override (§4)
  │   NO  → Skip
  │
  ├─ Is parallel_mode active with >5 tasks?
  │   YES → Apply parallel cost containment (§4)
  │   NO  → Skip
  │
  └─ Final tier determined → Log decision → Spawn worker with model tier → DONE
```

---

## Agent Self-Check

- [ ] Model tier selected BEFORE worker spawn (not after)
- [ ] Override conditions applied in correct priority (user > state > adaptive > default)
- [ ] Heavy model (Opus) used ONLY for Phase 7A code generation and health < 50 upgrades
- [ ] Balanced model (Sonnet) used as floor for all other phases — never downgrade below Sonnet
- [ ] Cost savings logged: actual tokens vs all-heavy baseline
- [ ] No Haiku/Fast tier references anywhere in pipeline (removed per pilot feedback)

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.2 — internal engineering  
**Classification:** Internal
