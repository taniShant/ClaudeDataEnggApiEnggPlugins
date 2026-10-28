# barclays-buk-cicd

CI/CD pipeline diagnostics and Harness inventory queries for BUK engineering teams.

## Agents

### `ci-diagnose-agent`

Diagnoses GitLab BUK One Pipeline CI failures for Java (Gradle/Maven), JavaScript, Go, and Python — identifies the failed job, extracts log evidence, maps it to a known pipeline component, and recommends next steps.

### `cd-diagnose-agent`

Diagnoses Harness CD pipeline execution failures — fetches the full execution tree and step logs via the Harness CLI, classifies the root cause (delegate, connector, authentication, infrastructure, template/config, application, approval/policy), and recommends next steps with an escalation path.

The agent loads a pipeline-specific pattern skill when the pipeline type is recognised, giving richer stage-level diagnostics, org variable checklists, and precise escalation contacts for that pipeline family. Area leads can contribute enrichment by adding a skill file under `skills/pipeline-patterns/` and one line to the agent frontmatter.

### `harness-insights-agent`

Answers free-text inventory and analytics questions about Harness — org/project structure, execution counts and status breakdowns by time window, delegate health, connector inventory, and prod vs nonprod comparisons.

**Read-only** — no agent modifies source code, pipeline configuration, or triggers pipeline actions.

## Install

```bash
/plugin install barclays-buk-cicd@barclays-cio-buk
```

## CI Diagnosis — Usage

Invoke with the failed GitLab pipeline URL and technology stack:

```
PIPELINE_URL:  https://app.gitlab.barcapint.com/my-group/my-service/-/pipelines/12345
TECH_STACK:    java-gradle
OUTPUT_PATH:   /workspace/ci-diagnosis.md
```

Or provide log content directly:

```
PIPELINE_URL:  none
JOB_NAME:      unit-test
TECH_STACK:    golang
LOG_CONTENT:   /path/to/pasted-log.txt
OUTPUT_PATH:   console
```

### Supported CI stacks

| Stack | Template | Notes |
|-------|----------|-------|
| `java-gradle` | `pipeline-gradle-java-ci.yml` | Full component coverage incl. MCA wrappers |
| `java-maven` | `pipeline-maven-java-ci.yml` | Build, test, sonar, publish |
| `javascript` | `pipeline-node-javascript-ci.yml` | Node/npm incl. MCA JS wrappers |
| `golang` | `pipeline-task-golang-ci.yml` | Taskfile-based; AWSCCEU wrapper; ABC TLS pattern |
| `python` | `pipeline-uv-python-ci.yml` | UV-based; AWSCCEU wrapper; ruff, mypy, bandit, pytest |

## CD Diagnosis — Usage

```bash
/barclays-buk-cicd:cd-diagnose EXECUTION_URL [OUTPUT_PATH]
```

Examples:
```bash
/barclays-buk-cicd:cd-diagnose https://barclays.harness.io/ng/account/.../deployments/eUme.../pipeline
/barclays-buk-cicd:cd-diagnose https://barclays.harness.io/ng/account/.../deployments/eUme.../pipeline /workspace/my-report.md
```

The command parses the URL, runs `harness_diagnose.py` (uses the Harness CLI), and delegates analysis to `cd-diagnose-agent`. The Harness CLI profile (`prod`/`nonprod`) is derived from the URL hostname automatically.

For log content downloads (best-effort), `HARNESS_API_TOKEN_PROD` or `HARNESS_API_TOKEN_NONPROD` must be set in shell. The script warns if missing but continues — execution summary and step list are fetched via CLI regardless.

### Covered failure categories

| Category | Examples |
|----------|---------|
| Delegate | No eligible delegates, selector mismatch, delegate offline |
| Connector | Invalid credentials, connection refused, certificate error |
| Authentication / secret | Secret not found, expression failed, CSM 403 |
| Infrastructure | CloudFormation rollback, Kubernetes crash, OCP auth failure |
| Template / config | Template not found, reconciliation required, missing input |
| Application | CrashLoopBackOff, OOMKilled, readiness probe failed |
| Approval / policy | OPA policy deny, freeze window active, approval timeout |

## Harness Query — Usage

```bash
/barclays-buk-cicd:harness-insights QUESTION [--nonprod]
```

Examples:
```bash
/barclays-buk-cicd:harness-insights how many pipelines failed in the last 24 hours
/barclays-buk-cicd:harness-insights what orgs and projects exist
/barclays-buk-cicd:harness-insights compare prod and nonprod projects
/barclays-buk-cicd:harness-insights how many delegates are connected --nonprod
```

Defaults to prod. Pass `--nonprod` to target the nonprod instance. For comparison questions mentioning both instances, data is fetched from both automatically.

### Covered query types

| Query type | Examples |
|------------|---------|
| Org structure | "what orgs exist", "list all organisations" |
| Project inventory | "what projects are in MCA org", "how many projects" |
| Execution counts | "how many pipelines ran today", "failed executions last 7 days" |
| Status breakdown | "success vs failure rate last 24 hours" |
| Delegate health | "how many delegates are connected" |
| Cross-instance comparison | "compare prod and nonprod projects" |

## Output

All agents write a structured markdown report with:

- Stage/job summary (root cause vs cascade vs skipped)
- Exact failure evidence quoted from logs
- Likely root cause with classification
- Recommended next steps (ordered, specific)
- Escalation path
- Flags — anything uncertain or missing

## Limitations

- CI agent requires `glab` CLI authenticated in your session
- CD agent: Harness CLI (`harness`) is used if available; falls back to direct API automatically. Set `HARNESS_API_TOKEN` (universal) or `HARNESS_API_TOKEN_PROD` / `HARNESS_API_TOKEN_NONPROD` (profile-specific) in your shell. The script prints step-by-step setup instructions if neither is configured.
- CD log content (best-effort): requires an API token as above; execution summary and step list are fetched via CLI or API regardless
- Harness log retention is ~7 days — logs for older executions will be absent
- `harness list pipeline` returns 500 on this account (v1 endpoint broken) — query agent uses execution data for pipeline-level analysis instead
- Execution fetch is capped at 200 per project — counts for very active projects may be understated
- Log redaction: do not paste logs containing credentials, tokens, or PII
- Does not access Jira, Confluence, or external monitoring systems
- Does not modify pipelines, trigger executions, or take remediation actions

## Jira

- CI diagnose: MCADOSR-15084
- CD diagnose: MCADOSR-15085
