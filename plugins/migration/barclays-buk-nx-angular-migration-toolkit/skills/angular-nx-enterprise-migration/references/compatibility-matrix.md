# Compatibility Matrix

For each migration phase, fill this table before implementation.

Do not proceed with a migration phase until the target versions are understood.

## Version matrix

| Package / Tool | Current | Target | Source of truth | Action | Risk |
|---|---:|---:|---|---|---|
| @angular/core | | | package.json / Angular update guide | | |
| @angular/common | | | package.json / Angular update guide | | |
| @angular/compiler | | | package.json / Angular update guide | | |
| @angular/compiler-cli | | | package.json / Angular update guide | | |
| @angular/cli | | | package.json / Angular update guide | | |
| @angular-devkit/build-angular | | | package.json | | |
| @angular/forms | | | package.json | | |
| @angular/router | | | package.json | | |
| @angular/platform-browser | | | package.json | | |
| @angular/platform-browser-dynamic | | | package.json | | |
| @angular/animations | | | package.json | | |
| @angular/cdk | | | package.json | | |
| nx | | | package.json / Nx migrations | | |
| @nrwl/angular | | | package.json / Nx migrations | | |
| @nrwl/workspace | | | package.json / Nx migrations | | |
| @nx/angular | | | package.json / Nx migrations | | |
| @nx/workspace | | | package.json / Nx migrations | | |
| TypeScript | | | Angular compatibility | | |
| RxJS | | | Angular compatibility | | |
| zone.js | | | Angular compatibility | | |
| NgRx Store | | | package peer deps | | |
| NgRx Effects | | | package peer deps | | |
| NgRx Entity | | | package peer deps | | |
| NgRx Router Store | | | package peer deps | | |
| jest | | | jest-preset-angular compatibility | | |
| jest-preset-angular | | | package peer deps | | |
| ts-jest | | | package peer deps | | |
| eslint | | | Angular ESLint compatibility | | |
| @typescript-eslint/parser | | | ESLint compatibility | | |
| @typescript-eslint/eslint-plugin | | | ESLint compatibility | | |
| single-spa | | | package peer deps | | |
| single-spa-angular | | | package peer deps | | |
| @barclays/blueprint-angular | | | internal package metadata | | |
| @barclays/olb-* | | | internal package metadata | | |
| @angular-builders/custom-webpack | | | package peer deps | | |
| webpack | | | Angular builder compatibility | | |
| ng-packagr | | | Angular package compatibility | | |
| Node.js | | | local / pipeline / builder image | | |
| npm | | | local / pipeline / builder image | | |

## Dependency grouping

Separate dependency changes into:

### Runtime dependencies

```text
@angular/*
@barclays/*
@ngrx/*
@ngx-translate/*
rxjs
single-spa
single-spa-angular
tslib
zone.js
```

### Development dependencies

```text
@angular-devkit/*
@angular-eslint/*
@angular/cli
@angular/compiler-cli
@nrwl/*
@nx/*
typescript
jest
jest-preset-angular
ts-jest
eslint
webpack
@angular-builders/custom-webpack
ng-packagr
```

## Compatibility decision rules

1. Angular package versions should stay aligned.
2. Angular CLI and Angular Devkit should stay compatible with Angular core.
3. TypeScript must match the supported Angular range.
4. RxJS must match the supported Angular range.
5. Zone.js must match the supported Angular range.
6. NgRx should normally follow the Angular major version.
7. jest-preset-angular must support the target Angular version.
8. single-spa-angular must support the target Angular version.
9. Blueprint Angular must support the target Angular version.
10. Internal @barclays packages must be verified from local package metadata or internal registry output.

## Blocker format

If something blocks migration, report it like this:

```markdown
## Compatibility blocker

Package:
Current version:
Required version:
Conflict:
Evidence:
Possible options:
Recommended option:
Decision needed:
```