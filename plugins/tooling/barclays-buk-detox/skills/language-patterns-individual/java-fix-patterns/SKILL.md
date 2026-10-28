---
name: java-fix-patterns
description: "Java Security Fix Patterns — Provide Java-specific security fix patterns and framework-specific best practices for applying CWE remediations in Java codebases. This skill is composed with CWE-specific remediation skills to transl"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/language_patterns_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Java Security Fix Patterns
## Quick Start

This skill provides language-specific fix patterns for applying CWE remediations in a target programming language.

```
# Loaded by detox-fix-agent based on the detected programming language.
# Provides language-idiomatic fix patterns for each CWE type.
```



## Purpose

Provide Java-specific security fix patterns and framework-specific best practices for applying CWE remediations in Java codebases. This skill is composed with CWE-specific remediation skills to translate generic vulnerability fixes into idiomatic Java code using Spring Security, JDBC, Java EE, and standard library APIs. It covers authentication and authorization (Spring Security), SQL injection prevention (PreparedStatement, JPA), input validation (javax.validation, OWASP ESAPI), cryptographic operations (Cipher, KeyStore), and structured error handling.

## Inputs

- **cwe_id** (required, string): The CWE identifier being remediated (e.g., `CWE-89`, `CWE-79`).
- **vulnerability** (required, JSON object): The normalized vulnerability object from the CWE skill, containing `file_path`, `line_number`, and `code_snippet`.
- **framework** (optional, string): The Java framework in use (`spring-boot`, `spring-mvc`, `java-ee`, `jakarta-ee`, `plain-java`). Auto-detected from imports and project structure if not provided.
- **java_version** (optional, string): The Java version (e.g., `11`, `17`, `21`). Auto-detected from `pom.xml` or `build.gradle` if not provided.
- **build_tool** (optional, string): `maven` or `gradle`. Auto-detected from project files if not provided.

## Steps

1. **Detect framework and Java version.**
   - Use `Glob` to find `pom.xml` or `build.gradle` / `build.gradle.kts`.
   - Use `Read` to examine the build file for Spring Boot version, Java EE / Jakarta EE dependencies, and Java source/target version.
   - Examine import statements in the vulnerable file to confirm the framework.

2. **Select the appropriate fix pattern based on CWE and framework.**
   - Match the CWE ID to the relevant pattern section below.
   - Choose the framework-specific variant (Spring, Java EE, plain Java).

3. **Apply the fix using the patterns defined below.**
   - Use `Edit` to apply the code transformation.
   - Add required imports at the top of the file.
   - If the fix requires a new dependency, note it in the output for the pipeline to add to `pom.xml` or `build.gradle`.

4. **Verify idiomatic Java conventions.**
   - Ensure the fix follows Java naming conventions (camelCase methods, PascalCase classes).
   - Ensure proper exception handling (checked vs. unchecked exceptions).
   - Ensure resources are properly closed (try-with-resources for `Connection`, `PreparedStatement`, `Cipher` streams).

5. **Scan for similar patterns.**
   - Use `Grep` to find other instances of the same vulnerable pattern in the file and project.
   - Apply the same fix pattern consistently.

---

## Fix Patterns

### Authentication and Authorization (Spring Security)

#### Method-Level Authorization with @PreAuthorize

**When to use:** Remediation of CWE-285 (Improper Authorization), CWE-862 (Missing Authorization), or CWE-863 (Incorrect Authorization) in Spring MVC controllers.

**Before (vulnerable):**
```java
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    @GetMapping("/users")
    public List<User> getAllUsers() {
        return userService.findAll();
    }

    @DeleteMapping("/users/{id}")
    public void deleteUser(@PathVariable Long id) {
        userService.deleteById(id);
    }
}
```

**After (fixed):**
```java
import org.springframework.security.access.prepost.PreAuthorize;

@RestController
@RequestMapping("/api/admin")
@PreAuthorize("hasRole('ADMIN')")
public class AdminController {

    @GetMapping("/users")
    @PreAuthorize("hasAuthority('USER_READ')")
    public List<User> getAllUsers() {
        return userService.findAll();
    }

    @DeleteMapping("/users/{id}")
    @PreAuthorize("hasAuthority('USER_DELETE')")
    public void deleteUser(@PathVariable Long id) {
        userService.deleteById(id);
    }
}
```

**Key points:**
- `@PreAuthorize` requires `@EnableMethodSecurity` (Spring 6+) or `@EnableGlobalMethodSecurity(prePostEnabled = true)` (Spring 5) on a `@Configuration` class.
- Use `hasRole()` for role-based checks and `hasAuthority()` for fine-grained permissions.
- Class-level annotation provides a baseline; method-level overrides for specific endpoints.

#### SecurityFilterChain Configuration

**When to use:** Configuring HTTP security, CSRF protection, session management, and header security in Spring Boot applications.

**Before (vulnerable -- permits all, no CSRF):**
```java
@Configuration
public class SecurityConfig extends WebSecurityConfigurerAdapter {
    @Override
    protected void configure(HttpSecurity http) throws Exception {
        http.csrf().disable()
            .authorizeRequests()
            .anyRequest().permitAll();
    }
}
```

**After (fixed -- Spring Boot 3.x / Spring Security 6.x):**
```java
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf
                .csrfTokenRepository(CookieCsrfTokenRepository.withHttpOnlyFalse())
            )
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/public/**").permitAll()
                .requestMatchers("/api/admin/**").hasRole("ADMIN")
                .anyRequest().authenticated()
            )
            .headers(headers -> headers
                .contentSecurityPolicy(csp -> csp
                    .policyDirectives("default-src 'self'; script-src 'self'")
                )
                .frameOptions(frame -> frame.deny())
            )
            .sessionManagement(session -> session
                .maximumSessions(1)
                .maxSessionsPreventsLogin(true)
            );
        return http.build();
    }
}
```

**Key points:**
- `WebSecurityConfigurerAdapter` is deprecated in Spring Security 5.7+ and removed in 6.x. Use the `SecurityFilterChain` bean pattern.
- Never disable CSRF for browser-facing endpoints. CSRF can be disabled for stateless REST APIs that use token-based authentication (e.g., JWT in `Authorization` header).
- Use the lambda DSL (e.g., `csrf(csrf -> ...)`) instead of the chaining DSL.

---

### SQL Injection Prevention (JDBC and JPA)

#### PreparedStatement (JDBC)

**When to use:** CWE-89 remediation when raw JDBC is used.

**Before (vulnerable):**
```java
public User findUser(String username) throws SQLException {
    Connection conn = dataSource.getConnection();
    Statement stmt = conn.createStatement();
    ResultSet rs = stmt.executeQuery(
        "SELECT * FROM users WHERE username = '" + username + "'"
    );
    // ...
}
```

**After (fixed):**
```java
public User findUser(String username) throws SQLException {
    String sql = "SELECT * FROM users WHERE username = ?";
    try (Connection conn = dataSource.getConnection();
         PreparedStatement pstmt = conn.prepareStatement(sql)) {
        pstmt.setString(1, username);
        try (ResultSet rs = pstmt.executeQuery()) {
            if (rs.next()) {
                return mapUser(rs);
            }
            return null;
        }
    }
}
```

**Key points:**
- Always use try-with-resources for `Connection`, `PreparedStatement`, and `ResultSet`.
- Parameter indices in `PreparedStatement` are 1-based.
- Use the type-specific setter (`setString`, `setInt`, `setLong`, `setTimestamp`) matching the SQL column type.

#### Dynamic Identifiers with Allowlist

**When to use:** CWE-89 when table or column names are dynamic and cannot be parameterized.

```java
private static final Set<String> ALLOWED_SORT_COLUMNS = Set.of(
    "username", "email", "created_at", "last_login"
);

public List<User> findAllSorted(String sortColumn) throws SQLException {
    if (!ALLOWED_SORT_COLUMNS.contains(sortColumn)) {
        throw new IllegalArgumentException("Invalid sort column: " + sortColumn);
    }
    String sql = "SELECT * FROM users ORDER BY " + sortColumn;
    try (Connection conn = dataSource.getConnection();
         PreparedStatement pstmt = conn.prepareStatement(sql);
         ResultSet rs = pstmt.executeQuery()) {
        return mapUsers(rs);
    }
}
```

#### JPA / Hibernate

**When to use:** CWE-89 when using JPA or Hibernate.

**Before (vulnerable -- string concatenation in JPQL):**
```java
public List<User> searchUsers(String name) {
    String jpql = "SELECT u FROM User u WHERE u.name LIKE '%" + name + "%'";
    return entityManager.createQuery(jpql, User.class).getResultList();
}
```

**After (fixed -- named parameters):**
```java
public List<User> searchUsers(String name) {
    String jpql = "SELECT u FROM User u WHERE u.name LIKE :pattern";
    return entityManager.createQuery(jpql, User.class)
        .setParameter("pattern", "%" + name + "%")
        .getResultList();
}
```

**After (fixed -- Criteria API, fully type-safe):**
```java
public List<User> searchUsers(String name) {
    CriteriaBuilder cb = entityManager.getCriteriaBuilder();
    CriteriaQuery<User> cq = cb.createQuery(User.class);
    Root<User> root = cq.from(User.class);
    cq.select(root).where(cb.like(root.get("name"), "%" + name + "%"));
    return entityManager.createQuery(cq).getResultList();
}
```

**After (fixed -- Spring Data JPA repository method):**
```java
public interface UserRepository extends JpaRepository<User, Long> {
    @Query("SELECT u FROM User u WHERE u.name LIKE %:name%")
    List<User> searchByName(@Param("name") String name);
}
```

---

### Input Validation (javax.validation / Jakarta Validation and OWASP ESAPI)

#### Bean Validation

**When to use:** CWE-20 (Improper Input Validation), CWE-79 (XSS prevention at input layer), or any CWE where input constraints need enforcement.

```java
import jakarta.validation.constraints.*;

public class CreateUserRequest {

    @NotBlank(message = "Username is required")
    @Size(min = 3, max = 50, message = "Username must be 3-50 characters")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "Username must be alphanumeric")
    private String username;

    @NotBlank(message = "Email is required")
    @Email(message = "Invalid email format")
    private String email;

    @NotNull(message = "Age is required")
    @Min(value = 13, message = "Minimum age is 13")
    @Max(value = 150, message = "Invalid age")
    private Integer age;

    // getters and setters
}
```

**Controller integration:**
```java
import jakarta.validation.Valid;

@PostMapping("/users")
public ResponseEntity<User> createUser(@Valid @RequestBody CreateUserRequest request) {
    // request is already validated; invalid input returns 400 automatically
    return ResponseEntity.ok(userService.create(request));
}
```

**Key points:**
- Spring Boot auto-validates `@Valid`-annotated parameters and returns 400 Bad Request on violations.
- For Jakarta EE (Java EE 9+), use `jakarta.validation.constraints.*`. For Java EE 8 and earlier, use `javax.validation.constraints.*`.
- Custom validators can be created with `@Constraint` for complex rules.

#### OWASP ESAPI Output Encoding

**When to use:** CWE-79 (XSS) when building HTML responses manually without a template engine.

```java
import org.owasp.esapi.ESAPI;

// HTML body context
String safeHtml = ESAPI.encoder().encodeForHTML(userInput);

// HTML attribute context
String safeAttr = ESAPI.encoder().encodeForHTMLAttribute(userInput);

// JavaScript context
String safeJs = ESAPI.encoder().encodeForJavaScript(userInput);

// URL parameter context
String safeUrl = ESAPI.encoder().encodeForURL(userInput);

// CSS context
String safeCss = ESAPI.encoder().encodeForCSS(userInput);
```

**Key points:**
- Each context requires its own encoding function. HTML encoding does not protect against XSS in JavaScript context.
- Prefer using a template engine with auto-escaping (Thymeleaf, Freemarker) over manual encoding.
- ESAPI requires the `org.owasp.esapi:esapi` dependency.

---

### Cryptographic Operations (Cipher, KeyStore)

#### Symmetric Encryption with AES-GCM

**When to use:** CWE-327 (Weak Crypto) when DES, 3DES, RC4, AES/ECB, or AES/CBC-without-HMAC is detected.

**Before (vulnerable):**
```java
import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

public byte[] encrypt(byte[] data, byte[] key) throws Exception {
    SecretKeySpec keySpec = new SecretKeySpec(key, "DES");
    Cipher cipher = Cipher.getInstance("DES/ECB/PKCS5Padding");
    cipher.init(Cipher.ENCRYPT_MODE, keySpec);
    return cipher.doFinal(data);
}
```

**After (fixed):**
```java
import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;
import java.security.SecureRandom;

public class AesGcmEncryptor {

    private static final int GCM_IV_LENGTH = 12;   // 96 bits
    private static final int GCM_TAG_LENGTH = 128;  // bits

    public byte[] encrypt(byte[] data, SecretKey key) throws Exception {
        byte[] iv = new byte[GCM_IV_LENGTH];
        new SecureRandom().nextBytes(iv);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.ENCRYPT_MODE, key, spec);
        byte[] ciphertext = cipher.doFinal(data);

        // Prepend IV to ciphertext for decryption
        byte[] result = new byte[iv.length + ciphertext.length];
        System.arraycopy(iv, 0, result, 0, iv.length);
        System.arraycopy(ciphertext, 0, result, iv.length, ciphertext.length);
        return result;
    }

    public byte[] decrypt(byte[] encryptedData, SecretKey key) throws Exception {
        byte[] iv = new byte[GCM_IV_LENGTH];
        System.arraycopy(encryptedData, 0, iv, 0, GCM_IV_LENGTH);

        byte[] ciphertext = new byte[encryptedData.length - GCM_IV_LENGTH];
        System.arraycopy(encryptedData, GCM_IV_LENGTH, ciphertext, 0, ciphertext.length);

        Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");
        GCMParameterSpec spec = new GCMParameterSpec(GCM_TAG_LENGTH, iv);
        cipher.init(Cipher.DECRYPT_MODE, key, spec);
        return cipher.doFinal(ciphertext);
    }

    public static SecretKey generateKey() throws Exception {
        KeyGenerator keyGen = KeyGenerator.getInstance("AES");
        keyGen.init(256);
        return keyGen.generateKey();
    }
}
```

**Key points:**
- AES-GCM provides both confidentiality and authenticity (authenticated encryption).
- Always use a random 12-byte IV (never reuse IVs with the same key).
- Use `SecureRandom` for IV generation, never `Random`.
- The authentication tag length should be 128 bits.
- Prepend the IV to the ciphertext so it is available for decryption.

#### KeyStore for Key Management

**When to use:** CWE-798 (Hardcoded Credentials) or CWE-321 (Hard-coded Cryptographic Key).

**Before (vulnerable):**
```java
private static final String SECRET_KEY = "MySuperSecretKey1234567890123456";

public SecretKeySpec getKey() {
    return new SecretKeySpec(SECRET_KEY.getBytes(), "AES");
}
```

**After (fixed):**
```java
import java.security.KeyStore;
import javax.crypto.SecretKey;

public SecretKey getKey(String keystorePath, char[] keystorePassword, String keyAlias)
        throws Exception {
    KeyStore keyStore = KeyStore.getInstance("PKCS12");
    try (var fis = new java.io.FileInputStream(keystorePath)) {
        keyStore.load(fis, keystorePassword);
    }
    KeyStore.SecretKeyEntry entry = (KeyStore.SecretKeyEntry) keyStore.getEntry(
        keyAlias, new KeyStore.PasswordProtection(keystorePassword)
    );
    return entry.getSecretKey();
}
```

**Key points:**
- Use PKCS12 format (the default since Java 9) over JKS.
- Keystore passwords should come from environment variables or a secrets manager, never hardcoded.
- For Spring Boot, use `@Value("${encryption.key}")` or Spring Vault integration.

#### Password Hashing with BCrypt (Spring Security)

**When to use:** CWE-327 or CWE-916 (Insufficient Password Hashing) in Spring applications.

```java
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;

@Bean
public PasswordEncoder passwordEncoder() {
    return new BCryptPasswordEncoder(12);
}

// Usage
String hashed = passwordEncoder.encode(rawPassword);
boolean matches = passwordEncoder.matches(rawPassword, storedHash);
```

---

### Error Handling (Exception Hierarchy)

#### Structured Security Exception Hierarchy

**When to use:** CWE-200 (Information Exposure), CWE-209 (Error Message Information Leak) when stack traces or internal details leak to users.

**Define a security exception hierarchy:**
```java
public abstract class SecurityException extends RuntimeException {
    private final String userMessage;
    private final String internalDetail;

    protected SecurityException(String userMessage, String internalDetail, Throwable cause) {
        super(internalDetail, cause);
        this.userMessage = userMessage;
        this.internalDetail = internalDetail;
    }

    public String getUserMessage() {
        return userMessage;
    }
}

public class AuthenticationFailedException extends SecurityException {
    public AuthenticationFailedException(String internalDetail) {
        super("Authentication failed", internalDetail, null);
    }
}

public class AuthorizationDeniedException extends SecurityException {
    public AuthorizationDeniedException(String resource, String internalDetail) {
        super("Access denied", internalDetail, null);
    }
}

public class InputValidationException extends SecurityException {
    public InputValidationException(String field, String internalDetail) {
        super("Invalid input for field: " + field, internalDetail, null);
    }
}
```

#### Global Exception Handler (Spring)

```java
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(AuthenticationFailedException.class)
    public ResponseEntity<ErrorResponse> handleAuthFailure(AuthenticationFailedException ex) {
        log.warn("Authentication failed: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
            .body(new ErrorResponse("AUTHENTICATION_FAILED", ex.getUserMessage()));
    }

    @ExceptionHandler(AuthorizationDeniedException.class)
    public ResponseEntity<ErrorResponse> handleAuthzDenied(AuthorizationDeniedException ex) {
        log.warn("Authorization denied: {}", ex.getMessage());
        return ResponseEntity.status(HttpStatus.FORBIDDEN)
            .body(new ErrorResponse("ACCESS_DENIED", ex.getUserMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception ex) {
        log.error("Unhandled exception", ex);
        // Never expose internal details to the client
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
            .body(new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred"));
    }
}

public record ErrorResponse(String code, String message) {}
```

**Key points:**
- Log internal details (stack traces, SQL errors, file paths) server-side only.
- Return generic, user-safe messages to the client.
- Use different HTTP status codes for different error categories.
- Never include exception class names, stack traces, or system paths in API responses.

---

## Output Format

Return a JSON object:

```json
{
  "status": "success | partial | error",
  "language": "java",
  "framework": "<string: detected framework>",
  "java_version": "<string: detected Java version>",
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
  "imports_added": ["<string: new import statements>"],
  "dependencies_needed": [
    {
      "group_id": "<string>",
      "artifact_id": "<string>",
      "version": "<string>",
      "build_tool": "maven | gradle"
    }
  ],
  "configuration_changes": ["<string: any config changes needed>"],
  "warnings": ["<string: manual review items>"],
  "error": "<string: error description if status is error, null otherwise>"
}
```

### Success Indicator

`status` is `"success"` and all `changes` entries contain valid, compilable Java code.

### Failure Indicator

`status` is `"error"` with a description in the `error` field.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **Cannot detect framework** | Default to plain Java patterns. Set a warning recommending framework-specific review. |
| **Spring version incompatibility** | Check for `WebSecurityConfigurerAdapter` (Spring 5) vs `SecurityFilterChain` (Spring 6). Apply the version-appropriate pattern. |
| **javax vs jakarta namespace** | Detect from imports and build file. Java EE 8 and earlier use `javax.*`; Jakarta EE 9+ use `jakarta.*`. Apply the matching namespace. |
| **Missing dependency** | Note the required dependency in `dependencies_needed`. Do not modify `pom.xml` or `build.gradle` directly. |
| **Incompatible Java version** | If a pattern requires Java 11+ features (e.g., `var`, `Set.of()`) and the project uses Java 8, use Java-8-compatible alternatives. |
| **File uses Lombok** | Preserve Lombok annotations. Do not expand Lombok-generated code. |

## Constraints

- **Preserve compilation**: All generated code must compile against the project's declared Java version and dependencies.
- **Respect existing patterns**: If the project already uses a specific security library (e.g., Apache Shiro instead of Spring Security), prefer patterns compatible with that library.
- **No runtime execution**: Do not compile or execute Java code to test fixes.
- **Minimal diff**: Change only the code required for the security fix. Do not refactor unrelated code.
- **Thread safety**: Ensure fix patterns are thread-safe. Do not introduce shared mutable state. `Cipher` instances are not thread-safe and must not be stored in static fields.
- **Resource management**: Always use try-with-resources for `Connection`, `PreparedStatement`, `ResultSet`, `InputStream`, and `OutputStream` objects.
- **Tool usage**: Use `Read` for file reading, `Grep` for pattern searching, `Glob` for file discovery, `Edit` for applying fixes. Do not use `Bash` to compile or run code.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
