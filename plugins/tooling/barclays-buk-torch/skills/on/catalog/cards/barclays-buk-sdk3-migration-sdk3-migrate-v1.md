# barclays-buk-sdk3-migration-sdk3-migrate-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-sdk3-migration-sdk3-migrate-v1` |
| Plugin name | `barclays-buk-sdk3-migration` |
| Component type | skill-user-only |
| Owner | Barclays AI |
| Action scope | externally-consequential |
| Invocation mode | user-only |
| Installation / release | /plugin install barclays-buk-sdk3-migration@barclays-cio-buk |
| Native command | `/barclays-buk-sdk3-migration:sdk3-migrate` |
| Skill name | `sdk3-migrate` |

## Description

Run SDK2 to SDK3 migration workflow with validation and phased execution

## When to use

Use when migrating a Java project from SDK2 to SDK3, requiring an orchestrated multi-phase workflow that handles build config changes, package migration, REST client updates, JUnit 4→5 test migration, integration test fixes, checkstyle remediation, and optional RAML-to-OAS conversion — this is NOT for greenfield SDK3 projects or partial/manual migration steps.

## Inputs

- PROJECT_PATH (required, positional): path to the project root (use `.` for cwd or an absolute path); must contain `build.gradle` or `pom.xml` and `src/main/java`
- --jira JIRA_ID (required): JIRA ticket ID matching `^[A-Z]+-[0-9]+$`
- --group GROUP (optional, default: `capl`): library group name; loads `barclays_internal_libraries_{group}.md` for dependency rules
- --template TEXT (optional): custom instructions passed to the analysis agent
- --full-automation (optional flag): enables enforced non-interactive mode with automation hooks; blocks all user prompts
- --spring-conventions (optional flag): enables Phase 0.5 to apply Spring best practices (e.g., removing `@Autowired` field injection)
- --skip-gitlab-ci (optional flag): skips GitLab CI pipeline generation
- --jira-token TOKEN (optional): JIRA auth token; falls back to `JIRA_AUTH_TOKEN` environment variable
- --gitlab-token TOKEN (optional): GitLab auth token; falls back to `GITLAB_TOKEN` environment variable

## Preconditions

- Project directory exists and contains `build.gradle` or `pom.xml` plus a `src/main/java` source tree
- The project is currently on SDK2 and compilable (`compileJava compileTestJava` and `test` must pass before migration begins — verified in Phase 0.5 compile step)
- Git is initialized in the project and the working tree is clean enough to create a feature branch (`feature/sdk3-migration-{JIRA_ID}`)
- Gradle wrapper (`gradlew`/`gradlew.bat`) or Maven (`mvn`) is available on the PATH
- If using `--jira-token` or `--gitlab-token`, valid tokens are provided (or the corresponding environment variables `JIRA_AUTH_TOKEN` / `GITLAB_TOKEN` are set)
- The BUK plugin `barclays-buk-sdk3-migration` is installed with all sub-agents available (`sdk3-migration-agent`, `spring-conventions-agent`, `junit-migration-agent`, `test-fix-agent`, `auto-decision-agent`, etc.)

## Expected outputs

- A fully migrated SDK3 codebase on a dedicated feature branch `feature/sdk3-migration-{JIRA_ID}`, with granular per-phase git commits (each prefixed with the JIRA ID)
- Updated `build.gradle` / `pom.xml` with SDK3 dependencies and BOM version cleanup
- Migrated Java packages and REST client code
- JUnit 4 tests converted to JUnit 5 (if applicable)
- Integration tests fixed (if present)
- Checkstyle violations resolved (errors only, if checkstyle is configured)
- Optional: Spring conventions applied (`@Autowired` removal, constructor injection)
- Optional: RAML specs converted to OAS under `src/main/resources/oas/`
- State file at `{PROJECT_PATH}/.claude/migration-state.json` tracking all phase statuses and analysis results
- Migration log at `{PROJECT_PATH}/logs/migration.log` with timestamped entries for every phase start/completion
- `.gitignore` updated to exclude `.claude/` and `scripts/` directories
- Branch pushed to remote in Phase 8 (finalization phase)

## Exclusions

- Does NOT perform greenfield SDK3 project setup — only migrates existing SDK2 projects
- Does NOT modify Java source files directly from the orchestrator; all code changes are delegated to specialized sub-agents
- Does NOT add migration phases or steps beyond those explicitly defined (Phases 0, 0.5, 1+2+3, 2.4, 2.5, 4, 5, 7, 7.5, 8, RAML-OAS)
- Does NOT fix checkstyle warnings — only checkstyle errors are addressed in Phase 7.5
- Does NOT run Spring conventions unless the `--spring-conventions` flag is explicitly provided
- Does NOT generate GitLab CI configuration if `--skip-gitlab-ci` flag is set
- Does NOT handle non-Java projects or projects without a standard `src/main/java` layout
- Does NOT create or manage JIRA tickets — it only references an existing JIRA ID for branch naming and commit messages

## Verification

The engineer should confirm that the feature branch `feature/sdk3-migration-{JIRA_ID}` has been pushed to the remote (Phase 8), that `./gradlew test` and `./gradlew integrationTest` pass cleanly on the migrated codebase, and that `{PROJECT_PATH}/.claude/migration-state.json` shows all expected phases with status `completed` (or `skipped` for inapplicable phases). The migration log at `{PROJECT_PATH}/logs/migration.log` should end with a finalization entry and contain no unresolved error entries.
