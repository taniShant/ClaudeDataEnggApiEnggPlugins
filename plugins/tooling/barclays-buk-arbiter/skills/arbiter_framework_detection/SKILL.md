---
user-invocable: false
description: "Framework and library detection patterns for Spring, JUnit, and common Java annotations"
---

# Skill: Framework Detection Patterns

## Source Attribution

**Source:** Framework patterns extracted from Arbiter call-graph analysis; annotations from Spring Framework, JUnit, and common Java libraries.  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Spring Framework major/minor release, JUnit version bump, or Arbiter framework detection changes.

## Agent Self-Check

- [ ] Spring entry points detected: @SpringBootApplication, @Service, @Controller, etc.
- [ ] Testing frameworks recognized: @Test, JUnit 4/5, Spock, TestNG
- [ ] Scheduled/async patterns detected: @Scheduled, @Async, @EventListener
- [ ] Reflection patterns handled: may lower confidence if detected
- [ ] Framework detection provides "cannot resolve via static analysis" flag

---

## Framework Patterns: Detection Reference

### Spring Framework

| Pattern | Regex | Meaning |
|---------|-------|---------|
| `@SpringBootApplication` | `@SpringBootApplication` | Application entry point |
| `@Service` | `@Service\|@Component\|@Repository` | Bean managed by Spring |
| `@RestController` | `@RestController\|@Controller` | HTTP endpoint |
| `@GetMapping` | `@GetMapping\|@PostMapping\|@PutMapping\|@DeleteMapping` | HTTP handler |
| `@Scheduled` | `@Scheduled` | Timer/scheduled task (entry point) |
| `@EventListener` | `@EventListener` | Event-driven (entry point) |
| `@Async` | `@Async` | Async method (entry point) |
| `@Bean` | `@Bean` | Factory method (potential entry point) |

### JUnit Testing

| Pattern | Regex | Meaning |
|---------|-------|---------|
| `@Test` | `@Test` | Test method (entry point) |
| `@BeforeEach` | `@BeforeEach\|@Before` | Test setup (entry point) |
| `@AfterEach` | `@AfterEach\|@After` | Test teardown (entry point) |
| `@BeforeClass` | `@BeforeClass\|@BeforeAll` | Static setup (entry point) |
| `@Parameterized` | `@ParameterizedTest\|@RunWith(Parameterized)` | Parameterized test |
| `@Nested` | `@Nested` | Nested test class |

### Other Common Patterns

| Pattern | Regex | Meaning |
|---------|-------|---------|
| `public interface` | `public\s+interface\s+\w+` | Public API (may be implemented externally) |
| Implements interface | `implements\s+\w+` | Possible override (lower confidence) |
| Override method | `@Override` | Overriding parent/interface method |
| Deprecated | `@Deprecated` | Marked for removal (increase confidence) |
| Reflection | `forName\|getMethod\|getDeclaredMethod` | Dynamic invocation (cannot resolve) |
| ServiceLoader | `ServiceLoader.load` | Dynamic loading (cannot resolve) |

---

## Analyzer Tier Recommendation

| Primary Language | Tier | Accuracy | Speed | Notes |
|------------------|------|----------|-------|-------|
| **Java (Gradle/Maven)** | Compiled | 90-98% | Slow | Requires compilation; full type resolution |
| **Python** | AST | 85-95% | Fast | Built-in ast module; no compilation |
| **JavaScript/TypeScript** | AST | 85-95% | Fast | @babel/parser; no compilation |
| **Go** | AST | 85-95% | Fast | go/parser available |
| **Ruby, PHP, C++** | Grep | 60-75% | Very fast | Fallback; regex-based; many false positives |

---

## Confidence Deduction Rules by Framework

### Spring-Annotated Methods

```
Base confidence: 4.0

If method has:
  @Service, @Component, @Repository      → -0.5 (bean managed by Spring)
  @Scheduled, @Async, @EventListener      → -1.0 (must not remove; entry point)
  @GetMapping, @PostMapping, etc.         → -1.0 (HTTP handler; entry point)
  @Bean                                   → -0.7 (factory; may be external dependency)

Result: Typically <2.0 (KEEP or UNCERTAIN)
```

### Test Methods

```
Base confidence: 3.0

If method has:
  @Test, @BeforeEach, @AfterEach         → -0.5 (test entry point; probably safe)
  
If method is only called by test code:
  Confidence reduced by additional -0.2 (test-only usage)

Result: Typically 2.5-3.0 (SAFE/LIKELY)
```

### Public Interface Methods

```
Base confidence: 3.5

If method is in:
  public interface                        → -0.5 (may be implemented elsewhere)
  Has @Override                           → -0.2 (possibly overriding external)

Result: Typically 2.8-3.0 (LIKELY)
```

---

## False Positive Patterns

| Pattern | Risk | Mitigation |
|---------|------|-----------|
| **Spring TaskScheduler registration** | Method called via TaskScheduler, not direct invocation | Flag methods in @EnableScheduling classes |
| **AOP proxies** | Method called via runtime proxy, not visible in source | Flag methods with @Aspect, @Transactional |
| **Reflection-based calling** | Dynamic method invocation via Class.forName | Flag if reflection patterns detected |
| **External lib loading** | ServiceLoader or plugin architecture | Flag if ServiceLoader.load detected |

---

## Decision Tree

```
1. Is class/method annotated with @Service, @Repository, @Controller?
   → YES: Lower confidence (-0.5), likely entry point
   → NO: Continue

2. Is method annotated with @Scheduled, @Async, @EventListener?
   → YES: Critical entry point; do not remove (KEEP)
   → NO: Continue

3. Is method annotated with @Test, @BeforeEach?
   → YES: Probably safe; confidence 2.5-3.0 (LIKELY/SAFE)
   → NO: Continue

4. Is class public and implements interface?
   → YES: Lower confidence (-0.5), may be called externally
   → NO: Continue

5. Is method marked @Deprecated?
   → YES: Increase confidence (+0.5), good candidate for removal
   → NO: Continue
```

---

## Fallback Strategy

If framework detection fails or is inconclusive:
- **AST-based analysis** (if available): Parse code structure
- **Grep-based analysis** (last resort): Regex patterns for calls
- **Manual review required**: High uncertainty; ask engineer

---

## Build System Detection

| Build System | Files | Detection |
|--------------|-------|-----------|
| **Gradle** | `build.gradle`, `build.gradle.kts`, `gradle.properties` | Primary for modern Java |
| **Maven** | `pom.xml` | Traditional Java; XML-based |
| **Ant** | `build.xml` | Legacy; rare in modern projects |
| **Bazel** | `BUILD`, `WORKSPACE` | Monorepo/Google projects |

---

## Notes

- Framework detection is **heuristic-based**; some false positives expected
- **Compiled analysis** (Spoon) most reliable but slow
- **Fallback gracefully** to AST/Grep if compilation fails
- **Document framework assumptions** in analysis report
