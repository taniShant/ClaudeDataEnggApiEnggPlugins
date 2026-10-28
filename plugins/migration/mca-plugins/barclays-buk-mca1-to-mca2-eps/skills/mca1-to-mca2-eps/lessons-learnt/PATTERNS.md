# Recurring Patterns — MCA1 to MCA2 Migration

## Pattern: Orphaned Test Resources

**Frequency:** Common
**Phase:** 14 (Cleanup)
**Issue:** MCA1 test infrastructure files (`services.xml`, `UserBean.xml`, `services.properties`) left behind after removing Java-side references (`@EnableSpringServiceLocator`, `GenericTestCase`).
**Resolution:** Scan `src/test/resources/` for files with zero Java references and delete them.

## Pattern: REST Call Stubs Not Fully Wired

**Frequency:** Common
**Phase:** 7 (REST Clients)
**Issue:** `ServiceManager.doService()` call sites replaced with WARN/TODO stubs instead of actual `RestClient.callRest()` or `MisClient.callService()` implementations.
**Resolution:** Phase 7 must fully wire replacements — inject named `RestClient` via `@Qualifier`, add `services.rest-clients.*` to test properties, update `ApplicationConfig` beans. No stubs allowed.

## Pattern: Endpoint Properties in Wrong File

**Frequency:** Common
**Phase:** 7 (REST Clients)
**Issue:** `services.rest-clients.*` endpoint properties added to `src/main/resources/application.properties` instead of test properties.
**Resolution:** All endpoint URLs go in `src/test/resources/application.properties` only. Production endpoints are injected externally at deployment.

## Pattern: OAS3 Spec Generation Skipped

**Frequency:** Common
**Phase:** 12 (OAS3 Specification)
**Issue:** Agent skips OAS3 generation when no existing spec is found, treating it as optional.
**Resolution:** OAS generation is mandatory. If no MCA1 OAS exists, the agent MUST generate a new spec from the migrated controllers.

## Pattern: Stub Classes Created Under Aggressive Strategy

**Frequency:** Common
**Phase:** 6, 8 (Context & Headers, Exception Handling)
**Issue:** Agent follows `migration-stubs.md` and creates 10-17 stub classes under `migration/stubs/` instead of replacing MCA1 types directly with MCA2 equivalents.
**Resolution:** `migration-stubs.md` is for behavior-preservation strategy only. Under aggressive strategy, every MCA1 type must be replaced directly — no stubs.

## Pattern: Package Rename Not Asked

**Frequency:** Common
**Phase:** 14 (Package Rename & Cleanup)
**Issue:** Agent skips the `AskUserQuestion` prompt for package rename, keeping legacy `com.barclays.scp.eps.*` packages by default.
**Resolution:** Phase 14 AskUserQuestion is mandatory and must not be skipped. "Rename now" is the recommended option.

## Pattern: checkmarx.properties Not Removed

**Frequency:** Common
**Phase:** 14 (Cleanup)
**Issue:** MCA1-era `checkmarx.properties` file left behind after migration.
**Resolution:** Added to Phase 14 orphan cleanup list.

## Pattern: Empty Package Directories Left Behind

**Frequency:** Common
**Phase:** 14 (Cleanup)
**Issue:** After package rename or file deletion, empty `com/barclays/scp/eps/` directory trees remain.
**Resolution:** Run `find src/ -type d -empty -delete` after all Phase 14 operations.

## Pattern: JaCoCo Exclusions Added to Bypass Coverage

**Frequency:** Occasional
**Phase:** 11 (Testing)
**Issue:** Agent modifies `jacocoTestReport.afterEvaluate` to exclude classes from coverage instead of writing tests.
**Resolution:** Do NOT modify JaCoCo configuration to bypass threshold. Coverage must be achieved by writing tests.
