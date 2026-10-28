---
name: understand-requirements
user-invocable: true
description: >
    Understand requirements from any source: Jira Business Epic, Product Requirement Document (PRD), or Brief.
    Automatically retrieves and normalises evidence, performs structured requirements analysis
    (explicit vs. inferred requirements, constraints, ambiguities, key concepts), and produces validated
    output with full provenance. No manual prerequisite setup required.
---

# Understand Requirements

Analyze requirements from any source — Jira Business Epic, Product Requirement Document (PRD), or Brief —
to produce structured requirements understanding: what change is being requested, what requirements are explicit vs. inferred,
what constraints and ambiguities exist, and what key concepts matter.

## Quick Start

Provide either:

- **Jira route:** The Jira issue key for a Business Epic
- **PRD/Brief route:** Path to a Product Requirement Document (prd.md, prd.json, brief.md, or brief.json)

The orchestration handles evidence retrieval, normalisation, and validation automatically — no manual prerequisite setup required.

**Critical:** Execute commands exactly as shown below using the full `${CLAUDE_PLUGIN_ROOT}` path. Do not convert it to a relative path, do not cd into directories, and do not modify the command structure. Claude Code automatically substitutes `${CLAUDE_PLUGIN_ROOT}` with the installed plugin's absolute path.

The skill will:

1. **Stage 0 (Deterministic Prerequisite Orchestration):**
   - Validate configuration (workspace or invocation directory)
   - Check whether evidence exists in the workspace
   - If absent: retrieve from source (Jira API or local file), save raw response, normalise to requirements.json
   - If present: validate schema and provenance integrity
   - Check whether an existing requirements-analysis.json is current and valid
   - Return a versioned orchestration result with `required_next_action` and analysis status

2. **Conditional Agentic Analysis (if orchestration determines analysis is required):**
   - Extract normalised evidence from requirements.json
   - Analyze to distinguish explicit requirements from reasonable inferences
   - Document constraints, ambiguities, and key concepts
   - Write candidate analysis to the authoritative staging path

3. **Stage 3 (Deterministic Postflight Validation and Persistence):**
   - Validate the candidate analysis structure
   - Verify all evidence citations reference actual source fields
   - Persist the final output to the workspace with provenance preserved

The orchestration result determines whether agentic analysis runs. If valid analysis already exists, it is reused and no retrieval or reasoning occurs.

---

## Workflow Details

### Stage 0: Prerequisite Orchestration (Deterministic)

#### For Jira evidence:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate_prerequisites.py" \
  --issue-key <ISSUE_KEY> \
  --invocation-dir /path/to/workspace
```

**For Windows/corporate environments with SSL issues:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/orchestrate_prerequisites.py" \
  --issue-key <ISSUE_KEY> \
  --invocation-dir /path/to/workspace \
  --ssl-no-revoke
```

#### For PRD/Brief evidence:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/parse_prd_and_brief.py" \
  --prd-path /path/to/prd.md \
  --brief-path /path/to/brief.md \
  --invocation-dir /path/to/workspace
```

Or PRD only (without Brief):

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/parse_prd_and_brief.py" \
  --prd-path /path/to/prd.md \
  --invocation-dir /path/to/workspace
```

**Orchestration Output (versioned JSON contract):**

```json
{
  "schema_version": "1.0",
  "issue_key": "BUKL2CUSCA-790",
  "requirements_path": "/path/to/workspace/BUKL2CUSCA-790/requirements/BUKL2CUSCA-790.json",
  "evidence_status": "retrieved | validated",
  "evidence_sha256": "...",
  "analysis_path": "/path/to/workspace/BUKL2CUSCA-790/analysis/requirements-analysis.json | null",
  "analysis_status": "absent | stale | invalid | reused",
  "required_next_action": "run_analysis | none"
}
```

**Branching Decision:**

- If `required_next_action == "none"`: Existing analysis is valid and current. Return it. **Stop here.**
- If `required_next_action == "run_analysis"`: Proceed to preflight validation and agentic analysis.

---

### Stage 1: Preflight Validation (Deterministic)

When orchestration indicates analysis is required, preflight extracts and validates evidence:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/understand_requirements.py" \
  --mode preflight \
  --requirements-path $REQUIREMENTS_PATH \
  --invocation-dir /path/to/workspace
```

**Preflight Output:**

```json
{
  "issue_key": "BUKL2CUSCA-790",
  "evidence": {
    "issue_key": "...",
    "summary": "...",
    "description": "...",
    "status": "...",
    "labels": [...],
    "components": [...],
    "linked_issues": [...],
    "acceptance_criteria": [...]
  },
  "evidence_units": [
    {
      "id": "description:0",
      "jira_field": "description",
      "source_value": "..."
    },
    ...
  ],
  "candidate_analysis_path": "/path/to/workspace/BUKL2CUSCA-790/analysis/candidate-requirements-analysis.json"
}
```

The `candidate_analysis_path` is the authoritative location where agentic analysis output must be written. This same path is used by postflight to validate and persist the final output.

---

### Stage 2: Requirements Analysis (Agentic)

**Agent Routing:** This stage is executed by the solution architect agent.

To invoke deterministically: Send a message to `barclays-buk-solution-architect:solution-architect-agent` (note the full qualified name with the agent suffix).

**Your task:** Analyze the normalised evidence and produce a structured requirements understanding.

**Input:** The preflight JSON above, containing `evidence` (context for reasoning) and `evidence_units` (citation catalogue).

**Output:** A JSON structure containing:

```json
{
  "change_summary": {
    "outcome": "One-line statement of what change is being requested",
    "rationale": "Why this change is needed (supported by evidence)",
    "supporting_evidence": ["functional_requirements:FR-1", "acceptance_criteria:1"]
  },
  
  "explicit_requirements": [
    {
      "id": "ER001",
      "requirement": "Requirement directly stated in the source",
      "supporting_evidence": ["functional_requirements:FR-1"]
    }
  ],
  
  "inferred_requirements": [
    {
      "id": "IR001",
      "requirement": "Reasonable interpretation not explicitly stated",
      "reasoning": "Why this inference is valid",
      "supporting_evidence": ["functional_requirements:FR-2"]
    }
  ],
  
  "constraints_and_dependencies": [
    {
      "id": "CD001",
      "constraint": "...",
      "is_explicit": true,
      "supporting_evidence": ["functional_requirements:FR-3"]
    }
  ],
  
  "ambiguities_and_unknowns": [
    {
      "id": "AMB001",
      "ambiguity": "Missing or unclear information",
      "impact": "Why this matters",
      "clarification_needed": "What question needs answering?"
    }
  ],
  
  "key_concepts": [
    {
      "concept": "Important concept",
      "definition": "What it means here",
      "supporting_evidence": ["functional_requirements:FR-1"]
    }
  ],
  
  "unratified_architectural_decisions": [
    {
      "id": "UNAD001",
      "proposed_solution": "Specific architecture pattern, technology choice, or design pattern proposed in source",
      "rationale": "Why this solution appears in the source material",
      "supporting_evidence": ["functional_requirements:FR-5"],
      "status": "RED (unratified)",
      "ratification_required": "ADR | KDD | explicit architecture review required",
      "existing_adr_reference": null,
      "downstream_disposition": "Requires architectural review; may be validated, challenged, or replaced by architecture stage"
    }
  ]
}
```

**Evidence Traceability (MANDATORY):**

- **Source-native identifiers are authoritative:** FR-1, FR-2, SM-1, etc. from PRD/Brief, or Jira field:index identifiers
- **Each requirement MUST trace to its source:** A requirement numbered FR-1 must have `supporting_evidence` that includes `functional_requirements:FR-1`, not SM-3 or other unrelated evidence
- **Do not mix evidence types:** Support metrics (SM-*) provide context but cannot replace the authoritative requirement evidence
- **All evidence IDs must exist in the catalogue:** Postflight validates every ID; an ID not in `evidence_units` will cause validation failure

**Boundary Enforcement (MANDATORY):**

This stage extracts **requirements understanding** — what is being asked for and what constraints apply. It does NOT silently approve or promote architectural solutions.

**Critical distinction:** Preserve architectural content from source material. Do NOT discard it. But classify it explicitly.

When requirements-understanding encounters source material that proposes, prescribes, or strongly implies an architectural solution, implementation pattern, technology choice, or material design decision:

1. **Preserve the source statement** with full evidence traceability.
2. **Classify it explicitly** as an unratified architectural decision requiring review.
3. **Do NOT reframe** it as an approved inferred requirement or constraint.
4. **Flag it RED** — unratified means its authority has not been established.
5. **Identify the ratification path**: ADR, KDD, or explicit architecture review required.
6. **Reference authoritative evidence** if an existing ADR/KDD already ratifies the decision — in that case, preserve the ratification status.

Example: If a PRD says "must use circuit breaker pattern", do NOT write:
```
"inferred_requirement": "A circuit breaker must be implemented..."
```

Instead, write:
```
"unratified_architectural_decision": {
  "id": "UNAD001",
  "proposed_solution": "Circuit breaker pattern for Aggregator API resilience",
  "rationale": "PRD FR-5 states if Aggregator API unavailable, graceful degradation required",
  "supporting_evidence": ["functional_requirements:FR-5"],
  "status": "RED (unratified)",
  "ratification_required": "ADR required — circuit breaker is a specific design choice",
  "existing_adr_reference": null
}
```

The source statement remains available for downstream architecture reasoning. But architecture-assessment cannot treat it as settled without explicit ratification.

**Semantic test for inferred requirements:**

For each item you consider adding to explicit_requirements or inferred_requirements, ask:

1. **Is this a demanded outcome?** — "The system must achieve X" (e.g., "respond within 3 seconds")
2. **Is this a binding constraint?** — "The system must obey Y" (e.g., "encrypt data at rest", "comply with ICO rules")
3. **Or is this a proposed design solution?** — "The system should use Z" (e.g., "implement a circuit breaker", "use a DAF orchestration layer")

If (3), move it to unratified_architectural_decisions with RED status and ratification_required field.

If (2) but the constraint is expressed via a specific technology mandate (e.g., "must use OAuth 2.0"), check whether that mandate is **externally imposed** (policy, regulation, platform requirement, or existing ratified architecture). If yes, capture as explicit constraint with authoritative evidence. If no, treat as unratified design decision.

**Critical rules:**

- Write this JSON to **exactly** the path provided in preflight's `candidate_analysis_path` field
- Do not write to a different location
- Do not use /tmp or temporary directories
- Do not invent paths
- Evidence IDs (e.g., "functional_requirements:FR-1") must come from the `evidence_units` catalogue
- Never reproduce source text; let postflight resolve IDs to authoritative values
- For `supporting_evidence` fields, use only the ID strings provided
- Each explicit/inferred requirement must have at least one supporting_evidence reference

---

### Stage 3: Postflight Validation and Persistence (Deterministic)

After the candidate analysis is written to the path established in Stage 1, invoke:

```bash
python "${CLAUDE_PLUGIN_ROOT}/scripts/understand_requirements.py" \
  --mode postflight \
  --requirements-path $REQUIREMENTS_PATH \
  --analysis-path $CANDIDATE_ANALYSIS_PATH \
  --invocation-dir /path/to/workspace
```

Where `$CANDIDATE_ANALYSIS_PATH` is the exact value from preflight's `candidate_analysis_path` field.

**Postflight validates:**
- Schema is correct
- All evidence IDs reference actual source fields
- Explicit/inferred distinction is maintained
- Provenance is intact

**Postflight persists:**
- Final output to: `${INVOCATION_DIR}/${issue_key}/analysis/requirements-analysis.json` (Jira) or `${INVOCATION_DIR}/analysis/requirements-analysis.json` (PRD/Brief)
- Evidence is resolved to authoritative source values
- SHA-256 provenance is preserved

---

## Guarantees

- **No LLM calls except in Stage 2** — Stages 0, 1, and 3 are deterministic
- **No retrieval unless necessary** — Stage 0 determines this; you don't decide
- **No manual prerequisite sequencing** — Orchestration handles all prerequisite decisions
- **Exact evidence traceability** — Every requirement links to normalized source fields
- **Provenance preserved** — Raw response SHA-256 is carried through to final analysis
- **Atomic output** — Final analysis is replaced atomically; previous version preserved on failure
- **Configuration validated early** — Stage 0 fails with precise error if workspace is not accessible

---

## Error Handling

If Stage 0 reports any error:

The skill exits with a precise error message describing the exact condition that requires attention. Read the error message carefully; it will guide you on what to fix (e.g., ensure the workspace directory is accessible, ensure source evidence exists, or provide JIRA_AUTH_TOKEN if Jira retrieval is needed). Do not attempt to repair or work around — fix the underlying condition as described.

If postflight reports analysis validation failure:

The candidate analysis did not meet structural requirements. Check the error message and revise the analysis JSON.

---

## What This Workflow Does

✓ Retrieves evidence from Jira, PRD, or Brief (if not already cached)
✓ Validates requirements schema and provenance
✓ Extracts deterministic evidence catalogue
✓ Enables agentic requirements analysis with traceable citations
✓ Validates analysis structure and evidence integrity
✓ Persists final output with preserved provenance
✓ Enables reuse of valid analysis without re-analyzing

---

## What This Workflow Does NOT Do

✗ Manually determine whether retrieval is required — Stage 0 decides
✗ Manually check environment variables — Stage 0 validates configuration
✗ Perform capability impact assessment — That's a downstream stage
✗ Make architecture/implementation decisions — That's downstream review
✗ Provide confidence scores — Uses evidence and reasoning instead
✗ Propose solutions to ambiguities — Surfaces them neutrally

---

## Implementation Details

Evidence retrieval, requirements normalisation, and analysis are orchestrated automatically by Stage 0. The deterministic components support the workflow with clear stage boundaries and are available for independent testing or debugging via their respective CLI interfaces.

The `understand-requirements` skill coordinates the complete pipeline and manages prerequisite orchestration. Users should invoke this skill rather than manually composing individual steps.

---

## Workspace Layout

Runtime artefacts are stored in the invocation directory:

**For Jira sources (with issue_key):**
```
${INVOCATION_DIR}/${issue_key}/
  raw/${issue_key}.json                   # Exact Jira HTTP response bytes
  requirements/${issue_key}.json          # Normalised requirements with provenance
  analysis/
    candidate-requirements-analysis.json  # Candidate (staging path during analysis)
    requirements-analysis.json            # Final validated output
```

**For PRD/Brief sources (without issue_key):**
```
${INVOCATION_DIR}/
  raw/
    prd.json, brief.json                  # Parsed PRD/Brief documents
  requirements/
    requirements.json                     # Normalised requirements with provenance
  analysis/
    candidate-requirements-analysis.json  # Candidate (staging path during analysis)
    requirements-analysis.json            # Final validated output
```

Never write to the plugin directory. Runtime state remains under the invocation directory (or workspace if explicitly specified).

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Every identified requirement is traceable to source evidence.
- [ ] Explicit requirements and inferred requirements are distinguished according to this skill's rules.
- [ ] Evidence references and source provenance have been preserved.
- [ ] Ambiguities and unknowns are explicitly represented rather than silently resolved.
- [ ] The validated output conforms to the defined requirements-analysis contract.