# barclays-buk-ui-engineer-ui-engineer-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-ui-engineer-agent-v1` |
| Plugin name | `barclays-buk-ui-engineer` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-ui-engineer@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `PROJECT_PATH` — absolute path to the project root; used for platform detection when `PLATFORM` is `"auto"`
- `JIRA_ID` — JIRA ticket identifier for the current task (e.g. `UCG-1234`)
- `PLATFORM` — one of `sdf | ios | android | mca | web | auto`; use `"auto"` to trigger detection from project files
- `UX_DESIGN_PATH` — path to the UX design markdown produced by ux-designer-agent, or `"none"`
- `COPY_PATH` — path to copy markdown produced by copywriter-agent, or `"none"`
- `FIGMA_URL` — Figma design URL, or `"none"`
- `OUTPUT_PATH` — absolute path where output screens and the summary report will be written
- `ADDITIONAL_INPUT` — free-text supplemental instructions, or `"none"`

## Preconditions

- `PROJECT_PATH` must be readable for platform auto-detection (when `PLATFORM` is `"auto"`)
- At least one of `UX_DESIGN_PATH`, `FIGMA_URL`, or `ADDITIONAL_INPUT` should be non-`"none"` to allow screen inference; the agent proceeds and flags the gap otherwise
- Specialist plugins (`barclays-buk-ui-engineer-sdf`, `barclays-buk-ui-engineer-ios`, `barclays-buk-ui-engineer-android`, `barclays-buk-ui-engineer-web`) must be installed for their respective platforms to be delegated to

## Expected outputs

- `{OUTPUT_PATH}/UI_ENGINEER_COMPLETE.md` — summary report listing platform detected, routing decision, screens produced, and standards applied
- `{OUTPUT_PATH}/<ScreenName>.*` — one screen file per screen (only when falling back to direct generation; specialist output is returned directly)

## Exclusions

- Does not generate screen files directly when a specialist plugin exists for the detected platform — delegation is always preferred
- Does not scaffold a new project or install specialist plugins on the caller's behalf
- Does not route to MCA specialist — the MCA platform falls through to direct generation until a specialist exists
- Does not manage Figma token or design asset download

## Verification

Check `{OUTPUT_PATH}/UI_ENGINEER_COMPLETE.md`: confirm the platform detection source is recorded (which file triggered the match), the routing decision is stated (specialist delegated or direct generation), and all produced screens are listed with file paths. If direct generation was used, verify each screen file applies the accessibility and security standards listed in the Flags section.
