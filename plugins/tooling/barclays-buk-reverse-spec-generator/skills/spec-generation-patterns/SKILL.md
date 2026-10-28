---
name: spec-generation-patterns
description: >
    Code extraction patterns for reverse-spec-generator: language-specific rules
    for detecting entities, behaviors, rules, and constraints from Python, Java,
    JavaScript/TypeScript, and generic code. Load when running /generate-spec.
user-invocable: false
---

# Spec Generation Patterns

> **Source:** Reverse Spec Generator — Generation Patterns and Format Reference (internal)
> **Owner:** Preetha Ramaswamy / BUK Quality Engineering
> **Review trigger:** When new language support is added or extraction heuristics are revised
> **Status:** Published
> Source documents are Internal — Restricted.

---

## Quick Start

```
Command: /generate-spec
Agent: reverse-spec-generator-agent (Step 2)
Load: Loaded when extracting specs from source code
Use: Language-specific rules for detecting entities, behaviors, rules, constraints (Python, Java, JS/TS)
Model: sonnet (pattern recognition and confidence scoring)
```

---

## 1. Core Principle

**Functionality implemented, not functionality derived.**

The spec documents what code executes — not what code signals it might do. Names, annotations, access modifiers, and documentation are navigation aids to locate code. The specification comes from reading the method body and tracing the call chain.

Concretely:
- A method named `createUser` may not create a user — read the body
- An annotation `@PostMapping` identifies an endpoint location — read the method body for behaviour
- An interface named `StoredProcedureRepository` may have a JPA implementation — read the implementing class
- A constant named `SESSION_TIMEOUT` may never be used — verify it is referenced in logic before extracting as a constraint
- A `@NotNull` annotation declares intent — verify validation runs on that code path before extracting as an invariant

**Confidence scoring measures documentation richness, not extraction correctness.** A fully-documented method with wrong JavaDoc scores 1.0. An undocumented method whose body is clear scores 0.5. Always read the body regardless of score.

---

## 2. Universal Extraction Rules

### 2.1 What Maps to What

| Code construct | Spec section |
|---|---|
| Class / record / interface / type definition | `entities` |
| Public method / function with docstring | `behaviors` |
| Guard clause (if cond: raise Exception) | `rules` |
| Named constant (UPPER_CASE) | `constraints` (limit or timeout) |
| Assert statement | `constraints` (invariant) |
| External service call / import | `constraints` (dependency) |

### 2.2 Confidence Scoring

| Score | Meaning | Example |
|---|---|---|
| 1.0 | Full docstring with all details | Complete JavaDoc or Google-style docstring |
| 0.8 | Docstring + type hints | Method with partial documentation |
| 0.6 | Partial documentation | Name + return type only |
| 0.5 | Name-only inference | Method name without any docs |

Extractions below threshold (default: 0.5) are excluded. Lower with `confidence_threshold=0.3` to include more speculative results.

### 2.3 Inference Anti-Patterns

The following are **never** sufficient on their own to produce a spec entry. Each requires reading the actual implementation:

| Signal | Why it is insufficient | What to do instead |
|---|---|---|
| Class / method / constant name | Names describe intent, not execution | Read the body |
| Annotation presence (`@NotNull`, `@Cacheable`, `@Transactional`) | Declares intent; runtime enforcement depends on context | Verify the annotation is active on that code path |
| Interface or abstract class declaration | Hides which implementation runs | Follow to the implementing class |
| Package / file location | Organisational convention, not a contract | Read the class regardless of where it sits |
| Import statement | Does not prove the dependency is called | Verify the dependency is invoked in the body |
| `public` / `protected` visibility | Accessibility is not the same as user-facing behaviour | Read the body to confirm it is a meaningful behaviour |
| Boilerplate name pattern (`getX`, `isX`, `setX`) | Usually boilerplate, but not always | Scan the body before excluding; extract if it contains logic beyond simple field access |

---

## 3. Python Patterns

### 3.1 Entities

```python
@dataclass
class User:
    """A system user with credentials."""
    id: str                           # → property type: string
    email: str                        # → property type: string
    status: str = "active"           # → property with default value
    roles: List[str] = field(default_factory=list)  # → type: array
    metadata: Optional[dict] = None  # → type: object, required: false
```

### 3.2 Behaviors

```python
def authenticate_user(email: str, password: str) -> Optional[AuthToken]:
    """
    Authenticate user with email and password.

    Args:
        email: User email address
        password: User password

    Returns:
        AuthToken if successful, None otherwise

    Raises:
        ValueError: If email format is invalid
    """
```

Supported docstring styles: **Google** (`Args:`, `Returns:`, `Raises:`), **NumPy** (`Parameters`, `Returns`, `Raises`).

### 3.3 Rules (guard clauses)

```python
if not email or "@" not in email:
    raise ValueError("Invalid email format")
# → Rule: "email_must_have_at_character"
```

### 3.4 Constraints (constants)

```python
MAX_LOGIN_ATTEMPTS = 5      # → limit
MIN_PASSWORD_LENGTH = 12    # → limit
SESSION_TIMEOUT = 3600      # → timeout (seconds)
```

### 3.5 Decorators

| Decorator | Effect |
|---|---|
| `@property` | Read-only accessor behavior |
| `@abstractmethod` | Required interface method |
| `@staticmethod` | Factory or utility behavior |

---

## 4. Java Patterns

### 4.1 Entities and Annotations

```java
public class User {
    @NotNull         // → invariant constraint
    private String id;

    @Email @NotNull  // → rule (must be valid email) + invariant
    private String email;

    @Size(min = 12, max = 128)  // → limit constraint
    private String password;
}
```

| Annotation | Extraction result |
|---|---|
| `@NotNull` | invariant constraint |
| `@Email` | rule (must be valid email) |
| `@Size(min,max)` | limit constraint |
| `@Min` / `@Max` | limit constraint |

### 4.2 Behaviors (JavaDoc)

```java
/**
 * Authenticate user with email and password.
 *
 * @param email User email address
 * @param password User password
 * @return Authentication token
 * @throws IllegalArgumentException if email already exists
 */
public String authenticateUser(String email, String password) { }
```

JavaDoc tag mapping:
- `@param` → `given` / `when` clauses
- `@return` → `then` clause
- `@throws` → rule

### 4.3 Access Modifiers

Only `public` elements are extracted. `private` and `protected` are skipped.

### 4.4 Spring Annotations

Spring annotations identify the *location* and *HTTP verb* of an endpoint, not its behaviour. The HTTP verb belongs in the `when` clause. The behaviour description — what the endpoint actually does — comes from reading the method body and the service it delegates to.

```java
@RestController
@RequestMapping("/api/users")
public class UserController {
    @PostMapping
    public User createUser(@RequestBody User user) { }  // HTTP verb: POST — read body for behaviour

    @GetMapping("/{id}")
    public User getUser(@PathVariable String id) { }    // HTTP verb: GET — read body for behaviour
}
```

### 4.5 Java Operational Rules

These rules apply specifically to Java extraction and override general heuristics where they conflict.

**Entity fields — include all, annotate optionality**
Extract every field in an entity class regardless of whether it carries `@NotNull`, `@NotBlank`, or any other validation annotation. Fields without a required-constraint annotation are `required: false`. Never filter fields by annotation presence.

**Call chain traversal — follow implementations in execution order**
When reading a service, repository, or handler, always follow through to the implementing class. Trace method calls in the order they execute to identify the primary data source (first retrieval call) versus enrichment (subsequent calls that augment retrieved data). Never stop at an interface or abstract class. Never use the interface name to infer what runs.

**Error code mapping — read the enum, never infer from the name**
When error or exception behaviour is referenced, locate the `ErrorCode` / `ErrorCodes` enum or equivalent mapping class and read the HTTP status assignment directly (e.g. `NO_LOCATION_FOUND("006", NOT_FOUND, false)` → 404). Never infer an HTTP status from an error name.

**Configuration profile — prefer production values**
When extracting configuration constraints, read `application.properties` (base profile) or `application-prod.properties`. Ignore `application-sit.properties`, `application-test.properties`, and `application-local.properties`. Note the profile used if values are environment-specific.

**Constraint scope — API consumer relevance only**
Only extract constraints that are meaningful to an API consumer: request / response size limits, rate limits, business rule thresholds, and functional timeouts. Do not extract infrastructure configuration: connection pool sizes, circuit breaker thresholds, retry counts, thread pool sizes, or framework tuning parameters.

---

## 5. JavaScript / TypeScript Patterns

### 5.1 Entities

```typescript
interface User {
    id: string;
    email: string;
    status: "active" | "inactive" | "suspended";  // → enum constraint
    roles?: string[];  // → type: array, required: false
}
```

### 5.2 Behaviors (JSDoc)

```javascript
/**
 * Create a new user account.
 * @param {string} email - User email address
 * @param {string} password - User password (min 12 characters)
 * @returns {Promise<User>} Created user object
 * @throws {Error} If email already exists
 */
async function createUser(email, password) { }
```

### 5.3 Constants

```javascript
const MAX_LOGIN_ATTEMPTS = 5;     // → limit
const SESSION_TIMEOUT = 3600;     // → timeout
const PASSWORD_MIN_LENGTH = 12;   // → limit
setTimeout(() => { }, 5000);      // → timeout (5000ms)
```

---

## 6. Writing Code for Better Extraction

| Practice | Example |
|---|---|
| Add docstrings | `def create_user(email): """Create a new user account."""` |
| Use type hints | `def create_user(email: str) -> User:` |
| Name constants clearly | `MAX_PASSWORD_LENGTH = 128` (not `pwd_max = 128`) |
| Use guard clauses | `if not email: raise ValueError("Email required")` |
| Group related methods | Keep all auth behaviors in `AuthService` |

---

## 7. Language Detection

Language is detected by file extension (`.py`, `.java`, `.js`, `.ts`), shebang line, or language keywords. Override by specifying `# Language: python` in the command invocation.

---

## Agent Self-Check

When applying this skill to generate or validate a spec, confirm:

**Implementation-first checks (must pass before any extraction is accepted)**
- [ ] Every extracted behavior comes from reading a method body, not from its name or signature alone
- [ ] Every entity has all fields extracted, including optional ones (`required: false`) — no fields filtered by annotation absence
- [ ] Every repository or service interface has been followed to its implementing class before describing what it does
- [ ] Call chains have been traced in execution order; primary data source and enrichment steps are correctly distinguished
- [ ] Any error / exception behaviour references an `ErrorCode` enum or explicit status mapping — HTTP status not inferred from error name
- [ ] Configuration values come from `application.properties` or `application-prod.properties` — test/SIT profiles excluded
- [ ] Constraints are limited to API consumer concerns (size limits, rate limits, business thresholds, functional timeouts) — infrastructure config excluded
- [ ] Boilerplate-named methods (`getX`, `isX`, `setX`) have been scanned before exclusion; any containing logic beyond field access are included

**Extraction completeness checks**
- [ ] Language has been detected or specified (Python / Java / JavaScript / generic)
- [ ] Guard clauses (if/raise, if/throw) have been mapped to rules where the exception is not caught upstream
- [ ] UPPER_CASE module constants have been evaluated as constraints only where they are referenced in logic
- [ ] `@dataclass` fields (Python) or class properties (Java) have been mapped to entity properties
- [ ] JavaDoc / JSDoc tags used as supplementary context only: @param→given, @return→then, @throws→rule
- [ ] Extracted entity names are PascalCase and behavior names are snake_case
- [ ] Generated spec passes the bdd-specification skill self-check

---

## Areas for Specialist Extension

- **Kotlin** — Android and backend Kotlin extraction patterns
- **Swift** — iOS Swift class and protocol extraction
- **Go** — struct, interface, and function extraction
- **Legacy Java** — Pre-annotation Java with XML-based config extraction
