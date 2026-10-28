Use the angular-nx-enterprise-migration skill.

Task:
Execute exactly one Angular major-version migration.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| source | Yes | Current Angular major version (e.g. 12) |
| target | Yes | Target Angular major version (e.g. 13) |

Input expected from user:
- source Angular major
- target Angular major

Example invocation:

```text
/angular-migrate-one-major source Angular 12 target Angular 13
```

Rules:
- Do not jump more than one Angular major.
- Do not redesign architecture.
- Do not convert to standalone components unless required by the migration.
- Preserve Single-SPA bootstrap, mount, unmount and props behaviour.
- Preserve Blueprint Angular component behaviour.
- Preserve custom builder, packer, SRI and deploy-url behaviour.
- Preserve Nexus artefact output shape.
- Preserve SIT deployment compatibility.
- Do not remove ngcc unless this phase proves it is safe.
- Do not use --force as a permanent solution.
- Do not use --legacy-peer-deps as a permanent solution.
- Stop if internal @barclays dependency compatibility is unclear.
- Stop if build output shape changes unexpectedly.
- Stop if Single-SPA lifecycle cannot be verified.
- Stop if Blueprint peer dependency compatibility is unclear.

Pre-flight steps:
1. Read CLAUDE.md.
2. Read `.claude/skills/angular-nx-enterprise-migration/SKILL.md`.
3. Read all reference files under `.claude/skills/angular-nx-enterprise-migration/references/`.
4. Check current git status:

```bash
git status
```

5. Confirm the working tree is clean before making changes.
6. Identify current Angular version from package.json.
7. Confirm the requested source and target Angular versions are exactly one major apart.
8. Inspect package.json and package-lock.json before changes.

Implementation steps:
1. Create a phase branch using this pattern:

```bash
git checkout -b chore/angular-X-to-Y
```

2. Run Nx migration for a compatible target version.

Use the actual version required by the phase:

```bash
npx nx migrate <compatible-nx-version>
```

3. Install dependencies after Nx migration file generation:

```bash
npm install
```

4. Run Nx migrations:

```bash
npx nx migrate --run-migrations
```

5. Run Angular migration for the target major:

```bash
npx ng update @angular/core@Y @angular/cli@Y
```

6. Install dependencies again:

```bash
npm install
```

7. Fix migration errors without broad refactoring.
8. Run validation:

```bash
npm run test -- --watch=false || true
npx nx affected:test || true
npx nx affected:build || true
npm run build || true
npm run build:single-spa:home || true
```

9. If present, run the validation script:

```bash
.claude/skills/angular-nx-enterprise-migration/scripts/validate-migration-phase.sh
```

10. Inspect generated output:

```bash
find dist -maxdepth 4 -type f 2>/dev/null | head -100 || true
```

11. Review git diff:

```bash
git status
git diff -- package.json package-lock.json
git diff -- angular.json nx.json workspace.json project.json
```

Required checks:
- package versions are aligned
- package-lock.json is consistent
- Nx migrations completed
- Angular migrations completed
- Single-SPA-related files still compile
- Blueprint imports still compile
- custom webpack still compiles
- custom builder still runs if part of build
- custom SRI still runs if part of build
- custom packer still runs if part of build
- deploy-url/base-href behaviour is preserved
- dist output path is reviewed
- Nexus artefact shape is reviewed
- pipeline impact is reviewed

Output format:

```markdown
# Angular Migration Phase Report

## Phase

Angular X to Angular Y

## Summary

...

## Commands executed

```bash
...
```

## Files changed

```text
...
```

## Dependency changes

| Package | Before | After | Reason |
|---|---:|---:|---|
| @angular/core | | | |
| @angular/cli | | | |
| nx / @nrwl / @nx | | | |
| typescript | | | |
| rxjs | | | |
| zone.js | | | |
| single-spa-angular | | | |
| @barclays/blueprint-angular | | | |

## Code changes

...

## Config changes

...

## Single-SPA validation

| Check | Status | Notes |
|---|---|---|
| bootstrap preserved | | |
| mount preserved | | |
| unmount preserved | | |
| props preserved | | |
| deploy-url preserved | | |
| asset loading preserved | | |
| local serve checked | | |
| production build checked | | |

## Blueprint validation

| Check | Status | Notes |
|---|---|---|
| Blueprint package version reviewed | | |
| peer dependencies reviewed | | |
| Angular compatibility reviewed | | |
| module imports reviewed | | |
| templates reviewed | | |
| styles reviewed | | |
| accessibility-sensitive components reviewed | | |

## Pipeline validation

| Check | Status | Notes |
|---|---|---|
| Node version reviewed | | |
| npm version reviewed | | |
| builder image reviewed | | |
| build command reviewed | | |
| artefact path reviewed | | |
| Nexus output reviewed | | |
| SIT deployment impact reviewed | | |

## Validation results

| Command | Status | Notes |
|---|---|---|
| npm install | | |
| unit tests | | |
| affected tests | | |
| affected build | | |
| app build | | |
| Single-SPA build | | |

## Known issues

...

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| | | |

## Rollback

1. Revert this migration commit or PR.
2. Restore package.json and package-lock.json from previous phase.
3. Restore Angular/Nx config from previous phase.
4. Run npm install.
5. Re-run previous successful build.
6. Redeploy previous Nexus artefact if required.

## PR-ready summary

...
```

Stop after completing this one major-version phase.

Do not continue to the next Angular major until explicitly asked.