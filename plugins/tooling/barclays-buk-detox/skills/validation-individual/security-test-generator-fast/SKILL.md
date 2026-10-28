---
name: security-test-generator-fast
description: "Security Test Generator (Fast Mode) — Generate minimal but effective security test cases for fixed vulnerabilities. Fast mode prioritizes quick generation and execution over comprehensive coverage, suitable for CI/CD pipelines. "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Security Test Generator (Fast Mode)
## Quick Start

This skill provides validation logic for confirming CWE fixes have been successfully applied.

```
# Loaded by detox-validator-agent during the Validate Fixes phase.
# Re-scans fixed files with Semgrep to confirm vulnerability is eliminated.
```



## Purpose

Generate minimal but effective security test cases for fixed vulnerabilities. Fast mode prioritizes quick generation and execution over comprehensive coverage, suitable for CI/CD pipelines.

## Inputs

- **cwe_id** (required, string): The CWE identifier (e.g., "CWE-89").
- **fixed_file** (required, string): Absolute path to the file that was fixed.
- **vulnerability_description** (required, string): Description of the vulnerability that was remediated.

## Steps

1. **Auto-detect test framework** (same as full version).

2. **Generate 2-3 minimal tests** (reduced from 3-7):
   - **One negative test**: Single known attack payload for the CWE (reject/sanitize assertion).
   - **One positive test**: Valid input that must still work (assert normal behavior).
   - **Optional edge case**: Empty string or boundary test if simple.

3. **Use CWE-specific minimal payloads**:
   - CWE-89 (SQL): `' OR '1'='1`
   - CWE-79 (XSS): `<script>alert(1)</script>`
   - CWE-78 (Command Injection): `; echo pwned`
   - CWE-22 (Path Traversal): `../../../etc/passwd`
   - CWE-312 (Missing Encryption): Check if data is encrypted
   - CWE-306 (Rate Limiting): Check if rate limit is enforced
   - CWE-290 (Auth Bypass): Check if unauthenticated request is rejected
   - CWE-367 (Race Condition): Check if operation is atomic
   - CWE-532 (Log Leakage): Check if sensitive data is not logged

4. **Place tests in standard location**:
   - `tests/security/test_cwe_XXX.py` (Python)
   - `src/test/java/.../SecurityTestCWE_XXX.java` (Java)
   - Similar for other languages

5. **Write minimal test file** (no complexity, no imports beyond test framework):
   - 1 test class/file
   - 2-3 test methods
   - Direct assertions (no complex setup)

6. **Quick syntax check only** (no execution):
   - Verify file exists and is readable
   - Do NOT attempt to run tests (skip execution to save time)
   - Return success if file was created

## Output Format

```json
{
  "status": "success",
  "test_file": "tests/security/test_cwe_089.py",
  "cwe_id": "CWE-89",
  "tests_count": 2,
  "generation_time_seconds": 10
}
```

On failure:

```json
{
  "status": "error",
  "error": "Description of what went wrong",
  "test_file": null
}
```

## Key Differences from Full Mode

- **2-3 tests instead of 3-7**: Reduces generation and execution time
- **No test execution**: Verify file exists, don't run (saves 10-30 seconds per CWE)
- **Simpler code generation**: Minimal setup, direct assertions
- **Fast framework detection**: Quick heuristic check instead of comprehensive scan
- **Skip complex scenarios**: No mock objects, no external API testing
- **Target time: < 30 seconds per CWE**

## Constraints

- Same safety constraints as full version (no real damage, no external services)
- Must create valid, syntactically correct test files
- Tests MUST be runnable (can be run later, just don't execute now)
- Keep test logic extremely simple

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
