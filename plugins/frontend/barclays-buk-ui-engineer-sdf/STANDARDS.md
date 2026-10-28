# barclays-buk-ui-engineer-sdf — Standards

> Extends `barclays-buk-ui-engineer/STANDARDS.md`. This document covers only what is specific to the SDF (Blueprint React Native) platform. Read the shared STANDARDS.md first.

---

## Mission

Create high-quality, beautiful React Native screens for customer journeys on the mobile and online banking channels — using Figma designs, an API contract, and user stories as inputs. Produces fully typed `@barclays/chameleon-blueprint` screen components and ViewModel hooks that are accessible, secure, and ready to wire up.

---

## Platform Scope

| Channel | Supported |
|---|---|
| Online Banking (SDF/React Native) | Yes |
| Mobile (SDF/React Native) | Yes |
| FullServe / MAE | No — use `barclays-buk-ui-engineer-mca` |

---

## Inputs

All shared inputs apply (see `barclays-buk-ui-engineer/STANDARDS.md`). SDF-specific additions:

| Input | Source | Required |
|---|---|---|
| `SCREENS[].nodeId` | Figma frame node ID | No — fallback heuristics if absent |
| `FIGMA_TOKEN` | Figma personal access token | No — MCP-only mode if absent |

---

## Outputs

| Artifact | Path | Description |
|---|---|---|
| Screen component | `{PROJECT_PATH}/src/screens/{COMPONENT_NAME}/{COMPONENT_NAME}.tsx` | Fully typed Blueprint React Native screen |
| ViewModel hook | `{PROJECT_PATH}/src/screens/{COMPONENT_NAME}/use{COMPONENT_NAME}.ts` | Custom hook — state derived from OAS schema, injected use-case interfaces |
| Barrel export (first run) | `{PROJECT_PATH}/src/screens/index.ts` | Re-exports all generated screens |
| Completion report | `{PROJECT_PATH}/UI_ENGINEER_SDF_COMPLETE.md` | Summary of screens generated, flags, suggested next steps |
| Execution log | `{PROJECT_PATH}/logs/ui-engineer-sdf.log` | Timestamped log of all agent actions |
| State file | `{PROJECT_PATH}/.claude/ui-engineer-sdf-state.json` | Phase completion state for resumption |

---

## Standards Enforced

All shared standards apply (accessibility WCAG 2.2 AA, security, design tokens, Figma extraction). SDF-specific Iron Rules:

### Iron Rules — Blueprint React Native

Each rule has a mechanical check. The validation agent (`ui-engineer-sdf-validation-agent`) enforces all of these.

| Rule | Check | Severity if violated |
|---|---|---|
| Root element is `<VanillaLayout>` | `grep -rL "VanillaLayout" src/screens/` returns no files | Critical — build will crash without correct root |
| `Navbar` present with `variant` specified | Every screen file contains `<Navbar` | High |
| Exported `{COMPONENT_NAME}Props` interface | `grep -rL "export interface.*Props" src/screens/` returns no files | High |
| `export default` present | `grep -rL "export default" src/screens/` returns no files | High |
| Zero `style={{...}}` props | `grep -rn "style={{" src/screens/` returns empty | High — Blueprint manages layout; inline styles fight it |
| Zero hardcoded colours | `grep -rEn "(#[0-9a-fA-F]{3,6}\|rgb\(\|rgba\()" src/screens/` returns empty | High |
| Zero `onClick` — use `onPress` | `grep -rn "onClick=" src/screens/` returns empty | Critical — React Native does not fire `onClick` |
| Zero `icon="close"` — use `icon="dismiss"` | `grep -rn 'icon="close"' src/screens/` returns empty | Medium — wrong icon silently renders nothing |
| `FormInput` never has a `label` prop | `grep -rn "FormInput" src/screens/` piped through `grep "label="` returns empty | High — label must be a separate `<Type>` component |
| `AccordionItem` title always wrapped in `<Type>` | No `title="` string literal on `AccordionItem` | High |
| `Modal` always uses `useRef<ModalRef>` | No `visible` prop on `Modal` | High — state-controlled Modal is unreliable in Blueprint |
| ESM imports only — zero `require()` | `grep -rn "= require(" src/screens/` returns empty | High |
| Imports from `@barclays/chameleon-blueprint` only | No imports from `@barclays/blueprint-react` or `@barclays/blueprint-css` | Critical — wrong package, nothing will render |

### ViewModel hook rules

| Rule | Check | Severity if violated |
|---|---|---|
| Hook file exists for every screen | `use{COMPONENT_NAME}.ts` present alongside screen | High |
| Hook returns typed state — no `any` | TypeScript compilation passes | High |
| Use-case interfaces injected as parameters — not imported directly | Hook accepts use-case interfaces as arguments | High — enables testing without mocking module system |

---

## Tools and Tech

| Property | Value | Why |
|---|---|---|
| Language | TypeScript | SDF projects are TypeScript-first |
| Framework | React Native | SDF (Shared Design Framework) |
| Component library | `@barclays/chameleon-blueprint` | Only Blueprint components — never raw RN primitives for UI |
| State | Custom hook (`use{ComponentName}`) | SDF convention — no Redux, no Zustand |
| Build check | `npx tsc --noEmit` | TypeScript compile must pass before validation |

### Skills loaded (SDF additions)

| Skill | Source | Purpose |
|---|---|---|
| `barclays-buk-ui-engineer-sdf:sdf` | This plugin | Blueprint component mappings, Iron Rules detail, screen layout patterns, anti-patterns |

---

## Quality Gates (in execution order)

| Gate | Check | Threshold |
|---|---|---|
| TypeScript compile | `npx tsc --noEmit` | Exit 0 |
| Iron Rule validation | `ui-engineer-sdf-validation-agent` — 13 checks | 0 violations |
| Accessibility | `barclays-buk-standards:accessibility` rules applied | 0 Critical violations |

---

## Handoff Criteria

All shared handoff criteria apply. SDF-specific additions:

| Gate | Why |
|---|---|
| Agent tested against a real `@barclays/chameleon-blueprint` SDF project | Component API and prop names change between Blueprint versions; must be validated against current |
| `npx tsc --noEmit` passes on first attempt for all generated screens | TypeScript errors in generated output are a blocker, not a warning |
| `ui-engineer-sdf-validation-agent` passes with APPROVED verdict | Validation agent is the mechanical gate — must be exercised |
| ViewModel hook state fields match OAS response schema on a real spec | Core of Option B — ViewModel generation is the primary new capability |
| All 13 Iron Rules confirmed zero-violation across at least 5 generated screens | One or two screens is not sufficient coverage |

---

## Definition of Done

All shared DoD items apply. SDF-specific additions:

- [ ] Generated screen files import exclusively from `@barclays/chameleon-blueprint`
- [ ] Every screen has a corresponding `use{ComponentName}.ts` hook alongside it
- [ ] Hook state interface fields are typed (no `any`), derived from OAS schema or clearly stubbed with `TODO`
- [ ] `ui-engineer-sdf-validation-agent` returns APPROVED verdict
- [ ] `npx tsc --noEmit` exits 0 on first attempt
