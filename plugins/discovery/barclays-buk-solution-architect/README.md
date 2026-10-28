# barclays-buk-solution-architect

> **Status: Draft**

Ensures solutions align to existing BUK design patterns and standards. Produces architecture diagrams, NFRs, and technical guardrails.

## Workflow Position

```
Jira Business Epic
  → Deterministic Jira retrieval
  → Deterministic normalisation
  → Normalised requirements.json + SHA-256 provenance
  → LLM requirements understanding
  → Structured requirements-analysis.json (carries source provenance)
  → Capability impact assessment (BUKL3BBA-1465)
  → Architecture Significance assessment (future stage)
```

## Dependencies

- `buk-standards` — provides `api-design` and `security` skills

## Skills

### Deterministic Requirements Validation

| Skill | Purpose |
|---|---|
| `review-requirements` | Validate requirements.json, verify raw response hash, display provenance and normalized content |

**Key guarantee:** No LLM involvement in validation. Deterministic code + fixtures for testing.

### Requirements Understanding (Agentic)

| Skill | Purpose |
|---|---|
| `understand-requirements` | Three-stage workflow: deterministic preflight validates input; current LLM analyzes requirements; deterministic postflight validates and persists. Produces structured analysis with explicit/inferred requirements, constraints, ambiguities. |

**Key guarantees:**
- Stage 1 & 3 (preflight/postflight): deterministic, testable from CLI, no LLM or API calls
- Stage 2 (analysis): uses current agent/LLM context (no nested API invocations)
- Evidence contract is runtime-neutral
- LLM receives only Business Epic evidence; does NOT receive BUK Capability Model, Domain Model, or architecture standards
- Capability assessment is a separate subsequent stage

## Agents

| Agent | Purpose |
|---|---|
| `solution-architect-agent` | Produces architecture diagrams, NFRs, ADRs, and security/API guardrails |

## Architecture & Runtime Model

### Architectural Boundary

This plugin defines a clear boundary between **source repository** and **runtime workspace**:

| Source Repository | Runtime Workspace |
|---|---|
| Capability and agent definitions | Retrieved Jira source evidence |
| Skill implementations | Normalised requirements.json |
| Automated tests | Run-specific outputs |
| Governed code | User data and ephemeral state |

Runtime artefacts are **never** written to the Git repository. They must be stored externally.

### Quick Start

Set your Jira personal access token:
```bash
export JIRA_AUTH_TOKEN='your-token-here'
# Get token from: https://estjira.barcapint.com/secure/ViewProfile.jspa
```

Set your runtime workspace (see GETTING_STARTED.md for workspace selection):
```bash
export BUK_SA_WORKSPACE=/path/to/external/workspace
```

Understand requirements from a Jira Business Epic:
```bash
python scripts/understand_requirements.py \
  --mode preflight \
  --issue-key BUKL2CUSX-173655 \
  --workspace $BUK_SA_WORKSPACE
```

This orchestrates automatic prerequisite retrieval, validation, and evidence extraction. See GETTING_STARTED.md for the complete workflow.

For full details, see [GETTING_STARTED.md](GETTING_STARTED.md).

### Implementation

**Deterministic Layer** (no LLM, no ambiguity):
- `scripts/retrieve_jira_requirements.py` — HTTP retrieval + deterministic normalisation to `requirements.json`
- `scripts/review_requirements.py` — schema validation, provenance verification, hash integrity check
- Fixtures in `scripts/tests/fixtures/` — deterministic test data (no external dependencies)

**Agentic Layer** (downstream):
- `solution-architect-agent` — consumes `requirements.json` for interpretation and design review
