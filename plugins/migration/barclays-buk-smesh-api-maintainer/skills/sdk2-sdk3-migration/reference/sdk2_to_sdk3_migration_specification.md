# SDK2 to SDK3 Migration Specification

> **AGENT NOTE:** This file is under 2000 lines. Section 3.3 contains dependency REMOVE rules referenced by most agents.

## Executive Summary

This document provides a comprehensive migration guide for converting a Barclays Internal API project from SDK2 (api-bom 2.15.1.1) to SDK3 (1.12.007). The migration involves changes to build configuration, Java version, test framework, core libraries, and API patterns.

**Based on Analysis of:**
- Source: `accountentries-iapi` (SDK2)
- Target: `accountentries-iapi_sdk3` (SDK3)

---

## 1. Build Configuration Changes (build.gradle)

### 1.1 Plugins Changes

#### SDK2 Plugins:
```gradle
apply plugin: 'java'
apply plugin: 'maven-publish'
apply plugin: 'eclipse'
apply plugin: 'eclipse-wtp'
apply plugin: 'idea'
apply plugin: 'jacoco'
apply plugin: 'org.springframework.boot'
apply plugin: 'org.owasp.dependencycheck'
apply plugin: 'io.spring.dependency-management'
```

#### SDK3 Plugins:
```gradle
apply plugin: 'java'
apply plugin: 'com.barclays.api.bap-bld-lib-plugin'  // NEW SDK3 PLUGIN
```

**Migration Actions:**
- Remove: `maven-publish`, `eclipse`, `eclipse-wtp`, `idea`, `jacoco`, `org.owasp.dependencycheck`, `io.spring.dependency-management`
- Add: `com.barclays.api.bap-bld-lib-plugin` (SDK3 custom plugin)
- Remove dependency management plugin (handled by SDK3 plugin)

---

### 1.1a Repositories Configuration (IMPORTANT)

#### SDK2:
Repositories were defined in buildscript block or external gradle files

#### SDK3:
```gradle
repositories {

    //
    //Public repositories
    //
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays/'
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/repositories/barclaysint-group'
    }
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/buk-maven2-group/'
    }

    def nexusUser = readProperty("nexusUsername")
    def nexusPassword = readProperty("nexusPassword")

    if (!nexusUser || !nexusPassword) {
        logger.warn('Nexus credentials are missing or incomplete.  Any restricted access repositories will not be included.')
    } else {
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/iAPIs_RELEASE/'
            credentials {
                username nexusUser
                password nexusPassword
            }
        }
        maven {
            url 'https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/'
            credentials {
                username nexusUser
                password nexusPassword
            }
        }
    }
}


//////////////////////////////////////
//           Functions              //
//////////////////////////////////////
def readProperty(String property){
    String sysValue = System.env.get(property);
    if (sysValue != null) {
        return sysValue;
    }
    if (project.hasProperty(property)) {
        return project.property(property);
    }
    return null;
}
```

**Migration Actions:**
- Add repositories block after plugins and before compiler settings
- Include Barclays Nexus repository for SDK3 dependencies
- Do NOT include mavenCentral() or gradlePluginPortal() (BANNED per project policy) - use only Barclays Nexus repositories

---

### 1.2 Gradle Common Files

#### SDK2 Common Files:
```
gradle/common/integrationtest.gradle
gradle/common/wiremock.gradle
gradle/common/jacoco.gradle
gradle/common/repositoryconfig.gradle
gradle/common/jarconfig.gradle
gradle/common/validation.gradle
gradle/common/genkerberostoken.gradle
```

#### SDK3 Common Files:
```
(none — ALL gradle/common/ files are deleted in SDK3)
```

**Migration Actions:**
- **Delete the entire `gradle/common/` directory without exception** — `rm -rf gradle/common`. Do NOT migrate any content from these files into `build.gradle`. The `bap-bld-lib-plugin` replaces all functionality previously in `gradle/common/`; nothing needs to be preserved.

---

### 1.2a Gradle Wrapper Configuration (CRITICAL)

> **Implementation Guide:** For step-by-step instructions, see `sdk2_sdk3_gradle` skill, Part 1.

#### SDK2 - gradle-wrapper.properties:
```properties
distributionUrl=https\://services.gradle.org/distributions/gradle-7.x.x-bin.zip
```

#### SDK3 - gradle-wrapper.properties (Barclays Internal):
```properties
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip
```

**Migration Actions:**
- Update Gradle wrapper to version 8.13 or higher (required for Java 21 and Spring Boot 3)
- Use Barclays Nexus URL for Gradle distribution: `https://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip`
- SDK3 requires Gradle 8+ for compatibility with:
  - Java 21 toolchain support
  - Spring Boot 3.x
  - Jakarta EE 9+ namespace changes
  - Modern Gradle API (archiveFileName vs archiveName)

**To update manually:**
Edit `gradle/wrapper/gradle-wrapper.properties`:
```properties
distributionUrl=https\://nexus.barcapint.com/nexus/content/groups/barclays/gradle-8.13-bin.zip
```

---

### 1.2b Gradle 8 Deprecated Property Changes

Gradle 8 deprecates several property names used in build scripts. These must be updated for SDK3 compatibility.

#### Report Configuration Properties

##### SDK2 (Gradle 7 - Deprecated):
```gradle
// JaCoCo, Checkstyle, or other report configurations
xml.enabled = true
csv.enabled = false
html.enabled = true
xml.destination = file("${buildDir}/reports/jacoco.xml")
html.destination = file("${buildDir}/reports/html")
```

##### SDK3 (Gradle 8 - Required):
```gradle
// Updated property names
xml.required = true
csv.required = false
html.required = true
xml.outputLocation = file("${buildDir}/reports/jacoco.xml")
html.outputLocation = file("${buildDir}/reports/html")
```

#### Archive Properties

##### SDK2 (Gradle 7 - Deprecated):
```gradle
task wiremockStub(type: Zip) {
    archiveName 'app-stub.zip'
}
```

##### SDK3 (Gradle 8 - Required):
```gradle
task wiremockStub(type: Zip) {
    archiveFileName = 'app-stub.zip'
}
```

#### Feature Previews to Remove

These feature previews are now default in Gradle 8 and must be removed from `settings.gradle`:

##### SDK2 settings.gradle:
```gradle
enableFeaturePreview('ONE_LOCKFILE_PER_PROJECT')
enableFeaturePreview('VERSION_ORDERING_V2')
enableFeaturePreview('VERSION_CATALOGS')
```

##### SDK3 settings.gradle:
```gradle
// Remove all enableFeaturePreview lines - these are now default behavior
rootProject.name = 'your-project-name'
```

**Migration Actions:**
- Replace `xml.enabled` with `xml.required` in all gradle files
- Replace `csv.enabled` with `csv.required` in all gradle files
- Replace `html.enabled` with `html.required` in all gradle files
- Replace `xml.destination` with `xml.outputLocation` in all gradle files
- Replace `csv.destination` with `csv.outputLocation` in all gradle files
- Replace `html.destination` with `html.outputLocation` in all gradle files
- Replace `archiveName` with `archiveFileName` in all gradle files
- Remove all `enableFeaturePreview` lines from settings.gradle

---

### 1.3 Java Version

#### SDK2:
```gradle
sourceCompatibility = JavaVersion.VERSION_1_8
targetCompatibility = JavaVersion.VERSION_1_8
```

#### SDK3:
```gradle
java {
    toolchain {
        languageVersion = JavaLanguageVersion.of(21)
    }
}
```

**Migration Actions:**
- Change from Java 8 to Java 21
- Use modern `java.toolchain` configuration
- Update `.java-version` file: `8` → `21`

---

### 1.4 Dependency Management

#### SDK2 - BOM Dependency:
```gradle
dependencyManagement {
    imports {
        mavenBom 'com.barclays.api.emm:api-bom:2.15.1.1'
    }
}
```

#### SDK3 - Platform BOM:
```gradle
dependencies {
    implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))
}
```

**Migration Actions:**
- Remove `dependencyManagement` block
- Add SDK3 platform BOM as a dependency
- SDK3_VERSION should be in gradle.properties (e.g., `1.12.007`)

---

### 1.5 Configuration Exclusions

#### SDK2:
```gradle
configurations {
    all*.exclude module: 'spring-boot-starter-logging'
    all*.exclude module: 'logback-classic'
    all*.exclude module: 'slf4j-simple'
}
```

#### SDK3:
```gradle
configurations {
    all*.exclude module: 'spring-boot-starter-logging'
    all*.exclude module: 'logback-classic'
    all*.exclude module: 'api-core-boot'  // NEW EXCLUSION
    all*.exclude module: 'slf4j-simple'
}
```

**Migration Actions:**
- Add exclusion for `api-core-boot` (replaced by SDK3 libraries)

---

### 1.6 Version Overrides

#### SDK2:
```gradle
ext['tomcat.version'] = '9.0.90'
```

#### SDK3:
```gradle
ext['tomcat.version'] = '10.1.44'
ext['netty.version'] = '4.1.125.Final'
ext['spring-framework.version'] = '6.2.11'
```

**Migration Actions:**
- Update Tomcat version: `9.0.90` → `10.1.44` (for Jakarta EE 9+)
- Add Netty version override: `4.1.125.Final`
- Add Spring Framework version: `6.2.11` (Spring Boot 3.x uses Spring 6)

---

### 1.7 API Generation Task Configuration

#### Overview

The `barclaysApiGenerate` task is part of the SDK3 plugin (`com.barclays.api.bap-bld-lib-plugin`) and generates API code from RAML specifications. During development and testing, you may want to disable this task to avoid regenerating API code unnecessarily.

#### Disabling API Generation (Optional)

**Option 1: Disable in build.gradle (Global)**

```gradle
tasks.named('barclaysApiGenerate').configure {
    enabled = false
}
```

**Option 2: Skip via Command Line (Per Execution)**

```bash
# Compile without regenerating API
$GRADLE_CMD compileJava -x barclaysApiGenerate

# Compile tests without regenerating API
$GRADLE_CMD compileTestJava -x barclaysApiGenerate

# Run tests without regenerating API
$GRADLE_CMD test -x barclaysApiGenerate

# Full build without regenerating API
$GRADLE_CMD build -x barclaysApiGenerate
```

#### When to Disable

**Recommended to disable during:**
- Test development and execution
- Code compilation during active development
- CI/CD builds where API has already been generated
- When API specification hasn't changed

**Keep enabled when:**
- RAML files have been modified
- Initial project setup
- Updating API contracts
- Publishing new API versions

---

### 1.8 Test Configuration

#### SDK2:
```gradle
test {
    include 'com/**/*MockTest.class'
    exclude 'com/**/*RealTest.class'
}
```

#### SDK3:
```gradle
tasks.named('test') {
    useJUnitPlatform()  // NEW - Required for JUnit 5
    include 'com/**/*MockTest.class'
    exclude 'com/**/*RealTest.class'
}
```

**Migration Actions:**
- Add `useJUnitPlatform()` to enable JUnit 5 (Jupiter)
- Use `tasks.named('test')` instead of direct `test` block

---

### 1.9 Buildscript Dependencies

#### SDK2:
```gradle
buildscript {
    ext {
        springBootVersion = '2.7.18'
    }
    dependencies {
        classpath "io.spring.gradle:dependency-management-plugin"
        classpath("org.springframework.boot:spring-boot-gradle-plugin:${springBootVersion}")
        classpath 'org.owasp:dependency-check-gradle:7.0.0'
    }
}
```

#### SDK3:
```gradle
buildscript {
    dependencies {
        classpath "info.solidsoft.gradle.pitest:gradle-pitest-plugin:1.15.0"
    }
}
```

**Migration Actions:**
- Remove Spring Boot plugin classpath (handled by SDK3 plugin)
- Remove dependency management plugin
- Remove OWASP dependency check (not yet supported in SDK3)
- Add PIT mutation testing plugin

---

### 1.9 Sonar Configuration

#### SDK2:
- No sonar configuration in build.gradle

#### SDK3:
```gradle
sonar {
    properties {
        property("sonar.projectKey", "${SONAR_PROJECT_NAME}")
        property("sonar.host.url", "https://sonarqube02.barcapint.com")
        property("sonar.sourceEncoding", "UTF-8")
        property("sonar.language", "java")
        property("sonar.sources", "src/main/java")
        property("sonar.tests", "src/test/java")
        property("sonar.exclusions", "**/Test*.java,**/*Spec*.groovy")
        property("sonar.coverage.jacoco.xmlReportPaths", "build/reports/jacoco/test/jacocoTestReport.xml")
        property("sonar.projectVersion", "${version}")
        property("sonar.java.binaries", "build/classes/")
        property("sonar.verbose", true)
        property("sonar.java.coveragePlugin", "jacoco")
        property("sonar.projectName", "${SONAR_PROJECT_NAME}")
        property("sonar.coverage.exclusions", "${jacocoCoverageExclusions}")
        property("sonar.projectBaseDir", "${rootDir}")
    }
}
```

**Migration Actions:**
- Add sonar configuration block to build.gradle
- Define `jacocoCoverageExclusions` in gradle.properties

---

## 2. Gradle Properties (gradle.properties)

### SDK2:
```properties
GROUP_ID=com.barclays.iapi.branchaccounts
VERSION=1.1.2
ARTIFACT_ID=accountentries-iapi
IMPLEMENTATION_TITLE=Account Entries Process API
API_BASE_TEMPLATE=2.15
SONAR_PROJECT_NAME=BUK::TC14::accountentries-iapi::APPL018596::CI1343090251
VERACODE_PROFILE_NAME=APPL018596_PBPAPIS.accountentriesiapi
```

### SDK3:
```properties
GROUP_ID=com.barclays.iapi.branchaccounts
VERSION=1.1.2
ARTIFACT_ID=accountentries-iapi
IMPLEMENTATION_TITLE=Account Entries Process API

# SDK3 Configuration
GLOBAL_VERSION=1.1.2
SDK3_VERSION=1.12.007

# Legacy (kept for reference)
API_BASE_TEMPLATE=2.15

# Sonar Configuration
SONAR_PROJECT_NAME=BUK::TC14::accountentries-iapi::APPL018596::CI1343090251

# Veracode Configuration (updated for SDK3)
VERACODE_APP_ID=APPL018596
VERACODE_CREDENTIALS_ID=VeracodeCredentials

# Jacoco Coverage Exclusions
jacocoCoverageExclusions=**/Application.class,**/config/**,**/filter/**,**/helper/ApplicationConstant.class
```

**Properties to DELETE (obsolete in SDK3):**
- `API_BASE_TEMPLATE_VERSION` - No longer used in SDK3
- `RAML_BUILD_NUMBER` - RAML replaced by OpenAPI
- `GENERATE_CODE_FROM_RAML` - RAML replaced by OpenAPI
- `RAML_BASE_PACKAGE` - RAML replaced by OpenAPI

**Properties to ADD (required for SDK3):**
- `GLOBAL_VERSION` - Version for all modules
- `SDK3_VERSION` - SDK3 platform version (e.g., `1.12.007`)
- `DISABLE_OAS_GENERATION=true` - Disable OpenAPI generation if not needed
- `GROUP_ID` - Maven group ID if not present
- `root.spec.url` - OpenAPI spec URL (if using OAS generation)
- `root.spec.filename=openApiSpecs.yaml` - OpenAPI spec filename
- `SANDBOX_WIREMOCK_STARTUP_ARGS=` - WireMock startup arguments

**Migration Actions:**
- Delete obsolete RAML-related properties
- Add `GLOBAL_VERSION` property
- Add `SDK3_VERSION` property (e.g., `1.12.007`)
- Add `DISABLE_OAS_GENERATION=true` if not using OpenAPI generation
- Update Veracode configuration (remove PROFILE_NAME, add APP_ID and CREDENTIALS_ID)
- Add `jacocoCoverageExclusions` for Sonar integration

---

## 3. Core Library Dependencies

### 3.1 SDK2 Core Libraries

```gradle
// API core
implementation 'com.barclays.api:api-core-boot'
// API Core Properties
implementation 'com.barclays.api:api-core-properties'
// RAML Request validator tool dependency
implementation 'com.barclays.api.tools:api-request-validator'
// GIS SDK Wrapper
implementation 'com.barclays.api.tools:gissdk-filters-wrapper'
// API Mesh Client Connector
implementation 'com.barclays.api:api-mesh-client-connector'
```

### 3.2 SDK3 Core Libraries

```gradle
// SDK3 Platform BOM
implementation(platform("com.barclays.api:sdk3:${SDK3_VERSION}"))

// SDK3 Core Libraries
implementation 'com.barclays.api:bap-bld-lib-request-validator'
implementation 'com.barclays.api:bap-bld-lib-restapi'
implementation 'com.barclays.api:bap-bld-lib-meshconnector'
implementation 'commons-io:commons-io:2.16.1'
```

### 3.3 SDK2 Dependencies That MUST BE REMOVED

These SDK2 dependencies are **obsolete** and must be completely removed from build.gradle:

| SDK2 Dependency (REMOVE) | Reason | SDK3 Replacement |
|--------------------------|--------|------------------|
| `com.barclays.api:api-core-boot` | Obsolete in SDK3 | Managed by SDK3 BOM |
| `com.barclays.api:api-core-utils` | Obsolete in SDK3 | Managed by SDK3 BOM |
| `com.barclays.api:api-core-properties` | Obsolete in SDK3 | Use `com.barclays.api:bap-bld-lib-common` |
| `com.barclays.api:api-mesh-client-connector` | Old SDK2 connector | Use `com.barclays.api:bap-bld-lib-meshconnector` |
| `com.barclays.api.tools:gissdk-filters-wrapper` | SDK2-specific tool | Not needed in SDK3 |
| `com.barclays.api.tools:api-request-validator` | Old validator | Use `com.barclays.api:bap-bld-lib-request-validator` |
| `com.sun.jersey:jersey-core` | Old JAX-RS 1.x | Not needed in SDK3 |

### 3.4 SDK3 Dependency Mapping

| SDK2 Library | SDK3 Replacement | Notes |
|-------------|------------------|-------|
| `api-core-boot` | ❌ Removed | Managed by SDK3 BOM |
| `api-core-utils` | ❌ Removed | Managed by SDK3 BOM |
| `api-core-properties` | `bap-bld-lib-common` | Via SDK3 BOM |
| `api-request-validator` | `bap-bld-lib-request-validator` | Direct replacement |
| `gissdk-filters-wrapper` | ❌ Removed | Security handled differently in SDK3 |
| `api-mesh-client-connector` | `bap-bld-lib-meshconnector` | Direct replacement |
| N/A | `bap-bld-lib-restapi` | New library for REST operations |
| N/A | `commons-io:commons-io:2.16.1` | Explicitly required in SDK3 |

### 3.5 Dependency Migration Workflow

When migrating build.gradle dependencies, process in this order:

1. **REMOVE** obsolete SDK2 dependencies (Section 3.3)
2. **MODIFY** group-specific dependencies that need groupId/artifactId/version changes (from `barclays_internal_libraries_{group}.md`)
3. **ADD** new SDK3 libraries not covered by SDK3 BOM
4. **VERIFY** no duplicates — always replace existing entries, never add alongside old ones

---

## 4. Test Dependencies (JUnit 4 → JUnit 5)

### 4.1 SDK2 Test Dependencies (JUnit 4)

```gradle
testImplementation 'junit:junit'
testImplementation 'org.mockito:mockito-core'
testImplementation 'org.springframework.boot:spring-boot-starter-test'
```

### 4.2 SDK3 Test Dependencies (JUnit 5)

```gradle
testRuntimeOnly 'org.junit.platform:junit-platform-launcher'
testImplementation 'org.junit.jupiter:junit-jupiter'
testImplementation 'org.assertj:assertj-core:3.24.2'
testImplementation 'org.mockito:mockito-core:5.7.0'
testImplementation 'org.mockito:mockito-junit-jupiter:5.7.0'
testImplementation 'org.springframework.boot:spring-boot-starter-test'
```

### 4.3 Test Dependency Mapping

| SDK2 (JUnit 4) | SDK3 (JUnit 5) | Notes |
|---------------|----------------|-------|
| `junit:junit` | `org.junit.jupiter:junit-jupiter` | JUnit 5 |
| `org.mockito:mockito-core` | `org.mockito:mockito-core:5.7.0` | Version update |
| N/A | `org.junit.platform:junit-platform-launcher` | JUnit 5 runtime |
| N/A | `org.mockito:mockito-junit-jupiter:5.7.0` | Mockito-JUnit 5 integration |
| N/A | `org.assertj:assertj-core:3.24.2` | Modern assertion library |

---

## 5. Caching Changes (EhCache 2.x → Spring Simple Cache)

### 5.1 Dependency Changes

#### SDK2 - EhCache 2.x:
```gradle
implementation 'org.springframework.boot:spring-boot-starter-cache'
implementation 'net.sf.ehcache:ehcache:2.10.9.2'
```

#### SDK3 - Spring Boot Simple Cache:
```gradle
implementation 'org.springframework.boot:spring-boot-starter-cache'
// EhCache 2.x removed - not compatible with Jakarta EE (Spring Boot 3)
```

---

### 5.2 Configuration Bean Changes

#### SDK2 - EhCache 2.x Configuration:

**AccountEntriesConfiguration.java:**
```java
@Configuration
@EnableCaching
public class AccountEntriesConfiguration {

    @Bean
    public CacheManager cacheManager() {
        return new EhCacheCacheManager(ehCacheCacheManager().getObject());
    }

    @Bean
    public EhCacheManagerFactoryBean ehCacheCacheManager() {
        EhCacheManagerFactoryBean cmfb = new EhCacheManagerFactoryBean();
        cmfb.setConfigLocation(new ClassPathResource("ehcache.xml"));
        cmfb.setShared(true);
        return cmfb;
    }
}
```

**Imports:**
```java
import org.springframework.cache.CacheManager;
import org.springframework.cache.ehcache.EhCacheCacheManager;
import org.springframework.cache.ehcache.EhCacheManagerFactoryBean;
import org.springframework.core.io.ClassPathResource;
```

#### SDK3 - Simple Cache Configuration:

**AccountEntriesConfiguration.java:**
```java
@Configuration
@EnableCaching
public class AccountEntriesConfiguration {
    // No CacheManager bean needed - Spring Boot auto-configures
    // No EhCacheManagerFactoryBean needed
}
```

**Changes:**
- **REMOVED:** `CacheManager` bean
- **REMOVED:** `EhCacheManagerFactoryBean` bean
- **REMOVED:** All EhCache-related imports
- **KEPT:** `@EnableCaching` annotation (required)

---

### 5.3 EhCache XML File Changes

#### SDK2 - ehcache.xml (ACTIVE):

**Location:** `src/main/resources/ehcache.xml`

**Status:** ✅ **LOADED AND USED** by `EhCacheManagerFactoryBean`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ehcache xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:noNamespaceSchemaLocation="http://www.ehcache.org/ehcache.xsd"
         updateCheck="false"
         monitoring="autodetect"
         dynamicConfig="true">

    <cache name="productNameCache"
        maxEntriesLocalHeap="10000"
        maxEntriesLocalDisk="1000"
        eternal="false"
        diskSpoolBufferSizeMB="20"
        timeToIdleSeconds="14400"
        timeToLiveSeconds="14400"
        memoryStoreEvictionPolicy="LFU"
        transactionalMode="off">
        <persistence strategy="none" />
    </cache>

</ehcache>
```

**Configuration Details:**
- **Cache Name:** `productNameCache`
- **Max Heap Entries:** 10,000
- **Max Disk Entries:** 1,000
- **TTL:** 14,400 seconds (4 hours)
- **Eviction Policy:** LFU (Least Frequently Used)
- **Persistence:** None (in-memory only)

#### SDK3 - ehcache.xml (IGNORED):

**Location:** `src/main/resources/ehcache.xml`

**Status:** ⚠️ **FILE EXISTS BUT NOT LOADED** — Same XML content as SDK2, but Spring Boot's simple cache is used instead. No `EhCacheManagerFactoryBean` bean exists to load it. EhCache 2.x is not compatible with Jakarta EE.

---

### 5.4 Application Properties Configuration

#### SDK2 - No Properties Needed:
```properties
# No cache configuration needed - ehcache.xml handles all configuration
```

#### SDK3 - Optional Cache Properties:

**Option 1: Simple Cache (Default - No configuration needed)**
```properties
# Spring Boot auto-configures simple cache with @EnableCaching
# No additional properties required
```

**Option 2: Explicit Simple Cache Configuration**
```properties
# Explicitly specify simple cache type
spring.cache.type=simple

# Define cache names (optional - auto-detected from @Cacheable annotations)
spring.cache.cache-names=productNameCache
```

---

### 5.5 Migration Action Summary

| Action | SDK2 | SDK3 | Required? |
|--------|------|------|-----------|
| **Remove EhCache dependency** | `net.sf.ehcache:ehcache:2.10.9.2` | Removed | ✅ Yes |
| **Remove CacheManager bean** | Present | Removed | ✅ Yes |
| **Remove EhCacheManagerFactoryBean bean** | Present | Removed | ✅ Yes |
| **Keep @EnableCaching** | Present | Present | ✅ Yes |
| **ehcache.xml file** | Loaded and used | Present but ignored | ⚠️ Can delete |
| **application.properties** | No cache properties | Optional cache properties | ❌ No |

⚠️ **Important:** Simple cache has **no TTL or size limits**. For production, consider migrating to Caffeine cache or EhCache 3.x. Cache annotations (`@Cacheable`, `@CacheEvict`, `@CachePut`) work identically with simple cache — no code changes needed.

---

## 6. Import Statement Changes

> **📚 Detailed Package Mapping:** For comprehensive package-by-package comparison including logging, payload, restclient, restapi, and common packages, see [sdk2_to_sdk3_package_mapping.md](sdk2_to_sdk3_package_mapping.md)

### 6.1 Core API Imports

#### SDK2 Imports:
```java
import com.barclays.api.core.web.beans.Request;
import com.barclays.api.core.web.beans.Resource;
import com.barclays.api.core.web.response.Message;
import com.barclays.api.core.web.response.MetaData;
import com.barclays.api.core.web.response.Response;
import com.barclays.api.core.web.exceptions.ApiServerException;
import com.barclays.api.core.web.exceptions.ApiRequestException;
import com.barclays.api.core.web.response.ErrorMessages;
import com.barclays.api.core.web.util.JsonUtils;
import com.barclays.api.core.web.util.RestClient;
```

#### SDK3 Imports:
```java
import com.barclays.api.bap.bld.lib.payload.beans.Request;
import com.barclays.api.bap.bld.lib.payload.beans.Resource;
import com.barclays.api.bap.bld.lib.payload.response.Message;
import com.barclays.api.bap.bld.lib.payload.response.MetaData;
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiServerException;
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiRequestException;
import com.barclays.api.bap.bld.lib.payload.response.ErrorMessages;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;  // NEW
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;  // NEW
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
```

### 6.2 Import Mapping Table (Summary)

| Category | SDK2 Package | SDK3 Package | Notes |
|----------|-------------|--------------|-------|
| **Logging** | `api.core.logging` | `bap.bld.lib.logging` | Direct mapping |
| **Payload Beans** | `api.core.web.beans` | `bap.bld.lib.payload.beans` | Request, Resource |
| **Secure Fields** | `api.core.web.beans` | `bap.bld.lib.logging.beans` | ⚠️ Moved to logging |
| **Payload Request** | `api.core.web.request` | `bap.bld.lib.payload.request` | Context classes |
| **Payload Response** | `api.core.web.response` | `bap.bld.lib.payload.response` | Message, MetaData, etc. |
| **Common Response** | `api.core.web.response` | `bap.bld.lib.common.response` | ⚠️ Response class only |
| **Exceptions** | `api.core.web.exceptions` | `bap.bld.lib.payload.exceptions` | API exceptions |
| **REST Client** | `api.core.web.util.RestClient` | `bap.bld.lib.restclient.RestApiClient` | Class renamed |
| **Filters** | `api.core.web.filters` | `bap.bld.lib.logging.filters` | ⚠️ Moved to logging |
| **Utilities** | `api.core.web.util` | `bap.bld.lib.payload.beans.util` | JsonUtils, ModUtils |

### 6.3 Removed Utilities

| SDK2 Utility | SDK3 Replacement |
|-------------|------------------|
| `com.barclays.api.core.web.util.JsonUtils` | Use `com.fasterxml.jackson.databind.ObjectMapper` directly |
| `com.barclays.api.core.data.APIProperties` | Use Spring Boot properties (`@Value`, `@ConfigurationProperties`) |

---

## 7. REST Client API Changes

### 7.1 SDK2 RestClient

```java
@Autowired
private RestClient accountEntriesRestClient;

// Usage
Response response = accountEntriesRestClient.callForResponse(
    URI.create(url),
    HttpMethod.GET,
    httpEntity
);

if (response.getHttpStatus() == HttpStatus.OK) {
    // Process response
}
```

### 7.2 SDK3 RestApiClient

```java
@Autowired
private RestApiClient accountEntriesRestClient;

@Autowired
private com.fasterxml.jackson.databind.ObjectMapper objectMapper;

// Usage
ResponseEntity<String> responseEntity = accountEntriesRestClient.call(
    HttpMethod.GET,
    URI.create(url),
    httpEntity.getHeaders(),
    String.class
);

// Parse response body to Response object
String responseBody = responseEntity.getBody();
Response response = objectMapper.readValue(responseBody, RestResponse.class);

if (responseEntity.getStatusCode().is2xxSuccessful()) {
    // Process response
}
```

### 7.3 Key API Differences

| Aspect | SDK2 | SDK3 |
|--------|------|------|
| Client Class | `RestClient` | `RestApiClient` |
| Method Name | `callForResponse()` | `call()` |
| Return Type | `Response` | `ResponseEntity<String>` |
| Parameters | `(URI, HttpMethod, HttpEntity)` | `(HttpMethod, URI, HttpHeaders, Class)` |
| Status Check | `response.getHttpStatus()` | `responseEntity.getStatusCode()` |
| Body Parsing | Automatic via TypeReference | Manual via ObjectMapper |
| RestResponse | Not used | Used for parsing response body |

### 7.4 RestResponse Class

SDK3 introduces `RestResponse` class for parsing API responses:

```java
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;

// Parse the response body
Response response = objectMapper.readValue(responseBody, RestResponse.class);

// Extract data
List<Resource<Transaction>> data = objectMapper.readValue(
    objectMapper.writeValueAsString(response.getData()),
    new TypeReference<List<Resource<Transaction>>>() {}
);
```

---

## 8. Date/Time Library Changes

### 8.1 SDK2 - Joda Time

```gradle
testImplementation 'com.fasterxml.jackson.datatype:jackson-datatype-joda'
```

```java
import org.joda.time.LocalDate;
import com.fasterxml.jackson.datatype.joda.JodaModule;

// Usage
LocalDate date = new LocalDate();

// ObjectMapper registration
objectMapper.registerModule(new JodaModule());
```

### 8.2 SDK3 - Java 8 Date/Time (java.time)

```gradle
implementation 'com.fasterxml.jackson.datatype:jackson-datatype-jsr310'
```

```java
import java.time.LocalDate;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;

// Usage
LocalDate date = LocalDate.now();

// ObjectMapper registration
objectMapper.registerModule(new JavaTimeModule());
```

### 8.3 Migration Actions

- Replace `org.joda.time.LocalDate` with `java.time.LocalDate`
- Replace `new LocalDate()` with `LocalDate.now()`
- Replace `JodaModule` with `JavaTimeModule`
- Update all date/time classes to use `java.time.*` package

---

## 9. JUnit 4 to JUnit 5 Test Migration

### 9.1 Annotations

| JUnit 4 | JUnit 5 | Notes |
|---------|---------|-------|
| `@Test` | `@Test` | Same annotation, different package |
| `@Before` | `@BeforeEach` | Setup before each test |
| `@After` | `@AfterEach` | Cleanup after each test |
| `@BeforeClass` | `@BeforeAll` | Setup once before all tests (static) |
| `@AfterClass` | `@AfterAll` | Cleanup once after all tests (static) |
| `@Ignore` | `@Disabled` | Skip test execution |
| `@Test(expected = Exception.class)` | `Assertions.assertThrows(Exception.class, () -> {})` | Exception testing |
| `@RunWith(SpringRunner.class)` | `@ExtendWith(SpringExtension.class)` | Spring integration |

### 9.2 Imports

#### SDK2 (JUnit 4):
```java
import org.junit.Assert;
import org.junit.Before;
import org.junit.After;
import org.junit.BeforeClass;
import org.junit.AfterClass;
import org.junit.Ignore;
import org.junit.Test;
import org.junit.runner.RunWith;
import org.springframework.test.context.junit4.SpringRunner;
import org.springframework.boot.test.mock.mockito.MockBean;
```

#### SDK3 (JUnit 5):
```java
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.Disabled;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.test.context.junit.jupiter.SpringExtension;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
```

### 9.3 Assertions

#### SDK2 (JUnit 4):
```java
Assert.assertEquals(expected, actual);
Assert.assertNotNull(value);
Assert.assertTrue(condition);
Assert.assertFalse(condition);
```

#### SDK3 (JUnit 5):
```java
Assertions.assertEquals(expected, actual);
Assertions.assertNotNull(value);
Assertions.assertTrue(condition);
Assertions.assertFalse(condition);
```

### 9.4 Exception Testing

#### SDK2 (JUnit 4):
```java
@Test(expected = ApiRequestException.class)
public void testException() {
    // Code that throws exception
}
```

#### SDK3 (JUnit 5):
```java
@Test
public void testException() {
    Assertions.assertThrows(ApiRequestException.class, () -> {
        // Code that throws exception
    });
}
```

### 9.5 Mock Annotations

#### SDK2:
```java
@MockBean
AccountEntriesService accountsService;
```

#### SDK3:
```java
@MockitoBean
private AccountEntriesService accountsService;
```

**Note:** Spring Boot 3.4+ uses `@MockitoBean` instead of `@MockBean`

### 9.6 Test Class Structure

#### SDK2 Example:
```java
@RunWith(SpringRunner.class)
@SpringBootTest
public class AccountEntriesControllerMockTest {

    @MockBean
    AccountEntriesService accountsService;

    @Before
    public void setUp() {
        // Setup code
    }

    @Test
    public void testMethod() {
        Assert.assertEquals(expected, actual);
    }

    @Ignore
    @Test(expected = ApiRequestException.class)
    public void testError() {
        // Test code
    }
}
```

#### SDK3 Example:
```java
@ExtendWith(SpringExtension.class)
@SpringBootTest
@ComponentScan(
    basePackages = {"com.barclays.api.*", "com.barclaycard.digital.*", "com.barclays.iapi.branchaccounts"},
    excludeFilters = {
        @ComponentScan.Filter(type = FilterType.ASSIGNABLE_TYPE, value = MeshConnectorRestClientConfiguration.class)
    })
public class AccountEntriesControllerMockTest {

    @MockitoBean
    private AccountEntriesService accountsService;

    @BeforeEach
    public void setUp() throws Exception {
        // Setup code
    }

    @Test
    public void testMethod() {
        Assertions.assertEquals(expected, actual);
    }

    @Disabled("Reason for disabling")
    @Test
    public void testError() {
        Assertions.assertThrows(ApiRequestException.class, () -> {
            // Test code
        });
    }
}
```

---

## 10. Application.java Changes

### 10.1 SDK2 Application

```java
package com.barclays.iapi.branchaccounts;

import com.barclays.api.core.data.APIProperties;
import com.barclays.api.request.validator.RequestValidationInitializer;
import com.barclays.api.tools.security.SecurityFilterConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Import;

@SpringBootApplication(scanBasePackages = {
    "com.barclays.iapi.branchaccounts",
    "com.barclays.api"
})
@Import({
    RequestValidationInitializer.class,
    SecurityFilterConfiguration.class
})
public class Application extends SpringBootServletInitializer {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        try {
            System.getProperties().putAll(APIProperties.getInstance().getProperties());
        } catch (IOException exception) {
            logger.error("Failed loading application properties.", exception);
            return application;
        }
        return application.sources(Application.class);
    }
}
```

### 10.2 SDK3 Application

```java
package com.barclays.iapi.branchaccounts;

import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.meshconnector.config.MeshConnectorRestClientConfiguration;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.ComponentScan;
import org.springframework.context.annotation.FilterType;

@SpringBootApplication
@ComponentScan(
    basePackages = {
        "com.barclays.api.*",
        "com.barclaycard.digital.*",
        "com.barclays.iapi.branchaccounts"
    },
    excludeFilters = {
        @ComponentScan.Filter(
            type = FilterType.ASSIGNABLE_TYPE,
            value = MeshConnectorRestClientConfiguration.class
        )
    }
)
public class Application extends SpringBootServletInitializer {

    private static final Logger LOG = LogFactory.getLogger(Application.class);

    public static void main(String[] args) {
        try {
            SpringApplication.run(Application.class, args);
        } catch (Exception exc) {
            LOG.error("Application Startup has failed", exc);
            throw exc;
        }
    }

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder applicationBuilder) {
        return applicationBuilder.sources(Application.class);
    }
}
```

### 10.3 Key Changes

| Aspect | SDK2 | SDK3 | Notes |
|--------|------|------|-------|
| Package Scanning | `scanBasePackages` in annotation | `@ComponentScan` | SDK3 requires explicit ComponentScan |
| @Import | Required for validators/security | Not needed | SDK3 auto-configures |
| APIProperties | Manual loading in configure() | Not used | Use Spring Boot properties |
| Logging | Various options | SDK3 LogFactory | Standardized logging |
| Exception Handling | None | Try-catch in main | Better error visibility |
| Exclude Filters | Not used | Exclude MeshConnector config | Avoid conflicts |

---

## 11. Jakarta EE Migration (javax → jakarta)

### 11.1 Package Renames

SDK3 uses Spring Boot 3.x, which migrated from Java EE to Jakarta EE. All `javax.*` packages have been renamed to `jakarta.*`.

| Java EE (javax) | Jakarta EE (jakarta) |
|----------------|---------------------|
| `javax.servlet.*` | `jakarta.servlet.*` |
| `javax.persistence.*` | `jakarta.persistence.*` |
| `javax.validation.*` | `jakarta.validation.*` |
| `javax.annotation.*` | `jakarta.annotation.*` |
| `javax.ws.rs.*` | `jakarta.ws.rs.*` |

### 11.2 Migration Actions

**Find and Replace across entire codebase:**
```
javax.servlet        → jakarta.servlet
javax.persistence    → jakarta.persistence
javax.validation     → jakarta.validation
javax.annotation     → jakarta.annotation
javax.ws.rs          → jakarta.ws.rs
```

**Example:**
```java
// SDK2
import javax.servlet.http.HttpServletRequest;
import javax.validation.constraints.NotNull;

// SDK3
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.constraints.NotNull;
```

---

## 13. Common Pitfalls and Solutions

| Pitfall | Solution |
|---------|----------|
| `Response response = restApiClient.call(...)` fails | Parse `ResponseEntity<String>` body via `objectMapper.readValue(body, RestResponse.class)` — see Section 7 |
| Tests not running after migration | Add `useJUnitPlatform()` to build.gradle + `testRuntimeOnly 'org.junit.platform:junit-platform-launcher'` |
| `@MockBean` not working in Spring Boot 3.4+ | Use `@MockitoBean` (import `org.springframework.test.context.bean.override.mockito.MockitoBean`) |
| LocalDate not serializing correctly | Register `new JavaTimeModule()` and `disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS)` |
| Multiple MeshConnector configs causing startup failures | Exclude `MeshConnectorRestClientConfiguration` via `@ComponentScan(excludeFilters)` — see Section 10 |

---

## 18. Post-Migration Verification

Run in order: `$GRADLE_CMD clean build` → `test` → `integrationTest` → `bootRun` → `jacocoTestReport` → `pitest` → `sonar`

---

## 19. File and Directory Structure Changes

### 19.1 Files to Remove/Delete

#### Gradle Common Files (gradle/common/)

**Delete the entire `gradle/common/` directory:**
```bash
rm -rf gradle/common
```
SDK3's `bap-bld-lib-plugin` provides all Gradle configuration inline. No files from `gradle/common/` are carried forward — the directory must not exist after migration.

---

#### BuildSrc Directory

**SDK2 buildSrc:**
```
buildSrc/
  ├── .gradle/
  └── build/
```
(No build.gradle file - empty buildSrc)

**SDK3 buildSrc:  (IMPORTANT) **
```
buildSrc/
  ├── .gradle/
  ├── build/
  └── build.gradle    ➕ ADD (new - required for SDK3 plugin)
```

**New buildSrc/build.gradle content is (IMPORTANT)  :**
```gradle
repositories {
    maven {
        url 'https://nexus.barcapint.com/nexus/content/groups/barclays'
    }
}

def rootProperties = new Properties()
file('../gradle.properties').withInputStream {
    rootProperties.load(it)
}
def sdkVersion = rootProperties.getProperty('SDK3_VERSION')

dependencies {
    implementation(platform("com.barclays.api:sdk3:${sdkVersion}"))
    implementation("com.barclays.api:bap-bld-lib-plugin")
    implementation("com.barclays.api:bap-bld-lib-kotlin-int-test-gradle-plugin")
    implementation("org.springframework.boot:spring-boot-gradle-plugin") {
        exclude group:'ch.qos.logback', module: 'logback-classic'
    }
}
```

---

#### Root Directory Files

**SDK2 Files:**
```
├── build.gradle                  ✅ KEEP (modify)
├── gradle.properties             ✅ KEEP (modify)
├── .java-version                 ✅ KEEP (update from 8 to 21)
├── gradlew                       ✅ KEEP
├── gradlew.bat                   ✅ KEEP
├── README.md                     ✅ KEEP
├── upload-artifact.gradle        ✅ KEEP
├── CLAUDE.md                     ✅ KEEP (optional docs)
└── settings.gradle               ❌ MISSING in SDK2
```

**SDK3 Files:**
```
├── build.gradle                  ✅ KEEP (modified)
├── gradle.properties             ✅ KEEP (modified)
├── .java-version                 ✅ KEEP (changed to 21)
├── gradlew                       ✅ KEEP
├── gradlew.bat                   ✅ KEEP
├── README.md                     ✅ KEEP
├── upload-artifact.gradle        ✅ KEEP
├── settings.gradle               ➕ ADD (new - required)
└── test_baseline.log             ➕ ADD (test output - optional)
```

**New settings.gradle content:**
```gradle
rootProject.name = 'accountentries-iapi'
```

---

#### Resource Files

**ehcache.xml Status:**

**SDK2:**
```
src/main/resources/ehcache.xml    ✅ ACTIVE (loaded by EhCacheManagerFactoryBean)
```

**SDK3:**
```
src/main/resources/ehcache.xml    ⚠️ PRESENT BUT IGNORED (can be deleted)
```

**Migration Action:**
- **Option A:** Delete `ehcache.xml` (recommended - file is not used)
- **Option B:** Keep for reference (file will be ignored by Spring Boot)

---

**application.properties:**

**SDK2:**
```
src/main/resources/application.properties    ❌ MISSING (not needed)
src/test/resources/application.properties    ✅ EXISTS
```

**SDK3:**
```
src/main/resources/application.properties    ➕ ADD (required for Spring Boot 3)
src/test/resources/application.properties    ✅ EXISTS
```

**New src/main/resources/application.properties:**
```properties
# Spring Boot 3 Configuration
spring.main.allow-bean-definition-overriding=true
spring.main.allow-circular-references=true

# Disable unused services
eureka.client.enabled=false
spring.cloud.config.enabled=false

# Logging
logging.level.root=INFO
logging.level.com.barclays.iapi.branchaccounts=DEBUG

# Application name
spring.application.name=accountentries-iapi
```

---

## 19.5 Advanced SDK3 API Changes (Discovered During Migration)

This section documents additional API changes that were discovered during actual migration but not initially covered in the specification. These are critical for compilation success.

### 19.5.0 Quick Reference Table

This table helps you quickly identify which issue you're facing based on compilation errors:

| Compilation Error | Root Cause | Fix | Section |
|-------------------|------------|-----|---------|
| `cannot find symbol: method assemble()` location: `Response` | Response interface doesn't have `assemble()` | Change `Response.assemble()` to `RestResponse.assemble()` | 19.5.1 |
| `cannot find symbol: method getHttpStatus()` location: `Response` | Response interface doesn't have status methods | Change parameter type from `Response` to `RestResponse` | 19.5.2 |
| `cannot find symbol: method getErrors()` location: `Response` | Response interface doesn't have error methods | Change parameter type from `Response` to `RestResponse` | 19.5.2 |
| `cannot find symbol: method fromDateFields(Date)` location: `LocalDate` | Joda Time method doesn't exist in java.time | Use `date.toInstant().atZone(ZoneId.systemDefault()).toLocalDate()` | 19.5.3 |
| `static import only from classes and interfaces` with `MoreObjects.firstNonNull` | Guava import issue | Replace with `Objects.requireNonNullElse()` | 19.5.4 |
| `return type void is not compatible with String` in filter | SDK3 filter signature changed | Change method return type from `void` to `String`, add `return result;` | 19.5.5 |
| `incompatible types: Response cannot be converted to RestResponse` | Variable type mismatch | Change local variable from `Response` to `RestResponse` | 19.5.2 |

### 19.5.0a Migration Order

Apply fixes in order: 19.5.2 (types) → 19.5.1 (assemble) → 19.5.3 (dates) → 19.5.4 (Guava) → 19.5.5 (filters).

### 19.5.1 RestResponse Builder Pattern (CRITICAL)

> **📖 Canonical Reference:** See `lessons_learnt.md` Section 3 for the complete Response vs RestResponse guide with method availability matrix and decision rules.

#### Compilation Error You'll See:
```
error: cannot find symbol
    return Response.assemble().build(resource);
                   ^
  symbol:   method assemble()
  location: interface Response
```

#### Problem:
In SDK2, service layer code used `Response.assemble()` to build response objects. In SDK3, this method does not exist on the `Response` interface.

#### Solution:
Use `RestResponse.assemble()` instead. The `Response` interface in SDK3 is minimal (only `getData()` methods). The concrete `RestResponse` provides the builder pattern.

#### SDK3 Code (replace `Response.assemble()` → `RestResponse.assemble()`):
```java
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;  // NEW IMPORT REQUIRED

public Response buildResponse(Resource resource, MetaData meta) {
    if (meta.isEmpty())
        return RestResponse.assemble().build(resource);  // Changed from Response.assemble()
    else
        return RestResponse.assemble().addMetadata(meta).build(resource);
}
```

#### Key Points:
- **Import Both**: Keep `Response` import for return type, add `RestResponse` import for builder
- **Builder Methods**: RestResponse.assemble() returns `ResponseAssembler` which has:
  - `build(Object)` - builds response with data
  - `build(ResponseHttpStatus, Object)` - builds response with specific status
  - `addMetadata(MetaData)` - adds metadata (chainable)
  - `setHeader(String, String)` - adds headers (chainable)
  - `addErrorMessage(Message)` - adds single error (chainable)
  - `addErrorMessages(Collection<Message>)` - adds multiple errors (chainable)
- **Empty Responses**: Use `RestResponse.empty(ResponseHttpStatus)` or `RestResponse.empty(HttpStatus)`

#### Affected Files:
- All service implementation classes that build API responses
- Typically in `*/service/impl/*ServiceImpl.java`

---

### 19.5.2 Response vs RestResponse Type Usage

> **📖 Canonical Reference:** See `lessons_learnt.md` Section 3 for the complete Response vs RestResponse guide with method availability matrix and decision rules.

#### Compilation Errors You'll See:
```
error: cannot find symbol
    if (response.getHttpStatus().is4xxClientError()) {
                ^
  symbol:   method getHttpStatus()
  location: variable response of type Response

error: cannot find symbol
    if (response.getErrors() != null) {
                ^
  symbol:   method getErrors()
  location: variable response of type Response

error: incompatible types: Response cannot be converted to RestResponse
    ValidationUtils.validateResponse(response, ...)
                                     ^
```

#### Problem:
SDK3's `Response` interface only has `getData()` methods. Methods like `getHttpStatus()`, `getErrors()`, `getMeta()`, etc. are only available on the `RestResponse` concrete class.

#### Solution:
When parsing or validating responses from external APIs, use `RestResponse` type instead of `Response` interface.

#### Response Interface (SDK3):
```java
public interface Response {
    public abstract <T> T getData() throws ClassCastException;
    public abstract <T> T getData(Class<T>) throws ClassCastException;
}
```

#### RestResponse Class (SDK3):
```java
public final class RestResponse implements Response {
    // Builder pattern
    public static ResponseAssembler assemble();
    public static RestResponse empty(ResponseHttpStatus);
    public static RestResponse empty(HttpStatus);

    // Getters/Setters
    public MetaData getMeta();
    public void setMeta(MetaData);
    public <T> T getData();
    public <T> T getData(Class<T>);
    public <T> T getData(TypeReference<T>);
    public void setData(Object);
    public List<Message> getErrors();
    public void setErrors(List<Message>);
    public MultiValueMap<String, String> getMultiValueHeaders();
    public void setHeaders(MultiValueMap<String, String>);
    public HttpStatus getHttpStatus();  // NOT in Response interface
    public void setHttpStatus(HttpStatus);
}
```

#### When to Use Each:

**GOLDEN RULE: Interface in method SIGNATURES, concrete class in method IMPLEMENTATION**

| Context | Use | Example |
|---------|-----|---------|
| Return types | `Response` interface | `public Response getTransactions() { ... }` |
| Building responses | `RestResponse` concrete | `RestResponse.assemble().build(data)` |
| Param needs `getHttpStatus()`/`getErrors()` | `RestResponse` | `validateResponse(RestResponse response)` |
| Param only needs `getData()` | `Response` interface | `processData(Response response)` |
| Local variables from API calls | `RestResponse` | `RestResponse response = objectMapper.readValue(...)` |

#### Affected Files:
- `*/helper/ValidationUtils.java` — parameter type change
- `*/gateway/impl/*GatewayImpl.java` — local variable type change

---

### 19.5.3 Joda Time to java.time Conversion (LocalDate.fromDateFields)

#### Compilation Error You'll See:
```
error: cannot find symbol
    transDatum.setPostedDate(LocalDate.fromDateFields(ts.getEntryPostedDate()));
                                      ^
  symbol:   method fromDateFields(Date)
  location: class LocalDate
```

#### Problem:
Joda Time's `LocalDate.fromDateFields(Date)` method does not exist in `java.time.LocalDate`. This is a common conversion pattern that needs updating.

#### SDK2 Code (Joda Time):
```java
import org.joda.time.LocalDate;
import java.util.Date;

if (ts.getEntryPostedDate() != null) {
    transDatum.setPostedDate(LocalDate.fromDateFields(ts.getEntryPostedDate()));
}
```

#### SDK3 Code (java.time):
```java
import java.time.LocalDate;
import java.time.ZoneId;
import java.util.Date;

if (ts.getEntryPostedDate() != null) {
    transDatum.setPostedDate(ts.getEntryPostedDate().toInstant()
        .atZone(ZoneId.systemDefault())
        .toLocalDate());
}
```

#### Affected Files:
- `*/helper/*Mapper.java` classes
- Any DTOs or data conversion utilities
- Search codebase for: `LocalDate.fromDateFields`, `LocalDateTime.fromDateFields`, `.toDate()`

---

### 19.5.4 Guava to Java Standard Library (firstNonNull)

#### Compilation Error You'll See:
```
error: cannot find symbol
    String encoding = firstNonNull(request.getCharacterEncoding(), WebUtils.DEFAULT_CHARACTER_ENCODING);
                      ^
  symbol:   method firstNonNull(String,String)
  location: class RequestResponsePayloadLoggingFilter

OR:

error: static import only from classes and interfaces
import static com.google.common.base.MoreObjects.firstNonNull;
^
```

#### Problem:
Guava's `com.google.common.base.MoreObjects.firstNonNull()` may cause static import issues or dependency conflicts in SDK3.

#### SDK2 Code (Guava):
```java
import static com.google.common.base.MoreObjects.firstNonNull;

public class MyFilter {
    public void processRequest(HttpServletRequest request) {
        String encoding = firstNonNull(request.getCharacterEncoding(), WebUtils.DEFAULT_CHARACTER_ENCODING);
    }
}
```

#### SDK3 Code (Java 9+ Standard Library):
```java
import java.util.Objects;

public class MyFilter {
    public void processRequest(HttpServletRequest request) {
        String encoding = Objects.requireNonNullElse(request.getCharacterEncoding(), WebUtils.DEFAULT_CHARACTER_ENCODING);
    }
}
```

#### Method Comparison:
| Guava | Java Standard | Purpose |
|-------|---------------|---------|
| `MoreObjects.firstNonNull(T, T)` | `Objects.requireNonNullElse(T, T)` | Returns first non-null value |
| `Preconditions.checkNotNull(T)` | `Objects.requireNonNull(T)` | Throws if null |
| `Preconditions.checkNotNull(T, String)` | `Objects.requireNonNull(T, String)` | Throws with message if null |

#### Affected Files:
- Custom filter implementations and utility classes using Guava's `MoreObjects` or `Preconditions`

---

### 19.5.5 RequestResponseLoggingFilter Method Signature Changes

#### Compilation Errors You'll See:
```
error: logRequest(HttpServletRequest,SecureFields) in CustomLoggingFilter cannot override logRequest(HttpServletRequest,SecureFields) in RequestResponseLoggingFilter
    protected void logRequest(HttpServletRequest request, SecureFields secureFields) {
                   ^
  return type void is not compatible with String

error: method does not override or implement a method from a supertype
    @Override
    ^

error: cannot find symbol
        return result;
               ^
  symbol:   variable result
  location: class CustomLoggingFilter
```

#### Problem:
SDK3's `RequestResponseLoggingFilter` changed method signatures — `logRequest()` and `logResponse()` now return `String` instead of `void`. SDK3 parent class needs the log string for centralized logging/metrics.

#### SDK3 Custom Filter (Fixed):
```java
public class CustomLoggingFilter extends RequestResponseLoggingFilter {
    @Override
    protected String logRequest(HttpServletRequest request, SecureFields secureFields) {
        String result = buildLogString(request, secureFields);
        LOG.info(result);
        return result;  // MUST return the log string
    }

    @Override
    protected String logResponse(HttpServletRequest request, HttpServletResponse response, SecureFields secureFields) {
        String result = buildLogString(request, response, secureFields);
        LOG.info(result);
        return result;  // MUST return the log string
    }
}
```

#### Affected Files:
- Custom implementations of `RequestResponseLoggingFilter`
- Typically in `*/filter/*LoggingFilter.java`

---

### 19.5.6 Validation Order for Advanced API Changes

Apply fixes in order from 19.5.1→19.5.5, then run: `$GRADLE_CMD compileJava -x barclaysApiGenerate` to verify BUILD SUCCESSFUL with 0 errors.

---

### 19.5.7 Correlation ID Pattern Simplification

SDK3 simplifies the correlation ID retrieval pattern. The `X_CORRELATION_ID` constant check is no longer needed.

#### SDK2 (Complex Pattern):
```java
String correlationId =
    StringUtils.hasText(MDC.get(InternalRequestContext.X_CORRELATION_ID))
        ? MDC.get(InternalRequestContext.X_CORRELATION_ID)
        : MDC.get(InternalRequestContext.CORRELATION_ID);
```

#### SDK3 (Simplified Pattern):
```java
String correlationId = MDC.get(InternalRequestContext.CORRELATION_ID);
```

**Migration Actions:**
- Search for `X_CORRELATION_ID` in all Java files
- Replace the ternary pattern with simple `CORRELATION_ID` retrieval
- SDK3 consolidates correlation ID handling to single constant

---

### 19.6 IDE Configuration Removal

SDK3 projects should not include IDE-specific Gradle configurations. Modern IDEs automatically detect Gradle projects without explicit plugins.

#### SDK2 build.gradle (Remove these blocks):
```gradle
//////////////////////
// Eclipse //
//////////////////////
eclipse {
    classpath {
        downloadJavadoc = true
        downloadSources = true
    }
}

idea {
    module {
        downloadJavadoc = true
        downloadSources = true
    }
}

sourceSets {
    generated {
        java.srcDir "${buildDir}/generated/sources"
    }
}

def generatedSourcesDir = file("${buildDir}/generated/sources")
```

#### SDK3 build.gradle:
```gradle
// Remove all eclipse {}, idea {}, sourceSets {}, and generatedSourcesDir definitions
// SDK3's bap-bld-lib-plugin handles all necessary configurations
// Modern IDEs (IntelliJ IDEA, Eclipse with Buildship, VS Code) automatically detect Gradle projects
```

**Migration Actions:**
- Remove `apply plugin: 'eclipse'`, `apply plugin: 'idea'`, entire `eclipse {}` and `idea {}` blocks
- Remove `sourceSets {}` blocks for generated sources and `generatedSourcesDir` variable definitions
- SDK3's `bap-bld-lib-plugin` handles all configurations; Gradle 8.13+ works seamlessly with modern IDEs

---

### 19.7 Spring Boot 3.3 Migration

SDK3 uses Spring Boot 3.3.x which includes property and configuration changes from earlier Spring Boot 3.x versions.

#### Spring Boot 3.3 Property Changes

The following properties have been renamed or deprecated:

##### Logging Properties:
```properties
# SDK2 / Spring Boot 2.x
logging.pattern.rolling-file-name=...

# SDK3 / Spring Boot 3.3
logging.logback.rollingpolicy.file-name-pattern=...
```

##### Actuator Properties:
```properties
# SDK2 / Spring Boot 2.x
management.metrics.export.prometheus.enabled=true

# SDK3 / Spring Boot 3.3
management.prometheus.metrics.export.enabled=true
```

**Migration Actions:**
- Review `application.properties` and `application.yml` for deprecated properties
- Update logging properties to use `logging.logback.rollingpolicy.*` prefix
- Update metrics properties to use new hierarchy
- Run application and check for deprecation warnings in logs
- Refer to Spring Boot 3.3 release notes for complete property mapping

---

### 19.8 SpringBootServletInitializer Removal

SDK3 uses embedded server deployment (JAR) instead of WAR deployment. The `SpringBootServletInitializer` is no longer needed.

#### SDK2 Application.java:
```java
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.boot.web.servlet.support.SpringBootServletInitializer;

@SpringBootApplication
public class Application extends SpringBootServletInitializer {

    @Override
    protected SpringApplicationBuilder configure(SpringApplicationBuilder application) {
        return application.sources(Application.class);
    }

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

#### SDK3 Application.java:
```java
@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }
}
```

**Migration Actions:**
- Remove `extends SpringBootServletInitializer` from Application class
- Remove `configure()` method override
- Remove import `org.springframework.boot.web.servlet.support.SpringBootServletInitializer`
- Remove import `org.springframework.boot.builder.SpringApplicationBuilder`
- SDK3 uses embedded Tomcat/Jetty server via JAR deployment

---

## 20. Additional Resources

- SDK3 Documentation: Internal Barclays confluence pages
- Spring Boot 3 Migration Guide: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide
- JUnit 5 Migration Guide: https://junit.org/junit5/docs/current/user-guide/#migrating-from-junit4
- Jakarta EE 9 Migration: https://jakarta.ee/specifications/platform/9/jakarta-platform-spec-9.0.html

---

**Document Version:** 1.5 | **Source Projects:** accountentries-iapi (SDK2) → accountentries-iapi_sdk3 (SDK3)
