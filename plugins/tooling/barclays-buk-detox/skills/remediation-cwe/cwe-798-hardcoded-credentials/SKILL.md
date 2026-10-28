---
name: cwe-798-hardcoded-credentials
description: "CWE-798: Hardcoded Credentials Remediation — Remediate hardcoded credential vulnerabilities by extracting secrets (passwords, API keys, tokens, connection strings) from source code and replacing "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/remediation_cwe/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# CWE-798: Hardcoded Credentials Remediation
## Quick Start

This skill provides the fix pattern for CWE-798. It is loaded by the detox fix-agent during the remediation pipeline.

```
# Invoked automatically by detox-fix-agent when CWE-798 is classified in the finding.
# The agent loads this skill, applies the language-specific fix, and validates with Semgrep.
```



## CWE Information

- **CWE ID**: CWE-798
- **CWE Name**: Use of Hard-coded Credentials
- **Severity**: High
- **OWASP Category**: A07:2021 - Identification and Authentication Failures

## Purpose

Remediate hardcoded credential vulnerabilities by extracting secrets (passwords, API keys, tokens, connection strings) from source code and replacing them with references to environment variables or a secrets manager. This skill identifies hardcoded credentials in source code, configuration files, and infrastructure definitions, replaces them with secure retrieval patterns, sets up the supporting infrastructure (`.env` files, `.gitignore` updates), and ensures that the credentials are not retained in version control history. It covers detection patterns across multiple languages and replacement using `os.environ` (Python), `process.env` (Node.js), `System.getenv` (Java), `.env` file setup, and secrets manager integration patterns.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the file containing the hardcoded credential.
  - `line_number` (integer, required): The 1-based line number of the hardcoded credential.
  - `cwe_id` (string, required): Must be `CWE-798`.
  - `code_snippet` (string, optional): The flagged code snippet.
  - `credential_type` (string, optional): Type of credential (`password`, `api_key`, `token`, `connection_string`, `private_key`, `secret_key`). Auto-detected if not provided.
  - `context` (object, optional): Output from the `code_context_analyzer` skill.
- **repo_root** (optional, string): Absolute path to the repository root. Defaults to the current working directory.
- **language** (optional, string): Programming language. Auto-detected if not provided.
- **secrets_backend** (optional, string): Preferred secrets backend (`env_vars`, `dotenv`, `aws_secrets_manager`, `azure_key_vault`, `hashicorp_vault`, `gcp_secret_manager`). Defaults to `env_vars`.

## Steps

1. **Read the vulnerable file and surrounding context.**
   - Use `Read` to open the file at `vulnerability.file_path`.
   - If `vulnerability.context` is provided, use it. Otherwise, read +/- 30 lines around `vulnerability.line_number`.

2. **Identify the hardcoded credential.**
   - Locate the exact string literal that contains the credential.
   - Determine the credential type: password, API key, token, connection string, private key, secret key, database URL, etc.
   - Identify how the credential is used (authentication call, database connection, HTTP header, etc.).

3. **Determine the appropriate environment variable name.**
   - Derive a descriptive, uppercase, underscore-separated name from the context:
     - Database password: `DB_PASSWORD` or `DATABASE_PASSWORD`.
     - API key for a service: `<SERVICE_NAME>_API_KEY` (e.g., `STRIPE_API_KEY`).
     - JWT secret: `JWT_SECRET` or `JWT_SECRET_KEY`.
     - Connection string: `DATABASE_URL` or `<SERVICE>_CONNECTION_STRING`.
   - Check if an environment variable name is already used elsewhere in the codebase for the same purpose using `Grep`.

4. **Replace the hardcoded credential with environment variable access.**
   - **Python**: Replace with `os.environ["VAR_NAME"]` (raises `KeyError` if missing) or `os.environ.get("VAR_NAME")` (returns `None` if missing). Use `os.environ["VAR_NAME"]` for required credentials.
   - **JavaScript/Node.js**: Replace with `process.env.VAR_NAME`. Add a startup check to verify required variables are set.
   - **Java**: Replace with `System.getenv("VAR_NAME")`. Add a null check.
   - **Configuration files (YAML, JSON, TOML, .properties)**: Replace the literal value with a placeholder or reference pattern appropriate to the framework (e.g., `${VAR_NAME}` for Spring, `<%= ENV['VAR_NAME'] %>` for ERB).

5. **Add necessary imports.**
   - Python: Add `import os` if not already imported.
   - Node.js: If using `dotenv`, add `require('dotenv').config()` or `import 'dotenv/config'` at the application entry point.
   - Java: No import needed for `System.getenv()`.

6. **Set up the .env file (if applicable).**
   - Check if a `.env` file exists at the repo root using `Glob`.
   - If it exists, use `Read` to check its contents, then use `Edit` to add the new variable with a placeholder value.
   - If it does not exist and the project uses a `.env`-based workflow (evidence: `dotenv` dependency, existing `.env.example`), create a `.env.example` file with the variable name and a placeholder.
   - **Never write the actual credential value to a `.env` file that will be committed.** Use a placeholder like `your_<credential_type>_here`.

7. **Update .gitignore.**
   - Use `Read` to check the `.gitignore` file at the repo root.
   - If `.env` is not listed, use `Edit` to add it.
   - Also ensure patterns like `*.pem`, `*.key`, and other secret file types are in `.gitignore` if relevant.

8. **Scan for similar patterns in the codebase.**
   - Use `Grep` to search the repository for other hardcoded credentials of the same type.
   - Common patterns to search for:
     - String literals matching the credential value.
     - Variable names like `password`, `secret`, `api_key`, `token`, `auth`, `credential` assigned to string literals.
   - Report all findings and apply the same fix pattern.

9. **Verify the fix.**
   - Use `Read` to re-read the modified file and confirm the credential is no longer hardcoded.
   - Confirm that the environment variable access is syntactically correct.
   - Confirm that `.gitignore` includes `.env`.

10. **Flag for credential rotation.**
    - Warn that the previously hardcoded credential should be considered compromised and must be rotated (a new value should be generated).
    - This is especially critical if the repository is public or has been shared.

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "file_path": "<string: path to the modified file>",
  "credential_type": "<string: password | api_key | token | connection_string | private_key | secret_key>",
  "env_var_name": "<string: the environment variable name>",
  "changes": [
    {
      "line_number": "<integer: original line number>",
      "original_code": "<string: the code with hardcoded credential, REDACTED>",
      "fixed_code": "<string: the replacement using env var>",
      "fix_type": "env_var | secrets_manager | config_placeholder"
    }
  ],
  "similar_patterns_found": "<integer: count of other hardcoded credentials found in the codebase>",
  "imports_added": ["<string: any new import statements added>"],
  "gitignore_updated": "<boolean: whether .gitignore was modified>",
  "env_example_updated": "<boolean: whether .env.example was created or updated>",
  "warnings": [
    "Credential has been exposed in source code and should be rotated immediately.",
    "<string: additional warnings>"
  ],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and the credential is replaced with an environment variable reference. `original_code` in the output MUST have the actual credential value redacted.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Vulnerable Pattern

Hardcoded credentials occur when sensitive authentication data is embedded directly in source code, configuration files, or infrastructure definitions as string literals. This exposes the credentials to anyone with read access to the code, including version control history, build artifacts, and backup systems.

### Detection Patterns

**Direct assignment to obvious variable names:**
```
# Python:       password = "SuperSecret123!"
# Python:       API_KEY = "sk-abc123def456"
# Python:       db_url = "postgresql://user:password@host:5432/db"
# JavaScript:   const apiKey = 'sk-abc123def456';
# JavaScript:   const dbPassword = "SuperSecret123!";
# Java:         String password = "SuperSecret123!";
# Java:         private static final String API_KEY = "sk-abc123def456";
```

**Credentials in function calls:**
```
# Python:       conn = psycopg2.connect(password="SuperSecret123!")
# Python:       requests.get(url, headers={"Authorization": "Bearer sk-abc123"})
# JavaScript:   mongoose.connect('mongodb://user:pass@host/db')
# Java:         DriverManager.getConnection(url, user, "SuperSecret123!")
```

**Credentials in configuration files:**
```yaml
# YAML:         database_password: SuperSecret123!
# JSON:         {"api_key": "sk-abc123def456"}
# .properties:  spring.datasource.password=SuperSecret123!
# TOML:         secret_key = "SuperSecret123!"
```

**Regex detection patterns:**
```
# API keys:          (?i)(api[_-]?key|apikey)\s*[:=]\s*['"][a-zA-Z0-9_\-]{16,}['"]
# Passwords:         (?i)(password|passwd|pwd)\s*[:=]\s*['"][^'"]{4,}['"]
# Tokens:            (?i)(token|secret|auth)\s*[:=]\s*['"][a-zA-Z0-9_\-\.]{16,}['"]
# Connection strings: (?i)(mysql|postgres|mongodb|redis):\/\/[^:]+:[^@]+@
# AWS keys:          AKIA[0-9A-Z]{16}
# Private keys:      -----BEGIN (RSA |EC |DSA )?PRIVATE KEY-----
# JWT secrets:       (?i)jwt[_-]?secret\s*[:=]\s*['"][^'"]{8,}['"]
```

**False positive indicators (these are typically NOT hardcoded credentials):**
```
# Empty strings:     password = ""
# Placeholder:       password = "CHANGE_ME"
# Env var access:    password = os.environ["DB_PASSWORD"]
# Test fixtures:     password = "test_password"  (in test files only)
# Documentation:     # Example: password = "your_password_here"
```

## Fix Pattern

The general fix is to extract the credential from source code and replace it with a reference to an external secret store. The credential value is then provided at runtime through environment variables, a secrets manager, or an encrypted configuration system.

**Transformation steps:**
1. Identify the hardcoded credential and its context.
2. Choose a descriptive environment variable name.
3. Replace the literal string with environment variable access.
4. Add a validation check to fail fast if the variable is not set.
5. Set up `.env` files and `.gitignore` for local development.
6. Flag the credential for rotation.

## Language-Specific Examples

### Python -- os.environ

**Before (vulnerable):**
```python
import psycopg2

def get_connection():
    return psycopg2.connect(
        host="db.example.com",
        database="myapp",
        user="admin",
        password="SuperSecret123!"
    )
```

**After (fixed):**
```python
import os
import psycopg2

def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )
```

**Explanation:** All connection parameters are moved to environment variables. `os.environ["VAR"]` is used (not `os.environ.get("VAR")`) so that a missing variable raises a `KeyError` at startup rather than causing a silent authentication failure.

### Python -- With validation and dotenv

**After (fixed, with dotenv for local development):**
```python
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()  # Load .env file for local development

REQUIRED_ENV_VARS = ["DB_HOST", "DB_NAME", "DB_USER", "DB_PASSWORD"]
missing = [var for var in REQUIRED_ENV_VARS if var not in os.environ]
if missing:
    raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def get_connection():
    return psycopg2.connect(
        host=os.environ["DB_HOST"],
        database=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )
```

**.env file (never committed):**
```
DB_HOST=db.example.com
DB_NAME=myapp
DB_USER=admin
DB_PASSWORD=your_database_password_here
```

**.env.example (committed, for documentation):**
```
DB_HOST=localhost
DB_NAME=myapp
DB_USER=admin
DB_PASSWORD=your_database_password_here
```

### JavaScript/Node.js -- process.env

**Before (vulnerable):**
```javascript
const stripe = require('stripe')('sk_live_abc123def456ghi789');

app.post('/charge', async (req, res) => {
  const charge = await stripe.charges.create({
    amount: req.body.amount,
    currency: 'usd',
    source: req.body.token,
  });
  res.json(charge);
});
```

**After (fixed):**
```javascript
require('dotenv').config();

if (!process.env.STRIPE_SECRET_KEY) {
  throw new Error('STRIPE_SECRET_KEY environment variable is required');
}

const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);

app.post('/charge', async (req, res) => {
  const charge = await stripe.charges.create({
    amount: req.body.amount,
    currency: 'usd',
    source: req.body.token,
  });
  res.json(charge);
});
```

**Explanation:** The Stripe API key is moved to `process.env.STRIPE_SECRET_KEY`. A startup check ensures the variable is set, failing fast with a clear error message rather than making API calls with `undefined`. The `dotenv` package loads variables from a `.env` file during local development.

### Java -- System.getenv

**Before (vulnerable):**
```java
public class DatabaseConfig {
    private static final String DB_URL = "jdbc:postgresql://db.example.com:5432/myapp";
    private static final String DB_USER = "admin";
    private static final String DB_PASSWORD = "SuperSecret123!";

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
    }
}
```

**After (fixed):**
```java
public class DatabaseConfig {
    private static final String DB_URL = requireEnv("DB_URL");
    private static final String DB_USER = requireEnv("DB_USER");
    private static final String DB_PASSWORD = requireEnv("DB_PASSWORD");

    private static String requireEnv(String name) {
        String value = System.getenv(name);
        if (value == null || value.isEmpty()) {
            throw new IllegalStateException("Required environment variable not set: " + name);
        }
        return value;
    }

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(DB_URL, DB_USER, DB_PASSWORD);
    }
}
```

**Explanation:** The hardcoded values are replaced with `System.getenv()` calls wrapped in a `requireEnv` helper that throws an `IllegalStateException` at class load time if a variable is missing. This fails fast with a clear error message.

### Configuration Files -- YAML (Spring Boot)

**Before (vulnerable):**
```yaml
# application.yml
spring:
  datasource:
    url: jdbc:postgresql://db.example.com:5432/myapp
    username: admin
    password: SuperSecret123!
```

**After (fixed):**
```yaml
# application.yml
spring:
  datasource:
    url: ${DB_URL}
    username: ${DB_USER}
    password: ${DB_PASSWORD}
```

**Explanation:** Spring Boot natively supports `${ENV_VAR}` syntax in YAML configuration files, resolving them from environment variables at runtime.

### Connection Strings

**Before (vulnerable):**
```python
DATABASE_URL = "postgresql://admin:SuperSecret123!@db.example.com:5432/myapp"
```

**After (fixed):**
```python
import os

DATABASE_URL = os.environ["DATABASE_URL"]
```

**.env:**
```
DATABASE_URL=postgresql://admin:your_password_here@db.example.com:5432/myapp
```

**Explanation:** The entire connection string is moved to an environment variable. This is preferred over decomposing the connection string into individual components when the consuming library expects a URL-format string. Note that the entire URL, including the host, should be externalized since it may differ across environments.

### .gitignore Setup

The following entries should be present in `.gitignore`:

```gitignore
# Environment files
.env
.env.local
.env.*.local
.env.production
.env.staging

# Secret files
*.pem
*.key
*.p12
*.jks
*.keystore

# IDE-specific files that may cache secrets
.idea/dataSources.xml
.vscode/launch.json
```

## Testing Guidance

### Verifying the Fix Eliminates the Vulnerability

1. **Static scan verification:**
   - Run the same SAST tool that detected the original finding. The hardcoded credential finding should no longer appear.
   - Use `Grep` to search for the credential value in the codebase -- it should return zero matches.

2. **Environment variable verification:**
   ```bash
   # Verify the application fails clearly without the variable:
   unset DB_PASSWORD
   python app.py  # Should raise EnvironmentError, not silently use a default
   ```

3. **Semgrep rules that should pass after fix:**
   ```yaml
   rules:
     - id: hardcoded-password
       patterns:
         - pattern: $VAR = "..."
         - metavariable-regex:
             metavariable: $VAR
             regex: (?i)(password|passwd|pwd|secret|token|api_key)
         - pattern-not: $VAR = os.environ[...]
         - pattern-not: $VAR = os.environ.get(...)
       message: "Hardcoded credential in variable assignment"
       languages: [python]
       severity: ERROR
   ```

### Verifying Functionality is Preserved

- Set the environment variable to the credential value and confirm the application works as before.
- Verify that the application starts correctly in all environments (development, staging, production) with the environment variables set.
- Confirm that error messages for missing variables are clear and do not leak the expected credential format.

### Verifying .gitignore

```bash
# Confirm .env is ignored:
git check-ignore .env  # Should output ".env"
```

## Common Mistakes

1. **Replacing the credential with a default value.** `os.environ.get("DB_PASSWORD", "SuperSecret123!")` still contains the hardcoded credential as a default. Never use the actual credential as a fallback value. Use `None` or raise an error.

2. **Committing the .env file.** The `.env` file contains the actual credential values and must never be committed. Always add `.env` to `.gitignore` before creating it. If it was already committed, it must be removed from version control history (see warning below).

3. **Not rotating the exposed credential.** Once a credential has been in source code (especially if pushed to a remote repository), it must be considered compromised. Generate a new credential and update the environment variable.

4. **Hardcoding in a different location.** Moving the credential from `app.py` to `config.py` as a string literal does not fix the vulnerability. It must be externalized to an environment variable or secrets manager.

5. **Using a .env file in production.** `.env` files via `dotenv` are suitable for local development only. In production, use the deployment platform's native environment variable configuration (e.g., Docker secrets, Kubernetes secrets, cloud provider secret management).

6. **Incomplete removal from git history.** If the credential was previously committed, it exists in git history even after the fix commit. Use `git filter-branch` or BFG Repo Cleaner to remove it from history, or consider the credential permanently compromised and rotate it.

7. **Logging the credential at startup.** Adding a validation check like `print(f"Using password: {os.environ['DB_PASSWORD']}")` to verify the fix works will log the credential. Never log credential values.

8. **Using weak or predictable environment variable names.** Do not use names like `X` or `VAR1`. Use descriptive names (`DB_PASSWORD`, `STRIPE_API_KEY`) so that operators know what each variable is for.

9. **Not handling the credential value in test environments.** Test configurations should use separate, non-production credentials. Provide a `.env.test` or test-specific environment configuration.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **File not found** | Return error JSON with `"error": "File not found: <path>"`. Do not retry. |
| **Cannot identify the credential** | If the flagged code does not appear to contain a credential (possible false positive), note this in warnings and flag for manual review. |
| **Credential is in a binary file** | Return error JSON. Binary files require different handling (e.g., encrypted config files, keystores). Flag for manual review. |
| **Credential is in git history** | Warn that the credential exists in git history and recommend rotation plus history cleaning. The skill only fixes the current source code. |
| **Multiple credentials in one file** | Address each credential separately, deriving appropriate environment variable names for each. |
| **Credential is shared across files** | Fix all files that reference the credential to use the same environment variable name. Use `Grep` to find all occurrences. |
| **.gitignore does not exist** | Create a new `.gitignore` file with the `.env` entry and common secret file patterns. |
| **Cannot determine credential type** | Use a generic environment variable name (e.g., `APP_SECRET_1`) and flag for manual review to assign a better name. |

## Constraints

- **Never output actual credential values.** All credential values in the output JSON must be redacted (replaced with `[REDACTED]`). The skill must never echo, log, or return the actual secret.
- **No execution**: Do not execute the application or connect to any external services to verify the credential works.
- **No history rewriting**: The skill modifies only the current source files. Git history cleaning is a separate, manual operation that requires careful coordination and is flagged as a recommendation only.
- **Preserve functionality**: The application must work identically when the environment variable is set to the credential value.
- **Minimal diff**: Change only the credential reference and supporting infrastructure (imports, .gitignore). Do not refactor surrounding code.
- **.env.example only**: If creating a `.env.example` file, use only placeholder values, never actual credentials.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes and updating `.gitignore`. Do not use `Bash` to run code or tests.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
