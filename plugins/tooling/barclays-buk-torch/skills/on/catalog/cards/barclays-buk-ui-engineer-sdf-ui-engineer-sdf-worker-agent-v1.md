# barclays-buk-ui-engineer-sdf-ui-engineer-sdf-worker-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-sdf-ui-engineer-sdf-worker-agent-v1` |
| Plugin name | `barclays-buk-ui-engineer-sdf` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-ui-engineer-sdf@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `PROJECT_PATH` — absolute path to the SDF React Native project
- `JIRA_ID` — JIRA ticket identifier for the current task
- `PHASE` — phase number (1 for screen generation)
- `BATCH_ID` — batch index (0-based) for this worker's assigned screens
- `SCREENS` — array of screen definition objects, each with `screenName`, `figmaUrl`, `nodeId`, `outputFile`, `description`
- `FIGMA_TOKEN` — Figma personal access token, or `"none"` if unavailable; without it the agent uses MCP tools or description-based fallback
- `ADDITIONAL_INPUT` — free-text supplemental instructions, or `"none"`

## Preconditions

- The SDF project must exist at `PROJECT_PATH` with `@barclays/chameleon-blueprint` installed
- `barclays-buk-ui-engineer:figma` skill must be loaded for Figma MCP extraction (agent flags placeholder if absent)
- `barclays-buk-standards:accessibility` skill must be loaded for WCAG 2.1 AA checks (agent flags placeholder if absent)
- `SCREENS` array must be non-empty; if `nodeId` is null for any screen, fallback heuristics are applied and flagged

## Expected outputs

- One `.tsx` Blueprint React Native screen component per screen in the assigned batch, written to `PROJECT_PATH/src/screens/<ScreenName>/<ScreenName>.tsx`
- Each component has: `VanillaLayout` root, `Navbar`, fully typed exported `Props` interface, `export default`, zero inline styles, zero hardcoded colours, WCAG 2.1 AA accessible markup
- Batch result object: `{ batchId, platform: "sdf", screens: [{ componentName, outputFile, status }], flags }`

## Exclusions

- Does not generate the screen barrel export (`src/screens/index.ts`) — that is the command's responsibility after all workers complete
- Does not run TypeScript compilation or validation — the command drives the `tsc` gate once all batches finish
- Does not process screens outside its assigned batch; screens are allocated exclusively per worker to avoid conflicts
- Does not spawn sub-agents of its own

## Verification

Inspect each generated `.tsx` file to confirm: root element is `<VanillaLayout>`, `Navbar` has a `variant` prop, the exported `Props` interface is present, and `export default` is at the end. Check the returned batch result `flags` section for any placeholder skill warnings or mapping ambiguities that need manual review.
