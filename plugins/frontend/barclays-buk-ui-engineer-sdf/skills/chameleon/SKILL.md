---
name: chameleon
description: >
    Cross-platform Chameleon architecture rules for Barclays SDF journeys: Blueprint-first
    UI, platform split file structure, TDD and coverage standards, accessibility,
    Redux typed state management, ChameleonBridge routing, image/icon patterns,
    navigation and back-button rules, loading/error patterns, offline support, and
    technology versions. Load this alongside the sdf skill when building or reviewing
    a Chameleon journey.
user-invocable: false
---

# Chameleon Architecture Standards

> **Owner:** Barclays BUK Platform Engineering
> **Review trigger:** On Chameleon framework major version bump, or constitution amendment
> **Ratified:** 2026-03-17 | **Last Amended:** 2026-07-06 | **Version:** 1.8.0

> [Full library reference](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/libraries/) | [Best practice overview](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/) | [Jest testing standards](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/jest-testing/) | [Linting standards](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/linting/) | [Deployment guide](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/deployment/)

---

## Quick Start

Key things to verify before raising a PR:

- Use `.native.tsx` by exception — only when web and native implementations genuinely differ — see [Section 2](#2-cross-platform-parity)
- All UI MUST use Blueprint components — no raw HTML styling, no custom primitives — see [Section 3](#3-blueprint-first-non-negotiable)
- All state goes through `useAppDispatch`/`useAppSelector` — raw hooks are banned — see [Section 6](#6-typed-state-management)
- All API calls go through `callApiOperation` wrapped in RTK Query — no direct bridge calls from components — see [Section 7](#7-chameleonbridge-routing-architecture)
- Back button behaviour depends on route position — wrong usage is a defect — see [Section 9](#9-navigation-and-back-button-rules)

---

## 1. Technology Versions

| Technology | Required Version |
|---|---|
| React | 19 |
| React Native | 0.80 |
| TypeScript | 5 |
| Node | 22+ |
| Web build | Vite |
| Native build | Metro + Babel |
| State | Redux Toolkit + RTK Query |
| Navigation | `@barclays/chameleon-router` (cross-platform), `@react-navigation/native` (native stack) |
| Package registry | Barclays internal Nexus (`nexus-amazon-pdn.barclays.intranet`) |

### Bootstrapping a new journey

**Option 1 — SDF Template (recommended):** Scaffolds the full journey stack — Chameleon frontend (`fe-{name}`), DAF backend (`x-{name}`), and optional VGW — from a single command.

```bash
npx @barclays/chameleon-sdf-template
# or with flags
npx @barclays/chameleon-sdf-template --name payments --team cobra-squad --vgw
```

> **Full SDF scaffold reference:** [SDF Template](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/sdf-template/)

**Option 2 — Chameleon template only:** Initialises the frontend repo without the backend stack.

```bash
npx @react-native-community/cli@20.0.0 init {yourProjectName} \
  --template @barclays/chameleon-template@latest \
  --pm npm \
  --skip-install \
  --skip-git-init
```

Do not use `npx react-native init` or Create React App — they do not produce a Chameleon-compatible project structure.

---

## 2. Cross-Platform Parity

Every user-facing feature MUST work on iOS, Android, and Web. A feature is not complete until it renders and behaves correctly on all three platforms.

### Adaptive behaviour

| Rule | Requirement |
|---|---|
| Mobile browser vs app | MUST show the same UI |
| Landscape browser vs iPad | MUST show the same UI — the Barclays app runs on iPad in landscape |
| Breakpoints | Use the `chameleon-util` screen size function; do not hardcode breakpoint values |

Platform-specific behaviour differences MUST be documented in the component's interface file.

### File naming convention

| Suffix | Resolved by | Purpose |
|---|---|---|
| `component.tsx` | Vite (web) and Metro fallback | Shared or web-only implementation |
| `component.native.tsx` | Metro (iOS + Android) | React Native override |
| `component.interface.ts` | Both | Shared type definitions — no platform imports |

Rules:
- Every `.native.tsx` MUST have a plain `.tsx` counterpart or the web build will fail
- React Native and libraries that depend on it (`blueprint-react-native`, `react-native-gesture-handler`, etc.) MUST only be imported inside `.native.tsx` files
- Platform split files are used **by exception** — only where web and native implementations genuinely differ; do not create `.native.tsx` speculatively

### Required platform splits

Three structural components almost always require a split because they involve React Native primitives that cannot appear in shared `.tsx` files: the app entry point (`App.tsx` / `App.native.tsx`), the header (`header.tsx` / `header.native.tsx`), and the layout wrapper (`vanilla.tsx` / `vanilla.native.tsx`). A journey is not complete until all three are implemented correctly on all platforms.

> **Full examples with code:** [Cross-Platform Coding](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/cross-platform/)

### The `onPress` / `onClick` trap

Write `onClick` in shared `.tsx` files. The a11y mapper HOC in `chameleon-blueprint` converts it to `onPress` at render time on native. Writing `onPress` in a shared file will not break the native build — the failure is web-only, silent at runtime, with no JavaScript error thrown. The only indicators are a console warning and a TypeScript squiggle. Always run `tsc --noEmit` before pushing.

---

## 3. Blueprint-First (NON-NEGOTIABLE)

All UI MUST use Barclays Blueprint components (`@barclays/blueprint-react`, `@barclays/blueprint-react-native`, `@barclays/chameleon-blueprint`). Custom styling outside the design system is prohibited unless the component gap is documented and bridged through the `blueprint-gecko` adapter layer (`src/components/blueprint-gecko/`).

- New components MUST use Blueprint primitives (Type, Icon, Section, Panel, etc.)
- Theme tokens MUST be used for colours, spacing, and typography — hardcoded values are not permitted
- Any missing Blueprint capability MUST be raised as a blueprint-gecko adapter with a clear justification, not worked around with raw HTML or React Native styles

---

## 4. Test-First (NON-NEGOTIABLE)

TDD is mandatory. The cycle is: write tests, confirm they fail, then implement.

- Tests MUST be written before implementation code
- Separate test files per platform: `*.native.spec.tsx` and `*.web.spec.tsx`
- Jest configuration uses a base `jest.config.ts` that delegates to platform-specific configs (`jest.config.web.ts`, `jest.config.native.ts`) — do not collapse these
- Use `renderWithProviders()` from `src/state/mock/store-test-utils.tsx` for component tests requiring Redux state
- Coverage threshold: **95% minimum** for branches, functions, lines, and statements — CI runs `npm run test:coverage` and fails below this threshold
- `jest-fail-on-console` enforces zero unexpected console errors in tests
- Respect RTL query priority: prefer queries a user would use (text, role, label) and only fall back to `testId` where necessary — test behaviour, not implementation
- All `chameleon-*` bridge libraries MUST be mocked; API response mocks MUST use JSON fixture files (`.json`) rather than inline objects

> **Full jest standards:** [Jest Testing](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/jest-testing/)

---

## 5. Accessibility (NON-NEGOTIABLE)

All interactive elements MUST be accessible to screen readers and assistive technologies.

### Blueprint handles the platform mapping

All Blueprint components are wrapped by the a11y mapper HOC (`libs/blueprint/src/a11y-mapper/mapper.tsx`). Write web ARIA props — the mapper converts them to React Native equivalents automatically at render time. You do not need to write both.

| Web prop you write | React Native prop the mapper produces |
|---|---|
| `aria-label` | `accessibilityLabel` |
| `role` | `accessibilityRole` |
| `aria-describedby` | `accessibilityHint` (resolved from the referenced element's text) |
| `aria-checked` | `accessibilityState={{ checked }}` |
| `aria-selected` | `accessibilityState={{ selected }}` |
| `aria-expanded` | `accessibilityState={{ expanded }}` |
| `aria-live` | `accessibilityLiveRegion` |
| `data-testid` | `testID` |

`aria-hidden={true}` renders a visually hidden placeholder on native — no extra handling required.

### Rules

- Use standard ARIA props on all interactive Blueprint components
- Do NOT manually add `accessibilityLabel`, `accessibilityRole` etc. alongside ARIA props — the mapper will produce duplicates
- For non-Blueprint components (custom wrappers, third-party), add React Native accessibility props directly
- Screen reader text MUST be human-readable (e.g. account numbers formatted digit-by-digit, amounts announced with currency)
- Accessibility MUST be tested — `getByRole`/`getByLabelText` queries are preferred over `getByTestId`

---

## 6. Typed State Management

All application state MUST flow through Redux Toolkit slices and RTK Query.

| Hook | Rule |
|---|---|
| `useAppDispatch` | REQUIRED — raw `useDispatch` from react-redux is PROHIBITED (enforced by ESLint) |
| `useAppSelector` | REQUIRED — raw `useSelector` from react-redux is PROHIBITED (enforced by ESLint) |

| Rule | Requirement |
|---|---|
| New state domains | MUST be implemented as RTK slices in `src/state/` |
| Data fetching | MUST use RTK Query endpoints with tag-based cache invalidation — `useEffect` + `useState` for data fetching is PROHIBITED |
| Direct bridge calls from components | PROHIBITED — ChameleonBridge interactions MUST be wrapped in RTK Query `queryFn` or thunks |
| RTK Query polling | MUST have a documented justification in the screen build plan |

---

## 7. ChameleonBridge Routing Architecture

### callApiOperation — standard API calls

All standard API calls MUST use `callApiOperation` on the bridge, which routes to the DAF backend. Chameleon frontend code MUST NOT reference upstream operation codes — those are owned by the host app and DAF layer.

**Barclays app (mobile):**
```
Chameleon fe  →  callApiOperation (ChameleonBridge)
                       ↓
               Barclays app (bmb-ios / bmb-android)
                       ↓  SPR01
               DAF backend (x-{journeyName})
                       ↓
               Downstream services
```

**Online Banking:**
```
Chameleon fe  →  callApiOperation (ChameleonBridge)
                       ↓
               Online Banking
                       ↓  Channel App / Edge Gateway
               DAF backend (x-{journeyName})
                       ↓
               Downstream services
```

### callLegacyOperation — mobile only

Legacy operation support is available on the Barclays app only. It calls the mobile gateway directly with op codes and bypasses the DAF backend. **Legacy operations are NOT supported on Online Banking.**

```
Chameleon fe  →  callLegacyOperation (ChameleonBridge)
                       ↓
               Barclays app (bmb-ios / bmb-android)
                       ↓  Mobile gateway (op codes)
               Downstream services
```

---

## 8. Image and Icon Patterns

Bundling binary asset files (`.png`, `.pdf`, `.svg`, `.webp`) directly into the bundle is not permitted. React Native `Image` with a `require()` asset reference is prohibited.

There are three approved patterns — use the correct one for the context:

| Need | Pattern |
|---|---|
| Photo or CMS-managed image | `ChameleonBridge.getImage` |
| Icon from the Barclays icon set | `<Icon>` from `@barclays/chameleon-blueprint` |
| Custom SVG not in the icon set | Inline in `src/assets/icons.ts` + `svgToSrc` platform split + `<Multimedia>` |
| `require('./image.png')` | Not permitted |
| `SvgXml` from `react-native-svg` | Not permitted |
| Import from `@barclays/blueprint-icons` | Not permitted — Metro cannot guarantee module evaluation order |

> **Full examples with code:** [Images and Icons](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/images-and-icons/)

---

## 9. Navigation and Back Button Rules

All journeys MUST use `@barclays/chameleon-router` for screen transitions. `chameleon-router` is a cross-platform abstraction — it uses **React Router** under the hood on web and **`@react-navigation/native`** on React Native. You write one set of route definitions; the correct navigation library is resolved per platform automatically. Do not use either library directly in journey code.

The header MUST be decoupled from screen components — screens declare their header configuration (title, actions) via the router context and MUST NOT render a header directly.

### Back button requirement

A back button MUST be present on every screen. The only permitted exception is where navigating back is genuinely not possible (e.g. a confirmation screen that completes an irreversible transaction). Any screen without a back button MUST have that decision documented and approved in the screen build plan.

### Back button implementation

The correct implementation depends on route position. Using the wrong one is a defect.

| Route position | Correct implementation |
|---|---|
| Root route, or any screen where the intent is to exit back to the host app | `chameleonBridge.goBack()` |
| Any route deeper than root where the intent is to remain within the journey | Router `goBack()` or the equivalent `chameleon-router` navigation hook |

Direct ChameleonBridge navigation calls from screen components are PROHIBITED — they MUST be wrapped in RTK Query `queryFn` or thunks (consistent with Section 6).

---

## 10. Loading and Error Patterns

Loading and error behaviour MUST be agreed at the start of every journey and documented in the screen build plan.

### Loading defaults

| Content type | Required behaviour |
|---|---|
| Static content (no remote data) | Renders immediately — no skeleton or spinner |
| Remote-data components | Use Blueprint ghost/skeleton primitives until data resolves; surrounding layout MUST be stable (no content shift on load) |

### Failure handling

Choose one pattern per endpoint and apply it consistently. Mixing patterns without documented rationale is a violation. Agree the pattern per endpoint in the screen build plan, not per implementation PR.

| Pattern | When appropriate |
|---|---|
| Error boundary | Unexpected render-time errors; catches thrown exceptions in the component tree |
| Full-screen error | A failed call that makes the entire screen unusable (e.g. account data unavailable) |
| Inline / modal error | A failed call affecting one component or a non-critical action (e.g. a secondary fetch, a form submission) |

---

## 11. Offline Support

- The `isOffline` prop drives route availability
- Offline-capable features MUST degrade gracefully when `isOffline` is true
- Features that cannot function offline MUST be clearly disabled or hidden, not silently broken

---

## 12. Simplicity and Convention

Follow established project patterns. Do not introduce new libraries, patterns, or architectural layers without documented justification in the plan's Complexity Tracking section.

- File naming: kebab-case for files, PascalCase for components, UPPER_SNAKE_CASE for constants
- Barrel exports via `index.ts` in each component/module directory
- Screen-specific components live under `src/screens/{screen}/components/`; shared components live under `src/components/`
- Commit messages MUST follow conventional-changelog format with JIRA ticket reference (enforced by CommitLint + Husky)

---

## Agent Self-Check

Before raising a PR, confirm:

- [ ] Platform split files (`.native.tsx`) only exist where web and native implementations genuinely differ — not created speculatively
- [ ] Required structural splits present: `App.tsx`/`App.native.tsx`, `header.tsx`/`header.native.tsx`, `vanilla.tsx`/`vanilla.native.tsx`
- [ ] No React Native imports in shared `.tsx` files (only in `.native.tsx` files)
- [ ] All UI uses Blueprint components — no raw HTML styling, no custom primitives outside blueprint-gecko
- [ ] Tests written before implementation; separate `*.native.spec.tsx` and `*.web.spec.tsx` files
- [ ] Coverage at or above 95% across branches, functions, lines, and statements
- [ ] ARIA props used on all interactive elements — no manual `accessibilityLabel`/`accessibilityRole` alongside ARIA props
- [ ] `useAppDispatch` and `useAppSelector` used exclusively — no raw `useDispatch`/`useSelector`
- [ ] All API calls use `callApiOperation` (or `callLegacyOperation` for mobile-only legacy ops) wrapped in RTK Query `queryFn` or thunks — no direct bridge calls from components
- [ ] No upstream operation codes referenced in Chameleon frontend code
- [ ] Image/icon pattern matches context: AEM remote → `getImage`, Blueprint icon → `<Icon>` from chameleon-blueprint, custom SVG → `icons.ts` + `svgToSrc`
- [ ] No binary asset files bundled via `require()`; no `SvgXml`; no direct import from `@barclays/blueprint-icons`
- [ ] Every screen has a back button, or its absence is documented and approved
- [ ] Back button uses `chameleonBridge.goBack()` at root, `Router.goBack()` mid-journey
- [ ] Loading and error patterns agreed per-endpoint in screen build plan
- [ ] `isOffline` prop handled — offline-capable features degrade gracefully

---

## Areas for Specialist Extension

This skill covers the cross-platform Chameleon architecture baseline. The following areas need extension by the relevant teams:

- **Mobile app team** — Legacy operation code catalogue and which journeys are eligible for `callLegacyOperation`
- **Online Banking team** — Edge Gateway specifics and channel app routing configuration
- **Design system team** — Blueprint ghost/skeleton component usage patterns and agreed loading state durations
