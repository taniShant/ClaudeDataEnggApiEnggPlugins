---
name: angular-nx-enterprise-migration
description: Use this skill to plan and execute a staged Angular/Nx enterprise migration from Angular 12 to the latest compatible version while preserving Single-SPA, Blueprint Angular, custom build packaging, Nexus artefacts and CI/CD behaviour.
owner: Sayan Sengupta
review-trigger: On every major Angular release (April and October)
user-invocable: false
---

# Angular Nx Enterprise Migration Skill

Use this skill for Angular/Nx migration work where the repository uses:

- Angular
- Nx monorepo
- Single-SPA Angular
- Blueprint Angular components
- custom webpack
- custom builder or packer scripts
- SRI generation
- Jenkins or GitLab pipeline
- Nexus artefact publishing
- SIT deployment

## Quick Start

To plan an Angular migration in an Nx monorepo:

1. **Phase 0 (Planning)**: Use the `angular-migration-architect-agent` to plan the migration
   - Agent reads the codebase and produces a migration ladder
   - Input: Access to Nx repo, current Angular version, target Angular version
   - Output: Step-by-step phases (one major version per phase), risk register, rollback plan
   - Command: `/angular-phase0` or invoke the agent directly

2. **Per-phase execution**: Repeat for each major version step
   - Run `/angular-dependency-audit` to check peer dependencies
   - Run `/angular-blueprint-review` if using Blueprint Angular
   - Run `/angular-single-spa-review` if using Single-SPA
   - Run `/angular-migrate-one-major` to execute the phase
   - Run `/angular-validate-phase` to verify the phase succeeded

3. **Verification**: Use `migration-verification-reviewer-agent` to review changes
   - Input: Git diff of committed changes
   - Output: PR-ready summary with pass/fail verdict and risks
   - Command: `/angular-migration-review`

**Example workflow for Angular 12 → 15 migration:**

```
Phase 0 (inventory):  /angular-phase0
↓
Phase 1 (12 → 13):    /angular-migrate-one-major
                      /angular-validate-phase
                      /angular-migration-review
↓
Phase 2 (13 → 14):    /angular-migrate-one-major
                      /angular-validate-phase
                      /angular-migration-review
↓
Phase 3 (14 → 15):    /angular-migrate-one-major
                      /angular-validate-phase
                      /angular-migration-review
```

## Core principle

This is a controlled enterprise migration, not a rewrite.

The migration must be performed one Angular major version at a time.

## Mandatory first step

Always start with Phase 0 inventory.

Do not edit files until Phase 0 has produced:

1. Current dependency matrix.
2. Current architecture summary.
3. Migration ladder.
4. Risk register.
5. Phase 1 implementation plan.
6. Exact commands proposed.
7. Files expected to change.
8. Rollback plan.

## Required references

When working, read these references from this skill:

- references/phase-0-inventory.md
- references/migration-phases.md
- references/compatibility-matrix.md
- references/validation-checklist.md
- references/single-spa-checklist.md
- references/blueprint-checklist.md
- references/pipeline-checklist.md
- references/pr-summary-template.md

## Execution rules

1. Run only one migration phase at a time.
2. Prefer Angular 12 to 13 as the first implementation phase.
3. Apply Nx migrations using Nx tooling.
4. Apply Angular migrations using Angular tooling.
5. Commit or summarise after each phase.
6. Run validation after each phase.
7. If blocked, produce an evidence-based blocker report.

## Do not do these

- Do not jump Angular 12 directly to latest.
- Do not rewrite the repo layout.
- Do not migrate to standalone components unless required.
- Do not remove Single-SPA.
- Do not remove Blueprint packages.
- Do not remove custom packaging logic without replacement.
- Do not permanently rely on --force.
- Do not permanently rely on --legacy-peer-deps.
- Do not guess internal @barclays package versions.
- Do not change pipeline configuration without explaining why.

## Required output format

For every phase, produce:

```markdown
# Angular Migration Phase Report

## Phase

Angular X to Angular Y

## Summary

...

## Files inspected

...

## Files changed

...

## Dependency changes

...

## Code changes

...

## Validation

- [ ] npm install
- [ ] tests
- [ ] build
- [ ] single-spa build
- [ ] artefact output verified
- [ ] pipeline impact reviewed

## Risks

...

## Rollback

...
```

## Stop conditions

Stop and ask for human decision only if:

- an internal @barclays package has unclear compatibility
- a peer dependency conflict cannot be resolved cleanly
- build output shape changes
- Single-SPA lifecycle cannot be verified
- Blueprint compatibility is unclear
- pipeline artefact publication would be impacted

## Source Attribution

> **Owner:** Sayan Sengupta  
> **Review trigger:** On every major Angular release (April and October)  
> **Status:** Active — maintained for BUK Angular/Nx projects

This skill consolidates enterprise Angular migration best practices from:

- Angular official upgrade guides (https://angular.io/guide/upgrade-optimization)
- Nx migration documentation (https://nx.dev/docs/reference/migration/overview)
- Barclays BUK Angular/Nx projects: deployment constraints, Single-SPA conventions, Blueprint Angular integration patterns
- Enterprise migration case studies: staged versioning, peer dependency management, custom build preservation

## Agent Self-Check

Before performing any migration phase, the agent using this skill must verify:

- [ ] Phase 0 inventory has been completed with no blockers
- [ ] Current dependency matrix documented and accessible
- [ ] Migration ladder validated (one major version per phase)
- [ ] Single-SPA entry points identified and lifecycle understood
- [ ] Blueprint Angular usage mapped and compatibility checked
- [ ] Custom webpack/builder configuration documented
- [ ] Nexus artefact publishing assumptions confirmed with pipeline team
- [ ] CI/CD pipeline impact assessed (Jenkins/GitLab config reviewed)
- [ ] Package-lock.json integrity preserved (no `--force` or `--legacy-peer-deps` as permanent workarounds)
- [ ] Rollback plan documented before starting implementation
- [ ] Internal @barclays package versions obtained (not guessed)
- [ ] Each phase completed and validated before proceeding to next
- [ ] Build output shape verified after each phase
- [ ] Test suite passes after each phase (unit, integration, e2e if applicable)