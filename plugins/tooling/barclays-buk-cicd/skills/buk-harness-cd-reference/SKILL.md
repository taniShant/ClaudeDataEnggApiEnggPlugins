---
name: buk-harness-cd-reference
description: >
    Domain reference for Harness CD pipeline concepts, object model, failure categories, and
    diagnostic patterns. Load when diagnosing Harness CD execution failures. Covers delegates,
    connectors, pipeline/stage/step structure, secrets, variables, approval flows, OPA policies,
    and common failure patterns with recommended next steps.
user-invocable: false
---

# BUK Harness CD Reference

> **Scope:** General Harness CD (Next-Gen / NG platform) — applies to any pipeline regardless of deployment type or application stack.
> **Owner:** BUK DevOps Team (sourabh.agrawal1@barclays.com)
> **Review trigger:** On Harness platform major version change, or when new failure patterns are confirmed in production.

---

## Quick Start

Load this skill when the agent receives a Harness execution URL to diagnose. It provides:

1. **Object model** — understand what each Harness entity is and where to find it (section 1)
2. **API access pattern** — how to fetch execution data at Barclays (section 2)
3. **Failure pattern catalogue** — match log error text to known failure categories (sections 3–9)
4. **Escalation paths** — who owns each failure category (section 10)

**When to load:** Immediately after receiving EXECUTION_URL — before fetching any API data.

---

## 1. Harness Object Model

Understanding the hierarchy is essential for attributing failures to the correct layer.

```
Account
└── Organisation (org)
    └── Project
        └── Pipeline
            └── Stage (sequential or parallel)
                └── Step Group (optional grouping)
                    └── Step (atomic unit of work)
```

### Key entities

| Entity | What it is | Where to find it |
|--------|------------|------------------|
| **Pipeline** | Orchestrates the full deployment flow | Project → Deployments → Pipelines |
| **Stage** | A logical phase (e.g. Deploy, Approval, Custom) | Inside a pipeline |
| **Stage Template** | Reusable stage definition stored in Harness | Account/Org/Project → Templates |
| **Step** | Atomic action within a stage (Shell Script, HTTP, Kubernetes Apply, etc.) | Inside a stage |
| **Delegate** | Agent running in the target infrastructure that executes steps | Account/Org → Delegates |
| **Connector** | Authenticated connection to an external system (GitLab, Kubernetes, AWS, Nexus) | Account/Org/Project → Connectors |
| **Secret** | Credential or sensitive value stored in Harness (or fetched from CSM/Vault) | Account/Org/Project → Secrets |
| **Service** | The application being deployed (manifest, artifact, config) | Project → Services |
| **Environment** | Target deployment environment (non-prod, prod) with infrastructure definition | Project → Environments |
| **Infrastructure Definition** | Target cluster/account/namespace within an environment | Inside an Environment |
| **Input Set** | Pre-defined input values for a pipeline run | Project → Pipelines → Input Sets |
| **Trigger** | Automated pipeline invocation (webhook, scheduled, artifact) | Project → Pipelines → Triggers |
| **OPA Policy** | Governance policy evaluated at pipeline or stage level | Account → Governance → Policies |

---

## 2. Harness CLI and API Access at Barclays

### Instances

| Instance | URL | Profile | Token env var |
|----------|-----|---------|---------------|
| Prod | `https://barclays.harness.io` | `prod` | `HARNESS_API_TOKEN_PROD` |
| Non-prod | `https://barclays-nonprod.harness.io` | `nonprod` | `HARNESS_API_TOKEN_NONPROD` |

> **Note:** Non-prod (Harness UAT) is only used by DevOps/Platform teams for pipeline development. End users run all pipelines in the Prod Harness instance.

### Preferred method: Harness CLI

Binary: `/c/harness-cli/harness.exe` (on PATH). Handles auth and proxy natively.

```bash
# Execution summary (full raw JSON)
harness get execution <planExecutionId> --profile prod --json --raw

# All steps with status, log_key, fqn
harness list execution_step <planExecutionId> --profile prod --json --all

# Log key index (includes per-step status)
harness list execution_log <planExecutionId> --profile prod --json --all
```

**Known CLI limitations:**
- `harness get execution_log --logkey <key>` — fails through Zscaler proxy (blob download via `/gateway/log-service/blob`). Use Python urllib fallback for log content.
- `list/get pipeline`, `list template` — return 500 on this account (v1 endpoint broken).

### Parsing the execution URL

Given: `https://barclays.harness.io/ng/account/<account>/all/orgs/<org>/projects/<project>/deployments/<planExecutionId>/pipeline`

Extract:
- `planExecutionId` = segment after `/deployments/`
- `profile` = `prod` if hostname is `barclays.harness.io`, else `nonprod`

### Fallback: Python urllib for log blob downloads

`curl` does not route through Zscaler reliably. Use Python urllib only for log blob fetches when the CLI cannot complete them:

```python
import subprocess, urllib.request, urllib.parse

proxy = subprocess.run(["bash", "-lc", "echo $http_proxy"], capture_output=True, text=True).stdout.strip()
opener = urllib.request.build_opener(urllib.request.ProxyHandler({"https": proxy, "http": proxy}))

url = f"https://barclays.harness.io/gateway/log-service/blob?accountID={account}&key={urllib.parse.quote(log_key)}"
req = urllib.request.Request(url, headers={"x-api-key": token})
with opener.open(req, timeout=30) as resp:
    data = resp.read()
```

Detect Python at runtime — DevHome path on BUK Windows, `python3` on macOS/Linux:

```bash
if [ -f "/c/devhome/tools/python3.12/current/python" ]; then
  PYTHON_BIN="/c/devhome/tools/python3.12/current/python"
else
  PYTHON_BIN="python3"
fi
```

---

## 3. Delegate Failures

Delegates are Kubernetes-based agents that execute Harness steps on behalf of the pipeline. They are deployed via Helm and run as pods inside a Kubernetes cluster. Delegate failures are infrastructure/platform failures — the deployment configuration is not the cause.

### Delegate infrastructure at Barclays

All Harness delegates at Barclays are Kubernetes-based, deployed and managed via Helm:

| Hosting platform | Description | Fix owner |
|-----------------|-------------|-----------|
| **BCP2 (OpenShift)** | The majority of delegates run on BCP2 — Barclays internal OpenShift-based Kubernetes clusters | BCP2 / platform team managing that delegate namespace |
| **AWS EKS** | A small number of teams run delegates on their own EKS clusters | The team owning that EKS cluster |

When a delegate failure occurs, the first diagnostic question is: **which platform hosts the delegate for this pipeline's environment?** The escalation path differs.

### Failure signals

| Signal | Meaning |
|--------|---------|
| `Delegate not available` | No delegate matched the selector or all matched delegates are unhealthy |
| `No eligible delegates found` | Delegate selector specified in the step has no live delegates matching |
| `Delegate selector not matched` | The step/connector specifies a selector tag that no online delegate has |
| `Delegate timed out` | A delegate picked up the task but did not complete it within the timeout |
| `Delegate heartbeat missed` | Delegate pod stopped sending heartbeats — likely crashed or evicted |
| `Unable to find any matching delegate` | Variant of no eligible delegates |

### Diagnosis steps

1. Identify the delegate selector on the failing step or connector
2. Go to Account/Org → Delegates in the Harness UI — are delegates with that selector tag online?
3. If **no delegates online**:
   - Determine whether the delegate runs on BCP2 or EKS (check the delegate name/tag or ask the team)
   - **BCP2 delegate:** check the Helm release health in the BCP2 namespace — pod may be evicted, OOMKilled, or the Helm release may need a rollback; escalate to the BCP2 platform team
   - **EKS delegate:** check the EKS cluster and Helm release for the delegate — escalate to the team owning that EKS cluster
4. If **delegates are online but not matching**: check the selector tag spelling on both the step/connector and the delegate profile — a typo or missing tag is the most common cause
5. If **delegate timed out**: the pod is alive but the task exceeded the timeout — check whether the delegate pod has sufficient CPU/memory resources (Helm values) and whether the target system was reachable

### Fix owner

- BCP2-hosted delegate → BCP2 / OpenShift platform team
- EKS-hosted delegate → team owning that EKS cluster
- Selector mismatch → DevOps team owning the pipeline (config fix)

---

## 4. Connector Failures

Connectors authenticate Harness to external systems. When a connector fails, steps that depend on it cannot fetch code, push artifacts, or talk to clusters.

### Connector types and their common failures

| Connector type | Common failure | Signal |
|----------------|----------------|--------|
| **GitLab / GitHub** | Invalid token or expired PAT | `Invalid credentials`, `401 Unauthorized`, `Repository not found` |
| **Kubernetes** | Expired kubeconfig, wrong cluster URL | `Unable to connect to cluster`, `connection refused`, `certificate signed by unknown authority` |
| **AWS** | Expired IAM role assumption, wrong ARN | `Unable to assume role`, `ExpiredTokenException`, `AccessDenied` |
| **Nexus / Artifactory** | Wrong credentials from CSM | `401 Unauthorized`, `403 Forbidden` on artifact fetch |
| **HTTP / Custom** | Connectivity or TLS | `connection refused`, `TLS handshake timeout` |
| **Harness Secret Manager** | CSM/Vault unreachable | `Unable to connect to secret manager`, `Vault token expired` |

### Diagnosis steps

1. Identify the connector name from the error message or the failing step configuration
2. Go to the connector in Harness UI → Test connection — does it pass?
3. If it fails: check the secret referenced by the connector — is the org/account variable or CSM path correct?
4. If the secret is correct but the test still fails: check network connectivity from the delegate to the target system

### Fix owner

DevOps (connector config or secret update) or Platform team (network/TLS issue).

---

## 5. Secret and Variable Failures

### Harness secret resolution

Harness resolves secrets from:
- **Harness built-in secret manager** — stored directly in Harness
- **CSM / Vault** — fetched at runtime via a secret manager connector
- **Org/account variables** — pipeline variables defined at org or account scope

### Failure signals

| Signal | Meaning |
|--------|---------|
| `Secret not found` | Secret identifier does not exist in the referenced scope (account/org/project) |
| `Invalid secret reference` | Secret expression is malformed (e.g. `<+secrets.getValue("name")>`) |
| `null` value in step input | Variable referenced in step inputs was not passed — check pipeline inputs and templateInputs |
| `Expression evaluation failed` | A Harness expression (`<+...>`) failed to resolve — variable missing or wrong scope |
| `Variable not resolved` | Pipeline variable used in a step was never set |
| `403 Forbidden` on CSM | CSM/Vault role does not have read permission for the secret path |

### Diagnosis steps

1. Identify the exact expression or variable name that failed to resolve from the error message
2. Check whether the variable is defined at the correct scope (step → stage → pipeline → project → org → account)
3. For pipeline execution inputs: check the Input Set or manual trigger inputs — was the variable provided?
4. For CSM secrets: verify the org variable path and CSM safe/role name — test the CSM connector

### Fix owner

DevOps (variable or secret configuration).

---

## 6. Template and Pipeline Configuration Errors

These failures occur before or during execution and indicate a misconfiguration in the pipeline YAML, stage template, or input set.

### Failure signals

| Signal | Meaning |
|--------|---------|
| `Invalid YAML` | Pipeline or template YAML does not parse |
| `Template not found` | A stage or step references a template that does not exist at the specified version |
| `Input set validation failed` | An Input Set provides values that do not match the pipeline's runtime input schema |
| `Required input missing` | A runtime input (`<+input>`) was not supplied at execution time |
| `Reconciliation required` | Template has been updated but the pipeline referencing it has not been reconciled |
| `gitBranch expression not supported` | `gitBranch` in a pipeline YAML uses an expression instead of a literal — must be a literal branch name |
| `Stage identifier conflict` | Two stages in a parallel group share the same identifier |

### Diagnosis steps

1. If `Template not found`: check the template name and version label in the stage configuration — does that version exist in Harness?
2. If `Input set validation failed`: open the Input Set in Harness UI and re-validate — the schema may have changed after a template update
3. If `Required input missing`: check the trigger or manual run inputs — the pipeline expects a value that was not supplied
4. If `Reconciliation required`: reconcile the pipeline via the Harness UI (Pipeline Studio → Reconcile) or via the API

### Fix owner

DevOps (pipeline/template config). Application team if the error is in their pipeline YAML.

---

## 7. Infrastructure Deployment Failures

These failures occur during the actual deployment step — Kubernetes apply, Helm upgrade, CloudFormation deploy, etc.

### Kubernetes / Helm

| Signal | Meaning |
|--------|---------|
| `CrashLoopBackOff` | Application pod keeps crashing after start |
| `OOMKilled` | Pod killed due to memory limit exceeded |
| `ImagePullBackOff` / `ErrImagePull` | Container image cannot be pulled (Nexus auth or image not found) |
| `Readiness probe failed` | Application did not become ready within the timeout |
| `Deployment timed out` | Kubernetes rollout did not complete within Harness wait timeout |
| `resource already exists` (Helm) | Helm release in a conflicting state — may need `helm rollback` or manual cleanup |
| `forbidden: unable to create resource` | RBAC — Harness service account lacks permission in the namespace |

### AWS CloudFormation

| Signal | Meaning |
|--------|---------|
| `ROLLBACK_COMPLETE` | Stack failed to create/update and rolled back — check stack events in AWS console |
| `ROLLBACK_IN_PROGRESS` | Stack update in progress rolling back |
| `No updates are to be performed` | CloudFormation detected no diff — pipeline may have deployed an identical stack |
| `AccessDenied` | IAM role used by the deployment lacks permissions for the resource being created |
| `Resource handler returned message` | CloudFormation resource provider error — check the specific resource type and error |
| `already exists` | Resource exists and CloudFormation cannot adopt it (needs import or manual delete) |

### OpenShift / BCP2

| Signal | Meaning |
|--------|---------|
| `oc: command not found` | Wrong delegate or missing oc CLI in delegate |
| `Unauthorized` | OpenShift token expired or wrong service account |
| `project not found` | Namespace/project does not exist in the cluster |
| `ImageStream not found` | Image not promoted to the target namespace |

### Diagnosis steps

1. For Kubernetes: check pod events (`kubectl describe pod`) in the target namespace — the Harness log often truncates the full event stream
2. For CloudFormation: open the AWS CloudFormation console for the stack — the Events tab shows the exact resource and error
3. For health check / readiness failures: the application is deploying but not starting — escalate to the application team with the pod logs
4. For auth/RBAC: check the service account and role binding in the cluster

### Fix owner

- Image pull / readiness / crash → Application team
- IAM / RBAC / cluster resource → Platform/infra team
- CloudFormation resource-level error → depends on resource type; involve platform team

---

## 8. Approval and Policy Failures

### Approval step failures

| Signal | Meaning |
|--------|---------|
| `Approval rejected` | An approver explicitly rejected the deployment |
| `Approval timed out` | No approver acted within the configured timeout |
| `No approvers available` | User group referenced in the approval step has no members |

### OPA / Governance failures

| Signal | Meaning |
|--------|---------|
| `OPA policy failed` | A Harness OPA policy evaluated the pipeline and returned a deny decision |
| `Policy set evaluation failed` | Pipeline did not pass a required governance gate |
| `Freeze window active` | A deployment freeze is in effect — pipeline blocked by governance |

### Diagnosis steps

1. For approval timeout: check who was in the approval user group — did they receive the notification?
2. For OPA failure: the error message usually contains the policy name and the rule that failed — check that policy in Account → Governance
3. For freeze window: check Account → Governance → Freeze Windows — when does the freeze end?

### Fix owner

Governance team (policy/freeze) or the designated approver (approval).

---

## 9. Execution Status Reference

| Status | Meaning |
|--------|---------|
| `FAILED` | At least one stage/step failed and the pipeline stopped |
| `ABORTED` | A user manually aborted the execution |
| `EXPIRED` | The execution exceeded its configured timeout |
| `SUCCESS` | All stages passed |
| `RUNNING` | Still in progress |
| `PAUSED` | Waiting at an approval or barrier step |
| `WAITING` | Waiting for an input or approval |
| `SKIPPED` | Stage/step was skipped by a conditional expression |
| `IGNORE_FAILED` | Step failed but pipeline continued (`failureStrategies: ignore`) |

When status is `ABORTED`, check whether the abort was intentional (user action) or triggered by a timeout or policy. The execution log will show who aborted and when.

---

## 10. Escalation Paths

| Failure category | First contact | Escalation |
|-----------------|---------------|------------|
| Delegate offline / pool issue | Team managing the delegate infrastructure for that environment | BUK DevOps Platform team |
| Connector misconfiguration | DevOps team owning the pipeline | BUK DevOps Platform team if connector is shared |
| Secret / CSM / Vault | DevOps team owning the secret path | Security/CSM team if safe/role is wrong |
| Kubernetes RBAC | Cluster platform team | |
| CloudFormation IAM | AWS platform team | |
| OCP / BCP2 cluster | BCP2 platform team | |
| Application crash / health check | Application team | |
| OPA policy / freeze | Governance team | |
| Template / pipeline config | DevOps team owning the pipeline | |
| Harness platform bug | BUK DevOps Platform team | Raise Harness support ticket |

---

## 11. Agent Self-Check

When applying this skill, confirm:

- [ ] Execution URL has been parsed for account, org, project, and planExecutionId
- [ ] Correct Harness instance (prod vs nonprod) identified and correct token var checked
- [ ] API token check performed before any API call — user prompted if missing
- [ ] Execution steps fetched (harness_steps.json) and first failed step identified by fqn order
- [ ] Log fetched for the root cause step (not just the cascade)
- [ ] Failure classified using the category table in the agent (section 4)
- [ ] Fix owner assigned based on category
- [ ] Cascade stages distinguished from root cause
- [ ] Report does NOT include any token, secret value, or credential
- [ ] Report does NOT recommend modifying, rerunning, or aborting the pipeline
