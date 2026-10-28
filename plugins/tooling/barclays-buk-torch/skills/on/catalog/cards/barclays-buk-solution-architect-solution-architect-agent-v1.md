# barclays-buk-solution-architect-solution-architect-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-solution-architect-solution-architect-agent-v1` |
| Plugin name | `barclays-buk-solution-architect` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-solution-architect@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `REQUIREMENTS_PATH` — path to requirements markdown file (typically the output of product-manager-agent)
- `UX_DESIGN_PATH` — path to UX design markdown file (output of ux-designer-agent), or `"none"`
- `EXISTING_ARCH_PATH` — path to existing architecture docs or ADRs, or `"none"`
- `TECH_STACK` — known technology constraints, e.g. `"Java 21 / Spring Boot 3.4.5"` or `"Node/Express"`
- `OUTPUT_PATH` — absolute path where the architecture document should be written

## Preconditions

- `REQUIREMENTS_PATH` must exist and be readable; if absent, architecture will be derived from additional context only and limitations stated in Flags
- The plugin must be installed: `/plugin install barclays-buk-solution-architect@barclays-cio-buk`

## Expected outputs

1. Structured architecture markdown document at `OUTPUT_PATH` containing:
   - Solution overview: one-paragraph description, key architectural decisions, alignment to existing patterns
   - Mermaid component diagram with all system components, data flows, external integrations, and trust boundaries
   - Component breakdown: responsibility, technology rationale, interfaces, and dependencies for each new or modified component
   - NFR table covering performance, availability, scalability, security, observability, and data retention
   - Security guardrails: authentication/authorisation model, data classification, encryption requirements, API security
   - API design principles for any new APIs: naming conventions, versioning strategy, error response shape, OpenAPI spec requirement
   - Technical risks and guardrails table
   - Architecture Decision Records (ADRs) for each significant decision

## Exclusions

- Does not provision infrastructure, create Kubernetes manifests, or trigger delivery pipelines
- Does not produce functional requirements or acceptance criteria — that is the product manager's responsibility
- Does not implement code or generate API specifications in code form
- Does not perform security reviews — that is the security architect's responsibility
- Does not make final technology choices without stating alternatives considered when inputs are ambiguous

## Verification

Check that `OUTPUT_PATH` exists and contains all eight sections. Confirm the Mermaid diagram is syntactically valid and includes trust boundaries, the NFR table covers all six categories, and at least one ADR is documented per significant decision. Security guardrails must reference authentication/authorisation model and data classification. Any placeholder skills, missing inputs, or decisions made under uncertainty should appear in the Flags section.
