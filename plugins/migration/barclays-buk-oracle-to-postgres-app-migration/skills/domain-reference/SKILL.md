---
name: domain-reference
description: "Oracle-to-PostgreSQL application migration domain reference — type mappings, property transformations, entity conversion rules, native query conversions, quality gate checks, iron rules, decision rules, and common pitfalls. Loaded by orchestrator and workers at phase gates."
user-invocable: false
---

# Oracle-to-PostgreSQL Application Migration — Domain Reference

> **Source:** MCA Core Engineering — Oracle-to-PostgreSQL Migration Runbook v1.0 (June 2026)
> **Owner:** MCA Core Engineering
> **Review trigger:** After each migration run or on Hibernate/PostgreSQL major version change
> **Status:** Reviewed

---

## Section 1: Overview & Scope

**What this plugin does:** Migrates a Spring Boot application's database connectivity from Oracle to PostgreSQL. Changes driver, dialect, properties, JPA entities, configuration classes, and test configuration.

**What this plugin does NOT do:**
- Migrate database schema (handled by `/oracle-to-postgres-database-migration`)
- Migrate stored procedures (PL/SQL → PL/pgSQL)
- Migrate data between databases
- Modify business logic unrelated to database connectivity

**Success Criteria:**
- Application compiles with PostgreSQL driver
- All unit tests pass
- All integration tests pass
- No Oracle references remain in active code
- Migration reports generated for MR reviewers

---

## Section 2: Phase Reference

| Phase | Name | Gate | Description |
|-------|------|------|-------------|
| 0 | Setup & Clone | Hard: branch created | Clone repo, create branch, init workspace |
| 1 | Pre-Migration Baseline | Soft: log results | Run tests, record baseline pass/fail counts |
| 2 | Analysis | Hard: analysis file exists | Detect all Oracle references |
| 3 | Migration | Hard: compilation passes | Update deps, properties, entities, config, tests |
| 4 | Validation Tests | Hard: test file created | Generate PostgresMigrationValidationTest |
| 5 | Validate | Hard: tests pass (or max retries) | Compile, test, fix loop (max 5) |
| 6 | Reports | Soft: reports exist | Generate migration-report.md, fixes-report.md |
| Push | Commit & MR | Anti-hallucination | Stage, commit, push, create MR |

---

## Section 3: Dependency Mappings

### Oracle → PostgreSQL Driver

| Oracle Dependency | PostgreSQL Replacement | Scope |
|---|---|---|
| `com.oracle.database.jdbc:ojdbc8` | `org.postgresql:postgresql` | `runtimeOnly` |
| `com.oracle.database.jdbc:ojdbc11` | `org.postgresql:postgresql` | `runtimeOnly` |
| `com.oracle.database.nls:orai18n` | (remove — not needed) | — |
| `com.oracle.database.security:osdt_cert` | (remove — not needed) | — |
| `com.oracle.database.xml:xmlparserv2` | (remove — not needed) | — |
| `com.oracle.database.observability:ojdbc8-observability` | (remove — not needed) | — |

### Test Dependencies (if TEST_STRATEGY=testcontainers)

| Dependency | Scope |
|---|---|
| `org.testcontainers:postgresql` | `testImplementation` |
| `org.testcontainers:junit-jupiter` | `testImplementation` |

### Version Resolution

Resolve from Barclays Nexus: `https://nexus.barcapint.com/nexus/content/groups/barclays/`
- PostgreSQL: `org/postgresql/postgresql/maven-metadata.xml`
- Testcontainers: `org/testcontainers/postgresql/maven-metadata.xml`

If Nexus unreachable: use latest known stable versions.

---

## Section 4: Property Transformation Rules

### JDBC URL

| Before (Oracle) | After (PostgreSQL) |
|---|---|
| `jdbc:oracle:thin:@host:1521/SID` | `jdbc:postgresql://host:5432/dbname?currentSchema={SCHEMA}` |
| `jdbc:oracle:thin:@host:1521:SID` | `jdbc:postgresql://host:5432/dbname?currentSchema={SCHEMA}` |
| `jdbc:oracle:thin:@(DESCRIPTION=...)` | `jdbc:postgresql://host:5432/dbname?currentSchema={SCHEMA}` |

**CRITICAL:** ALWAYS append `?currentSchema={POSTGRES_SCHEMA}` to the JDBC URL. PostgreSQL defaults to `public` schema. Without this parameter, queries target the wrong schema causing timeouts, errors, or silent data issues.

### Driver Class

| Before | After |
|---|---|
| `oracle.jdbc.OracleDriver` | `org.postgresql.Driver` |
| `oracle.jdbc.driver.OracleDriver` | `org.postgresql.Driver` |

### Hibernate Dialect

| Before | After |
|---|---|
| `org.hibernate.dialect.OracleDialect` | `org.hibernate.dialect.PostgreSQLDialect` |
| `org.hibernate.dialect.Oracle12cDialect` | `org.hibernate.dialect.PostgreSQLDialect` |
| `org.hibernate.dialect.Oracle10gDialect` | `org.hibernate.dialect.PostgreSQLDialect` |

### Connection Pool

| Property | Before | After |
|---|---|---|
| `connection-test-query` | `SELECT 1 FROM DUAL` | `SELECT 1` |
| `validationQuery` | `SELECT 1 FROM DUAL` | `SELECT 1` |

### Properties to Remove

- `oracle.net.tns_admin`
- `oracle.net.ssl_server_dn_match`
- `oracle.jdbc.defaultRowPrefetch`
- Any `oracle.*` prefixed property

---

## Section 5: Entity Transformation Rules

### Column Definition Conversions

| Oracle columnDefinition | Action | Rationale |
|---|---|---|
| `VARCHAR2(n)` | Remove `columnDefinition` | Hibernate infers `VARCHAR(n)` from `@Column(length=n)` |
| `NVARCHAR2(n)` | Remove `columnDefinition` | Use `@Column(length=n)` — PostgreSQL VARCHAR handles Unicode |
| `NUMBER(p,s)` | Remove | Hibernate infers from Java type (BigDecimal, Integer, Long) |
| `NUMBER(1)` (boolean) | Remove | Use Java `Boolean` type |
| `NUMBER` (no precision) | Remove | Hibernate infers BIGINT from Long, INTEGER from int |
| `TIMESTAMP(6)` | Keep as `TIMESTAMP(6)` | Same in PostgreSQL |
| `TIMESTAMP DEFAULT SYSTIMESTAMP` | `TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | SYSTIMESTAMP is Oracle-only |
| `RAW(16)` | `UUID` | Change Java type to `java.util.UUID` |
| `CLOB` | Remove | Use `@Lob` annotation or keep as Java `String` |
| `BLOB` | Remove | Use `@Lob` annotation or Java `byte[]` |
| `CHAR(1)` | Keep | Same in PostgreSQL |

**General Rule:** Remove `columnDefinition` wherever possible — let Hibernate derive the DDL type from the Java type. Only keep when PostgreSQL requires a specific type that differs from Hibernate's default.

### `insertable = false` with `@CreationTimestamp` / `@UpdateTimestamp` (Pilot Fix)

**Problem:** Oracle entities commonly use `@Column(insertable = false, columnDefinition = "TIMESTAMP (6) DEFAULT SYSTIMESTAMP ...")` combined with `@CreationTimestamp`. Oracle DB handles the default value at DB level. PostgreSQL INSERT fails with NOT NULL constraint violation because Hibernate's `@CreationTimestamp` cannot inject the value when `insertable = false` is set.

**Fix:** Remove `insertable = false` from any `@Column` annotation on a field also annotated with `@CreationTimestamp` or `@UpdateTimestamp`. Let Hibernate manage timestamps at application level — works identically on both databases.

**Detection:** NOT caught by H2 unit/integration tests. Only discovered via Karate/component tests against live PostgreSQL. H2 handles DEFAULT differently from real PostgreSQL.

**Source:** mca-eps-selfservice-locator pilot — `LocatorEvent.EVENT_TS` INSERT failed on live PostgreSQL.

### Sequence Generator Rules

- `@SequenceGenerator` works identically in PostgreSQL — keep as-is
- Sequence names: keep UPPERCASE (PostgreSQL is case-insensitive for unquoted identifiers)
- `allocationSize` must match the database sequence `INCREMENT BY`
- No schema prefix needed if `currentSchema` is set in JDBC URL

### Native Query Conversions

| Oracle Function/Syntax | PostgreSQL Equivalent |
|---|---|
| `NVL(a, b)` | `COALESCE(a, b)` |
| `NVL2(a, b, c)` | `CASE WHEN a IS NOT NULL THEN b ELSE c END` |
| `DECODE(a, b, c, d)` | `CASE WHEN a = b THEN c ELSE d END` |
| `SYSDATE` | `CURRENT_TIMESTAMP` |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP` |
| `FROM DUAL` | Remove entirely (PostgreSQL allows bare SELECT) |
| `ROWNUM <= n` | `LIMIT n` (move to end of query) |
| `(+)` outer join | Rewrite as `LEFT JOIN` / `RIGHT JOIN` |
| `LISTAGG(col, ',') WITHIN GROUP (ORDER BY ...)` | `STRING_AGG(col, ',' ORDER BY ...)` |
| `seq.NEXTVAL` | `nextval('seq_name')` |
| `seq.CURRVAL` | `currval('seq_name')` |
| `TO_DATE(str, fmt)` | `TO_TIMESTAMP(str, fmt)` |
| `TO_NUMBER(str)` | `CAST(str AS NUMERIC)` |
| `SUBSTR(s, p, l)` | Keep (PostgreSQL supports SUBSTR) or use `SUBSTRING(s FROM p FOR l)` |
| `REGEXP_LIKE(col, pattern)` | `col ~ pattern` |
| `TRUNC(date)` | `DATE_TRUNC('day', date)` |
| `ADD_MONTHS(date, n)` | `date + INTERVAL 'n months'` |
| `MONTHS_BETWEEN(d1, d2)` | `EXTRACT(EPOCH FROM (d1 - d2)) / 2592000` |
| `CONNECT BY ... START WITH ...` | `WITH RECURSIVE cte AS (...)` |

---

## Section 6: Quality Gate Checks Per Phase

| Phase | Gate Command | Pass Condition |
|---|---|---|
| 0 | `git branch --show-current` | Contains JIRA_ID |
| 1 | `./gradlew test` | Exit code captured (soft — pre-existing failures allowed) |
| 2 | `ls .oracle-to-postgres/app-analysis.json` | File exists |
| 3 | `./gradlew compileJava` | Exit 0 |
| 4 | `find src/it -name "PostgresMigrationValidationTest.java"` | File found |
| 5 | `./gradlew test integrationTest` | Exit 0 (or match baseline failures) |
| 6 | `ls .oracle-to-postgres/migration-report.md` | File exists |

---

## Section 7: Iron Rules

1. **Verify every file change** — re-read after editing to confirm correctness
2. **Log every step** — ISO timestamps with [INIT]/[START]/[DONE] markers
3. **Minimal changes only** — only Oracle→Postgres connectivity changes
4. **Preserve existing functionality** — tests must pass post-migration
5. **Never modify database scripts** — only application code and config
6. **Branch naming** — `${JIRA_ID}/oracle-to-postgres-app`
7. **Commit message** — `${JIRA_ID} | Oracle to Postgres app migration by oracle-to-postgres-app-migration plugin`
8. **Always clone fresh** — never work on pre-existing checkout (when using --git-url)
9. **Reports committed in-repo** — `.oracle-to-postgres/` directory
10. **currentSchema is mandatory** — ALWAYS in JDBC URL

---

## Section 8: Decision Rules

| Scenario | Decision | Rule Applied |
|---|---|---|
| columnDefinition has Oracle type, Java type is unambiguous | Remove columnDefinition entirely | Rule 4: Conservative |
| columnDefinition has Oracle type, Java type is ambiguous | Convert to PostgreSQL equivalent | Rule 3: Preserve behavior |
| Sequence name is UPPERCASE | Keep UPPERCASE (PostgreSQL handles unquoted case) | Rule 3: Preserve behavior |
| Native query uses NVL | Convert to COALESCE | Rule 2: Documented pattern |
| Native query uses complex PL/SQL | Flag for manual review, do NOT convert | Rule 1: Safety |
| Property file has `MODE=Oracle` in H2 URL | Change to `MODE=PostgreSQL` | Rule 2: Documented pattern |
| Test SQL uses `NUMBER(10)` | Convert to `BIGINT` | Rule 2: Documented pattern |
| Test SQL uses `VARCHAR2(100)` | Convert to `VARCHAR(100)` | Rule 2: Documented pattern |
| Build file has Oracle driver in `implementation` scope | Replace with PostgreSQL in `runtimeOnly` scope | Rule 4: Conservative |
| Stored procedure call found | LOG and flag for manual review, do NOT modify | Rule 1: Safety |
| Empty string behavior differs (Oracle: '' = NULL) | LOG as known difference, do NOT add workaround | Rule 4: Conservative |

---

## Section 9: Common Pitfalls

### 1. Missing currentSchema Parameter
**Problem:** PostgreSQL defaults to `public` schema. If tables are in a user-specific schema, all queries fail with "relation does not exist" or timeout.
**Fix:** ALWAYS append `?currentSchema={POSTGRES_SCHEMA}` to JDBC URL.

### 2. Oracle Driver Still on Classpath at Runtime
**Problem:** Application config points to PostgreSQL, but the deployed environment has Oracle driver on classpath (from parent POM, shared lib, or container image). HikariCP picks up Oracle driver by class name even if properties say PostgreSQL.
**Fix:** Verify `driverClassName` property is set to `org.postgresql.Driver`. Remove Oracle driver from all dependency scopes.

### 3. Timestamp Format During Data Migration
**Problem:** Oracle `DATE` type stores date+time. When exported in Oracle's default `DD-MON-RR` format and imported to PostgreSQL, 2-digit years are misinterpreted (e.g., `26` becomes year 0026 instead of 2026). Shows as `0001-06-16 BC`.
**Fix:** Export timestamps in ISO format (`YYYY-MM-DD HH24:MI:SS.FF6`). This is a DBA-side issue, not an application issue.

### 4. Sequence PostgreSQL Syntax vs Oracle Syntax
**Problem:** Hibernate with PostgreSQLDialect generates `select nextval('SEQ_NAME')`. If app is accidentally still connected to Oracle, this fails with `ORA-00923: FROM keyword not found`.
**Fix:** Ensure the JDBC connection is actually going to PostgreSQL (check logs for `oracle.jdbc.driver.T4CConnection` — that means Oracle).

### 5. Empty String vs NULL
**Problem:** Oracle treats empty string `''` as NULL. PostgreSQL treats them as different values. Queries with `WHERE col IS NULL` may miss rows that have empty strings.
**Fix:** Only address if tests fail. Do not proactively add workarounds.

### 6. Case Sensitivity in Table/Column Names
**Problem:** Oracle stores unquoted identifiers in UPPERCASE. PostgreSQL stores them in lowercase. If code uses quoted identifiers, case must match exactly.
**Fix:** For Hibernate-managed entities, let Hibernate handle the naming strategy. For native queries, keep as unquoted (PostgreSQL is case-insensitive for unquoted).

### 7. H2 Oracle Mode Remnants
**Problem:** Test configuration using `MODE=Oracle` causes H2 to emulate Oracle behavior. After migration, tests pass but don't validate PostgreSQL compatibility.
**Fix:** Change to `MODE=PostgreSQL` in all test JDBC URLs.

---

## Section 10: Test Configuration Patterns

### H2 PostgreSQL Mode (Default Strategy)

```properties
spring.datasource.hikari.jdbc-url=jdbc:h2:mem:testdb;INIT=RUNSCRIPT FROM 'classpath:schema.sql';NON_KEYWORDS=KEY,VALUE;MODE=PostgreSQL
spring.datasource.hikari.driverClassName=org.h2.Driver
```

### Testcontainers PostgreSQL

```properties
spring.datasource.hikari.jdbc-url=jdbc:tc:postgresql:15:///testdb?TC_REUSABLE=true
spring.datasource.hikari.driverClassName=org.testcontainers.jdbc.ContainerDatabaseDriver
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect
```

### Test SQL Script Conversions

| Oracle SQL | PostgreSQL SQL |
|---|---|
| `VARCHAR2(n)` | `VARCHAR(n)` |
| `NUMBER(p,s)` | `NUMERIC(p,s)` |
| `NUMBER` (no precision) | `BIGINT` |
| `NUMBER(1)` | `BOOLEAN` or `SMALLINT` |
| `SYSTIMESTAMP` | `CURRENT_TIMESTAMP` |
| `SYSDATE` | `CURRENT_TIMESTAMP` |
| `SEQ.NEXTVAL` | `nextval('SEQ')` |
| `CREATE SEQUENCE ... NOCYCLE NOCACHE ORDER` | `CREATE SEQUENCE ... MINVALUE 1 MAXVALUE 2147483647 INCREMENT BY 1 START WITH 1` |
| `TO_DATE('2024-01-01', 'YYYY-MM-DD')` | `TIMESTAMP '2024-01-01 00:00:00'` |

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] All Oracle JDBC driver dependencies removed from build files
- [ ] PostgreSQL driver added with correct scope (`runtimeOnly`)
- [ ] All JDBC URLs updated with `?currentSchema={POSTGRES_SCHEMA}` appended
- [ ] All driver class names changed to `org.postgresql.Driver`
- [ ] All Hibernate dialect references changed to `PostgreSQLDialect`
- [ ] All Oracle-specific `columnDefinition` values removed or converted
- [ ] All native queries converted from Oracle syntax to PostgreSQL syntax
- [ ] All test JDBC URLs changed from `MODE=Oracle` to `MODE=PostgreSQL`
- [ ] All test SQL scripts converted (VARCHAR2→VARCHAR, NUMBER→BIGINT, etc.)
- [ ] Connection pool validation queries changed from `SELECT 1 FROM DUAL` to `SELECT 1`
- [ ] No `import oracle.*` statements remain in Java source files
- [ ] Migration report generated and committed to `.oracle-to-postgres/`

**Pilot-informed checks (from mca-eps-selfservice-locator):**
- [ ] All `@Column(insertable = false)` on `@CreationTimestamp` / `@UpdateTimestamp` fields have had `insertable = false` removed — Oracle relied on DB default; PostgreSQL requires Hibernate to manage the value
- [ ] If Spring Cloud Config Server is used: ALL profile-specific property files flagged in migration report (not just DATASOURCE) for replication to new environment config folder
- [ ] Migration report includes explicit ⚠️ H2 Test Limitations section warning that H2 PostgreSQL mode does NOT catch: schema routing, `insertable=false` timestamp failures, strict constraint enforcement
- [ ] Migration report includes post-deployment verification steps: check logs for PGConnection (not T4CConnection), verify `currentSchema` routing, verify timestamp data format
- [ ] If `spring.profiles.active` or `spring.cloud.config` is detected: all profile property files listed for config server folder replication

---

## Areas for Specialist Extension

This skill covers the BUK baseline for Oracle-to-PostgreSQL application connectivity migration. The following areas need extension by the relevant teams:

- **DBA Team** — Database schema migration rules, stored procedure conversion (PL/SQL → PL/pgSQL), data migration format requirements
- **DevOps Team** — Spring Cloud Config Server folder replication, CI/CD pipeline configuration for PostgreSQL environments
- **QA Team** — Karate/component test patterns for live PostgreSQL validation beyond H2 unit tests
