Use the angular-nx-enterprise-migration skill.

Use the build-pipeline-specialist agent mindset.

Task:
Review build and pipeline impact for the Angular/Nx migration.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| phase | No | Migration phase to assess pipeline impact for (defaults to current) |

Rules:
- Do not edit files unless explicitly asked.
- Do not change pipeline files without a clear reason.
- Preserve Nexus artefact shape.
- Preserve SIT deployment compatibility.
- Preserve custom builder, packer, SRI and deploy-url behaviour.
- Document old and new values for any pipeline change.

Inspect files:

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

Search for:

```text
node
npm
builder
BUILDER_IMAGE
NODE_
install
build
test
lint
dist
artifact
artefact
nexus
deploy
SIT
sri
custom-builder
packer
ngcc
decorate-angular-cli
Wiz
Veracode
```

Commands to run if appropriate:

```bash
grep -R "BUILDER_IMAGE\|NODE_\|node\|npm\|dist\|artifact\|artefact\|nexus\|deploy\|SIT\|sri\|custom-builder\|packer\|ngcc\|decorate-angular-cli\|Wiz\|Veracode" -n .gitlab-ci.yml Jenkinsfile package.json tools scripts 2>/dev/null || true
node -v
npm -v
```

Output format:

```markdown
# Build and Pipeline Impact Review

## Node and npm

| Area | Current | Target/Required | Evidence | Risk |
|---|---:|---:|---|---|
| Local Node | | | | |
| Local npm | | | | |
| Pipeline Node | | | | |
| Builder image | | | | |

## Build scripts reviewed

| Script | Command | Risk | Notes |
|---|---|---|---|
| postinstall | | | |
| build | | | |
| build:single-spa | | | |
| postbuild | | | |
| test | | | |
| lint | | | |

## Custom build tooling

| Tool | Found | Location | Risk |
|---|---|---|---|
| decorate-angular-cli | | | |
| ngcc | | | |
| custom-builder | | | |
| packer | | | |
| custom-sri | | | |
| webpack config | | | |

## Artefact output review

| Item | Current | After migration | Risk |
|---|---|---|---|
| dist path | | | |
| app folder | | | |
| bundle naming | | | |
| assets path | | | |
| deploy-url | | | |
| SRI output | | | |
| archive output | | | |
| Nexus path | | | |

## Pipeline impact

...

## Required pipeline changes

...

## Risks

...

## Validation commands

```bash
npm run build || true
npm run build:single-spa:home || true
find dist -maxdepth 4 -type f 2>/dev/null | head -100 || true
```

## Recommendation

...
```

Do not apply fixes unless explicitly asked.
