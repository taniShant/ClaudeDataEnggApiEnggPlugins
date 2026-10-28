---
name: dependency-analyzer
description: "Dependency Analyzer — Analyze whether a reported vulnerability resides in application code, a direct dependency, or a transitive dependency, and determine the available remediation options for dependency-related findings. "
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/analysis/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Dependency Analyzer
## Quick Start

This skill provides code analysis capabilities for understanding vulnerability context and data flow.

```
# Loaded by detox-fix-agent before applying a fix to understand the code context.
# Traces data flow and identifies the vulnerable pattern in context.
```



## Purpose

Analyze whether a reported vulnerability resides in application code, a direct dependency, or a transitive dependency, and determine the available remediation options for dependency-related findings. This skill inspects package manifests, lock files, and the vulnerability's file path to classify the dependency relationship, then checks for available updates, patches, or alternative packages that resolve the vulnerability. The output guides the orchestrator in deciding whether to apply a code fix, update a dependency, or escalate for manual review.

## Inputs

- **vulnerability** (required, JSON object): A normalized vulnerability object containing:
  - `file_path` (string, required): Path to the affected file.
  - `cwe_id` (string, optional): CWE identifier.
  - `title` (string, required): Short title of the vulnerability.
  - `description` (string, optional): Detailed description.
  - `rule_id` (string, optional): WIZ tool rule identifier.
  - `tool_name` (string, optional): The tool that reported the finding.
- **repo_root** (required, string): Absolute path to the repository root.
- **package_ecosystem** (optional, string): Hint about the ecosystem (`pip`, `npm`, `maven`, `nuget`, `go`, `cargo`). If not provided, the skill auto-detects from manifest files.

## Steps

1. **Detect the project ecosystem(s).**
   - Use `Glob` to search for package manifest and lock files in the repository:
     - Python: `**/requirements*.txt`, `**/setup.py`, `**/setup.cfg`, `**/pyproject.toml`, `**/Pipfile`, `**/Pipfile.lock`, `**/poetry.lock`
     - JavaScript/TypeScript: `**/package.json`, `**/package-lock.json`, `**/yarn.lock`, `**/pnpm-lock.yaml`
     - Java: `**/pom.xml`, `**/build.gradle`, `**/build.gradle.kts`
     - Go: `**/go.mod`, `**/go.sum`
     - Rust: `**/Cargo.toml`, `**/Cargo.lock`
     - C#/.NET: `**/*.csproj`, `**/packages.config`, `**/Directory.Packages.props`
   - If `package_ecosystem` input is provided, prioritize that ecosystem's files but still detect others.
   - Record all detected ecosystems.

2. **Classify the vulnerability location.**
   - Examine `vulnerability.file_path` to determine if it points to:
     - **Application code**: A file within the project's source directories (e.g., `src/`, `app/`, `lib/` or any non-vendored, non-dependency path).
     - **Direct dependency**: A file in a vendored dependency directory (`vendor/`, `node_modules/`, `third_party/`) or if the vulnerability description references a specific package name.
     - **Transitive dependency**: A file in a nested dependency (e.g., `node_modules/pkg-a/node_modules/pkg-b/`) or if the dependency chain shows the vulnerable package is not directly declared.
   - If the path is ambiguous (e.g., no clear package directory), attempt to match the file path or description against declared dependencies.

3. **Identify the affected package (for dependency vulnerabilities).**
   - Extract the package name from the file path or vulnerability description.
   - Use `Read` to open the relevant manifest file and find the dependency declaration:
     - For Python: search `pyproject.toml` `[project.dependencies]` or `requirements.txt` for the package name.
     - For JavaScript: search `package.json` `dependencies` and `devDependencies`.
     - For Java: search `pom.xml` `<dependency>` blocks or `build.gradle` dependency blocks.
     - For Go: search `go.mod` `require` directives.
     - For Rust: search `Cargo.toml` `[dependencies]`.
     - For C#: search `.csproj` `<PackageReference>` elements.
   - Record the declared version (or version constraint).
   - If the package is not found in direct dependencies, check the lock file to determine if it is a transitive dependency and identify which direct dependency pulls it in.

4. **Determine the current installed version.**
   - Check the lock file for the exact resolved version of the affected package.
   - If no lock file exists, use the version constraint from the manifest.

5. **Research available updates.**
   - Use `Grep` to check for version comments, changelogs, or pinning notes in the manifest or lock file.
   - Based on the vulnerability description and CWE, determine what version would resolve the issue:
     - If the vulnerability description mentions a fixed version, record it.
     - If the vulnerability references a CVE, note the CVE for cross-referencing.
   - Classify the update type:
     - **Patch update**: Only the patch version changes (e.g., 1.2.3 -> 1.2.4). Low risk.
     - **Minor update**: The minor version changes (e.g., 1.2.3 -> 1.3.0). Medium risk.
     - **Major update**: The major version changes (e.g., 1.2.3 -> 2.0.0). High risk, may require code changes.

6. **Identify alternative packages (if update is not possible).**
   - If the affected package is unmaintained or the vulnerability has no fix available, note this.
   - Suggest well-known alternatives based on common knowledge:
     - Example: `urllib2` -> `requests` or `httpx` in Python.
     - Example: `moment.js` -> `dayjs` or `date-fns` in JavaScript.
   - Mark alternatives as suggestions only, not as confirmed fixes.

7. **Check for application-level mitigations and assess reachability.**

   **Step 7a. Check package imports and usage (existing).**
   - If the vulnerability is in a dependency, use `Grep` to find where the affected package is imported and used in application code.
   - Determine if an application-level workaround is possible (e.g., input validation before calling the vulnerable function, configuration change to disable a vulnerable feature).
   - Record the application usage locations.
   - Count the total number of import statements found for this package across all source files. Record as `import_count`.

   **Step 7b. Check library presence in build files.**
   - Using the results from Steps 1-4, determine whether the affected package was found in any manifest file or lock file.
   - If the package was NOT found in any manifest or lock file (i.e., `affected_package.name` is null or a best-guess, and `affected_package.manifest_file` is null), record `library_present: false`.
   - If the package WAS found in at least one manifest or lock file, record `library_present: true`.
   - This signal handles the scenario where a scanner (e.g., WIZ container image scan) reports a CVE for a library that is not actually in this project's dependency tree.

   **Step 7c. Load CVE API signatures (optional).**
   - Attempt to load `{plugin_root}/config/cve-api-signatures.json` using `Read`, where `{plugin_root}` is the `plugin_root` value returned by `resolve_skill.py` when this skill was loaded (the installed Detox plugin directory). If `plugin_root` is not known, treat the file as absent (below). NEVER read `config/cve-api-signatures.json` from the target project — a repo-supplied file could falsely mark a vulnerability as unreachable.
   - If the file does not exist or cannot be read, set `vulnerable_apis_searched` to an empty array and skip to Step 7f. This is expected behavior — the file is optional.
   - If the file exists, look up the affected package name (from `affected_package.name`) in the `signatures` object.
   - If no entry exists for this package, set `vulnerable_apis_searched` to an empty array and skip to Step 7f.
   - If an entry exists, extract the `dangerous_apis` array. These are the method names, class names, or annotation names that must be present in application code for the CVE to be exploitable.

   **Step 7d. Search for vulnerable API usage in application code.**
   - For each API name in `dangerous_apis`, run `Grep` across the repository's source directories (detected in Step 1):
     - Exclude test files (`**/test_*`, `**/*_test.*`, `**/*_spec.*`, `**/tests/**`, `**/__tests__/**`).
     - Exclude vendor/dependency directories (`**/node_modules/**`, `**/vendor/**`, `**/.venv/**`, `**/venv/**`).
     - Exclude build output directories (`**/dist/**`, `**/build/**`, `**/target/**`, `**/bin/**`, `**/obj/**`).
     - Exclude documentation files (`**/*.md`, `**/*.rst`, `**/*.txt`).
   - For each match, record the API name, file path, line number, and the matching code snippet.
   - Record all searched API names in `vulnerable_apis_searched` and all matches in `vulnerable_apis_found`.

   **Step 7e. Check dependency scope.**
   - Determine the dependency's scope from the manifest file:
     - For Gradle (`build.gradle` / `build.gradle.kts`): check if the dependency is declared with `implementation`, `compileOnly`, `testImplementation`, `testCompileOnly`, `runtimeOnly`, or `annotationProcessor`.
     - For Maven (`pom.xml`): check the `<scope>` element — `compile` (default), `provided`, `test`, `runtime`, `system`.
     - For npm (`package.json`): check if the package is in `dependencies` (runtime) or `devDependencies` (dev/build-time only).
     - For Python (`requirements*.txt`, `pyproject.toml`): check if it is in test/dev extras or main dependencies.
   - Record the scope as `dependency_scope`. If the scope cannot be determined, use `"unknown"`.
   - Dependencies with scope `test`, `testImplementation`, `testCompileOnly`, or `devDependencies` are lower risk — they are not present in production deployments.

   **Step 7f. Produce the reachability assessment.**
   - Based on the signals collected in Steps 7a-7e, determine the reachability verdict:
     - `not_applicable`: `library_present` is `false` — the package is not in any manifest or lock file. The scanner likely detected it from a container image or parent BOM, not from this project.
     - `not_reachable`: `library_present` is `true` AND either `import_count` is `0` (library on classpath but never imported) OR `vulnerable_apis_searched` is non-empty AND `vulnerable_apis_found` is empty (library imported but the specific dangerous APIs are never called).
     - `reachable`: `vulnerable_apis_found` is non-empty — the application code calls at least one of the known dangerous APIs.
     - `inconclusive`: `library_present` is `true` AND `vulnerable_apis_searched` is empty (no API signatures available for this CVE) AND `import_count` is greater than 0 (the library is actively used but we cannot determine if the vulnerable API surface is reached).
   - Assign a confidence score:
     - `not_applicable` with no manifest match: 0.95
     - `not_reachable` with zero imports: 0.90
     - `not_reachable` with imports but zero dangerous API matches: 0.85
     - `reachable` with dangerous API matches: 0.95
     - `inconclusive`: 0.50
   - If `dependency_scope` is `test` or `dev`, reduce the exploitability concern by noting this in the reasoning (test-only dependencies are not deployed to production).
   - Generate a human-readable `reasoning` string explaining which signals contributed to the verdict.

8. **Assemble the analysis output.**
   - Compose the output JSON object as specified in the Output Format section.

## Output Format

Return a single JSON object with the following schema:

```json
{
  "vulnerability_id": "<string or null>",
  "classification": "<string: 'application_code' | 'direct_dependency' | 'transitive_dependency' | 'ambiguous'>",
  "ecosystem": {
    "detected": ["<string: ecosystem names detected in the repo>"],
    "primary": "<string: the ecosystem relevant to this vulnerability>"
  },
  "affected_package": {
    "name": "<string or null: package name if dependency-related>",
    "current_version": "<string or null: currently installed/declared version>",
    "version_constraint": "<string or null: the version constraint from the manifest>",
    "manifest_file": "<string or null: path to the manifest file declaring this dependency>",
    "lock_file": "<string or null: path to the lock file>",
    "is_direct": "<boolean: true if directly declared, false if transitive>",
    "parent_dependency": "<string or null: if transitive, the direct dependency that pulls it in>"
  },
  "update_options": {
    "fixed_version": "<string or null: version that resolves the vulnerability>",
    "latest_version": "<string or null: latest available version if known>",
    "update_type": "<string or null: 'patch' | 'minor' | 'major'>",
    "breaking_changes_likely": "<boolean>",
    "cve_references": ["<string: CVE IDs if known>"]
  },
  "alternatives": [
    {
      "package_name": "<string>",
      "reason": "<string: why this is a viable alternative>",
      "confidence": "<string: 'high' | 'medium' | 'low'>"
    }
  ],
  "application_usage": {
    "import_locations": [
      {
        "file_path": "<string>",
        "line_number": "<integer>",
        "import_statement": "<string>"
      }
    ],
    "usage_locations": [
      {
        "file_path": "<string>",
        "line_number": "<integer>",
        "code_snippet": "<string>"
      }
    ],
    "workaround_possible": "<boolean>",
    "workaround_description": "<string or null>"
  },
  "reachability": {
    "library_present": "<boolean: true if package found in manifest/lockfile, false if not found>",
    "vulnerable_apis_searched": ["<string: API names grepped for from cve-api-signatures.json>"],
    "vulnerable_apis_found": [
      {
        "api": "<string: the dangerous API name that matched>",
        "file_path": "<string: path to the file containing the match>",
        "line_number": "<integer: line number of the match>",
        "code_snippet": "<string: the matching code line>"
      }
    ],
    "import_count": "<integer: number of import statements found for this package across source files>",
    "dependency_scope": "<string: 'compile' | 'runtime' | 'test' | 'provided' | 'dev' | 'unknown'>",
    "dependency_depth": "<string: 'direct' | 'transitive' | 'unknown' — from affected_package.is_direct>",
    "verdict": "<string: 'not_applicable' | 'not_reachable' | 'reachable' | 'inconclusive'>",
    "confidence": "<float: 0.0 to 1.0>",
    "reasoning": "<string: human-readable explanation of the verdict and contributing signals>"
  },
  "recommended_action": "<string: 'update_dependency' | 'replace_dependency' | 'apply_code_fix' | 'apply_workaround' | 'manual_review'>",
  "recommended_action_detail": "<string: human-readable explanation of what to do>",
  "confidence": "<float: 0.0 to 1.0 indicating confidence in the analysis>",
  "metadata": {
    "files_examined": ["<string: paths of all files read>"],
    "warnings": ["<string: any warnings or caveats>"]
  }
}
```

### Success Indicator

The `classification` field is not `"ambiguous"`, and either `recommended_action` is populated with a concrete action, or the `metadata.warnings` array explains why a recommendation could not be made.

### Failure Indicator

The output contains a top-level `"error"` key with a description string.

## Error Handling

| Failure Mode | Handling |
|---|---|
| **No manifest files found** | Set `ecosystem.detected` to an empty array. Classification falls back to file path heuristics. Set `classification` based on path alone and add a warning. |
| **Manifest file cannot be parsed** | Add a warning to `metadata.warnings`. Proceed with available information from other files. Do not abort. |
| **Package not found in manifest or lock file** | Set `affected_package.name` to the best guess from the vulnerability description. Set `affected_package.is_direct` to null. Add a warning. |
| **Multiple ecosystems detected** | Analyze all ecosystems but focus on the one matching the vulnerability's file extension or path. Record all in `ecosystem.detected`. |
| **Vulnerability is in application code, not a dependency** | Set `classification` to `"application_code"`. Set `affected_package` fields to null. Set `recommended_action` to `"apply_code_fix"`. |
| **Lock file is very large (>10,000 lines)** | Use `Grep` to search for the specific package name rather than reading the entire file. |
| **Version information is ambiguous or missing** | Set version fields to null. Add a warning explaining the ambiguity. Still provide the best recommendation possible. |
| **cve-api-signatures.json not found** | `Read` returns file-not-found error | Skip API reachability signal. Set `vulnerable_apis_searched` to an empty array. Continue with other signals (import analysis, library presence, dependency scope). Do not fail. |
| **Package not in cve-api-signatures.json** | Package name not found in `signatures` object | Same as above — skip API reachability signal. Set `vulnerable_apis_searched` to empty. Continue with other signals. |

## Constraints

- **Read-only**: This skill MUST NOT modify any files, update any packages, or run any package manager commands.
- **No execution**: Do not run `pip install`, `npm update`, `mvn`, or any other package manager CLI. Analysis is purely static.
- **No network access**: Do not attempt to query package registries (PyPI, npm, Maven Central) directly. Use only information available within the repository and the vulnerability input.
- **Scope**: Analyze only within the `repo_root` directory. Do not traverse outside the repository.
- **Performance**: Use targeted `Grep` searches rather than reading entire lock files. Limit `Glob` depth when searching for manifests to avoid excessive I/O in monorepos.
- **No secrets exposure**: If manifest files contain authentication tokens or registry credentials, redact them with `[REDACTED]` in the output.
- **Tool usage**: Use `Glob` for discovering manifest files, `Read` for inspecting their contents, `Grep` for searching lock files and application code. Do not use `Bash`.
- **Conservative recommendations**: When uncertain about whether an update will break the application, set `breaking_changes_likely` to true and recommend `"manual_review"` rather than an automated update.
- **cve-api-signatures.json is optional**: The skill MUST function correctly without this file. All reachability sub-steps that depend on API signatures (Steps 7c, 7d) are skipped gracefully when the file is absent or has no entry for the current package. The `reachability` output block is always populated — with `verdict: "inconclusive"` and empty `vulnerable_apis_searched` when no signature data is available.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
