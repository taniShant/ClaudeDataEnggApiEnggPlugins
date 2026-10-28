# H2 Test Database Configuration Reference

> **Purpose:** Patterns for detecting datasource failures and configuring H2 fallback in integration tests.
> **Used by:** integration-test-agent (Step 0.5), command orchestrator (Phase 5 datasource detection)

---

## 1. Datasource Failure Detection Patterns

Search test output for these patterns to detect database connectivity issues:

| Pattern | Indicates |
|---------|-----------|
| `Connection refused` | Database server unreachable |
| `Communications link failure` | Network/firewall issue |
| `database.*does not exist` | Missing database |
| `Could not connect` | Generic connection failure |
| `Unable to obtain JDBC Connection` | Connection pool exhaustion or DNS |
| `ORA-01017: invalid username/password` | Oracle auth failure |
| `FATAL: password authentication failed` | PostgreSQL auth failure |

---

## 2. PostgreSQL Feature Check (Pre-H2)

Before configuring H2, check if the project uses PostgreSQL-specific features H2 cannot emulate:

| Feature | Detection Pattern | H2 Compatible? |
|---------|-------------------|----------------|
| JSONB columns | `jsonb` in SQL/entity files | No |
| Array columns | `text[]`, `integer[]` in SQL | No |
| PG functions | `unnest`, `array_agg`, `string_agg`, `jsonb_*` | No |
| PG dialect | `PostgreSQLDialect` in config | Partial (use `MODE=PostgreSQL`) |
| Custom types | `CREATE TYPE` in SQL | No |

**If PG-specific features found:** Report and require manual database setup.
**If no PG-specific features:** Auto-configure H2 (see Section 3).

---

## 3. H2 Fallback Configuration Template

### 3.1 Test Properties

Create or update `src/integrationTest/resources/application-test.properties`:

```properties
spring.datasource.url=jdbc:h2:mem:testdb;MODE=PostgreSQL;DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop
```

### 3.2 H2 Dependency

Add to `build.gradle` if missing:

```groovy
testImplementation "com.h2database:h2"
```

H2 is BOM-managed — do NOT specify a version.

### 3.3 Test Class Annotations

Ensure test classes have `@ActiveProfiles("test")` to pick up the properties.

---

## 4. @AutoConfigureTestDatabase Usage Rules

**Use `@AutoConfigureTestDatabase(replace = Replace.ANY)` ONLY as a last resort.**

Decision tree:
1. First: Configure H2 via `application-test.properties` + `@ActiveProfiles("test")`
2. Verify the datasource error is gone
3. ONLY if step 1 fails: Add `@AutoConfigureTestDatabase(replace = Replace.ANY)` to the SPECIFIC failing test class

**Why last resort:** `@AutoConfigureTestDatabase` overrides at the class level, hiding configuration issues that would fail in CI. Properties-based configuration is transparent and auditable.

---

## 5. @MockitoBean Datasource Impact

With `@MockitoBean` (Spring Boot 3.4+), Spring attempts to create the real datasource BEFORE the mock override takes effect. This means:

| Scenario | `@MockBean` (old) | `@MockitoBean` (new) |
|----------|-------------------|---------------------|
| Datasource-dependent bean mocked | Spring skips real bean | Spring tries real datasource FIRST |
| No database available | Tests pass | Tests fail with connection error |

**Fix:** Configure H2 fallback BEFORE migrating `@MockBean` → `@MockitoBean`.

---

## 6. H2 Oracle Compatibility Mode

For APIs that use Oracle as their production database, H2 must be configured in Oracle compatibility mode.

### 6.1 Oracle Mode URL

```properties
# src/integrationTest/resources/application-test.properties
spring.datasource.url=jdbc:h2:mem:testdb;MODE=Oracle;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=create-drop
```

Key parameters:
- `MODE=Oracle` — enables Oracle SQL dialect emulation
- `DB_CLOSE_DELAY=-1` — keeps the in-memory database open for the duration of the JVM
- `DB_CLOSE_ON_EXIT=FALSE` — prevents H2 from closing the database on JVM shutdown (prevents test isolation issues)

### 6.2 Known Limitations of H2 Oracle Mode

H2 Oracle mode is **not a complete Oracle substitute**. Some Oracle-specific features are not emulated:

| Feature | H2 Oracle Mode Support |
|---|---|
| Standard SQL queries | ✅ Mostly works |
| Oracle functions (`NVL`, `DECODE`) | ✅ Supported |
| Sequences | ✅ Supported |
| `ROWNUM` | ✅ Supported |
| Wildcard SQL with `%` and `_` | ⚠ May behave differently |
| Oracle-specific data types | ❌ Not supported |
| Stored procedures | ❌ Not supported |
| Partitioned tables | ❌ Not supported |

**Recommendation**: Use H2 Oracle mode only for basic unit/integration tests. For accurate Oracle compatibility testing, use Testcontainers with a real Oracle image.

### 6.3 Wildcard Query Issue

Wildcard SQL queries (e.g., `LIKE '%value%'`) may not always work correctly with H2 in Oracle mode due to case-sensitivity differences.

**Fix**: Add `IGNORECASE=TRUE` if case-insensitive matching is required:
```properties
spring.datasource.url=jdbc:h2:mem:testdb;MODE=Oracle;DB_CLOSE_DELAY=-1;DB_CLOSE_ON_EXIT=FALSE;IGNORECASE=TRUE
```

---

**Document Version:** 1.1
**Last Updated:** 2026-10-22
**New in 1.1:** Added Section 6 — H2 Oracle Compatibility Mode
