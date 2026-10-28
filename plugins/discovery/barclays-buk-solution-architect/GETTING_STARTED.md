# Solution Architect Agent — Getting Started

## What you will be able to do

This guide walks you through retrieving a single Jira issue deterministically, saving its unmodified source response and provenance, normalising it into `requirements.json`, and validating the result as input for architecture review.

**Key principle:**

> Retrieval is deterministic; interpretation is agentic.

The current vertical slice does **not** yet implement:

- Domain Model assessment
- Town Plan integration
- Full architecture interpretation
- agentic review reasoning

Those are subsequent increments. This step produces the evidence layer that downstream agents consume.

## Prerequisites

### Software

- **Git**: version control for cloning the repository
- **Python**: 3.9 or later, for running retrieval and review scripts
- **Bash or PowerShell**: to set environment variables and run commands

### Access

- Credentials to access `estjira.barcapint.com`
- A valid Jira personal access token (PAT)

### Optional: Claude Code (for skill-based invocation)

If you plan to invoke the retrieval and review as Claude Code skills rather than direct Python commands, you will need:

- Claude Code version 2.1.110 or later
- The `barclays-buk-solution-architect` plugin installed

For this guide, we demonstrate direct Python invocation, which does not require Claude Code.

## 1. Clone and check out the branch

Clone the repository:

```bash
git clone <FORK-CLONE-URL>
cd <REPOSITORY-DIRECTORY>
```

Check out the feature branch:

```bash
git switch feat/BUKL3BBA-1464-deterministic-jira-requirements
```

For the standard BUK repository workflow, see [CONTRIBUTING.md](../../../CONTRIBUTING.md) Section 6.2: `git fetch upstream` then `git checkout -b feat/TICKET-XXXX-short-description upstream/main`.

## 2. Locate the Solution Architect plugin

Enter the plugin directory:

```bash
cd plugins/discovery/barclays-buk-solution-architect
```

The plugin contains:

- `scripts/retrieve_jira_requirements.py` — deterministic Jira retrieval and normalisation
- `scripts/review_requirements.py` — requirements validation and provenance display
- `scripts/tests/` — automated tests (no real Jira connection required)
- `skills/` — Claude Code skill definitions (optional; direct Python invocation is primary)

## 3. Configure runtime workspace

Runtime artefacts (retrieved Jira responses and normalised requirements) are stored in an **external workspace** — never under the Git repository.

Set your workspace location using either:

### Option A: Environment variable (recommended)

```bash
export BUK_SA_WORKSPACE=/path/to/workspace
```

### Option B: Command-line parameter

```bash
--output-dir /path/to/workspace
--workspace /path/to/workspace
```

**Precedence:** `--output-dir` or `--workspace` parameter overrides `BUK_SA_WORKSPACE` environment variable. If neither is provided, retrieval fails with a clear error.

**Example workspace locations:**
- Linux/macOS: `~/buk-sa-workspace` or `/tmp/buk-sa-workspace`
- Windows: `C:\Users\<username>\buk-sa-workspace`

**Note:** Persistent, managed runtime storage (e.g., network location, archive, retention lifecycle) is a future architectural decision involving information handling, compliance, and lifecycle policies.

## 4. Configure Jira authentication

Your Jira personal access token must be available as the `JIRA_AUTH_TOKEN` environment variable.

### On PowerShell

Set the token:

```powershell
$env:JIRA_AUTH_TOKEN = "YOUR-JIRA-TOKEN"
```

Verify it is set (safely, without printing it):

```powershell
if ($env:JIRA_AUTH_TOKEN) { "JIRA_AUTH_TOKEN is set" }
```

Remove it after you are finished:

```powershell
Remove-Item Env:JIRA_AUTH_TOKEN
```

### On bash or zsh

Set the token:

```bash
export JIRA_AUTH_TOKEN='YOUR-JIRA-TOKEN'
```

Verify it is set (safely, without printing it):

```bash
echo "${JIRA_AUTH_TOKEN:+JIRA_AUTH_TOKEN is set}"
```

Remove it after you are finished:

```bash
unset JIRA_AUTH_TOKEN
```

### ⚠️ Security reminders

- **Never print or echo your token to the terminal.** Use the verification commands above.
- **Never commit your token** to version control.
- **Never place it in documentation, Slack messages, or support requests.** If exposed, rotate it immediately at https://estjira.barcapint.com/secure/ViewProfile.jspa.
- **Never place it in an unignored `.env` file.** Use environment variables only.

## 5. Run the automated tests

Verify the installation by running the test suite:

```bash
python -m unittest scripts.tests.test_retrieve_jira_requirements -v
```

Expected output: All tests pass. The test suite uses static fixtures and does not require a connection to Jira. **Importantly, the test suite creates no runtime artefacts in the Git repository or elsewhere.**

## 6. Retrieve and Understand Requirements from a Jira Issue

The requirements retrieval and understanding workflow is automated through the `understand-requirements` skill and supporting orchestration scripts. This replaces manual multi-step invocation.

Replace `BUKL2CUSX-173655` with a Jira issue key you are authorised to view.

### Overview

The orchestration layer automatically:
- Checks whether the issue has been previously retrieved and validated
- Retrieves from Jira only if necessary (not cached or stale)
- Normalizes the response deterministically
- Prepares evidence for requirements analysis

See Section 8 below for the full requirements understanding workflow (including automatic retrieval).

## 7. Understand the Runtime Artefacts

When the requirements understanding workflow runs (Section 8), the orchestration layer automatically retrieves and validates requirements from Jira. The following files are created in your workspace:

| File | Purpose |
|------|---------|
| `$BUK_SA_WORKSPACE/raw/BUKL2CUSX-173655.json` | Unmodified Jira API response (source evidence) |
| `$BUK_SA_WORKSPACE/requirements/BUKL2CUSX-173655.json` | Normalised requirements with embedded provenance |

### About provenance

The `requirements.json` file includes a `source` object that records:

- Jira instance URL
- Issue key
- Retrieval timestamp
- API endpoint used
- Fields that were requested
- SHA-256 hash of the raw response
- Path to the saved raw response file (relative to workspace for portability)

The SHA-256 hash binds `requirements.json` back to the saved raw response. If the raw response is modified, the hash will no longer match, and the `review` command will detect it.

### Treating generated data

Generated artefacts in your workspace may contain internal Jira requirements. Follow your organisation's information-handling policy for retention, sharing and lifecycle of these outputs. This is distinct from the source repository, which should never contain runtime data.

## 8. Review the normalised requirements

### On PowerShell

```powershell
python scripts/review_requirements.py `
  --requirements-path $env:BUK_SA_WORKSPACE/requirements/BUKL2CUSX-173655.json `
  --workspace $env:BUK_SA_WORKSPACE
```

### On bash or zsh

```bash
python scripts/review_requirements.py \
  --requirements-path $BUK_SA_WORKSPACE/requirements/BUKL2CUSX-173655.json \
  --workspace $BUK_SA_WORKSPACE
```

### What the review command does

- Loads `requirements.json`
- Validates its expected structure (schema version, required fields)
- Displays provenance (Jira instance, issue key, retrieval timestamp, endpoint, requested fields, SHA-256)
- Verifies that the raw response file exists at the recorded path
- **Recomputes the SHA-256 hash of the raw file and compares it to the recorded value** (detects tampering)
- Prints a summary of normalised content (title, description, type, status, labels, components, linked issues, acceptance criteria)
- Reports any warnings from normalisation

### What the review command does NOT do

- Does not call Jira
- Does not call any language model
- Does not perform agentic architecture reasoning (that is a subsequent step)

## 8. Understand Requirements (Agentic Stage)

The requirements-understanding stage uses a three-phase deterministic-agentic-deterministic workflow to analyze the normalised Business Epic and produce structured requirements analysis.

### Workflow Overview

```
Stage 1: Deterministic Preflight (run from CLI)
  → Validate input, verify provenance, extract normalized evidence

Stage 2: Agentic Analysis (within Claude Code or skill context)
  → Current LLM analyzes evidence
  → Produces structured requirements understanding

Stage 3: Deterministic Postflight (run from CLI)
  → Validate analysis schema and evidence references
  → Persist to external workspace
```

### Stage 1: Run Preflight Validation

```bash
export BUK_SA_WORKSPACE=/path/to/external/workspace
python scripts/understand_requirements.py \
  --mode preflight \
  --requirements-path $BUK_SA_WORKSPACE/requirements/BUKL2CUSX-173655.json \
  --workspace $BUK_SA_WORKSPACE
```

**Output:** Validated evidence contract (JSON with `issue_key` and normalized `evidence`)

**Prerequisites:**
- `requirements.json` successfully validated (completed Step 7)
- No additional dependencies required (pure Python, deterministic)

**This validates:**
- ✓ Schema version 1.0
- ✓ Jira issue type is Business Epic
- ✓ Raw response file exists
- ✓ SHA-256 hash matches (provenance integrity)

### Stage 2: Analyze Requirements (Your Role as Agent/LLM)

The current Claude Code context (or external LLM) analyzes the normalized evidence and produces structured requirements understanding.

**What you should analyze:**
- Epic title, description, status, labels, components
- Linked issues and their relationships
- Acceptance criteria
- What change is being asked for?
- What requirements are directly stated vs. inferred?
- What constraints or dependencies exist?
- What information is missing or ambiguous?

**Output format:** JSON with these sections:
- `change_summary` (outcome, rationale, supporting evidence)
- `explicit_requirements` (directly stated, with evidence)
- `inferred_requirements` (reasonable interpretations, with reasoning + evidence)
- `constraints_and_dependencies` (with is_explicit flag + evidence)
- `ambiguities_and_unknowns` (missing/unclear info, clarification questions)
- `key_concepts` (business/architectural concepts, with definitions)

See `skills/understand-requirements/SKILL.md` for detailed schema and classification rules.

### Stage 3: Run Postflight Validation and Persist

```bash
python scripts/understand_requirements.py \
  --mode postflight \
  --requirements-path $BUK_SA_WORKSPACE/requirements/BUKL2CUSX-173655.json \
  --analysis-path /path/to/your-analysis.json \
  --workspace $BUK_SA_WORKSPACE
```

**Output:** Valid `requirements-analysis.json` persisted to `<workspace>/analysis/{issue_key}/`

**This validates:**
- ✓ Analysis schema and structure
- ✓ All evidence references are valid normalized fields
- ✓ Cited evidence actually exists in referenced fields
- ✓ Explicit/inferred distinction maintained
- ✓ Provenance preserved (raw_jira_response_sha256)

**No additional dependencies required (pure Python, deterministic)**

### Understanding the Analysis Output

The output `requirements-analysis.json` includes:

- **explicit_requirements**: Requirements directly stated in the Business Epic (not inferred, no reasoning field)
- **inferred_requirements**: Reasonable interpretations supported by evidence, with reasoning and evidence
- **constraints_and_dependencies**: Constraints or dependencies identified, marked explicit/inferred with evidence
- **ambiguities_and_unknowns**: Missing or unclear information, with impact and clarification question (not recommendations)
- **key_concepts**: Business/architectural concepts present in the change, with definitions
- **source_jira_evidence**: Provenance — issue key and SHA-256 hash of original raw Jira response

## 9. What happened under the covers?

```
Jira issue (live)
    |
    v
Deterministic API retrieval
(curl + HTTP, no inference)
    |
    +--> Unmodified raw HTTP response body
    |    (exact response bytes)
    |
    +--> SHA-256 hash of raw bytes
    |    (evidence of integrity)
    |
    v
Deterministic normalisation
(pure code, no LLM)
    |
    v
requirements.json
(structured data + provenance)
    |
    v
DETERMINISTIC PREFLIGHT (Stage 1)
    |
    +---> Validate schema and issue type
    |
    +---> Verify raw response file and SHA-256
    |
    v
Validated Evidence Contract
(normalized, runtime-neutral, ready for analysis)
    |
    v
AGENTIC ANALYSIS (Stage 2)
(current LLM context analyzes evidence)
    |
    +---> Explicit requirements
    |
    +---> Inferred requirements
    |
    +---> Constraints & dependencies
    |
    +---> Ambiguities & unknowns
    |
    +---> Key concepts
    |
    v
Analysis JSON
(produced by current agent/LLM)
    |
    v
DETERMINISTIC POSTFLIGHT (Stage 3)
    |
    +---> Validate analysis schema
    |
    +---> Verify evidence exists in cited fields
    |
    +---> Preserve provenance
    |
    v
requirements-analysis.json
(validated, persisted to workspace)
    |
    v
Ready for capability impact assessment
(separate downstream stage)
```

**Key principles:**

> Retrieval is deterministic; evidence extraction is deterministic; interpretation is agentic (uses current LLM context); validation is deterministic; capability assessment is deliberate and separate.

Retrieval follows deterministic code paths, using an explicit issue key and field allow-list. Given the same raw Jira response and normalisation parameters, the normalised requirements content is reproducible. Retrieval timestamps and provenance metadata will vary between retrieval events.
Interpretation — understanding what the requirements mean and designing the architecture — is agentic (can use LLMs, reasoning, standards, etc.). The two are separate concerns.

## 9. Using the Claude Code Skill

If you have Claude Code 2.1.110+ and the `barclays-buk-solution-architect` plugin installed, you can use the `understand-requirements` skill to orchestrate the full requirements workflow (retrieval, validation, and understanding).

For detailed operational definition, see:

- `skills/understand-requirements/SKILL.md`

For validation and review of requirements.json files:

- `skills/review-requirements/SKILL.md`

These files define the exact parameters, output format, and error handling for skill-based invocation. See the SKILL.md files linked above for the authoritative interface contracts.

## 10. Troubleshooting

### `export is not recognised` / `command not found`

Your terminal is PowerShell, not bash. Use the PowerShell syntax documented in section 3:

```powershell
$env:JIRA_AUTH_TOKEN = "YOUR-JIRA-TOKEN"
```

### `JIRA_AUTH_TOKEN is not set`

The script requires the environment variable to be set before execution. Use the safe verification command from section 3:

```bash
echo "${JIRA_AUTH_TOKEN:+JIRA_AUTH_TOKEN is set}"
```

If the output is empty, set the token and try again.

### `Jira API returned HTTP 0`

This means no valid HTTP response was received. The reported curl stderr should contain diagnostic information (network error, certificate error, etc.). Use the verification commands to help diagnose:

```bash
python scripts/retrieve_jira_requirements.py \
  --issue-key TEST-1 \
  --allowed-fields summary 2>&1 | grep -i "curl stderr" || echo "No curl error message"
```

### `schannel: CRYPT_E_NO_REVOCATION_CHECK`

This is a Windows Schannel certificate revocation check failure. Retry with `--ssl-no-revoke`:

```powershell
python scripts/retrieve_jira_requirements.py `
  --issue-key BUKL2CUSX-173655 `
  --allowed-fields summary,description,labels,components,status,issuetype,issuelinks `
  --ssl-no-revoke
```

**Do not use `-k`, `--insecure`, or disable certificate validation.** The `--ssl-no-revoke` flag skips only the revocation check, not certificate validation.

### `Jira API returned HTTP 401` or `HTTP 403`

Authentication failed or access denied. Check:

- Is your Jira personal access token current? Generate a new one if it has expired: https://estjira.barcapint.com/secure/ViewProfile.jspa
- Are you authorised to view this Jira issue? Verify with a colleague or your project lead.

**Do not paste your token into logs, chat, or support requests.** If you believe your token is exposed, rotate it immediately.

### `No output directory specified` or missing workspace

The retrieval script requires an external workspace directory. You must provide one of:

- `--output-dir <path>` command-line parameter
- `BUK_SA_WORKSPACE=<path>` environment variable

Check that your workspace directory exists and is writable:

```bash
mkdir -p ~/buk-sa-workspace
chmod u+w ~/buk-sa-workspace
```

Then retry with:

```bash
export BUK_SA_WORKSPACE=~/buk-sa-workspace
python scripts/retrieve_jira_requirements.py ...
```

### `[Errno 13] Permission denied` when writing to workspace

The process does not have permission to create or write files in your workspace directory. Check that:

- The workspace directory exists and is writable
- Your user account has write permission on the workspace
- No other process has locked the workspace directory

## 10. Current Scope & Limitations

### Currently Implemented

1. ✓ **Deterministic Jira Business Epic retrieval** with SHA-256 provenance
2. ✓ **Deterministic normalisation** to requirements.json
3. ✓ **Requirements understanding** — LLM analyzes Business Epic, distinguishes explicit from inferred requirements
4. ✓ **Evidence traceability** — all requirements cite supporting Jira fields with deterministic validation
5. ✓ **Capability impact assessment** (BUKL3BBA-1465) — Consumes requirements understanding, evaluates against BUK capability model, produces structured findings

### Current Limitations

- **One issue at a time**: The retrieval script accepts a single Jira issue key per invocation.
- **Explicit field allow-list**: You must specify which fields to retrieve. There is no "retrieve all fields" option; this is intentional (explicit is safer than implicit).
- **Acceptance criteria require configuration**: If you want to retrieve a custom Jira field, you must know its field ID (e.g. `customfield_12345`).
- **No LLM in retrieval or normalisation**: These steps are deterministic code only. Only the requirements understanding and capability assessment stages use LLM.
- **Full capability model not yet available**: Capability Impact is proven with representative domain (retail-and-business-loan.yml). Full 33-domain model will be integrated when available.
- **No Architecture Significance assessment**: Architecture Significance rules exist but implementation is planned separately.
- **No Domain Model or Town Plan integration**: Integration with domain model assessment and town plan harmonisation are planned as separate stages.
- **No Technical Impact assessment**: Technical (infrastructure, technology, operational) impact assessment is planned separately.
- **No architecture design decisions**: These stages understand requirements and assess capability impact; they don't design solutions.

## 12. Protecting generated data

Generated artefacts (raw Jira responses and `requirements.json`) are stored in your external workspace directory (configured via `--output-dir` or `BUK_SA_WORKSPACE`), **not in the Git repository**. This ensures runtime data and governed source code remain separate.

### Workspace storage

Your generated files are at:

```
$BUK_SA_WORKSPACE/
├── raw/
│   └── BUKL2CUSX-173655.json          (unmodified Jira API response)
└── requirements/
    └── BUKL2CUSX-173655.json          (normalised requirements with provenance)
```

These files are under your workspace, not under the Git repository root. They will never be committed to version control unless you explicitly choose to copy them elsewhere.

### Information handling

Generated artefacts may contain internal Jira requirements and must be treated according to your organisation's information classification policy.

- **Retention:** Follow your organisation's document retention policy for the workspace location
- **Sharing:** If you need to move or share generated files, follow your information security and legal team's guidance for the applicable classification
- **Archival:** Archive or delete the workspace when you no longer need the artefacts

---

## Next Steps

Once you have successfully retrieved and reviewed a Jira issue, the `requirements.json` file is ready for requirements understanding:

1. **Run requirements understanding** (Step 8) — Claude analyzes the Business Epic and produces structured `requirements-analysis.json`
2. **Manual review** — Review the analysis to understand explicit vs. inferred requirements, ambiguities, and key concepts
3. **Capability impact assessment** (planned) — Subsequent stage will assess which BUK capabilities are impacted
4. **Architecture design** (planned) — The `solution-architect-agent` will consume the requirements analysis and apply design patterns
5. **Downstream integration** — Security Architect, API Engineer, Data Engineer agents will use the analysis as context

For now, you have completed:
- Deterministic retrieval and normalization (BUKL3BBA-1464)
- Requirements understanding with evidence traceability (BUKL3BBA-1466)

Capability assessment and architecture design are planned as separate stages.
