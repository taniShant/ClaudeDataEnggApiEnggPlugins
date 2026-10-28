---
name: cwe-079-xss
description: "CWE-79: Cross-Site Scripting (XSS) Remediation — Remediate Cross-Site Scripting (XSS) vulnerabilities by applying context-appropriate output encoding and escaping. This skill identifies where untrust"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-79: Cross-Site Scripting (XSS) Remediation
## Quick Start

This skill provides the fix pattern for CWE-079. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-079 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-79
- **CWE Name**: Improper Neutralization of Input During Web Page Generation ('Cross-site Scripting')
- **Severity**: High
- **OWASP Category**: A03:2021 - Injection

## Purpose

Remediate Cross-Site Scripting (XSS) vulnerabilities by applying context-appropriate output encoding and escaping. This skill identifies where untrusted data is inserted into HTML output without proper encoding and applies the correct escaping strategy based on the output context (HTML body, HTML attribute, JavaScript, URL, CSS). It covers framework-specific patterns for React (JSX auto-escaping and its bypass risks), Django (template autoescape), and Express.js (helmet, escape-html), as well as manual escaping for raw HTML output.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the XSS vulnerability.
  - `line_number` (integer, required): The 1-based line number of the vulnerable code.
  - `cwe_id` (string, required): Must be `CWE-79`.
  - `xss_type` (string, optional): `reflected`, `stored`, or `dom`. Helps determine fix strategy.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language (`python`, `java`, `javascript`, `typescript`). Auto-detected if not provided.
- **framework** (optional, string): Web framework in use (`react`, `django`, `express`, `flask`, `spring`). Auto-detected if not provided.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 50 lines around `vulnerability.line_number`.

2. **Detect the language, framework, and templating engine.**
   - Examine import statements, file extensions, and code patterns.
   - Identify the templating system: Jinja2, Django templates, JSX, EJS, Handlebars, Thymeleaf, raw HTML string construction, etc.

3. **Determine the output context.**
   - **HTML body context**: Untrusted data placed between HTML tags (e.g., `<div>USER_DATA</div>`).
   - **HTML attribute context**: Untrusted data in an attribute value (e.g., `<input value="USER_DATA">`).
   - **JavaScript context**: Untrusted data embedded inside a `<script>` block or an inline event handler.
   - **URL context**: Untrusted data used in `href`, `src`, or URL path/query parameters.
   - **CSS context**: Untrusted data in a `<style>` block or `style` attribute.

4. **Apply the context-appropriate fix.**
   - **HTML body context**: Apply HTML entity encoding (escape `<`, `>`, `&`, `"`, `'`).
   - **HTML attribute context**: Apply HTML attribute encoding and ensure the attribute value is quoted.
   - **JavaScript context**: Apply JavaScript string escaping or use JSON serialization. Avoid embedding untrusted data in `<script>` blocks; prefer data attributes or API calls.
   - **URL context**: Apply URL encoding (`encodeURIComponent` / `urllib.parse.quote`). For `href`/`src` attributes, validate the URL scheme against an allowlist (`http`, `https`) to prevent `javascript:` URLs.
   - **CSS context**: Apply CSS escaping or use allowlist validation for property values.

5. **Apply framework-specific fixes.**
   - **React/JSX**: JSX auto-escapes interpolated values in text and attribute contexts. If the vulnerability involves `dangerouslySetInnerHTML`, replace it with safe rendering (use a sanitization library like DOMPurify if HTML rendering is required, or render text content directly). Check for `href` attributes with user-controlled `javascript:` URLs.
   - **Django templates**: Ensure `{% autoescape on %}` is active (it is by default). Remove any `|safe` filters or `{% autoescape off %}` blocks unless the data has been explicitly sanitized. Use `|escape` filter when needed.
   - **Express.js**: Add the `helmet` middleware for security headers (including CSP). Use `escape-html` or a templating engine's built-in escaping for any data rendered into HTML responses. Avoid `res.send()` with unsanitized user input in HTML strings.

6. **Handle DOM-based XSS (if applicable).**
   - Identify dangerous sinks: `innerHTML`, `outerHTML`, `document.write()`, `eval()`, `setTimeout(string)`, `setInterval(string)`.
   - Replace `innerHTML` with `textContent` when HTML rendering is not needed.
   - If HTML rendering is required, use a sanitization library (DOMPurify for browsers, sanitize-html for Node.js).
   - Replace `eval()` and string-based `setTimeout`/`setInterval` with function references.

7. **Apply the edit.**
   - Use `Edit` to replace the vulnerable code with the escaped/encoded version.
   - Add necessary imports (e.g., `from markupsafe import escape`, `import escapeHtml from 'escape-html'`, `const helmet = require('helmet')`).
   - Preserve code formatting, indentation, and surrounding logic.

8. **Scan for similar patterns in the same file.**
   - Use `Grep` to find other instances of the same vulnerable pattern.
   - Apply the same fix to all instances.

9. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the fix is syntactically correct.
   - Confirm that no unescaped user input flows into HTML output.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "xss_type": "<string: reflected | stored | dom>",
  "output_context": "<string: html_body | html_attribute | javascript | url | css>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the vulnerable code>",
      "fixed_code": "<string: the escaped/encoded replacement>",
      "fix_type": "html_encoding | attribute_encoding | js_escaping | url_encoding | sanitization_library | safe_api_replacement"
    }
  ],
  "similar_patterns_fixed": "<integer: count of additional similar patterns fixed>",
  "imports_added": ["<string: any new import statements added>"],
  "middleware_added": ["<string: any middleware additions, e.g., helmet>"],
  "warnings": ["<string: any warnings about manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries have valid `fixed_code`.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

XSS occurs when untrusted data is included in web page output without proper encoding, allowing an attacker to inject script code that executes in the victim's browser.

### Detection Patterns

**HTML context -- raw string interpolation:**
```
# Python (Flask/raw):      return f"<div>{user_input}</div>"
# Python (Django):         {{ variable|safe }}
# Python (Jinja2):         {% autoescape false %}...{{ variable }}...{% endautoescape %}
# JavaScript (Express):    res.send('<div>' + userInput + '</div>')
# JavaScript (EJS):        <%- userInput %>   (unescaped output)
# JSX (React):             <div dangerouslySetInnerHTML={{__html: userInput}} />
```

**JavaScript context:**
```
# Inline scripts:          <script>var x = '${userInput}';</script>
# Event handlers:          <div onclick="doStuff('${userInput}')">
```

**URL context:**
```
# href attributes:         <a href="${userInput}">link</a>
# Potential javascript::   <a href="javascript:${userInput}">link</a>
```

**DOM-based sinks:**
```
# innerHTML:               element.innerHTML = userInput
# document.write:          document.write(userInput)
# eval:                    eval(userInput)
```

## Fix Pattern

The general fix is to apply context-appropriate output encoding so that untrusted data is treated as data, never as code, by the browser.

**Transformation principles:**
1. Identify where untrusted data enters the HTML output.
2. Determine the output context (HTML body, attribute, JavaScript, URL, CSS).
3. Apply the encoding/escaping function specific to that context.
4. For DOM-based XSS, replace dangerous sink APIs with safe alternatives.
5. Add security headers (Content-Security-Policy via helmet) as defense-in-depth.

## Language-Specific Examples

### HTML Body Context

**Before (vulnerable) -- Python Flask:**
```python
from flask import request

@app.route('/greet')
def greet():
    name = request.args.get('name', '')
    return f"<h1>Hello, {name}!</h1>"
```

**After (fixed) -- Python Flask:**
```python
from flask import request
from markupsafe import escape

@app.route('/greet')
def greet():
    name = request.args.get('name', '')
    return f"<h1>Hello, {escape(name)}!</h1>"
```

**Explanation:** The `escape()` function from `markupsafe` converts characters like `<`, `>`, `&`, `"`, and `'` into their HTML entity equivalents, preventing injected HTML/script tags from being interpreted by the browser.

### JavaScript Context

**Before (vulnerable) -- Express.js with EJS:**
```javascript
app.get('/profile', (req, res) => {
  const username = req.query.username;
  res.render('profile', { username });
});

// profile.ejs:
// <script>var user = '<%- username %>';</script>
```

**After (fixed) -- Express.js with EJS:**
```javascript
app.get('/profile', (req, res) => {
  const username = req.query.username;
  res.render('profile', { username });
});

// profile.ejs:
// <script>var user = JSON.parse('<%= JSON.stringify(username) %>');</script>
```

**Explanation:** The `<%-` (unescaped) tag is replaced with `<%=` (escaped). The value is JSON-serialized server-side and parsed client-side, ensuring special characters are properly escaped for the JavaScript context. Alternatively, pass data via a `data-*` attribute and read it with `dataset`:

```html
<div id="profile" data-username="<%= username %>"></div>
<script>var user = document.getElementById('profile').dataset.username;</script>
```

### URL Context

**Before (vulnerable):**
```javascript
app.get('/redirect', (req, res) => {
  const target = req.query.url;
  res.send(`<a href="${target}">Click here</a>`);
});
```

**After (fixed):**
```javascript
const escapeHtml = require('escape-html');

app.get('/redirect', (req, res) => {
  const target = req.query.url;
  // Validate URL scheme
  let safeUrl = '#';
  try {
    const parsed = new URL(target);
    if (['http:', 'https:'].includes(parsed.protocol)) {
      safeUrl = parsed.href;
    }
  } catch (e) {
    // Invalid URL, use default
  }
  res.send(`<a href="${escapeHtml(safeUrl)}">Click here</a>`);
});
```

**Explanation:** The URL is parsed and validated against an allowlist of safe schemes (`http:`, `https:`) to prevent `javascript:` and `data:` URLs. The output is also HTML-escaped for the attribute context.

### React/JSX -- dangerouslySetInnerHTML

**Before (vulnerable):**
```jsx
function Comment({ text }) {
  return <div dangerouslySetInnerHTML={{ __html: text }} />;
}
```

**After (fixed):**
```jsx
import DOMPurify from 'dompurify';

function Comment({ text }) {
  // If HTML rendering is required, sanitize first
  const sanitized = DOMPurify.sanitize(text);
  return <div dangerouslySetInnerHTML={{ __html: sanitized }} />;
}

// Or, if plain text is sufficient:
function Comment({ text }) {
  return <div>{text}</div>;
}
```

**Explanation:** React's JSX auto-escapes interpolated values, so `{text}` in JSX is safe by default. If HTML rendering is required, `dangerouslySetInnerHTML` must be paired with a sanitization library like DOMPurify. If plain text rendering is acceptable, remove `dangerouslySetInnerHTML` entirely.

### Django Templates -- |safe Filter

**Before (vulnerable):**
```html
<!-- Django template -->
<div class="bio">{{ user.bio|safe }}</div>
```

**After (fixed):**
```html
<!-- Django template -->
<div class="bio">{{ user.bio }}</div>
```

**Explanation:** Removing the `|safe` filter allows Django's autoescape system to encode HTML entities in `user.bio`. If the field legitimately contains HTML that must be rendered, sanitize it server-side before saving to the database using a library like `bleach`:

```python
import bleach
ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'a', 'p', 'br']
ALLOWED_ATTRS = {'a': ['href', 'title']}
user.bio = bleach.clean(raw_bio, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS)
user.save()
```

### Express.js -- Helmet Middleware

**Before (no CSP headers):**
```javascript
const express = require('express');
const app = express();
// No security headers configured
```

**After (defense-in-depth with helmet):**
```javascript
const express = require('express');
const helmet = require('helmet');
const app = express();
app.use(helmet());
```

**Explanation:** The `helmet` middleware sets security-related HTTP headers including `Content-Security-Policy`, `X-Content-Type-Options`, and `X-XSS-Protection`. This is defense-in-depth and should be combined with output encoding, not used as a replacement.

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Manual test with XSS payloads:**
   - Input: `<script>alert('XSS')</script>` -- should render as visible text, not execute.
   - Input: `"><img src=x onerror=alert('XSS')>` -- should not break out of attribute context.
   - Input: `javascript:alert('XSS')` -- should not execute when used in `href`.
   - Input: `' onmouseover='alert(1)` -- should not create a new event handler attribute.

2. **Automated test pattern:**
   ```python
   def test_xss_prevented(client):
       response = client.get('/greet?name=<script>alert(1)</script>')
       assert b'<script>' not in response.data
       assert b'&lt;script&gt;' in response.data
   ```

3. **Semgrep rules that should pass after fix:**
   ```yaml
   rules:
     - id: flask-xss-raw-html
       patterns:
         - pattern: |
             return f"...<$TAG>...{$VAR}...</$TAG>..."
         - pattern-not: |
             return f"...<$TAG>...{escape($VAR)}...</$TAG>..."
       message: "Potential XSS: unescaped variable in HTML response"
       languages: [python]
       severity: WARNING
   ```

### Verifying Functionality is Preserved

- Verify that normal text input displays correctly (no double-encoding).
- Verify that legitimate special characters (&, <, >, quotes) display correctly in the browser (as their visible characters, not HTML entities visible as raw text).
- Test with internationalized input (Unicode, RTL text, emoji).
- If HTML rendering was intentional (rich text editors), verify that sanitized HTML still renders the allowed tags.

## Common Mistakes

1. **Encoding for the wrong context.** HTML entity encoding does not protect against XSS in a JavaScript context. Each context requires its own encoding strategy. Applying HTML encoding inside a `<script>` block is insufficient.

2. **Double-encoding.** Applying `escape()` when the templating engine already auto-escapes leads to `&amp;lt;` being displayed instead of `<`. Understand what the framework already does before adding manual encoding.

3. **Blacklist-based sanitization.** Filtering specific tags or keywords (`<script>`, `javascript:`, `onerror`) is trivially bypassed. Use allowlist-based sanitization or context-appropriate encoding instead.

4. **Client-side-only sanitization.** Sanitizing input only in the browser (e.g., with JavaScript before submission) is useless because attackers can bypass the client. Always sanitize or encode on the server side (or at output time).

5. **Sanitizing on input instead of encoding on output.** While input validation is good defense-in-depth, the primary defense must be output encoding at the point where data is rendered into HTML. Data stored in the database may be used in multiple contexts, each requiring different encoding.

6. **Trusting data from the database.** Stored XSS occurs when data in the database was not sanitized at input time. All data rendered into HTML must be encoded regardless of its source.

7. **Forgetting `javascript:` URLs.** Even with HTML attribute encoding, a value like `javascript:alert(1)` in an `href` attribute will execute. Always validate URL schemes against an allowlist.

8. **Removing `|safe` in Django without checking if HTML rendering is needed.** If the field legitimately stores HTML (e.g., from a rich text editor), simply removing `|safe` will show raw HTML tags to users. In that case, sanitize the stored HTML server-side instead.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot determine output context** | Flag for manual review. Provide the general encoding guidance but do not apply an edit. |
| **Template file in unknown engine** | Identify the engine from file extension and configuration. If unrecognizable, flag for manual review. |
| **Mixed contexts in one expression** | Handle the most dangerous context first. If untrusted data appears in multiple contexts in the same line, apply all necessary encodings and flag for manual review. |
| **CSP header conflicts** | If existing CSP headers are present, do not overwrite them. Flag for manual review to merge policies. |
| **Framework not recognized** | Apply manual HTML entity encoding as a baseline and flag for framework-specific review. |

## Constraints

- **Preserve rendering intent**: If the original code intentionally renders HTML (rich text, markdown), use sanitization rather than escaping. Do not break intentional HTML rendering.
- **No execution**: Do not run the web application or open it in a browser to test.
- **No schema changes**: Do not alter database schemas or stored data.
- **Minimal diff**: Change only the vulnerable output point. Do not refactor the entire template unless required.
- **Defense-in-depth**: Recommend CSP headers and other security middleware in warnings, but the primary fix must be output encoding.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
