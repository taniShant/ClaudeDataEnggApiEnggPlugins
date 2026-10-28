---
title: Error Handling and Recovery Patterns
description: SDK3-compliant exception hierarchy, global exception handlers, and error response patterns for generated Spring Boot 3 applications
type: advanced
---

# Error Handling and Recovery Patterns — SDK3 Compliant

## ⛔ PROHIBITED IMPORTS AND CLASSES

The following MUST NEVER appear in any generated Java file:

| Prohibited | Replace With |
|---|---|
| `com.barclays.api.rest.commons.response.*` | `com.barclays.api.bap.bld.lib.common.response.Response` |
| `com.barclays.api.rest.commons.message.Message` | `com.barclays.api.bap.bld.lib.payload.response.Message` |
| `com.barclays.api.bap.bld.lib.restapi.exception.RestApiException` | `com.barclays.api.bap.bld.lib.payload.exceptions.ApiException` |
| `ResponseEntity` (in controllers or exception handlers) | `com.barclays.api.bap.bld.lib.common.response.Response` |
| `@Slf4j` annotation | `LogFactory.getLogger(ClassName.class)` |
| `org.slf4j.Logger` | `com.barclays.api.bap.bld.lib.logging.Logger` |
| `RestTemplate` | `com.barclays.api.bap.bld.lib.restclient.RestApiClient` |
| `WebClient` | `com.barclays.api.bap.bld.lib.restclient.RestApiClient` |
| `@Retryable` without `@EnableRetry` on `ApplicationConfig` | Spring Retry requires `@EnableRetry` — always pair them |
| Custom `@Aspect` logging classes | SDK3 handles this via LogFactory/PerfLogger |

---

## Mandatory SDK3 Imports for All Error Handling Code

```java
// Response types (MANDATORY — use these, never rest.commons)
import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.Message;

// Logging (MANDATORY — never @Slf4j)
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;

// SDK3 exceptions (MANDATORY — never RestApiException)
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiException;
```

---

## Part 1: Application Exception Hierarchy

These are **application-level** domain exceptions (not SDK3 exceptions). They carry business error context.

```java
package {basePackage}.exception;

public abstract class DomainException extends RuntimeException {
    private final String errorCode;
    private final int httpStatus;
    private final String userMessage;

    public DomainException(String errorCode, int httpStatus, String userMessage) {
        super(userMessage);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
        this.userMessage = userMessage;
    }

    public DomainException(String errorCode, int httpStatus, String userMessage, Throwable cause) {
        super(userMessage, cause);
        this.errorCode = errorCode;
        this.httpStatus = httpStatus;
        this.userMessage = userMessage;
    }

    public String getErrorCode() { return errorCode; }
    public int getHttpStatus() { return httpStatus; }
    public String getUserMessage() { return userMessage; }
}
```

### Standard Application Exception Types

```java
// ResourceNotFoundException — 404
public class ResourceNotFoundException extends DomainException {
    public ResourceNotFoundException(String resourceType, String resourceId) {
        super("RESOURCE_NOT_FOUND", 404,
              String.format("%s with ID %s not found", resourceType, resourceId));
    }
}

// ValidationException — 400
public class ValidationException extends DomainException {
    public ValidationException(String message) {
        super("VALIDATION_ERROR", 400, message);
    }
}

// BusinessRuleViolationException — 422
public class BusinessRuleViolationException extends DomainException {
    public BusinessRuleViolationException(String rule, String message) {
        super("BUSINESS_RULE_VIOLATION", 422, message);
    }
}

// ConflictException — 409
public class ConflictException extends DomainException {
    public ConflictException(String resource, String conflictReason) {
        super("CONFLICT", 409,
              String.format("Conflict in %s: %s", resource, conflictReason));
    }
}

// GatewayException — wraps downstream API failures
public class GatewayException extends DomainException {
    public GatewayException(String message, org.springframework.http.HttpStatus status, Throwable cause) {
        super("GATEWAY_ERROR", status.value(), message, cause);
    }
}
```

---

## Part 2: GlobalExceptionHandler (SDK3 Compliant)

🔴 **Return type is always `Response` — NEVER `ResponseEntity`.**
🔴 **Use `Message.create()` from `com.barclays.api.bap.bld.lib.payload.response.Message`.**

```java
package {basePackage}.exception;

import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiException;
import com.barclays.api.bap.bld.lib.payload.response.Message;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.ArrayList;
import java.util.List;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger LOGGER = LogFactory.getLogger(GlobalExceptionHandler.class);

    // ── SDK3 ApiException (thrown by RestApiClient on downstream failures) ──
    // Use apiException.getStatus() to extract the HTTP status.
    // NEVER use RestApiException — that class is deprecated and must not be referenced.
    @ExceptionHandler(ApiException.class)
    public Response handleApiException(ApiException apiException) {
        LOGGER.error("SDK3 ApiException: {}", apiException.getMessage(), apiException);
        Message errorMessage = Message.create(
            "GATEWAY_ERROR",
            "Downstream API Error",
            apiException.getMessage()
        );
        ResponseHttpStatus status = mapHttpStatus(apiException.getStatus() != null
            ? apiException.getStatus().value() : 500);
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(status);
    }

    // ── Application domain exceptions ────────────────────────────────────────
    @ExceptionHandler(ResourceNotFoundException.class)
    public Response handleResourceNotFound(ResourceNotFoundException ex) {
        LOGGER.warn("Resource not found: {}", ex.getMessage());
        Message errorMessage = Message.create(
            "RESOURCE_NOT_FOUND",
            "Not Found",
            ex.getUserMessage()
        );
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(ResponseHttpStatus.NOT_FOUND);
    }

    @ExceptionHandler(ValidationException.class)
    public Response handleValidation(ValidationException ex) {
        LOGGER.warn("Validation error: {}", ex.getMessage());
        Message errorMessage = Message.create(
            "VALIDATION_ERROR",
            "Validation Error",
            ex.getUserMessage()
        );
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(ResponseHttpStatus.BAD_REQUEST);
    }

    @ExceptionHandler(ConflictException.class)
    public Response handleConflict(ConflictException ex) {
        LOGGER.warn("Conflict: {}", ex.getMessage());
        Message errorMessage = Message.create(
            "CONFLICT",
            "Conflict",
            ex.getUserMessage()
        );
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(ResponseHttpStatus.CONFLICT);
    }

    @ExceptionHandler(GatewayException.class)
    public Response handleGatewayException(GatewayException ex) {
        LOGGER.error("Gateway error: {}", ex.getMessage(), ex);
        List<Message> errorMessages = new ArrayList<>();
        errorMessages.add(Message.create("GATEWAY_ERROR", "Downstream Service Error", ex.getUserMessage()));
        return RestResponse.assemble()
                .addErrorMessages(errorMessages)
                .build(ResponseHttpStatus.BAD_GATEWAY);
    }

    @ExceptionHandler(BusinessRuleViolationException.class)
    public Response handleBusinessRule(BusinessRuleViolationException ex) {
        LOGGER.warn("Business rule violated: {}", ex.getMessage());
        Message errorMessage = Message.create(
            "BUSINESS_RULE_VIOLATION",
            "Business Rule Violation",
            ex.getUserMessage()
        );
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(ResponseHttpStatus.UNPROCESSABLE_ENTITY);
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public Response handleIllegalArgument(IllegalArgumentException ex) {
        LOGGER.warn("Illegal argument: {}", ex.getMessage());
        Message errorMessage = Message.create("INVALID_ARGUMENT", "Invalid Argument", ex.getMessage());
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(ResponseHttpStatus.BAD_REQUEST);
    }

    @ExceptionHandler(Exception.class)
    public Response handleGeneral(Exception ex) {
        LOGGER.error("Unexpected error: {}", ex.getMessage(), ex);
        Message errorMessage = Message.create(
            "INTERNAL_SERVER_ERROR",
            "Internal Server Error",
            "An unexpected error occurred"
        );
        return RestResponse.assemble()
                .addErrorMessage(errorMessage)
                .build(ResponseHttpStatus.INTERNAL_SERVER_ERROR);
    }

    // ── Status mapping helper ─────────────────────────────────────────────────
    private ResponseHttpStatus mapHttpStatus(int code) {
        return switch (code) {
            case 400 -> ResponseHttpStatus.BAD_REQUEST;
            case 401 -> ResponseHttpStatus.UNAUTHORIZED;
            case 403 -> ResponseHttpStatus.FORBIDDEN;
            case 404 -> ResponseHttpStatus.NOT_FOUND;
            case 409 -> ResponseHttpStatus.CONFLICT;
            case 422 -> ResponseHttpStatus.UNPROCESSABLE_ENTITY;
            case 502 -> ResponseHttpStatus.BAD_GATEWAY;
            case 503 -> ResponseHttpStatus.SERVICE_UNAVAILABLE;
            default  -> ResponseHttpStatus.INTERNAL_SERVER_ERROR;
        };
    }
}
```

---

## Part 2b: Message Construction Patterns

`Message` comes from `com.barclays.api.bap.bld.lib.payload.response.Message`.
Use `Message.create()` (never `Message.of()` for structured errors).

```java
// Full message (with UUID/correlationId, code, title, details)
Message msg = Message.create("uuid-here", "ERROR_CODE", "Error Title", "Detailed description");

// Without UUID (auto-generated)
Message msg = Message.create("ERROR_CODE", "Error Title", "Detailed description");

// Minimal (code and title only)
Message msg = Message.create("ERROR_CODE", "Error Title");
```

### Single vs Multiple Error Responses

```java
// Single error
return RestResponse.assemble()
        .addErrorMessage(Message.create("CODE", "Title", "Detail"))
        .build(ResponseHttpStatus.NOT_FOUND);

// Multiple errors
List<Message> errors = new ArrayList<>();
errors.add(Message.create("FIELD_ERROR", "Invalid Name", "Name cannot be blank"));
errors.add(Message.create("FIELD_ERROR", "Invalid Email", "Email format is invalid"));
return RestResponse.assemble()
        .addErrorMessages(errors)
        .build(ResponseHttpStatus.BAD_REQUEST);

// Success with data
return RestResponse.assemble().build(ResponseHttpStatus.OK, data);

// Created (201)
return RestResponse.assemble().build(ResponseHttpStatus.CREATED, data);
```

---

## Part 3: ApiException Handling in Gateways

When `RestApiClient` calls a downstream API and the downstream returns an error, it throws
`com.barclays.api.bap.bld.lib.payload.exceptions.ApiException`.

🔴 **NEVER catch `RestApiException`** — that class must not be used.
🔴 **Use `apiException.getStatus()` to extract the HTTP status** from the downstream response.

```java
// CORRECT: catch ApiException from RestApiClient, re-throw as GatewayException
import com.barclays.api.bap.bld.lib.payload.exceptions.ApiException;

@Override
public DownstreamResponse callDownstream(ApiContext apiContext, DownstreamRequest request) {
    PerfEvent perfEvent = PERFORMANCE_LOGGER.start("Invoking Downstream API");
    HttpHeaders httpHeaders = assembleHeaders(apiContext);
    URI uri = UriComponentsBuilder.fromUriString(baseUrl + "/downstream/path")
            .build().toUri();
    try {
        return restApiClient.call(
                RestClientHttpMethod.POST,
                uri,
                request,
                httpHeaders,
                DownstreamResponse.class
        ).getBody();
    } catch (ApiException apiException) {
        // ApiException is thrown by SDK3's RestApiClient for HTTP error responses.
        // Use apiException.getStatus() to get the org.springframework.http.HttpStatus.
        LOGGER.error("Downstream API error — status: {}, message: {}",
                apiException.getStatus(), apiException.getMessage(), apiException);
        throw new GatewayException(
                "Downstream API failed: " + apiException.getMessage(),
                apiException.getStatus() != null
                        ? apiException.getStatus()
                        : org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                apiException
        );
    } catch (Exception ex) {
        LOGGER.error("Unexpected error calling downstream: {}", ex.getMessage(), ex);
        throw new GatewayException(
                "Unexpected error: " + ex.getMessage(),
                org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                ex
        );
    } finally {
        perfEvent.stop();  // MANDATORY
    }
}
```

---

## Part 4: Error Handling in Services (SDK3 Compliant)

🔴 Use `LogFactory.getLogger()` — NEVER `@Slf4j`.

```java
package {basePackage}.service.impl;

import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import {basePackage}.context.ApiContext;
import {basePackage}.exception.ResourceNotFoundException;
import {basePackage}.exception.ConflictException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class {Resource}ServiceImpl implements {Resource}Service {

    private static final Logger LOGGER = LogFactory.getLogger({Resource}ServiceImpl.class);
    private final {Resource}Gateway {resource}Gateway;

    @Override
    public {Resource}Response get{Resource}(ApiContext apiContext, String id) {
        LOGGER.info("Fetching {resource} with id: {}", id);
        try {
            return {resource}Gateway.fetch{Resource}(apiContext, id);
        } catch (GatewayException ex) {
            LOGGER.error("Gateway error fetching {resource} {}: {}", id, ex.getMessage(), ex);
            throw ex;  // re-throw — GlobalExceptionHandler handles it
        }
    }

    @Override
    public {Resource}Response create{Resource}(ApiContext apiContext, Create{Resource}Request request) {
        LOGGER.info("Creating {resource}");
        return {resource}Gateway.create{Resource}(apiContext, request);
    }
}
```

---

## Part 5: Error Handling in Controllers (SDK3 Compliant)

🔴 Controllers do NOT catch exceptions inline — let `GlobalExceptionHandler` handle them.
🔴 Return type is always `Response` — NEVER `ResponseEntity`.

```java
package {basePackage}.controller;

import com.barclays.api.bap.bld.lib.common.response.Response;
import com.barclays.api.bap.bld.lib.logging.LogFactory;
import com.barclays.api.bap.bld.lib.logging.Logger;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus;
import com.barclays.api.bap.bld.lib.payload.response.RestResponse;
import {basePackage}.context.ApiContext;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/{resources}")
@RequiredArgsConstructor
public class {Resource}Controller {

    private static final Logger LOGGER = LogFactory.getLogger({Resource}Controller.class);
    private final {Resource}Service service;

    @GetMapping("/{id}")
    public Response get{Resource}(ApiContext apiContext, @PathVariable String id) {
        LOGGER.info("Fetching {resource} with id: {}", id);
        {Resource}Response result = service.get{Resource}(apiContext, id);
        return RestResponse.assemble().build(ResponseHttpStatus.OK, result);
        // No try-catch needed — ResourceNotFoundException propagates to GlobalExceptionHandler
    }

    @PostMapping
    public Response create{Resource}(ApiContext apiContext,
                                     @RequestBody Create{Resource}Request request) {
        LOGGER.info("Creating {resource}");
        {Resource}Response result = service.create{Resource}(apiContext, request);
        return RestResponse.assemble().build(ResponseHttpStatus.CREATED, result);
        // No try-catch needed — domain exceptions propagate to GlobalExceptionHandler
    }
}
```

---

## Part 6: Gateway Error Handling (SDK3 Compliant)

🔴 Use `RestApiClient` — NEVER `RestClient`, `RestTemplate`, or `WebClient`.
🔴 Catch `ApiException` (NOT `RestApiException`) for HTTP errors from downstream.
🔴 Use `ApiContext` for header assembly.
🔴 Use `UriComponentsBuilder` for URI construction.
🔴 Wrap ALL external calls in try-catch-finally with `perfEvent.stop()` in finally.

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
import org.springframework.stereotype.Component;
import org.springframework.web.util.UriComponentsBuilder;

import java.net.URI;

@Component
public class {Producer}GatewayImpl implements {Producer}Gateway {

    private static final Logger LOGGER = LogFactory.getLogger({Producer}GatewayImpl.class);
    private static final PerfLogger PERFORMANCE_LOGGER = LogFactory.getPerfLogger({Producer}GatewayImpl.class);

    @Value("${downstream.{producer}.base-url:https://api.internal}")
    private String baseUrl;

    private final RestApiClient restApiClient;

    public {Producer}GatewayImpl(RestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }

    @Override
    public {Response}Response call{Operation}(ApiContext apiContext, {Request}Request request) {
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
            // SDK3 RestApiClient throws ApiException for HTTP error responses.
            // Use apiException.getStatus() to get the HTTP status — NEVER use RestApiException.
            LOGGER.error("Downstream API error [status={}]: {}",
                    apiException.getStatus(), apiException.getMessage(), apiException);
            throw new GatewayException(
                    "{Producer} API failed: " + apiException.getMessage(),
                    apiException.getStatus() != null ? apiException.getStatus() : HttpStatus.INTERNAL_SERVER_ERROR,
                    apiException
            );
        } catch (Exception ex) {
            LOGGER.error("Unexpected error calling {producer} API: {}", ex.getMessage(), ex);
            throw new GatewayException(
                    "Unexpected error calling {producer}: " + ex.getMessage(),
                    HttpStatus.INTERNAL_SERVER_ERROR,
                    ex
            );
        } finally {
            perfEvent.stop();  // MANDATORY — always executes
        }
    }

    private HttpHeaders assembleHeaders(ApiContext apiContext) {
        HttpHeaders headers = new HttpHeaders();
        headers.add("Correlation-ID", apiContext.getCorrelationId());
        headers.add("Authorization", apiContext.getAuthorization());
        return headers;
    }
}
```

---

## Part 7: Import Mapping Reference

| Old/Wrong Import (NEVER USE) | Correct SDK3 Import |
|---|---|
| `com.barclays.api.rest.commons.response.*` | `com.barclays.api.bap.bld.lib.common.response.Response` |
| `com.barclays.api.rest.commons.response.RestResponse` | `com.barclays.api.bap.bld.lib.payload.response.RestResponse` |
| `com.barclays.api.rest.commons.response.ResponseHttpStatus` | `com.barclays.api.bap.bld.lib.payload.response.ResponseHttpStatus` |
| `com.barclays.api.rest.commons.message.Message` | `com.barclays.api.bap.bld.lib.payload.response.Message` |
| `com.barclays.api.bap.bld.lib.restapi.exception.RestApiException` | `com.barclays.api.bap.bld.lib.payload.exceptions.ApiException` |
| `lombok.extern.slf4j.Slf4j` (`@Slf4j`) | `com.barclays.api.bap.bld.lib.logging.LogFactory` + `Logger` |
| `org.springframework.http.ResponseEntity` | `com.barclays.api.bap.bld.lib.common.response.Response` |
| `org.springframework.web.client.RestTemplate` | `com.barclays.api.bap.bld.lib.restclient.RestApiClient` |

---

**Version**: 2.0.0
**Authority**: SDK3-compliant error handling for generated Spring Boot 3 applications
**Last Updated**: 2026-07-07
