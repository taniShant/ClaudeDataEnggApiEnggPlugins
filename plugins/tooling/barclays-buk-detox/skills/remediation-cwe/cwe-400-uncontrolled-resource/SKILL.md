---
name: cwe-400-uncontrolled-resource
description: "CWE-400: Uncontrolled Resource Consumption Remediation — Remediate uncontrolled resource consumption vulnerabilities by implementing rate limiting, request size limits, timeout enforcement, and circuit break"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-400: Uncontrolled Resource Consumption Remediation
## Quick Start

This skill provides the fix pattern for CWE-400. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-400 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-400
- **CWE Name**: Uncontrolled Resource Consumption
- **Severity**: High
- **OWASP Category**: A05:2021 - Security Misconfiguration

## Purpose

Remediate uncontrolled resource consumption vulnerabilities by implementing rate limiting, request size limits, timeout enforcement, and circuit breakers. This skill identifies code paths where an attacker can cause excessive resource consumption (CPU, memory, network, disk, connections) leading to denial of service, and adds protective controls to bound resource usage. It covers Python (Flask, Django, asyncio), Java (Spring, rate limiters), and JavaScript/Node.js (Express, rate-limit middleware).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the resource consumption vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-400`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `resource_type` (string, optional): Type of resource at risk (`cpu`, `memory`, `network`, `disk`, `connections`, `generic`). Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.
- **framework** (optional, string): Framework in use (`flask`, `django`, `spring`, `express`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, framework, and resource consumption pattern.**
   - Examine the code to identify what resource is being consumed without limits.
   - Classify the vulnerability: missing rate limiting, unbounded request body, no timeout, infinite loop potential, unbounded query results, etc.

3. **Identify the specific resource at risk.**
   - **CPU**: Regex denial of service (ReDoS), computationally expensive operations without limits.
   - **Memory**: Unbounded data loading, large request bodies, expanding data structures.
   - **Network/Connections**: No rate limiting, unbounded concurrent requests, connection exhaustion.
   - **Disk**: Unrestricted file uploads (size), unbounded log growth, temp file accumulation.
   - **Threads/Processes**: Fork bombs, unbounded thread creation, connection pool exhaustion.

4. **Apply the appropriate resource control.**
   - **Rate limiting**: Add request rate limits per IP, user, or API key.
   - **Request size limits**: Configure maximum request body size.
   - **Timeout enforcement**: Add timeouts to HTTP requests, database queries, external API calls.
   - **Circuit breakers**: Add circuit breakers to external service calls to prevent cascading failures.
   - **Pagination**: Add pagination to endpoints returning large result sets.
   - **Input length limits**: Validate and cap input lengths to prevent ReDoS and excessive processing.

5. **Apply the edit.**
   - Use `Edit` to add the resource controls.
   - Add necessary imports and middleware.
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other endpoints or functions with the same resource consumption risk.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm resource controls are in place.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "resource_type": "<string: cpu | memory | network | disk | connections | generic>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the code with resource controls>",
      "fix_type": "rate_limit | size_limit | timeout | circuit_breaker | pagination | input_validation"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "middleware_added": ["<string: any middleware additions>"],
  "configuration_changes": ["<string: any configuration changes needed>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and resource consumption is properly bounded.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Uncontrolled resource consumption occurs when an application does not limit the amount of resources (CPU, memory, bandwidth, disk, connections) that a single user or request can consume. An attacker can exploit this to exhaust resources and cause denial of service for legitimate users.

### Detection Patterns

**No rate limiting on endpoints:**
```
# Express:      app.post('/api/login', handler)  # No rate limiting
# Flask:        @app.route('/api/search', methods=['POST'])  # No rate limiting
# Spring:       @PostMapping("/api/process")  # No rate limiting
```

**No request body size limit:**
```
# Express:      app.use(express.json())  # No limit option
# Flask:        app.config['MAX_CONTENT_LENGTH'] not set
# Spring:       spring.servlet.multipart.max-file-size not configured
```

**No timeout on external calls:**
```
# Python:       requests.get(url)  # No timeout parameter
# JavaScript:   await fetch(url)  # No AbortController timeout
# Java:         HttpClient.newHttpClient()  # No timeout configured
```

**Unbounded data loading:**
```
# Python:       users = User.query.all()  # Loads all records into memory
# JavaScript:   const data = await Model.find({})  # Loads all records
# Java:         List<User> users = repo.findAll()  # Loads all records
```

**ReDoS-vulnerable regex:**
```
# Python:       re.match(r'(a+)+$', user_input)  # Catastrophic backtracking
# JavaScript:   /^(a+)+$/.test(userInput)  # Catastrophic backtracking
```

**Regex detection patterns:**
```
# No timeout:           requests\.(get|post|put|delete)\([^)]*\)(?!.*timeout)
# No rate limit:        app\.(get|post|put|delete)\(.*(?!.*rateLimit|rateLimiter)
# Unbounded query:      \.query\.(all|find)\(\)(?!.*limit|paginate)
# Large body no limit:  express\.json\(\)(?!.*limit)
# ReDoS pattern:        \(\[^)]*[+*]\)\+|\(\[^)]*[+*]\)\*
```

## Fix Pattern

The general fix applies resource limits at multiple levels:

1. **Rate limiting**: Limit the number of requests per time window per client.
2. **Request size limits**: Cap the maximum size of request bodies, headers, and URLs.
3. **Timeouts**: Set timeouts on all external calls (HTTP, database, file I/O).
4. **Pagination**: Limit the number of results returned per query/response.
5. **Circuit breakers**: Stop calling a failing service after a threshold is reached.
6. **Input validation**: Validate and cap input lengths and complexity.

**Transformation steps:**
1. Identify the resource at risk and the attack vector.
2. Apply the appropriate limit or control.
3. Configure the limit to a reasonable value (not too restrictive for legitimate use, not too permissive for abuse).
4. Return proper error responses (429 Too Many Requests, 413 Payload Too Large, 408 Request Timeout).

## Language-Specific Examples

### Python/Flask -- Rate Limiting

**Before (vulnerable):**
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    user = authenticate(username, password)
    if user:
        return jsonify({'token': generate_token(user)})
    return jsonify({'error': 'Invalid credentials'}), 401
```

**After (fixed):**
```python
from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

app = Flask(__name__)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://",
)

@app.route('/api/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    user = authenticate(username, password)
    if user:
        return jsonify({'token': generate_token(user)})
    return jsonify({'error': 'Invalid credentials'}), 401
```

**Explanation:** `Flask-Limiter` adds rate limiting to the login endpoint (5 attempts per minute per IP address). A global default limit is also set. When the limit is exceeded, a 429 Too Many Requests response is returned automatically. For production, use Redis as the storage backend instead of memory.

### Python/Flask -- Request Size Limit and Timeout

**Before (vulnerable):**
```python
import requests as http_client
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/api/process', methods=['POST'])
def process_data():
    data = request.get_json()
    # Fetch external data without timeout
    external_data = http_client.get(data['url'])
    return jsonify({'result': process(external_data.json())})
```

**After (fixed):**
```python
import requests as http_client
from flask import Flask, request, jsonify

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024  # 1 MB max request body

@app.route('/api/process', methods=['POST'])
def process_data():
    data = request.get_json()
    url = data.get('url', '')

    # Validate URL length
    if len(url) > 2048:
        return jsonify({'error': 'URL too long'}), 400

    # Fetch external data with timeout and size limit
    try:
        external_response = http_client.get(
            url,
            timeout=(5, 30),  # (connect timeout, read timeout) in seconds
            stream=True
        )
        # Limit response size
        content_length = int(external_response.headers.get('content-length', 0))
        if content_length > 10 * 1024 * 1024:  # 10 MB
            return jsonify({'error': 'External resource too large'}), 400
        external_data = external_response.json()
    except http_client.exceptions.Timeout:
        return jsonify({'error': 'External service timeout'}), 504
    except http_client.exceptions.RequestException:
        return jsonify({'error': 'External service unavailable'}), 502

    return jsonify({'result': process(external_data)})
```

**Explanation:** Multiple resource controls are added: (1) `MAX_CONTENT_LENGTH` limits incoming request body size, (2) connect and read timeouts are set on the external HTTP call, (3) the external response size is checked before parsing, and (4) proper error handling returns appropriate HTTP status codes.

### Python -- Pagination for Database Queries

**Before (vulnerable):**
```python
@app.route('/api/users', methods=['GET'])
def list_users():
    users = User.query.all()  # Loads ALL users into memory
    return jsonify([u.to_dict() for u in users])
```

**After (fixed):**
```python
@app.route('/api/users', methods=['GET'])
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 100)  # Cap at 100

    pagination = User.query.paginate(page=page, per_page=per_page, error_out=False)
    return jsonify({
        'users': [u.to_dict() for u in pagination.items],
        'total': pagination.total,
        'page': pagination.page,
        'per_page': pagination.per_page,
        'pages': pagination.pages
    })
```

**Explanation:** The unbounded `User.query.all()` is replaced with paginated queries. The `per_page` parameter is capped at 100 to prevent clients from requesting excessively large pages. Pagination metadata is included in the response.

### JavaScript/Express -- Rate Limiting

**Before (vulnerable):**
```javascript
const express = require('express');
const app = express();

app.use(express.json());

app.post('/api/login', async (req, res) => {
  const { username, password } = req.body;
  const user = await authenticate(username, password);
  if (user) {
    return res.json({ token: generateToken(user) });
  }
  res.status(401).json({ error: 'Invalid credentials' });
});
```

**After (fixed):**
```javascript
const express = require('express');
const rateLimit = require('express-rate-limit');
const app = express();

app.use(express.json({ limit: '1mb' }));  // Request body size limit

// Global rate limit
const globalLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,  // 15 minutes
  max: 100,  // 100 requests per window per IP
  standardHeaders: true,
  legacyHeaders: false,
  message: { error: 'Too many requests, please try again later.' }
});
app.use(globalLimiter);

// Strict rate limit for login
const loginLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,  // 5 login attempts per 15 minutes per IP
  message: { error: 'Too many login attempts, please try again later.' }
});

app.post('/api/login', loginLimiter, async (req, res) => {
  const { username, password } = req.body;
  const user = await authenticate(username, password);
  if (user) {
    return res.json({ token: generateToken(user) });
  }
  res.status(401).json({ error: 'Invalid credentials' });
});
```

**Explanation:** The `express-rate-limit` middleware is added with a global limit (100 requests per 15 minutes) and a stricter limit for the login endpoint (5 attempts per 15 minutes). The `express.json()` middleware is configured with a `limit` option to cap request body size at 1 MB.

### JavaScript/Express -- Timeout and Circuit Breaker

**Before (vulnerable):**
```javascript
const axios = require('axios');

app.get('/api/proxy', async (req, res) => {
  const response = await axios.get(req.query.url);  // No timeout
  res.json(response.data);
});
```

**After (fixed):**
```javascript
const axios = require('axios');

const externalClient = axios.create({
  timeout: 10000,  // 10 second timeout
  maxContentLength: 10 * 1024 * 1024,  // 10 MB max response
  maxBodyLength: 10 * 1024 * 1024,
});

// Simple circuit breaker
class CircuitBreaker {
  constructor(threshold = 5, resetTimeout = 60000) {
    this.failures = 0;
    this.threshold = threshold;
    this.resetTimeout = resetTimeout;
    this.state = 'CLOSED';
    this.nextAttempt = 0;
  }

  async call(fn) {
    if (this.state === 'OPEN') {
      if (Date.now() < this.nextAttempt) {
        throw new Error('Circuit breaker is open');
      }
      this.state = 'HALF_OPEN';
    }
    try {
      const result = await fn();
      this.failures = 0;
      this.state = 'CLOSED';
      return result;
    } catch (err) {
      this.failures++;
      if (this.failures >= this.threshold) {
        this.state = 'OPEN';
        this.nextAttempt = Date.now() + this.resetTimeout;
      }
      throw err;
    }
  }
}

const breaker = new CircuitBreaker(5, 60000);

app.get('/api/proxy', async (req, res) => {
  const url = req.query.url;
  if (!url || url.length > 2048) {
    return res.status(400).json({ error: 'Invalid URL' });
  }

  try {
    const response = await breaker.call(() => externalClient.get(url));
    res.json(response.data);
  } catch (err) {
    if (err.message === 'Circuit breaker is open') {
      return res.status(503).json({ error: 'Service temporarily unavailable' });
    }
    if (err.code === 'ECONNABORTED') {
      return res.status(504).json({ error: 'External service timeout' });
    }
    res.status(502).json({ error: 'External service error' });
  }
});
```

**Explanation:** Multiple controls are added: (1) axios timeout limits request duration, (2) `maxContentLength` limits response size, (3) a circuit breaker prevents repeated calls to a failing service, and (4) input validation limits URL length. Appropriate HTTP status codes are returned for each failure mode.

### Java/Spring -- Rate Limiting with Bucket4j

**Before (vulnerable):**
```java
@RestController
public class ApiController {

    @PostMapping("/api/search")
    public ResponseEntity<?> search(@RequestBody SearchRequest request) {
        List<Result> results = searchService.search(request.getQuery());
        return ResponseEntity.ok(results);
    }
}
```

**After (fixed):**
```java
import io.github.bucket4j.Bandwidth;
import io.github.bucket4j.Bucket;
import io.github.bucket4j.Refill;
import java.time.Duration;
import java.util.concurrent.ConcurrentHashMap;

@RestController
public class ApiController {

    private final ConcurrentHashMap<String, Bucket> buckets = new ConcurrentHashMap<>();

    private Bucket createBucket() {
        Bandwidth limit = Bandwidth.classic(20, Refill.greedy(20, Duration.ofMinutes(1)));
        return Bucket.builder().addLimit(limit).build();
    }

    private Bucket resolveBucket(String clientIp) {
        return buckets.computeIfAbsent(clientIp, k -> createBucket());
    }

    @PostMapping("/api/search")
    public ResponseEntity<?> search(@RequestBody SearchRequest request,
                                     HttpServletRequest httpRequest) {
        String clientIp = httpRequest.getRemoteAddr();
        Bucket bucket = resolveBucket(clientIp);

        if (!bucket.tryConsume(1)) {
            return ResponseEntity.status(429)
                .body(Map.of("error", "Rate limit exceeded. Try again later."));
        }

        // Limit query length
        if (request.getQuery() == null || request.getQuery().length() > 500) {
            return ResponseEntity.badRequest()
                .body(Map.of("error", "Invalid query"));
        }

        List<Result> results = searchService.search(request.getQuery(), 100); // Limit results
        return ResponseEntity.ok(results);
    }
}
```

**Explanation:** Bucket4j provides token-bucket rate limiting (20 requests per minute per IP). Input length is validated. The search query is limited to 100 results. A 429 status code is returned when the rate limit is exceeded.

### Java/Spring -- Request Timeout Configuration

**Before (vulnerable):**
```java
@Bean
public RestTemplate restTemplate() {
    return new RestTemplate();  // No timeout configured
}
```

**After (fixed):**
```java
import org.springframework.http.client.SimpleClientHttpRequestFactory;

@Bean
public RestTemplate restTemplate() {
    SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
    factory.setConnectTimeout(5000);  // 5 seconds
    factory.setReadTimeout(30000);    // 30 seconds
    return new RestTemplate(factory);
}
```

**Spring Boot application.properties:**
```properties
# Request size limits
server.tomcat.max-http-form-post-size=2MB
spring.servlet.multipart.max-file-size=10MB
spring.servlet.multipart.max-request-size=10MB

# Connection limits
server.tomcat.max-connections=200
server.tomcat.accept-count=100
server.tomcat.max-threads=200

# Timeout
server.tomcat.connection-timeout=20000
spring.mvc.async.request-timeout=30000
```

**Explanation:** The `RestTemplate` is configured with connect and read timeouts. Spring Boot application properties set limits on request size, concurrent connections, thread pool, and request timeout.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Rate limit test**: Send requests exceeding the rate limit. Verify a 429 response is returned.
2. **Large request test**: Send a request body exceeding the size limit. Verify a 413 response is returned.
3. **Timeout test**: Make a request to a slow external service. Verify the request times out and returns a 504 response.
4. **Pagination test**: Request data without specifying a page size. Verify the response contains a limited number of results with pagination metadata.
5. **ReDoS test**: Submit input designed to cause catastrophic regex backtracking. Verify the request completes within the timeout.

### Automated Test Pattern

```python
def test_rate_limiting(client):
    for i in range(6):
        response = client.post('/api/login', json={
            'username': 'test', 'password': 'wrong'
        })
    assert response.status_code == 429

def test_request_size_limit(client):
    large_data = {'data': 'x' * (2 * 1024 * 1024)}  # 2 MB
    response = client.post('/api/process', json=large_data)
    assert response.status_code == 413

def test_pagination(client):
    response = client.get('/api/users')
    data = response.get_json()
    assert len(data['users']) <= 100
    assert 'total' in data
    assert 'page' in data
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: missing-timeout-requests
    patterns:
      - pattern: requests.$METHOD($URL, ...)
      - pattern-not: requests.$METHOD($URL, ..., timeout=..., ...)
    message: "HTTP request without timeout"
    languages: [python]
    severity: WARNING
  - id: unbounded-query
    patterns:
      - pattern: $MODEL.query.all()
    message: "Unbounded database query - add pagination"
    languages: [python]
    severity: WARNING
```

### Verifying Functionality is Preserved

- Verify that legitimate requests within rate limits are processed normally.
- Verify that request size limits do not block normal-sized requests.
- Verify that timeouts are generous enough for normal operations but protective against hangs.
- Verify that pagination returns complete results across multiple pages.

## Common Mistakes

1. **Setting rate limits too high or too low.** Too high: ineffective. Too low: blocks legitimate users. Analyze typical usage patterns and set limits accordingly. Login endpoints should have stricter limits than read-only endpoints.

2. **Rate limiting by IP only.** Behind a shared NAT or proxy, many users share an IP. Consider rate limiting by authenticated user ID, API key, or a combination.

3. **Not setting timeouts on all external calls.** Every outbound HTTP request, database query, and external service call must have a timeout. A single missing timeout can cause the entire application to hang.

4. **Using client-provided pagination parameters without validation.** If the client can set `per_page=1000000`, pagination is useless. Always cap the maximum page size server-side.

5. **Applying rate limiting only at the application level.** Application-level rate limiting can be bypassed by overwhelming the application before the middleware runs. Add rate limiting at the infrastructure level (load balancer, API gateway, WAF) as defense-in-depth.

6. **Not handling rate limit responses gracefully.** Return a clear 429 response with a `Retry-After` header so clients know when they can retry.

7. **Using regex with user input without complexity limits.** If user input is used in a regex pattern, validate its length and complexity, or use the `re2` library (Python) which guarantees linear-time matching.

8. **Forgetting to limit WebSocket connections.** WebSocket connections are long-lived and can exhaust connection pools. Add connection limits and idle timeouts for WebSocket endpoints.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine the resource at risk** | Apply general controls (rate limiting + timeouts) and flag for manual review. |
| **Rate limiting library not available** | Recommend adding the library to dependencies. Provide an inline rate limiting implementation as a temporary measure. |
| **Infrastructure-level controls needed** | Note that some controls (connection limits, bandwidth limits) need to be configured at the infrastructure level (load balancer, reverse proxy). Flag for DevOps review. |
| **Multiple resources at risk** | Apply controls for each resource type independently. |
| **Framework not recognized** | Apply generic patterns (inline rate counting, manual timeouts) and flag for framework-specific review. |

## Constraints

- **Preserve legitimate access**: Resource limits must not block normal usage patterns. Set limits based on reasonable usage expectations.
- **No execution**: Do not run the application, make requests, or load-test.
- **Appropriate error responses**: Return proper HTTP status codes (429, 413, 408, 503, 504) with clear error messages.
- **Minimal diff**: Add resource controls without refactoring unrelated code.
- **Defense-in-depth**: Apply controls at multiple levels (application, middleware, infrastructure) when possible.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
