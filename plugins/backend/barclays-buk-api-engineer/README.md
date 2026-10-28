# barclays-buk-api-engineer

Ensures APIs and business logic are fully decoupled from screens and channels. Defines contracts, builds endpoints, generates documentation, and aligns to the domain model. Supports two service types: **DAF** (Spring Boot 3 microservices from a markdown spec) and **sMesh** (Spring Boot 3 from an OpenAPI 3.x spec).

## Workflow Position

```
Solution Architect → API Engineer → Quality Engineer / Security Architect 
```

---

## Agentic Invocation

From version 1.2.0 this plugin exposes a single agentic entry point — `api-engineer-agentic-agent` — that orchestrator agents can invoke without command-level knowledge or direct user interaction.

### How orchestrators discover this plugin

Orchestrators should invoke `barclays-buk-api-engineer:api-engineer-agentic-agent` when they need any of the following:

| Detected need | Capability routed |
|---|---|
| New DAF microservice from a markdown specification | DAF Generate |
| New Spring Boot 3 project from an OpenAPI spec | sMesh Generate |
| OpenAPI spec validation against Barclays standards | Spec Validate |
| Portal-readiness verification (CISO + BAN) | OAS Verify |
| OpenAPI spec designed from requirements | OAS Design |
| Existing OpenAPI spec needs new operations | OAS Update |
| Existing generated project needs targeted changes | sMesh Refine |
| Generated project has compile/test/coverage failures | Project Fix |
| Test-first (TDD) Spring Boot 3 generation | TDD Generate |

### Minimal orchestrator invocation

```
Run barclays-buk-api-engineer:api-engineer-agentic-agent with:

JIRA_ID:            {ticket id}
INTENT:             {free text describing what needs to be done}
SPEC_PATH:          {path to OpenAPI spec, or "none"}
SPEC_TYPE:          daf | smesh | "auto" (default: "auto" — set explicitly to bypass heuristic classification)
OPERATION:          generate | validate | refine | fix | design | update | verify | "auto"
                    (default: "auto" — set explicitly for deterministic operation selection)
SERVICE_SPEC_PATH:  {path to DAF markdown spec, or "none"}
PROJECT_PATH:       {path to existing project, or "none"}
OUTPUT_PATH:        {target directory, or "none"}
REQUIREMENTS_PATH:  {path to requirements doc, or "none"}
ADDITIONAL_INPUT:   {supplementary context, or "none"}
FLAGS:              {--full-automation | --tdd | --detailed | "none"}
```

Only `INTENT` is required. All other inputs are optional — the agent applies defaults and reports any assumptions in its `## Flags` section. Setting both `SPEC_TYPE` and `OPERATION` explicitly is **recommended** for orchestrators to ensure deterministic routing — this bypasses all heuristic classification and goes directly to Step 0.1 with 100% confidence.

### Agentic vs command-based invocation

Both invocation styles work and are fully backwards compatible:

| Style | When to use |
|---|---|
| **Agentic** (`api-engineer-agentic-agent`) | Orchestrator agents, automated pipelines, multi-plugin workflows |
| **Command** (`/barclays-buk-api-engineer:create …`) | Direct user invocation from a terminal or IDE |

The agentic agent delegates through the same workflow pipelines that underpin the commands. sMesh Generate and TDD Generate route through `commands/workflows/generate.md` and `commands/workflows/tdd.md` respectively, ensuring the full orchestration pipeline (spec parsing, standards validation, configuration, SDK integration, compilation) runs identically regardless of invocation style. Other capabilities (Spec Validate, OAS Verify, etc.) delegate to the same sub-agents. The capability-to-command mapping in the agent file shows the exact equivalence for each route.

### Classification and Diagnostics (v1.4.0+)

The agentic agent uses a multi-phase classification system to ensure intent is correctly identified before execution begins:

1. **Step -1 — Input Normalisation**: Trims whitespace, lowercases `SPEC_TYPE` and `OPERATION`, validates against allowed values, and detects input conflicts. Fails fast on unsupported values.
2. **Step 0 — Explicit Override** (three-tier resolution): When `SPEC_TYPE` is `daf` or `smesh`, classification is resolved within Step 0 with 100% confidence — it **never** falls through to signal scoring.
   - **Step 0.1 — OPERATION-based**: When both `SPEC_TYPE` and `OPERATION` are explicit (e.g. `smesh` + `generate`), the capability is resolved directly from a lookup table. **This is the most reliable invocation method for orchestrators.**
   - **Step 0.2 — INTENT keyword**: When `OPERATION` is `"auto"`, the existing keyword table matches INTENT words to capabilities within the declared SPEC_TYPE.
   - **Step 0.3 — Default**: When neither OPERATION nor keywords resolve, defaults apply: `daf` → DAF Generate, `smesh` → sMesh Generate.
3. **Step 1 — Confidence Scoring** (only when SPEC_TYPE is `"auto"`): All 9 capabilities are scored simultaneously using positive and negative signals extracted from the intent and input paths. Each capability accumulates points from matching signals and loses points from contradicting signals. The highest-scoring capability above its minimum threshold wins.
4. **Step 1.3 — Intent Confirmation Gate**: For ambiguous classifications (winning score < 70 or gap to runner-up < 20), the agent pauses and outputs an Intent Classification Result block. In `--full-automation` mode or when confidence is high, the agent proceeds without pausing.

**Trace ID:** Every invocation generates a trace ID (`{JIRA_ID}-{epoch}`). This ID appears in the routing banner, all log lines, the run summary, and is passed to sub-agents via the `TRACE_ID` parameter for cross-invocation correlation.

**Structured Logging:** Logs are written in JSON format to `{OUTPUT_PATH}/logs/api-engineer-agentic.log`. Each line includes the trace ID, event type, and structured data including classification confidence scores, runner-up alternatives, and execution duration.

**Execution Timeline:** The Agent Run Summary includes a step-by-step execution timeline with timestamps and total duration for each invocation.

### Reading the Flags section

The Flags section in every agent response includes classification diagnostics: winning capability, confidence score, runner-up, negative signals applied, and the score gap. A gap < 20 between winner and runner-up indicates the classification was close — inspect the diagnostics if the selected capability seems incorrect. To resolve ambiguity, re-invoke with `SPEC_TYPE` set explicitly.

---

## Commands

### Routing & Orchestration

| Command | Purpose |
|---|---|
| `create` | Primary entry point — routes to DAF or sMesh based on `--type` input; supports `--tdd` flag for test-first generation |

### DAF Commands (Spring Boot 3 from Markdown Specification)

| Command | Purpose |
|---|---|
| `create --type daf` | Generate a complete DAF microservice with automatic testing, coverage validation, and environment-specific config |
| `workflows:generate` | Multi-wave orchestrated generation with 6 phases: spec analysis → build config → core services → business logic → testing → validation |
| `workflows:validate` | Compliance gatekeeper — 19 red-flag checks before DAF service approval |
| `workflows:fix` | Autonomous healing for DAF services — compile errors, test failures, coverage gaps, SDK3 pattern violations |
| `workflows:tdd` | DAF test-first generation — RED (failing tests) → GREEN (implementation) → REFACTOR (self-correcting loop) |
| `workflows:refine` | Targeted updates to existing DAF services — add features, update models, merge spec changes |

### sMesh Commands (Spring Boot 3 from OpenAPI 3.x Specification)

| Command | Purpose |
|---|---|
| `generate` | Generate a Spring Boot 3 project from an OpenAPI 3.x spec with phased execution and resumption support |
| `validate` | Validate OpenAPI specs without code generation — OAS syntax + Barclays standards compliance |
| `refine` | Iteratively update a previously generated sMesh project — add endpoints, producers, update models |
| `tdd` | sMesh test-first generation — RED → GREEN → REFACTOR cycle |
| `fix` | Diagnose and fix failures in any generated project (compile, tests, coverage, SDK3 patterns, hexagonal boundaries) |

---

## `barclays-buk-api-engineer:create`

The primary entry point. Takes a Jira ticket and a service type, then routes to the appropriate workflow.

### Inputs

| Input | Required | Description |
|---|---|---|
| `JIRA_ID` | Yes | Jira ticket identifier, e.g. `PLATENG-1234` |
| `--type` | Yes | `daf` — Spring Boot 3 microservice from a markdown spec; `smesh` — Spring Boot 3 from an OpenAPI spec |

**Additional inputs for `--type daf`:**

| Input | Required | Description |
|---|---|---|
| `SPEC_FILE` | Yes | Path to the DAF service specification markdown file (`.md`) |
| `TARGET_DIR` | Yes | Target directory where the project will be generated |
| `--full-automation` | No | Skips all interactive prompts and makes autonomous decisions |

**Additional inputs for `--type smesh`:**

| Input | Required | Description |
|---|---|---|
| `--operation` | No | `generate`, `validate`, or `refine` — prompted interactively if omitted |
| *(see per-operation inputs below)* | | |

### Outputs

**For `--type daf`:**

A fully built, tested, and validated Spring Boot 3 DAF microservice at `TARGET_DIR/SERVICE_NAME/`, including:

| Artefact | Description |
|---|---|
| `build.gradle`, `settings.gradle`, `gradle.properties` | Gradle 8 build configuration using the DAF starter plugin |
| `daf-dependencies.gradle` | DAF module dependencies |
| `src/main/java/…` | Application, controllers, services, gateways, models, DTOs, error codes, AOP aspects, session management |
| `src/test/groovy/…` | Spock unit tests (90%+ line, branch, and mutation coverage) |
| `src/integrationTest/…` | Karate integration tests with WireMock stubs |
| `oas/openapi.yaml` | OpenAPI 3.0.3 specification |
| `{SERVICE_NAME}-config/` | Config repository with environment-specific properties (SIT, OAT, Prod) |
| `logs/daf-engineer.log` | Full generation log |

Build quality gates enforced before delivery:
- `./gradlew compileJava` — must pass (Wave 2)
- JaCoCo line coverage ≥ 90%, branch coverage ≥ 90% (Wave 3)
- Pitest mutation score ≥ 90% (Wave 3)
- 19 red-flag validation checks — must all pass (Wave 4)
- `./gradlew clean build test` — full golden gate (Wave 5)

**For `--type smesh`:** see per-operation outputs below.

### Usage Examples

```bash
# DAF microservice
/barclays-buk-api-engineer:create PLATENG-1234 --type daf ./my-service-spec.md /path/to/output

# DAF — full automation mode (no prompts)
/barclays-buk-api-engineer:create PLATENG-1234 --type daf ./spec.md ./my-service --full-automation

# sMesh — interactive operation selection
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh

# sMesh — generate (all args explicit)
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation generate ./api.yaml \
  --output ./my-project --package com.barclays.api --artifact my-service

# sMesh — validate spec
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation validate ./api.yaml --detailed

# sMesh — refine existing project
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation refine ./my-project \
  --add-endpoint /payments POST
```

---

## DAF Service Generation Workflow

DAF (Domain-Aligned Framework) services are Spring Boot 3 microservices generated from markdown specifications. The workflow is orchestrated through **6 waves**:

| Wave | Phase | Description |
|---|---|---|
| **0** | Spec Analysis | Parse markdown spec, extract domain model, service metadata, endpoint contracts |
| **1** | Build Configuration | Rename template packages, configure Gradle build, set DAF plugin versions, uncomment modules |
| **2** | Core Services | Generate JPA models, DTOs, controllers, service interfaces, implementations, gateways, AOP aspects |
| **3** | Quality Gates | JaCoCo line + branch coverage ≥90%, Pitest mutation score ≥90%, auto-generate missing tests |
| **4** | Compliance Validation | 19 red-flag checks: package consistency, template residuals, SDK3 patterns, build minimality, test coverage, integration completeness |
| **5** | Golden Gate Build | Full `./gradlew clean build test` — all sources compiled, all tests passing, all downstream APIs stubbed (WireMock) |

**Key DAF Features:**
- **Environment-specific config repo** — SIT, OAT, Prod properties auto-generated
- **AOP interceptor aspects** — Custom `@Around` annotations for cross-cutting concerns
- **Session management** — DafSessionManagementService with session key enums and session beans
- **Karate integration tests** — Full feature files with WireMock stubs, TestRunner, and DataUtils
- **SDK3 compliance** — RestResponse.assemble() pattern, LoggerSlf4jImpl, ErrorCode enums, segment codes

---

## sMesh Service Generation Workflow

sMesh services are Spring Boot 3 microservices generated from OpenAPI 3.x specifications. The workflow supports **phased execution** with resumption:

| Phase | Description |
|---|---|
| `parse` | Extract semantic model from OpenAPI spec |
| `standards` | Validate against Barclays API standards (OAS, Coding, Naming) |
| `configure` | Collect package, artifact, and configuration inputs |
| `generate:gradle` through `generate:readme` | Generate all source files (controllers, services, gateways, models, tests, CI/CD) |
| `sdk` | Integrate 7 SDK modules via org-sdk-integration plugin |
| `validate-sdk` | Re-run code-pattern compliance after SDK integration |
| `compile` | Verify Gradle compilation and test execution |

**Key sMesh Features:**
- **Resumable phases** — Stop and resume at any phase via `--phase` and `--from-phase` flags
- **Modular SDK integration** — 7 optional SDK modules applied automatically
- **TDD support** — Write failing contract tests first (RED), generate code (GREEN), auto-fix until pass (REFACTOR)
- **Incremental refinement** — Add endpoints, producers, update models, merge spec changes without full regeneration
- **Full test generation** — Unit tests (MockMvc), integration tests (Karate), coverage targets (90%+)

---

## DAF Workflow Commands

### `barclays-buk-api-engineer:workflows:generate` (DAF)

Orchestrates the complete DAF service generation through 6 waves: spec analysis → build config → core services → quality gates → compliance validation → golden gate build.

#### Inputs

| Input | Required | Description |
|---|---|---|
| `JIRA_ID` | Yes | Jira ticket identifier, e.g. `BUKAPISERV-1234` |
| `SPEC_FILE` | Yes | Path to the DAF service specification markdown file (`.md`) |
| `TARGET_DIR` | Yes | Target directory where the project will be generated |
| `--full-automation` | No | Skips all interactive prompts and makes autonomous decisions |
| `--max-cycles` | No | Self-correction retry budget for quality gates (default: 5) |

#### Outputs

A fully qualified DAF microservice at `TARGET_DIR/SERVICE_NAME/` including:

- Gradle 8 build (DAF starter plugin, configured modules)
- JPA entities, DTOs with hand-written builders, exception hierarchies
- Spring REST controllers with DafHeadersContext
- Service interfaces + implementations, gateways, repositories
- AOP aspect classes with custom interceptor annotations
- Session management service (DafSessionManagementService, session beans)
- Spock BDD unit tests (90%+ coverage), Karate integration tests with WireMock stubs
- OpenAPI 3.0.3 specification
- Environment-specific config repo (SIT, OAT, Prod)
- Full generation log (`logs/daf-engineer.log`)

#### Quality Gates

- Wave 2: `./gradlew compileJava` ✓
- Wave 3: JaCoCo ≥90% line + branch, Pitest ≥90% mutation (auto-generate tests if needed)
- Wave 4: 19 compliance checks (package consistency, template residuals, SDK3 patterns, etc.)
- Wave 5: `./gradlew clean build test` golden gate

#### Usage Examples

```bash
# Full DAF generation
/barclays-buk-api-engineer:workflows:generate BUKAPISERV-1234 ./my-service-spec.md /path/to/output

# Full automation
/barclays-buk-api-engineer:workflows:generate BUKAPISERV-1234 ./spec.md ./my-service --full-automation

# Extended quality gate budget
/barclays-buk-api-engineer:workflows:generate BUKAPISERV-1234 ./spec.md ./my-service --max-cycles 10
```

---

### `barclays-buk-api-engineer:workflows:validate` (DAF)

Post-generation compliance validator — reads the generated DAF service and performs 19 red-flag checks before approval.

#### Inputs

| Input | Required | Description |
|---|---|---|
| `PROJECT_PATH` | Yes | Path to generated DAF service root |

#### Outputs

| Section | Description |
|---|---|
| Package Consistency | All Java classes use correct basePackage and domain structure |
| Template Residuals | No `{{placeholder}}` or template boilerplate remains |
| SDK3 Compliance | RestResponse usage, SLF4J logging, ErrorCode enums, segment codes |
| Build Configuration | Gradle build is minimal and correct |
| Test Coverage | Line coverage ≥90%, branch coverage ≥90% (via JaCoCo) |
| Mutation Coverage | Mutation score ≥90% (via Pitest) |
| Integration Tests | Karate feature files complete, WireMock stubs present |
| Build Verification | `./gradlew compileJava` and `./gradlew build` both pass |

Returns: **APPROVED** or **REJECTED** with detailed findings.

#### Usage Examples

```bash
# Validate generated service
/barclays-buk-api-engineer:workflows:validate ./my-service-output/ServiceName
```

---

### `barclays-buk-api-engineer:workflows:fix` (DAF)

Autonomous healing for DAF services — diagnoses and fixes failures without regeneration.

#### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `PROJECT_PATH` | Yes | — | Path to DAF service root |
| `--mode` | No | `all` | `compile` \| `tests` \| `coverage` \| `patterns` \| `all` |
| `--max-cycles` | No | `5` | Maximum fix attempts per mode |

#### Fix Modes

| Mode | Description |
|---|---|
| `compile` | Fix Java compile errors (missing imports, type mismatches) |
| `tests` | Fix failing test classes (missing mocks, wrong assertions, missing Spring beans) |
| `coverage` | Add targeted tests to reach 90%+ JaCoCo coverage |
| `patterns` | Fix SDK3 violations (SLF4J→LoggerSlf4jImpl, ResponseEntity→RestResponse, ErrorCode patterns) |
| `all` | Run all modes sequentially |

#### Usage Examples

```bash
# Fix everything
/barclays-buk-api-engineer:workflows:fix ./my-service

# Fix only compile errors
/barclays-buk-api-engineer:workflows:fix ./my-service --mode compile

# Fix coverage gaps
/barclays-buk-api-engineer:workflows:fix ./my-service --mode coverage --max-cycles 8
```

---

### `barclays-buk-api-engineer:workflows:tdd` (DAF)

DAF test-first generation — RED → GREEN → REFACTOR cycle.

#### Inputs

| Input | Required | Description |
|---|---|---|
| `JIRA_ID` | Yes | Jira ticket identifier |
| `SPEC_FILE` | Yes | Path to DAF markdown specification |
| `TARGET_DIR` | Yes | Target output directory |
| `--max-cycles` | No | Self-correction budget (default: 5, range: 1–10) |
| `--full-automation` | No | Skip all interactive prompts |

#### TDD Phases

| Phase | Agent | Description |
|---|---|---|
| **RED** | `tdd-test-writer-agent` | Write failing contract tests from markdown spec — must compile but fail |
| **GREEN** | `daf-orchestrator-agent` | Generate full DAF service with tests already present — forces implementation of test contracts |
| **REFACTOR** | `self-correcting-agent` | Iterate up to `--max-cycles` times: compile → run tests → coverage → fix SDK3 patterns → validate → repeat |

#### Usage Examples

```bash
# Full TDD generation
/barclays-buk-api-engineer:workflows:tdd BUKAPISERV-1234 ./spec.md ./my-service

# Extended self-correction
/barclays-buk-api-engineer:workflows:tdd BUKAPISERV-1234 ./spec.md ./my-service --max-cycles 10 --full-automation
```

---

### `barclays-buk-api-engineer:workflows:refine` (DAF)

Targeted updates to existing DAF services — add features, update models, merge spec changes.

#### Inputs

| Input | Required | Description |
|---|---|---|
| `PROJECT_PATH` | Yes | Path to previously generated DAF service |
| `--add-endpoint PATH METHOD` | One of these | Add new endpoint, e.g. `--add-endpoint /payments POST` |
| `--add-gateway API_NAME` | | Add a new downstream API gateway integration |
| `--update-model MODEL_NAME` | | Regenerate a specific entity or DTO |
| `--spec SPEC_FILE` | | Merge an updated markdown spec |

#### Outputs

Modified source files + updated `.claude/daf-state.json`.

#### Usage Examples

```bash
# Add endpoint
/barclays-buk-api-engineer:workflows:refine ./my-service --add-endpoint /search GET

# Merge spec
/barclays-buk-api-engineer:workflows:refine ./my-service --spec ./updated-spec.md
```

---

## sMesh Service Generation Workflow

### `barclays-buk-api-engineer:generate` (sMesh)

Generates a production-ready Spring Boot 3 project from an OpenAPI 3.x specification.

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `SPEC_PATH` | Yes | — | Path to an OpenAPI 3.x `.yaml`, `.yml`, or `.json` file (or directory containing one) |
| `--output` | No | Current directory | Output directory for the generated project |
| `--package` | No | Prompted | Base Java package, e.g. `com.barclays.api` |
| `--artifact` | No | Prompted | Artifact/application name, e.g. `my-service` |
| `--version` | No | `1.0.0-SNAPSHOT` | Application version |
| `--db` | No | `no` | Include database layer: `yes` or `no` |
| `--api-class` | No | Auto-detected or `internal` | API classification: `internal` or `external`. Auto-derived from `API Type:` in the OAS `info.description` when present — see [API Classification Auto-Detection](#api-classification-auto-detection). |
| `--full-automation` | No | — | Skip all interactive prompts |
| `--phase` | No | — | Run only a single phase (e.g. `parse`, `generate`, `sdk`, `compile`) |
| `--from-phase` | No | — | Resume from a specific phase onwards |

### API Classification Auto-Detection

The generate workflow inspects the `info.description` field of the OAS file for an `API Type:` declaration. When found, the `api_classification` is derived automatically — no prompt is shown and the `--api-class` flag is not required.

**Mapping:**

| `info.description` value | `api_classification` |
|---|---|
| `External` | `external` |
| `Process` | `internal` |
| `Internal` | `internal` |
| `Domain` | `internal` |
| _(absent or unrecognised)_ | User is prompted (or `internal` in full-automation) |

Detection is **case-insensitive** — `external`, `EXTERNAL`, and `External` all resolve to `external`.

**Example OAS snippet:**
```yaml
info:
  title: Customer Accounts API
  version: 1.0.0
  description: |
    Manages customer account data.

    API Type: External
```

When detected, a notice is displayed during generation:
```
ℹ️  API classification auto-detected from spec: external (source: API Type: External in info.description)
```

The explicit `--api-class` flag always takes precedence over auto-detection. The `api_classification_source` field in `.claude/api-engineer-state.json` records which source resolved the value.

### Outputs

A complete Spring Boot 3 project at `OUTPUT_PATH/`, including:

| Artefact | Description |
|---|---|
| `build.gradle`, `buildSrc/`, `gradle.properties` | Gradle 8.13 build configuration |
| `src/main/java/…` | Controllers, services (interface + impl), gateways (interface + impl), models, application config |
| `src/test/java/…` | Unit and integration test classes |
| `.gitlab-ci.yml`, `project_metadata.yml` | CI/CD pipeline configuration |
| `README.md` | Generated project documentation including Barclays standards compliance report |
| `.claude/api-engineer-state.json` | State file enabling phase resumption |
| `.claude/generation.log` | Full generation log |

SDK integration (7 modules via `org-sdk-integration`) is applied automatically after code generation.

### Phase Reference

| Phase | Description |
|---|---|
| `parse` | Extract semantic model from the OpenAPI spec |
| `standards` | Validate against Barclays API standards |
| `configure` | Collect package, artifact, and configuration inputs |
| `generate` | Generate all source files (all sub-phases) |
| `generate:gradle` — `generate:readme` | Individual code generation sub-phases |
| `sdk` | Integrate organisation SDK modules |
| `validate-sdk` | Re-run code-pattern compliance after SDK integration |
| `compile` | Verify Gradle compilation |

### Usage Examples

```bash
# Full generation
/barclays-buk-api-engineer:generate ./api.yaml --output ./my-project \
  --package com.barclays.api --artifact my-service

# Full automation for CI/CD
/barclays-buk-api-engineer:generate ./api.yaml --full-automation

# Parse spec only
/barclays-buk-api-engineer:generate ./api.yaml --output ./my-project --phase parse

# Resume from SDK integration
/barclays-buk-api-engineer:generate ./api.yaml --output ./my-project --from-phase sdk
```

---

## `barclays-buk-api-engineer:validate` (sMesh)

Validates an OpenAPI 3.x specification for OAS syntax compliance and Barclays API standards compliance without generating any code.

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `SPEC_PATH` | Yes | — | Path to an OpenAPI 3.x `.yaml`, `.yml`, or `.json` file (or directory) |
| `--detailed` | No | — | Show all individual findings in the report |
| `--api-type` | No | `internal` | API classification: `internal` or `external` |

### Outputs

A combined validation report to the console:

| Section | Description |
|---|---|
| OAS Syntax Compliance | Format, structure, and reference validation |
| Barclays API Standards | OAS Specification Standard, API Coding Standard, API Naming Standard |
| Combined Summary | Overall PASS / WARN / FAIL with error and warning counts |

Exit status: `PASS` (no errors), `WARN` (warnings only), or `FAIL` (one or more errors).

### Usage Examples

```bash
# Basic validation
/barclays-buk-api-engineer:validate ./api.yaml

# Detailed report for an external API
/barclays-buk-api-engineer:validate ./api.yaml --api-type external --detailed

# Validate a directory of specs
/barclays-buk-api-engineer:validate ./specs --api-type internal
```

---

## `barclays-buk-api-engineer:refine` (sMesh)

Iteratively updates a previously generated Spring Boot 3 project: adds endpoints, adds producer APIs, updates models, or merges an updated specification.

### Inputs

| Input | Required | Description |
|---|---|---|
| `PROJECT_PATH` | Yes | Path to a previously generated Spring Boot 3 project (must contain `build.gradle` and `.claude/api-engineer-state.json`) |
| `--add-endpoint PATH METHOD` | One of these | Add a new endpoint, e.g. `--add-endpoint /users POST` |
| `--add-producer SPEC_PATH` | | Add a producer API from a spec file |
| `--update-model MODEL_NAME` | | Regenerate a specific model class |
| `--spec SPEC_PATH` | | Merge an updated OpenAPI spec into the project |

At least one change flag is required.

### Outputs

Modified source files in the existing project, plus:

| Artefact | Description |
|---|---|
| Updated Java source files | Controllers, services, gateways, models as required by the change |
| Updated `.claude/api-engineer-state.json` | State file reflecting the refinement |
| Console summary | List of files modified, compilation status, Barclays standards result (if a spec was consumed) |

### Usage Examples

```bash
# Add a new endpoint
/barclays-buk-api-engineer:refine ./my-service --add-endpoint /products POST

# Add a producer API
/barclays-buk-api-engineer:refine ./my-service --add-producer ./vendor-api.yaml

# Update a model
/barclays-buk-api-engineer:refine ./my-service --update-model User

# Merge an updated spec
/barclays-buk-api-engineer:refine ./my-service --spec ./api-v2.yaml

# Multiple changes at once
/barclays-buk-api-engineer:refine ./my-service --add-endpoint /search GET --add-producer ./search-api.yaml
```

---

## `barclays-buk-api-engineer:tdd` (sMesh)

Generates a Spring Boot 3 project using test-driven development. Tests are written first against the API contract (RED), then implementation is generated to satisfy them (GREEN), then a self-correcting loop runs until all tests pass (REFACTOR).

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `SPEC_PATH` | Yes | — | Path to an OpenAPI 3.x `.yaml`, `.yml`, or `.json` file |
| `--output` | No | Current directory | Output directory for the generated project |
| `--package` | No | Prompted | Base Java package, e.g. `com.barclays.api` |
| `--artifact` | No | Prompted | Artifact/application name |
| `--version` | No | `1.0.0-SNAPSHOT` | Application version |
| `--db` | No | `no` | Include database layer: `yes` or `no` |
| `--api-class` | No | Auto-detected or `internal` | API classification: `internal` or `external`. Auto-derived from `API Type:` in `info.description` when present. |
| `--max-cycles` | No | `5` | Maximum self-correction cycles (1–10) |
| `--full-automation` | No | — | Skip all interactive prompts |

### Outputs

Same as `generate`, plus:

| Artefact | Description |
|---|---|
| `src/test/java/…/*TddTest.java` | Contract tests written before implementation (replaced by full tests after GREEN phase) |
| `.claude/tdd-state.json` | TDD cycle state (phase, cycle count, metrics) |

### TDD Phases

| Phase | Description |
|---|---|
| **RED** | `tdd-test-writer-agent` writes failing contract tests from the spec. Tests must compile but fail. |
| **GREEN** | `project-generation-agent` generates all production code with tests already present. |
| **REFACTOR** | `self-correcting-agent` iterates up to `--max-cycles` times fixing compile errors, test failures, coverage gaps, and pattern violations. |

### Usage Examples

```bash
# Full TDD generation
/barclays-buk-api-engineer:tdd ./api.yaml --output ./my-project \
  --package com.barclays.api --artifact my-service

# Full automation
/barclays-buk-api-engineer:tdd ./api.yaml --output ./my-project --full-automation

# Extended self-correction budget
/barclays-buk-api-engineer:tdd ./api.yaml --output ./my-project --max-cycles 10

# Via create command
/barclays-buk-api-engineer:create PLATENG-5678 --type smesh --operation generate ./api.yaml \
  --output ./my-project --tdd --max-cycles 8
```

---

## `barclays-buk-api-engineer:fix`

Diagnoses and fixes failures in a previously generated Spring Boot 3 project. Applies surgical, targeted fixes without regenerating the project.

### Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `PROJECT_PATH` | Yes | — | Path to a Spring Boot project root (must contain `build.gradle`) |
| `--mode` | No | `all` | What to fix: `compile` \| `tests` \| `coverage` \| `patterns` \| `hexagonal` \| `all` |
| `--max-cycles` | No | `5` | Maximum fix attempts per category |

### Fix Modes

| Mode | Description |
|---|---|
| `compile` | Fix Java compile errors (missing imports, type mismatches, method signature mismatches) |
| `tests` | Fix failing test classes (missing mocks, wrong assertions, missing Spring beans) |
| `coverage` | Add targeted tests to bring JaCoCo line and branch coverage to 90%+ |
| `patterns` | Fix SDK3 pattern violations (SLF4J→LogFactory, ResponseEntity→RestResponse, etc.) |
| `hexagonal` | Fix hexagonal layer boundary violations: `@Autowired` field injection, controller bypassing service to call gateway directly, service instantiating concrete adapter classes |
| `all` | Run all modes in sequence: compile → tests → coverage → patterns → hexagonal |

### Outputs

| Artefact | Description |
|---|---|
| Modified source files | Targeted fixes in place — no regeneration |
| Console report | Fix summary: what was fixed, what remains, metrics |

### Usage Examples

```bash
# Fix everything
/barclays-buk-api-engineer:fix ./my-project

# Fix only compile errors
/barclays-buk-api-engineer:fix ./my-project --mode compile

# Fix test failures with extended budget
/barclays-buk-api-engineer:fix ./my-project --mode tests --max-cycles 8

# Fix coverage gaps
/barclays-buk-api-engineer:fix ./my-project --mode coverage

# Fix SDK3 pattern violations
/barclays-buk-api-engineer:fix ./my-project --mode patterns
```

---

## Model Strategy

Agents are assigned the smallest model capable of their task. This keeps token costs proportional to actual complexity.

| Model | Used for | Agents |
|---|---|---|
| **haiku** | Routing, decision lookup, structured rule checking, format validation | `daf-orchestrator-agent`, `tdd-orchestrator-agent`, `auto-decision-agent`, `clarification-checkpoint-agent`, `daf-validation-agent`, `spec-validation-agent` |
| **sonnet** | Code generation, complex analysis, standards validation, self-correction | All DAF worker agents, `project-generation-agent`, `refinement-agent`, `sdk-integration-invoker-agent`, `barclays-standards-validation-agent`, `spec-parsing-agent`, `api-engineer-agent`, `tdd-test-writer-agent`, `self-correcting-agent` |

**Rationale by agent class:**

- **Orchestrators** (`daf-orchestrator-agent`): Follow a fixed wave state machine — route, spawn, wait, log. No generation. Haiku follows structured instructions reliably at low cost.
- **Decision agents** (`auto-decision-agent`, `clarification-checkpoint-agent`): Lookup a pattern or collect a value. Deterministic, short context. Haiku.
- **Validation-only agents** (`daf-validation-agent`, `spec-validation-agent`): Read-only rule checkers. Pattern matching against known rules — no creative generation required. Haiku.
- **Standards validation** (`barclays-standards-validation-agent`): Multi-rule Barclays compliance analysis across a full OAS spec. Needs deeper reasoning than pure syntax checking. Sonnet.
- **Code generation workers** (all DAF workers, `project-generation-agent`, `refinement-agent`): Write complete Java classes with complex patterns, DAF SDK3 constraints, and coverage requirements. Sonnet is the right balance of quality and cost for generation tasks.
- **SDK invoker** (`sdk-integration-invoker-agent`): Invokes a plugin and interprets structured output — no code generation of its own. Sonnet (reads complex Gradle output).
- **TDD orchestrator** (`tdd-orchestrator-agent`): Drives RED→GREEN→REFACTOR phase transitions — fixed state machine, spawn-and-wait only. No code written. Haiku.
- **TDD test writer** (`tdd-test-writer-agent`): Generates contract test classes from spec with precise assertions. Requires code generation quality. Sonnet.
- **Self-correcting agent** (`self-correcting-agent`): Reads compiler errors, test failures, and JaCoCo reports; applies targeted multi-file fixes; iterates until pass or budget exhausted. Requires deep reasoning over real code. Sonnet.

## Agents

| Agent | Type | Model | Purpose |
|---|---|---|---|
| `api-engineer-agent` | General | sonnet | Designs and implements API contracts and business logic aligned to the BUK domain model |
| `daf-orchestrator-agent` | DAF | haiku | Hub orchestrator — manages 6 generation waves and delegates to worker agents |
| `daf-build-agent` | DAF | sonnet | Configures Gradle build files from the spec |
| `daf-config-agent` | DAF | sonnet | Generates Application.java, config classes, application.properties |
| `daf-model-agent` | DAF | sonnet | Generates model classes, DTOs, and exception types |
| `daf-config-repo-agent` | DAF | sonnet | Generates the environment-specific config repository |
| `daf-oas-agent` | DAF | sonnet | Generates the OpenAPI 3.0.3 specification |
| `daf-service-agent` | DAF | sonnet | Generates service interfaces, implementations, and gateways |
| `daf-controller-agent` | DAF | sonnet | Generates controllers and header context classes |
| `daf-module-agent` | DAF | sonnet | Integrates optional DAF modules (JWT, session, AEM cache, BCAG, etc.) |
| `daf-compliance-fixer-agent` | DAF | sonnet | Post-generation compliance fixer (ResponseEntity→RestResponse, SLF4J→SDK3 Logger, etc.) |
| `daf-test-agent` | DAF | sonnet | Generates Spock unit tests and Karate integration tests |
| `daf-validation-agent` | DAF | haiku | Validates the generated service against 19 red-flag compliance checks |
| `daf-aspect-sub-agent` | DAF | sonnet | Generates AOP aspects and custom interceptor annotations |
| `daf-gateway-sub-agent` | DAF | sonnet | Generates gateway interface and implementation classes |
| `daf-impl-sub-agent` | DAF | sonnet | Generates service implementation classes |
| `daf-session-sub-agent` | DAF | sonnet | Generates session management service and session beans |
| `auto-decision-agent` | DAF | haiku | Autonomous decision-maker for resolving ambiguity during generation |
| `spec-parsing-agent` | sMesh | sonnet | Extracts semantic model from OpenAPI 3.x specs |
| `spec-validation-agent` | sMesh | haiku | Validates OAS syntax and format compliance |
| `barclays-standards-validation-agent` | sMesh | sonnet | Validates specs against Barclays API standards (OAS Spec, Coding, Naming) |
| `clarification-checkpoint-agent` | sMesh | haiku | Collects configuration interactively or from a config file |
| `project-generation-agent` | sMesh | sonnet | Generates all Spring Boot 3 project files |
| `refinement-agent` | sMesh | sonnet | Applies targeted changes to existing generated projects |
| `sdk-integration-invoker-agent` | sMesh | sonnet | Integrates the organisation SDK (7 modules) into a generated project |
| `tdd-orchestrator-agent` | sMesh/DAF | haiku | Drives RED→GREEN→REFACTOR cycle — thin orchestrator, no code generation |
| `tdd-test-writer-agent` | sMesh/DAF | sonnet | Writes failing contract tests from spec before implementation exists |
| `self-correcting-agent` | sMesh/DAF | sonnet | Fixes compile errors, test failures, coverage gaps, and SDK3 pattern violations |

## Skills

| Skill | Loaded by | Purpose |
|---|---|---|
| `domain-reference` | DAF agents | DAF framework version table, module catalog, code patterns, spec template, lessons learned |
| `barclays-api-standards` | sMesh agents | Barclays OAS Specification, API Coding, and API Naming standards |
| `code-generation` | sMesh agents | Spring Boot 3 code generation rules, Java type mappings, error handling and security patterns |
| `spec-parsing` | sMesh agents | OpenAPI 3.x parsing guide with OAS and RAML reference patterns |
| `project-structure` | sMesh agents | Spring Boot 3 project layout conventions and refinement guide |
| `gradle-configuration` | sMesh agents | Gradle 8.13 build configuration for Barclays iAPI projects |
| `gitlab-ci-cd` | sMesh agents | GitLab CI/CD pipeline configuration |
| `integration-testing` | sMesh agents | Integration testing patterns for Spring Boot 3 API projects |
| `sdk-integration-guide` | sMesh agents | Guide for integrating the Barclays organisation SDK |

## Quality Gates

**Plugin Test Score:**
- Current: PASS (COOAPIB2B-12041, fixes applied post test-plugin run — commit `083c35c`)
- Required: ≥90/100
- Last run: `cd plugins/backend/barclays-buk-api-engineer && /test-plugin .`
- Result: PASS ✓

**How to re-run:**
```bash
cd plugins/backend/barclays-buk-api-engineer
/test-plugin .
# Score must be ≥90 before committing any change to this plugin
```

**Coverage Thresholds (Wave 5 gates — enforced at generation time, not plugin test time):**
- JaCoCo line coverage: ≥90%
- JaCoCo branch coverage: ≥90%
- Pitest mutation score: ≥90%

These thresholds are enforced by `daf-orchestrator-agent` Wave 3 and Wave 4 on every generated service. They are not plugin-test thresholds — they apply to the code the plugin generates.

---

## Pilot Evidence

**API Engineer Plugin (COOAPIB2B-12041) — DAF & sMesh generation improvements**

| User | Task | Outcome | Date |
|------|------|---------|------|
| API Engineer — BUK Retail CAPL | Generate a DAF microservice end-to-end from a payments markdown spec | ✓ Service generated successfully; user flagged that `api_classification` prompt caused friction when the spec already declared `API Type:` — led to the auto-detection feature | 2026-08-18 |
| API Engineer — BUK Retail CAPL | Generate an sMesh project from an internal OpenAPI spec; review agent output | ✓ Project generated; user noted Usage Notes sections were missing from most agents, making it hard to understand what each agent had done at the end of a run — led to the usage section expansion across 29 agents | 2026-08-21 |
| API Engineer — BUK Retail CAPL | Re-run DAF generation with updated spec after review feedback | ✓ Full 6-wave pipeline completed; residual issues from first run fixed via `workflows:fix`; config and model agents improved based on output observations | 2026-08-27 |

**Key learnings:**
- Prompting the user for `api_classification` when it is already encoded in the spec `info.description` creates unnecessary friction — auto-detection from `API Type:` eliminates the question in the majority of real specs
- Agents without a Usage Notes section left users unable to audit what had been generated at the end of a run — adding a structured end-of-run report per agent significantly improved observability
- DAF wave output became clearer once each agent documented its artefacts explicitly; users could cross-reference the log against the Usage Notes to identify which agent was responsible for a given file

---

## Dependencies

- `barclays-buk-standards` — provides `api-design`, `security`, and `daf` skills

---

## Quality Gates

**Plugin Test Score (OAS command family — UNSECLAPI-7563):**
- Score: **95/100** — PASS ✅
- Required threshold: ≥90/100
- Audit date: 2026-09-02
- Issues resolved: 7 (from 88/100 baseline)
- Run: `/test-plugin ./plugins/backend/barclays-buk-api-engineer`

---

## Pilot Evidence — OAS Command Family (UNSECLAPI-7563)

> **Note for reviewers:** The pilot evidence below documents internal validation runs by the author (Neha Gurav) during development. Evidence of ≥2 additional users on real tasks should be added here before final MR approval — please tag the API Engineer and Data Engineer who tested during the sprint review.

**Internal validation runs (author):**

| Task | Input | Outcome | Date |
|---|---|---|---|
| Generate OAS from implementation LLD (AOS Open Account API) | `aos-if025-implementation-lld.wiki` | Generated 80-field spec; BAN `specificationPassed: true` on Confluence input; data-leakage RED FLAGs correctly raised for designer decisions | 2026-08-27 |
| Generate OAS from OAS attachment (Process Application Service) | `ProcessApplicationService_OpenAPI.yaml` | Correct PAS fields extracted; all 7 common-libraries headers present; path version prefix handled correctly | 2026-08-29 |
| Add endpoint to existing spec via update-oas | Confluence URL + existing OAS | Two-phase field extraction shown to user before write; confirmed correct fields written; no hallucination of unrelated API fields | 2026-08-29 |

**Key learnings from validation:**
- Two-phase generation (extract → confirm → generate) required to prevent session-context hallucination
- BAN `specificationPassed: true` achieved from Confluence input — 3 HIGH data-leakage issues are designer decisions, not spec errors
- `Bash cp -r` for common-libraries required — LLM-regenerated templates produce wrong patterns that fail BAN
