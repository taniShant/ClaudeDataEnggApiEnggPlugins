---
description: Generate MTS service documentation for any BUK Spring Boot codebase
argument-hint: [SERVICE_METHOD_NAME or PROJECT_PATH]
---

You are the main Claude Code agent. When the user runs `/mts-documentation`, you will generate MTS (Mainframe Transaction Service) documentation for the current BUK Spring Boot codebase.

**Output:** Markdown files under `docs/mts/`. Always generates per-service documentation (including mainframe table mappings). Optionally generates overview docs (service catalogue, architecture, data lineage) based on user selection.

---

## Mode Detection

Check the argument passed to the command.

**Single-service mode:** If the argument looks like a method name (e.g., `retrievePersonalCustomerFullDetails`) or a `ServiceName.methodName` pair, run in **single-service mode**.

**Full mode:** If no argument is given, or the argument is a project path, run in **full mode** (Phase 1 -> Phase 1.5a -> Phase 1.5b -> Phase 2 -> Phase 3).

---

## Phase 0 — Pre-Flight Check (runs before both Full and Single-Service modes)

This phase detects the OS, locates the Gradle wrapper, and ensures the Gradle cache is populated so that downstream JAR-scanning steps succeed. All steps use Python for cross-platform correctness.

> Scripts are in `scripts/` directory within the plugin folder.

### Step 0.1 — Detect platform and Gradle wrapper

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight_platform.py" 2>/dev/null || python "${CLAUDE_PLUGIN_ROOT}/scripts/preflight_platform.py"
```

Parse the output and store `PLATFORM`, `GRADLE_WRAPPER`, `GRADLE_WRAPPER_EXISTS`, and `PYTHON_CMD`.

### Step 0.2 — Check Gradle cache for EBS/EGS artifacts

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight_cache.py" 2>/dev/null || python "${CLAUDE_PLUGIN_ROOT}/scripts/preflight_cache.py"
```

Parse and store `GRADLE_CACHE_STATUS` and `SOURCE_JARS_FOUND`.

### Step 0.2b — Detect compiled JAR fallback capability

Count compiled-only JARs (those with no matching `-sources.jar`) and detect `javap` availability:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/preflight_compiled_jars.py" 2>/dev/null || python "${CLAUDE_PLUGIN_ROOT}/scripts/preflight_compiled_jars.py"
```

Parse and store `COMPILED_JARS_FOUND`, `JAVAP_PATH`, and `COMPILED_JAR_FALLBACK`.

- `COMPILED_JAR_FALLBACK=FULL` — javap available, full Tier 1+2+3 extraction
- `COMPILED_JAR_FALLBACK=PARTIAL` — no javap, Tier 1+2 only (~85% coverage, no DataGroup-to-WMID conditional attribution)
- `COMPILED_JAR_FALLBACK=NONE` — no compiled-only JARs found (all have source JARs, or cache is empty)

### Step 0.2c — MIS source repo clone

For the service being documented, identify its EBS/EGS JAR name (from Step 0.2 or from
`build.gradle` if in single-service mode). Attempt to clone the corresponding MIS source repo:

```bash
<PYTHON_CMD> "${CLAUDE_PLUGIN_ROOT}/scripts/clone_mis_repos.py" <jar-name>
```

Parse and store `MIS_REPO_STATUS` and `MIS_REPO_PATH`.

- `MIS_REPO_STATUS=ALREADY_EXISTS` — repo already cloned at `MIS_REPO_PATH`, ready to use
- `MIS_REPO_STATUS=CLONED` — freshly cloned to `MIS_REPO_PATH`, ready to use
- `MIS_REPO_STATUS=NOT_MAPPED` — JAR has no MIS repo mapping yet; fall through to JAR extraction
- `MIS_REPO_STATUS=CLONE_FAILED` — network/auth issue; fall through to JAR extraction with warning

**In single-service mode:** pass the specific JAR name for the target service.
**In full mode:** run this step once per unique EBS/EGS JAR found across all services. Clone all mapped repos upfront before starting Phase 1.

If `MIS_REPO_STATUS=CLONE_FAILED`, print:
```
WARNING: MIS source repo clone failed for <jar-name>. TDL extraction will use
compiled JAR fallback. Check network access and ~/.gitconfig PAT token URL rewrite.
```

### Step 0.3 — Populate cache if empty

If `GRADLE_CACHE_STATUS=EMPTY` AND `GRADLE_WRAPPER_EXISTS=True`:

```bash
<GRADLE_WRAPPER> dependencies --configuration compileClasspath 2>&1 | tail -5
```

Then re-run the Step 0.2 check. If still empty after running dependencies, set:
```
GRADLE_CACHE_STATUS=EMPTY
```
Then also re-run Step 0.2b to recheck compiled JARs. Print a warning:
```
WARNING: Gradle cache still empty after running dependencies. Source JAR steps
(1.7, 1.10-1.15, S.4, S.7a-e) will use compiled JAR fallback if available
(COMPILED_JAR_FALLBACK=<level>). If NONE, documentation will be incomplete —
re-run after a successful build.
```

If `GRADLE_WRAPPER_EXISTS=False` and `GRADLE_CACHE_STATUS=EMPTY`, print:
```
WARNING: No Gradle wrapper found and cache is empty. JAR-scanning steps will be
skipped. Run 'gradle dependencies' or 'gradlew dependencies' manually first.
```

### Step 0.4 — Store pre-flight results

The following variables are now available for all downstream phases:
- `PLATFORM` — `Darwin`, `Linux`, or `Windows`
- `GRADLE_WRAPPER` — `./gradlew` or `gradlew.bat`
- `GRADLE_WRAPPER_EXISTS` — `True` or `False`
- `PYTHON_CMD` — `python3` or `python`
- `GRADLE_CACHE_STATUS` — `POPULATED` or `EMPTY`
- `SOURCE_JARS_FOUND` — integer count
- `COMPILED_JARS_FOUND` — integer count of compiled-only JARs (no matching `-sources.jar`)
- `JAVAP_PATH` — path to `javap` binary, or `NOT_AVAILABLE`
- `COMPILED_JAR_FALLBACK` — `FULL` (javap available), `PARTIAL` (no javap), or `NONE` (no compiled-only JARs)
- `MIS_REPO_STATUS` — `ALREADY_EXISTS`, `CLONED`, `NOT_MAPPED`, or `CLONE_FAILED`
- `MIS_REPO_PATH` — absolute path to cloned MIS repo (e.g., `~/.mts-source/egs-odsmf-customer`), or unset if NOT_MAPPED/CLONE_FAILED

---

## Single-Service Mode

For single-service mode, read and follow `${CLAUDE_PLUGIN_ROOT}/skills/mts-reference/reference/single_service_mode.md`.

---

## Full Mode — Phase 1: Discovery (Sub-Agent)

Launch the discovery agent as a sub-agent using the Task tool. Do NOT run discovery steps inline.

```
Task tool call:
  subagent_type: general-purpose
  prompt: "You are the MTS Discovery Agent. Follow the instructions in ${CLAUDE_PLUGIN_ROOT}/agents/mts-discovery-agent.md — read that file first. Run full MTS discovery on the project at <project-path>. Execute all steps 1.1 through 1.27 and return the structured summary with all SECTION: headers including transport-specific sections (TRANSPORT_CLASSIFICATION, SOAP_STUB_REGISTRY, DATABASE_DIRECT_REGISTRY, HYBRID_SERVICE_REGISTRY, SOAP_WEBSERVICE_REGISTRY, ITSU_ORACLE_REGISTRY, ALS_BACKEND_REGISTRY, ALREADY_API_INVENTORY, WRITE_TABLES, ORCHESTRATION_SUB_SERVICES, DOSERVICE_CORRELATION_MAP).

  Pre-flight results from Phase 0:
  - PLATFORM=<PLATFORM>
  - PYTHON_CMD=<PYTHON_CMD>
  - GRADLE_WRAPPER=<GRADLE_WRAPPER>
  - GRADLE_CACHE_STATUS=<GRADLE_CACHE_STATUS>
  - SOURCE_JARS_FOUND=<SOURCE_JARS_FOUND>
  - COMPILED_JARS_FOUND=<COMPILED_JARS_FOUND>
  - JAVAP_PATH=<JAVAP_PATH>
  - COMPILED_JAR_FALLBACK=<COMPILED_JAR_FALLBACK>

  Use PYTHON_CMD for all Python invocations. If GRADLE_CACHE_STATUS=EMPTY, skip Steps 1.7, 1.10-1.15 and record them in INCOMPLETE_STEPS. If SOURCE_JARS_FOUND=0 but COMPILED_JAR_FALLBACK is FULL or PARTIAL, use compiled JAR fallback (see compiled_jar_extraction.md)."
```

**IMPORTANT:** Use `subagent_type: general-purpose`, NOT `mts-discovery-agent`. Custom agent names are not valid subagent types.

Wait for the agent to return the structured discovery summary. Parse `## SECTION: DISCOVERY_METADATA` for the service count.

If the discovery agent reports `## SECTION: INCOMPLETE_STEPS`, note which steps were incomplete and continue with available data.

---

## Full Mode — Phase 1.5a: Service Selection

Present the list of discovered doService calls to the user using `AskUserQuestion`.

**Display format:** Show a numbered summary table of all discovered services:
```
Found [N] doService calls:

| # | Service Name | Method | Transport | File:Line |
|---|...|...|...|...|
```

**Note:** Services classified as `already-api-rest` or `already-api-direct-http` are shown in the table for awareness but are excluded from the migration documentation pipeline. Mark them with `[out of scope]` in the display.

Then use `AskUserQuestion` with:
- **question:** "Which service would you like to document? Select one to start, or choose 'All services' to generate everything."
- **options:**
  - **"All services (Recommended)"** — generates per-service docs for every discovered doService call in parallel. Include description: "Generates all [N] per-service docs."
  - One option per discovered doService call, labelled as `ServiceName.methodName`, with description showing the category and file location

**If user selects "All services":** Continue to Phase 1.5b.

**If user selects a single service:** Skip Phase 1.5b entirely — go directly to Phase 2 launching ONLY the per-service agent for that service. No overview docs.

---

## Full Mode — Phase 1.5b: Overview Document Selection (Full Mode Only)

**This phase runs ONLY when the user selected "All services" in Phase 1.5a.** If the user selected a single service, skip this phase entirely.

Use `AskUserQuestion` with:
- **question:** "Which overview documents do you want in addition to the per-service docs?"
- **header:** "Scope"
- **options:**
  - **"Per-service docs only (Recommended)"** — description: "Just the per-service docs for the services you selected. This is all the downstream pipeline needs."
  - **"With service catalogue"** — description: "Per-service docs + service-catalogue.md (combined service inventory and orchestration map)."
  - **"Full set"** — description: "Per-service docs + service-catalogue.md + architecture-overview.md + data-lineage.md."

Store the user's selection as `OVERVIEW_SCOPE` for use in Phase 2 dispatch.

---

## Full Mode — Phase 2: Data Routing & Agent Dispatch

Create `docs/mts/` directory first:
```bash
mkdir -p docs/mts
```

### Data Routing Table

Each agent receives only the discovery sections it needs, extracted from the Phase 1 structured summary. **Overview agents are conditional** based on the `OVERVIEW_SCOPE` selected in Phase 1.5b.

| Agent | subagent_type | Agent Instructions File | Sections from Discovery | Output File | Condition |
|-------|---------------|------------------------|------------------------|-------------|-----------|
| Per-Service Doc (x N) | `general-purpose` | `agents/mts-per-service-doc-agent.md` | Service-specific slice of all sections (mainframe OR transport-specific) | `docs/mts/service-doc-<Name>-<method>.md` | **Always** (except `already-api-*`) |
| Service Catalogue | `general-purpose` | `agents/mts-service-catalogue-agent.md` | `DOSERVICE_CALLS`, `EBS_DEPENDENCIES`, `TRANSACTION_REGISTRY`, `CALL_CHAINS`, `REST_ENDPOINTS`, `TRANSPORT_CLASSIFICATION`, `SOAP_STUB_REGISTRY`, `DATABASE_DIRECT_REGISTRY`, `HYBRID_SERVICE_REGISTRY`, `ALREADY_API_INVENTORY` | `docs/mts/service-catalogue.md` | `OVERVIEW_SCOPE` = "With service catalogue" OR "Full set" |
| Architecture | `general-purpose` | `agents/mts-architecture-agent.md` | `CONFIG_SUMMARY`, `REST_ENDPOINTS`, `EBS_DEPENDENCIES` | `docs/mts/architecture-overview.md` | `OVERVIEW_SCOPE` = "Full set" only |
| Data Lineage | `general-purpose` | `agents/mts-data-lineage-agent.md` | `CALL_CHAINS`, `DOSERVICE_CALLS`, `TRANSACTION_REGISTRY` | `docs/mts/data-lineage.md` | `OVERVIEW_SCOPE` = "Full set" only |

**Transport-specific data routing for Per-Service Doc agents:**
- `mainframe-mq` services: Include `TRANSACTION_REGISTRY`, `DATAGROUP_WMID_TDL_CHAINS`, `COMMAND_CHAINS`, `WMOD_FIELD_INVENTORY`, `TRANSACTION_NAME_CORRELATION`
- `soap-stub` services: Include `SOAP_STUB_REGISTRY` data for this service
- `oracle-db-direct` / `db2-reference` services: Include `DATABASE_DIRECT_REGISTRY` data for this service
- `cmod-odwek` services: Include `CMOD_ODWEK_REGISTRY` data (if any — typically not in fullserve-buk)
- `tcv-hybrid` / `scv` services: Include `HYBRID_SERVICE_REGISTRY` data for this service
- `soap-webservice` services: Include EGS gateway class, SOAP service ID, backend system, routing conditions
- `itsu-oracle` services: Include EBS data access class, Oracle tables, JNDI datasource
- `als-backend` services: Include EBS/EGS gateway, ALS transaction class, ALS tables
- `already-api-*` services: **Skip per-service doc generation** — these are inventory-only

**IMPORTANT:** All agents use `subagent_type: general-purpose`. Each agent prompt must start with: "You are the MTS [Agent Name]. Follow the instructions in `${CLAUDE_PLUGIN_ROOT}/[agent-file]` — read that file first." This ensures the agent reads its own instruction file. Agent instructions files are relative to `${CLAUDE_PLUGIN_ROOT}/`.

**Note:** The `mts-service-inventory-agent` and `mts-code-journeys-agent` are **no longer dispatched**. Their content is consolidated into the `mts-service-catalogue-agent`. The old agent files are retained but deprecated.

### Agent Prompt Structure

Each agent prompt must include:
1. The project path
2. The relevant discovery sections (per Data Routing Table above)
3. The output file path to write

### Per-Service Doc Agent — Additional Data

For **mainframe-mq** services, extract the entry from `DOSERVICE_CORRELATION_MAP` keyed by (ServiceName, operationCode) and pass the **entire correlation entry** verbatim to the per-service agent. This provides the pre-correlated chain (doService → Command → Gateway → Transaction → DataGroups → TDL) so the sonnet agent doesn't need to cross-reference multiple sections.

In addition to the correlation map entry, include:
- **WMOD response fields** from `WMOD_FIELD_INVENTORY` section (for this service's Transaction)
- **TRANSACTION_NAME correlation** from `TRANSACTION_NAME_CORRELATION` section (for this service)
- **Confidence indicators** from `CONFIDENCE_INDICATORS` section (for this service's items)

For **non-mainframe** services (soap-stub, oracle-db-direct, db2-reference, soap-webservice, itsu-oracle, als-backend, etc.), include the relevant transport-specific registry data.

**For all services:** If the discovery summary includes `WRITE_TABLES` or `ORCHESTRATION_SUB_SERVICES`, pass them to the per-service agent prompt.

For services where discovery did not find Transaction data (reference-data-only services), include a note: "No mainframe transaction data extracted for this service."

### Launch ALL Agents in ONE Message

This is critical for performance — every independent agent MUST be launched in the same tool-call block:

- **"Per-service docs only":** Launch N per-service agents in ONE message
- **"With service catalogue":** Launch 1 service-catalogue agent + N per-service agents in ONE message
- **"Full set":** Launch 3 overview agents + N per-service agents in ONE message
- **Single service (from Phase 1.5a):** Launch 1 per-service agent only

---

## Full Mode — Phase 3: Verification & Next Service

After all agents complete:

1. **Confirm files exist:**
   ```
   Glob docs/mts/*.md
   ```

2. **Generate index file (`docs/mts/README.md`):**
   Write a landing page using the discovery data. **Only include sections for docs that were actually generated.**

   Include:
   - Project name and one-line description
   - **Overview Documents** table — only list overview docs that were generated based on `OVERVIEW_SCOPE`. If `OVERVIEW_SCOPE` was "Per-service docs only", omit this section entirely.
   - **Per-Service Documents** section split by category (mainframe-touching / reference-data-only), each with a relative link
   - **REST Endpoints** quick-reference table
   - Footer noting this was generated by the mts-documentation plugin

   Generate this inline (NOT by an agent) — all data is already available.

3. **Report to user — list only generated files:**

   For **"Per-service docs only"**:
   ```
   MTS Documentation complete. Generated files in docs/mts/:
   - README.md — index with links to all docs
   - service-doc-*.md — [M] per-service docs (each includes mainframe table mappings)

   [Any warnings about missing source JARs, unresolved items, or incomplete discovery steps]
   ```

   For **"With service catalogue"**:
   ```
   MTS Documentation complete. Generated files in docs/mts/:
   - README.md — index with links to all docs
   - service-catalogue.md — [N] doService calls + orchestration map
   - service-doc-*.md — [M] per-service docs (each includes mainframe table mappings)

   [Any warnings]
   ```

   For **"Full set"**:
   ```
   MTS Documentation complete. Generated files in docs/mts/:
   - README.md — index with links to all docs
   - service-catalogue.md — [N] doService calls + orchestration map
   - architecture-overview.md
   - data-lineage.md — field-level traceability per endpoint
   - service-doc-*.md — [M] per-service docs (each includes mainframe table mappings)

   [Any warnings]
   ```

4. **Ask about next service (only if user selected a single service in Phase 1.5a):**
   If the user selected a single service and there are remaining undocumented services, use `AskUserQuestion` with one option per remaining service plus **"Done for now"**.

   If the user selects a service, launch **only** the per-service agent (do NOT re-generate overview files). Repeat until "Done for now".
