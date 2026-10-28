# Phase 0 Inventory

Phase 0 is read-only.

Do not edit files.

## Purpose

The goal of Phase 0 is to understand the current repository state before making any dependency, code, build, or pipeline changes.

This phase must produce enough evidence to plan the first safe migration step.

## Rules

- Do not edit files.
- Do not run migrations.
- Do not update package.json.
- Do not update package-lock.json.
- Do not use --force.
- Do not use --legacy-peer-deps.
- Do not guess package compatibility.
- Do not assume internal @barclays package support.
- Do not remove ngcc.
- Do not change pipeline files.

## Commands to run

```bash
node -v
npm -v
npx nx report || true
npx ng version || true
npm ls @angular/core @angular/cli @angular-devkit/build-angular @nrwl/workspace nx @nx/workspace single-spa single-spa-angular @barclays/blueprint-angular @ngrx/store rxjs typescript zone.js jest jest-preset-angular ts-jest eslint || true
```

## Files to inspect

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

## Package areas to inspect

Inspect these package groups:

```text
@angular/*
@angular-devkit/*
@angular-eslint/*
@nrwl/*
@nx/*
single-spa
single-spa-angular
@barclays/*
@ngrx/*
rxjs
zone.js
typescript
jest
jest-preset-angular
ts-jest
eslint
webpack
@angular-builders/custom-webpack
ng-packagr
```

## Build script areas to inspect

Inspect package.json scripts related to:

```text
postinstall
start
serve
serve-single-spa
build
build-single-spa
test
lint
postbuild
pack
publish
sri
custom-builder
packer
```

## Required output

Produce this table:

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

## Architecture summary required

Produce a short summary covering:

- application type
- Nx workspace structure
- Angular version baseline
- Single-SPA entry points
- Blueprint dependency usage
- custom build scripts
- custom webpack usage
- output folder assumptions
- pipeline files present
- artefact publishing assumptions

## Risk register required

Produce a risk register with:

| Risk | Evidence | Impact | Mitigation |
|---|---|---|---|
| | | | |

## Phase 1 plan required

After inventory, produce a plan for Angular 12 to 13 only.

Include:

- packages expected to change
- files expected to change
- commands proposed
- validation commands
- expected blockers
- rollback strategy

## Stop point

Stop after producing the Phase 0 report.

Do not execute Angular 12 to 13 migration until explicitly asked.