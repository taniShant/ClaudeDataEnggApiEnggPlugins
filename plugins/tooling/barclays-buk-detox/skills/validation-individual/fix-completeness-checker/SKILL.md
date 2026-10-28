---
name: fix-completeness-checker
description: "Fix Completeness Checker — Verify that a vulnerability fix is thorough and complete by ensuring all instances of the vulnerable pattern are addressed (not just the single reported line), no new instances of the same pattern wer"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Fix Completeness Checker
## Quick Start

This skill provides validation logic for confirming CWE fixes have been successfully applied.

```
# Loaded by detox-validator-agent during the Validate Fixes phase.
# Re-scans fixed files with Semgrep to confirm vulnerability is eliminated.
```



## Purpose

Verify that a vulnerability fix is thorough and complete by ensuring all instances of the vulnerable pattern are addressed (not just the single reported line), no new instances of the same pattern were introduced by the fix, and the fix follows secure coding best practices for the specific CWE. This skill acts as the final quality gate before a remediation is accepted, catching partial fixes that leave the codebase still vulnerable.

## Inputs

- **repo_dir** (required, string): Absolute path to the root of the repository.
- **vulnerability** (required, JSON object): The normalized vulnerability being remediated. Must contain:
  - `cwe_id` (string, required): The CWE identifier (e.g., `CWE-89`).
  - `file_path` (string, required): Absolute path to the originally reported file.
  - `line_number` (integer, required): The line number originally reported.
  - `code_snippet` (string, optional): The original vulnerable code snippet.
  - `rule_id` (string, optional): The SAST rule that flagged the vulnerability.
- **fix_diff** (required, string): The unified diff of the applied fix (output of `git diff` or equivalent). Used to understand exactly what was changed.
- **modified_files** (required, array of strings): Absolute paths to all files modified by the fix.
- **vulnerable_pattern** (optional, string): A regex or code pattern that represents the vulnerable construct. If not provided, the skill will derive the pattern from the vulnerability's `code_snippet` and `cwe_id`.
- **language** (optional, string): The programming language of the affected files (e.g., `python`, `javascript`, `java`, `go`, `csharp`, `rust`). If omitted, inferred from file extensions.

## Steps

1. **Validate inputs.**
   - Confirm `repo_dir` exists using `Bash`: `test -d <repo_dir> && echo "OK"`.
   - Confirm `vulnerability.file_path` exists using `Bash`: `test -f <file_path> && echo "OK"`.
   - Confirm `fix_diff` is non-empty. If empty, the fix may not have been applied -- return an error.
   - Confirm each file in `modified_files` exists.
   - Determine the language from `language` input or from the file extension of `vulnerability.file_path`.

2. **Derive the vulnerable pattern (if not provided).**
   - Based on the `cwe_id` and `code_snippet`, construct a search pattern that matches the vulnerable coding construct. Common pattern derivations:
     - **CWE-89 (SQL Injection)**: Pattern matches string concatenation or f-string/format-string usage within SQL query construction. Examples: `"SELECT.*" \+ `, `f"SELECT.*\{`, `"SELECT.*%s".* %`, `.execute\(f"`, `.execute\(".*" \+`, `cursor\.execute\(.*%`.
     - **CWE-79 (XSS)**: Pattern matches unsanitized user input rendered in HTML. Examples: `innerHTML\s*=`, `\|\s*safe`, `render_template_string\(`, `dangerouslySetInnerHTML`, `document\.write\(`.
     - **CWE-78 (OS Command Injection)**: Pattern matches user input passed to shell commands. Examples: `os\.system\(`, `subprocess\.call\(.*shell=True`, `exec\(`, `child_process\.exec\(`.
     - **CWE-22 (Path Traversal)**: Pattern matches unsanitized user input in file paths. Examples: `open\(.*\+`, `os\.path\.join\(.*request`, `Path\(.*\+`, `fs\.readFile\(.*req\.`.
     - **CWE-502 (Deserialization)**: Pattern matches unsafe deserialization. Examples: `pickle\.loads?\(`, `yaml\.load\(`, `yaml\.unsafe_load`, `Marshal\.load`, `ObjectInputStream`.
     - **CWE-327 (Broken Crypto)**: Pattern matches weak cryptographic algorithms. Examples: `MD5`, `SHA1`, `DES`, `RC4`, `hashlib\.md5`, `hashlib\.sha1`.
     - **CWE-798 (Hard-coded Credentials)**: Pattern matches literals assigned to password/key variables. Examples: `password\s*=\s*["']`, `api_key\s*=\s*["']`, `secret\s*=\s*["']`.
     - **CWE-611 (XXE)**: Pattern matches XML parsing without disabling external entities. Examples: `XMLParser\(`, `etree\.parse\(`, `DocumentBuilderFactory`, `xml2js\.parseString`.
   - If the CWE is not in the above list, generalize the pattern from the `code_snippet` by identifying the security-sensitive function call or construct.
   - Record the derived pattern for use in subsequent steps.

3. **Verify the originally reported line is fixed.**
   - Use `Read` to examine the modified file at and around the original `vulnerability.line_number`.
   - Check whether the original `code_snippet` (or pattern) is still present at or near the reported line (allow for line shifts of up to 20 lines due to additions/removals).
   - If the original vulnerable code is still present, mark this as `"original_not_fixed"`.
   - If the original vulnerable code is gone, verify that the replacement code at that location uses the secure alternative (see Step 6 for best practices).

4. **Search for other instances of the vulnerable pattern in the same file.**
   - Use `Grep` with the derived `vulnerable_pattern` against `vulnerability.file_path`.
   - Exclude lines that are comments (lines starting with `#`, `//`, `/*`, `*`, `--` depending on language).
   - Record each match with its line number and the matching code.
   - Compare these matches against the `fix_diff` to determine if each instance was addressed by the fix.
   - Categorize each match as:
     - **Fixed**: The line is within the diff's changed regions.
     - **Unfixed**: The line matches the vulnerable pattern but was not modified by the fix.
     - **False positive**: The match is in a comment, string literal used as documentation, or test assertion (heuristic detection).

5. **Search for the vulnerable pattern across the entire repository.**
   - Use `Grep` with the derived `vulnerable_pattern` across the repository, excluding:
     - Test files (`**/test_*`, `**/*_test.*`, `**/*_spec.*`, `**/tests/**`, `**/__tests__/**`).
     - Vendor/dependency directories (`**/node_modules/**`, `**/vendor/**`, `**/.venv/**`, `**/venv/**`).
     - Build output directories (`**/dist/**`, `**/build/**`, `**/target/**`, `**/bin/**`, `**/obj/**`).
     - Documentation files (`**/*.md`, `**/*.rst`, `**/*.txt`).
   - For each match outside the originally reported file:
     - Record the file path, line number, and matching code.
     - Mark it as a **related unfixed instance** -- the same vulnerable pattern exists elsewhere in the codebase.
   - This step answers: "Was only the reported instance fixed, or were all instances across the codebase addressed?"

6. **Check that the fix follows secure coding best practices.**
   - Based on the `cwe_id`, verify the fix uses the recommended secure pattern:
     - **CWE-89 (SQL Injection)**: Fix must use parameterized queries, prepared statements, or an ORM's built-in parameterization. String concatenation, f-strings, or `%`-formatting for query construction is not acceptable.
     - **CWE-79 (XSS)**: Fix must use context-appropriate output encoding/escaping (HTML entity encoding, JavaScript encoding, URL encoding). Auto-escaping template engines must be enabled. `| safe` or `dangerouslySetInnerHTML` usage must be justified.
     - **CWE-78 (OS Command Injection)**: Fix must avoid shell=True. Use array-based command construction with `subprocess.run([...])` or equivalent. User input must be validated against an allowlist or properly escaped using `shlex.quote()` or equivalent.
     - **CWE-22 (Path Traversal)**: Fix must normalize paths and validate against a base directory. Use `os.path.realpath()` / `Path.resolve()` and confirm the resolved path starts with the intended base. Reject paths containing `..`.
     - **CWE-502 (Deserialization)**: Fix must replace unsafe deserialization with safe alternatives (`json.loads` instead of `pickle.loads`, `yaml.safe_load` instead of `yaml.load`). If unsafe deserialization is required, input must be cryptographically signed and verified.
     - **CWE-327 (Broken Crypto)**: Fix must use strong algorithms (SHA-256+, AES-256, RSA-2048+). Password hashing must use bcrypt, scrypt, or Argon2.
     - **CWE-798 (Hard-coded Credentials)**: Fix must move credentials to environment variables, secret managers, or configuration files excluded from version control. The secret must not remain in the code.
     - **CWE-611 (XXE)**: Fix must disable external entity resolution and DTD processing in the XML parser configuration.
   - Use `Read` to examine the fixed code and verify it matches the secure pattern.
   - If the CWE is not in the above list, check general secure coding principles: input validation, output encoding, principle of least privilege, defense in depth.

7. **Check that the fix did not introduce new instances of the same vulnerability.**
   - Parse the `fix_diff` to extract all lines added by the fix (lines starting with `+` in the diff, excluding `+++` header lines).
   - Apply the `vulnerable_pattern` against the added lines.
   - If any added line matches the vulnerable pattern, flag it as a **new instance introduced by the fix**.
   - This catches cases where a developer "fixes" one instance but introduces the same vulnerability in the replacement code.

8. **Assess fix completeness and assign a verdict.**
   - **COMPLETE**: The originally reported instance is fixed. All instances of the vulnerable pattern in the same file are fixed. The fix follows secure coding best practices. No new instances were introduced by the fix.
   - **PARTIAL_SAME_FILE**: The originally reported instance is fixed, but other instances of the same pattern remain unfixed in the same file.
   - **PARTIAL_OTHER_FILES**: The originally reported instance is fixed and the file is clean, but the same vulnerable pattern exists in other files in the repository.
   - **INCOMPLETE**: The originally reported instance is not fixed, or the fix introduced new instances, or the fix does not follow secure coding best practices.
   - **NOT_FIXED**: The original vulnerable code is still present and unchanged.

9. **Compile and return the structured result.**

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "verdict": "COMPLETE",
  "cwe_id": "CWE-89",
  "file_path": "/absolute/path/to/file.py",
  "language": "python",
  "vulnerable_pattern": "regex pattern used for searching",
  "original_instance": {
    "fixed": true,
    "original_line": 42,
    "original_code": "cursor.execute(\"SELECT * FROM users WHERE id=\" + user_id)",
    "fixed_code": "cursor.execute(\"SELECT * FROM users WHERE id=%s\", (user_id,))",
    "fixed_line": 42,
    "follows_best_practices": true,
    "best_practice_notes": "Uses parameterized query with placeholder"
  },
  "same_file_instances": {
    "total_found": 3,
    "fixed": 3,
    "unfixed": 0,
    "false_positives": 0,
    "details": [
      {
        "line": 42,
        "code": "cursor.execute(\"SELECT * FROM users WHERE id=%s\", (user_id,))",
        "status": "fixed"
      },
      {
        "line": 67,
        "code": "cursor.execute(\"INSERT INTO logs VALUES (%s, %s)\", (user_id, action))",
        "status": "fixed"
      },
      {
        "line": 95,
        "code": "cursor.execute(\"DELETE FROM sessions WHERE token=%s\", (token,))",
        "status": "fixed"
      }
    ]
  },
  "other_file_instances": {
    "total_found": 1,
    "files_affected": [
      {
        "file_path": "/absolute/path/to/other_file.py",
        "matches": [
          {
            "line": 23,
            "code": "db.execute(\"SELECT * FROM orders WHERE user_id=\" + uid)",
            "status": "unfixed"
          }
        ]
      }
    ]
  },
  "new_instances_introduced": {
    "count": 0,
    "details": []
  },
  "best_practices_check": {
    "passed": true,
    "cwe_specific_checks": [
      {
        "check": "Uses parameterized queries",
        "passed": true,
        "evidence": "All SQL execution calls use placeholder syntax"
      },
      {
        "check": "No string concatenation in SQL",
        "passed": true,
        "evidence": "No instances of string concatenation found in SQL query construction"
      }
    ]
  },
  "recommendations": [],
  "warnings": []
}
```

When the fix is incomplete, `recommendations` provides actionable guidance:

```json
{
  "recommendations": [
    "Fix the remaining 1 instance in /absolute/path/to/other_file.py at line 23",
    "Consider a repository-wide search-and-replace for the vulnerable pattern",
    "Add a Semgrep rule to CI to prevent reintroduction of this pattern"
  ]
}
```

On error, return:

```json
{
  "status": "error",
  "error": "Human-readable description of what went wrong",
  "cwe_id": "CWE-89",
  "file_path": "/absolute/path/to/file.py"
}
```

### Success Indicators

- `status` is `"success"`.
- `verdict` is `"COMPLETE"` -- the fix is thorough and follows best practices.
- `original_instance.fixed` is `true`.
- `original_instance.follows_best_practices` is `true`.
- `same_file_instances.unfixed` is `0`.
- `new_instances_introduced.count` is `0`.

### Failure Indicators

- `verdict` is `"NOT_FIXED"` or `"INCOMPLETE"` -- the fix is inadequate.
- `original_instance.fixed` is `false`.
- `original_instance.follows_best_practices` is `false`.
- `new_instances_introduced.count` is greater than `0`.
- `same_file_instances.unfixed` is greater than `0`.

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| **Repository directory not found** | `test -d` returns non-zero | Return error JSON immediately. |
| **Vulnerability file not found** | `test -f` returns non-zero | Return error JSON. The file may have been deleted or renamed -- suggest checking the diff. |
| **Fix diff is empty** | `fix_diff` is an empty string | Return error JSON: `"No diff provided. The fix may not have been applied."` |
| **Vulnerable pattern cannot be derived** | CWE is not recognized and no `code_snippet` or `vulnerable_pattern` provided | Return error JSON: `"Cannot derive vulnerable pattern. Provide a vulnerable_pattern or code_snippet input."` |
| **Grep returns too many matches** | More than 200 matches across the repository | Truncate to the first 200 matches. Add a warning noting truncation and recommend manual review. The vulnerable pattern may be too broad. |
| **Grep pattern is invalid regex** | Grep tool returns a regex syntax error | Escape special characters in the pattern and retry. If still failing, fall back to literal string search of the `code_snippet`. |
| **Language not recognized** | File extension does not map to a known language | Set `language` to `"unknown"`. Best practices checking will be limited to generic checks. Add a warning. |
| **Diff cannot be parsed** | `fix_diff` is not in unified diff format | Attempt to identify changed lines by searching for `+` and `-` prefixed lines. If parsing fails entirely, skip diff-based analysis and rely only on pattern searching. Add a warning. |
| **Modified file is binary** | Read tool or Grep returns binary content indicator | Skip that file. Add a warning noting the binary file was excluded. |
| **Best practices check is inconclusive** | The fix uses a pattern not in the known secure patterns list | Set `follows_best_practices` to `null` (unknown) and add a recommendation for manual security review. |

## Constraints

- **NEVER** modify any files in the repository. This is a read-only analysis skill.
- **NEVER** execute any code from the repository or run the application.
- **NEVER** apply fixes or suggest auto-fix patches. This skill only validates existing fixes.
- Pattern matching against test files should be noted but not counted as unfixed vulnerabilities (tests may intentionally contain vulnerable patterns for testing purposes).
- Limit `Grep` searches to a maximum of 200 results per pattern per search scope.
- The repository-wide search (Step 5) must exclude third-party and generated code directories to avoid false positives.
- All file paths in the output must be absolute.
- The `vulnerable_pattern` derived in Step 2 must be logged in the output so it can be reviewed for correctness.
- Do not include more than 200 characters of code per `code` field in the output to keep results manageable.
- When reporting unfixed instances in other files (`other_file_instances`), limit to the first 20 files and 5 matches per file. Note truncation if exceeded.
- Best practices checks must be CWE-specific. Generic advice like "validate input" is insufficient -- the check must verify the specific secure coding construct for the CWE is present.
- Do not flag intentionally vulnerable code in test fixtures, security test suites, or documentation examples as unfixed instances. Use path-based heuristics (`test`, `spec`, `fixture`, `example`, `docs`) to identify these.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
