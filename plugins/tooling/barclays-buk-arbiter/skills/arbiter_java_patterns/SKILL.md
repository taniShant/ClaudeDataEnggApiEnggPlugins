---
user-invocable: false
description: "Java-specific code patterns, refactoring rules, and anti-patterns for dead code analysis"
---

# Skill: Java Patterns & Refactoring

## Source Attribution

**Source:** Java language patterns from JDK specifications, Spring Framework conventions, and industry best practices for safe code removal.  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Java language release, Spring Framework major release, or when Arbiter removal patterns change.

## Agent Self-Check

- [ ] Removal patterns handle: class deletion, method removal, field cleanup, import pruning
- [ ] Circular dependencies detected and flagged
- [ ] Private class removal vs public API removal handled differently
- [ ] Test utilities removal uses different validation rules
- [ ] Side-effect patterns documented (System.out.println in <init>, etc.)

---

## Quick-Reference: Safe Removal Patterns

### Private Methods (✅ Safe)
```java
// SAFE to remove (confidence 3.5-4.0)
private void unusedHelper() { ... }
```

### Private Classes (✅ Safe)
```java
// SAFE to remove (confidence 3.5-4.0)
private static class UnusedConfig { ... }
```

### Unused Imports (✅ Safe)
```java
// SAFE to remove (confidence 4.0)
import com.unused.Class;  // Not used anywhere
```

### Test Utility (✅ Likely)
```java
// LIKELY safe (confidence 2.5-3.0, test-only)
public static String testHelper() { ... }
// Called only from test code; probably removable
```

### Public API Method (⚠️ Risky)
```java
// UNCERTAIN (confidence 1.5-2.0, public)
public User fetchUser(String id) { ... }
// Public method; may be called from outside repo
```

---

## Removal Workflow: By Entity Type

| Entity | Example | Safe? | Confidence | Action |
|--------|---------|-------|-----------|--------|
| **Private method** | `private void helper()` | ✅ | 3.5-4.0 | Remove directly |
| **Private class** | `private static class X` | ✅ | 3.5-4.0 | Remove entire class/file |
| **Unused import** | `import unused.*` | ✅ | 4.0 | Remove import line |
| **Public method** | `public void method()` | ⚠️ | 1.5-2.5 | Review; may have external callers |
| **@Deprecated** | `@Deprecated public void old()` | ✅ | 3.0-4.0 | Bonus confidence; review docs |
| **Test utility** | Test helper in src/ | ✅ | 2.5-3.0 | Different validation gates |
| **Interface method** | `interface I { void m(); }` | 🔴 | <1.0 | Do not remove (public API) |

---

## Anti-Patterns: High False Positive Risk

| Anti-Pattern | Risk | Why | Mitigation |
|--------------|------|-----|-----------|
| **Reflection** | 🔴 Critical | `forName()`, `getMethod()` | Flag if reflection detected; lower confidence |
| **Serialization** | 🔴 Critical | `readObject()`, `writeObject()` | Flag serializable classes; do not remove |
| **JNI methods** | 🔴 Critical | `native` keyword | Flag native methods; do not remove |
| **Synchronized blocks** | ⚠️ Medium | May have subtle threading logic | Extra review; integration tests |
| **Custom annotations** | ⚠️ Medium | Unknown annotation processors | Flag custom annotations; lower confidence |

---

## Hexagonal Architecture Layers

**Allowed dependency directions:**
```
UI/Controller → Service → Repository/Gateway → Data
  ↓
Controllers should not call Repository directly
```

**Violations flagged as risky:**
- Service calling UI layer
- Repository calling Service (backward dependency)
- Cross-layer concrete references

**Fix:** Refactor to proper layer boundaries before removal.

---

## Side Effects Detection

| Pattern | Side Effect | Action |
|---------|------------|--------|
| `System.out.println()` | Stdout during init | Flag; may be logging initialization |
| `Thread.currentThread()` | Threading logic | Flag; thread-local state possible |
| `WeakReference`, `PhantomReference` | GC interaction | Flag; subtle memory behavior |
| `setAccessible(true)` | Reflection on private | Flag; may invoke private code |

---

## Effort Estimation by Pattern

| Pattern | Removal Effort | Validation Effort |
|---------|----------------|------------------|
| Unused import | <1 min | Compile check |
| Private method | 2 min | Compile + unit tests |
| Private class | 5 min | Compile + unit tests |
| Test utility | 3 min | Compile + test suite |
| Public method | 15 min | Compile + integration tests + review |
| @Deprecated method | 10 min | Compile + review migration docs |

---

## Removal Checklist

Before removing an entity, verify:

- [ ] Confidence score ≥ 1.0 (else KEEP)
- [ ] No reflection patterns detected
- [ ] No native methods in class
- [ ] No serialization methods (readObject, writeObject)
- [ ] Not in anti-pattern list
- [ ] No circular dependencies
- [ ] Comments reviewed for external documentation
- [ ] Tests pass pre-removal (baseline)
- [ ] Dry-run shows no unexpected side effects

---

## Post-Removal Validation

After removing an entity:

| Check | Pass Criteria |
|-------|--------------|
| **Compile** | `gradlew build -x test` exits 0 |
| **Unit tests** | All unit tests pass |
| **Integration tests** | (LIKELY/UNCERTAIN) All integration tests pass |
| **Imports** | No unused imports left |
| **References** | No dangling references |

**Automatic rollback** if any check fails.

---

## Examples

### Example 1: Remove Unused Private Method (SAFE)

```java
// Before
public class UserService {
    public User getUser(String id) { ... }
    
    private void legacyLogging() {  // ← unused
        System.out.println("...");
    }
}

// After
public class UserService {
    public User getUser(String id) { ... }
}

Confidence: 3.8 (private, no side effects)
Action: Direct removal, compile + unit test
```

### Example 2: Remove @Deprecated Public Method (LIKELY)

```java
// Before
@Deprecated
public User fetchUserLegacy(String id) {  // ← only legacy references
    return legacyService.fetch(id);
}

// After
// Method removed entirely
// All callers refactored to newMethod()

Confidence: 3.2 (@Deprecated bonus, public review needed)
Action: Review usage, refactor callers, remove
Validation: Compile + full test suite + integration tests
```

---

## Notes

- **Fallback:** If uncertain, keep code; better to have dead code than break functionality
- **Framework magic:** Spring/JUnit/Reflection may invoke code invisibly
- **External callers:** Public methods may be called from outside repository
- **Serialize carefully:** Serialization protocol is fragile; keep compatible fields
