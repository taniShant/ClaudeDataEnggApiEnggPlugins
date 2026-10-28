---
name: buk-onepipeline-ci-reference
description: >
    Domain reference for BUK One Pipeline CI components and team wrappers (MCA Java/JS, AWSCCEU Go, AWSCCEU Python).
    Load when diagnosing CI failures across Java (Gradle/Maven), JavaScript/Node, Go (Task), and Python (UV) pipelines.
    Contains pipeline stage maps, component-to-job mappings, known failure patterns, wrapper-specific jobs, and their causes.
user-invocable: false
---

# BUK One Pipeline CI Reference

> **Source:** BUK One Pipeline CI (`barclays/digital-platform/cicd-components/pipelines/buk-onepipeline-ci`), MCA pipeline wrappers (`barclays/mca/mca-pipelines`), AWSCCEU Go wrapper (`barclays/awscceu/tools/task-golang-ci-pipeline-cc-wrapper`), AWSCCEU Python wrapper (`barclays/awscceu/tools/python-ci-pipeline-cc-wrapper`) — all inspected 2026-09-28
> **Owner:** BUK DevOps Team (sourabh.agrawal1@barclays.com)
> **Review trigger:** On BUK One Pipeline major version change, or when new failure patterns are confirmed in production
> **Status:** Production — based on direct inspection of buk-onepipeline-ci codebase; validated in production runs

---

## Quick Start

Load this skill when the agent receives a CI failure to diagnose. It provides:

1. **Component lookup** — map the failed job name to a BUK One Pipeline component (section 3–6)
2. **Failure pattern matching** — match log error text to known patterns and their causes
3. **Infrastructure vs application classification** — section 9 distinguishes runner issues from code failures

**When to load:** Immediately on receiving PIPELINE_URL or LOG_CONTENT input — before parsing the log.

**What it returns:** Stage maps, component-to-job mappings, known error patterns, and recommended next steps per pattern.

**Example invocation context:**
```
Job: "unit-test" failed
Tech stack: java-gradle
→ Load section 3 (Java Gradle Component Reference) → unit-test component patterns
→ Scan log for: BUILD FAILED, tests were run + failures, is lower than minimum
→ Classify: application failure (test assertion) or coverage failure
```

---

## 1. Pipeline Templates and Technology Stacks

BUK One Pipeline provides reusable GitLab CI component templates. Consumers include the relevant pipeline template in their `.gitlab-ci.yml`:

| Template | Technology Stack | Key Components |
|----------|-----------------|----------------|
| `pipeline-gradle-java-ci.yml` | Java (Gradle) | checkstyle, build, unit-test, component-test, mutation-test, sbom, sonar, veracode-sast, veracode-sca, publish, docker, contract-test |
| `pipeline-maven-java-ci.yml` | Java (Maven) | build, unit-test, sonar, veracode-sast, veracode-sca, publish |
| `pipeline-node-javascript-ci.yml` | JavaScript/Node | build, unit-test, sonar, veracode-sca, publish |
| `pipeline-task-golang-ci.yml` | Go (Taskfile) | build, unit-test, component-test, sonar, veracode-sca |
| `pipeline-uv-python-ci.yml` | Python (UV) | lint, type-check, unit-test, component-test, sonar, veracode-sca |
| `pipeline-react-native-ci.yml` | React Native | build, unit-test |
| `pipeline-gradle-android-ci.yml` | Android (Gradle) | build, unit-test |
| `pipeline-swift-ios-ci.yml` | iOS (Swift) | build, unit-test |
| `pipeline-terraform-ci.yml` | Terraform | validate, plan |
| `pipeline-cloudformation-ci.yml` | AWS CloudFormation | validate, deploy |

---

## 2. Pipeline Architecture

### Three-Layer Model

Every BUK CI pipeline is composed of up to three layers. Always identify which layers are present before attributing a failure — the layer determines who owns the fix.

```
Layer 1 — BUK One Pipeline (shared platform standard)
    Repo: barclays/digital-platform/cicd-components/pipelines/buk-onepipeline-ci
    Provides: base templates, all standard components (build/test/scan/publish)
    Owned by: BUK DevOps Platform team

Layer 2 — Team wrapper (optional, area-specific centralisation)
    Examples:
      MCA:     barclays/mca/mca-pipelines
      AWSCCEU Go:    barclays/awscceu/tools/task-golang-ci-pipeline-cc-wrapper
      AWSCCEU Python: barclays/awscceu/tools/python-ci-pipeline-cc-wrapper
    Provides: extra jobs, variable overrides, team-specific config on top of Layer 1
    Owned by: the area team (MCA DevOps, AWSCCEU DevOps, etc.)

Layer 3 — Application .gitlab-ci.yml (app-specific)
    Repo: the application repository itself
    Provides: include of Layer 1 or Layer 2 template, app-specific variable values
    Owned by: the application team
```

#### How to detect which layers are present

Fetch the app's `.gitlab-ci.yml` (or check the log for `include:` lines). The include URL reveals the layer:

| Include URL pattern | Layer present |
|---------------------|---------------|
| `...buk-onepipeline-ci...` only | Layer 1 only (pure BUK standard) |
| `...mca-pipelines...` or `customer-care-mca-*` | Layer 2: MCA wrapper |
| `...task-golang-ci-pipeline-cc-wrapper...` | Layer 2: AWSCCEU Go wrapper |
| `...python-ci-pipeline-cc-wrapper...` | Layer 2: AWSCCEU Python wrapper |

If the include points to a team wrapper, also look one level deeper — the wrapper itself includes the BUK base template.

#### Failure layer attribution

Once layers are identified, attribute each failure to the correct layer:

| Failure layer | Definition | Who fixes it |
|---------------|------------|--------------|
| **BUK pipeline** | Bug or misconfiguration in a BUK One Pipeline component or base template | Raise with BUK DevOps Platform team; link `buk-onepipeline-ci` component source |
| **Team wrapper** | Extra job, variable override, or config added by MCA/AWSCCEU wrapper layer | Raise with the area team (MCA DevOps / AWSCCEU DevOps) |
| **App code** | Test failure, build error, coverage below threshold, lint violation | Application team to fix in their repo |
| **App config** | Wrong variable value, missing file, bad path in app's `.gitlab-ci.yml` | Application team to fix pipeline config |
| **Environment** | Runner OOM, CSM auth, Nexus unreachable, GitLab runner crash | Platform/infra team; raise if persistent |

#### Layer attribution heuristics

- Job defined **only** in BUK base template, fails with component error → **BUK pipeline**
- Job defined **only** in team wrapper (e.g. `mca-process-app-config`, `task-go-publish`) → **Team wrapper**
- Job passes elsewhere but fails for this app, error is in app code/tests → **App code**
- Variable missing or wrong value set in app's `.gitlab-ci.yml` → **App config**
- CSM 403, runner OOM, SSH refused, Nexus unreachable across multiple apps → **Environment**
- When in doubt: the layer that introduced the failing job or the failing variable owns the fix

Always include the failure layer in the diagnosis report so the right team can act.

---

### Component Lifecycle (Python)
Every Python component inherits from `ComponentBase` and runs four phases:
1. `parse_args()` — CLI argument parsing
2. `pre()` — input validation and environment setup
3. `run()` — core component logic
4. `post()` — cleanup, metrics writing

Exit code 0 = success. Any non-zero exit = failure.

### Runner Flow
```
App .gitlab-ci.yml  (Layer 3)
    ↓ includes
Team wrapper template  (Layer 2 — if present)
    ↓ includes
BUK base template  (Layer 1: templates/pipeline-*.yml)
    ↓ includes multiple component templates
templates/<component>/template.yml
    ↓ calls Python binary
src/<tech>_components/<component>/component.py
```

### Secrets and Credentials (CSM)
Most jobs extend `.csm_extract_secrets` to pull Nexus and other credentials from CSM (Barclays Vault):
- `csm_safe_id` — ITSI safe ID (default: `snsvc10000`)
- `csm_role_name` — GitLab role name (default: `buk-cicd-gl-role`)
- `csm_secret_name` — secret name (default: `buk-cicd-gl-secret`)
- CSM failures appear as `VAULT_ADDR` errors or 403/401 on Nexus requests

### Nexus (Dependency Repository)
All builds resolve dependencies from internal Nexus:
- Release URL: `https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-releases/`
- Snapshot URL: `https://nexus.barcapint.com/nexus/content/repositories/barclays-restricted-snapshots/`
- Credentials injected via `nexusUsername` / `nexusPassword` Gradle parameters
- 403 Forbidden on Nexus = CSM credentials not retrieved

---

## 3. Java (Gradle) Component Reference

### Stage Order (Gradle Java Pipeline)
```
csm → properties-setup → checkstyle → build → unit-test → component-test
    → mutation-test → sbom → sonar → veracode-sast → veracode-sca
    → docker-build-publish → contract-test-publish → contract-test-verify
    → publish
```

### Component: checkstyle
- **Binary:** `gradle-java-checkstyle`
- **Default Gradle task:** `allCheckstyle`
- **Reports:** `build/reports/checkstyle/main.html`, `build/reports/checkstyle/test.html`
- **Failure pattern:** `Checkstyle rule violations were found` or `violations found` — rule threshold exceeded
- **Common causes:** Code style violations (Google or Sun style), missing Checkstyle config file
- **Fix:** Run `./gradlew allCheckstyle` locally, fix violations, re-push

### Component: build (gradle-java-ci-build)
- **Binary:** `gradle-java-build`
- **Default Gradle task:** `clean build`
- **Outputs:** `build/libs/app.jar`, compiled classes
- **Failure patterns:**
  - `BUILD FAILED` + `Could not resolve` → Nexus connectivity/credentials
  - `BUILD FAILED` + `Compilation error` → code does not compile
  - `BUILD FAILED` + `Execution failed for task ':compileJava'` → Java compile error
- **Common causes:** Dependency resolution failure (CSM not configured), compile error in code change

### Component: unit-test (gradle-java-ci-unit-test)
- **Binary:** `gradle-java-unit-test`
- **Default Gradle task:** `check`
- **Reports:** `build/reports/tests/test/index.html`, `build/reports/jacoco/test/jacocoTestReport.xml`
- **Coverage thresholds:** `unit_test_min_line_coverage`, `unit_test_min_instruction_coverage`, `unit_test_min_branch_coverage`
- **Failure patterns:**
  - `tests were run` + `failures` → test assertion failures — check report for which tests
  - `is lower than minimum` → coverage threshold not met
  - `BUILD FAILED` + `Execution failed for task ':test'` → test compilation or execution error
- **Common causes:** Failing unit tests, coverage regression after code change

### Component: component-test (gradle-java-ci-component-test)
- **Binary:** `gradle-java-component-test`
- **Default Gradle task:** `jacocoIntegrationTestReport`
- **Reports:** `build/reports/integrationTest/index.html`
- **Services:** Requires application and/or dependent services running
- **Failure patterns:**
  - `Connection refused` → application service not started or port wrong
  - `TLS handshake` errors → TLS configuration issue (see Go section for ABC pattern)
  - `BUILD FAILED` + integration test name → specific test failing

### Component: mutation-test (gradle-java-ci-mutation-test)
- **Binary:** `gradle-java-mutation-test`
- **Default Gradle task:** `pitest`
- **Reports:** `build/reports/pit/`
- **Thresholds:** `mut_test_min_line_coverage`, `mut_test_min_mutation_coverage`, `mut_test_min_test_strength`
- **Failure patterns:**
  - `Mutation testing complete` + percentage below threshold → mutation score too low
  - Long-running / timeout → pitest running too long (add exclusions)

### Component: sonar
- **Instances:** `OLD_SONAR` (sonarqube02.barcapint.com) or `NEW_SONAR`
- **Quality gate:** `FAIL_ON_QUALITY_GATE_FAILURE` (default) or `PASS_ON_QUALITY_GATE_FAILURE`
- **Failure patterns:**
  - `Quality gate failed` or `ERROR: SonarQube quality gate failure` → code quality gate not passed
  - `Could not connect to server` → SonarQube connectivity
  - `SONARQUBE_SCAN_TOKEN` error → missing token in CSM

### Component: veracode-sast
- **Scan type:** Static Application Security Testing
- **Artifact:** `build-job-jars/app.jar`
- **Failure patterns:**
  - `Failed to upload` → Veracode upload failure (VID/VKEY credentials)
  - `Severity` + `VERY_HIGH` → scan found high-severity issues above `veracode_sast_fail_on_severity` threshold

### Component: veracode-sca
- **Scan type:** Software Composition Analysis (dependency vulnerabilities)
- **Failure patterns:**
  - `SRCCLR_API_TOKEN` error → missing token
  - `No supported build tool found` → wrong `veracode_sca_scan_type` configured

### Component: publish (gradle-java-ci-publish)
- **Binary:** `gradle-java-publish`
- **Default Gradle task:** `publish`
- **Nexus target:** `barclays-restricted-releases/` or `barclays-restricted-snapshots/`
- **Failure patterns:**
  - `401 Unauthorized` on Nexus PUT → artifact version already exists in an immutable repo (staging repos reject republishing the same version) — bump the version or delete the existing artifact from Nexus
  - `401 Unauthorized` on Nexus GET (during dependency resolution) → missing or expired Nexus credentials from CSM
  - `403 Forbidden` on Nexus → wrong Nexus path or insufficient permissions
  - `Could not publish` → version clash — same version already published

### Component: docker-build-publish
- **Failure patterns:**
  - `Cannot connect to Docker daemon` → Docker service not running in job
  - `UNAUTHORIZED` on registry → Nexus container registry auth failure
  - `Dockerfile not found` → `docker_build_pub_dockerfile_path` wrong

---

## 4. Go (Taskfile) Component Reference

### Pipeline: pipeline-task-golang-ci.yml
Uses [Taskfile](https://taskfile.dev/) (`task` binary) to run Go build and test operations.

### Known Pattern: ABC Component Test — TLS Handshake Error
**Context:** Golang component tests using internal Barclays services over TLS.

**Symptom:**
```
TLS handshake timeout
x509: certificate signed by unknown authority
dial tcp <IP>: i/o timeout
```

**Root cause:** The Go runtime does not trust the Barclays internal CA. Either:
1. The CA bundle is not mounted / injected into the runner container
2. The `GONOSUMCHECK` / `GONOSUMDB` / `GOFLAGS` environment variables are not set
3. The Barclays CA certificate is not in the runner image's system trust store

**Fix patterns:**
- Add `GONOSUMCHECK=*` and `GONOSUMDB=*` to suppress module checksum verification for internal proxies
- Use `SSL_CERT_FILE` or `SSL_CERT_DIR` to point Go to the Barclays CA bundle
- Extend the job with `.csm_extract_secrets` to ensure runner has network credentials
- For ABC (Application Behaviour Component) tests specifically: check that the `abc_*` inputs in `pipeline-task-golang-ci.yml` are correctly configured, particularly `abc_tls_cert_path`

**Evidence lines to look for:**
```
FAIL\t<package>\t[build failed]
--- FAIL: TestABC
tls: failed to verify certificate
```

---

## 5. Python (UV) Component Reference

### Pipeline: pipeline-uv-python-ci.yml
Uses UV as the Python package manager and project runner.

### Stage Order
```
csm → uv-python-build → ruff-lint → mypy-type-check → bandit-security
    → unit-test → component-test → sonar → veracode-sca → publish
```

### Failure patterns

| Pattern | Component | Likely cause |
|---------|-----------|--------------|
| `error[E...]` (ruff) | lint | Code style violation |
| `error:` (mypy) | type-check | Type annotation error |
| `Issue: ` (bandit) | security-scan | Security finding above severity threshold |
| `FAILED tests/` | unit-test | Test assertion failure |
| `coverage: FAIL` | unit-test | Coverage below 85% threshold |
| `ModuleNotFoundError` | any | Missing package — `uv sync` not run or package missing from pyproject.toml |
| `uv: command not found` | any | UV not installed in runner image — wrong builder image |
| `No such file or directory: 'pyproject.toml'` | any | Wrong working directory or missing pyproject.toml |

---

## 6. JavaScript/Node Component Reference

### Pipeline: pipeline-node-javascript-ci.yml

### Failure patterns

| Pattern | Likely cause |
|---------|--------------|
| `npm ERR! code E404` | Package not found in registry |
| `npm ERR! code EACCES` | Permission error |
| `Cannot find module '<name>'` | Missing dependency — run `npm install` |
| `error TS<N>:` | TypeScript compilation error |
| `Test Suites: N failed` | Jest/Mocha test failures |
| `SyntaxError:` | JavaScript/TypeScript parse error |
| `ENOMEM` / `JavaScript heap out of memory` | OOM — increase `--max_old_space_size` |

---

## 7. Properties Setup Component

**Component:** `shared-ci-properties-setup` — runs early, sets pipeline variables consumed by all downstream jobs.

**Key outputs:**
- `APP_FULL_VERSION` — computed artifact version
- `ARTIFACT_ID` — from `gradle.properties` or `project_metadata.yml`
- `GROUP_ID` — from `gradle.properties`

**Failure patterns:**
- `FileNotFoundError: gradle.properties` → missing `gradle.properties` at `properties_setup_properties_file_path`
- `FileNotFoundError: project_metadata.yml` → missing `project_metadata.yml` at `properties_setup_project_metadata_file_path`
- `KeyError: ARTIFACT_ID` → required field missing from `gradle.properties`

If properties-setup fails, ALL downstream jobs will fail with missing variable errors. Always check the properties-setup job first.

---

## 8. CSM (Central Secrets Manager) Component

**Purpose:** Pulls credentials (Nexus username/password, scan tokens) from Barclays Vault before each job.

**Failure patterns:**
- `Error reading secret` or `permission denied` → wrong `csm_safe_id` or `csm_role_name`
- `VAULT_ADDR: not set` → CSM endpoint not reachable or env variable missing
- `Error logging in` → GitLab JWT token expired or role misconfigured
- `403 on Nexus` after a successful CSM step → CSM retrieved a wrong or expired credential

**Impact:** If CSM fails, subsequent `nexusUsername`/`nexusPassword` parameters will be empty, causing Nexus 401/403 errors in build and publish jobs.

---

## 9. Compliance Verification Component

**Purpose:** Reads metric artifacts from all upstream jobs and validates them against agreed thresholds. A compliance gate — not optional.

**Important:** All jobs covered by compliance-verification are agreed pipeline standards. Never recommend disabling, ignoring, or bypassing any metric check. If a metric is absent or below threshold, the fix is to resolve the underlying issue, not to work around the gate.

**Failure patterns:**

| Pattern | Likely cause | Correct next step |
|---------|-------------|-------------------|
| `None of the metrics ['cicd.pipeline.<metric>'] found` | Upstream job ran but did not emit the metric — often because the condition that generates it did not trigger (e.g. no mutations found for changed files, no test output produced) | Investigate why the upstream job produced no metric. Check the job artifact JSON directly. If the mutation test found zero mutations, investigate whether the changed code is in scope for mutation testing |
| `Compliance Verification Status: FAILURE` + metric value below threshold | Code change caused a metric to drop below the agreed threshold | Fix the code: add tests, fix security findings, reduce vulnerabilities |
| `Failed to get metric ... from ...logs.json` | Artifact file exists but the expected key is absent | Inspect the artifact JSON to see what keys were written. May indicate a version mismatch between the task library and compliance component |
| `Error processing ..._logs.json` | Artifact file is malformed or missing | Check the upstream job for partial failure or early exit that prevented artifact upload |

**Diagnosing a missing mutation metric specifically:**

When `cicd.pipeline.new_test_mutation_coverage_percent` is absent:
1. Download the mutation test job artifact and check which keys are present
2. Check `.gremlins.yml` — if the changed file path is excluded, no mutations run and no metric is emitted
3. Check whether the changed code contains any mutable statements (pure config changes, test-only changes, and interface-only files may produce zero mutations)
4. Raise with the pipeline component team if the task library version has changed the metric key — do not bypass the check

---

## 10. Infrastructure and Runner Issues

These are NOT application failures — they indicate a problem with the GitLab runner or its environment.

| Signal | Type | Recommended action |
|--------|------|--------------------|
| `Runner system failure` | Runner crash | Retry the job; if repeated, report to DevOps |
| `exit code 137` | OOM kill | Increase runner memory or reduce parallel tasks |
| `exit code 143` | Timeout | Increase job timeout or optimise slow operation |
| `fatal: unable to access 'https://...'` | Git clone failure | Check runner network access to GitLab |
| `SSH: Connection refused` | SSH runner issue | Report to pipeline platform team |
| `No space left on device` | Runner disk full | Report to pipeline platform team |
| `Docker daemon not running` | Docker service | Check job uses correct Docker-in-Docker configuration |

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Failed job has been identified by name and mapped to a BUK One Pipeline component
- [ ] Log has been searched for at least 3 of the failure signal patterns listed in sections 3–9
- [ ] Failure type has been classified using the 7-category taxonomy in the agent
- [ ] If the failure is a Nexus 403/401, CSM component and credential flow has been checked
- [ ] If the failure is a test failure, the specific failing test names have been extracted from the log
- [ ] If the failure is a coverage or mutation threshold, the actual vs. required value has been quoted
- [ ] If no matching failure pattern was found, this has been stated in the Flags section
- [ ] Report does NOT recommend disabling, skipping, or ignoring any pipeline job, stage, or metric check
- [ ] Report does NOT recommend lowering thresholds or adding `allow_failure` to existing jobs
- [ ] All recommended next steps address the root cause, not a workaround to the pipeline gate

---

---

## 11. MCA Pipeline Wrappers (Java + JavaScript)

Source: `barclays/mca/mca-pipelines` (develop branch)

MCA teams use wrapper templates that layer on top of BUK One Pipeline. When diagnosing a failure in an MCA Java or JavaScript project, check which wrapper template it uses — extra jobs and overrides apply.

### MCA wrapper templates

| Template | Stack | Extra jobs vs BUK baseline |
|----------|-------|---------------------------|
| `customer-care-mca-java-ci-pipeline.yml` | Java (apps) | mca-process-app-config, mca-rvd-check, cypress-testing, deploy-component-testing (BYOF), cleanup-and-release-resources |
| `customer-care-mca-batch-ci-pipeline.yml` | Java (libs/batch) | mca-libs-version-config; deployment/helm/component test jobs DISABLED |
| `customer-care-api-java-ci-pipeline.yml` | Java (REST APIs) | Different Nexus repos (barclays-restricted-*), different runner tags |
| `customer-care-mca-javascript-ci-pipeline.yml` | JavaScript (apps) | node-javascript-fixture-test, Lerna/Turbo monorepo publish support |
| `customer-care-mca-libs-javascript-ci-pipeline.yml` | JavaScript (libs) | 6h mutation test timeout, full file artifact preservation |

### MCA-specific jobs and their failure patterns

**`gradle-java-properties-setup`** (clones mca-pipelines repo, runs `load_exceptions.py`)
- Failure: SSH access to GitLab fails, or `load_exceptions.py` errors on malformed exception config

**`mca-process-app-config`** (clones Process App config from Bitbucket `pcbepsconf`)
- Failure patterns: `SSH: Connection refused` (Bitbucket unreachable), missing config file in cloned repo
- This job runs early — its failure blocks downstream deployment jobs

**`mca-rvd-check`** (Runtime Vulnerability Detection — `allow_failure: true`)
- Non-blocking. Failure here does not block the pipeline but is monitored separately.

**`cypress-testing`** (UI testing — only runs if `CYPRESS_TEST_REPO_URL` is set)
- Failure patterns: SSH key missing for Bitbucket, Xvfb not starting, `npm run cypress-test-gitlab` exit 1

**`deploy-component-testing`** (BYOF component tests against deployed app)
- If `BCP_DEPLOYMENT_NAME` is empty (because helm-bcp-deployment failed), the service URL is malformed (`-<BOB_ID>.<cluster>...`) and DNS resolution fails
- Always check helm-bcp-deployment first if component testing shows DNS/connection errors

**`node-javascript-mutation-test N/M`** (Stryker JS mutation testing — parallelised, typically 5 shards)
- Each shard runs Stryker against a slice of the mutant pool across 755+ source files (34,435 mutants total in observed runs)
- **Job execution timeout (3h):** exit code 143 (128 + SIGTERM 15) — shard ran past the GitLab 3h job limit; repeated "No tests found" messages are from worker child processes killed by SIGTERM, not genuine test failures
  - Fix: increase timeout in `.gitlab-ci.yml` (`timeout: 4h`), reduce Stryker scope (exclude generated/fixture files), or increase shard count to reduce per-shard load
- **ChildProcessCrashedError:** worker process killed mid-run — almost always the timeout case above
- **Mutation score below threshold:** Stryker reports a score below the configured minimum — increase test coverage for the mutated files
- Note: `customer-care-mca-libs-javascript-ci-pipeline.yml` already uses a 6h timeout; if a libs project is still timing out, shard count or scope reduction is needed

**`cleanup-and-release-resources`** (runs `always` — Helm cleanup)
- Removes ci-${PIPELINE_ID} releases and stale releases >1 hour old
- Failure here does not block the pipeline result but may leave orphaned Helm releases

**`helm-bcp-deployment`** — BCP cluster: `hc9-np-gl`, namespace BOB ID: `46082`
- PKI cert validation fails → check `deployment_logs/` artifact → validate PKI config ID and BOB ID allowlisting
- See `.deployment_failure_suggestion` anchor in `scripts/deploy-bcp.yml` for the diagnostic checklist embedded in the pipeline itself

### MCA-specific variables to note in logs

| Variable | MCA value | Significance |
|----------|-----------|--------------|
| `CSM_ROLE_NAME` | `buk-cicd-gl-role` | Different from AWSCCEU wrapper |
| `CSM_SECRET_NAME` | `buk-cicd-gl-secret` | Different from AWSCCEU wrapper |
| `CLUSTER_NAME` | `hc9-np-gl` | BCP OpenShift cluster |
| `BCP_BOB_ID` | `46082` | OpenShift namespace |
| Nexus (apps) | `buk-releases` / `buk-staging` | Different from API wrapper |
| Nexus (APIs) | `barclays-restricted-releases` / `barclays-restricted-snapshots` | Different from app wrapper |

### `.validate_no_overrides` — MCA build breaker

`scripts/mca-pipeline-config.yml` contains a `.validate_no_overrides` anchor that fails the pipeline if the application's own `.gitlab-ci.yml` attempts to override test coverage thresholds. If you see a failure with a message about overrides being disallowed, the fix is to remove the threshold override from the application repo — not to change the pipeline.

---

## 12. AWSCCEU Go Pipeline Wrapper

Source: `barclays/awscceu/tools/task-golang-ci-pipeline-cc-wrapper`

AWSCCEU Go projects use this wrapper over `pipeline-task-golang-ci@3.0`.

### Wrapper templates

| Template | Purpose | Key difference |
|----------|---------|----------------|
| `templates/app.yml` | Full Go apps with ABC testing | Veracode enabled, `abc_deployment_account: 097270639671`, `abc_deployment_region: eu-west-2` |
| `templates/lib.yml` | Go libraries | No build, no component test, no Veracode |
| `templates/basic.yml` | Terraform-only / minimal Go | All Go jobs disabled; uses `raw-publish.barcapint.com` |
| `templates/ife.yml` | Internet Facing Environment | `GOTOOLCHAIN: go1.25.0+auto`, different Nexus (`barclaysint-releases`) |
| `templates/terraform-basic.yml` | Terraform + Sonar only | Base is `pipeline-terraform-ci@main`, not Go |
| `templates/terraform-app.yml` | Terraform + Go hybrid | Base is `pipeline-terraform-ci@main` + Go jobs |

### AWSCCEU-specific variables and CSM identity

| Variable | Value | Significance |
|----------|-------|--------------|
| `csm_auth_url` | `https://csm-uk1-stg.barcapint.com:8200/v1/CSM/auth/jwt/login` | Staging CSM (not prod) |
| `csm_role` | `ci1215208834_gitlab_gitlab-role` | Primary AWSCCEU CSM role |
| `csm_role_mca` | `snsvc0042565_gitlab_mca-gitlab-role` | MCA service account role |
| `GROUP_ID` | `barclays/awscceu` | Nexus artifact grouping |
| `abc_deployment_account` | `097270639671` | AWS account for ABC tests |
| `abc_deployment_region` | `eu-west-2` | AWS region for ABC tests |

### AWSCCEU Go-specific failure patterns

**CSM authentication** — `csm-uk1-stg.barcapint.com` (staging CSM endpoint). If this times out or returns 403, all jobs that need Nexus or scan credentials will fail. Distinct from the production CSM endpoint used by MCA.

**ABC test / CloudFormation stack** — ABC tests deploy to AWS account `097270639671` eu-west-2 via SAM CLI. If the stack (`abc-<pipeline-id>-<service-name>`) is in `ROLLBACK_COMPLETE`, SAM cannot create a changeset. Fix: delete the stale stack in AWS console, then retry. (This is the pattern seen in `open-question-connect-agent` pipeline 25304518.)

**LocalStack image** — `nexus-amazon-dev-docker-registry.barclays.intranet/external/docker.io/localstack/localstack:4.3.0` used in component tests. If this image is unavailable, component tests fail at container pull before any test runs.

**`publish-consolidated-test-reports`** — Secondary component always included. If this job fails, it indicates the test report artifact from a prior job is missing or malformed, not a test failure itself.

**IFE template (`ife.yml`)** — Uses `GOTOOLCHAIN: go1.25.0+auto`. If Go version mismatch errors appear, this explicit toolchain pin is the cause.

**`task-go-publish` → Nexus 400 `Only letters, digits, underscores(_), hyphens(-), and dots(.) are allowed`** — The Maven artifact upload endpoint (`/nexus/service/local/artifact/maven/content`) rejects forward slashes in the `g` (group) form field. The AWSCCEU Go wrapper passes `GROUP_ID=barclays/awscceu` which contains `/`. Fix: change the `nexus_group` pipeline variable to use `.` or `-` instead (e.g. `barclays.awscceu`). Helios `artefact-check`/`artefact-link` failures that follow are cascades — they resolve once publish succeeds.

---

## 13. AWSCCEU Python Pipeline Wrapper

Source: `barclays/awscceu/tools/python-ci-pipeline-cc-wrapper`

AWSCCEU Python projects use this wrapper over `pipeline-uv-python-ci@3.0`.

### Extra stages added

```
.pre → build_and_verify → scan → publish → runtime_testing → cleanup
     → compliance → fetch_git_details → send_git_details
     → fetch_mr_details → send_merge-request_details → .post
```

### Extra jobs not in vanilla BUK Python pipeline

**`sonar-setup`** (stage: `.pre`) — Clones wrapper repo and copies `sonar-project.properties` if absent.
- Failure: GitLab clone fails (SSH/token issue), or wrapper repo branch `main` not accessible
- Only runs if `SONAR_PROJECT_NAME != "NOT_PRESENT"`

**`rename-artifact`** (stage: `build_and_verify`) — Renames build ZIP to `product-<name>.zip`.
- Failure: `uv-python-build` artifact missing or no ZIP found in `dist/` — check build job first
- Downstream jobs that expect `product-*.zip` will fail if this job fails

**CloudFormation downstream pipeline** — Always triggered in parallel via `templates/wrapper.yml`.
- Failure: `cfn_downstream_pipeline` failing blocks the parent pipeline (`strategy: depend`)
- Check CloudFormation template at `cfn_lint_template_location` (default: `deployments/template.yml`)

**`analyze_vulnerabilities.py`** — Parses Prisma Cloud scan JSON; fails if critical CVEs without acceptance tags exist.
- Failure message: untagged critical vulnerabilities found
- Fix: tag the vulnerability in Prisma Cloud as accepted/mitigated, or upgrade the affected dependency

**`prepare_promotion_pipeline.py`** — Veracode promotion pipeline scheduler.
- Only runs in promotion context; failure here affects Veracode promotion scheduling, not the main build

### AWSCCEU Python-specific variables and CSM identity

| Variable | Value | Significance |
|----------|-------|--------------|
| `csm_safe_id` | `ci1204967649` | AWSCCEU Python CSM Safe ID (differs from Go wrapper) |
| `csm_role_name` | `gitlab-role-buksmartans` | CSM role for Python projects |
| `SYSTEM_ACCOUNT` | `sysBUKChatDevTools` | Service account for all operations |
| `sonar_workspace_key` | `buksmartans` | SonarQube workspace |
| Nexus publish | `https://raw-publish.barcapint.com/repository/raw-hosted/` | Raw artifact repo (not Maven) |
| `MULTI_MODULE_REPO` | `true` | Affects build artifact detection |

### AWSCCEU Python-specific failure patterns

**`uv-python-unit-test` is `allow_failure: true`** in this wrapper. A unit test failure will not block the pipeline — check the compliance-verification job to see if coverage thresholds still enforce it.

**`uv-python-format`, `uv-python-type-check`, `uv-python-lint`, `uv-python-sbom`** — All `allow_failure: true`. These are soft gates; their failure is reported but does not block.

**`uv-python-cosmicray-mutation-test`** — Parallelised (5 workers, 12 `cosmicray_num_workers`). If one shard fails, the whole mutation test fails. Check which shard failed and what mutation it was testing.

**Scheduled pipeline (`bi_monthly_security_scan`)** — A special scheduled pipeline runs a reduced job set (mainly scans). If a scan job fails in this context, it is a security scan finding, not a code regression.

**Sonar `sonar-project.properties`** — Expected at repo root. If `sonar-setup` fails to copy it, `sonar-scan` will fail with a missing configuration error. The source is in the wrapper repo at `barclays/awscceu/tools/python-ci-pipeline-cc-wrapper`.

**Artifact path** — SonarQube coverage report expected at `test-coverage/src/*/coverage.xml`. If the path differs (e.g., the project structure changed), Sonar will report 0% coverage and may fail the quality gate.

---

## Areas for Specialist Extension

This skill covers BUK One Pipeline plus the MCA and AWSCCEU wrappers. The following areas need extension by the relevant teams:

- **Android/iOS platform teams** — Add platform-specific failure patterns for `pipeline-gradle-android-ci.yml` and `pipeline-swift-ios-ci.yml`
- **Infrastructure teams** — Add Terraform and CloudFormation failure patterns for `pipeline-terraform-ci.yml` and `pipeline-cloudformation-ci.yml`
- **Security teams** — Expand Veracode, Wiz, and Prisma failure patterns with specific CVE remediation guidance
- **Pact/contract testing** — Extend contract-test publish/verify failure patterns once usage patterns are established
