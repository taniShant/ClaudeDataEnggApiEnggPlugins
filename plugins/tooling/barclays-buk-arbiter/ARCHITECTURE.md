# Arbiter Plugin Architecture

## Two-Layer Design

Arbiter uses a proven pattern of **Markdown routing layer** + **Python implementation layer**:

```
User Command (e.g., /arbiter-discover)
    ↓
Command Router (Markdown)
    ↓
Agent (Markdown/Haiku or Sonnet)
    ↓
Python Script (deterministic logic)
    ↓
Results (JSON) → Agent formatting → User output
```

**Philosophy:**
- **Markdown layer:** Handles routing, user interaction (BUK marketplace standard)
- **Python layer:** All deterministic logic (no LLM calls in Python)
- **Token optimization:** Haiku for mechanical tasks, Sonnet for reasoning

## Agent Model Split

| Agent | Model | Purpose | Reasoning? |
|-------|-------|---------|-----------|
| `arbiter-discover-agent` | **Haiku** | Language/framework detection | No (regex) |
| `arbiter-analyze-agent` | **Sonnet** | Call graph, confidence scoring | Yes (complex analysis) |
| `arbiter-plan-agent` | **Haiku** | Format removal plan YAML output | No (deterministic Python planning + formatting) |
| `arbiter-remove-agent` | **Sonnet** | Safe removal execution, gates | Yes (validation decisions) |
| `arbiter-validate-agent` | **Haiku** | Test parsing, result reporting | No (XML parsing) |

**Cost Impact:**
- All-Sonnet baseline: ~55K tokens per workflow
- Mixed (Haiku + Sonnet): ~13.5K tokens per workflow
- **Savings: 75%** through model selection + caching

## Call Flow Diagram

```
DISCOVER (Haiku: 2K in)
  ├─ Python: detect_languages() → JSON
  ├─ Haiku: format report
  └─ Cache: .arbiter/cache/language_detection.json
      ↓
ANALYZE (Sonnet: 8K in)
  ├─ Python: build_call_graph() → reuse cache
  ├─ Sonnet: score confidence, categorize
  └─ Cache: .arbiter/cache/call_graphs/*.json
      ↓
PLAN (Sonnet: 6K in)
  ├─ Sonnet: batch by confidence
  ├─ Sonnet: allocate to sprints
  └─ Output: ARBITER_PLAN.yaml (for Remove agent)
      ↓
REMOVE (Sonnet: 5K in)
  ├─ Parse plan YAML (from previous agent)
  ├─ Python: execute_removal() (dry-run or execute)
  ├─ Sonnet: validate gates, decide rollback
  └─ Commit: git commit with task ID
      ↓
VALIDATE (Haiku: 2K in)
  ├─ Python: run tests, compile check
  ├─ Haiku: parse XML, format report
  └─ Compare: baseline vs current → regression detection
      ↓
STATUS (Haiku: <1K in)
  └─ Read .arbiter/state/workflow.yaml → dashboard
```

## Caching Strategy

### Cache 1: Language Detection

**Path:** `.arbiter/cache/language_detection.json`

**Key:** `hash(source_files_list)`

**Content:**
```json
{
  "languages": [{"language": "java", "count": 15002}],
  "build_system": "gradle",
  "frameworks": ["Spring", "JUnit"],
  "timestamp": "ISO8601"
}
```

**Benefits:** Discover agent doesn't need to re-scan files.

### Cache 2: Call Graph

**Path:** `.arbiter/cache/call_graphs/java_<hash>.json`

**Key:** `hash(source_code + language + config)`

**Content:**
```json
{
  "nodes": [{"name": "UserService.getUser", "type": "method"}],
  "edges": [{"from": "A", "to": "B", "type": "CALLS"}],
  "entry_points": ["main", "@SpringBootApplication"],
  "reachable": [...],
  "confidence_scores": {...}
}
```

**Benefits:** Analyze agent reuses graph across multiple removal plans (90% token savings on repeat).

### Cache 3: State File

**Path:** `.arbiter/state/workflow.yaml`

**Content:**
```yaml
workflow_id: "discover-analyze-plan-remove-validate-20260720T100000Z"
current_phase: "execute"
tasks:
  total: 18
  completed: 3
  pending: 15
effort:
  planned_hours: 37
  completed_hours: 5.5
  remaining_hours: 31.5
cache_stats:
  hits: 3
  misses: 1
```

**Benefits:** Status agent reads single YAML file (no LLM calls); fast dashboard.

## v1.0 Production Release (Current)

**This is Arbiter v1.0 — Production-Ready Release with Optimizations:**

### 1. Merged Discovery + Analysis Phase
- **Legacy:** Two separate agents scanning repository independently (2n file system traversals)
- **v1.0:** Single combined agent (`arbiter-discover-analyze-agent`) with one pass (n traversals)
- **Savings:** 20% token reduction, 50% faster for initial scan

### 2. Deterministic Planning in Python
- **Legacy:** Plan agent uses Sonnet for batching logic (reasoning-based, variable output)
- **v1.0:** Planner module (`src/planner.py`) implements deterministic batching algorithm
- **Savings:** 6K tokens (eliminate one Sonnet call), guaranteed <1min execution time

### 3. Batch Execution Modes
- **Legacy:** User calls `/arbiter-remove next` for each task (18 commands for 18 tasks)
- **v1.0:** Support `/arbiter-remove --all`, `/arbiter-remove --category`, `/arbiter-remove --batch`
- **Savings:** 95% fewer user commands, 90% less context switching

### 4. Implicit Baseline Establishment
- **Legacy:** Explicit `/arbiter-validate --baseline` phase required before removals
- **v1.0:** Baseline automatically established on first remove task
- **Savings:** One fewer user command, clearer workflow

### 5. Model Optimization
- **Legacy:** 4 Sonnet calls (analyze, plan, remove, discover-analyze combined doesn't use sonnet for discover alone)
- **v1.0:** 2 Sonnet calls (discover-analyze, remove); Plan moved to Python
- **Savings:** 35% token reduction

## Token Budget Allocation (v1.0 Production)

```
Total per workflow: ~8-9K tokens (35% IMPROVEMENT vs legacy implementations)

Discover-Analyze (Sonnet, merged): 8K
  Single pass:  Detect languages + build call graph
  Input:  7K (repo scan, frameworks)
  Output: 1K (combined analysis)

Plan (Haiku + Python):             ~0.5K
  Deterministic batching algorithm (Python: src/planner.py)
  Haiku for formatting YAML output for downstream agent consumption
  Input:  ANALYSIS_JSON
  Output: Removal plan YAML (structured for Remove agent)

Remove (Sonnet):                   5K
  Input:  5K (plan + validation rules)
  Output: 2K (removal log + baseline validation)

Validate (Haiku):                  <1K
  Implicit (per-task baseline comparison)
  No additional agent call needed

Status (Haiku):                    <1K
  Read YAML only
  Output: Dashboard
```

**Comparison: v1.0 vs Legacy:**

| Phase | Legacy Model | Legacy Tokens | v1.0 Model | v1.0 Tokens | Savings |
|-------|-----------|-----------|-----------|-----------|---------|
| Discovery | Haiku | 2.5K | (Merged) | - | - |
| Analysis | Sonnet | 11K | (Merged) | - | - |
| Combined | - | 13.5K | Sonnet | 8K | 40% ↓ |
| Planning | Sonnet | 9K | Python | <1K | 99% ↓ |
| Execution | Sonnet | 7K | Sonnet | 5K | 29% ↓ |
| **Total** | 4 Sonnet calls | **~13.5K** | **2 Sonnet calls** | **~8-9K** | **35% ↓** |

## Skill Loading Strategy

### Skills Declaration (in agent frontmatter)

```yaml
skills:
  - barclays-buk-arbiter:arbiter_methodology
  - barclays-buk-arbiter:arbiter_analysis
  - barclays-buk-arbiter:arbiter_java_patterns
```

### Skill Content Format

All skills use **compact, searchable format** (not prose):

- **Tables** for lookup data (patterns, deductions, gates)
- **Bullet points** for rules and guidelines
- **Code snippets** for examples (3-5 lines max)
- **No verbose explanations** (link to principles instead)

**Result:** Skill files 500-800 tokens each (vs. 2-3K with prose).

### Skill Reuse

| Skill | Used By | When |
|-------|---------|------|
| `arbiter_methodology` | All agents | Initial context load |
| `arbiter_analysis` | Analyze, Plan | Call graph and confidence scoring |
| `arbiter_java_patterns` | Analyze, Plan, Remove | Language-specific patterns |
| `arbiter_validation` | Validate | Test execution and parsing |
| `arbiter_deprecation` | Remove | @Deprecated handling |
| `arbiter_framework_detection` | Discover, Analyze | Spring/JUnit patterns |
| `arbiter_ios_patterns` | iOS Discover, Plan, Remove | Swift/ObjC hidden usage patterns |
| `arbiter_ios_framework_detection` | iOS Discover | UIKit/SwiftUI/Combine/CoreData rules |
| `arbiter_ios_validation` | iOS Remove, Validate | xcodebuild gates, xcresult parsing |

## Python Implementation Layer

### Module Structure

```
src/
├── __init__.py                    # Entry point
├── language_detector.py           # detect_languages()
├── call_graph_analyzer.py         # build_call_graph()
├── deadcode_finder.py             # find_dead_code_candidates()
├── removal_executor.py            # execute_removal()
├── validator.py                   # validate_removal()
├── patterns/
│   ├── __init__.py
│   └── java.py                    # Java pattern detection
├── hooks/
│   ├── compile-validator.py       # Post-removal compilation check
│   └── test-validator.py          # Post-removal test check
└── scripts/
    └── discover-languages.py      # Batch discovery CLI
```

### Design Principle: Deterministic Only

All Python modules:
- ✅ Read files and parse (no LLM)
- ✅ Execute shell commands (compilers, test runners)
- ✅ Parse results (XML, JSON)
- ✅ Return structured output
- ❌ No reasoning, decision-making, or hallucination risk

**Example (language_detector.py):**
```python
def detect_languages(repo_path):
    # Glob for *.java, *.py, etc. (deterministic)
    # Count files by extension (deterministic)
    # Return JSON with percentages (deterministic)
    # No LLM calls, no reasoning
```

## Java Tool Integration (v1.0+)

**Architecture:** Python orchestration layer calls standalone Java tool via subprocess

```
removal_executor.py
    ↓ (subprocess.run)
java -jar arbiter-removal-tool.jar --method <name> --file <path>
    ↓ (Spoon AST transformation)
Modified source file + JSON result
    ↓ (parse JSON)
removal_executor.py continues
```

**Tool Details:**
- **JAR:** `build/libs/arbiter-removal-tool.jar` (fat JAR with dependencies)
- **Build:** Gradle (`./gradlew clean build` creates JAR)
- **Entrypoint:** `com.barclays.buk.arbiter.removal.SpoonRemovalTool`
- **Arguments:** `--method <name> --file <path>` or `--class <name> --file <path>`
- **Output:** JSON with status (success/not_found/error), message, removedLines, errorDetails
- **Exit Code:** 0 = success, 1 = parse error, 2 = not found, 3 = other error

**Subprocess Call Pattern:**
```python
result = subprocess.run([
    'java', '-jar', jar_path,
    '--method', method_name,
    '--file', file_path
], capture_output=True, text=True, timeout=10)

json_result = json.loads(result.stdout)
if json_result['status'] == 'success':
    # File already modified by Java tool
    return True
else:
    # Log error and return False
    return False
```

**Benefits:**
- Clean separation of concerns: Python orchestration, Java AST transformation
- Java tool is deterministic (same input → same output)
- Easy to extend: add Python removal tool, Go removal tool, etc.
- Testable: subprocess calls are easily mocked in unit tests

## Safe Removal Strategy (v1.0+) - True AST Transformation

**Method/Class Removal:** True AST transformation using Spoon (via subprocess)
- **Primary:** Spoon library (full syntactic awareness of Java language)
- **Fallback:** None. If Spoon fails → explicit error in JSON, skip removal, log message
- **Why this approach:** 
  - True AST transformation (not position-guessing or string slicing)
  - Full Java syntax support: annotations, generics, lambdas, nested structures, comments, Javadoc
  - Fail-fast: explicit error status instead of silent failures
  - Zero known edge cases (Spoon handles all Java syntax correctly)
- **Result:** Production-safe removal with no position-based vulnerabilities

**Supported Nested Structures:** if/else (any depth), try/catch/finally, for/while/foreach, lambda expressions, inner classes, generics, annotations, Javadoc, comments

**No Edge Cases:** Spoon's full syntactic awareness eliminates all position-guessing vulnerabilities

**Import Removal:** Simple regex (safe, no nesting risk) applied after Spoon removal

## Validation Gates Execution

Each removal task has gates that agents invoke:

```
REMOVE agent:
  1. Call Python: remove_executor.execute_removal(task, mode="dry-run")
  2. If dry-run OK, call: execute_removal(task, mode="execute")
     ↳ For each entity:
        - Find Spoon JAR in build/libs/
        - Call: java -jar arbiter-removal-tool.jar --method <name> --file <path>
        - Parse JSON result (success/not_found/error)
        - File already modified by Spoon subprocess
     ↳ Uses true AST transformation for methods/classes (Spoon handles all nesting)
  3. Invoke Bash: ./gradlew build -x test  (compile gate)
  4. Invoke Bash: ./gradlew test  (unit test gate)
  5. If fails: git checkout (rollback)
  6. If success: git commit with task ID
```

**Automatic rollback:**
```python
# Pseudocode
try:
    execute_removal(task)
    # execute_removal calls Spoon via subprocess for each entity
    if not compile_check():
        git_rollback()
        return "failed: compile"
    if not unit_test_check():
        git_rollback()
        return "failed: tests"
    git_commit(task_id)
    return "success"
except Exception as e:
    git_rollback()
    return f"failed: {e}"
```

## Hexagonal Architecture (3-4 Layers)

Arbiter agents should flag violations:

```
Layer 1: Controller (HTTP handlers, CLI)
  ↓ (calls)
Layer 2: Service (analysis, batching, removal)
  ↓ (calls)
Layer 3: Repository/Gateway (file I/O, shell execution)
  ↓ (calls)
Layer 4: Domain (data models, rules)
```

**Violations:**
- ❌ Controller directly calling Repository (skip Service)
- ❌ Service calling Controller (backward dependency)
- ❌ Calling into Layer 4 from Layer 1

**Arbiter response:** Flag as high-risk, lower confidence, require manual review.

## Performance Characteristics

### Phase Duration

| Phase | Duration | Input Size | Bottleneck |
|-------|----------|-----------|-----------|
| Discovery | 1-2 min | Full repo | Glob pattern scanning |
| Analysis | 10-15 min | Source code | Compilation (if Tier 2) |
| Planning | <1 min | Analysis results | Batching algorithm |
| Execution | Hours-days | Per-task | Compilation + test suite |
| Validation | 10-30 min | Test suite | Test execution time |

### Scalability

- **Repo size:** Linear for discovery; sublinear for analysis (caching)
- **Code complexity:** Linear (call graph size = O(methods + calls))
- **Token usage:** ~13.5K per workflow (independent of repo size)

## iOS/Swift Architecture (v1.1)

**Author / owner:** Pratik Goswami

### iOS Agent Model Split

| Agent | Model | Purpose | Reasoning? |
|-------|-------|---------|-----------|
| `arbiter-discover-analyze-ios-agent` | **Sonnet** | Entity discovery + call graph + scoring | Yes (complex analysis) |
| `arbiter-plan-ios-agent` | **Haiku** | Deterministic batching | No (Python planner) |
| `arbiter-remove-ios-agent` | **Sonnet** | Safe removal + validation gates | Yes (validation decisions) |
| `arbiter-validate-ios-agent` | **Haiku** | Test parsing, baseline comparison | No (mechanical) |
| `arbiter-verify-ios-agent` | **Haiku** | Status reporting | No (read state files) |

### iOS Call Flow

```
DISCOVER-ANALYZE-iOS (Sonnet: 8K)
  ├─ Python: ios_detector.run_detection() → project metadata
  ├─ Python: build_ios_call_graph() → entities + usage
  ├─ Python: scan_all_resources() → storyboard/XIB/plist refs
  ├─ Python: scan_dynamic_dispatch() → selector/class string refs
  ├─ Python: IOSConfidenceEngine.score_all() → 0-4 scores
  └─ Cache: .arbiter/swift/ENTITIES.json, CONFIDENCE.json
      ↓
PLAN-iOS (Python deterministic)
  ├─ Python: IOSRemovalPlanner.plan() → batched tasks
  └─ Output: .arbiter/swift/PLAN.json
      ↓
REMOVE-iOS (Sonnet: 5K)
  ├─ Git: create backup branch
  ├─ Python: execute removal (file delete or comment-out)
  ├─ Bash: xcodebuild build (compile gate)
  ├─ Bash: xcodebuild test (unit test gate, LIKELY/UNCERTAIN)
  └─ Git: commit or rollback
      ↓
VERIFY-iOS (Haiku: <1K)
  └─ Read .arbiter/swift/ state files → status dashboard
```

### iOS Python Module Structure

```
src/ios/
├── __init__.py                      # Package exports
├── resolve_env.py                   # Interpreter + plugin path resolution (run first)
├── arbiter_meta.py                  # Provenance stamps (generatedBy), usage-data guard
├── ios_detector.py                  # Project detection (build system, schemes)
├── ast_reference_scanner.py         # tree-sitter reference graph (Swift + ObjC), swiftinterface index
├── objc_syntax.py                   # ObjC parsing, selectors, SDK/Pods/vendored selector index
├── ios_call_graph_analyzer.py       # Entities with line ranges + usage counts
├── ios_framework_rules.py           # Lifecycle methods, annotations, protocols, test detection
├── ios_confidence_engine.py         # 0-4 scale scoring with deductions (agent path)
├── ios_confidence_engine_v2.py      # AST-aware scoring (ios_analyze_improved.py)
├── ios_dynamic_dispatch_scanner.py  # Runtime references (NSSelectorFromString, KVC, …)
├── ios_resource_scanner.py          # Storyboard/XIB (incl. legacy)/plist/asset scanning
├── ios_deadcode_finder.py           # Reachability from call graph + resources
├── ios_planner.py                   # Deterministic batching (SAFE=10, LIKELY=5); ObjC review list
├── ios_removal_executor.py          # Syntax-aware removal, bisection, per-repo commits
├── ios_calibration_report.py        # Predicted vs actual (OUTCOMES.jsonl)
└── ios_analyze_improved.py          # One-shot pipeline (analysis → plan)
```

### iOS Caching Strategy

All iOS artifacts stored in `.arbiter/swift/` (separate from Java's `.arbiter/cache/`):

| File | Content | Written By |
|------|---------|-----------|
| `ENTITIES.json` | Entity inventory + call graph | discover-analyze |
| `RESOURCE_REFS.json` | Storyboard/XIB/plist class references | discover-analyze |
| `DISPATCH_SCAN.json` | Dynamic dispatch patterns | discover-analyze |
| `CONFIDENCE.json` | Scored entities (0-4 scale) | discover-analyze |
| `PLAN.json` | Batched removal tasks | plan |
| `REMOVAL_LOG.json` | Execution history | remove |
| `VALIDATION_BASELINE.json` | Pre-removal test metrics | validate |

### iOS Confidence Scoring (0-4 Scale)

```
Start: 4.0 (assume unused)

Auto-KEEP (score = 0):
  - iOS lifecycle methods (57 patterns)
  - Entry points (@main, app delegate)
  - React Native bridge (RCT_EXPORT_*)
  - Used in call graph (any reference)

Deductions:
  -2.5: Storyboard/XIB customClass reference
  -2.0: @IBAction / @IBOutlet / override / NSClassFromString target
  -1.5: @objc / dynamic dispatch target
  -1.0: Public access / Codable conformance / data source protocol
  -0.7: UIViewController superclass / SwiftUI property wrapper
  -0.3: NSObject / Hashable

Categories:
  SAFE:      3.0-4.0 (removable with compile-only validation)
  LIKELY:    2.0-2.9 (removable with unit tests)
  UNCERTAIN: 1.0-1.9 (requires manual review)
  KEEP:      <1.0    (do not remove)
```

---

## Future Enhancements

### v1.1
- [ ] Support Python, Go, JavaScript/TypeScript (additional Tier 1 languages)
- [ ] Graphical dashboard (interactive task browser)
- [ ] Metrics dashboard (accuracy, false positives, LOC removed)

### v1.2
- [ ] Multi-language call graphs (Java ↔ Python interop)
- [ ] REST API dead code detection (trace HTTP call chains)
- [ ] Custom language plugin architecture

### v1.3
- [ ] CI/CD integration (pre-commit hooks, PR checks)
- [ ] Automated scheduling (weekly incremental scans)
- [ ] Compliance reporting (audit trail, approval workflows)

## Testing Strategy

### Unit Tests

Test each Python module independently:
```bash
python -m pytest src/test_language_detector.py
python -m pytest src/test_call_graph_analyzer.py
```

### Integration Tests

Test full workflow:
```bash
/arbiter-discover test_repo
/arbiter-analyze test_repo
/arbiter-plan
/arbiter-remove T001 --dry-run  # Verify no actual removal
```

### Plugin Validation

```bash
/test-plugin ./plugins/tooling/barclays-buk-arbiter
# Must score ≥90
```

---

**Architecture Owned By:** Preetha Ramaswamy  
**Last Updated:** 2026-07-20  
**Review Cadence:** Quarterly
