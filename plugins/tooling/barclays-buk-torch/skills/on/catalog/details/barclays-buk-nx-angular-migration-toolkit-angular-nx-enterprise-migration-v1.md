# barclays-buk-nx-angular-migration-toolkit-angular-nx-enterprise-migration-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-nx-angular-migration-toolkit-angular-nx-enterprise-migration-v1` |
| Plugin name | `barclays-buk-nx-angular-migration-toolkit` |
| Component type | skill-model-invocable |
| Owner | Sayan Sengupta |
| Action scope | local-modification |
| Invocation mode | model-invocable |
| Installation / release | /plugin install barclays-buk-nx-angular-migration-toolkit@barclays-cio-buk |
| Native command | `/barclays-buk-nx-angular-migration-toolkit:angular-nx-enterprise-migration` |
| Skill name | `angular-nx-enterprise-migration` |

## Description

Use this skill to plan and execute a staged Angular/Nx enterprise migration from Angular 12 to the latest compatible version while preserving Single-SPA, Blueprint Angular, custom build packaging, Nexus artefacts and CI/CD behaviour.

## When to use

Use when migrating an Nx Angular monorepo (Angular 12 or later) to a newer Angular version — handles one-major-version-at-a-time staged migration with validation at each step, preserving Single-SPA entry points, Blueprint Angular components, custom webpack/builder configuration, Nexus artefact publishing, and Jenkins/GitLab CI pipelines; NOT for non-Nx Angular projects, greenfield setups, or partial manual upgrades outside the Nx workspace.

## Inputs

- REPO_PATH (required, positional): path to the Nx Angular monorepo root; must contain `nx.json` and `package.json`
- --current-version VERSION (optional): current Angular major version (auto-detected from `package.json` if omitted)
- --target-version VERSION (optional, default: latest stable): target Angular major version; migration executes one major version per phase until this target is reached

## Preconditions

- Plugin `barclays-buk-nx-angular-migration-toolkit` is installed with all sub-agents available
- Nx Angular workspace present (`nx.json`, `package.json`, at least one Angular app or library in the workspace)
- Node.js and npm or yarn are available on the PATH and match the workspace engine requirements
- CI/CD pipeline configuration (Jenkins or GitLab) is readable and writable for pipeline impact assessment
- Phase 0 inventory must be completed (current dependency matrix, migration ladder, risk register, and rollback plan produced) before any file modifications begin

## Expected outputs

- Phase 0 inventory artefact: current dependency matrix, architecture summary, migration ladder (one phase per major Angular version), risk register, and rollback plan
- Per-phase migration execution, one major Angular version at a time:
  - Updated `package.json` and lock file with Angular, Nx, and peer dependency versions for the target major
  - Angular and Nx schematics applied via official tooling (`ng update`, `nx migrate`)
  - Blueprint Angular package versions updated to compatible releases
  - Single-SPA Angular lifecycle entry points preserved and verified
  - Custom webpack/builder/packer configuration updated for the target major
  - SRI generation scripts verified against new build output shape
  - Nexus artefact publishing confirmed compatible with updated build output
  - Jenkins or GitLab pipeline configuration reviewed and updated where impacted
- Per-phase migration report (phase summary, files changed, dependency changes, validation checklist, risks, rollback instructions)
- PR per major version with commit history scoped to that phase

## Exclusions

- Does NOT jump multiple major Angular versions in a single phase — migration is strictly one major version at a time
- Does NOT rewrite the monorepo layout or migrate to standalone Angular components unless explicitly required by the target version
- Does NOT remove Single-SPA, Blueprint packages, or custom packaging logic without a verified replacement
- Does NOT guess internal `@barclays` package versions — version resolution must be confirmed before proceeding
- Does NOT permanently apply `--force` or `--legacy-peer-deps` as peer dependency workarounds
- Does NOT handle non-Nx Angular projects or plain Angular CLI workspaces

## Verification

After each phase, confirm that `npm install` completes without unresolved peer dependency conflicts, the test suite (unit, integration, and e2e if applicable) passes, the production build completes and the output shape matches the prior phase, Single-SPA lifecycle hooks remain intact, Blueprint Angular components render without errors, and the CI/CD pipeline configuration reflects any required changes. The per-phase migration report must show all validation checklist items passing before the next phase begins.
