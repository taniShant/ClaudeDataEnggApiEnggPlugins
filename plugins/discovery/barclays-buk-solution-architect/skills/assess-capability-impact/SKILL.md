---
name: assess-capability-impact
user-invocable: true
description: >
    Assess which BUK capabilities are impacted by a change. Consumes validated requirements understanding
    and authoritative capability model to produce structured, traceable capability impact findings.
    Distinguishes direct, inferred, and possible impacts with explicit uncertainty representation.
---

# Assess Capability Impact

> **Source:** BUK Domain Model
> **Owner:** BUK Architecture Practice
> **Review trigger:** When the BUK Domain Model or capability impact assessment contract changes
> **Status:** Draft
> Source documents are Restricted — Internal.

Analyze validated requirements understanding against the authoritative BUK capability model to produce structured capability impact findings: which capabilities are affected, in which domains, what is the evidence classification, and where uncertainty remains.

## Workflow Overview

The capability impact assessment follows a three-stage deterministic-agentic-deterministic pattern:

```
Stage 0: Prerequisite Orchestration (Deterministic)
  → Validates workspace configuration
  → Determines whether assessment required
  
Stage 1: Preflight Validation (Deterministic)
  → Validates requirements-analysis.json schema and provenance
  → Loads authoritative capability model from knowledge/domains/*.yml
  → Validates model integrity and hierarchy
  → Computes model fingerprint
  → Extracts authoritative capability catalogue
  
Stage 2: Capability Assessment (Agentic)
  → Analyzes requirements against capabilities
  → Determines impact classification (direct/inferred/possible)
  → Articulates rationale and uncertainty
  → Cites requirement evidence
  
Stage 3: Postflight Validation (Deterministic)
  → Validates findings schema and structure
  → Verifies all capability and requirement references
  → Checks consistency with model
  → Persists validated findings to workspace
```

## Quick Start

This skill assesses capability impact for requirements from either Jira or PRD/Brief sources.

**Prerequisites:**
- Requirements understanding has been completed (produces `requirements-analysis.json`)
- Capability model files exist at `plugins/discovery/barclays-buk-solution-architect/knowledge/domains/`

**Workspace Paths:**

For Jira sources:
```
<invocation-dir>/<issue_key>/analysis/requirements-analysis.json
```

For PRD/Brief sources (no Jira issue key):
```
<invocation-dir>/analysis/requirements-analysis.json
```

The invocation directory is the work-item boundary. For PRD/Brief demand, the invocation directory IS the root.

**Critical:** 
- Capability Impact does NOT access Jira
- No `--ssl-no-revoke` or other network configuration needed
- No Jira credentials required
- Works entirely offline with pre-fetched requirements
- **Consumes the VALIDATED Requirements Understanding OUTPUT** (`requirements-analysis.json`), not raw retrieval data
- Supports schema v2.0 with both Jira and PRD/Brief sources

**Exact Workflow Stages:**

1. **Stage 1 (Deterministic Preflight):**
   - Invoke with requirements-analysis.json from Requirements Understanding:
     - Jira: `<invocation-dir>/<issue_key>/analysis/requirements-analysis.json`
     - PRD/Brief: `<invocation-dir>/analysis/requirements-analysis.json`
   - Load and validate capability model YAML files from `knowledge/domains/`
   - Extract authoritative capability catalogue
   - Provide exact output schema to agentic stage
   - Return candidate_findings_path (where Stage 2 writes) and output_schema_path (for agentic reference)
   - Prepare context for agentic analysis

2. **Stage 2 (Agentic Assessment):**
   - Analyze each requirement against the model
   - Determine which capabilities are affected
   - Classify impact as direct (explicit), inferred (logical consequence), or possible (judgment required)
   - Document rationale for each impact
   - Surface explicit uncertainty where evidence is insufficient
   - Preserve unratified architectural decisions from source evidence (mark RED if architectural patterns are present without explicit ratification)
   - Persist findings to the candidate_findings_path provided by Stage 1 using the helper mechanism

3. **Stage 3 (Deterministic Postflight):**
   - Validate findings structure and schema
   - Verify all capability IDs exist in model with correct names and hierarchy
   - Verify all requirement IDs exist in requirements-analysis.json
   - Check hierarchy consistency
   - Persist validated findings (source-neutral paths):
     - Jira: `<invocation-dir>/<issue_key>/capability-impact/capability-impact-analysis.json`
     - PRD/Brief: `<invocation-dir>/capability-impact/capability-impact-analysis.json`

**Note:** There is NO separate Stage 0 orchestration mode. This skill directly invokes Stage 1 preflight with the Requirements Understanding path.

---

## Workflow Details

### Important: No Jira Network Access Required

**Capability Impact does NOT access Jira.** It consumes pre-fetched, validated requirements understanding. Therefore:
- ✓ No Jira credentials needed
- ✓ No SSL/network configuration required
- ✓ No `--ssl-no-revoke` or similar network flags needed
- ✓ Works offline once requirements-analysis.json is available

### Stage 1 Preflight Invocation

**Requirement:** Capability Impact consumes the **validated Requirements Understanding output**, not requirements.json or any earlier source-normalisation artefact.

**Command (Jira source):**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assess_capability_impact.py" \
  --mode preflight \
  --requirements-path <invocation-dir>/<issue_key>/analysis/requirements-analysis.json \
  --capability-model-dir "${CLAUDE_PLUGIN_ROOT}/knowledge/domains" \
  --invocation-dir <invocation-dir>
```

**Command (PRD/Brief source):**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assess_capability_impact.py" \
  --mode preflight \
  --requirements-path <invocation-dir>/analysis/requirements-analysis.json \
  --capability-model-dir "${CLAUDE_PLUGIN_ROOT}/knowledge/domains" \
  --invocation-dir <invocation-dir>
```

**Preflight Output (Jira):**

```json
{
  "issue_key": "BUKL2CUSX-173655",
  "requirements_path": "/path/to/workspace/BUKL2CUSX-173655/analysis/requirements-analysis.json",
  "requirements_sha256": "...",
  "capability_model_fingerprint": "sha256:...",
  "requirement_ids": ["ER001", "ER002", "IR001", ...],
  "capability_catalogue": { "cap.xxx.yyy": {...}, ... },
  "candidate_findings_path": "/path/to/workspace/BUKL2CUSX-173655/capability-impact/candidate-capability-impact.json",
  "output_schema_path": "/absolute/path/to/capability_impact.schema.json"
}
```

**Preflight Output (PRD/Brief):**

```json
{
  "issue_key": null,
  "requirements_path": "/path/to/workspace/analysis/requirements-analysis.json",
  "requirements_sha256": "...",
  "capability_model_fingerprint": "sha256:...",
  "requirement_ids": ["ER001", "ER002", "IR001", ...],
  "capability_catalogue": { "cap.xxx.yyy": {...}, ... },
  "candidate_findings_path": "/path/to/workspace/capability-impact/candidate-capability-impact.json",
  "output_schema_path": "/absolute/path/to/capability_impact.schema.json"
}
```

The `requirements_path`, `candidate_findings_path`, and `output_schema_path` are provided for agent reference.

---

### Stage 1: Preflight Validation (Deterministic)

**Input:**
- `requirements-analysis.json` (from Requirements Understanding)
- Capability model YAML files from `knowledge/domains/`

**Validation Checks:**
- ✓ requirements-analysis.json schema version 1.0 or 2.0
- ✓ Source provenance present (raw_jira_response_sha256 for v1.0, source_evidence array for v2.0)
- ✓ All required requirement sections present (explicit_requirements, inferred_requirements, constraints_and_dependencies, ambiguities_and_unknowns, key_concepts)
- ✓ Capability model schema version 1.0
- ✓ All domain, sub-domain, capability IDs follow expected format
- ✓ No duplicate capability IDs across all domains
- ✓ Hierarchy is internally consistent
- ✓ Model fingerprint is deterministic and reproducible
- ✓ Source-neutral path handling (supports Jira with issue_key and PRD/Brief without issue_key)

**Output:**
- Validated requirements data
- Authoritative capability catalogue (id → {name, domain, subdomain, hierarchy, description})
- Model fingerprint (SHA-256)

---

### Stage 2: Capability Assessment (Agentic)

**IMPORTANT: Read the Output Schema First**

Before analyzing, you MUST read the exact output contract:

```
${CLAUDE_PLUGIN_ROOT}/scripts/schemas/capability_impact.schema.json
```

This schema defines EXACTLY what your findings must contain. Postflight validation will reject any findings that do not conform to this schema. Validate against this schema BEFORE writing the candidate findings, not after.

**Input:**
- Validated requirements from Stage 1
- Authoritative capability catalogue from Stage 1
- Full capability model for semantic reasoning
- **Exact output schema** (read above)

**Your Task:**

Analyze each requirement and determine which capabilities are affected. Your findings MUST conform to the capability_impact.schema.json schema.

For each affected capability, produce a finding containing:
- Capability ID (from model, not invented)
- Capability name (exact match from model)
- Domain and sub-domain (from model hierarchy)
- Impact classification: `direct` | `inferred` | `possible`
  - **direct**: Requirement explicitly names or directly describes the capability
  - **inferred**: Requirement outcome logically implies capability execution
  - **possible**: Capability may be touched but requires architectural judgment
- Impacted requirement IDs (one or more)
- Rationale explaining the relationship
- Supporting evidence citations (requirement_id → evidence_id mapping)
- Explicit uncertainty (if any)
- Potential boundary effects (if any)
- Cross-domain effects (if any)

**Critical Rules:**

**What to Include:**
- Capability IDs and names ONLY from the supplied authoritative model — never invented
- Hierarchy (domain → sub-domain → capability) ONLY from the model — never guessed or reasoned
- Every finding must cite ≥1 requirement
- Rationale must articulate the semantic connection (not just terminology similarity)
- Explicit uncertainty represented (not hidden in status or fields)

**What NOT to Do:**
- Do NOT invent domain, sub-domain, or capability names/IDs not in the supplied model
- Do NOT suggest or propose names for missing capability areas
- Do NOT format unmatched requirement concerns as proposed "Dispute Resolution domain" or "Fraud Management domain"
- Do NOT map a requirement to a capability just because terminology is similar or adjacent
- Do NOT force a requirement onto the nearest semantically similar capability if it's not actually a good match
- Do NOT generate negative findings ("capability not affected") from missing evidence
- Do NOT perform keyword matching — reason semantically with HIGH threshold for matching
- Do NOT generate findings simply because wording is analogous or workflows are similar
- Do NOT score significance or determine governance routes (downstream responsibility)

**Distinguishing Authoritative Names from Subject Matter Descriptions:**

When the supplied model lacks capabilities sufficiently aligned to requirements:
- ✓ DO describe the unmatched requirement subject matter neutrally (e.g., "fraud/dispute case management concerns")
- ✗ DO NOT format or present these as proposed domain or capability names
- ✗ DO NOT use phrasing like "missing Dispute Resolution domain" or "should add Fraud Management capability"
- Instead use: "The supplied model does not contain capabilities sufficiently aligned to [describe subject matter neutrally without inventing model entity names]"

Example:
- ✗ INCORRECT: "Fraud Management domain (proposed)" or "Missing: Customer Service Operations"
- ✓ CORRECT: "Fraud/dispute case-management and colleague case-visibility concerns are not sufficiently aligned to any supplied capability"

**Valid Assessment Outcomes:**
- An assessment MAY contain many findings (all requirements affect multiple capabilities)
- An assessment MAY contain a few findings (requirements only affect specific capabilities)
- An assessment MAY contain ZERO findings (no supplied capabilities are sufficiently supported by the requirements)
- If requirements appear relevant to capability areas NOT present in the supplied model, represent this as UNCERTAINTY with explicit explanation of missing model coverage

**Model Completeness:**
- If you observe that relevant capability areas appear absent from the supplied model set, explicitly represent this in the uncertainties section
- Do NOT invent what the missing capabilities might be called
- Do NOT guess the identifiers for missing domains/capabilities
- Do NOT format unmatched concerns as proposed capability names or structured entities
- Do describe unmatched concern areas neutrally and factually, referencing ONLY what the supplied model DOES contain
- Example (CORRECT): "Fraud/dispute case-management and colleague interaction concerns are not sufficiently aligned to capabilities in the supplied Retail and Business Loan domain model"
- Example (INCORRECT): "Missing Dispute Resolution domain and Fraud Management domain" — do not invent these as proposed entities

**Persisting Candidate Findings:**

Write findings to the `candidate_findings_path` provided by Stage 1 preflight. Use the provided helper script for deterministic, cross-platform persistence:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/persist_capability_findings.py" \
  --output-path {candidate_findings_path}
```

The helper reads JSON from stdin and writes it safely with proper encoding:

```bash
# Construct findings JSON, then pipe to helper
cat <<'EOF' | python "${CLAUDE_PLUGIN_ROOT}/scripts/persist_capability_findings.py" --output-path {candidate_findings_path}
{
  "schema_version": "1.0",
  "assessment_type": "capability_impact",
  "assessment_status": "completed | completed_with_uncertainties",
  "input_provenance": {
    "requirements_path": "{requirements_path}",
    "requirements_sha256": "{requirements_sha256}",
    "capability_model_fingerprint": "{capability_model_fingerprint}",
    "assessment_generated_at": "ISO 8601 timestamp"
  },
  "findings": [ ... ],
  "domain_summary": [ ... ],
  "cross_domain_analysis": { ... },
  "uncertainties": [ ... ]
}
EOF
```

The helper:
- Validates JSON syntax before writing
- Creates parent directories as needed
- Uses UTF-8 encoding (Windows/POSIX compatible)
- Returns status as JSON for verification

**Finding structure:**

```json
{
  "schema_version": "1.0",
  "assessment_type": "capability_impact",
  "assessment_status": "completed | completed_with_uncertainties",
  "input_provenance": {
    "requirements_path": "...",
    "requirements_sha256": "(from Stage 1)",
    "capability_model_fingerprint": "(from Stage 1)",
    "assessment_generated_at": "ISO 8601 timestamp"
  },
  "findings": [
    {
      "id": "CAP-001",
      "capability_id": "cap.rbl.originate-loan-accounts",
      "capability_name": "Originate Loan Accounts",
      "capability_domain": "dom.retail-and-business-loan",
      "capability_subdomain": "sub.rbl.loan-account-opening",
      "impact_classification": "direct | inferred | possible",
      "impacted_by_requirement_ids": ["ER001", "IR002"],
      "rationale": "Requirement ER001 explicitly requests new account origination...",
      "supporting_evidence": [
        {
          "requirement_id": "ER001",
          "evidence_id": "description:0",
          "evidence_field": "description"
        }
      ],
      "uncertainty": null | "Specific articulated uncertainty",
      "boundary_implications": null | "Describes potential boundary effects",
      "cross_domain_effects": null | "Describes cross-domain coupling"
    }
  ],
  "domain_summary": [...],
  "cross_domain_analysis": {...},
  "uncertainties": [...]
}
```

---

### Stage 3: Postflight Validation and Persistence (Deterministic)

**Command invoked by skill:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/assess_capability_impact.py" \
  --mode postflight \
  --requirements-path $REQUIREMENTS_PATH \
  --capability-model-dir "${CLAUDE_PLUGIN_ROOT}/knowledge/domains" \
  --findings-path $CANDIDATE_FINDINGS_PATH \
  --workspace $BUK_SA_WORKSPACE
```

**Validation Checks:**
- ✓ Finding schema is valid
- ✓ All requirement IDs exist in requirements-analysis.json
- ✓ All capability IDs exist in capability model
- ✓ Capability names match model exactly
- ✓ Domain/sub-domain hierarchy matches model exactly
- ✓ Evidence IDs have correct format (field:index)
- ✓ Evidence fields are recognized (summary, description, labels, etc.)
- ✓ Evidence classification is valid (direct, inferred, possible)
- ✓ Provenance is complete (SHA-256 references preserved)

**If Validation Passes:**
- Persists findings to: `${BUK_SA_WORKSPACE}/capability-impact/{issue_key}/capability-impact-analysis.json`
- Returns success with findings count and affected domains

**If Validation Fails:**
- Reports precise error and fails the postflight stage
- Candidate findings are preserved for review

---

## What This Workflow Does

✓ Consumes validated requirements understanding  
✓ Loads authoritative capability model  
✓ Assesses which capabilities are impacted  
✓ Distinguishes direct, inferred, and possible impacts  
✓ Provides explicit rationale and evidence citations  
✓ Surfaces uncertainties without hiding them  
✓ Preserves provenance (requirements SHA-256 + model fingerprint)  
✓ Validates findings deterministically before persistence  

---

## What This Workflow Does NOT Do

✗ Load Architecture Significance rules (that's downstream)  
✗ Score significance or determine governance routes  
✗ Perform keyword matching (uses semantic analysis)  
✗ Invent capability IDs or redefine hierarchy  
✗ Generate negative findings from missing evidence  
✗ Assess Technical Impact (separate specialist assessment)  
✗ Make architecture decisions (reports facts for downstream review)  

---

## Guarantees

- **No LLM calls except in Stage 2** — Stages 0, 1, and 3 are deterministic
- **Authoritative model is the only source of capability definitions** — IDs, names, and hierarchy are not invented
- **Evidence traceability** — Every finding links to requirements and requirements link to Jira evidence
- **Explicit uncertainty** — Gaps in evidence are articulated, not hidden
- **Deterministic validation** — Postflight rejects malformed, inconsistent, or invented capability references
- **Provenance preserved end-to-end** — Requirements SHA-256 and model fingerprint are carried through

---

## Error Handling

**If Stage 1 Preflight Fails:**

The skill exits with a precise error message describing the validation failure. Fix the underlying condition (e.g., ensure requirements-analysis.json is valid, ensure capability model files are present and well-formed) and retry.

**If Stage 2 Analysis Cannot Complete:**

Report the error clearly. This typically indicates:
- Requirements understanding is incomplete or malformed
- Capability model is corrupted or missing
- Workspace configuration is invalid

**If Stage 3 Postflight Fails:**

The candidate findings have a structural problem. Check the error message for the specific failure (e.g., unknown capability ID, requirement reference not found, hierarchy mismatch) and revise the findings.

---

## Workflow Status

**Schema Version:** 1.0  
**Assessment Type:** capability_impact  
**Assessment Status Values:** completed | completed_with_uncertainties | failed  

---

## Configuration

The following environment variables control workflow execution:

- `BUK_SA_WORKSPACE` — External workspace directory (required)
- Capability model files — Located at `plugins/discovery/barclays-buk-solution-architect/knowledge/domains/` (required)

---

## Output Location

Valid capability impact findings are persisted to:

```
$BUK_SA_WORKSPACE/capability-impact/{issue_key}/capability-impact-analysis.json
```

This output is consumed by downstream Architecture Significance assessment.

---

## Key Concepts

**Direct Impact:** Requirement explicitly describes or names the capability. Evidence classification: `direct`

**Inferred Impact:** Requirement outcome logically implies the capability will execute. Evidence classification: `inferred`

**Possible Impact:** Capability is potentially affected but requires architectural judgment to confirm. Evidence classification: `possible`

**Uncertainty:** Explicit acknowledgment that evidence is insufficient to fully determine impact. Recorded as a finding-level property, not hidden in status.

**Evidence Classification:** Distinguishes direct evidence (explicit requirement statements) from inferred (logical consequence) from possible (judgment required). Downstream assessments use this to determine confidence.

---

## Next Steps

Once capability impact findings are persisted:

1. **Manual review** — Review findings for semantic correctness and completeness
2. **Architecture Significance assessment** (downstream) — Applies significance rules to capability impact findings, evaluates domain boundaries, multi-domain effects, and determines governance route
3. **Technical Impact assessment** (downstream) — Separate specialist assessment of technology, infrastructure, and operational impact

The Capability Impact assessment is complete and independent. The output is input to downstream assessments.

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Every capability ID, capability name, domain and sub-domain in the findings exists in the supplied authoritative capability model and matches its hierarchy.
- [ ] Every capability-impact finding cites at least one valid requirement and preserves the supporting evidence reference.
- [ ] Each finding is classified as `direct`, `inferred`, or `possible` using the definitions in this skill, rather than terminology or keyword similarity alone.
- [ ] Uncertainty and insufficient model coverage are explicitly represented without inventing capability names, IDs or hierarchy.
- [ ] The candidate findings conform to `capability_impact.schema.json` and have passed deterministic postflight validation before being treated as the capability-impact output.

---