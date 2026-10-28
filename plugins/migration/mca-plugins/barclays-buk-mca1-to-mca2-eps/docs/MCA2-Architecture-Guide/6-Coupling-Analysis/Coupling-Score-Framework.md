# Coupling Score Framework: MCA2 EPS Quantitative Analysis

## Executive Summary

5-tier quantitative framework for measuring MCA2 EPS framework integration depth, architectural quality, and platform adoption maturity. Couples module usage counts with layering patterns and feature toggle adoption to generate actionable architecture metrics.

---

## CORE CONCEPTS

### What is Coupling Score?

**Coupling Score** measures the breadth and depth of MCA2 EPS framework integration in an application across five dimensions:

1. **Core Module Usage** - Foundation framework adoption (Context, Logging, Exception, Response, Filter)
2. **Framework Integration** - Advanced features (Routing, Proxy, Service Client, Property Resolution)
3. **Optional Extensions** - Specialized integrations (JCEKS, ServiceLocator, SSL, Legacy Clients)
4. **Architectural Layering** - Proper API→Core→Starter separation
5. **Configuration Best Practices** - Feature toggle adoption via @ConditionalOnProperty

### Why Measure Coupling?

- **Architectural Assessment** - Quantify framework adoption level
- **Risk Identification** - Spot tightly coupled components
- **Improvement Planning** - Prioritize refactoring efforts
- **Team Alignment** - Set adoption targets and track progress
- **Maintenance Cost** - Estimate upgrade and migration efforts

---

## COUPLING SCORE FORMULA

### Complete Formula

```
COUPLING_SCORE = (Core + Framework + Optional) + Layering_Bonus + Conditional_Bonus

Where:
  Core = Count(core modules) × 3
  Framework = Count(framework modules) × 2
  Optional = Count(optional modules) × 1
  Layering_Bonus = -1 × Count(properly layered components)
  Conditional_Bonus = -0.5 × Count(@ConditionalOnProperty usage)
```

### Step-by-Step Calculation

#### Step 1: Count Core Module Usage (Weight: 3)

**Core Modules (Foundation Layer):**
- mca-context
- mca-filter-core
- mca-eps-core
- mca-exception-handling-core
- mca-response-handling-core
- mca-logging-aspects

**Scoring Rules:**
- Each core module present = +3 points
- Total possible: 18 points (6 modules × 3)
- Core modules are CRITICAL - framework won't function without them

**Example:**
```
Application uses:
  ✓ mca-context                    +3
  ✓ mca-filter-core                +3
  ✓ mca-eps-core                   +3
  ✓ mca-exception-handling-core     +3
  ✓ mca-response-handling-core      +3
  ✗ mca-logging-aspects             0  (not using AspectJ weaving)

Core_Score = 15 points
```

---

#### Step 2: Count Framework Module Usage (Weight: 2)

**Framework Modules (Integration Layer):**
- mca-router-http
- mca-secure-proxy-core
- mca-service-client-starter
- mca-placeholder-starter
- mca-oauth-validator-core
- mca-masking

**Scoring Rules:**
- Each framework module present = +2 points
- Total possible: 12 points (6 modules × 2)
- Framework modules add capabilities but not required
- Presence indicates advanced feature adoption

**Example:**
```
Application uses:
  ✓ mca-service-client-starter      +2
  ✓ mca-oauth-validator-core        +2
  ✓ mca-masking                     +2
  ✗ mca-router-http                  0
  ✗ mca-secure-proxy-core            0
  ✗ mca-placeholder-starter          0

Framework_Score = 6 points
```

---

#### Step 3: Count Optional Module Usage (Weight: 1)

**Optional/Extension Modules:**
- mca-jceks-spring-properties-processor
- mca-service-locator
- mca-spring-boot-ssl
- bem-client
- mis-client
- mca-reference-data
- mca-entitlement
- mca-sso

**Scoring Rules:**
- Each optional module present = +1 point
- Total possible: 8 points (8 modules × 1)
- Optional modules indicate specialized use cases
- Minimal impact on overall integration score

**Example:**
```
Application uses:
  ✓ mca-jceks-spring-properties-processor +1
  ✗ mca-service-locator                    0
  ✓ mca-spring-boot-ssl                    +1
  ✗ bem-client                             0
  ✗ mis-client                             0
  ✗ mca-reference-data                     0
  ✗ mca-entitlement                        0
  ✗ mca-sso                                0

Optional_Score = 2 points
```

---

#### Step 4: Evaluate Architectural Layering (Bonus: -1 per layer)

**Proper Layering Pattern:**
```
Application Layer (Controllers, Endpoints)
        ↓ (imports from)
Configuration Layer (Auto-config, beans)
        ↓ (imports from)
Core Implementation Layer (Business logic)
        ↓ (imports from)
API/Interface Layer (Contracts, abstractions)
        ↓ (imports from)
Foundation Layer (utilities, no imports)
```

**Scoring Rules:**
- Each properly implemented layer = -1 point (BONUS = reduces score)
- Unidirectional dependencies = -1 point
- No circular dependencies detected = -1 point
- Maximum layering bonus: -5 points

**Example:**
```
Application Structure Assessment:

✓ Has separate config/ directory with beans           -1
✓ Has separate service/ directory for business logic  -1
✓ Has separate dto/ for data transfer objects         -1
✗ Mixes filters with controllers in same directory    0
✗ Direct service imports from controllers             0

Layering_Bonus = -3 points
```

---

#### Step 5: Feature Toggle Adoption (Bonus: -0.5 per toggle)

**Feature Toggle Indicators:**
```
@ConditionalOnProperty
@ConditionalOnMissingBean
@ConditionalOnClass
@Profile
```

**Scoring Rules:**
- Each @ConditionalOnProperty usage = -0.5 points
- Each additional conditional annotation = -0.25 points
- Maximum conditional bonus: -2.5 points
- Encourages Spring Boot best practices

**Example:**
```
@ConditionalOnProperty usage:

✓ OAuth validation filter toggle              -0.5
✓ DDoS prevention filter toggle               -0.5
✓ Masking configuration toggle                -0.5
✓ Custom feature flag                         -0.5
✓ @ConditionalOnClass checks (2 occurrences) -0.5

Conditional_Bonus = -2.5 points
```

---

### Final Calculation

**Complete Example:**

```
Application: Order Management Microservice

Step 1 - Core Module Usage:
  mca-context                    +3
  mca-filter-core                +3
  mca-eps-core                   +3
  mca-exception-handling-core     +3
  mca-response-handling-core      +3
  mca-logging-aspects             +3
  ─────────────────────────────────
  Core_Score = 18

Step 2 - Framework Module Usage:
  mca-service-client-starter      +2
  mca-oauth-validator-core        +2
  mca-masking                     +2
  ─────────────────────────────────
  Framework_Score = 6

Step 3 - Optional Module Usage:
  mca-jceks-spring-properties-processor +1
  mca-spring-boot-ssl                   +1
  ─────────────────────────────────
  Optional_Score = 2

Step 4 - Layering Bonus:
  Configuration layer: -1
  Service layer: -1
  DTO layer: -1
  Unidirectional imports: -1
  ─────────────────────────────────
  Layering_Bonus = -4

Step 5 - Conditional Bonus:
  @ConditionalOnProperty (3 occurrences): -1.5
  @ConditionalOnClass (2 occurrences): -0.5
  ─────────────────────────────────
  Conditional_Bonus = -2.0

─────────────────────────────────────────────
TOTAL COUPLING SCORE = 18 + 6 + 2 - 4 - 2 = 20
```

---

## TIER CLASSIFICATION SYSTEM

### Tier 1: Minimal Integration (Score 0-3)

**Characteristics:**
- Single logger or basic context usage
- No filter chain customization
- Minimal framework features
- Likely demo or non-critical application
- Single exception type or no custom handling

**Examples:**
- Simple CRUD service with one logger
- Configuration server with no context
- Utility microservice with minimal features

**Improvement Path:**
1. Add mca-context for request context propagation
2. Enable mca-filter-core for request processing
3. Implement mca-exception-handling-core for standardized errors
4. Activate mca-response-handling-core for response envelopes

**Score 0:**
```
  Minimal logging only
  No context system
  No filter chain
```

**Score 1-2:**
```
  Basic logger configured
  No other framework usage
```

**Score 3:**
```
  Single core module (filter OR exception OR response)
  No layering structure
```

---

### Tier 2: Core Framework (Score 4-8)

**Characteristics:**
- All core modules implemented (context, logging, exception, response, filter)
- Basic filter chain with required filters
- Request context propagation working
- Standardized exception handling
- Standard response envelope
- Some basic layering

**Examples:**
- New REST microservice following framework patterns
- Team adopting MCA2 framework for first time
- Application with context-based multi-tenancy
- Service with basic error handling

**Improvement Path:**
1. Add mca-service-client-starter for distributed calls
2. Implement proper layering (API→Core→Starter)
3. Add OAuth validation (mca-oauth-validator-core)
4. Enable feature toggles (@ConditionalOnProperty)

**Score 4-5:**
```
  3-4 core modules present
  Basic layering starting
  No framework modules yet
```

**Score 6-7:**
```
  All 5-6 core modules implemented
  Basic layering structure
  1-2 conditional toggles
```

**Score 8:**
```
  All core modules
  Good layering (-2 to -3 bonus)
  Multiple conditional toggles (-1 to -1.5 bonus)
```

---

### Tier 3: Moderate Integration (Score 9-15)

**Characteristics:**
- All core modules + 2-3 framework modules
- RestTemplate with context propagation
- Comprehensive exception handling
- Request whitelisting or DDoS prevention
- Proper layering implemented
- Multiple feature toggles
- Data masking for sensitive fields
- Some service-to-service integration

**Examples:**
- Mature REST microservice
- API gateway with routing
- Service orchestrating multiple backends
- Application with comprehensive security
- Multi-tenant application with masking

**Improvement Path:**
1. Add secure proxy integration (mca-secure-proxy-core)
2. Implement circuit breaker patterns
3. Add comprehensive logging with masking
4. Full conditional bean registration
5. Complete architectural refactoring

**Score 9-11:**
```
  All core modules (18 points)
  1-2 framework modules (2-4 points)
  Moderate layering bonus (-2 to -3)
  Basic conditional bonus (-0.5 to -1)
```

**Score 12-14:**
```
  All core modules (18 points)
  2-3 framework modules (4-6 points)
  Good layering bonus (-3 to -4)
  Strong conditional bonus (-1.5 to -2)
```

**Score 15:**
```
  All core modules (18 points)
  3+ framework modules (6+ points)
  Excellent layering bonus (-4 to -5)
  Maximum conditional bonus (-2 to -2.5)
  Optional modules (-1 to -2)
```

---

### Tier 4: Heavy Integration (Score 16-25)

**Characteristics:**
- All core + most framework modules
- Secure proxy integration
- Circuit breaker/resilience patterns
- Complex routing logic
- Comprehensive REST client patterns
- Advanced configuration management
- Property resolution chains
- Full feature toggle adoption
- 1-2 optional modules

**Examples:**
- API gateway with advanced routing
- Service mesh entry point
- Central authentication service
- Complex event processor
- Multi-tenant platform core

**Improvement Path:**
1. Maximize conditional bean registration
2. Add remaining optional modules
3. Implement complete architectural patterns
4. Add comprehensive monitoring/tracing
5. Production hardening

**Score 16-20:**
```
  All core modules (18 points)
  3-4 framework modules (6-8 points)
  Strong layering bonus (-4 to -5)
  Strong conditional bonus (-2 to -2.5)
  1-2 optional modules (-1 to -2)
```

**Score 21-25:**
```
  All core modules (18 points)
  4-5 framework modules (8-10 points)
  Excellent layering bonus (-4 to -5)
  Maximum conditional bonus (-2 to -2.5)
  2+ optional modules (-2 to -3)
```

---

### Tier 5: Full Platform Integration (Score 26+)

**Characteristics:**
- All core + all framework modules
- All optional modules integrated
- Enterprise-scale architecture
- Complete feature toggle coverage
- Maximum architectural layering
- Production-grade resilience
- Comprehensive monitoring
- Full migration from legacy systems

**Examples:**
- Central platform service
- Migration-in-progress legacy→MCA2
- Flagship application demonstrating patterns
- Reference implementation for other teams
- Production platform core

**Improvement Path:**
1. Monitor and optimize performance
2. Refine and consolidate patterns
3. Share learnings with other teams
4. Consider contribution to framework
5. Plan for next-generation patterns

**Score 26+:**
```
  All core modules (18 points)
  All framework modules (12 points)
  2-3+ optional modules (2-3+ points)
  Maximum layering bonus (-4 to -5)
  Maximum conditional bonus (-2 to -2.5)
  Strategic integrations (-2+ points)
```

---

## REFERENCE TIER TABLE

| Tier | Score Range | Adoption Level | Core Modules | Framework Modules | Optional Modules | Layering | Feature Toggles |
|------|------------|---|---|---|---|---|---|
| 1 | 0-3 | Minimal | 0-1 | 0 | 0 | None | None |
| 2 | 4-8 | Core | 4-6 | 0-1 | 0 | Basic | Few |
| 3 | 9-15 | Moderate | 6 | 2-3 | 0-1 | Good | Multiple |
| 4 | 16-25 | Heavy | 6 | 3-5 | 1-2 | Excellent | Comprehensive |
| 5 | 26+ | Full | 6 | 5-6 | 2-3 | Maximum | Maximum |

---

## RISK ASSESSMENT SCORING

### Risk Categories

#### 1. Coupling Tightness Risk (0-10)

**Formula:**
```
COUPLING_TIGHTNESS = (Total_Import_Count / Total_File_Count) × 10
```

**Interpretation:**
- 0-2: Loose coupling (GOOD)
- 2-5: Moderate coupling (OK)
- 5-7: Tight coupling (CAUTION)
- 7-10: Very tight coupling (RISK)

**Mitigation:**
- Implement dependency injection
- Create facade patterns
- Use service locator strategically
- Apply @ConditionalOnProperty toggles

**Example:**
```
OrderService imports:
  - RestTemplate (1)
  - OrderRepository (1)
  - CustomerService (1)
  - NotificationService (1)
  - LogService (1)
  - ContextUtil (1)
  - ExceptionHandler (1)

Total imports: 7
Total files in application: 45
Coupling_Tightness = (7 / 45) × 10 = 1.56 (GOOD)
```

---

#### 2. Circular Dependency Risk (0-10)

**Detection:**
```
A → B
B → C
C → A (CIRCULAR!)
```

**Scoring:**
- No circular dependencies: 0 (GOOD)
- 1-2 circular dependency chains: 3 (CAUTION)
- 3-5 circular chains: 6 (RISK)
- 5+ circular chains: 10 (SEVERE RISK)

**Mitigation:**
- Extract common interfaces to third package
- Apply Observer pattern
- Use events/messaging
- Refactor into separate modules

---

#### 3. Layering Violation Risk (0-10)

**Violation Types:**
1. Controller → Repository (skip service layer)
2. Service → Service (circular dependencies)
3. Utility → Business logic (wrong direction)

**Scoring:**
- No violations: 0 (GOOD)
- 1-2 violations: 3 (CAUTION)
- 3-5 violations: 6 (RISK)
- 5+ violations: 10 (SEVERE RISK)

**Example Risk Calculation:**
```
Layering Violations Found:
  1. OrderController → OrderRepository (skip service)
  2. PaymentService → OrderService → PaymentService (circular)
  3. UtilityClass → CustomerRepository (wrong direction)

Violation_Count = 3
Layering_Violation_Risk = 3 × 2 = 6 (RISK)
```

---

#### 4. Technology Debt Risk (0-10)

**Components:**
- Deprecated patterns (2 points each)
- Unmaintained dependencies (3 points each)
- Code duplication >10% (2 points)
- Test coverage <50% (3 points)
- Missing documentation (1 point)

**Example:**
```
Technology Debt Assessment:
  - Using old servlet filters (2)
  - Old version of Spring (3)
  - 15% code duplication (2)
  - 45% test coverage (3)
  - No architecture documentation (1)

Total_Debt = 11 points → Normalize to 10
Technology_Debt_Risk = 10 (SEVERE RISK)
```

---

### Overall Risk Score

```
OVERALL_RISK_SCORE = (
  Coupling_Tightness +
  Circular_Dependency +
  Layering_Violation +
  Technology_Debt
) / 4

Risk_Rating:
  0-2: LOW RISK (Green) - Proceed confidently
  2-4: MODERATE RISK (Yellow) - Monitor closely
  4-6: HIGH RISK (Orange) - Plan improvements
  6-8: VERY HIGH RISK (Red) - Immediate action needed
  8-10: CRITICAL RISK (Dark Red) - Urgent refactoring
```

---

## ARCHITECTURE QUALITY METRICS

### Metric 1: Module Cohesion (0-100%)

**Definition:** Ratio of internal module relationships to total relationships

```
COHESION = (Internal_Relationships / Total_Relationships) × 100
```

**Target:**
- 70%+: Good cohesion
- 50-70%: Acceptable
- <50%: Poor cohesion

**Example:**
```
Module: OrderService
  Internal relationships (ServiceHelper, ValueObject): 8
  External relationships (external services): 5
  Total: 13

Cohesion = (8 / 13) × 100 = 61.5% (Acceptable)
```

---

### Metric 2: Framework Adoption Coverage (0-100%)

**Definition:** Percentage of recommended framework features in use

```
ADOPTION_COVERAGE = (Features_Implemented / Features_Available) × 100
```

**Features Checklist:**
- [ ] Context propagation
- [ ] Filter chain customization
- [ ] Exception hierarchy
- [ ] Response envelope
- [ ] Data masking
- [ ] OAuth validation
- [ ] DDoS prevention
- [ ] Layered architecture
- [ ] Feature toggles
- [ ] Service-to-service integration

**Example:**
```
Features Implemented: 7
Features Available: 10

Adoption_Coverage = (7 / 10) × 100 = 70%
```

---

### Metric 3: Dependency Graph Depth (1-N)

**Definition:** Maximum depth of dependency chain

```
DEPENDENCY_DEPTH = Maximum(Path Length from any module to foundation)
```

**Optimal:**
- 3-4: Good (manageable)
- 4-5: Acceptable
- 5+: Too deep (refactor needed)

**Example:**
```
Deepest chain:
  OrderController
    → OrderService
      → OrderRepository
        → DataSource
          → Connection Pool

Depth = 5 (ACCEPTABLE, monitor)
```

---

### Metric 4: Test Coverage Index (0-100%)

**Definition:** Percentage of business logic covered by tests

```
TEST_COVERAGE = (Lines_Tested / Total_Lines) × 100
```

**Requirements by Tier:**
- Tier 1-2: 50%+ (basic)
- Tier 3: 70%+ (moderate)
- Tier 4: 85%+ (advanced)
- Tier 5: 95%+ (production)

**Example:**
```
Order Service:
  Total lines: 500
  Lines covered: 425
  Coverage = (425 / 500) × 100 = 85% (Advanced tier requirement)
```

---

### Metric 5: Configuration Externalization Index (0-100%)

**Definition:** Percentage of configurable properties externalized

```
CONFIG_INDEX = (Properties_Externalized / Total_Properties) × 100
```

**Properties Checklist:**
- [ ] Logging levels
- [ ] Connection timeouts
- [ ] Thread pool sizes
- [ ] Feature flags
- [ ] Security settings
- [ ] Cache TTLs
- [ ] Rate limits
- [ ] Error thresholds

**Example:**
```
Total configurable properties: 25
Externalized: 22

Config_Index = (22 / 25) × 100 = 88% (Excellent)
```

---

## AUTOMATED CALCULATION ALGORITHMS

### Algorithm 1: Coupling Score Calculator

```java
public class CouplingScoreCalculator {

    public double calculateCouplingScore(Application app) {
        // Step 1: Count core modules
        int coreModules = countCoreModulesUsed(app);
        double coreScore = coreModules * 3;

        // Step 2: Count framework modules
        int frameworkModules = countFrameworkModulesUsed(app);
        double frameworkScore = frameworkModules * 2;

        // Step 3: Count optional modules
        int optionalModules = countOptionalModulesUsed(app);
        double optionalScore = optionalModules * 1;

        // Step 4: Layering bonus
        double layeringBonus = -1 * assessLayering(app);

        // Step 5: Conditional bonus
        double conditionalBonus = -0.5 * countConditionalBeans(app);

        // Total
        double totalScore = coreScore + frameworkScore + optionalScore
                          + layeringBonus + conditionalBonus;

        return Math.max(0, totalScore);  // Ensure non-negative
    }

    private int countCoreModulesUsed(Application app) {
        int count = 0;
        String[] coreModules = {
            "mca-context",
            "mca-filter-core",
            "mca-eps-core",
            "mca-exception-handling-core",
            "mca-response-handling-core",
            "mca-logging-aspects"
        };

        for (String module : coreModules) {
            if (app.hasDependency(module)) count++;
        }
        return count;
    }

    private int countFrameworkModulesUsed(Application app) {
        int count = 0;
        String[] frameworkModules = {
            "mca-router-http",
            "mca-secure-proxy-core",
            "mca-service-client-starter",
            "mca-placeholder-starter",
            "mca-oauth-validator-core",
            "mca-masking"
        };

        for (String module : frameworkModules) {
            if (app.hasDependency(module)) count++;
        }
        return count;
    }

    private int countOptionalModulesUsed(Application app) {
        int count = 0;
        String[] optionalModules = {
            "mca-jceks-spring-properties-processor",
            "mca-service-locator",
            "mca-spring-boot-ssl",
            "bem-client",
            "mis-client",
            "mca-reference-data",
            "mca-entitlement",
            "mca-sso"
        };

        for (String module : optionalModules) {
            if (app.hasDependency(module)) count++;
        }
        return count;
    }

    private int assessLayering(Application app) {
        int layers = 0;

        if (app.hasDirectory("config")) layers++;
        if (app.hasDirectory("service")) layers++;
        if (app.hasDirectory("repository")) layers++;
        if (app.hasDirectory("dto")) layers++;
        if (hasUnidirectionalDependencies(app)) layers++;

        return Math.min(layers, 5);  // Max 5 layers
    }

    private int countConditionalBeans(Application app) {
        int count = 0;
        count += app.findAnnotation("@ConditionalOnProperty").size();
        count += app.findAnnotation("@ConditionalOnClass").size() / 2;
        count += app.findAnnotation("@ConditionalOnMissingBean").size() / 2;
        return count;
    }

    public String classifyTier(double score) {
        if (score <= 3) return "Tier 1 - Minimal";
        if (score <= 8) return "Tier 2 - Core";
        if (score <= 15) return "Tier 3 - Moderate";
        if (score <= 25) return "Tier 4 - Heavy";
        return "Tier 5 - Full Platform";
    }
}
```

### Algorithm 2: Risk Assessment Calculator

```java
public class RiskAssessmentCalculator {

    public RiskProfile assessRisks(Application app) {
        double couplingRisk = calculateCouplingTightness(app);
        double circularRisk = detectCircularDependencies(app);
        double layeringRisk = assessLayeringViolations(app);
        double debtRisk = assessTechDebt(app);

        double overallRisk = (couplingRisk + circularRisk +
                            layeringRisk + debtRisk) / 4;

        return new RiskProfile(couplingRisk, circularRisk,
                             layeringRisk, debtRisk, overallRisk);
    }

    private double calculateCouplingTightness(Application app) {
        int totalImports = app.countTotalImports();
        int totalFiles = app.countTotalFiles();

        if (totalFiles == 0) return 0;
        return (totalImports / (double) totalFiles) * 10;
    }

    private double detectCircularDependencies(Application app) {
        List<Cycle> cycles = app.findDependencyCycles();
        int cycleCount = cycles.size();

        if (cycleCount == 0) return 0;
        if (cycleCount <= 2) return 3;
        if (cycleCount <= 5) return 6;
        return 10;
    }

    private double assessLayeringViolations(Application app) {
        int violations = 0;

        // Check for direct controller→repository access
        violations += app.findDependencies("controller", "repository").size();

        // Check for circular service dependencies
        violations += app.findCircularDependencies("service").size();

        // Normalize to 0-10 scale
        return Math.min(violations * 2, 10);
    }

    private double assessTechDebt(Application app) {
        double debt = 0;

        // Deprecated patterns
        debt += app.findDeprecatedPatterns().size() * 2;

        // Unmaintained dependencies
        debt += app.findOutdatedDependencies().size() * 3;

        // Code duplication
        double duplication = app.calculateCodeDuplication();
        if (duplication > 0.1) debt += 2;

        // Test coverage
        double coverage = app.getTestCoverage();
        if (coverage < 0.5) debt += 3;

        // Missing documentation
        if (!app.hasArchitectureDoc()) debt += 1;

        return Math.min(debt, 10);
    }
}
```

---

## SAMPLE APPLICATION ANALYSIS

### Example 1: Simple REST API (Tier 2)

```
Application: CustomerService v1.0
Purpose: Customer CRUD REST API
Team Size: 2 developers

COUPLING SCORE CALCULATION:

Core Modules (×3):
  ✓ mca-context                    +3
  ✓ mca-filter-core                +3
  ✓ mca-eps-core                   +3
  ✓ mca-exception-handling-core     +3
  ✓ mca-response-handling-core      +3
  ✗ mca-logging-aspects             0
  ─────────────────────────────────
  Core_Score = 15

Framework Modules (×2):
  ✗ All framework modules           0
  ─────────────────────────────────
  Framework_Score = 0

Optional Modules (×1):
  ✗ All optional modules            0
  ─────────────────────────────────
  Optional_Score = 0

Layering Bonus (-1 per layer):
  ✓ config/ directory              -1
  ✓ service/ directory             -1
  ✗ No repository layer             0
  ✗ No DTO layer                    0
  ─────────────────────────────────
  Layering_Bonus = -2

Conditional Bonus (-0.5 per toggle):
  ✓ One @ConditionalOnProperty    -0.5
  ─────────────────────────────────
  Conditional_Bonus = -0.5

─────────────────────────────────────────────
TOTAL SCORE = 15 + 0 + 0 - 2 - 0.5 = 12.5

TIER: Tier 3 - Moderate Integration
STATUS: Good baseline, room for growth
RECOMMENDATIONS:
  1. Add mca-service-client-starter for service calls
  2. Implement complete layering (add DTO/repository)
  3. Add more @ConditionalOnProperty toggles
```

---

### Example 2: API Gateway (Tier 4)

```
Application: API Gateway v2.0
Purpose: Central request routing and security
Team Size: 8 developers

COUPLING SCORE CALCULATION:

Core Modules (×3):
  ✓ mca-context                    +3
  ✓ mca-filter-core                +3
  ✓ mca-eps-core                   +3
  ✓ mca-exception-handling-core     +3
  ✓ mca-response-handling-core      +3
  ✓ mca-logging-aspects             +3
  ─────────────────────────────────
  Core_Score = 18

Framework Modules (×2):
  ✓ mca-router-http                 +2
  ✓ mca-secure-proxy-core           +2
  ✓ mca-service-client-starter      +2
  ✓ mca-placeholder-starter         +2
  ✓ mca-oauth-validator-core        +2
  ✓ mca-masking                     +2
  ─────────────────────────────────
  Framework_Score = 12

Optional Modules (×1):
  ✓ mca-jceks-spring-properties-processor +1
  ✓ mca-spring-boot-ssl             +1
  ✗ mca-service-locator             0
  ─────────────────────────────────
  Optional_Score = 2

Layering Bonus (-1 per layer):
  ✓ config/ directory              -1
  ✓ router/ directory              -1
  ✓ filter/ directory              -1
  ✓ client/ directory              -1
  ✓ Unidirectional dependencies    -1
  ─────────────────────────────────
  Layering_Bonus = -5

Conditional Bonus (-0.5 per toggle):
  ✓ OAuth validation toggle        -0.5
  ✓ DDoS prevention toggle         -0.5
  ✓ Masking toggle                 -0.5
  ✓ Router configuration toggle    -0.5
  ✓ Custom feature toggles (2)     -1.0
  ─────────────────────────────────
  Conditional_Bonus = -3.0

─────────────────────────────────────────────
TOTAL SCORE = 18 + 12 + 2 - 5 - 3.0 = 24

TIER: Tier 4 - Heavy Integration
STATUS: Excellent - Production-ready
QUALITY METRICS:
  - Module Cohesion: 78%
  - Test Coverage: 87%
  - Circular Dependencies: 0
  - Layering Violations: 0
  - Configuration Index: 92%
```

---

## IMPROVEMENT RECOMMENDATIONS BY TIER

### Tier 1 → Tier 2 (Minimal → Core)

**Current State:** Single module or minimal usage
**Target:** All core modules implemented

**Action Items:**
1. Add mca-context to build.gradle
2. Create @Configuration class with @EnableExperienceAPI
3. Configure exception handlers using MCA2 exceptions
4. Implement exception handlers using MCA2 exceptions
5. Add filter chain configuration

**Estimated Effort:** 2-3 days
**Impact:** Foundation for all future improvements

---

### Tier 2 → Tier 3 (Core → Moderate)

**Current State:** Core framework working
**Target:** Add framework modules and proper layering

**Action Items:**
1. Refactor into layers (config, service, dto, repository)
2. Add mca-service-client-starter for REST calls
3. Implement OAuth validation (mca-oauth-validator-core)
4. Add data masking (mca-masking) for sensitive fields
5. Create @ConditionalOnProperty toggles for features

**Estimated Effort:** 5-7 days
**Impact:** Better service orchestration and security

---

### Tier 3 → Tier 4 (Moderate → Heavy)

**Current State:** Multiple framework modules in use
**Target:** Complete integration with all frameworks

**Action Items:**
1. Implement mca-secure-proxy-core for session management
2. Add mca-router-http for advanced routing
3. Implement circuit breaker patterns
4. Add comprehensive logging with AspectJ weaving
5. Complete @ConditionalOnProperty coverage
6. Add optional modules (JCEKS, SSL)

**Estimated Effort:** 10-14 days
**Impact:** Enterprise-grade resilience and security

---

### Tier 4 → Tier 5 (Heavy → Full Platform)

**Current State:** Most frameworks implemented
**Target:** Complete platform integration

**Action Items:**
1. Add remaining optional modules
2. Maximize @ConditionalOnProperty usage
3. Implement full monitoring/tracing
4. Complete migration from legacy patterns
5. Achieve maximum architectural layering
6. Document patterns for team reuse

**Estimated Effort:** 15-20 days
**Impact:** Reference implementation for organization

---

## INTEGRATION WITH CI/CD

### Automated Scoring in Pipeline

```yaml
name: MCA2 Coupling Analysis

on: [push, pull_request]

jobs:
  coupling-score:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Calculate Coupling Score
        run: |
          ./scripts/calculate-coupling-score.sh
          ./scripts/assess-risks.sh
          ./scripts/generate-report.sh

      - name: Comment PR with Results
        if: github.event_name == 'pull_request'
        uses: actions/github-script@v6
        with:
          script: |
            const fs = require('fs');
            const report = fs.readFileSync('coupling-report.md', 'utf8');
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: report
            });

      - name: Fail if Risk Too High
        run: |
          RISK=$(grep "OVERALL_RISK" coupling-report.md | cut -d: -f2)
          if [ "$RISK" -gt 7 ]; then
            echo "Risk score $RISK exceeds threshold of 7"
            exit 1
          fi
```

---

**Coupling Score Framework provides quantitative architecture assessment methodology for MCA2 EPS applications.**

