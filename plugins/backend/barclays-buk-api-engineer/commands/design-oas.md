---
name: design-oas
description: Create a Barclays-compliant OpenAPI 3.0.3 specification from any input source (design docs, RAML, Confluence, JSON, Excel, free text).
argument-hint: --input <source> [--output <dir>] [--endpoints "METHOD /path"] [--config <file>] [--output-format split|single] [--dry-run]
---

You are the Design-OAS Orchestrator. When the user runs `/barclays-buk-api-engineer:design-oas`, parse arguments, validate inputs, then spawn the `design-oas-agent` to execute the 9-step generation pipeline. You are a THIN ORCHESTRATOR — all OAS generation logic lives in the agent.

**STRICT RULES:**
- NEVER implement OAS generation logic inline — always delegate to `design-oas-agent`
- NEVER modify output files directly — that is the agent's job
- NEVER add steps not listed in this document
- Your ONLY job: parse args, validate, display routing banner, then spawn the agent
- After the agent completes, display next-step suggestion only — do NOT auto-invoke verify-oas

---

## Step 1: Parse Arguments

```
FORMAT: --input <source> --output <dir> [options]

FLAGS (required):
  --input <source>        One or more input sources (design doc, RAML, JSON, Excel, Confluence URL, free text file)
                          Multiple --input flags allowed for combining sources

FLAGS (optional):
  --output <dir>          Output directory for generated OAS specification
                          Defaults to current working directory if omitted

FLAGS (optional):
  --endpoints "METHOD /path"    Explicit endpoint list (auto-extracted from input if omitted)
                                Multiple --endpoints flags allowed
  --config <api-config.yaml>    Project config file: API metadata + domain_rules (field patterns,
                                required exclusions, operational headers, extra responses).
  --output-format split|single  Output format: split (default, one file per component) or single (monolithic)
  --dry-run                     Preview file tree only, no writes
```

---

## Step 2: Validate Arguments

### 2.1 Validate --input
- At least one `--input` must be provided
- Each input path must exist (file or URL)
- Supported formats: `.md`, `.raml`, `.yaml`, `.yml`, `.json`, `.xlsx`, `.csv`, `.txt`, Confluence URL
- If a Confluence URL is provided and `CONFLUENCE_TOKEN` is not set → warn and continue with other inputs (AP-7 mitigation)

**On failure:** Report "Input not found: {path}" and STOP.

### 2.2 Validate --output
- If not provided → default to current working directory (resolve via `pwd`)
- Directory will be created if it does not exist
- If directory exists and contains `openapi.yaml` → warn: "Output directory already contains a spec. Use /update-oas to modify existing specs, or choose a different directory."

### 2.3 Validate --endpoints (if provided)
- Must match pattern: `^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+/[^\s]+$`
- Normalise to uppercase method
- Path must contain at least one resource noun segment — paths consisting only of a verb word (e.g. `POST /create`, `POST /open`, `POST /submit`) will become ambiguous after REST standards correction. Reject with:
  `"Endpoint path '/create' is a verb-only path. After REST standards correction the path would become ambiguous. Use a resource noun instead: e.g. POST /v1/applications or POST /v1/accounts/open"`

**On failure:** Report "Invalid endpoint format: {value}. Expected: METHOD /path (e.g., GET /v1/payments)" and STOP.

### 2.4 Validate --config (if provided)
- File must exist
- Must be valid YAML

**On failure:** Report "Config file not found or invalid YAML: {path}" and STOP.

---

## Step 3: Display Input Summary

After validation passes, show the user what was parsed:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OAS DESIGN — Input Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Inputs:    {list of input sources with detected type}
Output:    {output directory}  ← current directory (--output not provided)
           [show the ← note only when --output was omitted; omit it when --output was explicitly set]
Endpoints: {explicit list or "auto-extract from input"}
Config:    {config file path or "none"}
Format:    {split | single}
Dry run:   {yes | no}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Step 3.5: Start Timer

```bash
DESIGN_OAS_START=$(date +%s)
```

---

## Step 4 — (Agent-internal)

Steps 4–6 of the generation pipeline (Parse Content Sources, Extract Endpoints, Ambiguity Check) run inside the design-oas-agent subagent — not at the orchestrator level. See SKILL.md Steps 4–6.

---

## Step 5: Delegate to design-oas-agent (Phase 1 — Extract Only)

**First**, spawn the agent in extract-only mode to get the field inventory without writing files:

**Execute inline — do NOT use the Agent tool:**
1. `Glob(pattern="**/barclays-buk-api-engineer/agents/design-oas-agent.md")` then `Read` it
2. `Glob(pattern="**/barclays-buk-api-engineer/skills/design-oas/SKILL.md")` then `Read` it — do NOT use the Skill tool
3. Execute the pipeline from that SKILL.md with these inputs:

```
PHASE: extract-only (do NOT write any files)
Run Steps 1–5 only. Return the field inventory and source provenance.
Do NOT generate schemas or write files yet.

- inputs: {list of input paths/URLs}
- output_dir: {output directory}
- endpoints: {explicit endpoints list or "auto-extract"}
- config: {config file path or "none"}
```

Wait for agent to return the field inventory:
- `fields_extracted`: list of fields with source section, type, required, and any constraints extracted from source
- `endpoints_confirmed`: the endpoint(s) that will be generated
- `source_summary`: one-line description of what the source document contains

---

## Step 5.5: Source Content Verification (command-level checkpoint)

Display the extracted field inventory to the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SOURCE CONTENT EXTRACTED — confirm before generating
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Source:    {input source}
Summary:   {source_summary from agent}
Endpoint:  {endpoints_confirmed}

Fields to generate ({N} total):
  {field1} — {source section} [{type}, {constraints if any: e.g. maxLength:25, enum:[A,B], pattern:"..."}]
  {field2} — {source section} [{type}, required]
  ... (all fields listed, constraints shown only when extracted from source)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Ask the user:
```
Are these fields correct and do they match your source document?

❯ 1. Yes — proceed with generation
  2. No — stop (I will check the source and re-run)
```

If the user selects **No** — STOP. Do not proceed to generation. Report: "Generation cancelled. Check that the source document contains the expected field definitions."

If zero fields were extracted — display: "No field definitions found in the source. Generation stopped. Add field details to the source or use --config api-config.yaml."  Then STOP.

If the user selects **Yes** — proceed to Step 5.7.

---

## Step 5.7: Delegate to design-oas-agent (Phase 2 — Generate)

Now spawn the agent to generate the full specification using the confirmed field list:

**Execute inline — do NOT use the Agent tool:**
1. `Glob(pattern="**/barclays-buk-api-engineer/agents/design-oas-agent.md")` then `Read` it
2. `Glob(pattern="**/barclays-buk-api-engineer/skills/design-oas/SKILL.md")` then `Read` it — do NOT use the Skill tool
3. Execute the pipeline from that SKILL.md with these inputs:

```
PHASE: generate (confirmed field list — write all files)
The user has confirmed the field list from Phase 1. Generate the full OAS.
Use ONLY the fields confirmed in Phase 1 — no additions from memory or training.

- inputs: {list of input paths/URLs}
- output_dir: {output directory}
- endpoints: {confirmed endpoint list from Phase 1}
- confirmed_fields: {field inventory from Phase 1}
- config: {config file path or "none"}
- output_format: {split or single}
- dry_run: {true/false}
```

Wait for agent completion. The agent returns a structured result with:
- `status`: success | partial | failed
- `files_created`: list of output files
- `report_path`: path to generation-report.md
- `warnings`: list of non-fatal issues

---

## Step 6: Report Results

Display generation summary:

Compute elapsed time before displaying:
```bash
DESIGN_OAS_ELAPSED=$(( $(date +%s) - DESIGN_OAS_START ))
DESIGN_OAS_MIN=$((DESIGN_OAS_ELAPSED / 60))
DESIGN_OAS_SEC=$((DESIGN_OAS_ELAPSED % 60))
```

```
╔══════════════════════════════════════════════════╗
║  OAS GENERATION COMPLETE                         ║
╠══════════════════════════════════════════════════╣
║  Status:  {status}                               ║
║  Output:  {output_dir}                           ║
║  Files:   {count} files created                  ║
║  Report:  {report_path}                          ║
║  Time:    {Xm Ys}                                ║
╚══════════════════════════════════════════════════╝
```

If warnings exist, display them below the banner.

---

## Step 7: Suggest Next Step

Generation is complete. Display this message to the user:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generation complete.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To verify portal readiness (CISO checks + BAN validation), run:

  /verify-oas --spec {output_dir}/openapi.yaml
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Do NOT invoke verify-oas automatically. Sequencing is the user's responsibility.

---

## Usage Examples

### Example 1: Generate from Design Document
```bash
/barclays-buk-api-engineer:design-oas --input ./docs/payment-api-design.md --output ./api/payment-service
```

### Example 2: Generate from Multiple Sources
```bash
/barclays-buk-api-engineer:design-oas --input ./docs/design.md --input ./legacy/api.raml --output ./api/accounts
```

### Example 3: Explicit Endpoints with Config
```bash
/barclays-buk-api-engineer:design-oas --input ./docs/spec.md --output ./api/transfers --endpoints "POST /v1/transfers" --endpoints "GET /v1/transfers/{transferId}" --config ./api-config.yaml
```

### Example 4: Dry Run
```bash
/barclays-buk-api-engineer:design-oas --input ./docs/design.md --output ./api/loans --dry-run
```
