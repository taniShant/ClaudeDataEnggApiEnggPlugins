---
name: figma
description: Shared Figma design extraction skill for all barclays-buk-ui-engineer platform specialists. Covers Figma MCP tool calls, design context extraction, component naming conventions, and batch result schema. Load this skill in every ui-engineer worker agent — platform-specific mapping and generation rules live in the platform skill.
user-invocable: false
owner: BUK PE
review_trigger: figma-local MCP API change, new platform added to ui-engineer family
source: BUK PE / barclays-buk-ui-engineer
status: Production
---

# Figma Design Extraction

Shared by all `barclays-buk-ui-engineer-*` worker agents. This skill covers everything up to and including raw design context extraction. What you do with that context (component mapping, code generation) is the platform skill's responsibility.

---

## MCP Availability Check

**This is a hard gate. If the Figma MCP tools are not available and a `nodeId` is present — STOP. Do not generate any code. Do not fall back to heuristics. Do not proceed.**

Two MCP servers are supported:

- **`figma-local`** — requires Figma Desktop app to be running with Dev Mode MCP Server enabled. No credentials needed.
- **`figma-remote`** — requires `FIGMA_MCP_PATH` and `FIGMA_API_KEY` configured in plugin settings.

**Do NOT use curl, wget, Bash, or any shell command to probe MCP availability.** The only valid availability check is whether the MCP tool call itself succeeds when you invoke it. Never shell out to probe a server address — the result tells you nothing useful about whether the MCP tools are wired into your session.

### If the MCP tool call fails or the tools are not registered in the session

It does not matter whether the server is "reachable" — what matters is whether `get_design_context` is available as a tool in this agent session. If it is not, or if calling it returns an error:

**STOP immediately.** Output this message and nothing else:

```
❌ Figma MCP tools not available in this session — cannot proceed.

The figma-local MCP server must be registered in the Claude session before this
agent can run. Generating code without real Figma design context is not acceptable
— it produces incorrect layouts that will fail design review.

To fix:
  1. Open Figma Desktop app
  2. Go to Preferences → Dev Mode → enable "MCP Server"
  3. In your project directory, run:
       bash /path/to/buk/plugins/frontend/barclays-buk-ui-engineer/scripts/setup-figma-mcp.sh <project-path>
     This writes .mcp.json and updates .claude/settings.json with the figma-local server.
  4. Start a NEW Claude Code session from the project directory
     (MCP servers are registered at session start — restarting is required)
  5. Re-run this agent

If Figma Desktop is unavailable, configure figma-remote instead:
  - Set FIGMA_MCP_PATH and FIGMA_API_KEY in the plugin's userConfig
  - See plugins/frontend/barclays-buk-ui-engineer/README.md for details
```

Do not emit a batch result. Do not write any files. Do not continue.

### The only valid fallback path

Section 2 heuristics apply **only** when `screen.nodeId` is explicitly `null` — meaning the discover agent already determined no Figma frame exists for this screen. This is not a fallback for MCP failure. A null nodeId is a deliberate signal; an unavailable MCP server is a setup problem that must be fixed.

---

## Quick Start

```
# Step 0 — open the correct file/node in Figma Desktop before any MCP call
# Open Figma Desktop and navigate to the file manually, or paste the URL into Figma Desktop.

# Step 1 — call get_design_context before generating any code
tool: figma-local / get_design_context
nodeId: {screen.nodeId}
clientLanguages: "kotlin"        # android
                 "swift"         # ios
                 "typescript"    # sdf / web
clientFrameworks: "jetpack-compose" | "swiftui" | "react-native" | "react"

# Step 2 — call get_variable_defs to extract design tokens
tool: figma-local / get_variable_defs
nodeId: {screen.nodeId}

# Step 2.5 — call get_screenshot for visual reference
tool: figma-local / get_screenshot
nodeId: {screen.nodeId}

# Step 3 — if nodeId is null, use keyword fallback heuristics (Section 2)

# Step 4 — derive PascalCase component name ending in Screen (Section 3)

# Step 5 — emit canonical batch result JSON (Section 4)
```

**Prerequisites:** Figma Dev Mode MCP server must be running via Figma Desktop app. Enable it under Figma menu → Preferences → Dev Mode MCP Server. The `figma-local` server must appear as connected in `/mcp` before invoking any agent.

---

## Agent Self-Check

Before completing any screen generation task:

- [ ] `get_design_context` called for every screen with a non-null `nodeId`
- [ ] `get_variable_defs` called to extract design tokens — no raw hex/rgb values used in generated code
- [ ] `get_screenshot` called for every screen with a non-null `nodeId`
- [ ] Code Connect snippets (`<CodeConnectSnippet>`) extracted and used as primary component mapping where present
- [ ] Layout measurements (gap, padding, icon spacing, footer offset) extracted from frame geometry in `get_design_context` and applied in native `.native.tsx` style objects
- [ ] Fallback heuristics applied and flagged in output when `nodeId` is null
- [ ] Component names are PascalCase and end in `Screen`
- [ ] Batch result JSON emitted with all required fields populated — no partial omissions
- [ ] `status` field in batch result reflects actual outcome (`success` / `partial` / `failed`)
- [ ] Any MCP errors or fallbacks reported in `flags` array

---

## Section 1: Figma MCP Tool Calls

For each screen in your assigned batch, call the Figma MCP tools **before generating any code**.

### 1.1 get_design_context

```
tool: figma-local / get_design_context
nodeId: {screen.nodeId}
clientLanguages: "typescript"        ← React Native / Web platforms
                 "swift"             ← iOS platform
                 "kotlin"            ← Android platform
clientFrameworks: "react-native"     ← SDF / MCA
                  "swiftui"          ← iOS
                  "jetpack-compose"  ← Android
                  "react"            ← Web
artifactType: "WEB_PAGE_OR_APP_SCREEN"
```

From the response, extract:

| What | Where to use it |
|---|---|
| Component hierarchy — elements and nesting | Determines which container and content components to use |
| Text content — all strings, visual properties (size, weight, colour) | Maps to typography components and props |
| Colour values | Map to design token props — **never use raw hex/rgb values** |
| Layout — flex direction, alignment, spacing | Informs layout component choice and spacing props |
| Interactive elements — buttons, inputs, links, tappable areas | Maps to interactive components with correct event handlers |
| Navigation bar — presence, title, back/prefix icons | Always map to the platform's Navbar/NavigationBar equivalent |

### 1.1a: Code Connect Snippets — use first

**When `get_design_context` returns `<CodeConnectSnippet>` elements, those snippets are the canonical implementation.** They are authored by the design system team and reflect the correct component API, layout pattern, and prop usage for the target platform.

**Priority rule: Code Connect snippet → platform skill component mappings → fallback inference**

- Match snippets by `data-snippet-language`: `"React Native"` for SDF/MCA, `"Compose"` for Android, `"SwiftUI"` for iOS, `"React"` for Web
- Extract the code from inside the `<CodeConnectSnippet>` wrapper — do NOT include the wrapper element itself in generated code
- Use the imports listed at the top of the `get_design_context` response that correspond to the snippet's language
- If a snippet imports from a native-only package (e.g. `@barclays/blueprint-react-native`), generate a `.native.tsx` platform split — the shared `.tsx` uses the web/heuristic mapping, the `.native.tsx` uses the snippet
- If multiple snippet options are returned (`options={[...]}` format), choose the most appropriate variant based on the Figma design
- **If no snippet is present for a node**, fall through to the platform skill's component mapping heuristics as normal — Code Connect is opt-in per component, not universal

### 1.2 get_variable_defs

```
tool: figma-local / get_variable_defs
nodeId: {screen.nodeId}
```

From the response, extract design tokens (colour variables, spacing variables). Map tokens to platform component props using the tables below. **Do NOT use raw token values as hardcoded strings.**

**For native `.native.tsx` platform splits, also extract layout measurements from the `get_design_context` frame geometry** — these drive spacing values that Blueprint component props cannot express:

| What to extract | Where to find it | Use in native code |
|---|---|---|
| Gap between cards/panels | `gap-[Npx]` on the parent container | `gap: N` in container `View` style |
| Padding inside card | `p-[Npx]` or Figma spacing on Pane | `Panel.Pane` `spacing` prop or inner `View` padding |
| Gap between icon and text in a row | horizontal margin/padding on child elements | `gap: N` on the row `View` |
| Footer distance from bottom | `top: Npx` relative to frame height | `marginTop: 'auto'` or explicit footer `View` |

These values come from the Figma frame's CSS classes in `get_design_context` output (e.g. `gap-[16px]`, `left-[24px]`, `top-[112px]`). Extract them and apply as numeric pixel values in native style objects. Use the spacing token table below to pick the nearest standard value — only fall back to a raw number when no standard token matches within 2px.

#### Colour tokens

| Semantic intent | SDF prop | iOS token | Android token |
|---|---|---|---|
| Primary text / headings | `color="title"` on `Type` | `.title` | `LocalTypography.current.standard` |
| Secondary / muted text | `color="disabled"` on `Type` | `.neutral700` | `LocalColors.current.onSurface` |
| Screen background | `Section variant="primary"` | `.neutral100` | `LocalColors.current.neutral100` |
| Content section (grey) | `Section variant="secondary"` | (theme default) | `LocalColors.current.neutral200` |
| Brand / interactive | `Button variant="primary"` | `.interactive` or `.brand` | `LocalColors.current.primary` |
| Error state | `color="error"` on `Type` | `.error` | `LocalColors.current.error` |
| Success state | `color="success"` on `Type` | `.success` | `LocalColors.current.success` |
| Warning state | `color="warning"` on `Type` | `.warning` | (theme) |
| Info state | `color="info"` on `Type` | `.information` | (theme) |
| Divider / border | `Separator` component | `.neutral300` or `.grey` | `LocalColors.current.neutral300` |

#### Spacing tokens

| Figma value | SDF prop | iOS token | Android token |
|---|---|---|---|
| 4px | `spacingBottom="xs"` on `SectionItem` | `.su4` | `LocalSpacing.current.xSmall` |
| 8px | `spacingBottom="sm"` | `.su8` | `LocalSpacing.current.small` |
| 16px | `spacingBottom="md"` | `.su16` | `LocalSpacing.current.medium` |
| 24px | `spacingBottom="lg"` | `.su24` | `LocalSpacing.current.large` |
| 32px | `spacingBottom="xl"` | `.su32` | `LocalSpacing.current.xLarge` |
| 40px | `spacingBottom="2xl"` | `.su40` | (use xLarge) |

### 1.3 get_screenshot

```
tool: figma-local / get_screenshot
nodeId: {screen.nodeId}
```

Call for every screen with a non-null `nodeId`. Use it actively during the component mapping step — it reveals visual weight, spatial grouping, and rendered composition that the component hierarchy alone does not convey. **Do not embed the image in generated code.** Store the result for use in post-generation visual comparison.

---

## Section 2: Fallback When No nodeId

If `screen.nodeId` is null, skip all MCP calls. Infer layout from keyword heuristics using `screen.screenName` and `screen.description`:

| Keyword match | Inferred layout pattern |
|---|---|
| "dashboard" | Hero summary + grid/tile sections + CTA button |
| "form" or "settings" | Label + input rows + submit button |
| "list" or "table" | Search input + list items + empty state |
| "detail" or "profile" | Hero section + metadata rows |
| "login" or "sign in" | Input fields + primary button (full width) |
| "onboarding" | Instructional text + CTA + skip link |
| No match | Content section + footer button |

Apply the platform-specific component names for each pattern — these are defined in the platform skill.

---

## Section 3: Component Naming Conventions

These apply across all platforms.

### Screen component name
- Derive from `screen.screenName`
- Convert to **PascalCase**
- Must end in `Screen`

Examples:
- `customer-dashboard` → `CustomerDashboardScreen`
- `QQ_Welcome` → strip prefix → `WelcomeScreen`
- `login` → `LoginScreen`

### File path
- `SCREEN_DIR`: `{PROJECT_PATH}/src/screens/{COMPONENT_NAME}/`
- `OUTPUT_FILE`: `{SCREEN_DIR}{COMPONENT_NAME}.{ext}` where ext is `.tsx` (RN/Web), `.swift` (iOS), `.kt` (Android)

```bash
mkdir -p "{SCREEN_DIR}"
```

---

## Section 4: Batch Result Schema

Every worker agent must emit this JSON after processing its batch. Populate all fields — do not omit on partial failure.

```json
{
  "batchId": "{BATCH_ID}",
  "platform": "{sdf|ios|android|mca|web}",
  "status": "success | partial | failed",
  "generatedScreens": [
    {
      "componentName": "{ComponentName}",
      "outputFile": "{outputFile}",
      "figmaNodeId": "{nodeId or null}",
      "mcpDataUsed": true,
      "propsInterfaceExported": true,
      "platformComponents": ["{ComponentA}", "{ComponentB}", "..."]
    }
  ],
  "errors": [
    {
      "screenName": "{screenName}",
      "reason": "{description of failure}"
    }
  ]
}
```

- `status: "success"` — all screens generated without error
- `status: "partial"` — some screens generated, some failed — populate `errors`
- `status: "failed"` — no screens generated — populate `errors`

Never leave the batch in an ambiguous state. Always emit this schema.

### Batch sizing guidance

Default batch sizes by platform — limits blast radius when the compile gate fails mid-batch:

| Platform | Screens per batch | Reason |
|---|---|---|
| SDF | 5 | `tsc --noEmit` gate is fast (~10s) |
| iOS | 3 | `xcodebuild` gate is slow (~60s) |
| Android / TBA | 3 | Gradle gate is slow (~45s) |

---

## Section 5: MCP Prerequisites

The `figma-local` MCP server must be running before any Figma tool call. It is provided by the Figma Desktop app Dev Mode plugin.

| Requirement | How to verify |
|---|---|
| Figma Desktop app open | App is running on the user's machine |
| Dev Mode MCP enabled | Settings → Dev Mode → MCP Server → enabled |

**If the MCP server is unavailable and a `nodeId` is present — STOP. See the MCP Availability Check section at the top. Section 2 fallback heuristics are NOT a substitute for MCP failure — they apply only when `screen.nodeId` is explicitly null.**

**Do NOT prompt the user for a `FIGMA_TOKEN`** unless REST API access is explicitly required (e.g. bulk file discovery). Single-screen generation via `nodeId` uses MCP only — no token needed.

---

## Section 6: Common Failure Modes

| Failure | Cause | Resolution |
|---|---|---|
| MCP call returns empty component tree | Node is a group or section, not a frame | Try parent node; or treat as fallback |
| `nodeId` decodes to wrong frame | URL used `-` separator instead of `%3A` | Convert `44800-19476` → `44800:19476` |
| Design tokens are empty | `get_variable_defs` called before file is loaded | Retry once; if still empty, apply platform defaults |
| Screen name produces non-PascalCase | Name contains special chars or is all-uppercase prefix | Strip non-alphanumeric, apply PascalCase, append `Screen` |
