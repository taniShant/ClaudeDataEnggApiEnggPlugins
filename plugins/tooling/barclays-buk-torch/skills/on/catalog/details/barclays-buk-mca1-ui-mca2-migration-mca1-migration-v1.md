# barclays-buk-mca1-ui-mca2-migration-mca1-migration-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-mca1-ui-mca2-migration-mca1-migration-v1` |
| Plugin name | `barclays-buk-mca1-ui-mca2-migration` |
| Component type | skill-user-only |
| Owner | Pandu Ranga Rao Maddala, Atul Singh |
| Action scope | local-modification |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-mca1-ui-mca2-migration@barclays-cio-buk |
| Native command | `/barclays-buk-mca1-ui-mca2-migration:mca1-migration` |
| Skill name | `mca1-migration` |

## Description

Autonomously migrate MCA1 JMVC/BDL frontend projects to MCA2 React with Blueprint-React and functional component patterns. Use when user says "migrate MCA1 UI", "MCA2 frontend migration", "convert BDL components", "replace JMVC", or runs /mca1-migration. Transforms all 41 BDL <mca-*> web components to Blueprint-React equivalents, converts JMVC BaseController classes to React functional components, migrates $scope bindings to useState/Redux, and sets up MemoryRouter with Redux Toolkit. Optionally converts regression tests to Cypress or Playwright with MSW mocks.

## When to use

Use when migrating an MCA1 JMVC/BDL frontend project to MCA2 React with Blueprint-React — covers BDL <mca-*> component replacement, JMVC $scope-to-useState conversion, BaseController-to-functional-component migration, MemoryRouter setup, and optional regression test conversion; this skill is NOT for backend MCA1 migration (use mca1-to-mca2-eps for that), NOT for projects already on MCA2 React, and NOT for partial/manual component-by-component migration.

## Inputs

- Project root directory (run from repo root, or provide `MCA1_REPO_PATH` as the first positional argument; must contain `package.json` and `src/`)
- Optional: `--jira JIRA_ID` — JIRA ticket ID used to name the feature branch (`feature/mca2-migration-{JIRA_ID}`)
- Optional: `--template-repo URL` — URL of an MCA2 template repository; when provided, the plugin clones it, detects state management library, routing patterns, folder structure, and naming conventions, and uses those instead of defaults (Redux Toolkit + canonical folder structure)
- Optional: `--regression-repo URL` — URL of an external regression test repository; when provided, the plugin converts existing regression scripts to Cypress or Playwright E2E tests with isolated MSW mocks

## Preconditions

- Plugin `barclays-buk-mca1-ui-mca2-migration` installed with all sub-agents available
- MCA1 project with JMVC/BDL patterns (`BaseController`, `$scope` bindings, `<mca-*>` web component tags, BDL imports)
- Node.js and npm available on the PATH (`npm --version` exits 0)
- `@barclays/blueprint-react` v1.3.0 available (declared in `package.json` or installable via `npm install`)
- Git initialised in the project root (git workflow — branch creation, staging, commits — is handled by the user after migration completes)

## Expected outputs

- MCA2 React + TypeScript source files replacing all JMVC/BDL patterns:
  - All 41 BDL `<mca-*>` components replaced with correct Blueprint-React equivalents using the render-function pattern for `FormItem`/`FormMultiItem`, slot props for `Dialog`, standard HTML inside `Table`, and `MemoryRouter` (never `BrowserRouter`)
  - All `BaseController` class shells converted to React functional components with `useState`/`useEffect`; Redux thunks and reducers left untouched
  - All `$scope` local state converted to `useState`; service call dispatches wired to existing Redux thunks via `useEffect`
  - All BDL imports replaced with `@barclays/blueprint-react` imports
- Build passing: `npm run lint`, `npx tsc --noEmit`, and `npm run build` all exit 0 after Phase 3 quality gate
- Optional: E2E regression tests in `cypress/e2e/regression/` (Cypress) or `e2e/regression/` (Playwright) with isolated MSW mock handlers; test files compile and lint cleanly
- Optional: `{PROJECT_PATH}/.claude/template-analysis.json` when `--template-repo` provided
- State management and API service files (Redux reducers, thunks, selectors, `process.json`, API service files) are left unmodified

## Exclusions

- Does NOT migrate backend MCA1 EPS applications — use `mca1-to-mca2-eps` for backend migration
- Does NOT modify Redux reducers, async thunks, API service files, `process.json`, or domain calculation functions (UI scope only)
- Does NOT handle git workflow — user creates the feature branch, stages changes, and commits after the skill completes
- Does NOT fix pre-existing lint or TypeScript errors unrelated to the BDL/JMVC migration
- Does NOT add `BrowserRouter` — MCA2 modules always use `MemoryRouter`
- Does NOT import non-existent Blueprint components (`DialogHeader`, `TableHead`, `FormGroup`, `Tooltip`, `Popover`, `Spinner` do not exist in Blueprint-React v1.3.0)
- Does NOT run JAXB, Spring Boot, or Gradle changes — this skill is frontend-only

## Verification

Confirm that zero BDL imports remain (`grep -r "from 'bdl'" src/` returns no matches), zero `$scope` bindings remain, zero `BaseController` references remain, and zero non-existent Blueprint component imports (`DialogHeader`, `TableHead`, `FormGroup`, `Tooltip`, `Spinner`) remain. The three build quality gates must all pass: `npm run lint`, `npx tsc --noEmit`, and `npm run build` exit 0. If regression tests were generated, `cypress/e2e/regression/` or `e2e/regression/` must contain at least one test file and the corresponding TypeScript compile and lint checks must pass.
