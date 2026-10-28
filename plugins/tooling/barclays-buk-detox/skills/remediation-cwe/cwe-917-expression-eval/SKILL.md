---
name: cwe-917-expression-eval
description: "CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statement ('Expression Language Injection') Remediation — Remediate expression language (EL) injection vulnerabilities by avoiding dynamic evaluation of user-controlled strings in expression languages (OGNL, EL, SpEL)."
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-917: Improper Neutralization of Special Elements used in an Expression Language Statement ('Expression Language Injection') Remediation
## Quick Start

This skill provides the fix pattern for CWE-917. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-917 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-917
- **CWE Name**: Improper Neutralization of Special Elements used in an Expression Language Statement ('Expression Language Injection')
- **Severity**: High
- **OWASP Category**: A03:2021 - Injection
- **Reference**: https://cwe.mitre.org/data/definitions/917.html

## Purpose

Remediate expression language (EL) injection vulnerabilities by avoiding dynamic evaluation of user-controlled strings in expression languages (OGNL, EL, SpEL, etc.). These vulnerabilities allow arbitrary code execution.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-917`.

## Steps

1. **Identify dynamic expression evaluation** with user input.
   - Look for `eval()`, `execute()`, expression parsers with user input.

2. **Remove dynamic evaluation.**
   - Use static templates or whitelisted expressions.
   - Avoid evaluating user input as expressions.

3. **Apply the edit.**
   - Use `Edit` to replace eval with safe alternatives.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "eval_removed": true,
      "alternative": "template | whitelist | static"
    }
  ],
  "dangerous_evals_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
# VULNERABLE: eval() with user input
user_expression = request.args.get('expr')
result = eval(user_expression)  # RCE!

# VULNERABLE: Expression language injection
#{user_expression}  # If user_expression comes from user input
```

## Fix Pattern

1. Never eval() user input.
2. Use whitelisted expressions only.
3. Use template engines with auto-escaping.
4. Use parameter binding instead of string interpolation.

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
@app.route('/calculate')
def calculate():
    expression = request.args.get('expr')
    result = eval(expression)  # VULNERABLE!
    return {"result": result}
```

**After (fixed):**
```python
import ast
import operator

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}

def safe_calculate(expression):
    try:
        tree = ast.parse(expression, mode='eval')
        return eval(compile(tree, '<ast>', 'eval'), {"__builtins__": {}}, {})
    except:
        raise ValueError("Invalid expression")

@app.route('/calculate')
def calculate():
    try:
        expression = request.args.get('expr', '1+1')
        result = safe_calculate(expression)
        return {"result": result}
    except ValueError as e:
        return {"error": str(e)}, 400
```

### Java - Spring EL Injection

**Before (vulnerable):**
```java
@GetMapping("/evaluate")
public ResponseEntity<?> evaluate(@RequestParam String expression) {
    StandardEvaluationContext context = new StandardEvaluationContext();
    ExpressionParser parser = new SpelExpressionParser();
    Object result = parser.parseExpression(expression).getValue(context);  // VULNERABLE!
    return ResponseEntity.ok(result);
}
```

**After (fixed):**
```java
private static final List<String> ALLOWED_EXPRESSIONS = Arrays.asList(
    "2+2", "10*5", "100/2"
);

@GetMapping("/evaluate")
public ResponseEntity<?> evaluate(@RequestParam String expression) {
    if (!ALLOWED_EXPRESSIONS.contains(expression)) {
        return ResponseEntity.badRequest().body("Expression not allowed");
    }

    // Use whitelisted expressions only
    int result = evaluateWhitelistedExpression(expression);
    return ResponseEntity.ok(result);
}

private int evaluateWhitelistedExpression(String expr) {
    // Safe evaluation of whitelisted expressions
    switch (expr) {
        case "2+2": return 4;
        case "10*5": return 50;
        case "100/2": return 50;
        default: throw new IllegalArgumentException("Not whitelisted");
    }
}
```

### Java - OGNL Injection

**Before (vulnerable):**
```java
String userInput = request.getParameter("action");
String ognl = "#action=" + userInput;  // VULNERABLE!
ognl.parseExpression(ognl).getValue(context);
```

**After (fixed):**
```java
String userAction = request.getParameter("action");
if (!isValidAction(userAction)) {
    throw new IllegalArgumentException("Invalid action");
}

// Use whitelisted actions instead of OGNL
executeAction(userAction);
```

## Testing Guidance

1. **Test with valid expression**: Ensure whitelisted expressions work.
2. **Test injection payload**: Try `__import__('os').system('id')` or similar. Should be rejected.
3. **Verify no code execution**: Monitor for unexpected system calls.

## Common Mistakes

1. **Using eval() with any user input.**
2. **Incomplete blacklist** - easy to bypass.
3. **Expression language enabled in templates** when handling user data.
4. **Not escaping user input in EL contexts.**

## Constraints

- Never use eval() with user input.
- Whitelist expressions if user input must map to actions.
- Use template engines with auto-escaping.
- Disable dangerous expression languages when not needed.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
