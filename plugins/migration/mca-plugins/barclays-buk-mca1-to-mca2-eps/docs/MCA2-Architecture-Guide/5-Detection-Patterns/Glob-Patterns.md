# Glob Patterns: File-Based MCA2 EPS Detection

## Executive Summary

25+ glob patterns for file-based discovery of MCA2 EPS framework usage. All patterns use standard glob syntax compatible with find, locate, and file globbing tools.

---

## QUICK START

### Usage

```bash
# Basic glob with find
find /path/to/app -name "*Filter.java" -type f

# Extended glob patterns (bash)
shopt -s globstar  # Enable ** for recursive matching
ls src/**/mca*.gradle

# Using locate (faster, requires updatedb)
locate "*/mca-context/build.gradle"

# Using fd command (faster, more intuitive)
fd "Filter\.java$" src/

# Using globstar in find (POSIX)
find src -name "*.java" -path "*filter*"

# Save results to file
find src -name "*Filter.java" > filter_files.txt
```

---

## FILTER CHAIN PATTERNS (5 Patterns)

Discover MCA2 filter chain components by file patterns.

### Pattern 1: Filter Implementation Files

**Glob Pattern:**
```bash
**/src/main/java/**/filters/*Filter.java
**/src/main/java/**/*Filter.java
**/*FilterConfig.java
**/*FilterChain*.java
```

**Usage Examples:**

```bash
# Find all filter implementations
find . -path "*/filters/*Filter.java" -type f

# More specific: MCA filters
find . -name "*Filter.java" -type f | grep -E "(Context|Correlation|Exception|DdoS)"

# Using fd (faster)
fd "Filter\.java$" --path "filters"

# Using globstar (recursive)
find . -name "**/*Filter.java" 2>/dev/null
```

**Expected Output:**
```
./src/main/java/com/example/filters/ContextFilter.java
./src/main/java/com/example/filters/CustomAuthFilter.java
./src/main/java/com/example/filters/RequestLoggingFilter.java
./src/main/java/com/example/config/FilterConfig.java
```

**Indicates:** Filter implementations; filter chain configuration

---

### Pattern 2: Filter Configuration Classes

**Glob Pattern:**
```bash
**/config/*FilterConfig.java
**/config/*SecurityConfig.java
**/config/*ContextConfig.java
**/mvc/*FilterConfiguration.java
```

**Usage Examples:**

```bash
# Find filter configuration classes
find . -path "*/config/*FilterConfig.java" -type f

# Combined: filter config + security config
find . -path "*/config/*" -name "*Filter*Config.java" -o -name "*Security*Config.java"

# Using globstar
find . -name "**/*FilterConfig.java" -o -name "**/*SecurityConfig.java"
```

**Expected Output:**
```
./src/main/java/com/example/config/FilterConfig.java
./src/main/java/com/example/config/SecurityConfig.java
./src/main/java/com/example/config/ContextConfig.java
```

**Indicates:** Filter configuration locations

---

### Pattern 3: Spring Boot Autoconfiguration Imports

**Glob Pattern:**
```bash
**/src/main/resources/META-INF/spring/org.springframework.boot.*.imports
**/META-INF/spring/AutoConfiguration.imports
**/META-INF/spring/EnvironmentPostProcessor.imports
```

**Usage Examples:**

```bash
# Find auto-configuration imports
find . -path "*/META-INF/spring/*.imports" -type f

# View configuration classes
find . -path "*/META-INF/spring/*.imports" -exec cat {} \;

# Check for MCA2 auto-config
find . -path "*/META-INF/spring/*.imports" -exec grep -l "mca\|barclays" {} \;

# Using locate (if available)
locate "META-INF/spring/*.imports"
```

**Expected Output:**
```
./src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
./src/main/resources/META-INF/spring/org.springframework.boot.EnvironmentPostProcessor.imports
```

**File Contents Example:**
```
com.barclays.global.mca.libs.eps.ExperienceAPIAutoConfiguration
com.barclays.global.mca.libs.filter.FilterAutoConfiguration
com.barclays.global.mca.libs.context.ContextAutoConfiguration
```

**Indicates:** Spring Boot 3 auto-configuration registration; framework activation

---

### Pattern 4: Filter Exclusion Patterns

**Glob Pattern:**
```bash
**/resources/**/*filter*.properties
**/resources/**/*filter*.yml
**/config/**/*.properties
**/application-*.properties
**/application-*.yml
```

**Usage Examples:**

```bash
# Find filter configuration properties
find . -name "*filter*.properties" -o -name "*filter*.yml"

# Find all application property files
find . -name "application*.properties" -o -name "application*.yml"

# Find MCA-specific properties
find . -name "*.properties" -exec grep -l "mca\.filter" {} \;

# View filter properties
find . -name "*.properties" -exec grep "mca\.filter\|mca\.context" {} \; -print
```

**Expected Output:**
```
./src/main/resources/application.properties
./src/main/resources/application-dev.properties
./src/main/resources/application-prod.properties
./src/main/resources/application-filter.yml
```

**Indicates:** Filter configuration settings

---

### Pattern 5: OncePerRequestFilter Override Detection

**Glob Pattern:**
```bash
**/OncePerRequestFilter.java
**/*extends*.java
**/src/main/java/**/*Filter.java
```

**Usage Examples:**

```bash
# Search Java files for filter pattern
find . -name "*Filter.java" -type f

# Narrow to only potential custom filters (not in dependencies)
find ./src/main/java -name "*Filter.java" -type f

# Find files that might extend filter base
find . -name "*Filter.java" -exec grep -l "extends.*Filter" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/filters/CustomFilter.java
./src/main/java/com/example/filters/AuthenticationFilter.java
```

**Indicates:** Filter extension points; custom filter implementations

---

## CONTEXT SYSTEM PATTERNS (6 Patterns)

Discover IOL context system components and configuration. Note: Context storage (ContextStore, context-store-*) is part of the Secure Proxy module. Pattern 7a is listed here for convenience but detects Secure Proxy usage, not EPS core.

### Pattern 6: Context Class Files

**Glob Pattern:**
```bash
**/src/main/java/**/*Context.java
**/domain/**/*Context.java
**/context/**/**.java
**/schemas/**/*Context.java
```

**Usage Examples:**

```bash
# Find all context class files
find . -name "*Context.java" -type f

# Exclude test files
find ./src/main/java -name "*Context.java" -type f

# Count context classes
find . -name "*Context.java" -type f | wc -l

# View context files
find ./src/main/java -name "*Context.java" | xargs ls -lh

# Specific context types
find . -name "Customer*.java" -o -name "User*.java" -o -name "Account*.java"
```

**Expected Output:**
```
./src/main/java/com/example/context/CustomerContext.java
./src/main/java/com/example/context/UserContext.java
./src/main/java/com/example/context/AccountContext.java
./src/main/java/com/example/context/ProcessContext.java
./src/main/java/com/example/context/DeviceContext.java
```

**Indicates:** Context classes in use; context data model

---

### Pattern 7: IOLSchema Files

**Glob Pattern:**
```bash
**/IOLSchema.java
```

**Usage Examples:**

```bash
# Find IOLSchema implementations
find . -name "IOLSchema.java" -type f
```

**Expected Output:**
```
./src/main/java/com/example/context/IOLSchema.java
```

**Indicates:** IOL context data model usage; core EPS context system

---

### Pattern 7a: Secure Proxy Context Store Files

> **Note:** Context storage (ContextStore, context-store-rdb, context-store-mongo, context-store-ehcache) is part of the Secure Proxy module, not EPS core.

**Glob Pattern:**
```bash
**/ContextStore.java
**/*ContextStore*.java
**/store/**Context*.java
```

**Usage Examples:**

```bash
# Find context store backends (Secure Proxy)
find . -name "*ContextStore.java" -type f

# Find context store configurations
find . -name "*ContextStore*Config.java"

# Locate context storage implementations
find . -path "*/context-store*" -name "*.java"
```

**Expected Output:**
```
./src/main/java/com/example/store/ContextStore.java
./src/main/java/com/example/store/RdbContextStore.java
./src/main/java/com/example/store/MongoContextStore.java
```

**Indicates:** Secure Proxy context storage implementations; not EPS core

---

### Pattern 8: Context Configuration Files

**Glob Pattern:**
```bash
**/resources/**context*.properties
**/resources/**context*.yml
**/*ContextConfig.java
**/config/*Context*.java
```

**Usage Examples:**

```bash
# Find context property files
find . -name "*context*.properties" -o -name "*context*.yml"

# Find context configuration classes
find . -name "*ContextConfig.java"

# View context configuration
find . -name "*.properties" -exec grep -l "context\." {} \;
```

**Expected Output:**
```
./src/main/resources/application.properties
./src/main/resources/context-config.properties
./src/main/java/com/example/config/ContextConfig.java
```

**Indicates:** Context system configuration (IOL context classes and propagation)

---

### Pattern 9: Context Utilities and Helpers

**Glob Pattern:**
```bash
**/utils/*Context*.java
**/utilities/*Context*.java
**/*ContextMapper.java
**/*ContextValidator.java
**/*WebUtils.java
```

**Usage Examples:**

```bash
# Find context utility classes
find . -name "*ContextMapper.java" -o -name "*ContextValidator.java"

# Find WebUtils (context access)
find . -name "*WebUtils.java"

# Find all context-related utilities
find . -path "*/utils/*" -name "*Context*"

# Count utility classes
find . -name "*ContextMapper.java" -o -name "*ContextValidator.java" | wc -l
```

**Expected Output:**
```
./src/main/java/com/example/utils/ContextMapper.java
./src/main/java/com/example/utils/ContextValidator.java
./src/main/java/com/example/utils/WebUtils.java
./src/main/java/com/example/utils/ContextPropagation.java
```

**Indicates:** Context manipulation utilities; context propagation helpers

---

### Pattern 10: Context Test Files

**Glob Pattern:**
```bash
**/src/test/java/**/*Context*Test.java
**/tests/**/*ContextTest.java
**/*ContextIntegrationTest.java
```

**Usage Examples:**

```bash
# Find context tests
find . -path "*/test/java/*" -name "*Context*Test.java"

# Find integration tests
find . -name "*ContextIntegrationTest.java"

# Count context tests
find . -path "*/test/*" -name "*Context*Test.java" | wc -l

# List all context-related tests
find . -path "*/test/*" -name "*Context*.java" | sort
```

**Expected Output:**
```
./src/test/java/com/example/context/ContextTest.java
./src/test/java/com/example/context/ContextIntegrationTest.java
./src/test/java/com/example/filters/ContextFilterTest.java
```

**Indicates:** Context system test coverage; test implementation quality

---

## EPS CORE PATTERNS (4 Patterns)

Discover MCA2 EPS core framework components.

### Pattern 11: Application Class with @EnableExperienceAPI

**Glob Pattern:**
```bash
**/Application.java
**/src/main/java/**/*Application.java
**/SpringBootApplication*.java
**/main/**/*.java
```

**Usage Examples:**

```bash
# Find Application classes
find . -name "Application.java" -type f

# Find in main paths
find ./src/main/java -name "*Application.java"

# Search for @EnableExperienceAPI annotation
find . -name "Application.java" -exec grep -l "@EnableExperienceAPI" {} \;

# Find Spring Boot main classes
find . -name "Application.java" -exec grep -l "@SpringBootApplication" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/Application.java
./src/main/java/com/example/CardControlApplication.java
./src/main/java/com/example/OrderServiceApplication.java
```

**Indicates:** Framework activation; main application entry point

---

### Pattern 12: EPS Configuration Classes

**Glob Pattern:**
```bash
**/*EpsConfig.java
**/*ExperienceAPIConfig.java
**/config/*Eps*.java
**/config/*ExperienceAPI*.java
```

**Usage Examples:**

```bash
# Find EPS configuration classes
find . -name "*EpsConfig.java" -o -name "*ExperienceAPIConfig.java"

# Find in config directories
find . -path "*/config/*" -name "*Eps*.java"

# Search all configuration classes
find . -path "*/config/*" -name "*.java" -exec grep -l "EPS\|ExperienceAPI" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/config/EpsConfig.java
./src/main/java/com/example/config/ExperienceAPIConfig.java
```

**Indicates:** EPS framework configuration; custom EPS setup

---

### Pattern 13: Build Configuration - Gradle

**Glob Pattern:**
```bash
**/build.gradle
**/settings.gradle
**/gradle.properties
**/gradle/wrapper/gradle-wrapper.properties
```

**Usage Examples:**

```bash
# Find main build files
find . -maxdepth 2 -name "build.gradle" -o -name "settings.gradle"

# Check all gradle files
find . -name "*.gradle" -type f

# Find gradle properties
find . -name "gradle.properties" -o -name "gradle-wrapper.properties"

# Search for mca dependencies
find . -name "build.gradle" -exec grep -l "mca-" {} \;

# View gradle file structure
find . -name "build.gradle" | xargs wc -l | sort -rn
```

**Expected Output:**
```
./build.gradle
./settings.gradle
./gradle.properties
./gradle/wrapper/gradle-wrapper.properties
./mca-examples/mca-experience-api-cardcontrol-reference-app/build.gradle
```

**Indicates:** Gradle build configuration; MCA2 dependency declarations

---

### Pattern 14: Build Configuration - Maven

**Glob Pattern:**
```bash
**/pom.xml
**/.m2/settings.xml
**/mvn.properties
```

**Usage Examples:**

```bash
# Find Maven configuration
find . -name "pom.xml" -type f

# Check Maven directory structure
find . -name "pom.xml" -exec ls -l {} \;

# Search for mca dependencies in pom
find . -name "pom.xml" -exec grep -l "mca-" {} \;

# View pom dependencies
find . -name "pom.xml" -exec grep -A 5 "mca-context" {} \;
```

**Expected Output:**
```
./pom.xml
./mca-examples/mca-experience-api-cardcontrol-reference-app/pom.xml
```

**Indicates:** Maven build configuration; dependency management

---

## EXCEPTION & RESPONSE PATTERNS (4 Patterns)

Discover exception and response handling components.

### Pattern 15: Exception Class Files

**Glob Pattern:**
```bash
**/exceptions/**Exception.java
**/*Exception.java
**/error/**Exception.java
**/*ErrorCode.java
```

**Usage Examples:**

```bash
# Find all exception classes
find . -path "*/exceptions/*Exception.java" -o -name "*Exception.java"

# Exclude third-party and test exceptions
find ./src/main/java -name "*Exception.java" -type f

# Find error code enums
find . -name "*ErrorCode.java"

# Count exception classes
find ./src/main/java -name "*Exception.java" | wc -l

# List custom exceptions
find ./src/main/java -name "*Exception.java" | grep -v "springframework\|test"
```

**Expected Output:**
```
./src/main/java/com/example/exceptions/ApplicationException.java
./src/main/java/com/example/exceptions/RequestException.java
./src/main/java/com/example/exceptions/ServerException.java
./src/main/java/com/example/exceptions/ErrorCode.java
```

**Indicates:** Exception hierarchy implementation; error codes

---

### Pattern 16: Exception Handler Configuration

**Glob Pattern:**
```bash
**/*ExceptionHandler.java
**/advice/*ExceptionHandler.java
**/*GlobalExceptionHandler.java
**/exception/**Handler*.java
```

**Usage Examples:**

```bash
# Find exception handlers
find . -name "*ExceptionHandler.java"

# Find global exception handlers
find . -name "*GlobalExceptionHandler.java"

# Find @RestControllerAdvice classes
find . -name "*.java" -type f -exec grep -l "@RestControllerAdvice\|@ControllerAdvice" {} \;

# Find exception handler methods
find . -name "*.java" -exec grep -l "@ExceptionHandler" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/exception/GlobalExceptionHandler.java
./src/main/java/com/example/exception/ApiExceptionHandler.java
./src/main/java/com/example/advice/ErrorResponseAdvice.java
```

**Indicates:** Centralized exception handling; error response standardization

---

### Pattern 17: Response/DTO Classes

**Glob Pattern:**
```bash
**/dto/*Response*.java
**/*Response.java
**/model/*Response*.java
**/*ResponseAssembler.java
```

**Usage Examples:**

```bash
# Find response classes
find . -path "*/dto/*Response*.java" -o -name "*Response.java"

# Find response assemblers
find . -name "*ResponseAssembler.java"

# Find response-related classes
find ./src/main/java -path "*/response*" -name "*.java"

# Count response classes
find . -name "*Response*.java" -type f | wc -l
```

**Expected Output:**
```
./src/main/java/com/example/dto/ApiResponse.java
./src/main/java/com/example/response/Response.java
./src/main/java/com/example/response/ResponseAssembler.java
./src/main/java/com/example/dto/OrderResponse.java
```

**Indicates:** Response envelope implementation; standardized API responses

---

### Pattern 18: API Response Serialization (Jackson)

**Glob Pattern:**
```bash
**/*Serializer.java
**/*Deserializer.java
**/jackson/**Mixin*.java
```

**Usage Examples:**

```bash
# Find serialization classes
find . -name "*Serializer.java" -o -name "*Deserializer.java"

# Find Jackson configuration
find . -path "*/jackson/*" -name "*.java"

# Find custom Jackson configuration
find . -name "*.java" -exec grep -l "ObjectMapper\|@JsonSerialize" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/jackson/ErrorResponseSerializer.java
./src/main/java/com/example/jackson/ContextDeserializer.java
```

**Indicates:** Custom serialization logic; response formatting

---

## LOGGING & MASKING PATTERNS (4 Patterns)

Discover logging and data protection components.

### Pattern 19: Logging and Masking Annotations

**Glob Pattern:**
```bash
**/*Masking*.java
**/*Redactor.java
**/annotation/*Mask*.java
**/*Masked.java
```

**Usage Examples:**

```bash
# Find masking-related files
find . -name "*Masking*.java" -o -name "*Redactor.java"

# Find annotation definitions
find . -path "*/annotation/*" -name "*Mask*.java"

# Search for masking implementation
find . -name "*.java" -exec grep -l "@Masked\|Mask<T>" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/masking/Masking.java
./src/main/java/com/example/masking/Redactor.java
./src/main/java/com/example/annotation/Masked.java
./src/main/java/com/example/masking/StringMasker.java
```

**Indicates:** Data masking implementation; PII protection

---

### Pattern 20: Logging Configuration Files

**Glob Pattern:**
```bash
**/log4j*.xml
**/log4j*.properties
**/logback*.xml
**/logging*.xml
**/.*.log
```

**Usage Examples:**

```bash
# Find logging configuration
find . -name "log4j*.xml" -o -name "logback*.xml"

# Find logging properties
find . -name "log4j*.properties" -o -name "logging*.properties"

# List log files
find . -name "*.log" -o -name "*.log.*"

# Find application.properties with logging config
find . -name "*.properties" -exec grep -l "logging\." {} \;
```

**Expected Output:**
```
./src/main/resources/logback.xml
./src/main/resources/log4j2.xml
./src/main/resources/application.properties (contains: logging.level=)
./logs/application.log
```

**Indicates:** Logging framework configuration

---

### Pattern 21: Performance Monitoring

**Glob Pattern:**
```bash
**/*Trace*.java
**/*Metric*.java
**/*Monitor*.java
**/tracing/**Tracer*.java
```

**Usage Examples:**

```bash
# Find tracing classes
find . -name "*Trace*.java" -o -name "*Metric*.java" -o -name "*Monitor*.java"

# Find performance monitoring
find . -path "*/monitoring/*" -name "*.java"

# Search for trace bean usage
find . -name "*.java" -exec grep -l "@Trace\|@Metric\|@Monitor" {} \;
```

**Expected Output:**
```
./src/main/java/com/example/tracing/TraceContext.java
./src/main/java/com/example/metrics/MetricsCollector.java
./src/main/java/com/example/monitoring/PerformanceMonitor.java
```

**Indicates:** Performance monitoring configuration; tracing setup

---

## PROPERTIES & CONFIGURATION PATTERNS (4 Patterns)

Discover configuration files and property definitions.

### Pattern 22: Application Properties Files

**Glob Pattern:**
```bash
**/application.properties
**/application-*.properties
**/application.yml
**/application-*.yml
**/*.properties
**/*.yml
```

**Usage Examples:**

```bash
# Find all property files
find . -name "*.properties" -o -name "*.yml"

# Find application configuration
find . -name "application*.properties" -o -name "application*.yml"

# Find environment-specific properties
find . -name "application-dev.properties" -o -name "application-prod.properties"

# View MCA2 configuration properties
find . -name "*.properties" -exec grep -l "mca\." {} \;

# Count property files
find . -name "*.properties" | wc -l
```

**Expected Output:**
```
./src/main/resources/application.properties
./src/main/resources/application-dev.properties
./src/main/resources/application-prod.properties
./src/main/resources/application-staging.properties
./src/main/resources/context-config.properties
```

**Indicates:** Application configuration; environment profiles

---

### Pattern 23: Spring Boot Configuration Classes

**Glob Pattern:**
```bash
**/*Config.java
**/config/**Configuration.java
**/config/**Properties.java
**/properties/**Properties.java
```

**Usage Examples:**

```bash
# Find configuration classes
find . -path "*/config/*Config*.java" -o -name "*Configuration.java"

# Find property classes
find . -name "*Properties.java"

# Find all config-related files
find . -path "*/config/*" -name "*.java" | head -20

# Search for @Configuration annotation
find . -name "*.java" -exec grep -l "@Configuration" {} \;

# Count configuration classes
find ./src/main/java -path "*/config/*" -name "*.java" | wc -l
```

**Expected Output:**
```
./src/main/java/com/example/config/FilterConfig.java
./src/main/java/com/example/config/ContextConfig.java
./src/main/java/com/example/config/SecurityConfig.java
./src/main/java/com/example/properties/AppProperties.java
./src/main/java/com/example/config/DataSourceConfig.java
```

**Indicates:** Spring Boot configuration; application settings

---

### Pattern 24: YAML Configuration Files

**Glob Pattern:**
```bash
**/*.yml
**/*.yaml
**/config/*.yml
**/config/*.yaml
```

**Usage Examples:**

```bash
# Find YAML files
find . -name "*.yml" -o -name "*.yaml"

# Find YAML in config
find . -path "*/config/*" -name "*.yml"

# View YAML structure
find . -name "application*.yml" -exec cat {} \;

# Search for specific properties in YAML
find . -name "*.yml" -exec grep -l "mca\." {} \;
```

**Expected Output:**
```
./src/main/resources/application.yml
./src/main/resources/application-prod.yml
./config/kubernetes/config.yml
```

**Indicates:** YAML-based configuration

---

### Pattern 25: Environment Variable Definitions

**Glob Pattern:**
```bash
**/.env
**/.env.*
**/env.properties
**/docker-compose.yml
**/Dockerfile
**/kubernetes/*.yaml
```

**Usage Examples:**

```bash
# Find environment files
find . -name ".env" -o -name ".env.*"

# Find Docker configuration
find . -name "docker-compose.yml" -o -name "Dockerfile"

# Find Kubernetes manifests
find . -path "*/kubernetes/*" -name "*.yaml"

# View environment variables
find . -name ".env" -exec cat {} \;

# Search for MCA environment variables
find . -name ".env*" -exec grep "MCA\|mca" {} \;
```

**Expected Output:**
```
./docker-compose.yml
./Dockerfile
./kubernetes/deployment.yaml
./kubernetes/service.yaml
./.env.local
./.env.prod
```

**Indicates:** Environment configuration; container setup

---

## BUILD & DEPENDENCY PATTERNS (3 Patterns)

Discover build configuration and dependency declarations.

### Pattern 26: Dependency Declaration Files

**Glob Pattern:**
```bash
**/build.gradle
**/build.gradle.kts
**/pom.xml
**/Gemfile
**/requirements.txt
**/package.json
```

**Usage Examples:**

```bash
# Find all build files
find . -name "build.gradle" -o -name "pom.xml"

# Find Kotlin gradle files
find . -name "build.gradle.kts"

# Search for MCA dependencies
find . -name "build.gradle" -exec grep -l "mca-" {} \;

# View dependency declarations
find . -name "pom.xml" -o -name "build.gradle" | xargs wc -l | sort -rn

# Find specific MCA library
find . -name "*.gradle" -exec grep -l "mca-context" {} \;
```

**Expected Output:**
```
./build.gradle
./pom.xml
./mca-examples/mca-experience-api-cardcontrol-reference-app/build.gradle
```

**Indicates:** Dependency management; framework version

---

### Pattern 27: Test Configuration Files

**Glob Pattern:**
```bash
**/src/test/java/**/*.java
**/src/it/java/**/*.java
**/src/test/resources/**
**/test/**/*Test.java
```

**Usage Examples:**

```bash
# Find test directories
find . -path "*/src/test/java/*" -type d

# Find all test classes
find . -path "*/src/test/java/*" -name "*Test.java"

# Find integration tests
find . -path "*/src/it/java/*" -name "*.java"

# Count test files
find . -path "*/test/*" -name "*Test.java" | wc -l

# Find test configurations
find . -path "*/src/test/resources/*" -name "*.properties" -o -name "*.yml"
```

**Expected Output:**
```
./src/test/java/com/example/context/ContextTest.java
./src/test/java/com/example/filters/FilterChainTest.java
./src/it/java/com/example/integration/E2EIntegrationTest.java
./src/test/resources/application-test.properties
```

**Indicates:** Test implementation; test coverage

---

### Pattern 28: Documentation Files

**Glob Pattern:**
```bash
**/README.md
**/CHANGELOG.md
**/docs/**/*.md
**/documentation/**/*.md
**/Architecture.md
```

**Usage Examples:**

```bash
# Find documentation files
find . -name "README.md" -o -name "CHANGELOG.md"

# Find architecture documentation
find . -path "*/docs/*" -name "*.md" -o -name "*Architecture*.md"

# List all markdown files
find . -name "*.md" | head -20

# Search documentation for keywords
find . -name "*.md" -exec grep -l "MCA\|filter\|context" {} \;

# Count documentation
find . -name "*.md" | wc -l
```

**Expected Output:**
```
./README.md
./CHANGELOG.md
./docs/Architecture.md
./docs/Getting-Started.md
./docs/Configuration-Guide.md
```

**Indicates:** Documentation availability; implementation guides

---

## ADVANCED PATTERN COMBINATIONS (3 Patterns)

Multi-pattern searches for comprehensive discovery.

### Pattern 29: Complete Framework Integration Discovery

**Glob Pattern (Combined):**
```bash
# Find all key framework components at once
Application.java + *FilterConfig.java + *ContextConfig.java + application.properties + META-INF/spring/*.imports
```

**Usage Bash Script:**

```bash
#!/bin/bash
# Comprehensive MCA2 Framework Discovery

echo "=== MCA2 EPS Framework Discovery ==="
echo ""

echo "1. Framework Activation Points:"
find . -name "Application.java" -exec grep -l "@EnableExperienceAPI" {} \; 2>/dev/null || echo "No @EnableExperienceAPI found"
echo ""

echo "2. Filter Configuration:"
find . -name "*FilterConfig.java" 2>/dev/null || echo "No FilterConfig found"
echo ""

echo "3. Context Configuration:"
find . -name "*ContextConfig.java" 2>/dev/null || echo "No ContextConfig found"
echo ""

echo "4. Auto-Configuration Registration:"
find . -path "*/META-INF/spring/*.imports" -type f 2>/dev/null || echo "No auto-config imports found"
echo ""

echo "5. MCA Dependencies:"
find . -name "build.gradle" -exec grep "mca-" {} \; 2>/dev/null | head -5 || echo "No MCA dependencies found"
echo ""

echo "6. Filter Chain Files:"
find ./src/main/java -name "*Filter.java" 2>/dev/null | wc -l | xargs -I {} echo "Found {} filter files"
echo ""

echo "7. Context Classes:"
find ./src/main/java -name "*Context.java" 2>/dev/null | wc -l | xargs -I {} echo "Found {} context files"
echo ""

echo "8. Exception Handlers:"
find . -name "*ExceptionHandler.java" 2>/dev/null || echo "No exception handlers found"
```

**Expected Output:**
```
=== MCA2 EPS Framework Discovery ===

1. Framework Activation Points:
./src/main/java/com/example/Application.java

2. Filter Configuration:
./src/main/java/com/example/config/FilterConfig.java

3. Context Configuration:
./src/main/java/com/example/config/ContextConfig.java

4. Auto-Configuration Registration:
./src/main/resources/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports

5. MCA Dependencies:
implementation 'com.barclays.global.mca:mca-context:2.3.0'
implementation 'com.barclays.global.mca:mca-filter-core:2.3.0'

6. Filter Chain Files:
Found 5 filter files

7. Context Classes:
Found 12 context files

8. Exception Handlers:
./src/main/java/com/example/exception/GlobalExceptionHandler.java
```

**Indicates:** Full framework integration audit

---

### Pattern 30: Layered Architecture Validation

**Glob Pattern (Directory Structure):**
```bash
# Check proper layering: API -> Core -> Starter
**/api/**/*.java          # Interface/contract layer
**/core/**/*.java         # Implementation layer
**/starter/**/*.java      # Spring Boot auto-config layer
**/config/**/*.java       # Configuration layer
**/filter/**/*.java       # Request processing
**/context/**/*.java      # Context data model
```

**Usage Bash Script:**

```bash
#!/bin/bash
# Validate layered architecture

echo "=== Layered Architecture Validation ==="
echo ""

TOTAL_FILES=$(find ./src/main/java -name "*.java" | wc -l)
API_FILES=$(find ./src/main/java -path "*api*" -name "*.java" | wc -l)
CORE_FILES=$(find ./src/main/java -path "*core*" -name "*.java" | wc -l)
STARTER_FILES=$(find ./src/main/java -path "*starter*" -name "*.java" | wc -l)
CONFIG_FILES=$(find ./src/main/java -path "*config*" -name "*.java" | wc -l)

echo "Total source files: $TOTAL_FILES"
echo "API layer files: $API_FILES"
echo "Core layer files: $CORE_FILES"
echo "Starter layer files: $STARTER_FILES"
echo "Config layer files: $CONFIG_FILES"
echo ""

if [ $API_FILES -gt 0 ]; then
  echo "✓ API layer exists (interfaces/contracts)"
else
  echo "✗ Missing API layer"
fi

if [ $CORE_FILES -gt 0 ]; then
  echo "✓ Core layer exists (implementations)"
else
  echo "✗ Missing Core layer"
fi

if [ $STARTER_FILES -gt 0 ] || [ $CONFIG_FILES -gt 0 ]; then
  echo "✓ Auto-configuration layer exists"
else
  echo "✗ Missing auto-configuration layer"
fi
```

**Indicates:** Proper layering adherence

---

### Pattern 31: End-to-End Integration Test Coverage

**Glob Pattern (Test Directory Structure):**
```bash
# Locate comprehensive test coverage
**/src/test/java/**/unit/**Test.java       # Unit tests
**/src/test/java/**/integration/**Test.java # Integration tests
**/src/it/java/**/*.java                   # Separate IT source set
**/src/test/resources/**                   # Test fixtures
```

**Usage Bash Script:**

```bash
#!/bin/bash
# Assess test coverage and structure

echo "=== Test Coverage Assessment ==="
echo ""

UNIT_TESTS=$(find ./src/test/java -name "*Test.java" | wc -l)
IT_TESTS=$(find ./src/it/java -name "*.java" 2>/dev/null | wc -l)
TEST_RESOURCES=$(find ./src/test/resources -type f 2>/dev/null | wc -l)

echo "Unit tests: $UNIT_TESTS"
echo "Integration tests: $IT_TESTS"
echo "Test resources (fixtures, config): $TEST_RESOURCES"
echo ""

if [ $UNIT_TESTS -gt 0 ]; then
  echo "✓ Unit tests present"
  echo "  Sample tests:"
  find ./src/test/java -name "*Test.java" | head -3
fi

echo ""

if [ $IT_TESTS -gt 0 ]; then
  echo "✓ Integration tests (separate source set)"
  echo "  Sample tests:"
  find ./src/it/java -name "*.java" 2>/dev/null | head -3
else
  echo "ℹ No separate IT source set (using src/test/java)"
fi

echo ""

if [ $TEST_RESOURCES -gt 0 ]; then
  echo "✓ Test resources configured"
fi
```

**Indicates:** Test infrastructure completeness

---

## QUICK REFERENCE TABLE

| Pattern # | Name | Glob Pattern | Purpose |
|-----------|------|--------------|---------|
| 1 | Filter Files | **/filters/*Filter.java | Filter implementations |
| 2 | Filter Config | **/config/*FilterConfig.java | Filter setup |
| 3 | Spring Auto-Config | **/META-INF/spring/*.imports | Auto-configuration |
| 4 | Filter Properties | **/resources/**filter*.properties | Filter config |
| 5 | Filter Classes | **/*Filter.java | All filter classes |
| 6 | Context Classes | **/*Context.java | Context implementations |
| 7 | IOLSchema | **/IOLSchema.java | Context data model |
| 7a | Context Store | **/*ContextStore*.java | Secure Proxy storage |
| 8 | Context Config | **/*ContextConfig.java | Context setup |
| 9 | Context Utils | **/utils/*Context*.java | Context helpers |
| 10 | Context Tests | **/test/java/**/*Context*Test.java | Context tests |
| 11 | Application Class | **/Application.java | Main entry point |
| 12 | EPS Config | **/*EpsConfig.java | EPS setup |
| 13 | Gradle Build | **/build.gradle | Gradle config |
| 14 | Maven Build | **/pom.xml | Maven config |
| 15 | Exception Classes | **/*Exception.java | Exception types |
| 16 | Exception Handlers | **/*ExceptionHandler.java | Error handling |
| 17 | Response Classes | **/*Response.java | Response types |
| 18 | Serializers | **/*Serializer.java | Data serialization |
| 19 | Masking | **/*Masking*.java | Data protection |
| 20 | Logging Config | **/log*.xml, **/logging*.xml | Logging setup |
| 21 | Performance Monitoring | **/*Trace*.java, **/*Metric*.java | Monitoring |
| 22 | Application Properties | **/application*.properties | App config |
| 23 | Configuration Classes | **/config/**Config.java | Spring config |
| 24 | YAML Config | **/*.yml | YAML config |
| 25 | Environment Config | **/.env, **/docker-compose.yml | Environment |
| 26 | Dependencies | **/build.gradle, **/pom.xml | Build deps |
| 27 | Tests | **/src/test/java/**Test.java | Test code |
| 28 | Documentation | **/*.md | Documentation |
| 29 | Framework Discovery | Combined patterns | Complete audit |
| 30 | Architecture Validation | **/api/**/**, **/core/**/* | Layering check |
| 31 | Test Coverage | **/test/java/**, **/it/java/** | Test quality |

---

## INTEGRATION WITH TOOLS

### Using find Command

```bash
# Basic find with glob patterns
find . -path "*/config/*Filter*.java" -type f

# Find with multiple patterns
find . \( -name "*Filter.java" -o -name "*Context.java" \) -type f

# Find and execute (count lines)
find . -name "*Filter.java" -exec wc -l {} \; | awk '{sum+=$1} END {print sum " total lines"}'

# Find with size criteria
find . -name "*Context.java" -size +100c -type f
```

### Using fd Command (Faster Alternative)

```bash
# Install: brew install fd (macOS) or apt-get install fd-find (Linux)
fd "Filter\.java$" src/

# Multiple patterns
fd "Filter\.java$|Context\.java$" src/

# Exclude patterns
fd "\.java$" src/ --exclude test

# Type filtering
fd "\.java$" src/ --type f
```

### Using locate (Requires System Database)

```bash
# Update database (periodic cron job)
sudo updatedb

# Locate files
locate "mca-context/src/main"

# Case-insensitive
locate -i "filterconfig.java"
```

### Using ripgrep (With Glob Support)

```bash
# Find files by glob
rg -l "IOLSchema" --glob "**/*Context.java"

# Multiple globs
rg -l "Filter" --glob "**/*Filter.java" --glob "**/*Config.java"

# Type filtering
rg -l "context" --type java src/main/
```

---

## PATTERN USAGE SCRIPTS

### Complete Discovery Script

```bash
#!/bin/bash
# mca2-file-discovery.sh - Complete file discovery

APP_PATH=${1:-.}

{
  echo "=== MCA2 EPS Framework File Discovery ==="
  echo "Directory: $APP_PATH"
  echo "Timestamp: $(date)"
  echo ""

  echo "FILTER CHAIN:"
  echo "  Custom Filters: $(find $APP_PATH -path "*/filters/*Filter.java" | wc -l)"
  echo "  Filter Config: $(find $APP_PATH -name "*FilterConfig.java" | wc -l)"
  echo ""

  echo "CONTEXT SYSTEM:"
  echo "  Context Classes: $(find $APP_PATH -name "*Context.java" | wc -l)"
  echo ""

  echo "SECURE PROXY:"
  echo "  Context Store (Secure Proxy): $(find $APP_PATH -name "*ContextStore*.java" | wc -l)"
  echo ""

  echo "EXCEPTION HANDLING:"
  echo "  Exception Classes: $(find $APP_PATH -name "*Exception.java" | wc -l)"
  echo "  Exception Handlers: $(find $APP_PATH -name "*ExceptionHandler.java" | wc -l)"
  echo ""

  echo "CONFIGURATION:"
  echo "  Property Files: $(find $APP_PATH -name "*.properties" | wc -l)"
  echo "  YAML Files: $(find $APP_PATH -name "*.yml" -o -name "*.yaml" | wc -l)"
  echo "  Config Classes: $(find $APP_PATH -path "*/config/*" -name "*Config.java" | wc -l)"
  echo ""

  echo "BUILD & DEPENDENCIES:"
  echo "  Build Files: $(find $APP_PATH -name "build.gradle" -o -name "pom.xml" | wc -l)"
  echo "  Tests: $(find $APP_PATH -path "*/test/*" -name "*Test.java" | wc -l)"
  echo ""

  echo "DETAILED FILE LIST:"
  echo ""
  echo "Application Entry Point:"
  find $APP_PATH -maxdepth 3 -name "Application.java" -exec echo "  {}" \;
  echo ""

  echo "Filter Chain Components:"
  find $APP_PATH -name "*Filter*.java" | head -5 | xargs -I {} echo "  {}"
  echo ""

  echo "Context Components:"
  find $APP_PATH -name "*Context*.java" | head -5 | xargs -I {} echo "  {}"

} | tee mca2-discovery-$(date +%Y%m%d-%H%M%S).txt
```

### Comparison Script (Before/After Analysis)

```bash
#!/bin/bash
# Compare file structure before and after refactoring

BEFORE_SNAPSHOT=$1
AFTER_SNAPSHOT=$2

echo "=== MCA2 EPS Framework Refactoring Analysis ==="
echo ""

echo "BEFORE:"
cat $BEFORE_SNAPSHOT | grep -E "^  [A-Z]"
echo ""

echo "AFTER:"
cat $AFTER_SNAPSHOT | grep -E "^  [A-Z]"
echo ""

echo "CHANGES:"
diff <(cat $BEFORE_SNAPSHOT | grep ":" | cut -d: -f2) \
     <(cat $AFTER_SNAPSHOT | grep ":" | cut -d: -f2)
```

---

## PERFORMANCE TIPS

### Fast Discovery on Large Codebases

```bash
# Exclude common slow directories
find . -name "*.java" -type f \
  -not -path "*/node_modules/*" \
  -not -path "*/build/*" \
  -not -path "*/.gradle/*" \
  -not -path "*/.m2/*"

# Use fd (significantly faster)
fd "Filter\.java$" src/ --exclude build --exclude .gradle

# Limit depth for quick scans
find . -maxdepth 3 -name "*Application.java"
```

### Caching Results

```bash
# Cache discovery results
find . -name "*.java" -path "*/config/*" > config_files.cache

# Use cached results
cat config_files.cache | wc -l

# Invalidate cache when appropriate
rm config_files.cache
```

---

**Glob Patterns provides 31 file-based discovery patterns for comprehensive MCA2 EPS framework detection.**

