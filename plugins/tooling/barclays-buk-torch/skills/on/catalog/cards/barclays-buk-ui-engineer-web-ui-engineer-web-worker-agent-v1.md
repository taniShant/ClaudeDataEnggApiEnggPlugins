# barclays-buk-ui-engineer-web-ui-engineer-web-worker-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-web-ui-engineer-web-worker-agent-v1` |
| Plugin name | `barclays-buk-ui-engineer-web` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-ui-engineer-web@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `PROJECT_PATH` — absolute path to the ROLB web project root
- `JIRA_ID` — JIRA ticket identifier for the current task (e.g. `UCG-1234`)
- `PHASE` — phase number (1 for page generation)
- `BATCH_ID` — batch index (0-based) identifying this worker's assigned screens
- `SCREENS` — array of screen definition objects, each with `screenName`, `figmaUrl`, `nodeId`, `outputFile`, `description`
- `FIGMA_TOKEN` — Figma personal access token, or `"none"` if unavailable; without it the agent uses MCP tools or description-based fallback
- `ADDITIONAL_INPUT` — free-text supplemental instructions, or `"none"`

## Preconditions

- The web project must exist at `PROJECT_PATH` with `@barclays/blueprint-react` installed
- `barclays-buk-ui-engineer:figma` skill must be loaded for Figma MCP extraction (agent flags placeholder if absent)
- `barclays-buk-standards:accessibility` skill must be loaded for WCAG 2.1 AA checks (agent flags placeholder if absent)
- `barclays-buk-standards:security` skill must be loaded for secure coding checks (agent flags placeholder if absent)
- `SCREENS` array must be non-empty; if `nodeId` is null for any screen, fallback heuristics are applied and flagged

## Expected outputs

- One `.tsx` Blueprint React page component per screen in the assigned batch, written to `{PROJECT_PATH}/src/pages/{componentName}/{COMPONENT_NAME}.tsx`
- Each file: `<Page>` as root element, `Navbar` in the `Page head` slot, exported `{COMPONENT_NAME}Props` interface, `export default` at end, all form fields wrapped in `FormItem` render prop with `{...props}` spread, zero inline styles, zero hardcoded colours, WCAG 2.1 AA accessible markup with correct heading hierarchy
- Batch result object: `{ batchId, platform: "web", screens: [{ componentName, outputFile, status }], flags }`

## Exclusions

- Does not generate a page barrel export or register routes in a React Router configuration — the orchestrating command handles that after all batches complete
- Does not run TypeScript compilation (`tsc`) or ESLint checks — the caller drives the build gate once all batches finish
- Does not process screens outside its assigned batch; screens are allocated exclusively per worker to avoid conflicts
- Does not spawn sub-agents of its own
- Does not generate non-ROLB (non-Blueprint React) web components; this worker is specific to `@barclays/blueprint-react` projects

## Verification

Inspect each generated `.tsx` file to confirm: root element is `<Page>`, `Navbar` is in the `head` slot, `{COMPONENT_NAME}Props` interface is exported, `export default` is present, every `FormInput`/`FormSelect`/`FormTextArea` is wrapped in a `FormItem` with a render prop that spreads `{...props}`, no inline styles or hardcoded colour values are present. Check the returned batch result `flags` section for placeholder skill warnings or component mapping ambiguities requiring manual review.
