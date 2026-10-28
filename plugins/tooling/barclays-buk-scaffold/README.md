# barclays-buk-scaffold

Scaffold new Barclays journey repositories from approved templates — SDF (Chameleon + DAF) stack.

## Usage

```
/scaffold:sdf [--name <journey-name> --team <team-name> [--vgw|--no-vgw]]
```

Scaffolds a complete SDF development workspace:
- `fe-{name}/` — Chameleon React + React Native frontend
- `x-{name}/` — Spring Boot DAF backend
- Optional VGW (Virtual Gateway) clone

## What it does

1. Runs `@barclays/chameleon-sdf-template` CLI with validated inputs
2. Installs all dependencies (`npm run install:all`)
3. Guides you through platform-specific startup (web, iOS, Android)

## Standards

Loads `barclays-buk-ui-engineer-sdf:chameleon` and `barclays-buk-standards:daf` to enforce SDF stack conventions.

## Author

Philip Thomas (philip.thomas@barclays.com)
