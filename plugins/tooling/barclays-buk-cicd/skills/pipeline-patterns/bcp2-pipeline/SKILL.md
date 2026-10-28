---
name: bcp2-pipeline
description: >
    Diagnostic patterns for Harness CD pipelines that deploy to BCP2 (OpenShift) clusters.
    Covers both non-prod (ephemeral testbed) and prod (CR-driven) deployment flows.
    Applies to any Customer Care / BUK team using the shared BCP2 deploy pipeline pattern.
    Load when PIPELINE_TYPE is bcp2.
user-invocable: false
owner: BUK DevOps
review-trigger: When pipeline stages change or new failure patterns are confirmed in prod or non-prod.
---

# BCP2 Pipeline — Diagnostic Patterns

> **Applies to:** Any Harness CD pipeline deploying to BCP2 (OpenShift) clusters in BUK.
> The shared pipeline pattern is used by Customer Care, MCA, and other BUK areas.
> MCA-specific values (org `MCA`, project `MCA_NonProd`/`MCA_Prod`) are shown as examples.

---

## Non-Prod Pipeline Stage Layout

```
1. Config Validation         — validates env-config.json + app-dependencies.json from the config repo
2. Generate Deploy Plan      — builds a dynamic child pipeline from app-dependencies.json
3. Deploy EPS / UI           — deploys app to an ephemeral BCP2 namespace per testbed (TBG/TB5/TBP)
4. Test Execution            — clones app repo at deployed tag, runs src/test/app_validation.py in a K8s Job
5. Upload Evidence to S3     — uploads everything written to REPORTS_DIR
6. Validate Business Metrics — checks Observe logs for business endpoint coverage (not just health checks)
```

Stage 4 is `continueOnFailure: true` — subsequent stages still run on test failure.

## Prod Pipeline Stage Layout

```
1. CR Validation        — validates CR exists in ServiceFirst, is Approved, and deployment window is valid
2. Retrieve CR Manifest — fetches releaseManifest.txt from the GitLab commit permalink in the CR description
3. Generate Deploy Plan — builds and executes dynamic child pipeline from manifest deployment steps
```

---

## Stage 1 (Non-Prod): Config Validation

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `No Space Left on Device` | Harness shared workspace full | DevOps — raise with support to clear workspace |
| `env-config.json not found` | File not committed to `pipeline-config/` on master branch of config repo | App team |
| `app-dependencies.json not found` | Same as above | App team |
| Invalid JSON in either config file | Syntax error in team-managed config file | App team — validate JSON before commit |
| `cre-*` regression key missing or renamed | Protected pipeline-managed key removed or repurposed | App team — restore original key; do not rename `cre-*` keys |
| Wrong testbed in `test_bed` array | Environments only created for listed testbeds | App team — check `TBG`, `TB5`, `TBP` spelling |

## Stage 1 (Prod): CR Validation

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `CR not found` / `Change record not found` | CR number wrong or not yet created | Requestor |
| `CR state is not Approved` / `not Implement` | CR not yet approved by CAB | Change manager / CAB |
| `Deployment window not valid` | Current time is outside the CR's deployment window | Requestor — update CR window in ServiceFirst |
| `MANIFEST_LINK not found in CR description` | Release Creation pipeline did not run, or link was manually removed | App team — re-run Release Creation pipeline or paste the commit permalink manually |
| `CI not present in CIsBeingChanged` | A namespace CI is not listed in the CR | App team — update `cisBeingChanged` in manifest `releaseMetadata` |
| `sf_prod_username / sf_prod_password not set` | Missing org vars for ServiceFirst prod credentials | DevOps — provision org vars |

---

## Stage 2 (Non-Prod): Generate Deploy Plan

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `APPLICATION_CONFIG_REPO_PATH incorrect` | Full GitLab URL pasted instead of `barclays/...` path | App team — provide path only, not URL |
| `Config repo not found` | Config repo path wrong or app not onboarded | App team — check repo naming convention |
| `applicationConfigRepoPath` auto-resolve fails | Non-MCA app; path not auto-resolvable | App team — explicitly set `applicationConfigRepoPath` in manifest |
| `oc_nonprod_* org var not set` | Missing OpenShift non-prod credentials | DevOps — provision `oc_nonprod_server` / `oc_nonprod_token` |
| Infrastructure definition not found | `bcp2_infra_nonprod` missing in Harness | DevOps — re-import from git (`mca/nonprod/infraDefinitions/`) |

## Stage 2 (Prod): Retrieve CR Manifest

`MANIFEST_LINK` is a **GitLab commit permalink** (40-char SHA URL) embedded in the CR description by the Release Creation pipeline. This stage fetches `releaseManifest.txt` from that GitLab URL — not from S3.

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `MANIFEST_LINK not found in CR description` | Release Creation pipeline did not run, or link was manually removed | App team — re-run Release Creation pipeline or paste the commit permalink manually |
| `Manifest URL is branch-based` | URL contains `/blob/master/` instead of a 40-char SHA permalink | App team — use the GitLab commit permalink (click the commit SHA, copy the URL) |
| `404 / repository not found` | Config repo path wrong or access token missing | DevOps — verify `gitlab_access_token` org var and repo path |

---

## Stage 3 (Non-Prod): Deploy EPS / UI

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `ImagePullBackOff` | EPS/UI artifact not published to Nexus for the specified version | App team — verify CI pipeline pushed the artifact |
| `CrashLoopBackOff` / `OOMKilled` | Application fails to start | App team |
| `Readiness probe failed` | App not healthy within timeout | App team |
| `secrets is forbidden: User sysmcabbrw cannot list resource secrets` | Service account lacks RBAC in target namespace | DevOps — fix RBAC config for the namespace |
| `project not found` (OCP) | Namespace not onboarded or wrong cluster | App team — run `bcp-namespace-manager` pipeline; do not onboard via Skylight |
| `Unauthorized` (OCP) | OpenShift token expired | DevOps — rotate `oc_nonprod_token` org var |
| Deployed but app unreachable in test environment | `ui_static` or `menu_entry` missing/wrong in `app-dependencies.json` | App team — check existing `container.properties` in NR env for correct values |

## Stage 3 (Prod): Generate Deploy Plan

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `oc_prod_* org var not set` | Missing prod OpenShift credentials | DevOps — provision `oc_prod_server` / `oc_prod_token` |
| `bcp2_infra_prod not found` | Prod infra definition missing or imported with wrong path | DevOps — re-import from `mca/prod/infraDefinitions/bcp2_infra_prod.yaml` (note: typo `infraDefintions` has caused this before) |
| `CrashLoopBackOff` / RBAC / OCP errors | Same as non-prod stage 3 — see above | App team / DevOps |

---

## Stage 4 (Non-Prod): Test Execution

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| `Tag does not exist in GitLab` | App repo not tagged at the deployed version | App team — ensure CI creates the git tag on publish |
| `src/test/app_validation.py not found` | Test script missing in app repo | App team — create `src/test/app_validation.py` |
| Tests exit non-zero | Test failures — logs streamed to Harness console | App team |
| `K8s Job failed to start` | Delegate or cluster issue | DevOps / BCP2 platform team |

---

## Stage 6 (Non-Prod): Validate Business Metrics

| Signal | Cause | Fix owner |
|--------|-------|-----------|
| Business metrics validation fails | Tests only hit health-check endpoints — real business endpoints not exercised | App team — ensure `app_validation.py` calls real business endpoints, not just `/actuator/health` |
| Observe data missing | ESaaS log harvesting not enabled for the namespace | App team — follow ESaaS Onboarding Steps after namespace creation |

---

## Delegates

Both non-prod and prod BCP2 pipelines use BCP2-hosted delegates. If a delegate is offline, escalate to the BCP2 platform team for the cluster shown in the delegate name or selector tag visible in the Harness Delegates UI.

---

## Key Contacts & Escalation

| Issue area | Contact |
|------------|---------|
| `env-config.json` / `app-dependencies.json` / test scripts | App team |
| Namespace onboarding, RBAC, OCP cluster | BCP2 platform team |
| Org variables, pipeline config | DevOps team owning the pipeline |
| CR / ServiceFirst change management | Change manager / CAB |
| Harness shared workspace full | BUK DevOps Platform (raise support ticket) |
| ESaaS log harvesting | Platform engineering |

---

## Enriching this skill for your team

Add your team's specific values (namespace IDs, config repo paths, testbed assignments, CR template IDs) as a new section at the bottom. Reference this skill from `cd-diagnose-agent` by adding one line to its `skills:` frontmatter.
