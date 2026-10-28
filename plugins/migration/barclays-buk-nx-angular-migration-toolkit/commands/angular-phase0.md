Use the angular-nx-enterprise-migration skill.

Task:
Run Phase 0 inventory only.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| path | No | Path to Nx workspace root (defaults to current directory) |

Rules:
- Do not edit files.
- Do not run migrations.
- Do not change package.json.
- Do not change package-lock.json.
- Do not use --force.
- Do not use --legacy-peer-deps.
- Do not remove ngcc.
- Do not change pipeline files.
- Do not guess internal @barclays package compatibility.
- Do not jump directly to latest Angular.

Steps:
1. Read CLAUDE.md.
2. Read `.claude/skills/angular-nx-enterprise-migration/SKILL.md`.
3. Read all files under `.claude/skills/angular-nx-enterprise-migration/references/`.
4. Run the Phase 0 inventory script if present:

```bash
.claude/skills/angular-nx-enterprise-migration/scripts/phase0-inventory.sh
```

5. If the inventory script is not present, manually run:

```bash
node -v
npm -v
npx nx report || true
npx ng version || true
npm ls @angular/core @angular/cli @angular-devkit/build-angular @nrwl/workspace nx @nx/workspace single-spa single-spa-angular @barclays/blueprint-angular @ngrx/store rxjs typescript zone.js jest jest-preset-angular ts-jest eslint || true
```

6. Inspect these files if present:

```text
package.json
package-lock.json
angular.json
workspace.json
nx.json
project.json
apps/**/project.json
libs/**/project.json
tsconfig*.json
jest.config.*
jest.preset.*
setup-jest.*
setup-jest.ts
setup-jest.js
.eslintrc*
eslint.config.*
webpack.config.*
extra-webpack.config.*
feature-webpack.config.*
src/main.single-spa.ts
src/main.ts
src/app/app.module.ts
tools/**
scripts/**
.gitlab-ci.yml
Jenkinsfile
.nvmrc
.npmrc
```

7. Produce a Phase 0 report containing:
   - current dependency matrix
   - current architecture summary
   - Nx workspace summary
   - Single-SPA summary
   - Blueprint Angular summary
   - custom builder / packer / SRI summary
   - pipeline summary
   - risk register
   - migration ladder
   - Angular 12 to 13 implementation plan only
   - files expected to change in Phase 1
   - exact commands proposed for Phase 1
   - rollback plan

Output format:

```markdown
# Phase 0 Inventory Report

## Current dependency matrix

| Area | Current value | Evidence | Risk | Notes |
|---|---:|---|---|---|
| Angular | | | | |
| Angular CLI | | | | |
| Angular Devkit | | | | |
| Nx | | | | |
| Node | | | | |
| npm | | | | |
| TypeScript | | | | |
| RxJS | | | | |
| Zone.js | | | | |
| NgRx | | | | |
| Jest | | | | |
| jest-preset-angular | | | | |
| ESLint | | | | |
| single-spa | | | | |
| single-spa-angular | | | | |
| Blueprint Angular | | | | |
| Barclays internal packages | | | | |
| Custom webpack | | | | |
| Custom builder | | | | |
| SRI generation | | | | |
| Pipeline | | | | |
| Nexus output | | | | |

## Architecture summary

...

## Single-SPA summary

...

## Blueprint summary

...

## Build and pipeline summary

...

## Risk register

| Risk | Evidence | Impact | Mitigation |
|---|---|---|---|
| | | | |

## Recommended migration ladder

...

## Phase 1 plan: Angular 12 to 13

### Expected package changes

...

### Expected file changes

...

### Commands proposed

...

### Validation commands

...

### Rollback plan

...
```

Stop after the Phase 0 report.

Do not execute Angular 12 to 13 migration until explicitly asked.