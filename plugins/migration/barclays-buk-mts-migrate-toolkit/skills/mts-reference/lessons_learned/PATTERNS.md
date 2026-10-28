---
name: mts-lessons-learned-patterns
description: Common failure modes and fixes for MTS discovery, matching, and migration runs
type: reference
---

# MTS Common Patterns & Lessons Learned

## Discovery Patterns

### P-D-01: SERVICE_NAME constant is an enum, not a String literal

**Symptom:** Step 1.4 fails to resolve the SERVICE_NAME — Grep finds it but the value is an enum reference (e.g., `ServiceName.RETRIEVE_CUSTOMER`), not a String literal.

**Fix:** Read the enum class to resolve the String value. Search for `public String getServiceName()` or check the enum's field value directly.

---

### P-D-02: doService call is wrapped in a utility method

**Symptom:** Step 1.3 finds no direct `doService(` calls but the service clearly uses the EBS gateway.

**Fix:** Search for `doService` in the EBS JAR utility class (usually `AbstractEBSGateway` or similar). Grep for `doService` in the full Gradle cache, not just the project source.

---

### P-D-03: Gradle cache is populated but source JARs are zero

**Symptom:** `GRADLE_CACHE_STATUS=POPULATED` but `SOURCE_JARS_FOUND=0`. The cache has `.jar` files but no `-sources.jar` files.

**Fix:** This is a compiled-JAR-only situation. Set `COMPILED_JAR_FALLBACK` appropriately and proceed with Steps 1.10-1.15 using compiled JAR extraction (constant pool or javap).

---

### P-D-04: Transport classification is ambiguous for hybrid services

**Symptom:** Service uses both EBS doService AND a direct database call. Classification algorithm gives ambiguous result.

**Fix:** Apply the hybrid rule: if both `doService` AND `jdbc` / `JdbcTemplate` / `NamedParameterJdbcTemplate` are present in the same service implementation class, classify as `tcv-hybrid`. See `hybrid_service_patterns.md`.

---

## API Matching Patterns

### P-M-01: High TDL overlap but low score — score calculation error

**Symptom:** The match report shows 4/5 TDL columns matched but the overall score is below 0.5.

**Fix:** Re-read `api-match-scoring.md` carefully. The scoring is weighted — TDL column match is only one dimension. Check if request field mapping is scoring 0 due to missing query parameters.

---

### P-M-02: Backstage catalogue returns no candidates

**Symptom:** Layer 1 search returns 0 results even for well-known services.

**Fix:** Check if `backstage_clone.py` ran successfully. If clone failed, the static fallback in `backstage_catalogue_index.md` is used — but this file may be stale. Run `/refresh-ods-catalogue` to update it, then retry.

---

### P-M-03: API candidate appears in Confluence but not in Backstage

**Symptom:** You know the replacement API exists but Layer 1 returns nothing.

**Fix:** The Backstage catalogue indexes `catalog-info.yaml` files. If the API hasn't been registered in Backstage yet, it won't appear. Fall back to Layers 2-4 (Confluence). Record the gap for the team.

---

## Migration Patterns

### P-C-01: Strategy C — feature flag class not found

**Symptom:** `FeatureFlag.java` does not exist or does not follow the expected enum pattern.

**Fix:** Search for other flag-like classes (`Flags.java`, `FeatureToggle.java`, `AppConfig.java` with boolean methods). If none found, document in issues as a bean gap and leave injection as a TODO comment in generated code.

---

### P-C-02: mts-compat converter generates incorrect Boolean field

**Symptom:** Generated converter uses `Boolean.parseBoolean(dto.getSomeField())` where `getSomeField()` returns a `char` or `Character`.

**Fix:** This is a known bug documented in `mts-migrate-code-agent`. Use `'Y' == dto.getSomeField()` or `"Y".equals(String.valueOf(dto.getSomeField()))` instead.

---

### P-C-03: compileJava fails due to missing ODS client dependency

**Symptom:** After code generation, `compileJava` fails with `cannot find symbol: class OdsXxxClient`.

**Fix:** The ODS API dependency is missing from `build.gradle`. Add the appropriate SDK3 dependency. Check the match report's winning API name to determine the correct artifact coordinates from the ODS API catalogue.
