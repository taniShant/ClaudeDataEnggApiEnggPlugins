# API SDK Module 4: RestClient

## Overview

Complete RestApiClient built around Spring RestClient (replacing deprecated RestTemplate). Includes RequestHandler and ResponseHandler implementations for handling logic before and after downstream requests. Apache HttpClient 5 pre-configured for HTTP pooling.

**Gradle Dependency:**
```gradle
com.barclays.api:bap-bld-lib-restclient:{version}
```

If using the prescriptive framework (`bap-bld-lib-restapi`), this dependency is already included.

---

## Core Components

### 1. CoreRestApiClient

Default bean created automatically with RestAPI module.

**Supported Methods:**
```java
restApiClient.makeRequest(RestClientHttpMethod.GET, uri, headers);
restApiClient.makeRequest(RestClientHttpMethod.POST, uri, body, headers);
restApiClient.makeRequest(RestClientHttpMethod.GET, uri, upstreamHeaders, downstreamHeaders);
restApiClient.makeRequest(RestClientHttpMethod.POST, uri, body, upstreamHeaders, downstreamHeaders);
```

**Note:** Methods with both upstream/downstream headers are deprecated (auto-header functionality used instead).

### 2. RestClientHttpMethod Enum

Wrapper for Spring's `HttpMethod` to avoid Spring dependency:
- GET
- POST
- PUT
- PATCH
- DELETE

### 3. Headers Format

Headers passed as:
```java
Map<String, List<String>>
```

This avoids requiring Spring dependencies for header handling.

---

## RestClient Flow

```
User calls restApiClient.makeRequest()
    ↓
RequestHandler.handle() — transforms headers/body
    ↓
RestClient — makes actual HTTP call
    ↓
Downstream API response
    ↓
ResponseHandler.handle(ResponseEntity) — transforms to Response
    ↓
Response returned to caller
```

---

## Integration Points in Spring Boot Project

### 1. Gateway Implementation

Create gateway interfaces and implementations for each producer API:

**GatewayInterface.java**
```java
package {base-package}.gateway;

import com.barclays.api.bap.bld.lib.common.Response;
import java.util.Map;
import java.util.List;

public interface ProducerGateway {
    Response fetchUser(String userId, Map<String, List<String>> headers);
    Response createUser(String userId, Object body, Map<String, List<String>> headers);
    Response updateUser(String userId, Object body, Map<String, List<String>> headers);
    Response deleteUser(String userId, Map<String, List<String>> headers);
}
```

**GatewayImpl.java**
```java
package {base-package}.gateway.impl;

import com.barclays.api.bap.bld.lib.restclient.CoreRestApiClient;
import com.barclays.api.bap.bld.lib.restclient.RestClientHttpMethod;
import com.barclays.api.bap.bld.lib.common.Response;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.util.Map;
import java.util.List;

@Component
public class ProducerGatewayImpl implements ProducerGateway {
    
    private final CoreRestApiClient restApiClient;
    
    @Value("${producer.api.baseUrl:http://producer-service:8080}")
    private String producerBaseUrl;
    
    public ProducerGatewayImpl(CoreRestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }
    
    @Override
    public Response fetchUser(String userId, Map<String, List<String>> headers) {
        URI uri = URI.create(producerBaseUrl + "/api/users/" + userId);
        return restApiClient.makeRequest(
            RestClientHttpMethod.GET,
            uri,
            headers
        );
    }
    
    @Override
    public Response createUser(String userId, Object body, Map<String, List<String>> headers) {
        URI uri = URI.create(producerBaseUrl + "/api/users");
        return restApiClient.makeRequest(
            RestClientHttpMethod.POST,
            uri,
            body,
            headers
        );
    }
    
    @Override
    public Response updateUser(String userId, Object body, Map<String, List<String>> headers) {
        URI uri = URI.create(producerBaseUrl + "/api/users/" + userId);
        return restApiClient.makeRequest(
            RestClientHttpMethod.PUT,
            uri,
            body,
            headers
        );
    }
    
    @Override
    public Response deleteUser(String userId, Map<String, List<String>> headers) {
        URI uri = URI.create(producerBaseUrl + "/api/users/" + userId);
        return restApiClient.makeRequest(
            RestClientHttpMethod.DELETE,
            uri,
            headers
        );
    }
}
```

### 2. Service Layer Usage

**ServiceImpl.java**
```java
package {base-package}.service.impl;

import {base-package}.gateway.ProducerGateway;
import com.barclays.api.bap.bld.lib.common.Response;
import org.springframework.stereotype.Service;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class UserServiceImpl implements UserService {
    
    private final ProducerGateway producerGateway;
    
    public UserServiceImpl(ProducerGateway producerGateway) {
        this.producerGateway = producerGateway;
    }
    
    @Override
    public Response getUserDetails(String userId, Map<String, List<String>> headers) {
        // Call downstream API via gateway
        return producerGateway.fetchUser(userId, headers);
    }
}
```

### 3. Controller Layer Integration

**Controller.java**
```java
package {base-package}.controller;

import {base-package}.service.UserService;
import com.barclays.api.bap.bld.lib.common.Response;
import org.springframework.web.bind.annotation.*;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/users")
public class UserController {
    
    private final UserService userService;
    
    public UserController(UserService userService) {
        this.userService = userService;
    }
    
    @GetMapping("/{id}")
    public Response getUser(
        @PathVariable String id,
        @RequestHeader Map<String, List<String>> headers) {
        return userService.getUserDetails(id, headers);
    }
}
```

---

## HTTP Pooling Configuration

Apache HttpClient 5 uses these properties (if defined, otherwise defaults):

**application.yml**
```yaml
http:
  socketTimeout: 0
  connectionTimeout: 180000
  connectionRequestTimeout: 180000
  maxTotal: 150
  maxPerRoute: 50
  defaultMaxPerRoute: 50
  keepAlive: true
  socketTcpNoDelay: false
  keepAliveDuration: 3600000
```

---

## Custom RestClient Implementation

If using this module independently without the RestAPI framework:

```java
RestApiClient restApiClient = new CoreRestApiClient(
    restClient,           // Spring RestClient instance
    requestHandler,       // RequestHandler implementation
    responseHandler       // ResponseHandler implementation
);
```

You must provide:
- Spring RestClient instance
- RequestHandler implementation (from Payload module or custom)
- ResponseHandler implementation (from Payload module or custom)

---

## Auto-Header Forwarding

Headers automatically forwarded to downstream (deprecated methods, but still functional):

```java
Map<String, List<String>> receivedHeaders;   // from incoming request
Map<String, List<String>> downstreamHeaders; // for outgoing call
restApiClient.makeRequest(
    RestClientHttpMethod.GET,
    uri,
    receivedHeaders,
    downstreamHeaders
);
```

**Recommended Approach (new):**
Use single header map and configure auto-headers in `application.yml`:

```yaml
api:
  core:
    request:
      auto-headers: X-Scenario,Correlation-ID,clientId,Authorization
```

---

## Error Handling in Gateway

```java
@Override
public Response fetchUser(String userId, Map<String, List<String>> headers) {
    try {
        URI uri = URI.create(producerBaseUrl + "/api/users/" + userId);
        return restApiClient.makeRequest(
            RestClientHttpMethod.GET,
            uri,
            headers
        );
    } catch (HttpClientErrorException e) {
        // Handle 4xx errors
        return handleClientError(e);
    } catch (HttpServerErrorException e) {
        // Handle 5xx errors
        return handleServerError(e);
    }
}
```

---

## Code Generation Templates

### Multiple Producer Gateway Pattern

```java
@Component
public class UserServiceGatewayImpl implements UserServiceGateway {
    private final CoreRestApiClient restApiClient;
    @Value("${user.service.baseUrl}") private String baseUrl;
    
    public UserServiceGatewayImpl(CoreRestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }
    
    // Generate methods for each endpoint from spec
}

@Component
public class PaymentServiceGatewayImpl implements PaymentServiceGateway {
    private final CoreRestApiClient restApiClient;
    @Value("${payment.service.baseUrl}") private String baseUrl;
    
    public PaymentServiceGatewayImpl(CoreRestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }
    
    // Generate methods for each endpoint from spec
}
```

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-restclient` dependency added
- [ ] CoreRestApiClient bean injected in gateways
- [ ] Gateway interface created per producer spec
- [ ] Gateway implementation created with all endpoint methods
- [ ] RestClientHttpMethod used for HTTP methods
- [ ] Headers passed as `Map<String, List<String>>`
- [ ] HTTP pooling configured in `application.yml` if needed
- [ ] Error handling implemented in gateway methods
- [ ] Auto-header configuration set for downstream calls
- [ ] Services use gateways for all downstream calls
- [ ] Controllers pass request headers to services/gateways
