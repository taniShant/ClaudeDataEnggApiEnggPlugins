# barclays-buk-api-engineer-api-engineer-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-api-engineer-api-engineer-agent-v1` |
| Plugin name | `barclays-buk-api-engineer` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-api-engineer@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `REQUIREMENTS_PATH` — path to requirements markdown file (typically the output of a product-manager-agent)
- `ARCHITECTURE_PATH` — path to architecture markdown file (typically the output of a solution-architect-agent)
- `DOMAIN_MODEL_PATH` — path to existing domain model or API specs, or `"none"` if absent
- `TECH_STACK` — language and framework string, e.g. `"Java 21 / Spring Boot 3.4.5 / DAF SDK3"` or `"Node/Express"`
- `PROJECT_PATH` — absolute path to the project root
- `OUTPUT_PATH` — absolute path where API artefacts should be written

## Preconditions

- `REQUIREMENTS_PATH` must exist and be readable
- `ARCHITECTURE_PATH` must exist and be readable
- For DAF mode: `TECH_STACK` must be Java/Spring Boot; `barclays-buk-standards:daf` skill must be loaded; DAF SDK3 patterns (no Lombok, thin controllers, gateway layer, constructor injection) will be enforced

## Expected outputs

1. OpenAPI 3.x specification (`openapi.yaml`) — all endpoints, request/response schemas, security schemes (OAuth 2.0/Bearer), and consistent error response shapes
2. API implementation files: controller, service interface + impl, gateway interface + impl, `ErrorCodes` enum (for DAF/Spring Boot projects)
3. API documentation: `README.md` covering authentication, endpoint summary, and example requests/responses for each endpoint

## Exclusions

- Does not deploy services or register APIs in a gateway — that is the caller's responsibility
- Does not produce frontend code or UI components
- Does not generate test files — test generation is handled by dedicated test agents in the DAF pipeline
- Does not generate CI/CD configuration, Kubernetes manifests, or Helm charts
- Does not handle multi-service orchestration — each invocation produces artefacts for a single service boundary

## Verification

Review `openapi.yaml` to confirm all endpoints declare security schemes, complete request/response schemas, and a consistent error shape. For DAF output, confirm no `ResponseEntity<T>` direct usage in controllers, no Lombok annotations, and no `ThreadLocal` usage. Check `README.md` for at least one example request/response per endpoint.
