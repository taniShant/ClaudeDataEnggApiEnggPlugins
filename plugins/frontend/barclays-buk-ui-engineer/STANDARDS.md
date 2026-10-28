# barclays-buk-ui-engineer — Standards

---

## Mission

Turn a Figma design, an API contract, and a set of user stories into a high-quality, beautiful UI for a customer journey — across every BUK channel. Given those inputs, this plugin family produces fully typed, production-ready screens and ViewModels that a feature engineer can connect business logic to immediately, without rebuilding from scratch.

Every screen it generates is platform-correct, accessible, and secure by default. Where it cannot fill a gap, it says so — it never silently produces broken output.

---

## Plugin family structure

```
barclays-buk-ui-engineer (dispatcher)
  ├── barclays-buk-ui-engineer-sdf      — Blueprint React Native (@barclays/chameleon-blueprint)
  ├── barclays-buk-ui-engineer-ios      — SwiftUI + BarclaysBlueprint
  ├── barclays-buk-ui-engineer-android  — Jetpack Compose + Blueprint Compose
  ├── barclays-buk-ui-engineer-web      — Blueprint React (@barclays/blueprint-react)
  └── barclays-buk-ui-engineer-mca      — planned
```

Each platform plugin is independently invocable. The dispatcher detects the platform and delegates — it is a convenience router, not a required step.

---

## Shared Inputs

All platform worker agents accept these inputs. All non-required inputs default to `"none"` — agents proceed without them and flag what was missing (Principle 7).

| Input | Source | Required |
|---|---|---|
| `PROJECT_PATH` | Absolute path to the target codebase | Yes |
| `JIRA_ID` | Ticket reference — stamped in file headers | Yes |
| `FIGMA_URL` | Figma design URL — source of truth for UI, copy, and layout | Yes — or "none" for description-only mode |
| `OAS_SPEC_PATH` | Absolute path to OpenAPI spec (`.yaml` or `.json`) | No — ViewModel state stubbed if absent |
| `PLATFORM` | Target platform | Yes for dispatcher — workers receive it from dispatcher |
| `PLATFORM_OPTIONS` | Platform-specific parameters e.g. `{"package": "com.barclays..."}` | No — defaults applied if absent |
| `ADDITIONAL_INPUT` | Free text context | No |

**Note on copy and UX design:** These inputs are sourced from Figma directly. The `barclays-buk-copywriter` and `barclays-buk-ux-designer` agents must update Figma with approved output before invoking the UI engineer. Figma is the integration point.

**Worker agents also receive:**

| Input | Source | Required |
|---|---|---|
| `PHASE` | Batch execution phase number | Yes |
| `BATCH_ID` | Batch identifier within the phase | Yes |
| `SCREENS` | Array of `{screenName, figmaUrl, nodeId, outputFile, description}` | Yes |
| `FIGMA_TOKEN` | Figma personal access token | No — MCP-only mode if absent |

---

## Shared Outputs

Every platform worker produces the following per screen in its assigned batch:

| Artifact | Description |
|---|---|
| Screen file | One platform-specific screen file per screen (see platform STANDARDS.md for path and extension) |
| ViewModel / state file | One ViewModel or state holder per screen — fields derived from OAS response schema where available, stubbed where absent |
| Batch result JSON | Structured result schema — see Section: Batch Result Schema |
| Execution log entry | Appended to `{PROJECT_PATH}/logs/ui-engineer-{platform}.log` |

**Test generation** is out of scope for initial generation. The batch result flags that tests must be written. This is a known gap — see Handoff Criteria.

---

## Shared Standards Enforced

### Accessibility — WCAG 2.2 AA

All generated screens must comply with WCAG 2.2 AA. Standards are defined in `barclays-buk-standards:accessibility`. Mechanical checks:

| Standard | Passing means | Severity if missing |
|---|---|---|
| Every interactive element has an accessible label | No unlabelled buttons, inputs, or tappable areas | Critical |
| Colour is never the sole means of conveying information | Error states combine colour + descriptive text | High |
| Heading hierarchy is sequential | No skipped heading levels | High |
| Focus order matches visual order | Tab/swipe sequence is logical | High |
| Touch targets meet minimum size | Platform minimums: 44×44pt iOS, 48×48dp Android, 44×44px Web | High |

Detail: `barclays-buk-standards:accessibility`

### Security

All generated screens must apply the secure coding baseline. Standards are defined in `barclays-buk-standards:security`. Mechanical checks:

| Standard | Passing means | Severity if missing |
|---|---|---|
| No sensitive data in logs or console output | PANs, sort codes, account numbers, NI numbers, email never logged | Critical |
| Sensitive input fields use secure platform variants | Passwords, PINs, card numbers use masked/secure field components | Critical |
| No hardcoded credentials or secrets | Zero API keys, tokens, or passwords in generated source | Critical |

Detail: `barclays-buk-standards:security`

### Design tokens — never raw values

| Standard | Passing means | Severity if missing |
|---|---|---|
| No hardcoded colour values | Zero hex, rgb, or rgba literals in generated source | High |
| No hardcoded spacing values | Spacing uses platform token system (BPSpacing, design token props, etc.) | Medium |

### Figma extraction

Figma MCP calls (`figma-local` server) must be made before generating any code. If `nodeId` is null, fallback heuristics apply. Standards are defined in `barclays-buk-ui-engineer:figma`.

| Standard | Passing means | Severity if missing |
|---|---|---|
| `get_design_context` called for each screen with a nodeId | Design context extracted before mapping | High |
| `get_variable_defs` called for each screen with a nodeId | Design tokens extracted before mapping | High |
| Fallback heuristics applied and flagged when nodeId is null | Agent reports which screens used fallback | Medium |

---

## Tools and Tech

### All platform workers

| Property | Value | Why |
|---|---|---|
| Model tier | Sonnet | Generation loops run per screen; Opus latency would be prohibitive at batch scale |
| Tools | Bash, Read, Glob, Grep, Edit, Write | Full file access for reading project context and writing generated output |
| MCP server | `figma-local` | Figma Dev Mode MCP — must be running via Figma Desktop app. Enable under Figma menu → Preferences → Dev Mode MCP Server. |

### Shared skills loaded by all platform workers

| Skill | Source | Purpose |
|---|---|---|
| `barclays-buk-ui-engineer:figma` | Dispatcher plugin | Figma MCP extraction, fallback heuristics, component naming, batch result schema |
| `barclays-buk-standards:accessibility` | Standards plugin | WCAG 2.2 AA baseline and platform-specific accessibility rules |
| `barclays-buk-standards:security` | Standards plugin | Secure coding baseline |

Platform workers load additional platform-specific skills — see platform STANDARDS.md.

---

## Batch Result Schema

Every worker agent emits this JSON after processing its batch. All fields are required — do not omit on partial failure.

```json
{
  "batchId": "{BATCH_ID}",
  "platform": "{sdf|ios|android|web}",
  "status": "success | partial | failed",
  "generatedScreens": [
    {
      "componentName": "{ComponentName}",
      "screenFile": "{outputFile}",
      "viewModelFile": "{viewModelFile or null}",
      "figmaNodeId": "{nodeId or null}",
      "mcpDataUsed": true,
      "oasDataUsed": true,
      "platformComponents": ["{ComponentA}", "{ComponentB}"]
    }
  ],
  "errors": [
    {
      "screenName": "{screenName}",
      "reason": "{description of failure}"
    }
  ],
  "flags": ["{any placeholder skills, missing inputs, or decisions under uncertainty}"]
}
```

- `status: "success"` — all screens generated without error
- `status: "partial"` — some screens generated, some failed — populate `errors`
- `status: "failed"` — no screens generated — populate `errors`
- `viewModelFile: null` — ViewModel could not be generated (OAS_SPEC_PATH absent and no description available); flagged
- `oasDataUsed: false` — ViewModel state was stubbed, not derived from OAS schema

---

## Workflow Position

```
barclays-buk-ux-designer     → UX_DESIGN_PATH
barclays-buk-copywriter       → COPY_PATH
barclays-buk-api-engineer     → OAS_SPEC_PATH
                               ↓
         barclays-buk-ui-engineer (dispatcher)
                               ↓
              platform specialist worker
                               ↓
         barclays-buk-quality-engineer
         barclays-buk-accessibility-auditor
```

Upstream artefacts are optional — the plugin proceeds without them and flags what's missing. It does not block on absent inputs (Principle 7).

---

## Shared Handoff Criteria

Before any platform plugin is ready for use by feature teams, the contributing engineer must complete:

| Gate | Why |
|---|---|
| Worker agent tested end-to-end against a real project with Figma nodeId | Core value proposition — must produce compilable, platform-correct output from real design context |
| Worker agent tested with OAS_SPEC_PATH provided — ViewModel fields must match API response schema | Ensures ViewModel generation is wired, not stubbed |
| Worker agent tested with all inputs set to `"none"` — fallback output must compile | Graceful degradation must work; broken fallback is worse than no fallback |
| All Iron Rules verified — validation or grep confirms zero violations in generated output | Iron Rules exist because violations cause build failures or runtime crashes |
| Accessibility checks verified — generated output passes `barclays-buk-accessibility-auditor` review | Accessibility is non-negotiable; the plugin must not ship screens that fail WCAG 2.2 AA |
| WCAG 2.2 AA confirmed (not 2.1) | Current standard |
| Plugin tester score 90+ (`/test-plugin ./plugins/frontend/{plugin-name}`) | BUK marketplace quality gate |
| README.md and STANDARDS.md internally consistent | Version, capability list, and output list must match |

**Known gap — test generation:** Unit and mutation test generation is not yet produced by any platform worker. This must be addressed before the plugin family is considered complete. Until then, each platform worker flags in its batch result that tests must be written manually.

---

## Definition of Done

A reviewer confirms a platform plugin is shippable when all of the following are true:

- [ ] Every Iron Rule in the platform STANDARDS.md has a corresponding mechanical check (grep or validation agent)
- [ ] ViewModel is generated for every screen — fields match OAS response schema when provided, stubbed with `TODO` when absent
- [ ] Generated screens compile on first attempt against the target project (`tsc --noEmit`, `swiftc`, `./gradlew assembleDebug`)
- [ ] All generated screens pass the platform's validation agent or equivalent checks
- [ ] Every generated file has JIRA ID and Figma URL in its header comment
- [ ] Placeholder skills, missing inputs, and decisions under uncertainty are all reported in `flags` (Principle 5)
- [ ] Agent suggests next steps and does not block on missing upstream artefacts (Principle 7)
- [ ] No raw colour or spacing values in any generated file
- [ ] No sensitive data patterns in any generated file
- [ ] README.md, STANDARDS.md, and `plugin.json` are internally consistent (status, capability list, agent list)
