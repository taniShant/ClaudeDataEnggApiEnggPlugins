---
name: cwe-942-cors-policy
description: "CWE-942: Permissive Cross-domain Policy with Untrusted Domains Remediation — Remediate overly permissive CORS (Cross-Origin Resource Sharing) policies by restricting allowed origins to specific trusted domains. Overly permissiv"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-942: Permissive Cross-domain Policy with Untrusted Domains Remediation
## Quick Start

This skill provides the fix pattern for CWE-942. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-942 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-942
- **CWE Name**: Permissive Cross-domain Policy with Untrusted Domains
- **Severity**: High
- **OWASP Category**: A01:2021 - Broken Access Control

## Purpose

Remediate overly permissive CORS (Cross-Origin Resource Sharing) policies by restricting allowed origins to specific trusted domains. Overly permissive CORS policies allow any website to make requests to your API.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file.
  - `line_number` (integer, required): The 1-based line number.
  - `cwe_id` (string, required): Must be `CWE-942`.

## Steps

1. **Identify CORS configuration** that allows all origins.
2. **Replace with whitelist** of allowed origins.
3. **Add credential handling** properly.

## Output Format

```json
{
  "status": "success | partial | error",
  "file_path": "<string>",
  "changes": [
    {
      "line_number": "<integer>",
      "cors_policy": "string"
    }
  ],
  "error": "null or string"
}
```

## Vulnerable Pattern

```python
@app.after_request
def allow_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'  # VULNERABLE!
    return response
```

## Fix Pattern

Whitelist specific trusted origins instead of allowing all.

## Language-Specific Examples

### Python - Flask

**Before (vulnerable):**
```python
@app.after_request
def allow_cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'  # Allows anyone
    return response
```

**After (fixed):**
```python
ALLOWED_ORIGINS = [
    'https://www.example.com',
    'https://app.example.com'
]

@app.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin')
        if origin not in ALLOWED_ORIGINS:
            return '', 403
        return ''

@app.after_request
def apply_cors(response):
    origin = request.headers.get('Origin')
    if origin in ALLOWED_ORIGINS:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response
```

### JavaScript - Express

**Before (vulnerable):**
```javascript
app.use(cors());  // Allows all origins
```

**After (fixed):**
```javascript
const cors = require('cors');

const allowedOrigins = [
    'https://www.example.com',
    'https://app.example.com'
];

app.use(cors({
    origin: function (origin, callback) {
        if (!origin || allowedOrigins.includes(origin)) {
            callback(null, true);
        } else {
            callback(new Error('Not allowed by CORS'));
        }
    },
    credentials: true,
    methods: ['GET', 'POST'],
    allowedHeaders: ['Content-Type']
}));
```

## Constraints

- Use specific whitelisted origins.
- Never use `*` with credentials.
- Properly validate origins.
- Use HTTPS for all origins.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
