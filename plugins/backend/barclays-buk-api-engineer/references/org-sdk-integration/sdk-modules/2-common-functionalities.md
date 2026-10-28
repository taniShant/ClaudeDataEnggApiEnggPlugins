# API SDK Module 2: Common Functionalities

## Overview

Common utilities library holding generic types and interfaces required across multiple SDK libraries. This module is foundational and used by RestClient and other modules.

**Gradle Dependency:**
```gradle
com.barclays.api:bap-bld-lib-common:{version}
```

If using the prescriptive framework (`bap-bld-lib-restapi`), this dependency is already included.

---

## Core Components

### 1. Request Class

Generic `Request` class used in downstream calls via RestClient.

**Key Methods:**
```java
<T> T getData(Class<T> type) throws ClassCastException
<T> T getData(TypeReference<T> ref) throws ClassCastException
Map<String, Object> getMeta()
```

### 2. Response Interface

Supports both success and error scenarios in RestClient operations.

**Key Methods:**
```java
<T> T getData() throws ClassCastException
<T> T getData(Class<T> type) throws ClassCastException
Map<String, Object> getMeta()
List<Message> getErrors()
```

### 3. RequestHandler Interface

Handles request transformation and header merging before downstream calls.

**Abstract Methods:**
```java
Request handle(Map<String, List<String>> upstreamHeaders, 
               Map<String, List<String>> downstreamHeaders, 
               Object body);

Request handle(Map<String, List<String>> downstreamHeaders, Object body);

HttpHeaders mergeHeaders(Map<String, List<String>> upstreamHeaders, 
                         Map<String, List<String>> downstreamHeaders);
```

### 4. ResponseHandler Interface

Assembles `Response` objects in success and error scenarios.

**Abstract Method:**
```java
Response handle(ResponseEntity responseEntity);
```

---

## Integration Points in Spring Boot Project

### 1. RestClient Configuration Bean

Create a bean that initializes the RestClient with handlers:

```java
package {base-package}.config;

import com.barclays.api.bap.bld.lib.restclient.CoreRestApiClient;
import com.barclays.api.bap.bld.lib.payload.request.RequestHandlerImpl;
import com.barclays.api.bap.bld.lib.payload.response.ResponseHandlerImpl;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestClient;

@Configuration
public class RestClientConfiguration {
    
    @Bean
    public CoreRestApiClient coreRestApiClient(RestClient restClient) {
        RequestHandlerImpl requestHandler = new RequestHandlerImpl();
        ResponseHandlerImpl responseHandler = new ResponseHandlerImpl();
        return new CoreRestApiClient(restClient, requestHandler, responseHandler);
    }
}
```

### 2. Gateway Implementation Pattern

Use RequestHandler and ResponseHandler in gateway classes:

```java
package {base-package}.gateway.impl;

import com.barclays.api.bap.bld.lib.common.Request;
import com.barclays.api.bap.bld.lib.common.Response;
import com.barclays.api.bap.bld.lib.restclient.RestClientHttpMethod;
import org.springframework.stereotype.Component;
import java.net.URI;
import java.util.*;

@Component
public class ProducerGatewayImpl implements ProducerGateway {
    
    private final CoreRestApiClient restApiClient;
    
    public ProducerGatewayImpl(CoreRestApiClient restApiClient) {
        this.restApiClient = restApiClient;
    }
    
    @Override
    public Response fetchResource(String id, Map<String, List<String>> headers) {
        URI uri = URI.create("http://producer-service/api/resource/" + id);
        return restApiClient.makeRequest(
            RestClientHttpMethod.GET, 
            uri, 
            headers
        );
    }
}
```

### 3. Custom Request/Response Handling

If custom response objects are needed (not using Barclays standard):

```java
public class CustomResponse implements Response {
    
    private Object data;
    private Map<String, Object> meta;
    private List<Message> errors;
    
    @Override
    public <T> T getData() throws ClassCastException {
        return (T) data;
    }
    
    @Override
    public <T> T getData(Class<T> type) throws ClassCastException {
        // Custom conversion logic
        return type.cast(data);
    }
    
    @Override
    public Map<String, Object> getMeta() {
        return meta;
    }
    
    public List<Message> getErrors() {
        return errors;
    }
}
```

### 4. Auto-Header Configuration

Configure which headers are automatically forwarded to downstream calls:

**application.yml**
```yaml
api:
  core:
    request:
      auto-headers: X-Scenario,Correlation-ID,clientId,Authorization,customHeader1
```

Default auto-headers:
- `X-Scenario`
- `Correlation-ID`
- `clientId`
- `Authorization`

---

## Header Merging Strategy

The `RequestHandler.mergeHeaders()` method:
1. Takes upstream (incoming) headers
2. Takes downstream (outgoing) headers
3. Merges them intelligently:
   - Auto-headers from upstream are copied to downstream if not already present
   - Downstream headers take precedence if already set
   - Returns merged `HttpHeaders` object

---

## Request/Response Flow

```
API Request
    ↓
Gateway.fetchResource(headers)
    ↓
RestApiClient.makeRequest(method, uri, headers)
    ↓
RequestHandler.handle() — transform headers/body
    ↓
RestClient/WebClient — actual HTTP call
    ↓
ResponseHandler.handle(ResponseEntity) — transform to Response
    ↓
Response object returned
```

---

## Integration Checklist

- [ ] `com.barclays.api:bap-bld-lib-common` dependency added
- [ ] RestClientConfiguration bean created
- [ ] RequestHandlerImpl and ResponseHandlerImpl configured
- [ ] Gateway classes implement with proper handler usage
- [ ] Auto-headers configured in application.yml if needed
- [ ] Custom Response implementations provided if not using Barclays standard
- [ ] Header merging tested for upstream/downstream scenarios
