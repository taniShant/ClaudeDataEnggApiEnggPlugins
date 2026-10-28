---
name: mca1-to-mca2-eps
description: >
  MCA1 to MCA2 migration skill (aggressive strategy). Complete transformation
  mapping for migrating applications from scp-eps-java-common (MCA1) to mca-java-common
  (MCA2). Use when user says "migrate MCA1", "MCA2 migration", "replace scp-eps",
  "upgrade to mca-java-common", or runs /migrate-mca1-to-mca2. Replaces ALL MCA1
  patterns with MCA2 equivalents — no stubs, no compatibility shims. Preserves business
  logic but replaces all framework types directly. Derived from frozen MDD
  validated by Pilot 1 (scp-eps-audit) and Pilot 2 (scp-eps-bal-and-enq).
user-invocable: false
source: barclays-claude-code-plugins/plugins/mca1-to-mca2-eps/skills/mca1-to-mca2-eps/SKILL.md
owner: MCA Core Engineering (mcaplatform@barclays.com)
review-trigger: When mca-java-common BOM version changes or MCA2 framework APIs are updated
status: Full
---

# MCA1 to MCA2 Migration — Aggressive Strategy

## GATED PHASES (STOP-AND-RETURN ENFORCEMENT)

Phases 7, 11, and 14 are **gated phases** with a strict two-part structure:
- **Part A (GATE):** STOP immediately and return ONLY the gate signal (`GATE_PHASE_7`, `GATE_PHASE_11`, or `GATE_PHASE_14`). Do NOT read files, scan code, plan changes, or call any tools (including AskUserQuestion). The orchestrator (command layer) handles user interaction.
- **Part B (EXECUTE):** Only runs AFTER the orchestrator resumes you with the user's choice.

When you reach Phase 7, 11, or 14, you MUST return ONLY the gate signal with ZERO tool calls. If you call Read, Edit, Write, Grep, Glob, Bash, or AskUserQuestion, the migration is INVALID.

- **Phase 7 (REST Clients):** Return `GATE_PHASE_7` — orchestrator asks user which strategy
- **Phase 11 (Testing):** Return `GATE_PHASE_11` — orchestrator asks user whether to write tests or skip
- **Phase 14 (Package Rename):** Return `GATE_PHASE_14` — orchestrator asks user whether to rename packages

The orchestrator calls `AskUserQuestion` and resumes you with the user's answer. See agent doc for Part B execution details.

## Strategy Declaration

**This skill uses the AGGRESSIVE strategy.**

- **Replace ALL MCA1 patterns** — replace all MCA1 framework patterns (controllers, service dispatch,
  context, exceptions, filters, dependencies, packages) with MCA2 equivalents directly.
- **No stubs** — do NOT create stub/shim classes. Replace every MCA1 type (`EpsApplicationException`,
  `EpsResponseBean`, `MessageBeanHelper`, `UserBean`, etc.) with its MCA2 equivalent inline.
- **Preserve all existing business logic** — validation, data transformation, formatting, mapping,
  computation, business rules, and data assembly MUST be carried over into the MCA2 service layer.
- **Mark logic for future review** — classify preserved logic with `@MCA2-*` markers so the team
  can decide what to refactor later.

**This skill does NOT:**
- Create stub/shim classes under `migration/stubs/` (use `reference/migration-stubs.md` only as a type reference, not as templates to create)
- Strip business logic from service layers
- Assume downstream REST APIs implement all logic
- Consolidate N services into 1 (unless feature team requests it — DEC-023)
- Add caching by default (team-level enhancement — DEC-024)

## Prerequisites

- JDK migration to Java 21 is complete
- Spring Boot 3.3+ upgrade is complete
- Jakarta EE namespace migration (javax -> jakarta) is complete
- Gradle 8.5 is configured

## Reference Documents

All documents are self-contained and agent-consumable. For complete context, read them in
order: transformation mapping first (patterns + dependencies), stubs second (artifact templates),
this file third (execution plan). Each document can also be consumed independently.

- [Transformation Mapping Reference](reference/transformation-mapping.md) — Quick-reference mapping table, dependency mapping, 12 patterns + Part I-M amendments
- [Migration Stubs Catalog](reference/migration-stubs.md) — **Behavior-preservation strategy ONLY. Do NOT use for aggressive strategy.** Type reference only — do not create stub classes.
- [Dependency Mapping Reference](reference/dependency-mapping.md) — Dependency table (MCA1 → MCA2 coordinates)
- [Test Migration Guide](reference/test-migration-guide.md) — JMock to Mockito patterns, MockedStatic strategies
- [Test Templates](reference/test-templates.md) — Pre-built test templates for controller, service, helper, config, POJO patterns
- [OAS3 Migration Guide](reference/oas-migration-guide.md) — OAS spec migration patterns
- [MCA2 OAS Template](reference/oas-template/openapi.yaml) — OAS template for new specs
- [Pattern Mapping Reference](reference/pattern-mapping.md) — Code pattern transforms (controller, service, context)
- [Common Pitfalls](reference/common-pitfalls.md) — Extended pitfalls 11-21 (static initializers, MisClient, coverage)

## Reference Loading Guide

Load reference files just-in-time for each phase. Do NOT load all files at once.

| Phase | Required Reference Files |
|-------|--------------------------|
| Pre-Migration Analysis | This file (SKILL.md) only |
| Phase 1 (Build System) | `reference/dependency-mapping.md` (MANDATORY), `reference/transformation-mapping.md` dependency section |
| Phase 2 (Application Bootstrap) | `reference/transformation-mapping.md` Patterns 1-2 |
| Phase 3 (Configuration) | `reference/transformation-mapping.md` Pattern 3 |
| Phase 4 (Controllers) | `reference/transformation-mapping.md` Patterns 3-4, `reference/pattern-mapping.md` |
| Phase 5 (Services) | `reference/transformation-mapping.md` Patterns 5-6, `reference/pattern-mapping.md` |
| Phase 6 (Context & Headers) | `reference/transformation-mapping.md` Pattern 6 |
| Phase 7 (REST Clients) | `reference/transformation-mapping.md` Pattern 5 |
| Phase 8 (Exception Handling) | `reference/transformation-mapping.md` Patterns 7-8, `reference/common-pitfalls.md` |
| Phase 9 (Helpers & Utilities) | `reference/transformation-mapping.md` Pattern 9 |
| Phase 10 (Filter Chain) | `reference/transformation-mapping.md` Pattern 10 |
| Phase 11 (Testing) | `reference/test-migration-guide.md`, `reference/test-templates.md`, `reference/transformation-mapping.md` Pattern 12, `reference/common-pitfalls.md` |
| Phase 12 (OAS3 Specification) | `reference/oas-migration-guide.md`, `reference/oas-template/openapi.yaml` |
| Phase 13 (Process.json) | `reference/transformation-mapping.md` section 16 |
| Phase 14 (Package Rename (Optional) & Cleanup) | None (patterns in this file) |

---

## @MCA2-* Marker Classification

All preserved logic from MCA1 services, helpers, mappers, and utils MUST be classified and marked.

| Category | Marker | Action | Permanent? |
|---|---|---|---|
| **Presentation logic** | `// @MCA2-PRESENTATION` | Formatting, display mapping, response shaping for front-end | YES — permanently appropriate in EPS layer |
| **Validation logic** | `// @MCA2-VALIDATION` | Input validation, field checks, error message construction | YES — permanently appropriate in EPS layer |
| **Mapping logic** | `// @MCA2-MAPPING` | DTO transformation, field mapping, type conversion | YES — permanently appropriate in EPS layer |
| **Business rules** | `// @MCA2-REVIEW-BUSINESS-RULE` | Business decisions, eligibility checks, routing, calculations | Review later — may migrate to downstream API |
| **Data assembly** | `// @MCA2-REVIEW-DATA-ASSEMBLY` | Multi-source aggregation, cross-domain joins | Review later — may migrate to downstream API |
| **DB access** | `// @MCA2-REVIEW-DB-ACCESS` | JDBC, DataSource, SQL queries | Keep logic, mark — may need REST API created |
| **Team enhancement** | `// @MCA2-TEAM-ENHANCEMENT` | Caching, performance optimizations added during migration | Not a migration requirement |
| **MIS tech debt** | `// @MCA2-TECH-DEBT-MIS` | MIS call preserved via MisClient; uplift to RestClient.callRest() later | Review later — tech debt to be uplifted |

**Marker placement:** Place the marker comment on the line ABOVE the method or block it classifies.
For single-line expressions, place it on the same line at the end.

---

## 14-Phase Execution Plan

### Pre-Migration Analysis

**Actions:**
1. Read all source files under `src/main/java/` and `src/test/java/`
2. Catalog all MCA1 patterns present (controllers, services, helpers, mappers, validators, utils)
3. Identify all `scp-eps-*` dependencies in `build.gradle`
4. Count domains (controller count = domain count)
5. Assess typed vs. untyped decision (Part I)
6. Assess caching need (Part K decision tree)
7. Identify all business logic to preserve

**Output:** A migration plan listing:
- Files to create/modify/delete
- Stubs needed (from `reference/migration-stubs.md` catalog)
- Single-domain vs. multi-domain structure (Part J)
- Typed vs. untyped return types (Part I)
- Caching yes/no (Part K)

### Phase 1: Build System (build.gradle)

**Actions:**
1. **Read `reference/transformation-mapping.md` dependency tables FIRST** — exact group IDs vary
2. Replace BOM: `com.barclays.eps:mca-dependencies:6.2.x` -> `com.barclays.global.mca:mca-dependencies:{MCA2_BOM}` (default: 2.3.021)
3. Remove all `scp-eps-*` dependencies
4. Remove `mca-logging-spy`, `is-fwork-slf4j`, `is-logging-slf4j`
5. Remove `mca-service-locator`
6. Remove all EBS/EDO JARs (`ebs_*`, `egs_*`, `edo_*`) — **unless** any `ServiceManager.doService()` call uses Option 3 (MisClient), in which case keep the EBS/EDO JARs required by MisClient
7. Remove all database drivers (`ojdbc7`, `db2jcc4`)
8. Remove `scp-eps-test-common`
9. Add 4 core MCA2 libs (DEC-019): `mca-eps-core`, `mca-logging-config-logback`, `mca-service-client-starter`, `mca-response-handling-core`
10. Add project-specific libs as needed
10a. If any `ServiceManager.doService()` call will use Option 3 (MisClient): add `com.barclays.global.mca:mca-mis-client` (from BOM)
11. Add `mockito-core:{MOCKITO_VERSION}` (default: 5.14.2) and `mockito-junit-jupiter:{MOCKITO_VERSION}` (default: 5.14.2)
12. Remove OpenRewrite plugin blocks

**Constraint:** Do NOT add `mca-context`, `mca-context-utils`, `mca-spring-context-utils`,
`mca-exception-handling-core`, `mca-exception-handling-spring` — these are transitive from
`mca-eps-core` (DEC-019). Do NOT add `mca-filter-contexts` — removed after 1.0.003 (DEC-018).

### Phase 2: Application Bootstrap

**Actions:**
1. Create `Application.java` with `@SpringBootApplication` + `@EnableExperienceAPI`
2. Create `ApplicationConfig.java` with all `@Bean` definitions
3. If any doService call uses Option 3 (MisClient): add `@EnableMisServiceClient` to Application class

**Constraint:** Import only `ApplicationConfig.class` (DEC-022). No `@EnableSpringServiceLocator`.

### Phase 3: Configuration (XML to Java)

**Actions:**
1. Delete all XML config files
2. Delete `DataSourceConfig.java` (zero DB connections in MCA2)
3. Update `application.properties` (see `reference/transformation-mapping.md` properties section)
4. Configure REST client YAML if applicable
5. For multi-domain projects (Part J): create `config/`, `controller/`, `service/`, `service/impl/`, `mapper/`, `beans/` directories

### Phase 4: Controllers

**Actions:**
- Remove `extends EpsServiceAbstractController`
- Remove `implements` controller interface — controller interfaces are not needed in MCA2
- Rename class from `*ControllerImpl` to `*Controller` (drop `Impl` suffix)
- Delete the controller interface class — it is MCA1 boilerplate
- Replace `@Resource` with constructor injection
- Remove `HttpServletRequest` from method signatures
- Return `Response<T>` via `Response.<T>assemble().build(data)` (DEC-017, DEC-020)
- For void endpoints: return `ResponseEntity<Void>` (Part L)

### Phase 5: Services (with preserved logic)

**Actions (CRITICAL — behavior-preservation):**
- Remove `extends EpsAbstractService`
- Replace `@Resource` with constructor injection
- **PRESERVE all validation logic** — mark `@MCA2-VALIDATION`
- **PRESERVE all mapping logic** — mark `@MCA2-MAPPING`
- **PRESERVE all helper logic** — mark `@MCA2-PRESENTATION`
- **PRESERVE all business rules** — mark `@MCA2-REVIEW-BUSINESS-RULE`
- **PRESERVE all data assembly** — mark `@MCA2-REVIEW-DATA-ASSEMBLY`
- Remove `HttpServletRequest` from method signatures

**Constraint: What NOT to strip:**
- Validation methods from `Validate*ServiceImpl` classes
- Mapping methods from `*MapperImpl` classes
- Helper methods from `*Helper` classes
- Computation logic (balance aggregation, fee calculation, pagination)
- Business rules (eligibility checks, account type classification)
- Error code handling and error message construction

### Phase 6: Context & Headers

**Actions:**
1. Replace `EpsServiceHelper.getUserBean(request)` with `contextProvider.getIOLContext()`
2. Replace all `UserBean`, `CustomerBean`, `AccountBean` field access with direct `IOLSchema` access via `contextProvider.getIOLContext().getUserContext()`, `.getCustomerContext()`, `.getAccountContext()`
3. Replace all `com.barclays.scp.eps.common.*` type references with MCA2 equivalents — do NOT create stub classes
4. If business logic does complex processing on user/customer/account context fields, refactor to work directly with `IOLSchema` types

### Phase 7: REST Clients

**Actions:**
- Replace `ServiceManager.doService()` — ask user PER CALL SITE:
  - Option 1: `restClient.callRest()` (framework, recommended)
  - Option 2: `APIServiceManager` wrapper (team-level)
  - Option 3: `MisClient` from `mca-mis-client` (tech debt — mark `@MCA2-TECH-DEBT-MIS`)
- If any call uses Option 3: ensure `mca-mis-client` dependency is in build.gradle and `@EnableMisServiceClient` is on Application class

### Phase 8: Exception Handling + Stub Graduation

**Actions:**
1. Replace framework exception handling:
   - `EpsApplicationException` in framework dispatch -> `RestCallErrorException`
   - Auto-configured `ExceptionControllerAdvice` handles everything (DEC-021)
   - No custom `GlobalExceptionHandler` needed
2. **Graduate EpsApplicationException stub** to `ApplicationException(Message)`:
   - Replace `throw new EpsApplicationException(...)` with `throw new ApplicationException(Message.create(code, title))`
   - Replace `catch (EpsApplicationException)` — in MCA2 with MisClient, checked exceptions are wrapped by `reduce()`. Use `catch (Exception)` + `findCause()` pattern to walk the cause chain. See `reference/common-pitfalls.md` Pitfall 19.
   - Remove `EpsApplicationException` stub file after all references are replaced.
3. **Graduate MessageBeanHelper stub** — remove field/constructor param from all services. Replace error DTO population with `throw new ApplicationException(Message.create(code, title))`. Delete stub file.
4. **Graduate EpsResponseBean stub** — remove `extends EpsResponseBean` from domain beans. Add `implements Serializable` if the original was serializable. Delete stub file.

### Phase 9: Helpers & Utilities

**Actions:**
1. **PRESERVE completely** — helpers, mappers, validators, and utils contain business logic
2. Update imports from `com.barclays.scp.eps.common.*` to stub imports
3. Replace `LogHelper.*` with SLF4J:
   - `LogHelper.error(Class, method, msg)` -> `logger.error(msg, ex)`
   - Add `private static final Logger logger = LoggerFactory.getLogger(...)` where needed
4. Remove `import com.barclays.scp.eps.common.utils.LogHelper`
5. Mark each class/method with appropriate `@MCA2-*` marker

### Phase 10: Filter Chain

**Actions:**
- Delete framework filter registrations — auto-configured by `@EnableExperienceAPI`
- Preserve app-owned filters (e.g., `CrossScriptingFilter`)
- Remove MCA1 `FilterRegistrationBean` declarations for framework filters

### Phase 11: Testing (OPTIONAL — ask user)

**This phase is optional.** Post-migration, developers may update/add/remove code and need to rewrite tests. The agent MUST ask the user via `AskUserQuestion` whether to execute test migration now or defer it.

**If deferred:** Log `[SKIP] Phase 11: deferred by user` and proceed to Phase 12.

**If executing:** Follow the 3 sub-phases below.

#### Phase 11a: Size, Plan & Read Templates

1. Read `reference/test-migration-guide.md`, `reference/test-templates.md`, and `reference/common-pitfalls.md`
2. Size every source class (`wc -l`) — identify the largest classes upfront
3. Plan ALL tests before writing any. For each class, pick a template from `test-templates.md`:
   - Controller → Template 1 (MockMvc)
   - Service → Template 2 (Mockito happy + error) or Template 3 (findCause error path)
   - Large helper (1,000+ lines) → Template 4 (targeted methods)
   - ApplicationConfig → Template 5 (context loads)
   - POJO beans → Template 6 (getter/setter batch)
   - MockData → Template 7 (shared utility)

**Minimum test count:**
```
(N controllers × 1) + (N services × 1) + 3 (mapper + config + MockData) + 1 per APIServiceManager
```

#### Phase 11b: Batch Write (single pass, no builds between files)

Write ALL planned tests in one batch using the templates. Do NOT run `./gradlew test` between individual files.

**Test patterns:**
- Use `@ExtendWith(MockitoExtension.class)` + `@MockitoSettings(strictness = Strictness.LENIENT)`
- Mock `RequestContextProvider`, `APIServiceManager`, `UtilityMapper`
- For `IOLContextAdapter` tests: mock `IOLSchema`, `UserContext`, and `Channel` (`com.barclays.global.mca.libs.context.data.Channel`)
- For static MCA1 classes: `MockedStatic<DateFactory>`, `MockedStatic<LocalityInfo>`
- Exception: `ReferenceData` cannot use `MockedStatic` — use `spy()` + `doReturn()`

#### Phase 11c: Verify & Patch (max 2 iterations)

1. Run `./gradlew test jacocoTestReport`
2. Use `{PLUGIN_ROOT}/tools/analyze-coverage-gaps.sh` to rank coverage gaps:
   ```bash
   "{PLUGIN_ROOT}/tools/analyze-coverage-gaps.sh" "${PROJECT_PATH}" --threshold=70 --top=15
   ```
3. If coverage passes — done. If not, write targeted tests for top 5 HIGH-priority classes.
4. **Cap at 2 iterations.** If still failing after 2 rounds, ask user whether to continue or accept.

**Do NOT modify JaCoCo exclusion lists, `afterEvaluate` blocks, or `codeCoverageTask` configuration to bypass the coverage threshold.** Coverage must be achieved by writing tests, not by excluding classes or lowering the threshold.

**Coverage recovery priority (highest ROI first):**
1. Largest helper/utility classes (most missed instructions per test written)
2. Re-enable @Disabled tests with `MockedStatic` where possible
3. Service impl classes with new exception handling paths
4. ApplicationConfig spring context test
5. POJO bean getter/setter tests (low effort, moderate coverage gain)

### Phase 12: OAS3 Specification (MANDATORY — do NOT skip)

**Actions:**
1. Read `reference/oas-migration-guide.md` and `reference/oas-template/openapi.yaml`
2. If MCA1 OAS exists: migrate header references (`UserContextHeader` to `X-UserContext`), error models (`EpsResponseBean` to `ErrorResponseType`), rename models (drop `Bean` suffix), add missing error responses (403, 429, 503)
3. **If no OAS exists: you MUST generate a new spec** from the migrated controllers using the MCA2 template, with proper IOL header parameters and `Response<T>` wrapper schemas. Do NOT skip generation — it is mandatory.
4. Enable OAS validation via `core.default.oas.enabled=true` in `application.properties`

### Phase 13: Process.json (Journey Definition)

**Actions:**
1. Read `reference/transformation-mapping.md` section 16
2. Remove `"type": "mca1"` from all process.json files
3. Update URIs from `scp-eps-*` to `mca-eps-*`
4. Rename process IDs from MCA1 naming convention (e.g., `scpEpsAudit_v1` to `mcaEpsAudit_v1`)
5. Update `uiModuleName` if the UI module was renamed
6. Update chained process IDs in task events
7. Preserve all endpoint definitions, context arrays, and structure

### Phase 14: Package Rename (MUST ASK) & Cleanup

**Actions:**
1. **MUST ask the user via `AskUserQuestion`** whether to rename packages — do NOT skip this prompt:
   - **Option A: Rename now (Recommended)** — rename `com.barclays.scp.eps.*` to `com.barclays.mca.eps.*` in all source files and move files to new package directories
   - **Option B: Keep existing** — keep `com.barclays.scp.eps.*` package names; defer rename to a later stage
2. If Option A chosen: rename packages and move files to new package directories
3. Run final cleanup: remove orphaned MCA1 resources (`services.xml`, `UserBean.xml`, `services.properties`, `checkmarx.properties`, empty files)
4. Prune empty directories: `find src/ -type d -empty -delete`
5. Run `grep -r "EpsService\|EpsAbstract\|@ImportResource" src/` to verify no MCA1 framework remnants
6. Validate: `./gradlew clean build`

---

## Decision Trees

### Typed vs. Untyped Returns (Part I)

```
Does preserved business logic access response fields?
├── YES → Use typed wrapper beans with .getData()
└── NO → How many endpoints?
    ├── < 10 → Use typed wrapper beans (safer)
    └── 10+ → Use Object pass-through (Pattern 4a)
```

### Caching (Part K)

```
Does MCA1 source already implement caching?
├── YES → Carry forward as EHCache. Mark @MCA2-TEAM-ENHANCEMENT.
└── NO → Does project have shared reference/preload data?
    ├── YES (dropdowns, rule codes) → Consider adding (team decision).
    └── NO (customer-specific, transactional) → Do NOT add caching.
```

### Multi-Domain vs. Single-Domain (Part J)

```
How many distinct business domains?
├── 1-2 → Single-domain: 1 Controller + 1 Service
└── 3+ → Multi-domain: N Controller + N Service pairs, shared infra
```

### Void / Fire-and-Forget (Part L)

```
Does the MCA1 endpoint return meaningful data to the caller?
├── YES → Return Response<T> or ResponseEntity<Object>
└── NO (audit write, session cleanup, notification)
    → void service method + ResponseEntity<Void> controller
```

### Service Dispatch per Call Site (DEC-016)

For EACH `ServiceManager.doService()` call, ask the user:

```
Which replacement for this ServiceManager.doService() call?
├── Option 1: RestClient.callRest() (Recommended)
│   └── Framework-level REST client from mca-service-client-starter
├── Option 2: APIServiceManager wrapper
│   └── Team-level convenience wrapper over RestClient
└── Option 3: MisClient (Tech Debt)
    └── Preserves MIS call via mca-mis-client. Requires @EnableMisServiceClient.
        Mark with @MCA2-TECH-DEBT-MIS. Uplift to RestClient later.
```

### Package Rename (Optional)

```
Rename com.barclays.scp.eps.* packages to com.barclays.mca.eps.*?
├── Option A: Rename now → Rename all packages and move files
└── Option B: Keep existing (DEFAULT) → Defer rename to a later stage
```

### Service Consolidation (DEC-023)

```
Has the feature team requested service consolidation?
├── YES → Consolidate to 1 service per domain
└── NO → Preserve N-services structure from MCA1 (DEFAULT)
```

---

## File-by-File Transformation Rules

### build.gradle
- **Action:** Replace dependencies per `reference/transformation-mapping.md`
- **Preserve:** Project-specific non-MCA1 dependencies
- **Remove:** All `scp-eps-*`, all `ebs_*`/`egs_*`/`edo_*` (unless Option 3 MisClient chosen — keep EBS/EDO JARs), all DB drivers, OpenRewrite blocks

### Application.java (bootstrap)
- **Action:** `@EnableExperienceAPI`, `@Import({ApplicationConfig.class})`, rename to `Application`
- **Remove:** `@ImportResource`, `@EnableSpringServiceLocator`, `MCAMQAutoConfiguration`, `DataSourceConfig`

### ApplicationConfig.java
- **Action:** Create single `@Configuration` with all `@Bean` definitions
- **Preserve:** Bean names from XML config (`@Bean(name = "...")`)
- **Remove:** All XML config files

### Controllers
- **Action:** Remove `extends EpsServiceAbstractController`, remove `implements` controller interface, rename `*ControllerImpl` to `*Controller`, constructor DI, `Response<T>`
- **Remove:** `HttpServletRequest` parameter, `@Resource` setter injection, controller interface classes
- **Delete:** Controller interface files (MCA1 boilerplate, not needed in MCA2)

### Services
- **Action:** Remove `extends EpsAbstractService`, constructor DI, replace dispatch
- **PRESERVE:** ALL business logic (validation, mapping, computation, rules, data assembly)
- **Mark:** All preserved logic with appropriate `@MCA2-*` markers

### Helpers / Mappers / Validators / Utils
- **PRESERVE COMPLETELY** — these ARE the business logic
- **Action:** Update imports only (MCA1 -> stubs or MCA2), replace `LogHelper` with SLF4J
- **Mark:** Each class with appropriate `@MCA2-*` marker

### XML config files
- **Action:** Delete all

### DataSourceConfig.java
- **Action:** Delete — zero DB connections in MCA2

### FilterRegistration classes
- **Action:** Delete framework filter registrations — auto-configured by `@EnableExperienceAPI`
- **Preserve:** App-owned filters (e.g., `CrossScriptingFilter`)

### application.properties
- **Action:** Remove MCA1 properties, add MCA2 properties (see `reference/transformation-mapping.md`)
- **Change:** `spring.application.name` from `scp-eps-*` to `mca-eps-*`

### process.json (Journey Definition)
- **Action:** Move from `src/main/resources/{name}.json` to `src/main/resources/processes/{name}.json` (MCA2 `ClasspathResourceProcessService` requires `processes/` subdirectory)
- **Action:** Update process ID from path-style (`epsaudit/process/audit`) to MCA2 format (`{name}_v1`)
- **Action:** Remove MCA1 shim fields: `"mcaType"`, `"mca2ui"`, `"fragmentFileContentRequested"`
- **Action:** Rename `"context"` → `"contexts"` (plural) on all endpoints
- **Action:** Remove `?cc=true` from all endpoint URIs (MCA2 uses `"contexts"` array for context injection)
- **Action:** Remove `"type": "mca1"` from any endpoint that has it
- **Action:** Use semantic task IDs (e.g., `AUD001`) instead of numeric (`"1"`, `"2"`)
- **Action:** Add `apiDefinition.oas` block referencing OAS spec
- **Preserve:** All endpoint definitions, task structure, event/transition logic
- **Reference:** See `reference/transformation-mapping.md` Pattern 13 and `docs/MCA2-EPS-Guide/2-Core-Frameworks/Process-System.md` for full MCA2 process.json spec

---

## Verification Checklist

After migration, verify ALL of the following:

### Framework Replacement (must be zero)
- [ ] Zero `com.barclays.scp.eps.common` imports in `src/main/` (replaced with stubs or MCA2)
- [ ] Zero `extends EpsServiceAbstractController` in any controller
- [ ] Zero `extends EpsAbstractService` in any service
- [ ] Zero `LogHelper` references in any source file
- [ ] Zero `FilterRegistrationBean` for framework filters
- [ ] Zero XML config files in resources (except test resources)
- [ ] Zero `scp-eps-*` dependencies in build.gradle
- [ ] Zero `ebs_*` / `egs_*` / `edo_*` dependencies in build.gradle (unless Option 3 MisClient chosen — keep EBS/EDO JARs)
- [ ] Zero `DataSource` beans (unless marked `@MCA2-REVIEW-DB-ACCESS`)
- [ ] Zero `ServiceManager.doService()` calls (replaced with RestClient, APIServiceManager, or MisClient per DEC-016)
- [ ] Zero `@ImportResource` annotations
- [ ] Zero `@EnableSpringServiceLocator` annotations
- [ ] Zero `"type": "mca1"` in process.json

### MCA2 Framework (must be present)
- [ ] `@EnableExperienceAPI` on `Application.java`
- [ ] `@Import({ApplicationConfig.class})` on `Application.java`
- [ ] `mca-dependencies:{MCA2_BOM}` (default: 2.3.021) BOM in build.gradle
- [ ] 4 core MCA2 libs in build.gradle (mca-eps-core, mca-logging-config-logback, mca-service-client-starter, mca-response-handling-core)
- [ ] `@EnableMisServiceClient` on `Application.java` (only if any call site uses Option 3 MisClient)
- [ ] `mca-mis-client` in build.gradle (only if any call site uses Option 3 MisClient)
- [ ] All packages renamed from `com.barclays.scp.eps` to `com.barclays.mca.eps` (only if user chose Option A for package rename)
- [ ] `spring.application.name` updated to `mca-eps-*`

### Behavior Preservation (must be true)
- [ ] ALL validation logic preserved (from `Validate*ServiceImpl`, `ValidateUtil`, etc.)
- [ ] ALL mapper logic preserved (from `*MapperImpl` classes)
- [ ] ALL helper logic preserved (from `*Helper` classes)
- [ ] ALL business rules preserved (eligibility, classification, routing, calculation)
- [ ] ALL data assembly logic preserved (multi-source aggregation)
- [ ] `@MCA2-*` markers present on all preserved logic
- [ ] Zero dropped logic — every method from MCA1 service/helper/mapper/validator classes accounted for

### No Stubs (aggressive strategy)
- [ ] Zero `migration/stubs/` directory — no stub classes created
- [ ] Zero `@MCA2-STUB` markers in any source file
- [ ] Zero `com.barclays.scp.eps.common` imports remaining (all replaced with MCA2 equivalents)

### Tests (Part M minimums)
- [ ] 1 controller test per controller (MockMvc)
- [ ] 1 service test per service impl (happy + error path)
- [ ] 1 UtilityMapper test
- [ ] 1 ApplicationConfig test
- [ ] 1 MockData.java utility
- [ ] Total test files >= `(N controllers) + (N services) + 3`

### Build
- [ ] `./gradlew clean build` succeeds (includes `codeCoverageTask` threshold gate)
- [ ] `./gradlew test` succeeds
- [ ] No compile warnings for missing MCA1 types
- [ ] JaCoCo instruction coverage meets `codeCoverageTask.ccLmit` threshold (typically 70%)
- [ ] No large helper classes with <50% coverage (dominant coverage drag — see Pitfall 21)

---

## Common Pitfalls

1. **Dropping business logic** — The #1 risk. If an MCA1 service has 500 lines of validation/mapping logic, all 500 lines must appear in the MCA2 output with `@MCA2-*` markers. Check the line count.

2. **Wrong dependency group IDs** — MCA2 uses multiple group ID prefixes: `com.barclays.global.mca` (most), `com.barclays.mca` (mca-eps-libs-audit). Always read `reference/transformation-mapping.md` first.

3. **Adding transitive deps explicitly** — Do not declare `mca-context`, `mca-exception-handling-core`, etc. They come transitively from `mca-eps-core` (DEC-019).

4. **Custom GlobalExceptionHandler** — Not needed. Framework auto-configures `ExceptionControllerAdvice` via `@EnableExperienceAPI` (DEC-021).

5. **Importing RestClientsConfig** — Consolidated into `ApplicationConfig` (DEC-022). Import only `ApplicationConfig`.

6. **Service consolidation by default** — Do NOT consolidate N services to 1 unless the feature team requests it (DEC-023).

7. **Adding EHCache by default** — Only if MCA1 had caching or team requests it (DEC-024).

8. **Missing IOLContextAdapter** — If preserved logic calls `userBean.getUserId()`, you need the adapter to populate the stub from `IOLSchema`.

9. **Using `@IOLContext` in services** — The reference uses `RequestContextProvider.getIOLContext()` in services, not `@IOLContext` parameter injection (which is controller-only).

10. **Leaving `HttpServletRequest` in signatures** — MCA2 uses `RequestContextProvider` or `@IOLContext`, not direct servlet access.

11. **Missing `@MCA2-*` markers** — Every block of preserved logic needs a marker. Missing markers make it impossible for the team to review and plan future refactoring.

12. **`scp-eps-libs-customer` transitively pulls `scp-eps-core-comm`** — Must remove it AND create stubs for its types. See `reference/migration-stubs.md`.

13. **Static class initializer failures in tests** — `DateFactory`, `LocalityInfo`, `ReferenceData` trigger `ServiceLocator` static initializers. Use `MockedStatic` (except `ReferenceData` — use `spy()`).

14. **EpsResponseBean, EpsApplicationException, MessageBeanHelper — graduate stubs** — These have direct MCA2 replacements. `EpsResponseBean` → plain POJO. `EpsApplicationException` → `ApplicationException(Message)`. `MessageBeanHelper` → `throw ApplicationException(Message)` directly. Graduate (delete) these stubs during or after migration. See `reference/common-pitfalls.md` Pitfall 14.

15. **`mca-filter-contexts` does not exist** — Removed after 1.0.003 (DEC-018). Do not include.

16. **Missing `@EnableMisServiceClient` when using MisClient** — If any `ServiceManager.doService()` call uses Option 3 (MisClient), the Application class MUST have `@EnableMisServiceClient`. Without it, the `MisClient` bean will not be available and Spring will fail to start.

17. **Lambda effectively-final variables in MisClient `callService()`** — When converting `ServiceManager.doService()` to `misClient.callService(svc -> svc.method(uc, requestDto)).reduce()`, ensure `requestDto` is effectively final (assigned exactly once). Use `final` keyword or restructure the assignment. See `reference/common-pitfalls.md` Pitfall 17.

18. **`@SpringBootApplication scanBasePackages` needed when Application class is in a sub-package** — If the Application class is in `com.barclays.scp.eps.audit.config`, add `scanBasePackages = "com.barclays.scp.eps.audit"` to ensure controllers and services in sibling packages are scanned. See `reference/common-pitfalls.md` Pitfall 18.

19. **MisClient.reduce() wraps checked exceptions** — `reduce()` wraps checked exceptions (e.g., `NoRecordsFoundException`, `ServiceInvalidException`) in unchecked wrappers. You cannot catch checked exceptions directly from a try block containing `reduce()`. Use `catch (Exception)` + `findCause()` helper to walk the cause chain. See `reference/common-pitfalls.md` Pitfall 19.

20. **Mockito rejects checked exceptions from methods that don't declare them** — When mocking methods that internally call `MisClient.reduce()`, Mockito validates the throws clause. Wrap checked exceptions in `RuntimeException` in test setups: `thenThrow(new RuntimeException(new ServiceInvalidException(...)))`. See `reference/common-pitfalls.md` Pitfall 20.

21. **Coverage regression during migration** — Migration inherently drops code coverage due to: (a) new stub classes with no tests, (b) new code paths from exception handling changes (findCause pattern, new catch blocks), (c) @Disabled tests for static initializer classes, (d) new ApplicationConfig with no Spring context test. The build's `codeCoverageTask` (typically 70% gate) will fail. Large helper classes (1,000+ lines) dominate coverage metrics — a single untested helper can drag overall coverage below the threshold. See `reference/common-pitfalls.md` Pitfall 21.

---

## MCA2 @Enable* Annotations Reference

| Annotation | Module | Purpose |
|---|---|---|
| `@EnableExperienceAPI` | eps-core | Core EPS: filters, context, exceptions, response |
| `@EnableMisServiceClient` | mis-client | MIS backend client (add only if app uses MIS) |
| `@EnableSecureProxy` | secure-proxy-core | Gateway: auth, session, routing |
| `@EnableEHCacheContextStore` | context-store-ehcache | In-memory session storage |
| `@EnableReferenceData` | referencedata | CSV-based reference data |
| `@EnableBemServiceClient` | bem-client | BEM notification client |
| `@EnableSpringBootSSL` | spring-boot-ssl | mTLS with CN whitelisting |

## Agent Self-Check

- [ ] Step 0 executed first — plugin resource documents located before any migration work begins
- [ ] Dependency versions resolved from Nexus (Step 0b) — no hardcoded versions used
- [ ] Phase 0 (DevOps plugin) completed before any code migration phases
- [ ] All 14 phases executed in order; skipped phases logged with `[SKIP]` reason
- [ ] Gated phases (7, 11, 14) returned gate signal to orchestrator before executing Part B
- [ ] Phase Ownership Table observed — no cross-phase pattern modifications
- [ ] Aggressive strategy applied — no stub/shim classes created under `migration/stubs/`
- [ ] All preserved business logic marked with appropriate `@MCA2-*` markers
- [ ] `./gradlew clean build` passes after Final Validation phase
- [ ] TECH-DEBT-REPORT.md written at project root after migration completes
