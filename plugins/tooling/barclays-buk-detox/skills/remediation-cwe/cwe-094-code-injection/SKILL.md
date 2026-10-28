---
name: cwe-094-code-injection
description: "CWE-94: Code Injection Remediation — Remediate code injection vulnerabilities by eliminating the use of `eval()`, `exec()`, `Function()`, and other dynamic code execution functions that p"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-94: Code Injection Remediation
## Quick Start

This skill provides the fix pattern for CWE-094. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-094 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-94
- **CWE Name**: Improper Control of Generation of Code ('Code Injection')
- **Severity**: Critical
- **OWASP Category**: A03:2021 - Injection

## Purpose

Remediate code injection vulnerabilities by eliminating the use of `eval()`, `exec()`, `Function()`, and other dynamic code execution functions that process untrusted input. This skill identifies patterns where user-controlled data is passed to code execution functions and replaces them with safe alternatives such as data-driven lookups, parser-based approaches, sandboxed execution, or restricted expression evaluators. It covers Python (`eval`, `exec`, `compile`), JavaScript/Node.js (`eval`, `Function`, `vm.runInNewContext`), and Java (scripting engine, reflection-based execution).

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the code injection vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-94`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `injection_type` (string, optional): Type of injection (`eval`, `exec`, `function_constructor`, `template_injection`, `reflection`). Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language and identify the dangerous function.**
   - Locate the specific dynamic code execution function: `eval()`, `exec()`, `compile()`, `Function()`, `vm.runInNewContext()`, `ScriptEngine.eval()`, etc.
   - Trace the user-controlled input to the dangerous function.

3. **Understand the intent of the dynamic code execution.**
   - Determine what the code is trying to accomplish with the dynamic execution:
     - **Mathematical expression evaluation**: Parsing and computing arithmetic expressions.
     - **Dynamic dispatch**: Calling different functions based on user input.
     - **Template rendering**: Generating dynamic content from templates.
     - **Configuration processing**: Evaluating configuration values.
     - **JSON/data parsing**: Parsing structured data.
   - The safe alternative depends on the intent.

4. **Apply the appropriate safe alternative.**
   - **Mathematical expressions**: Use `ast.literal_eval()` (Python), a math expression parser library, or a restricted evaluator.
   - **Dynamic dispatch**: Use a dictionary/map lookup to map input values to functions.
   - **Template rendering**: Use a sandboxed template engine (Jinja2 sandbox, Handlebars).
   - **Configuration processing**: Use a proper configuration library (JSON, YAML, TOML parser).
   - **JSON/data parsing**: Use `json.loads()`, `JSON.parse()`, or equivalent.
   - **If no safe alternative exists**: Add strict input validation (allowlist of acceptable inputs) and document the residual risk.

5. **Apply the edit.**
   - Use `Edit` to replace the dangerous function call with the safe alternative.
   - Add necessary imports.
   - Preserve code formatting, indentation, and surrounding logic.

6. **Scan for similar patterns in the same file and related files.**
   - Use `Grep` to find other instances of `eval`, `exec`, `Function`, or similar dangerous functions.
   - Apply the same fix to all instances.

7. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the dangerous function is removed.
   - Confirm that no user-controlled input flows to a code execution function.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "injection_type": "<string: eval | exec | function_constructor | template_injection | reflection>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the safe replacement>",
      "fix_type": "literal_eval | parser_library | dict_lookup | json_parse | input_validation | sandbox"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all dynamic code execution of user input has been eliminated or safely constrained.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Code injection occurs when an application generates and executes code using untrusted input. Unlike command injection (CWE-78), which targets OS commands, code injection targets the application's own programming language interpreter.

### Detection Patterns

**Python -- eval/exec:**
```
# eval with user input:    eval(request.args.get('expr'))
# exec with user input:    exec(user_code)
# compile with user input: compile(user_input, '<string>', 'exec')
# input() in Python 2:     input(prompt)  # Calls eval() internally in Python 2
```

**JavaScript -- eval/Function:**
```
# eval:                    eval(userInput)
# Function constructor:    new Function('return ' + userInput)()
# setTimeout with string:  setTimeout(userInput, 1000)
# setInterval with string: setInterval(userInput, 1000)
# vm.runInNewContext:       vm.runInNewContext(userInput, {})
```

**Java -- scripting engine:**
```
# ScriptEngine:            engine.eval(userInput)
# Runtime exec:            Runtime.getRuntime().exec(userInput)  // Also CWE-78
# Reflection:              Class.forName(userInput).newInstance()
```

**Template injection:**
```
# Jinja2:                  Template(user_input).render()
# Mako:                    Template(user_input).render()
# Velocity:                Velocity.evaluate(context, writer, "log", userInput)
```

**Regex detection patterns:**
```
# Python eval/exec:        (eval|exec)\s*\(.*?(request|input|args|form|param)
# JavaScript eval:         eval\s*\(.*?(req\.|input|param|query|body)
# Function constructor:    new\s+Function\s*\(.*?(req\.|input|param)
# setTimeout string:       setTimeout\s*\(\s*['"$`]|setTimeout\s*\(\s*\w+\s*[,)]
# Template injection:      Template\s*\(.*?(request|input|user|param)
```

## Fix Pattern

The general fix is to eliminate dynamic code execution of untrusted input entirely. The specific replacement depends on the original intent:

**Transformation strategies:**
1. **Replace eval with a safe parser**: Use `ast.literal_eval()`, `json.loads()`, or a math expression library.
2. **Replace dynamic dispatch with a lookup table**: Map input strings to predefined functions.
3. **Replace template strings with parameterized templates**: Use safe template engines with auto-escaping.
4. **Restrict input to an allowlist**: If dynamic execution cannot be avoided, validate input against a strict allowlist.
5. **Use a sandbox**: If arbitrary code execution is a feature requirement (e.g., a code playground), use a sandboxed environment with resource limits.

## Language-Specific Examples

### Python -- eval() for Math Expressions

**Before (vulnerable):**
```python
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/calculate')
def calculate():
    expression = request.args.get('expr')
    result = eval(expression)
    return jsonify({'result': result})
```

**After (fixed):**
```python
import ast
import operator
from flask import Flask, request, jsonify

app = Flask(__name__)

SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}

def safe_eval_expr(expr):
    """Evaluate a mathematical expression safely using AST parsing."""
    tree = ast.parse(expr, mode='eval')

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPERATORS:
            return SAFE_OPERATORS[type(node.op)](_eval(node.operand))
        else:
            raise ValueError(f"Unsupported expression: {ast.dump(node)}")
    return _eval(tree)

@app.route('/calculate')
def calculate():
    expression = request.args.get('expr', '')
    try:
        result = safe_eval_expr(expression)
        return jsonify({'result': result})
    except (ValueError, SyntaxError) as e:
        return jsonify({'error': 'Invalid expression'}), 400
```

**Explanation:** The `eval()` call is replaced with a custom AST-based expression evaluator that only supports numeric literals and basic arithmetic operators. This prevents arbitrary code execution while preserving the math evaluation functionality. No function calls, attribute access, or imports are possible.

### Python -- eval() for JSON Parsing

**Before (vulnerable):**
```python
def parse_config(config_string):
    return eval(config_string)
```

**After (fixed):**
```python
import json

def parse_config(config_string):
    return json.loads(config_string)
```

**Explanation:** `eval()` used for parsing data structures is replaced with `json.loads()`. If the data format is Python-specific (tuples, sets), use `ast.literal_eval()` instead, which safely evaluates literal expressions only.

### Python -- eval() for Dynamic Dispatch

**Before (vulnerable):**
```python
def process_action(action_name, data):
    result = eval(f"{action_name}(data)")
    return result
```

**After (fixed):**
```python
ALLOWED_ACTIONS = {
    'validate': validate,
    'transform': transform,
    'export': export,
    'analyze': analyze,
}

def process_action(action_name, data):
    action_func = ALLOWED_ACTIONS.get(action_name)
    if action_func is None:
        raise ValueError(f"Unknown action: {action_name}")
    return action_func(data)
```

**Explanation:** Dynamic function invocation via `eval()` is replaced with a dictionary lookup. Only explicitly listed functions can be called. This is the safest approach for dynamic dispatch because it maintains a strict allowlist of callable functions.

### Python -- exec() for Dynamic Code

**Before (vulnerable):**
```python
def run_user_script(script_code):
    exec(script_code)
```

**After (fixed):**
```python
import ast

def run_user_script(script_code):
    """Execute only safe, pre-approved operations from user script."""
    tree = ast.parse(script_code)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Call)):
            raise ValueError("Imports and function calls are not allowed")
        if isinstance(node, ast.Attribute):
            raise ValueError("Attribute access is not allowed")
    # If truly needed, use RestrictedPython or a sandbox
    raise NotImplementedError(
        "Dynamic code execution has been disabled for security. "
        "Please use the supported API methods instead."
    )
```

**Explanation:** In most cases, `exec()` with user input should be removed entirely and replaced with a supported API. If arbitrary code execution is a feature requirement (e.g., a coding platform), use a sandboxed environment like RestrictedPython, Docker containers, or WebAssembly with strict resource limits.

### JavaScript -- eval() Replacement

**Before (vulnerable):**
```javascript
app.get('/calculate', (req, res) => {
  const expr = req.query.expr;
  const result = eval(expr);
  res.json({ result });
});
```

**After (fixed):**
```javascript
const mathjs = require('mathjs');

// Create a restricted math parser (no access to Node.js internals)
const limitedMath = mathjs.create(mathjs.all);
const evaluate = limitedMath.evaluate;

app.get('/calculate', (req, res) => {
  const expr = req.query.expr;
  try {
    const result = evaluate(expr);
    res.json({ result });
  } catch (e) {
    res.status(400).json({ error: 'Invalid expression' });
  }
});
```

**Explanation:** The `eval()` call is replaced with `mathjs.evaluate()`, which provides a safe mathematical expression evaluator that cannot access JavaScript globals, the file system, or network resources.

### JavaScript -- Function Constructor Replacement

**Before (vulnerable):**
```javascript
function runFilter(filterCode, data) {
  const filterFn = new Function('data', filterCode);
  return filterFn(data);
}
```

**After (fixed):**
```javascript
const FILTERS = {
  'active': (data) => data.filter(item => item.active),
  'recent': (data) => data.filter(item => Date.now() - item.created < 86400000),
  'highValue': (data) => data.filter(item => item.value > 1000),
};

function runFilter(filterName, data) {
  const filterFn = FILTERS[filterName];
  if (!filterFn) {
    throw new Error(`Unknown filter: ${filterName}`);
  }
  return filterFn(data);
}
```

**Explanation:** The `Function` constructor, which is equivalent to `eval()`, is replaced with a predefined filter registry. Users select from available filters by name rather than providing arbitrary code.

### JavaScript -- setTimeout with String

**Before (vulnerable):**
```javascript
app.post('/schedule', (req, res) => {
  const action = req.body.action;
  const delay = req.body.delay;
  setTimeout(action, delay);
  res.json({ status: 'scheduled' });
});
```

**After (fixed):**
```javascript
const ACTIONS = {
  'sendReport': sendReport,
  'cleanCache': cleanCache,
  'notifyUsers': notifyUsers,
};

app.post('/schedule', (req, res) => {
  const actionName = req.body.action;
  const delay = Math.min(Math.max(parseInt(req.body.delay, 10) || 0, 0), 3600000);
  const actionFn = ACTIONS[actionName];
  if (!actionFn) {
    return res.status(400).json({ error: 'Unknown action' });
  }
  setTimeout(actionFn, delay);
  res.json({ status: 'scheduled' });
});
```

**Explanation:** `setTimeout` with a string argument evaluates it as code (equivalent to `eval()`). The fix replaces the string argument with a function reference from a predefined lookup table. The delay is also validated and capped.

### Java -- ScriptEngine eval

**Before (vulnerable):**
```java
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;

public String evaluate(String expression) throws Exception {
    ScriptEngine engine = new ScriptEngineManager().getEngineByName("JavaScript");
    Object result = engine.eval(expression);
    return result.toString();
}
```

**After (fixed):**
```java
import javax.script.ScriptEngine;
import javax.script.ScriptEngineManager;
import javax.script.SimpleBindings;

public String evaluate(String expression) throws Exception {
    // Validate expression contains only safe characters
    if (!expression.matches("[0-9+\\-*/().\\s]+")) {
        throw new IllegalArgumentException("Invalid expression: only arithmetic operators allowed");
    }

    ScriptEngine engine = new ScriptEngineManager().getEngineByName("JavaScript");
    SimpleBindings bindings = new SimpleBindings();
    // No variables or functions exposed in bindings
    Object result = engine.eval(expression, bindings);
    return result.toString();
}
```

**Explanation:** Input validation restricts the expression to arithmetic characters only. An empty `SimpleBindings` prevents access to Java objects from the script. For production use, consider replacing ScriptEngine with a dedicated math expression library like `exp4j` or `mXparser`.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Code execution test**: Pass `__import__('os').system('id')` (Python) or `require('child_process').execSync('id')` (JavaScript) as input. Verify code is not executed.
2. **Object access test**: Pass `__builtins__` (Python) or `this.constructor` (JavaScript) as input. Verify internal objects are not accessible.
3. **Valid input test**: Pass legitimate input (e.g., `2 + 3 * 4` for math) and verify it still works correctly.

### Automated Test Pattern

```python
def test_code_injection_prevented():
    with pytest.raises((ValueError, SyntaxError)):
        safe_eval_expr("__import__('os').system('id')")

def test_valid_expression():
    assert safe_eval_expr("2 + 3 * 4") == 14

def test_function_calls_blocked():
    with pytest.raises(ValueError):
        safe_eval_expr("print('hello')")
```

### Semgrep Rules That Should Pass After Fix

```yaml
rules:
  - id: python-eval-injection
    patterns:
      - pattern-either:
          - pattern: eval($INPUT)
          - pattern: exec($INPUT)
      - pattern-not: ast.literal_eval($INPUT)
    message: "Dynamic code execution with potentially untrusted input"
    languages: [python]
    severity: ERROR
  - id: javascript-eval-injection
    patterns:
      - pattern-either:
          - pattern: eval($INPUT)
          - pattern: new Function($INPUT)
    message: "Dynamic code execution with potentially untrusted input"
    languages: [javascript]
    severity: ERROR
```

### Verifying Functionality is Preserved

- Verify that the intended functionality (math evaluation, dynamic dispatch, etc.) still works correctly with valid inputs.
- Test edge cases: empty strings, very large numbers, special characters.
- If the fix uses a library (mathjs, exp4j), verify it handles the required operations.

## Common Mistakes

1. **Replacing eval() with ast.literal_eval() when the input is not a literal.** `ast.literal_eval()` only handles literal values (strings, numbers, tuples, lists, dicts, booleans, None). It cannot evaluate expressions like `2 + 3`. Use a math parser library for arithmetic expressions.

2. **Using a blacklist to filter dangerous input.** Filtering keywords like `import`, `exec`, `system` is trivially bypassable (e.g., `__import__`, `getattr`, Unicode tricks). Use an allowlist approach or a safe parser.

3. **Sandboxing with restricted globals but not restricted builtins.** In Python, passing `{"__builtins__": {}}` to `eval()` can still be bypassed through object introspection (`().__class__.__bases__[0].__subclasses__()`). Do not rely on restricted globals for security.

4. **Using `vm.runInNewContext()` in Node.js as a sandbox.** The `vm` module is not a security mechanism. Code running in a `vm` context can escape to the host context. Use a proper sandbox like `isolated-vm` or a separate process/container.

5. **Replacing eval with a regex-based validator.** Regex validation of code is inherently fragile and cannot account for all bypass techniques. Use a parser-based approach.

6. **Not removing all instances.** If `eval()` is used in multiple places, fixing only the flagged instance leaves other entry points vulnerable. Use `Grep` to find all instances.

7. **Assuming template engines are safe by default.** Some template engines (Jinja2 without sandbox, Mako) allow arbitrary code execution in templates. If user input is used to construct templates, use the sandboxed mode.

8. **Confusing code injection with command injection.** CWE-94 (code injection) targets the application's programming language; CWE-78 (command injection) targets the OS shell. The fixes are different.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine the intent of eval/exec** | Flag for manual review. Provide the general recommendation to eliminate eval/exec and suggest alternatives. |
| **Dynamic code execution is a core feature** | If the application is a code playground, REPL, or similar, recommend sandboxed execution (Docker, WebAssembly, isolated-vm) rather than removing eval. Flag for architectural review. |
| **eval is used in a build script or development tool** | Development-time eval (e.g., in Webpack config, build scripts) is lower risk if not processing user input. Verify the input source and flag for review if it processes external data. |
| **Third-party library uses eval internally** | Note the library and version. Check if a newer version has removed the eval usage. Flag for review and consider alternative libraries. |
| **Multiple eval patterns with different intents** | Address each instance separately with the appropriate safe alternative. |

## Constraints

- **Preserve functionality**: The safe alternative must produce the same results for all valid inputs.
- **No execution**: Do not execute any code to test the fix.
- **Eliminate, do not restrict**: The preferred fix is to eliminate eval/exec entirely, not to restrict its input. Input validation is a last resort when no safe alternative exists.
- **Minimal diff**: Replace only the dangerous function call and its immediate context. Do not refactor unrelated code.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
