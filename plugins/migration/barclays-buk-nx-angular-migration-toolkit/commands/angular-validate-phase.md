Use the angular-nx-enterprise-migration skill.

Task:
Validate the current Angular migration phase.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| phase | No | Phase identifier to validate (e.g. "12-to-13", defaults to current branch state) |

Rules:
- Do not edit files unless explicitly asked.
- Do not run migrations.
- Do not update dependencies.
- Run validation commands that exist.
- If a command fails, capture the failure and diagnose it.
- Do not hide failing commands.
- Do not mark the phase complete unless build and Single-SPA output are reviewed.

Steps:
1. Read package.json scripts.
2. Identify available validation commands.
3. Run install validation.
4. Run lint validation if available.
5. Run unit test validation if available.
6. Run affected test validation if available.
7. Run build validation if available.
8. Run Single-SPA build validation if available.
9. Inspect dist output.
10. Produce validation report.

Commands:

```bash
npm install
npm run lint --if-present
npm run test -- --watch=false || true
npx nx affected:test || true
npx nx affected:build || true
npm run build --if-present
npm run build:single-spa:home --if-present
find dist -maxdepth 4 -type f 2>/dev/null | head -100 || true
git status
```

If `.claude/skills/angular-nx-enterprise-migration/scripts/validate-migration-phase.sh` exists, run:

```bash
.claude/skills/angular-nx-enterprise-migration/scripts/validate-migration-phase.sh
```

Output format:

```markdown
# Migration Phase Validation Report

## Commands executed

```bash
...
```

## Validation result

| Check | Status | Notes |
|---|---|---|
| npm install | | |
| lint | | |
| unit tests | | |
| affected tests | | |
| affected build | | |
| app build | | |
| Single-SPA build | | |
| dist output | | |
| git status | | |

## Build output

```text
...
```

## Dist output summary

```text
...
```

## Failures

| Command | Failure | Likely cause | Suggested fix |
|---|---|---|---|
| | | | |

## Risks

...

## Phase completion recommendation

Status: COMPLETE / COMPLETE WITH RISKS / NOT COMPLETE

Reason:
...
```

Do not apply fixes unless explicitly asked.