# Grep Patterns: MCA2 EPS Detection Library

## Executive Summary

38 searchable regex patterns (grep/ripgrep) for detecting MCA2 EPS framework usage in consuming applications. All patterns are ready-to-copy CLI commands organized by EPS framework component.

---

## QUICK START

### Usage

```bash
# Basic pattern usage (grep)
grep -r "PATTERN" /path/to/app/src --include="*.java"

# Using ripgrep (faster, recommended)
rg "PATTERN" /path/to/app/src --type java

# Show line numbers
grep -rn "PATTERN" /path/to/app/src --include="*.java"

# Show context (3 lines before/after)
grep -rn -C 3 "PATTERN" /path/to/app/src --include="*.java"

# Output to file
grep -rn "PATTERN" /path/to/app/src --include="*.java" > results.txt

# Count matches
grep -rc "PATTERN" /path/to/app/src --include="*.java" | sort -t: -k2 -rn
```

---

## FILTER CHAIN DETECTION (8 Patterns)

Detect MCA2 filter chain usage and configuration.

### Pattern 1: OncePerRequestFilter Extension

**Purpose:** Find all custom filters extending the core MCA2 filter base class

```bash
grep -rn "extends OncePerRequestFilter" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/filters/CustomAuthFilter.java:12:public class CustomAuthFilter extends OncePerRequestFilter {
src/main/java/com/example/filters/RequestLoggingFilter.java:15:public class RequestLoggingFilter extends OncePerRequestFilter {
```

**Indicates:** Custom filter implementations; core framework integration

---

### Pattern 2: Filter Chain Configuration

**Purpose:** Find FilterRegistrationBean declarations and filter ordering

```bash
grep -rn "FilterRegistrationBean\|addFilter\|addFilterBefore\|addFilterAfter" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/FilterConfig.java:18:FilterRegistrationBean<MyFilter> bean = new FilterRegistrationBean<>(new MyFilter());
src/main/java/com/example/config/SecurityConfig.java:35:http.addFilterBefore(customFilter, UsernamePasswordAuthenticationFilter.class);
```

**Indicates:** Manual filter registration; non-standard filter ordering

---

### Pattern 3: Core MCA2 Filter Usage

**Purpose:** Find usage of specific MCA2 filters (ContextFilter, CorrelationIdFilter, ExceptionFilter, DdosPreventionFilter)

```bash
grep -rn "ContextFilter\|CorrelationIdFilter\|ExceptionFilter\|DdosPreventionFilter" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/EpsConfig.java:22:@Bean
src/main/java/com/example/config/EpsConfig.java:23:public ContextFilter contextFilter() {
src/main/java/com/example/Application.java:8:@EnableExperienceAPI  // Enables all core filters
```

**Indicates:** Core MCA2 filter chain activation; framework integration

---

### Pattern 4: Filter Lifecycle Methods

**Purpose:** Detect filter implementation methods (doFilterInternal, shouldNotFilter, init, destroy)

```bash
grep -rn "doFilterInternal\|shouldNotFilter\|void init\|void destroy" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/filters/CustomFilter.java:42:protected void doFilterInternal(
src/main/java/com/example/filters/CustomFilter.java:52:protected boolean shouldNotFilter(HttpServletRequest request) {
```

**Indicates:** Custom filter implementations; extension points in use

---

### Pattern 5: Filter Conditional Configuration

**Purpose:** Find @ConditionalOnProperty usage for filter toggling

```bash
grep -rn "@ConditionalOnProperty.*filter" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/FilterAutoConfig.java:18:@ConditionalOnProperty(name = "mca.filter.oauth-validator.enabled", havingValue = "true")
src/main/java/com/example/config/FilterAutoConfig.java:19:public OAuthValidatorFilter oauthValidatorFilter() {
```

**Indicates:** Feature toggle usage; conditional filter activation

---

### Pattern 6: Filter Chain Order Specification

**Purpose:** Find filter order/priority configuration

```bash
grep -rn "\.setOrder\|filter.*order\|FilterChain.*order" src/ --include="*.java" -i
```

**Expected Output:**
```
src/main/java/com/example/config/FilterConfig.java:28:bean.setOrder(10);
src/main/java/com/example/config/FilterConfig.java:35:bean.setOrder(FilterConfig.CUSTOM_FILTER_ORDER);
```

**Indicates:** Non-standard filter ordering; potential ordering conflicts

---

### Pattern 7: Filter URL Pattern Mapping

**Purpose:** Find URL patterns where filters are applied/excluded

```bash
grep -rn "addUrlPatterns\|setUrlPatterns\|shouldNotFilter" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/FilterConfig.java:30:bean.addUrlPatterns("/api/*", "/orders/*");
src/main/java/com/example/filters/ContextFilter.java:48:String path = request.getRequestURI();
```

**Indicates:** Filter scope definition; potential coverage gaps

---

### Pattern 8: Filter Error Handling

**Purpose:** Detect filter exception handling and error flow

```bash
grep -rn "try.*catch\|throws.*Exception" src/ --include="*.java" | grep -i filter
```

**Expected Output:**
```
src/main/java/com/example/filters/CustomFilter.java:45:try {
src/main/java/com/example/filters/CustomFilter.java:50:} catch (Exception e) {
src/main/java/com/example/filters/CustomFilter.java:55:throws ServletException, IOException
```

**Indicates:** Error handling patterns; exception propagation

---

## CONTEXT SYSTEM DETECTION (5 Patterns)

Detect IOL context system usage and propagation. Note: Context storage (ContextStore, context-store-*) is part of the Secure Proxy module. Pattern 13 is listed here for convenience but detects Secure Proxy usage, not EPS core.

### Pattern 9: IOLSchema and Context Container

**Purpose:** Find IOLSchema instantiation and context management

```bash
grep -rn "IOLSchema\|new IOLSchema\|getIOLSchema" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/service/OrderService.java:12:private IOLSchema schema;
src/main/java/com/example/controller/OrderController.java:28:IOLSchema schema = WebUtils.getIOLSchemaFromScope();
src/main/java/com/example/config/ContextConfig.java:35:new IOLSchema()
```

**Indicates:** Context system in use; context propagation at service/controller level

---

### Pattern 10: IOLContext Annotation Usage

**Purpose:** Find @IOLContext parameter injection in controllers/services

```bash
grep -rn "@IOLContext" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/controller/OrderController.java:18:public ResponseEntity<?> getOrders(
src/main/java/com/example/controller/OrderController.java:19:  @IOLContext CustomerContext customer,
src/main/java/com/example/controller/OrderController.java:20:  @IOLContext UserContext user
src/main/java/com/example/controller/OrderController.java:21:) {
```

**Indicates:** Framework-enabled context injection; proper framework integration

---

### Pattern 11: WebUtils Context Access

**Purpose:** Find direct context access via WebUtils (alternative to @IOLContext)

```bash
grep -rn "WebUtils\.setIOLSchemaInScope\|WebUtils\.getIOLSchemaFromScope\|WebUtils\.removeIOLSchemaFromScope" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/batch/BatchProcessor.java:42:WebUtils.setIOLSchemaInScope(schema);
src/main/java/com/example/service/DataService.java:55:IOLSchema schema = WebUtils.getIOLSchemaFromScope();
src/main/java/com/example/batch/BatchProcessor.java:48:WebUtils.removeIOLSchemaFromScope();
```

**Indicates:** Batch/non-web context propagation; ThreadLocal context management

---

### Pattern 12: Context Classes - Customer/Account/User

**Purpose:** Find specific context class instantiation and usage

```bash
grep -rn "new CustomerContext\|new AccountContext\|new UserContext\|new ProcessContext" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/ContextFactory.java:18:CustomerContext customer = new CustomerContext();
src/main/java/com/example/config/ContextFactory.java:19:customer.setCustomerId(customerId);
src/main/java/com/example/filter/ContextExtractorFilter.java:35:UserContext user = new UserContext();
```

**Indicates:** Context creation in progress; context population

---

### Pattern 13: Secure Proxy Context Store Backend

**Purpose:** Find Secure Proxy context store configuration (RDB, MongoDB, EHCache). Note: Context storage is part of the Secure Proxy module, not EPS core.

```bash
grep -rn "ContextStore\|@EnableRDBContextStore\|@EnableMongoContextStore\|@EnableEhCacheContextStore\|context\.store\.type" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/Application.java:8:@EnableRDBContextStore
src/main/java/com/example/config/ContextStoreConfig.java:15:ContextStore contextStore;
src/main/resources/application.properties:12:context.store.type=rdb
```

**Indicates:** Secure Proxy session storage backend selection; not EPS core

---

### Pattern 14: Context Header Propagation

**Purpose:** Find context serialization and header manipulation for service-to-service calls

```bash
grep -rn "X-.*Context\|X-CustomerContext\|X-UserContext\|X-AccountContext" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/client/RestClientUtil.java:28:headers.put("X-CustomerContext", customerJson);
src/main/java/com/example/client/ServiceCallInterceptor.java:45:String contextHeader = ContextMapper.toJson(schema);
src/main/java/com/example/config/RestTemplateConfig.java:52:request.getHeaders().set("X-UserContext", userJson);
```

**Indicates:** Context propagation to downstream services; distributed context flow

---

## EPS CORE DETECTION (4 Patterns)

Detect MCA2 EPS framework core components.

### Pattern 15: @EnableExperienceAPI Annotation

**Purpose:** Find Experience API framework enablement

```bash
grep -rn "@EnableExperienceAPI\|@EnableEPS\|@Enable.*Experience" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/Application.java:7:@EnableExperienceAPI
src/main/java/com/example/Application.java:8:@SpringBootApplication
src/main/java/com/example/Application.java:9:public class Application {
```

**Indicates:** Core MCA2 EPS framework activation; framework initialization

---

### Pattern 16: EPSConfiguration or Framework Config

**Purpose:** Find EPS-specific configuration classes and beans

```bash
grep -rn "ExperienceAPIConfig\|EPSConfiguration\|EpsConfig\|ExperienceAPIAutoConfiguration" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/EpsConfig.java:8:@Configuration
src/main/java/com/example/config/EpsConfig.java:9:public class EpsConfig {
src/main/java/com/example/Application.java:15:// Auto-configured via ExperienceAPIAutoConfiguration
```

**Indicates:** Custom EPS configuration; framework beans in use

---

### Pattern 17: MCA Module Dependencies in Gradle/Maven

**Purpose:** Find mca-* library dependencies in build files

```bash
grep -rn "mca-context\|mca-filter-core\|mca-eps-core\|mca-response-handling\|mca-exception-handling" build.gradle src/ --include="*.gradle"
```

**Expected Output:**
```
build.gradle:18:implementation 'com.barclays.global.mca:mca-context:2.3.0'
build.gradle:19:implementation 'com.barclays.global.mca:mca-filter-core:2.3.0'
build.gradle:20:implementation 'com.barclays.global.mca:mca-eps-core:2.3.0'
```

**Indicates:** Direct MCA2 framework dependency; framework version used

---

### Pattern 18: Spring Boot Auto-Configuration Discovery

**Purpose:** Find Spring Boot 3 auto-configuration imports (META-INF/spring/*)

```bash
find src/main/resources/META-INF/spring -name "*AutoConfiguration.imports" -exec cat {} \;
```

**Alternative (grep search):**
```bash
grep -rn "org.springframework.boot.autoconfigure\|com.barclays.global.mca" src/main/resources/META-INF/spring/
```

**Expected Output:**
```
src/main/resources/META-INF/spring/org.springframework.boot.AutoConfiguration.imports:
com.barclays.global.mca.libs.eps.ExperienceAPIAutoConfiguration
com.barclays.global.mca.libs.filter.FilterAutoConfiguration
```

**Indicates:** Auto-configuration registered; Spring Boot integration

---

## EXCEPTION & RESPONSE DETECTION (2 Patterns)

Detect exception handling and response envelope usage.

### Pattern 19: Exception Hierarchy Usage

**Purpose:** Find GenericException and concrete exception types

```bash
grep -rn "GenericException\|ApplicationException\|ServerException\|RequestException\|NotFoundException\|AuthorizationException" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/service/OrderService.java:45:throw new RequestException("Invalid order", ErrorCode.VALIDATION_ERROR);
src/main/java/com/example/service/OrderService.java:52:throw new ApplicationException("Insufficient balance", ErrorCode.INSUFFICIENT_BALANCE);
src/main/java/com/example/repository/OrderRepository.java:28:throw new NotFoundException("Order not found");
src/main/java/com/example/controller/OrderController.java:18:} catch (ServerException e) {
```

**Indicates:** MCA2 exception handling in use; error processing

---

### Pattern 20: Response Envelope and ResponseAssembler

**Purpose:** Find Response<T> envelope and builder pattern usage

```bash
grep -rn "Response<\|ResponseAssembler\|Response\.assemble\|response\.build" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/controller/OrderController.java:35:return Response.assemble()
src/main/java/com/example/controller/OrderController.java:36:  .status("SUCCESS")
src/main/java/com/example/controller/OrderController.java:37:  .data(order)
src/main/java/com/example/controller/OrderController.java:38:  .build();
src/main/java/com/example/dto/ApiResponse.java:8:public class ApiResponse extends Response<Order> {
```

**Indicates:** Standardized response envelope in use; fluent API pattern

---

## LOGGING & MASKING DETECTION (3 Patterns)

Detect AspectJ logging and data masking.

### Pattern 21: AspectJ Masking Annotations

**Purpose:** Find @Masked annotation usage for field-level masking

```bash
grep -rn "@Masked\|@MaskingPattern" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/domain/User.java:12:@Masked(pattern = MaskingPattern.EMAIL)
src/main/java/com/example/domain/User.java:13:private String email;
src/main/java/com/example/domain/Payment.java:18:@Masked(pattern = MaskingPattern.CREDIT_CARD)
src/main/java/com/example/domain/Payment.java:19:private String cardNumber;
```

**Indicates:** Data masking configuration; PII protection

---

### Pattern 22: Performance Logging Annotations

**Purpose:** Find @PerfLogParam and @PerfLogRecordedOperation for performance tracking

```bash
grep -rn "@PerfLogParam\|@PerfLogRecordedOperation\|@RecordedOperation" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/service/OrderService.java:28:@PerfLogRecordedOperation(name = "processOrder")
src/main/java/com/example/service/OrderService.java:29:public Order processOrder(Order order) {
src/main/java/com/example/service/ReportService.java:42:@PerfLogParam(value = "generateReport", threshold = 5000)
```

**Indicates:** Performance monitoring in use; trace tracking enabled

---

### Pattern 23: MDC Correlation ID Usage

**Purpose:** Find correlation ID usage via MDC (Mapped Diagnostic Context)

```bash
grep -rn "MDC\.put\|MDC\.get\|Correlation-ID\|correlationId" src/ --include="*.java" | head -20
```

**Expected Output:**
```
src/main/java/com/example/filter/CorrelationIdFilter.java:35:String correlationId = MDC.get("correlationId");
src/main/java/com/example/service/AuditService.java:42:logger.info("Order processed {}", MDC.get("correlationId"));
src/main/java/com/example/config/LoggingConfig.java:15:logging.pattern.console=%d{ISO8601} [%X{correlationId}] %5p %msg%n
```

**Indicates:** Distributed tracing in use; correlation ID propagation

---

## SPRING BOOT AUTO-CONFIG DETECTION (2 Patterns)

Detect Spring Boot 3 configuration patterns specific to MCA2.

### Pattern 24: Conditional Bean Registration

**Purpose:** Find @ConditionalOnProperty, @ConditionalOnMissingBean, @ConditionalOnClass

```bash
grep -rn "@ConditionalOnProperty\|@ConditionalOnMissingBean\|@ConditionalOnClass" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/OAuthConfig.java:8:@ConditionalOnProperty(name = "mca.security.oauth.enabled", havingValue = "true")
src/main/java/com/example/config/CacheConfig.java:12:@ConditionalOnMissingBean(CacheManager.class)
src/main/java/com/example/config/MaskingConfig.java:15:@ConditionalOnClass(name = "com.barclays.global.mca.libs.masking.Mask")
```

**Indicates:** Feature toggles in use; proper Spring Boot 3 patterns

---

### Pattern 25: PropertySource Configuration

**Purpose:** Find @PropertySource or application.properties/yml references to mca.* properties

```bash
grep -rn "mca\\.eps\|mca\\.filter\|mca\\.context\|mca\\.service\|mca\\.proxy" src/main/resources/ --include="*.properties" --include="*.yml"
```

**Expected Output:**
```
src/main/resources/application.properties:8:mca.eps.enabled=true
src/main/resources/application.properties:9:mca.filter.context.enabled=true
src/main/resources/application-prod.properties:6:mca.filter.ddos-prevention.enabled=true
```

**Indicates:** Framework configuration in place; environment-specific setup

---

## OAS VALIDATION DETECTION (3 Patterns)

Detect OpenAPI Specification (OAS) validation usage and configuration.

### Pattern 33: OAS Validation Classes

**Purpose:** Find usage of OAS validation core classes (OASRequestValidation, OasProvider, OasValidationResult, SimpleOasProvider, EmptyOasProvider)

```bash
grep -rn "OASRequestValidation\|OasProvider\|OasValidationResult\|SimpleOasProvider\|EmptyOasProvider" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/OasConfig.java:12:@Bean
src/main/java/com/example/config/OasConfig.java:13:public OasProvider oasProvider() {
src/main/java/com/example/validation/RequestValidator.java:22:OasValidationResult result = oasRequestValidation.validate(request);
src/main/java/com/example/config/OasConfig.java:18:return new SimpleOasProvider(resource);
```

**Indicates:** OAS request validation in use; API contract enforcement active

---

### Pattern 34: OAS Configuration Properties

**Purpose:** Find `core.default.oas.*` configuration in properties and YAML files

```bash
grep -rn "core\.default\.oas\.\|core\.default\.validation-filter" src/main/resources/ --include="*.properties" --include="*.yml" --include="*.yaml"
```

**Expected Output:**
```
src/main/resources/application.properties:15:core.default.oas.enabled=true
src/main/resources/application.properties:16:core.default.oas.blockingMode=true
src/main/resources/application.properties:17:core.default.oas.path=classpath:oas/openapi.yaml
src/main/resources/application-dev.properties:8:core.default.oas.blockingMode=false
src/main/resources/application.yml:22:  default.validation-filter.exclude.paths: /actuator/**,/process/**
```

**Indicates:** OAS validation configured; environment-specific blocking mode settings

---

### Pattern 35: OpenAPI Specification Files

**Purpose:** Find OpenAPI specification files (YAML and JSON) in the project

```bash
find src/main/resources -name "openapi.yaml" -o -name "openapi.yml" -o -name "openapi.json" -o -name "*.oas.yaml" -o -name "*.oas.json"
```

**Alternative (grep for OAS content markers inside YAML/JSON files):**
```bash
grep -rn "openapi:\|\"openapi\":" src/main/resources/ --include="*.yaml" --include="*.yml" --include="*.json"
```

**Expected Output:**
```
src/main/resources/oas/openapi.yaml:1:openapi: 3.0.3
src/main/resources/oas/openapi.yaml:2:info:
```

**Indicates:** OpenAPI spec file present; used as the contract for OAS validation

---

## PROCESS SYSTEM DETECTION (3 Patterns)

Detect process.json journey definitions and process-lib module usage.

### Pattern 36: ProcessService / ProcessController / ProcessDiscovery Classes

**Purpose:** Find usage of process-lib core classes and secure-proxy-api process interfaces

```bash
grep -rn "ProcessService\|ProcessController\|ProcessDiscovery\|ProcessDefinition\|ClasspathResourceProcessService" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/config/ProcessConfig.java:12:@Autowired
src/main/java/com/example/config/ProcessConfig.java:13:private ProcessService processService;
src/main/java/com/example/discovery/MyProcessDiscovery.java:8:public class MyProcessDiscovery implements ProcessDiscovery {
src/main/java/com/example/config/ProcessConfig.java:18:ClasspathResourceProcessService service = new ClasspathResourceProcessService();
```

**Indicates:** Process-lib module in use; journey definitions loaded and served

---

### Pattern 37: Process.json Files and Process Configuration

**Purpose:** Find process.json definition files and process-related configuration properties

```bash
find src/main/resources -name "*.json" -path "*/processes/*" 2>/dev/null
```

**Alternative (grep for process properties in config files):**
```bash
grep -rn "process\.\|processes/\|processId\|launchId\|process-lib" src/main/resources/ --include="*.properties" --include="*.yml" --include="*.yaml" --include="*.json"
```

**Expected Output:**
```
src/main/resources/processes/myJourney_v1.json
src/main/resources/processes/cardControl_v2.json
src/main/resources/application.properties:25:secure-proxy.default.urlmappings.bootstrap=/launchProcess
```

**Indicates:** Process definitions present; MCA journey structure configured

---

### Pattern 38: LaunchProcess / BootstrapContext / BootstrapService Usage

**Purpose:** Find process bootstrap and launch classes used during process initialization

```bash
grep -rn "LaunchProcess\|BootstrapContext\|BootstrapService\|ContextData\|EndPoint" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/service/JourneyService.java:15:LaunchProcess launchRequest = new LaunchProcess();
src/main/java/com/example/config/ProxyConfig.java:22:@Autowired BootstrapService bootstrapService;
src/main/java/com/example/model/ProcessEndpoint.java:8:private EndPoint endpoint;
```

**Indicates:** Secure proxy process bootstrap in use; process initialization and chaining configured

---

## ADVANCED PATTERN COMBINATIONS

Multi-pattern searches for comprehensive framework assessment.

### Pattern 26: Complete Filter Chain Setup

**Purpose:** Find all components of a properly configured filter chain

```bash
grep -rn "@EnableExperienceAPI\|FilterRegistrationBean\|@ConditionalOnProperty.*filter" src/ --include="*.java" | sort | uniq
```

**Expected Output:**
```
src/main/java/com/example/Application.java:7:@EnableExperienceAPI
src/main/java/com/example/config/FilterConfig.java:15:public FilterRegistrationBean<CustomFilter> customFilter() {
src/main/java/com/example/config/FilterConfig.java:18:@ConditionalOnProperty(name = "custom.filter.enabled")
```

**Indicates:** Complete framework integration; proper setup

---

### Pattern 27: Context Propagation End-to-End

**Purpose:** Find all components of context propagation (creation, storage, propagation)

```bash
grep -rn "new.*Context\|@IOLContext\|WebUtils\|X-.*Context" src/ --include="*.java" | wc -l
```

**Shorter version - Context creation and usage:**
```bash
grep -rn "@IOLContext\|WebUtils\.get\|X-.*Context" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/controller/OrderController.java:19:@IOLContext CustomerContext customer
src/main/java/com/example/service/OrderService.java:45:IOLSchema schema = WebUtils.getIOLSchemaFromScope();
src/main/java/com/example/client/RestClient.java:62:headers.put("X-CustomerContext", contextJson);
```

**Indicates:** Complete context flow from request to service calls

---

### Pattern 28: Error Handling Pipeline

**Purpose:** Find complete error handling (exception throwing, catching, response assembly)

```bash
grep -rn "throw new.*Exception\|@ExceptionHandler\|Response\.assemble" src/ --include="*.java" | wc -l
```

**More specific - Find exception handlers and response building:**
```bash
grep -rn "@ExceptionHandler\|@RestControllerAdvice\|GlobalExceptionHandler" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/exception/GlobalExceptionHandler.java:6:@RestControllerAdvice
src/main/java/com/example/exception/GlobalExceptionHandler.java:10:@ExceptionHandler(RequestException.class)
src/main/java/com/example/exception/GlobalExceptionHandler.java:11:public ResponseEntity<?> handleRequestException(RequestException e) {
```

**Indicates:** Centralized error handling; response standardization

---

## SERVICE-TO-SERVICE DETECTION (2 Patterns)

Detect RestTemplate and service client patterns.

### Pattern 29: RestTemplate and RestClientFactory

**Purpose:** Find service-to-service REST communication with context propagation

```bash
grep -rn "RestTemplate\|RestClientFactory\|RestClient\|@FeignClient" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/client/RestClientFactory.java:12:public RestTemplate createRestTemplate() {
src/main/java/com/example/service/PaymentService.java:15:RestTemplate restTemplate;
src/main/java/com/example/client/OrderServiceClient.java:8:@FeignClient(name = "order-service")
```

**Indicates:** Service orchestration; distributed service calls

---

### Pattern 30: Circuit Breaker and Resilience

**Purpose:** Find circuit breaker patterns for fault tolerance

```bash
grep -rn "@CircuitBreaker\|@Retry\|@Bulkhead\|Resilience4j\|spring-cloud-circuit-breaker" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/client/PaymentServiceClient.java:8:@CircuitBreaker(name = "paymentService")
src/main/java/com/example/client/OrderServiceClient.java:12:@Retry(name = "orderService")
build.gradle:45:implementation 'org.springframework.cloud:spring-cloud-starter-circuitbreaker-resilience4j'
```

**Indicates:** Resilience patterns in use; fault tolerance configured

---

## BATCH & ASYNC DETECTION (2 Patterns)

Detect batch processing and async patterns.

### Pattern 31: Batch Processing and ThreadLocal Context

**Purpose:** Find batch job configuration and context management outside web scope

```bash
grep -rn "@Scheduled\|JobBuilderFactory\|StepBuilderFactory\|WebUtils\.set\|WebUtils\.remove" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/batch/OrderBatchProcessor.java:12:@Scheduled(cron = "0 0 * * * *")
src/main/java/com/example/batch/OrderBatchProcessor.java:18:WebUtils.setIOLSchemaInScope(schema);
src/main/java/com/example/batch/OrderBatchProcessor.java:35:WebUtils.removeIOLSchemaFromScope();
```

**Indicates:** Batch processing with context propagation; ThreadLocal management

---

### Pattern 32: Async/Reactive Processing

**Purpose:** Find async task execution and reactive streams

```bash
grep -rn "@Async\|@EnableAsync\|CompletableFuture\|Mono<\|Flux<\|ReactiveContextStore" src/ --include="*.java"
```

**Expected Output:**
```
src/main/java/com/example/service/AsyncOrderService.java:8:@EnableAsync
src/main/java/com/example/service/AsyncOrderService.java:12:@Async
src/main/java/com/example/service/AsyncOrderService.java:13:public CompletableFuture<Order> processOrderAsync(Order order) {
src/main/java/com/example/controller/ReactiveController.java:18:public Mono<Order> getOrder(String id) {
```

**Indicates:** Async processing; reactive patterns in use

---

## QUICK REFERENCE TABLE

| Pattern # | Name | Search Term | Framework Component |
|-----------|------|-------------|-------------------|
| 1 | OncePerRequestFilter | extends OncePerRequestFilter | Filter Chain |
| 2 | Filter Registration | FilterRegistrationBean | Filter Configuration |
| 3 | Core Filters | ContextFilter\|CorrelationIdFilter | EPS Core |
| 4 | Filter Lifecycle | doFilterInternal\|shouldNotFilter | Filter Chain |
| 5 | Conditional Filters | @ConditionalOnProperty.*filter | Configuration |
| 6 | Filter Ordering | setOrder\|filter.*order | Filter Chain |
| 7 | Filter URL Patterns | addUrlPatterns\|setUrlPatterns | Filter Chain |
| 8 | Filter Error Handling | try.*catch.*filter | Exception Handling |
| 9 | IOLSchema | IOLSchema\|getIOLSchema | Context System |
| 10 | @IOLContext Injection | @IOLContext | Context System |
| 11 | WebUtils Context | WebUtils\.setIOLSchemaInScope | Context System |
| 12 | Context Classes | new CustomerContext\|new UserContext | Context System |
| 13 | Context Store | @EnableRDBContextStore\|context\.store\.type | Secure Proxy |
| 14 | Context Headers | X-.*Context\|X-CustomerContext | Context Propagation |
| 15 | @EnableExperienceAPI | @EnableExperienceAPI\|@EnableEPS | EPS Core |
| 16 | EPS Config | ExperienceAPIConfig\|EPSConfiguration | EPS Configuration |
| 17 | MCA Dependencies | mca-context\|mca-filter-core | Dependencies |
| 18 | Auto-Configuration | AutoConfiguration.imports | Spring Boot Integration |
| 19 | Exceptions | GenericException\|RequestException | Exception Handling |
| 20 | Response Envelope | Response<\|ResponseAssembler | Response Handling |
| 21 | Data Masking | @Masked\|@MaskingPattern | Data Protection |
| 22 | Performance Logging | @PerfLogRecordedOperation | Monitoring |
| 23 | Correlation ID | MDC\.put\|Correlation-ID | Tracing |
| 24 | Conditional Beans | @ConditionalOnProperty\|@ConditionalOnMissingBean | Spring Config |
| 25 | Properties | mca\.eps\|mca\.filter | Configuration |
| 26 | Full Chain Setup | @EnableExperienceAPI\|FilterRegistrationBean | EPS Integration |
| 27 | Context Flow | @IOLContext\|WebUtils\.get\|X-.*Context | End-to-End |
| 28 | Error Pipeline | @ExceptionHandler\|Response\.assemble | Error Handling |
| 29 | REST Clients | RestTemplate\|RestClientFactory | Service Calls |
| 30 | Resilience | @CircuitBreaker\|@Retry | Fault Tolerance |
| 31 | Batch Processing | @Scheduled\|WebUtils\.set | Batch Jobs |
| 32 | Async Processing | @Async\|CompletableFuture | Async/Reactive |
| 33 | OAS Validation Classes | OASRequestValidation\|OasProvider | OAS Validation |
| 34 | OAS Config Properties | core\.default\.oas\. | OAS Configuration |
| 35 | OpenAPI Spec Files | openapi:\|openapi.yaml | OAS Spec Detection |
| 36 | Process Classes | ProcessService\|ProcessController\|ProcessDiscovery | Process System |
| 37 | Process.json Files | processes/\|processId\|launchId | Process Configuration |
| 38 | Bootstrap/Launch | LaunchProcess\|BootstrapContext\|BootstrapService | Process Bootstrap |

---

## PATTERN USAGE EXAMPLES

### Example 1: Complete Framework Scan

```bash
# Scan for all MCA2 framework components
echo "=== Core Framework ==="
grep -rn "@EnableExperienceAPI" src/ --include="*.java"

echo "=== Filters ==="
grep -rn "extends OncePerRequestFilter" src/ --include="*.java" | wc -l

echo "=== Context System ==="
grep -rn "@IOLContext" src/ --include="*.java" | wc -l

echo "=== Exception Handling ==="
grep -rn "GenericException\|RequestException\|ServerException" src/ --include="*.java" | wc -l

echo "=== Configuration ==="
grep -rn "mca\\.eps\|mca\\.filter" src/main/resources/ --include="*.properties" | wc -l
```

### Example 2: Risk Assessment Scan

```bash
# Assess architecture quality
echo "=== Adoption Score ==="
FRAMEWORK=$(grep -rc "@EnableExperienceAPI" src/ --include="*.java")
FILTERS=$(grep -rc "extends OncePerRequestFilter" src/ --include="*.java")
CONTEXT=$(grep -rc "@IOLContext" src/ --include="*.java")
EXCEPTIONS=$(grep -rc "GenericException" src/ --include="*.java")
CONFIG=$(grep -rc "mca\\.filter" src/main/resources/ --include="*.properties")

TOTAL=$((FRAMEWORK * 10 + FILTERS * 3 + CONTEXT * 2 + EXCEPTIONS * 1 + CONFIG * 1))
echo "EPS Adoption Score: $TOTAL"

if [ $TOTAL -lt 5 ]; then echo "Tier 1: Minimal"; fi
if [ $TOTAL -ge 5 ] && [ $TOTAL -lt 15 ]; then echo "Tier 2: Core"; fi
if [ $TOTAL -ge 15 ] && [ $TOTAL -lt 30 ]; then echo "Tier 3: Moderate"; fi
if [ $TOTAL -ge 30 ]; then echo "Tier 4+: Heavy"; fi
```

### Example 3: Automated Pattern Report

```bash
#!/bin/bash
# Generate comprehensive pattern report

OUTPUT_FILE="mca-analysis-$(date +%Y%m%d-%H%M%S).txt"

{
  echo "MCA2 EPS Framework Analysis Report"
  echo "Generated: $(date)"
  echo "Directory: $(pwd)"
  echo ""

  echo "=== FILTER CHAIN ==="
  echo "Custom Filters: $(grep -rc 'extends OncePerRequestFilter' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo "Filter Registrations: $(grep -rc 'FilterRegistrationBean' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo ""

  echo "=== CONTEXT SYSTEM ==="
  echo "@IOLContext Injections: $(grep -rc '@IOLContext' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo "Context Class Usage: $(grep -rc 'new.*Context()' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo "WebUtils Usage: $(grep -rc 'WebUtils\.' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo ""

  echo "=== EPS CORE ==="
  echo "@EnableExperienceAPI: $(grep -rc '@EnableExperienceAPI' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo "MCA Dependencies: $(grep -rc 'mca-' build.gradle pom.xml 2>/dev/null || echo 0)"
  echo ""

  echo "=== EXCEPTION & RESPONSE ==="
  echo "Exception Usage: $(grep -rc 'Exception' src/ --include='*.java' 2>/dev/null | awk -F: '{sum+=$2} END {print sum}')"
  echo "Response Envelope: $(grep -rc 'Response<\|ResponseAssembler' src/ --include='*.java' 2>/dev/null || echo 0)"
  echo ""

  echo "=== CONFIGURATION ==="
  echo "MCA Properties: $(grep -rc 'mca\.' src/main/resources/ --include='*.properties' --include='*.yml' 2>/dev/null || echo 0)"

} | tee $OUTPUT_FILE

echo "Report saved to: $OUTPUT_FILE"
```

---

## INTEGRATION WITH CI/CD

### GitHub Actions Integration

```yaml
name: MCA2 Framework Detection

on: [push, pull_request]

jobs:
  detect:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run MCA2 Detection Patterns
        run: |
          echo "=== Filter Chain Usage ==="
          grep -rn "extends OncePerRequestFilter" src/ --include="*.java" || echo "None found"

          echo "=== Context System Usage ==="
          grep -rn "@IOLContext" src/ --include="*.java" || echo "None found"

          echo "=== EPS Framework ==="
          grep -rn "@EnableExperienceAPI" src/ --include="*.java" || echo "None found"
```

### Local CI Script

```bash
#!/bin/bash
# local-mca-check.sh - Run locally before committing

echo "Running MCA2 Framework Checks..."

# Check for filter issues
FILTER_COUNT=$(grep -rc "extends OncePerRequestFilter" src/ --include="*.java" || echo 0)
echo "Found $FILTER_COUNT custom filters"

# Check for context propagation
CONTEXT_COUNT=$(grep -rc "@IOLContext" src/ --include="*.java" || echo 0)
echo "Found $CONTEXT_COUNT @IOLContext injections"

# Check for exceptions
EXCEPTION_COUNT=$(grep -c "GenericException\|RequestException\|ServerException" src/ --include="*.java" || echo 0)
echo "Found $EXCEPTION_COUNT exception usages"

if [ $FILTER_COUNT -eq 0 ] && [ $CONTEXT_COUNT -eq 0 ]; then
  echo "WARNING: No MCA2 EPS patterns detected"
  exit 1
fi

echo "MCA2 framework checks passed!"
exit 0
```

---

## TROUBLESHOOTING PATTERN MATCHING

### No Results Found

```bash
# Verify pattern works (should find something)
grep -rn "extends" src/ --include="*.java" | head -5

# Try simpler pattern
grep -r "Filter" src/ --include="*.java" | head -10

# Check if directory exists
ls -la src/
```

### Too Many Results

```bash
# Add context exclusions
grep -rn "IOLContext" src/ --include="*.java" --exclude-dir=.git --exclude-dir=build

# Limit to specific directory
grep -rn "IOLContext" src/main/java --include="*.java"

# Filter false positives
grep -rn "IOLContext" src/ --include="*.java" | grep -v "//.*IOLContext"
```

### Performance Issues

```bash
# Use ripgrep for faster searching (install: brew install ripgrep)
rg "IOLContext" src/ --type java

# Limit search scope
rg "IOLContext" src/main/java --type java

# Run pattern detection in background
nohup grep -rn "IOLContext" src/ --include="*.java" > results.txt 2>&1 &
tail -f results.txt
```

---

## PATTERN MAINTENANCE

### Adding New Patterns

When new MCA2 framework components are introduced:

1. Identify searchable keywords from source code
2. Create regex pattern for `grep -rn`
3. Test pattern on known codebase
4. Document expected output
5. Add to appropriate category
6. Update quick reference table

### Updating Patterns

As framework evolves:

```bash
# Find deprecated patterns
grep -rn "deprecated.*filter\|deprecated.*context" src/ --include="*.java"

# Update pattern documentation
# Re-test patterns on latest codebase
# Validate against reference apps
```

---

## QUICK REFERENCE

### Most Important Patterns (Start Here)

```bash
# Framework activation
grep -rn "@EnableExperienceAPI" src/ --include="*.java"

# Context propagation
grep -rn "@IOLContext\|WebUtils\.get" src/ --include="*.java"

# Filter chain
grep -rn "extends OncePerRequestFilter" src/ --include="*.java"

# Error handling
grep -rn "GenericException\|@ExceptionHandler" src/ --include="*.java"

# Configuration
grep -rn "mca\.filter\|mca\.eps" src/main/resources/
```

**Grep Patterns provides 38 ready-to-use regex patterns for MCA2 EPS framework detection.**

