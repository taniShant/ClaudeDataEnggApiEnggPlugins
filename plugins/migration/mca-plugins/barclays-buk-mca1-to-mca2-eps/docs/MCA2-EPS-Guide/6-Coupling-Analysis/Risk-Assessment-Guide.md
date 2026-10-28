# Risk Assessment Guide: Architectural Vulnerabilities

## Executive Summary

Framework for identifying and quantifying architectural risks in MCA2 EPS applications. Focuses on circular dependencies, tight coupling, missing patterns, and configuration vulnerabilities that can lead to maintenance, scalability, and reliability issues.

---

## Risk Classification Framework

### Risk Severity Levels

| Level | Impact | Examples | Action |
|-------|--------|----------|--------|
| **CRITICAL** | System-wide failure, data corruption | Circular dependencies in core modules, missing exception handling | IMMEDIATE - Must fix before deployment |
| **HIGH** | Significant functionality loss, major bugs | Tight coupling >80%, missing filter ordering, unhandled exceptions | URGENT - Fix within 1 sprint |
| **MEDIUM** | Degraded performance, reduced reliability | Missing masking, suboptimal caching, incomplete context usage | IMPORTANT - Fix within 2 sprints |
| **LOW** | Code quality issues, maintainability concerns | Dead code, unused imports, incomplete logging | NICE-TO-HAVE - Include in next refactor |

---

## Risk Category 1: Circular Dependencies

### Critical Risks

#### Risk 1.1: Core Module Circular Dependency

**Risk Pattern:** Module A imports Module B, Module B imports Module A

```
❌ EXAMPLE (ANTI-PATTERN):
├─ mca-context (Layer 1)
│  └─ imports ContextProcessor from context-utils
├─ context-utils (Layer 2)
│  └─ imports IOLSchema from context
└─ RESULT: Circular dependency chain (1 → 2 → 1)
```

**Detection:**
```bash
# Find circular dependencies using Gradle
./gradlew :mca-libraries:mca-context:dependencies --graph-text | \
  grep -E "→.*←" | head -5

# Alternative: Check import cycles
find . -name "*.java" -path "*/src/main/java/*" -exec grep -l "import" {} \; | \
  xargs -I {} sh -c 'grep "import" {} | cut -d" " -f2 | cut -d";" -f1 > /tmp/deps.txt; \
  grep "^package" {} | cut -d" " -f2 | cut -d";" -f1 >> /tmp/deps.txt; \
  if grep -q "$(head -1 /tmp/deps.txt)" <<< "$(tail -1 /tmp/deps.txt)"; then \
    echo "CIRCULAR: {}"; fi'
```

**Impact if present:**
- ❌ Compilation failures
- ❌ ClassLoader issues
- ❌ Runtime exceptions
- ❌ Impossible to version modules independently
- ❌ Difficult testing and mocking

**Risk Score:** 🔴 **CRITICAL (100/100)**

**Fix Strategy:**
1. Identify circular path: A → B → C → A
2. Extract common code to new Layer 1 module
3. Break cycle: A → Common ← B ← C
4. Use abstraction (interface) pattern

```java
// BEFORE (CIRCULAR):
// context.data → ContextProcessor (context-utils)
// ContextProcessor → IOLSchema (context.data)

// AFTER (FIXED):
// Layer 1: IOLSchema (context.data) - No imports
// Layer 1: ContextProcessor interface (context-utils-api)
// Layer 2: ContextProcessorImpl (context-utils)
//   └─ imports IOLSchema (Layer 1) ✅
// No circular dependency
```

---

#### Risk 1.2: Optional Framework Circular Dependency

**Risk Pattern:** Optional frameworks creating circular chains

```
❌ EXAMPLE:
├─ router (Layer 4)
│  └─ imports RequestProcessor from service-client-starter
├─ service-client-starter (Layer 4)
│  └─ imports Router for routing decisions
└─ RESULT: Circular dependency at Layer 4
```

**Detection:**
```bash
# Check optional frameworks for cycles
./gradlew :mca-libraries:mca-router-http:dependencies | \
  grep "mca-service-client-starter"

./gradlew :mca-libraries:mca-service-client-starter:dependencies | \
  grep "mca-router"
```

**Risk Score:** 🟠 **HIGH (75/100)**

**Fix Strategy:** Use dependency injection and interface-based design

```java
// BEFORE (CIRCULAR):
public class RouterImpl {
  private ServiceClient serviceClient; // Direct dependency
}

public class ServiceClientImpl {
  private Router router; // Back-reference creates cycle
}

// AFTER (FIXED):
public interface RequestProcessor {
  Response process(Request request);
}

public class RouterImpl implements RequestProcessor {
  // Route requests without ServiceClient reference
}

public class ServiceClientImpl {
  private RequestProcessor processor; // Interface reference, breaks cycle
}
```

---

### Detection & Prevention

#### Automated Detection Script

```bash
#!/bin/bash
# detect-circular-deps.sh

echo "=== MCA2 Circular Dependency Detection ==="
echo

# Check Layer boundaries
echo "Checking Layer 1 (Foundation) for upward imports..."
LAYER1_VIOLATIONS=$(grep -r "import.*mca.*filter\|import.*mca.*eps\|import.*boot\|import.*config" \
  mca-libraries/context/src/main/java \
  mca-libraries/exception-handling-core/src/main/java \
  mca-libraries/logging-aspects/src/main/java 2>/dev/null | wc -l)

if [ $LAYER1_VIOLATIONS -gt 0 ]; then
  echo "⚠️  Layer 1 upward imports detected: $LAYER1_VIOLATIONS"
fi

# Check for known circular patterns
echo "Checking for known circular dependency patterns..."

if grep -q "context-utils" mca-libraries/context/build.gradle && \
   grep -q "mca-context" mca-libraries/context-utils/build.gradle; then
  echo "❌ CRITICAL: context ↔ context-utils circular dependency detected"
  exit 1
fi

if grep -q "service-client-starter" mca-libraries/mca-router-http/build.gradle && \
   grep -q "mca-router" mca-libraries/mca-service-client-starter/build.gradle; then
  echo "⚠️  Router ↔ ServiceClient potential circular dependency"
fi

echo "✅ Circular dependency check complete"
```

---

## Risk Category 2: Tight Coupling

### High-Risk Coupling Patterns

#### Risk 2.1: Over-35% Coupling (Moderate Concern)

**Definition:** Module A depends on >35% of other modules in its layer

```
❌ EXAMPLE:
mca-context imports from:
├─ No foundation modules ✅
└─ Used by 12 other modules (>35% of total) ⚠️
```

**Detection:**
```bash
# Measure coupling for a module
MODULE="mca-context"
TOTAL_MODULES=52
DEPENDENTS=$(grep -r "implementation.*$MODULE\|import.*$MODULE" \
  mca-libraries/*/build.gradle mca-extension-libraries/*/build.gradle | wc -l)

COUPLING_PERCENT=$((DEPENDENTS * 100 / TOTAL_MODULES))

if [ $COUPLING_PERCENT -gt 35 ]; then
  echo "⚠️  MODERATE COUPLING: $MODULE used by $COUPLING_PERCENT% of modules"
fi
```

**Risk Score:** 🟡 **MEDIUM (45/100)**

**Impact:**
- Difficult to modify without affecting many modules
- Testing complexity increases
- Parallel development conflicts
- Slow build times (many modules to rebuild)

**Fix Strategy:** Extract abstractions, create facade modules

```java
// BEFORE (TIGHT COUPLING):
// 12 modules directly import IOLSchema implementation details

// AFTER (LOOSE COUPLING):
// Create interface module (context-api)
//   └─ IOLSchema (interface)
// Implementation in context-core
//   └─ IOLSchemaImpl
// Consumers import from context-api only
```

#### Risk 2.2: Bidirectional Coupling

**Definition:** A imports B AND B imports A (at any distance)

```
❌ EXAMPLE (BIDIRECTIONAL):
context → IOLSchema {
  @Entity
  @OneToMany ContextProcessor[] processors
}
context-utils → ContextProcessor {
  @Transient
  IOLSchema schema
}
```

**Detection:**
```bash
# Find bidirectional dependencies
echo "Checking for bidirectional imports..."

MODULE1="mca-context"
MODULE2="mca-context-utils"

FORWARD=$(grep -r "import.*$MODULE2" $MODULE1/src/main/java 2>/dev/null | wc -l)
BACKWARD=$(grep -r "import.*$MODULE1" $MODULE2/src/main/java 2>/dev/null | wc -l)

if [ $FORWARD -gt 0 ] && [ $BACKWARD -gt 0 ]; then
  echo "⚠️  BIDIRECTIONAL: $MODULE1 → $MODULE2 → $MODULE1"
fi
```

**Risk Score:** 🟠 **HIGH (65/100)**

**Fix Strategy:** Use observer/event pattern, dependency injection

```java
// BEFORE (BIDIRECTIONAL):
// IOLSchema has list of ContextProcessor
// ContextProcessor references IOLSchema

// AFTER (UNIDIRECTIONAL):
// IOLSchema publishes ContextUpdatedEvent
// ContextProcessor listens to event
// No backward reference needed
```

---

## Risk Category 3: Missing Critical Patterns

### Critical Gaps

#### Risk 3.1: Missing @EnableExperienceAPI

**Definition:** Spring Boot application without core EPS enablement

```java
// ❌ WRONG - Missing @EnableExperienceAPI
@SpringBootApplication
public class MyApp {
  public static void main(String[] args) {
    SpringApplication.run(MyApp.class);
  }
}

// ✅ CORRECT
@SpringBootApplication
@EnableExperienceAPI
public class MyApp {
  public static void main(String[] args) {
    SpringApplication.run(MyApp.class);
  }
}
```

**Detection:**
```bash
# Find applications without framework enablement
find . -path "*/src/main/java/**/*Application.java" -exec grep -L "@EnableExperienceAPI" {} \;

# Count enabled applications
TOTAL_APPS=$(find . -name "*Application.java" -path "*/src/main/java/*" | wc -l)
ENABLED_APPS=$(grep -r "@EnableExperienceAPI" . --include="*Application.java" | wc -l)

echo "Applications with EPS enabled: $ENABLED_APPS / $TOTAL_APPS"
if [ $ENABLED_APPS -lt $TOTAL_APPS ]; then
  echo "⚠️  Some applications not using EPS framework"
fi
```

**Impact:**
- ❌ EPS framework not initialized
- ❌ Context system not propagating
- ❌ Filter chain not executing
- ❌ Exception handling not in place
- ❌ Logging not integrated

**Risk Score:** 🔴 **CRITICAL (95/100)**

**Fix:** Add @EnableExperienceAPI

```java
@SpringBootApplication
@EnableExperienceAPI                    // Enable core EPS
@EnableSecureProxy                      // Optional: if using Secure Proxy (includes context storage)
@EnableRouter                           // Optional: if using routing
public class CardControlApp {
  public static void main(String[] args) {
    SpringApplication.run(CardControlApp.class);
  }
}
```

#### Risk 3.2: Missing Filter Ordering

**Definition:** Filters registered without explicit ordering

```java
// ❌ WRONG - No order specified
@Bean
public FilterRegistrationBean<CorrelationIdFilter> registerFilter() {
  return new FilterRegistrationBean<>(new CorrelationIdFilter());
  // Defaults to order Integer.MAX_VALUE (last position)
}

// ✅ CORRECT - Explicit ordering
@Bean
public FilterRegistrationBean<CorrelationIdFilter> registerFilter() {
  FilterRegistrationBean<CorrelationIdFilter> bean =
    new FilterRegistrationBean<>(new CorrelationIdFilter());
  bean.setOrder(0);  // Must be first
  return bean;
}
```

**Detection:**
```bash
# Find filter registrations without setOrder
grep -r "FilterRegistrationBean" . --include="*.java" -A 3 | \
  grep -B 3 "return bean" | grep -L "setOrder"
```

**Impact:**
- ⚠️  Unpredictable filter execution order
- ⚠️  Correlation ID not set before other filters
- ⚠️  Context not available to all filters
- ⚠️  Exception filter not catching upstream errors

**Risk Score:** 🟠 **HIGH (70/100)**

**Fix:** Ensure proper filter ordering

```
Core Filters (must be first):
├─ Order 0: CorrelationIdFilter (set correlation ID)
├─ Order 1: ExceptionFilter (catch all exceptions)
├─ Order 2: DisableSessionFilter (prevent session creation)
├─ Order 3: MultiReadRequestFilter (read body multiple times)

Optional Filters (4-9):
├─ Order 4: OAuthValidatorFilter
├─ Order 5: DdosPreventionFilter
├─ Order 300: ValidationFilter
├─ Order 7: RequestWhitelistFilter

Custom Filters (10+):
└─ Order 10+: Application-specific filters
```

#### Risk 3.3: Missing Exception Hierarchy

**Definition:** Application throwing generic exceptions instead of MCA2 types

```java
// ❌ WRONG - Generic exception
public void processAccount(String accountId) {
  if (accountId == null) {
    throw new IllegalArgumentException("Account ID required");
  }
}

// ✅ CORRECT - MCA2 exception hierarchy
public void processAccount(String accountId) {
  if (accountId == null) {
    throw new RequestException("Account ID required", ErrorCode.VALIDATION_FAILED);
  }
}
```

**Detection:**
```bash
# Find applications throwing wrong exception types
grep -r "throw new.*Exception" src/ --include="*.java" | \
  grep -v "GenericException\|ApplicationException\|ServerException\|RequestException\|NotFoundException\|AuthorizationException" | \
  head -10

# Count correct exception usage
CORRECT=$(grep -r "throw new.*Exception" src/ --include="*.java" | \
  grep "GenericException\|ApplicationException\|ServerException\|RequestException\|NotFoundException\|AuthorizationException" | wc -l)

TOTAL=$(grep -r "throw new.*Exception" src/ --include="*.java" | wc -l)

PERCENT=$((CORRECT * 100 / (TOTAL > 0 ? TOTAL : 1)))
echo "Using MCA2 exceptions: $PERCENT%"

if [ $PERCENT -lt 90 ]; then
  echo "⚠️  Less than 90% of exceptions use MCA2 hierarchy"
fi
```

**Impact:**
- ⚠️  Inconsistent error responses
- ⚠️  Wrong HTTP status codes returned
- ⚠️  Exception handling breaks on non-MCA2 exceptions
- ⚠️  Logging and monitoring fail

**Risk Score:** 🟠 **HIGH (60/100)**

**Fix:** Use MCA2 exception hierarchy everywhere

```java
// Replace with:
throw new RequestException("Account ID required",
  ErrorCode.VALIDATION_FAILED,
  accountId);
```

---

## Risk Category 4: Configuration Vulnerabilities

### High-Risk Configuration Issues

#### Risk 4.1: Missing Data Masking Configuration

> **Note:** Context store selection (context.store.type, @EnableRDBContextStore, @EnableMongoContextStore, @EnableEhCacheContextStore) is part of the **Secure Proxy** module, not EPS core. If your application uses Secure Proxy for session management, see the Secure Proxy documentation for context store configuration.

**Definition:** Application handles sensitive data without masking

```properties
# ❌ WRONG - No masking for sensitive data
mca.eps.enabled=true
# (no masking config)

# ✅ CORRECT - Masking patterns configured
mca.eps.enabled=true
masking.patterns.credit-card=\d{4}(?:\d(?=.\d{3}))
masking.patterns.email=(?<=.{1}).(?=[^@]*@)
masking.patterns.phone=(?<=.{1}).(?=[^-]*-[^-]*$)
```

**Detection:**
```bash
# Find applications with PII but no masking
if grep -q "customerNumber\|accountNumber\|ssn\|email\|phone" src/ --include="*.java" && \
   ! grep -q "masking\|@Masked" application*.properties src/ --include="*.java"; then
  echo "⚠️  Application handles PII without masking configured"
fi

# Count @Masked annotations
MASKED_FIELDS=$(grep -r "@Masked" src/ --include="*.java" | wc -l)
echo "Masked fields: $MASKED_FIELDS"

if [ $MASKED_FIELDS -eq 0 ]; then
  echo "⚠️  No @Masked annotations found"
fi
```

**Impact:**
- ⚠️  PII exposed in logs and error messages
- ⚠️  Compliance violations (GDPR, PCI-DSS)
- ⚠️  Security audit failures
- ⚠️  Potential data breach exposure

**Risk Score:** 🟠 **HIGH (80/100)**

**Fix:** Enable and configure masking

```java
// In entity/DTO:
@Masked(pattern = MaskingPattern.CREDIT_CARD)
private String creditCardNumber;

@Masked(pattern = MaskingPattern.EMAIL)
private String emailAddress;

@Masked(pattern = MaskingPattern.PHONE)
private String phoneNumber;
```

---

## Risk Scoring Methodology

### Automated Risk Assessment

```bash
#!/bin/bash
# risk-assessment.sh - Calculate application risk score

echo "=== MCA2 Risk Assessment Report ==="
echo

RISK_SCORE=0
TOTAL_CHECKS=0

# Check 1: Circular Dependencies (Critical - 15 points)
echo "[Check 1/8] Circular Dependencies..."
CIRCULAR=$(./gradlew dependencies 2>/dev/null | grep -E "→.*←" | wc -l)
if [ $CIRCULAR -eq 0 ]; then
  echo "  ✅ No circular dependencies: +15 points"
  RISK_SCORE=$((RISK_SCORE + 15))
else
  echo "  ❌ $CIRCULAR circular dependency chains: -15 points"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 15))

# Check 2: @EnableExperienceAPI Present (Critical - 20 points)
echo "[Check 2/8] @EnableExperienceAPI..."
if grep -q "@EnableExperienceAPI" src/main/java/*Application.java 2>/dev/null; then
  echo "  ✅ Framework enabled: +20 points"
  RISK_SCORE=$((RISK_SCORE + 20))
else
  echo "  ❌ Framework NOT enabled: -20 points"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 20))

# Check 3: Exception Hierarchy (High - 12 points)
# Note: Context store configuration is part of Secure Proxy, not EPS core
echo "[Check 3/7] Exception Hierarchy Usage..."
MCA_EXCEPT=$(grep -r "throw new.*GenericException\|throw new.*ApplicationException" src/ \
  --include="*.java" 2>/dev/null | wc -l)
GENERIC_EXCEPT=$(grep -r "throw new.*Exception" src/ \
  --include="*.java" 2>/dev/null | grep -v "GenericException\|ApplicationException" | wc -l)

if [ $GENERIC_EXCEPT -eq 0 ]; then
  echo "  ✅ All exceptions are MCA2 types: +12 points"
  RISK_SCORE=$((RISK_SCORE + 12))
elif [ $MCA_EXCEPT -gt $GENERIC_EXCEPT ]; then
  echo "  ⚠️  Mixed exception types: +6 points"
  RISK_SCORE=$((RISK_SCORE + 6))
else
  echo "  ❌ Mostly generic exceptions: +0 points"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 12))

# Check 5: Filter Ordering (High - 12 points)
echo "[Check 4/7] Filter Ordering..."
UNORDERED=$(grep -r "FilterRegistrationBean" src/ --include="*.java" -A 3 | \
  grep -B 3 "return bean" | grep -L "setOrder" | wc -l)

if [ $UNORDERED -eq 0 ]; then
  echo "  ✅ All filters have explicit ordering: +12 points"
  RISK_SCORE=$((RISK_SCORE + 12))
else
  echo "  ⚠️  $UNORDERED filters without ordering: +6 points"
  RISK_SCORE=$((RISK_SCORE + 6))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 12))

# Check 6: Data Masking (Medium - 10 points)
echo "[Check 5/7] Data Masking..."
MASKED=$(grep -r "@Masked\|masking.patterns" src/ --include="*.java" 2>/dev/null | wc -l)

if [ $MASKED -gt 0 ]; then
  echo "  ✅ Data masking configured: +10 points"
  RISK_SCORE=$((RISK_SCORE + 10))
else
  echo "  ⚠️  No data masking: +5 points"
  RISK_SCORE=$((RISK_SCORE + 5))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 10))

# Check 7: Layer Compliance (Medium - 10 points)
echo "[Check 6/7] Layer Compliance..."
LAYER_VIOLATIONS=$(grep -r "import.*boot\|import.*config" src/ --include="*.java" | wc -l)

if [ $LAYER_VIOLATIONS -lt 5 ]; then
  echo "  ✅ Layer boundaries respected: +10 points"
  RISK_SCORE=$((RISK_SCORE + 10))
else
  echo "  ⚠️  Layer violations detected: +5 points"
  RISK_SCORE=$((RISK_SCORE + 5))
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 10))

# Check 8: Logging Integration (Low - 5 points)
echo "[Check 7/7] Logging Integration..."
if grep -q "LoggerFactory\|SLF4J" src/ --include="*.java"; then
  echo "  ✅ Logging properly integrated: +5 points"
  RISK_SCORE=$((RISK_SCORE + 5))
else
  echo "  ⚠️  Limited logging integration: +0 points"
fi
TOTAL_CHECKS=$((TOTAL_CHECKS + 5))

# Calculate final score
PERCENT=$((RISK_SCORE * 100 / TOTAL_CHECKS))

echo
echo "================================"
echo "FINAL RISK ASSESSMENT SCORE: $RISK_SCORE / $TOTAL_CHECKS ($PERCENT%)"
echo "================================"

if [ $PERCENT -ge 90 ]; then
  echo "✅ EXCELLENT - Application meets all best practices"
  echo "   Recommendation: Ready for production"
elif [ $PERCENT -ge 70 ]; then
  echo "⚠️  GOOD - Application mostly compliant"
  echo "   Recommendation: Address medium-risk items before deployment"
elif [ $PERCENT -ge 50 ]; then
  echo "❌ FAIR - Several architectural issues detected"
  echo "   Recommendation: Fix critical issues before deployment"
else
  echo "🔴 POOR - Multiple critical risks"
  echo "   Recommendation: DO NOT deploy - requires significant refactoring"
fi
```

---

## Risk Mitigation Roadmap

### Priority 1 (IMMEDIATE): Fix Critical Risks

```
Timeline: Week 1
├─ [ ] Identify circular dependencies
├─ [ ] Add @EnableExperienceAPI
└─ [ ] Verify core filters in place

Success Criteria:
└─ Application starts without errors
└─ Correlation ID propagated through requests
└─ Context available to all handlers
```

### Priority 2 (URGENT): Address High Risks

```
Timeline: Week 2-3
├─ [ ] Replace generic exceptions with MCA2 types
├─ [ ] Fix filter ordering
├─ [ ] Implement data masking
└─ [ ] Verify exception handling

Success Criteria:
└─ 90%+ requests using correct exception types
└─ Filter execution order correct
└─ Sensitive data masked in logs
└─ All exceptions caught and handled properly
```

### Priority 3 (IMPORTANT): Resolve Medium Risks

```
Timeline: Week 4-6
├─ [ ] Fix layer violations
├─ [ ] Reduce coupling where possible
├─ [ ] Add comprehensive logging
└─ [ ] Implement performance monitoring

Success Criteria:
└─ No upward layer imports
└─ Coupling metrics <70%
└─ All critical operations logged
└─ Performance baseline established
```

---

## Next Steps

1. **Run Risk Assessment** — Execute automated detection script
2. **Prioritize Issues** — Organize by severity and impact
3. **Create Fix Plan** — Estimate effort for each risk
4. **Execute Remediation** — Fix critical issues first
5. **Monitor Progress** — Rerun assessment regularly

**Risk Assessment Guide enables proactive architecture quality management.**

