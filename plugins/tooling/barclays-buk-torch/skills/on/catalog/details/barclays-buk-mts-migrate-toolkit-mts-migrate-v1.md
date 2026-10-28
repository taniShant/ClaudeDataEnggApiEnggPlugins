# barclays-buk-mts-migrate-toolkit-mts-migrate-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-mts-migrate-toolkit-mts-migrate-v1` |
| Plugin name | `barclays-buk-mts-migrate-toolkit` |
| Component type | skill-user-only |
| Owner | MCA Core Engineering |
| Action scope | externally-consequential |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-mts-migrate-toolkit@barclays-cio-buk |
| Native command | `/barclays-buk-mts-migrate-toolkit:mts-migrate` |
| Skill name | `mts-migrate` |

## Description

Generate migration code from MTS mainframe service to a replacement API, with strategy selection (new microservice, existing microservice, or in-place dual-path)

## When to use

Use when migrating a BUK Spring Boot service that calls MTS mainframe APIs to a replacement REST API — supports three strategies: new microservice, existing microservice, or in-place dual-path with feature flag; run mts-documentation first to produce the artefacts this skill consumes; NOT for services that are already REST or have no MTS doService/callService calls.

## Inputs

- PROJECT_PATH (required, positional): path to the MTS service codebase root; must contain `build.gradle` or `pom.xml` and a `src/main/java` source tree
- --strategy STRATEGY (required): migration approach — one of `new-microservice`, `existing-microservice`, or `in-place-dual-path`
- --jira JIRA_ID (optional): JIRA ticket ID for branch naming and commit prefixes (format `^[A-Z]+-[0-9]+$`)

## Preconditions

- Plugin `barclays-buk-mts-migrate-toolkit` is installed with all sub-agents available
- Target project is a Spring Boot service containing MTS `doService()` or `callService()` calls (EBS/EGS pattern)
- MTS dependencies (EBS/EGS JARs) are present and the Gradle cache is populated
- `mts-documentation` has been run on the codebase and per-service documentation files exist; `api-replacement-match` results are available (replacement API candidates identified)
- Git is initialized in the project and the working tree is clean enough to create a feature branch

## Expected outputs

- Generated migration code replacing MTS calls with REST equivalents, scoped to the chosen strategy:
  - `new-microservice`: new standalone service scaffolded with REST client wiring
  - `existing-microservice`: REST client injected into the existing service alongside removal of MTS transport
  - `in-place-dual-path`: feature-flag-gated dual path (MTS + REST) with converter classes and tests, allowing gradual rollout
- Updated `build.gradle` or `pom.xml` with MTS dependencies replaced or conditioned
- Converter and adapter classes bridging MTS request/response models to REST equivalents
- Unit tests covering the new REST-backed code paths
- PR branch with per-phase commits prefixed with JIRA ID (if provided)

## Exclusions

- Does NOT run `mts-documentation` or `api-replacement-match` — those must be completed beforehand
- Does NOT modify services already using REST or HTTP transport (classified as `already-api-rest` or `already-api-direct-http`)
- Does NOT select or validate the replacement API — that is the responsibility of `api-replacement-match`
- Does NOT push the branch to remote — the engineer must review and push manually
- Does NOT handle non-Java projects or projects without the standard `src/main/java` layout

## Verification

Confirm that the feature branch contains commits covering the chosen migration strategy, that `./gradlew test` passes on the migrated codebase, and that MTS `doService()`/`callService()` call sites have been replaced or dual-pathed as expected. For `in-place-dual-path`, verify that the feature flag is wired and that both the legacy MTS path and the new REST path compile and have test coverage. The per-service documentation files produced by `mts-documentation` should be cross-referenced to confirm all documented MTS calls are addressed.
