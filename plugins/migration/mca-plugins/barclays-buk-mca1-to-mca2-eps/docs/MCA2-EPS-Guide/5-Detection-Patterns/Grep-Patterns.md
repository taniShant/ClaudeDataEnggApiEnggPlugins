# Grep Patterns: EPS Framework Detection

## Executive Summary

This document provides 30+ searchable regex patterns (grep/ripgrep) to detect MCA2 EPS framework usage in Java applications. Patterns are organized by framework component and ready to copy-paste for automated codebase analysis.

**Tools:** These patterns work with:
- `grep -r "pattern" src/`
- `rg "pattern" src/` (ripgrep - faster)
- Most IDEs' find/search functionality

---

## FILTER CHAIN PATTERNS (8 patterns)

### Pattern 1: Filter Class Inheritance

**Pattern:** `extends OncePerRequestFilter`

**Description:** Finds all custom filter implementations

```bash
# Grep command
grep -r "extends OncePerRequestFilter" src/ --include="*.java"

# Ripgrep command (faster)
rg "extends OncePerRequestFilter" src/ --type java

# Expected matches in MCA2:
# CorrelationIdFilter.java
# ExceptionFilter.java
# DisableSessionFilter.java
# MultiReadRequestFilter.java
# OAuthValidatorFilter.java
# DdosFilter.java
# ValidationFilter.java
# RequestWhitelistingFilter.java
# DynamicLoggingFilter.java
# PerfLogExclusionFilter.java
```

### Pattern 2: FilterChain.doFilter() Calls

**Pattern:** `filterChain\.doFilter\(`

**Description:** Verifies filters correctly chain to next filter (every filter should call this)

```bash
rg "filterChain\.doFilter\(" src/ --type java

# Every filter doFilterInternal() should have this call
# Missing this = broken filter chain
```

### Pattern 3: FilterRegistrationBean Usage

**Pattern:** `FilterRegistrationBean<`

**Description:** Detects all filter registrations

```bash
rg "FilterRegistrationBean<" src/ --type java

# Output should show all custom filters being registered
# Check that setOrder() is called for each
```

### Pattern 4: Filter Configuration Classes

**Pattern:** `@Bean.*FilterRegistrationBean`

**Description:** Finds all filter configuration methods

```bash
rg -A 5 "public.*FilterRegistrationBean" src/ --type java

# Shows filter configurations with their order values
```

### Pattern 5: shouldNotFilter Implementation

**Pattern:** `protected boolean shouldNotFilter\(`

**Description:** Detects filters with path exclusions

```bash
rg "protected boolean shouldNotFilter" src/ --type java

# Count: should match number of filters with exclusions
```

### Pattern 6: try-finally in Filters

**Pattern:** `try \{.*filterChain.*finally`

**Description:** Ensures proper cleanup in filters (multiline pattern)

```bash
rg -U "try \{.*?filterChain.*?finally" src/ --type java --multiline

# Critical: Every filter should use try-finally for cleanup
```

### Pattern 7: Filter Order Assignment

**Pattern:** `bean\.setOrder\((\d+)\)`

**Description:** Extracts all filter order values

```bash
rg "bean\.setOrder\((\d+)\)" src/ --type java -o '$1'

# Check ordering is correct: 0,1,2,3,4,5,6,7,8,9,10...
```

### Pattern 8: Missing FilterChain Calls

**Pattern:** `doFilterInternal.*\}(?!.*filterChain\.doFilter)`

**Description:** CRITICAL - finds filters that don't call doFilter() (multiline)

```bash
rg -U "protected void doFilterInternal.*?\n.*?\n.*?\}" src/ --type java --multiline | \
  grep -v "filterChain.doFilter" | head -5

# Any match = BROKEN filter (chain stops here)
```

---

## CONTEXT SYSTEM PATTERNS (5 patterns)

### Pattern 9: IOLSchema Usage

**Pattern:** `IOLSchema`

**Description:** Finds all IOL context schema usage

```bash
rg "IOLSchema" src/ --type java

# Count: high usage indicates context system integration
```

### Pattern 10: ContextFilter Detection

**Pattern:** `class.*ContextFilter`

**Description:** Finds context filter implementations

```bash
rg "class.*ContextFilter" src/ --type java

# Should find ContextFilter in mca-filter-core
```

### Pattern 11: @IOLContext Annotation

**Pattern:** `@IOLContext`

**Description:** Detects context injection in controllers

```bash
rg "@IOLContext" src/ --type java

# Count: number of methods using context injection
# Each should be a request parameter
```

### Pattern 12: WebUtils Context Access

**Pattern:** `WebUtils\.get.*Context\(\)`

**Description:** Detects context access in services

```bash
rg "WebUtils\.get.*Context\(" src/ --type java

# Shows where services access request context
```

### Pattern 13: Context HTTP Headers

**Pattern:** `X-.*Context`

**Description:** Finds context header usage

```bash
rg "X-.*Context" src/ --type java

# Should include: X-UserContext, X-CustomerContext, X-AccountContext, etc.
```

---

## EXCEPTION HANDLING PATTERNS (5 patterns)

### Pattern 16: GenericException Hierarchy

**Pattern:** `extends GenericException`

**Description:** Finds all exception types

```bash
rg "extends GenericException" src/ --type java

# Should find: ApplicationException, RequestException, NotFoundException, AuthorizationException, ServerException
```

### Pattern 17: Exception Throwing

**Pattern:** `throw new (ApplicationException|NotFoundException|AuthorizationException|ServerException|RequestException)`

**Description:** Detects exception usage

```bash
rg "throw new (ApplicationException|NotFoundException|AuthorizationException|ServerException|RequestException)" src/ --type java

# Count: number of places throwing MCA2 exceptions
```

### Pattern 18: ResponseHttpStatus Mapping

**Pattern:** `ResponseHttpStatus`

**Description:** Finds HTTP status mapping usage

```bash
rg "ResponseHttpStatus" src/ --type java

# Should be in ExceptionFilter and error handlers
```

### Pattern 19: Error Response Building

**Pattern:** `Response\s*\.\s*assemble\(\)\s*\.\s*error`

**Description:** Detects error response building

```bash
rg "Response\s*\.\s*assemble\(\)\s*\.\s*error" src/ --type java

# Should be in exception handlers
```

### Pattern 20: GenericException Catch

**Pattern:** `catch\s*\(\s*GenericException`

**Description:** Finds exception handling blocks

```bash
rg "catch\s*\(\s*GenericException" src/ --type java

# Count: exception handling coverage
```

---

## RESPONSE HANDLING PATTERNS (4 patterns)

### Pattern 21: Response Assembly

**Pattern:** `Response\s*\.\s*assemble\(\)`

**Description:** Detects response building via fluent API

```bash
rg "Response\s*\.\s*assemble\(\)" src/ --type java

# Every REST endpoint should use this pattern
```

### Pattern 22: Success Response

**Pattern:** `\.build\(`

**Description:** Finds successful response building

```bash
rg "\.assemble\(\).*\.build\(" src/ --type java

# Matches: Response.assemble().build(data)
```

### Pattern 23: Response Entity Wrapping

**Pattern:** `ResponseEntity<Response`

**Description:** Detects Response envelope usage

```bash
rg "ResponseEntity<Response" src/ --type java

# Should wrap all REST responses
```

### Pattern 24: Null Inclusion Annotation

**Pattern:** `@JsonInclude`

**Description:** Finds JSON serialization configuration

```bash
rg "@JsonInclude" src/ --type java

# Should be on Response class (NON_NULL)
```

---

## ENABLE ANNOTATIONS PATTERNS (5 patterns)

### Pattern 25: @EnableExperienceAPI

**Pattern:** `@EnableExperienceAPI`

**Description:** Finds core EPS framework enablement

```bash
rg "@EnableExperienceAPI" src/ --type java

# Should appear in main Application class
# Count: 1 per application
```

### Pattern 26: Optional Framework Enablement

**Pattern:** `@Enable(SecureProxy|Router|Masking|MisServiceClient)`

**Description:** Detects optional framework features

```bash
rg "@Enable(SecureProxy|Router|Masking|MisServiceClient)" src/ --type java

# Count: shows which optional features are enabled
```

### Pattern 28: Configuration Properties

**Pattern:** `@ConfigurationProperties`

**Description:** Finds property binding classes

```bash
rg "@ConfigurationProperties" src/ --type java

# Should be for each configurable framework
```

### Pattern 29: Conditional Bean Registration

**Pattern:** `@ConditionalOnProperty`

**Description:** Detects conditional feature flags

```bash
rg "@ConditionalOnProperty" src/ --type java

# Count: number of conditional features
```

### Pattern 30: Enable Annotation in Application Class

**Pattern:** `@SpringBootApplication.*@Enable`

**Description:** Verifies application properly enables frameworks

```bash
rg -A 10 "@SpringBootApplication" src/ --type java | grep -c "@Enable"

# Should have at least @EnableExperienceAPI
```

---

## LOGGING & MASKING PATTERNS (3 patterns)

### Pattern 31: SLF4J Logger

**Pattern:** `LoggerFactory\.getLogger`

**Description:** Detects SLF4J usage

```bash
rg "LoggerFactory\.getLogger" src/ --type java

# Count: number of logging integration points
```

### Pattern 32: Masking Annotations

**Pattern:** `@Masked`

**Description:** Finds data masking application

```bash
rg "@Masked" src/ --type java

# Count: how many fields/parameters are masked
```

### Pattern 33: Masking Configuration

**Pattern:** `masking\.patterns\.|MaskingService`

**Description:** Detects masking setup

```bash
rg "masking\.patterns\.|MaskingService" src/ --type java

# Should be in configuration
```

---

## USAGE: Running Detection Patterns

### Single Pattern Search

```bash
# Search for one pattern
rg "@EnableExperienceAPI" src/ --type java

# Output:
# src/main/java/com/example/Application.java:5:@EnableExperienceAPI
```

### Multiple Patterns (Organized)

```bash
# Check filter chain
echo "=== FILTER CHAIN PATTERNS ==="
rg "extends OncePerRequestFilter" src/ --type java | wc -l
rg "filterChain\.doFilter\(" src/ --type java | wc -l
rg "bean\.setOrder\(" src/ --type java | wc -l

# Check context system
echo "=== CONTEXT SYSTEM PATTERNS ==="
rg "@IOLContext" src/ --type java | wc -l
rg "WebUtils\.get.*Context" src/ --type java | wc -l

# Check exceptions
echo "=== EXCEPTION PATTERNS ==="
rg "extends GenericException" src/ --type java | wc -l
rg "throw new.*Exception" src/ --type java | wc -l
```

### Generate Detection Report

```bash
#!/bin/bash
# save as detect-mca2.sh

echo "MCA2 EPS Framework Detection Report"
echo "===================================="
echo

echo "FILTER CHAIN:"
echo "  Filters: $(rg 'extends OncePerRequestFilter' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo "  Chain calls: $(rg 'filterChain\.doFilter\(' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo "  Filter registrations: $(rg 'FilterRegistrationBean<' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo

echo "CONTEXT SYSTEM:"
echo "  @IOLContext usage: $(rg '@IOLContext' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo "  WebUtils access: $(rg 'WebUtils\.get.*Context' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo

echo "EXCEPTIONS:"
echo "  Exception types: $(rg 'extends GenericException' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo "  Exception throws: $(rg 'throw new.*Exception' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo

echo "ENABLEMENT:"
echo "  @EnableExperienceAPI: $(rg '@EnableExperienceAPI' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo

echo "SECURITY & MASKING:"
echo "  Masking configured: $(rg '@Masked|masking\.patterns' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
echo "  OAuth enabled: $(rg '@ConditionalOnProperty.*oauth' src/ --type java -c | awk '{sum+=$1} END {print sum}')"
```

---

## Pattern Combinations: Complex Queries

### Find All Filter Classes with Order

```bash
rg -B 2 "bean\.setOrder" src/ --type java

# Output shows filter and order together
```

### Find Filters Missing doFilter Calls

```bash
# WARNING: This is complex multiline pattern
rg -U "public class.*extends OncePerRequestFilter.*?\}" src/ --type java --multiline | \
  grep -v "filterChain.doFilter" | head -5

# Result: BROKEN filters (missing chain calls)
```

### Find All @Enable Annotations in Application

```bash
rg "@SpringBootApplication" -A 20 src/ --type java | rg "@Enable"

# Shows all enabled frameworks
```

---

## Interpreting Results

| Count | Interpretation |
|-------|-----------------|
| @EnableExperienceAPI = 0 | EPS not enabled (problem!) |
| @EnableExperienceAPI = 1 | Correct (enabled once) |
| @EnableExperienceAPI > 1 | Duplicate enables (unusual) |
| Filters extending OncePerRequestFilter > 10 | Core + many custom filters |
| @IOLContext = 0 | Context not injected (maybe using WebUtils instead) |

---

## Next Steps

1. **Run pattern detection** — Execute patterns on your codebase
2. **Review results** — Compare with expected counts
3. **Identify gaps** — Missing patterns indicate incomplete integration
4. **Create custom patterns** — Add app-specific patterns

---

## Quick Reference: Copy-Paste Patterns

```bash
# Most useful single command - finds framework adoption score
rg "@EnableExperienceAPI|@IOLContext|extends GenericException|Response\.assemble" src/ --type java | wc -l

# High count = Good framework integration
# Low count = Limited framework adoption
```

**Grep Patterns provide automated detection of MCA2 framework usage across codebases.**
