# barclays-buk-ui-engineer-ios-ui-engineer-ios-worker-agent-v1

| Field | Value |
| --- | --- |
| Capability ID | `barclays-buk-ui-engineer-ios-ui-engineer-ios-worker-agent-v1` |
| Plugin name | `barclays-buk-ui-engineer-ios` |
| Component type | agent-plugin |
| Owner | BUK Retail CAPL |
| Action scope | externally-consequential |
| Invocation mode | tool/agent — no slash command |
| Installation / release | /plugin install barclays-buk-ui-engineer-ios@barclays-cio-buk |

## Description

_No skill entry point — invoked through plugin tools/agents._

## Inputs

- `PROJECT_PATH` — absolute path to the iOS project root
- `JIRA_ID` — JIRA ticket identifier for the current task (e.g. `UCG-1234`)
- `PHASE` — phase number (1 for screen generation)
- `BATCH_ID` — batch index (0-based) identifying this worker's assigned screens
- `SCREENS` — array of screen definition objects, each with `screenName`, `figmaUrl`, `nodeId`, `outputFile`, `description`
- `FIGMA_TOKEN` — Figma personal access token, or `"none"` if unavailable; without it the agent uses MCP tools or description-based fallback
- `ADDITIONAL_INPUT` — free-text supplemental instructions, or `"none"`

## Preconditions

- The iOS project must exist at `PROJECT_PATH` with `BarclaysBlueprint` imported (`.xcodeproj` or `.xcworkspace` present)
- `barclays-buk-ui-engineer:figma` skill must be loaded for Figma MCP extraction (agent flags placeholder if absent)
- `barclays-buk-standards:accessibility` skill must be loaded for WCAG 2.1 AA checks (agent flags placeholder if absent)
- `barclays-buk-standards:security` skill must be loaded for secure coding baseline (agent flags placeholder if absent)
- `barclays-buk-ui-engineer-ios:security-ios` skill must be loaded for iOS-specific rules (App Attest, TrustKit, `BPScreenProtection`); takes precedence over the generic security skill for iOS-specific rules (agent flags placeholder if absent)
- `SCREENS` array must be non-empty; if `nodeId` is null for any screen, fallback heuristics are applied and flagged

## Expected outputs

- One `.swift` SwiftUI view file per screen in the assigned batch, written to `{PROJECT_PATH}/Sources/Screens/{COMPONENT_NAME}/{COMPONENT_NAME}.swift`
- Each file: ViewModel-injected struct conforming to `View`, `BPNavigationBar` present, `BPScreenProtection` wrapper for any screen displaying account data or personal details, `BPSecureTextField` for sensitive inputs, WCAG 2.1 AA accessible labels, zero hardcoded colours or spacing values, zero `UIKit` imports, all user-facing strings localisation-ready
- Batch result object: `{ batchId, platform: "ios", screens: [{ componentName, outputFile, status }], flags }`

## Exclusions

- Does not register generated views in a SwiftUI navigation stack or coordinator — routing is the caller's responsibility after generation
- Does not run Swift compilation or SwiftLint checks — the caller drives the build gate once all batches finish
- Does not process screens outside its assigned batch; screens are allocated exclusively per worker to avoid conflicts
- Does not spawn sub-agents of its own

## Verification

Inspect each generated `.swift` file to confirm: `BPNavigationBar` is present, `BPScreenProtection` wraps screens that display account or personal data, `BPSecureTextField` is used for all sensitive inputs, no hardcoded colour or spacing values are present, no `UIKit` imports, and all user-facing strings use `LocalizedStringKey`. Check the returned batch result `flags` section for placeholder skill warnings or sensitive-screen classification decisions requiring manual review.
