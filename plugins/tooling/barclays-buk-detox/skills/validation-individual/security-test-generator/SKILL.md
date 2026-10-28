---
name: security-test-generator
description: "Security Test Generator — Generate security-focused test cases for a vulnerability that has been successfully fixed. The tests prove that the fix is effective by attempting known attack payloads and asserting they are properly"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Security Test Generator
## Quick Start

This skill provides validation logic for confirming CWE fixes have been successfully applied.

```
# Loaded by detox-validator-agent during the Validate Fixes phase.
# Re-scans fixed files with Semgrep to confirm vulnerability is eliminated.
```



## Purpose

Generate security-focused test cases for a vulnerability that has been successfully fixed. The tests prove that the fix is effective by attempting known attack payloads and asserting they are properly blocked, while also verifying that legitimate inputs continue to work correctly.

## Inputs

- **cwe_id** (required, string): The CWE identifier (e.g., "CWE-89").
- **fixed_file** (required, string): Absolute path to the file that was fixed.
- **vulnerability_description** (required, string): Description of the vulnerability that was remediated.
- **language** (optional, string): Programming language of the fixed file.

## Steps

1. **Detect the project's test framework.**
   - Use `Glob` and `Read` to identify the test framework:
     - Python: Look for `conftest.py`, `pytest.ini`, `pyproject.toml` with `[tool.pytest]` -> **pytest**.
     - JavaScript/TypeScript: Look for `jest.config.*`, `vitest.config.*`, or `scripts.test` in `package.json`.
     - Java: Look for `pom.xml` (JUnit via Maven) or `build.gradle` (JUnit via Gradle).
     - Go: Native `testing` package.
     - C#: Look for `*.csproj` with test SDK references -> **xUnit/NUnit/MSTest**.
   - If no test framework is detected, default to the language's standard test library.

2. **Read the fixed file to understand the security pattern applied.**
   - Use `Read` to examine the fixed file.
   - Identify:
     - What sanitization/validation/encoding was added.
     - What functions or methods are the entry points.
     - What inputs are being validated.

3. **Generate 3-7 security test cases.**
   - **Negative tests** (attack payloads that must be blocked):
     - Generate test cases with known attack payloads specific to the CWE.
     - For CWE-89 (SQL Injection): `' OR 1=1 --`, `'; DROP TABLE users; --`, `1 UNION SELECT * FROM passwords`.
     - For CWE-79 (XSS): `<script>alert(1)</script>`, `" onload="alert(1)`, `javascript:alert(1)`.
     - For CWE-78 (OS Command Injection): `; rm -rf /`, `| cat /etc/passwd`, `` `whoami` ``.
     - For CWE-22 (Path Traversal): `../../../etc/passwd`, `..\\..\\..\\windows\\system32`.
     - For CWE-502 (Deserialization): Malicious serialized objects.
     - Assert that these inputs are rejected, sanitized, or rendered harmless.
   - **Positive tests** (legitimate inputs that must still work):
     - Generate 1-2 test cases with valid inputs that should pass through normally.
     - Assert that the function produces expected results for safe inputs.
   - **Boundary tests** (edge cases):
     - Generate 1 test case for edge cases like empty strings, very long inputs, unicode characters.

4. **Place tests in the correct location.**
   - Create tests in `tests/security/` (Python), `__tests__/security/` (JS/TS), `src/test/.../security/` (Java), or `security_test.go` (Go).
   - Name the test file to include the CWE ID: e.g., `test_cwe_089_sql_injection.py`.
   - Include the CWE ID in individual test function names for traceability.

5. **Write the test file.**
   - Use `Write` to create the test file.
   - Include a header comment explaining:
     - Which CWE this tests.
     - Which file contains the fix.
     - That these are auto-generated security regression tests.

6. **Syntax-check and run the generated tests.**
   - Use `Bash` to run only the newly created test file.
   - If tests fail due to import errors or syntax issues, fix and retry once.
   - Report the result (pass/fail) and number of tests.

## Output Format

Return a JSON object:

```json
{
  "status": "success",
  "test_file": "tests/security/test_cwe_089_sql_injection.py",
  "tests_generated": 5,
  "tests_passed": 5,
  "tests_failed": 0,
  "all_passed": true,
  "cwe_id": "CWE-89",
  "fixed_file": "src/db/queries.py"
}
```

On failure:

```json
{
  "status": "error",
  "error": "Description of what went wrong",
  "test_file": null,
  "all_passed": false
}
```

## Constraints

- **NEVER** modify the fixed source file — only create new test files.
- **NEVER** create tests that depend on external services or network access.
- **NEVER** create tests that could cause actual damage (no real file deletion, no real DB drops).
- Test payloads must be safe — they test that the application *rejects* malicious input, not that it *executes* it.
- Keep tests focused and fast — each test should complete in under 5 seconds.
- Use the project's existing test conventions (imports, fixtures, assertions) where possible.
- If the fixed file cannot be imported or tested in isolation, generate tests that call the public API of the module.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
