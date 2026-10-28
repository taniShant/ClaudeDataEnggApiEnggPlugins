# Lessons Learned - Resilience4j Implementation

**Reference Project:** cc-domain-qry-account
**Library:** system-core-resilience4j:1.0.5
**Date:** December 2025

---

## Overview

Resilience4j is a lightweight fault tolerance library designed for Java functional programming. In SDK3 projects, it provides Circuit Breaker, Bulkhead, and Time Limiter patterns for resilient service-to-service communication with primary/fallback strategy.

---

## Migrating from Hystrix to Resilience4j

**If your project uses Hystrix (e.g., `system-core-hystrix`), you MUST migrate to Resilience4j for SDK3.**

### Property Mapping: Hystrix → Resilience4j

| Hystrix Property | Resilience4j Property |
|------------------|----------------------|
| `hystrix.threadpool.default.coreSize` | `resilience4j.thread-pool-bulkhead.configs.default.coreThreadPoolSize` |
| `hystrix.threadpool.default.maximumSize` | `resilience4j.thread-pool-bulkhead.configs.default.maxThreadPoolSize` |
| `hystrix.threadpool.default.maxQueueSize` | `resilience4j.thread-pool-bulkhead.configs.default.queueCapacity` |
| `hystrix.threadpool.default.keepAliveTimeMinutes` | `resilience4j.thread-pool-bulkhead.configs.default.keepAliveDuration` (in ms) |
| `hystrix.command.default.circuitBreaker.requestVolumeThreshold` | `resilience4j.circuitbreaker.configs.default.minimumNumberOfCalls` |
| `hystrix.command.default.circuitBreaker.errorThresholdPercentage` | `resilience4j.circuitbreaker.configs.default.failureRateThreshold` |
| `hystrix.command.default.circuitBreaker.sleepWindowInMilliseconds` | `resilience4j.circuitbreaker.configs.default.waitDurationInOpenState` |
| `hystrix.command.default.execution.isolation.thread.timeoutInMilliseconds` | `resilience4j.timelimiter.configs.default.timeoutDuration` |
| `hystrix.ignore.exceptions[N]` | `resilience4j.ignore.for-all-services.exceptions[N]` |
| `hystrix.command.<name>.execution.isolation.thread.timeoutInMilliseconds` | `resilience4j.timelimiter.instances.<name>.timeoutDuration` |

### Example Conversion

**Hystrix (hystrix-config.properties):**
```properties
hystrix.threadpool.default.coreSize=5
hystrix.threadpool.default.maximumSize=5
hystrix.threadpool.default.maxQueueSize=5
hystrix.command.default.circuitBreaker.requestVolumeThreshold=20
hystrix.command.default.circuitBreaker.errorThresholdPercentage=50
hystrix.command.default.circuitBreaker.sleepWindowInMilliseconds=5000
hystrix.command.default.execution.isolation.thread.timeoutInMilliseconds=10000
hystrix.ignore.exceptions[0]=com.barclaycard.digital.core.exception.NotFoundException
hystrix.command.fromAccountOds.execution.isolation.thread.timeoutInMilliseconds=750
hystrix.command.fromAccountTrh.execution.isolation.thread.timeoutInMilliseconds=9250
```

**Resilience4j (resilience4j-config.properties):**
```properties
resilience4j.thread-pool-bulkhead.configs.default.coreThreadPoolSize=5
resilience4j.thread-pool-bulkhead.configs.default.maxThreadPoolSize=5
resilience4j.thread-pool-bulkhead.configs.default.queueCapacity=5
resilience4j.circuitbreaker.configs.default.minimumNumberOfCalls=20
resilience4j.circuitbreaker.configs.default.failureRateThreshold=50
resilience4j.circuitbreaker.configs.default.waitDurationInOpenState=5000
resilience4j.timelimiter.configs.default.timeoutDuration=10000
resilience4j.ignore.for-all-services.exceptions[0]=com.barclaycard.digital.core.exception.NotFoundException
resilience4j.timelimiter.instances.fromAccountOds.timeoutDuration=750
resilience4j.timelimiter.instances.fromAccountTrh.timeoutDuration=9250
```

### What to Remove

**build.gradle:**
```gradle
// ❌ REMOVE
implementation 'com.barclaycard.digital:system-core-hystrix:3.1.0'
```

**Delete file:** `src/main/resources/hystrix-config.properties`

---

## 1. Required Dependency

### build.gradle

```gradle
dependencies {
    implementation 'com.barclaycard.digital:system-core-resilience4j:1.0.5'
}
```

**Key Points:**
- The `system-core-resilience4j` library is a Barclays wrapper around standard `io.github.resilience4j`
- Provides custom configurations like `CustomContextPropagator` and `Resilience4jIgnoreExceptionMarker`
- No need to add individual resilience4j modules - included transitively

---

## 2. Properties File Configuration

Create `src/main/resources/resilience4j-config.properties`:

### 2.1 Circuit Breaker Configuration

```properties
#default circuit-breaker config
resilience4j.circuitbreaker.configs.default.slidingWindowSize=10
resilience4j.circuitbreaker.configs.default.failureRateThreshold=50
resilience4j.circuitbreaker.configs.default.ignoreExceptions=com.barclaycard.digital.core.exception.Resilience4jIgnoreExceptionMarker

#Additional circuit breaker properties (optional but recommended)
resilience4j.circuitbreaker.configs.default.permittedNumberOfCallsInHalfOpenState=3
resilience4j.circuitbreaker.configs.default.automaticTransitionFromOpenToHalfOpenEnabled=true
resilience4j.circuitbreaker.configs.default.waitDurationInOpenState=60000
resilience4j.circuitbreaker.configs.default.slowCallRateThreshold=100
resilience4j.circuitbreaker.configs.default.slowCallDurationThreshold=60000
resilience4j.circuitbreaker.configs.default.slidingWindowType=COUNT_BASED
resilience4j.circuitbreaker.configs.default.minimumNumberOfCalls=5
resilience4j.circuitbreaker.configs.default.recordExceptions=java.lang.Exception
```

**Circuit Breaker State Machine:**
```
                    failureRateThreshold exceeded
    ┌─────────┐ ────────────────────────────────────► ┌─────────┐
    │ CLOSED  │                                        │  OPEN   │
    │ (normal)│ ◄──────────────────────────────────── │(failing)│
    └─────────┘     success in HALF_OPEN               └─────────┘
         ▲                                                  │
         │                                                  │ waitDurationInOpenState
         │         ┌───────────┐                            │
         └──────── │ HALF_OPEN │ ◄──────────────────────────┘
           success │ (testing) │ failure → back to OPEN
                   └───────────┘
```

**Circuit Breaker Properties Explained:**

| Property | Default | Description |
|----------|---------|-------------|
| `slidingWindowSize` | 10 | Number of calls to track for failure rate calculation |
| `slidingWindowType` | COUNT_BASED | `COUNT_BASED` or `TIME_BASED` |
| `failureRateThreshold` | 50 | Percentage of failures before circuit opens (0-100) |
| `slowCallRateThreshold` | 100 | Percentage of slow calls threshold |
| `slowCallDurationThreshold` | 60000 | Duration (ms) to consider a call slow |
| `minimumNumberOfCalls` | 5 | Minimum calls before calculating failure rate |
| `permittedNumberOfCallsInHalfOpenState` | 3 | Test calls allowed when half-open |
| `waitDurationInOpenState` | 60000 | Time (ms) before transitioning to half-open |
| `automaticTransitionFromOpenToHalfOpenEnabled` | true | Auto-transition without waiting for call |
| `ignoreExceptions` | - | Exceptions that don't count as failures |
| `recordExceptions` | - | Exceptions that count as failures |

**Named Circuit Breaker Instances:**
```properties
#Create named configuration
resilience4j.circuitbreaker.configs.aggressive.slidingWindowSize=5
resilience4j.circuitbreaker.configs.aggressive.failureRateThreshold=30
resilience4j.circuitbreaker.configs.aggressive.waitDurationInOpenState=30000

#Apply to specific service
resilience4j.circuitbreaker.instances.critical-service.baseConfig=aggressive
resilience4j.circuitbreaker.instances.normal-service.baseConfig=default
```

### 2.2 Thread Pool Bulkhead Configuration

```properties
#default threadpool config
resilience4j.thread-pool-bulkhead.configs.default.maxThreadPoolSize=100
resilience4j.thread-pool-bulkhead.configs.default.coreThreadPoolSize=20
resilience4j.thread-pool-bulkhead.configs.default.queueCapacity=100
resilience4j.thread-pool-bulkhead.configs.default.keepAliveDuration=60000
resilience4j.thread-pool-bulkhead.configs.default.writableStackTraceEnabled=true
resilience4j.thread-pool-bulkhead.configs.default.contextPropagators=com.barclaycard.digital.core.resilience4j.config.CustomContextPropagator
```

| Property | Value | Description |
|----------|-------|-------------|
| `maxThreadPoolSize` | 100 | Maximum threads in pool |
| `coreThreadPoolSize` | 20 | Core threads always kept alive |
| `queueCapacity` | 100 | Queue size for waiting tasks |
| `keepAliveDuration` | 60000 | Idle thread timeout (ms) |
| `writableStackTraceEnabled` | true | Enable stack traces for BulkheadFullException |
| `contextPropagators` | CustomContextPropagator | Propagates request context to async threads |

### 2.3 Time Limiter Configuration

```properties
#default time limiter config
resilience4j.timelimiter.configs.default.timeoutDuration=10000
resilience4j.timelimiter.configs.default.cancelRunningFuture=true

#Scheduled executor for TimeLimiter - REQUIRED for context propagation
resilience4j.scheduled.executor.corePoolSize=20
resilience4j.scheduled.executor.contextPropagators=com.barclaycard.digital.core.resilience4j.config.CustomContextPropagator

#Named timeout configurations
resilience4j.timelimiter.configs.primary.timeoutDuration=1000
resilience4j.timelimiter.configs.fallback.timeoutDuration=3000

#Service instances using named configs
resilience4j.timelimiter.instances.primary-service.baseConfig=primary
resilience4j.timelimiter.instances.fallback-service.baseConfig=fallback
resilience4j.timelimiter.instances.payAmountPercentage-primary-service.baseConfig=primary
resilience4j.timelimiter.instances.payAmountPercentage-fallback-service.baseConfig=fallback
```

| Property | Value | Description |
|----------|-------|-------------|
| `timeoutDuration` | 10000 | Default timeout in milliseconds |
| `cancelRunningFuture` | true | Cancel the CompletableFuture if timeout occurs |
| `configs.primary.timeoutDuration` | 1000 | Primary service timeout (1 second) |
| `configs.fallback.timeoutDuration` | 3000 | Fallback service timeout (3 seconds) |

### 2.4 Exception Ignore Configuration

```properties
#Configure exceptions where fallback is NOT triggered (per-service)
resilience4j.ignore.fallback-mappings[0].class-name=com.barclays.api.account.service.accounts.AccountQueryProxyService
resilience4j.ignore.fallback-mappings[0].exceptions=com.barclaycard.digital.core.exception.NotFoundException,com.barclaycard.digital.core.ods.exception.OdsInternalIssueException

resilience4j.ignore.fallback-mappings[1].class-name=com.barclays.api.account.service.virtualcards.VirtualCardsQueryProxyService
resilience4j.ignore.fallback-mappings[1].exceptions=com.barclaycard.digital.core.exception.NotFoundException,com.barclaycard.digital.core.ods.exception.OdsInternalIssueException

#Global exceptions to ignore for ALL services
resilience4j.ignore.for-all-services.exceptions[0]=com.barclaycard.digital.core.ods.exception.OdsRuntimeException
resilience4j.ignore.for-all-services.exceptions[1]=com.barclaycard.digital.core.ods.exception.OdsBadRequestException
```

**Why Ignore Exceptions:**
- `NotFoundException` - Business logic exception, should propagate not trigger fallback
- `OdsBadRequestException` - Client error, fallback won't help
- `OdsRuntimeException` - Unrecoverable error, fallback inappropriate

---

## 3. Code Implementation Pattern

### 3.1 Required Imports

```java
import com.barclaycard.digital.core.exception.Resilience4jIgnoreExceptionMarker;
import io.github.resilience4j.bulkhead.annotation.Bulkhead;
import io.github.resilience4j.circuitbreaker.annotation.CircuitBreaker;
import io.github.resilience4j.timelimiter.annotation.TimeLimiter;
import java.util.concurrent.CompletableFuture;
```

### 3.2 Complete Proxy Service Pattern

```java
public class AccountQueryProxyService implements AccountQueryService {
  private static final Logger LOGGER = LoggerFactory.getLogger(AccountQueryProxyService.class);
  private final AccountServiceDecorator primaryService;
  private final QueryService<AccountDataDetailResponseWrapper> fallbackService;

  public AccountQueryProxyService(
      AccountServiceDecorator primaryService,
      @Qualifier("accountFallback") QueryService<AccountDataDetailResponseWrapper> fallbackService) {
    this.primaryService = primaryService;
    this.fallbackService = fallbackService;
  }

  // Primary method with all three annotations - ORDER MATTERS!
  @TimeLimiter(name = "primary-service")
  @Bulkhead(name = "primary-service", type = Bulkhead.Type.THREADPOOL)
  @CircuitBreaker(name = "primary-service", fallbackMethod = "fallback")
  public CompletableFuture<AccountDataDetailResponseWrapper> getAccountQueryServiceResponse(
      QueryServiceRequest request) {
    LOGGER.info("Calling the getData query operation.");
    AccountDataDetailResponseWrapper response =
        primaryService.getDecoratedAccountDataDetailResponseWrapper(request);
    LOGGER.info("Account domain data obtained from primary service");
    return CompletableFuture.completedFuture(response);
  }

  // Fallback method for recoverable errors - calls fallback service
  @Bulkhead(name = "fallback-service", type = Bulkhead.Type.THREADPOOL)
  @TimeLimiter(name = "fallback-service")
  public CompletableFuture<AccountDataDetailResponseWrapper> fallback(
      QueryServiceRequest request, Throwable throwable) {
    LOGGER.warn("Calling the fallback query operation. Cause: {}", throwable.getMessage());
    AccountDataDetailResponseWrapper response = fallbackService.getData(request);
    LOGGER.info("Account domain data obtained from fallback service");
    return CompletableFuture.completedFuture(response);
  }

  // Fallback for ignored exceptions - re-throws original cause (NO fallback service call)
  public CompletableFuture<AccountDataDetailResponseWrapper> fallback(
      QueryServiceRequest request, Resilience4jIgnoreExceptionMarker ex) throws Throwable {
    LOGGER.error("Error encountered while getting data from primary/fallback Service");
    throw ex.getCause();
  }
}
```

### 3.3 Annotation Order and Purpose

```java
@TimeLimiter(name = "primary-service")                              // 1. Timeout control
@Bulkhead(name = "primary-service", type = Bulkhead.Type.THREADPOOL) // 2. Thread isolation
@CircuitBreaker(name = "primary-service", fallbackMethod = "fallback") // 3. Circuit breaker
```

**Execution Flow:**
1. **TimeLimiter** - Wraps execution with timeout, cancels if exceeds duration
2. **Bulkhead** - Limits concurrent executions via thread pool, prevents resource exhaustion
3. **CircuitBreaker** - Tracks success/failure, opens circuit when threshold reached, triggers fallback

---

## 4. Critical Rules

### Rule 1: CompletableFuture Return Type is MANDATORY

Methods with `@Bulkhead(type = THREADPOOL)` MUST return `CompletableFuture<T>`:

```java
// ✅ CORRECT
@Bulkhead(name = "primary-service", type = Bulkhead.Type.THREADPOOL)
public CompletableFuture<ResponseWrapper> getData(Request request) {
    ResponseWrapper result = service.call(request);
    return CompletableFuture.completedFuture(result);
}

// ❌ WRONG - will fail at runtime with BulkheadFullException
@Bulkhead(name = "primary-service", type = Bulkhead.Type.THREADPOOL)
public ResponseWrapper getData(Request request) {
    return service.call(request);
}
```

### Rule 2: Fallback Method Signature Must Match

Fallback must match primary signature PLUS `Throwable` parameter as last argument:

```java
// Primary method signature
public CompletableFuture<T> primaryMethod(QueryServiceRequest request)

// Fallback method signature - adds Throwable as LAST parameter
public CompletableFuture<T> fallback(QueryServiceRequest request, Throwable throwable)
```

### Rule 3: Multiple Fallbacks for Different Exception Types

Create multiple fallback methods to handle different exception types differently:

```java
// Fallback for general exceptions - triggers fallback service
public CompletableFuture<T> fallback(QueryServiceRequest request, Throwable throwable) {
    LOGGER.warn("Primary failed, calling fallback service");
    return CompletableFuture.completedFuture(fallbackService.getData(request));
}

// Fallback for ignored exceptions - re-throw original (NO fallback service)
public CompletableFuture<T> fallback(
    QueryServiceRequest request, Resilience4jIgnoreExceptionMarker ex) throws Throwable {
    LOGGER.error("Ignored exception, re-throwing original cause");
    throw ex.getCause();
}

// Fallback for specific business exceptions - re-throw directly
public CompletableFuture<T> fallback(QueryServiceRequest request, NotFoundException ex) {
    LOGGER.error("Not found exception, re-throwing");
    throw ex;
}
```

### Rule 4: Instance Names Must Match

Annotation name must exactly match properties file instance name:

```java
@TimeLimiter(name = "primary-service")  // Must match properties
```

```properties
resilience4j.timelimiter.instances.primary-service.baseConfig=primary  # Must match annotation
```

---

## 5. Integration Test Configuration

For integration tests, use relaxed thresholds to prevent circuit opening:

`src/integrationTest/resources/resilience4j-config.properties`:
```properties
#Test config - higher thresholds to avoid circuit opening
resilience4j.circuitbreaker.configs.default.slidingWindowSize=100
resilience4j.circuitbreaker.configs.default.failureRateThreshold=100
```

---

## 6. Common Pitfalls

### Pitfall 1: Context Not Propagating to Async Threads

**Symptom:** Request context (correlation ID, auth headers) missing in async threads.

**Fix:** Add `CustomContextPropagator` to BOTH bulkhead AND scheduled executor configs.

### Pitfall 2: Circuit Breaker Opens During Startup

**Symptom:** Circuit opens immediately after deployment due to initial failures.

**Fix:** Set `minimumNumberOfCalls` to ensure enough samples before calculating failure rate:
```properties
resilience4j.circuitbreaker.configs.default.minimumNumberOfCalls=10
```

### Pitfall 3: Fallback Also Fails

**Symptom:** Both primary and fallback fail, causing complete outage.

**Fix:** Ensure fallback service has its own bulkhead and timelimiter with appropriate timeouts.

---

## 7. Quick Reference

### Required Files

| File | Purpose |
|------|---------|
| `build.gradle` | Add `system-core-resilience4j:1.0.5` dependency |
| `resilience4j-config.properties` | Circuit breaker, bulkhead, timelimiter configs |

### Annotation Cheat Sheet

| Annotation | Purpose | Key Config |
|------------|---------|------------|
| `@CircuitBreaker` | Fail fast when service is down | `failureRateThreshold`, `slidingWindowSize`, `waitDurationInOpenState` |
| `@Bulkhead` | Limit concurrent requests | `maxThreadPoolSize`, `queueCapacity`, `coreThreadPoolSize` |
| `@TimeLimiter` | Timeout control | `timeoutDuration`, `cancelRunningFuture` |

### Property Prefixes

| Prefix | Purpose |
|--------|---------|
| `resilience4j.circuitbreaker.configs.*` | Circuit breaker configuration |
| `resilience4j.circuitbreaker.instances.*` | Named circuit breaker instances |
| `resilience4j.thread-pool-bulkhead.configs.*` | Bulkhead configuration |
| `resilience4j.timelimiter.configs.*` | Time limiter configuration |
| `resilience4j.timelimiter.instances.*` | Named time limiter instances |
| `resilience4j.scheduled.executor.*` | Scheduled executor for TimeLimiter |
| `resilience4j.ignore.*` | Exception ignore rules |

---

## 8. Summary

To implement Resilience4j in a Barclays iAPI project:

1. **Add dependency:** `system-core-resilience4j:1.0.5` to build.gradle
2. **Create config:** `resilience4j-config.properties` with circuit breaker, bulkhead, and timelimiter settings
3. **Configure circuit breaker:** Set appropriate `failureRateThreshold`, `slidingWindowSize`, `waitDurationInOpenState`
4. **Annotate methods:** Use `@TimeLimiter`, `@Bulkhead`, `@CircuitBreaker` in correct order
5. **Return CompletableFuture:** All decorated methods MUST return `CompletableFuture<T>`
6. **Implement fallbacks:** Create fallback methods matching primary signature + Throwable
7. **Handle ignored exceptions:** Use `Resilience4jIgnoreExceptionMarker` for exceptions that should propagate
8. **Configure context propagation:** Add `CustomContextPropagator` to preserve request context

---

**Document Version:** 1.0
**Date:** 2025-12-31
**Reference Project:** cc-domain-qry-account
