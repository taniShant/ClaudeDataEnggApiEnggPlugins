# Validation Checklist

Run every applicable validation after each migration phase.

If a command does not exist, report it and continue.

## Install validation

```bash
npm install
```

Check:

- package-lock.json updated correctly
- no unresolved peer dependency conflicts
- no permanent use of --force
- no permanent use of --legacy-peer-deps unless needed
- no unexpected package downgrade
- no unrelated package churn

## Static validation

```bash
npm run lint || true
npx nx affected:lint || true
```

Check:

- ESLint config loads
- TypeScript parser works
- Angular template linting works
- no migration-created lint config corruption

## Unit test validation

```bash
npm run test -- --watch=false || true
npx nx affected:test || true
```

Check:

- Jest starts correctly
- jest-preset-angular is compatible
- jsdom environment works
- setup-jest file works
- Angular TestBed compiles
- path aliases resolve
- transform config works

## Build validation

```bash
npm run build || true
npx nx affected:build || true
```

Check:

- Angular compiler succeeds
- Nx executor works
- TypeScript version is compatible
- custom webpack still works
- assets are copied
- styles are built
- budgets do not fail unexpectedly

## Single-SPA build validation

```bash
npm run build:single-spa:home || true
```

If this script does not exist, identify the actual Single-SPA build script from package.json and run that instead.

Check:

- Single-SPA bundle is generated
- deploy-url is correct
- public path is correct
- lifecycle bundle is emitted
- output path is compatible with existing deployment

## Output checks

Verify:

- dist folder exists
- expected app folder exists
- main bundle exists
- polyfills bundle exists if expected
- runtime bundle exists if expected
- styles bundle exists if expected
- assets are copied
- SRI output exists if expected
- custom packer output exists if expected
- generated artefact name is correct
- output is compatible with Nexus publication

## Git validation

```bash
git status
git diff -- package.json package-lock.json
git diff -- angular.json nx.json workspace.json project.json
```

Check:

- only expected files changed
- package changes are explainable
- migration changes are explainable
- no unrelated formatting churn
- no accidental deletion of custom scripts

## Required phase report

After validation, produce:

```markdown
## Validation result

| Check | Status | Notes |
|---|---|---|
| npm install | | |
| lint | | |
| unit tests | | |
| affected tests | | |
| build | | |
| Single-SPA build | | |
| artefact output | | |
| pipeline impact | | |

## Issues found

...

## Fixes applied

...

## Remaining risks

...
```
