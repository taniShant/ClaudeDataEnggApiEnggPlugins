Use the angular-nx-enterprise-migration skill.

Use the dependency-compatibility-auditor agent mindset.

Task:
Audit dependency compatibility for the Angular/Nx migration.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| target | No | Target Angular major version to audit against (defaults to next major) |

Rules:
- Do not edit files.
- Do not run migrations.
- Do not update package.json.
- Do not update package-lock.json.
- Do not use --force.
- Do not use --legacy-peer-deps.
- Do not guess internal @barclays package versions.
- Separate evidence from recommendation.

Steps:
1. Read package.json.
2. Read package-lock.json.
3. Inspect npm scripts.
4. Inspect npmrc files if present.
5. Inspect Angular package versions.
6. Inspect Nx package versions.
7. Inspect TypeScript, RxJS and Zone.js versions.
8. Inspect NgRx versions.
9. Inspect Jest and jest-preset-angular versions.
10. Inspect ESLint and TypeScript ESLint versions.
11. Inspect Single-SPA and single-spa-angular versions.
12. Inspect @barclays package versions.
13. Identify peer dependency risks.
14. Produce a compatibility report.

Optional read-only commands:

```bash
npm ls @angular/core @angular/cli @angular-devkit/build-angular @nrwl/workspace nx @nx/workspace typescript rxjs zone.js @ngrx/store jest jest-preset-angular ts-jest eslint single-spa single-spa-angular @barclays/blueprint-angular || true
npm view @angular/core peerDependencies || true
npm view single-spa-angular peerDependencies || true
```

If internal registry access is unavailable, record the limitation.

Output format:

```markdown
# Angular/Nx Dependency Compatibility Audit

## Current package summary

| Package | Current version | Dependency type | Evidence |
|---|---:|---|---|
| | | | |

## Runtime dependencies

| Package | Current | Risk | Notes |
|---|---:|---|---|
| | | | |

## Development dependencies

| Package | Current | Risk | Notes |
|---|---:|---|---|
| | | | |

## Angular compatibility

...

## Nx compatibility

...

## TypeScript / RxJS / Zone.js compatibility

...

## NgRx compatibility

...

## Jest compatibility

...

## ESLint compatibility

...

## Single-SPA compatibility

...

## Blueprint / Barclays package compatibility

...

## Blockers

| Package | Conflict | Evidence | Decision needed |
|---|---|---|---|
| | | | |

## Recommended next target

Recommended next phase:
Reason:

## Proposed package changes for next phase

| Package | Current | Proposed target | Reason |
|---|---:|---:|---|
| | | | |

## Commands proposed for next phase

```bash
...
```

## Risks

...

## Rollback strategy

...
```

Stop after the audit.

Do not modify files.
