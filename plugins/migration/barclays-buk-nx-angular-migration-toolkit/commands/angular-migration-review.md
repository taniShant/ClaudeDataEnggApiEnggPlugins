Use the angular-nx-enterprise-migration skill.

Use the migration-verification-reviewer agent mindset.

Task:
Review the current Angular/Nx migration changes.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| branch | No | Branch to diff against (defaults to main) |

Rules:
- Do not modify files unless explicitly asked.
- Do not run new migrations.
- Do not update dependencies.
- Do not use --force.
- Do not use --legacy-peer-deps.
- Be strict.
- Flag unexplained dependency jumps.
- Flag unrelated file churn.
- Flag removed custom scripts.
- Flag removed deploy-url/base-href handling.
- Flag removed Single-SPA lifecycle logic.
- Flag Blueprint compatibility gaps.
- Flag pipeline impact gaps.
- Flag missing validation evidence.

Steps:
1. Read CLAUDE.md.
2. Read `.claude/skills/angular-nx-enterprise-migration/SKILL.md`.
3. Read all reference files under `.claude/skills/angular-nx-enterprise-migration/references/`.
4. Check git status:

```bash
git status
```

5. Review full diff:

```bash
git diff
```

6. Review package changes:

```bash
git diff -- package.json package-lock.json
```

7. Review Angular/Nx config changes:

```bash
git diff -- angular.json nx.json workspace.json project.json
```

8. Review app/project config changes:

```bash
git diff -- "apps/**/project.json" "libs/**/project.json"
```

9. Review Single-SPA-related changes:

```bash
git diff -- "*single-spa*" "src/main.single-spa.ts" "src/main.ts"
```

10. Review build and pipeline related changes:

```bash
git diff -- .gitlab-ci.yml Jenkinsfile package.json "tools/**" "scripts/**" "*webpack*.js"
```

11. If validation output exists in the conversation or generated logs, review it.
12. If no validation output exists, state this clearly.

Review checklist:
- package.json versions are aligned
- package-lock.json is consistent
- no permanent --force / --legacy-peer-deps workaround
- Angular package versions are aligned
- Nx package versions are aligned
- TypeScript version is compatible with target Angular
- RxJS version is compatible
- Zone.js version is compatible
- NgRx version is compatible
- jest-preset-angular version is compatible
- Single-SPA lifecycle is preserved
- single-spa-angular version is compatible
- Blueprint package compatibility is checked
- custom webpack remains valid
- custom builder remains valid
- packer/SRI remains valid
- deploy-url/base-href remains valid
- output folder shape is reviewed
- pipeline impact is documented
- Nexus artefact shape is reviewed
- SIT deployment assumptions are reviewed

Output format:

```markdown
# Angular Migration Review

## Review result

Status: PASS / PASS WITH RISKS / FAIL

## Summary

...

## Files reviewed

```text
...
```

## Dependency review

| Area | Status | Notes |
|---|---|---|
| Angular packages | | |
| Angular CLI / Devkit | | |
| Nx packages | | |
| TypeScript | | |
| RxJS | | |
| Zone.js | | |
| NgRx | | |
| Jest | | |
| Single-SPA | | |
| Blueprint | | |
| Barclays internal packages | | |

## Config review

| Area | Status | Notes |
|---|---|---|
| angular.json | | |
| nx.json | | |
| project.json files | | |
| tsconfig files | | |
| jest config | | |
| eslint config | | |
| webpack config | | |

## Single-SPA review

| Check | Status | Notes |
|---|---|---|
| bootstrap | | |
| mount | | |
| unmount | | |
| props | | |
| deploy-url | | |
| asset loading | | |
| repeated mount/unmount risk | | |

## Blueprint review

| Check | Status | Notes |
|---|---|---|
| package compatibility | | |
| module imports | | |
| templates | | |
| styles | | |
| accessibility-sensitive areas | | |

## Build and pipeline review

| Check | Status | Notes |
|---|---|---|
| build scripts | | |
| custom builder | | |
| packer | | |
| SRI | | |
| dist output | | |
| pipeline files | | |
| Nexus artefact path | | |
| SIT impact | | |

## Validation evidence

| Command | Evidence found | Status | Notes |
|---|---|---|---|
| npm install | | | |
| lint | | | |
| tests | | | |
| build | | | |
| Single-SPA build | | | |

## Blocking issues

- ...

## Non-blocking issues

- ...

## Required fixes before merge

- ...

## Suggested follow-up checks

- ...

## PR-ready review comment

...
```

Do not apply fixes unless explicitly asked.
