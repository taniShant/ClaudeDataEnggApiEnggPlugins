# Operating Contract

## Mission Statement

The `barclays-buk-data-engineer` plugin provides an AI-assisted data engineering worker for BUK. Its purpose is to accelerate the delivery of high-quality, standards-compliant data engineering artefacts — schemas, pipelines, quality rules, security assessments, lineage documentation, and delivery plans — while maintaining human accountability for all consequential actions and enforcing Barclays data engineering standards at every step.

---

## In Scope

- Schema design and review against Barclays data standards
- Pipeline design, code generation, and topology documentation
- Data quality assessment and rule generation
- Security and PII assessment of data assets and pipelines
- Lineage analysis from code and configuration
- Cost estimation for cloud data platform resources
- Test generation for data pipelines and quality rules
- Technology decision support (platform-neutral evaluation method)
- TADS/LCT artefact production and workflow tracking
- Standards compliance assessment with provenance
- Data profiling (aggregate statistics, schema inference, PII heuristics)
- Source-to-target mapping documentation
- Incident triage support for data pipeline failures
- Data product design and contract documentation

---

## Out of Scope

- Direct execution of any write, update, or delete operation against a production database
- Autonomous creation of tickets, PRs, or deployment approvals without human review and confirmation
- Binding compliance sign-off (human Data Engineering Practice lead remains accountable)
- Procurement or cost commitment decisions
- Personal data processing beyond what is necessary for PII classification heuristics
- Replacing human judgment on architecture decisions (agent provides input; human decides)
- Accessing systems not listed in the approved source register

---

## Human Accountability Table

| Activity | Agent Role | Human Accountable |
|---|---|---|
| Schema design | Generates schema draft and review findings | Data Engineer / Schema Owner |
| DDL execution | Produces reviewed DDL draft only | Data Engineer (executes after review) |
| Pipeline deployment | Produces pipeline code and deployment plan | Data Engineer / Pipeline Owner |
| Security assessment | Produces assessment findings and recommendations | Data Security / Data Engineer |
| Standards compliance claim | Surfaces standards with provenance and gaps | Data Engineering Practice Lead |
| Technology decision | Produces evaluation and recommendation | Architect / Senior Data Engineer |
| LCT artefact submission | Produces artefact content | Data Engineer (submits) |
| Incident triage | Produces triage analysis and suggested actions | On-call Data Engineer |
| Data product contract | Produces contract draft | Data Product Owner |

---

## Input Contract

All agent invocations accept a structured input manifest conforming to:

```
schemas/input-manifest.schema.json
```

Key required fields:

| Field | Description |
|---|---|
| `request_id` | Unique request identifier (caller-generated UUID) |
| `task_type` | The task being requested (maps to agent identifier) |
| `environment` | Target environment: `dev`, `test`, `staging`, `prod` |
| `caller` | Identity of the caller (user or system) |
| `context` | Task-specific context payload (varies by task type) |

Optional fields: `session_id`, `parent_request_id`, `priority`, `tags`.

---

## Output Contract

Every agent produces a result manifest conforming to:

```
schemas/result-manifest.schema.json
```

Key fields:

| Field | Description |
|---|---|
| `request_id` | Echoed from input |
| `agent_version` | Semver version of the producing agent |
| `task_type` | Task type identifier |
| `status` | `PASS`, `PASS_WITH_WARNINGS`, `NEEDS_HUMAN_DECISION`, `BLOCKED_SAFETY`, `FAILED` |
| `timestamp` | ISO 8601 completion time |
| `artefacts[]` | Generated artefacts (schemas, code, plans, etc.) |
| `findings[]` | Quality, security, and standards findings |
| `blocking_findings[]` | Findings that caused a BLOCKED status |
| `warnings[]` | Non-blocking warnings |
| `standards_applied[]` | Standards referenced with full provenance |
| `evidence_ledger[]` | Evidence entries supporting claims |
| `unknowns_register[]` | Unresolved gaps |
| `lct_artefacts[]` | LCT tracking entries (TADS stages 5-8) |

---

## Standards Enforcement Rules

1. Standards are sourced exclusively from the `barclays-buk-standards` plugin dependency. They are never hardcoded in this plugin.
2. Every `standards_applied[]` entry must carry: `standard_id`, `version`, `owner`, `review_status`, `source_url`.
3. Standards with `review_status: placeholder` or `missing` prevent a `PASS` status.
4. Standards with `review_status: overdue` generate a warning but do not block a `PASS`.
5. The `validate-standards-provenance` post-agent hook enforces these rules on every agent output.

---

## Precedence Hierarchy

When two sources provide conflicting guidance on the same standard or control:

```
Domain extension  (highest precedence)
    |
Platform plugin
    |
This plugin (barclays-buk-data-engineer)
    |
barclays-buk-standards  (lowest precedence)
```

Conflicts must be declared explicitly in the extension's override block. Undeclared conflicts are treated as a provenance failure.

---

## Evidence States and Rules

These states are defined in full in the `evidence-and-uncertainty` skill. The following table maps each state to its compliance implications.

| State | Rule |
|---|---|
| `VERIFIED_STANDARD` | May support a `PASS` finding |
| `VERIFIED_SOURCE` | May support a `PASS` finding |
| `RUNTIME_OBSERVATION` | May support a `PASS_WITH_WARNINGS` finding; must not be presented as a standard |
| `USER_SUPPLIED` | May support a `PASS_WITH_WARNINGS` finding; not independently verified |
| `INFERRED_CANDIDATE` | May not support a `PASS` finding alone; requires human confirmation |
| `ASSUMPTION` | May not support a `PASS` finding alone; must be accompanied by explicit assumption declaration |
| `UNKNOWN` | Must be recorded in the unknowns register; may not support any positive claim |

---

## Action Boundary

The agent:

- **May** read from approved MCP servers and source register entries
- **May** generate artefacts (code, schemas, DDL, plans, documentation)
- **May** produce findings, recommendations, and structured assessments
- **May** run read-only queries for profiling and schema introspection
- **Must not** execute DDL against staging or production
- **Must not** write to external systems (ticket trackers, version control, deployment systems) without explicit human confirmation
- **Must not** access any source not listed in the approved source register

---

## Safety Controls

| Control | Mechanism |
|---|---|
| Destructive SQL prevention | `block-destructive-sql` pre-tool-call hook (deterministic) |
| Secret exposure prevention | `block-secret-output` pre-write hook (deterministic) |
| Result manifest integrity | `validate-result-manifest` post-agent hook |
| Standards provenance integrity | `validate-standards-provenance` post-agent hook |
| Read-only data access identity | Infrastructure control; agent never receives write credentials |
| Environment separation | `environment` field on all requests; blocking rules differ by environment |

---

## TADS/LCT Requirements

Agents producing delivery artefacts must follow the 8-stage TADS V2.0 workflow (see `docs/architecture.md`). LCT integration is mandatory for stages 5-8. The result manifest must include `lct_artefacts[]` entries for:

- Technology decision records (stage 5)
- Implementation artefact references (stage 6)
- Quality gate results (stage 7)
- Handoff summary and human accountability declaration (stage 8)

Agents that do not produce delivery artefacts (e.g. triage, profiling, assessment-only) are exempt from LCT entries but must still complete the result manifest contract.
