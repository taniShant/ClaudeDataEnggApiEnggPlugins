# barclays-buk-drawio-drawio-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-drawio-drawio-agent-v1` |
| Plugin name | `barclays-buk-drawio` |
| Component type | agent-plugin |
| Owner | Vishal Khare (vishal.khare1@barclays.com) |
| Action scope | local-modification |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-drawio@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- TASK (required): One of `Create` or `Update`
- SPEC (required): Diagram description in plain text (for Create) or structured critique feedback listing specific fixes (for Update)
- FILE_PATH (required): Target `.drawio` file path to write (Create) or read and update (Update)
- FIXES (required for Update): Structured critique feedback with specific fixes to apply — may be omitted for Create

## Preconditions

- `barclays-buk-drawio:drawio-style-guide` skill must be available; if it is a placeholder, the agent reports the issue and stops
- For Update: FILE_PATH must point to an existing, valid `.drawio` XML file
- FILE_PATH directory must be writable
- `barclays-buk-standards` dependency must be installed (declared in plugin.json)

## Expected outputs

- A `.drawio` XML file written to FILE_PATH containing well-formed mxGraph XML with all shapes, connectors, and styling applied from the style guide
- A concise text summary returned to the caller listing: components/nodes with their cell IDs, connections (source → target), and the file path written to — raw XML is never returned in the response

## Exclusions

- Does NOT export diagrams to PNG, SVG, PDF, or any other format
- Does NOT return raw draw.io XML in its response (XML is written to file only)
- Does NOT enforce diagrammatic correctness of the content (e.g., whether an architecture accurately reflects the system) — that is the caller's responsibility
- Does NOT perform any Git operations or commit the written file
- Does NOT validate that the diagram meets any specific methodology standard (e.g., BPMN, UML) beyond draw.io XML structural integrity

## Verification

After execution, verify that FILE_PATH exists and contains a valid `.drawio` XML file with the `<mxfile>` → `<diagram>` → `<mxGraphModel>` → `<root>` hierarchy. Open the file in draw.io (app.diagrams.net) or a compatible viewer and confirm all described components and relationships are present, labeled correctly, and styled per the Barclays draw.io style guide. Check the text summary returned by the agent for a complete list of cell IDs and connections.
