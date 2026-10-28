---
name: sdf
description: >
  Use this skill when working with the Barclays SDF (Strategic Development Framework) journey stack.
  Covers the scaffold output structure, Chameleon frontend conventions, DAF backend conventions,
  the npm orchestration layer, VGW (Virtual Gateway) setup, and the lightweight vs full-fat
  development modes. Trigger for any question or task involving fe-{journeyName}, x-{journeyName},
  the sdf-template CLI, or setting up a new SDF journey.
user-invocable: false
source: barclays-claude-code-plugins/plugins/scaffold/skills/sdf/SKILL.md
owner: Philip Thomas (philip.thomas@barclays.com)
review-trigger: On each update to the @barclays/chameleon-sdf-template CLI or SDF stack conventions
status: Full
---

# SDF Journey Stack

The SDF scaffold creates a local development workspace for Barclays journey teams. It produces two
repositories and an optional VGW clone, wired together with a root-level npm scripts layer.

## Workspace layout

```
{journeyName}/                  ← workspace root (run npm scripts from here)
├── package.json                ← npm scripts orchestrate frontend + backend
├── scripts/                    ← cross-platform helpers (gradlew, start-api-window, etc)
├── fe-{journeyName}/           ← Chameleon frontend (React + React Native)
├── x-{journeyName}/            ← DAF backend (Spring Boot)
└── [virtual-gateway-bcp/]      ← Virtual Gateway (optional, cloned if --vgw)
```

## Frontend (`fe-{journeyName}`)

A Chameleon cross-platform app built on React 19 + React Native 0.80, TypeScript 5, Node 22+.

**Key directories:**
```
src/
  screens/start/Start.tsx       ← start screen, calls the DAF backend
  services/welcome-service.ts   ← API service layer
mockBridge/bridge.mock.ts       ← mock ChameleonBridge (fetch-based, no auth)
Makefile                        ← frontend make targets
```

**Development modes:**

| Mode | How | When |
|---|---|---|
| Lightweight | `mockBridge` + direct fetch to `localhost:8080` | Local dev, no Barclays app needed |
| Full-fat | Barclays app + VGW (Docker) + DAF backend | Testing with real DAF contract headers |

**npm scripts:**
- `npm run install:all` — install npm dependencies and build backend
- `npm run start:web` — run on web (Vite, port 5173)
- `npm run start:android` / `npm run start:ios` — build + install + run on each platform
- `npm run start:android:metro` / `npm run start:ios:metro` — Metro only (faster, after first build)
- `npm run stop` — stop VGW (if running)
- `npm run clean` — clean both repos

**Full-fat scripts (VGW required):**
- `npm run start:full:ios` / `npm run start:full:android` — start with VGW + real Barclays app
- `npm run vgw:configure` — re-register API URL substitution with VGW
- `npm run vgw:stop` — stop the VGW Docker container

## Backend (`x-{journeyName}`)

A Spring Boot 3 + DAF 5 service, Gradle-based.

**Key files:**
```
src/main/java/com/barclays/api/{journeyNameJava}/
  Application.java              ← Spring Boot entry point
  controller/WelcomeController  ← GET /api/welcome
  service/WelcomeService        ← business logic
  model/WelcomeResponse         ← DTO
src/main/resources/
  application.yml               ← main config
  application-local.yml         ← local dev profile
  openapi.yaml                  ← API spec
```

**Running the backend:**
```bash
cd x-{journeyName}
./gradlew bootRun --args='--spring.profiles.active=local'
# or via root npm scripts:
npm run start:api   # starts backend in background on port 8080
```

**Health check:** `curl http://localhost:8080/api/welcome`

## Name derivation

The CLI derives all names from the journey name input:

| Input | `card-payments` |
|---|---|
| `journeyName` | `card-payments` |
| `journeyNameJava` | `cardpayments` (hyphens stripped) |
| `JourneyName` | `CardPayments` (PascalCase) |
| Frontend repo | `fe-card-payments` |
| Backend repo | `x-card-payments` |
| npm package | `@barclays/fe-card-payments` |
| Java package | `com.barclays.api.cardpayments` |
| Spring app name | `x-card-payments` |

## Chameleon Constitution

Frontend code must follow the Chameleon Constitution (`docs/chameleon-constitution.md` in the generated
frontend repo). Key non-negotiables:

- **Blueprint-First** — all UI uses `@barclays/blueprint-react` components; no custom styling
- **Cross-platform parity** — features must work on iOS, Android, and web
- **Test-first** — TDD, 85% minimum coverage
- **Typed state** — Redux Toolkit + RTK Query; no raw `useDispatch`/`useSelector`
- **Accessibility** — ARIA labels, React Native accessibility props required

## Prerequisites

| Tool | Required | Recommended |
|---|---|---|
| Node.js | >=22 | — |
| npm | >=10 | — |
| Git | >=2 | — |
| Java | — | >=21 (for backend) |
| Docker | — | >=20 (for VGW) |

## CLI reference

```bash
npx @barclays/chameleon-sdf-template [options]

Options:
  --name <journeyName>    Journey name (lowercase, alphanumeric, hyphens)
  --team <teamName>       Team name (lowercase, alphanumeric, hyphens)
  --vgw                   Include VGW repository
  --no-vgw                Skip VGW repository
  --install-vgw           Clone VGW only (to current directory, then exit)
```

## Agent Self-Check

- [ ] Journey name follows pattern: lowercase, alphanumeric + hyphens, no leading/trailing hyphens
- [ ] Team name follows same pattern as journey name
- [ ] CLI invoked with explicit flags (`--name`, `--team`) — never run interactively
- [ ] `npm run install:all` confirmed successful before proceeding to start scripts
- [ ] iOS/Android start instructions directed to user terminal, not run via Claude
- [ ] VGW scripts mentioned only when `--vgw` was specified during scaffolding
- [ ] Chameleon Constitution constraints (Blueprint-First, cross-platform parity) applied to any frontend work
