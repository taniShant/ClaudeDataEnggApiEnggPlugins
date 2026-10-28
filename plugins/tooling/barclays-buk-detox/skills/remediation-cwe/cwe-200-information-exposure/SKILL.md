---
name: cwe-200-information-exposure
description: "CWE-200: Exposure of Sensitive Information Remediation — Remediate information exposure vulnerabilities by removing sensitive data from error responses, log messages, and API responses. This skill transforms"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-200: Exposure of Sensitive Information Remediation
## Quick Start

This skill provides the fix pattern for CWE-200. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-200 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-200
- **CWE Name**: Exposure of Sensitive Information to an Unauthorized Actor
- **Severity**: Medium
- **OWASP Category**: A01:2021 — Broken Access Control

## Purpose

Remediate information exposure vulnerabilities by removing sensitive data from error responses, log messages, and API responses. This skill transforms code that leaks stack traces, database errors, internal paths, credentials, PII, or system configuration details into code that returns generic error messages to users while logging detailed information securely on the server side, and that filters sensitive fields from API responses before transmission.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `line_number` (integer, required): Line where the information exposure was detected.
  - `code_snippet` (string, optional): The vulnerable code flagged by the scanner.
  - `cwe_id` (string, required): Must be `CWE-200`.
- **code_context** (required, JSON object): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root.

## Vulnerable Pattern

Information exposure occurs when an application reveals sensitive data to actors who should not have access to it. This includes:
- Detailed error messages (stack traces, SQL errors, internal exceptions) returned in HTTP responses.
- Sensitive data (passwords, tokens, PII, session IDs) written to log files.
- Internal system details (file paths, server versions, database schemas) exposed in API responses or headers.
- Debug mode left enabled in production.

### Detection Patterns

**General indicators:**
- Exception details returned directly to the client.
- Catch blocks that include the exception message in the HTTP response body.
- Log statements that include passwords, tokens, credit card numbers, or SSNs.
- API responses that include fields not needed by the client (internal IDs, admin flags, password hashes).
- Debug/verbose mode enabled without environment checks.

**Regex patterns for detection:**
```
# Python - exception details in response
return.*?(str\(e\)|repr\(e\)|traceback\.format_exc|e\.args|exception)
# Python - sensitive data in logs
(logging\.|logger\.|log\.)(debug|info|warning|error|critical)\s*\(.*?(password|token|secret|api_key|ssn|credit.card)
# Java - exception in response
response\.(getWriter|getOutputStream).*?(getMessage|getStackTrace|printStackTrace|toString)
(catch|Exception).*?response\.(setStatus|sendError).*?(e\.getMessage|e\.toString)
# Node.js - error details in response
res\.(json|send|status)\s*\(.*?(err\.message|err\.stack|error\.message|error\.stack)
# Generic - debug mode
DEBUG\s*=\s*True|debug\s*[:=]\s*true|app\.debug\s*=\s*True
# Sensitive headers
(Server|X-Powered-By|X-AspNet-Version)
```

## Fix Pattern

### General Approach

1. **Generic error responses**: Replace detailed error messages with user-friendly, non-revealing messages. Return a reference ID that can be used to correlate with server-side logs.
2. **Server-side logging**: Log the full error details (including stack traces) on the server side at an appropriate log level, but never include raw secrets or credentials.
3. **Log filtering**: Implement log sanitization to redact sensitive fields (passwords, tokens, credit card numbers, SSNs) before they are written to logs.
4. **Response sanitization**: Filter API responses to include only the fields the client needs. Remove internal identifiers, admin flags, password hashes, and system details.
5. **Disable debug mode in production**: Ensure debug/verbose modes are controlled by environment configuration and disabled in production.
6. **Remove sensitive headers**: Strip server version headers and other fingerprinting information.

### Step-by-Step Transformation

1. Identify the type of information exposure (error response, log leakage, API response, debug mode).
2. For error responses: Replace the detailed error with a generic message and log the details server-side.
3. For log leakage: Add redaction for sensitive fields before logging.
4. For API responses: Add a response serialization layer that only includes allowed fields.
5. For debug mode: Ensure it is tied to an environment variable and defaults to disabled.

## Language-Specific Examples

### Python/Flask — Error Response

**Before (vulnerable):**
```python
from flask import Flask, jsonify
import traceback

app = Flask(__name__)

@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    try:
        user = db.query(User).filter_by(id=user_id).one()
        return jsonify(user.to_dict())
    except Exception as e:
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc(),
            "query": f"SELECT * FROM users WHERE id = {user_id}"
        }), 500
```

**After (fixed):**
```python
import logging
import uuid
from flask import Flask, jsonify

app = Flask(__name__)
logger = logging.getLogger(__name__)

@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    try:
        user = db.query(User).filter_by(id=user_id).one()
        return jsonify(user.to_dict())
    except Exception:
        error_id = uuid.uuid4().hex[:12]
        logger.exception("Error fetching user %s [error_id=%s]", user_id, error_id)
        return jsonify({
            "error": "An internal error occurred.",
            "error_id": error_id
        }), 500
```

**Explanation:** The detailed error message, traceback, and SQL query are removed from the response. A unique `error_id` is generated and returned to the client for correlation with server-side logs. `logger.exception` logs the full stack trace server-side.

### Python/Flask — Global Error Handler

**Before (vulnerable):**
```python
@app.errorhandler(Exception)
def handle_error(e):
    return jsonify({"error": str(e), "type": type(e).__name__}), 500
```

**After (fixed):**
```python
import logging
import uuid

logger = logging.getLogger(__name__)

@app.errorhandler(Exception)
def handle_error(e):
    error_id = uuid.uuid4().hex[:12]
    logger.exception("Unhandled exception [error_id=%s]", error_id)
    return jsonify({
        "error": "An internal error occurred. Please contact support.",
        "error_id": error_id
    }), 500

@app.errorhandler(404)
def handle_not_found(e):
    return jsonify({"error": "Resource not found."}), 404

@app.errorhandler(400)
def handle_bad_request(e):
    return jsonify({"error": "Invalid request."}), 400
```

**Explanation:** A global error handler catches all unhandled exceptions and returns a generic message. Specific error handlers for 404 and 400 provide appropriate but non-revealing messages. The exception type name is no longer exposed.

### Python — Log Filtering

**Before (vulnerable):**
```python
import logging

logger = logging.getLogger(__name__)

def authenticate(username: str, password: str) -> bool:
    logger.info(f"Login attempt: username={username}, password={password}")
    user = db.get_user(username)
    if user and user.check_password(password):
        logger.info(f"Login successful: {username}, token={user.generate_token()}")
        return True
    logger.warning(f"Login failed: username={username}, password={password}")
    return False
```

**After (fixed):**
```python
import logging

logger = logging.getLogger(__name__)

def authenticate(username: str, password: str) -> bool:
    logger.info("Login attempt: username=%s", username)
    user = db.get_user(username)
    if user and user.check_password(password):
        logger.info("Login successful: username=%s", username)
        return True
    logger.warning("Login failed: username=%s", username)
    return False
```

**Explanation:** Passwords and tokens are removed from all log messages. Only the username is logged (which is necessary for audit purposes). Parameterized logging (`%s`) is used instead of f-strings for better performance and to avoid accidental evaluation.

### Java — Error Response

**Before (vulnerable):**
```java
@RestController
public class UserController {

    @GetMapping("/api/users/{id}")
    public ResponseEntity<?> getUser(@PathVariable Long id) {
        try {
            User user = userService.findById(id);
            return ResponseEntity.ok(user);
        } catch (Exception e) {
            Map<String, String> error = new HashMap<>();
            error.put("error", e.getMessage());
            error.put("stackTrace", Arrays.toString(e.getStackTrace()));
            return ResponseEntity.status(500).body(error);
        }
    }
}
```

**After (fixed):**
```java
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestController
public class UserController {

    private static final Logger logger = LoggerFactory.getLogger(UserController.class);

    @GetMapping("/api/users/{id}")
    public ResponseEntity<?> getUser(@PathVariable Long id) {
        try {
            User user = userService.findById(id);
            return ResponseEntity.ok(user);
        } catch (Exception e) {
            String errorId = UUID.randomUUID().toString().substring(0, 12);
            logger.error("Error fetching user {} [errorId={}]", id, errorId, e);
            Map<String, String> error = new HashMap<>();
            error.put("error", "An internal error occurred.");
            error.put("errorId", errorId);
            return ResponseEntity.status(500).body(error);
        }
    }
}
```

**Explanation:** The stack trace and exception message are removed from the response. A unique error ID is generated for log correlation. The full exception is logged server-side via SLF4J.

### Java — Global Exception Handler

**Before (vulnerable):**
```java
@ControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> handleException(Exception e) {
        return ResponseEntity.status(500).body(Map.of(
            "error", e.getMessage(),
            "class", e.getClass().getName()
        ));
    }
}
```

**After (fixed):**
```java
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@ControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger logger = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(Exception.class)
    public ResponseEntity<?> handleException(Exception e) {
        String errorId = UUID.randomUUID().toString().substring(0, 12);
        logger.error("Unhandled exception [errorId={}]", errorId, e);
        return ResponseEntity.status(500).body(Map.of(
            "error", "An internal error occurred.",
            "errorId", errorId
        ));
    }
}
```

**Explanation:** The exception class name and message are no longer exposed. A correlation ID is included for debugging.

### Node.js/Express — Error Response

**Before (vulnerable):**
```javascript
app.get('/api/users/:id', async (req, res) => {
    try {
        const user = await User.findById(req.params.id);
        res.json(user);
    } catch (err) {
        res.status(500).json({
            error: err.message,
            stack: err.stack,
            code: err.code
        });
    }
});
```

**After (fixed):**
```javascript
const { v4: uuidv4 } = require('uuid');
const logger = require('./logger'); // Assumes a structured logger

app.get('/api/users/:id', async (req, res) => {
    try {
        const user = await User.findById(req.params.id);
        res.json(user);
    } catch (err) {
        const errorId = uuidv4().slice(0, 12);
        logger.error('Error fetching user', {
            userId: req.params.id,
            errorId,
            error: err.message,
            stack: err.stack
        });
        res.status(500).json({
            error: 'An internal error occurred.',
            errorId
        });
    }
});
```

**Explanation:** The error message and stack trace are removed from the client response. Detailed error information is logged server-side with a structured logger. A correlation error ID is returned to the client.

### Node.js/Express — Global Error Handler

**Before (vulnerable):**
```javascript
app.use((err, req, res, next) => {
    res.status(err.status || 500).json({
        message: err.message,
        stack: process.env.NODE_ENV === 'production' ? undefined : err.stack
    });
});
```

**After (fixed):**
```javascript
const { v4: uuidv4 } = require('uuid');
const logger = require('./logger');

app.use((err, req, res, next) => {
    const errorId = uuidv4().slice(0, 12);
    logger.error('Unhandled error', {
        errorId,
        method: req.method,
        path: req.path,
        error: err.message,
        stack: err.stack
    });
    res.status(err.status || 500).json({
        error: 'An internal error occurred.',
        errorId
    });
});
```

**Explanation:** The conditional check for `NODE_ENV` is fragile (if unset, it leaks). The fixed version never returns error details regardless of environment.

### Response Sanitization — Generic Pattern

**Before (vulnerable):**
```python
@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    user = db.query(User).filter_by(id=user_id).one()
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "password_hash": user.password_hash,
        "is_admin": user.is_admin,
        "internal_notes": user.internal_notes,
        "ssn": user.ssn,
        "created_at": user.created_at.isoformat()
    })
```

**After (fixed):**
```python
SAFE_USER_FIELDS = {"id", "username", "email", "created_at"}

@app.route("/api/users/<int:user_id>")
def get_user(user_id):
    user = db.query(User).filter_by(id=user_id).one()
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    })
```

**Explanation:** Sensitive fields (`password_hash`, `is_admin`, `internal_notes`, `ssn`) are removed from the API response. Only fields necessary for the client are included. Consider using a serialization schema (Pydantic model, Marshmallow schema) to enforce this consistently.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Error response test**: Trigger an error (invalid input, non-existent resource, server error) and verify the response body contains only a generic message and error ID, with no stack trace, SQL query, file path, or exception class name.
2. **Log inspection**: Verify that server-side logs contain the full error details (for debugging) but do not contain raw passwords, tokens, or credit card numbers.
3. **API response test**: Make an API call and verify the response does not include fields like `password_hash`, `internal_notes`, `is_admin`, or other internal-only fields.
4. **Header inspection**: Verify that response headers do not include `Server`, `X-Powered-By`, `X-AspNet-Version`, or similar fingerprinting headers.
5. **Debug mode test**: Verify that the application does not return debug information (even when `DEBUG=True` is accidentally set in production).

### Verifying Existing Functionality Is Preserved

1. Verify that successful API responses still contain all expected client-facing fields.
2. Verify that error responses include enough information for the client to take corrective action (e.g., validation errors should indicate which field is invalid, without revealing internal details).
3. Verify that server-side logging still captures sufficient information for debugging.

### Semgrep Rules

After the fix, the following Semgrep patterns should no longer match:
```yaml
rules:
  - id: error-details-in-response
    patterns:
      - pattern-either:
          - pattern: return jsonify({"error": str($E), ...})
          - pattern: res.json({..., stack: $ERR.stack, ...})
          - pattern: response.body(... e.getMessage() ...)
    message: "Error details exposed in response"
    severity: ERROR
  - id: sensitive-data-in-logs
    patterns:
      - pattern-either:
          - pattern: logger.$METHOD(... password ...)
          - pattern: logger.$METHOD(... token ...)
          - pattern: logger.$METHOD(... secret ...)
    message: "Sensitive data in log statement"
    severity: ERROR
```

## Common Mistakes

1. **Checking `NODE_ENV` or `DEBUG` to decide what to expose**: Environment-based checks are fragile. If the variable is unset or misconfigured, sensitive data leaks. Never include sensitive data in responses regardless of environment.
2. **Logging the entire request body**: Request bodies may contain passwords, tokens, or PII. Log only specific, non-sensitive fields.
3. **Returning different error formats for different exceptions**: Revealing the exception type (e.g., `SQLException` vs `NullPointerException`) helps attackers understand the application internals. Use a single generic error format.
4. **Forgetting to sanitize nested objects**: A user object may contain a nested `profile` object with sensitive fields. Sanitization must be recursive or schema-based.
5. **Over-suppressing errors**: Client-side validation errors should still be informative (e.g., "email field is required") without revealing internal details. The fix should distinguish between client errors (4xx) and server errors (5xx).
6. **Not generating a correlation ID**: Without a correlation ID, support teams cannot match user-reported errors to server logs. Always include one.
7. **Logging at the wrong level**: Detailed error information should be logged at `ERROR` level, not `INFO` or `DEBUG`, to ensure it is captured by production log aggregators.

## Steps

1. Use `Read` to open the file at `vulnerability.file_path` and examine the `code_context` to identify the type of information exposure.
2. Classify the exposure: error response, log leakage, API response over-exposure, or debug mode.
3. For error responses: Use `Edit` to replace detailed error messages with generic ones and add server-side logging with a correlation ID.
4. For log leakage: Use `Edit` to remove sensitive fields from log statements or add redaction.
5. For API response over-exposure: Use `Edit` to filter the response to include only client-facing fields.
6. For debug mode: Use `Edit` to ensure debug mode is tied to an environment variable and defaults to disabled.
7. Use `Grep` to search for similar patterns in the same file and across the project.
8. Check for a global error handler — if one does not exist, recommend creating one.

## Output Format

Return a JSON object:

```json
{
  "status": "fixed | failed | needs_review",
  "file_path": "<string: absolute path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: line where the change was made>",
      "description": "<string: what was changed and why>"
    }
  ],
  "exposure_type": "<string: 'error_response' | 'log_leakage' | 'api_response' | 'debug_mode' | 'header_leakage'>",
  "data_removed": ["<string: types of sensitive data removed from the exposure>"],
  "notes": "<string: any additional context or recommendations>"
}
```

### Success Indicator

The `status` field is `"fixed"` and sensitive information is no longer exposed to unauthorized actors.

### Failure Indicator

The `status` field is `"failed"` with a description of what prevented the fix.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return `{"status": "failed", "reason": "File not found"}`. Do not retry. |
| **Cannot determine what data is sensitive** | Apply the most conservative approach (remove all non-essential data from the exposure). Set `status` to `"needs_review"`. |
| **Error handler is in a framework configuration, not code** | Note the configuration file that needs to be changed and set `status` to `"needs_review"`. |
| **Logging framework uses custom appenders** | Note that log redaction may need to be applied at the appender/formatter level. Set `status` to `"needs_review"`. |
| **API response format is defined by an OpenAPI/Swagger spec** | Note the specification file that needs updating. Fix the code and set `status` to `"needs_review"`. |

## Constraints

- **Preserve debugging capability**: Sensitive information must still be available in server-side logs for debugging. The fix moves information from client-facing responses to server-side logs, it does not delete it.
- **Preserve client-facing error quality**: Client errors (4xx) should still provide enough information for the client to correct their request. Only server errors (5xx) should be made generic.
- **Minimal diff**: Change only the error handling, logging, or response serialization. Do not refactor unrelated code.
- **Correlation IDs**: Always include a correlation/error ID in generic error responses.
- **Do not introduce new dependencies** unless necessary. Use built-in UUID generation.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Edit` for code modifications.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
