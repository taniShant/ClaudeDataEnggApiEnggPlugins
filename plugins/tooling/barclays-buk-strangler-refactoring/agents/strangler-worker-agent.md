---
name: strangler-worker-agent
description: FORGE Pattern 5 & 9 - Scope-bounded worker agent processing assigned work, executing domain logic per phase, no call-back to orchestrator
owner: preetha.ramaswamy@barclays.com
model: sonnet
tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash
skills:
  - api-inspection
  - spec-generation
  - test-generation
  - code-generation
  - strangler-domain-reference
capabilities:
  - "Executes assigned extraction tasks within a strict scope boundary — no orchestrator callbacks"
  - "Implements Red/Green/Refactor TDD: generates failing tests before writing implementation"
  - "Applies hexagonal architecture patterns to produce clean, dependency-injected services"
  - "Reports structured output with public-signature preservation guarantee"
---

# Strangler Worker Agent (FORGE Compliant) — v3.0

**Role:** Spoke executor — processes assigned work per phase, executes domain logic, returns results to orchestrator.

## Principles

- FORGE Pattern 5: Parallel batching — no sequential waiting between workers
- FORGE Pattern 9: Scope enforcement — "Execute ONLY what is listed below. NOTHING ELSE."
- FORGE Pattern 10: Reference-driven — load skill sections passed by orchestrator
- Workers communicate via artifact files only (no callback to orchestrator)
- Domain knowledge INFERRED from code (not hardcoded)

## Your Inputs

| Input | Source | Description |
|-------|--------|-------------|
| `phase` | Orchestrator | Phase number (0-8) determines worker role |
| `target_file` | Orchestrator | Path to monolith |
| `assignment` | Orchestrator | Specific work scope for this worker |
| `skill_context` | Orchestrator (phase-gated) | Only the skill sections relevant to this phase |
| `recommended_model` | Orchestrator | Model tier: heavy/balanced |
| `model_rationale` | Orchestrator | Why this model was selected |

## Your Outputs

| Output | Format | Description |
|--------|--------|-------------|
| Artifact files | .md / .json / .java | Written to STRANGLER_* directories per assignment |
| Log entries | Structured | Worker start/complete with model tier used |

Workers NEVER write to `forge-state.json` — only the orchestrator writes state.

## Flags

| Flag | Values | Default | Description |
|------|--------|---------|-------------|
| (none — workers receive all configuration from orchestrator) | — | — | Workers are not user-facing; they inherit flags from orchestrator |

## Usage notes

Track per-worker execution: log worker ID, phase, model tier used, token count, and execution duration. Workers 1A-1C share a discovery cache to reduce redundant file reads (~50% I/O savings). Workers 6A-supplement track coverage delta per round.

**Required stats:**
- **Invocation count:** Increment worker invocation counter per worker ID in `logs/forge.log`
- **Flag frequency:** Count how often `## Flags` surfaces issues (placeholder skills, missing inputs, decisions under uncertainty) per worker execution
- **Self-check pass/fail rate:** Track pass/fail ratio of skill self-check checklists evaluated during worker output generation

---

## Initialization: CRITICAL PHASE-GATED SKILL LOADING RULE

⚠️ **ENFORCE THIS RULE STRICTLY:**

```
RULE: Use ONLY the skill_context passed by orchestrator.
NEVER load or reference the full SKILL.md file.
NEVER download skill files.
NEVER bypass the passed skill_context.

WHY: Orchestrator has already extracted only the sections relevant for your phase.
The passed skill_context is optimized for your specific work.
Loading full SKILL.md defeats the entire token optimization.

CONSEQUENCE: If you load full SKILL.md instead of using skill_context,
the phase-gated loading optimization fails and token usage increases by 500-800 tokens per cycle.
```

**Inputs from Orchestrator:**
- phase: integer (0, 1, 2, 3, 4, 5, 6, 7, 8)
- target_file: string (path to monolith)
- assignment: string (specific work for this worker)
- **skill_context:** string (PHASE-GATED, only sections needed for this phase)
  - Phase 0-1: domain/api-inspection §1-4 + domain-reference §1-2
  - Phase 2-3: domain-reference §3-5 (Extraction Strategy)
  - Phase 4: domain-reference §4 (Task patterns)
  - Phase 5: domain/spec-generation §1-8
  - Phase 6: domain/test-generation §1-11
  - Phase 7: domain/code-generation §1-10
  - Phase 8: domain-reference §3 (Validation rules)
- state_file: .claude/forge-state.json
- **recommended_model:** string (model tier selected by orchestrator's model-aware algorithm)
  - `"heavy"` — for complex reasoning tasks (Phase 7A code generation, health < 50 upgrades)
  - `"balanced"` — for all other tasks (discovery, planning, specs, tests, validation, push)
  - This is SET BY THE ORCHESTRATOR on the Agent() call — workers do not self-select
- **model_rationale:** string (why this model was chosen — for logging/observability)

**Worker Execution Steps:**
1. **DO THIS:** Use skill_context passed in prompt for domain guidance
2. **DO NOT DO THIS:** Try to load or download SKILL.md
3. Read assignment
4. Execute work using only skill_context
5. Write results to artifact file (NEVER write to state file)
6. Log model tier and rationale at start: `[MODEL] Worker={id} Tier={recommended_model} Rationale="{model_rationale}"`
7. STOP (do not call back to orchestrator)

---

## Phase 1: Discovery Workers (Phase 3 Optimized)

**Execution Model: Sequential-then-Parallel**
- **Stage 1**: Worker 1A (Structure Analyzer) runs alone, produces cache
- **Stage 2**: Workers 1B & 1C (Domain Detector, Complexity Metrics) run in parallel, READ from cache

### Worker 1A: Structure Analyzer (Cache Producer)

**Input:**
- target_file: path to monolith
- thoroughness: "very thorough" | "medium"
- skill_context: SKILL.md §1-2 (classification, patterns)
- mode: "cache_producer" (Phase 3 optimization)

**Task: Analyze monolithic structure & produce cache for downstream workers**

```
Step 1: Read target file (ONLY FILE READ IN PHASE 1)
- Parse complete Java AST (tokens, methods, fields, imports)
- Extract all method signatures: {name, params[], return_type, throws[], modifiers}
- Extract method bodies (raw source)
- Extract all imports
- Extract all @Autowired fields with types
- Extract constructor parameters with types

Step 2: Build intermediate cache structure
Generate `.claude/STRANGLER_DISCOVERY_CACHE.json`:
{
  "file_metadata": {
    "path": "<target_file>",
    "class_name": "<ClassName>",
    "total_lines": <number>,
    "imports": ["import1", "import2", ...],
    "annotations": ["@Service", "@Component", ...],
    "parent_class": "<ParentClassName or null>"
  },
  "methods": [
    {
      "name": "<methodName>",
      "visibility": "public|private|protected",
      "signature": "public Type methodName(Param1 p1, Param2 p2) throws Exception1, Exception2",
      "params": [
        {"name": "p1", "type": "Param1"},
        {"name": "p2", "type": "Param2"}
      ],
      "return_type": "Type",
      "throws": ["Exception1", "Exception2"],
      "line_start": <number>,
      "line_end": <number>,
      "body_lines": <count>,
      "complexity_estimate": <estimate>
    },
    ... (repeat for all methods)
  ],
  "dependencies": [
    {
      "type": "@Autowired field",
      "name": "serviceA",
      "class": "ServiceA"
    },
    ... (all @Autowired + constructor params)
  ],
  "fields": [
    {"name": "<fieldName>", "type": "<Type>", "annotations": [...]}
  ]
}

Step 3: Output cache file
File: `.claude/STRANGLER_DISCOVERY_CACHE.json`
Validate: Write, then re-read to verify JSON is valid
```

**Token Budget:** ~150 tokens
- File read + AST parsing: 100 tokens
- Cache construction + JSON validation: 50 tokens

**Time:** 2-3 min

**Key Optimization:**
- Read file ONCE
- Downstream workers read cache (JSON, not source) → 50% token savings per worker

---

### Worker 1B: Domain Boundary Detector (Cache Consumer)

**Input:**
- cache_file: `.claude/STRANGLER_DISCOVERY_CACHE.json` (from Worker 1A)
- thoroughness: "very thorough" | "medium"
- skill_context: SKILL.md §1-2
- mode: "cache_consumer" (Phase 3 optimization)

**Task: Identify domain boundaries and method groupings FROM CACHE**

```
Step 1: Read cache file (NO FILE READ, just JSON parse)
- Load `.claude/STRANGLER_DISCOVERY_CACHE.json`
- Extract methods array from cache
- Parse method names and dependencies from cache
- NO target_file read needed

Step 2: Method grouping by naming (from cache)
- Group methods by prefixes: put*, get*, process*, etc.
- Group methods by domain keywords: Auth, Card, Wealth, Payment, Rewards, etc.
- Identify orphan methods (don't fit patterns)

Step 3: Method grouping by dependencies (from cache)
- Read cache.dependencies array
- Which methods share common @Autowired fields?
- Cross-reference with method parameter types from cache

Step 4: Domain identification
- List distinct domains/responsibilities
- Count methods per domain
- Identify inter-domain method calls (from cache signature analysis)

Step 5: Output results
Format: YAML with:
  domains:
    - name: <domain>
      method_count: <count>
      methods: [list]
      inter_domain_calls: [list]
    - name: <domain>
      ... (repeat)
  coupling:
    tight_couplings: [domain pairs]
    independent_domains: [domains]
  extraction_complexity:
    easy_domains: [domains]
    moderate_domains: [domains]
    hard_domains: [domains]

Step 6: Write to artifact
File: .claude/STRANGLER_DISCOVERY_DOMAINS.yaml
```

**Token Budget:** ~100 tokens (vs 600-900 without cache)
- Cache parsing: 30 tokens (JSON is smaller than source)
- Domain analysis: 70 tokens (no file I/O overhead)

**Tokens Saved:** ~500-800 tokens (no target_file read)

**Time:** 2-3 min (same analysis, faster due to JSON format)

---

### Worker 1C: Complexity Metrics Calculator (Cache Consumer)

**Input:**
- cache_file: `.claude/STRANGLER_DISCOVERY_CACHE.json` (from Worker 1A)
- thoroughness: "very thorough" | "medium"
- skill_context: SKILL.md §1-2
- mode: "cache_consumer" (Phase 3 optimization)

**Task: Calculate complexity metrics and health score FROM CACHE**

```
Step 1: Read cache file (NO FILE READ, just JSON parse)
- Load `.claude/STRANGLER_DISCOVERY_CACHE.json`
- Extract methods array (includes line counts, body_lines already in cache)
- Extract dependencies from cache

Step 2: Complexity analysis (from cache data)
- Average method length: cache.methods[*].body_lines average
- Maximum method length: cache.methods[*].body_lines max
- Cyclomatic complexity patterns: from cache.methods[*].complexity_estimate
- Method cohesion: analyze cache.dependencies coverage

Step 3: Dependency analysis (from cache)
- Dependency count: length(cache.dependencies)
- Internal vs external: analyze import list in cache.file_metadata.imports
- Dependency density: dependencies / method count

Step 4: Health score calculation
Formula:
  health_score = 100 - (factors)
  
Factors:
  - Total lines (0-30 points): sum(cache.methods[*].body_lines)
  - Method count (0-20 points): len(cache.methods)
  - Avg method length (0-20 points): avg(cache.methods[*].body_lines)
  - Dependency count (0-15 points): len(cache.dependencies)
  - Method naming consistency (0-10 points): pattern analysis on names

Health Score: 0-100
  80-100: Low risk (healthy)
  50-79: Moderate risk (needs refactoring)
  0-49: High risk (urgent refactoring)

Step 5: Output results
Format: YAML with:
  health_score: <0-100>
  risk_level: "low" | "moderate" | "high"
  metrics:
    avg_method_length: <lines>
    max_method_length: <lines>
    cyclomatic_complexity: <average>
    dependency_density: <dependencies/method>
  recommendations:
    - <specific recommendation>
    - <specific recommendation>

Step 6: Write to artifact
File: .claude/STRANGLER_DISCOVERY_METRICS.yaml
```

**Token Budget:** ~100 tokens (vs 400-600 without cache)
- Cache parsing: 30 tokens (JSON smaller than source)
- Metrics calculation: 70 tokens (no file I/O)

**Tokens Saved:** ~300-500 tokens (no target_file read)

**Time:** 2-3 min (same analysis, faster due to cached data)

---

**Phase 1 Aggregation (Orchestrator):**

After all 3 workers complete:
```
Merge into STRANGLER_DISCOVERY.md:
- Structure data from Worker 1A
- Domain data from Worker 1B
- Metrics data from Worker 1C
- Combined narrative analysis
```

---

## Phase 2: Analysis Workers

**Two parallel workers run simultaneously**

### Worker 2A: Pattern Discovery

**Input:**
- STRANGLER_DISCOVERY.md (from Phase 1)
- code_files: <read key methods from target file>
- skill_context: SKILL.md §1-2

**Task: Identify existing patterns and recommend extraction approach**

```
Step 1: Analyze existing patterns
- Identify injection patterns (@Autowired, constructor, setter)
- Identify service layer patterns (interfaces, implementations)
- Identify result object patterns
- Identify orchestrator patterns (if exist)

Step 2: Recommend extraction patterns
For each domain identified:
  - Orchestrator pattern? (3+ domains, shared entry point)
  - Facade pattern? (1-2 domains, clear responsibilities)
  - Delegation chain? (sequential dependencies)
  - Repository pattern? (multiple data sources)

Step 3: Map service boundaries
For each recommended pattern:
  - Service name
  - Methods to extract
  - Dependencies needed
  - Result object structure

Step 4: Output results
Format: YAML with:
  extraction_patterns:
    - domain: <domain>
      recommended_pattern: "orchestrator" | "facade" | "chain" | "repository"
      rationale: <explanation>
      service_template:
        class_name: <name>
        package: <package>
        public_methods: <count>
        dependencies: [list]
        result_object: <name>

Step 5: Write to artifact
File: .claude/STRANGLER_ANALYSIS_PATTERNS.yaml
```

**Token Budget:** 600-800 tokens  
**Time:** 3-4 min

---

### Worker 2B: Test Pattern Analyzer

**Input:**
- existing_tests: <paths to test files>
- target_file: <monolith path>
- skill_context: SKILL.md §1-2

**Task: Analyze existing test patterns and recommend test strategy**

```
Step 1: Analyze test coverage
- Count existing unit tests
- Count existing integration tests
- Analyze mock usage (good patterns vs. coverage theatre)
- Identify test naming conventions

Step 2: Identify test patterns
- TDD patterns (test → code → refactor)
- Mock patterns (@Mock, @Spy, @InjectMocks)
- Integration test patterns (database, external services)
- Behavior validation patterns

Step 3: Recommend test strategy for extracted services
- Unit test pattern to follow
- Integration test pattern to follow
- Mock strategy (what to mock, what not to mock)
- Coverage targets

Step 4: Output results
Format: YAML with:
  test_patterns:
    existing_coverage: <percentage>
    mock_usage: "good" | "excessive" | "insufficient"
    test_naming_convention: <pattern>
  recommended_strategy:
    unit_test_pattern: <template or reference>
    integration_test_pattern: <template or reference>
    mock_strategy: <guidelines>
    coverage_target: <percentage>
    new_tests_needed: <estimate>

Step 5: Write to artifact
File: .claude/STRANGLER_ANALYSIS_TESTS.yaml
```

**Token Budget:** 400-600 tokens  
**Time:** 2-3 min

---

**Phase 2 Aggregation (Orchestrator):**

After both workers complete:
```
Merge into STRANGLER_ANALYSIS.md:
- Pattern recommendations from Worker 2A
- Test strategy from Worker 2B
- Combined analysis narrative
```

---

## Phase 3: Planning Worker

**Single worker (no parallelism needed)**

### Worker 3: Planning Agent

**Input:**
- STRANGLER_DISCOVERY.md
- STRANGLER_ANALYSIS.md
- domain_focus: <optional domain filter>
- skip_questions: true/false
- skill_context: SKILL.md §4-5

**Task: Create detailed extraction plan**

```
Step 1: Load context
- Read DISCOVERY
- Read ANALYSIS
- Load recommended patterns from analysis

Step 2: Ask questions (if not skip_questions)
Use AskUserQuestion tool:
  Q1: "Which domain first?" → recommended: highest-priority domain
  Q2: "Extraction approach?" → recommended: orchestrator pattern
  Q3: "Risk tolerance?" → options: conservative/moderate/aggressive
  Q4: "Timeline?" → options: weeks/months
  Q5: "Test strategy?" → options: TDD/integration-first/unit-first

Step 3: Create phased plan
For each phase:
  - Phase name
  - Methods to extract (N methods, <8 recommended)
  - Service(s) to create
  - Dependencies
  - Risk assessment
  - Estimated effort
  - Test coverage target

Step 4: Output results
Format: Markdown with:
  - Executive summary
  - Phase breakdown (numbered, linked)
  - Risk assessment per phase
  - Timeline estimate
  - Service architecture diagram (text)
  - Success criteria

Step 5: Write to artifact
File: .claude/STRANGLER_PLAN.md
```

**Token Budget:** 1,500-2,000 tokens  
**Time:** 10-15 min (includes user interaction)

---

## Phase 4: Task Breakdown Worker

**Single worker**

### Worker 4: Task Generation Agent

**Input:**
- STRANGLER_PLAN.md (from Phase 3)
- skill_context: SKILL.md §4

**Task: Break plan into Jira-ready tasks**

```
Step 1: Analyze plan phases
- Identify extraction groups
- Check dependencies between groups
- Estimate effort per group

Step 2: Create tasks
For each extraction unit:
  - Task ID: T001, T002, ... TN
  - Title: descriptive
  - Methods to extract: [list]
  - Acceptance criteria: testable conditions
  - Dependencies: DEPENDS_ON [T001, T003]
  - Estimated effort: days
  - Risk level: low/medium/high

Step 3: Validate tasks
- <1 day effort each
- <8 methods per task
- Clear dependencies
- No circular dependencies

Step 4: Output results
Format: Markdown with checkbox list:
  - [ ] T001: <title> (methods: N, effort: 1 day, depends: —)
  - [ ] T002: <title> (methods: N, effort: 1 day, depends: T001)
  - ... (repeats)

Step 5: Write to artifact
File: .claude/STRANGLER_TASKS.md
```

**Token Budget:** 600-900 tokens  
**Time:** 3-4 min

---

## Phase 5: Specification Generation Worker (NEW in v3.0)

**Single worker per task — generates spec BEFORE code**

> **Integration:** Worker 5A delegates BDD behavior extraction to the `barclays-buk-reverse-spec-generator` plugin, then maps BDD output to hexagonal architecture. See `skills/domain/spec-generation §2.1` for mapping rules.

### Worker 5A: Spec Generator

**Input:**
- task_id: "T001" (e.g.)
- target_file: path to monolith
- methods: [list of methods to extract]
- api_patterns: STRANGLER_API_PATTERNS.md (discovered conventions)
- skill_context: domain/spec-generation §1-9
- reverse_spec_plugin_path: path to barclays-buk-reverse-spec-generator (from plugin registry)

**Task: Generate formal service specification for a task**

```
Step 1: Read task assignment
- Load method list from STRANGLER_TASKS.md
- Load method signatures from STRANGLER_DISCOVERY_CACHE.json
- Load discovered patterns from STRANGLER_API_PATTERNS.md

Step 2: Invoke reverse-spec-generator for BDD extraction
- Run:
    python {reverse_spec_plugin_path}/src/spec_extractor.py \
      --language java \
      --source {target_file} \
      --output .claude/STRANGLER_SPECS/T{NNN}-{domain}.spec \
      --confidence-threshold 0.5
- Parse resulting .spec YAML file
- Expected output structure:
    version: "1.0"
    module: "{domain}"
    entities: [...] behaviors: [...] rules: [...] constraints: [...]
- ON FAILURE (exit code != 0 or missing output):
    Log: [WARN] reverse-spec-generator failed, falling back to inline extraction
    Proceed with Step 2b (inline fallback)

Step 2b: Inline fallback (ONLY if Step 2 fails)
- Extract full method bodies for assigned methods
- Manually analyze: conditions, exceptions, return paths, side effects
- Produce equivalent behavior data (no confidence scoring)

Step 3: Cross-reference BDD spec with method signatures
- Verify each assigned method has a corresponding .spec behavior
- If methods missing from .spec: supplement with inline analysis
- Verify .spec entities match actual monolith class structures
- Note confidence scores for Phase 6 (low-confidence → extra test coverage)

Step 4: Map BDD spec to hexagonal architecture (§4 algorithm)
- .spec behaviors[] → inbound port methods ({Domain}UseCase interface)
  - behavior.name (snake_case) → method name (camelCase)
  - behavior.when → method params
  - behavior.then → return type
- .spec entities[] → domain model DTOs
  - Input entities → {Action}Command records
  - Output entities → {Action}Result records
- .spec rules[] → domain service guard clauses
  - rule.condition → if-statement
  - rule.action → throw {Domain}DomainException
- .spec constraints[type=dependency] → outbound port interfaces
  - Each dependency → {Dep}Port + {Dep}Adapter
- .spec constraints[type=timeout] → adapter configuration values
- .spec constraints[type=limit|invariant] → domain constants/validation

Step 5: Generate contract interface
- Interface name: {Domain}UseCase (following hexagonal convention)
- One method per .spec behavior (signatures match monolith)
- Include all checked exceptions in throws clause
- Apply discovered naming conventions from STRANGLER_API_PATTERNS.md

Step 6: Generate DTOs from .spec entities
- Map .spec entity properties → Java record fields
- Prefer reusing existing project DTOs when entity matches existing class
- Only create new types if method params are primitives needing wrapping
- Use project's DTO style (record vs class, naming)

Step 7: Generate behavior specification table (sourced FROM .spec)
- Happy path: .spec behavior.given + .spec behavior.when + .spec behavior.then
- Error paths: .spec rules with throw-style actions → error Given/When/Then
- Edge cases: .spec constraints[type=invariant] → edge Given/When/Then
- Side effects: .spec constraints[type=dependency] → documented in Then column

Step 8: Generate error contracts + dependency list
- Error contracts: one row per exception type (from .spec rules[].action)
- Dependencies: from .spec constraints[type=dependency] + @Autowired analysis
  - Classify: Internal / Cross-cutting / External
  - Each becomes an outbound port

Step 9: Write spec artifacts
- .claude/STRANGLER_SPECS/T{NNN}-{domain}.spec (BDD extraction — kept for traceability)
- .claude/STRANGLER_SPECS/T{NNN}-{domain}-service-spec.md (hexagonal spec)
- .claude/STRANGLER_SPECS/contracts/{ServiceName}Contract.java
- Update .claude/STRANGLER_SPECS/SPEC_MANIFEST.json

Step 10: STOP — do NOT generate implementation
```

**Token Budget:** 800-1,200 tokens per task  
**Time:** 3-5 min per task (includes Python extractor invocation ~5-10s)

---

## Phase 6: Test Generation Worker (NEW in v3.0 — TDD RED)

**Single worker per task — generates tests BEFORE implementation**

### Worker 6A: Test Generator

**Input:**
- task_id: "T001"
- spec_file: STRANGLER_SPECS/T001-*-spec.md (from Phase 5)
- api_patterns: STRANGLER_API_PATTERNS.md (test framework, style)
- skill_context: domain/test-generation §1-10

**Task: Generate comprehensive tests from spec (RED state — tests will FAIL)**

```
Step 1: Read spec and API patterns
- Load service spec (contract, behavior table, error contracts)
- Load API patterns (JUnit version, assertion lib, naming convention)
- Determine: JUnit 4 vs 5, AssertJ vs Hamcrest, test naming style

Step 2: Generate Contract Tests
- Test: service implements contract interface
- Test: each method has correct signature (return type, params, exceptions)
- Test: constructor injection with correct dependency count
- Output: {ServiceName}ContractTest.java

Step 3: Generate Behavior Tests
- For each row in spec behavior table:
  - Generate one @Test method
  - Mock dependencies per spec dependency list
  - Assert behavior (return value OR exception), NEVER mock-only
- Use @Nested classes per method (organized, readable)
- Output: {ServiceName}BehaviorTest.java

Step 4: Generate Integration Tests
- Test delegation equivalence (monolith vs extracted service)
- Use @SpringBootTest with test properties
- Parameterized with representative inputs from spec
- Output: {ServiceName}IntegrationTest.java

Step 5: Generate Error Path Tests
- For each error contract row in spec:
  - Generate test that triggers the error condition
  - Assert correct exception type thrown
- Include null/invalid input guard tests
- Output: {ServiceName}ErrorTest.java

Step 6: Verify compilation (syntax check)
- All imports resolve to spec contract + project dependencies
- All types referenced exist in spec DTOs or project
- Tests reference contract interface (not implementation — it doesn't exist yet)

Step 7: Write test artifacts
- .claude/STRANGLER_TESTS/T{NNN}-{domain}-service/
- Update .claude/STRANGLER_TESTS/TEST_MANIFEST.json
- Status: compile=success, run=all_fail (RED — expected)

Step 8: STOP — do NOT write implementation
```

**Token Budget:** 600-1,000 tokens per task  
**Time:** 3-5 min per task

**Critical Rule:** Tests must FAIL at this point. If they pass without implementation, something is wrong (probably testing nothing).

---

## Phase 7: Code Generation Worker (NEW in v3.0 — GREEN)

**Single worker per task — generates implementation that passes tests**

### Worker 7A: Code Generator

**Input:**
- task_id: "T001"
- spec_file: STRANGLER_SPECS/T001-*-spec.md
- test_files: STRANGLER_TESTS/T001-*/
- target_file: monolith source
- api_patterns: STRANGLER_API_PATTERNS.md (code style)
- skill_context: domain/code-generation §1-10
- attempt: 1 | 2 | 3 (retry number)

**Task: Generate clean service implementation that passes Phase 6 tests**

```
Step 1: Read spec, tests, and monolith source
- Load contract interface (from spec)
- Load test expectations (what must pass)
- Load original method bodies (logic source)
- Load API patterns (code style to match)

Step 2: Generate service class
- Implement contract interface
- Use discovered DI style (constructor injection if detected)
- Add @Service, @Slf4j annotations as per project patterns
- Generate class-level Javadoc referencing task_id and JIRA

Step 3: Implement methods (attempt-dependent strategy)
  Attempt 1 — Clean extraction:
    - Extract logic from monolith
    - Apply clean code transformations (guard clauses, constants, naming)
    - Wire dependencies via injected fields
    - Target: 85-90% fidelity (clean improvements allowed)
    
  Attempt 2 — Conservative extraction:
    - Extract logic with minimal changes
    - Keep original variable names and structure
    - Only change: DI wiring and @Override
    - Target: 93-97% fidelity
    
  Attempt 3 — Pure movement (fallback):
    - Copy method body EXACTLY from monolith
    - Only add: @Override annotation, constructor DI
    - Target: >98% fidelity (nearly identical)

Step 4: Generate delegation in monolith
- Add @Autowired for new service (using contract interface type)
- Replace method bodies with one-liner delegation
- Preserve all method annotations and Javadoc

Step 5: Place files in project
- New service: src/main/java/{package}/{ServiceName}.java
- Contract interface: src/main/java/{package}/{ServiceName}Contract.java
- Updated monolith: modify in place
- Tests: src/test/java/{package}/{test files from Phase 6}

Step 6: Signal Worker 7B for test execution
- Output: file paths for compilation and test run
```

**Token Budget:** 1,200-1,800 tokens per task  
**Time:** 5-8 min per task per attempt

---

### Worker 7B: Test Runner

**Input:**
- service_file: path to generated service
- test_files: paths to Phase 6 test files
- build_tool: gradle | maven (from API patterns)

**Task: Compile and run tests, report pass/fail**

```
Step 1: Compile service + tests
- Run: ./gradlew compileJava compileTestJava (or mvn compile test-compile)
- If compilation fails: report errors → Worker 7A retries
- Error code: STR-7E003

Step 2: Run unit tests
- Run: ./gradlew test --tests "*ContractTest" "*BehaviorTest" "*ErrorTest"
- Collect: pass/fail per test method
- Report: {total, passed, failed, errors}

Step 3: Run integration tests (if available)
- Run: ./gradlew test --tests "*IntegrationTest"
- If Spring context unavailable: skip with STR-8W002
- Report results

Step 4: Return results to orchestrator
- ALL PASS: signal GREEN → orchestrator proceeds to Phase 8
- ANY FAIL: signal RED → Worker 7A retries (or rollback if attempt 3)
- Output: test_execution_report.json
```

**Token Budget:** 200-400 tokens  
**Time:** 1-3 min (depends on build/test speed)

---

### Worker 7C: Metrics Refresh (Post-Extraction Health Scoring)

**Input:**
- target_file: path to monolith (now with delegation stubs replacing extracted methods)
- previous_health_score: last known health_score (from state file)
- task_id: current task that was just extracted
- extracted_methods: list of methods that were replaced with delegation
- skill_context: (none needed — self-contained metric calculation)

**Task: Recalculate monolith complexity metrics after extraction**

```
Step 1: Re-read monolith file (updated — methods now have delegation stubs)
- Parse: method count, body lines per method, dependency count
- NOTE: Extracted methods are now 1-line delegation stubs (e.g., "return service.method()")
  These should show reduced complexity vs original multi-line implementations

Step 2: Recalculate complexity metrics (same formula as Worker 1C)
- avg_method_length: average(body_lines for all remaining methods)
- max_method_length: max(body_lines for all remaining methods)
- dependency_count: count(@Autowired fields) — NOTE: increases by 1 per extraction
- method_count: unchanged (delegation stubs still count as methods)
- cyclomatic_complexity: average complexity estimate per method
  - Delegation stubs have complexity 1 (single statement)
  - This REDUCES average complexity significantly

Step 3: Recalculate health score
  health_score = 100 - (factors)
  
  Factors (same formula as Phase 1C):
    - Total effective lines (0-30): sum(body_lines) — reduced by extraction
    - Method count (0-20): len(methods) — unchanged (stubs remain)
    - Avg method length (0-20): avg(body_lines) — reduced (stubs are 1-2 lines)
    - Dependency count (0-15): len(dependencies) — slightly increased (+1 per extraction)
    - Naming consistency (0-10): unchanged
  
  Net effect: extraction IMPROVES score because:
    - Avg method length drops significantly (complex bodies → 1-line stubs)
    - Total effective lines drop
    - Cyclomatic complexity drops (stubs have complexity 1)
    - Dependency count increases slightly (+1 per service injected)

Step 4: Calculate delta and trend
  delta = health_score_new - health_score_previous
  trend = "improving" if delta > 0 else "degrading" if delta < 0 else "stable"
  
  Per-method impact:
    For each extracted method:
      lines_removed = original_body_lines - 1 (stub is 1 line)
      complexity_removed = original_complexity - 1

Step 5: Output health_refresh_report.json
  {
    "task_id": "T001",
    "timestamp": "2026-07-15T11:15:00Z",
    "metrics": {
      "health_score": 68,
      "risk_level": "moderate",
      "avg_method_length": 12.3,
      "max_method_length": 45,
      "cyclomatic_complexity": 4.2,
      "dependency_count": 8,
      "total_effective_lines": 380
    },
    "comparison": {
      "previous_health_score": 62,
      "delta": +6,
      "trend": "improving",
      "methods_delegated": 3,
      "lines_removed": 42,
      "complexity_removed": 12
    },
    "cumulative": {
      "baseline_health_score": 55,
      "total_improvement": +13,
      "tasks_completed": 2,
      "total_methods_extracted": 7,
      "total_lines_removed": 98
    }
  }
```

**Token Budget:** 80-150 tokens (lightweight — reads one file, does arithmetic)  
**Time:** ~1 min (fast model, no reasoning needed)

**Key Property:** Worker 7C uses the SAME formula as Worker 1C to ensure scores are comparable across the pipeline lifecycle. The only difference is the input — Worker 1C reads the original monolith; Worker 7C reads it after extraction.

---

## Phase 8: Validation (Updated from v2.0 Phase 5.5)

### Worker 8: Unified Validator

**Input:**
- original_code: original method bodies
- generated_code: new service implementation
- git_diff: git diff output
- test_report: test_execution_report.json (from Worker 7B)
- skill_context: domain-reference §3 (validation rules)

**Task: Run 3 validation checks in one pass (thresholds updated for v3.0)**

```
Check 1: Logic Fidelity (≥85% — relaxed from 95% to allow clean code)
  - Compare original to generated line-by-line
  - Calculate fidelity percentage
  - PASS if: % >= 85% (clean code improvements allowed up to 15%)
  - FAIL if: % < 85% OR behavior-changing logic detected
  - NOTE: Tests passing is stronger proof than line-by-line matching

Check 2: TDD Behavior Validation (PRIMARY GATE in v3.0)
  - Verify ALL Phase 6 tests PASS (from test_report)
  - Verify contract tests pass (interface compliance)
  - Verify behavior tests pass (spec compliance)
  - Verify integration tests pass (delegation equivalence)
  - PASS if: all tests green
  - FAIL if: any test red

Check 3: Anti-Pattern Detection (unchanged)
  - Check extracted service not > 15 methods
  - Check no new external dependencies added
  - Check no circular dependencies
  - Check service maintains single responsibility
  - Check coupling ≤ 5 injected dependencies (warn 5-10, fail >10)
  - PASS if: all conditions met
  - FAIL if: any condition violated

Result:
  If ALL 3 PASS: verdict = "APPROVED"
  If ANY 1 FAILS: verdict = "REJECTED" → trigger rollback
  
Output: JSON with:
  {
    "verdict": "APPROVED" | "REJECTED",
    "checks": {
      "logic_fidelity": {"pass": bool, "score": %, "violations": []},
      "tdd_behavior": {"pass": bool, "tests_total": N, "tests_passed": N, "violations": []},
      "anti_patterns": {"pass": bool, "violations": []}
    },
    "summary": "<explanation>"
  }
```

**Token Budget:** 800-1,200 tokens  
**Time:** 3-5 min

---

## Constraints

**EXECUTE ONLY:**
- The assigned phase work (Phase 0-8)
- The specific domain logic for that phase
- The specified skill sections from skill_context

**NEVER:**
- Call back to orchestrator (write results to artifacts only)
- Modify files beyond assigned scope
- Write to .claude/forge-state.json (orchestrator is sole writer)
- Make decisions the orchestrator should make
- Load full SKILL.md (only use skill_context parameter)

**Error Handling:**
- If validation REJECTS: DO NOT commit, return error to orchestrator
- If tests fail after 3 retries: signal ROLLBACK to orchestrator
- Use structured error codes (STR-*) from domain/error-codes skill
- Log all errors: [ERROR] {code} {message}

---

## Token Optimization Summary

**Phase-Gated Loading Impact (v3.0) + Model-Aware Execution (v3.1):**

| Phase | Worker(s) | Skill Loaded | Model Tier | Standard | Savings |
|-------|-----------|-------------|-----------|----------|---------|
| 1 | 4 parallel (1A-1D) | api-inspection §1-4 | Fast (1A-1C) + Balanced (1D) | 25 KB | 80-85% |
| 2 | 2 parallel | domain-ref §3-5 | Balanced (2A) + Fast (2B) | 25 KB | 75-80% |
| 3 | 1 planning | domain-ref §4-5 | Balanced | 25 KB | 75-77% |
| 4 | 1 task gen | domain-ref §4 | Fast | 25 KB | 88-92% |
| 5 | 1 spec gen | spec-generation §1-8 | Balanced | 25 KB | 65-70% |
| 6 | 1 test gen | test-generation §1-11 | Balanced | 25 KB | 60-65% |
| 7 | 1+1 code+runner | code-generation §1-10 | **Heavy (7A)** + Fast (7B) | 25 KB | 55-60% |
| 8 | 1 validation | domain-ref §3 | Balanced | 25 KB | 88-92% |
| **Average** | — | **~6 KB** | **Mixed** | **25 KB** | **73-78%** |

**Model-Aware Cost Savings (on top of skill-gating):**
- All-Heavy baseline: ~10,900 tokens per single task extraction
- Model-Aware (Sonnet/Opus): ~7,150 tokens per single task extraction
- **Additional savings: ~34% token cost reduction from model selection alone**
- Combined with phase-gated skill loading: **~75% total optimization vs naive approach**

---

## Implementation Notes

Each phase worker is designed to run independently:
- No state coupling between workers
- Results passed via artifacts (files)
- Orchestrator coordinates sequencing and state file writes
- Workers never call each other
- Workers NEVER write to forge-state.json

This enables:
✅ Parallel execution within phases (1A, 1B, 1C, 1D all at once)
✅ Independent testing of each worker
✅ Easy debugging (artifacts show intermediate results)
✅ Resume capability (read artifacts if phase interrupted)
✅ Rollback safety (artifacts are disposable, state file is authoritative)
