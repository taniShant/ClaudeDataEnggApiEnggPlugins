# barclays-buk-ux-designer-ux-designer-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ux-designer-ux-designer-agent-v1` |
| Plugin name | `barclays-buk-ux-designer` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-ux-designer@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `REQUIREMENTS_PATH` — path to requirements markdown file (typically the output of product-manager-agent)
- `CHANNEL` — target channel: `app`, `web`, or `both`
- `TARGET_MARKET` — target customer group
- `VULNERABLE_GROUPS` — known vulnerability characteristics, or `"none"`
- `EXISTING_PATTERNS` — path to existing design patterns or component library docs, or `"none"`
- `OUTPUT_PATH` — absolute path where the UX design document should be written

## Preconditions

- `REQUIREMENTS_PATH` must exist and be readable; if absent, journey will be derived from additional context only and assumptions will be stated in Flags
- The plugin must be installed: `/plugin install barclays-buk-ux-designer@barclays-cio-buk`

## Expected outputs

1. Structured UX design markdown document at `OUTPUT_PATH` containing:
   - Customer research insights relevant to the target market and vulnerable groups
   - 2–3 journey options at high level with flows, decision points, trade-offs, and a recommended option with rationale
   - Detailed journey map for the recommended option: screen name, customer goal, content needed, primary action, error/edge states, and exit points
   - Per-screen accessibility requirements: heading hierarchy, interactive element labels, error state rules, touch targets, screen reader order
   - Consumer Duty considerations per step: key information disclosure, vulnerable customer friction points, support options
   - Copy requirements brief for each screen (tone, key messages, regulatory content flags)

## Exclusions

- Does not produce functional requirements or acceptance criteria — that is the product manager's responsibility
- Does not produce architecture, API contracts, or technical specifications
- Does not implement UI code or Figma assets
- Does not submit Consumer Duty assessments — it identifies design-level considerations only
- Does not make final journey recommendations without stating rationale; ambiguous recommendations are flagged

## Verification

Check that `OUTPUT_PATH` exists and contains all four sections. Confirm the recommended journey option is identified with rationale, each screen in the detailed design has accessibility requirements specified, and Consumer Duty considerations are documented per step. Any placeholder skills, missing inputs, or design decisions under uncertainty should appear in the Flags section.
