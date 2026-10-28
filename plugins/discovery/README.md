# discovery

Plugins covering the upstream product delivery phases — from problem statement through to technical design.

These plugins assist with work that happens before build: capturing requirements, defining user journeys, producing UX designs, writing copy, and establishing the architectural and security foundations.

## Scope

| Discipline | Plugin | Description |
|---|---|---|
| Product Management | `barclays-buk-product-manager` | Requirements, AC, governance flags |
| UX Design | `barclays-buk-ux-designer` | Journey options, UX design, copy brief |
| Copywriting | `barclays-buk-copywriter` | Customer-facing and UI copy |
| Solution Architecture | `barclays-buk-solution-architect` | Architecture diagrams, NFRs, guardrails |
| Security Architecture | `barclays-buk-security-architect` | Threat modelling, security review, compliance |

## Adding a discovery plugin

Follow the naming convention: `barclays-buk-<discipline>` or `barclays-buk-<discipline>-<capability>`

All discovery plugins should declare `"dependencies": ["barclays-buk-standards"]` and load only the skills their agents actually need.
