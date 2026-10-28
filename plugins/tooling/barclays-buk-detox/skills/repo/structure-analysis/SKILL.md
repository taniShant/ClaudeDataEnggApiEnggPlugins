---
name: structure-analysis
description: "Repository Structure Analysis — Analyze a cloned repository's directory layout, identify key files, determine the build system in use, locate application entry points, and produce a structured summary. This skill provides the founda"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/repo/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Repository Structure Analysis
## Quick Start

This skill provides repository management patterns (clone, branch, analyse structure).

```
# Loaded by detox-orchestrator-agent during the Repository Setup phase.
# Clones the target repo, creates a working branch, and detects the tech stack.
```



## Purpose

Analyze a cloned repository's directory layout, identify key files, determine the build system in use, locate application entry points, and produce a structured summary. This skill provides the foundational understanding of a codebase that downstream skills (tech stack detection, CWE remediation routing, fix application) depend on to operate correctly.

## Inputs

- **repo_dir** (required, string): Absolute path to the root of the cloned repository to analyze.
- **max_depth** (optional, integer): Maximum directory depth to traverse when building the directory tree. Defaults to `4`.
- **focus_paths** (optional, list[string]): Specific subdirectories or files to analyze in greater detail. If omitted, the entire repository root is analyzed.
- **exclude_patterns** (optional, list[string]): Glob patterns for directories/files to exclude from analysis. Defaults to `["node_modules", ".git", "__pycache__", ".venv", "venv", "dist", "build", ".tox", ".mypy_cache", ".pytest_cache", "*.egg-info"]`.

## Steps

1. **Validate the repository directory.**
   - Use `Bash` to confirm the directory exists: `test -d <repo_dir> && echo "OK"`.
   - Confirm it is a git repository: `test -d <repo_dir>/.git && echo "OK"`.
   - If either check fails, return an error immediately.

2. **Generate the directory tree.**
   - Use `Bash` to produce a tree listing: `find <repo_dir> -maxdepth <max_depth> -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/dist/*' -not -path '*/build/*' | sort`.
   - Alternatively, if the `tree` command is available, use: `tree -L <max_depth> -I '.git|node_modules|__pycache__|.venv|venv|dist|build' --dirsfirst <repo_dir>`.
   - Capture the output as the `directory_tree` field.

3. **Identify key configuration and manifest files.**
   - Use `Glob` to search for common project files at the repository root and one level deep:
     - Python: `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `Pipfile`, `poetry.lock`, `tox.ini`, `noxfile.py`
     - JavaScript/TypeScript: `package.json`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `tsconfig.json`, `.eslintrc*`, `webpack.config.*`, `vite.config.*`, `next.config.*`
     - Java/Kotlin: `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle`, `gradlew`
     - Go: `go.mod`, `go.sum`
     - Rust: `Cargo.toml`, `Cargo.lock`
     - Ruby: `Gemfile`, `Gemfile.lock`, `.ruby-version`
     - C#/.NET: `*.csproj`, `*.sln`, `Directory.Build.props`, `nuget.config`
     - Docker/Infra: `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml`, `.dockerignore`
     - CI/CD: `.github/workflows/*.yml`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/config.yml`, `azure-pipelines.yml`
     - General: `Makefile`, `justfile`, `.editorconfig`, `.gitignore`, `LICENSE`, `README*`
   - For each file found, record its relative path from the repository root.

4. **Determine the build system.**
   - Based on the manifest files found in Step 3, classify the build system:
     - If `pyproject.toml` exists, use `Read` to check the `[build-system]` table for the build backend (setuptools, hatchling, flit, poetry-core, maturin, etc.).
     - If `package.json` exists, use `Read` to check for `scripts.build`, and identify the bundler (webpack, vite, esbuild, rollup, next, etc.).
     - If `pom.xml` exists, classify as Maven. If `build.gradle` or `build.gradle.kts` exists, classify as Gradle.
     - If `go.mod` exists, classify as Go modules.
     - If `Cargo.toml` exists, classify as Cargo.
     - If `Makefile` exists alongside other build files, note it as an auxiliary build tool.
   - Record all detected build systems (a project may have multiple, e.g., a Python backend with a JavaScript frontend).

5. **Locate application entry points.**
   - Use `Grep` to search for common entry point patterns:
     - Python: `if __name__ == ["']__main__["']`, `@click.command`, `@app.route`, `def main(`, `app = FastAPI(`, `app = Flask(`, `urlpatterns`, `INSTALLED_APPS`
     - JavaScript/TypeScript: `"main"` field in `package.json`, files named `index.js`, `index.ts`, `app.js`, `app.ts`, `server.js`, `server.ts`
     - Java: `public static void main`, `@SpringBootApplication`
     - Go: `func main()`
     - Rust: `fn main()`
     - C#: `static void Main`, `static async Task Main`, `WebApplication.CreateBuilder`
   - For each match, record the file path and line number.
   - Use `Read` to examine the first 30 lines of each identified entry point file to confirm it is genuinely an entry point and capture a brief description.

6. **Identify test directories and configuration.**
   - Use `Glob` to search for: `tests/`, `test/`, `spec/`, `__tests__/`, `*_test.go`, `*_test.py`, `*.test.js`, `*.test.ts`, `*.spec.js`, `*.spec.ts`.
   - Check for test configuration files: `pytest.ini`, `conftest.py`, `jest.config.*`, `.mocharc.*`, `phpunit.xml`.
   - Record the test directory paths and test framework configuration files found.

7. **Detect documentation files.**
   - Use `Glob` to search for: `docs/`, `doc/`, `README*`, `CHANGELOG*`, `CONTRIBUTING*`, `*.rst`, `mkdocs.yml`, `conf.py` (Sphinx).
   - Record paths found.

8. **Assess repository size and statistics.**
   - Use `Bash` to count files by extension: `find <repo_dir> -type f -not -path '*/.git/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -20`.
   - Use `Bash` to count total lines of code (excluding vendored/generated): `find <repo_dir> -type f \( -name '*.py' -o -name '*.js' -o -name '*.ts' -o -name '*.java' -o -name '*.go' -o -name '*.rs' -o -name '*.cs' \) -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/vendor/*' | xargs wc -l 2>/dev/null | tail -1`.
   - Record total file count, lines of code, and top file extensions.

9. **Compile and return the structured summary.**
   - Assemble all findings into the output format specified below.

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "repo_dir": "/tmp/cwe-remediation/aBcDeFgHiJ",
  "directory_tree": "... truncated tree output ...",
  "key_files": {
    "manifests": [
      {"path": "pyproject.toml", "type": "python_project"},
      {"path": "package.json", "type": "npm_manifest"}
    ],
    "config": [
      {"path": ".github/workflows/ci.yml", "type": "github_actions"},
      {"path": "Dockerfile", "type": "docker"}
    ],
    "documentation": [
      {"path": "README.md", "type": "readme"},
      {"path": "docs/", "type": "docs_directory"}
    ]
  },
  "build_systems": [
    {
      "type": "setuptools",
      "manifest": "pyproject.toml",
      "build_command": "pip install -e .",
      "notes": "Uses hatchling as build backend"
    }
  ],
  "entry_points": [
    {
      "file": "src/main.py",
      "line": 45,
      "type": "cli_entry_point",
      "description": "Click-based CLI, defines 'cwe-remediate' command"
    },
    {
      "file": "src/orchestrator.py",
      "line": 27,
      "type": "pipeline_entry",
      "description": "Orchestrator.run() method, main pipeline execution"
    }
  ],
  "test_structure": {
    "test_dirs": ["tests/"],
    "test_config_files": ["pytest.ini", "tests/conftest.py"],
    "test_framework": "pytest"
  },
  "stats": {
    "total_files": 142,
    "total_lines_of_code": 8500,
    "top_extensions": [
      {"extension": "py", "count": 45},
      {"extension": "js", "count": 30},
      {"extension": "md", "count": 12}
    ]
  }
}
```

On failure, return:

```json
{
  "status": "failed",
  "error": "Human-readable description of what went wrong",
  "repo_dir": "/tmp/cwe-remediation/aBcDeFgHiJ"
}
```

### Success Indicators

- `status` is `"success"`.
- `key_files.manifests` contains at least one entry (every meaningful repository has at least one manifest).
- `entry_points` is non-empty for application repositories (may be empty for libraries with no standalone entry point).
- `build_systems` contains at least one entry.

### Failure Indicators

- `status` is `"failed"`.
- `repo_dir` does not exist or is not a git repository.
- The directory tree is empty (may indicate an empty repository or incorrect path).

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| `repo_dir` does not exist | `test -d` returns non-zero | Fail immediately with error message specifying the path. |
| `repo_dir` is not a git repository | `.git` directory missing | Fail immediately. This skill requires a cloned git repository. |
| `tree` command not available | `which tree` returns non-zero | Fall back to `find`-based directory listing. |
| Repository is extremely large (>50,000 files) | `find` count exceeds threshold | Reduce `max_depth` to 2, apply stricter exclude patterns, and note the limitation in the output. |
| File read errors (permissions) | `Read` tool returns error | Skip the unreadable file, log a warning in the output, and continue with remaining files. |
| No manifest files found | `key_files.manifests` is empty | Do not fail. Return the result with an empty manifests list and add a `"warnings"` field noting that no standard manifest files were detected. |
| No entry points found | `entry_points` is empty | Do not fail. This is valid for library-only repositories. Add a note in the output. |
| Command timeout during `find` or `wc` | Process exceeds 30 seconds | Kill the process, return partial results, and note the timeout in the output. |

## Constraints

- **NEVER** modify any files in the repository. This is a read-only analysis skill.
- **NEVER** execute any build commands, install dependencies, or run code from the analyzed repository.
- **NEVER** traverse into `.git/` internals. Exclude `.git` from all searches and listings.
- **NEVER** follow symbolic links outside the repository root to avoid path traversal issues.
- Limit the directory tree output to a maximum of 500 lines. If the tree exceeds this, truncate and add a note.
- Limit `Grep` searches to a maximum of 50 results per pattern to avoid excessive output.
- All file paths in the output must be relative to `repo_dir`, not absolute paths, to ensure portability.
- The total analysis should complete within 60 seconds. If individual steps take longer than 10 seconds, use the partial results and move on.
- Do not include file contents in the output beyond brief descriptions of entry points. This is a structural analysis, not a code review.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
