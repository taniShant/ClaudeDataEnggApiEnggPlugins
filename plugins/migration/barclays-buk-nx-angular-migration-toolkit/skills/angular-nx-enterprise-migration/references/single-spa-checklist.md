# Single-SPA Checklist

Use this checklist for every migration phase.

The goal is to preserve Single-SPA micro-frontend behaviour.

## Files to inspect

```text
src/main.single-spa.ts
src/main.ts
src/app/app.module.ts
root-config files
registerApplications files
layout engine files
webpack config
extra-webpack.config.js
feature-webpack.config.js
package.json scripts
angular.json
project.json
```

## Package dependencies to inspect

```text
single-spa
single-spa-angular
single-spa-layout
@angular/elements
zone.js
rxjs
```

## Lifecycle checks

Verify these lifecycle areas:

- bootstrap
- mount
- unmount
- props handling
- Angular zone handling
- router integration
- base href
- deploy URL
- public path
- DOM cleanup
- style cleanup
- repeated mount/unmount behaviour

## Code patterns to inspect

Search for:

```text
singleSpaAngular
getSingleSpaExtraProviders
bootstrapFunction
template
Router
NavigationStart
APP_BASE_HREF
registerApplication
constructApplications
constructRoutes
constructLayoutEngine
start()
mountRootParcel
```

## Migration risks

Check for:

- deprecated Single-SPA APIs
- single-spa-angular major version mismatch
- changed lifecycle signature
- removed helper functions
- changed root-config registration format
- deploy-url asset loading breakage
- styles not removed on unmount
- duplicated DOM nodes on remount
- broken Angular routing under Single-SPA root container

## Local validation

Run whichever script exists:

```bash
npm run serve:single-spa:home || true
npm run build:single-spa:home || true
npm run serve-single-spa || true
```

## Production validation

Confirm:

- production Single-SPA build succeeds
- deploy-url is correct
- dist output path is unchanged or documented
- assets resolve from expected path
- generated bundles match deployment assumptions
- custom builder still runs
- SRI still runs if expected

## Required output

Produce this section in every phase report:

```markdown
## Single-SPA validation

| Check | Status | Notes |
|---|---|---|
| bootstrap preserved | | |
| mount preserved | | |
| unmount preserved | | |
| props preserved | | |
| deploy-url preserved | | |
| asset loading preserved | | |
| style cleanup reviewed | | |
| local serve checked | | |
| production build checked | | |

## Single-SPA risks

...
```