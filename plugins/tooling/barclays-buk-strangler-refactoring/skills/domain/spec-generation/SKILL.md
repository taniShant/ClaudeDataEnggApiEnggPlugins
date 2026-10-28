---
name: spec-generation
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — Spec Generation — BDD Contract Extraction (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** When new spec patterns or language support is added
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 5 (Spec Generation)
Worker: 5A (Spec Generator)
Load: orchestrator passes skill_context = spec-generation §1-9
Use: Generate hexagonal service spec (ports, adapters, DTOs, behavior table)
Model: balanced
```

# Specification Generation — Hexagonal Service Blueprint

> **Purpose:** Generate formal service specifications that follow hexagonal architecture. Extracted services will have inbound ports (use cases), outbound ports (driven interfaces), domain logic (framework-free), and adapters (Spring wiring). Specs become the blueprint that drives TDD test generation and clean code generation.

> **Complementary scope:** This skill defines how to generate hexagonal service specs from extracted monolith methods (internal architecture). It is complementary to `barclays-buk-standards:api-design`, which defines external API contract standards (DAF headers, versioning, channel exposure). There is no overlap — this skill addresses service internals (ports, adapters, domain purity); the standards skill addresses API externals (HTTP contracts, authorization layers, deployment).

---

## §1 — Philosophy: Spec-First + Hexagonal

```
Tasks (Phase 4) → SPECS (Phase 5) → Tests (Phase 6) → Code (Phase 7)
                       ↑
                  YOU ARE HERE

The extracted service will be structured as:

┌─────────────────────────────────────────────────┐
│              ADAPTER (Inbound)                    │
│  @Service class — implements inbound port        │
│  Receives Spring calls, delegates to domain      │
├─────────────────────────────────────────────────┤
│              DOMAIN                               │
│  Pure business logic — NO Spring annotations     │
│  Uses outbound ports for external calls          │
│  Framework-agnostic, unit-testable in isolation  │
├─────────────────────────────────────────────────┤
│              ADAPTER (Outbound)                   │
│  Implements outbound ports                       │
│  Talks to databases, external services, etc.     │
└─────────────────────────────────────────────────┘
```

A specification defines:
1. **INBOUND PORT** — Use-case interface (what the domain exposes to callers)
2. **OUTBOUND PORT** — Driven interface (what the domain needs from infrastructure)
3. **DOMAIN MODEL** — Pure business logic, no framework dependencies
4. **ADAPTERS** — Spring wiring that connects ports to real implementations
5. **DTOs** — Input/output objects at port boundaries
6. **BEHAVIOR** — Given/When/Then for each use case
7. **ERROR CONTRACTS** — Domain exceptions (framework-free)

---

## §2 — Spec Generation Input

| Input | Source | Contains |
|-------|--------|----------|
| Task definition | `STRANGLER_TASKS.md` | Task ID, assigned methods, dependencies |
| Method signatures | `STRANGLER_DISCOVERY.md` cache | Full signatures (params, return, exceptions) |
| Method bodies | Original monolith source | Logic to analyze for behavior extraction |
| API patterns | `STRANGLER_API_PATTERNS.md` | Naming conventions, DI style, test framework |
| Extraction pattern | `STRANGLER_PLAN.md` | Orchestrator/Facade/Delegation/Repository |

---

## §2.1 — Reverse-Spec-Generator Integration

Phase 5 delegates BDD behavior extraction to the `barclays-buk-reverse-spec-generator` plugin rather than performing inline analysis. This produces validated, confidence-scored `.spec` YAML which is then mapped to hexagonal architecture.

### Pipeline

```
Monolith methods (source code)
       │
       ▼
┌──────────────────────────────────────────────────────┐
│  barclays-buk-reverse-spec-generator                  │
│  (Python CLI — spec_extractor.py)                     │
│                                                       │
│  Extracts:                                            │
│    • entities   (classes, records, data structures)   │
│    • behaviors  (methods → Given/When/Then)           │
│    • rules      (guard clauses, business logic)       │
│    • constraints (limits, timeouts, dependencies)     │
│                                                       │
│  Output: .spec YAML with confidence scores            │
└───────────────────────────┬──────────────────────────┘
                            │
                            ▼
┌──────────────────────────────────────────────────────┐
│  Hexagonal Mapping (§4 algorithm)                     │
│                                                       │
│  BDD entities    → Domain DTOs (Commands, Results)    │
│  BDD behaviors   → Inbound Port methods (UseCase)     │
│  BDD rules       → Domain Service guard clauses       │
│  BDD constraints → Outbound Ports / adapter config    │
│                                                       │
│  Output: Hexagonal service spec + contract interface  │
└──────────────────────────────────────────────────────┘
```

### Invocation

Worker 5A invokes the reverse-spec-generator Python extractor directly:

```bash
cd {project_root}
python {REVERSE_SPEC_PLUGIN}/src/spec_extractor.py \
  --language java \
  --source {monolith_file} \
  --output .claude/STRANGLER_SPECS/T{NNN}-{domain}.spec \
  --confidence-threshold 0.5
```

Where `{REVERSE_SPEC_PLUGIN}` = path to `barclays-buk-reverse-spec-generator` plugin root (detected from Claude Code plugin registry or hardcoded as sibling plugin).

### Fallback

If the reverse-spec-generator is unavailable (not installed, Python error, extraction failure):
- Worker 5A falls back to **inline behavior extraction** (manual method body analysis)
- A warning is logged: `[WARN] reverse-spec-generator unavailable, falling back to inline extraction`
- Output quality may be lower (no confidence scoring, no language-specific patterns)

### BDD → Hexagonal Mapping Rules

| BDD `.spec` Element | Hexagonal Target | Mapping |
|--------------------|-----------------|---------|
| `entities[].name` | `domain/model/{Name}.java` | Each entity → Java record in domain model |
| `entities[].properties` | Record fields | Properties → record constructor params |
| `behaviors[].name` | `{Domain}UseCase` method | Each behavior → inbound port method |
| `behaviors[].given` | Test preconditions | Feed Phase 6 test generation |
| `behaviors[].when` | Method invocation | The use-case call |
| `behaviors[].then` | Return type + assertions | Expected outcomes |
| `rules[].condition` | `DomainService` guard | if-condition → throw `{Domain}DomainException` |
| `rules[].action` | Exception with code | Action clause → exception message |
| `constraints[type=dependency]` | `{Dep}Port` (outbound) | Dependency → outbound port interface |
| `constraints[type=limit]` | Domain constant | Limit value in domain model |
| `constraints[type=invariant]` | Validation logic | Invariant check in domain service |
| `constraints[type=timeout]` | Adapter configuration | Timeout in outbound adapter |

### Output Artifacts (Phase 5)

Worker 5A produces TWO artifacts per task:

1. **BDD Spec** (raw extraction): `.claude/STRANGLER_SPECS/T{NNN}-{domain}.spec`
   - Validated `.spec` YAML from reverse-spec-generator
   - Preserved for traceability, test generation input, convergence loop

2. **Hexagonal Spec** (architecture blueprint): `.claude/STRANGLER_SPECS/T{NNN}-{domain}-service-spec.md`
   - Full hexagonal structure (ports, adapters, DTOs, behavior table)
   - Contract interface `.java` file
   - Referenced by Phase 6 (test generation) and Phase 7 (code generation)

---

## §3 — Hexagonal Spec Document Structure

Each task produces one spec file: `STRANGLER_SPECS/T{NNN}-{domain}-service-spec.md`

### Template:

```markdown
# Service Specification: T{NNN} — {DomainName}

## Overview
- **Domain:** {detected domain}
- **Architecture:** Hexagonal (Ports & Adapters)
- **Responsibility:** {single-sentence purpose}
- **Method Count:** {N}
- **Risk Level:** {low | medium | high}

## Package Structure

{base.package}.{domain}/
├── domain/
│   ├── {DomainName}UseCase.java              ← Inbound port (interface)
│   ├── {DomainName}DomainService.java        ← Domain logic (pure, no Spring)
│   ├── {OutboundDep}Port.java                ← Outbound port (interface)
│   └── model/
│       ├── {DomainCommand}.java              ← Input DTO
│       └── {DomainResult}.java               ← Output DTO
├── adapter/
│   ├── inbound/
│   │   └── {DomainName}ServiceAdapter.java   ← @Service, delegates to domain
│   └── outbound/
│       └── {OutboundDep}Adapter.java         ← Implements outbound port
└── config/
    └── {DomainName}Config.java               ← Bean wiring

## Inbound Port (Use Case Interface)

\```java
package {base.package}.{domain}.domain;

/**
 * Inbound port — defines what this domain exposes.
 * No Spring annotations. No framework imports.
 */
public interface {DomainName}UseCase {
    {ReturnType} {methodName}({CommandType} command) throws {DomainException};
}
\```

## Outbound Port (Driven Interface)

\```java
package {base.package}.{domain}.domain;

/**
 * Outbound port — what the domain NEEDS from infrastructure.
 * Defined by domain, implemented by adapter.
 */
public interface {OutboundDep}Port {
    {ReturnType} {operation}({params});
}
\```

## Domain Service (Pure Business Logic)

\```java
package {base.package}.{domain}.domain;

/**
 * Pure domain logic. NO Spring annotations.
 * Dependencies injected via constructor (ports only).
 * Easily unit-testable without Spring context.
 */
public class {DomainName}DomainService implements {DomainName}UseCase {

    private final {OutboundDep}Port {outboundDep};

    public {DomainName}DomainService({OutboundDep}Port {outboundDep}) {
        this.{outboundDep} = {outboundDep};
    }

    @Override
    public {ReturnType} {methodName}({CommandType} command) throws {DomainException} {
        // Pure business logic extracted from monolith
        // Uses outbound ports, never concrete implementations
    }
}
\```

## Inbound Adapter (Spring Wiring)

\```java
package {base.package}.{domain}.adapter.inbound;

import org.springframework.stereotype.Service;
import lombok.RequiredArgsConstructor;

/**
 * Inbound adapter — receives calls from monolith delegation.
 * Delegates to domain service. Only Spring annotations live HERE.
 */
@Service
@RequiredArgsConstructor
public class {DomainName}ServiceAdapter implements {DomainName}UseCase {

    private final {DomainName}DomainService domainService;

    @Override
    @Transactional  // Framework concern — lives in adapter, not domain
    public {ReturnType} {methodName}({CommandType} command) throws {DomainException} {
        return domainService.{methodName}(command);
    }
}
\```

## Outbound Adapter

\```java
package {base.package}.{domain}.adapter.outbound;

import org.springframework.stereotype.Component;
import lombok.RequiredArgsConstructor;

/**
 * Outbound adapter — implements the port defined by domain.
 * Talks to real infrastructure (DB, external service, etc.)
 */
@Component
@RequiredArgsConstructor
public class {OutboundDep}Adapter implements {OutboundDep}Port {

    private final {ConcreteInfra} infra;  // JPA repo, REST client, etc.

    @Override
    public {ReturnType} {operation}({params}) {
        return infra.{concreteMethod}({args});
    }
}
\```

## Configuration (Bean Wiring)

\```java
package {base.package}.{domain}.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class {DomainName}Config {

    @Bean
    public {DomainName}DomainService {domainName}DomainService({OutboundDep}Port {outboundPort}) {
        return new {DomainName}DomainService({outboundPort});
    }
}
\```

## Domain Model (DTOs at port boundary)

\```java
package {base.package}.{domain}.domain.model;

// Input to the use case (replaces raw method params)
public record {DomainCommand}(
    {Type} {field},
    {Type} {field}
) {}

// Output from the use case
public record {DomainResult}(
    {Type} {field},
    {Type} {field}
) {}
\```

## Domain Exception

\```java
package {base.package}.{domain}.domain;

// Domain exception — NO Spring, NO HTTP status codes
public class {DomainException} extends RuntimeException {
    private final String code;
    public {DomainException}(String code, String message) {
        super(message);
        this.code = code;
    }
}
\```

## Delegation Contract (monolith update)

\```java
// The monolith delegates to the inbound adapter:
@Autowired private {DomainName}UseCase {domainName};

public {OriginalReturnType} {originalMethod}({originalParams}) throws {originalException} {
    var command = new {DomainCommand}({map params to command});
    var result = {domainName}.{methodName}(command);
    return {map result to original return type};
}
\```

## Behavior Specification

| # | Method | Given | When | Then |
|---|--------|-------|------|------|
| 1 | {method} | {precondition} | Called with {input} | Returns {output} |
| 2 | {method} | {error condition} | Called with {bad input} | Throws {DomainException} |

## Dependencies (Ports Only)

| Port | Type | Purpose | Implemented By |
|------|------|---------|----------------|
| {Name}Port | Outbound | {why needed} | {Name}Adapter |

## Spec Status
- Generated: {timestamp}
- Status: pending_review | approved | rejected
```

---

## §4 — Hexagonal Decomposition Algorithm

Decompose monolith methods into hexagonal layers using the BDD `.spec` extracted by the reverse-spec-generator (§2.1) as primary input, supplemented by method body analysis.

### Step 1: Identify Domain Logic (from BDD rules + method body)
```
Primary source: .spec rules[] + constraints[type=invariant]
Supplementary: method body analysis (conditions, calculations)

From BDD rules:
- Each rule.condition → guard clause in DomainService
- Each rule.action → domain exception or state transition

From method body (cross-reference):
- Calculations (fees, totals, conversions)
- Validations not captured as BDD rules
- State transitions (status changes, workflow steps)

This becomes: {DomainName}DomainService
```

### Step 2: Identify Outbound Dependencies (from BDD constraints + @Autowired)
```
Primary source: .spec constraints[type=dependency]
Supplementary: @Autowired fields used by assigned methods

From BDD constraints (type=dependency):
- Each dependency constraint → outbound port interface
- constraint.value identifies the concrete dependency

From @Autowired analysis:
- Other services → becomes outbound port
- Database queries (repository calls) → becomes outbound port
- External API calls (REST clients) → becomes outbound port
- Event publishers → becomes outbound port

Each becomes: {Dependency}Port (interface) + {Dependency}Adapter (implementation)
```

### Step 3: Identify Inbound Interface (from BDD behaviors)
```
Primary source: .spec behaviors[]
Each behavior becomes a method on the inbound port:

- behavior.name → method name (convert snake_case → camelCase for Java)
- behavior.given → preconditions (used in test generation)
- behavior.when → the method call with params
- behavior.then → return type + side effects

Mapping:
- Framework DTOs (PaymentRequest) → Domain commands (ProcessPaymentCommand)
- Framework exceptions → Domain exceptions
- The inbound adapter handles the translation
```

### Step 4: Identify Domain Model (from BDD entities)
```
Primary source: .spec entities[]
Each entity maps to a domain model class:

- entity.name → Java record/class in domain/model/
- entity.properties → record fields
- entity.properties[].type → Java type (string→String, number→BigDecimal, etc.)
- entity.properties[].required → @NotNull or Optional<T>

DTOs at port boundaries:
- Input entities → {Action}Command records
- Output entities → {Action}Result records
```

### Step 5: Identify Cross-Cutting Concerns (Adapter Responsibility)
```
These belong in the ADAPTER, not the domain:
- @Transactional → inbound adapter
- @Cacheable → inbound adapter
- Logging with correlation IDs → inbound adapter
- Exception translation (domain → HTTP) → controller (stays in monolith)
- Metrics/tracing → inbound adapter
- Timeout handling (from constraints[type=timeout]) → outbound adapter

Domain service is PURE — no annotations, no framework imports.
```

---

## §5 — Port & Adapter Naming Rules

| Concept | Naming Convention | Package |
|---------|-------------------|---------|
| Inbound port | `{Domain}UseCase` | `{base}.{domain}.domain` |
| Domain service | `{Domain}DomainService` | `{base}.{domain}.domain` |
| Outbound port | `{Dependency}Port` | `{base}.{domain}.domain` |
| Domain command | `{Action}Command` | `{base}.{domain}.domain.model` |
| Domain result | `{Action}Result` | `{base}.{domain}.domain.model` |
| Domain exception | `{Domain}DomainException` | `{base}.{domain}.domain` |
| Inbound adapter | `{Domain}ServiceAdapter` | `{base}.{domain}.adapter.inbound` |
| Outbound adapter | `{Dependency}Adapter` | `{base}.{domain}.adapter.outbound` |
| Config | `{Domain}Config` | `{base}.{domain}.config` |

---

## §6 — When to Create Outbound Ports

**Create an outbound port when the domain calls:**

| Dependency Type | Create Port? | Port Name | Adapter |
|----------------|-------------|-----------|---------|
| Another internal service | YES | `{Service}Port` | `{Service}Adapter` (wraps @Autowired) |
| JPA Repository | YES | `{Entity}RepositoryPort` | `{Entity}RepositoryAdapter` |
| External REST client | YES | `{External}GatewayPort` | `{External}GatewayAdapter` |
| Event publisher | YES | `{Event}PublisherPort` | `{Event}PublisherAdapter` |
| Logger | NO | — | Use SLF4J directly (cross-cutting) |
| Clock/time | YES (if testable) | `ClockPort` | `SystemClockAdapter` |

**Do NOT create a port for:**
- Pure utility methods (String manipulation, math)
- Java standard library (Collections, Streams)
- Logging (SLF4J is lightweight enough)

---

## §7 — Spec Manifest

```json
{
  "generated_at": "2026-07-15T10:30:00Z",
  "architecture": "hexagonal",
  "tasks_total": 5,
  "specs": [
    {
      "task_id": "T001",
      "domain": "payment",
      "inbound_port": "PaymentUseCase",
      "domain_service": "PaymentDomainService",
      "outbound_ports": ["AccountPort", "AuditPort"],
      "adapters": {
        "inbound": "PaymentServiceAdapter",
        "outbound": ["AccountAdapter", "AuditAdapter"]
      },
      "package": "com.barclays.app.payment",
      "methods": 3,
      "status": "pending_review"
    }
  ]
}
```

---

## §8 — Spec Review Gate

After generation, the pipeline PAUSES for review. Engineer verifies:
1. Port boundaries are correct (domain logic has no framework imports)
2. Outbound ports match actual external dependencies
3. Command/Result DTOs capture all necessary data
4. Behavior spec covers happy path + error paths

Only APPROVED specs proceed to Phase 6 (test generation).

---

## §9 — Worker 5A Specification

**Worker 5A: Spec Generator (with reverse-spec-generator integration)**

```
Phase: 5
Input: STRANGLER_TASKS.md, STRANGLER_DISCOVERY.md, STRANGLER_API_PATTERNS.md, monolith source
Output: .claude/STRANGLER_SPECS/ (BDD .spec + hexagonal specs + manifest)
Dependency: barclays-buk-reverse-spec-generator plugin (Python extractor)

Execution per task:
1. Read task assignment (methods, dependencies, discovered patterns)

2. Invoke reverse-spec-generator for BDD extraction:
   a. Run: python {REVERSE_SPEC_PLUGIN}/src/spec_extractor.py \
        --language java --source {monolith_file} \
        --output .claude/STRANGLER_SPECS/T{NNN}-{domain}.spec \
        --confidence-threshold 0.5
   b. Parse output .spec YAML (entities, behaviors, rules, constraints)
   c. On FAILURE: fall back to inline method body analysis (log warning)

3. Read method bodies from monolith (supplement BDD extraction):
   - Cross-reference .spec behaviors against method signatures
   - Identify any behaviors missed by extraction (low-confidence methods)
   - Verify .spec entities match actual class structures

4. Decompose into hexagonal layers (§4 algorithm, BDD-driven):
   a. Map .spec behaviors → inbound port methods (UseCase interface)
   b. Map .spec entities → domain model DTOs (Commands, Results)
   c. Map .spec rules → domain service guard clauses
   d. Map .spec constraints[type=dependency] → outbound ports
   e. Map .spec constraints[type=timeout] → adapter configuration
   f. Identify cross-cutting concerns → adapter responsibilities

5. Generate hexagonal spec document (§3 template)

6. Write artifacts + update manifest:
   - .claude/STRANGLER_SPECS/T{NNN}-{domain}.spec (BDD extraction)
   - .claude/STRANGLER_SPECS/T{NNN}-{domain}-service-spec.md (hexagonal spec)
   - .claude/STRANGLER_SPECS/contracts/{ServiceName}Contract.java
   - Update .claude/STRANGLER_SPECS/SPEC_MANIFEST.json

7. STOP — do NOT generate implementation

Constraints:
- Domain service MUST have zero framework imports
- Every external call MUST go through an outbound port
- Inbound adapter is the ONLY class with @Service
- Original method signature preserved via delegation in monolith
- BDD .spec MUST pass validation (spec_validator.py) before hexagonal mapping
- Fallback to inline extraction if reverse-spec-generator fails (no hard dependency)
```

---

## Agent Self-Check

- [ ] Generated spec follows hexagonal structure (domain/, adapters/in, adapters/out, application/)
- [ ] Contract interface defines all public methods from task assignment
- [ ] DTOs are plain records (no framework annotations in domain layer)
- [ ] Behavior table has Given/When/Then for every method
- [ ] Outbound ports identified for every external dependency
- [ ] Spec references discovered API patterns (not hardcoded conventions)

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
