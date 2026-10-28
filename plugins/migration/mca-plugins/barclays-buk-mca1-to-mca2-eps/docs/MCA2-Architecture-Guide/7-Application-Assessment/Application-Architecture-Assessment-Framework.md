# Application Architecture Assessment Framework

## Executive Summary

Multi-stage methodology for assessing MCA2 EPS framework adoption in consuming applications. Provides automated detection, quantitative scoring, risk identification, and actionable recommendations. Designed for architecture reviews, onboarding assessments, and continuous compliance monitoring.

---

## ASSESSMENT OVERVIEW

### Assessment Stages

```
Stage 1: Framework Detection
  └─ Identify which MCA2 modules and patterns are in use

Stage 2: Coverage Analysis
  └─ Map framework usage across application layers

Stage 3: Coupling Assessment
  └─ Calculate coupling score and classify tier

Stage 4: Configuration Validation
  └─ Verify properties, auto-config, and feature toggles

Stage 5: Process & Journey Assessment
  └─ Evaluate process.json structure, endpoints, and OAS integration

Stage 6: Risk Assessment
  └─ Identify architectural issues and anti-patterns

Stage 7: Recommendations
  └─ Generate prioritized improvement plan
```

---

## STAGE 1: FRAMEWORK DETECTION

### 1.1 Dependency Detection

Scan build files for MCA2 module dependencies.

**Automated Detection Script:**
```bash
#!/bin/bash
APP_PATH=${1:-.}

echo "=== MCA2 Framework Dependency Detection ==="
echo ""

# Gradle
if [ -f "$APP_PATH/build.gradle" ]; then
  echo "Build System: Gradle"
  echo ""
  echo "MCA2 Dependencies Found:"
  grep -h "mca-" "$APP_PATH"/build.gradle "$APP_PATH"/*/build.gradle 2>/dev/null \
    | grep -v "^//" | sed 's/^[ \t]*/  /' | sort -u
fi

# Maven
if [ -f "$APP_PATH/pom.xml" ]; then
  echo "Build System: Maven"
  echo ""
  echo "MCA2 Dependencies Found:"
  grep -A1 "mca-" "$APP_PATH/pom.xml" 2>/dev/null | sed 's/^[ \t]*/  /'
fi
```

**Detection Checklist:**

| Module | Grep Pattern | Category |
|--------|-------------|----------|
| mca-context | `mca-context[^-]` | Core |
| mca-filter-core | `mca-filter-core` | Core |
| mca-eps-core | `mca-eps-core` | Core |
| mca-exception-handling-core | `mca-exception-handling` | Core |
| mca-response-handling-core | `mca-response-handling` | Core |
| mca-logging-aspects | `mca-logging-aspects` | Core |
| mca-oas-validation | `mca-oas-validation` | Core |
| mca-process-lib | `mca-process-lib` | Process |
| mca-service-client-starter | `mca-service-client` | Framework |
| mca-masking | `mca-masking` | Framework |
| mca-oauth-validator-core | `mca-oauth-validator` | Framework |
| mca-secure-proxy-core | `mca-secure-proxy` | Proxy |
| mca-router-http | `mca-router-http` | Proxy |
| mca-placeholder-starter | `mca-placeholder` | Framework |

---

### 1.2 Annotation Detection

Scan source code for MCA2 enable annotations and framework markers.

```bash
echo "=== Enable Annotations ==="
grep -rn "@EnableExperienceAPI" "$APP_PATH/src" --include="*.java" || echo "  Not found"
grep -rn "@EnableSecureProxy" "$APP_PATH/src" --include="*.java" || echo "  Not found"
grep -rn "@EnableMasking" "$APP_PATH/src" --include="*.java" || echo "  Not found"

echo ""
echo "=== Context Usage ==="
grep -rc "@IOLContext" "$APP_PATH/src" --include="*.java" | awk -F: '{sum+=$2} END {print "  @IOLContext injections:", sum}'
grep -rc "WebUtils.getIOLSchemaFromScope" "$APP_PATH/src" --include="*.java" | awk -F: '{sum+=$2} END {print "  WebUtils context access:", sum}'

echo ""
echo "=== Exception Handling ==="
grep -rc "GenericException\|RequestException\|ServerException\|ApplicationException\|NotFoundException\|AuthorizationException" \
  "$APP_PATH/src" --include="*.java" | awk -F: '{sum+=$2} END {print "  MCA2 exception usage:", sum}'

echo ""
echo "=== Response Envelope ==="
grep -rc "Response\.assemble\|ResponseAssembler" "$APP_PATH/src" --include="*.java" \
  | awk -F: '{sum+=$2} END {print "  Response.assemble() calls:", sum}'

echo ""
echo "=== OAS Validation ==="
grep -rn "OASRequestValidation\|OasProvider\|SimpleOasProvider" "$APP_PATH/src" --include="*.java" || echo "  Not found"
find "$APP_PATH" -name "openapi.yaml" -o -name "openapi.json" 2>/dev/null | head -5

echo ""
echo "=== Process System ==="
grep -rn "ProcessService\|ProcessDiscovery\|BootstrapService" "$APP_PATH/src" --include="*.java" || echo "  Not found"
find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null | head -5
```

---

### 1.3 Detection Result Classification

| Detection Result | Classification | Score Impact |
|-----------------|---------------|-------------|
| @EnableExperienceAPI found | EPS Core Active | +10 |
| mca-context dependency present | Context System Active | +3 |
| mca-filter-core dependency present | Filter Chain Active | +3 |
| @IOLContext injection count > 0 | Context Injection Active | +2 |
| MCA2 exceptions used | Exception Handling Active | +2 |
| Response.assemble() used | Response Envelope Active | +2 |
| OAS validation configured | Request Validation Active | +3 |
| process.json files present | Process System Active | +3 |
| Data masking annotations found | Data Protection Active | +2 |
| @ConditionalOnProperty used | Feature Toggles Active | +1 each |

---

## STAGE 2: COVERAGE ANALYSIS

### 2.1 Layer Coverage Map

Assess framework usage across application architectural layers.

```
Layer                 Expected MCA2 Usage            Detection Method
─────────────────────────────────────────────────────────────────────
Controller Layer      @IOLContext, Response<T>        grep @IOLContext, Response.assemble
Service Layer         MCA2 exceptions, WebUtils       grep throw.*Exception, WebUtils
Repository Layer      (minimal MCA2 usage)            N/A
Configuration Layer   @Enable*, @Conditional*         grep @Enable, @ConditionalOn
Filter Layer          OncePerRequestFilter            grep extends.*Filter
Client Layer          RestClientFactory               grep RestClientFactory, RestTemplate
Process Layer         process.json, ProcessService    find processes/*.json
```

**Automated Coverage Script:**
```bash
#!/bin/bash
APP_PATH=${1:-.}

echo "=== Layer Coverage Analysis ==="
echo ""

CONTROLLER=$(grep -rl "@IOLContext\|Response\.assemble\|@RestController" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
SERVICE=$(grep -rl "throw new.*Exception\|WebUtils\.\|GenericException" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
CONFIG=$(grep -rl "@Enable\|@ConditionalOn\|@Configuration" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
FILTER=$(grep -rl "extends.*Filter\|FilterRegistrationBean" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
CLIENT=$(grep -rl "RestClientFactory\|RestTemplate" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
PROCESS=$(find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null | wc -l)

echo "  Controller Layer: $CONTROLLER files using MCA2 patterns"
echo "  Service Layer:    $SERVICE files using MCA2 patterns"
echo "  Config Layer:     $CONFIG files with MCA2 configuration"
echo "  Filter Layer:     $FILTER custom filter implementations"
echo "  Client Layer:     $CLIENT files using MCA2 REST clients"
echo "  Process Layer:    $PROCESS process.json definitions"
echo ""

TOTAL=$((CONTROLLER + SERVICE + CONFIG + FILTER + CLIENT + PROCESS))
JAVA_FILES=$(find "$APP_PATH/src/main/java" -name "*.java" 2>/dev/null | wc -l)

if [ "$JAVA_FILES" -gt 0 ]; then
  COVERAGE=$((TOTAL * 100 / JAVA_FILES))
  echo "  Framework Penetration: $TOTAL/$JAVA_FILES files ($COVERAGE%)"
else
  echo "  No Java files found"
fi
```

### 2.2 Coverage Scoring

| Coverage Level | Penetration | Rating |
|----------------|------------|--------|
| Minimal | <10% files | Poor |
| Basic | 10-25% files | Below Average |
| Moderate | 25-50% files | Average |
| Good | 50-75% files | Above Average |
| Comprehensive | >75% files | Excellent |

---

## STAGE 3: COUPLING ASSESSMENT

### 3.1 Coupling Score Calculation

Apply the 5-tier scoring formula from the Coupling Score Framework:

```
COUPLING_SCORE = (Core × 3) + (Framework × 2) + (Optional × 1)
               + Layering_Bonus + Conditional_Bonus

Core Modules (×3):     mca-context, mca-filter-core, mca-eps-core,
                       mca-exception-handling-core, mca-response-handling-core,
                       mca-logging-aspects

Framework Modules (×2): mca-service-client-starter, mca-masking,
                        mca-oauth-validator-core, mca-oas-validation,
                        mca-process-lib, mca-placeholder-starter

Optional Modules (×1):  mca-router-http, mca-secure-proxy-core,
                        mca-jceks-processor, mca-spring-boot-ssl,
                        mca-sso, mca-entitlement, mca-reference-data

Layering_Bonus:  -1 per properly separated layer (max -5)
Conditional_Bonus: -0.5 per @ConditionalOnProperty usage (max -2.5)
```

### 3.2 Tier Classification

| Tier | Score | Level | Characteristics |
|------|-------|-------|----------------|
| 1 | 0-3 | Minimal | Single module, basic usage |
| 2 | 4-8 | Core | Core modules, basic layering |
| 3 | 9-15 | Moderate | Core + 2-3 frameworks, good layering |
| 4 | 16-25 | Heavy | Most modules, excellent layering |
| 5 | 26+ | Full Platform | All modules, maximum integration |

### 3.3 Automated Coupling Calculator

```bash
#!/bin/bash
APP_PATH=${1:-.}
SCORE=0

echo "=== Coupling Score Calculation ==="

# Core modules (×3 each)
for mod in mca-context mca-filter-core mca-eps-core mca-exception-handling mca-response-handling mca-logging-aspects; do
  if grep -q "$mod" "$APP_PATH/build.gradle" "$APP_PATH/pom.xml" 2>/dev/null; then
    echo "  [CORE] $mod: +3"
    SCORE=$((SCORE + 3))
  fi
done

# Framework modules (×2 each)
for mod in mca-service-client mca-masking mca-oauth-validator mca-oas-validation mca-process-lib mca-placeholder; do
  if grep -q "$mod" "$APP_PATH/build.gradle" "$APP_PATH/pom.xml" 2>/dev/null; then
    echo "  [FRAMEWORK] $mod: +2"
    SCORE=$((SCORE + 2))
  fi
done

# Optional modules (×1 each)
for mod in mca-router-http mca-secure-proxy mca-jceks mca-spring-boot-ssl mca-sso mca-entitlement mca-reference-data; do
  if grep -q "$mod" "$APP_PATH/build.gradle" "$APP_PATH/pom.xml" 2>/dev/null; then
    echo "  [OPTIONAL] $mod: +1"
    SCORE=$((SCORE + 1))
  fi
done

# Layering bonus
LAYERS=0
for dir in config service dto repository client filter; do
  if find "$APP_PATH/src/main/java" -type d -name "$dir" 2>/dev/null | grep -q .; then
    LAYERS=$((LAYERS + 1))
  fi
done
LAYER_BONUS=$(( LAYERS > 5 ? 5 : LAYERS ))
SCORE=$((SCORE - LAYER_BONUS))
echo "  [LAYERING] $LAYERS layers detected: -$LAYER_BONUS"

# Conditional bonus
CONDITIONALS=$(grep -rc "@ConditionalOnProperty" "$APP_PATH/src" --include="*.java" 2>/dev/null | awk -F: '{sum+=$2} END {print sum+0}')
COND_BONUS=$(echo "$CONDITIONALS * 0.5" | bc 2>/dev/null || echo 0)
echo "  [CONDITIONALS] $CONDITIONALS toggles: -$COND_BONUS"

echo ""
echo "  TOTAL COUPLING SCORE: $SCORE"
echo ""

if [ "$SCORE" -le 3 ]; then echo "  TIER: 1 - Minimal Integration"
elif [ "$SCORE" -le 8 ]; then echo "  TIER: 2 - Core Framework"
elif [ "$SCORE" -le 15 ]; then echo "  TIER: 3 - Moderate Integration"
elif [ "$SCORE" -le 25 ]; then echo "  TIER: 4 - Heavy Integration"
else echo "  TIER: 5 - Full Platform Integration"
fi
```

---

## STAGE 4: CONFIGURATION VALIDATION

### 4.1 Required Configuration Checks

```bash
#!/bin/bash
APP_PATH=${1:-.}
ISSUES=0

echo "=== Configuration Validation ==="
echo ""

# Check 1: EPS enabled
if grep -q "mca.eps.enabled=true" "$APP_PATH"/src/main/resources/*.properties 2>/dev/null; then
  echo "  ✓ mca.eps.enabled=true"
else
  echo "  ✗ MISSING: mca.eps.enabled=true"
  ISSUES=$((ISSUES + 1))
fi

# Check 2: Correlation ID in logging pattern
if grep -q "correlationId" "$APP_PATH"/src/main/resources/*.properties "$APP_PATH"/src/main/resources/*.xml 2>/dev/null; then
  echo "  ✓ Correlation ID in logging pattern"
else
  echo "  ✗ MISSING: correlationId in logging pattern"
  ISSUES=$((ISSUES + 1))
fi

# Check 3: Exception detail messages disabled in prod
PROD_PROPS=$(find "$APP_PATH" -name "application-prod*" 2>/dev/null)
if [ -n "$PROD_PROPS" ]; then
  if grep -q "detailed-error-messages=false" $PROD_PROPS 2>/dev/null; then
    echo "  ✓ Detailed error messages disabled in production"
  else
    echo "  ⚠ WARNING: detailed-error-messages not explicitly false in prod"
    ISSUES=$((ISSUES + 1))
  fi
fi

# Check 4: Data masking enabled
if grep -q "mca.masking.enabled=true" "$APP_PATH"/src/main/resources/*.properties 2>/dev/null; then
  echo "  ✓ Data masking enabled"
else
  echo "  ⚠ WARNING: Data masking not enabled"
fi

# Check 5: Auto-configuration registration
if find "$APP_PATH" -path "*/META-INF/spring/*.imports" 2>/dev/null | grep -q .; then
  echo "  ✓ Spring Boot auto-configuration imports found"
else
  echo "  ⚠ INFO: No custom auto-configuration imports"
fi

# Check 6: OAS validation
if grep -q "core.default.oas.enabled=true" "$APP_PATH"/src/main/resources/*.properties "$APP_PATH"/src/main/resources/*.yml 2>/dev/null; then
  echo "  ✓ OAS validation enabled"
  if grep -q "blockingMode=true" "$APP_PATH"/src/main/resources/*prod* 2>/dev/null; then
    echo "  ✓ OAS blocking mode enabled in production"
  else
    echo "  ⚠ WARNING: OAS blockingMode not enabled in production"
  fi
else
  echo "  ⚠ INFO: OAS validation not enabled"
fi

# Check 7: Process definitions
PROCESS_COUNT=$(find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null | wc -l)
if [ "$PROCESS_COUNT" -gt 0 ]; then
  echo "  ✓ $PROCESS_COUNT process.json definition(s) found"
else
  echo "  ⚠ INFO: No process.json definitions found"
fi

# Check 8: No secrets in properties
if grep -q "password=\|secret=\|key=" "$APP_PATH"/src/main/resources/application.properties 2>/dev/null; then
  echo "  ✗ SECURITY: Potential secrets in application.properties"
  ISSUES=$((ISSUES + 1))
else
  echo "  ✓ No obvious secrets in properties files"
fi

echo ""
echo "  Configuration Issues Found: $ISSUES"
```

### 4.2 Environment Profile Validation

| Property | Dev | Staging | Production |
|----------|-----|---------|------------|
| mca.eps.enabled | true | true | true |
| mca.filter.exception.detailed-error-messages | true | true | **false** |
| mca.filter.exception.include-stacktrace | true | false | **false** |
| mca.masking.enabled | false | true | **true** |
| mca.filter.ddos-prevention.enabled | false | true | **true** |
| core.default.oas.enabled | true | true | **true** |
| core.default.oas.blockingMode | false | true | **true** |
| server.ssl.enabled | false | true | **true** |
| logging.level.root | DEBUG | INFO | **WARN** |

---

## STAGE 5: PROCESS & JOURNEY ASSESSMENT

### 5.1 Process.json Validation

```bash
#!/bin/bash
APP_PATH=${1:-.}

echo "=== Process System Assessment ==="
echo ""

PROCESS_FILES=$(find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null)

if [ -z "$PROCESS_FILES" ]; then
  echo "  No process.json files found. Skipping process assessment."
  exit 0
fi

for pfile in $PROCESS_FILES; do
  echo "  Analyzing: $pfile"

  # Check process ID
  if grep -q '"id"' "$pfile"; then
    PROC_ID=$(grep '"id"' "$pfile" | head -1 | sed 's/.*"id"[^"]*"\([^"]*\)".*/\1/')
    echo "    Process ID: $PROC_ID"
  else
    echo "    ✗ MISSING: process.id field"
  fi

  # Count endpoints
  ENDPOINTS=$(grep -c '"uri"' "$pfile" 2>/dev/null || echo 0)
  echo "    Endpoints defined: $ENDPOINTS"

  # Count tasks
  TASKS=$(grep -c '"id"' "$pfile" 2>/dev/null || echo 0)
  echo "    Tasks defined: $TASKS"

  # Check contexts
  if grep -q '"contexts"' "$pfile"; then
    echo "    ✓ Context requirements specified"
  else
    echo "    ⚠ No context requirements in endpoints"
  fi

  # Check OAS integration
  if grep -q '"oas"' "$pfile" || grep -q '"apiDefinition"' "$pfile"; then
    echo "    ✓ OAS/API definition present"
  else
    echo "    ⚠ No OAS definition in process"
  fi

  # Check for MCA1 legacy endpoints
  MCA1=$(grep -c '"mca1"' "$pfile" 2>/dev/null || echo 0)
  if [ "$MCA1" -gt 0 ]; then
    echo "    ⚠ $MCA1 legacy MCA1 endpoint(s) detected"
  fi

  echo ""
done
```

### 5.2 Process Quality Checklist

| Criterion | Check | Severity |
|-----------|-------|----------|
| Process ID present | `"id"` field exists | Critical |
| Endpoints have URIs | All endpoints have `"uri"` | Critical |
| Endpoints have methods | All endpoints have `"method"` | Critical |
| Context requirements defined | Endpoints specify `"contexts"` | High |
| Request schemas present | POST/PUT endpoints have `"requestSchema"` | Medium |
| OAS definition included | `"apiDefinition"` section present | Medium |
| Tasks define workflow | `"tasks"` array is non-empty | Medium |
| Events have targets | Each event has `"task"` or `"endpoint"` | Medium |
| No hardcoded URLs | URIs use path parameters, not literals | Low |
| File follows naming convention | `{processName}_v{version}.json` | Low |

---

## STAGE 6: RISK ASSESSMENT

### 6.1 Architectural Risk Indicators

```bash
#!/bin/bash
APP_PATH=${1:-.}
RISK_SCORE=0

echo "=== Risk Assessment ==="
echo ""

# Risk 1: Missing exception handling
UNHANDLED=$(grep -rl "catch.*Exception.*e" "$APP_PATH/src" --include="*.java" 2>/dev/null \
  | xargs grep -l "e.printStackTrace\|System.out\|System.err" 2>/dev/null | wc -l)
if [ "$UNHANDLED" -gt 0 ]; then
  echo "  ✗ RISK: $UNHANDLED file(s) with printStackTrace/System.out in catch blocks"
  RISK_SCORE=$((RISK_SCORE + 3))
else
  echo "  ✓ No printStackTrace/System.out in exception handlers"
fi

# Risk 2: Direct controller-to-repository access
DIRECT_REPO=$(grep -rl "Repository\|JpaRepository" "$APP_PATH/src" --include="*.java" 2>/dev/null \
  | xargs grep -l "@RestController\|@Controller" 2>/dev/null | wc -l)
if [ "$DIRECT_REPO" -gt 0 ]; then
  echo "  ✗ RISK: $DIRECT_REPO controller(s) directly accessing repositories (skipping service layer)"
  RISK_SCORE=$((RISK_SCORE + 2))
else
  echo "  ✓ No direct controller-to-repository access"
fi

# Risk 3: Hardcoded credentials
HARDCODED=$(grep -rn "password.*=.*['\"]" "$APP_PATH/src/main/resources" --include="*.properties" --include="*.yml" 2>/dev/null \
  | grep -v "\${" | grep -v "changeme\|placeholder" | wc -l)
if [ "$HARDCODED" -gt 0 ]; then
  echo "  ✗ SECURITY: $HARDCODED potential hardcoded credential(s)"
  RISK_SCORE=$((RISK_SCORE + 5))
else
  echo "  ✓ No hardcoded credentials detected"
fi

# Risk 4: Missing correlation ID
if ! grep -q "correlationId\|Correlation-ID" "$APP_PATH/src/main/resources" 2>/dev/null; then
  echo "  ✗ RISK: No correlation ID configuration found"
  RISK_SCORE=$((RISK_SCORE + 2))
else
  echo "  ✓ Correlation ID configured"
fi

# Risk 5: Missing masking for sensitive fields
SENSITIVE=$(grep -rn "cardNumber\|accountNumber\|ssn\|socialSecurity\|password\|creditCard" \
  "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | grep -v "@Masked\|Mask\|mask" | wc -l)
if [ "$SENSITIVE" -gt 0 ]; then
  echo "  ⚠ WARNING: $SENSITIVE references to sensitive fields without masking"
  RISK_SCORE=$((RISK_SCORE + 2))
else
  echo "  ✓ No unmasked sensitive field references detected"
fi

# Risk 6: Large process.json without OAS
for pfile in $(find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null); do
  ENDPOINTS=$(grep -c '"uri"' "$pfile" 2>/dev/null || echo 0)
  HAS_OAS=$(grep -c '"oas"\|"apiDefinition"' "$pfile" 2>/dev/null || echo 0)
  if [ "$ENDPOINTS" -gt 3 ] && [ "$HAS_OAS" -eq 0 ]; then
    echo "  ⚠ WARNING: $(basename $pfile) has $ENDPOINTS endpoints but no OAS validation"
    RISK_SCORE=$((RISK_SCORE + 1))
  fi
done

echo ""
echo "  RISK SCORE: $RISK_SCORE"
if [ "$RISK_SCORE" -le 2 ]; then echo "  RATING: LOW RISK (Green)"
elif [ "$RISK_SCORE" -le 5 ]; then echo "  RATING: MODERATE RISK (Yellow)"
elif [ "$RISK_SCORE" -le 8 ]; then echo "  RATING: HIGH RISK (Orange)"
else echo "  RATING: CRITICAL RISK (Red)"
fi
```

### 6.2 Risk Categories

| Category | Indicators | Severity |
|----------|-----------|----------|
| **Security** | Hardcoded secrets, missing masking, missing SSL | Critical |
| **Stability** | Missing exception handling, no correlation ID | High |
| **Architecture** | Skipped layers, circular dependencies, no feature toggles | Medium |
| **Compliance** | Detailed errors in prod, missing audit logging | High |
| **Process Quality** | Missing OAS validation, no context requirements, legacy endpoints | Medium |
| **Performance** | No connection pool tuning, no async logging, large unvalidated payloads | Low |

---

## STAGE 7: RECOMMENDATIONS

### 7.1 Recommendation Engine

Based on assessment results, generate prioritized recommendations:

```
IF tier < 2:
  PRIORITY 1: Add core MCA2 dependencies (context, filter, eps, exception, response)
  PRIORITY 2: Create @EnableExperienceAPI application class
  PRIORITY 3: Implement basic exception handling with MCA2 exceptions
  PRIORITY 4: Add correlation ID to logging patterns

IF tier == 2:
  PRIORITY 1: Add OAS validation (mca-oas-validation)
  PRIORITY 2: Implement proper layering (config, service, dto)
  PRIORITY 3: Add data masking for sensitive fields
  PRIORITY 4: Create process.json for journey definitions

IF tier == 3:
  PRIORITY 1: Add service client patterns (mca-service-client-starter)
  PRIORITY 2: Enable OAS blocking mode in production
  PRIORITY 3: Implement @ConditionalOnProperty for feature toggles
  PRIORITY 4: Add integration tests for filter chain

IF tier == 4:
  PRIORITY 1: Maximize feature toggle coverage
  PRIORITY 2: Add comprehensive process.json with OAS definitions
  PRIORITY 3: Implement circuit breaker patterns
  PRIORITY 4: Production-harden all configurations

IF tier >= 5:
  PRIORITY 1: Monitor and optimize performance
  PRIORITY 2: Refine process definitions and journey flows
  PRIORITY 3: Document patterns for team reuse
  PRIORITY 4: Contribute improvements back to framework
```

### 7.2 Recommendation Priority Matrix

| Risk Level | Tier | Top Recommendation |
|------------|------|-------------------|
| Critical + Tier 1 | Emergency | Add core framework and fix security issues |
| Critical + Tier 2-3 | Urgent | Fix security, add OAS validation |
| High + Tier 2 | Important | Add exception handling, masking |
| High + Tier 3-4 | Planned | Improve process definitions, feature toggles |
| Medium + Any | Scheduled | Architecture improvements, optimization |
| Low + Tier 4-5 | Optional | Performance tuning, documentation |

---

## COMPLETE ASSESSMENT SCRIPT

### Full Automated Assessment

```bash
#!/bin/bash
# mca2-assessment.sh - Complete MCA2 EPS Architecture Assessment
# Usage: ./mca2-assessment.sh /path/to/application

APP_PATH=${1:-.}
REPORT_FILE="mca2-assessment-$(date +%Y%m%d-%H%M%S).md"
SCORE=0
RISK=0
ISSUES=()

{
echo "# MCA2 EPS Architecture Assessment Report"
echo "**Application:** $(basename $APP_PATH)"
echo "**Date:** $(date)"
echo "**Assessor:** Automated"
echo ""
echo "---"
echo ""

# ═══════════════════════════════════════
# STAGE 1: FRAMEWORK DETECTION
# ═══════════════════════════════════════
echo "## Stage 1: Framework Detection"
echo ""

CORE_COUNT=0
FRAMEWORK_COUNT=0
OPTIONAL_COUNT=0

for mod in mca-context mca-filter-core mca-eps-core mca-exception-handling mca-response-handling mca-logging-aspects; do
  if grep -q "$mod" "$APP_PATH/build.gradle" "$APP_PATH/pom.xml" 2>/dev/null; then
    echo "- [x] **$mod** (Core)"
    CORE_COUNT=$((CORE_COUNT + 1))
  else
    echo "- [ ] $mod (Core)"
  fi
done

for mod in mca-service-client mca-masking mca-oauth-validator mca-oas-validation mca-process-lib mca-placeholder; do
  if grep -q "$mod" "$APP_PATH/build.gradle" "$APP_PATH/pom.xml" 2>/dev/null; then
    echo "- [x] **$mod** (Framework)"
    FRAMEWORK_COUNT=$((FRAMEWORK_COUNT + 1))
  else
    echo "- [ ] $mod (Framework)"
  fi
done

for mod in mca-router-http mca-secure-proxy mca-jceks mca-spring-boot-ssl; do
  if grep -q "$mod" "$APP_PATH/build.gradle" "$APP_PATH/pom.xml" 2>/dev/null; then
    echo "- [x] **$mod** (Optional)"
    OPTIONAL_COUNT=$((OPTIONAL_COUNT + 1))
  else
    echo "- [ ] $mod (Optional)"
  fi
done

echo ""
echo "**Summary:** $CORE_COUNT core, $FRAMEWORK_COUNT framework, $OPTIONAL_COUNT optional modules"
echo ""

# ═══════════════════════════════════════
# STAGE 2: COVERAGE ANALYSIS
# ═══════════════════════════════════════
echo "## Stage 2: Coverage Analysis"
echo ""

CONTROLLER=$(grep -rl "@IOLContext\|Response\.assemble" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
SERVICE=$(grep -rl "throw new.*Exception\|WebUtils\." "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
CONFIG=$(grep -rl "@Enable\|@ConditionalOn" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
FILTER=$(grep -rl "extends.*Filter" "$APP_PATH/src/main/java" --include="*.java" 2>/dev/null | wc -l)
PROCESS=$(find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null | wc -l)

echo "| Layer | Files | Status |"
echo "|-------|-------|--------|"
echo "| Controller | $CONTROLLER | $([ $CONTROLLER -gt 0 ] && echo '✓' || echo '✗') |"
echo "| Service | $SERVICE | $([ $SERVICE -gt 0 ] && echo '✓' || echo '✗') |"
echo "| Configuration | $CONFIG | $([ $CONFIG -gt 0 ] && echo '✓' || echo '✗') |"
echo "| Filter | $FILTER | $([ $FILTER -gt 0 ] && echo '✓' || echo '✗') |"
echo "| Process | $PROCESS | $([ $PROCESS -gt 0 ] && echo '✓' || echo '-') |"
echo ""

# ═══════════════════════════════════════
# STAGE 3: COUPLING SCORE
# ═══════════════════════════════════════
echo "## Stage 3: Coupling Score"
echo ""

SCORE=$((CORE_COUNT * 3 + FRAMEWORK_COUNT * 2 + OPTIONAL_COUNT * 1))
echo "- Core modules: $CORE_COUNT × 3 = $((CORE_COUNT * 3))"
echo "- Framework modules: $FRAMEWORK_COUNT × 2 = $((FRAMEWORK_COUNT * 2))"
echo "- Optional modules: $OPTIONAL_COUNT × 1 = $OPTIONAL_COUNT"
echo "- **Raw Score: $SCORE**"
echo ""

if [ "$SCORE" -le 3 ]; then TIER="Tier 1 - Minimal"
elif [ "$SCORE" -le 8 ]; then TIER="Tier 2 - Core"
elif [ "$SCORE" -le 15 ]; then TIER="Tier 3 - Moderate"
elif [ "$SCORE" -le 25 ]; then TIER="Tier 4 - Heavy"
else TIER="Tier 5 - Full Platform"
fi

echo "**Classification: $TIER**"
echo ""

# ═══════════════════════════════════════
# STAGE 4: CONFIGURATION VALIDATION
# ═══════════════════════════════════════
echo "## Stage 4: Configuration Validation"
echo ""

CONFIG_ISSUES=0
PROPS="$APP_PATH/src/main/resources"

echo "| Check | Status |"
echo "|-------|--------|"

if grep -q "mca.eps.enabled=true" "$PROPS"/*.properties 2>/dev/null; then
  echo "| EPS enabled | ✓ |"
else
  echo "| EPS enabled | ✗ MISSING |"
  CONFIG_ISSUES=$((CONFIG_ISSUES + 1))
fi

if grep -q "correlationId" "$PROPS"/*.properties "$PROPS"/*.xml 2>/dev/null; then
  echo "| Correlation ID in logs | ✓ |"
else
  echo "| Correlation ID in logs | ✗ MISSING |"
  CONFIG_ISSUES=$((CONFIG_ISSUES + 1))
fi

if grep -q "core.default.oas.enabled" "$PROPS"/*.properties "$PROPS"/*.yml 2>/dev/null; then
  echo "| OAS validation configured | ✓ |"
else
  echo "| OAS validation configured | - Not configured |"
fi

echo ""
echo "**Configuration Issues: $CONFIG_ISSUES**"
echo ""

# ═══════════════════════════════════════
# STAGE 5: PROCESS ASSESSMENT
# ═══════════════════════════════════════
echo "## Stage 5: Process Assessment"
echo ""

PROCESS_FILES=$(find "$APP_PATH" -path "*/processes/*.json" 2>/dev/null)
if [ -n "$PROCESS_FILES" ]; then
  for pfile in $PROCESS_FILES; do
    FNAME=$(basename "$pfile")
    ENDPOINTS=$(grep -c '"uri"' "$pfile" 2>/dev/null || echo 0)
    HAS_OAS=$(grep -c '"oas"\|"apiDefinition"' "$pfile" 2>/dev/null || echo 0)
    echo "- **$FNAME**: $ENDPOINTS endpoints, OAS: $([ $HAS_OAS -gt 0 ] && echo 'Yes' || echo 'No')"
  done
else
  echo "No process.json definitions found."
fi
echo ""

# ═══════════════════════════════════════
# STAGE 6: RISK ASSESSMENT
# ═══════════════════════════════════════
echo "## Stage 6: Risk Assessment"
echo ""

RISK=0
RISK=$((RISK + CONFIG_ISSUES))

UNHANDLED=$(grep -rl "e.printStackTrace\|System.out.print" "$APP_PATH/src" --include="*.java" 2>/dev/null | wc -l)
if [ "$UNHANDLED" -gt 0 ]; then
  echo "- ✗ **$UNHANDLED file(s) with printStackTrace/System.out** (Risk +3)"
  RISK=$((RISK + 3))
fi

HARDCODED=$(grep -rn "password.*=.*['\"]" "$PROPS" --include="*.properties" 2>/dev/null | grep -v "\${" | wc -l)
if [ "$HARDCODED" -gt 0 ]; then
  echo "- ✗ **$HARDCODED potential hardcoded secret(s)** (Risk +5)"
  RISK=$((RISK + 5))
fi

echo ""
echo "**Risk Score: $RISK**"
if [ "$RISK" -le 2 ]; then echo "**Rating: LOW RISK** ✓"
elif [ "$RISK" -le 5 ]; then echo "**Rating: MODERATE RISK** ⚠"
elif [ "$RISK" -le 8 ]; then echo "**Rating: HIGH RISK** ⚠"
else echo "**Rating: CRITICAL RISK** ✗"
fi
echo ""

# ═══════════════════════════════════════
# STAGE 7: RECOMMENDATIONS
# ═══════════════════════════════════════
echo "## Stage 7: Recommendations"
echo ""

if [ "$CORE_COUNT" -lt 5 ]; then
  echo "1. **Add missing core modules** - $((6 - CORE_COUNT)) core module(s) not detected"
fi
if [ "$FRAMEWORK_COUNT" -lt 2 ]; then
  echo "2. **Add OAS validation and process definitions** - Enable request validation"
fi
if [ "$CONFIG_ISSUES" -gt 0 ]; then
  echo "3. **Fix configuration issues** - $CONFIG_ISSUES issue(s) found"
fi
if [ "$RISK" -gt 2 ]; then
  echo "4. **Address risk items** - Risk score $RISK requires attention"
fi
if [ "$PROCESS" -eq 0 ]; then
  echo "5. **Create process.json definitions** - Define journey structure for MCA processes"
fi

echo ""
echo "---"
echo "*Generated by MCA2 EPS Architecture Assessment Framework*"

} | tee "$REPORT_FILE"

echo ""
echo "Report saved to: $REPORT_FILE"
```

---

## ASSESSMENT REPORT TEMPLATE

### Sample Output

```markdown
# MCA2 EPS Architecture Assessment Report
**Application:** order-management-service
**Date:** 2026-02-26
**Assessor:** Automated

## Stage 1: Framework Detection
- [x] **mca-context** (Core)
- [x] **mca-filter-core** (Core)
- [x] **mca-eps-core** (Core)
- [x] **mca-exception-handling** (Core)
- [x] **mca-response-handling** (Core)
- [ ] mca-logging-aspects (Core)
- [x] **mca-service-client** (Framework)
- [x] **mca-masking** (Framework)
- [ ] mca-oas-validation (Framework)

**Summary:** 5 core, 2 framework, 0 optional modules

## Stage 3: Coupling Score
- Core modules: 5 × 3 = 15
- Framework modules: 2 × 2 = 4
- **Raw Score: 19**
- **Classification: Tier 4 - Heavy**

## Stage 6: Risk Assessment
**Risk Score: 3**
**Rating: MODERATE RISK** ⚠

## Stage 7: Recommendations
1. **Add mca-logging-aspects** for AspectJ-based logging
2. **Enable OAS validation** for request schema enforcement
3. **Create process.json** for journey definitions
```

---

## INTEGRATION WITH CI/CD

### GitHub Actions Assessment

```yaml
name: MCA2 Architecture Assessment

on:
  pull_request:
    branches: [ main, release/* ]

jobs:
  assess:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run MCA2 Assessment
        run: chmod +x scripts/mca2-assessment.sh && ./scripts/mca2-assessment.sh .

      - name: Check Risk Threshold
        run: |
          RISK=$(grep "Risk Score:" mca2-assessment-*.md | grep -o '[0-9]*')
          if [ "$RISK" -gt 5 ]; then
            echo "Risk score $RISK exceeds threshold of 5"
            exit 1
          fi

      - name: Comment PR with Assessment
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const files = fs.readdirSync('.').filter(f => f.startsWith('mca2-assessment-'));
            const report = fs.readFileSync(files[0], 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });
```

---

## QUICK REFERENCE

### Assessment Stages Summary

| Stage | Purpose | Output |
|-------|---------|--------|
| 1. Detection | Find MCA2 modules and patterns | Module inventory |
| 2. Coverage | Map usage across layers | Layer coverage map |
| 3. Coupling | Calculate integration depth | Tier classification |
| 4. Configuration | Validate properties and setup | Issue count |
| 5. Process | Assess journey definitions | Process quality score |
| 6. Risk | Identify architectural issues | Risk rating |
| 7. Recommendations | Generate improvement plan | Prioritized actions |

### Scoring Quick Reference

| Metric | Good | Acceptable | Poor |
|--------|------|-----------|------|
| Core Modules | 6/6 | 4-5/6 | <4/6 |
| Coverage | >50% | 25-50% | <25% |
| Tier | 3-5 | 2 | 1 |
| Config Issues | 0 | 1-2 | 3+ |
| Risk Score | 0-2 | 3-5 | 6+ |

**Application Architecture Assessment Framework provides comprehensive methodology for evaluating MCA2 EPS integration.**
