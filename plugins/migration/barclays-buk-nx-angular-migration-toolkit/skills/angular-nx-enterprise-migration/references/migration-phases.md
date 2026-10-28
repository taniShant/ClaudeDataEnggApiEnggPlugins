# Migration Phases

Use one Angular major version per phase.

This migration must be controlled, incremental, and reviewable.

## Recommended migration ladder

```text
12 -> 13
13 -> 14
14 -> 15
15 -> 16
16 -> 17
17 -> 18
18 -> 19
19 -> 20
20 -> 21
21 -> latest only after dependency gates pass
```

## Important rule

Do not jump directly from Angular 12 to the latest version.

Each major migration must be:

- planned
- implemented
- validated
- summarised
- accepted before moving to the next phase

## Per-phase branch naming

Use this branch pattern:

```text
chore/angular-12-to-13
chore/angular-13-to-14
chore/angular-14-to-15
chore/angular-15-to-16
chore/angular-16-to-17
chore/angular-17-to-18
chore/angular-18-to-19
chore/angular-19-to-20
chore/angular-20-to-21
```

## Per-phase sequence

Use this pattern and adjust versions based on actual compatibility.

```bash
git checkout -b chore/angular-X-to-Y

npx nx migrate <compatible-nx-version>
npm install
npx nx migrate --run-migrations

npx ng update @angular/core@Y @angular/cli@Y

npm install
npm run test -- --watch=false || true
npx nx affected:test || true
npx nx affected:build || true
npm run build || true
npm run build:single-spa:home || true
```

## Nx migration guidance

Use Nx migration tooling.

Do not manually rename all @nrwl packages to @nx packages unless Nx migrations require it.

Check these files after Nx migration:

```text
package.json
package-lock.json
nx.json
angular.json
workspace.json
project.json
apps/**/project.json
libs/**/project.json
```

Check for executor changes such as:

```text
@nrwl/angular:webpack-browser
@nrwl/angular:package
@nrwl/jest:jest
@nrwl/linter:eslint
@nx/angular:webpack-browser
@nx/angular:ng-packagr-lite
@nx/jest:jest
@nx/eslint:lint
```

## Angular migration guidance

Use Angular migration tooling.

Do not manually bump Angular packages without checking migration output.

Check:

```text
@angular/core
@angular/common
@angular/compiler
@angular/compiler-cli
@angular/cli
@angular-devkit/build-angular
@angular/forms
@angular/router
@angular/platform-browser
@angular/platform-browser-dynamic
@angular/animations
@angular/cdk
```

## Commit strategy

Use one Commit per major Angular version where practical.

Each Commit must contain:

- JIRA Reference Number. Ask User about Jira during first commit and save the same in `memory` for future use.
- dependency changes
- migration-generated changes
- required compatibility fixes
- test/build validation output
- risk summary
- rollback notes
- "Co-authored By: Claude"

## Phase completion criteria

A phase is complete only when:

- npm install succeeds
- package-lock.json is consistent
- Angular compile issues are fixed
- Nx config is valid
- unit tests are either passing or failures are documented
- build is passing or blockers are documented
- Single-SPA build is validated
- Blueprint impact is reviewed
- artefact output is reviewed
- pipeline impact is reviewed
- PR summary is produced

## Stop conditions

Stop the phase if:

- internal @barclays dependency compatibility is unclear
- peer dependency conflicts cannot be resolved cleanly
- Single-SPA lifecycle breaks
- Blueprint components cannot be built
- custom builder or packer output changes unexpectedly
- Nexus artefact shape changes
- pipeline Node version or builder image is incompatible