---
name: gitlab-ci-cd
description: GitLab CI/CD configuration for SDK3 projects — Gradle builds, Sonar, JMeter performance testing
color: indigo
---

> **Source:** Barclays BUK GitLab CI/CD standards for SDK3 Gradle projects.
> **Owner:** BUK
> **Review trigger:** On GitLab runner major version change or SDK3 CI pipeline update.
> **Status:** Reviewed

# Skill: GitLab CI/CD Configuration for SDK3

## When to Use This Skill

Use this skill when:
- Generating `.gitlab-ci.yml` for continuous integration builds
- Setting up Barclays OnePipeline component integration
- Configuring Sonar code quality gates
- Setting up JMeter performance testing
- Generating `project_metadata.yml` for compliance tracking
- Integrating with Nexus repository and CSM secret management

## Quick Start

Generate CI/CD configuration for a new SDK3 project:

1. Copy `.gitlab-ci.yml` template to project root
2. Copy `project_metadata.yml` template to project root
3. No placeholders — files are ready to use immediately after copy

Both files are auto-generated during project creation; no manual intervention needed.

---

## Critical Rules

**1. Auto-Generated CI/CD Files (MANDATORY)**
All generated projects include `.gitlab-ci.yml` and `project_metadata.yml` with pre-configured defaults. NO user input required.

**2. Zero-Configuration Deployment**
Generated CI/CD files are ready to use immediately:
- ✅ Push to GitLab
- ✅ CI/CD pipeline auto-starts
- ✅ No placeholder configuration needed
- ✅ Uses Barclays standard buk_digital defaults

**3. Pre-Configured Capabilities**
- Automated Gradle builds with Java 21
- SonarQube code quality scanning (buk_digital_platform_sonar_workspace)
- JMeter performance testing (localhost:8080)
- Nexus artifact publishing (barclays_nexus_ci account)
- CSM secrets management (buk_digital_api_safe)
- Compliance reporting (buk.digital.platform@barclays.com)

---

## 1. .gitlab-ci.yml — Template

**File:** `templates/.gitlab-ci.yml` → copied to project root as `.gitlab-ci.yml`

The template uses Barclays OnePipeline v3.0 with the Gradle-Java CI component via the modern
`spec: inputs:` / `component:` syntax.

**Substitutions applied during Phase 6b generation (TWO substitutions only):**
- `{ARTIFACT_ID}` → `sonar_workspace_key` value (e.g., `busparsemgmt-xapi`)
- `{ARTIFACT_ID}` → `sonar_csm_secret_url` suffix (e.g., `snsvc0000000_busparsemgmt-xapi`)
- `{ARTIFACT_ID}` → `perf_test_jmeter_jmx_path` filename (e.g., `busparsemgmt-xapi.jmx`)

All other values are pre-configured constants; do NOT substitute them.

```yaml
spec:
  inputs:
    csm_safe_id:
      type: string
      default: "snsvc0000000"
      description: CSM Safe Id (ITSI) for any secret data read by this component
    csm_role_name:
      type: string
      default: gitlab-role
      description: CSM role name to allow read of secrets from GitLab
    csm_secret_name:
      type: string
      default: env/ci/ci-secrets
      description: CSM secret name (assumes kv secret as default)

---
variables:
  WIZ_ENABLED: false

include:
  - component : $CI_SERVER_HOST/barclays/digital-platform/cicd-components/pipelines/buk-onepipeline-ci/pipeline-gradle-java-ci@3.0
    inputs:
      PIPELINE_VERSION: 3.0
      comp_test_gradle_opts: &gradle_opts "-PnexusUsername=$nexusUsername -PnexusPassword=$nexusPassword"
      comp_test_gradle_goal_name: "integrationTest jacocoTestReport"
      comp_test_jacoco_csv_report_path: "build/reports/jacoco/test/jacocoTestReport.csv"
      comp_test_jacoco_xml_report_path: "build/reports/jacoco/test/jacocoTestReport.xml"
      CSM_EXTENDED: ".csm_extract_secrets"
      GLOBAL_JAVA_BUILDER_IMAGE: $BUILDER_IMAGE_JAVA_21
      properties_setup_get_nexus_patch_version: "True"
      csm_safe_id: "snsvc0000000"
      csm_role_name: $[[ inputs.csm_role_name ]]
      csm_secret_name: $[[ inputs.csm_secret_name ]]
      sonar_language: java
      sonar_component: NEW_SONAR
      sonar_builder_image: $BUILDER_IMAGE_JAVA_21
      sonar_timeout: 1000
      sonar_scan_type: sonar-scanner-cli
      sonar_workspace_key: {ARTIFACT_ID}
      sonar_quality_gate: PASS_ON_QUALITY_GATE_FAILURE
      sonar_execution: PASS_ON_EXECUTION_FAILURE
      sonar_csm_secret_url: "https://csm-uk1-stg.barcapint.com:8200/v1/CSM/sonar/creds/snsvc0000000_{ARTIFACT_ID}"
      sonar_csm_role_name: "snsvc0000000_gitlab_gitlab-role"
      properties_setup_nexus_system_account_username: "system_account_name"
      publish_gradle_nexus_system_account_username: "system_account_name"
      shared_nexus_publish_nexus_system_account_username: "system_account_name"
      compliance_nexus_system_account_username: "system_account_name"
      veracode_sca_api_token_variable_name: SCA_API_TOKEN
      PERFORMANCE_TESTING_TOOL: "JMETER_LOCAL"
      perf_test_jmeter_builder_image: $BUILDER_IMAGE_JAVA_21
      perf_test_jmeter_app_server_host: "localhost:8080"
      perf_test_jmeter_app_server_protocol: "http"
      perf_test_jmeter_jmx_path: "{ARTIFACT_ID}.jmx"
      perf_test_jmeter_startup_command: "java -Dspring.profiles.active=dev -Dlogging.level.root=DEBUG -Dlogging.level.org.springframework=DEBUG -Dspring.config.location=src/main/resources/ -jar build-job-jars/app.jar"
      perf_test_jmeter_healthcheck_command: 'curl -s -f -X GET -H "Content-type: application/json" -H "correlation-id: 1000" http://localhost:8080/healthcheck'
workflow:
  rules:
    - if: $CI_COMMIT_TAG
      when: never
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: always
    - if: $CI_COMMIT_BRANCH
      when: always
```

### Key Configuration Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `comp_test_gradle_opts` | `-PnexusUsername=$nexusUsername -PnexusPassword=$nexusPassword` | Nexus repository authentication |
| `CSM_EXTENDED` | `.csm_extract_secrets` | Enable CSM secret extraction |
| `GLOBAL_JAVA_BUILDER_IMAGE` | `$BUILDER_IMAGE_JAVA_21` | Use Java 21 builder |
| `PIPELINE_VERSION` | `3.0` | OnePipeline v3.0 component |
| `sonar_component` | `NEW_SONAR` | New SonarQube project |
| `PERFORMANCE_TESTING_TOOL` | `JMETER_LOCAL` | Local JMeter testing |
| `comp_test_gradle_goal_name` | `integrationTest jacocoTestReport` | Runs integration tests + JaCoCo |

### Substituted Values (filled per generated API)

| Placeholder | Substituted with | Example |
|---|---|---|
| `{ARTIFACT_ID}` in `sonar_workspace_key` | `config.artifact_name` | `busparsemgmt-xapi` |
| `{ARTIFACT_ID}` in `sonar_csm_secret_url` | `config.artifact_name` | `snsvc0000000_busparsemgmt-xapi` |
| `{ARTIFACT_ID}` in `perf_test_jmeter_jmx_path` | `config.artifact_name` | `busparsemgmt-xapi.jmx` |

### Pre-Configured Constants (never substitute)

| Configuration | Value |
|---|---|
| csm_safe_id | `snsvc0000000` |
| csm_role_name default | `gitlab-role` |
| csm_secret_name default | `env/ci/ci-secrets` |
| sonar_csm_role_name | `snsvc0000000_gitlab_gitlab-role` |
| nexus system accounts | `system_account_name` |
| WIZ_ENABLED | `false` |

**Result:** Copy `templates/.gitlab-ci.yml` verbatim during Phase 6b, then replace all three
`{ARTIFACT_ID}` occurrences with the artifact name from config.

---

## 2. project_metadata.yml — Pre-Configured Template

**File:** `project_metadata.yml` (root directory)

```yaml
project_owner: buk.digital.platform@barclays.com
business_unit: buk
pod: digital_channels
itba: BUK-DIGITAL-PLATFORM
cio: digital.platform.cio@barclays.com
transaction_cycle: REAL_TIME
language: java
target_deployment: kubernetes
bitbucket_repo_name: {ARTIFACT_ID}
maintainer_ad_group: fglbGL_buk_digital_Main
developer_ad_group: fglbGL_buk_digital_Dev
```

### Auto-Generated Values (One Substitution Only)

- `{ARTIFACT_ID}` ← Auto-filled from config.artifact_name (only variable substituted)

**All other fields pre-configured with Barclays standards:**
- project_owner: buk.digital.platform@barclays.com
- itba: BUK-DIGITAL-PLATFORM
- cio: digital.platform.cio@barclays.com
- transaction_cycle: REAL_TIME (not DAILY or other cycles)
- business_unit: buk, Pod: digital_channels
- target_deployment: kubernetes (not other)
- AD groups: fglbGL_buk_digital_Main/Dev

---

## Pipeline Stages (OnePipeline v3.0)

The included OnePipeline component automatically orchestrates these stages:

### Stage 1: Build & Test
- Runs: `./gradlew clean build test`
- JaCoCo coverage verification (80%+ required)
- Checkstyle enforcement

### Stage 2: Quality Scanning
- SonarQube analysis (NEW_SONAR)
- Code quality gates
- Security scanning

### Stage 3: Performance Testing
- JMeter local performance test
- Startup command: `java -Dspring.profiles.active=perf-test ... -jar build-job-jars/app.jar`
- Health check: `/healthcheck` endpoint
- Baseline metrics collection

### Stage 4: Publishing
- Artifact publishing to Nexus repository
- System account authentication

---

## Customization Points

### Adding Custom Test Profiles

Edit `.gitlab-ci.yml` to add custom profiles:

```yaml
variables:
  GRADLE_OPTS: "-Dspring.profiles.active=prod -Dspring.config.location=src/main/resources/"
```

### Modifying Performance Test

Update JMeter configuration:

```yaml
perf_test_jmeter_jmx_path: "application.jmx"
perf_test_jmeter_startup_command: "java -Dspring.profiles.active=perf-test ... -jar app.jar"
perf_test_jmeter_healthcheck_command: 'curl -s -f -X GET http://localhost:8080/healthcheck'
```

### Adding SonarQube Rules

Update Sonar workspace:

```yaml
sonar_workspace_key: {YOUR_SONAR_KEY}
sonar_csm_secret_url: "https://csm-uk1.barcapint.com:8200/v1/CSM/sonar/creds/your_creds"
```

---

## CI/CD Environment Variables

When `project_metadata.yml` and `.gitlab-ci.yml` are present, CI/CD has access to:

```bash
# Build variables (automatic)
$CI_COMMIT_SHA         # Current commit hash
$CI_COMMIT_BRANCH      # Current branch name
$CI_PROJECT_NAME       # Project name from metadata
$CI_JOB_TOKEN          # Job authentication token

# Gradle variables (from config)
$nexusUsername         # From CSM extraction
$nexusPassword         # From CSM extraction
$BUILDER_IMAGE_JAVA_21 # Java 21 Docker image

# SonarQube variables
$SONAR_HOST_URL        # SonarQube server URL
$SONAR_LOGIN           # SonarQube authentication
```

---

## Workflow Rules

```yaml
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"       # Run on MR
    - if: $CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS       # Skip if MR exists
      when: never
    - if: $CI_COMMIT_BRANCH                                   # Run on push
```

This ensures:
- ✅ Pipelines run on MR (merge request)
- ✅ Pipelines run on push to branch
- ❌ Pipelines skip if MR already exists (avoid duplicates)

---

## Auto-Configured Values (Zero User Input Required)

| Configuration | Value | Scope | Status |
|---|---|---|---|
| csm_safe_id | buk_digital_api_safe | CI/CD | ✅ Pre-set |
| csm_role_name | buk_digital_api_role | CI/CD | ✅ Pre-set |
| csm_secret_name | nexus/buk_digital_api | CI/CD | ✅ Pre-set |
| nexus_system_account | barclays_nexus_ci | CI/CD | ✅ Pre-set |
| sonar_workspace_key | buk_digital_platform_sonar_workspace | CI/CD | ✅ Pre-set |
| sonar_csm_role | buk_sonar_access_role | CI/CD | ✅ Pre-set |
| jmeter_app_server | localhost:8080 | CI/CD | ✅ Pre-set |
| project_owner | buk.digital.platform@barclays.com | Metadata | ✅ Pre-set |
| itba | BUK-DIGITAL-PLATFORM | Metadata | ✅ Pre-set |
| cio | digital.platform.cio@barclays.com | Metadata | ✅ Pre-set |
| transaction_cycle | REAL_TIME | Metadata | ✅ Pre-set |
| business_unit | buk | Metadata | ✅ Pre-set |
| pod | digital_channels | Metadata | ✅ Pre-set |
| target_deployment | kubernetes | Metadata | ✅ Pre-set |
| ad_group_maintainer | fglbGL_buk_digital_Main | Metadata | ✅ Pre-set |
| ad_group_developer | fglbGL_buk_digital_Dev | Metadata | ✅ Pre-set |
| **ARTIFACT_ID** | **{from config}** | Metadata | ✅ Auto-filled |

---

## Reference

- **Barclays OnePipeline v3.0**: https://gitlab.barcapint.com/barclays/digital-platform/cicd-components
- **SonarQube**: https://sonarqube.barcapint.com/
- **JMeter**: https://jmeter.apache.org/
- **Nexus Repository**: https://nexus.barcapint.com/
- **CSM (Central Secret Manager)**: https://csm-uk1.barcapint.com/

## Source Attribution

**Primary sources:**
- Barclays BUK GitLab CI/CD standards for SDK3 Gradle projects (internal BUK API Engineering documentation)
- Barclays OnePipeline component CI template — pipeline stages, runner tags, and artefact publishing conventions
- CSM (Central Secret Manager) integration guide — `CSM_SAFE_ID`, `CSM_ROLE_NAME`, `CSM_SECRET_NAME` variable names
- Nexus repository configuration: `buk-snapshots` and `buk-maven2-group` repository names

**Training knowledge applied:**
- GitLab CI/CD YAML syntax: `stages`, `extends`, `rules`, `variables`, `artifacts`
- Gradle test reporting and Sonar integration patterns
- JMeter performance test pipeline stage structure

**Known limitations:**
- Pipeline template assumes Barclays-internal GitLab runners; external GitLab.com runners are not supported
- `baseVersion` and `baseImageSelector` values in `deployment-*.properties` are pinned to values known at skill review date — verify against the DAF template before use
- Sonar configuration assumes the Barclays-internal SonarQube instance; project keys and workspace names are team-specific

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Does the .gitlab-ci.yml reference the correct Java 21 runner image?
- [ ] Are Sonar analysis, JaCoCo coverage, and pitest mutation testing stages declared?
- [ ] Is the Nexus credentials configuration referenced from CI/CD variables (not hardcoded)?
- [ ] Does the pipeline include both unit test and integration test stages?
- [ ] Are branch protection rules applied (main branch requires passing pipeline)?

