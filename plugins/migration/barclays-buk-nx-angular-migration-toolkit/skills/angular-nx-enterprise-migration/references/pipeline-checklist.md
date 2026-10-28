# Pipeline Checklist

Use this checklist for every migration phase.

The goal is to preserve Jenkins/GitLab build behaviour, Nexus artefact publishing, and SIT deployment compatibility.

## Files to inspect

```text
.gitlab-ci.yml
Jenkinsfile
package.json
package-lock.json
.nvmrc
.npmrc
tools/**
scripts/**
webpack.config.*
extra-webpack.config.*
feature-webpack.config.*
angular.json
project.json
nx.json
```

## Pipeline areas to inspect

Check:

- Node version
- npm version
- builder image
- install command
- build command
- test command
- lint command
- cache paths
- dist paths
- artefact paths
- Nexus upload logic
- deployment path
- environment variables
- scan configuration
- Wiz config if present
- Veracode config if present
- branch naming assumptions
- snapshot/release versioning assumptions

## Node version checks

Document:

```markdown
## Node version impact

Current local Node:
Current pipeline Node:
Target Node:
Builder image:
Reason for change:
Risk:
```

## Build script checks

Inspect package.json scripts for:

```text
postinstall
ngcc
decorate-angular-cli
start
serve
serve-single-spa
build
build-single-spa
postbuild
custom-builder
custom-sri
packer
publish
```

## Custom output checks

Verify:

- dist directory location
- app subfolder name
- generated bundle names
- static assets
- deploy URL
- base href
- SRI output
- packer output
- generated archive if any
- Nexus upload path
- version naming

## Pipeline change rules

Before changing pipeline files:

1. Document old value.
2. Document new value.
3. Explain why the change is required.
4. Confirm local build output still matches pipeline expectations.
5. Confirm artefact publishing path is unchanged or intentionally documented.
6. Confirm rollback path.

## Pipeline risk areas

Watch for:

- old Node version incompatible with newer Angular
- npm version changing package-lock format
- builder image missing required tooling
- changed dist output path
- changed Angular output hashing
- changed deploy-url behaviour
- changed SRI behaviour
- changed Nexus artefact structure
- broken SIT deployment assumptions
- scan config no longer pointing to correct folder

## Required output

Produce this section in every phase report:

```markdown
## Pipeline validation

| Check | Status | Notes |
|---|---|---|
| Node version reviewed | | |
| npm version reviewed | | |
| builder image reviewed | | |
| build command reviewed | | |
| test command reviewed | | |
| artefact path reviewed | | |
| Nexus output reviewed | | |
| SIT deployment impact reviewed | | |
| scan config reviewed | | |

## Pipeline risks

...

## Pipeline changes required

...
```
