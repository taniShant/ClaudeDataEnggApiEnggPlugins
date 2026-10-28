# barclays-buk-ui-engineer-android-ui-engineer-android-worker-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-android-ui-engineer-android-worker-agent-v1` |
| Plugin name | `barclays-buk-ui-engineer-android` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-ui-engineer-android@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `PROJECT_PATH` — absolute path to the Android project root
- `JIRA_ID` — JIRA ticket identifier for the current task (e.g. `UCG-1234`)
- `PHASE` — phase number (1 for screen generation)
- `BATCH_ID` — batch index (0-based) identifying this worker's assigned screens
- `SCREENS` — array of screen definition objects, each with `screenName`, `figmaUrl`, `nodeId`, `outputFile`, `description`
- `FIGMA_TOKEN` — Figma personal access token, or `"none"` if unavailable; without it the agent uses MCP tools or description-based fallback
- `ADDITIONAL_INPUT` — free-text supplemental instructions, or `"none"`

## Preconditions

- The Android project must exist at `PROJECT_PATH` with `com.barclays.mobile.blueprint.compose:ui` (`barclays.designLanguage`) as a dependency
- `barclays-buk-ui-engineer:figma` skill must be loaded for Figma MCP extraction (agent flags placeholder if absent)
- `barclays-buk-standards:accessibility` skill must be loaded for WCAG 2.1 AA checks (agent flags placeholder if absent)
- `barclays-buk-standards:security` skill must be loaded for secure coding checks (agent flags placeholder if absent)
- `SCREENS` array must be non-empty; if `nodeId` is null for any screen, fallback heuristics are applied and flagged

## Expected outputs

- One `.kt` Jetpack Compose screen composable per screen in the assigned batch, written to `{PROJECT_PATH}/src/main/java/{package}/screens/{COMPONENT_NAME}/{COMPONENT_NAME}.kt`
- Each file: `BlueprintScaffold` as root composable, `BlueprintLargeNavBar` in the `top` slot, hoisted state data class, typed callback parameters, WCAG 2.1 AA accessible markup, zero hardcoded colours or typography, `BlueprintSecureField` for all sensitive inputs
- Batch result object: `{ batchId, platform: "android", screens: [{ componentName, outputFile, status }], flags }`

## Exclusions

- Does not generate a screen barrel export or registration in the Navigation graph — the orchestrating command handles that after all batches complete
- Does not run Kotlin compilation or Lint checks — the caller drives the build gate once all batches finish
- Does not process screens outside its assigned batch; screens are allocated exclusively per worker to avoid conflicts
- Does not spawn sub-agents of its own

## Verification

Inspect each generated `.kt` file to confirm: root composable is `BlueprintScaffold`, `BlueprintLargeNavBar` is present in the `top` slot, state is hoisted into a separate data class, `BlueprintSecureField` is used for any sensitive inputs, no hardcoded colour or typography values are present. Check the returned batch result `flags` section for any placeholder skill warnings or component mapping ambiguities requiring manual review.
