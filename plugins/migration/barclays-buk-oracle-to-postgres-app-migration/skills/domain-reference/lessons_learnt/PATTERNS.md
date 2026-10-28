# Recurring Patterns — Oracle-to-PostgreSQL Application Migration

> Auto-maintained by orchestrator. Updated after each successful migration run.

---

## Pattern: Missing currentSchema in JDBC URL

- **Frequency:** 2 times across 2 runs
- **Trigger:** PostgreSQL JDBC URL configured without `?currentSchema=` parameter
- **Resolution:** ALWAYS append `?currentSchema={POSTGRES_SCHEMA}` to every PostgreSQL JDBC URL. This is enforced as an iron rule.
- **Example:** mca-eps-selfservice-locator — queries hit `public` schema instead of `pgassacuser`, causing relation-not-found errors

---

## Pattern: Oracle Driver Still Loaded at Runtime

- **Frequency:** 1 time across 2 runs
- **Trigger:** Application properties point to PostgreSQL but deployed container still has Oracle driver on classpath. HikariCP log shows `oracle.jdbc.driver.T4CConnection` despite PostgreSQL config.
- **Resolution:** Verify deployed logs show PostgreSQL connection, not Oracle T4C. Check for Oracle driver in parent BOMs, shared library folders, or container base images.
- **Example:** mca-eps-selfservice-locator — Hibernate dialect set to PostgreSQLDialect but connection was actually Oracle 19c, causing `select nextval()` to fail with ORA-00923

---

## Pattern: Timestamp Data Corruption After Migration

- **Frequency:** 1 time across 2 runs
- **Trigger:** Oracle DATE/TIMESTAMP columns exported in Oracle's default `DD-MON-RR` format. When imported to PostgreSQL, 2-digit year `26` interpreted as year 0026 (shows as `0001-06-16 BC`).
- **Resolution:** This is a DBA/data-migration issue, not an application issue. Ensure data export uses ISO format `YYYY-MM-DD HH24:MI:SS.FF6`. Application code is correct if using `Timestamp.from(Instant.now())`.
- **Example:** mca-eps-selfservice-locator — LATEST_TS and EVENT_TS columns showing BC dates after data migration

---

## Pattern: H2 Oracle Mode in Tests

- **Frequency:** Common (most projects)
- **Trigger:** Test JDBC URL contains `MODE=Oracle` for H2 in-memory database
- **Resolution:** Change to `MODE=PostgreSQL`. Also update test SQL scripts to remove Oracle syntax (VARCHAR2, NUMBER, SYSTIMESTAMP, SEQ.NEXTVAL).
- **Example:** Multiple projects — test passes but doesn't validate PostgreSQL behavior

---

## Pattern: Spring Cloud Config Server — Missing Non-DB Profile Properties in New Config Folder

- **Frequency:** 1 time across 2 runs
- **Trigger:** Application uses Spring Cloud Config Server with multiple profile-based property files (e.g., `-DATASOURCE.properties`, `-DEVICES.properties`, `-MENU.properties`). External config repo uses folder-per-environment (`oracle/`, `postgres/`). Migration creates new `postgres/` folder but only copies database-related properties.
- **Resolution:** When creating a new config folder in the external config repo, copy ALL profile-specific property files — not just DATASOURCE. Non-database configs (DEVICES, MENU, etc.) are unchanged by migration but must still be present in the new folder. The orchestrator should identify all profile-activated files and flag them for inclusion.
- **Example:** mca-eps-selfservice-locator — `LocatorConfig.groups` map was empty on BCP2 because `mca-eps-selfservice-locator-DEVICES.properties` and `mca-eps-selfservice-locator-MENU.properties` were missing from the `postgres/` config folder. NPE in `ContainerURLProvider.getContainerUrl()` — local bootRun worked fine because it uses `test-config/scc/` which has all files.
- **Detection:** App starts successfully, connects to PostgreSQL, but fails at runtime when accessing `@ConfigurationProperties`-bound maps/lists that are populated from non-DB profile files. Error is typically NPE on `.get()` from an empty map.
- **Prevention:** During Phase 2 (Analysis), scan for `spring.profiles.active` and list ALL profile-specific config files. In the migration report, flag any external config repo files that must be replicated to the new environment folder.

---

## Pattern: `insertable = false` with `@CreationTimestamp` Breaks on PostgreSQL

- **Frequency:** 1 time across 2 runs
- **Trigger:** Oracle entity uses `@Column(insertable = false, columnDefinition = "TIMESTAMP (6) DEFAULT SYSTIMESTAMP ...")` with `@CreationTimestamp`. Oracle DB default handles the timestamp. PostgreSQL INSERT fails with NOT NULL constraint violation because Hibernate can't inject the value.
- **Resolution:** Remove `insertable = false` from timestamp columns annotated with `@CreationTimestamp` or `@UpdateTimestamp`. Let Hibernate manage timestamps at application level — works identically on both databases.
- **Example:** mca-eps-selfservice-locator — `LocatorEvent.EVENT_TS` INSERT failed on live PostgreSQL. H2 tests passed because H2 handles DEFAULT differently.
- **Detection:** NOT caught by H2 unit/integration tests. Only discovered via Karate/component tests against live PostgreSQL.
- **Prevention:** During Phase 3 (Migration), scan all `@Column` annotations for `insertable = false` combined with `@CreationTimestamp`/`@UpdateTimestamp` and remove `insertable = false`.

---

## Pattern: H2 PostgreSQL Mode Masks Schema and Constraint Issues

- **Frequency:** 2 times across 2 runs
- **Trigger:** Tests use H2 with `MODE=PostgreSQL` which doesn't emulate: (1) schema routing (`currentSchema`), (2) timestamp insertion semantics with `insertable = false`, (3) strict constraint enforcement in some edge cases.
- **Resolution:** H2 tests are necessary but NOT sufficient. Always require Karate/component tests against live PostgreSQL before declaring migration complete. Add `PostgresMigrationValidationTest` as a baseline but understand its limitations.
- **Example:** mca-eps-selfservice-locator — H2 tests passed for both `currentSchema` and `insertable = false` issues that failed on live PostgreSQL.
- **Prevention:** Phase 5 (Validate) must include a checklist item: "Component tests against live PostgreSQL executed and passing." Do not rely solely on H2-based test results.

---

## Pattern: H2 PostgreSQL Mode Timestamp Ordering Differs from Real PostgreSQL

- **Frequency:** 1 time across 2 runs
- **Trigger:** Tests assert strict temporal ordering of rows inserted within the same transaction. H2's `CURRENT_TIMESTAMP` in PostgreSQL mode returns the transaction start time for all rows (identical timestamps), while real PostgreSQL can provide distinct timestamps per statement.
- **Resolution:** Relax strict ordering assertions in H2-based tests to `assertNotNull` checks. If ordering is critical, use `clock_timestamp()` in PostgreSQL or add an explicit sequence-based ordering column.
- **Example:** mca-eps-selfservice-locator — `LocatorEventsRepositoryTest` strict `after()` assertions failed with H2 PostgreSQL mode because all inserts got identical timestamps.
