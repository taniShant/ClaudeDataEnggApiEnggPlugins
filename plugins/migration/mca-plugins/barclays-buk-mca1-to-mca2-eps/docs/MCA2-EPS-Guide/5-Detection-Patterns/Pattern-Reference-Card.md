# Pattern Reference Card: Quick Lookup

## One-Page Quick Reference for All Detection Patterns

---

## FILTER CHAIN PATTERNS

| # | Pattern | Type | Command | Expected Matches |
|---|---------|------|---------|------------------|
| 1 | `extends OncePerRequestFilter` | Grep | `rg "extends OncePerRequestFilter" src/` | 3-5 filters |
| 2 | `filterChain\.doFilter\(` | Grep | `rg "filterChain\.doFilter\(" src/` | ≥ 3 |
| 3 | `FilterRegistrationBean<` | Grep | `rg "FilterRegistrationBean<" src/` | ≥ 3 |
| 4 | `bean\.setOrder\(` | Grep | `rg "bean\.setOrder\(" src/` | ≥ 3 |
| 5 | `protected boolean shouldNotFilter` | Grep | `rg "protected boolean shouldNotFilter" src/` | 0-5 |
| 6 | `**/src/main/java/**/*Filter.java` | Glob | `find . -path "*/src/main/java/**/*Filter.java"` | 3-10 files |
| 7 | `**/*FilterConfig.java` | Glob | `find . -path "**/*FilterConfig.java"` | 1-3 files |
| **Interpretation:** | Core filters + optional filters | | | |

---

## CONTEXT SYSTEM PATTERNS

| # | Pattern | Type | Command | Expected Matches |
|---|---------|------|---------|------------------|
| 8 | `IOLSchema` | Grep | `rg "IOLSchema" src/` | ≥ 5 |
| 9 | `@IOLContext` | Grep | `rg "@IOLContext" src/` | ≥ 3 |
| 10 | `WebUtils\.get.*Context\(` | Grep | `rg "WebUtils\.get.*Context\(" src/` | 0-5 |
| 11 | `X-.*Context` | Grep | `rg "X-.*Context" src/` | ≥ 3 |
| 12 | `**/IOLSchema.java` | Glob | `find . -path "*/IOLSchema.java"` | 1 file |
| 13 | `**/WebUtils.java` | Glob | `find . -path "*/WebUtils.java"` | 1 file |
| **Interpretation:** | High count = good context integration | | | |

---

## EXCEPTION PATTERNS

| # | Pattern | Type | Command | Expected Matches |
|---|---------|------|---------|------------------|
| 16 | `extends GenericException` | Grep | `rg "extends GenericException" src/` | 5 |
| 17 | `throw new.*Exception` | Grep | `rg "throw new (Application\|NotFoundException\|...)Exception" src/` | ≥ 10 |
| 18 | `ResponseHttpStatus` | Grep | `rg "ResponseHttpStatus" src/` | ≥ 1 |
| 19 | `catch\s*\(\s*GenericException` | Grep | `rg "catch.*GenericException" src/` | ≥ 1 |
| 20 | `**/src/main/java/**/*Exception.java` | Glob | `find . -path "*/src/main/java/**/*Exception.java"` | 5-10 files |
| 21 | `**/*ExceptionHandler.java` | Glob | `find . -path "**/*ExceptionHandler.java"` | 1 file |
| **Interpretation:** | Comprehensive exception handling | | | |

---

## RESPONSE PATTERNS

| # | Pattern | Type | Command | Expected Matches |
|---|---------|------|---------|------------------|
| 22 | `Response\s*\.\s*assemble\(\)` | Grep | `rg "Response.*assemble\(\)" src/` | ≥ 10 |
| 23 | `\.build\(` | Grep | `rg "\.assemble\(\).*\.build\(" src/` | ≥ 5 |
| 24 | `ResponseEntity<Response` | Grep | `rg "ResponseEntity<Response" src/` | ≥ 5 |
| 25 | `@JsonInclude` | Grep | `rg "@JsonInclude" src/` | ≥ 1 |
| 26 | `**/Response.java` | Glob | `find . -path "*/Response.java"` | 1 file |
| 27 | `**/*ResponseAssembler.java` | Glob | `find . -path "**/*ResponseAssembler.java"` | 1-3 files |
| **Interpretation:** | Consistent response formatting | | | |

---

## ENABLEMENT PATTERNS

| # | Pattern | Type | Command | Expected Matches |
|---|---------|------|---------|------------------|
| 28 | `@EnableExperienceAPI` | Grep | `rg "@EnableExperienceAPI" src/` | **exactly 1** |
| 29 | `@Enable(SecureProxy\|Router)` | Grep | `rg "@Enable(SecureProxy\|Router)" src/` | 0-2 |
| 31 | `@ConfigurationProperties` | Grep | `rg "@ConfigurationProperties" src/` | ≥ 1 |
| 32 | `@ConditionalOnProperty` | Grep | `rg "@ConditionalOnProperty" src/` | ≥ 3 |
| 33 | `**/Application.java` | Glob | `find . -path "*/src/main/java/**/*Application.java"` | 1 file |
| 34 | `META-INF/spring/*.imports` | Glob | `find . -path "*/META-INF/spring/*.imports"` | 1-2 files |
| **Interpretation:** | Framework properly enabled | | | |

---

## CONFIGURATION PATTERNS

| # | Pattern | Type | Command | Expected Matches |
|---|---------|------|---------|------------------|
| 35 | `**/application*.properties` | Glob | `find . -path "*/application*.properties"` | 1-4 files |
| 36 | `**/application-*.properties` | Glob | `find . -path "*/application-*.properties"` | 1-3 files |
| 37 | `mca\.eps\|masking\.enabled` | Grep | `grep -r "mca.eps\|masking.enabled" application*.properties` | ≥ 3 matches |
| **Interpretation:** | Proper configuration structure | | | |

---

## QUICK ANALYSIS MATRIX

### Integration Score (Count Matches and Rate)

```
FILTER CHAIN:
  ✓ extends OncePerRequestFilter        Count: ___ (Expected: 3-5)
  ✓ filterChain.doFilter()               Count: ___ (Expected: ≥ 3)
  Score: ___/10

CONTEXT SYSTEM:
  ✓ @IOLContext annotations             Count: ___ (Expected: ≥ 3)
  Score: ___/10

EXCEPTIONS:
  ✓ extends GenericException             Count: ___ (Expected: 5)
  ✓ throw GenericException               Count: ___ (Expected: ≥ 10)
  Score: ___/10

RESPONSES:
  ✓ Response.assemble() calls           Count: ___ (Expected: ≥ 10)
  ✓ ResponseEntity<Response>            Count: ___ (Expected: ≥ 5)
  Score: ___/10

ENABLEMENT:
  ✓ @EnableExperienceAPI                Count: ___ (Expected: 1)
  Score: ___/10

TOTAL SCORE: ___ / 50
```

---

## INTERPRETATION GUIDE

### Score Thresholds

| Score | Level | Status |
|-------|-------|--------|
| 0-10 | Minimal | ❌ Not using MCA2 |
| 11-20 | Basic | ⚠️ Minimal integration |
| 21-30 | Good | ✅ Core frameworks used |
| 31-40 | Strong | ✅✅ Comprehensive integration |
| 41-50 | Excellent | ✅✅✅ Full platform adoption |

### Per-Category Interpretation

**FILTER CHAIN (0-10):**
- 0-2: Not using MCA2 filters
- 3-5: Core filters present
- 6-10: Core + custom filters

**CONTEXT SYSTEM (0-10):**
- 0-2: Not using context
- 3-5: Context system in use
- 6-10: Comprehensive context integration

**EXCEPTIONS (0-10):**
- 0-2: Not using MCA2 exceptions
- 3-5: Basic exception usage
- 6-10: Comprehensive exception handling

**RESPONSES (0-10):**
- 0-2: Not using Response envelope
- 3-5: Some response formatting
- 6-10: Consistent response handling

**ENABLEMENT (0-10):**
- 0-2: Incomplete enablement
- 3-5: Basic enablement
- 6-10: Proper framework enablement

---

## COMMAND CHEAT SHEET

### Copy-Paste Ready Commands

```bash
# All filter patterns
rg "extends OncePerRequestFilter|filterChain\.doFilter|FilterRegistrationBean" src/ --type java | wc -l

# All context patterns
rg "@IOLContext|WebUtils\.get.*Context" src/ --type java | wc -l

# All exception patterns
rg "extends GenericException|throw new.*Exception" src/ --type java | wc -l

# All response patterns
rg "Response\.assemble|ResponseEntity<Response" src/ --type java | wc -l

# All enablement patterns
rg "@EnableExperienceAPI|@ConfigurationProperties" src/ --type java | wc -l

# Quick overall score
echo "TOTAL PATTERNS: $(rg "extends OncePerRequestFilter|@IOLContext|extends GenericException|Response\.assemble|@EnableExperienceAPI" src/ --type java | wc -l)"
```

---

## PATTERN CATEGORIES BY PURPOSE

### Framework Detection
- @EnableExperienceAPI (Grep #28)
- **/Application.java (Glob #33)

### Feature Completeness
- extends OncePerRequestFilter (Grep #1)
- @IOLContext (Grep #9)
- extends GenericException (Grep #16)
- Response.assemble() (Grep #22)

### Configuration Verification
- application*.properties (Glob #35)
- META-INF/spring/*.imports (Glob #34)
- @ConfigurationProperties (Grep #31)

### Quality Assessment
- filterChain.doFilter() (Grep #2)
- try-finally in filters (Grep #6)
- Exception handlers (Glob #21)

---

## Next Steps

1. **Run Quick Analysis** — Use Command Cheat Sheet
2. **Calculate Score** — Use Integration Score Matrix
3. **Interpret Results** — Check Interpretation Guide
4. **Identify Gaps** — Find missing patterns
5. **Generate Report** — Use Detection-Runner-Guide.md

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✓ | Recommended to find |
| ✅ | Good integration level |
| ⚠️ | Incomplete integration |
| ❌ | Not integrated |
| **exactly 1** | Should appear once |
| ≥ N | Should appear N or more times |
| 0-5 | Range of acceptable values |

**Reference Card provides one-page lookup for all detection patterns.**
