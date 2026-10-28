---
name: aws-pipeline
description: >
    Diagnostic patterns for Harness CD pipelines that deploy to AWS via Service Catalog,
    CloudFormation, S3, Tyk, ECS/EKS, and Terraform. Covers non-prod and prod CR-driven flows.
    Applies to any BUK team using the shared AWS deploy pipeline pattern (cc-aws-release-registry).
    Load when PIPELINE_TYPE is aws.
user-invocable: false
owner: BUK DevOps
review-trigger: When pipeline stages change or new failure patterns are confirmed.
---

# AWS Pipeline — Diagnostic Patterns

> **Applies to:** Any Harness CD pipeline in BUK deploying to AWS (Service Catalog, CloudFormation,
> S3, Tyk API, ECS/EKS, Terraform). Driven by a manifest committed to `cc-aws-release-registry`.
> Non-prod: `aws-deploy-pipeline`. Prod: CR-driven via shared Release Creation pipeline.

---

## Pipeline Stage Layout

```
1. Prepare                   — clones cc-aws-release-registry; sets up execution environment
2. Validate Release Manifest — parses manifest JSON; checks step types, required attributes, config files
3. Generate Dynamic Plan     — builds dynamic Harness pipeline YAML (one stage per manifest step)
4. Deploy                    — executes each step in sequence via cct-task-library tasks
```

Pipeline inputs: `TARGET_DEPLOY_ENVIRONMENT` (required), `RELEASE_MANIFEST_FILE` (required),
`PHASE` (implementation/backout), `STEPS_TO_RUN` (ALL or `1,2,3`), `registry_branch` (default: master).

---

## Stage 2: Validate Release Manifest

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `Manifest JSON invalid` | Syntax error in manifest file | App team — validate JSON before commit |
| `Step type not supported` | `stepType` value not in the supported list | App team — check Step Types reference; raise via DevOps Support for new types |
| `Config file not found` | Product config missing at `configs/scProducts/{productName}/{productName}-{configVersion}.json` | App team — folder AND file must exactly match `provisionedProductName` |
| `Pipeline cannot find manifest` | Wrong path or wrong branch | App team — manifest must be on master (or `registry_branch`); path is relative to repo root |
| `Required attribute missing` | Mandatory field absent from a step's `stepAttributes` | App team — check Step Types reference for required fields |
| `EVIDENCE_VALIDATION_FAILED` | Testing evidence not found in S3 for a manifest step (prod CR creation) | Ensure non-prod pipeline ran to completion and uploaded evidence |

---

## Stage 4: Deploy — Common Failures by Step Type

### CreateAndProvisionProduct / Service Catalog

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `product version not available after creation` | Lambda propagation delay (artifact present but not yet visible) OR Nexus artifact not published | App team — **first** verify the artifact exists in Nexus for the target version; if missing, CI must publish before re-running; if present, re-run with `STEPS_TO_RUN=<n>` to retry propagation |
| `ROLLBACK_COMPLETE` / `ROLLBACK_IN_PROGRESS` | CloudFormation stack failed — check Events tab in AWS console for the specific resource | Depends: platform team (IAM/VPC) or app team (app config) |
| `AccessDenied` on stack resource | IAM automation role missing permissions | App team / AWS platform — update automation role policy (`AutomationPolicyCommon`) |
| `already exists` | Resource exists and CF cannot adopt it | Platform team — import or manually delete conflicting resource |
| `No updates are to be performed` | Stack identical to deployed state | Not an error — likely intentional re-run; confirm with app team |

### Auth / Credentials

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `Unable to locate role` / `Auth fails` | `TARGET_DEPLOY_ENVIRONMENT` wrong or account/role mismatch | App team — check env dropdown maps to the correct AWS account |
| STS token expired mid-run | AWS STS tokens expire after ~1 hour; long manifests with many steps | App team — set `REAUTH_PER_STEP=true` in pipeline variables |
| `CSM role not found` | CSM BCP role for Harness delegate not created for this account | App team — add one BCP role to CSM safe (part of account onboarding) |

### Tyk API Steps

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `TykOnboard` skipped — API already exists | API with same name already registered; step is idempotent | Not an error — use `TykUpdate` to modify |
| `TykUpdate` fails | `apiName` not found and `apiId` not provided | App team — provide `apiId` explicitly or verify API name spelling |
| `TykCertUpload` fails | CSM PKI role or URL wrong | App team — verify `csmRoleCertificate` and `csmCertificateIssueUrl` |

### DeployUIComponent

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| HTML downloading instead of rendering | Old pipeline version — S3 Content-Type bug | App team — ensure `lib_repo_branch=main` in pipeline variables |
| Artifact not found | npm package not published to Nexus for specified version | App team — verify CI published the package |

### Terraform Steps

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `terraform init` fails | Artifact not in Nexus or wrong version | App team — verify Nexus artifact for `productVersion` |
| `terraform apply` fails | Resource or permission error | App team / AWS platform — check `terraform plan` output in logs |

---

## AWS Account Not Onboarded

If the pipeline cannot find the target environment or role:
1. Check `aws_environments.json` in `cc-aws-release-registry` — is the account listed?
2. If not: raise in Virtual Channels – DevOps Support; 5-step onboarding required (DevOps + app team)
3. App team owns: CSM BCP role creation, automation IAM role, system account, Service Portfolio permissions

---

## Delegates

AWS pipelines use BCP2-hosted delegates (the same delegate pool as BCP2 OpenShift pipelines). If a delegate is offline, escalate to the BCP2 platform team. The CSM BCP role for the delegate must be created per AWS account as part of account onboarding ("Add one BCP role to CSM safe for the Harness delegate").

---

## Re-running Failed Steps

Set `STEPS_TO_RUN=<n>` (e.g. `3`) to re-run only the failed step — no need to repeat passed steps.
For long manifests (>1 hour total runtime), set `REAUTH_PER_STEP=true` to avoid STS token expiry.

---

## Release Creation Pipeline (prod CR)

The Release Creation pipeline embeds a **GitLab commit permalink** (40-char SHA URL) as `MANIFEST_LINK` in the CR description. The prod deploy pipeline fetches `releaseManifest.txt` from that GitLab URL.
Common failures: `EVIDENCE_VALIDATION_FAILED`, branch-based manifest URL, missing `READY_FOR_CR` label.
CR template for AWS EPS: `NCTMP0014983`.

---

## Key Contacts & Escalation

| Issue area | Contact |
|------------|---------|
| Manifest / config file errors | App team |
| CloudFormation / IAM resource failures | App team + AWS platform team |
| Tyk API errors | App team |
| AWS account not onboarded | Virtual Channels – DevOps Support |
| Delegate offline | BCP2 platform team |
| New step type request | Raise via Jira MCADOSR or DevOps Support |
| Pipeline / cct-task-library bug | BUK DevOps Platform |

---

## Enriching this skill for your team

Add your team-specific values (account IDs, LCT IDs, manifest paths, Tyk API names)
as a new section at the bottom. Reference this skill from `cd-diagnose-agent` by adding one line
to its `skills:` frontmatter.
