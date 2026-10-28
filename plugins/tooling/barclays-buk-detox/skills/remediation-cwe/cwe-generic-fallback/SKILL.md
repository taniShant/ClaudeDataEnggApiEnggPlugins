---
name: cwe-generic-fallback
description: "Generic CWE Remediation Fallback — Provide general security remediation guidance when a specific CWE remediation skill is not available. This fallback skill applies universal secure cod"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Generic CWE Remediation Fallback
## Quick Start

This skill provides the fix pattern for this CWE. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when this CWE is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: Generic (applies to any CWE without a dedicated remediation skill)
- **CWE Name**: Generic Security Vulnerability
- **Severity**: Varies (determined by the specific CWE)
- **OWASP Category**: Varies (determined by the specific CWE)

## Purpose

Provide general security remediation guidance when a specific CWE remediation skill is not available. This fallback skill applies universal secure coding principles — understanding the vulnerability, analyzing code context, validating inputs, encoding outputs, applying the principle of least privilege, and documenting the fix — to produce a reasonable remediation for any CWE. It prioritizes safe, conservative fixes and flags cases that require human expert review.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `line_number` (integer, required): Line where the vulnerability was detected.
  - `code_snippet` (string, optional): The vulnerable code flagged by the scanner.
  - `cwe_id` (string, required): The CWE identifier (e.g., `CWE-XXX`).
  - `cwe_name` (string, optional): The official CWE name.
  - `description` (string, optional): Description of the vulnerability from the scanner.
  - `rule_id` (string, optional): The WIZ rule that triggered the finding.
- **code_context** (required, JSON object): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root.

## Vulnerable Pattern

Since this is a generic fallback, the vulnerable pattern is not predefined. The skill must analyze the specific CWE and code context to identify the vulnerable pattern dynamically.

### General Vulnerability Categories

Use the CWE ID to classify the vulnerability into one of these broad categories, which guide the remediation approach:

| CWE Range / Category | General Approach |
|---|---|
| **Input Validation (CWE-20, 79, 89, 94, etc.)** | Validate, sanitize, and encode all untrusted input before use. |
| **Authentication (CWE-287, 306, 307, 798, etc.)** | Strengthen authentication mechanisms, remove hardcoded credentials, enforce rate limiting. |
| **Authorization (CWE-269, 284, 285, 639, etc.)** | Add proper access control checks, enforce least privilege. |
| **Cryptography (CWE-310, 326, 327, 328, 338, etc.)** | Use strong, modern algorithms with proper key management. |
| **Error Handling (CWE-209, 388, 754, 755, etc.)** | Handle errors gracefully without exposing sensitive information. |
| **Resource Management (CWE-400, 770, 772, 404, etc.)** | Add proper resource limits, cleanup, and error handling. |
| **Code Quality (CWE-476, 561, 563, 570, etc.)** | Fix null dereferences, remove dead code, improve logic. |
| **Configuration (CWE-16, 732, 1004, 1275, etc.)** | Apply secure default configurations, restrict permissions. |

### Dynamic Detection

1. Read the CWE description to understand the root cause.
2. Examine the code context to identify the specific vulnerable pattern.
3. Map the CWE to the closest general category above.
4. Apply the appropriate remediation principles.

## Fix Pattern

### General Approach — The Secure Remediation Framework

Apply these principles in order for any vulnerability:

#### 1. Understand the Vulnerability

- Read the CWE description (from the input or by referencing the CWE ID).
- Understand what the attacker can do (impact) and how (attack vector).
- Identify the root cause: what assumption is the code making that can be violated?

#### 2. Analyze the Code Context

- Examine the vulnerable code and its surrounding context.
- Trace the data flow: where does untrusted input enter, how is it processed, and where is it used?
- Identify the trust boundary: at what point does data cross from untrusted to trusted?

#### 3. Apply Input Validation

- Validate all inputs at the trust boundary (where untrusted data enters the application).
- Use allowlists over denylists when possible.
- Validate data type, length, range, and format.
- Reject invalid input rather than trying to sanitize it.

#### 4. Apply Output Encoding

- Encode output appropriate to the context (HTML encoding for HTML, URL encoding for URLs, SQL parameterization for SQL, etc.).
- Never construct commands, queries, or structured output by concatenating untrusted data.

#### 5. Apply the Principle of Least Privilege

- Ensure the code operates with the minimum permissions required.
- Restrict file access, network access, database permissions, and process privileges.
- Use sandboxes, chroot jails, or containers where appropriate.

#### 6. Add Proper Error Handling

- Handle errors gracefully without exposing sensitive information.
- Log errors server-side for debugging.
- Return generic error messages to users.

#### 7. Document the Fix

- Add a code comment explaining what vulnerability was fixed and why the fix is correct.
- Reference the CWE ID in the comment for future maintainers.

### Step-by-Step Transformation

1. Read the CWE description to understand the vulnerability class.
2. Examine the code context to identify the specific vulnerable pattern.
3. Determine which of the secure coding principles above apply.
4. Apply the most targeted fix that eliminates the vulnerability without over-engineering.
5. Verify the fix preserves existing functionality.
6. Add a brief code comment referencing the CWE.

## Language-Specific Examples

Since this is a generic fallback, examples are provided for the most common remediation patterns applicable across CWEs.

### Input Validation — Generic Pattern

**Before (vulnerable):**
```python
def process_data(user_input: str):
    # Directly uses untrusted input without validation
    result = dangerous_operation(user_input)
    return result
```

**After (fixed):**
```python
import re

VALID_INPUT_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,100}$")

def process_data(user_input: str):
    # CWE-XXX: Validate input before use
    if not user_input or not VALID_INPUT_PATTERN.match(user_input):
        raise ValueError("Invalid input format")
    result = dangerous_operation(user_input)
    return result
```

**Explanation:** Input is validated against a strict pattern before being passed to the sensitive operation. The validation uses an allowlist regex that permits only expected characters and enforces a maximum length.

### Output Encoding — Generic Pattern

**Before (vulnerable):**
```python
def render_output(user_data: str) -> str:
    return f"<div>{user_data}</div>"
```

**After (fixed):**
```python
from markupsafe import escape

def render_output(user_data: str) -> str:
    # CWE-XXX: Encode output to prevent injection
    return f"<div>{escape(user_data)}</div>"
```

**Explanation:** User data is HTML-encoded before being embedded in HTML output, preventing cross-site scripting.

### Least Privilege — Generic Pattern

**Before (vulnerable):**
```python
import os

def read_config(filename: str) -> str:
    # No restriction on file path
    with open(filename) as f:
        return f.read()
```

**After (fixed):**
```python
import os
from pathlib import Path

CONFIG_DIR = Path("/app/config")

def read_config(filename: str) -> str:
    # CWE-XXX: Restrict file access to config directory
    safe_path = (CONFIG_DIR / filename).resolve()
    if not safe_path.is_relative_to(CONFIG_DIR):
        raise ValueError("Access denied: path traversal detected")
    with open(safe_path) as f:
        return f.read()
```

**Explanation:** File access is restricted to a specific directory. The path is resolved to its canonical form and verified to be within the allowed directory, preventing path traversal attacks.

### Error Handling — Generic Pattern

**Before (vulnerable):**
```java
try {
    riskyOperation();
} catch (Exception e) {
    return e.toString();
}
```

**After (fixed):**
```java
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import java.util.UUID;

private static final Logger logger = LoggerFactory.getLogger(MyClass.class);

try {
    riskyOperation();
} catch (Exception e) {
    // CWE-XXX: Do not expose internal error details
    String errorId = UUID.randomUUID().toString().substring(0, 12);
    logger.error("Operation failed [errorId={}]", errorId, e);
    return "An error occurred. Reference: " + errorId;
}
```

**Explanation:** The internal exception details are logged server-side and a generic message with a correlation ID is returned to the caller.

### Access Control — Generic Pattern

**Before (vulnerable):**
```javascript
app.get('/api/admin/users', async (req, res) => {
    // No authorization check
    const users = await User.findAll();
    res.json(users);
});
```

**After (fixed):**
```javascript
const { requireRole } = require('./middleware/auth');

app.get('/api/admin/users', requireRole('admin'), async (req, res) => {
    // CWE-XXX: Enforce authorization before accessing admin resources
    const users = await User.findAll({
        attributes: ['id', 'username', 'email', 'createdAt']
    });
    res.json(users);
});
```

**Explanation:** An authorization middleware is added to enforce that only admin users can access the endpoint. The query is also restricted to return only non-sensitive fields.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Reproduce the original vulnerability**: If a proof-of-concept or test case exists, run it against the fixed code and verify it no longer succeeds.
2. **WIZ re-scan**: Run the same WIZ tool/rule that detected the vulnerability against the fixed code. It should no longer trigger.
3. **Boundary testing**: Test with inputs at the boundary of validation rules (empty strings, maximum lengths, special characters, null values).
4. **Negative testing**: Attempt to bypass the fix using common evasion techniques (encoding, case manipulation, null bytes, double encoding).

### Verifying Existing Functionality Is Preserved

1. Run existing unit tests and integration tests. All should pass.
2. Test the happy path with valid inputs to ensure the fix does not reject legitimate data.
3. Verify error handling returns appropriate status codes and messages.

### Semgrep Rules

Since this is a generic fallback, Semgrep rule creation depends on the specific CWE. After applying the fix, verify that:
- The original WIZ rule/scan that detected the vulnerability no longer triggers.
- No new WIZ findings are introduced by the fix.

## Common Mistakes

1. **Fixing the symptom instead of the root cause**: A WIZ finding on line 42 may be a symptom of missing input validation on line 10. Fix the root cause, not just the specific line.
2. **Over-engineering the fix**: The fix should be proportional to the risk. Do not rewrite entire modules to fix a single vulnerability.
3. **Introducing new vulnerabilities**: Ensure the fix itself does not introduce new security issues (e.g., replacing SQL injection with command injection).
4. **Using denylists instead of allowlists**: Denylists are almost always incomplete. Prefer allowlists that explicitly permit known-good values.
5. **Ignoring the data flow**: A vulnerability may have multiple entry points. Fixing one path while leaving another open is an incomplete fix.
6. **Not testing the fix**: Every fix should be verified with both positive (fix works) and negative (original functionality preserved) tests.
7. **Copy-pasting fixes without understanding them**: Each vulnerability has a unique context. Understand why the fix works before applying it.
8. **Removing functionality instead of securing it**: The goal is to make the code secure while preserving its intended behavior, not to delete features.

## Steps

1. **Read the vulnerability details**: Examine the `cwe_id`, `cwe_name`, `description`, and `code_snippet` to understand what was detected.
2. **Read the affected file**: Use `Read` to open `vulnerability.file_path` and examine the code at and around `vulnerability.line_number`.
3. **Analyze the code context**: Use the `code_context` object to understand the enclosing function, class, data flow, and imports.
4. **Classify the vulnerability**: Map the CWE to one of the general categories (input validation, authentication, authorization, cryptography, error handling, resource management, code quality, configuration).
5. **Research the specific CWE**: If the CWE name and description are provided, use them. Otherwise, use `Grep` to search the project's vulnerability database or documentation for the CWE details.
6. **Determine the fix approach**: Based on the category and specific CWE, select the appropriate secure coding principle(s) to apply.
7. **Apply the fix**: Use `Edit` to modify the vulnerable code. Apply the minimum change necessary to eliminate the vulnerability.
8. **Add a code comment**: Add a brief comment referencing the CWE ID and explaining the fix.
9. **Check for related instances**: Use `Grep` to search for similar patterns in the file and project.
10. **If confidence is low**: Set `status` to `"needs_review"` and provide detailed notes about what was done and what needs human verification.

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
  "cwe_id": "<string: the CWE ID that was remediated>",
  "cwe_name": "<string: the CWE name, if known>",
  "category": "<string: the vulnerability category (input_validation, authentication, authorization, cryptography, error_handling, resource_management, code_quality, configuration)>",
  "fix_approach": "<string: description of the remediation approach applied>",
  "confidence": "<string: 'high' | 'medium' | 'low' — how confident the agent is in the fix>",
  "notes": "<string: detailed notes about the fix, any assumptions made, and recommendations for human review>"
}
```

### Success Indicator

The `status` field is `"fixed"` and the `confidence` field is `"high"` or `"medium"`.

### Failure Indicator

The `status` field is `"failed"` or the `confidence` field is `"low"`, indicating human review is required.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return `{"status": "failed", "reason": "File not found"}`. Do not retry. |
| **CWE ID not recognized** | Proceed with the generic secure coding framework. Set `confidence` to `"low"` and `status` to `"needs_review"`. |
| **Vulnerability description is vague or missing** | Analyze the code context independently. Look for common vulnerability patterns in the flagged code. Set `confidence` to `"low"`. |
| **Fix requires architectural changes** | Document the required changes in `notes` and set `status` to `"needs_review"`. Do not attempt large-scale refactoring. |
| **Multiple interacting vulnerabilities** | Fix only the specific vulnerability identified. Note related issues in `notes`. |
| **Language or framework not recognized** | Apply generic principles (input validation, output encoding) as best as possible. Set `confidence` to `"low"`. |
| **Fix would break existing tests** | Apply the fix and note that tests need updating. Set `status` to `"needs_review"`. |

## Constraints

- **Conservative approach**: When in doubt, set `status` to `"needs_review"` rather than applying an uncertain fix. A false fix is worse than no fix.
- **Preserve functionality**: The fix must not break existing behavior. If functionality and security conflict, set `status` to `"needs_review"` and explain the trade-off.
- **Minimal diff**: Apply the smallest change that eliminates the vulnerability. Do not refactor, optimize, or improve unrelated code.
- **No new dependencies**: Avoid introducing new libraries or frameworks unless absolutely necessary for the fix.
- **Document uncertainty**: If the fix requires assumptions, document them clearly in `notes`.
- **Scope limit**: Fix only the identified vulnerability. Do not proactively scan for or fix other issues.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Edit` for code modifications. Use `Bash` only for syntax validation if needed.
- **Escalate when appropriate**: For CWEs that involve complex business logic, authentication protocols, or cryptographic key management, prefer `"needs_review"` over an automated fix.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
