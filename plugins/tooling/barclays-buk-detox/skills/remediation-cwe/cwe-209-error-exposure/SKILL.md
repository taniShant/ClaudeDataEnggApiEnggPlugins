---
name: cwe-209-error-exposure
description: "CWE-209: Information Exposure Through an Error Message Remediation — Remediate information exposure through error messages by removing sensitive details from error responses returned to users. Error messages may reveal "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-209: Information Exposure Through an Error Message Remediation
## Quick Start

This skill provides the fix pattern for CWE-209. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-209 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-209
- **CWE Name**: Information Exposure Through an Error Message
- **Severity**: Medium
- **OWASP Category**: A09:2021 - Security Logging and Monitoring Failures

## Purpose

Remediate information exposure through error messages by removing sensitive details from error responses returned to users. Error messages may reveal system internals, file paths, database structure, or other sensitive information.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-209`.

## Steps

1. **Identify error handlers** that return detailed error information.

2. **Add generic error messages** for users while logging details.

3. **Apply the edit.**
   - Use `Edit` to replace detailed errors with generic ones.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "exposure_type": "stack_trace | file_path | database_details"
    }
  ],
  "error_handlers_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
try:
    result = database.query(user_input)
except Exception as e:
    return {"error": str(e)}  # VULNERABLE: may expose database details

# Returning stack traces:
except Exception as e:
    return {"error": traceback.format_exc()}  # VULNERABLE
```

## Fix Pattern

1. Log detailed errors server-side.
2. Return generic errors to users.
3. Include error ID for support reference.

## Language-Specific Examples

### Python - Flask

**Before (vulnerable):**
```python
@app.route('/data/<item_id>')
def get_data(item_id):
    try:
        result = db.query(f"SELECT * FROM items WHERE id={item_id}")
        return jsonify(result)
    except Exception as e:
        return {"error": str(e)}, 500  # May expose SQL syntax, table names
```

**After (fixed):**
```python
import logging
import uuid

logger = logging.getLogger(__name__)

@app.route('/data/<item_id>')
def get_data(item_id):
    try:
        result = db.query(f"SELECT * FROM items WHERE id={item_id}")
        return jsonify(result)
    except Exception as e:
        error_id = str(uuid.uuid4())
        logger.error(f"Error ID {error_id}: {str(e)}")  # Log detailed error
        return {
            "error": "An error occurred processing your request",
            "error_id": error_id
        }, 500  # Generic error to user
```

### Java - Spring Boot

**Before (vulnerable):**
```java
@GetMapping("/api/data/{id}")
public ResponseEntity<?> getData(@PathVariable String id) {
    try {
        return ResponseEntity.ok(dataService.get(id));
    } catch (DatabaseException e) {
        return ResponseEntity.status(500)
            .body(new ErrorResponse(e.getMessage()));  // Exposes DB details
    }
}
```

**After (fixed):**
```java
@GetMapping("/api/data/{id}")
public ResponseEntity<?> getData(@PathVariable String id) {
    try {
        return ResponseEntity.ok(dataService.get(id));
    } catch (DatabaseException e) {
        String errorId = UUID.randomUUID().toString();
        logger.error("Error ID {}: {}", errorId, e.getMessage());
        return ResponseEntity.status(500)
            .body(new ErrorResponse("An error occurred. Reference: " + errorId));
    }
}
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
app.get('/api/data/:id', (req, res) => {
    try {
        const data = db.query(`SELECT * FROM items WHERE id=${req.params.id}`);
        res.json(data);
    } catch (error) {
        res.status(500).json({ error: error.message });  // Exposes details
    }
});
```

**After (fixed):**
```javascript
const crypto = require('crypto');

app.get('/api/data/:id', (req, res) => {
    try {
        const data = db.query(`SELECT * FROM items WHERE id=${req.params.id}`);
        res.json(data);
    } catch (error) {
        const errorId = crypto.randomUUID();
        logger.error(`Error ID ${errorId}:`, error);
        res.status(500).json({
            error: "An error occurred processing your request",
            errorId: errorId
        });
    }
});
```

## Testing Guidance

1. **Trigger error conditions**: Cause exceptions to occur.
2. **Verify generic errors**: Ensure users see generic messages.
3. **Verify logging**: Check that detailed errors are logged server-side.
4. **Verify error ID**: Ensure error IDs are included for support reference.

## Common Mistakes

1. **Returning stack traces** to users.
2. **Exposing file paths** in error messages.
3. **Revealing database structure** in error messages.
4. **Not logging detailed errors** for debugging.
5. **Returning raw exception messages** without sanitization.

## Constraints

- Users must see generic error messages.
- Detailed errors must be logged server-side.
- Error IDs must be included for support reference.
- No sensitive information in error responses.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
