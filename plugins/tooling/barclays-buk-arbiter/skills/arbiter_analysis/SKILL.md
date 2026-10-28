---
user-invocable: false
description: "Dead code analysis rules, call graph heuristics, and confidence scoring methodology"
---

# Skill: Dead Code Analysis Rules

## Source Attribution

**Source:** Dead code analysis heuristics from traditional static analysis tools, compiler dead code warnings, and call graph reachability algorithms.  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Arbiter version major/minor release, or when confidence scoring rules change.

## Agent Self-Check

- [ ] Entry point detection: main, @SpringBootApplication, @Test, HTTP endpoints, interfaces
- [ ] Call graph traversal: BFS from entry points
- [ ] Confidence scoring: Applied consistently, deductions documented
- [ ] False positive analysis: Patterns that lower confidence captured
- [ ] Caching: Call graph cached to avoid redundant analysis

---

## Dead Code Definition

**An entity is dead code if:**
1. It is not reachable from any entry point
2. It is not called/used by other entities
3. It has zero incoming edges in the call graph

---

## Entry Points (Always Reachable)

| Entry Point | Pattern |
|-------------|---------|
| **main()** | `public static void main(String[] args)` |
| **Spring Boot** | `@SpringBootApplication` |
| **Controllers** | `@RestController`, `@Controller` methods with `@GetMapping`, etc. |
| **Scheduled** | `@Scheduled`, `@Async`, `@EventListener` |
| **Tests** | `@Test`, `@BeforeEach`, `@AfterEach` |
| **Interfaces** | Public interface methods (may be implemented externally) |
| **Overrides** | Methods overriding parent/interface (may be called externally) |

---

## Call Graph Algorithm

```
1. Extract entry points → mark as REACHABLE

2. For each REACHABLE entity:
   a. Find all entities it calls/instantiates/accesses
   b. Mark those as REACHABLE
   c. Repeat until no new entities marked

3. All unreachable entities → candidates for removal
```

---

## Confidence Scoring: Deduction Matrix

| Deduction | Amount | Applies to |
|-----------|--------|-----------|
| **Public visibility** | -0.5 | Any public class/method/field |
| **Spring annotation** | -0.5 | @Service, @Component, @Repository, etc. |
| **@Scheduled/@Async** | -1.0 | Task/event-driven entry points |
| **@Deprecated** | +0.5 | Explicitly marked for removal |
| **Framework annotation** | -0.5 | @Test, @Bean, custom annotations |
| **Reflection detected** | -1.0 | If `forName()`, `getMethod()` found |
| **Comment mentions** | -0.2 | If external docs reference entity |
| **Test-only usage** | -0.2 | Called only from test code |
| **Interface impl** | -0.2 | Implements interface (may override) |

**Formula:** Start 4.0 → apply deductions → clamp 0-4

---

## Quick Categorization

```
if confidence >= 3.0:
  Category = SAFE
  Batch size = 5
  Effort = 0.5-1h

else if confidence >= 2.0:
  Category = LIKELY
  Batch size = 3
  Effort = 1-2h
  Requires review + integration tests

else if confidence >= 1.0:
  Category = UNCERTAIN
  Batch size = 1
  Effort = 2-4h
  Requires investigation + full tests

else (confidence < 1.0):
  Category = KEEP
  Action = Do not remove
```

---

## Heuristics for Lowering Confidence

| Heuristic | Deduction | Rationale |
|-----------|-----------|-----------|
| **Widely imported** | -0.2 | Many files import; may be used indirectly |
| **Large method** | -0.1 | Complex methods more likely to have hidden usage |
| **Generic names** | -0.1 | `process()`, `handle()` may be called via reflection |
| **Old code** | +0.2 | Ancient dead code less likely to be used |
| **Mentioned in TODOs** | -0.3 | Comments suggest future use planned |

---

## Cache Strategy

**Cache key:** `hash(source_files + language + framework)`

**Cache entry:**
```json
{
  "call_graph": { "nodes": [...], "edges": [...] },
  "reachable": ["main", "UserService.getUser", ...],
  "candidates": ["UserService.legacy", ...],
  "confidence_scores": {"entity": 3.7, ...},
  "cache_timestamp": "ISO8601",
  "valid_until": "source file change detection"
}
```

**Benefits:**
- Reuse call graph across multiple removal plans
- 90% token savings on repeat analysis
- No redundant compilation/AST parsing

---

## Special Cases

| Case | Handling |
|------|----------|
| **Circular dependency** | Flag both as risky; may need refactoring first |
| **Bi-directional call** | Mark as KEEP; indicates mutual dependency |
| **Generic type bound** | Lower confidence; may satisfy type constraint |
| **Default methods** | Lower confidence; interface default may be called |

---

## False Positive Patterns (Common Mistakes)

| Pattern | False Positive | Why | Fix |
|---------|---|------|-----|
| **Spring TaskScheduler** | Method looks unused but called via scheduler | Regex doesn't catch indirect invocation | Check @EnableScheduling; lower confidence |
| **JUnit Parameterized** | Test helper seems unused | Called by @ParameterizedTest mechanism | Flag test classes; don't remove |
| **Custom annotations** | Processor invokes method invisibly | Annotation processor is runtime | Flag custom annotations; lower confidence |
| **Reflection patterns** | Dynamic invocation via forName | Cannot resolve statically | Flag reflection; confidence -1.0 |

---

## Metrics

Track across multiple runs:

| Metric | Goal | Calculation |
|--------|------|-------------|
| **Accuracy** | >95% | (successful removals / total removals) |
| **False positive rate** | <5% | (removals that broke tests / total) |
| **Analysis time** | <15 min | Total time for analyze phase |
| **Cache hit rate** | >50% (repeat runs) | (cache hits / total queries) |

---

## Notes

- **Conservative:** Start high confidence (4.0); apply deductions for uncertainty
- **Document assumptions:** Unknown frameworks/patterns = lower confidence
- **Iterative:** Each failure is a learning opportunity; improve scoring over time
