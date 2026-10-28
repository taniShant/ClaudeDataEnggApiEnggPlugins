---
name: cwe-020-improper-input-validation
description: "CWE-20: Improper Input Validation Remediation — Remediate improper input validation vulnerabilities by implementing comprehensive input validation on all user-supplied data. This skill identifies co"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-20: Improper Input Validation Remediation
## Quick Start

This skill provides the fix pattern for CWE-020. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-020 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-20
- **CWE Name**: Improper Input Validation
- **Severity**: High
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate improper input validation vulnerabilities by implementing comprehensive input validation on all user-supplied data. This skill identifies code patterns where user input is not validated, filtered, or sanitized before being used in critical operations, security decisions, or system commands. Proper validation prevents injection attacks, buffer overflows, path traversal, and other input-based vulnerabilities.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file with improper input validation.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-20`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language. Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Identify the input source and usage context.**
   - Determine where the user input comes from (HTTP parameters, file upload, API request, environment variable, etc.).
   - Identify how the input is used (database query, file operation, command execution, security decision, etc.).

3. **Determine the appropriate validation rules.**
   - Based on the expected input format, determine validation rules: type checking, length limits, character whitelisting, range validation, format validation (email, URL, date, etc.).

4. **Apply input validation.**
   - Add validation code before the input is used.
   - Use allow-list (whitelist) validation when possible instead of block-list (blacklist).
   - Validate length, type, and format.
   - Reject invalid input with a clear error message.

5. **Apply the edit.**
   - Use `Edit` to add validation code.
   - Preserve code formatting and surrounding logic.

6. **Scan for similar patterns.**
   - Use `Grep` to find other uses of unvalidated input.
   - Apply the same validation to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm validation is in place.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: unvalidated input usage>",
      "fixed_code": "<string: code with input validation>",
      "validation_type": "type_check | length_check | whitelist | format_check | range_check"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "functions_added": ["<string: validation function names>"],
  "warnings": ["<string: any manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

Improper input validation occurs when an application accepts user-supplied input without verifying that it conforms to the expected format, type, length, or range. This allows attackers to inject malicious data that can be used for injection attacks, buffer overflows, path traversal, or other exploits.

### Detection Patterns

**Direct use without validation:**
```
url_param = request.args.get('id')
result = database.query("SELECT * FROM users WHERE id = " + url_param)

file_path = request.args.get('file')
contents = open(file_path).read()

email = request.form['email']
send_email(email)
```

**Missing length checks:**
```
name = request.args.get('name')
user.name = name  # No length check

buffer = array(256)
strcpy(buffer, user_input)  # Buffer overflow possible
```

## Fix Pattern

1. Identify the expected input characteristics (type, length, format, range, allowed characters).
2. Create a validation function or use a validation library.
3. Validate input immediately after receipt.
4. Reject invalid input with an error.
5. Use validated input throughout the application.

## Language-Specific Examples

### Python - Flask

**Before (vulnerable):**
```python
from flask import Flask, request

app = Flask(__name__)

@app.route('/user/<user_id>')
def get_user(user_id):
    # No validation of user_id
    query = f"SELECT * FROM users WHERE id = {user_id}"
    result = db.execute(query)
    return jsonify(result)
```

**After (fixed):**
```python
from flask import Flask, request
import re

app = Flask(__name__)

def validate_user_id(user_id):
    """Validate that user_id is a positive integer."""
    if not isinstance(user_id, str):
        raise ValueError("user_id must be a string")
    if not re.match(r'^\d+$', user_id):
        raise ValueError("user_id must contain only digits")
    if len(user_id) > 10:
        raise ValueError("user_id is too long")
    return int(user_id)

@app.route('/user/<user_id>')
def get_user(user_id):
    try:
        validated_id = validate_user_id(user_id)
        query = "SELECT * FROM users WHERE id = %s"
        result = db.execute(query, (validated_id,))
        return jsonify(result)
    except ValueError as e:
        return {"error": str(e)}, 400
```

### Java - Spring Boot

**Before (vulnerable):**
```java
@RestController
public class UserController {
    @GetMapping("/user/{userId}")
    public User getUser(@PathVariable String userId) {
        return userService.getUserById(userId);
    }
}

public class UserService {
    public User getUserById(String userId) {
        String query = "SELECT * FROM users WHERE id = " + userId;
        return db.query(query);
    }
}
```

**After (fixed):**
```java
@RestController
public class UserController {
    @GetMapping("/user/{userId}")
    public User getUser(@PathVariable String userId) {
        if (!isValidUserId(userId)) {
            throw new IllegalArgumentException("Invalid user ID format");
        }
        return userService.getUserById(Integer.parseInt(userId));
    }

    private boolean isValidUserId(String userId) {
        if (userId == null || userId.isEmpty()) return false;
        if (userId.length() > 10) return false;
        return userId.matches("^\\d+$");
    }
}

public class UserService {
    public User getUserById(int userId) {
        String query = "SELECT * FROM users WHERE id = ?";
        return db.queryForObject(query, new Object[]{userId}, User.class);
    }
}
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
app.get('/file', (req, res) => {
    const fileName = req.query.file;
    const filePath = `/uploads/${fileName}`;
    res.sendFile(filePath);
});
```

**After (fixed):**
```javascript
const path = require('path');
const fs = require('fs');

function validateFileName(fileName) {
    if (typeof fileName !== 'string') {
        throw new Error('File name must be a string');
    }
    if (fileName.length > 255) {
        throw new Error('File name too long');
    }
    if (!/^[a-zA-Z0-9._-]+$/.test(fileName)) {
        throw new Error('File name contains invalid characters');
    }
    if (fileName.includes('..')) {
        throw new Error('Path traversal not allowed');
    }
    return fileName;
}

app.get('/file', (req, res) => {
    try {
        const fileName = validateFileName(req.query.file);
        const filePath = path.join(__dirname, 'uploads', fileName);
        // Verify the file is within the uploads directory
        if (!filePath.startsWith(path.join(__dirname, 'uploads'))) {
            throw new Error('Access denied');
        }
        res.sendFile(filePath);
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});
```

## Testing Guidance

### Verifying the Fix

1. **Test valid input**: Ensure valid, properly formatted input passes validation and is processed correctly.
2. **Test invalid format**: Try inputs that don't match the expected format. Verify they are rejected.
3. **Test length limits**: Try inputs exceeding length limits. Verify they are rejected.
4. **Test boundary values**: Try inputs at the edges of valid ranges.
5. **Test injection attempts**: Try SQL injection, command injection, path traversal payloads. Verify they are rejected.

### Semgrep Rules

```yaml
rules:
  - id: unsanitized-sql-input
    pattern-either:
      - pattern: $QUERY = "... " + $VAR
      - pattern: $QUERY = f"... {$VAR}"
    message: "Unsanitized input in SQL query"
    languages: [python, javascript, java]
    severity: ERROR
```

## Common Mistakes

1. **Trusting client-side validation only.** Client-side validation can be bypassed. Always validate on the server.

2. **Using blacklist instead of whitelist.** Blacklist validation blocks known bad patterns but new patterns may slip through. Use whitelist validation when possible.

3. **Insufficient length checks.** Buffer overflows result from unchecked input length.

4. **Not validating all input sources.** Validate input from all sources: HTTP parameters, file uploads, API requests, environment variables, etc.

5. **Storing unvalidated input.** Never store unvalidated input. Validate before storage and retrieval.

6. **Case sensitivity issues.** Validation may need to be case-insensitive depending on the context.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **No validation function exists** | Create one based on the expected input format |
| **Multiple validation rules needed** | Create separate validation functions for different input types |
| **Validation logic complex** | Use a validation library if available |
| **Difficult to determine expected format** | Flag for manual review |

## Constraints

- **Preserve functionality**: Validation must not break legitimate use cases.
- **Fail securely**: Invalid input must be rejected, not processed with warnings.
- **Minimal performance impact**: Validation should be efficient.
- **Clear error messages**: Users should understand why their input was rejected (without revealing security details).

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
