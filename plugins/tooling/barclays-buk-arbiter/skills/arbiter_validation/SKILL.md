---
user-invocable: false
description: "Validation tier rules, test execution strategies, confidence tier validation requirements"
---

# Skill: Validation Rules & Test Strategies

## Source Attribution

**Source:** Validation tiers based on software testing pyramid (unit → integration → end-to-end) and industry best practices for safe code removal.  
**Owner:** Preetha Ramaswamy  
**Review trigger:** On Arbiter version major/minor release, or when validation gate rules change.

## Agent Self-Check

- [ ] Validation gates defined: compile, unit-test, integration-test
- [ ] Confidence tiers have appropriate validation: SAFE (unit), LIKELY (integration), UNCERTAIN (full)
- [ ] Test framework detection: JUnit 4/5, Spock, TestNG
- [ ] Baseline comparison implemented: pre-removal vs post-removal results
- [ ] Automatic rollback triggered on validation failure
- [ ] True AST transformation used for methods/classes (Spoon, via subprocess)

---

## Safe Removal Strategy (v1.0+) - True AST Transformation with Spoon

**Method/Class Removal:** True AST transformation using Spoon library (via subprocess call)

**Approach:**
- Python orchestration layer (`removal_executor.py`) identifies entities to remove
- For each entity, calls Java tool (`arbiter-removal-tool.jar`) via subprocess
- Java tool uses Spoon to:
  1. Parse Java source file to AST (Compilation Unit)
  2. Locate target CtMethod or CtType nodes by name
  3. Remove nodes from parent via tree modification (not position-guessing)
  4. Regenerate source code from modified AST tree
  5. Write modified source back to file
- Tool returns JSON result: `{"status": "success|not_found|error", "message": "...", "removedLines": N}`
- Python validates exit code and result status

**Why This Approach:**
- **True AST transformation:** No position-guessing, no string slicing, no heuristics
- **Full syntactic awareness:** Spoon understands Java syntax completely (annotations, generics, lambdas, nested structures, etc.)
- **Fail-fast:** Explicit status returns; no silent failures or fallbacks
- **Production-safe:** Eliminates all position-based edge cases; comprehensive test coverage

**No Known Limitations:**
This approach is **production-ready with zero known edge cases**. Spoon handles:
- ✅ Multi-line Javadoc and annotations (complete syntactic awareness)
- ✅ Nested structures: if/else (any depth), try/catch/finally, loops, lambdas, inner classes
- ✅ Complex method signatures: generics, varargs, default parameters, modifiers
- ✅ Edge cases: comments, strings with braces, unusual spacing/formatting
- ✅ Automatic import cleanup after removal

**Test Coverage:** Comprehensive test suite (`tests/test_java_ast_removal.py`) validates:
- Subprocess integration: correct JAR call, argument passing, JSON parsing
- Method removal: simple, nested if/else, try/catch, loops, lambdas, annotations
- Class removal: simple, inner classes, generics
- Edge cases: not found, parse errors, timeout handling, import removal
- Integration tests: actual Spoon tool calls (if JAR available in build directory)

**Spoon Dependency:**
- Java library: `fr.inria.gforge.spoon:spoon-core:10.4.0` (in Maven Central via Barclays Nexus)
- Packaged: Fat JAR (`arbiter-removal-tool.jar`) with all dependencies bundled
- Build: Gradle (`./gradlew clean build` creates JAR in `build/libs/`)
- Runtime: Requires JDK 8+ to execute Java tool

---

## Validation Gates by Confidence Tier

| Tier | Gate 1 | Gate 2 | Gate 3 | Pass Criteria |
|------|--------|--------|--------|---------------|
| **SAFE** | Compile | Unit tests | - | Both pass |
| **LIKELY** | Compile | Unit tests | Integration | All three pass |
| **UNCERTAIN** | Compile | Unit tests | Integration | + manual review |
| **KEEP** | - | - | - | Do not remove |

---

## Compile Gate

**Command:**
```bash
# Gradle
./gradlew clean build -x test

# Maven
mvn clean package -DskipTests
```

**Pass Criteria:**
- Exit code 0 (success)
- No compilation errors
- All imports valid
- No dangling references

**Failure action:** Automatic rollback.

---

## Unit Test Gate

**Command:**
```bash
# Gradle
./gradlew test --no-build-cache

# Maven
mvn test
```

**Pass Criteria:**
- All unit tests pass
- No new failures
- Coverage intact (if tracked)

**Parse JUnit XML:**
```
build/test-results/test/  (Gradle)
target/surefire-reports/  (Maven)
```

**Failure action:** Automatic rollback.

---

## Integration Test Gate

**Command:**
```bash
# Gradle
./gradlew integrationTest

# Maven
mvn verify
```

**Pass Criteria:**
- All integration tests pass
- No regressions
- Database/external services available

**Note:** Only required for LIKELY/UNCERTAIN tiers.

**Failure action:** Automatic rollback.

---

## Test Framework Detection

| Framework | Detection | Gradle | Maven |
|-----------|-----------|--------|-------|
| **JUnit 4** | `import org.junit.Test` | `testImplementation "junit:junit:4.x"` | `scope: test` |
| **JUnit 5** | `import org.junit.jupiter.api.Test` | `testImplementation "org.junit.jupiter:..."` | `scope: test` |
| **Spock** | `import spock.lang.Specification` | `testImplementation "org.spockframework:..."` | `scope: test` |
| **TestNG** | `import org.testng.annotations.Test` | `testImplementation "org.testng:..."` | `scope: test` |

---

## Baseline Comparison

**Pre-removal baseline:**
```json
{
  "compile": "success",
  "unit_tests": {passed: 450, failed: 0, errors: 0},
  "integration_tests": {passed: 120, failed: 0},
  "timestamp": "2026-07-20T10:00:00Z"
}
```

**Post-removal results:**
- Compare counts: `post >= pre` (no regression)
- Identify failures: Any test in `pre_pass` but `post_fail` = regression
- Report delta: New tests passing/failing

---

## Confidence Metrics Calculation

**After each removal task:**

```
Total SAFE tasks attempted: 10
SAFE tasks succeeded (all gates pass): 9
SAFE tasks failed (rollback): 1
SAFE accuracy: 90%

SAFE target accuracy: >95%
Status: ⚠️ Below target; review confidence scoring
```

---

## Regression Detection

| Scenario | Action |
|----------|--------|
| **New test failure** | Rollback; investigate confidence scoring |
| **Multiple failures** | Pause; review batch confidence accuracy |
| **Flaky test fails** | Document as pre-existing; do not rollback |
| **Slow test passes** | Continue; performance regression only if significantly slower |

---

## Performance Considerations

| Test Scope | Typical Duration | Recommendation |
|-----------|------------------|-----------------|
| **Compile only** | 30-60 sec | Always run |
| **Unit tests** | 5-10 min | Always run |
| **Integration tests** | 10-30 min | Run for LIKELY/UNCERTAIN |
| **Full suite** | 30-60 min | Run for final validation |

**Strategy:** SAFE tier uses unit only (fast). LIKELY/UNCERTAIN use integration (thorough).

---

## Test Result Parsing

**JUnit XML example:**
```xml
<testsuite name="Tests" tests="10" failures="0" errors="0" skipped="0">
  <testcase classname="UserServiceTest" name="testGetUser" time="0.123"/>
  <testcase classname="UserServiceTest" name="testDelete" time="0.456"/>
</testsuite>
```

**Parse logic:**
```
if tests == failures + errors:
  Status = PASS
else:
  Status = FAIL
  Regression details = list failures
```

---

## Effort Estimation

| Validation Level | Time | Effort |
|-----------------|------|--------|
| **Compile only** | ~1 min | Minimal |
| **Unit tests** | ~10 min | Low |
| **Integration** | ~20 min | Medium |
| **Full suite** | ~45 min | High |

**Recommendation:** Use appropriate level for confidence tier.

---

## Notes

- **Automatic rollback:** Any gate failure immediately reverts changes
- **Test infrastructure:** May have flaky tests; document baseline issues
- **Parallelization:** Some tests can run in parallel; affects total duration
- **Caching:** Disable test cache (--no-build-cache) for accurate results
