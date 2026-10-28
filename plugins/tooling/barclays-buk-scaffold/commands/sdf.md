---
description: Scaffold a new Barclays SDF journey stack — Chameleon frontend (fe-{name}) and DAF backend (x-{name}) repositories
argument-hint: "[optional: --name <journey-name> --team <team-name> [--vgw|--no-vgw]]"
---

When the user runs `/scaffold:sdf`, they want to scaffold a new SDF journey development stack
using the `@barclays/chameleon-sdf-template` CLI.

## Instructions

The CLI requires a TTY for interactive prompts which is not available here. Always run it with
explicit flags — never without arguments.

1. **If the user provided all required arguments** (`--name` and `--team`), run immediately.
2. **If any required arguments are missing**, ask for them as plain conversational questions in your response text. Do not use AskUserQuestion — journey names and team names are user-specific and open-ended; plain conversation allows the user to provide any valid input without being constrained by predefined options. Ask:
   - "What is the journey name?" (e.g. `payments`, `card-payments`)
   - "What is the team name?" (e.g. `cobra-squad`)
   - "Include the Virtual Gateway? (yes/no, default yes)"
3. Once all inputs are gathered, run:

```bash
npx @barclays/chameleon-sdf-template --name <journeyName> --team <teamName> [--vgw|--no-vgw]
```

## Validation rules

- Journey name: lowercase, alphanumeric + hyphens, no leading/trailing hyphens (e.g. `payments`, `card-payments`)
- Team name: same pattern (e.g. `cobra-squad`, `eagle-squad`)
- Reject and re-ask if either value fails validation before running the CLI

## What it creates

```
{journeyName}/
├── package.json         ← npm scripts orchestrate everything
├── scripts/             ← cross-platform helpers
├── fe-{journeyName}/    ← Chameleon React + React Native frontend
├── x-{journeyName}/     ← Spring Boot DAF backend
└── [virtual-gateway-bcp/] ← Virtual Gateway (if --vgw)
```

## After scaffolding

Once the CLI exits successfully:

### 1. Install dependencies

Always run install first and wait for it to complete:

```bash
cd {journeyName} && npm run install:all
```

Confirm it exits successfully before proceeding.

### 2. Choose a platform and start developing

Ask which platform they want to try (web, iOS, or Android), then:

- **Web**: run in the background — Vite starts in seconds on port 5173:
  ```bash
  cd {journeyName} && npm run start:web
  ```

- **iOS or Android**: do NOT run through Claude. The first build requires Gradle compilation,
  CMake native layer compilation, APK/IPA packaging, and Metro bundler startup — this takes
  5-10 minutes and produces hundreds of lines of build output that cannot be streamed here
  meaningfully. Instead, tell the user to run it directly in their terminal:
  ```bash
  cd {journeyName} && npm run start:ios
  # or
  cd {journeyName} && npm run start:android
  ```
  Tell them what to watch for as signals it's working:
  - Gradle downloading dependencies (first run only)
  - `BUILD SUCCESSFUL` — native build done
  - `Metro waiting on exp+...` or the app launching on the simulator/device

### 3. Show available scripts for reference

Always tell the user the npm scripts available:

| Script | Description |
|---|---|
| `npm run install:all` | Install dependencies for both frontend and backend |
| `npm run start:web` | Vite dev server (web) + API on localhost:8080 |
| `npm run start:ios` | Build + run on iOS simulator + API |
| `npm run start:ios:metro` | Metro only (faster for day-to-day) |
| `npm run start:android` | Build + run on Android emulator + API |
| `npm run start:android:metro` | Metro only (faster for day-to-day) |
| `npm run start:api` | API only (blocking) |
| `npm run test:fe` | Front-end unit tests with coverage |
| `npm run test:be` | Back-end unit tests |
| `npm run lint:fe` | Front-end lint |
| `npm run clean` | Clean both projects |

**If VGW was included**, also mention:
| Script | Description |
|---|---|
| `npm run start:full:ios` | VGW + API + iOS Metro (full-fat) |
| `npm run start:full:android` | VGW + API + Android Metro (full-fat) |
| `npm run vgw:configure` | Re-register API URL substitution with VGW |
| `npm run vgw:stop` | Stop the VGW Docker container |
