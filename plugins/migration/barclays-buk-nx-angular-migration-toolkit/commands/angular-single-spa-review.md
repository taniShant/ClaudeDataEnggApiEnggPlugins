Use the angular-nx-enterprise-migration skill.

Use the single-spa-migration-specialist-agent mindset.

Task:
Review Single-SPA Angular compatibility for the current migration phase.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| phase | No | Migration phase to review Single-SPA compatibility for (defaults to current) |

Rules:
- Do not edit files unless explicitly asked.
- Do not run migrations.
- Preserve bootstrap, mount and unmount.
- Preserve props handling.
- Preserve deploy-url and asset loading.
- Do not change root-config assumptions without documenting impact.

Inspect files:

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
package.json
angular.json
project.json
```

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

Commands to run if appropriate:

```bash
grep -R "singleSpaAngular\|getSingleSpaExtraProviders\|registerApplication\|constructApplications\|constructRoutes\|constructLayoutEngine\|APP_BASE_HREF" -n src apps libs . 2>/dev/null || true
npm run build:single-spa:home || true
npm run serve:single-spa:home || true
```

Output format:

```markdown
# Single-SPA Migration Review

## Current Single-SPA package versions

| Package | Version | Evidence |
|---|---:|---|
| single-spa | | |
| single-spa-angular | | |
| single-spa-layout | | |
| @angular/elements | | |
| zone.js | | |

## Files inspected

```text
...
```

## Lifecycle review

| Lifecycle area | Status | Notes |
|---|---|---|
| bootstrap | | |
| mount | | |
| unmount | | |
| props | | |
| router integration | | |
| zone handling | | |
| base href | | |
| deploy-url | | |
| asset loading | | |
| style cleanup | | |

## API usage found

| API / pattern | Found | Location | Risk |
|---|---|---|---|
| singleSpaAngular | | | |
| getSingleSpaExtraProviders | | | |
| registerApplication | | | |
| constructApplications | | | |
| constructRoutes | | | |
| constructLayoutEngine | | | |

## Required changes

...

## Risks

...

## Validation commands

```bash
...
```

## Recommendation

...
```

Do not apply fixes unless explicitly asked.