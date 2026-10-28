---
name: regression-checker
description: "Regression Checker — Verify that a vulnerability fix did not introduce regressions by comparing test results before and after the fix, checking for new linting errors, and confirming that no imports were broken. This skil"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/validation_individual/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Regression Checker
## Quick Start

This skill provides validation logic for confirming CWE fixes have been successfully applied.

```
# Loaded by detox-validator-agent during the Validate Fixes phase.
# Re-scans fixed files with Semgrep to confirm vulnerability is eliminated.
```



## Purpose

Verify that a vulnerability fix did not introduce regressions by comparing test results before and after the fix, checking for new linting errors, and confirming that no imports were broken. This skill acts as a safety gate that ensures a remediation improves security posture without degrading existing functionality, code quality, or build integrity.

## Inputs

- **repo_dir** (required, string): Absolute path to the root of the repository.
- **modified_files** (required, array of strings): List of absolute paths to files that were modified by the fix.
- **pre_fix_test_results** (required, JSON object): Test results captured before the fix was applied. Must conform to the `test_runner` skill output schema, containing at minimum `results.total`, `results.passed`, `results.failed`, `results.errored`, and `failures` array.
- **post_fix_test_results** (required, JSON object): Test results captured after the fix was applied. Same schema as `pre_fix_test_results`.
- **tech_stack** (optional, JSON object): Output from `tech_stack_detection`. Used to determine which linter to run. If omitted, linter detection is performed independently.
- **pre_fix_lint_results** (optional, JSON object): Lint results from before the fix. If not provided, linting comparison is skipped and only post-fix lint errors in modified files are reported.

## Steps

1. **Validate inputs.**
   - Confirm `repo_dir` exists using `Bash`: `test -d <repo_dir> && echo "OK"`.
   - Confirm each path in `modified_files` exists using `Bash`: `test -f <path> && echo "OK"` for each.
   - Confirm `pre_fix_test_results` and `post_fix_test_results` both contain the required fields. If either is missing required fields, return an error.

2. **Compare test results (before vs. after).**
   - Compare the following metrics:
     - `total`: Total number of tests. Flag if the count decreased (tests may have been deleted).
     - `passed`: Number of passing tests. Flag if this decreased.
     - `failed`: Number of failing tests. Flag if this increased.
     - `errored`: Number of errored tests. Flag if this increased.
   - Compute the delta for each metric: `delta = post_fix_value - pre_fix_value`.
   - Identify **newly failing tests**: Tests that appear in `post_fix_test_results.failures` but not in `pre_fix_test_results.failures` (matched by `test_name`).
   - Identify **newly fixed tests**: Tests that appear in `pre_fix_test_results.failures` but not in `post_fix_test_results.failures`.
   - Identify **consistently failing tests**: Tests present in both failure lists (these are pre-existing failures, not regressions).
   - A regression is detected if there are any newly failing tests.

3. **Detect the linter for modified files (if `tech_stack` is not provided).**
   - For each modified file, determine its language from the file extension.
   - Detect the appropriate linter:
     - **Python** (`.py`): Check for `ruff.toml` or `[tool.ruff]` in `pyproject.toml` -> **Ruff**. Check for `.flake8` or `[flake8]` in `setup.cfg` -> **Flake8**. Check for `.pylintrc` or `[tool.pylint]` in `pyproject.toml` -> **Pylint**. Fallback: use `ruff` if available, then `flake8`, then `pylint`.
     - **JavaScript/TypeScript** (`.js`, `.ts`, `.jsx`, `.tsx`): Check for `.eslintrc*` or `eslint.config.*` -> **ESLint**. Check for `biome.json` -> **Biome**.
     - **Go** (`.go`): Check for `.golangci.yml` -> **golangci-lint**. Fallback: `go vet`.
     - **Java** (`.java`): Check for `checkstyle.xml` -> **Checkstyle**. Otherwise skip (Java linting typically runs through the build system).
     - **C#** (`.cs`): Use `dotnet format --verify-no-changes`.
     - **Rust** (`.rs`): Use `cargo clippy`.
   - Record detected linters. If no linter is detected or available, note this and skip linting checks.

4. **Run linting on modified files.**
   - For each modified file, run the detected linter targeting only that file:
     - **Ruff**: `cd <repo_dir> && ruff check <file_path> --output-format json 2>&1`
     - **Flake8**: `cd <repo_dir> && flake8 <file_path> --format json 2>&1`
     - **Pylint**: `cd <repo_dir> && pylint <file_path> --output-format json 2>&1`
     - **ESLint**: `cd <repo_dir> && npx eslint <file_path> --format json 2>&1`
     - **Biome**: `cd <repo_dir> && npx biome check <file_path> --reporter json 2>&1`
     - **golangci-lint**: `cd <repo_dir> && golangci-lint run <file_path> --out-format json 2>&1`
     - **go vet**: `cd <repo_dir> && go vet <file_path> 2>&1`
     - **dotnet format**: `cd <repo_dir> && dotnet format --verify-no-changes --include <file_path> 2>&1`
     - **cargo clippy**: `cd <repo_dir> && cargo clippy -- -W clippy::all 2>&1`
   - Parse the linter output to extract errors and warnings.
   - Set a timeout of 60 seconds per linter invocation.

5. **Compare lint results (if `pre_fix_lint_results` provided).**
   - Compare pre-fix and post-fix lint findings for the modified files.
   - Identify **new lint errors**: Errors present in post-fix results but not in pre-fix results.
   - Identify **resolved lint errors**: Errors present in pre-fix but absent in post-fix (this is a positive outcome).
   - Ignore warnings that existed before the fix (do not flag them as regressions).
   - If `pre_fix_lint_results` is not provided, report all current lint errors in modified files but note that no baseline comparison is available.

6. **Check for broken imports.**
   - For each modified file, extract its import statements:
     - **Python**: Use `Grep` to find lines matching `^import ` or `^from .* import`.
     - **JavaScript/TypeScript**: Use `Grep` to find lines matching `^import `, `require\(`, or `^export .* from`.
     - **Java**: Use `Grep` to find lines matching `^import `.
     - **Go**: Use `Grep` to find lines matching `"[^"]*"` within import blocks.
     - **C#**: Use `Grep` to find lines matching `^using `.
     - **Rust**: Use `Grep` to find lines matching `^use `.
   - For each import, verify the imported module or file exists:
     - For relative/local imports, use `Glob` to confirm the target file or module exists in the repository.
     - For standard library and third-party imports, check that they appear in the dependency manifest (e.g., `requirements.txt`, `package.json`, `go.mod`).
   - Flag any imports that:
     - Reference a module or file that does not exist in the repository (possible broken import).
     - Were added by the fix but do not appear in the dependency manifest (possible missing dependency).
     - Were removed by the fix but are still referenced elsewhere in the same file (possible orphan usage).

7. **Check for syntax validity of modified files.**
   - For each modified file, perform a basic syntax check:
     - **Python**: `cd <repo_dir> && python -m py_compile <file_path> 2>&1`
     - **JavaScript**: `cd <repo_dir> && node --check <file_path> 2>&1`
     - **TypeScript**: If `npx tsc` is available, `cd <repo_dir> && npx tsc --noEmit <file_path> 2>&1`.
     - **Go**: `cd <repo_dir> && go build <file_path> 2>&1` (or `go vet`).
     - **Java**: Syntax validation is handled by the Maven/Gradle build step; skip if build is not run.
     - **C#**: `cd <repo_dir> && dotnet build --no-restore 2>&1` (checks compilation).
     - **Rust**: `cd <repo_dir> && cargo check 2>&1`.
   - Record any syntax errors found.

8. **Determine the overall regression verdict.**
   - **NO_REGRESSION**: No newly failing tests, no new lint errors in modified files, no broken imports, no syntax errors.
   - **TEST_REGRESSION**: One or more tests that passed before now fail.
   - **LINT_REGRESSION**: New lint errors were introduced in modified files.
   - **IMPORT_REGRESSION**: One or more imports are broken or missing.
   - **SYNTAX_ERROR**: One or more modified files have syntax errors.
   - **MULTIPLE_REGRESSIONS**: More than one category of regression detected. List all categories.
   - Assign a severity:
     - `"critical"`: Syntax errors or test regressions (the code is broken).
     - `"high"`: Broken imports (the code likely will not run).
     - `"medium"`: New lint errors (code quality degradation).
     - `"low"`: Test count decreased but no failures (tests may have been inadvertently removed).

9. **Compile and return the structured result.**

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "verdict": "NO_REGRESSION",
  "severity": null,
  "repo_dir": "/absolute/path/to/repo",
  "modified_files": ["/absolute/path/to/file.py"],
  "test_comparison": {
    "pre_fix": {
      "total": 120,
      "passed": 118,
      "failed": 2,
      "errored": 0
    },
    "post_fix": {
      "total": 120,
      "passed": 120,
      "failed": 0,
      "errored": 0
    },
    "deltas": {
      "total": 0,
      "passed": 2,
      "failed": -2,
      "errored": 0
    },
    "newly_failing": [],
    "newly_fixed": [
      {
        "test_name": "test_sql_injection_prevention",
        "file": "tests/test_security.py"
      }
    ],
    "consistently_failing": []
  },
  "lint_comparison": {
    "linter_used": "Ruff",
    "new_errors": [],
    "resolved_errors": [],
    "total_current_errors": 0,
    "baseline_available": true
  },
  "import_check": {
    "broken_imports": [],
    "missing_dependencies": [],
    "orphan_references": []
  },
  "syntax_check": {
    "files_checked": ["/absolute/path/to/file.py"],
    "errors": []
  },
  "warnings": []
}
```

On error, return:

```json
{
  "status": "error",
  "error": "Human-readable description of what went wrong",
  "repo_dir": "/absolute/path/to/repo"
}
```

### Success Indicators

- `status` is `"success"`.
- `verdict` is `"NO_REGRESSION"` -- the fix introduced no regressions.
- All sub-checks (test_comparison, lint_comparison, import_check, syntax_check) show clean results.

### Failure Indicators

- `verdict` is any value other than `"NO_REGRESSION"`.
- `severity` is `"critical"` or `"high"` -- the fix is likely broken and should not be merged.
- `test_comparison.newly_failing` is non-empty.
- `syntax_check.errors` is non-empty.

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| **Repository directory not found** | `test -d` returns non-zero | Return error JSON immediately. |
| **Modified file not found** | `test -f` returns non-zero for a path in `modified_files` | Remove the missing file from the check list. Add a warning noting the file was not found. Continue with remaining files. |
| **Pre-fix or post-fix test results missing required fields** | Schema validation fails | Return error JSON specifying which fields are missing. |
| **Linter not available** | Linter command returns `command not found` | Skip linting for that language. Add a warning: `"Linter <name> not available. Lint regression check skipped for <language> files."` |
| **Linter timeout** | Bash command exceeds 60 seconds | Kill the linter process. Report partial results if available. Add a warning about the timeout. |
| **Lint output cannot be parsed** | JSON parse failure or unexpected output format | Fall back to counting lines of output as a rough error count. Set lint `confidence` to `"low"`. |
| **Import resolution failure** | Cannot determine whether an import is valid (e.g., dynamic imports, conditional imports) | Mark the import as `"unresolvable"` and add it to warnings. Do not flag it as a broken import. |
| **Syntax check command not available** | `python`, `node`, etc. not on PATH | Skip syntax check for that language. Add a warning. |
| **Test result comparison ambiguity** | Test names changed between runs (renamed or parameterized tests) | Use fuzzy matching on test names (Levenshtein distance or substring matching). If matches are uncertain, list them under `warnings` rather than `newly_failing`. |

## Constraints

- **NEVER** modify any files in the repository. This is a read-only validation skill (linting and syntax checks are read-only operations).
- **NEVER** install tools, dependencies, or packages.
- **NEVER** run linters or syntax checks with auto-fix enabled (no `--fix`, `--fix-unsafe`, `--write`, or equivalent flags).
- **NEVER** run the full test suite within this skill. Test execution is the responsibility of the `test_runner` skill. This skill only compares pre-existing test results.
- All linter commands must target only the modified files, not the entire repository, to keep execution times bounded.
- Linter execution timeout is 60 seconds per file. Syntax check timeout is 30 seconds per file.
- Do not report pre-existing lint errors as regressions. Only flag errors that are new relative to the baseline (or, if no baseline exists, that appear in lines modified by the fix).
- All paths in the output must be absolute.
- Limit `raw_output` fields to a maximum of 100 lines each.
- The import check should only verify local/relative imports structurally. Do not attempt to resolve third-party imports beyond checking the dependency manifest.
- When multiple regression categories are detected, report all of them -- do not stop at the first one found.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
