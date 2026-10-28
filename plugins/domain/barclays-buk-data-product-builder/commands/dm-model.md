---
description: Invoke Data Modeller — design target data model from business requirement
disable-model-invocation: false
argument-hint: <requirement-path> [--update <existing-model-path>] [--mapping <mapping-file-path>]
---

# /dm-model

Invoke the DM Data Modeller agent (Elena) to design a target data model with ER diagrams, composite keys, audit columns, and optional KPI normalised pattern from a business requirement document. Supports update mode for iterating on an existing data model.

## Usage

```
/dm-model dm-output/BUKL2CUSX-2355/business-requirement.md
/dm-model dm-output/BUKL2CUSX-2355/business-requirement.md --update dm-output/BUKL2CUSX-2355/data-model.md
/dm-model dm-output/BUKL2CUSX-2355/business-requirement.md --update dm-output/BUKL2CUSX-2355/data-model.md --mapping dm-output/BUKL2CUSX-2355/data-mapping.md
```

## Behaviour

### Step 1: Detect Input Mode and Read Requirement Document

Parse the user's arguments to determine the input mode:

| Pattern | Mode | Example |
|---------|------|---------|
| Path only (no flags) | **New mode** | `dm-output/BUKL2CUSX-2355/business-requirement.md` |
| Path followed by `--update <existing-model-path>` | **Update mode** | `dm-output/.../business-requirement.md --update dm-output/.../data-model.md` |

#### Read Requirement (both modes)

1. Read the file at the specified `<requirement-path>`
2. If file not found → report error: `"Requirement document not found at <path>. Run /dm-bra first to produce a business requirement."`, **HALT**
3. Validate the file looks like a BRA output (contains "BUSINESS REQUIREMENT" header and numbered sections)
4. If validation fails → warn but proceed (the agent will handle malformed input)

#### Read Existing Model (Update mode only)

1. Read the existing data model at the `--update` path
2. If file not found → report error: `"Existing data model not found at <path>. Check the path and try again."`, **HALT**
3. Store the existing model content for passing to the agent in Step 3

#### Read Existing Mapping (Update mode only, optional)

1. If `--mapping <mapping-file-path>` was provided, read the file at that path
2. If file not found → report warning: `"Mapping file not found at <path>. Proceeding without existing mapping — attribute placement will be based on BRD requirements and grain analysis only."`, continue without it
3. Store the mapping content (if available) for passing to the agent in Step 3

### Step 2: Determine Reference Slug

Extract the reference from the path:
- If path matches `dm-output/<ref>/business-requirement.md` → use `<ref>` as the slug
- Otherwise → use the parent directory name or filename stem

### Step 2.5: Check FDP Source Domains

Before invoking the agent, check for FDP CSV files that enable FDP-grounded design:

1. **Ensure folder exists:** `mkdir -p data/source-domains/`
2. **Count domain CSVs:** List `.csv` files in `data/source-domains/` excluding `sample_domain.csv`
3. **Report status:**
   - If **zero** real CSVs found → emit:
     > **Note:** No FDP CSV files found in `data/source-domains/`. The Data Modeller will proceed without FDP-grounded design. To enable FDP alignment, place your domain CSVs in this folder. See the FDP Source Domains section in `README.md` for the expected format.
   - If **one or more** real CSVs found → emit:
     > **FDP Sources:** Found [N] domain CSV file(s) in `data/source-domains/`. FDP-grounded design will be active.

4. **Pass FDP context to agent:** When invoking the agent in Step 3, include the FDP availability status in the prompt:
   - If CSVs present: "FDP source domains are available at `data/source-domains/` with [N] domain CSV files. Scan them during Step 1.5."
   - If no CSVs: "No FDP source domains available. Skip FDP-grounded design (Step 1.5) and design from the business requirement only."

### Step 3: Invoke DM Data Modeller Agent

Invoke `dm-data-modeller-agent` via Agent tool with:
- The full content of the business requirement document
- The requirement file path for metadata reference
- The FDP availability status from Step 2.5
- **Explicit instruction to execute the Entry Gate (MANDATORY):** Tell the agent: "You MUST execute your Entry Gate before proceeding. Ask the user Question 1 (new vs. update model) and Question 2 (data product type: FDP/CDP/BDP) and wait for both answers before designing anything."
- If update mode: the existing data model content and instruction: "The user has indicated they want to update an existing model. Skip Entry Gate Question 1 — the answer is 'Existing Model' and the existing model file content is provided below. You MUST still ask Entry Gate Question 2 (data product type). Then proceed to Step 0.5 (Existing Model Ingestion) with the provided model content."
- **Existing mapping file (Update mode, optional pass-through):** If a mapping file was provided via `--mapping` and successfully read, include its content and instruct: "The existing source-to-target data mapping file is provided below." If `--mapping` was NOT provided, instruct: "No existing mapping file was provided. You SHOULD ask the user: 'Please also provide the existing source-to-target data mapping file.' If the user cannot provide it, proceed without it and note: 'No existing mapping file provided — new attribute placement based on BRD requirements and grain analysis only.'"

### Step 4: Write Output

Write the agent's output to `dm-output/<ref>/data-model.md`.

### Step 5: Update Tracking

Read or create `dm-session/tracking.json` (schema: `schemas/dm_tracking.schema.json`).
Append to `commands_run` and update `outputs.data_model`.

### Step 6: Suggest Next Step

```
→ Next: Validate this data model against quality gates:
  /dm-validate dm-output/<ref>/data-model.md --type dm
```

---

## Isolation

- Output goes to `dm-output/` — never touches `generated/` or `session/session_state.json`
- Tracking goes to `dm-session/` — never touches `session/`
- Existing plugin commands and hooks are unaffected
