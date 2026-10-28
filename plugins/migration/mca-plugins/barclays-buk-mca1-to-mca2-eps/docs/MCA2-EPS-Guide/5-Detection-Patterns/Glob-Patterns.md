# Glob Patterns: File Discovery

## Executive Summary

File-based patterns (glob expressions) to locate EPS framework files in codebases. These patterns work with file explorers, IDE search, and command-line glob tools.

**Tools:**
- IDEs: IntelliJ "Open by Pattern", VS Code "Search by Pattern"
- CLI: `find`, `glob`, or IDE-specific tools
- Git: `git ls-files <pattern>`

---

## CONFIGURATION FILES (5 patterns)

### Pattern 1: Spring Boot Auto-Configuration Registration

**Glob:** `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports`

**What it detects:** Framework auto-configuration declarations

```bash
# Find auto-config registration
find . -path "*/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports"

# Example content should contain:
# com.barclays.global.mca.libs.eps.config.ExperienceAPIConfig
# com.barclays.global.mca.libs.context.config.ContextAutoConfiguration
```

### Pattern 2: Environment Post-Processors

**Glob:** `META-INF/spring/org.springframework.boot.EnvironmentPostProcessor.imports`

**What it detects:** Early property configuration

```bash
find . -path "*/META-INF/spring/org.springframework.boot.EnvironmentPostProcessor.imports"

# Example content:
# com.barclays.global.mca.libs.context.processor.ContextPropertyPostProcessor
```

### Pattern 3: Spring Configuration Metadata

**Glob:** `META-INF/spring-configuration-metadata.json`

**What it detects:** IDE autocomplete configuration

```bash
find . -path "*/META-INF/spring-configuration-metadata.json"

# Indicates IDE support for properties
```

### Pattern 4: Property Files - Default

**Glob:** `**/application.properties`

**What it detects:** Default property configuration

```bash
find . -path "*/application.properties"

# Check for:
# mca.eps.enabled=true
# logging.level.com.barclays.global.mca=...
```

### Pattern 5: Property Files - Profile-Specific

**Glob:** `**/application-{dev,test,prod}.properties`

**What it detects:** Environment-specific configurations

```bash
find . -path "*/application-*.properties"

# Should find: application-dev.properties, application-prod.properties, etc.
```

---

## FILTER CLASSES (3 patterns)

### Pattern 6: Filter Implementations

**Glob:** `**/src/main/java/**/*Filter.java`

**What it detects:** Filter class files

```bash
find . -path "*/src/main/java/**/*Filter.java"

# Expected files:
# CorrelationIdFilter.java
# ExceptionFilter.java
# CustomAuthFilter.java (application-specific)
```

### Pattern 7: Filter Configuration Classes

**Glob:** `**/*FilterConfig.java` OR `**/*FilterConfiguration.java`

**What it detects:** Filter registration configurations

```bash
find . -path "**/*Filter{Config,Configuration}.java"

# Example:
# CoreFilterConfig.java
# CustomFilterConfig.java
```

### Pattern 8: Servlet Configuration

**Glob:** `**/*ServletConfig.java` OR `**/*WebMvcConfig.java`

**What it detects:** Web layer configuration

```bash
find . -path "**/*{ServletConfig,WebMvcConfig}.java"
```

---

## CONTEXT SYSTEM FILES (3 patterns)

### Pattern 9: Context Classes

**Glob:** `**/src/main/java/**/*Context.java`

**What it detects:** Context data model classes

```bash
find . -path "*/src/main/java/**/*Context.java"

# Expected:
# UserContext.java
# CustomerContext.java
# AccountContext.java
# ProcessContext.java
# etc.
```

### Pattern 10: IOL Schema

**Glob:** `**/IOLSchema.java`

**What it detects:** Root IOL container

```bash
find . -path "*/IOLSchema.java"

# Should find exactly one: the context root container
```

### Pattern 11: Web Utils

**Glob:** `**/WebUtils.java`

**What it detects:** Request scope utilities

```bash
find . -path "*/WebUtils.java"

# Should find the utility class for context access
```

---

## EXCEPTION CLASSES (2 patterns)

### Pattern 13: Exception Hierarchy Files

**Glob:** `**/src/main/java/**/*Exception.java`

**What it detects:** All exception classes

```bash
find . -path "*/src/main/java/**/*Exception.java"

# Should find:
# GenericException.java
# ApplicationException.java
# NotFoundException.java
# AuthorizationException.java
# RequestException.java
# ServerException.java
```

### Pattern 14: Exception Handlers

**Glob:** `**/*ExceptionHandler.java` OR `**/*ControllerAdvice.java`

**What it detects:** Global exception handlers

```bash
find . -path "**/*{ExceptionHandler,ControllerAdvice}.java"

# Spring error handling configuration
```

---

## RESPONSE HANDLING FILES (2 patterns)

### Pattern 15: Response Classes

**Glob:** `**/Response.java` OR `**/ResponseEntity*.java`

**What it detects:** Response envelope classes

```bash
find . -path "*/Response.java"

# Should find the generic Response<T> container
```

### Pattern 16: Response Assemblers

**Glob:** `**/src/main/java/**/*ResponseAssembler.java` OR `**/src/main/java/**/*Assembler.java`

**What it detects:** Response building utilities

```bash
find . -path "*/src/main/java/**/*Assembler.java"

# Should find ResponseAssembler, SuccessResponseAssembler, ErrorResponseAssembler
```

---

## TEST FILES (3 patterns)

### Pattern 17: Integration Tests

**Glob:** `**/src/it/java/**/*IntegrationTest.java` OR `**/src/it/java/**/*Test.java`

**What it detects:** Integration test suites

```bash
find . -path "*/src/it/java/**/*Test.java"

# Should find integration tests for EPS components
```

### Pattern 18: Unit Tests

**Glob:** `**/src/test/java/**/*Test.java`

**What it detects:** Unit test files

```bash
find . -path "*/src/test/java/**/*Test.java" | head -20

# Count: indicates test coverage
```

### Pattern 19: Test Configuration

**Glob:** `**/src/test/java/**/*TestConfig.java` OR `**/src/test/resources/application-test.properties`

**What it detects:** Test environment setup

```bash
find . -path "*/src/test/**/*{TestConfig,application-test.properties}"
```

---

## BUILD FILES (3 patterns)

### Pattern 20: Gradle Build Files

**Glob:** `**/build.gradle` (at module level)

**What it detects:** Module build configuration

```bash
find . -path "*/build.gradle" -type f

# Count: number of modules
# Check each for: implementation 'com.barclays.global.mca:*'
```

### Pattern 21: Gradle Wrapper

**Glob:** `gradle/wrapper/gradle-wrapper.properties`

**What it detects:** Gradle version

```bash
find . -path "*/gradle/wrapper/gradle-wrapper.properties"

# Should show gradle version (8.5+)
```

### Pattern 22: Dependency Management

**Glob:** `**/pom.xml` OR `**/build.gradle` (looking for BOM imports)

**What it detects:** Dependency management configuration

```bash
grep -r "mca-java-common-bom" . --include="pom.xml" --include="build.gradle"

# Shows BOM usage for version management
```

---

## DOCUMENTATION & CONFIGURATION (2 patterns)

### Pattern 23: README Files

**Glob:** `**/README.md`

**What it detects:** Documentation

```bash
find . -path "*/README.md" | grep -E "(src/|mca-|lib)" | head -10
```

### Pattern 24: Configuration Classes

**Glob:** `**/src/main/java/**/*Config.java` OR `**/src/main/java/**/*Configuration.java`

**What it detects:** All configuration files

```bash
find . -path "*/src/main/java/**/*{Config,Configuration}.java"

# Should find:
# ExperienceAPIConfig.java
# CoreFilterConfig.java
# etc.
```

---

## APPLICATION CLASS (1 pattern)

### Pattern 25: Main Application Class

**Glob:** `**/Application.java` OR `**/[A-Z]*Application.java`

**What it detects:** Spring Boot entry point

```bash
find . -path "*/src/main/java/**/*Application.java" | grep -v Test

# Should find exactly one (per module)
# Check it has: @SpringBootApplication, @EnableExperienceAPI, @Enable*
```

---

## EXTENDED PATTERNS: Detection Recipes

### Recipe 1: Find All MCA Dependencies

```bash
# In build.gradle
grep -r "com.barclays.global.mca" . --include="build.gradle" | sort | uniq

# In pom.xml
grep -r "com.barclays.global.mca" . --include="pom.xml" | sort | uniq
```

### Recipe 2: Locate Application Class and Verify Enablement

```bash
# Find main application
find . -path "*/src/main/java/**/*Application.java" -not -path "*/test/*"

# Then check for @Enable annotations
grep -A 5 "@SpringBootApplication" [APPLICATION_FILE]
```

### Recipe 3: Find All Properties Files and Their Content

```bash
# Find all property files
find . -path "*/application*.properties" -o -path "*/application*.yml"

# Check for EPS configuration in each
grep -l "mca.eps\|masking.enabled" $(find . -path "*/application*.properties")
```

### Recipe 4: Verify Filter Chain Setup

```bash
# Find filter config
find . -path "**/src/main/java/**/*FilterConfig.java"

# Count filters in that file
grep -c "FilterRegistrationBean" [FILTER_CONFIG_FILE]

# Verify ordering
grep "setOrder" [FILTER_CONFIG_FILE] | sort -t'(' -k2 -n
```

### Recipe 5: Extract All Exception Types

```bash
# Find all exceptions in application
find . -path "*/src/main/java/**/*Exception.java" \
  | xargs grep -l "extends GenericException"

# Count them
find . -path "*/src/main/java/**/*Exception.java" \
  | xargs grep "extends GenericException" | wc -l
```

---

## IDE SEARCH EXAMPLES

### IntelliJ IDEA

```
# File → Open by Pattern
Ctrl+Cmd+O (Mac) or Ctrl+Shift+O (Windows/Linux)

# Search patterns:
**/src/main/java/**/*Filter.java
**/application*.properties
**/META-INF/spring/*.imports
```

### VS Code

```
# File → Go to File (Cmd+P or Ctrl+P)

# Then search by pattern:
**/Application.java
**/build.gradle
**/src/main/java/**/*Filter.java
```

---

## Git Integration

### Find Committed EPS Files

```bash
# List all files with EPS patterns
git ls-files | grep -E "(Filter|Context|Exception|Response)\.java"

# Count EPS files by type
git ls-files | grep -c "Filter\.java"
git ls-files | grep -c "Context\.java"
git ls-files | grep -c "Exception\.java"
```

### Show Recent EPS Changes

```bash
# Recent commits touching EPS
git log --name-only --oneline | grep -E "(Filter|Context|Exception|Response)\.java" | head -20

# Show diff for specific file type
git log -p -- "*/src/main/java/**/*Filter.java" | head -100
```

---

## Analysis Script: Find Framework Integration Level

```bash
#!/bin/bash
# save as detect-framework-files.sh

echo "=== MCA2 EPS Framework File Detection ==="
echo

echo "Configuration Files:"
echo -n "  Auto-configs: "
find . -path "*/META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports" 2>/dev/null | wc -l

echo -n "  Properties: "
find . -path "*/application*.properties" -o -path "*/application*.yml" 2>/dev/null | wc -l

echo
echo "Framework Classes:"
echo -n "  Filters: "
find . -path "*/src/main/java/**/*Filter.java" 2>/dev/null | wc -l

echo -n "  Context classes: "
find . -path "*/src/main/java/**/*Context.java" 2>/dev/null | wc -l

echo -n "  Exception classes: "
find . -path "*/src/main/java/**/*Exception.java" 2>/dev/null | wc -l

echo -n "  Response classes: "
find . -path "*/src/main/java/**/Response*.java" 2>/dev/null | wc -l

echo
echo "Configuration Classes:"
echo -n "  Config files: "
find . -path "*/src/main/java/**/*Config*.java" 2>/dev/null | wc -l

echo
echo "Test Files:"
echo -n "  Integration tests: "
find . -path "*/src/it/java/**/*Test.java" 2>/dev/null | wc -l

echo -n "  Unit tests: "
find . -path "*/src/test/java/**/*Test.java" 2>/dev/null | wc -l

echo
echo "Build Files:"
echo -n "  Gradle modules: "
find . -name "build.gradle" -not -path "./.gradle/*" 2>/dev/null | wc -l

echo -n "  Maven modules: "
find . -name "pom.xml" 2>/dev/null | wc -l
```

---

## Quick Reference: Most Important Globs

```
# Configuration setup
**/application*.properties
**/META-INF/spring/*.imports
**/src/main/java/**/*Application.java

# Core framework files
**/src/main/java/**/*Filter.java
**/src/main/java/**/*Context.java
**/src/main/java/**/*Exception.java

# Configuration
**/src/main/java/**/*Config*.java
**/build.gradle

# Tests
**/src/it/java/**/*Test.java
**/src/test/java/**/*Test.java
```

**Glob Patterns provide file-system discovery of EPS framework integration.**
