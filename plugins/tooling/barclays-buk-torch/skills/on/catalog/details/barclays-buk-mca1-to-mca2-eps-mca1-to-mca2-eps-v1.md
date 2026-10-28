# barclays-buk-mca1-to-mca2-eps-mca1-to-mca2-eps-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-mca1-to-mca2-eps-mca1-to-mca2-eps-v1` |
| Plugin name | `barclays-buk-mca1-to-mca2-eps` |
| Component type | skill-model-invocable |
| Owner | MCA Core Engineering |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-mca1-to-mca2-eps@barclays-cio-buk |
| Native command | `/barclays-buk-mca1-to-mca2-eps:mca1-to-mca2-eps` |
| Skill name | `mca1-to-mca2-eps` |

## Description

MCA1 to MCA2 migration skill (aggressive strategy). Complete transformation mapping for migrating applications from scp-eps-java-common (MCA1) to mca-java-common (MCA2). Use when user says "migrate MCA1", "MCA2 migration", "replace scp-eps", "upgrade to mca-java-common", or runs /migrate-mca1-to-mca2. Replaces ALL MCA1 patterns with MCA2 equivalents — no stubs, no compatibility shims. Preserves business logic but replaces all framework types directly. Derived from frozen MDD validated by Pilot 1 (scp-eps-audit) and Pilot 2 (scp-eps-bal-and-enq).

## When to use

Use when migrating an EPS application from scp-eps-java-common (MCA1) to mca-java-common (MCA2) using the aggressive replacement strategy — all MCA1 framework types, patterns, and dependencies are replaced inline with MCA2 equivalents without creating compatibility stubs or shims; this skill is NOT for incremental/partial migrations, stub-based migrations, or projects that have not already completed JDK 21, Spring Boot 3.3+, Jakarta EE namespace, and Gradle 8.5 upgrades.

## Inputs

- Source tree under `src/main/java/` and `src/test/java/` (the MCA1 application to migrate)
- `build.gradle` containing `scp-eps-*` dependencies and the MCA1 BOM (`com.barclays.eps:mca-dependencies:6.2.x`)
- XML configuration files (to be deleted and replaced with Java config)
- `application.properties` (to be updated with MCA2 property keys)
- Optional: OAS2/Swagger specification files (migrated to OAS3 in Phase 12)
- Optional: `process.json` (updated in Phase 13)
- Gate decisions provided interactively by the user at Phase 7 (REST client strategy), Phase 11 (test writing vs. skip), and Phase 14 (package rename yes/no)
- MCA2 BOM version (default: `2.3.021`), Mockito version (default: `5.14.2`)

## Preconditions

- JDK migration to Java 21 is complete
- Spring Boot 3.3+ upgrade is complete
- Jakarta EE namespace migration (`javax` → `jakarta`) is complete
- Gradle 8.5 is configured
- The project uses scp-eps-java-common (MCA1) framework patterns (controllers extending `EpsServiceAbstractController`, services extending `EpsAbstractService`, `@Resource` injection, XML config, etc.)
- Reference documents are accessible at `reference/transformation-mapping.md`, `reference/dependency-mapping.md`, `reference/migration-stubs.md` (for type lookup only), `reference/test-migration-guide.md`, `reference/test-templates.md`, `reference/oas-migration-guide.md`, `reference/oas-template/openapi.yaml`, `reference/pattern-mapping.md`, and `reference/common-pitfalls.md`
- The orchestrating command layer is present to handle gated phases (7, 11, 14) via `AskUserQuestion`

## Expected outputs

- Rewritten `build.gradle` with MCA2 BOM (`com.barclays.global.mca:mca-dependencies`), four core MCA2 libs (`mca-eps-core`, `mca-logging-config-logback`, `mca-service-client-starter`, `mca-response-handling-core`), Mockito dependencies, and all `scp-eps-*`/EBS/EDO/DB driver/OpenRewrite artifacts removed
- New `Application.java` (`@SpringBootApplication` + `@EnableExperienceAPI`) and `ApplicationConfig.java` with `@Bean` definitions
- All XML config files deleted; `application.properties` updated with MCA2 keys
- Controllers rewritten: no inheritance from `EpsServiceAbstractController`, no controller interfaces, constructor injection, `Response<T>` return types via `Response.assemble().build(data)`
- Services rewritten: no `EpsAbstractService`, constructor injection, all business logic preserved and classified with `@MCA2-*` markers (`@MCA2-VALIDATION`, `@MCA2-MAPPING`, `@MCA2-PRESENTATION`, `@MCA2-REVIEW-BUSINESS-RULE`, `@MCA2-REVIEW-DATA-ASSEMBLY`, `@MCA2-REVIEW-DB-ACCESS`, `@MCA2-TECH-DEBT-MIS`, `@MCA2-TEAM-ENHANCEMENT`)
- Migrated context/header access, REST clients (strategy chosen at Phase 7 gate), exception handling, helpers/utilities, and filter chain to MCA2 equivalents
- Optionally: migrated tests (JMock → Mockito, using pre-built templates), OAS3 specification, updated `process.json`, and renamed packages
- Pre-migration analysis plan listing files to create/modify/delete, domain structure, typed vs. untyped decisions, and caching assessment

## Exclusions

- Does NOT create stub or shim classes under `migration/stubs/` — `reference/migration-stubs.md` is used as a type reference only
- Does NOT strip or discard business logic from service layers
- Does NOT assume downstream REST APIs implement all business logic
- Does NOT consolidate N services into 1 (unless explicitly requested by feature team — DEC-023)
- Does NOT add caching by default (team-level enhancement — DEC-024)
- Does NOT perform JDK 21 migration, Spring Boot 3.3 upgrade, Jakarta EE namespace migration, or Gradle 8.5 setup (these are prerequisites)
- Does NOT add transitive dependencies explicitly (`mca-context`, `mca-context-utils`, `mca-spring-context-utils`, `mca-exception-handling-core`, `mca-exception-handling-spring`, `mca-filter-contexts`)
- Does NOT handle incremental or stub-based (conservative) migration strategies
- Is NOT directly user-invocable — it is invoked by an orchestrating command layer (e.g., `/migrate-mca1-to-mca2`)

## Verification

Verify that `build.gradle` contains no `scp-eps-*` dependencies and references the MCA2 BOM, that no Java source file imports any `com.barclays.eps.scp` or MCA1 framework type (e.g., `EpsServiceAbstractController`, `EpsAbstractService`, `EpsApplicationException`, `EpsResponseBean`, `MessageBeanHelper`, `UserBean`), and that all preserved business logic blocks are annotated with the appropriate `@MCA2-*` classification markers. A clean Gradle build (`./gradlew build`) with all migrated tests passing confirms end-to-end completion.
