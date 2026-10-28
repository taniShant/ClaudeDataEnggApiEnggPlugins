---
title: Resiliency Patterns — Spring Retry for Gateway Layer
description: >
    Canonical Spring Retry patterns (@Retryable, @Recover, @Backoff) for all gateway methods
    in generated Spring Boot 3 applications. Applied automatically to every GatewayImpl —
    no user opt-in required.
type: advanced
---

# Resiliency Patterns — Spring Retry for Gateway Layer

All generated `*GatewayImpl` classes apply Spring Retry automatically. Every method that
calls a downstream REST API via `RestApiClient` carries `@Retryable` and a paired `@Recover`.
`@EnableRetry` is activated on `ApplicationConfig` via the template.

---

## Why Spring Retry (not Resilience4j)

- Consistent with the existing DAF session management pattern (`@Retryable` on
  `DafSessionManagementServiceImpl` — domain-reference Section 6)
- Spring Boot 3 native; no additional Nexus resolution needed beyond `spring-retry` JAR
- Annotation-based — visible to `daf-validation-agent` and `sdk3-compliance-agent` checks
- `@EnableRetry` on `ApplicationConfig` activates the AOP proxy chain without any extra beans

---

## Retryable HTTP Status Codes

Only transient server-side failures should be retried. Client errors and auth failures must
**not** be retried — they will always fail and waste latency budget.

| HTTP Status | Meaning | Retry? |
|---|---|---|
| 429 Too Many Requests | Rate limited — back off and retry | YES |
| 502 Bad Gateway | Upstream timeout/error | YES |
| 503 Service Unavailable | Downstream temporarily down | YES |
| 504 Gateway Timeout | Upstream timed out | YES |
| 400 Bad Request | Caller error — fix the request | NO |
| 401 Unauthorized | Auth failure — no point retrying | NO |
| 403 Forbidden | Access denied — no point retrying | NO |
| 404 Not Found | Resource absent — no point retrying | NO |
| 409 Conflict | Business conflict — no point retrying | NO |
| 422 Unprocessable Entity | Validation error — no point retrying | NO |
| 500 Internal Server Error | May be transient — retry as GatewayException | YES (via Exception catch) |

The `isRetryable(ApiException)` helper in each `GatewayImpl` encodes this policy.
Never retry on non-retryable codes — doing so masks bugs and inflates latency.

---

## Canonical Pattern (sMesh — uses LogFactory)

This is the authoritative pattern for sMesh (OpenAPI-generated) gateway implementations.

```java
package {basePackage}.gateway.impl;

import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.PerfEvent;
import com.barclays.api.bap.bld.lib.logging.PerfLogger;
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiException;
import com.barclays.api.bap.bld.lib.restclient.RestApiClient;
import com.barclays.api.bap.bld.lib.restclient.http.RestClientHttpMethod;
import {basePackage}.context.ApiContext;
import {basePackage}.exception.GatewayException;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;

@Component
public class {Producer}GatewayImpl implements {Producer}Gateway {

    private static final Logger LOGGER = LogFactory.getLogger({Producer}GatewayImpl.class);
    private static final PerfLogger PERFORMANCE_LOGGER =
            LogFactory.getPerfLogger({Producer}GatewayImpl.class);

    @Value("${downstream.{producer}.base-url:https://api.internal}")
    private String baseUrl;

    private final RestApiClient restApiClient;

    public {Producer}GatewayImpl(RestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }

    @Override
    @Retryable(
        retryFor = GatewayException.class,
        maxAttemptsExpression = "${retry.gateway.max-attempts:3}",
        backoff = @Backoff(
            delayExpression = "${retry.gateway.delay:500}",
            multiplierExpression = "${retry.gateway.multiplier:2}",
            random = true
        )
    )
    public {Response}Response call{Operation}(
            ApiContext apiContext, {Request}Request request) {
        LOGGER.info("Calling {producer} downstream API");
        PerfEvent perfEvent = PERFORMANCE_LOGGER.start("Invoking {Producer} API");
        HttpHeaders httpHeaders = assembleHeaders(apiContext);
        URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/path/to/endpoint")
                .build()
                .toUri();
        try {
            return restApiClient.call(
                    RestClientHttpMethod.POST,
                    uri,
                    request,
                    httpHeaders,
                    {Response}Response.class
            ).getBody();
        } catch (ApiException apiException) {
            LOGGER.error("{Producer} API error [status={}]: {}",
                    apiException.getStatus(), apiException.getMessage(), apiException);
            if (isRetryable(apiException)) {
                throw new GatewayException(
                        "Retryable error calling {Producer} API: " + apiException.getMessage(),
                        apiException.getStatus() != null
                                ? apiException.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR,
                        apiException);
            }
            throw new GatewayException(
                    "Non-retryable error calling {Producer} API: " + apiException.getMessage(),
                    apiException.getStatus() != null
                            ? apiException.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR,
                    apiException);
        } catch (Exception e) {
            LOGGER.error("Unexpected error calling {producer} API: {}", e.getMessage(), e);
            throw new GatewayException(
                    "Unexpected error calling {producer}: " + e.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR, e);
        } finally {
            perfEvent.stop();  // MANDATORY — always executes
        }
    }

    @Recover
    public {Response}Response recover{Operation}(
            GatewayException ex, ApiContext apiContext, {Request}Request request) {
        LOGGER.error("{Producer} API exhausted all retries. Last error: {}", ex.getMessage(), ex);
        throw ex;
    }

    private boolean isRetryable(ApiException e) {
        if (e.getStatus() == null) {
            return true;
        }
        int code = e.getStatus().value();
        return code == 429 || code == 502 || code == 503 || code == 504;
    }

    private HttpHeaders assembleHeaders(ApiContext apiContext) {
        HttpHeaders httpHeaders = new HttpHeaders();
        httpHeaders.add("Correlation-ID", apiContext.getCorrelationId());
        httpHeaders.add("Authorization", apiContext.getAuthorization());
        return httpHeaders;
    }
}
```

---

## DAF Pattern (uses LoggerSlf4jImpl)

DAF services use `LoggerSlf4jImpl` instead of `LogFactory.getLogger()`. Apply the same
`@Retryable`/`@Recover` structure with DAF-specific imports.

```java
package com.barclays.api.{domain}.gateway.{featureName}.impl;

import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.logging.LoggerSlf4jImpl;
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiException;
import com.barclays.daf.exceptions.ExperienceApiException;
import org.springframework.retry.annotation.Backoff;
import org.springframework.retry.annotation.Recover;
import org.springframework.retry.annotation.Retryable;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;

@Component
public class {Name}GatewayImpl implements {Name}Gateway {

    private static final Logger log = new LoggerSlf4jImpl({Name}GatewayImpl.class);

    private final RestTemplate restTemplate;

    @Value("${api.{name}.url}")
    private String apiUrl;

    @Value("${api.{name}.method}")
    private String apiMethod;

    public {Name}GatewayImpl(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    @Override
    @Retryable(
        retryFor = ExperienceApiException.class,
        maxAttemptsExpression = "${retry.gateway.max-attempts:3}",
        backoff = @Backoff(
            delayExpression = "${retry.gateway.delay:500}",
            multiplierExpression = "${retry.gateway.multiplier:2}",
            random = true
        )
    )
    public {ResponseType} {method}({params}) {
        log.info("Calling {Name} API with url: {}", apiUrl);
        try {
            HttpHeaders headers = new HttpHeaders();
            // assemble headers from context
            HttpEntity<?> entity = new HttpEntity<>(/* body if POST */, headers);
            return restTemplate
                    .exchange(apiUrl, HttpMethod.valueOf(apiMethod), entity, {ResponseType}.class)
                    .getBody();
        } catch (Exception e) {
            log.error("Error calling {Name} API: {}", e.getMessage(), e);
            throw new ExperienceApiException(e.getMessage());
        }
    }

    @Recover
    public {ResponseType} recover{Method}(
            ExperienceApiException ex, {params}) {
        log.error("{Name} API exhausted all retries. Last error: {}", ex.getMessage(), ex);
        throw ex;
    }
}
```

---

## ApplicationConfig — @EnableRetry (mandatory)

`@EnableRetry` is already included in the `templates/ApplicationConfig.java` template.
Do NOT add it again to individual gateway classes.

```java
@Configuration
@EnableRetry  // activates Spring Retry AOP proxy for all @Retryable methods in this context
public class ApplicationConfig {
    // ... existing beans ...
}
```

---

## application.properties — Retry Configuration Keys

These properties are generated into `src/main/resources/application.properties` for every
project with downstream gateways. They control retry behaviour at runtime without
requiring code changes.

```properties
# ─── Gateway Retry Configuration ─────────────────────────────────────────────
# Maximum number of attempts (1 = no retry, 3 = 1 attempt + 2 retries)
retry.gateway.max-attempts=3
# Initial delay before first retry in milliseconds
retry.gateway.delay=500
# Backoff multiplier — each retry waits delay * multiplier^n milliseconds
retry.gateway.multiplier=2
```

Per-producer override (for fine-grained tuning, add additional `@Retryable` expression values):

```properties
# Example per-producer overrides (if a specific gateway needs different policy)
retry.gateway.payment.max-attempts=5
retry.gateway.payment.delay=200
```

---

## @Recover method rules

1. **Same return type** as the `@Retryable` method — Spring Retry matches by return type
2. **First parameter** MUST be the exception type being recovered — `GatewayException ex`
3. **Remaining parameters** MUST match the `@Retryable` method signature exactly in the same order
4. **Method name convention** — prefix with `recover` + original method name (e.g., `recoverProcessPayment`)
5. **Default behaviour** — re-throw the exception to propagate to `GlobalExceptionHandler`
6. For complex use-cases a fallback/degraded response can be returned instead of re-throwing

```java
// CORRECT — re-throw for GlobalExceptionHandler to handle
@Recover
public PaymentResponse recoverProcessPayment(
        GatewayException ex, ApiContext apiContext, PaymentRequest request) {
    LOGGER.error("Payment API exhausted all retries: {}", ex.getMessage(), ex);
    throw ex;
}

// CORRECT — return degraded response (only if business allows partial data)
@Recover
public PaymentResponse recoverProcessPayment(
        GatewayException ex, ApiContext apiContext, PaymentRequest request) {
    LOGGER.error("Payment API exhausted all retries — returning empty response: {}",
            ex.getMessage(), ex);
    return new PaymentResponse(/* safe defaults */);
}
```

---

## Compliance checklist for validation agents

The `daf-validation-agent` and `sdk3-compliance-agent` must verify:

- [ ] Every `*GatewayImpl.java` method that calls `restApiClient.call()` or `restTemplate.exchange()` carries `@Retryable`
- [ ] Every `@Retryable` method has a corresponding `@Recover` method in the same class
- [ ] `@Recover` method signature: first param is the exception type, remaining params match `@Retryable` method
- [ ] `org.springframework.retry.annotation.*` imported in every `*GatewayImpl.java`
- [ ] `@EnableRetry` is present on `ApplicationConfig` (not on gateway classes)
- [ ] `retry.gateway.max-attempts`, `retry.gateway.delay`, `retry.gateway.multiplier` present in `application.properties`
- [ ] `spring-retry` dependency present in `build.gradle`

---

**Version**: 1.0.0
**Authority**: BUK API Engineering — mandatory for all generated gateway implementations
**Applies to**: sMesh (OpenAPI-generated) and DAF gateway layer
