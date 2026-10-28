# Performance Considerations: Optimization Guide

## Executive Summary

Performance tuning guidelines for MCA2 EPS applications. Covers caching strategies, filter chain optimization, context storage performance, connection pooling, and monitoring for production deployments.

---

## Performance Baseline

### Expected Metrics (Per Request)

| Metric | Baseline | Target | Notes |
|--------|----------|--------|-------|
| Request latency (no DB) | 10-20ms | <50ms | In-memory operations |
| Request latency (with DB) | 50-150ms | <200ms | Including context lookup |
| Filter overhead | 2-5ms | <3ms | Per filter execution |
| Context propagation | 1-2ms | <2ms | Header serialization |
| Startup time (cold) | 5-10s | <15s | Include DB connection pool warm-up |
| Memory usage | 200-400MB | <500MB | Per JVM instance |
| Thread pool utilization | 50-70% | <80% | Tomcat thread pool |

---

## Performance Optimization Areas

### 1. Connection Pooling

#### Database Connection Tuning

```properties
# application-prod.properties
spring.datasource.hikari.maximum-pool-size=25
spring.datasource.hikari.minimum-idle=5
spring.datasource.hikari.connection-timeout=30000
spring.datasource.hikari.idle-timeout=600000
spring.datasource.hikari.max-lifetime=1800000
spring.datasource.hikari.auto-commit=true

# Connection validation
spring.datasource.hikari.connection-test-query=SELECT 1
spring.datasource.hikari.leak-detection-threshold=60000
```

**Tuning Strategy:**
```
Formula: maximum-pool-size = (core_cpu_count × 2) + effective_spindle_count
Example: 4-core CPU → (4 × 2) + 1 = 9, round to 10-15
```

### 2. Caching Strategy

#### Enable Caching for Context

```java
@Configuration
@EnableCaching
public class CacheConfiguration {

  @Bean
  public CacheManager cacheManager() {
    return new ConcurrentMapCacheManager(
      "contexts",
      "sessions",
      "customers",
      "users"
    );
  }
}
```

#### Cache Frequently Accessed Data

```java
@Service
public class CustomerService {

  private final CustomerRepository customerRepository;

  @Cacheable(value = "customers", key = "#customerId")
  public Customer getCustomer(String customerId) {
    return customerRepository.findById(customerId).orElse(null);
  }

  @CacheEvict(value = "customers", key = "#customerId")
  public void invalidateCustomer(String customerId) {
    // Manually invalidate on updates
  }
}
```

### 3. Filter Chain Optimization

#### Conditional Filter Execution

```java
@Component
public class ConditionalOAuthFilter extends OncePerRequestFilter {

  @Override
  protected boolean shouldNotFilter(HttpServletRequest request) {
    // Skip filter for non-OAuth protected endpoints
    String path = request.getRequestURI();
    return path.startsWith("/public") ||
           path.startsWith("/health") ||
           path.startsWith("/metrics");
  }

  @Override
  protected void doFilterInternal(
    HttpServletRequest request,
    HttpServletResponse response,
    FilterChain chain
  ) throws ServletException, IOException {
    // OAuth validation only for protected endpoints
    validateOAuthToken(request);
    chain.doFilter(request, response);
  }
}
```

#### Async Logging for Performance

```properties
# application-prod.properties
logging.async.queue-size=512
logging.async.shutdown-wait-time=10000
logging.level.com.barclays.global.mca=INFO
```

**Impact:**
- ✅ Reduce logging latency by 5-10ms per request
- ✅ Better throughput under high load
- ✅ Prevents logging from blocking business logic

### 4. Database Query Optimization

#### Query Optimization

```java
// Before (N+1 queries)
@Service
public class AccountService {
  public List<Account> getAccountsWithTransactions(String customerId) {
    List<Account> accounts = repository.findByCustomerId(customerId);
    for (Account account : accounts) {
      account.setTransactions(transactionRepository.findByAccountId(account.getId()));
      // N+1 database calls!
    }
    return accounts;
  }
}

// After (Single query with join)
@Service
public class AccountService {
  public List<Account> getAccountsWithTransactions(String customerId) {
    return repository.findAccountsWithTransactionsByCustomerId(customerId);
    // Single query with JOIN
  }
}

@Repository
public interface AccountRepository extends JpaRepository<Account, String> {
  @Query("SELECT DISTINCT a FROM Account a LEFT JOIN FETCH a.transactions WHERE a.customerId = :customerId")
  List<Account> findAccountsWithTransactionsByCustomerId(@Param("customerId") String customerId);
}
```

---

## Monitoring & Profiling

### JVM Tuning

```bash
#!/bin/bash
# Start with optimized JVM settings for production

java -server \
  -Xms2048m \
  -Xmx2048m \
  -XX:+UseG1GC \
  -XX:MaxGCPauseMillis=200 \
  -XX:+ParallelRefProcEnabled \
  -XX:+AlwaysPreTouch \
  -XX:+UnlockDiagnosticVMOptions \
  -XX:G1SummarizeRSetStatsPeriod=1 \
  -Dspring.profiles.active=prod \
  -jar order-service.jar
```

**Key Settings:**
- `-Xms` = `-Xmx` (avoid pause for heap growth)
- `UseG1GC` (low latency garbage collection)
- `MaxGCPauseMillis=200` (keep GC pauses under 200ms)

### Metrics Collection

```properties
# application-prod.properties
management.endpoints.web.exposure.include=metrics,prometheus
management.metrics.export.prometheus.enabled=true

# Custom metrics
management.metrics.tags.application=${spring.application.name}
management.metrics.tags.environment=${spring.profiles.active}
```

### Performance Dashboard Queries (Prometheus)

```promql
# Request latency (95th percentile)
histogram_quantile(0.95, http_request_duration_seconds_bucket)

# Database connection pool usage
hikaricp_connections_active / hikaricp_connections_max

# Context cache hit rate
cache_gets_hit / (cache_gets_hit + cache_gets_miss)

# Filter execution time
filter_execution_time_seconds

# Memory pressure
jvm_memory_used_bytes / jvm_memory_max_bytes
```

---

## Load Testing & Capacity Planning

### Load Test Script (Apache JMeter)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmeterTestPlan version="1.2">
  <TestPlan guiclass="TestPlanGui" testclass="TestPlan">
    <!-- 1000 concurrent users, 5 minute ramp-up -->
    <elementProp name="TestPlan.user_defined_variables" elementType="Arguments"/>

    <ThreadGroup guiclass="ThreadGroupGui" testclass="ThreadGroup">
      <elementProp name="ThreadGroup.main_controller"/>
      <stringProp name="ThreadGroup.num_threads">1000</stringProp>
      <stringProp name="ThreadGroup.ramp_time">300</stringProp>
      <stringProp name="ThreadGroup.duration">600</stringProp>
    </ThreadGroup>

    <!-- HTTP Sampler -->
    <HTTPSampler guiclass="HttpTestSampleGui" testclass="HTTPSampler">
      <elementProp name="HTTPsampler.Arguments" elementType="Arguments"/>
      <stringProp name="HTTPSampler.domain">localhost</stringProp>
      <stringProp name="HTTPSampler.port">8080</stringProp>
      <stringProp name="HTTPSampler.path">/api/orders</stringProp>
      <stringProp name="HTTPSampler.method">POST</stringProp>
      <stringProp name="HTTPSampler.contentEncoding">utf-8</stringProp>
    </HTTPSampler>
  </TestPlan>
</jmeterTestPlan>
```

### Expected Performance Under Load

```
Scenario: 1000 concurrent users, standard REST API

Metrics:
├─ Throughput: 5,000-8,000 requests/second
├─ Avg latency: 100-150ms
├─ 95th percentile: 200-300ms
├─ 99th percentile: 400-600ms
├─ Errors: <1%
└─ CPU usage: 70-80%

Result: ✅ PASS if all metrics within bounds
```

---

## Caching Best Practices

### Strategic Caching Points

```java
// 1. Customer/User caching
@Cacheable(value = "customers", key = "#customerId", ttl = 3600)
public Customer getCustomer(String customerId) { }

// 2. Reference data caching (long TTL)
@Cacheable(value = "reference_data", key = "#country", ttl = 86400)
public List<City> getCitiesByCountry(String country) { }

// Cache invalidation on updates
@CacheEvict(value = "customers", key = "#customer.id")
public void updateCustomer(Customer customer) { }
```

### Cache Eviction Strategies

```properties
# application-prod.properties

# Context cache - aggressive eviction
spring.cache.cache-names=contexts,customers,referencedata
spring.cache.caffeine.spec=expireAfterWrite=30m,maximumSize=10000

# Or use time-based eviction
spring.cache.redis.time-to-live=1800000
```

---

## Scaling Considerations

### Horizontal Scaling (Multiple Instances)

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 3  # Scale to 3 instances
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  selector:
    matchLabels:
      app: order-service
  template:
    spec:
      containers:
      - name: order-service
        image: order-service:v1.0
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /actuator/health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
```

### Database Connection Pool Sizing (Scaled)

```
3 instances × 25 connections = 75 total connections
Database should support: ≥100 connections (overhead margin)

Formula: (number_of_instances × max_pool_size) × 1.25 safety_factor
```

---

## Memory Profiling

### Identify Memory Leaks

```bash
# Generate heap dump on OutOfMemoryError
java -XX:+HeapDumpOnOutOfMemoryError \
  -XX:HeapDumpPath=/var/dumps/ \
  -jar order-service.jar
```

### Analyze with JProfiler

```bash
# After heap dump generated
jprofiIer --open heap_dump.hprof
```

---

> **Note:** Context storage backend selection (EHCache, RDB, MongoDB) and its performance characteristics are part of the **Secure Proxy** module. Refer to the Secure Proxy documentation for context store performance tuning guidance.

---

## Performance Optimization Checklist

### Before Production Deployment

```
✓ Connection pool tuned for expected load
✓ Caching enabled for context/customers
✓ Database indexes created and analyzed
✓ Async logging enabled
✓ JVM tuned for production workload
✓ Filter chains use shouldNotFilter() for exclusions
✓ N+1 queries eliminated
✓ Load testing passed (expected traffic × 2)
✓ 95th percentile latency <300ms
✓ Error rate <1%
✓ Memory usage stable over time
✓ GC pauses <500ms
✓ CPU utilization <80% at peak
```

### Performance Monitoring Checklist

```
Daily:
✓ Average response time
✓ Error rate
✓ Database connection pool utilization
✓ GC pause duration

Weekly:
✓ Cache hit rates
✓ Slowest queries
✓ Memory trend
✓ Peak vs average load

Monthly:
✓ Capacity utilization
✓ Scaling decisions needed
✓ Cache effectiveness review
✓ Performance trend analysis
```

---

## Next Steps

1. **Profile Baseline** — Establish current performance metrics
2. **Identify Bottlenecks** — Use profiler to find slow points
3. **Optimize Connection Pool** — Tune for expected load
4. **Implement Caching** — Cache frequently accessed data
5. **Monitor Production** — Track metrics continuously

**Performance Considerations enable scalable, responsive applications.**

