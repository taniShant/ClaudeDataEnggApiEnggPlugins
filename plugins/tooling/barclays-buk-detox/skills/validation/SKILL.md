---
name: validation
description: Fix validation using Semgrep re-scanning, security test generation, build verification, regression checking, and fix completeness analysis
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Validation & Testing
## Quick Start

This skill provides validation logic for confirming CWE fixes have been successfully applied.

```
# Loaded by detox-validator-agent during the Validate Fixes phase.
# Re-scans fixed files with Semgrep to confirm vulnerability is eliminated.
```



## Purpose

Defines how to validate that CWE fixes are effective, how to generate security regression tests, how to verify builds still pass, and how to check for fix completeness. Used by the detox-validator-agent and the orchestrator's validation stage.

---

## Semgrep Re-scan Validation

### Purpose
Verify that a vulnerability fix eliminated the finding by re-scanning with Semgrep.

### Steps

1. **Run Semgrep on the fixed file:**
   ```bash
   semgrep --config auto --json {file_path} 2>/dev/null
   ```

2. **Parse JSON output:**
   - Results are in `results[]` array
   - Each result has: `check_id`, `path`, `start.line`, `end.line`, `extra.message`, `extra.severity`, `extra.metadata`

3. **Filter by CWE (if specified):**
   - Match `extra.metadata.cwe` containing the target CWE ID
   - Match `check_id` containing CWE-related keywords

4. **Determine verdict:**
   - Zero matching findings → `APPROVED`
   - Findings remain → `REJECTED` with details

### Output Format
```json
{
  "verdict": "APPROVED|REJECTED|SKIPPED",
  "file_path": "/path/to/file",
  "cwe_id": "CWE-89",
  "findings_after": 0,
  "remaining_findings": [],
  "message": "Explanation"
}
```

### Fallback (Semgrep unavailable)
If Semgrep is not installed:
1. Check: `which semgrep`
2. Attempt install: `pip install semgrep`
3. If still unavailable: return `SKIPPED` with installation instructions

---

## Security Test Generation

### Purpose
Generate test cases that prove a vulnerability fix is effective.

### Test Types

**Negative tests (attack payloads that must fail):**

| CWE | Test Payloads |
|-----|---------------|
| CWE-89 (SQLi) | `' OR '1'='1`, `'; DROP TABLE users; --`, `1 UNION SELECT * FROM passwords` |
| CWE-79 (XSS) | `<script>alert(1)</script>`, `" onload="alert(1)`, `javascript:alert(1)` |
| CWE-78 (Command Inj) | `; rm -rf /`, `\| cat /etc/passwd`, `` `whoami` `` |
| CWE-22 (Path Trav) | `../../../etc/passwd`, `..\\..\\windows\\system32`, `%2e%2e%2f` |
| CWE-502 (Deser) | Malicious serialized objects |
| CWE-611 (XXE) | `<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>` |
| CWE-918 (SSRF) | `http://169.254.169.254/`, `http://localhost/admin` |
| CWE-94 (Code Inj) | `__import__('os').system('id')`, `eval("1+1")` with side effects |

**Positive tests (valid inputs that must still work):**
- Normal expected inputs that the function handles
- Edge cases: empty strings, max-length inputs, unicode characters

**Boundary tests:**
- Empty input
- Very long input (buffer boundary)
- Special characters that are valid but tricky

### Test Framework Detection

| Indicator | Framework |
|-----------|-----------|
| `conftest.py`, `pytest.ini`, `[tool.pytest]` in pyproject.toml | pytest |
| `jest.config.*`, `vitest.config.*` | Jest/Vitest |
| JUnit dependency in pom.xml/build.gradle | JUnit 5 |
| `testing` package import | Go testing |
| `*.csproj` with test SDK | xUnit/NUnit |

### Test File Naming
- Python: `tests/security/test_cwe_{id}_{name}.py`
- JavaScript: `__tests__/security/cwe-{id}-{name}.test.js`
- Java: `src/test/.../security/Cwe{Id}{Name}Test.java`
- Go: `security_test.go` or `cwe_{id}_test.go`

### Test Structure (Fast Mode — 2-3 tests)
For CI/CD pipelines, generate minimal tests:
1. One negative test with the most common attack payload
2. One positive test with valid input
3. Optional edge case (empty string or boundary)

### Test Structure (Full Mode — 3-7 tests)
For comprehensive coverage:
1. 2-3 negative tests with different attack vectors
2. 1-2 positive tests with valid inputs
3. 1-2 boundary/edge case tests

---

## Build Verification

### Purpose
Verify that fixes don't break compilation or build.

### Build System Detection and Commands

| Indicator | Build System | Command |
|-----------|-------------|---------|
| `build.gradle`, `gradlew` | Gradle | `./gradlew build -x test` |
| `pom.xml` | Maven | `mvn compile -q` |
| `package.json` | npm | `npm run build` |
| `pyproject.toml`, `setup.py` | Python | `python -m py_compile {files}` |
| `go.mod` | Go | `go build ./...` |
| `Cargo.toml` | Rust | `cargo build` |
| `*.csproj` | .NET | `dotnet build` |

### Verification Steps
1. Detect build system from project root
2. Run build command with test skipped (compile only)
3. Capture exit code and output
4. Return `APPROVED` (exit 0) or `REJECTED` (non-zero)

### Build Failure Recovery
If build fails after fix:
1. Capture error output (last 50 lines)
2. Report to orchestrator for auto-fix retry
3. Auto-fix prompt includes: the error output + the fix that was applied
4. Constraint: auto-fix must NOT revert the security fix

---

## Test Suite Verification

### Purpose
Run existing tests to check for regressions introduced by fixes.

### Steps
1. Detect test framework (same as build detection)
2. Run test command:
   - Gradle: `./gradlew test`
   - Maven: `mvn test -q`
   - npm: `npm test`
   - Python: `pytest --tb=short`
   - Go: `go test ./...`
3. Capture results (pass/fail count, error output)
4. Return verdict

### Regression Handling
- Test failures do NOT revert fixes
- Failures are flagged in the PR body for reviewer attention
- The priority is security fix over passing tests (within reason)

---

## Fix Completeness Checking

### Purpose
Verify that a fix is complete — no partial remediations that leave residual vulnerability.

### Checks

1. **All instances fixed**: Grep for the same vulnerable pattern in the entire file. If other instances exist, the fix is incomplete.

2. **All inputs parameterized**: For injection CWEs, verify ALL user inputs in the function are properly handled, not just the flagged one.

3. **No bypass paths**: Check if there are alternative code paths that could reach the same vulnerability (e.g., different HTTP methods, different endpoints calling the same function).

4. **Import completeness**: Verify all required imports/dependencies for the fix are present.

5. **Error handling preserved**: Ensure error handling around the fixed code is still functional.

### Completeness Verdict
```json
{
  "complete": true,
  "checks_passed": ["all_instances", "all_inputs", "imports", "error_handling"],
  "checks_failed": [],
  "warnings": []
}
```

---

## Validation Pipeline Order

1. **Syntax check** — Does the file still parse correctly?
2. **Build check** — Does the project still compile?
3. **Semgrep re-scan** — Is the vulnerability eliminated?
4. **Completeness check** — Are all instances fixed?
5. **Test suite** — Do existing tests still pass?
6. **Security test generation** — (Optional) Generate regression tests

---

## Constraints

- Validation is READ-ONLY — never modify files
- Semgrep timeout: 120 seconds per file
- Build timeout: 600 seconds
- Test timeout: 600 seconds
- If Semgrep unavailable, validation is SKIPPED (not REJECTED)
- Test failures do NOT block fixes — they are informational
- Always report remaining findings with line numbers for manual review

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
