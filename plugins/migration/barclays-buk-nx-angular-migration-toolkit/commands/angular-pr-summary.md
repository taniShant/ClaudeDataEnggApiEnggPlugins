Use the angular-nx-enterprise-migration skill.

Task:
Generate a PR-ready summary for the current Angular migration phase.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| branch | No | Branch to generate PR summary for (defaults to current branch) |

Rules:
- Do not edit files.
- Do not run migrations.
- Review git diff before writing the summary.
- Mention only changes supported by the diff or validation evidence.
- Clearly separate completed validation from missing validation.
- Highlight risks honestly.

Steps:
1. Read git status.
2. Read git diff.
3. Inspect package changes.
4. Inspect Angular/Nx config changes.
5. Inspect Single-SPA changes.
6. Inspect Blueprint-related changes.
7. Inspect build/pipeline changes.
8. Summarise validation evidence.
9. Produce a concise PR-ready summary.

Commands:

```bash
git status
git diff --stat
git diff -- package.json package-lock.json
git diff -- angular.json nx.json workspace.json project.json
git diff
```

Output format:

```markdown
# PR Summary

## Title

Angular migration: Angular X to Angular Y

## Summary

This PR migrates the application from Angular X to Angular Y as part of the staged Angular/Nx enterprise migration.

## Scope

- ...
- ...

## Files changed

```text
...
```

## Dependency changes

| Package | Before | After | Reason |
|---|---:|---:|---|
| @angular/core | | | |
| @angular/cli | | | |
| nx / @nrwl / @nx | | | |
| typescript | | | |
| rxjs | | | |
| zone.js | | | |
| single-spa-angular | | | |
| @barclays/blueprint-angular | | | |

## Code changes

- ...

## Config changes

- ...

## Pipeline changes

If none:

```text
No pipeline changes were required in this phase.
```

If present:

| Item | Before | After | Reason |
|---|---|---|---|
| Node version | | | |
| Builder image | | | |
| Build command | | | |
| Artefact path | | | |
| Scan path | | | |

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

```text
...
```

## Known issues

- ...

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| | | |

## Rollback

1. Revert this PR.
2. Restore package.json and package-lock.json from previous phase.
3. Restore Angular/Nx config from previous phase.
4. Run npm install.
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
```
