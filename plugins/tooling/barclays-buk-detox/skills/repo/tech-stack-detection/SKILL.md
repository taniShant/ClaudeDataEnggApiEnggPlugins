---
name: tech-stack-detection
description: "Technology Stack Detection — Detect the complete technology stack of a cloned repository, including programming languages, frameworks, package managers, test frameworks, linters, formatters, CI/CD systems, and infrastructure tool"
user-invocable: false
source: barclays-claude-code-plugins/plugins/detox/skills/repo/SKILL.md
owner: Detox Team (DETOX PRJ Teams channel, http://detox/)
review-trigger: When new CWE patterns are identified or Semgrep rules change
status: Full
---

# Technology Stack Detection
## Quick Start

This skill provides repository management patterns (clone, branch, analyse structure).

```
# Loaded by detox-orchestrator-agent during the Repository Setup phase.
# Clones the target repo, creates a working branch, and detects the tech stack.
```



## Purpose

Detect the complete technology stack of a cloned repository, including programming languages, frameworks, package managers, test frameworks, linters, formatters, CI/CD systems, and infrastructure tooling. Output a structured JSON report of all detected components with confidence levels, enabling downstream skills to select the correct CWE remediation strategies and language-specific fix patterns.

## Inputs

- **repo_dir** (required, string): Absolute path to the root of the cloned repository to analyze.
- **structure_summary** (optional, JSON object): Output from the `structure_analysis` skill. If provided, reuse its findings to avoid redundant file scanning. If omitted, perform independent detection.
- **detect_versions** (optional, boolean): Whether to extract version numbers for detected components. Defaults to `true`.

## Steps

1. **Validate the repository directory.**
   - Use `Bash` to confirm the directory exists and is a git repository: `test -d <repo_dir>/.git && echo "OK"`.
   - If the check fails, return an error immediately.

2. **Detect programming languages.**
   - Use `Bash` to count files by extension: `find <repo_dir> -type f -not -path '*/.git/*' -not -path '*/node_modules/*' -not -path '*/__pycache__/*' -not -path '*/.venv/*' -not -path '*/venv/*' -not -path '*/vendor/*' -not -path '*/dist/*' -not -path '*/build/*' | sed 's/.*\.//' | sort | uniq -c | sort -rn`.
   - Map file extensions to languages using these mappings:
     - `.py` -> Python
     - `.js`, `.mjs`, `.cjs` -> JavaScript
     - `.ts`, `.tsx` -> TypeScript
     - `.jsx` -> JavaScript (React)
     - `.java` -> Java
     - `.kt`, `.kts` -> Kotlin
     - `.go` -> Go
     - `.rs` -> Rust
     - `.rb` -> Ruby
     - `.cs` -> C#
     - `.cpp`, `.cc`, `.cxx`, `.c`, `.h`, `.hpp` -> C/C++
     - `.php` -> PHP
     - `.swift` -> Swift
     - `.scala` -> Scala
     - `.sh`, `.bash` -> Shell
     - `.sql` -> SQL
   - For each detected language, record the file count and calculate the percentage of total source files.
   - Classify each language as `"primary"` (>30% of source files), `"secondary"` (5-30%), or `"minor"` (<5%).
   - Check for language version specifications:
     - Python: use `Read` on `pyproject.toml` (look for `requires-python`), `.python-version`, `runtime.txt`, or `setup.cfg`.
     - Node.js: use `Read` on `package.json` (look for `engines.node`), `.nvmrc`, `.node-version`.
     - Java: use `Read` on `pom.xml` (look for `maven.compiler.source`), `build.gradle` (look for `sourceCompatibility`).
     - Go: use `Read` on `go.mod` (look for the `go` directive).
     - Rust: use `Read` on `rust-toolchain.toml` or `rust-toolchain`, `Cargo.toml` (look for `edition`).

3. **Detect frameworks and libraries.**
   - For each primary and secondary language detected, inspect the relevant dependency manifest:
   - **Python** -- use `Read` on `pyproject.toml` (`[project.dependencies]` and `[project.optional-dependencies]`), `requirements*.txt`, or `Pipfile`:
     - Web: `flask`, `django`, `fastapi`, `starlette`, `tornado`, `aiohttp`, `sanic`, `bottle`
     - ORM: `sqlalchemy`, `django.db`, `tortoise-orm`, `peewee`
     - API: `graphene`, `strawberry`, `pydantic`, `marshmallow`
     - Task queues: `celery`, `rq`, `dramatiq`
     - CLI: `click`, `typer`, `argparse` (stdlib)
   - **JavaScript/TypeScript** -- use `Read` on `package.json` (`dependencies` and `devDependencies`):
     - Frontend: `react`, `vue`, `angular`, `svelte`, `next`, `nuxt`, `gatsby`
     - Backend: `express`, `fastify`, `koa`, `nestjs`, `hapi`
     - ORM: `prisma`, `typeorm`, `sequelize`, `knex`, `drizzle-orm`
     - Utility: `lodash`, `axios`, `zod`, `joi`
   - **Java/Kotlin** -- use `Read` on `pom.xml` or `build.gradle` / `build.gradle.kts`:
     - Frameworks: `spring-boot`, `spring-framework`, `quarkus`, `micronaut`, `jakarta`
     - ORM: `hibernate`, `mybatis`, `jooq`
   - **Go** -- use `Read` on `go.mod` (the `require` block):
     - Web: `gin`, `echo`, `fiber`, `chi`, `gorilla/mux`
     - ORM: `gorm`, `ent`, `sqlx`
   - **Rust** -- use `Read` on `Cargo.toml` (`[dependencies]`):
     - Web: `actix-web`, `axum`, `rocket`, `warp`
     - ORM: `diesel`, `sqlx`, `sea-orm`
   - **C#/.NET** -- use `Read` on `*.csproj` files:
     - Frameworks: `Microsoft.AspNetCore`, `Microsoft.EntityFrameworkCore`
   - Record each detected framework with its version (if `detect_versions` is true) and category.

4. **Detect package managers.**
   - Identify which package managers are in use based on lock files and configuration:
     - `poetry.lock` -> Poetry
     - `Pipfile.lock` -> Pipenv
     - `requirements*.txt` (without Poetry/Pipenv) -> pip
     - `uv.lock` or `uv.toml` -> uv
     - `package-lock.json` -> npm
     - `yarn.lock` -> Yarn (check for `.yarnrc.yml` to distinguish Yarn Classic vs Yarn Berry)
     - `pnpm-lock.yaml` -> pnpm
     - `bun.lockb` -> Bun
     - `go.sum` -> Go modules
     - `Cargo.lock` -> Cargo
     - `Gemfile.lock` -> Bundler
     - `composer.lock` -> Composer (PHP)
   - Use `Glob` to search for these lock files at the repository root and one level deep (for monorepo support).

5. **Detect test frameworks.**
   - Search for test configuration and usage patterns:
   - **Python**:
     - Use `Glob` to find `pytest.ini`, `conftest.py`, `setup.cfg` (look for `[tool:pytest]`), `pyproject.toml` (look for `[tool.pytest]`).
     - Use `Grep` to search for `import unittest`, `import pytest`, `from pytest`, `from unittest`.
     - Detect: `pytest`, `unittest`, `nose2`, `hypothesis`, `tox`, `nox`.
   - **JavaScript/TypeScript**:
     - Use `Glob` to find `jest.config.*`, `.mocharc.*`, `vitest.config.*`, `cypress.config.*`, `playwright.config.*`.
     - Use `Read` on `package.json` to check `devDependencies` for `jest`, `mocha`, `vitest`, `cypress`, `playwright`, `testing-library`.
   - **Java/Kotlin**:
     - Use `Grep` to search for `import org.junit`, `import org.testng`, `import io.kotest`.
     - Check build files for `testImplementation` or `<scope>test</scope>` dependencies.
   - **Go**:
     - Use `Grep` to search for `import "testing"`, `github.com/stretchr/testify`.
   - **Rust**:
     - Use `Grep` to search for `#[cfg(test)]`, `#[test]`.
   - Record each detected test framework.

6. **Detect linters and formatters.**
   - Use `Glob` to search for configuration files:
     - Python: `.flake8`, `.pylintrc`, `ruff.toml`, `pyproject.toml` (sections `[tool.ruff]`, `[tool.black]`, `[tool.isort]`, `[tool.mypy]`), `.mypy.ini`, `.bandit`
     - JavaScript/TypeScript: `.eslintrc*`, `.prettierrc*`, `biome.json`, `.stylelintrc*`, `tsconfig.json`
     - Go: `.golangci.yml`, `.golangci.yaml`
     - Rust: `rustfmt.toml`, `.rustfmt.toml`, `clippy.toml`
     - General: `.editorconfig`, `.pre-commit-config.yaml`
   - For each configuration file found, identify the tool and record it.

7. **Detect CI/CD systems.**
   - Use `Glob` to search for:
     - `.github/workflows/*.yml` or `.github/workflows/*.yaml` -> GitHub Actions
     - `.gitlab-ci.yml` -> GitLab CI
     - `Jenkinsfile` -> Jenkins
     - `.circleci/config.yml` -> CircleCI
     - `azure-pipelines.yml` or `.azure-pipelines/` -> Azure DevOps
     - `.travis.yml` -> Travis CI
     - `bitbucket-pipelines.yml` -> Bitbucket Pipelines
     - `.buildkite/pipeline.yml` -> Buildkite
   - Record each detected CI/CD system and its configuration file path.

8. **Detect infrastructure and deployment tooling.**
   - Use `Glob` to search for:
     - `Dockerfile`, `docker-compose.yml`, `docker-compose.yaml` -> Docker
     - `*.tf`, `*.tfvars` -> Terraform
     - `serverless.yml`, `serverless.yaml` -> Serverless Framework
     - `cdk.json`, `cdk.context.json` -> AWS CDK
     - `pulumi.yaml`, `Pulumi.yaml` -> Pulumi
     - `kubernetes/`, `k8s/`, `*.yaml` containing `apiVersion:` -> Kubernetes manifests
     - `helm/`, `Chart.yaml` -> Helm charts
     - `ansible/`, `playbook.yml` -> Ansible
   - Record each detected tool with its configuration path.

9. **Detect security tooling already in place.**
   - Use `Glob` and `Grep` to search for:
     - `.semgrep.yml`, `.semgrep/` -> Semgrep
     - `.snyk`, `.snyk.yml` -> Snyk
     - `.trivyignore`, `trivy.yaml` -> Trivy
     - `bandit` configuration in `pyproject.toml` or `.bandit` -> Bandit
     - `safety` in requirements or config -> Safety
     - `npm audit`, `yarn audit` in CI workflows -> npm/yarn audit
     - `dependabot.yml` in `.github/` -> Dependabot
     - `renovate.json`, `.renovate.json` -> Renovate
   - Record each detected security tool.

10. **Assign confidence levels.**
    - For each detected component, assign a confidence level:
      - `"high"`: Component identified by its canonical lock file, configuration file, or import statement. No ambiguity.
      - `"medium"`: Component inferred from dependency lists or file extensions, but not confirmed by a dedicated configuration file.
      - `"low"`: Component presence is speculative, based solely on file extensions of minor languages or indirect references.
    - Primary languages with dedicated manifest files should always be `"high"` confidence.

11. **Compile and return the structured JSON report.**
    - Assemble all findings into the output format specified below.

## Output Format

Return a JSON object with the following structure:

```json
{
  "status": "success",
  "repo_dir": "/tmp/cwe-remediation/aBcDeFgHiJ",
  "languages": [
    {
      "name": "Python",
      "version": "3.12",
      "classification": "primary",
      "file_count": 45,
      "percentage": 62.5,
      "confidence": "high"
    },
    {
      "name": "JavaScript",
      "version": null,
      "classification": "secondary",
      "file_count": 15,
      "percentage": 20.8,
      "confidence": "high"
    }
  ],
  "frameworks": [
    {
      "name": "FastAPI",
      "version": "0.111.0",
      "language": "Python",
      "category": "web",
      "confidence": "high"
    },
    {
      "name": "SQLAlchemy",
      "version": "2.0.30",
      "language": "Python",
      "category": "orm",
      "confidence": "high"
    },
    {
      "name": "React",
      "version": "18.3.1",
      "language": "JavaScript",
      "category": "frontend",
      "confidence": "high"
    }
  ],
  "package_managers": [
    {
      "name": "Poetry",
      "language": "Python",
      "lock_file": "poetry.lock",
      "confidence": "high"
    },
    {
      "name": "npm",
      "language": "JavaScript",
      "lock_file": "package-lock.json",
      "confidence": "high"
    }
  ],
  "test_frameworks": [
    {
      "name": "pytest",
      "language": "Python",
      "config_file": "pyproject.toml",
      "confidence": "high"
    },
    {
      "name": "Jest",
      "language": "JavaScript",
      "config_file": "jest.config.js",
      "confidence": "high"
    }
  ],
  "linters_formatters": [
    {
      "name": "Ruff",
      "language": "Python",
      "config_file": "pyproject.toml",
      "category": "linter",
      "confidence": "high"
    },
    {
      "name": "mypy",
      "language": "Python",
      "config_file": "pyproject.toml",
      "category": "type_checker",
      "confidence": "high"
    },
    {
      "name": "ESLint",
      "language": "JavaScript",
      "config_file": ".eslintrc.json",
      "category": "linter",
      "confidence": "high"
    }
  ],
  "ci_cd": [
    {
      "name": "GitHub Actions",
      "config_files": [".github/workflows/ci.yml", ".github/workflows/deploy.yml"],
      "confidence": "high"
    }
  ],
  "infrastructure": [
    {
      "name": "Docker",
      "config_files": ["Dockerfile", "docker-compose.yml"],
      "confidence": "high"
    }
  ],
  "security_tools": [
    {
      "name": "Semgrep",
      "config_file": ".semgrep.yml",
      "confidence": "high"
    },
    {
      "name": "Dependabot",
      "config_file": ".github/dependabot.yml",
      "confidence": "high"
    }
  ]
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
- `languages` contains at least one entry.
- All detected components have a `confidence` field.
- Version fields are populated when `detect_versions` is `true` and version information is available (null when not determinable).

### Failure Indicators

- `status` is `"failed"`.
- `repo_dir` does not exist or is not a git repository.
- `languages` is empty (may indicate an empty repository or a repository containing only non-code assets).

## Error Handling

| Failure Mode | Detection | Action |
|---|---|---|
| `repo_dir` does not exist | `test -d` returns non-zero | Fail immediately with error message specifying the path. |
| `repo_dir` is not a git repository | `.git` directory missing | Fail immediately. This skill requires a cloned git repository. |
| Manifest file is malformed or unreadable | `Read` tool returns a parse error or unexpected content | Skip the problematic file, log a warning in the output under a `"warnings"` field, and continue detecting from other sources. |
| No programming languages detected | File extension counting yields zero source files | Return `"status": "success"` with empty `languages` array and a `"warnings"` field noting the repository may contain only non-code assets. |
| Monorepo with multiple package manifests | Multiple `package.json` or `pyproject.toml` files found at different paths | Detect all sub-projects. Include the relative path prefix for each component to distinguish them. Add a `"monorepo": true` flag to the output. |
| Extremely large repository (>50,000 files) | `find` file count exceeds threshold | Apply stricter exclude patterns, limit file scanning depth to 2, and add a warning about incomplete results. |
| Version not determinable | Manifest does not specify a version constraint | Set the `version` field to `null` for that component. Do not fail. |
| Conflicting signals (e.g., both Poetry and Pipenv lock files) | Multiple lock files for the same ecosystem detected | Report all detected package managers. Add a `"warnings"` entry noting the conflict and suggesting the user verify which is active. |

## Constraints

- **NEVER** modify any files in the repository. This is a read-only detection skill.
- **NEVER** execute any code from the repository, install dependencies, or run build commands.
- **NEVER** execute `pip install`, `npm install`, `go build`, `cargo build`, or any similar commands.
- **NEVER** traverse into `.git/` internals.
- **NEVER** follow symbolic links outside the repository root.
- All file paths in the output must be relative to `repo_dir`.
- Limit `Grep` searches to a maximum of 50 results per pattern.
- Limit `Read` operations to the first 100 lines of each manifest file to avoid reading unnecessarily large files.
- The total detection process should complete within 60 seconds. If individual steps exceed 10 seconds, capture partial results and continue.
- When `structure_summary` is provided as input, reuse its `key_files` data instead of re-scanning the filesystem for manifest files. This avoids redundant I/O.
- Do not include file contents in the output. Only report component names, versions, categories, paths, and confidence levels.
- Confidence levels must be assigned objectively based on the detection method, not inflated. Use `"low"` when detection is purely heuristic.

## Agent Self-Check

- [ ] Skill loaded before the pipeline stage it governs
- [ ] CWE classification confirmed before applying fix pattern
- [ ] Language-specific fix pattern applied (not generic fallback) where available
- [ ] Semgrep validation re-scan executed after fix to confirm vulnerability eliminated
- [ ] Security regression test generated for the remediated finding
- [ ] Audit trail entry written to DETOX-REMEDIATION-REPORT
