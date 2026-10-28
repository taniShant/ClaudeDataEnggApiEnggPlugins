# barclays-buk-copywriter-copywriter-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-copywriter-copywriter-agent-v1` |
| Plugin name | `barclays-buk-copywriter` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | local-modification |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-copywriter@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- JOURNEY_NAME (required): Name of the journey or communication being written
- BRIEF (required): Requirements and context from the PM / UX Designer
- COPY_TYPE (required): One of `journey`, `communication`, or `both`
- CHANNEL (required): One of `app`, `web`, `letter`, `email`, `sms`, or `in-app-notification`
- TARGET_MARKET (required): Description of the target customer group
- VULNERABLE_GROUPS (required): Known vulnerability characteristics for this target market, or `"none"`
- OUTPUT_PATH (required): Absolute path where the output copy document should be written

## Preconditions

- OUTPUT_PATH directory must be writable
- BRIEF must contain sufficient context to identify customer goals and key actions
- `barclays-buk-standards` skills (`accessibility`, `consumer-duty`, `vulnerable-customers`, `customer-engagement`, `brand`) must be available; if any are placeholders, the agent reports which checks were skipped

## Expected outputs

- `OUTPUT_PATH/copy.md`: Complete copy document structured by screen/section/message, with Heading, Body, CTA, Error states, Supporting copy, and QA Notes per screen
- A `## QA Notes` section within the copy document flagging fees/charges, CUNA triggers, and regulatory language requiring downstream verification
- A `## Flags` section reporting any placeholder skills, missing inputs, or decisions made under uncertainty

## Exclusions

- Does NOT validate regulatory compliance — that is the responsibility of downstream QA agents
- Does NOT generate UX designs, wireframes, or screen layouts
- Does NOT verify product facts (fees, rates, product names) for accuracy
- Does NOT enforce channel word limits beyond guidance; caller is responsible for final fit-check

## Verification

After execution, verify that `OUTPUT_PATH/copy.md` exists and contains one structured section per screen or message in the journey, each with Heading, Body, CTA, and Error states populated. Confirm the `## QA Notes` section is present and lists any fee/charge disclosures or regulatory language. Check the `## Flags` section for any reported placeholder skills or missing inputs that may affect copy quality.
