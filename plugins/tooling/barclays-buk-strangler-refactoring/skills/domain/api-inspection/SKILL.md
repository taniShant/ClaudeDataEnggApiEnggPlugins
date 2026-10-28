---
name: api-inspection
Source: Barclays BUK Strangler Refactoring Plugin v3.2
Owner: preetha.ramaswamy@barclays.com
Review trigger: Quarterly or on major version bump
user-invocable: false
Status: Published
---
> **Source:** Strangler Refactoring Plugin v3.2 — API Inspection — Domain Pattern Discovery (internal)
> **Owner:** Preetha Ramaswamy / BUK CIO Engineering
> **Review trigger:** Quarterly or when new API patterns are identified in extraction
> **Status:** Published
> Source documents are Internal — Restricted.


## Quick Start

```
Phase: 1 (Discovery)
Worker: 1D (API Pattern Inspector)
Load: orchestrator passes skill_context = api-inspection §1-4
Use: Scan controllers, services, tests → output STRANGLER_API_PATTERNS.md
Model: balanced
```

# API Inspection — Domain Pattern Discovery

> **Purpose:** Discover domain logic patterns by inspecting existing APIs in the codebase. Replaces hardcoded domain classification with inference from real code. Java-focused.

---

## §1 — Philosophy

**Domain knowledge is DISCOVERED, not assumed.**

The plugin does NOT assume:
- "Payment domain uses `put*` prefix"
- "Services are named `*PolicyService`"
- "Field injection with `@Autowired`"

Instead, it INSPECTS the existing project to learn:
- What domains exist (from packages, controllers, endpoints)
- How services are named (from actual class names)
- What DI style is used (from actual code patterns)
- What test framework is used (from actual test files)

---

## §2 — Inspection Targets (Java)

### 2.1 REST Controllers
```
Scan patterns:
  **/src/main/java/**/*Controller.java
  **/src/main/java/**/*Resource.java
  **/src/main/java/**/*Api.java
  **/src/main/java/**/*Endpoint.java

Extract from each:
  - Class annotation: @RestController, @Controller
  - Base path: @RequestMapping("/api/v1/{domain}")
  - HTTP methods: @GetMapping, @PostMapping, @PutMapping, @DeleteMapping
  - Method signatures: parameters, return types, exceptions
  - Security: @PreAuthorize, @Secured, @RolesAllowed
  - Request/Response types: @RequestBody, @ResponseBody types
```

### 2.2 Service Layer
```
Scan patterns:
  **/src/main/java/**/*Service.java
  **/src/main/java/**/*ServiceImpl.java
  **/src/main/java/**/*UseCase.java
  **/src/main/java/**/*Handler.java

Extract from each:
  - Class annotation: @Service, @Component
  - Injected dependencies: constructor params or @Autowired fields
  - Public methods: signatures, return types, exceptions
  - Transaction boundaries: @Transactional
  - Caching: @Cacheable, @CacheEvict
```

### 2.3 Repository Layer
```
Scan patterns:
  **/src/main/java/**/*Repository.java
  **/src/main/java/**/*Dao.java

Extract from each:
  - Interface extensions: JpaRepository, CrudRepository, custom
  - Entity types managed
  - Custom query methods
```

### 2.4 DTOs & Models
```
Scan patterns:
  **/src/main/java/**/model/**/*.java
  **/src/main/java/**/dto/**/*.java
  **/src/main/java/**/request/**/*.java
  **/src/main/java/**/response/**/*.java

Extract from each:
  - Class type: record, class, enum
  - Fields and types
  - Validation annotations: @NotNull, @Valid, @Size
  - Serialization: @JsonProperty, @JsonIgnore
```

### 2.5 Configuration & Cross-Cutting
```
Scan patterns:
  **/src/main/java/**/*Config.java
  **/src/main/java/**/*Configuration.java
  **/src/main/java/**/*Interceptor.java
  **/src/main/java/**/*Filter.java
  **/src/main/java/**/*Aspect.java

Extract: Beans defined, interceptor chains, AOP advice
```

### 2.6 Existing Tests
```
Scan patterns:
  **/src/test/java/**/*Test.java
  **/src/test/java/**/*IT.java
  **/src/test/java/**/*Tests.java

Extract from each:
  - Test framework: JUnit 4 (@Test, @RunWith) vs JUnit 5 (@Test, @ExtendWith)
  - Assertion library: JUnit assertions, AssertJ, Hamcrest
  - Mock framework: Mockito (@Mock, @InjectMocks), EasyMock
  - Integration style: @SpringBootTest, @WebMvcTest, @DataJpaTest
  - Test naming: camelCase, should_when_then, given_when_then
```

### 2.7 Build Configuration
```
Scan patterns:
  build.gradle, build.gradle.kts, pom.xml

Extract:
  - Spring Boot version
  - Java version (sourceCompatibility)
  - Key dependencies (spring-web, spring-data, lombok, mapstruct)
  - Test dependencies (junit-jupiter, mockito, assertj, testcontainers)
  - Plugins (lombok, mapstruct, jacoco)
```

---

## §3 — Domain Inference Algorithm

### Step 1: Package-Based Domain Detection
```
For each top-level package under src/main/java/{base.package}/:
  - If package contains controllers AND services → domain boundary
  - Domain name = package name (e.g., "payments", "cards", "accounts")

Example:
  com.barclays.app.payments/ → Payment domain
  com.barclays.app.cards/    → Cards domain
  com.barclays.app.shared/   → Shared/cross-cutting (not a domain)
```

### Step 2: Endpoint-Based Domain Detection (if flat packages)
```
If no sub-packages exist (monolith with flat structure):
  - Group controllers by @RequestMapping base path
  - /api/v1/payments/** → Payment domain
  - /api/v1/cards/**    → Cards domain
  
If no controllers (service-only monolith):
  - Group methods by semantic prefix
  - process*Payment*, refund*, get*Payment* → Payment domain
  - *Card*, *Reward* → Cards domain
```

### Step 3: Dependency Graph Domain Validation
```
For each detected domain:
  - Count internal calls (methods calling methods in same domain)
  - Count external calls (methods calling other domains)
  - Domain cohesion = internal_calls / total_calls
  
  If cohesion < 0.5: domain boundary may be wrong (split or merge)
  If cohesion > 0.8: strong domain boundary
```

### Step 4: Cross-Cutting Concern Detection
```
A service is cross-cutting if:
  - Injected in >60% of other services (e.g., AuditService, LoggingService)
  - Has no domain-specific logic (utility, infrastructure)
  
Cross-cutting services are NOT extraction targets.
They remain shared and injected into extracted services.
```

---

## §4 — Architecture Pattern Detection

### Detect which architectural style the project uses:

```
LAYERED (most common):
  Evidence: Controller → Service → Repository layers
  Detection: All three layers present in each domain package
  
HEXAGONAL:
  Evidence: ports/ and adapters/ packages, UseCase classes
  Detection: Interface ports + implementation adapters pattern
  
DDD/CQRS:
  Evidence: Command/Query separation, aggregate roots, event handlers
  Detection: *Command.java, *Query.java, *Event.java, *Aggregate.java
  
MONOLITH (God Class):
  Evidence: Single large service with all methods
  Detection: One class >500 lines with >20 public methods, no clear layers
```

### Output format:
```
architecture_style: "layered" | "hexagonal" | "ddd_cqrs" | "monolith"
confidence: 0.0 - 1.0
evidence: [list of files/patterns that support detection]
```

---

## §5 — Naming Convention Discovery

### Detect actual naming patterns (don't assume):

```
SERVICE NAMING:
  Scan all @Service classes → extract suffix pattern
  - *Service (most common)
  - *ServiceImpl (implementation of interface)
  - *PolicyService (Barclays-specific)
  - *UseCase (hexagonal)
  
DTO NAMING:
  Scan model/dto packages → extract suffix pattern
  - *Request / *Response
  - *DTO
  - *Model
  - *Command / *Query (CQRS)
  - Java records vs classes
  
TEST NAMING:
  Scan test classes → extract naming convention
  - shouldDoXWhenY() — BDD style
  - testMethodName() — traditional
  - givenX_whenY_thenZ() — Given/When/Then
  
PACKAGE STRUCTURE:
  Detect package organization style:
  - By layer: controller/, service/, repository/
  - By domain: payments/, cards/, accounts/
  - Hybrid: payments/controller/, payments/service/
```

---

## §6 — Dependency Injection Style Detection

```
CONSTRUCTOR INJECTION (preferred):
  Evidence: final fields + @RequiredArgsConstructor or explicit constructor
  Detection: No @Autowired on fields, constructor with all dependencies
  
FIELD INJECTION (legacy):
  Evidence: @Autowired on private fields, no constructor
  Detection: @Autowired annotation count > 0 on fields
  
SETTER INJECTION (rare):
  Evidence: @Autowired on setter methods
  Detection: @Autowired on methods starting with set*
  
LOMBOK USAGE:
  Evidence: @RequiredArgsConstructor, @Builder, @Data, @Value
  Detection: Lombok annotations present, no boilerplate constructors
```

---

## §7 — Output Artifact: STRANGLER_API_PATTERNS.md

The API Inspector worker produces this artifact for consumption by subsequent phases:

```markdown
# Discovered API Patterns

## Project Metadata
- Spring Boot version: {detected}
- Java version: {detected}
- Build tool: Gradle | Maven
- Key frameworks: {list}

## Architecture Style
- Detected: {style}
- Confidence: {0-1}
- Evidence: {files}

## Domain Map
| Domain | Package | Controllers | Services | Repositories | DTOs | Methods |
|--------|---------|-------------|----------|--------------|------|---------|
| {domain} | {pkg} | {count} | {count} | {count} | {count} | {count} |

## Naming Conventions
- Services: {detected pattern, e.g., "*Service"}
- DTOs: {detected pattern, e.g., "*Request/*Response"}
- Tests: {detected pattern, e.g., "*Test"}
- Test methods: {detected style, e.g., "shouldXWhenY"}
- Package org: {by-layer | by-domain | hybrid}

## Dependency Injection
- Style: {constructor | field | setter}
- Lombok: {yes/no}
- Pattern: {description}

## Test Framework
- Framework: {JUnit 4 | JUnit 5}
- Assertions: {AssertJ | Hamcrest | JUnit native}
- Mocking: {Mockito | EasyMock}
- Integration: {SpringBootTest | WebMvcTest | DataJpaTest}
- Naming: {shouldWhen | givenWhenThen | testMethod}

## Cross-Cutting Services
| Service | Injected In | Purpose |
|---------|------------|---------|
| {name} | {percentage}% of services | {role} |

## Inter-Domain Dependencies
| From Domain | To Domain | Methods | Coupling |
|-------------|-----------|---------|----------|
| {from} | {to} | {count} | {low/medium/high} |

## Monolith Target Analysis
- File: {target file}
- Total methods: {count}
- Detected domains: {count}
- Cohesion score: {0-1}
- Recommended pattern: {orchestrator | facade | delegation | repository}
```

---

## §8 — Worker 1D Specification

**Worker 1D: API Pattern Inspector**

```
Phase: 1 (parallel with Workers 1A, 1B, 1C)
Scope: Read-only project scanning
Input: Project root path, target_file path
Output: .claude/STRANGLER_API_PATTERNS.md
Token Budget: ~300-500 tokens (file scanning is cheap)
Tool Access: Bash (find, grep), Read (file content)

Execution:
1. Scan project structure (find *.java by layer)
2. Detect architecture style
3. Infer domain boundaries
4. Detect naming conventions
5. Detect DI style and test framework
6. Identify cross-cutting concerns
7. Write STRANGLER_API_PATTERNS.md

Constraints:
- Read-only (NEVER modify project files)
- Scan top 50 most relevant files max (avoid token explosion)
  Tier detection: by package path (`*/controller/*`, `*/service/*`, `*/repository/*`, `*/model/*` or `*/dto/*`)
  OR by class annotation (@RestController/@Controller, @Service, @Repository, @Entity).
  Sort order: controllers first, then services, then repositories, then DTOs/models,
  then remaining files by descending file size. Within each tier, sort by file size descending,
  then alphabetical by path for complete determinism.
  If >50 candidates exist, log tier distribution and skip count:
    "Scanned 50 files: 12 controllers, 18 services, 15 repositories, 5 models. Skipped 23."
- STOP if project has no Java source (error STR-1E002)
```

---

## Agent Self-Check

- [ ] Discovered patterns reflect actual codebase (not assumed/hardcoded)
- [ ] Naming conventions extracted from ≥3 existing files (not just one)
- [ ] DI style correctly identified (constructor vs field injection)
- [ ] Test framework and assertion library detected
- [ ] Output written to STRANGLER_API_PATTERNS.md with all required sections
- [ ] No external CDN or Google Fonts references in discovered patterns

## Source

**Owner:** preetha.ramaswamy@barclays.com  
**Review cadence:** Quarterly or on major version bump  
**Origin:** Barclays BUK Strangler Refactoring Plugin v3.0 — internal engineering  
**Classification:** Internal
