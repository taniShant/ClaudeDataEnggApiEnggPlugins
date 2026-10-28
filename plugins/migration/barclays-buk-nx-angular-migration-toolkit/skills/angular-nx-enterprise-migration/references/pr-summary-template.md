# PR Summary Template

Use this template after every migration phase.

## Title

Angular migration: Angular X to Angular Y

## Summary

This PR migrates the application from Angular X to Angular Y as part of the staged Angular/Nx enterprise migration.

The migration preserves:

- Nx workspace structure
- Single-SPA lifecycle behaviour
- Blueprint Angular component behaviour
- custom builder behaviour
- custom packer behaviour
- SRI generation behaviour
- deploy-url/base-href behaviour
- Nexus artefact compatibility
- pipeline compatibility unless explicitly changed

## Scope

Include only what applies:

- Angular package updates
- Angular CLI updates
- Angular Devkit updates
- Nx migration updates
- TypeScript compatibility updates
- RxJS compatibility updates
- Zone.js compatibility updates
- NgRx compatibility updates
- Jest compatibility updates
- ESLint compatibility updates
- Single-SPA compatibility updates
- Blueprint compatibility updates
- Webpack/custom builder updates
- Pipeline updates if required

## Files changed

```text
package.json
package-lock.json
angular.json
nx.json
project.json
...
```

## Dependency changes

| Package | Before | After | Reason |
|---|---:|---:|---|
| @angular/core | | | |
| @angular/cli | | | |
| nx | | | |
| typescript | | | |
| rxjs | | | |
| zone.js | | | |
| single-spa-angular | | | |
| @barclays/blueprint-angular | | | |

## Code changes

Describe code changes here:

- ...
- ...
- ...

## Config changes

Describe config changes here:

- ...
- ...
- ...

## Pipeline changes

If pipeline changed, document:

| Item | Before | After | Reason |
|---|---|---|---|
| Node version | | | |
| Builder image | | | |
| Build command | | | |
| Artefact path | | | |
| Scan path | | | |

If pipeline did not change, state:

```text
No pipeline changes were required in this phase.
```

## Validation completed

- [ ] npm install
- [ ] lint
- [ ] unit tests
- [ ] affected tests
- [ ] app build
- [ ] Single-SPA build
- [ ] artefact output verified
- [ ] deploy-url verified
- [ ] SRI/packer output verified
- [ ] pipeline impact reviewed
- [ ] Blueprint impact reviewed
- [ ] Single-SPA lifecycle reviewed

## Validation evidence

Paste command output summary:

```text
npm install:
...

test:
...

build:
...

single-spa build:
...
```

## Known issues

- ...
- ...

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| | | |

## Rollback

Rollback steps:

1. Revert this PR.
2. Restore package.json and package-lock.json from previous phase.
3. Restore Angular/Nx config from previous phase.
4. Re-run npm install.
5. Re-run previous successful build.
6. Redeploy previous Nexus artefact if required.

## Reviewer focus areas

Please review:

- package version alignment
- package-lock correctness
- Angular migration changes
- Nx config changes
- Single-SPA lifecycle changes
- Blueprint component compatibility
- custom builder/SRI/packer output
- pipeline impact
- validation evidence