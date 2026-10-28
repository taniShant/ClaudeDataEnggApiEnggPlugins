# barclays-buk-api-engineer-create-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-api-engineer-create-v1` |
| Plugin name | `barclays-buk-api-engineer` |
| Component type | skill-user-only |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-api-engineer@barclays-cio-buk |
| Native command | `/barclays-buk-api-engineer:create` |
| Skill name | `create` |

## Description

Create a new Barclays API service. Routes to DAF (Spring Boot 3 microservice from markdown spec) or sMesh (Spring Boot 3 from OpenAPI spec with generate/validate/refine/fix operations).

## When to use

Use to generate a new Barclays API service from a specification. Supports two modes — DAF (Spring Boot 3 microservice from a markdown spec driven through a 6-wave pipeline) and sMesh (Spring Boot 3 from an OpenAPI 3.x spec with generate, validate, refine, and fix operations). Requires a JIRA ticket ID for audit traceability. Use --operation fix to repair an existing project rather than generating from scratch.

## Inputs

- `JIRA_ID` (required) — JIRA ticket identifier, e.g. `PLATENG-1234`; logged at workflow start for traceability
- `--type daf|smesh` (required) — service type to generate
- **For `--type daf`:** `SPEC_FILE` (path to markdown service specification), `TARGET_DIR` (output directory), optional `--full-automation`, optional `--operation fix PROJECT_PATH [--mode compile|tests|coverage|patterns|hexagonal|all] [--max-cycles N]`
- **For `--type smesh`:** `--operation generate|validate|refine|fix`; for `generate`: `SPEC_PATH` (OpenAPI 3.x spec), `--output`, `--package`, `--artifact`, `--version`, `--db yes|no`, `--api-class external|internal`, `--tdd`, `--max-cycles N`; for `validate`: `SPEC_PATH`, `--api-type`; for `refine`: `PROJECT_PATH` with endpoint/model/spec flags; for `fix`: `PROJECT_PATH`, `--mode`, `--max-cycles`

## Preconditions

- `JIRA_ID` must be non-empty and match `[A-Z]+-[0-9]+`
- For DAF: `SPEC_FILE` must exist, be readable, and end in `.md`; parent directory of `TARGET_DIR` must exist and be writable
- For sMesh generate/validate: the OpenAPI 3.x spec file must be valid YAML or JSON
- For sMesh refine/fix: `PROJECT_PATH` must point to a previously generated Spring Boot project

## Expected outputs

- **DAF:** A complete Spring Boot 3 microservice at `TARGET_DIR` — controllers, services, gateways, `ErrorCodes` enum, Spock unit tests, Karate integration tests, JaCoCo/pitest coverage reports, a DAF config repo, and a final wave result banner showing coverage percentages
- **sMesh generate:** A Spring Boot 3 project generated from the OpenAPI spec at the specified output directory
- **sMesh validate:** A validation report listing OAS syntax issues and Barclays API standards violations
- **sMesh refine:** Updated project files reflecting added endpoints, producers, or model changes
- **sMesh fix / DAF fix:** Targeted fixes to compilation errors, test failures, or coverage gaps in an existing project

## Exclusions

- Does not deploy services, register APIs in a gateway, or modify CI/CD pipelines
- Does not create or author the specification file — spec authoring is handled by separate tooling
- Does not modify Kubernetes manifests, Helm charts, or infrastructure configuration
- `--full-automation` mode is scoped to the current session — it does not persist hooks beyond the workflow run

## Verification

For DAF: the Wave 5 Golden Gate (full clean build + tests + coverage) must pass before the workflow reports success — check the final banner for line/branch/mutation coverage. For sMesh generate: run the project's build command (`./gradlew build` or `mvn clean install`) and confirm compilation and tests pass. For validate: review the report for zero blocking violations before using the spec.
