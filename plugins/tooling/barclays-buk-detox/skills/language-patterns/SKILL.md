---
name: language-patterns
description: Language-specific security fix patterns for Python, Java, JavaScript, TypeScript, C#, and Go
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Language-Specific Security Fix Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provides language-specific security fix patterns and framework best practices for applying CWE remediations. These patterns are composed with CWE-specific skills to translate generic vulnerability fixes into idiomatic, framework-native secure code.

---

## Python Fix Patterns

### Detection
- File extensions: `.py`
- Frameworks: Django, Flask, FastAPI, SQLAlchemy, psycopg2
- Version detection: `pyproject.toml`, `setup.cfg`, `requirements.txt`

### CSRF Protection (Django) — CWE-352
```python
# Ensure CsrfViewMiddleware in MIDDLEWARE
# Templates: {% csrf_token %}
# AJAX: X-CSRFToken header from cookie
# API views: @csrf_exempt ONLY for token-auth endpoints
```

### SQL Injection (SQLAlchemy) — CWE-89
```python
from sqlalchemy import text
# NEVER: conn.execute("SELECT * FROM t WHERE x = '" + val + "'")
# CORRECT: conn.execute(text("SELECT * FROM t WHERE x = :val"), {"val": val})
```

### SQL Injection (psycopg2) — CWE-89
```python
# NEVER: cursor.execute(f"SELECT * FROM t WHERE x = '{val}'")
# CORRECT: cursor.execute("SELECT * FROM t WHERE x = %s", (val,))
```

### XSS (Django Templates) — CWE-79
```python
# Django autoescapes by default. The vulnerability is using |safe filter:
# NEVER: {{ user_input|safe }}
# CORRECT: {{ user_input }}  (auto-escaped)
# If HTML needed: use bleach.clean() then |safe
```

### XSS (Flask/Jinja2) — CWE-79
```python
# Jinja2 autoescapes in Flask. Vulnerability is:
# NEVER: Markup(user_input) or |safe filter
# CORRECT: {{ user_input }} (auto-escaped)
# Manual: markupsafe.escape(user_input)
```

### Path Traversal — CWE-22
```python
import os
base = os.path.realpath(SAFE_DIR)
requested = os.path.realpath(os.path.join(base, user_path))
if not requested.startswith(base + os.sep):
    raise ValueError("Access denied")
```

### Command Injection — CWE-78
```python
import subprocess, shlex
# NEVER: os.system(f"cmd {user_input}")
# NEVER: subprocess.call(f"cmd {user_input}", shell=True)
# CORRECT: subprocess.run(["cmd", user_input], shell=False, check=True)
```

### Deserialization — CWE-502
```python
# NEVER: pickle.loads(untrusted_data)
# CORRECT: json.loads(untrusted_data)
# If pickle needed: verify HMAC signature first
```

### Hardcoded Credentials — CWE-798
```python
import os
# NEVER: password = "secret123"
# CORRECT: password = os.environ["DB_PASSWORD"]
# BETTER: use vault client or secrets manager SDK
```

### Weak Crypto — CWE-327
```python
# NEVER: hashlib.md5(), hashlib.sha1() for security
# Password hashing: bcrypt.hashpw() or argon2
# Data integrity: hashlib.sha256()
# Encryption: cryptography.fernet.Fernet or AES-GCM via cryptography lib
```

### Logging Sensitive Data — CWE-532
```python
# NEVER: logger.info(f"Login {user} password={password}")
# CORRECT: logger.info(f"Login attempt for user={user}")
# Use structured logging with explicit safe fields
```

### SSL Verification — CWE-295
```python
# NEVER: requests.get(url, verify=False)
# CORRECT: requests.get(url)  # verify=True is default
# For custom CA: requests.get(url, verify="/path/to/ca-bundle.crt")
```

---

## Java Fix Patterns

### Detection
- File extensions: `.java`
- Frameworks: Spring Boot, Jakarta EE, JDBC, Hibernate
- Build: `pom.xml` (Maven), `build.gradle` (Gradle)

### SQL Injection (JDBC) — CWE-89
```java
// NEVER: stmt.executeQuery("SELECT * FROM t WHERE x = '" + val + "'")
// CORRECT:
PreparedStatement ps = conn.prepareStatement("SELECT * FROM t WHERE x = ?");
ps.setString(1, val);
ResultSet rs = ps.executeQuery();
```

### SQL Injection (Spring JPA) — CWE-89
```java
// NEVER: em.createQuery("SELECT u FROM User u WHERE u.name = '" + name + "'")
// CORRECT:
TypedQuery<User> q = em.createQuery("SELECT u FROM User u WHERE u.name = :name", User.class);
q.setParameter("name", name);
```

### XSS (Spring MVC) — CWE-79
```java
// Thymeleaf auto-escapes with th:text
// NEVER: th:utext="${userInput}"  (unescaped)
// CORRECT: th:text="${userInput}"  (escaped)
// Manual: HtmlUtils.htmlEscape(userInput)
```

### Command Injection — CWE-78
```java
// NEVER: Runtime.getRuntime().exec("cmd " + userInput)
// CORRECT:
ProcessBuilder pb = new ProcessBuilder("cmd", userInput);
pb.redirectErrorStream(true);
Process p = pb.start();
```

### XXE — CWE-611
```java
DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
dbf.setFeature("http://xml.org/sax/features/external-general-entities", false);
dbf.setFeature("http://xml.org/sax/features/external-parameter-entities", false);
dbf.setXIncludeAware(false);
dbf.setExpandEntityReferences(false);
```

### Deserialization — CWE-502
```java
// Use ObjectInputFilter (JEP 290) for Java 9+:
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter("!*");
ois.setObjectInputFilter(filter);
// Better: Use JSON (Jackson/Gson) instead of Java serialization
```

### Path Traversal — CWE-22
```java
Path base = Paths.get(SAFE_DIR).toRealPath();
Path requested = base.resolve(userInput).normalize().toRealPath();
if (!requested.startsWith(base)) {
    throw new SecurityException("Path traversal");
}
```

### CSRF (Spring Security) — CWE-352
```java
// Spring Security enables CSRF by default. Don't disable it:
// NEVER: http.csrf().disable()
// If disabling for stateless API: ensure token-based auth is in place
```

### Weak Crypto — CWE-327
```java
// NEVER: Cipher.getInstance("DES"), MessageDigest.getInstance("MD5")
// CORRECT:
Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
MessageDigest md = MessageDigest.getInstance("SHA-256");
// Passwords: BCrypt.hashpw(password, BCrypt.gensalt(12))
```

---

## JavaScript Fix Patterns

### Detection
- File extensions: `.js`, `.mjs`, `.cjs`
- Frameworks: Express, Node.js, React, Next.js
- Package manager: `package.json`

### SQL Injection (pg) — CWE-89
```javascript
// NEVER: pool.query(`SELECT * FROM t WHERE x = '${val}'`)
// CORRECT: pool.query('SELECT * FROM t WHERE x = $1', [val])
```

### SQL Injection (mysql2) — CWE-89
```javascript
// NEVER: connection.execute("SELECT * FROM t WHERE x = '" + val + "'")
// CORRECT: connection.execute('SELECT * FROM t WHERE x = ?', [val])
```

### XSS (Express) — CWE-79
```javascript
// NEVER: res.send(`<div>${userInput}</div>`)
// CORRECT:
const escapeHtml = require('escape-html');
res.send(`<div>${escapeHtml(userInput)}</div>`);
// Or use template engine with auto-escaping (EJS with <%=, not <%-
```

### XSS (React) — CWE-79
```javascript
// React auto-escapes JSX interpolation: {userInput} is safe
// NEVER: dangerouslySetInnerHTML={{__html: userInput}}
// If HTML needed: use DOMPurify.sanitize(userInput) first
```

### Command Injection — CWE-78
```javascript
// NEVER: exec(`cmd ${userInput}`)
// CORRECT:
const { execFile } = require('child_process');
execFile('cmd', [userInput], (err, stdout) => { ... });
```

### Path Traversal — CWE-22
```javascript
const path = require('path');
const base = path.resolve(SAFE_DIR);
const requested = path.resolve(base, userInput);
if (!requested.startsWith(base + path.sep)) {
    throw new Error('Path traversal');
}
```

### Prototype Pollution — Related to CWE-1321
```javascript
// NEVER: Object.assign(target, JSON.parse(userInput))
// CORRECT: Use Object.create(null) as base, or validate keys
// Block __proto__, constructor, prototype keys
```

### SSRF — CWE-918
```javascript
const { URL } = require('url');
const ALLOWED = new Set(['api.example.com']);
const parsed = new URL(userUrl);
if (!ALLOWED.has(parsed.hostname)) {
    throw new Error('URL not allowed');
}
```

---

## TypeScript Fix Patterns

### Detection
- File extensions: `.ts`, `.tsx`
- Frameworks: NestJS, Express, Angular, Next.js
- Config: `tsconfig.json`

Same patterns as JavaScript apply, with additional type safety:

### Type-Safe Input Validation
```typescript
// Use Zod, io-ts, or class-validator for runtime validation
import { z } from 'zod';
const UserInput = z.object({
    name: z.string().max(100),
    email: z.string().email(),
});
const validated = UserInput.parse(req.body);
```

### NestJS Guards — CWE-862
```typescript
@UseGuards(AuthGuard, RolesGuard)
@Roles('admin')
@Get('/admin/users')
async getUsers() { ... }
```

---

## C# Fix Patterns

### Detection
- File extensions: `.cs`
- Frameworks: ASP.NET Core, Entity Framework
- Project: `*.csproj`

### SQL Injection (EF Core) — CWE-89
```csharp
// NEVER: context.Users.FromSqlRaw($"SELECT * FROM Users WHERE Name = '{name}'")
// CORRECT: context.Users.FromSqlInterpolated($"SELECT * FROM Users WHERE Name = {name}")
// Or: context.Users.Where(u => u.Name == name) (LINQ is always safe)
```

### SQL Injection (ADO.NET) — CWE-89
```csharp
// CORRECT:
using var cmd = new SqlCommand("SELECT * FROM Users WHERE Name = @name", conn);
cmd.Parameters.AddWithValue("@name", name);
```

### XSS (Razor) — CWE-79
```csharp
// Razor auto-encodes @Model.Property
// NEVER: @Html.Raw(userInput)
// If HTML needed: use HtmlSanitizer library first
```

### Path Traversal — CWE-22
```csharp
var basePath = Path.GetFullPath(SAFE_DIR);
var fullPath = Path.GetFullPath(Path.Combine(basePath, userInput));
if (!fullPath.StartsWith(basePath + Path.DirectorySeparatorChar))
    throw new UnauthorizedAccessException("Path traversal");
```

---

## Go Fix Patterns

### Detection
- File extensions: `.go`
- Modules: `go.mod`
- Frameworks: net/http, gin, echo, fiber

### SQL Injection (database/sql) — CWE-89
```go
// NEVER: db.Query("SELECT * FROM users WHERE name = '" + name + "'")
// CORRECT: db.Query("SELECT * FROM users WHERE name = $1", name)
// Or with ? for MySQL: db.Query("SELECT * FROM users WHERE name = ?", name)
```

### Command Injection — CWE-78
```go
// NEVER: exec.Command("sh", "-c", "cmd " + userInput)
// CORRECT: exec.Command("cmd", userInput) // No shell interpretation
```

### Path Traversal — CWE-22
```go
base := filepath.Clean(SAFE_DIR)
requested := filepath.Clean(filepath.Join(base, userInput))
if !strings.HasPrefix(requested, base+string(filepath.Separator)) {
    return fmt.Errorf("path traversal detected")
}
```

### XSS (html/template) — CWE-79
```go
// html/template auto-escapes. Vulnerability is using text/template for HTML:
// NEVER: import "text/template" for HTML output
// CORRECT: import "html/template"
```

### SSRF — CWE-918
```go
parsed, err := url.Parse(userURL)
if err != nil || !isAllowedHost(parsed.Hostname()) {
    return fmt.Errorf("URL not allowed")
}
```

### Weak Crypto — CWE-327
```go
// NEVER: crypto/md5, crypto/sha1 for security
// CORRECT: crypto/sha256 for integrity
// Passwords: golang.org/x/crypto/bcrypt
import "golang.org/x/crypto/bcrypt"
hash, _ := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
```

---

## Language Detection Rules

| Extension | Language | Primary Framework |
|-----------|----------|-------------------|
| `.py` | Python | Django/Flask/FastAPI |
| `.java` | Java | Spring Boot/Jakarta |
| `.js`, `.mjs` | JavaScript | Express/Node.js |
| `.ts`, `.tsx` | TypeScript | NestJS/Next.js |
| `.cs` | C# | ASP.NET Core |
| `.go` | Go | net/http/gin/echo |

## Import Conventions

When adding security-related imports:
- Python: Add at top of file after existing imports, grouped by standard lib / third-party
- Java: Add after package declaration, before class
- JavaScript: Add with other requires/imports at top
- TypeScript: Add with other imports, maintain type imports separately
- C#: Add in the using block at top
- Go: Add in the import block, maintain goimports ordering

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
