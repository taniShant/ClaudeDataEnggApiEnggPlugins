---
name: cwe-95-code-injection
description: "CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code Remediation — Remediate code injection vulnerabilities by avoiding dynamic code execution (eval, exec, Function constructor, etc.) with user-controlled input. Code "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-95: Improper Neutralization of Directives in Dynamically Evaluated Code Remediation
## Quick Start

This skill provides the fix pattern for CWE-95. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-95 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-95
- **CWE Name**: Improper Neutralization of Directives in Dynamically Evaluated Code ('Code Injection')
- **Severity**: Critical
- **OWASP Category**: A03:2021 - Injection

## Purpose

Remediate code injection vulnerabilities by avoiding dynamic code execution (eval, exec, Function constructor, etc.) with user-controlled input. Code injection allows arbitrary code execution on the server.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-95`.

## Steps

1. **Identify dangerous code execution functions** with user input.
   - `eval()`, `exec()`, `Function()` constructor, etc.

2. **Replace with safe alternatives.**
   - Use function lookup/dispatch tables instead of dynamic code execution.
   - Use template engines.
   - Use parameter binding.

3. **Apply the edit.**
   - Use `Edit` to remove eval/exec calls.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "dangerous_function": "eval | exec | Function",
      "replacement": "function_lookup | template | parameter_binding"
    }
  ],
  "dangerous_calls_fixed": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
# VULNERABLE: eval() with user input = RCE
user_code = request.args.get('code')
eval(user_code)

# VULNERABLE: exec() with user input = RCE
exec(user_code)
```

## Fix Pattern

1. Use whitelisted function names instead of dynamic code execution.
2. Use dispatch tables/function mappings.
3. Use template engines with sandboxing.

## Language-Specific Examples

### Python

**Before (vulnerable):**
```python
@app.route('/execute')
def execute():
    code = request.args.get('code')
    result = eval(code)  # VULNERABLE RCE!
    return {"result": result}
```

**After (fixed):**
```python
ALLOWED_FUNCTIONS = {
    'len': len,
    'max': max,
    'min': min,
    'sum': sum,
}

@app.route('/execute')
def execute():
    func_name = request.args.get('function')
    args = request.args.getlist('args')

    if func_name not in ALLOWED_FUNCTIONS:
        return {"error": "Function not allowed"}, 403

    func = ALLOWED_FUNCTIONS[func_name]
    try:
        result = func(*args)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}, 400
```

### JavaScript

**Before (vulnerable):**
```javascript
app.get('/evaluate', (req, res) => {
    const code = req.query.code;
    const result = eval(code);  // VULNERABLE RCE!
    res.json({ result });
});
```

**After (fixed):**
```javascript
const ALLOWED_FUNCTIONS = {
    'length': (x) => x.length,
    'uppercase': (x) => x.toUpperCase(),
    'lowercase': (x) => x.toLowerCase(),
};

app.get('/evaluate', (req, res) => {
    const funcName = req.query.function;
    const arg = req.query.arg;

    if (!ALLOWED_FUNCTIONS[funcName]) {
        return res.status(403).json({ error: 'Function not allowed' });
    }

    try {
        const result = ALLOWED_FUNCTIONS[funcName](arg);
        res.json({ result });
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});
```

### JavaScript - Template Alternative

**Before (vulnerable):**
```javascript
const template = req.body.template;
const html = eval(`\`${template}\``);  // VULNERABLE!
```

**After (fixed):**
```javascript
const Handlebars = require('handlebars');

app.post('/render', (req, res) => {
    const template = req.body.template;
    const data = req.body.data;

    // Use Handlebars instead of eval
    const compiled = Handlebars.compile(template);
    const html = compiled(data);

    res.json({ html });
});
```

## Testing Guidance

1. **Test valid function**: Whitelisted functions should work.
2. **Test code injection payload**: Try `eval("__import__('os').system('id')")`. Should be rejected.
3. **Verify no code execution**: Monitor for unexpected processes or files.

## Common Mistakes

1. **Using eval/exec with any user input.**
2. **Using eval inside a try-catch** - doesn't prevent code execution, just catches errors.
3. **Incomplete blacklist** - easy to bypass.
4. **Using new Function()** - just as dangerous as eval.

## Constraints

- Never use eval(), exec(), or Function() constructor with user input.
- Use whitelisted function dispatch tables.
- Use template engines with proper sandboxing.
- Verify no dangerous built-ins are accessible.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
