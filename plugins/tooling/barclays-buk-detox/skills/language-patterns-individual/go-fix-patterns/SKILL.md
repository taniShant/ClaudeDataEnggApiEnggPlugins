---
name: go-fix-patterns
description: "Go Security Fix Patterns — Provide Go-specific security fix patterns and standard library best practices for applying CWE remediations in Go codebases. This skill is composed with CWE-specific remediation skills to translate ge"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Go Security Fix Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provide Go-specific security fix patterns and standard library best practices for applying CWE remediations in Go codebases. This skill is composed with CWE-specific remediation skills to translate generic vulnerability fixes into idiomatic Go code using the standard library and common third-party packages. It covers TLS configuration (crypto/tls), SQL injection prevention (database/sql prepared statements), template auto-escaping (html/template), command injection prevention (os/exec without shell), HTTP server hardening (timeouts, TLS), and input validation patterns.

## Inputs

- **cwe_id** (required, string): The CWE identifier being remediated (e.g., `CWE-89`, `CWE-79`).
- **vulnerability** (required, JSON object): The normalized vulnerability object from the CWE skill, containing `file_path`, `line_number`, and `code_snippet`.
- **framework** (optional, string): The HTTP framework in use (`stdlib`, `gin`, `echo`, `chi`, `fiber`). Auto-detected from imports if not provided.
- **go_version** (optional, string): The Go version (e.g., `1.21`, `1.22`). Auto-detected from `go.mod` if not provided.

## Steps

1. **Detect Go version and framework.**
   - Use `Glob` to find `go.mod`.
   - Use `Read` to examine `go.mod` for the Go version directive and module dependencies (gin, echo, chi, fiber).
   - Examine import statements in the vulnerable file to confirm the framework.

2. **Select the appropriate fix pattern based on CWE and framework.**
   - Match the CWE ID to the relevant pattern section below.
   - Choose the framework-specific variant if applicable.

3. **Apply the fix using the patterns defined below.**
   - Use `Edit` to apply the code transformation.
   - Add required imports. Go files must have all imports declared; unused imports cause compilation errors.
   - If the fix requires a new module, note it in the output for the pipeline to run `go get`.

4. **Verify idiomatic Go conventions.**
   - Follow Go naming conventions (exported PascalCase, unexported camelCase, acronyms in ALL CAPS like `HTTP`, `URL`, `ID`).
   - Handle errors explicitly. Do not ignore error returns.
   - Use `defer` for resource cleanup.
   - Prefer returning `error` values over panicking.

5. **Scan for similar patterns.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the project.
   - Apply the same fix pattern consistently.

---

## Fix Patterns

### TLS Configuration (crypto/tls)

#### Secure TLS Client Configuration

**When to use:** CWE-295 (Improper Certificate Validation), CWE-327 (Weak Crypto) when TLS is misconfigured.

**Before (vulnerable -- TLS verification disabled):**
```go
import (
    "crypto/tls"
    "net/http"
)

func createClient() *http.Client {
    tr := &http.Transport{
        TLSClientConfig: &tls.Config{
            InsecureSkipVerify: true, // Disables certificate verification
        },
    }
    return &http.Client{Transport: tr}
}
```

**After (fixed):**
```go
import (
    "crypto/tls"
    "crypto/x509"
    "net/http"
    "os"
    "time"
)

func createClient() (*http.Client, error) {
    // Load custom CA if needed (e.g., internal PKI)
    caCert, err := os.ReadFile("/etc/ssl/certs/internal-ca.pem")
    if err != nil {
        return nil, fmt.Errorf("reading CA certificate: %w", err)
    }

    caCertPool := x509.NewCertPool()
    if !caCertPool.AppendCertsFromPEM(caCert) {
        return nil, fmt.Errorf("failed to parse CA certificate")
    }

    tlsConfig := &tls.Config{
        MinVersion: tls.VersionTLS12,
        CurvePreferences: []tls.CurveID{
            tls.X25519,
            tls.CurveP256,
        },
        CipherSuites: []uint16{
            tls.TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384,
            tls.TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256,
            tls.TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256,
        },
        RootCAs: caCertPool, // Use system CAs: set RootCAs to nil
    }

    tr := &http.Transport{
        TLSClientConfig: tlsConfig,
    }

    return &http.Client{
        Transport: tr,
        Timeout:   30 * time.Second,
    }, nil
}
```

**Minimal fix (use system CAs, enforce TLS 1.2+):**
```go
func createClient() *http.Client {
    tr := &http.Transport{
        TLSClientConfig: &tls.Config{
            MinVersion: tls.VersionTLS12,
        },
    }
    return &http.Client{
        Transport: tr,
        Timeout:   30 * time.Second,
    }
}
```

**Key points:**
- Never set `InsecureSkipVerify: true` in production code. It disables all certificate verification, enabling man-in-the-middle attacks.
- Set `MinVersion: tls.VersionTLS12` to prevent downgrade attacks to TLS 1.0/1.1.
- When `RootCAs` is `nil`, Go uses the system's certificate pool, which is the correct default for public CAs.
- For internal CAs, load the CA certificate explicitly into a `CertPool`.
- Go 1.22+ defaults `MinVersion` to TLS 1.2 if not explicitly set, but setting it explicitly documents the intent.

#### Secure TLS Server Configuration

**When to use:** CWE-327 for HTTP server TLS configuration.

```go
import (
    "crypto/tls"
    "log"
    "net/http"
    "time"
)

func startServer(handler http.Handler) error {
    tlsConfig := &tls.Config{
        MinVersion:               tls.VersionTLS12,
        PreferServerCipherSuites: true,
        CurvePreferences: []tls.CurveID{
            tls.X25519,
            tls.CurveP256,
        },
    }

    server := &http.Server{
        Addr:         ":443",
        Handler:      handler,
        TLSConfig:    tlsConfig,
        ReadTimeout:  10 * time.Second,
        WriteTimeout: 15 * time.Second,
        IdleTimeout:  120 * time.Second,
    }

    return server.ListenAndServeTLS("cert.pem", "key.pem")
}
```

---

### SQL Injection Prevention (database/sql)

#### Prepared Statements

**When to use:** CWE-89 (SQL Injection) in Go applications.

**Before (vulnerable -- string concatenation):**
```go
import "database/sql"

func getUser(db *sql.DB, username string) (*User, error) {
    query := "SELECT id, username, email FROM users WHERE username = '" + username + "'"
    row := db.QueryRow(query)
    var user User
    err := row.Scan(&user.ID, &user.Username, &user.Email)
    if err != nil {
        return nil, err
    }
    return &user, nil
}
```

**After (fixed -- parameterized query):**
```go
import "database/sql"

func getUser(db *sql.DB, username string) (*User, error) {
    query := "SELECT id, username, email FROM users WHERE username = $1"
    row := db.QueryRow(query, username)
    var user User
    err := row.Scan(&user.ID, &user.Username, &user.Email)
    if err != nil {
        if err == sql.ErrNoRows {
            return nil, nil
        }
        return nil, fmt.Errorf("querying user: %w", err)
    }
    return &user, nil
}
```

**Before (vulnerable -- fmt.Sprintf in SQL):**
```go
func searchProducts(db *sql.DB, name string) ([]Product, error) {
    query := fmt.Sprintf("SELECT * FROM products WHERE name LIKE '%%%s%%'", name)
    rows, err := db.Query(query)
    // ...
}
```

**After (fixed):**
```go
func searchProducts(db *sql.DB, name string) ([]Product, error) {
    query := "SELECT * FROM products WHERE name LIKE $1"
    rows, err := db.Query(query, "%"+name+"%")
    if err != nil {
        return nil, fmt.Errorf("searching products: %w", err)
    }
    defer rows.Close()

    var products []Product
    for rows.Next() {
        var p Product
        if err := rows.Scan(&p.ID, &p.Name, &p.Price); err != nil {
            return nil, fmt.Errorf("scanning product row: %w", err)
        }
        products = append(products, p)
    }
    if err := rows.Err(); err != nil {
        return nil, fmt.Errorf("iterating product rows: %w", err)
    }
    return products, nil
}
```

**Placeholder styles by driver:**
- PostgreSQL (`lib/pq`, `pgx`): `$1`, `$2`, `$3` (numbered)
- MySQL (`go-sql-driver/mysql`): `?` (positional)
- SQLite (`mattn/go-sqlite3`): `?` (positional) or `$1` (numbered)

**Dynamic identifiers with allowlist:**
```go
var allowedSortColumns = map[string]bool{
    "name":       true,
    "email":      true,
    "created_at": true,
}

func getUsersSorted(db *sql.DB, sortColumn string) ([]User, error) {
    if !allowedSortColumns[sortColumn] {
        return nil, fmt.Errorf("invalid sort column: %s", sortColumn)
    }
    // sortColumn is validated; safe to interpolate for identifier
    query := fmt.Sprintf("SELECT id, name, email FROM users ORDER BY %s", sortColumn)
    rows, err := db.Query(query)
    if err != nil {
        return nil, err
    }
    defer rows.Close()
    // ... scan rows
}
```

**Key points:**
- `database/sql` supports parameterized queries natively through `db.Query(query, args...)`, `db.QueryRow(query, args...)`, and `db.Exec(query, args...)`.
- Never use `fmt.Sprintf`, `+` concatenation, or `strings.Builder` to embed user input in SQL strings.
- Always check `rows.Err()` after iterating.
- Always `defer rows.Close()` to prevent connection leaks.
- Use `sql.ErrNoRows` to distinguish "no results" from actual errors.

---

### Template Auto-Escaping (html/template)

#### Safe HTML Rendering

**When to use:** CWE-79 (XSS) in Go web applications.

**Before (vulnerable -- text/template for HTML):**
```go
import "text/template"

func renderPage(w http.ResponseWriter, data PageData) {
    tmpl := template.Must(template.ParseFiles("page.html"))
    tmpl.Execute(w, data)
}
```

**After (fixed -- html/template):**
```go
import "html/template"

func renderPage(w http.ResponseWriter, data PageData) {
    tmpl := template.Must(template.ParseFiles("page.html"))
    if err := tmpl.Execute(w, data); err != nil {
        http.Error(w, "Internal Server Error", http.StatusInternalServerError)
        log.Printf("Template execution error: %v", err)
    }
}
```

**Before (vulnerable -- fmt.Fprintf with HTML):**
```go
func handler(w http.ResponseWriter, r *http.Request) {
    name := r.URL.Query().Get("name")
    fmt.Fprintf(w, "<h1>Hello, %s!</h1>", name)
}
```

**After (fixed -- html/template):**
```go
import "html/template"

var greetTmpl = template.Must(template.New("greet").Parse(`<h1>Hello, {{.Name}}!</h1>`))

func handler(w http.ResponseWriter, r *http.Request) {
    name := r.URL.Query().Get("name")
    w.Header().Set("Content-Type", "text/html; charset=utf-8")
    if err := greetTmpl.Execute(w, struct{ Name string }{Name: name}); err != nil {
        http.Error(w, "Internal Server Error", http.StatusInternalServerError)
        log.Printf("Template execution error: %v", err)
    }
}
```

**After (fixed -- manual escaping for simple cases):**
```go
import "html"

func handler(w http.ResponseWriter, r *http.Request) {
    name := r.URL.Query().Get("name")
    safeName := html.EscapeString(name)
    fmt.Fprintf(w, "<h1>Hello, %s!</h1>", safeName)
}
```

**Key points:**
- `html/template` auto-escapes values based on context (HTML, JavaScript, URL, CSS). It is context-aware.
- `text/template` performs no escaping. Never use `text/template` for HTML output.
- `html.EscapeString()` provides basic HTML entity escaping but is not context-aware.
- Parse templates once at startup (package-level `var` or `init()`) and reuse them. Do not parse templates per request.
- Always handle template execution errors. Do not write partial output followed by an error response.
- Set `Content-Type: text/html; charset=utf-8` explicitly to prevent MIME-type sniffing.

---

### Command Injection Prevention (os/exec)

#### Safe Process Execution

**When to use:** CWE-78 (OS Command Injection) in Go applications.

**Before (vulnerable -- shell execution with user input):**
```go
import "os/exec"

func pingHost(host string) (string, error) {
    cmd := exec.Command("sh", "-c", "ping -c 4 "+host)
    out, err := cmd.Output()
    return string(out), err
}
```

**After (fixed -- direct command, no shell):**
```go
import (
    "fmt"
    "os/exec"
    "regexp"
    "time"
    "context"
)

var hostnameRegex = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9.-]{0,253}[a-zA-Z0-9]$`)

func pingHost(host string) (string, error) {
    // Validate input
    if !hostnameRegex.MatchString(host) {
        return "", fmt.Errorf("invalid hostname: %s", host)
    }

    // Execute without shell -- arguments are passed directly to the executable
    ctx, cancel := context.WithTimeout(context.Background(), 15*time.Second)
    defer cancel()

    cmd := exec.CommandContext(ctx, "ping", "-c", "4", host)
    out, err := cmd.Output()
    if err != nil {
        return "", fmt.Errorf("ping failed: %w", err)
    }
    return string(out), nil
}
```

**Key points:**
- Never use `exec.Command("sh", "-c", userInput)` or `exec.Command("bash", "-c", userInput)`. Spawning a shell enables command injection through `;`, `&&`, `||`, `|`, backticks, and `$()`.
- `exec.Command("ping", "-c", "4", host)` passes `host` as a single argument directly to the `ping` executable. Shell metacharacters are not interpreted.
- Always validate user input before passing it as a command argument.
- Use `exec.CommandContext` with a timeout to prevent long-running commands.
- Go's `os/exec` does not invoke a shell by default (unlike some other languages), which is inherently safer. Do not bypass this by explicitly invoking `sh` or `bash`.

---

### HTTP Server Hardening (net/http)

#### Timeouts and TLS

**When to use:** CWE-400 (Resource Exhaustion / Slowloris), CWE-319 (Cleartext Transmission), general HTTP hardening.

**Before (vulnerable -- no timeouts, no TLS):**
```go
func main() {
    http.HandleFunc("/", handler)
    http.ListenAndServe(":8080", nil) // No timeouts, no TLS
}
```

**After (fixed):**
```go
import (
    "crypto/tls"
    "log"
    "net/http"
    "time"
)

func main() {
    mux := http.NewServeMux()
    mux.HandleFunc("/", handler)

    server := &http.Server{
        Addr:    ":443",
        Handler: mux,
        TLSConfig: &tls.Config{
            MinVersion: tls.VersionTLS12,
        },
        ReadTimeout:       10 * time.Second,
        ReadHeaderTimeout: 5 * time.Second,
        WriteTimeout:      15 * time.Second,
        IdleTimeout:       120 * time.Second,
        MaxHeaderBytes:    1 << 20, // 1 MB
    }

    // Redirect HTTP to HTTPS
    go func() {
        redirectServer := &http.Server{
            Addr:         ":80",
            ReadTimeout:  5 * time.Second,
            WriteTimeout: 5 * time.Second,
            Handler: http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
                target := "https://" + r.Host + r.URL.RequestURI()
                http.Redirect(w, r, target, http.StatusMovedPermanently)
            }),
        }
        log.Fatal(redirectServer.ListenAndServe())
    }()

    log.Fatal(server.ListenAndServeTLS("cert.pem", "key.pem"))
}
```

**Key points:**
- Always set `ReadTimeout`, `ReadHeaderTimeout`, `WriteTimeout`, and `IdleTimeout` on `http.Server`. Without these, a slow client can hold connections indefinitely (Slowloris attack).
- `ReadHeaderTimeout` prevents slow header attacks specifically; it was added in Go 1.8.
- `MaxHeaderBytes` limits the size of request headers.
- Use `http.NewServeMux()` explicitly instead of `http.DefaultServeMux`. The default mux is a global variable and can be modified by any imported package.
- Always call `ListenAndServeTLS` for production. Redirect HTTP (port 80) to HTTPS (port 443).

#### Security Headers Middleware

```go
func securityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("Content-Security-Policy", "default-src 'self'; script-src 'self'")
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("X-XSS-Protection", "0") // Disabled; CSP is preferred
        w.Header().Set("Referrer-Policy", "strict-origin-when-cross-origin")
        w.Header().Set("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")
        w.Header().Set("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        next.ServeHTTP(w, r)
    })
}

// Usage:
mux := http.NewServeMux()
mux.HandleFunc("/", handler)
wrappedMux := securityHeaders(mux)
server := &http.Server{Handler: wrappedMux}
```

---

### Input Validation

#### Validation Patterns

**When to use:** CWE-20 (Improper Input Validation), defense-in-depth for CWE-89, CWE-79, CWE-78.

**Struct validation with a validator library:**
```go
import "github.com/go-playground/validator/v10"

type CreateUserRequest struct {
    Username string `json:"username" validate:"required,alphanum,min=3,max=50"`
    Email    string `json:"email" validate:"required,email"`
    Age      int    `json:"age" validate:"required,gte=13,lte=150"`
    Role     string `json:"role" validate:"required,oneof=user moderator admin"`
}

var validate = validator.New()

func validateRequest(req *CreateUserRequest) error {
    if err := validate.Struct(req); err != nil {
        validationErrors := err.(validator.ValidationErrors)
        var messages []string
        for _, e := range validationErrors {
            messages = append(messages, fmt.Sprintf("Field '%s' failed on '%s' validation", e.Field(), e.Tag()))
        }
        return fmt.Errorf("validation failed: %s", strings.Join(messages, "; "))
    }
    return nil
}
```

**HTTP handler with validation:**
```go
func createUserHandler(w http.ResponseWriter, r *http.Request) {
    var req CreateUserRequest
    if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
        http.Error(w, `{"error": "Invalid JSON"}`, http.StatusBadRequest)
        return
    }

    if err := validateRequest(&req); err != nil {
        w.Header().Set("Content-Type", "application/json")
        w.WriteHeader(http.StatusBadRequest)
        json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
        return
    }

    // Process validated request
}
```

**Manual validation helpers:**
```go
import (
    "fmt"
    "net/url"
    "regexp"
    "strings"
)

var (
    usernameRegex = regexp.MustCompile(`^[a-zA-Z0-9_]{3,50}$`)
    emailRegex    = regexp.MustCompile(`^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`)
)

func validateUsername(username string) error {
    if !usernameRegex.MatchString(username) {
        return fmt.Errorf("invalid username: must be 3-50 alphanumeric characters or underscores")
    }
    return nil
}

func validateURL(rawURL string) (*url.URL, error) {
    parsed, err := url.ParseRequestURI(rawURL)
    if err != nil {
        return nil, fmt.Errorf("invalid URL: %w", err)
    }
    if parsed.Scheme != "http" && parsed.Scheme != "https" {
        return nil, fmt.Errorf("only HTTP and HTTPS URLs are allowed")
    }
    return parsed, nil
}

func validateSortColumn(column string) error {
    allowed := map[string]bool{
        "name": true, "email": true, "created_at": true,
    }
    if !allowed[strings.ToLower(column)] {
        return fmt.Errorf("invalid sort column: %s", column)
    }
    return nil
}
```

**Key points:**
- `go-playground/validator` is the most widely used validation library in Go.
- Compile `regexp` patterns at package level (`var` or `init()`), not per request. `regexp.MustCompile` panics at startup on invalid patterns, which is preferable to silent runtime failures.
- Always validate and sanitize input before passing it to database queries, templates, or command execution.
- Return structured error responses with appropriate HTTP status codes (400 for validation, 404 for not found, 500 for internal errors).
- Limit request body size with `http.MaxBytesReader` to prevent large payload attacks.

---

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "language": "go",
  "framework": "<string: detected framework>",
  "go_version": "<string: detected Go version>",
  "pattern_applied": "<string: name of the pattern applied>",
  "file_path": "<string: path to the modified file>",
  "changes": [
    {
      "line_number": "<integer>",
      "original_code": "<string>",
      "fixed_code": "<string>",
      "pattern": "<string: pattern name used>"
    }
  ],
  "imports_added": ["<string: new import paths>"],
  "modules_needed": ["<string: modules to go get>"],
  "configuration_changes": ["<string: any configuration changes needed>"],
  "warnings": ["<string: manual review items>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries contain valid, compilable Go code.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Cannot detect framework** | Default to standard library (`net/http`) patterns. Most Go security patterns use standard library APIs regardless of framework. |
| **Go version incompatibility** | Check `go.mod` for the Go version directive. Some APIs (e.g., `errors.Join`, `slog`) require Go 1.20+/1.21+. Use version-appropriate alternatives. |
| **Database driver not identified** | Check imports for `lib/pq`, `pgx`, `go-sql-driver/mysql`, `mattn/go-sqlite3`. Apply the driver-specific placeholder style (`$1` vs `?`). If unknown, default to `?` and add a warning. |
| **Missing module** | Note the required module in `modules_needed`. Do not modify `go.mod` directly. |
| **CGo dependency** | Some libraries (e.g., `mattn/go-sqlite3`) require CGo. Note this in warnings if relevant. |
| **Gin/Echo/Chi-specific middleware** | If the project uses a non-stdlib router, adapt the middleware pattern to the framework's middleware interface. |

## Constraints

- **Preserve compilation**: All generated code must compile with `go build`. Go does not tolerate unused imports or variables.
- **Error handling**: Every error must be handled. Do not use `_` to discard errors from security-sensitive operations.
- **No runtime execution**: Do not run `go build`, `go test`, or execute any Go code.
- **Minimal diff**: Change only the code required for the security fix.
- **Resource cleanup**: Use `defer` for closing resources (`rows.Close()`, `resp.Body.Close()`, file handles). Place `defer` immediately after successful acquisition.
- **Concurrency safety**: Go programs are concurrent. Ensure fix patterns are safe for concurrent use. Do not introduce shared mutable state without synchronization.
- **Import management**: When adding imports, maintain the standard Go import grouping (stdlib, blank line, third-party). Remove unused imports.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to build or run code.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
