# deploy-service-v1

| Field | Value |
| --- | --- |
| Capability ID | `deploy-service-v1` |
| Plugin name | `release-workflows` |
| Component type | skill-model-invocable |
| Owner | platform-delivery-team |
| Action scope | externally-consequential |
| Invocation mode | model-invocable |
| Installation / release | release-workflows >= 2.1.0; install via the approved plugin registry at go/plugins |
| Native command | `/release-workflows:deploy-service` |
| Skill name | `deploy-service` |

## Description

Deploy a service revision to a target environment using the approved pipeline, then verify the deployment reached a healthy state.

## When to use

Use when an implementation is ready to be promoted to a named environment and the deployment pipeline is available. Not for initial environment provisioning, rollback of a previous revision, or infrastructure changes outside the service boundary.

## Inputs

- Target environment name (e.g., `staging`, `production`)
- Service name and the revision identifier or image digest to deploy
- Confirmation that the deployment pipeline is accessible and the caller has the required deployment role

## Preconditions

- The service revision has passed CI and all required pre-deployment checks
- The target environment is not locked for maintenance
- The caller holds a valid deployment credential for the target environment
- The approved deployment pipeline is reachable (network and IAM access)

## Expected outputs

- Deployment receipt: pipeline run ID, revision deployed, timestamp, and final pipeline status
- Post-deployment health check result: number of healthy instances, any failed readiness probes
- A summary of any rollout events (e.g., canary traffic split progress, circuit-breaker state)

## Exclusions

- Does not provision new environments or modify infrastructure outside the service boundary
- Does not perform rollback; use the dedicated `rollback-service` workflow for that
- Does not update pipeline configuration or deployment policy
- Does not handle multi-region coordinated rollouts; each region is a separate invocation

## Verification

Run `pipeline status <run-id> --env <target-env>` after the workflow completes and confirm the reported revision matches the requested image digest. The check applies to the deployment record produced in this run; it does not verify the state of prior deployments.
