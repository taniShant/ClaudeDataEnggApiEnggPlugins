# barclays-buk-nx-angular-migration-toolkit

Handles Angular major-version migrations in Nx monorepos, especially Angular 12+ upgrades with enterprise constraints: Single-SPA Angular, Blueprint Angular components, custom webpack packaging, and CI/CD pipeline preservation.

## Use this plugin when

- You have an Nx monorepo with Angular applications
- You need to migrate from Angular 12 to a newer Angular version
- Your applications use Single-SPA Angular (micro-frontends)
- Your applications use Blueprint Angular components
- You have custom webpack or builder scripts
- Your deployment pipeline uses Jenkins or GitLab
- You publish artefacts to Nexus

## What the plugin does

This plugin provides a **staged, incremental, and safe** migration strategy:

1. **Phase 0 (Inventory)**: Understand current architecture, dependencies, and risks before touching code
2. **Per-phase execution**: Migrate one Angular major version at a time
3. **Validation**: After each phase, verify build output, tests, and deployment assumptions
4. **Rollback readiness**: Every phase includes a documented rollback plan

### Core agents

| Agent | Purpose |
|---|---|
| `angular-migration-architect-agent` | Plan the migration ladder from current to target version, one major version per phase |
| `dependency-compatibility-auditor-agent` | Audit package.json and package-lock.json for peer dependency conflicts and safe upgrade paths |
| `blueprint-angular-specialist-agent` | Identify Blueprint Angular compatibility blockers and UI/accessibility areas at risk |
| `single-spa-migration-specialist-agent` | Preserve Single-SPA lifecycle, bootstrap, mount, unmount, and root-config integration |
| `migration-verification-reviewer-agent` | Review changes after migration, verify validation steps, and produce PR summary |

### Core skill

**angular-nx-enterprise-migration** — Controlled enterprise migration methodology covering:
- Staged versioning (one major per phase)
- Single-SPA preservation
- Blueprint Angular preservation
- Custom build logic preservation
- Nexus artefact publishing
- CI/CD pipeline assumptions

## How to use

### Step 1: Plan the migration

```
Use the angular-migration-architect-agent

Your inputs:
- Access to the Nx repository
- Current Angular version
- Target Angular version

Output:
- Migration ladder (stepping stones)
- Risk register
- Phase 1 implementation plan
```

### Step 2: Audit dependencies

```
Use the dependency-compatibility-auditor-agent

Your inputs:
- package.json
- package-lock.json
- Target Angular version for this phase

Output:
- Current and target dependency matrix
- Peer dependency conflicts
- Migration commands with rationale
```

### Step 3: Check Blueprint Angular

```
Use the blueprint-angular-specialist-agent

Your inputs:
- package.json and package-lock.json
- Component templates using Blueprint
- SCSS/CSS files

Output:
- Blueprint compatibility blockers
- UI areas at risk
- Accessibility re-validation checklist
```

### Step 4: Check Single-SPA

```
Use the single-spa-migration-specialist-agent

Your inputs:
- main.single-spa.ts
- Root app bootstrap code
- Root-config registration

Output:
- Single-SPA lifecycle risks
- Required code changes
- Validation commands
```

### Step 5: Execute one phase

```
/angular-migrate-one-major

Executes:
1. npm install / yarn install (with new dependencies)
2. ng update @angular/core @angular/cli (if needed)
3. nx migrate latest (if needed)
4. Run build and tests
5. Commits changes with migration summary
```

### Step 6: Verify the phase

```
Use the migration-verification-reviewer-agent

Your inputs:
- Git diff of committed migration changes
- Build and test output (if available)
- Original plan from angular-migration-architect-agent

Output:
- Pass/fail verdict
- PR-ready summary
- Risks identified
- Rollback readiness
```

### Step 7: Repeat for next phase

Go back to Step 2, selecting the next major version in the migration ladder.

## Key principles

- **Staged, not big-bang**: One Angular major version per phase
- **Evidence-based**: Every phase validated before proceeding
- **Rollback-ready**: Rollback plan documented upfront
- **Transparent about unknowns**: Placeholder internal packages flagged explicitly
- **Enterprise-first**: Preserves Single-SPA, Blueprint, custom builds, CI/CD assumptions

## Commands

| Command | Purpose |
|---|---|
| `/angular-phase0` | Run Phase 0 (inventory, planning, risk register) |
| `/angular-dependency-audit` | Audit current dependency compatibility |
| `/angular-blueprint-review` | Review Blueprint Angular compatibility |
| `/angular-single-spa-review` | Review Single-SPA lifecycle preservation |
| `/angular-migrate-one-major` | Execute one major version migration |
| `/angular-validate-phase` | Validate current phase (build, tests, output shape) |
| `/angular-migration-review` | Review migration changes against plan |
| `/angular-pipeline-review` | Review CI/CD pipeline impact |
| `/angular-pr-summary` | Produce PR-ready summary for a completed phase |

## Flags / Known limitations

- **Placeholder**: Internal @barclays package versions — requires local inspection or CI registry lookup
- **Manual**: Single-SPA lifecycle testing — automated checks validate bootstrap/mount, but full repeated-mount/unmount testing is manual
- **Manual**: UI and accessibility smoke tests — visual validation required after major Angular versions
- **Manual**: Blueprint Angular version compatibility — requires Blueprint team coordination if new major versions needed
- **Caution**: Peer dependency conflicts — may require careful version negotiation; `--force` and `--legacy-peer-deps` are temporary workarounds only

## Requirements

- Nx 10+
- Angular 12+ (for this migration; starting point)
- Node.js 14+ (check Angular version matrix)
- npm or yarn with access to internal Barclays registry

## Plugin dependencies

- `barclays-buk-standards` (for shared security standards)

## Owner

Sayan Sengupta  
Review cadence: On every major Angular release (April and October)

## See also

- [Angular upgrade guide](https://angular.io/guide/upgrade-optimization)
- [Nx migration guide](https://nx.dev/docs/reference/migration/overview)
- [Single-SPA angular docs](https://single-spa.js.org/docs/ecosystem-angular)
