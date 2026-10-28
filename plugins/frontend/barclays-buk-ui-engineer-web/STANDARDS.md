# barclays-buk-ui-engineer-web — Standards

> Extends `barclays-buk-ui-engineer/STANDARDS.md`. This document covers only what is specific to the Web (Blueprint React) platform. Read the shared STANDARDS.md first.

---

## Mission

Create high-quality, beautiful React pages for customer journeys on the Online Banking (ROLB) web channel — using Figma designs, an API contract, and user stories as inputs. Produces fully typed `@barclays/blueprint-react` page components and data hooks that are accessible, secure, and ready to wire up.

---

## Platform Scope

| Channel | Supported |
|---|---|
| Online Banking (native React/web) | Yes |
| Mobile (SDF/React Native) | No — use `barclays-buk-ui-engineer-sdf` |

---

## Inputs

All shared inputs apply (see `barclays-buk-ui-engineer/STANDARDS.md`). Web-specific additions:

| Input | Source | Required |
|---|---|---|
| `SCREENS[].nodeId` | Figma frame node ID | No — fallback heuristics if absent |
| `FIGMA_TOKEN` | Figma personal access token | No — MCP-only mode if absent |

---

## Outputs

| Artifact | Path | Description |
|---|---|---|
| Page component | `{PROJECT_PATH}/src/pages/{componentName}/{COMPONENT_NAME}.tsx` | Fully typed Blueprint React page component |
| Data hook | `{PROJECT_PATH}/src/pages/{componentName}/use{COMPONENT_NAME}.ts` | Custom hook — state and API calls derived from OAS schema |
| Completion report | `{PROJECT_PATH}/UI_ENGINEER_WEB_COMPLETE.md` | Summary of screens generated, flags, suggested next steps |
| Execution log | `{PROJECT_PATH}/logs/ui-engineer-web.log` | Timestamped log of all agent actions |

---

## Standards Enforced

All shared standards apply (accessibility WCAG 2.2 AA, security, design tokens, Figma extraction). Web-specific Iron Rules:

### Iron Rules — Blueprint React

| Rule | Check | Severity if violated |
|---|---|---|
| Root element is `<Page>` | `grep -rL "<Page" src/pages/` returns no files | Critical — `Page` provides required layout slots and document structure |
| `Navbar` in `Page head` slot | Every page file contains `<Navbar` | High |
| Exported `{COMPONENT_NAME}Props` interface | `grep -rL "export interface.*Props" src/pages/` returns no files | High |
| `export default {COMPONENT_NAME}` present | `grep -rL "export default" src/pages/` returns no files | High |
| `FormInput`/`FormSelect`/`FormTextArea` always wrapped in `FormItem` with render prop | `grep -rn "FormInput\|FormSelect\|FormTextArea" src/pages/` never appears without enclosing `FormItem` | Critical — bare form inputs are not accessible (no label linkage) |
| `FormItem` render prop always spreads `{...props}` onto the input | Every `render={(props) =>` callback spreads `{...props}` | Critical — `aria-describedby`, `id`, `aria-invalid` wired by Blueprint; spreading is required |
| `Alert` always includes `media` slot with an icon | `grep -rn "<Alert" src/pages/` piped to check for `media=` | High |
| `Modal` always controlled via `ref.current.open()` / `ref.current.close()` — never a state boolean | `grep -rn "visible=" src/pages/` on Modal elements returns empty | High — state-controlled Modal is unreliable in Blueprint |
| `TileButton` or `TileLink` for interactive cards — never `Tile` with `onClick` | `grep -rn "Tile.*onClick" src/pages/` returns empty | High |
| `Icon ariaHidden` for decorative icons — `Icon ariaLabel` for meaningful icons | Every `<Icon` has either `ariaHidden` or `ariaLabel` | Critical — WCAG 2.2 AA |
| Heading `Type` elements use correct `element` prop — `h1` once per page, sequential | No heading level skips; `h1` appears exactly once per page | High |
| ESM imports only — zero `require()` | `grep -rn "= require(" src/pages/` returns empty | High |
| Imports from `@barclays/blueprint-react` only — not `chameleon-blueprint` | `grep -rn "chameleon-blueprint" src/pages/` returns empty | Critical — wrong package, nothing will render |
| Zero inline styles | `grep -rn "style={{" src/pages/` returns empty | High |

### Data hook rules

| Rule | Check | Severity if violated |
|---|---|---|
| Hook file exists for every page component | `use{COMPONENT_NAME}.ts` present alongside page | High |
| Hook returns typed state — no `any` | TypeScript compilation passes | High |
| API calls derived from OAS schema — endpoint, method, request/response types | Fetch calls match OAS spec when provided | High |
| Hook accepts service/API interfaces as parameters — not imported directly | Enables testing without network | High |

---

## Tools and Tech

| Property | Value | Why |
|---|---|---|
| Language | TypeScript | ROLB projects are TypeScript-first |
| Framework | React | Online Banking (ROLB) native web |
| Component library | `@barclays/blueprint-react` | Blueprint React — never raw HTML elements or `chameleon-blueprint` |
| State | Custom hook (`use{ComponentName}`) | ROLB convention |
| Build check | `npx tsc --noEmit` | TypeScript compile must pass |

### Skills loaded (Web additions)

No additional platform-specific skills beyond the shared set. All rules are embedded in this STANDARDS.md and the agent itself.

---

## Quality Gates (in execution order)

| Gate | Check | Threshold |
|---|---|---|
| TypeScript compile | `npx tsc --noEmit` | Exit 0 |
| Iron Rule validation | Grep checks above | 0 Critical violations |
| Accessibility | `barclays-buk-standards:accessibility` Web rules applied | 0 Critical violations |

---

## Handoff Criteria

All shared handoff criteria apply. Web-specific additions:

| Gate | Why |
|---|---|
| Agent tested against a real `@barclays/blueprint-react` ROLB project | Blueprint React API and prop names must be validated against the version in use |
| `npx tsc --noEmit` passes on first attempt for all generated files | TypeScript errors in generated output are a blocker |
| `FormItem` render prop pattern verified — `{...props}` spread confirmed | The most commonly violated Iron Rule; must be tested explicitly as it is invisible at runtime but breaks accessibility |
| Data hook state fields match OAS response schema on a real spec | Core of Option B — hook generation validated against a real contract |
| All 14 Iron Rules confirmed zero-violation across at least 5 generated pages | Adequate coverage of the rule set |

---

## Definition of Done

All shared DoD items apply. Web-specific additions:

- [ ] Generated page files import exclusively from `@barclays/blueprint-react`
- [ ] Every page has a corresponding `use{ComponentName}.ts` hook alongside it
- [ ] All `FormInput`/`FormSelect`/`FormTextArea` elements wrapped in `FormItem` with render prop spreading `{...props}`
- [ ] All `Alert` elements include a `media` slot
- [ ] All `Modal` elements use `ref.current.open()` — no `visible` prop
- [ ] `npx tsc --noEmit` exits 0 on first attempt
