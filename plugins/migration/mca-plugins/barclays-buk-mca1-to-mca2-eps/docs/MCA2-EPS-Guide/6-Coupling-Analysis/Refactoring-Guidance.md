# Refactoring Guidance: Architectural Improvements

## Executive Summary

Practical strategies for improving MCA2 EPS application architecture, reducing coupling, and migrating from legacy patterns. Includes step-by-step refactoring approaches, before/after examples, and validation techniques.

---

## Refactoring Strategy Framework

### Core Principles

```
1. NO BREAKING CHANGES
   ├─ Maintain backward compatibility during refactoring
   ├─ Gradual migration over multiple sprints
   └─ Keep existing APIs stable

2. INCREMENTAL IMPROVEMENTS
   ├─ Fix one architectural issue at a time
   ├─ Test thoroughly between each change
   └─ Validate with automated checks

3. RISK MITIGATION
   ├─ Always have rollback plan
   ├─ Use feature flags for gradual rollout
   └─ Monitor metrics throughout

4. DOCUMENTATION
   ├─ Document architecture decisions
   ├─ Update diagrams and guides
   └─ Share knowledge with team
```

---

## Refactoring Pattern 1: Reduce Circular Dependencies

### Pattern 1A: Extract to Abstraction Layer

**Scenario:** Two modules have circular imports through shared interfaces

```
BEFORE (CIRCULAR):
├─ Module A
│  └─ imports ConcreteProcessorImpl from Module B
├─ Module B
│  └─ imports DataModelA from Module A
└─ Result: A ↔ B circular

AFTER (FIXED):
├─ Module API (new - interfaces only)
│  ├─ IProcessor (interface)
│  └─ IDataModel (interface)
├─ Module A (imports from API only)
│  └─ DataModelAImpl implements IDataModel
├─ Module B (imports from API only)
│  └─ ConcreteProcessorImpl implements IProcessor
└─ Result: A → API ← B (unidirectional)
```

**Step-by-Step Execution:**

**Step 1:** Create new API module (5 minutes)
```bash
mkdir -p mca-libraries/mca-processor-api/src/main/java/com/barclays/global/mca/libs/processor
cd mca-libraries/mca-processor-api

# Create build.gradle
cat > build.gradle << 'EOF'
plugins { id "java-library" }

java { sourceCompatibility = JavaVersion.VERSION_21 }

dependencies {
  // No internal MCA dependencies (keep this module in Layer 1)
}
EOF
```

**Step 2:** Extract interfaces (15 minutes)
```java
// mca-processor-api/src/main/java/com/barclays/global/mca/libs/processor/IProcessor.java
package com.barclays.global.mca.libs.processor;

public interface IProcessor {
  Result process(Request request);
}

// mca-processor-api/src/main/java/com/barclays/global/mca/libs/processor/Result.java
package com.barclays.global.mca.libs.processor;

public class Result {
  private final boolean success;
  private final String message;

  public Result(boolean success, String message) {
    this.success = success;
    this.message = message;
  }
  // getters...
}
```

**Step 3:** Update Module A (10 minutes)
```java
// BEFORE
package com.barclays.global.mca.libs.modulea;

import com.barclays.global.mca.libs.moduleb.ConcreteProcessor; // Circular!

public class DataModelA {
  private ConcreteProcessor processor;
  // PROBLEM: imports concrete impl from Module B
}

// AFTER
package com.barclays.global.mca.libs.modulea;

import com.barclays.global.mca.libs.processor.IProcessor; // Interface only

public class DataModelA {
  private IProcessor processor; // Interface, not concrete

  public DataModelA(IProcessor processor) {
    this.processor = processor; // Injected via DI
  }
}
```

**Step 4:** Update Module B (10 minutes)
```java
// BEFORE
package com.barclays.global.mca.libs.moduleb;

import com.barclays.global.mca.libs.modulea.DataModelA; // Circular!

public class ConcreteProcessorImpl {
  public Result process(DataModelA data) { }
}

// AFTER
package com.barclays.global.mca.libs.moduleb;

import com.barclays.global.mca.libs.processor.IProcessor;
import com.barclays.global.mca.libs.processor.Result;

public class ConcreteProcessorImpl implements IProcessor {
  public Result process(Request request) {
    // Doesn't import DataModelA
  }
}
```

**Step 5:** Update build.gradle dependencies (5 minutes)
```gradle
// mca-libraries/modulea/build.gradle
dependencies {
  implementation project(":mca-libraries:mca-processor-api")
  // Don't import moduleb
}

// mca-libraries/moduleb/build.gradle
dependencies {
  implementation project(":mca-libraries:mca-processor-api")
  // Don't import modulea
}
```

**Step 6:** Verify no circular imports
```bash
./gradlew :mca-libraries:modulea:dependencies | grep moduleb  # Should be empty
./gradlew :mca-libraries:moduleb:dependencies | grep modulea  # Should be empty
```

**Verification Checklist:**
```
✓ New API module has no MCA dependencies
✓ Module A imports only from API
✓ Module B imports only from API
✓ Build succeeds: ./gradlew build
✓ Tests pass: ./gradlew test
✓ No circular dependencies detected
```

**Result:**
- 🟢 Circular dependency eliminated
- 🟢 Both modules can evolve independently
- 🟢 Easier testing and mocking
- ✅ No breaking changes to consumers

---

## Refactoring Pattern 2: Reduce Tight Coupling

### Pattern 2A: Replace Direct Dependency with Dependency Injection

**Scenario:** Service tightly coupled to 8+ other modules

```
BEFORE (TIGHT COUPLING):
└─ FilterService
   ├─ new RequestProcessor() [direct instantiation]
   ├─ new ExceptionHandler()
   ├─ new LoggingService()
   ├─ new MaskingService()
   ├─ new ValidationService()
   └─ Result: 5 hard-coded dependencies

AFTER (LOOSE COUPLING):
└─ FilterService
   ├─ @Autowired RequestProcessor [injected]
   ├─ @Autowired ExceptionHandler [injected]
   ├─ @Autowired LoggingService [injected]
   ├─ @Autowired MaskingService [injected]
   ├─ @Autowired ValidationService [injected]
   └─ Result: Easy to mock, test, and replace
```

**Step-by-Step Execution:**

**Step 1:** Add Spring dependency (5 minutes)
```gradle
// build.gradle
dependencies {
  implementation "org.springframework.boot:spring-boot-starter-web"
}
```

**Step 2:** Add constructor injection (15 minutes)
```java
// BEFORE
public class FilterService {
  private RequestProcessor requestProcessor = new RequestProcessorImpl();
  private ExceptionHandler exceptionHandler = new ExceptionHandlerImpl();
  private LoggingService loggingService = new LoggingServiceImpl();

  public void executeFilter(Request request) {
    // Hard-coded dependencies above
  }
}

// AFTER
@Component
public class FilterService {
  private final RequestProcessor requestProcessor;
  private final ExceptionHandler exceptionHandler;
  private final LoggingService loggingService;

  // Constructor injection (preferred over field injection)
  public FilterService(
    RequestProcessor requestProcessor,
    ExceptionHandler exceptionHandler,
    LoggingService loggingService
  ) {
    this.requestProcessor = requestProcessor;
    this.exceptionHandler = exceptionHandler;
    this.loggingService = loggingService;
  }

  public void executeFilter(Request request) {
    // Use injected dependencies
  }
}
```

**Step 3:** Verify bean configuration (10 minutes)
```bash
# Spring Boot auto-discovers @Component
./gradlew bootRun --args='--debug' | grep "FilterService\|Created"
```

**Verification Checklist:**
```
✓ All dependencies are @Autowired or constructor-injected
✓ No new-ing dependencies (except primitives)
✓ No static service locators
✓ Tests can inject mocks
✓ Application context starts successfully
```

**Result:**
- 🟢 Loose coupling - dependencies easily replaceable
- 🟢 Testable - can inject mocks
- 🟢 Maintainable - single responsibility principle
- ✅ Zero breaking changes

---

## Refactoring Pattern 3: Break Tight Coupling with Design Patterns

### Pattern 3A: Observer Pattern (Publish-Subscribe)

**Scenario:** Multiple services tightly coupled through method calls

```
BEFORE (TIGHT COUPLING - Direct method calls):
└─ OrderService
   ├─ calls InventoryService.decrementStock()
   ├─ calls AccountingService.recordTransaction()
   ├─ calls NotificationService.sendEmail()
   ├─ calls LoggingService.logOrderCreated()
   └─ Result: OrderService tightly coupled to 4 services

AFTER (LOOSE COUPLING - Event-driven):
├─ OrderService (publishes OrderCreatedEvent)
├─ InventoryService (subscribes to OrderCreatedEvent)
├─ AccountingService (subscribes to OrderCreatedEvent)
├─ NotificationService (subscribes to OrderCreatedEvent)
├─ LoggingService (subscribes to OrderCreatedEvent)
└─ Result: Services independent, reusable events
```

**Implementation:**

**Step 1:** Define event (5 minutes)
```java
// OrderCreatedEvent.java
public class OrderCreatedEvent extends ApplicationEvent {
  private final Order order;
  private final long timestamp;

  public OrderCreatedEvent(Object source, Order order) {
    super(source);
    this.order = order;
    this.timestamp = System.currentTimeMillis();
  }

  public Order getOrder() { return order; }
  public long getTimestamp() { return timestamp; }
}
```

**Step 2:** Publisher emits event (10 minutes)
```java
// BEFORE
@Service
public class OrderService {
  private InventoryService inventory;
  private AccountingService accounting;
  private NotificationService notification;
  private LoggingService logging;

  public void createOrder(Order order) {
    inventory.decrementStock(order.getItems());      // Tight coupling
    accounting.recordTransaction(order);             // Tight coupling
    notification.sendEmail(order);                   // Tight coupling
    logging.logOrderCreated(order);                  // Tight coupling
  }
}

// AFTER
@Service
public class OrderService {
  private final ApplicationEventPublisher eventPublisher;

  @Autowired
  public OrderService(ApplicationEventPublisher eventPublisher) {
    this.eventPublisher = eventPublisher;
  }

  public void createOrder(Order order) {
    // ... create order logic ...

    // Publish event - subscribers handle the rest
    eventPublisher.publishEvent(new OrderCreatedEvent(this, order));
  }
}
```

**Step 3:** Subscribers listen to event (5 minutes each)
```java
// InventoryService
@Service
public class InventoryService {
  @EventListener
  public void onOrderCreated(OrderCreatedEvent event) {
    decrementStock(event.getOrder().getItems());
  }
}

// AccountingService
@Service
public class AccountingService {
  @EventListener
  public void onOrderCreated(OrderCreatedEvent event) {
    recordTransaction(event.getOrder());
  }
}

// NotificationService
@Service
public class NotificationService {
  @EventListener
  public void onOrderCreated(OrderCreatedEvent event) {
    sendEmail(event.getOrder());
  }
}
```

**Result:**
- 🟢 OrderService no longer depends on other services
- 🟢 New subscribers can be added without changing OrderService
- 🟢 Easy to enable/disable subscribers via configuration
- ✅ Highly extensible

---

## Refactoring Pattern 4: Migrate Legacy Patterns

### Pattern 4A: Service Locator → Dependency Injection

**Scenario:** Application using service locator (anti-pattern)

```java
// ❌ LEGACY - Service Locator Anti-Pattern
public class ServiceLocator {
  private static Map<Class<?>, Object> services = new HashMap<>();

  public static <T> void register(Class<T> clazz, T impl) {
    services.put(clazz, impl);
  }

  @SuppressWarnings("unchecked")
  public static <T> T getService(Class<T> clazz) {
    return (T) services.get(clazz);
  }
}

// Usage (WRONG)
public class OrderService {
  public void createOrder(Order order) {
    // Hidden dependency - hard to test
    InventoryService inventory = ServiceLocator.getService(InventoryService.class);
    inventory.decrementStock(order.getItems());
  }
}
```

**Migration Path (3-step approach):**

**Step 1:** Wrap service locator in adapter (Week 1)
```java
// Adapter layer - maintains compatibility
@Component
public class ServiceRegistry {
  private final ApplicationContext context;

  @Autowired
  public ServiceRegistry(ApplicationContext context) {
    this.context = context;
  }

  // Backwards-compatible method
  public <T> T getService(Class<T> clazz) {
    return context.getBean(clazz); // Use Spring instead
  }
}
```

**Step 2:** Gradually migrate to DI (Week 2-3)
```java
// BEFORE (using service locator)
public class OrderService {
  public void createOrder(Order order) {
    InventoryService inventory = ServiceLocator.getService(InventoryService.class);
    inventory.decrementStock(order.getItems());
  }
}

// AFTER (using DI)
@Service
public class OrderService {
  private final InventoryService inventory;

  @Autowired
  public OrderService(InventoryService inventory) {
    this.inventory = inventory;
  }

  public void createOrder(Order order) {
    inventory.decrementStock(order.getItems());
  }
}
```

**Step 3:** Remove service locator (Week 4)
```bash
# Find remaining service locator usages
grep -r "ServiceLocator\.get\|ServiceRegistry\.get" src/ --include="*.java"

# Should return zero results after migration complete
```

**Result:**
- 🟢 Explicit dependencies in constructor
- 🟢 Testable with mock injection
- 🟢 IDE can track usages
- ✅ No magic/hidden dependencies

---

## Refactoring Pattern 5: Enable Architectural Best Practices

### Pattern 5A: Add Conditional Enablement

**Scenario:** Framework always fully enabled, need feature toggles

```
BEFORE (All-or-nothing):
└─ @SpringBootApplication
   └─ Application always initializes ALL features

AFTER (Configurable):
├─ Core features: always enabled (@EnableExperienceAPI)
├─ Optional features: configurable (@ConditionalOnProperty)
└─ Advanced features: opt-in (@ConditionalOnProperty)
```

**Step-by-Step Execution:**

**Step 1:** Create feature properties (5 minutes)
```properties
# application.properties
mca.eps.enabled=true
mca.masking.enabled=true
mca.security.oauth.enabled=false
mca.security.ddos.enabled=true
mca.router.enabled=false
```

**Step 2:** Add conditional auto-configurations (15 minutes)
```java
// MaskingAutoConfiguration.java
@Configuration
@ConditionalOnProperty(
  name = "mca.masking.enabled",
  havingValue = "true"
)
public class MaskingAutoConfiguration {
  @Bean
  public MaskingService maskingService() {
    return new MaskingServiceImpl();
  }
}

// OAuthAutoConfiguration.java
@Configuration
@ConditionalOnProperty(
  name = "mca.security.oauth.enabled",
  havingValue = "true"
)
public class OAuthAutoConfiguration {
  @Bean
  public OAuthValidator oauthValidator() {
    return new OAuthValidatorImpl();
  }
}
```

**Step 3:** Register auto-configurations (5 minutes)
```
# META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports
com.barclays.global.mca.libs.masking.MaskingAutoConfiguration
com.barclays.global.mca.libs.security.OAuthAutoConfiguration
com.barclays.global.mca.libs.security.DdosAutoConfiguration
com.barclays.global.mca.libs.router.RouterAutoConfiguration
```

**Step 4:** Test conditional enablement (10 minutes)
```java
@SpringBootTest(properties = "mca.masking.enabled=false")
public class MaskingDisabledTest {
  @Autowired(required = false)
  private MaskingService maskingService;

  @Test
  void shouldNotLoadMaskingWhenDisabled() {
    assertThat(maskingService).isNull();
  }
}
```

**Result:**
- 🟢 Features can be enabled/disabled via properties
- 🟢 Reduces startup time when features disabled
- 🟢 Environment-specific configurations
- ✅ Gradual feature rollout capability

---

## Refactoring Roadmap & Timeline

### Month 1: Foundation (Weeks 1-4)

```
Week 1: Planning & Analysis
├─ Identify circular dependencies
├─ Measure coupling metrics
├─ Document current architecture
└─ Create refactoring plan

Week 2-3: Critical Fixes
├─ Fix circular dependencies (Pattern 1A)
├─ Add @EnableExperienceAPI
└─ Verify core filters

Week 4: Validation
├─ Run automated tests
├─ Performance baseline
├─ Document lessons learned
└─ Plan Month 2 work
```

### Month 2: Dependency Injection (Weeks 5-8)

```
Week 5-6: Replace Service Locators
├─ Identify service locator usages
├─ Create adapter layer
├─ Begin gradual migration
└─ Test thoroughly

Week 7-8: Add Constructor Injection (Pattern 2A)
├─ Convert field injection to constructor
├─ Update bean definitions
├─ Verify DI chain complete
└─ Performance validation
```

### Month 3: Design Patterns (Weeks 9-12)

```
Week 9-10: Implement Observer Pattern (Pattern 3A)
├─ Define domain events
├─ Add event publishers
├─ Add event subscribers
└─ Remove direct coupling

Week 11-12: Feature Toggles (Pattern 5A)
├─ Add conditional properties
├─ Create auto-configurations
├─ Test all combinations
└─ Document toggles
```

---

## Validation & Testing Strategy

### Automated Validation

```bash
#!/bin/bash
# validate-refactoring.sh

echo "=== Refactoring Validation ==="
echo

# Check 1: No circular dependencies
echo "Checking for circular dependencies..."
CIRCULAR=$(./gradlew dependencies 2>/dev/null | grep -E "→.*←" | wc -l)
if [ $CIRCULAR -eq 0 ]; then
  echo "✅ PASS: No circular dependencies"
else
  echo "❌ FAIL: $CIRCULAR circular dependency chains found"
  exit 1
fi

# Check 2: All beans autowired
echo "Checking for non-autowired beans..."
NONAUTO=$(grep -r "new.*Service()\|ServiceLocator.get" src/ --include="*.java" | wc -l)
if [ $NONAUTO -eq 0 ]; then
  echo "✅ PASS: All dependencies autowired"
else
  echo "⚠️  WARNING: $NONAUTO non-autowired instantiations"
fi

# Check 3: Layer compliance
echo "Checking layer compliance..."
VIOLATIONS=$(grep -r "import.*boot\|import.*autoconfigure" \
  mca-libraries/context*/src/main/java mca-libraries/exception*/src/main/java 2>/dev/null | \
  grep -v "servlet\|web" | wc -l)

if [ $VIOLATIONS -lt 3 ]; then
  echo "✅ PASS: Layer compliance maintained"
else
  echo "⚠️  WARNING: $VIOLATIONS potential layer violations"
fi

# Check 4: Test coverage
echo "Checking test coverage..."
./gradlew test --continue 2>&1 | grep -E "tests passed|tests failed"

echo
echo "✅ Validation complete"
```

---

## Success Criteria & Metrics

### Target Architecture State

```
Circular Dependencies:        0
Coupling (>70%):              0 modules
Layer Violations:             0
Service Locator Usage:        0
Constructor Injection:        >95%
Feature Toggles Working:      >90%
Test Coverage:                >85%
Build Time (clean):           <5 minutes
Startup Time (all features):  <30 seconds
Startup Time (minimal):       <15 seconds
```

---

## Common Challenges & Solutions

### Challenge 1: Breaking Changes During Refactoring

**Problem:** Refactoring creates incompatibilities with consuming code

**Solution:** Use adapter pattern, deprecation warnings, versioning

```java
// Keep old API for backward compatibility
@Deprecated(since = "2.1", forRemoval = true)
public static <T> T getService(Class<T> clazz) {
  return new ServiceRegistry().getService(clazz);
}

// Migration message
@DeprecationHandler
public void warnServiceLocatorUsage() {
  System.err.println(
    "ServiceLocator.getService() is deprecated. " +
    "Use dependency injection instead. " +
    "Will be removed in version 3.0"
  );
}
```

### Challenge 2: Tight Timeline

**Problem:** Limited time to complete all refactoring

**Solution:** Prioritize by impact, use feature flags

```
Priority 1 (Critical): Circular dependencies, @EnableExperienceAPI
Priority 2 (High): Constructor injection, service locator removal
Priority 3 (Medium): Event-driven architecture
Priority 4 (Nice-to-have): Advanced patterns
```

---

## Next Steps

1. **Choose Starting Pattern** — Pick one refactoring pattern to begin
2. **Create Plan** — Estimate timeline for your codebase
3. **Execute Incrementally** — Complete one pattern per sprint
4. **Validate Thoroughly** — Run automated checks after each change
5. **Document Progress** — Share results with team

**Refactoring Guidance enables systematic architectural improvements.**

