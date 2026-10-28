---
name: cwe-601-open-redirect
description: "CWE-601: URL Redirection to Untrusted Site (Open Redirect) Remediation — Remediate open redirect vulnerabilities by validating and sanitizing redirect URLs. Open redirect vulnerabilities allow attackers to redirect users to"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-601: URL Redirection to Untrusted Site (Open Redirect) Remediation
## Quick Start

This skill provides the fix pattern for CWE-601. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-601 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-601
- **CWE Name**: URL Redirection to Untrusted Site ('Open Redirect')
- **Severity**: Medium
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate open redirect vulnerabilities by validating and sanitizing redirect URLs. Open redirect vulnerabilities allow attackers to redirect users to malicious sites, enabling phishing attacks and social engineering.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-601`.

## Steps

1. **Identify redirect operations** that use user-controlled URLs.
   - Look for `redirect()`, `window.location`, etc.

2. **Add URL validation.**
   - Whitelist allowed redirect domains.
   - Or validate that URL is relative (starts with `/` or `./`).
   - Reject URLs with different protocol or domain.

3. **Apply the edit.**
   - Use `Edit` to add URL validation before redirect.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "validation_type": "whitelist | relative_url | domain_check"
    }
  ],
  "redirects_secured": "<integer>",
  "warnings": ["<string: manual review needed>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

## Vulnerable Pattern

```python
@app.route('/redirect')
def redirect_user():
    url = request.args.get('url')
    return redirect(url)  # VULNERABLE: no validation!
```

## Fix Pattern

1. Validate that URL is from a trusted domain.
2. Or validate that URL is relative (local).
3. Reject invalid URLs.

## Language-Specific Examples

### Python - Flask

**Before (vulnerable):**
```python
@app.route('/redirect')
def redirect_user():
    url = request.args.get('url')
    return redirect(url)  # Any attacker URL accepted
```

**After (fixed):**
```python
from urllib.parse import urlparse, urljoin

@app.route('/redirect')
def redirect_user():
    url = request.args.get('url', '/')

    # Validate that URL is relative (starts with /)
    if not url.startswith('/'):
        # Or check against whitelist
        return redirect('/')

    # Additional check: ensure no protocol/domain in relative URL
    parsed = urlparse(url)
    if parsed.scheme or parsed.netloc:
        return redirect('/')

    return redirect(url)
```

### Java - Spring Boot

**Before (vulnerable):**
```java
@GetMapping("/redirect")
public String redirect(@RequestParam String url) {
    return "redirect:" + url;  // No validation!
}
```

**After (fixed):**
```java
@GetMapping("/redirect")
public String redirect(@RequestParam String url) {
    if (url == null || !isValidRedirectUrl(url)) {
        return "redirect:/";
    }
    return "redirect:" + url;
}

private boolean isValidRedirectUrl(String url) {
    try {
        URI uri = new URI(url);
        // Allow relative URLs only
        return !uri.isAbsolute() && url.startsWith("/");
    } catch (URISyntaxException e) {
        return false;
    }
}
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
app.get('/redirect', (req, res) => {
    const url = req.query.url;
    res.redirect(url);  // No validation!
});
```

**After (fixed):**
```javascript
function isValidRedirectUrl(url) {
    if (!url) return false;

    // Only allow relative URLs
    if (url.startsWith('http://') || url.startsWith('https://')) {
        return false;
    }

    // Only allow URLs starting with /
    if (!url.startsWith('/')) {
        return false;
    }

    return true;
}

app.get('/redirect', (req, res) => {
    let url = req.query.url || '/';

    if (!isValidRedirectUrl(url)) {
        url = '/';
    }

    res.redirect(url);
});
```

## Testing Guidance

1. **Test relative URL**: `/home` should redirect to `/home`.
2. **Test absolute URL**: `https://attacker.com` should be rejected (redirect to `/`).
3. **Test protocol-relative URL**: `//attacker.com` should be rejected.
4. **Test encoded URL**: `%2F%2fattacker.com` should be rejected.

## Common Mistakes

1. **Only checking protocol** - `//attacker.com` bypasses protocol check.
2. **Not checking domain** - if allowing absolute URLs.
3. **Decoding encoded URLs** - may bypass validation.
4. **Whitelisting is incomplete** - missed allowed domains.

## Constraints

- Relative URLs only (recommended).
- Or strict whitelist of allowed domains.
- Reject URLs with different protocol or domain.
## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
