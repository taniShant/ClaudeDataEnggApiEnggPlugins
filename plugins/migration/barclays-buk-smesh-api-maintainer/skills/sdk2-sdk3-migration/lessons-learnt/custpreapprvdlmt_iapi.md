# Lessons Learned — custpreapprvdlmt-iapi

**Project:** custpreapprvdlmt-iapi (Customer Pre-Approved Limits)
**SDK Migration:** SDK2 → SDK3 (Java 8 → Java 21, Spring Boot 2.x → 3.x)

---

## Lesson 1: Legacy GroupId Variants Not Caught by Specific-Prefix Sweep

### Problem

This project declared `api-core-data` and `api-core-cache` using the legacy groupId `com.barclays.buk.imcc.buk` — an older variant that predates `com.barclays.iapi.core`. The Phase 1 residual check was scanning for a fixed list of known old groupIds and missed this variant entirely.

```gradle
// As found in build.gradle (OLD — will break on Java 21):
implementation 'com.barclays.buk.imcc.buk:api-core-data:1.0.010'
implementation 'com.barclays.buk.imcc.buk:api-core-cache:1.0.006'

// Correct SDK3 coordinates:
implementation 'com.barclays.api.emm.common.core:api-core-data:1.1.003'
implementation 'com.barclays.api.emm.common.core:api-core-cache:2.1.005'
```

### Fix

Step 10.2b now uses the `emm` rule instead of a fixed-prefix list:
- **SDK3-compatible:** groupId contains `emm` OR is `bap.bld.lib`
- **Legacy (requires migration):** any `com.barclays.*` / `com.barclaycard.*` groupId that does NOT contain `emm` or `bap.bld.lib`

This catches any old groupId variant regardless of the specific prefix used.

---

## Lesson 2: Transitive SDK2 Libraries Not Caught by grep

### Problem

`api-referencedata-connector:1.0.022` (SDK2 version) was pulled in transitively through `api-customer-transactions:1.0.127`. The declared dependency scan only grepped `build.gradle` — it never ran `./gradlew dependencies` — so the transitive old-version library was invisible until test runtime failures revealed it as `ClassNotFoundException`.

### Fix

Step 10.2b now runs `./gradlew dependencies --configuration runtimeClasspath` and `testRuntimeClasspath` as Pass 2, and greps the output for all known old-groupId patterns.

---

## Lesson 3: Undocumented Project-Specific Library

### Problem

`com.barclays.iapi.core:api-customer-transactions:1.0.127` is a project-specific Barclays library not listed in any reference table. Because it wasn't in the tables, the residual check skipped it with "no action needed". The library was pulling in SDK2-version transitive dependencies.

### Fix

Step 10.2b now has a Pass 4 for undocumented Barclays libraries: any `com.barclays.*` / `com.barclaycard.*` dep not matched in Passes 1-3 must be Nexus-searched for an SDK3-compatible version.

---

## Lesson 4: api-mainframe-connector Breaking API Change (1.1.x → 1.5.x)

### Problem

The migration from `api-mainframe-connector:1.1.007` to `1.5.004` introduced a generics + varargs breaking change to the `execute()` method:

```java
// SDK2 (1.1.007):
MainframeResponse execute(MainframeTransaction tx)

// SDK3 (1.5.004):
<T> T execute(MainframeTransaction<T> tx, String... options)
```

Mockito test stubs written against the old signature failed with `NoSuchMethodError` at runtime:
```java
// BROKEN — old signature no longer exists:
when(client.execute(any(CustomerLimitsRetrieveTransaction.class))).thenReturn(response);

// FIXED — matches new generic + varargs signature:
when(client.execute(any(CustomerLimitsRetrieveTransaction.class))).thenReturn(response);
// OR (if varargs matters):
when(client.execute(any(CustomerLimitsRetrieveTransaction.class), any(String[].class))).thenReturn(response);
```

### Fix

When migrating `api-mainframe-connector` from any `1.x` version to `1.5.+`:
- Search for all test mocks of `MainframeClient.execute()` or similar
- Update mock signatures to match the generic form
- This should be handled in Phase 4 (JUnit migration) or Phase 5 (test fixing)

---

## Summary Table

| Library | Old Coords | New Coords | Issue Type |
|---------|-----------|-----------|------------|
| api-core-data | `com.barclays.buk.imcc.buk:api-core-data:1.0.010` | `com.barclays.api.emm.common.core:api-core-data:1.1.003` | Legacy groupId variant |
| api-core-cache | `com.barclays.buk.imcc.buk:api-core-cache:1.0.006` | `com.barclays.api.emm.common.core:api-core-cache:2.1.005` | Legacy groupId variant |
| api-referencedata-connector | `com.barclays.iapi.core:api-referencedata-connector:1.0.022` (transitive) | `com.barclays.api.emm.common.core:api-referencedata-connector:1.2.010` | Transitive SDK2 library |
| api-customer-transactions | `com.barclays.iapi.core:api-customer-transactions:1.0.127` | Search Nexus for SDK3 version | Undocumented project-specific library |
| api-mainframe-connector | `com.barclays.iapi.core:api-mainframe-connector:1.1.007` | `com.barclays.api.emm.common.core:api-mainframe-connector:1.5.004` | Breaking API change in 1.5.x |
