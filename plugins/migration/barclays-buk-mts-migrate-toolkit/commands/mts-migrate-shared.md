# Shared Generation Steps

Common steps executed after any strategy (A, B, or C) completes. The orchestrator calls these steps with all collected data to generate code, tests, issues doc, and produce the final report.

**Called by:** `mts-migrate.md` orchestrator after strategy dispatch completes.

---

## Input (REQUIRED — orchestrator MUST embed all of these)

- `STRATEGY`: A | B | C
- `RESPONSE_CONTRACT`: mts-compat | ods-native
- `TARGET_REPO_PATH`: absolute path to target repo
- `PATTERN_PROFILE`: full structured Pattern Profile block (not a file path)
- `MATCH_REPORT_DATA`: winner API, endpoint, field mappings, data gaps, error handling, converter bugs, notification impacts, derived field impacts, config cascade
- `MTS_SERVICE_DOC_DATA`: gateway, EDO class, service name, request/response structure
- `SERVICE_NAME_METHOD`: the MTS service.method being migrated
- **(Strategy C only)** `CALLING_SERVICE_CLASS`: full source text
- **(Strategy C only)** `CALLING_SERVICE_CLASS_PATH`: file path to calling service class
- **(Strategy C only)** `FEATURE_FLAG_DATA`: flag enum/property contents
- **(Strategy C only)** `FEATURE_FLAG_FILE_PATH`: path to flag file or "N/A"
- **(Strategy C only)** `CONFIG_DATA`: relevant config section
- **(Strategy C only)** `CONFIG_FILE_PATH`: path to config file
- **(Strategy C only)** `BEAN_GAP_LIST`: fields available in API but missing from beans

---

## Step S.1 — Generate Code

Launch the `mts-migrate-code-agent` using the Task tool:

```
Task tool call:
  subagent_type: general-purpose
  model: <AGENT_MODEL>
  prompt: <embed full instructions from agents/mts-migrate-code-agent.md>

  ## EMBEDDED INPUT DATA

  ### STRATEGY
  <STRATEGY value>

  ### RESPONSE_CONTRACT
  <RESPONSE_CONTRACT value>

  ### TARGET_REPO_PATH
  <TARGET_REPO_PATH value>

  ### PATTERN_PROFILE
  <full PATTERN_PROFILE text — NOT a file reference>

  ### MATCH_REPORT_DATA
  <all extracted tables: request params, response fields, query params, data gaps,
   error handling, converter bugs>

  ### MTS_SERVICE_DOC_DATA
  <gateway, EDO class, service name, request/response structure>

  ### (Strategy C only) CALLING_SERVICE_CLASS
  <full source text of the calling service class>

  ### (Strategy C only) FEATURE_FLAG_DATA
  <flag enum/property contents>

  ### (Strategy C only) CONFIG_DATA
  <relevant config section text>

  ### (Strategy C only) BEAN_GAP_LIST
  <list of bean gaps>

  ### (mts-compat only) BUK_EDO_CLASS_DEFINITIONS
  <verbatim field declarations from EDO classes>
```

**STRICT:** All data is embedded directly in the prompt. The agent never reads upstream files.

Wait for completion. Receive `CODE_GENERATION_RESULT`:
- `files_created`: list of absolute paths
- `files_modified`: list of absolute paths with change descriptions
- `warnings`: list of warnings

---

## Step S.1.5 — Compile Verification

After code generation completes, detect the Gradle wrapper and verify the generated code compiles.

**Detect wrapper (cross-platform):**
```bash
python3 -c "
import platform, os, subprocess, sys
plat = platform.system()
repo = '<TARGET_REPO_PATH>'
if plat == 'Windows':
    wrapper = os.path.join(repo, 'gradlew.bat')
else:
    wrapper = os.path.join(repo, 'gradlew')
if os.path.isfile(wrapper):
    print(f'WRAPPER={wrapper}')
else:
    # Fall back to system gradle
    print('WRAPPER=gradle')
" 2>/dev/null || python -c "
import platform, os
plat = platform.system()
repo = '<TARGET_REPO_PATH>'
wrapper = os.path.join(repo, 'gradlew.bat') if plat == 'Windows' else os.path.join(repo, 'gradlew')
print(f'WRAPPER={wrapper}' if os.path.isfile(wrapper) else 'WRAPPER=gradle')
"
```

Then run compilation with the detected wrapper:
```bash
cd <TARGET_REPO_PATH> && <DETECTED_WRAPPER> compileJava 2>&1 | tail -20
```

If compilation fails:
1. Read the error output
2. Fix the compilation errors (missing imports, type mismatches, wrong package declarations)
3. Re-run compilation until it succeeds
4. Log all fixes made as `COMPILE_FIXES` for the issues doc

If Gradle is not available at all (no wrapper and no system `gradle`), skip this step with a warning:
```
WARNING: Gradle not available — skipping compile verification.
Review generated code manually before building.
```

---

## Step S.2 — Generate Tests

Launch the `mts-migrate-test-agent` using the Task tool:

```
Task tool call:
  subagent_type: general-purpose
  model: <AGENT_MODEL>
  prompt: <embed full instructions from agents/mts-migrate-test-agent.md>

  ## EMBEDDED INPUT DATA

  ### STRATEGY
  <STRATEGY value>

  ### RESPONSE_CONTRACT
  <RESPONSE_CONTRACT value>

  ### TARGET_REPO_PATH
  <TARGET_REPO_PATH value>

  ### PATTERN_PROFILE_TESTS
  <Tests section from the Pattern Profile — framework classification + full example test class>

  ### NEW_CLASSES
  <list of classes created by code agent in Step S.1, with full paths>

  ### MATCH_REPORT_FIELDS
  <response field mapping table from match report>

  ### SAMPLE_API_RESPONSE_JSON
  <sample API response JSON structure from match report>
```

Wait for completion. Receive `TEST_GENERATION_RESULT`:
- `files_created`: list of test file paths
- `warnings`: list of warnings

---

## Step S.2.5 — Test Execution

Run generated tests using the wrapper detected in Step S.1.5:

```bash
cd <TARGET_REPO_PATH> && <DETECTED_WRAPPER> test 2>&1 | tail -40
```

If the wrapper was not detected in S.1.5, re-detect using the same Python snippet from S.1.5.

If tests fail:
1. Read the failure output
2. Fix test failures (wrong assertions, missing mocks, import errors)
3. Re-run tests until they pass
4. Log all fixes made as `TEST_FIXES` for the issues doc

If Gradle is not available (no wrapper and no system `gradle`), skip with warning.

---

## Step S.3 — Generate Issues Doc

Launch the `mts-migrate-issues-agent` using the Task tool:

```
Task tool call:
  subagent_type: general-purpose
  model: <AGENT_MODEL>
  prompt: <embed full instructions from agents/mts-migrate-issues-agent.md>

  ## EMBEDDED INPUT DATA

  ### STRATEGY
  <STRATEGY value>

  ### MATCH_REPORT_GAPS
  <data gaps, transformation fields, constraint differences from match report>

  ### CONVERTER_BUGS
  <Boolean.parseBoolean issues, under-mapped converters, missing decode from match report>

  ### NOTIFICATION_IMPACTS
  <notification IDs affected by the migration, or "NONE">

  ### DERIVED_FIELD_IMPACTS
  <endpoint fields that default incorrectly, or "NONE">

  ### CONFIG_CASCADE
  <unconfigured query params and downstream effects, or "NONE">

  ### ERROR_HANDLING
  <HTTP vs MTS status differences from match report>

  ### FILES_CREATED_MODIFIED
  <combined file lists from Step S.1 and Step S.2>

  ### OUTPUT_PATH
  docs/mts/migrate-issues-<ServiceName>-<method>.md
```

Wait for completion. Receive `ISSUES_RESULT`:
- `output_path`: path to the generated issues document
- `summary_stats`: category counts and severities

---

## Step S.4 — Report

After all agents complete:

### S.4a — Clean Up Empty Directories

Remove any empty directories in the generated project to avoid confusion:

```bash
find <TARGET_REPO_PATH>/src -type d -empty -delete
```

### S.4b — List All Files

```
Glob <TARGET_REPO_PATH>/src/main/java/**/*.java  (filter to new/modified)
Glob <TARGET_REPO_PATH>/src/test/java/**/*.java  (filter to new/modified)
Glob docs/mts/migrate-issues-*.md
```

### S.4c — Read Issues Summary

Read the generated issues doc to extract the Summary table stats.

### S.4d — Report to User

```
MTS migration code generation complete:

Strategy: <A: New microservice | B: Existing microservice | C: In-place>
Response contract: <mts-compat | ods-native>
Target: <TARGET_REPO_PATH>
Repo pattern: <Pattern Profile summary — e.g., "CONSTRUCTOR_AUTOWIRED + SPRING_CONVERTER + JUNIT5_MOCKITO + ENUM_FLAG">

New files created:
- <list of new files with paths>

Modified files:
- <list of modified files with description of change>

Summary:
- N new classes, N modified files, N unit tests
- N field mappings (X exact, Y renamed, Z transformed)
- N known migration issues (see migrate-issues doc)
- N fields with no API equivalent (true gaps)

Review the issues doc for manual follow-up items:
  <issues doc path>
```

### S.4e — Offer Next Migration

```
AskUserQuestion:
  question: "Would you like to migrate another MTS service method?"
  header: "Next"
  options:
    - label: "Yes"
      description: "Run /mts-migrate for another service method"
    - label: "No, I'm done"
      description: "End the migration session"
```
