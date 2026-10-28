# Lessons Learned - Cards API Project (Comprehensive)

> **Note:** This document provides detailed, comprehensive coverage of SDK3 migration issues.
> See also: [SKILL.md](../SKILL.md) for the main migration guide.

## Related Documentation

| Topic | Document | Notes |
|-------|----------|-------|
| Response vs RestResponse | [accountentries_iapi.md](accountentries_iapi.md#3-️-response-vs-restresponse---know-the-difference-canonical-reference) | **Canonical reference** for Response/RestResponse patterns |
| Quick Reference Cards | [quick_reference.md](quick_reference.md) | Condensed problem/solution format |
| Resilience4j Patterns | [resilience4j.md](resilience4j.md) | Circuit breaker, bulkhead, time limiter |

### Card Mapping (This File → Quick Reference)

| This File | Quick Reference | Topic |
|-----------|-----------------|-------|
| Card 7 | Card 7 | Bootstrap/common-filter (expanded) |
| Card 8 | Card 8 | Jakarta EE/javax.validation (expanded) |
| Card 9 | Card 9 | CycloneDX BOM (expanded) |
| Card 10 | Card 12 | Karate/JUnit 5 (expanded) |
| Card 11 | Card 10-11 | SDK2 class exclusion (expanded) |

## Project Context

**Project:** process-qry-statement-v1-springboard2 (Cards API)
**SDK Migration:** SDK2 → SDK3 (Java 8 → Java 21, Spring Boot 2.7.18 → 3.5.7)
**Date:** December 2025
**Total Cards:** 11 (covering Log4j, Spring Framework, Tomcat, Netty, Jakarta EE, Karate, and more)

---

## Card 1: SLF4J Logger Bridge Conflict

### Issue
Multiple SLF4J bridges on classpath causing conflicts:
- **Old bridge**: `log4j-slf4j-impl` (for SLF4J 1.x)
- **New bridge**: `log4j-slf4j2-impl` (for SLF4J 2.x)
- Spring Boot 3.x uses SLF4J 2.x exclusively

### Problem
```gradle
// ❌ WRONG - Both bridges present causes conflicts
dependencies {
    implementation 'org.apache.logging.log4j:log4j-slf4j-impl'  // SLF4J 1.x bridge
    implementation 'org.apache.logging.log4j:log4j-slf4j2-impl' // SLF4J 2.x bridge
}
```

**Error Symptoms:**
```
Multiple SLF4J bindings detected on classpath
ClassNotFoundException: org.slf4j.impl.StaticLoggerBinder
or
NoSuchMethodError in logger initialization
```

### Solution
```gradle
// ✅ CORRECT - Exclude old SLF4J 1.x bridge, use only SLF4J 2.x bridge
configurations {
    all*.exclude module: 'log4j-slf4j-impl'  // Exclude legacy SLF4J 1.x bridge
}

dependencies {
    // SLF4J 2.x bridge for Log4j2 (replaces old log4j-slf4j-impl)
    implementation 'org.apache.logging.log4j:log4j-slf4j2-impl:2.23.1'
}
```

### Detection
Search for conflicting bridges:
```bash
./gradlew dependencies | grep -i "slf4j"
```

If you see both `log4j-slf4j-impl` and `log4j-slf4j2-impl`, you have a conflict.

**Why This Matters:**
- SLF4J 1.x and 2.x are incompatible on the same classpath
- Spring Boot 3.x requires SLF4J 2.x exclusively
- Multiple bindings cause runtime failures and unexpected logging behavior

**Reference:**
- Spring Boot 3.x migration: [Logging Changes](https://spring.io/blog/2023/01/31/spring-boot-3-migration-guide)
- SLF4J 2.x documentation: [Upgrade Guide](https://www.slf4j.org/docs.html)

---

## Card 2: Spring Boot Logger Starter Exclusion

### Issue
Spring Boot 3.x auto-configures logging dependencies that may conflict with custom Log4j setup.

### Problem
```gradle
// ❌ WRONG - Allows conflicting logging auto-configuration
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
    // spring-boot-starter-logging pulled in automatically
}
```

**Error Symptoms:**
```
Multiple loggers attempting to initialize
Unexpected Logback/SLF4J bindings
Logger configuration not being applied
```

### Solution
```gradle
// ✅ CORRECT - Exclude Spring Boot logging starter
configurations {
    all*.exclude module: 'spring-boot-starter-logging'
    all*.exclude module: 'logback-classic'  // Logback is the default in Spring Boot
    all*.exclude module: 'slf4j-simple'
}

dependencies {
    // Spring Boot starter without logging
    implementation('org.springframework.boot:spring-boot-starter-web')
    // Our explicit Log4j2 setup takes precedence
    implementation 'org.apache.logging.log4j:log4j-slf4j2-impl:2.23.1'
}
```

### Detection
Check what logging dependencies are being pulled in:
```bash
./gradlew dependencies --configuration runtimeClasspath | grep -E "(logback|slf4j|log4j)"
```

Look for:
- `spring-boot-starter-logging`
- `logback-classic`
- `slf4j-simple`
- `log4j-slf4j-impl` (legacy)

### Why This Matters:
- Spring Boot defaults to Logback + SLF4J 1.x in legacy versions
- This conflicts with explicit Log4j2 configuration
- Excluding ensures your Log4j2 setup is the only logger on classpath

**Reference:**
- Spring Boot Logging: [Spring Boot Docs](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.logging)

---

## Card 3: Log4j2 Version Pinning for Security

### Issue
Log4j2 security vulnerabilities (CVE-2021-44228) require specific versions.

### Problem
```gradle
// ❌ WRONG - Version floating, vulnerable
dependencies {
    implementation 'org.apache.logging.log4j:log4j'  // No version specified
}
```

**Error Symptoms:**
```
Security scan failures
Vulnerability: CVE-2025-24813 detected (if using old Log4j)
```

### Solution
```gradle
// ✅ CORRECT - Pin Log4j2 version with security fixes
ext['log4j2.version']='2.23.1'  // Pinned safe version with BUKMULE-2254 fix

configurations {
    // Ensures all Log4j2 modules use the same version
}

dependencies {
    // Explicit Log4j2 core (version inherited from ext)
    implementation 'org.apache.logging.log4j:log4j:2.23.1'

    // ECS JSON layout for structured logging
    implementation 'org.apache.logging.log4j:log4j-layout-template-json'

    // SLF4J bridge with explicit version
    implementation 'org.apache.logging.log4j:log4j-slf4j2-impl:2.23.1'
}
```

### Details
The project documents this fix for:
- **BUKMULE-2254**: Primary Log4j2 vulnerability remediation
- **BUKMULE-2775**: Fix for logging not working in co-app, co-perf, co-ercime files

### Why This Matters:
- Log4j2 versions before 2.17.0 are vulnerable to RCE exploits
- Version 2.23.1 includes all critical security patches
- Pinned versions prevent transitive dependency issues

**Current Version Used:**
```
log4j2.version = 2.23.1  // CVE-2025-24813 remediation
```

**References:**
- Apache Log4j2 Security: [Apache Security](https://logging.apache.org/log4j/2.x/security.html)
- CVSS Score: Log4j2 RCE exploits are CVSS 10.0 (maximum severity)

---

## Card 4: Spring Framework Version Compatibility

### Issue
Spring Framework 6.x (in Spring Boot 3.5.7) has different dependency requirements than Spring 5.x.

### Problem
```gradle
// ❌ WRONG - Spring 5.x version with Spring Boot 3.x
ext['spring-framework.version'] = '5.3.34'  // Incompatible with Boot 3.x
```

**Error Symbols:**
```
NoClassDefFoundError: org/springframework/web/...
Incompatible method signature errors
Spring Boot 3.x requires Spring 6.x
```

### Solution
```gradle
// ✅ CORRECT - Spring Framework 6.x for Spring Boot 3.x
ext['spring-framework.version'] = '6.2.11'

dependencies {
    // Let Spring Boot 3.5.7 BOM manage spring-web version
    // It will resolve to Spring 6.2.11 automatically

    // Removed override: spring-web:5.3.34
    // Reason: Incompatible with Spring Boot 3.5.7 which requires Spring 6.x
}
```

### Migration Details
| Component | SDK2 (Boot 2.x) | SDK3 (Boot 3.x) |
|-----------|-----------------|-----------------|
| **Spring Boot** | 2.7.18 | 3.5.7 |
| **Spring Framework** | 5.3.34 | 6.2.11 |
| **Java** | 8 | 21 |
| **SLF4J** | 1.x | 2.x |

### Why This Matters:
- Spring 6.x introduces package name changes (`javax` → `jakarta`)
- API method signatures differ between Spring 5.x and 6.x
- Spring Boot 3.x enforces Spring 6.x requirements
- Mismatched versions cause mysterious ClassNotFound errors

### Build Configuration Comment
From `build.gradle`:
```gradle
// Removed: spring-web:5.3.34 override - incompatible with Spring Boot 3.5.7 which requires Spring 6.x
// Let Spring Boot 3.5.7 BOM manage spring-web version (6.2.11)
```

**Reference:**
- Spring 6 Migration: [Spring Framework 6 Migration Guide](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)

---

## Card 5: Tomcat Version Pinning for CVE Remediation

### Issue
Embedded Tomcat versions in Spring Boot may contain security vulnerabilities.

### Problem
```gradle
// ❌ WRONG - Allows Spring Boot default version (may be vulnerable)
dependencies {
    implementation 'org.springframework.boot:spring-boot-starter-web'
}
```

**Security Issue:**
```
CVE-2025-24813 detected in default Tomcat version
```

### Solution
```gradle
// ✅ CORRECT - Pin Tomcat to patched version
ext['tomcat.version'] = '10.1.44'

dependencies {
    // Explicitly pin to CVE-fixed version
    implementation('org.apache.tomcat.embed:tomcat-embed-core') {
        version { strictly '10.1.44' }
    }
    implementation('org.apache.tomcat.embed:tomcat-embed-el') {
        version { strictly '10.1.44' }
    }
    implementation('org.apache.tomcat.embed:tomcat-embed-websocket') {
        version { strictly '10.1.44' }
    }
    implementation('org.apache.tomcat:tomcat-annotations-api') {
        version { strictly '10.1.44' }
    }
}
```

### Why This Matters:
- Embedded Tomcat is included in every Spring Boot web application
- Vulnerabilities in Tomcat affect all dependent services
- CVE-2025-24813 is a critical vulnerability in servlet processing
- Version 10.1.44 is the minimum safe version for Spring Boot 3.5.7

### Gradle `strictly` Version Constraint
The `strictly` constraint ensures:
```gradle
version { strictly '10.1.44' }  // Forces exact version, no higher
```

This is stronger than `implementation 'x:y:10.1.44'` because it prevents transitive dependencies from pulling in higher (potentially vulnerable) versions.

**Reference:**
- Apache Tomcat Security: [Tomcat Security Documentation](https://tomcat.apache.org/security.html)
- CVE-2025-24813: Tomcat servlet processing vulnerability

---

## Card 6: Netty Version Management

### Issue
Netty is used for non-blocking I/O and has its own security considerations.

### Problem
```gradle
// ❌ WRONG - Netty version floating
dependencies {
    // Netty pulled in transitively with unknown version
}
```

### Solution
```gradle
// ✅ CORRECT - Pin Netty version
ext['netty.version'] = '4.1.125.Final'

dependencies {
    // All Netty modules will use 4.1.125.Final
}
```

### Why This Matters:
- Netty is used by Spring WebFlux and async HTTP clients
- Version mismatches can cause connection pooling issues
- Security patches are released regularly
- Pinned version ensures consistency across all Netty modules

**Current Version:**
```
netty.version = 4.1.125.Final  // Latest stable with security patches
```

---

## Card 7: SDK2/SDK3 Bootstrap Configuration Conflict

### Issue
During SDK3 migration, Spring Boot attempts to load old SDK2 bootstrap classes (`DefaultFilterBootstrap`) that are excluded from the classpath, causing startup failures.

### Problem
```
org.springframework.beans.factory.BeanDefinitionStoreException: I/O failure while processing
configuration class [com.barclaycard.digital.filter.bootstrap.DefaultFilterBootstrap]

Exception encountered during context initialization - cancelling refresh attempt
```

**Root Causes:**
1. Configuration classes with SDK2 imports remain in the codebase
2. `api-core-boot` (SDK2) is excluded in `build.gradle` (line 42)
3. Spring classpath scanning discovers SDK2 bootstrap auto-configuration candidates
4. Spring tries to load classes that don't exist on the classpath

**Affected File:**
```
src/main/java/com/barclays/api/statement/config/InternalApiInitializerConfig.java
```

### Solution

**Primary Fix: Upgrade `common-filter` to 5.0.3** (SDK3-compatible version) ⭐ **RECOMMENDED**

The root cause is that `common-filter:4.1.0` is an SDK2 library that contains `DefaultFilterBootstrap` extending SDK2's `InternalApiInitializer` classes. When `api-core-boot` is excluded from the classpath (line 42 in build.gradle), Spring's component scanning discovers `DefaultFilterBootstrap` but cannot load its parent SDK2 classes, resulting in `BeanDefinitionStoreException`.

**Solution: Upgrade to `common-filter:5.0.3` (SDK3-compatible)**

```gradle
// build.gradle
// ❌ WRONG - SDK2 version (causes BeanDefinitionStoreException)
implementation 'com.barclaycard.digital:common-filter:4.1.0'

// ✅ CORRECT - SDK3 compatible version
implementation 'com.barclaycard.digital:common-filter:5.0.3'
```

**Why this fix works:**
- `common-filter:5.0.3` contains `DefaultFilterBootstrap` that extends SDK3 classes (from `com.barclays.api.bap.bld.lib`)
- These parent classes ARE available on the classpath (not excluded)
- Spring can successfully load and initialize the bootstrap configuration
- Application starts without `BeanDefinitionStoreException`

**Commit Reference:**
```
CARDOPSAPI-12483 | Address Card 7: Upgrade common-filter to 5.0.3 (SDK3-compatible)
- Upgrade common-filter from 4.1.0 (SDK2) to 5.0.3 (SDK3)
- Prevents BeanDefinitionStoreException at runtime during application startup
- Verified: BUILD SUCCESSFUL, app.jar generated successfully
```

**Secondary Fix: Custom Component Scan Filter** (if using older common-filter versions)

If you cannot immediately upgrade common-filter, add a custom TypeFilter to exclude SDK2 bootstrap classes:

```java
// Application.java
@SpringBootApplication
@ComponentScan(
    basePackages = {"com.barclays.api", "com.barclaycard.digital"},
    excludeFilters = @ComponentScan.Filter(
        type = FilterType.CUSTOM,
        classes = DefaultFilterBootstrapExcludeFilter.class))
public class Application { ... }

// Custom filter class
class DefaultFilterBootstrapExcludeFilter implements org.springframework.core.type.filter.TypeFilter {
  private static final java.util.Set<String> EXCLUDED_BOOTSTRAP_CLASSES =
      java.util.Set.of(
          "com.barclaycard.digital.filter.bootstrap.DefaultFilterBootstrap",
          "com.barclaycard.digital.filter.bootstrap.SecureFieldsBootstrap");

  @Override
  public boolean match(
      org.springframework.core.type.classreading.MetadataReader metadataReader,
      org.springframework.core.type.classreading.MetadataReaderFactory metadataReaderFactory) {
    return EXCLUDED_BOOTSTRAP_CLASSES.contains(
        metadataReader.getClassMetadata().getClassName());
  }
}
```

### Migration Context

| Aspect | SDK2 | SDK3 |
|--------|------|------|
| **Bootstrap** | Manual bean registration | Auto-configuration via `bap-bld-lib-plugin` |
| **Init Class** | `api-core-boot` dependency | `com.barclays.api.bap.bld.lib.restapi.bootstrap` |
| **Configuration** | Explicit `@Configuration` beans | Plugin-managed auto-config |
| **Classpath** | `api-core-boot` included | `api-core-boot` excluded (line 42 in build.gradle) |

### Why This Matters:

**The Classpath Conflict Mechanism:**
- `api-core-boot` is excluded in build.gradle line 42 (intentional for SDK3 enforcement)
- `common-filter:4.1.0` contains `DefaultFilterBootstrap` class (registered as auto-configuration candidate)
- Spring's classpath scanning discovers this class at startup and tries to load it
- `DefaultFilterBootstrap` extends SDK2 classes from `api-core-boot` (which are NOT on classpath)
- Result: `BeanDefinitionStoreException` - parent classes cannot be found
- **This error occurs ONLY at runtime**, not during compilation (both libraries compile fine)

**Why common-filter:5.0.3 Fixes It:**
- `common-filter:5.0.3` contains the SAME `DefaultFilterBootstrap` class name
- BUT it extends SDK3 classes from `com.barclays.api.bap.bld.lib` (which ARE on classpath)
- Spring successfully loads and initializes the bootstrap class
- Application starts without errors

**Key Insights:**
- **SDK2 vs SDK3 library compatibility**: `common-filter:4.1.0` extends SDK2 classes that are excluded from the classpath
- **Compile-time vs Runtime mismatch**: Both `common-filter` versions compile fine, but only 5.0.3 works at runtime
- **Library versioning critical**: Library versions must match the framework version (SDK2 libs with SDK2 framework, SDK3 libs with SDK3 framework)
- **Transitive dependencies**: Updating one library can cascade fixes through the entire dependency tree
- **Component scanning is exhaustive**: Spring scans ALL classpath resources, discovering both compatible and incompatible candidates

### common-filter Versions Matrix

| Version | SDK2/SDK3 | Status | Bootstrap Classes | Parent Classes |
|---------|-----------|--------|-------------------|----------------|
| 4.1.0 | SDK2 | ❌ Incompatible | DefaultFilterBootstrap, SecureFieldsBootstrap | com.barclays.api.core.boot (SDK2) |
| 5.0.3 | SDK3 | ✅ Compatible | DefaultFilterBootstrap, SecureFieldsBootstrap | com.barclays.api.bap.bld.lib (SDK3) |

### Build Configuration Impact

From `build.gradle` line 42:
```gradle
//SDK3: Exclude SDK2 artifacts
all*.exclude module: 'api-core-boot'
```

This exclusion is intentional and correct—it enforces SDK3 usage. The problem was that leftover SDK2 configuration classes weren't removed during migration.

### Detection

**Symptom: BeanDefinitionStoreException on startup**
```bash
# Look for Spring startup error mentioning DefaultFilterBootstrap
java -jar ./build/libs/app.jar 2>&1 | grep "BeanDefinitionStoreException\|DefaultFilterBootstrap"

# Expected ERROR output:
# org.springframework.beans.factory.BeanDefinitionStoreException: I/O failure while processing
# configuration class [com.barclaycard.digital.filter.bootstrap.DefaultFilterBootstrap]
```

**Check Current common-filter Version:**
```bash
# Check if you have SDK2 version (4.1.0) or SDK3 version (5.0.3)
grep "common-filter:" build.gradle

# Verify on classpath
./gradlew dependencies --configuration runtimeClasspath | grep "common-filter"

# Expected OUTPUT for SDK3:
# +--- com.barclaycard.digital:common-filter:5.0.3
```

**Verify No SDK2 Bootstrap Imports:**
```bash
# Verify no @Configuration classes import SDK2 bootstrap
grep -r "api.bap.bld.lib.restapi.bootstrap.InternalApiInitializer" src/main/
grep -r "api.core.boot" src/main/

# Should return: NO RESULTS (if migration is complete)
```

### Verification After Fix

**Step 1: Verify Correct Version in build.gradle**
```bash
grep "common-filter:" build.gradle

# Expected output:
# implementation 'com.barclaycard.digital:common-filter:5.0.3'
```

**Step 2: Rebuild and Verify No Errors**
```bash
# Clean rebuild
./gradlew clean compileJava
# Expected: BUILD SUCCESSFUL

# Build JAR
./gradlew bootJar
# Expected: BUILD SUCCESSFUL, app.jar generated

# Check classpath has correct version
./gradlew dependencies --configuration runtimeClasspath | grep "common-filter"
# Expected: +--- com.barclaycard.digital:common-filter:5.0.3
```

**Step 3: Successful Application Startup**
```bash
java -jar ./build/libs/app.jar

# Expected log output (NO BeanDefinitionStoreException):
# 2025-01-05T12:24:10.605+05:30  INFO ... No active profile set, falling back to 1 default profile
# 2025-01-05T12:24:12.575+05:30  INFO ... Started Application in X seconds
# (No errors mentioning DefaultFilterBootstrap, BeanDefinitionStoreException, or parent class loading failures)
```

**Step 4: Verify No Bootstrap Errors in Logs**
```bash
# Check logs for any bootstrap-related errors
java -jar ./build/libs/app.jar 2>&1 | grep -E "DefaultFilterBootstrap|BeanDefinitionStoreException|ClassNotFoundException|parent|extends"

# Expected output: EMPTY (no errors)
```

### Reference
- **SDK2 to SDK3 Migration Guide**: See project CLAUDE.md
- **Barclays bap-bld-lib-plugin**: Auto-configuration via Maven plugin discovery
- **Spring Boot Auto-Configuration**: [Spring Boot Reference](https://docs.spring.io/spring-boot/docs/current/reference/html/features.html#features.developing-auto-configuration)

---

## Card 8: Spring Web SDK2 Version Conflict and Jakarta EE Migration

### Issue
During SDK3 migration, explicit SDK2 Spring Framework 5.x (javax.servlet) dependencies conflict with SDK3's Jakarta EE (jakarta.servlet) namespace, causing ClassNotFoundException at runtime despite successful compilation.

### Problem
```gradle
// ❌ WRONG - Explicit SDK2 Spring Framework 5.x
implementation 'org.springframework:spring-web:5.3.34'
implementation 'org.hibernate.validator:hibernate-validator:6.2.2.Final'
```

**Error Symptoms:**
```
java.lang.NoClassDefFoundError: javax/servlet/ServletRequest
at runtime (despite BUILD SUCCESSFUL)
or
ClassNotFoundException in servlet initialization
or
Incompatible javax.servlet and jakarta.servlet namespaces
```

### Root Causes

1. **Explicit SDK2 Dependency Override**: Spring Framework 5.x uses `javax.servlet` package
2. **SDK3 BOM Provides Spring 6.x**: Spring Framework 6.2.11 uses `jakarta.servlet` package
3. **Transitive Classpath Conflict**: Both old (javax) and new (jakarta) servlet packages present simultaneously
4. **Compiler vs Runtime Mismatch**: Compilation succeeds because Spring Framework is available; runtime fails due to namespace conflict
5. **Hibernate Validator Issue**: Version 6.2.2.Final depends on javax.validation, incompatible with Jakarta

### Migration Context

| Component | SDK2 | SDK3 |
|-----------|------|------|
| **Spring Framework** | 5.3.34 (javax.servlet) | 6.2.11 (jakarta.servlet) |
| **Java EE** | javax.* packages | Jakarta EE (jakarta.*) |
| **Validation API** | javax.validation | jakarta.validation |
| **Servlet API** | javax.servlet | jakarta.servlet |

### Solution

**Step 1: Remove Explicit Spring Web Override**
```gradle
// ❌ WRONG - Remove this line
implementation 'org.springframework:spring-web:5.3.34'

// ✅ CORRECT - Let SDK3 BOM provide Spring Framework 6.2.11
// (No explicit spring-web needed)
```

**Step 2: Update Hibernate Validator**
```gradle
// ❌ WRONG - SDK2 version with javax.validation
implementation 'org.hibernate.validator:hibernate-validator:6.2.2.Final'

// ✅ CORRECT - Let SDK3 BOM manage version, add Jakarta API
implementation 'org.hibernate.validator:hibernate-validator'
implementation 'jakarta.validation:jakarta.validation-api'
```

**Step 3: Complete Corrected Dependencies Section**
```gradle
// ✅ CORRECT - SDK3 build.gradle
dependencies {
    // Remove: org.springframework:spring-web:5.3.34
    // Spring Framework 6.2.11 comes from SDK3 BOM with jakarta.servlet

    implementation 'com.barclaycard.digital:common-filter:5.0.3'  // SDK3-compatible
    implementation 'com.barclaycard.digital:common-context:1.3.0'
    implementation 'com.barclaycard.digital:executor-core:1.1.1'
    implementation 'com.barclaycard.digital:core-jsonapi-web:4.4.1'

    // Jakarta Validation API (SDK3 replaces javax.validation)
    implementation 'org.hibernate.validator:hibernate-validator'
    implementation 'jakarta.validation:jakarta.validation-api'
}
```

### Why This Matters

- **Package Namespace Change**: Java EE transitioned from `javax.*` to `jakarta.*` packages
- **Spring Framework 6.x Requirement**: Spring Boot 3.x requires Spring Framework 6.x which uses Jakarta EE exclusively
- **Binary Incompatibility**: javax.servlet and jakarta.servlet are not interchangeable at runtime
- **BOM Management**: SDK3 BOM is configured to provide the correct versions automatically
- **Classpath Pollution**: Manual version pins override BOM management and introduce conflicts

### Common Migration Errors

**Error 1: Explicit Spring Web Override**
```
java.lang.NoClassDefFoundError: javax/servlet/ServletRequest
Caused by: java.lang.ClassNotFoundException: javax.servlet.ServletRequest
```
**Fix:** Remove `org.springframework:spring-web:5.3.34` line from build.gradle

**Error 2: Hibernate Validator Version Conflict**
```
WARNING: Unable to load class for jakarta.validation...
Fallback to javax.validation...
```
**Fix:** Remove version pin from `hibernate-validator`, add explicit `jakarta.validation-api`

**Error 3: Mixed javax and jakarta on classpath**
```
Multiple implementations of Java EE APIs detected
Namespace conflict between javax.servlet and jakarta.servlet
```
**Fix:** Ensure NO javax.* dependencies are explicitly pinned; let BOM manage all versions

### Detection

**Search for problematic patterns:**
```bash
# Find explicit Spring Framework versions
grep -n "spring-web:5" build.gradle
grep -n "spring-framework.*5\." build.gradle

# Find javax.* namespace dependencies
grep -n "javax\." build.gradle

# Verify Hibernate Validator version pin
grep -n "hibernate-validator.*Final" build.gradle

# Check what's actually on classpath
./gradlew dependencies --configuration runtimeClasspath | grep -E "(spring-web|jakarta|javax\.)"
```

### Verification After Fix

```bash
# Compile successfully
./gradlew compileJava
# Expected: BUILD SUCCESSFUL

# Build JAR
./gradlew bootJar
# Expected: BUILD SUCCESSFUL, app.jar created

# Verify no javax.servlet on classpath
./gradlew dependencies --configuration runtimeClasspath | grep "javax.servlet"
# Expected: No results (javax.servlet should NOT be present)

# Verify jakarta.servlet is present
./gradlew dependencies --configuration runtimeClasspath | grep "jakarta.servlet"
# Expected: jakarta-servlet should be present via Spring Framework 6.2.11

# Run application
java -jar ./build/libs/app.jar
# Expected: Successful startup, no NoClassDefFoundError
```

### Gradle BOM Configuration Impact

From `build.gradle` (SDK3 setup):
```gradle
// ✅ CORRECT - SDK3 BOM provides correct versions
dependencyManagement {
    imports {
        mavenBom 'com.barclays.api:api-bom:${apiComVersion}'  // api-bom includes Spring Boot BOM
    }
}

// Spring Framework version is managed by:
// 1. Spring Boot BOM (automatically included in api-bom)
// 2. Spring Boot 3.5.7 requires Spring Framework 6.2.11
// 3. Spring Framework 6.2.11 provides jakarta.servlet

// DO NOT override with:
// implementation 'org.springframework:spring-web:5.3.34'  // ❌ Breaks SDK3
```

### Commit Reference
**CARDOPSAPI-12483 | Fix javax.servlet runtime error by removing SDK2 Spring Web dependency**
- Removed: `org.springframework:spring-web:5.3.34` (SDK2, javax.servlet)
- Updated: `hibernate-validator` to use SDK3 BOM-managed version
- Added: `jakarta.validation:jakarta.validation-api` (Jakarta EE)
- Result: No more NoClassDefFoundError at runtime, successful JAR execution

### Related Cards
- **Card 4**: Spring Framework Version Compatibility (6.2.11 requirement)
- **Card 7**: SDK2/SDK3 Bootstrap Configuration (common-filter 5.0.3 upgrade)

### References
- **Jakarta EE Migration**: [Jakarta EE Overview](https://jakarta.ee/about/facts/)
- **Spring Framework 6 Migration**: [Spring Framework 6.0 Migration Guide](https://github.com/spring-projects/spring-framework/wiki/Spring-Framework-6.0-Release-Notes)
- **Spring Boot 3 Package Mapping**: [Spring Boot 3 Migration - Packages](https://spring.io/blog/2023/01/31/spring-boot-3-migration-guide)
- **Hibernate Validator Jakarta**: [Hibernate Validator 8.0 Release Notes](https://docs.jboss.org/hibernate/validator/8.0/)

---

## Card 9: CycloneDX BOM Task Failure and Build Network Timeout Issues

### Issue
During SDK3 migration, the `cyclonedxBom` task (CycloneDX Software Bill of Materials generation) fails due to network connectivity issues, preventing successful build execution and causing build hangs.

### Problem
```
Task: cyclonedxBom
Error: Network connectivity error while downloading external RAML specifications
Result: Build fails or hangs waiting for network resources
Status: Build hangs or times out during gradle build execution
```

**Error Symptoms:**
```
java.net.ConnectException: Connection timeout
or
java.net.UnknownHostException downloading external specs
or
Build task 'cyclonedxBom' hangs indefinitely
or
Build fails without clear error message due to network timeout
```

### Root Causes

1. **Optional SBOM Generation**: `cyclonedxBom` is an optional task that generates CycloneDX format SBOM (Software Bill of Materials)
2. **Network Dependency**: Task attempts to download external RAML specifications from network resources during build
3. **Not Required for Deployment**: SBOM generation is optional; actual code compilation and JAR generation work fine
4. **Blocking Behavior**: Task runs during standard build lifecycle, blocking other operations
5. **Network Environment Variability**: Network access may be restricted, slow, or unavailable depending on build environment

### Impact Analysis

| Operation | Impact | Reason |
|-----------|--------|--------|
| **Code Compilation** | ✅ Unaffected | Main compilation doesn't depend on cyclonedxBom |
| **JAR Generation** | ✅ Unaffected | bootJar task completes successfully |
| **Build Execution** | ❌ Blocked | Task runs during build lifecycle, blocking completion |
| **Testing** | ❌ Blocked | Maven/Gradle runs cyclonedxBom in lifecycle |
| **CI/CD Pipeline** | ⚠️ May be affected | Depends on network access and timeout settings |

### Solution

**Disable the cyclonedxBom task in build.gradle:**

```gradle
// ✅ CORRECT - Add to build.gradle
// Disable cyclonedxBom task (optional SBOM generation)
// This task fails due to network connectivity issues downloading external RAML specs
// Main code compilation and JAR generation are unaffected
tasks.named('cyclonedxBom').configure {
    enabled = false
}
```

**Alternative Solutions (if you need SBOM generation):**

1. **Run with Network Access:**
   ```bash
   # Explicitly enable if network is available
   ./gradlew build -Dorg.gradle.jvmargs="-Dhttp.proxyHost=... -Dhttp.proxyPort=..."
   ```

2. **Run Selected Tasks Only:**
   ```bash
   # Skip cyclonedxBom when running build
   ./gradlew compileJava bootJar
   ```

### Why This Matters

**SBOM (Software Bill of Materials) Context:**
- CycloneDX is an industry standard for tracking software component dependencies
- Used for security audits and compliance reporting
- **NOT required** for application compilation or execution
- **ONLY required** when SBOM reports are explicitly requested for governance/compliance

**Network vs Build Environment Distinction:**
- Gradle tasks should be resilient to network connectivity
- Optional tasks that require network should be explicitly triggered, not auto-executed
- Different build environments (local, CI/CD) have different network contexts
- Task disabling is the recommended approach for non-critical optional tasks
- Build cache and task execution may differ across environments
- Disabling optional tasks improves overall build responsiveness

### Build Configuration Impact

**Location in build.gradle:**
```gradle
// At end of build.gradle (after other task configurations)

// Disable barclaysApiGenerate task (same pattern)
tasks.named('barclaysApiGenerate').configure {
    enabled = false
}

// Disable cyclonedxBom task (optional SBOM generation) ✅ ADD THIS
tasks.named('cyclonedxBom').configure {
    enabled = false
}
```

### Detection

**Check if cyclonedxBom is causing issues:**
```bash
# Run build with verbose output
./gradlew build --info 2>&1 | grep -i "cyclone\|raml\|network\|timeout"

# Expected output if problematic:
# Executing task 'cyclonedxBom'
# Downloading RAML specifications...
# Connection timeout or Unknown host

# Check if task is registered
./gradlew tasks | grep -i "cyclone"
# Expected: cyclonedxBom
```

### Verification After Fix

**Step 1: Disable Task in build.gradle**
```bash
# Add to build.gradle:
tasks.named('cyclonedxBom').configure {
    enabled = false
}
```

**Step 2: Verify Task is Disabled**
```bash
# Check task list
./gradlew tasks --all | grep -i "cyclone"
# Expected output: EMPTY (task no longer listed)

# Or verify in task graph
./gradlew build --dry-run 2>&1 | grep -i "cyclone"
# Expected: EMPTY (task not in execution plan)
```

**Step 3: Verify Code Compilation Still Works**
```bash
# Build should complete successfully
./gradlew clean compileJava
# Expected: BUILD SUCCESSFUL

# JAR generation should work
./gradlew bootJar
# Expected: BUILD SUCCESSFUL, app.jar generated in build/libs/

# Full build without cyclonedxBom
./gradlew build
# Expected: BUILD SUCCESSFUL (all tests pass if applicable)
```

### Common Scenarios

**Scenario 1: Build Timeout During Execution**
```
Symptom: Build starts but hangs indefinitely without progress
Root Cause: cyclonedxBom task waiting for network resources
Solution: Disable cyclonedxBom in build.gradle as shown above
```

**Scenario 2: Build Timeout on CI/CD Pipeline**
```
Symptom: CI/CD pipeline times out on cyclonedxBom task
Root Cause: Network resources unavailable or very slow in CI environment
Solution: Disable in build.gradle OR configure task timeout
```

**Scenario 3: Network Connectivity Issues in Different Environments**
```
Symptom: Build works in one environment but fails in another
Root Cause: Network access or proxy settings differ across environments
Solution: Disable optional network-dependent tasks in build.gradle
```

### Commit Reference

**CARDOPSAPI-12483 | Disable cyclonedxBom task to resolve network timeout issues**
- Add `tasks.named('cyclonedxBom').configure { enabled = false }`
- Prevents network errors and build hangs during gradle execution
- cyclonedxBom is optional SBOM generation, not required for deployment
- Main code compilation and JAR generation unaffected
- Verified: Build execution successful without network timeouts

### Related Concepts

**Similar Optional Tasks:**
- `barclaysApiGenerate` - Also optional, can be disabled if not needed
- `cycloneDxReport` - Related SBOM reporting task
- `jacocoTestReport` - Code coverage reporting (optional)

**Best Practices:**
- Document why each optional task is disabled
- Only disable tasks that are not required for deployment
- Consider environment-specific build profiles for optional tasks
- Use Gradle task filtering for CI/CD vs local builds

### References

- **CycloneDX Standard**: [CycloneDX Project](https://cyclonedx.org/)
- **Gradle Task Configuration**: [Gradle Task Configuration Guide](https://docs.gradle.org/current/userguide/task_configuration.html)
- **Software Bill of Materials (SBOM)**: [NIST SBOM Guidelines](https://www.cisa.gov/sbom)

---

## Card 10: Karate Testing Framework SDK2 to SDK3 Migration

### Issue
Karate testing framework requires version and API updates when migrating from SDK2 (JUnit 4) to SDK3 (JUnit 5). The core changes involve updating test runner class inheritance, JUnit version compatibility, and assertion method signatures.

### Problem

**SDK2 Pattern (JUnit 4) - build.gradle:**
```gradle
// ❌ WRONG - SDK2 versions with JUnit 4
testImplementation 'com.intuit.karate:karate-junit4:0.9.6'
testImplementation 'com.intuit.karate:karate-apache:0.9.6'
testImplementation 'net.masterthought:cucumber-reporting:3.13.0'
testImplementation 'junit:junit:4.13.2'
testImplementation 'org.junit.vintage:junit-vintage-engine'  // JUnit 4 compatibility layer
```

**SDK2 Test Code Example (JUnit 4 with @RunWith):**
```java
// ❌ WRONG - SDK2 pattern using @RunWith and JUnit 4 annotations
package KarateTest;

import com.intuit.karate.junit4.Karate;              // SDK2 - JUnit 4 runner
import org.junit.BeforeClass;                        // SDK2 - JUnit 4
import org.junit.AfterClass;                         // SDK2 - JUnit 4
import org.junit.Test;                               // SDK2 - JUnit 4
import org.junit.runner.RunWith;                     // SDK2 - JUnit 4
import org.junit.Assert;                             // SDK2 - JUnit 4 assertions

/**
 * SDK2: Karate tests using JUnit 4
 */
@RunWith(Karate.class)                              // ❌ JUnit 4 pattern
public class HealthCheckIntTest {

    private static WiremockRunner wiremock;

    @BeforeClass                                    // ❌ JUnit 4
    public static void beforeClass() {
        System.setProperty("karate.env", "int");
        wiremock = new WiremockRunner();
        wiremock.startWiremock("path/to/wiremock");
    }

    @Test                                           // ❌ JUnit 4 import
    public void runTest() throws Exception {
        // Feature file executed by Karate runner via @RunWith
        // Results handled by framework
    }

    @AfterClass                                     // ❌ JUnit 4
    public static void tearDown() {
        wiremock.stopWiremock();
    }
}
```

**Error Symptoms:**
```
ClassNotFoundException: org.junit.BeforeClass not found
or
NoSuchMethodError: Karate junit4 runner initialization failed
or
Karate tests don't execute - no test runner found for JUnit 5 platform
or
@RunWith annotation not supported in JUnit 5
```

### Root Causes

1. **JUnit 4 vs JUnit 5 APIs**: `@BeforeClass` and `@AfterClass` (JUnit 4) replaced by `@BeforeAll` and `@AfterAll` (JUnit 5)
2. **Test Runner Model Change**: JUnit 4 used `@RunWith` annotation; JUnit 5 uses direct test execution
3. **Karate Runner Version**: `karate-junit4:0.9.6` designed for JUnit 4; SDK3 requires `karate-junit5` for JUnit 5
4. **Assertion Libraries**: JUnit 4 assertions (`org.junit.Assert`) vs JUnit 5 (`org.junit.jupiter.api.Assertions`)
5. **Cucumber Reporting**: Version 3.13.0 only supports JUnit 4; JUnit 5 requires 5.7.5+

### Solution

**Step 1: Update Gradle Dependencies (build.gradle)**

```gradle
// ✅ CORRECT - SDK3 versions compatible with JUnit 5
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'       // ✅ JUnit 5 support
testImplementation 'com.intuit.karate:karate-apache:1.4.1'       // ✅ Updated version
testImplementation 'net.masterthought:cucumber-reporting:5.7.5'  // ✅ JUnit 5 compatible

// JUnit 5 (comes from spring-boot-starter-test in Spring Boot 3.x)
testImplementation 'org.junit.jupiter:junit-jupiter'
testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'

// Cucumber for Karate feature file parsing
testImplementation 'io.cucumber:cucumber-java:7.14.0'
testImplementation 'io.cucumber:cucumber-junit-platform-engine:7.14.0'

// Task configuration for JUnit 5
tasks.named('test') {
    useJUnitPlatform()  // ✅ Enable JUnit 5 test platform
}
```

**Step 2: Update Test Class - SDK3 Pattern (JUnit 5 with Direct Runner API)**

```java
// ✅ CORRECT - SDK3 pattern using direct Runner API (no @RunWith needed)
package KarateTest;

import static com.barclaycard.digital.wiremock.utils.AbstractWiremockKarateTest.WIREMOCK_CONFIGURATION_DIRECTORY;
import static org.junit.jupiter.api.Assertions.assertEquals;    // ✅ JUnit 5 assertion

import com.barclaycard.digital.wiremock.utils.WiremockRunner;
import com.intuit.karate.Results;                               // ✅ Direct Runner API
import com.intuit.karate.Runner;                                // ✅ Direct Runner API
import org.junit.jupiter.api.AfterAll;                          // ✅ JUnit 5
import org.junit.jupiter.api.BeforeAll;                         // ✅ JUnit 5
import org.junit.jupiter.api.Test;                              // ✅ JUnit 5
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * SDK3: Karate tests using JUnit 5 Direct Runner API
 *
 * Migration Changes:
 * 1. Removed @RunWith(Karate.class) - not needed in JUnit 5
 * 2. Changed @BeforeClass to @BeforeAll (JUnit 5)
 * 3. Changed @AfterClass to @AfterAll (JUnit 5)
 * 4. Use direct Runner.path().tags().parallel() API
 * 5. Use JUnit 5 assertEquals from Assertions class
 */
public class HealthCheckIntTest {

    private static final Logger LOG = LoggerFactory.getLogger(HealthCheckIntTest.class);
    private static WiremockRunner wiremock = new WiremockRunner();

    @BeforeAll                                                   // ✅ JUnit 5 (was @BeforeClass)
    public static void beforeClass() {
        System.setProperty("karate.env", "int");
        wiremock.startWiremock(WIREMOCK_CONFIGURATION_DIRECTORY);
    }

    @Test                                                        // ✅ JUnit 5 import: org.junit.jupiter.api.Test
    public void runTest() throws Exception {
        // ✅ CORRECT - Direct Runner API (no @RunWith inheritance needed)
        Results results =
            Runner.path("src/integrationTest/resources/features/service_mesh_healthcheck.feature")
                .tags(
                    "@SpringBoardHealthCheck",
                    "~@ServiceMeshHealthCheck",
                    "~@ignore",
                    "~@restAssured")
                .parallel(1);

        // ✅ CORRECT - JUnit 5 assertion
        assertEquals(0, results.getFailCount());

        if (results.getFailCount() > 0) {
            LOG.error("Test failures detected: {}", results.getFailCount());
        }
    }

    @AfterAll                                                    // ✅ JUnit 5 (was @AfterClass)
    public static void tearDown() {
        wiremock.stopWiremock();
    }
}
```

### Side-by-Side Comparison

#### Import Changes

**SDK2 (JUnit 4):**
```java
❌ REMOVE:
import com.intuit.karate.junit4.Karate;
import org.junit.BeforeClass;
import org.junit.AfterClass;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.junit.Assert;
```

**SDK3 (JUnit 5):**
```java
✅ ADD:
import com.intuit.karate.Results;
import com.intuit.karate.Runner;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.assertEquals;
```

#### Class Declaration Changes

**SDK2:**
```java
❌ WRONG
@RunWith(Karate.class)
public class HealthCheckIntTest {
}
```

**SDK3:**
```java
✅ CORRECT
public class HealthCheckIntTest {
    // No @RunWith annotation
    // No class inheritance
}
```

#### Method Annotation Changes

**SDK2:**
```java
❌ WRONG
@BeforeClass
public static void beforeClass() { }

@Test
public void runTest() { }

@AfterClass
public static void tearDown() { }
```

**SDK3:**
```java
✅ CORRECT
@BeforeAll
public static void beforeClass() { }

@Test
public void runTest() { }

@AfterAll
public static void tearDown() { }
```

#### Test Execution Changes

**SDK2 (Implicit via @RunWith):**
```java
❌ WRONG
@RunWith(Karate.class)
public class HealthCheckIntTest {
    @Test
    public void runTest() throws Exception {
        // Karate runner handles feature file execution automatically
        // Results implicit in framework
    }
}
```

**SDK3 (Explicit Direct Runner API):**
```java
✅ CORRECT
public class HealthCheckIntTest {
    @Test
    public void runTest() throws Exception {
        // Direct control over Runner execution
        Results results = Runner.path("path/to/feature.feature")
            .tags("@tag")
            .parallel(1);

        // Explicit assertion on results
        assertEquals(0, results.getFailCount());
    }
}
```

### Dependency Version Matrix

| Component | SDK2 | SDK3 | Change | Reason |
|-----------|------|------|--------|--------|
| **karate** | 0.9.6 (junit4) | 1.4.1 (junit5) | ✅ Major version + variant | JUnit 5 support |
| **cucumber-reporting** | 3.13.0 | 5.7.5 | ✅ Version bump | JUnit 5 event model |
| **junit** | 4.13.2 | Removed | ✅ Removed | Replaced by JUnit Jupiter |
| **junit-jupiter** | N/A | 5.x (via boot) | ✅ Added | JUnit 5 core |
| **junit-platform** | N/A | 1.10.1 | ✅ Added | JUnit 5 platform |
| **cucumber-java** | N/A | 7.14.0 | ✅ Added | Feature file parsing |

### Why This Matters

**Test Framework Alignment:**
- JUnit 5 is the standard for Spring Boot 3.x and Java 21
- Mixing JUnit 4 and JUnit 5 causes classpath conflicts
- `karate-junit4` is JUnit 4 only; SDK3 requires `karate-junit5`

**Direct Runner API Benefits:**
- More explicit control over test execution flow
- Better composition of multiple test scenarios
- Easier to collect and validate Results object
- No inheritance or annotation magic needed

**Version Compatibility:**
- Cucumber reporting 3.13.0 uses JUnit 4 event listeners
- Version 5.7.5 implements JUnit Platform listener interface
- Mixing versions causes reporter initialization failures

**Code Clarity:**
- Direct `Runner.path().tags().parallel()` is more readable
- Explicit `assertEquals(results.getFailCount(), 0)` is clearer than framework magic
- No hidden test discovery mechanism

### Detection & Verification

**Find SDK2 Karate Patterns:**
```bash
# Find @RunWith(Karate.class) patterns
grep -r "@RunWith(Karate" src/integrationTest/

# Find old karate-junit4 dependency
grep "karate-junit4" build.gradle

# Find JUnit 4 lifecycle methods
grep -r "@BeforeClass\|@AfterClass" src/integrationTest/
```

**Verify SDK3 Configuration:**
```bash
# Check for JUnit 5 Karate
./gradlew dependencies --configuration testRuntimeClasspath | grep "karate"
# Expected: karate-junit5:1.4.1

# Verify Cucumber reporting version
./gradlew dependencies --configuration testRuntimeClasspath | grep "cucumber-reporting"
# Expected: cucumber-reporting:5.7.5

# Check for useJUnitPlatform configuration
grep "useJUnitPlatform" build.gradle
# Expected: tasks.named('test') { useJUnitPlatform() }
```

**Run Tests:**
```bash
# Compile integration tests
./gradlew compileIntegrationTestJava
# Expected: BUILD SUCCESSFUL

# Run Karate tests
./gradlew integrationTest
# Expected: Tests execute with JUnit 5 platform
# Expected: Feature files parsed and executed correctly
```

### Common Migration Errors & Fixes

**Error 1: ClassNotFoundException: org.junit.BeforeClass**

```
java.lang.ClassNotFoundException: org.junit.BeforeClass
Caused by: java.lang.NoClassDefFoundError
```

**Fix:**
```java
// ❌ REMOVE
import org.junit.BeforeClass;

// ✅ ADD
import org.junit.jupiter.api.BeforeAll;

// Update annotation
@BeforeAll  // Changed from @BeforeClass
public static void beforeClass() { }
```

---

**Error 2: karate-junit4 incompatible with JUnit 5**

```
java.lang.ClassNotFoundException: com.intuit.karate.junit4.Karate
or
No runner found for class HealthCheckIntTest
```

**Fix:**
```gradle
// ❌ WRONG
testImplementation 'com.intuit.karate:karate-junit4:0.9.6'

// ✅ CORRECT
testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
```

---

**Error 3: @RunWith annotation not recognized**

```
Error: Annotation @RunWith cannot be applied to class
or
RunWith is not applicable
```

**Fix:**
```java
// ❌ REMOVE
@RunWith(Karate.class)
public class HealthCheckIntTest { }

// ✅ USE DIRECT API
public class HealthCheckIntTest {
    @Test
    public void runTest() throws Exception {
        Results results = Runner.path("...").parallel(1);
        assertEquals(0, results.getFailCount());
    }
}
```

---

**Error 4: Cucumber reporting version mismatch**

```
java.lang.NoSuchMethodError in net.masterthought package
or
Reporting listener not found for JUnit 5 events
```

**Fix:**
```gradle
// ❌ WRONG
testImplementation 'net.masterthought:cucumber-reporting:3.13.0'

// ✅ CORRECT
testImplementation 'net.masterthought:cucumber-reporting:5.7.5'
```

### Complete Test Configuration (build.gradle)

```gradle
// ✅ CORRECT - SDK3 test configuration with Karate
dependencies {
    // JUnit 5 core (included via spring-boot-starter-test)
    testImplementation 'org.junit.jupiter:junit-jupiter'
    testImplementation 'org.junit.platform:junit-platform-suite-api:1.10.1'
    testRuntimeOnly 'org.junit.platform:junit-platform-launcher'

    // Karate - JUnit 5 version
    testImplementation 'com.intuit.karate:karate-junit5:1.4.1'
    testImplementation 'com.intuit.karate:karate-apache:1.4.1'

    // Cucumber for feature file support
    testImplementation 'io.cucumber:cucumber-java:7.14.0'
    testImplementation 'io.cucumber:cucumber-junit-platform-engine:7.14.0'

    // Reporting - JUnit 5 compatible version
    testImplementation 'net.masterthought:cucumber-reporting:5.7.5'

    // Other test dependencies
    testImplementation 'org.assertj:assertj-core:3.24.2'
    testImplementation 'org.mockito:mockito-core:5.7.0'
    testImplementation 'org.mockito:mockito-junit-jupiter:5.7.0'
}

// ✅ CORRECT - Enable JUnit 5 platform
tasks.named('test') {
    useJUnitPlatform()
}
```

### Commit Reference

```
CARDOPSAPI-12483 | Migrate Karate tests from JUnit 4 to JUnit 5 (SDK3)
- Upgrade karate-junit4:0.9.6 to karate-junit5:1.4.1
- Update Cucumber reporting 3.13.0 to 5.7.5 (JUnit 5 support)
- Change @BeforeClass/@AfterClass to @BeforeAll/@AfterAll
- Remove @RunWith(Karate.class) annotation, use direct Runner API
- Update test imports from org.junit to org.junit.jupiter.api
- Enable JUnit 5 platform with useJUnitPlatform()
- Verified: Integration tests execute successfully with JUnit 5
```

### References

- **Karate Testing Framework:** [Karate GitHub](https://github.com/intuit/karate)
- **Karate JUnit 5 Support:** [Karate JUnit 5 Integration](https://github.com/intuit/karate/wiki/Karate-JUnit-5)
- **JUnit 5 Migration:** [JUnit 5 User Guide](https://junit.org/junit5/docs/current/user-guide/)
- **Spring Boot 3 Testing:** [Spring Boot 3 Migration Guide](https://spring.io/blog/2023/01/31/spring-boot-3-migration-guide)
- **Cucumber Java:** [Cucumber Java Documentation](https://cucumber.io/docs/cucumber/)

---

## Card 11: SDK2/SDK3 Breaking Class Name Changes (Async Repository Pattern)

### Issue

During SDK3 migration, SDK2 library classes are renamed in SDK3 libraries with breaking changes to both class names and method signatures. The repository pattern changes from synchronous to asynchronous (CompletableFuture), causing compilation errors and runtime failures when old class names are used.

### Problem

**SDK2 Pattern (Synchronous):**
```java
// ❌ SDK2 - Old class names that don't exist in SDK3
import com.barclaycard.digital.account.repository.AccountQueryRepository;     // ❌ Not in SDK3
import com.barclaycard.digital.account.repository.AccountRequest;            // ❌ Not in SDK3
import com.barclaycard.digital.account.repository.AccountResponse;           // ❌ Not in SDK3

@Component
@UUID
public class AccountQueryImplReadStore implements AccountQueryReadStore {

  private final AccountQueryRepository accountQueryRepository;

  public AccountQueryImplReadStore(
      @Qualifier("accountProxyQueryRepository") AccountQueryRepository accountQueryRepository) {
    this.accountQueryRepository = accountQueryRepository;
  }

  @Override
  public AccountIdResponse getAccountId(String deviceId) {
    // ❌ COMPILATION ERROR: Cannot resolve symbol 'AccountRequest'
    AccountResponse accountResponse =
        accountQueryRepository.find(new AccountRequest(deviceId));
    return new AccountIdResponse(
        accountResponse.getAccountNumber(),
        new AccountIdResponseAttributes(accountResponse.getAccountNumber()));
  }
}
```

**Error Symptoms:**
```
error: cannot find symbol
  symbol:   class AccountQueryRepository
  location: package com.barclaycard.digital.account.repository

error: cannot find symbol
  symbol:   class AccountRequest
  location: package com.barclaycard.digital.account.repository

error: cannot find symbol
  symbol:   class AccountResponse
  location: package com.barclaycard.digital.account.repository

error: incompatible types
  required: AccountIdResponse
  found:    CompletableFuture<AccountCardResponse>
```

### Root Causes

1. **Breaking Class Rename**: SDK3 libraries renamed `AccountQuery*` classes to `AccountCard*`
   - `AccountQueryRepository` → `AccountCardQueryRepository`
   - `AccountRequest` → `AccountCardRequest`
   - `AccountResponse` → `AccountCardResponse`

2. **Synchronous to Asynchronous API Change**:
   - SDK2: Repository `.find()` returns direct object: `AccountResponse find(AccountRequest)`
   - SDK3: Repository `.find()` returns async: `CompletableFuture<AccountCardResponse> find(AccountCardRequest)`

3. **Bean Qualifier Change**:
   - SDK2: `@Qualifier("accountProxyQueryRepository")`
   - SDK3: `@Qualifier("accountCardProxyQueryRepository")`

4. **Cascading Effects**:
   - Changes ripple through all test files using `AccountResponse`
   - Mock setup patterns must change to handle `CompletableFuture`

### Solution

**Step 1: Update Main Implementation (AccountQueryImplReadStore.java)**

```java
// ✅ SDK3 - Updated class names and async pattern
import com.barclaycard.digital.account.repository.AccountCardQueryRepository;  // ✅ NEW SDK3 class
import com.barclaycard.digital.account.repository.AccountCardRequest;          // ✅ NEW SDK3 class
import com.barclaycard.digital.account.repository.AccountCardResponse;         // ✅ NEW SDK3 class
import java.util.concurrent.CompletableFuture;                                 // ✅ NEW - async support
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.stereotype.Component;

@Component
@UUID
public class AccountQueryImplReadStore implements AccountQueryReadStore {

  private final AccountCardQueryRepository accountCardProxyQueryRepository;      // ✅ Updated type

  public AccountQueryImplReadStore(
      @Qualifier("accountCardProxyQueryRepository")                             // ✅ Updated qualifier
          AccountCardQueryRepository accountCardProxyQueryRepository) {          // ✅ Updated param type
    this.accountCardProxyQueryRepository = accountCardProxyQueryRepository;
  }

  @Override
  public AccountIdResponse getAccountId(String deviceId) {
    // ✅ FIXED - Handle async CompletableFuture return type
    CompletableFuture<AccountCardResponse> accountResponseFuture =
        accountCardProxyQueryRepository.find(new AccountCardRequest(deviceId, deviceId));

    // ✅ Convert async to sync with .join()
    AccountCardResponse accountResponse = accountResponseFuture.join();

    return new AccountIdResponse(
        accountResponse.getAccountNumber(),
        new AccountIdResponseAttributes(accountResponse.getAccountNumber()));
  }
}
```

**Step 2: Update Test Implementation (AccountQueryImplReadStoreTest.java)**

```java
// ✅ SDK3 - Updated class names and async mock pattern
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.when;

import com.barclaycard.digital.account.repository.AccountCardQueryRepository;  // ✅ NEW
import com.barclaycard.digital.account.repository.AccountCardRequest;          // ✅ NEW
import com.barclaycard.digital.account.repository.AccountCardResponse;         // ✅ NEW
import java.util.concurrent.CompletableFuture;                                 // ✅ NEW
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
public class AccountQueryImplReadStoreTest {

  private static final String DEVICE_ID = "31393933-3533-3231-3435-303933303035";
  private static final String ACCOUNT_NUMBER = "5613361458799";

  @InjectMocks private AccountQueryImplReadStore accountQueryImplReadStore;

  @Mock private AccountCardQueryRepository accountCardQueryRepository;         // ✅ Updated mock type

  private AccountCardResponse accountCardResponse;                              // ✅ Updated variable type
  private AccountIdResponse accountIdResponse;

  @BeforeEach
  public void before() {
    // ✅ No MockitoAnnotations.initMocks() - JUnit 5 @ExtendWith handles it
    accountQueryImplReadStore = new AccountQueryImplReadStore(accountCardQueryRepository);
  }

  @Test
  public void shouldGetAccountId() {
    givenAccountQueryParams();
    whenAccountIdCallMade();
    thenCheckAccountNumber();
  }

  private void givenAccountQueryParams() {
    accountCardResponse = new AccountCardResponse();
    accountCardResponse.setAccountNumber(ACCOUNT_NUMBER);

    // ✅ CRITICAL: Mock returns CompletableFuture (async), not direct object
    when(accountCardQueryRepository.find(any(AccountCardRequest.class)))
        .thenReturn(CompletableFuture.completedFuture(accountCardResponse));
  }

  private void givenAccountQueryParamsNoMock() {
    doThrow(NotFoundException.class)
        .when(accountCardQueryRepository)
        .find(any(AccountCardRequest.class));
  }
}
```

### Side-by-Side Comparison

#### Import Changes

**SDK2 (Synchronous):**
```java
❌ REMOVE:
import com.barclaycard.digital.account.repository.AccountQueryRepository;
import com.barclaycard.digital.account.repository.AccountRequest;
import com.barclaycard.digital.account.repository.AccountResponse;
```

**SDK3 (Asynchronous):**
```java
✅ ADD:
import com.barclaycard.digital.account.repository.AccountCardQueryRepository;
import com.barclaycard.digital.account.repository.AccountCardRequest;
import com.barclaycard.digital.account.repository.AccountCardResponse;
import java.util.concurrent.CompletableFuture;
```

#### Class Members - Field & Constructor

**SDK2:**
```java
❌ WRONG
private final AccountQueryRepository accountQueryRepository;

public AccountQueryImplReadStore(
    @Qualifier("accountProxyQueryRepository") AccountQueryRepository accountQueryRepository) {
  this.accountQueryRepository = accountQueryRepository;
}
```

**SDK3:**
```java
✅ CORRECT
private final AccountCardQueryRepository accountCardProxyQueryRepository;

public AccountQueryImplReadStore(
    @Qualifier("accountCardProxyQueryRepository")
        AccountCardQueryRepository accountCardProxyQueryRepository) {
  this.accountCardProxyQueryRepository = accountCardProxyQueryRepository;
}
```

#### Method Implementation - Synchronous vs Asynchronous

**SDK2 (Synchronous):**
```java
❌ WRONG
@Override
public AccountIdResponse getAccountId(String deviceId) {
    // Direct sync call, returns object immediately
    AccountResponse accountResponse =
        accountQueryRepository.find(new AccountRequest(deviceId));
    return new AccountIdResponse(...);
}
```

**SDK3 (Asynchronous with CompletableFuture):**
```java
✅ CORRECT
@Override
public AccountIdResponse getAccountId(String deviceId) {
    // Async call, returns CompletableFuture
    CompletableFuture<AccountCardResponse> accountResponseFuture =
        accountCardProxyQueryRepository.find(new AccountCardRequest(deviceId, deviceId));

    // Block and wait for result with .join()
    AccountCardResponse accountResponse = accountResponseFuture.join();
    return new AccountIdResponse(...);
}
```

#### Test Mock Setup

**SDK2 (Direct Object Return):**
```java
❌ WRONG
@Mock private AccountQueryRepository accountQueryRepository;
private AccountResponse accountResponse;

when(accountQueryRepository.find(any(AccountRequest.class)))
    .thenReturn(accountResponse);  // Direct object, not CompletableFuture
```

**SDK3 (CompletableFuture Return):**
```java
✅ CORRECT
@Mock private AccountCardQueryRepository accountCardQueryRepository;
private AccountCardResponse accountCardResponse;

when(accountCardQueryRepository.find(any(AccountCardRequest.class)))
    .thenReturn(CompletableFuture.completedFuture(accountCardResponse));  // Wrapped in CompletableFuture
```

### Class Renaming Pattern Matrix

| SDK2 Class | SDK3 Class | Package | Files Affected | Change Type |
|------------|------------|---------|-----------------|------------|
| `AccountQueryRepository` | `AccountCardQueryRepository` | `com.barclaycard.digital.account.repository` | 2 (main + test) | Class + API |
| `AccountRequest` | `AccountCardRequest` | `com.barclaycard.digital.account.repository` | 2 (main + test) | Class name |
| `AccountResponse` | `AccountCardResponse` | `com.barclaycard.digital.account.repository` | 6 (all query services) | Class name |
| **Return Type** | **CompletableFuture<T>** | **Built-in Java** | 1 (implementation) | **Async/Sync** |

### Affected Files (6 Total)

1. **Main Implementation:**
   - `src/main/java/com/barclays/api/statement/service/impl/AccountQueryImplReadStore.java` - Core class renames + async handling

2. **Test Files:**
   - `src/test/java/com/barclays/api/statement/service/impl/AccountQueryImplReadStoreTest.java` - All 3 class renames + CompletableFuture mock
   - `src/test/java/com/barclays/api/statement/service/impl/BalanceQueryServiceImplTest.java` - AccountResponse → AccountCardResponse
   - `src/test/java/com/barclays/api/statement/service/impl/FundsConfirmationQueryServiceTest.java` - AccountResponse → AccountCardResponse
   - `src/test/java/com/barclays/api/statement/service/impl/StatementQueryServiceImplTest.java` - AccountResponse → AccountCardResponse (multiple usages)
   - `src/test/java/com/barclays/api/statement/service/impl/TransactionQueryServiceImplTest.java` - AccountResponse → AccountCardResponse (multiple usages)

### Why This Matters

**Breaking API Changes:**
- Not a simple namespace migration (javax → jakarta)
- Actual class names changed due to library API evolution
- Return type changed from sync to async (CompletableFuture)
- Affects both compilation AND runtime behavior

**Synchronous to Asynchronous Transition:**
- SDK2 used blocking synchronous calls: `find(request) → object`
- SDK3 uses non-blocking async calls: `find(request) → CompletableFuture<object>`
- Must convert with `.join()` when synchronous result needed
- Thread implications: `.join()` blocks caller thread

**Cascading Dependencies:**
- Mock setups must return `CompletableFuture.completedFuture()`
- All downstream service tests affected
- Constructor injection patterns changed (bean qualifiers)

### Detection

**Symptom: Compilation Errors**
```bash
# Run compilation
./gradlew compileJava

# Expected errors if not fixed:
# error: cannot find symbol: class AccountQueryRepository
# error: cannot find symbol: class AccountRequest
# error: cannot find symbol: class AccountResponse
# error: incompatible types: found CompletableFuture, required AccountIdResponse
```

**Find All Usages:**
```bash
# Find SDK2 class usages
grep -r "AccountQueryRepository\|AccountRequest\|AccountResponse" src/

# Should return EMPTY (if migration complete)
# Only AccountCard* classes should appear in SDK3
grep -r "AccountCard" src/

# Expected output (SDK3):
# AccountCardQueryRepository
# AccountCardRequest
# AccountCardResponse
```

### Verification After Fix

**Step 1: Verify Class Names Updated**
```bash
grep -n "AccountCardQueryRepository\|AccountCardRequest\|AccountCardResponse" \
    src/main/java/com/barclays/api/statement/service/impl/AccountQueryImplReadStore.java

# Expected output:
# import com.barclaycard.digital.account.repository.AccountCardQueryRepository;
# import com.barclaycard.digital.account.repository.AccountCardRequest;
# import com.barclaycard.digital.account.repository.AccountCardResponse;
# private final AccountCardQueryRepository accountCardProxyQueryRepository;
# CompletableFuture<AccountCardResponse> accountResponseFuture = ...
```

**Step 2: Verify CompletableFuture Usage**
```bash
grep -n "CompletableFuture\|\.join()" \
    src/main/java/com/barclays/api/statement/service/impl/AccountQueryImplReadStore.java

# Expected output:
# import java.util.concurrent.CompletableFuture;
# CompletableFuture<AccountCardResponse> accountResponseFuture = ...
# AccountCardResponse accountResponse = accountResponseFuture.join();
```

**Step 3: Verify Test Mock Patterns**
```bash
grep -n "CompletableFuture\.completedFuture" \
    src/test/java/com/barclays/api/statement/service/impl/AccountQueryImplReadStoreTest.java

# Expected output:
# .thenReturn(CompletableFuture.completedFuture(accountCardResponse));
```

**Step 4: Compile and Build**
```bash
# Clean compile
./gradlew clean compileJava
# Expected: BUILD SUCCESSFUL

# Run tests
./gradlew test
# Expected: All tests PASS

# Build JAR
./gradlew bootJar
# Expected: BUILD SUCCESSFUL, app.jar generated
```

### Common Migration Errors & Fixes

**Error 1: Cannot resolve symbol 'AccountQueryRepository'**

```
error: cannot find symbol
  symbol:   class AccountQueryRepository
  location: package com.barclaycard.digital.account.repository
```

**Fix:**
```java
// ❌ REMOVE
import com.barclaycard.digital.account.repository.AccountQueryRepository;

// ✅ ADD
import com.barclaycard.digital.account.repository.AccountCardQueryRepository;

// Update variable
private final AccountCardQueryRepository accountCardProxyQueryRepository;
```

---

**Error 2: Incompatible types: CompletableFuture found, AccountIdResponse required**

```
error: incompatible types
  required: AccountIdResponse
  found:    CompletableFuture<AccountCardResponse>
```

**Fix:**
```java
// ❌ WRONG - Missing .join() to convert async to sync
public AccountIdResponse getAccountId(String deviceId) {
    CompletableFuture<AccountCardResponse> result =
        accountCardProxyQueryRepository.find(new AccountCardRequest(deviceId, deviceId));
    return new AccountIdResponse(...); // Type mismatch!
}

// ✅ CORRECT - Use .join() to block and get result
public AccountIdResponse getAccountId(String deviceId) {
    CompletableFuture<AccountCardResponse> accountResponseFuture =
        accountCardProxyQueryRepository.find(new AccountCardRequest(deviceId, deviceId));
    AccountCardResponse accountResponse = accountResponseFuture.join(); // ✅ Blocks here
    return new AccountIdResponse(
        accountResponse.getAccountNumber(),
        new AccountIdResponseAttributes(accountResponse.getAccountNumber()));
}
```

---

**Error 3: Mock setup returns wrong type - Test fails at runtime**

```
when() requires an argument which has to be 'a method call on a mock'.
For example:
    when(mock.getArticles()).thenReturn(articles);

You are trying to test a private method getArticles that has CompletableFuture return type
But mock is configured to return direct object
```

**Fix:**
```java
// ❌ WRONG - Mock returns direct object, not CompletableFuture
when(accountQueryRepository.find(any(AccountRequest.class)))
    .thenReturn(accountResponse);

// ✅ CORRECT - Mock returns CompletableFuture wrapper
when(accountCardQueryRepository.find(any(AccountCardRequest.class)))
    .thenReturn(CompletableFuture.completedFuture(accountCardResponse));
```

---

**Error 4: Bean injection fails - Qualifier mismatch**

```
UnsatisfiedDependencyException: Error creating bean with name 'accountQueryImplReadStore'
No bean named 'accountProxyQueryRepository' available
```

**Fix:**
```java
// ❌ WRONG - Old SDK2 bean qualifier
@Qualifier("accountProxyQueryRepository")
AccountQueryRepository accountQueryRepository

// ✅ CORRECT - Updated SDK3 bean qualifier
@Qualifier("accountCardProxyQueryRepository")
AccountCardQueryRepository accountCardProxyQueryRepository
```

---

**Error 5: Multiple AccountResponse usages in test setup**

```
givenAccountQueryParams() method in test uses:
    private AccountResponse accountResponse;
    accountResponse = new AccountResponse();
```

**Fix:**
```java
// ❌ REMOVE ALL SDK2 references
import com.barclaycard.digital.account.repository.AccountResponse;
private AccountResponse accountResponse;

// ✅ UPDATE TO SDK3
import com.barclaycard.digital.account.repository.AccountCardResponse;
private AccountCardResponse accountCardResponse;
```

### Commit Reference

```
CARDOPSAPI-14731 | Code Refactor: Migrate SDK2 class names to SDK3 (AccountQuery* → AccountCard*)
- Migrate AccountQueryRepository → AccountCardQueryRepository
- Migrate AccountRequest → AccountCardRequest
- Migrate AccountResponse → AccountCardResponse
- Update bean qualifiers: accountProxyQueryRepository → accountCardProxyQueryRepository
- Handle CompletableFuture async return type with .join() conversion
- Update 6 files: 1 main implementation + 5 test files
- Update mock patterns to return CompletableFuture.completedFuture()
- Remove unnecessary SDK2 classes: DeviceIdRequest, MockitoAnnotations.initMocks()
- Verified: All tests PASS, compilation SUCCESSFUL
```

### JAR/Library Details - Where Breaking Changes Introduced

**SDK2 to SDK3 Dependency Upgrades Introducing Class Changes:**

| Library | SDK2 Version | SDK3 Version | Breaking Changes | Reason |
|---------|--------------|--------------|------------------|--------|
| `com.barclaycard.digital:system-qry-cardholder-account-runtime` | N/A | `10.1-000` | AccountQueryRepository → AccountCardQueryRepository, AccountRequest → AccountCardRequest, AccountResponse → AccountCardResponse | SDK3 library introduced new account query API with "Card" naming prefix; Async/CompletableFuture return type |
| `com.barclaycard.digital:common-context` | `1.3.0` | `2.0.4` | Package namespace updates, potential class renames | Jakarta EE namespace migration (javax → jakarta); Java 17+ compatibility |
| `com.barclaycard.digital:executor-core` | `1.1.1` | `2.0.0` | API changes for concurrent execution patterns | Java 21 concurrent APIs; CompletableFuture-based operations |
| `com.barclaycard.digital:common-filter` | `4.1.0` | `5.0.3` | Bootstrap class inheritance changed | SDK3-compatible bootstrap classes; Different parent class hierarchy |
| `com.barclaycard.digital:core-jsonapi-web` | `4.4.1` | `5.2-001` | Spring Framework 6.x API updates | Spring Framework 6.2.11 compatibility; Response pattern changes |

**build.gradle Dependency Declaration (SDK3):**

```gradle
// SDK3: Account query repository with async pattern
// ✅ This JAR contains the NEW AccountCard* classes (AccountCardQueryRepository, etc.)
implementation('com.barclaycard.digital:system-qry-cardholder-account-runtime:10.1-000')

// SDK3: Common context library (Jakarta EE, Java 17+ compatible)
// Upgraded from 1.3.0 (SDK2) to 2.0.4 (SDK3) - Jakarta EE namespace
implementation 'com.barclaycard.digital:common-context:2.0.4'

// SDK3: Executor core (Java 21 concurrent APIs)
// Upgraded from 1.1.1 (SDK2) to 2.0.0 (SDK3) - Java 21 concurrent APIs
implementation 'com.barclaycard.digital:executor-core:2.0.0'

// SDK3: Common filter (SDK3-compatible bootstrap classes)
implementation 'com.barclaycard.digital:common-filter:5.0.3'

// SDK3: JSON API web (Spring Framework 6.x compatible)
// Upgraded from 4.4.1 (SDK2) to 5.2-001 (SDK3) - Spring Framework 6.x compatible
implementation 'com.barclaycard.digital:core-jsonapi-web:5.2-001'
```

**Key Points:**

1. **com.barclaycard.digital:system-qry-cardholder-account-runtime:10.1-000** (PRIMARY SOURCE)
   - This is the JAR providing `AccountCardQueryRepository`, `AccountCardRequest`, `AccountCardResponse`
   - Introduced in SDK3 with brand new "Card" naming convention
   - Methods return `CompletableFuture<T>` (async pattern)
   - Replaces older SDK2 `system-qry-account*` libraries

2. **Version Jump Significance:**
   - `10.1-000` indicates SDK3 release (first release with "000" suffix)
   - Major version 10 suggests significant API restructuring
   - All methods are non-blocking async (CompletableFuture-based)

3. **Cascading Impacts:**
   - Any code depending on old `AccountQuery*` classes must update ALL references
   - Test frameworks must handle CompletableFuture mocks
   - Constructor injection qualifiers must match new bean names

4. **Finding the Source JAR:**
   ```bash
   # Extract JAR to inspect class files
   jar -xf system-qry-cardholder-account-runtime-10.1-000.jar

   # Find the account repository classes
   find . -name "*AccountCard*" -type f

   # Expected results:
   # com/barclaycard/digital/account/repository/AccountCardQueryRepository.class
   # com/barclaycard/digital/account/repository/AccountCardRequest.class
   # com/barclaycard/digital/account/repository/AccountCardResponse.class

   # Verify async pattern
   javap -c com/barclaycard/digital/account/repository/AccountCardQueryRepository.class | grep CompletableFuture
   # Expected: CompletableFuture<AccountCardResponse> find(AccountCardRequest)
   ```

**Migration Impact by Dependency:**

- ✅ **system-qry-cardholder-account-runtime:10.1-000** - REQUIRED: Update all class references
- ✅ **common-context:2.0.4** - RECOMMENDED: Handles Jakarta EE auto-configuration
- ✅ **executor-core:2.0.0** - REQUIRED: Provides CompletableFuture execution context
- ✅ **common-filter:5.0.3** - REQUIRED: Prevents BeanDefinitionStoreException (Card 7)
- ✅ **core-jsonapi-web:5.2-001** - RECOMMENDED: Spring Framework 6.x compatible response patterns

### Related Concepts

**Async/Sync Patterns in Java:**
- `CompletableFuture<T>` - Non-blocking async computation
- `.join()` - Blocks until result available (synchronous wait)
- Mock with `when().thenReturn(CompletableFuture.completedFuture())` - Pre-completed future for testing
- Thread pool implications - `.join()` holds thread while waiting

**Repository Pattern Evolution:**
- SDK2: Synchronous repository interface
- SDK3: Asynchronous repository interface using CompletableFuture
- Allows non-blocking I/O and better thread utilization

**Bean Qualifier Importance:**
- Matches constructor injection by name
- Must match bean name in Spring context
- Prevents injection ambiguity when multiple beans exist

### References

- **CompletableFuture Java Documentation**: [Oracle CompletableFuture](https://docs.oracle.com/javase/8/docs/api/java/util/concurrent/CompletableFuture.html)
- **Async Programming in Spring**: [Spring Async Guide](https://spring.io/guides/gs/async-method/)
- **Mockito CompletableFuture Testing**: [Mockito Documentation](https://javadoc.io/doc/org.mockito/mockito-core/latest/org/mockito/Mockito.html)
- **Spring Boot 3 SDK3 Migration**: [Spring Boot 3 Migration Guide](https://spring.io/blog/2023/01/31/spring-boot-3-migration-guide)
- **Repository Pattern**: [Martin Fowler - Repository Pattern](https://martinfowler.com/eaaCatalog/repository.html)

---

## Complete build.gradle Configuration Summary

### Header Configuration
```gradle
// SDK3: Exclude conflicting logging modules
configurations {
    //excluded due to slf4j conflict (api-core-boot resolves the required logger implementation)
    all*.exclude module: 'spring-boot-starter-logging'
    all*.exclude module: 'logback-classic'
    all*.exclude module: 'slf4j-simple'

    //SDK3: Exclude SDK2 artifacts
    all*.exclude module: 'api-core-boot'

    //Exclude old SLF4J 1.x bridge, use SLF4J 2.x bridge instead
    all*.exclude module: 'log4j-slf4j-impl'
}

// Version pins for security and CVE remediation
ext['log4j2.version']='2.23.1'           // BUKMULE-2254, BUKMULE-2775
ext['tomcat.version'] = '10.1.44'        // CVE-2025-24813
ext['netty.version'] = '4.1.125.Final'
ext['spring-framework.version'] = '6.2.11'
```

### Dependencies Section (Logging)
```gradle
//Adding dependency to have ECS Template for JSON logging
implementation ("org.apache.logging.log4j:log4j-layout-template-json")

//SLF4J 2.x bridge for Log4j2 (replaces old log4j-slf4j-impl for SLF4J 1.x)
implementation 'org.apache.logging.log4j:log4j-slf4j2-impl:2.23.1'

// Override with pinned log4j version
implementation 'org.apache.logging.log4j:log4j:2.0'
```

---

## Troubleshooting Guide

### Error: Multiple SLF4J bindings
```
Symptom: SLF4J: Class path contains multiple SLF4J bindings
Solution: Run ./gradlew dependencies and remove conflicting binding
          Ensure log4j-slf4j-impl is excluded in configurations block
```

### Error: Logger not initialized
```
Symptom: No appenders found or logging not working
Solution: Check log4j2.xml is in src/main/resources/
          Verify log4j-slf4j2-impl is present
          Confirm spring-boot-starter-logging is excluded
```

### Error: ClassNotFoundException for Tomcat
```
Symptom: java.lang.ClassNotFoundException: org.apache.catalina...
Solution: Ensure tomcat-embed-* dependencies are included with version 10.1.44
          Check for transitive older versions: ./gradlew dependencies
```

### Error: Spring Framework version mismatch
```
Symptom: NoClassDefFoundError for org.springframework classes
Solution: Verify spring-framework.version = '6.2.11' in build.gradle
          Don't override spring-web version - let BOM manage it
```

### Error: BeanDefinitionStoreException: DefaultFilterBootstrap
```
Symptom: org.springframework.beans.factory.BeanDefinitionStoreException
         I/O failure while processing configuration class
         [com.barclaycard.digital.filter.bootstrap.DefaultFilterBootstrap]

Root Cause: common-filter:4.1.0 (SDK2) contains DefaultFilterBootstrap extending SDK2 classes
            that are excluded from classpath (api-core-boot excluded in build.gradle line 42)
            Spring discovers the class during component scanning but cannot load its parent

Solution: Upgrade common-filter to 5.0.3 (SDK3-compatible version)
          Change: implementation 'com.barclaycard.digital:common-filter:4.1.0'
          To:     implementation 'com.barclaycard.digital:common-filter:5.0.3'

Verify: Run: ./gradlew bootJar && java -jar ./build/libs/app.jar
        Expected: Successful startup, no BeanDefinitionStoreException
        Check logs for: "No active profile set" or "Started Application"
```

### Error: Build execution hangs or times out
```
Symptom: Build hangs indefinitely without progress
         Eventually times out or fails with generic gradle error
         Build works in some environments but not others

Root Cause: cyclonedxBom task running during build
            Task attempts to download external RAML specifications from network
            Network access may be restricted or very slow in build environment

Solution: Disable cyclonedxBom task in build.gradle
          Add at end of build.gradle:
          tasks.named('cyclonedxBom').configure {
              enabled = false
          }

Verify: 1. Check Gradle task list: ./gradlew tasks --all | grep cyclone
           Expected: No cyclonedxBom in output
        2. Full build: ./gradlew build
           Expected: Completes without network timeouts
        3. Verify output: BUILD SUCCESSFUL message appears
```

### Error: Build hangs on RAML spec download or network timeout
```
Symptom: Build task 'cyclonedxBom' executing
         Waiting for network resources (RAML specs)
         Connection timeout after several minutes
         or: java.net.ConnectException or java.net.UnknownHostException

Root Cause: Optional SBOM generation task (cyclonedxBom) depends on network resources
            Network may be unavailable, slow, or blocked by proxy in your environment
            Task is not required for code compilation or JAR generation

Solution: Disable cyclonedxBom in build.gradle (see above)
          Or skip task: ./gradlew build -x cyclonedxBom
          Or run specific tasks: ./gradlew compileJava bootJar

Verify: ./gradlew build
        Expected: Completes without network errors or timeouts
        Expected: app.jar created in build/libs/
```

---

## Quick Reference - All Version Pins

> **Cross-Reference:** For comprehensive version mappings, see:
> - [Barclays Internal Libraries — Versions](../reference/barclays_internal_libraries_versions.md) - 600+ Barclays libraries
> - [Dependency Versions](../reference/third_party_dependencies.md) - Third-party dependencies

| Component | Version | Reason |
|-----------|---------|--------|
| `log4j2` | 2.23.1 | Security: BUKMULE-2254, BUKMULE-2775 |
| `spring-framework` | 6.2.11 | Spring Boot 3.5.7 requirement; Jakarta EE (jakarta.servlet) |
| `tomcat` | 10.1.44 | Security: CVE-2025-24813 |
| `netty` | 4.1.125.Final | Async I/O stability |
| `common-filter` | 5.0.3 | SDK3 compatibility (replaces 4.1.0 SDK2 version) |
| `spring-web` | **REMOVED** | ❌ Remove SDK2 version (5.3.34 with javax.servlet) |
| `hibernate-validator` | BOM-managed | ✅ Use SDK3 BOM version (NOT 6.2.2.Final) |
| `jakarta.validation-api` | BOM-managed | ✅ Added for Jakarta EE (replaces javax.validation) |
| `spring-boot` | 3.5.7 | SDK3 migration |
| `java` | 21 | SDK3 migration |

## Quick Reference - Gradle Tasks Configuration

| Task | Status | Reason |
|------|--------|--------|
| `cyclonedxBom` | ❌ **DISABLED** | Optional SBOM generation; Network issues downloading RAML specs |
| `barclaysApiGenerate` | ❌ **DISABLED** | Optional API generation; Not required for SDK3 build |
| `compileJava` | ✅ Enabled | Required for compilation |
| `bootJar` | ✅ Enabled | Required for JAR generation |
| `build` | ✅ Enabled | Full build (after disabling optional tasks) |

---

## Common Issues & Solutions Matrix

| Error | Card | Root Cause | Solution |
|-------|------|-----------|----------|
| `BeanDefinitionStoreException: DefaultFilterBootstrap` | Card 7 | common-filter:4.1.0 (SDK2) extends excluded classes | Upgrade common-filter to 5.0.3 (SDK3-compatible) |
| `Multiple SLF4J bindings detected` | Card 1 | Both `log4j-slf4j-impl` and `log4j-slf4j2-impl` | Exclude `log4j-slf4j-impl` in configurations |
| `Logger not initialized` | Card 2 | `spring-boot-starter-logging` pulled in | Exclude `spring-boot-starter-logging`, `logback-classic`, `slf4j-simple` |
| `CVE detected` | Card 3,5 | Vulnerable dependency versions | Pin versions: log4j2 2.23.1, tomcat 10.1.44 |
| `Spring version mismatch` | Card 4 | Spring 5.x with Spring Boot 3.x | Set `spring-framework.version = 6.2.11` |
| `NoClassDefFoundError: javax/servlet/ServletRequest` | Card 8 | Explicit Spring Web 5.3.34 override | Remove `org.springframework:spring-web:5.3.34`, let BOM provide Spring 6.2.11 |
| `Jakarta vs javax namespace conflict` | Card 8 | Mixed javax.* and jakarta.* dependencies | Remove explicit version pins, use SDK3 BOM management |
| `Build hangs or times out` | Card 9 | cyclonedxBom task network timeout | Disable: `tasks.named('cyclonedxBom').configure { enabled = false }` |
| `Build hangs on RAML spec download` | Card 9 | cyclonedxBom network dependency | Disable cyclonedxBom; use `./gradlew compileJava bootJar` instead |
| `ConnectException or UnknownHostException in build` | Card 9 | Optional tasks requiring network access | Disable optional tasks; they're not required for deployment |

---

## Checklist for SDK3 Migration & Log4j Configuration

### Logging Configuration
- [ ] `spring-boot-starter-logging` excluded in configurations
- [ ] `logback-classic` excluded in configurations
- [ ] `log4j-slf4j-impl` excluded in configurations
- [ ] `log4j-slf4j2-impl:2.23.1` present in dependencies
- [ ] `log4j-layout-template-json` added for ECS logging
- [ ] `log4j2.version` set to 2.23.1 in ext

### Version Pinning
- [ ] `tomcat.version` set to 10.1.44
- [ ] `netty.version` set to 4.1.125.Final
- [ ] `spring-framework.version` set to 6.2.11
- [ ] Tomcat embed modules use `strictly` version constraint
- [ ] No explicit `spring-web` version override
- [ ] No explicit `spring-web:5.3.34` dependency in build.gradle
- [ ] `org.springframework:spring-web:5.3.34` removed (SDK2 version)

### Jakarta EE & Namespace Migration (Card 8)
- [ ] No `javax.servlet` dependencies on classpath (verify with `./gradlew dependencies`)
- [ ] `jakarta.servlet` present via Spring Framework 6.2.11
- [ ] `jakarta.validation:jakarta.validation-api` added to dependencies
- [ ] `org.hibernate.validator:hibernate-validator` version NOT pinned (uses SDK3 BOM)
- [ ] No explicit `hibernate-validator:6.2.2.Final` (SDK2 with javax.validation)
- [ ] No `javax.validation` imports in code (only `jakarta.validation`)

### Gradle Tasks Configuration (Card 9)
- [ ] `cyclonedxBom` task disabled: `tasks.named('cyclonedxBom').configure { enabled = false }`
- [ ] `barclaysApiGenerate` task disabled: `tasks.named('barclaysApiGenerate').configure { enabled = false }`
- [ ] Optional tasks do NOT appear in: `./gradlew tasks --all`
- [ ] Build completes without network timeouts or hangs
- [ ] Build execution completes without gradle hangs
- [ ] JAR generation works without cyclonedxBom task running
- [ ] SBOM generation disabled (not required for deployment)

### Bootstrap Configuration (SDK3 Migration)
- [ ] `api-core-boot` excluded in configurations (line 42)
- [ ] No `@Configuration` classes import SDK2 bootstrap classes
- [ ] `InternalApiInitializerConfig.java` contains no `@Bean` definitions
- [ ] `bap-bld-lib-plugin` is applied (line 2 of build.gradle)
- [ ] No commented-out SDK2 bean definitions remain in config classes

### Build & Runtime Verification
- [ ] Build completes with `./gradlew compileJava` successfully
- [ ] Boot JAR builds with `./gradlew bootJar` successfully
- [ ] No warnings about multiple SLF4J bindings in build output
- [ ] Application starts without `BeanDefinitionStoreException`
- [ ] No `DefaultFilterBootstrap` errors in startup logs
- [ ] Application logs are produced when running locally
- [ ] Spring profile successfully initializes: "No active profile set"
- [ ] No `NoClassDefFoundError: javax/servlet/ServletRequest` at runtime (Card 8)
- [ ] No javax.servlet on classpath: `./gradlew dependencies` shows NO javax.servlet
- [ ] Application starts and runs without ClassNotFoundException for servlet/validation classes
- [ ] Build executes without hangs or timeouts (Card 9)
- [ ] No `cyclonedxBom` task execution in build logs (Card 9)
- [ ] Build completes in reasonable time without RAML spec download attempts (Card 9)
- [ ] No network timeout errors in build output (Card 9)
- [ ] `./gradlew tasks --all` does NOT show cyclonedxBom task (Card 9)

---

## Related Documentation

- **SDK2 to SDK3 Migration**: See `/skills/sdk2_sdk3_migration/lessons_learnt.md`

---

**Document Version:** 1.7
**Last Updated:** 2026-01-12 (removed IDE-specific content per standards)
**Project Team:** Cards API Development

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.7 | 2026-01-12 | Removed IDE-specific tasks and content from Card 9; Removed "Step 3: Test IntelliJ Execution" verification steps; Removed IDE-specific troubleshooting sections; Updated scenarios to be environment-agnostic; Removed IntelliJ references from checklist items; Updated card title from "IntelliJ Runtime Issues" to "Build Network Timeout Issues"; Removed IDE-specific instructions from Alternative Solutions; Updated Root Causes to remove IDE execution context; Generalized content to focus on build system and network configuration |
| 1.6 | 2026-01-08 | Updated Card 11: Added JAR/Library Details section documenting where breaking class name changes are introduced; Identified primary source: `com.barclaycard.digital:system-qry-cardholder-account-runtime:10.1-000` (contains AccountCard* classes); Added dependency upgrade matrix showing SDK2→SDK3 versions; Included build.gradle dependency declarations with explanations; Added key points about version jump significance (10.1-000 indicates SDK3 release); Included JAR inspection commands to verify async pattern; Added migration impact by dependency section |
| 1.5 | 2026-01-08 | Added Card 11: SDK2/SDK3 Breaking Class Name Changes (Async Repository Pattern); Documented class renames: AccountQueryRepository→AccountCardQueryRepository, AccountRequest→AccountCardRequest, AccountResponse→AccountCardResponse; Detailed CompletableFuture async/sync conversion pattern with .join(); Included 6 affected files (1 main + 5 tests); Added comprehensive mock setup patterns for async returns; Documented cascading effects across test suite; Added side-by-side SDK2 vs SDK3 comparisons; Included 5 common migration errors with fixes; Added bean qualifier pattern changes |
| 1.4 | 2026-01-06 | Added Card 9: CycloneDX BOM Task Failure and IntelliJ Runtime Issues; Documented cyclonedxBom network timeout problem; Added Impact Analysis table; Added Alternative Solutions; Included Common Scenarios; Added Gradle Tasks Configuration checklist; Added Troubleshooting entries for IntelliJ hangs and network timeouts; Updated Quick Reference with Gradle Tasks table |
| 1.3 | 2026-01-06 | Added Card 8: Spring Web SDK2 Version Conflict and Jakarta EE Migration; Documented NoClassDefFoundError: javax/servlet/ServletRequest issue; Added Common Issues matrix entries for javax vs jakarta namespace conflicts; Added Jakarta EE & Namespace Migration checklist section; Added verification items for servlet/validation class loading |
| 1.2 | 2026-01-05 | Enhanced Card 7: Added primary fix for common-filter 5.0.3 upgrade; Added secondary fix for custom ComponentScan filter; Added common-filter version compatibility matrix; Documented root cause and migration path |
| 1.1 | 2026-01-05 | Added Card 7: SDK2/SDK3 Bootstrap Configuration Conflict; Updated checklist with bootstrap verification items; Added common issues matrix |
| 1.0 | 2025-12-24 | Initial release: Cards 1-6 covering Log4j, Spring Framework, Tomcat, and Netty configuration |
