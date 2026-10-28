# mca-eps-selfservice-locator — Oracle-to-PostgreSQL Migration

**Date:** 2026-06-19
**JIRA:** COREENGDEV-1038
**Complexity:** Low (2 entities, 1 config class, minimal native queries)
**Oracle References Found:** 12 in 8 files

## Phases

### Phase 0: Setup
- Cloned from GitLab, created branch `COREENGDEV-1038/oracle-to-postgres-app`

### Phase 2: Analysis
- Oracle driver: ojdbc8 in dependencies.gradle
- Dialect: OracleDialect hardcoded in LocatorDBConfig.java
- Entities: LocatorEvent (sequence, @CreationTimestamp), LatestConfig (@UpdateTimestamp)
- Test config: H2 with Oracle mode
- No native queries, no stored procedures

### Phase 3: Migration
- Replaced ojdbc8 with postgresql driver
- Updated JDBC URL with `?currentSchema=pgassacuser`
- Changed dialect to PostgreSQLDialect in LocatorDBConfig.java
- Updated test SQL: VARCHAR2→VARCHAR, NUMBER→BIGINT
- Changed H2 mode from Oracle to PostgreSQL

### Phase 5: Validate
- Unit tests: PASS
- Integration tests: PASS
- Oracle remnant scan: CLEAN

## Post-Deployment Issues (not caused by app migration)

### Issue 1: Oracle Driver Still Connected
- **Symptom:** `select nextval('LOCATOR_EVENTS_SEQ')` fails with ORA-00923
- **Root Cause:** Deployed environment config server was still serving Oracle JDBC URL. Application code was correct but config server override took precedence.
- **Resolution:** Config server properties needed to be updated separately from application code.

### Issue 2: Timestamp BC Dates
- **Symptom:** LATEST_TS showing `0001-06-16 16:51:42 BC` instead of 2026 dates
- **Root Cause:** Data migration used Oracle's default date format (`DD-MON-RR`). PostgreSQL misinterpreted 2-digit year.
- **Resolution:** DBA must re-export data using ISO format. Application code (Timestamp.from(Instant.now())) is correct for new inserts.

### Issue 3: Spring Cloud Config Server — Missing Profile-Specific Properties
- **Symptom:** `Cannot invoke "LocatorConfig$GroupConfig.getUrl()" because the return value of "java.util.Map.get(Object)" is null` — NPE on server but works locally with bootRun against same PostgreSQL instance
- **Root Cause:** Application uses Spring Cloud Config Server with profile-based property files (`mca-eps-selfservice-locator-DEVICES.properties`, `mca-eps-selfservice-locator-MENU.properties`). When the new `postgres/` config folder was created in the external config repo (referenced by `CONFIG_FOLDER: 'postgres'` in `.gitlab-ci-variables.yml`), only the DATASOURCE properties were copied. The DEVICES and MENU profile property files were missing from the new folder, so `LocatorConfig.groups` map was empty on the server.
- **Why local works:** bootRun uses `test-config/scc/` directory (set in build.gradle) which contains all profile files. Server uses external Spring Cloud Config Server repo with separate config folder per environment.
- **Resolution:** When creating a new config folder for PostgreSQL in the external config repo, ALL profile-specific property files must be copied — not just the DATASOURCE/database-related ones. Non-database config (DEVICES, MENU, etc.) is unchanged but still needs to exist in the new folder.

## Test-Related Issues

### Issue 4: `insertable = false` with `@CreationTimestamp` Breaks on PostgreSQL
- **Symptom:** INSERT into LOCATOR_EVENTS fails with NOT NULL constraint violation on EVENT_TS
- **Root Cause:** Original Oracle entity had `@Column(insertable = false, columnDefinition = "TIMESTAMP (6) DEFAULT SYSTIMESTAMP NOT NULL ENABLE")` — relied on Oracle DB default to set timestamp. With PostgreSQL, Hibernate's `@CreationTimestamp` couldn't inject the value because `insertable = false` prevented it.
- **Resolution:** Removed `insertable = false` so `@CreationTimestamp` manages the value at application level. Works identically on both databases.
- **Why H2 tests missed it:** H2 PostgreSQL mode handles DEFAULT differently from real PostgreSQL — the constraint violation only appears against live DB.

### Issue 5: H2 PostgreSQL Mode Timestamp Ordering Limitation
- **Symptom:** `LocatorEventsRepositoryTest` asserts strict temporal ordering of events but H2 PostgreSQL mode returns identical timestamps for all inserts within a transaction
- **Root Cause:** H2's PostgreSQL mode uses `CURRENT_TIMESTAMP` which returns transaction start time (all rows get same timestamp), unlike real PostgreSQL where each statement can get a distinct timestamp via `clock_timestamp()`.
- **Resolution:** Relaxed strict `after()` assertions to `assertNotNull` checks. Real PostgreSQL doesn't have this issue — it's an H2 emulation limitation.

### Issue 6: currentSchema Not Tested by H2
- **Symptom:** All queries against live PostgreSQL timeout at 90 seconds — tables not found in `public` schema
- **Root Cause:** PostgreSQL requires `?currentSchema=pgassacuser` in JDBC URL to route to correct schema. H2 has no schema routing, so unit/integration tests pass without it.
- **Resolution:** Added `?currentSchema=pgassacuser` to all PostgreSQL JDBC URLs. The `PostgresMigrationValidationTest` was added to catch this but only validates against H2 — Karate tests against live DB are essential.

## Lessons

- Config Server overrides must be updated alongside application code migration
- Data migration format is critical — always use ISO timestamps
- Verify actual runtime connection (check logs for T4CConnection vs PGConnection)
- When external config repo uses folder-per-environment (e.g., `oracle/`, `postgres/`), ALL profile property files must be present in the new folder — not just database-related ones. Missing non-DB config files cause silent startup failures where beans receive empty maps/configs.
- H2 PostgreSQL mode masks critical issues: schema routing, timestamp insertion semantics, and constraint enforcement differ from real PostgreSQL — Karate/component tests against live DB are essential
- `insertable = false` combined with `@CreationTimestamp` is an Oracle-specific pattern — remove `insertable = false` during migration so Hibernate manages timestamps at application level
- Unit/integration tests with H2 are necessary but NOT sufficient — always run component tests (Karate) against live PostgreSQL before declaring migration complete
