# barclays-buk-scaffold-sdf-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-scaffold-sdf-v1` |
| Plugin name | `barclays-buk-scaffold` |
| Component type | skill-model-invocable |
| Owner | Philip Thomas |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-scaffold@barclays-cio-buk |
| Native command | `/barclays-buk-scaffold:sdf` |
| Skill name | `sdf` |

## Description

Use this skill when working with the Barclays SDF (Strategic Development Framework) journey stack. Covers the scaffold output structure, Chameleon frontend conventions, DAF backend conventions, the npm orchestration layer, VGW (Virtual Gateway) setup, and the lightweight vs full-fat development modes. Trigger for any question or task involving fe-{journeyName}, x-{journeyName}, the sdf-template CLI, or setting up a new SDF journey.

## When to use

Use when scaffolding a new Barclays SDF journey workspace, understanding the generated workspace layout (fe-{journeyName}, x-{journeyName}, VGW), configuring development modes (lightweight vs full-fat), running npm orchestration scripts, or applying Chameleon Constitution conventions to frontend code — not for non-SDF journey types, production deployment, or CI/CD pipeline configuration.

## Inputs

- `--name <journeyName>` (required): Journey name, must be lowercase, alphanumeric with hyphens, no leading/trailing hyphens
- `--team <teamName>` (required): Team name, same pattern constraints as journey name
- `--vgw` (optional flag): Include the Virtual Gateway (virtual-gateway-bcp) repository in the workspace
- `--no-vgw` (optional flag): Explicitly skip VGW repository cloning
- `--install-vgw` (optional flag): Clone VGW repository only into the current directory, then exit
- CLI invocation: `npx @barclays/chameleon-sdf-template [options]` — must always be run with explicit flags, never interactively

## Preconditions

- Node.js >= 22 and npm >= 10 installed
- Git >= 2 installed
- Java >= 21 available if backend development is needed (for Spring Boot / Gradle)
- Docker >= 20 available if full-fat development mode with VGW is required
- CLI flags passed explicitly (--name, --team) — interactive prompts must not be relied upon
- Journey name validated: lowercase, alphanumeric + hyphens only, no leading or trailing hyphens

## Expected outputs

- A workspace root directory `{journeyName}/` containing a `package.json` with npm orchestration scripts and a `scripts/` directory with cross-platform helpers
- `fe-{journeyName}/`: A Chameleon cross-platform frontend (React 19 + React Native 0.80, TypeScript 5) with screens, services, mockBridge, and a Makefile
- `x-{journeyName}/`: A Spring Boot 3 + DAF 5 backend with a WelcomeController (GET /api/welcome), service layer, DTO, OpenAPI spec, and Gradle build
- (Optional) `virtual-gateway-bcp/`: A VGW clone for full-fat development mode, included only when `--vgw` is specified
- Derived naming across the stack: npm package (`@barclays/fe-{journeyName}`), Java package (`com.barclays.api.{journeyNameJava}`), Spring app name (`x-{journeyName}`), PascalCase class names

## Exclusions

- Does not deploy to any environment or configure CI/CD pipelines
- Does not run iOS/Android build commands directly — those must be directed to the user's terminal
- Does not cover non-SDF journey architectures or non-Chameleon frontend frameworks
- Does not manage VGW Docker container lifecycle beyond the provided npm scripts (vgw:configure, vgw:stop)
- Does not generate production-ready configuration (application.yml local profile is for development only)
- Does not handle Barclays app signing, provisioning, or mobile device management
- VGW-related scripts and guidance are out of scope when `--vgw` was not specified during scaffolding

## Verification

Confirm that `npm run install:all` completes successfully in the workspace root, which installs npm dependencies and builds the backend. Verify the backend is healthy by running `curl http://localhost:8080/api/welcome` after `npm run start:api`, and confirm the frontend launches via `npm run start:web` on port 5173. Cross-check the Agent Self-Check list in the skill — journey/team name patterns, explicit CLI flags, VGW consistency, and Chameleon Constitution compliance should all be validated.
