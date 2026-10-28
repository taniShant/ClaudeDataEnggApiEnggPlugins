# barclays-buk-product-manager-product-manager-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-product-manager-product-manager-agent-v1` |
| Plugin name | `barclays-buk-product-manager` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-product-manager@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `PROBLEM_STATEMENT` — description of the problem to be solved
- `PRODUCT_NAME` — name of the product or service
- `TARGET_MARKET` — target customer group
- `VULNERABLE_GROUPS` — known vulnerability characteristics, or `"none"`
- `CONSTRAINTS` — budget, timeline, regulatory, or technical constraints, or `"none"`
- `OUTPUT_PATH` — absolute path where the requirements document should be written

## Preconditions

- `PROBLEM_STATEMENT` must be sufficiently scoped to derive user stories; if vague, assumptions will be stated in the Flags section of the output
- The plugin must be installed: `/plugin install barclays-buk-product-manager@barclays-cio-buk`

## Expected outputs

1. Structured requirements markdown document at `OUTPUT_PATH` containing:
   - Problem definition in customer terms
   - Functional requirements as uniquely identified INVEST-conformant user stories with MUST/SHOULD/MAY keywords
   - Acceptance criteria in Given/When/Then format with edge cases
   - MoSCoW prioritisation with rationale and dependency mapping
   - Quantifiable success measures with baseline and target
   - Consumer Duty flags (CDA, CUNA, NAPA, vulnerable customers, fair value)
   - Governance flags (DRA/FRA, Change Control, RAID items, Forum submissions)

## Exclusions

- Does not produce UX designs, journey maps, or wireframes — that is the UX designer's responsibility
- Does not produce architecture or technical design artefacts
- Does not implement code or generate test files
- Does not submit governance artefacts to any system — it identifies and documents triggers only
- Does not make prioritisation decisions without stating assumptions when inputs are ambiguous

## Verification

Check that `OUTPUT_PATH` exists and contains all seven sections. Confirm every user story has a Given/When/Then acceptance scenario, a MoSCoW priority, and functional requirements use MUST/SHOULD/MAY. Confirm Consumer Duty and Governance Flags sections are present and either identify triggered obligations or explicitly state none apply. Any assumptions or gaps should appear in the Flags section.
