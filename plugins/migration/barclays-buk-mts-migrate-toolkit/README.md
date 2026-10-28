# barclays-buk-mts-migrate-toolkit

> **Marketplace:** `plugins/migration/barclays-buk-mts-migrate-toolkit/`  
> **Dependencies:** barclays-buk-standards  
> **JIRA:** CPSUBPOD01-23452

MTS service discovery, API replacement matching, and migration code generation for BUK Spring Boot codebases.

## Overview

This plugin automates the end-to-end migration of mainframe-integrated MTS services to modern ODS APIs. It scans a BUK Spring Boot codebase to document every `doService()` call (MCA1 framework) and `callService()` call (MCA2 framework), with automatic framework detection for MCA1, MCA2, or hybrid repos. It searches Backstage live catalogue, GitLab source repos, and Confluence for candidate replacement APIs with confidence-scored matching (including gateway-equivalence and DB-table-equivalence boosts), and generates dual-path migration code with feature-flag routing, converters, tests, and an issues document.

Key capabilities:

- **Three-stage pipeline** — document, match, migrate as sequential commands
- **MCA1 + MCA2 framework support** — discovers `doService()` (MCA1) and `callService()` (MCA2 MIS/BEM) with automatic framework detection
- **15 transport categories** — mainframe-mq, SOAP stub/EAO, Oracle DB, DB2, CMOD, TCV hybrid, SCV, soap-webservice (ILP/Hogan), itsu-oracle, als-backend, REST detection, and framework/reference-data-only classification
- **Variable method tracing** — traces multiplexer methods to discover all (service, method) pairs routed through a single call site
- **3 migration strategies** — new microservice (A), existing microservice (B), or in-place dual-path (C)
- **13-layer API search** — Backstage live repo, pcbcooiit (ODS sAPIs), PCBICCAPIS (process/domain APIs), COOCUSTCRM (z/OS system APIs — writes), GRPQRTUKBA (UKBA), BCDUKCAPI (Cards/Lending), EST (Open Banking), DCMDEV (DCM/Documents), APITECHDES (API Index + Digital Channels), EMMAPIS (Customer Insights), EPZOSCON (EP z/OS Connect), deep investigation
- **Gateway-equivalence scoring** — GitLab source search confirms which ODS API wraps the same EGS gateway
- **Confidence-scored matching** — multi-layer API candidate search with field overlap scoring
- **Pattern-adaptive code generation** — discovers target repo conventions (DI style, test framework, flag pattern) and generates code that matches
- **3-tier JAR extraction** — constant pool, ROP/RIP parser, and javap bytecode disassembly for compiled EGS JARs
- **MIS source repo cloning** — clones EBS/EGS source repos from GitLab for highest-fidelity TDL/DAG extraction
- **Write table extraction** — detects INSERT/UPDATE operations and extracts target table schemas for write services
- **Orchestration TDL tracing** — traces composite EBS services through sub-service calls to enumerate all TDL tables accessed
- **Autonomous FORGE orchestration** — orchestrator-worker agent hierarchy with 18 agents across 3 pipelines

## Three-Stage Pipeline

```
/mts-documentation  ->  /api-replacement-match  ->  /mts-migrate
(document service)     (find replacement API)      (generate code changes)
```

1. **`/mts-documentation`** — Scans the codebase, discovers MTS service calls, resolves constants, traces call chains, extracts mainframe transaction data from EGS JARs, and generates per-service documentation with field mappings and data lineage.
2. **`/api-replacement-match`** — Loads the service doc, searches Confluence and Backstage for candidate replacement APIs, compares fields and TDL table overlap, and produces a confidence-scored match report.
3. **`/mts-migrate`** — Reads the match report, asks the developer for strategy and response contract, generates flag-based dual-path code (MTS + API), converters, tests, and an issues document.

## Requirements

- **BUK Spring Boot codebase** with a `src/` directory
- **Python 3** (stdlib only — no external dependencies required)
- **Gradle cache populated** — run `./gradlew build` once so EBS/EGS JARs are available in `~/.gradle/caches/`

### MCP Service Dependency

The `/api-replacement-match` and `/refresh-ods-catalogue` commands require the **Confluence MCP** tools to be configured and accessible. These tools are used to search Confluence spaces for ODS API documentation pages. The **GitLab MCP** is used for Deep Fetch (spec repo discovery, gateway-equivalence verification).

| Tool | Purpose | Required By |
|------|---------|-------------|
| `mcp__Confluence__confluence_search` | Search Confluence spaces for ODS API documentation | `/api-replacement-match`, `/refresh-ods-catalogue` |
| `mcp__GitLab__search` | Search GitLab repos for OpenAPI specs and gateway references | `/api-replacement-match` (Deep Fetch) |

#### Graceful Degradation

Commands that do not require Confluence or GitLab work without them:
- `/mts-documentation` — fully local, no external dependencies
- `/mts-migrate` — reads previously generated match reports, no live Confluence/GitLab access needed

When Confluence MCP is unavailable, `/api-replacement-match` falls back to Backstage + seed catalogue only. When GitLab MCP is unavailable, Deep Fetch is skipped and response field scores are discounted as "unverified" (user is warned and offered the choice to authenticate first). `/refresh-ods-catalogue` requires Confluence and will stop with setup instructions if unavailable.

## Commands

### /mts-documentation

Generate MTS service documentation for any BUK Spring Boot codebase.

```bash
/mts-documentation [SERVICE_METHOD_NAME | PROJECT_PATH]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `SERVICE_METHOD_NAME` | positional | no | A method name (e.g., `retrievePersonalCustomerFullDetails`) or qualified name (e.g., `CustomerGateway.findByPrimaryKey`) |
| `PROJECT_PATH` | positional | no | Path to the project directory (defaults to current working directory) |

**Mode detection:**
- **No argument or a directory path** — `full` mode: documents all MTS services in the codebase
- **Method name or qualified name** — `single-service` mode: documents only the specified service

**Examples:**
```bash
# Full documentation — all services in current directory
/mts-documentation

# Full documentation — specific project path
/mts-documentation /path/to/buk-project

# Single service by method name
/mts-documentation retrievePersonalCustomerFullDetails

# Single service by qualified name
/mts-documentation CustomerGateway.findByPrimaryKey
```

**Output:** Architecture overview, service catalogue, per-service docs, code journeys, and data lineage files written to `docs/mts/`.

### /api-replacement-match

Find candidate ODS replacement APIs for an MTS mainframe service.

```bash
/api-replacement-match <ServiceName.method | service=ServiceName> [--spaces key1,key2] [--url https://...]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ServiceName.method` | positional | yes* | Method name or qualified name to match |
| `service=ServiceName` | positional | yes* | Match all methods for a service (per-service mode) |
| `--spaces` | flag | no | Additional Confluence space keys to search (comma-separated) |
| `--url` | flag | no | Direct Confluence page URL to include as a candidate |

*One of `ServiceName.method` or `service=ServiceName` is required.

**Mode detection:**
- **`service=ServiceName`** — `per-service` mode: matches all methods for the named service
- **Method name or qualified name** — `single-operation` mode: matches one specific method

**Examples:**
```bash
# Single operation match
/api-replacement-match PersonalCustomerService.retrievePersonalCustomerCoreDetails

# Per-service match (all methods)
/api-replacement-match service=PersonalCustomerService

# With additional Confluence space and direct URL
/api-replacement-match findByPrimaryKey --spaces COOCUSTCRM --url https://confluence.barcapint.com/display/pcbcooiit/Customer+API
```

**Output:** Confidence-scored match report written to `docs/mts/api-match-<ServiceName>-<method>.md`.

### /mts-migrate

Generate migration code from MTS mainframe service to a replacement API.

```bash
/mts-migrate <ServiceName.method> [--report path/to/api-match-report.md]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ServiceName.method` | positional | yes | Method name or qualified name to migrate |
| `--report` | flag | no | Path to a specific match report (auto-discovered if omitted) |

The command prompts interactively for:
1. **Migration strategy** — A (new microservice), B (existing microservice), or C (in-place dual-path)
2. **Response contract** — `mts-compat` (preserve EDO structure) or `ods-native` (use API response directly)

**Examples:**
```bash
# Basic migration (auto-discovers match report)
/mts-migrate CustomerGateway.findByPrimaryKey

# With explicit match report path
/mts-migrate findByPrimaryKey --report docs/mts/api-match-CustomerGateway-findByPrimaryKey.md
```

**Output:** Generated code, tests, and issues document. See [Migration Strategies](#migration-strategies) and [Output Artifacts](#output-artifacts) for details.

### Migration Strategies

| Strategy | Name | When to Use | What Happens |
|----------|------|-------------|--------------|
| **A** | New Microservice | Greenfield — no existing target service | Clones a GitLab template, scaffolds it, discovers patterns, generates endpoint + converters + tests |
| **B** | Existing Microservice | Target service already exists on the filesystem | Validates the target path, discovers its patterns, generates endpoint + converters + tests matching existing conventions |
| **C** | In-Place Dual-Path | Migrate within the BUK monolith | Discovers BUK repo patterns, finds the calling service class, generates flag-routed dual-path code (MTS + API) with converters + tests |

### /refresh-ods-catalogue

Refresh the ODS API seed catalogue by validating entries against live Confluence and GitLab data.

```bash
/refresh-ods-catalogue [--dry-run]
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `--dry-run` | flag | no | Print a summary of changes without writing the catalogue file |

**Prerequisites:** Confluence MCP tools must be configured and accessible.

Validates existing catalogue entries against live Confluence pages, discovers new pages, marks stale entries, and refreshes the Backstage catalogue index. The catalogue is used by `/api-replacement-match` for Layer 1 candidate lookup.

## How It Works

### Documentation Pipeline

1. **Pre-flight** — Validates `src/` exists, checks Gradle cache for EGS JARs, detects platform (macOS/Linux/Windows)
2. **Discovery** — Detects framework (MCA1/MCA2/hybrid), scans for `doService()` and `callService()` calls, resolves constants and variable method names (Pattern 3 caller tracing), traces call chains, extracts mainframe transaction data using the 3-tier JAR extraction pipeline
3. **Parallel generation** — Dispatches 7 worker agents in parallel: architecture overview, service inventory, service catalogue, per-service docs (one per service), code journeys, and data lineage
4. **Validation** — Gatekeeper agent scans all generated docs for red flags before completion

### API Matching Pipeline

1. **Load documentation** — Reads the per-service doc generated by Stage 1
2. **Probe tools** — Checks Confluence MCP availability; falls back gracefully if unavailable
3. **13-layer search** — Searches Backstage live repo (Layer 1), pcbcooiit ODS sAPIs (Layer 2), PCBICCAPIS process/domain APIs (Layer 3), COOCUSTCRM z/OS system APIs (Layer 4 — primary for writes), GRPQRTUKBA UKBA APIs (Layer 5), BCDUKCAPI Cards/Lending APIs (Layer 6), EST Open Banking (Layer 7a), DCMDEV Document/DCM APIs (Layer 7b), APITECHDES API Index + Digital Channels (Layer 7c), EMMAPIS Customer Insights (Layer 7d), EPZOSCON EP z/OS Connect (Layer 7e), plus deep investigation (Layer 8). Includes GitLab source search for gateway-equivalence and DB-table-equivalence verification.
4. **Score candidates** — Compares field names, TDL table overlap, and domain alignment; produces confidence scores
5. **Report** — Writes a structured match report with field mapping tables, data gaps, and recommendations

### Migration Pipeline

1. **Load inputs** — Reads match report and per-service documentation
2. **Strategy selection** — Prompts for strategy (A/B/C) and response contract (mts-compat/ods-native)
3. **Strategy execution** — Dispatches to strategy-specific steps (clone/scaffold for A, validate path for B, find calling class for C)
4. **Pattern discovery** — Explores the target repo to build a Pattern Profile (DI style, test framework, converter pattern, flag pattern, etc.)
5. **Response contract negotiation** — Prompts for mts-compat or ods-native response shape
6. **Code generation** — Generates API service class, converters/mappers, response models, config entries, and flag routing
7. **Compile verification** — Runs `gradlew compileJava` and fixes compilation errors
8. **Test generation** — Generates unit tests matching the target repo's test framework
9. **Test execution** — Runs `gradlew test` and fixes test failures
10. **Issues documentation** — Produces a post-migration issues doc with gaps, bugs, notification impacts, and manual follow-up items

### Resume Capability

Each pipeline stage produces JSON state files and markdown artifacts in `docs/mts/`. If a pipeline is interrupted, re-running the same command will detect existing artifacts and resume from the last completed step.

## Transport Patterns

| # | Pattern | Transport | Approx. Count |
|---|---------|-----------|---------------|
| 1 | `mainframe-mq` | IBM MQ -> CICS mainframe | ~35 services |
| 2 | `oracle-db-direct` | JDBC -> Oracle reference DB | ~3 services |
| 3 | `db2-reference` | JDBC -> DB2 | ~1 service |
| 4 | `soap-stub` | AXIS2 SOAP via StubConnector | ~25 services |
| 5 | `soap-eao` | SOAP via SoapBindingStub/Eao | Multiple |
| 6 | `cmod-odwek` | HTTP POST via CMOD classes | ~6 (other repos) |
| 7 | `tcv-hybrid` | Dual-path MQ+REST with feature flag | ~3 services |
| 8 | `scv` | SOAP to SingleCustomerView | ~1 service |
| 9 | `soap-webservice` | SOAP to ILP/Hogan backend (non-CICS) | ~2 services |
| 10 | `itsu-oracle` | ITSU framework / Oracle JDBC direct | ~1 service |
| 11 | `als-backend` | ALS datastream (DAG-based) | ~2 services |
| 12 | `already-api-rest` | Already REST (out of scope) | ~88 services |
| 13 | `already-api-direct-http` | Already HTTP (out of scope) | Various |
| 14 | `reference-data-only` | Local reference data lookup (no backend) | ~3 services |
| 15 | `framework` | Framework/ITSU session service (no tables) | ~1 service |

Patterns 1–11 are actively documented and migrated. Patterns 12–13 are detected during discovery but excluded from migration (already using modern APIs). Patterns 14–15 are classified for completeness but have no backend to migrate.

## 3-Tier JAR Extraction

When source JARs are unavailable, the toolkit falls back to compiled JAR extraction using three complementary tiers:

| Tier | Method | What It Extracts | Dependency |
|------|--------|------------------|------------|
| **1** | Constant pool parser | WMID/WMOD string constants, service names | Python stdlib only |
| **2** | ROP/RIP file parser | Authoritative field types, lengths, and cross-validation data | Python stdlib only |
| **3** | javap bytecode disassembly | Exact program/version codes, DataGroup mappings, conditional gating | Requires `javap` (JDK) |

Source JARs are preferred when available. The `extract_jar.py` orchestrator script runs all three tiers, merges results, and assigns confidence scores.

## Skills

### mts-reference

Domain knowledge for documenting and migrating BUK Spring Boot applications that integrate with mainframe services. Loaded automatically when agents encounter `doService()` (MCA1) or `callService()` (MCA2) calls, EBS/EGS framework classes, WMID/WMOD parameters, TDL table mappings, or any transport pattern.

**Skill Structure:**
- `reference/` — 26 canonical reference files (WMID-TDL mappings, DataGroup enums, mainframe programs, EBS/EGS conventions, call flow patterns, doService patterns, MCA2 patterns, service categories, SOAP/EAO patterns, CMOD/ODWEK patterns, hybrid service patterns, Backstage catalogue index, API search strategy, discovery output format, single-service mode, compiled JAR extraction tiers, ODS API catalogue, transport extraction steps, WireMock test data, API match scoring, API match search layers, per-service doc sections, discovery mainframe extraction)
- `templates/` — 4 template files (per-service doc structure, output section templates, API match report template, migration output template)
- `lessons_learned/` — 3 files (patterns, example project, lessons README)
- `scripts/` — 5 bundled extraction scripts (see [Scripts](#scripts))
- `evals/` — 1 evaluation file (evals.json)

## Scripts

### Bundled Extraction Scripts

Located in `skills/mts-reference/scripts/`. Python 3 stdlib only, no external dependencies.

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `extract_jar.py` | Full orchestrator — runs Tiers 1+2+3, merges, assigns confidence | First choice for any compiled JAR extraction |
| `jar_constant_pool.py` | Tier 1: constant pool parser | When you only need WMID/WMOD string lists quickly |
| `jar_rop_rip.py` | Tier 2: ROP/RIP parser — authoritative field types + lengths | When checking if `riprop/` directory is present |
| `jar_javap.py` | Tier 3: exact program/version codes + DataGroup mappings | When javap is available and conditional gating matters |
| `backstage_lookup.py` | Layer 1 API candidate search — static catalogue fallback | When searching for replacement API candidates (static fallback only) |

### Pipeline Scripts

Located in `scripts/`. Python 3 stdlib only, no external dependencies.

| Script | Purpose |
|--------|---------|
| `preflight_platform.py` | Detect OS, Python command, and Gradle wrapper path |
| `preflight_cache.py` | Verify Gradle cache is populated with EBS/EGS JARs |
| `preflight_compiled_jars.py` | Locate compiled JARs when source JARs are unavailable |
| `jar_find_sources.py` | Find source JARs in Gradle cache by artifact pattern |
| `jar_find_compiled.py` | Find compiled JARs in Gradle cache by artifact pattern |
| `jar_extract_command_calls.py` | Extract command class call chains from JAR |
| `jar_extract_command_compiled.py` | Extract command class data from compiled JARs |
| `jar_extract_dto_fields.py` | Extract DTO field declarations from JAR classes |
| `jar_extract_transaction_compiled.py` | Extract transaction class data from compiled JARs |
| `jar_extract_transaction_identity.py` | Extract transaction identity (program code, version) |
| `jar_extract_wmid_chain.py` | Trace WMID parameter chains through gateway classes |
| `jar_extract_wmod_fields.py` | Extract WMOD field mappings from gateway classes |
| `jar_extract_wmod_rip.py` | Extract WMOD RIP/ROP file data |
| `backstage_clone.py` | Clone or update the Backstage catalogue repository |
| `clone_mis_repos.py` | Clone EBS/EGS MIS source repos from GitLab for TDL/DAG extraction |

## Agents

The plugin uses an orchestrator-worker hierarchy across three pipelines:

```
/mts-documentation  ──>  mts-doc-orchestrator-agent
                            ├── mts-discovery-agent
                            ├── mts-architecture-agent
                            ├── mts-service-inventory-agent
                            ├── mts-service-catalogue-agent
                            ├── mts-per-service-doc-agent  (×N services)
                            ├── mts-code-journeys-agent
                            └── mts-data-lineage-agent

/api-replacement-match  ──>  mts-match-orchestrator-agent
                                └── mts-api-match-agent

/mts-migrate  ──>  mts-migrate-orchestrator-agent
                      ├── mts-migrate-scaffold-agent  (Strategy A only)
                      ├── mts-migrate-code-agent
                      ├── mts-migrate-test-agent
                      └── mts-migrate-issues-agent
```

### Documentation Agents

| Agent | Role | Model |
|-------|------|-------|
| `mts-doc-orchestrator-agent` | Orchestrates full documentation pipeline: pre-flight, discovery, parallel agent dispatch, verification | sonnet |
| `mts-discovery-agent` | Detects MCA1/MCA2 framework, discovers doService + callService calls, resolves constants and variable methods (Pattern 3), traces call chains, extracts mainframe transaction data | sonnet |
| `mts-architecture-agent` | Generates architecture overview: technology stack, layers, filters, endpoints, databases, MQ, EBS dependencies | sonnet |
| `mts-service-inventory-agent` | Generates service inventory: all doService calls with resolved names, DTOs, EBS JARs, categories | sonnet |
| `mts-service-catalogue-agent` | Generates service catalogue combining inventory and orchestration map | sonnet |
| `mts-per-service-doc-agent` | Generates per-service doc for a single doService call: call flow, field mapping, backend mappings | sonnet |
| `mts-code-journeys-agent` | Generates code journeys: REST endpoint routing through service layers to doService calls | sonnet |
| `mts-data-lineage-agent` | Generates data lineage: traces each response field back to its source doService call and mainframe table | sonnet |

### API Matching Agents

| Agent | Role | Model |
|-------|------|-------|
| `mts-match-orchestrator-agent` | Orchestrates API matching pipeline: loads doc, probes tools, parallel search, score, validate, report | sonnet |
| `mts-api-match-agent` | Compares MTS service doc against candidate ODS API docs, scores field/table overlap, writes match report | sonnet |

### Migration Agents

| Agent | Role | Model |
|-------|------|-------|
| `mts-migrate-orchestrator-agent` | Orchestrates migration pipeline: loads inputs, strategy dispatch, shared code gen steps, report | sonnet |
| `mts-migrate-scaffold-agent` | Clones GitLab template and renames all project identifiers (Strategy A only) | sonnet |
| `mts-migrate-code-agent` | Generates API service class, converters/mappers, response model, config, flag routing | sonnet |
| `mts-migrate-test-agent` | Generates unit tests matching the target repo's test framework | sonnet |
| `mts-migrate-issues-agent` | Produces post-migration issues doc: gaps, bugs, notification impacts, manual follow-up items | sonnet |

### Cross-Cutting Agents

| Agent | Role | Model |
|-------|------|-------|
| `auto-decision-agent` | Resolves ambiguity when MTS agents encounter choices autonomously | sonnet |
| `mts-validation-agent` | Read-only gatekeeper that scans output for red flags before any git commit or push | haiku |
| `mts-push-agent` | Executes post-workflow cleanup and commit phase for generated artefacts | sonnet |

## Output Artifacts

### Stage 1 — Documentation (`/mts-documentation`)

| Artifact | Path |
|----------|------|
| Architecture overview | `docs/mts/architecture-overview.md` |
| Service catalogue | `docs/mts/service-catalogue.md` |
| Per-service docs | `docs/mts/<ServiceName>-<method>.md` (one per service) |
| Code journeys | `docs/mts/code-journeys.md` |
| Data lineage | `docs/mts/data-lineage.md` |

### Stage 2 — API Matching (`/api-replacement-match`)

| Artifact | Path |
|----------|------|
| Match report | `docs/mts/api-match-<ServiceName>-<method>.md` |

### Stage 3 — Migration (`/mts-migrate`)

| Artifact | Path |
|----------|------|
| Generated code | `src/main/java/...` (API service, converters, models, config) |
| Generated tests | `src/test/java/...` (unit tests matching target framework) |
| Issues document | `docs/mts/migrate-issues-<ServiceName>-<method>.md` |

## Installation

1. Add this marketplace to Claude Code:
   ```
   /plugin
   # Select "Add marketplace"
   # Enter the repository path
   ```

2. Install the mts-migrate-toolkit plugin:
   ```
   /plugin
   # Select "Browse and install plugins"
   # Choose "mts-migrate-toolkit"
   ```

3. Restart Claude Code to load the plugin

---

**Plugin Version**: 1.3.0 | Author: Kavitha Ramakrishnan | Commands: `/mts-documentation`, `/api-replacement-match`, `/mts-migrate`, `/refresh-ods-catalogue`
