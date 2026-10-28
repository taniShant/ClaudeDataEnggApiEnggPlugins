---
name: sdf
description: "Blueprint React Native (@barclays/chameleon-blueprint) component mappings, Figma MCP/REST API usage, screen generation heuristics, iron rules, and quality gates for generating safe-area-wrapped .tsx screens for SDF (Software Development Framework) projects."
---

# barclays-buk-ui-engineer-sdf Domain Reference

## Quick Start

```bash
# Generate screens from a Figma URL
/ui-engineer-sdf /path/to/sdf-app --jira UCG-1234 \
  --figma-url "https://www.figma.com/file/ABC123?node-id=12%3A45"

# Generate screens from a text description (no Figma)
/ui-engineer-sdf /path/to/sdf-app --jira UCG-1234 \
  --additional-input "Create a payment confirmation screen with amount, payee name, and a Confirm button"

# Full automation — no human prompts
/ui-engineer-sdf /path/to/sdf-app --jira UCG-1234 \
  --figma-url "https://www.figma.com/file/ABC123?node-id=12%3A45" --full-automation
```

Generated output: `src/screens/[ScreenName]/[ScreenName].tsx` — a safe-area-wrapped Blueprint component, typed props, ESM imports, JIRA traceability comment.

---

## Section 1: Overview and Scope

### What This Plugin Does

`buk-ui-engineer-sdf` converts a Figma page URL into production-ready, screen-level React Native components using the **Barclays Blueprint** design system for Chameleon aka SDF Cross Platform UI (`@barclays/chameleon-blueprint`). It uses the Figma Dev Mode MCP server to extract real design context and maps Figma elements to the correct Blueprint components.

Each generated screen includes:
- A safe-area root wrapper (see Section 3.1 for the correct approach)
- A `Navbar` with appropriate variant
- Fully typed exported `Props` interface
- ESM-compliant imports from `@barclays/chameleon-blueprint`
- No inline styles, no hardcoded colours, no `require()` calls
- Task traceability comment linking screen → Figma node → JIRA

### Target Channels

This plugin targets **SDF (Software Development Framework)** projects used by:
- **Online Banking** — React Native with `@barclays/chameleon-blueprint`
- **Mobile** — React Native with `@barclays/chameleon-blueprint`

### When to Use

- Bootstrapping a new React Native screen from a Figma design
- Producing consistent Blueprint component skeletons for a new feature
- Accelerating design-to-code handoff for the Barclays mobile or OB app

### What Success Looks Like

- `npx tsc --noEmit` exits 0 with zero TypeScript errors
- Every generated `.tsx` file exports a default component and a named `Props` interface
- All components imported from `@barclays/chameleon-blueprint`
- No inline styles, hardcoded colours, or `require()` calls

---

## Section 2: Figma API Reference

### Two-API Strategy

The plugin uses two different Figma APIs for different purposes:

| API | Used For | Auth |
|-----|----------|------|
| **MCP** (`figma-local`) | Design context, component hierarchy, styles, variables | Figma Desktop App session — no token needed |
| **REST API** | File structure, screen detection, batch screenshots | `X-Figma-Token` header (from env `FIGMA_TOKEN`) |

### FIGMA_TOKEN — When It Is and Isn't Needed

`FIGMA_TOKEN` is a Figma personal access token. It is **only required for bulk screen discovery** — when you pass a whole Figma file URL (no `node-id`) and want the plugin to automatically find all screens in the file by scanning the document tree.

**Token required:**
```
/ui-engineer-sdf /path/to/app --jira UCG-1 --figma-url "https://www.figma.com/file/ABC123/MyDesign"
# ↑ No node-id — plugin must call REST API to discover screens
```

**Token NOT required** (these all work without it):
```
# Single node URL — node-id is explicit, no discovery needed
--figma-url "https://www.figma.com/file/ABC123?node-id=12%3A45"

# Description only — no Figma URL at all
--additional-input "Login screen with email, password, and sign in button"
```

Design extraction (colours, layout, components) always uses the **MCP server** via your Figma Desktop app — no token involved.

**Set the token once:**
```bash
export FIGMA_TOKEN="your-personal-access-token"
```

### MCP Tool Usage

All MCP calls use the `figma-local` with these parameters:

```
nodeId:           "1:16848"         — target node ID from Figma URL
clientLanguages:  "typescript"
clientFrameworks: "react-native"
artifactType:     "WEB_PAGE_OR_APP_SCREEN"
```

**Available MCP tools:**

| Tool | What it Returns | When to Use |
|------|----------------|-------------|
| `get_design_context` | Full component hierarchy, colors, styles, text, layout | Always — primary design extraction |
| `get_screenshot` | Visual reference image | After design context — visual reference |
| `get_variable_defs` | Design tokens (colors, spacing, typography) | To map Figma variables to Blueprint tokens |
| `get_metadata` | XML element tree with position/size metadata | Structural validation only |

### Figma REST API — Screen Detection

**Endpoint:** `GET https://api.figma.com/v1/files/{fileKey}`
**Header:** `X-Figma-Token: {FIGMA_TOKEN}`

**Screen detection predicate** — a node qualifies as a screen if:
1. `node.type` is `FRAME` or `COMPONENT`, AND
2. Either:
   - Name matches the project prefix (e.g. `QQ_Welcome`, `BB_Dashboard`)
   - OR dimensions match mobile screen size: `|width - 360| ≤ 50 AND |height - 800| ≤ 50`

**Screen metadata extracted per node:**
```json
{
  "id": "0:34854",
  "name": "QQ_Welcome",
  "componentName": "WelcomeScreen",
  "dimensions": { "width": 390, "height": 844 },
  "figmaUrl": "https://www.figma.com/file/{key}?node-id=0:34854"
}
```

**Component name derivation:**
- Strip prefix (e.g. `QQ_`) → PascalCase → append `Screen` if missing
- `QQ_Welcome` → `WelcomeScreen`
- `BB_CustomerDashboard` → `CustomerDashboardScreen`

### Node ID Extraction from URL

```
URL: https://www.figma.com/file/ABC123/MyDesign?node-id=12%3A45
node-id query param decoded: "12:45"
```

---

## Section 3: Blueprint Component Mappings

**All components imported from `@barclays/chameleon-blueprint`** unless otherwise stated.

---

### 3.0: Platform Parity — Check Before You Map

#### Code Connect takes precedence over all component mappings

**If `get_design_context` returned a `<CodeConnectSnippet data-snippet-language="React Native">` for a component, use that snippet's structure directly.** Do not substitute a different component based on the cross-platform safe set or the mappings in Section 3.2–3.11. The Code Connect snippet is the design system team's canonical React Native implementation.

- If the snippet imports from `@barclays/blueprint-react-native`, generate a `.native.tsx` split per Section 3.0d — the shared `.tsx` uses the web/heuristic mapping, the `.native.tsx` uses the snippet verbatim (adapting prop values from the Figma design)
- If no Code Connect snippet is present for a node, fall through to the mappings below as normal

#### chameleon-blueprint is web-first

`@barclays/chameleon-blueprint` is a **web-first bridging layer**. It wraps two underlying packages:
- `@barclays/blueprint-react` — web implementations (the source of truth for prop APIs)
- `@barclays/blueprint-react-native` — React Native implementations

The package exposes the **web React prop API** on both platforms. A runtime bridge (patches + a11y remapping HOC) converts web props to their native equivalents automatically:

| Web prop you write | Native equivalent the bridge injects |
|---|---|
| `onClick` | `onPress` |
| `onChange` (ChangeEvent) | `onChangeText` (string) |
| `href` | `Linking.openURL(href)` |
| `data-testid` | `testID` |
| `aria-label` | `accessibilityLabel` |

**Write web React props.** The bridge handles native. Do not write `onPress` or `onChangeText` in shared `.tsx` files — these are native-only and will not work on web.

> **Note — the bridge is incomplete.** Not every component has a patch. When in doubt, read the actual `.d.ts` before using a component (see Section 3.0b below).

**Rule: `.native.tsx` splits are by exception only.** Most screens should be a single shared `.tsx` file. Only create a `.native.tsx` split when:
- A required component is native-only and has no web equivalent (e.g. `FormInputDatepicker`, `Snackbar`)
- A layout difference is so significant it cannot be expressed in shared markup (e.g. the `header` and `vanilla` layout components)

Do not create `.native.tsx` splits pre-emptively. Check parity first.

---

#### 3.0c: Responsive layouts — breakpoints and the `useIsMobile` hook

SDF journeys run on mobile, tablet, and web browser. Screens must respond to viewport width. The correct approach is a project-local `useIsMobile` hook using `useScreenWidthQuery` from `@barclays/chameleon-utils`.

**`useScreenWidthQuery` checks whether the viewport is exactly within a named band** (`'xs' | 'sm' | 'md' | 'lg' | 'xl'`). To express "mobile-sized" (below the `md` breakpoint), combine the bands that cover mobile:

```typescript
// CORRECT — combine xs and sm bands
import { useScreenWidthQuery } from '@barclays/chameleon-utils';

export const useIsMobile = (): boolean => {
  const isXs = useScreenWidthQuery('xs');
  const isSm = useScreenWidthQuery('sm');
  return isXs || isSm;
};
```

**Do NOT use a single band as a threshold.** `!useScreenWidthQuery('md')` is not a mobile guard — it returns `true` for every viewport that is NOT exactly in the `md` band, which is nearly always.

**`useScreenWidthQuery` has a native implementation** (`@barclays/chameleon-utils` ships `utils.native.js`). No platform split is needed — the same hook works on web and native.

**The web implementation debounces resize events by 500ms.** This is imperceptible in normal use — users do not resize browser windows mid-session in production. If you have a specific reason to eliminate the delay (e.g. a resize-heavy dev tool or animation), pass `0` as the second argument: `useScreenWidthQuery('md', 0)`. Note the native type signature does not accept a second argument, so doing this requires a platform split (`useIsMobile.ts` with `delay=0`, `useIsMobile.native.ts` without).

**VanillaLayout responsive pattern** — on `md+` screens, constrain content to a centred 480px column:

- Web: wrap in a centred flex container with `maxWidth: 480`
- Native: pass `maxWidth: 480` to `ScrollView` and the footer `View` with `alignItems: 'center'` on the outer container

The layout component (`src/components/layouts/vanilla/`) handles this — screens themselves do not need any width logic.

**Rule: any hook or utility that references `window`, `document`, or other browser globals MUST have a `.native.ts` platform split.** Metro resolves the base `.ts` file for native builds only when no `.native.ts` exists — a hook without a split that references `window` will crash the native build silently.

---

#### 3.0d: Automatic platform split triggers — generate BOTH `.tsx` and `.native.tsx`

When the Figma design contains any of the following patterns, the agent MUST generate both a shared `.tsx` and a `.native.tsx`. Do not flag and continue — generate both files.

**When generating `.native.tsx`, always extract and apply layout measurements from the Figma frame geometry.** Blueprint component tokens (`spaced`, `spacingBottom`) alone are insufficient for native layout fidelity — they control internal component padding but not the spacing *between* components. Extract these values from the `get_design_context` output and apply them as explicit style values:

| Figma geometry | CSS class in `get_design_context` | Native style |
|---|---|---|
| Gap between stacked panels/cards | `gap-[16px]` on parent container | `gap: 16` on wrapper `View` |
| Horizontal padding on content area | `left-[24px]` / `w-[314px]` | `paddingHorizontal: 24` on wrapper `View` |
| Gap between icon and text in a row | `gap-[Npx]` inside a flex row | `gap: N` on the row `View` |
| Footer pinned near bottom | `top-[698px]` on 829px frame | `marginTop: 'auto'` or separate footer `View` outside scroll content |
| Top padding of content area | `top-[112px]` | `paddingTop: N` on wrapper `View` |

| Figma pattern | `.tsx` (shared / web) | `.native.tsx` (native override) |
|---|---|---|
| **Horizontal key/value table** (label left, value right, same row, white card, row separators) | `Section + SectionItem` stacked fallback | `Table/TableRow/TableCell` from `@barclays/blueprint-react-native` |
| **Horizontal flex row** (two or more elements side-by-side, not a grid) | `<div style={{ display: 'flex', flexDirection: 'row', gap: '8px' }}>` | `<View style={{ flexDirection: 'row', gap: 8 }}>` from `react-native` |
| **Interactive Tile** (tap/press handler on a card) | Non-interactive `Tile` or `FormRadio bordered` | `Tile` with `onPress` |
| **Native-only component** in design (`GuideTile`, `SuperHeroHeader`, `FormInputDatepicker`, `Snackbar`, `FormInputButton`, `Dropdown`, `FormSlider`) | Use the documented web alternative from Section 3.0 | Use the native component directly |

**File structure when both are generated** — always use a `.types.ts` file. Never import `Props` across platform files:

```
MyScreen/
  MyScreen.types.ts       ← Props interface (shared)
  MyScreen.tsx            ← web / shared implementation
  MyScreen.native.tsx     ← native override
  index.ts                ← re-exports the default: export { default } from './MyScreen'
```

The `index.ts` barrel exports only the default — Metro resolves `MyScreen.native.tsx` on native automatically when it exists. The barrel itself stays platform-agnostic.

**Recognising a horizontal key/value table in Figma:** The Figma node has rows where each row contains two text nodes side-by-side — a label (muted/grey colour, left-aligned) and a value (medium weight, right-aligned). The container is a white rounded card. This is the most common pattern requiring a native split in financial screens.

**`AccordionItem` with toggle state also requires a split** — `onPress` is native-only. In shared `.tsx` use `onChange`; in `.native.tsx` import `AccordionItem` directly from `@barclays/blueprint-react-native` (not via `chameleon-blueprint`) to access `onPress`. This is the one case where a component import differs between platform files despite `AccordionItem` appearing in the cross-platform safe set.

---

#### 3.0a: Platform split pattern — when a split is genuinely required

Splits are by exception only. When one IS required, always use a shared `.types.ts` file for the `Props` interface. Never import `Props` from one platform file into the other — Metro resolves `./MyScreen` to `./MyScreen.native.tsx` on native, creating a circular import that crashes with "element type is invalid: expected a string but got undefined".

**Correct structure:**
```
MyScreen/
  MyScreen.types.ts       ← Props interface lives here
  MyScreen.tsx            ← web: imports Props from .types.ts
  MyScreen.native.tsx     ← native: imports Props from .types.ts
```

```typescript
// MyScreen.types.ts
export interface Props { ... }

// MyScreen.tsx
import type { Props } from './MyScreen.types';
export type { Props };  // re-export so importers can use MyScreen's Props without knowing about .types.ts
// ... web implementation

// MyScreen.native.tsx
import type { Props } from './MyScreen.types';
// DO NOT re-export Props here — the .tsx file owns the re-export
// ... native implementation
```

**The `export type { Props }` re-export in `.tsx` is required and intentional.** Validation checks grep for `export interface.*Props` OR `export type {.*Props` in screen files — the re-export pattern satisfies the check. Do not add a duplicate `export interface` in `.tsx` when Props is defined in `.types.ts`.

---

### 3.0b: Read the `.d.ts` before generating — prevent hallucinated props

**Before writing any component usage, read the actual installed type definition from `node_modules`.** Do not rely on memory or training data for prop names — Blueprint APIs change between versions and the installed version is the ground truth.

```bash
# Find the type definition for a component
find node_modules/@barclays/chameleon-blueprint -name "*.d.ts" | xargs grep -l "ProgressBarProps\|export.*ProgressBar" | head -5
```

Or read the package index directly:

```bash
# Check the TypeScript entry point
cat node_modules/@barclays/chameleon-blueprint/package.json | grep typings
# Then read that file to see all exports
```

**For each component you plan to use, verify:**
1. It is exported from `@barclays/chameleon-blueprint` (not just from one of the underlying packages)
2. The prop names you intend to use exist in the `.d.ts` — check spelling exactly
3. Required props are provided

**Known cases where training data is wrong:**

| Component | Wrong (do not use) | Correct (from `.d.ts`) |
|---|---|---|
| `ProgressBar` | `value`, `max` | `percent` (0–100), `children` (label, required) |
| `Progress` | anything — not cross-platform safe | Use `ProgressBar` instead |
| `FormInput` (web/shared) | `onChangeText`, `autoCapitalize` | `onChange: React.ChangeEvent<HTMLInputElement>` |
| `Link` (web/shared) | `onClick` only, no `href` | `href` is required — use `Button variant="subtle"` for action-only triggers |
| `Separator` | `spacingBottom` | `spacing` |
| `Section` / `SectionItem` | `style` prop | No `style` prop — use Blueprint spacing tokens only |

If a component's props cannot be confirmed from the `.d.ts`, do not use that component. Choose the nearest confirmed alternative from the safe set.

---

#### Figma frame width vs simulator width

Barclays SDF Figma frames use a **360px canvas width** — a generic mobile minimum. No iOS simulator matches this exactly (iPhone SE = 375px, iPhone 13/14/15 = 390px, iPhone 16 = 393px). Text wrapping will differ between Figma and any simulator because the available text width is wider on device. This is expected and correct — do not flag line-wrap differences as fidelity failures. Only flag layout structure differences (wrong component, wrong spacing token, missing section).

---

#### Cross-Platform Safe Set (50 components — safe in shared `.tsx`)

These components exist in both `blueprint-react` and `blueprint-react-native`:

```
Accordion         AccordionItem     Alert             Arrange
Badge             Banner            Brick             Button
ButtonGroup       Carousel          Chip              ChipGroup
ControlPanel      Form              FormCheckbox      FormInput
FormItem          FormMultiItem     FormRadio         FormTextArea
Ghost             Grid              HeroAlert         Icon
Indicator         InsightCard       Link              List
Loading           MiniBanner        Modal             Multimedia
Navbar            Notification      NumberStepper     PaginationSimple
Panel             Pips              Progress          ProgressBar
ProgressVertical  Quicklink         Section           SegmentedButtons
Separator         SimpleFileUpload  SlimBanner        Table
Tabs              Tile
```

---

#### Native-Only Components (require `.native.tsx` split if web support is needed)

These exist only in `blueprint-react-native`. Using them in a shared `.tsx` will break on web:

| Component | Web alternative |
|---|---|
| `Dropdown` | `FormRadio bordered` or a custom select |
| `FormInputButton` | `FormInput` + separate `Button` |
| `FormInputDatepicker` | Use `FormInput type="date"` on web, plain `FormInput` on native — `FormInputDatepicker` may not exist in the installed version; verify with `grep -r "FormInputDatepicker" node_modules/@barclays/blueprint-react-native/` before using |
| `FormSlider` | `NumberStepper` or range input |
| `GuideTile` | `Tile` with `Icon` + `Type` children |
| `Interrupt` | `Modal` |
| `PasscodeIndicator` | `Pips` |
| `SearchButton` | `FormInput` + `Button` |
| `SimpleTimer` / `Timer` | Custom implementation |
| `Snackbar` | `Notification` |
| `SuperHeroHeader` | `Section` + `Type` hero pattern |
| `Toggle` | `FormCheckbox` |
| `TogglePanel` | `Accordion` |
| `Type` (native pkg name) | Exported as `Type` via chameleon-blueprint on both — use `Type` from `@barclays/chameleon-blueprint`, never import `Type` from `blueprint-react-native` directly |

---

#### Web-Only Components (never use in a Chameleon shared `.tsx` or `.native.tsx`)

These exist only in `blueprint-react`. They will not resolve on React Native:

```
Account             Autocomplete        Box                 BrandLogo
Breadcrumbs         ComplexDropdown     Content             ControlPane
Currency            DescriptionList     Dialog              DragDrop
DrawerSheet         Footer              FormButton          FormInputWithRange
FormSelect          Hero                MediaSection        MenuIcon
MicroTheme          Nav                 Page                Pagination
PopupNav            ProgressCircular    ScreenReader        SearchDropdown
SegmentedNavigation TabLink             ThemeProvider       Toast
Typography
```

**Note:** `Typography` (web) and `Type` (native) are both surfaced as `Type` via `@barclays/chameleon-blueprint`. Always use `Type` from `chameleon-blueprint` — never import `Typography` directly.

---

### 3.1 Screen Structure — Always Required

Every generated screen MUST handle safe area insets and scrolling. The standard approach is `VanillaLayout`, a project-local component present in every SDF project scaffolded from the template.

**Step 1: Detect the wrapper to use**

- Check `src/components/layouts/vanilla/` — if present, import from there
- If absent, use `SafeAreaView` + `ScrollView` from React Native directly

**When VanillaLayout exists** (most projects):

```typescript
import React from 'react';
import { VanillaLayout } from '../../components/layouts/vanilla';
import { Section, SectionItem, Navbar, Type } from '@barclays/chameleon-blueprint';

export interface WelcomeScreenProps {
  onGetStarted: () => void;
  isLoading?: boolean;
}

function WelcomeScreen({ onGetStarted, isLoading = false }: WelcomeScreenProps): React.ReactElement {
  return (
    <VanillaLayout>
      <Navbar variant="standard" title="Welcome" />
      <Section variant="secondary">
        <SectionItem spacingBottom="lg">
          {/* screen content */}
        </SectionItem>
      </Section>
    </VanillaLayout>
  );
}

export default WelcomeScreen;
```

**When VanillaLayout is absent** (fall back to React Native primitives):

```typescript
import React from 'react';
import { SafeAreaView, ScrollView } from 'react-native';
import { Section, SectionItem, Navbar, Type } from '@barclays/chameleon-blueprint';

function WelcomeScreen({ onGetStarted }: WelcomeScreenProps): React.ReactElement {
  return (
    <SafeAreaView style={{ flex: 1 }}>
      <ScrollView contentContainerStyle={{ flexGrow: 1 }}>
        <Navbar variant="standard" title="Welcome" />
        <Section variant="secondary">
          <SectionItem spacingBottom="lg">
            {/* screen content */}
          </SectionItem>
        </Section>
      </ScrollView>
    </SafeAreaView>
  );
}
```

**Note:** `VanillaLayout` is NOT exported from `@barclays/chameleon-blueprint`. It is a project-local component. Never import it from the Blueprint package.

**VanillaLayout footer pinning contract:** On native, `VanillaLayout` renders all direct children **except the last one** inside a `ScrollView`. The last direct child is rendered outside the scroll view as a pinned footer. This means: put scrollable content in a `Section` first, put the footer action (primary button, links, helper text) in a separate `Section` last. Both must be direct children of `VanillaLayout` — nesting the footer `Section` inside the content `Section` breaks the pinning contract and the footer will scroll with content.

### 3.2 Layout Components

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Content section (gray #f6f6f6) | `Section` | `<Section variant="secondary">...</Section>` |
| Content section (white) | `Section` | `<Section variant="primary">...</Section>` |
| White card / panel | `SectionItem` | `<SectionItem>...</SectionItem>` — NOT wrapped in Section |
| Spacing container | `SectionItem` | `<SectionItem spacingBottom="md">...</SectionItem>` |
| Multi-column grid | `Grid` | `<Grid columns={2} gap="md">...</Grid>` |
| Horizontal row | platform split | Web: `<div style={{ display: 'flex', flexDirection: 'row', gap: '8px' }}>`, Native: `<View style={{ flexDirection: 'row', gap: 8 }}>` — `Arrange` has no `direction` prop; `Arrange.Item` does not exist on web |

**SectionItem spacing values:** `'2xl' | 'xl' | 'lg' | 'md' | 'sm' | 'xs'` (also `spacing` and `spacingTop`)

**Section variants:** `'primary'` (white) | `'secondary'` (gray #f6f6f6)

### 3.3 Typography

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Heading / Title | `Type` | `<Type color="title" size="xl" weight="bold">Heading</Type>` |
| Section header (18px Medium — e.g. "Higher rate", "Things to know") | `Type` | `<Type size="md" color="title">Header</Type>` — no `weight` prop needed, `size="md"` resolves to `BarclaysEffraApp-Medium` 18px |
| Body text (16px Regular, #272727) | `Type` | `<Type color="title">Body text</Type>` — **NO `size` prop**, add `color="title"` when Figma specifies `#272727` |
| Body text (16px Regular, #515151 muted) | `Type` | `<Type>Body text</Type>` — **NO `size` prop**, no `color` prop — defaults to muted grey |
| Body text medium (16px Medium, #272727) | `Type` | `<Type weight="medium" color="title">Text</Type>` — **NO `size` prop** |
| Caption / small | `Type` | `<Type size="sm">Caption</Type>` |
| Error message | `Type` | `<Type size="sm" color="error">Error message</Type>` |
| Success message | `Type` | `<Type size="sm" color="success">Success message</Type>` |

> **CRITICAL — `BarclaysLightTheme` typography scale does NOT map `size` props the way you expect:**
>
> | `size` prop | Resolved fontFamily | fontSize |
> |---|---|---|
> | *(omitted — default)* | `BarclaysEffraApp-Regular` | 16px |
> | `"xs"` | `BarclaysEffraApp-Regular` | 12px |
> | `"sm"` | `BarclaysEffraApp-Regular` | 14px |
> | `"md"` | **`BarclaysEffraApp-Medium`** | **18px** | ← correct for `Barclays/Mobile & Tablet/Medium/Medium` section headings |
> | `"lg"` | `BarclaysEffraApp-Medium` | 20px |
> | `"xl"` | `BarclaysEffraApp-Medium` | 24px |
>
> **`size="md"` is NOT 16px Regular body text** — it is 18px Medium. For 16px Regular (`Barclays/Desktop/Standard/Regular` in Figma), omit `size` entirely. Only add `weight="medium"` if the Figma token specifies Medium weight at 16px.

**Type Props:**
- `size`: `'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl'`
- `color`: `'success' | 'error' | 'warning' | 'inverse' | 'info' | 'title' | 'disabled'` — **NO `'secondary'`, NO `'action'`** — `'action'` does not exist; use `'info'` for interactive/link-style blue text
- `weight`: `'light' | 'regular' | 'medium' | 'bold' | 'heavy'`
- `alignment`: `'left' | 'right' | 'center'`

### 3.4 Navigation

#### Decoupled header — check before adding Navbar to any screen

**Before rendering any Navbar inside a screen component, check `src/App.tsx` (and `src/App.native.tsx`).**

If `ChameleonRouter` receives a `header={...}` prop, the project uses a **decoupled header**. In this case:
- Screens MUST NOT render `Navbar` directly — the header component handles it
- Screen title is set via `options.title` in the route definition in `routes.tsx`
- Rendering a Navbar inside a screen alongside the router header produces a double header — this is a defect

```typescript
// App.tsx — decoupled header pattern
<ChameleonRouter screens={routes} header={Header} />
//                                 ↑ if this prop exists, screens must not render Navbar
```

If `ChameleonRouter` has NO `header` prop, screens own their own Navbar and must render one.

#### Back button rules (from `barclays-buk-ui-engineer-sdf:chameleon` Section 12)

A back button MUST be present on every screen. The only permitted exception is a confirmation screen that completes an irreversible transaction — that decision must be documented.

The correct back button implementation depends on route position:

| Route position | Correct implementation |
|---|---|
| Root route (`canGoBack=false`) — exits to host app | `BarclaysBridge.goBack()` from `@barclays/chameleon-bridge` |
| Any screen deeper than root (`canGoBack=true`) — stays in journey | `useNavigate().goBack()` from `@barclays/chameleon-router` |

The `canGoBack` boolean is provided by `ChameleonHeaderProps` on the header component. Use it to switch between the two implementations — **always render the back button, never suppress it**. The header component handles this routing logic centrally so individual screens do not need to be aware of their position in the stack.

Direct `chameleonBridge` calls from screen components are prohibited. They must be wrapped.

#### Header component — required platform split

The `header` component (`src/components/header/`) always requires a `.native.tsx` split. Web uses `LinkButton` + `useNavigate`; native uses equivalent React Navigation primitives. This split is part of the project scaffold — do not generate it as part of screen composition.

#### Other navigation components

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Tab navigation | `Tabs` + `Tab` | See Tabs pattern below |
| Pagination | `PaginationSimple` | `<PaginationSimple currentPage={1} totalPages={10} />` |

**Tabs Pattern — uses children, NOT items array:**
```typescript
<Tabs initialTabIndex={0} activeTabChanged={(index) => setActive(index)}>
  <Tab label="Tab 1">
    <Type>Tab 1 content</Type>
  </Tab>
  <Tab label="Tab 2">
    <Type>Tab 2 content</Type>
  </Tab>
</Tabs>
```

### 3.5 Buttons & Links

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Primary CTA button | `Button` | `<Button variant="primary" fullWidth onClick={handler}>Label</Button>` |
| Secondary button | `Button` | `<Button variant="secondary" onClick={handler}>Label</Button>` |
| Subtle / ghost button | `Button` | `<Button variant="subtle" onClick={handler}>Label</Button>` |
| Danger / destructive | `Button` | `<Button variant="primary" status="danger">Delete</Button>` |
| Inline text link (navigates somewhere) | `Link` | `<Link href="/path" onClick={handler}>Link text</Link>` |
| Inline text action (no destination, button semantics) | `Button variant="subtle"` | `<Button variant="subtle" onClick={handler}>Cancel</Button>` |
| Inline text action (no destination, text-level styling) | `Type` + `underline` | `<Type underline onClick={handler}>Enter address manually</Type>` |

**Button Props:**
- `variant`: `'primary' | 'secondary' | 'subtle'`
- `status`: `'default' | 'danger'`
- `fullWidth`: boolean — use for CTAs spanning the full container width
- `onClick`: `() => void` — web prop; bridge converts to `onPress` on native automatically
- `media`: ReactNode, `mediaPosition`: `'left' | 'right'`

**Link in `.native.tsx` splits:** Inside a `.native.tsx` file you can use `Link` with `onPress` directly (no `href` required) — this is valid because Metro resolves to the native implementation which accepts `onPress`. This is the correct pattern for footer links like "Barclays Verify" that trigger a callback. Do NOT use `href="#"` as a dummy — use `onPress` directly in native files.

```typescript
// In .native.tsx — onPress is valid, no href needed
<Link onPress={onBarclaysVerifyPress}>Barclays Verify</Link>
```

**Link requires `href`.** For inline text actions with no navigation destination, two alternatives:
- `Button variant="subtle"` — semantically a button, appropriate for primary inline actions (Cancel, Edit)
- `Type underline onClick={handler}` — text-level styling with click handler, appropriate for secondary inline prompts (Enter manually, Forgot password)

**`LinkButton` does NOT exist** — use `Link` (with href), `Button variant="subtle"`, or `Type underline`.

### 3.6 Form Components

**CRITICAL — FormInput has NO `label` prop.** Labels must be separate `Type` components.

**CRITICAL — never use `FormItem` in shared `.tsx` OR as a top-level import from `@barclays/chameleon-blueprint`.** `FormItem` is a native component that uses `React.cloneElement` on its children — it crashes on web with "argument must be a React element but you passed undefined". This failure is silent at compile time and only surfaces as a runtime crash on web. Always use the `Type` + `FormInput` pattern directly inside `SectionItem`.

**Standard Form Field Pattern:**
```typescript
<SectionItem spacingBottom="md">
  <Type size="md" weight="medium">Email Address</Type>
  <FormInput
    value={email}
    onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)}
    placeholder="user@example.com"
  />
  {emailError && <Type size="sm" color="error">{emailError}</Type>}
</SectionItem>
```

`FormInput` extends `ComponentPropsWithoutRef<"input">` on web. Use standard HTML input props — `onChange` with a `ChangeEvent`, not `onChangeText`. The bridge converts this to `onChangeText` on native.

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Form container | `Form` | `<Form>...</Form>` |
| Text input field | `FormInput` | `<FormInput value={value} onChange={(e) => handler(e.target.value)} placeholder="..." />` |
| Textarea | `FormTextArea` | `<FormTextArea value={value} onChange={(e) => handler(e.target.value)} />` |
| Checkbox | `FormCheckbox` | `<FormCheckbox checked={val} onChange={handler} label="Label" />` |
| Radio button | `FormRadio` | `<FormRadio checked={val} onChange={handler} label="Label" bordered />` |
| Input with button | `FormInputButton` (.native.tsx) / `FormInput` + `Button` (.tsx) | Native-only — requires platform split if web support needed |
| Number stepper | `NumberStepper` | `<NumberStepper value={val} onChange={handler} min={0} max={100} />` |
| PIN / secure entry | `SecureCode` | `<SecureCode length={6} onChange={handler} />` |

**FormRadio — CRITICAL API:**
```typescript
// CORRECT
<FormRadio
  bordered              // adds white card style
  checked={selected === 'opt1'}   // 'checked' NOT 'selected'
  onChange={() => setSelected('opt1')}
  label="Option Label"  // REQUIRED — string, NOT children
  description="Optional help text"
/>

// WRONG — do NOT do this
<FormRadio selected={true}>
  <Type>Label</Type>
</FormRadio>
```

**FormRadio Props:**
| Prop | Type | Required |
|------|------|----------|
| `label` | string | YES |
| `checked` | boolean | No |
| `onChange` | `(val: boolean) => void` | No |
| `bordered` | boolean | No — adds card border |
| `description` | string | No |
| `disabled` | boolean | No |
| `alignRight` | boolean | No |
| `error` | boolean | No |

### 3.7 Feedback & Status

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Info/warning/error alert | `Alert` | `<Alert variant="info" media={<Icon icon="info" />}><Type>Message</Type></Alert>` |
| Slim banner | `SlimBanner` | `<SlimBanner media={<Icon icon="info" />}>Banner text</SlimBanner>` |
| Badge / label | `Badge` | `<Badge variant="success">New</Badge>` |
| Chip / tag | `Chip` | `<Chip label="Tag" onRemove={handler} />` |
| Chip group | `ChipGroup` | `<ChipGroup items={chips} />` |
| Loading spinner | `Loading` | `<Loading size="lg" />` |
| Journey step indicator | `ProgressBar` | `<ProgressBar percent={67} labelPosition="below"><Type alignment="center">Step 2 of 3</Type></ProgressBar>` |
| Loading / task progress bar | `ProgressBar` | `<ProgressBar percent={50}>Loading...</ProgressBar>` |
| Toast notification | `Notification` | `<Notification title="Title" message="Message" />` |

**Alert — `media` prop is REQUIRED, use `head` NOT `title`:**
```typescript
<Alert
  variant="info"                              // 'info' | 'success' | 'warning' | 'error'
  media={<Icon icon="info" size="md" />}      // REQUIRED — always set size, defaults to full-width on web
  head={<Type>Alert title</Type>}             // use 'head', NOT 'title'
  onDismiss={() => setVisible(false)}
>
  <Type>Alert body text</Type>
</Alert>
```

**Icon inside `media` must have an explicit `size` prop.** Without it the icon stretches to fill the container on web.

**SlimBanner — NO `variant` prop.**

**Badge variants:** `'info' | 'error' | 'success' | 'warning' | 'neutral' | 'emphasis' | 'count'`

### 3.8 Content Display

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Collapsible / FAQ | `Accordion` + `AccordionItem` | See Accordion pattern below |
| Card / tile | `Tile` | `<Tile onPress={handler}><Type>Content</Type></Tile>` |
| Guide tile | `GuideTile` (.native.tsx) / `Tile` + `Icon` + `Type` (.tsx) | Native-only — requires platform split if web support needed |
| Insight card | `InsightCard` | `<InsightCard title="Insight">Data</InsightCard>` |
| Hero header | `SuperHeroHeader` (.native.tsx) / `Section` + `Type` (.tsx) | Native-only — requires platform split if web support needed |
| Carousel | `Carousel` | `<Carousel items={items} />` |
| List | `List` | `<List items={items} />` |
| Table (web / shared) | `Table` from `@barclays/chameleon-blueprint` | `<Table>...</Table>` — web HTML table wrapper |
| Table (native — key/value card style) | `Table`, `TableRow`, `TableCell` from `@barclays/blueprint-react-native` | See native Table pattern below — requires `.native.tsx` split |

**Accordion — CRITICAL: `AccordionItem` title MUST be wrapped in `Type`:**
```typescript
// CORRECT — shared .tsx (no onPress, controlled via useState)
<Accordion>
  <AccordionItem
    title={<Type weight="medium" color="title">Section Title</Type>}
    expanded={expanded}
    onChange={(val) => setExpanded(!!val)}>
    <Type>Content here</Type>
  </AccordionItem>
</Accordion>

// CORRECT — .native.tsx split (import AccordionItem from blueprint-react-native directly)
import { AccordionItem } from '@barclays/blueprint-react-native';
<Accordion>
  <AccordionItem
    title={<Type weight="medium" color="title">Section Title</Type>}
    expanded={expanded}
    onPress={() => setExpanded(prev => !prev)}>
    <Type>Content here</Type>
  </AccordionItem>
</Accordion>

// WRONG — bare string title causes React Native runtime error
<Accordion title="Section Title">
  <Type>Content here</Type>
</Accordion>
```

**AccordionItem Props:**
- `title`: ReactNode — **REQUIRED, MUST wrap in `<Type>`** — do NOT add `size` to the title Type; section heading size is inherited from the Accordion component itself
- `children`: ReactNode
- `expanded`: boolean (default: false — use `true` when Figma shows `behaviour="Open"`)
- `onChange`: `(val?: boolean) => void` — shared `.tsx` only
- `onPress`: `(val?: boolean) => void` — `.native.tsx` only; import `AccordionItem` directly from `@barclays/blueprint-react-native` to access this prop
- `media`: ReactNode

**Interactive `Tile` requires a platform split** — avoid it for selectable list items. The web `Tile` is presentational only (no click handler); interactive variants are `TileButton` (web-only) and `Tile` with `onPress` (native-only). This forces a `.native.tsx` split.

**For selectable lists, use `FormRadio bordered` instead.** It is cross-platform, semantically correct for "pick one from a list", and requires no split:

```typescript
<FormRadio
  bordered
  label={address.fullAddress}
  checked={selectedId === address.id}
  onChange={() => onSelectAddress(address)}
/>
```

Pair it with a pinned "Confirm" `Button` disabled until a selection is made. Selection and confirmation are separate steps — do not navigate immediately on `onChange`.

**Non-interactive `Tile` (no handler)** is safe in shared `.tsx` — just omit the press/click prop.

**Native Table pattern — key/value card-style rows (`.native.tsx` split required):**

Use `Table`/`TableRow`/`TableCell` from `@barclays/blueprint-react-native` directly (NOT via `chameleon-blueprint` — the TypeScript types are incompatible). This produces a white card with rounded corners and subtle row separators — the standard Figma table pattern.

```typescript
// In MyScreen.native.tsx
import { Table, TableRow, TableCell } from '@barclays/blueprint-react-native';

<Table border={false}>
  <TableRow border>
    <TableCell border={false} position="top-left">
      <Type color="disabled">Balance</Type>
    </TableCell>
    <TableCell border={false} position="top-right">
      <Type weight="medium" color="title" alignment="right">First £5,000</Type>
    </TableCell>
  </TableRow>
  <TableRow border>
    <TableCell border={false}>
      <Type color="disabled">AER</Type>
    </TableCell>
    <TableCell border={false}>
      <Type weight="medium" color="title" alignment="right">5.00%</Type>
    </TableCell>
  </TableRow>
  <TableRow>
    <TableCell border={false} position="bottom-left">
      <Type color="disabled">Gross p.a.</Type>
    </TableCell>
    <TableCell border={false} position="bottom-right">
      <Type weight="medium" color="title" alignment="right">1.16%</Type>
    </TableCell>
  </TableRow>
</Table>
```

- `border={false}` on `Table` — removes the outer border
- `border` on `TableRow` — adds a subtle bottom separator between rows (omit on the last row)
- `border={false}` on `TableCell` — removes the cell border (vertical divider between columns)
- `position` on `TableCell` — controls border-radius for top-left/top-right/bottom-left/bottom-right corners
- Do NOT use `Section`/`SectionItem`/`Separator` for tabular data — it produces tight rows with hard divider lines, not the card style.

### 3.9 Media & Icons

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Icon | `Icon` | `<Icon icon="back" size="sm" />` |
| Image / photo | `Multimedia` | `<Multimedia src={require('./image.png')} ratio="16x9" />` |
| Placeholder | `Ghost` | `<Ghost width={100} height={100} />` |

**Icon Props:**
- `icon`: IconName — **use `'dismiss'` for X (NOT `'close'`)**
- `size`: `'xxs' | 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl'`
- `color`: `'black' | 'white' | 'error' | 'success' | 'info' | 'warning' | 'disabled'`

**Multimedia — NOT `Image` for React Native:**
- `src`: ImageSourcePropType | string — REQUIRED
- `ratio`: `'3x4' | '1x1' | '4x3' | '16x9' | '3x1' | '3x2'` — NOT `aspectRatio`
- `fit`: `'contain' | 'cover'`

### 3.10 Overlays

**Modal — ref-based, NOT controlled via `visible` prop:**
```typescript
import { Modal, ModalRef } from '@barclays/chameleon-blueprint';

const modalRef = useRef<ModalRef>(null);
// Open: modalRef.current?.open()
// Close: modalRef.current?.close()

<Modal
  ref={modalRef}
  title="Modal Title"       // REQUIRED
  onDismiss={() => {}}      // NOT onClose!
  position="center"         // 'center' | 'bottom'
  dismissible               // shows close button
  footer={<Button variant="primary">Confirm</Button>}
>
  <Type>Modal content</Type>
</Modal>
```

### 3.11 Utilities

| Figma Element | Blueprint Component | Correct Usage |
|---|---|---|
| Divider / separator | `Separator` | `<Separator spacing="md" />` |
| Quick link | `Quicklink` | `<Quicklink media={<Icon icon="arrow-right" />} onPress={handler}>Text</Quicklink>` |

**Quicklink — `media` is REQUIRED, use `onPress` NOT `onClick`.**

---

## Section 4: Component Layout Heuristics

| Figma Visual Pattern | Blueprint Decision |
|---|---|
| Button-like element, visually prominent (filled) | `Button variant="primary"` |
| Button-like element, outlined / ghost | `Button variant="secondary"` or `"subtle"` |
| Text with size ≥ 18pt and bold weight | `Type size="lg"` or `"xl"` with `weight="bold"` |
| Text above an input box | Separate `Type` label + `FormInput` in `SectionItem` |
| Multiple radio card options | `FormRadio bordered` — one per option in `SectionItem` |
| Collapsible content sections | `Accordion` + `AccordionItem` with Type-wrapped title |
| Card / interactive panel | `Tile` for interactive, `SectionItem` for passive |
| X / close icon | `Icon icon="dismiss"` — NEVER `"close"` |
| Cross-platform image | `Multimedia` — NEVER bare `Image` |
| Horizontal flex row | platform split — web `<div style={{ display: 'flex', flexDirection: 'row', gap: '8px' }}>`, native `<View style={{ flexDirection: 'row', gap: 8 }}>` — `Arrange` has no `direction` prop |
| Two or more columns | `Grid columns={n}` |
| Vertical spacing between elements | `SectionItem spacingBottom="md"` (or `lg`, `sm`) |
| Gray background section | `Section variant="secondary"` |
| White background section | `Section variant="primary"` |

---

## Section 5: Screen Layout Patterns

| Screen Type (keyword) | Required Sections | Key Components |
|---|---|---|
| dashboard | Navbar, MetricCardsRow, DataTable or List, QuickActionsBar | `Navbar`, `Grid`, `Tile`, `Button`, `List` |
| form / settings | Navbar, FormFieldsSection, FormActions | `Navbar`, `SectionItem` + `Type` + `FormInput`, `Button variant="primary" fullWidth` |
| list / table | Navbar, SearchBar, PaginatedList, EmptyState | `Navbar`, `FormInputButton`, `List`, `Type` |
| detail / profile | Navbar, HeroSection, MetadataGrid, ActionToolbar | `Navbar`, `SuperHeroHeader` or `Section`, `SectionItem`, `Button` |
| login / sign in | Navbar, CredentialFields, SubmitButton, ErrorAlert | `Navbar variant="homepage"`, `FormInput`, `Button variant="primary" fullWidth`, `Alert` |
| onboarding | Navbar, StepContent, PrimaryButton, SkipLink | `Navbar`, `Type`, `SectionItem`, `Button`, `Link` |
| generic / unknown | Navbar, ContentArea, FooterActionBar | `Navbar variant="standard"`, `Section`, `SectionItem`, `Button` |

---

## Section 6: ESM Import Rules

All generated files MUST use ESM import syntax. **`require()` is NEVER permitted.**

| Import Type | Correct Pattern | Forbidden Anti-Pattern |
|---|---|---|
| Default import | `import React from 'react'` | `const React = require('react')` |
| Named import | `import { useState } from 'react'` | `const { useState } = require('react')` |
| Blueprint components | `import { Section, Type } from '@barclays/chameleon-blueprint'` | `const { Section } = require(...)` |
| VanillaLayout | `import { VanillaLayout } from '../../components/layouts/vanilla'` | `const { VanillaLayout } = require('../../components/layouts/vanilla')` |

---

## Section 7: TypeScript Conventions

```typescript
export interface {ComponentName}Props {
  // data props — concrete types, never `any`
  // callback props — e.g. onNavigate: (route: string) => void
  // optional state — isLoading?: boolean; error?: string | null
}
```

**Event handler types for shared `.tsx` (web-first props — bridge converts to native):**
```typescript
// Text inputs — web ChangeEvent; bridge converts to onChangeText on native
onChange: (e: React.ChangeEvent<HTMLInputElement>) => void   // FormInput
onChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void // FormTextArea

// Actions — web onClick; bridge converts to onPress on native
onClick: () => void                       // Button, Link, Quicklink, Tile

// Boolean controls — same on both platforms
onChange: (val: boolean) => void          // FormRadio, FormCheckbox
```

**In `.native.tsx` splits only:**
```typescript
onChangeText: (text: string) => void      // FormInput, FormTextArea (native prop directly)
onPress: () => void                       // Button, Link, Tile (native prop directly)
onPress: (val?: boolean) => void          // AccordionItem — native-only, no web equivalent; omit in shared .tsx
```

> **AccordionItem `onPress` is native-only.** The web bridge does not convert it. In shared `.tsx`, omit `onPress` entirely — use controlled `expanded` state with a wrapping component pattern instead if toggling is needed. In `.native.tsx`, `onPress` works as expected.

---

## Section 8: Quality Gate Checks

| Phase | Gate Command | Pass Condition |
|-------|-------------|----------------|
| 1 | `npx tsc --noEmit` | Exit code 0 — zero type errors |
| Validation | `grep -rn "style={{"` in screens | Count = 0 |
| Validation | `grep -rEn "#[0-9a-fA-F]{3,6}"` in screens | Count = 0 |
| Validation | `grep -rn "= require("` in screens | Count = 0 |
| Validation | `grep -rn "onClick="` in screens | Count = 0 |
| Validation | `grep -rn "icon=\"close\""` in screens | Count = 0 |

---

## Section 9: Iron Rules — Non-Negotiable Laws

### Rule 1: No Inline Styles (except sanctioned horizontal flex-row layout)
**NEVER** use the `style` prop for colour, font, or spacing values. The one permitted exception is the horizontal flex-row pattern required by Section 3.0d — `flexDirection: 'row'`, `flex: 1`, `alignItems: 'center'`, `gap: N`, `justifyContent: 'center'` in a `.native.tsx` file. These are purely layout properties that have no Blueprint token equivalent. Any style value that is not a pure flex/layout property is still forbidden.

### Rule 2: No Hardcoded Colours or Spacing
**NEVER** hardcode hex/rgb/hsl colour values or raw px/rem spacing.

### Rule 3: Never Omit Prop Types
**NEVER** generate a component without a fully typed, exported Props interface.

### Rule 4: Every Screen Must Handle Safe Areas and Scrolling
**EVERY** screen component MUST be wrapped in a safe-area root. Use `VanillaLayout` from `../../components/layouts/vanilla` if the project has it (check `src/components/layouts/vanilla/` first). Fall back to `SafeAreaView` + `ScrollView` from React Native if not. **Never import `VanillaLayout` from `@barclays/chameleon-blueprint`** — it is not exported from that package.

### Rule 4a: Never render Navbar inside a screen if the project uses a decoupled header
Check `src/App.tsx` for `header={...}` on `ChameleonRouter`. If that prop is present, **NEVER** render `Navbar` inside a screen component. The screen title is set via `options.title` in `routes.tsx`. Rendering a Navbar inside a screen in this setup produces a double header.

### Rule 5: Use onClick in shared .tsx, onPress in .native.tsx
React Native uses `onPress`, not `onClick`.

### Rule 6: FormInput Has No Label Prop
**NEVER** pass `label` to `FormInput`. Always use a separate `<Type>` above it.

### Rule 7: AccordionItem Title Must Be Type-Wrapped
**NEVER** pass a plain string as `title` to `AccordionItem`. Always: `title={<Type>...</Type>}`.

### Rule 8: Icon Close Does Not Exist
**NEVER** use `icon="close"`. Always use `icon="dismiss"`.

### Rule 9: Modal Is Ref-Based
**NEVER** control a Modal via a `visible` prop. Always use `useRef<ModalRef>`.

### Rule 10a: Back button must always be present in the header
Every screen must have a back button. The header component renders one automatically via `useNavigate().goBack()` — but only when `options.headerShown: true` is set in the route definition. Never set `headerShown: false` unless the screen is a confirmed irreversible success state and that decision is documented. If the design omits a back button, flag it — do not silently accept it.

### Rule 10b: Informational / fraud alerts must use `variant="info"` with the info icon
`variant="warning"` (yellow) is for actionable warnings that require the user to do something. Static informational messages — including fraud warnings — must use `variant="info"` (blue) with `media={<Icon icon="info" />}`. Using warning for informational content is a design system violation.

```typescript
// ✅ CORRECT — fraud warning / informational message
<Alert variant="info" media={<Icon icon="info" />}>
  <Type>We will never contact you to ask you to change your address.</Type>
</Alert>

// ❌ WRONG — warning is yellow and implies the user must act
<Alert variant="warning">
  <Type>We will never contact you to ask you to change your address.</Type>
</Alert>
```

### Rule 10c: Primary CTA button must be pinned to the bottom of the screen
The primary action button must always sit at the bottom of the screen, visually anchored regardless of content length. Achieve this by structuring the layout with a flex-filling content area and a fixed footer section:

```typescript
<VanillaLayout>
  {/* scrollable content area */}
  <Section>
    <SectionItem>{/* screen content */}</SectionItem>
  </Section>

  {/* pinned footer — always at bottom */}
  <Section>
    <SectionItem spacingBottom="lg">
      <Button variant="primary" fullWidth onClick={onContinue}>
        Continue
      </Button>
    </SectionItem>
  </Section>
</VanillaLayout>
```

`VanillaLayout` owns the pinning contract on native — it renders all children except the last inside a `ScrollView`, and the last child outside it as a pinned footer. No `style` prop is needed on any `Section`. The pattern is simply: content `Section` first, footer `Section` last, both direct children of `VanillaLayout`.

A button that floats mid-screen below short content and disappears off-screen on long content is a defect. The validation agent checks for a `Section` wrapping the primary `Button` that is a direct child of `VanillaLayout` (not nested inside the content section).

### Rule 10: Check Platform Parity Before Mapping Any Component
**NEVER** use a component in a shared `.tsx` without first confirming it is in the cross-platform safe set (Section 3.0). `FormInputButton`, `GuideTile`, `SuperHeroHeader`, `Snackbar`, `Dropdown`, `FormInputDatepicker`, and `FormSlider` are native-only and will silently break on web. Create a `.native.tsx` split only when genuinely required — not as a default.

### Rule 11: Horizontal Key/Value Tables Always Require a Native Split
**NEVER** use `Section + SectionItem` for tabular data that Figma renders as side-by-side label/value rows in a white card. It produces stacked vertical layout. **ALWAYS** generate both `.tsx` (stacked fallback) and `.native.tsx` (`Table/TableRow/TableCell` from `@barclays/blueprint-react-native`). See Section 3.0d for all automatic split triggers — do not flag and continue, generate both files.

### Rule 12: `FormItem` is a Runtime Bomb in Shared `.tsx`
**NEVER** use `FormItem` in shared `.tsx`. It compiles fine but crashes on web at runtime. Use `Type` + `FormInput` directly inside `SectionItem`.

### Rule 13: `AccordionItem onPress` is Native-Only
**NEVER** use `onPress` on `AccordionItem` in shared `.tsx`. Use `onChange` in shared files. In `.native.tsx`, import `AccordionItem` directly from `@barclays/blueprint-react-native` to access `onPress`.

### Rule 14: Typography — `size="md"` for 18px Section Headings, No `size` for 16px Body
- **18px Medium section heading** (Figma: `Barclays/Mobile & Tablet/Medium/Medium`): `<Type size="md" color="title">`
- **16px Regular body text** (Figma: `Barclays/Desktop/Standard/Regular`): `<Type color="title">` — NO `size` prop
- **`size="xl"` = 24px** — only for hero/page-level headings, not section subheadings
- **Body text color**: always add `color="title"` when Figma specifies `#272727`. Bare `<Type>` without color defaults to `#515151` (muted grey)

### Rule 15: Paragraph Spacing — Use Separate `SectionItem` per Paragraph
When a Figma text block contains multiple paragraphs with visible spacing between them, render each paragraph as its own `SectionItem` with `spacingBottom`. Do not stack multiple `Type` components inside one `SectionItem` — they will render with no gap between them.

---

## Section 10: Common Anti-Patterns

```typescript
// ❌ FormInput with label prop
<FormInput label="Email" value={email} />
// ✅ CORRECT
<SectionItem><Type>Email</Type><FormInput value={email} onChange={(e) => setEmail(e.target.value)} /></SectionItem>

// ❌ FormInput with onChangeText in shared .tsx (native-only prop)
<FormInput onChangeText={setEmail} />
// ✅ CORRECT — web-first prop; bridge converts to onChangeText on native
<FormInput onChange={(e: React.ChangeEvent<HTMLInputElement>) => setEmail(e.target.value)} />

// ❌ AccordionItem with string title
<AccordionItem title="Section">...</AccordionItem>
// ✅ CORRECT
<AccordionItem title={<Type>Section</Type>}>...</AccordionItem>

// ❌ Alert without media
<Alert title="Info" variant="info">Content</Alert>
// ✅ CORRECT
<Alert media={<Icon icon="info" />} variant="info"><Type>Content</Type></Alert>

// ❌ Icon with close
<Icon icon="close" />
// ✅ CORRECT
<Icon icon="dismiss" />

// ❌ Modal with visible prop
<Modal visible={open} onClose={() => setOpen(false)}>...</Modal>
// ✅ CORRECT
const modalRef = useRef<ModalRef>(null);
<Modal ref={modalRef} onDismiss={() => {}} title="Title">...</Modal>

// ❌ onClick on Blueprint component in .native.tsx
<Button onClick={handler}>Click</Button>
// ✅ CORRECT in .native.tsx
<Button onPress={handler}>Click</Button>

// ❌ AccordionItem onPress in shared .tsx
<AccordionItem onPress={() => setExpanded(p => !p)} title={<Type>Title</Type>}>...</AccordionItem>
// ✅ CORRECT in shared .tsx — use onChange
<AccordionItem onChange={(val) => setExpanded(!!val)} title={<Type>Title</Type>}>...</AccordionItem>

// ❌ AccordionItem title with size prop
<AccordionItem title={<Type size="md" weight="medium">Title</Type>}>...</AccordionItem>
// ✅ CORRECT — no size on title Type
<AccordionItem title={<Type weight="medium" color="title">Title</Type>}>...</AccordionItem>

// ❌ Section heading using size="xl" (24px — too large for 18px Figma heading)
<Type size="xl" weight="medium" color="title">Higher rate</Type>
// ✅ CORRECT — size="md" = 18px Medium
<Type size="md" color="title">Higher rate</Type>

// ❌ Body text with no color (defaults to #515151 muted grey)
<Type>Interest rates are variable...</Type>
// ✅ CORRECT when Figma specifies #272727
<Type color="title">Interest rates are variable...</Type>

// ❌ Multiple paragraphs in one SectionItem (no gap between them)
<SectionItem>
  <Type color="title">First paragraph.</Type>
  <Type color="title">Second paragraph.</Type>
</SectionItem>
// ✅ CORRECT — separate SectionItem per paragraph
<SectionItem spacingBottom="sm">
  <Type color="title">First paragraph.</Type>
</SectionItem>
<SectionItem spacingBottom="lg">
  <Type color="title">Second paragraph.</Type>
</SectionItem>

// ❌ No safe-area wrapper
function MyScreen(): React.ReactElement {
  return <Section><Type>Content</Type></Section>;
}
// ✅ CORRECT (VanillaLayout from project's own components, no Navbar — header is decoupled)
import { VanillaLayout } from '../../components/layouts/vanilla';
function MyScreen(): React.ReactElement {
  return <VanillaLayout><Section><Type>Content</Type></Section></VanillaLayout>;
}
```

---

## Section 11: File Structure

```
src/screens/
├── WelcomeScreen/
│   └── WelcomeScreen.tsx
├── DashboardScreen/
│   └── DashboardScreen.tsx
└── index.ts             ← orchestrator generates this barrel
```

`index.ts` barrel format:
```typescript
// auto-generated by buk-ui-engineer-sdf
export { default as WelcomeScreen } from './WelcomeScreen/WelcomeScreen';
export { default as DashboardScreen } from './DashboardScreen/DashboardScreen';
```

---

## Section 12: Lessons Learned

### Platform Parity Gotchas

- **`Type` is the correct import on both platforms** — chameleon-blueprint abstracts `Typography` (web) and `Type` (native) behind a single `Type` export. Never import `Typography` from blueprint-react directly.
- **`FormInputButton` is native-only** — listed as cross-platform in older docs. Use `FormInput` + `Button` in shared `.tsx`; use `FormInputButton` in `.native.tsx` only.
- **`GuideTile` is native-only** — use `Tile` + `Icon` + `Type` in shared `.tsx`.
- **`SuperHeroHeader` is native-only** — use a `Section variant="secondary"` + `Type` hero pattern in shared `.tsx`.
- **`FormInputDatepicker` is native-only** — web needs a separate date input approach in `.tsx`.
- **`Snackbar` is native-only** — use `Notification` for cross-platform toast/feedback.
- **`.native.tsx` splits are by exception** — the majority of screens in a well-structured SDF project are single shared `.tsx` files. The `layouts/vanilla` and `header` components are the canonical examples of where splits are genuinely needed.
- **`LinkButton` does not exist in `@barclays/chameleon-blueprint`** — it resolves to `undefined` at runtime and renders nothing, causing a silent missing back button. Use `Link` instead. The native header uses `Link` from `blueprint-react-native`; the web header should use `Link` from `chameleon-blueprint`.
- **Header back button must always render** — every screen requires a back button. `canGoBack` from `ChameleonHeaderProps` determines which back action to use, not whether to show it: `canGoBack=true` → `router.goBack()` (mid-journey); `canGoBack=false` → `BarclaysBridge.goBack()` (exit to host app). Never suppress the back button based on `canGoBack`.

### Responsive Layout Gotchas

- **`useScreenWidthQuery('md')` does not mean "md and above"** — it returns `true` only when the viewport is exactly in the `md` band. To express "mobile-sized", combine bands: `useScreenWidthQuery('xs') || useScreenWidthQuery('sm')`. Never use a single band as a threshold.
- **`useScreenWidthQuery` works on native** — `@barclays/chameleon-utils` ships `utils.native.js`. No platform split is needed for a `useIsMobile` hook built on it.
- **Any hook referencing `window` must have a `.native.ts` split** — Metro resolves the base `.ts` for native when no `.native.ts` exists. A hook without a native split that touches `window` will crash the native build.
- **`Arrange` is a grid component, not a flex-row utility** — `Arrange` does not have a `direction` prop on either platform. For a horizontal layout (e.g. icon + label side by side), create a platform split: web uses `<div style={{ display: 'flex', flexDirection: 'row' }}>`, native uses `<View style={{ flexDirection: 'row' }}>`.
- **`Arrange` with `flexWrap: wrap` will stack items when no explicit width is set** — `Arrange` applies `flexDirection: row, flexWrap: wrap` internally. Inside a `Panel.Pane` (which wraps children in `flexGrow: 1`), items may wrap to the next line rather than staying inline. If `Arrange.Item size="fit"` chevrons are appearing below content instead of right-aligned, drop `Arrange` and use `<View style={{ flexDirection: 'row', alignItems: 'center' }}>` with `<View style={{ flex: 1 }}>` for the fill column.
- **Code Connect snippet uses `element={View}` on `Panel.Pane`** — the native `Panel.Pane` `element` prop accepts a component constructor (`View`, `Pressable`), not a JSX element (`<View />`). Pass the component reference directly: `element={View}`.
- **`Panel` and its subcomponents (`Panel.Button`, `Panel.Pane`) are in the cross-platform safe set — import from `@barclays/chameleon-blueprint`, never from `@barclays/blueprint-react-native` directly.** The `.native.tsx` split file must still use `import { Panel } from '@barclays/chameleon-blueprint'`. Importing from `blueprint-react-native` directly in a screen file is an RN9 violation that will be caught by the validation agent.

### Visual Validation Gotchas

- **`agent-device open` flags — `--platform` and `--json` are not valid flags.** The correct command is `agent-device open <bundleId> --foreground`. Similarly `agent-device screenshot <path>` takes no `--json` flag.
- **`agent-device reload` does not exist.** To pick up a new bundle after code changes: wipe the app HTTP cache (`rm -f <container>/Library/Caches/<bundleId>/Cache.db*`) then relaunch with `xcrun simctl launch booted <bundleId>`. Do not attempt `agent-device reload`.
- **Figma MCP is NOT available in subagent sessions.** The `figma-local` MCP connection lives in the main session only. This agent cannot call `get_design_context` or `get_screenshot`. The Figma reference screenshot and side-by-side comparison must be performed by the caller (main Claude session) after this agent reports its simulator screenshot path and Figma nodeId. Report these clearly in the output.
- **Do NOT modify `app.json`.** The `name` field in the project's `app.json` is irrelevant to the Shell app's module resolution. The preflight script passes the component name explicitly via the `shellapp://bundle?name=<name>` deep link. Never edit `app.json` as part of screen generation.
- **Stale Metro process serves old bundle** — `lsof -ti :PORT` may return multiple PIDs when Metro was restarted. `kill "$pid"` fails silently on a multi-line PID list. Always use `echo "$pids" | xargs kill` (as in `metro.sh`) to kill all processes. Confirm Metro is fresh by verifying the bundle contains expected new content: `curl -s http://localhost:8081/index.bundle?platform=ios | grep "expected-string"`.
- **App HTTP cache survives Metro restart** — React Native caches the last downloaded bundle in `Library/Caches/<bundleId>/Cache.db`. When Metro is restarted with new code but the app relaunches, it may serve the cached bundle. Always wipe the cache before a validation screenshot: `xcrun simctl get_app_container booted <bundleId> data` to find the container, then `rm -f <container>/Library/Caches/<bundleId>/Cache.db*`.
- **`agent-device open` fails with "Device is already in use"** — a previous `agent-device` session is holding the device. Run `pkill -f "agent-device"` to kill all daemon processes, then retry `open`.
- **React DevTools shows components but `find <Name>` returns nothing** — in dev bundles, component `displayName` is registered via `$RefreshReg$` but DevTools resolves names differently. Use `find "."` to list all components — `Context.Provider key=<ScreenName>` confirms the screen is mounted. Named lookup only works when component display names are explicitly set.

### Layout and UX Gotchas

- **Back button absent** — the header only shows a back button when `options.headerShown: true` is set in the route. If the header shows a title but no back arrow, check the route definition first before touching the screen component.
- **Alert variant="warning" for informational content** — `warning` renders yellow. Fraud warnings and static info messages must use `variant="info"` (blue) with `media={<Icon icon="info" />}`. Only use `warning` when the user must take action to resolve something.
- **Primary button floating mid-screen** — always split the screen layout into a flex-filling scrollable content area and a pinned footer section. A button placed inside the same `Section` as the content will float wherever the content ends, leaving dead space below it on short content and getting buried on long content.

### chameleon-blueprint is Web-First — Write Web Props

- **`@barclays/chameleon-blueprint` exposes the web React prop API on both platforms.** Write `onClick`, `onChange(e: ChangeEvent)`, `href` etc. The runtime bridge converts these to `onPress`, `onChangeText(string)`, `Linking.openURL()` on native. Do not write `onPress` or `onChangeText` in shared `.tsx` — those are native-only and fail on web.
- **The bridge is incomplete** — not all components are patched. Always read the `.d.ts` from `node_modules/@barclays/chameleon-blueprint` before using a component to confirm the actual prop names in the installed version. Training data prop names are frequently wrong.
- **`Progress` is not cross-platform safe — use `ProgressBar` for step indicators.** The native `Progress` component requires `steps: Array<string>` even in simple/percentage mode, and has a completely different API from the web version. The bridge does not patch it. Use `ProgressBar` for both journey step indicators and loading bars: `<ProgressBar percent={33}>Step 1 of 3</ProgressBar>`.
- **`FormInput` uses `onChange` with a `ChangeEvent`, not `onChangeText`.** `autoCapitalize` is not a valid web prop — omit it in shared `.tsx`.
- **`Link` requires `href`.** For action-only triggers with no navigation destination, use `Button variant="subtle"` (button semantics) or `<Type underline onClick={handler}>` (text-level styling). `Type` extends `HTMLAttributes` so `onClick` is valid on it.
- **`Link onClick` in shared `.tsx` has a `MouseEvent` type, not `() => void`.** When using `Link` as a press handler in shared code, always write `onClick={(e) => { e.preventDefault(); callback?.(); }}`. Passing a `() => void` handler directly will cause a TypeScript error because `ComponentProps<"a">["onClick"]` expects `MouseEventHandler<HTMLAnchorElement>`. On native the bridge converts this to `onPress` and `e.preventDefault()` is a no-op — the pattern is safe cross-platform.
- **`Separator` has only `spacing`, not `spacingBottom`.** The `spacingBottom` prop does not exist on `Separator`.
- **`Section` and `SectionItem` have no `style` prop.** The flex/scroll contract is owned by `VanillaLayout`. Never pass `style={{ flex: 1 }}` to a `Section`.

### Blueprint-Specific Gotchas

- **Section `variant="primary"` is valid** — it renders white. `"secondary"` renders gray.
- **`FormTextArea`** has capital A — `FormTextArea`, not `FormTextarea`.
- **Accordion without AccordionItem** compiles but renders nothing — always pair them.
- **`Tile` with `onPress`** adds press feedback automatically — no need for a wrapping `TouchableOpacity`.
- **`Navbar` must always specify `variant`** — omitting it causes a runtime prop warning.
- **`SlimBanner` has no `variant` prop** — it uses `media` for icon and children for text only.
- **`ModalRef` must be imported** alongside `Modal`: `import { Modal, ModalRef } from '@barclays/chameleon-blueprint'`.
- **`size="md"` on `Type` is NOT 16px Regular body text** — in `BarclaysLightTheme` it resolves to 18px Medium. For 16px Regular (`Barclays/Desktop/Standard/Regular`), omit `size` entirely. See Section 3.3 for the full size scale.
- **`AccordionItem onPress` is native-only** — in shared `.tsx` use `onChange: (val?: boolean) => void`. In `.native.tsx`, import `AccordionItem` directly from `@barclays/blueprint-react-native` (not from `chameleon-blueprint`) to use `onPress`. This is the one exception where a component must be imported from the underlying package rather than the bridge.
- **`AccordionItem` title must NOT include a `size` prop on the inner `Type`** — the size is controlled by the Accordion component. Use `<Type weight="medium" color="title">` only.
- **`Section`/`SectionItem`/`Separator` is wrong for card-style tables on native** — it renders tight rows with hard divider lines. Use `Table`/`TableRow`/`TableCell` from `@barclays/blueprint-react-native` in a `.native.tsx` split. See the native Table pattern in Section 3.8.
- **Figma MCP calls are mandatory before code generation** — if Figma MCP is unavailable, stop and surface the error. Never infer screen content from partial information; hallucinated content (wrong text, wrong values) is worse than no output. Always call `get_design_context`, `get_screenshot`, and `get_variable_defs`, and write raw output to `figma-raw-{nodeId}.md` before writing any `.tsx` files.

---

## Section 13: Navigation Wiring

After generating screen files, wire them into the project's navigation layer. This is part of screen-composer output — a generated screen with no route is incomplete.

### 13.0 Boilerplate screens — remove before wiring the journey

The SDF scaffold template ships with two placeholder screens: `StartScreen` and `SecondScreen`. These exist solely to demonstrate routing — they have no business logic and must be removed before real journey screens are wired in.

**Check for boilerplate before updating `routes.tsx` and `App.interface.ts`:**

```bash
grep -q "StartScreen\|SecondScreen" "{PROJECT_PATH}/src/routes.tsx" && echo "BOILERPLATE_PRESENT"
```

If `BOILERPLATE_PRESENT`:
1. Remove `StartScreen` and `SecondScreen` entries from `routes.tsx`
2. Remove their imports from `routes.tsx`
3. Remove `StartScreen` and `SecondScreen` from `RootStackParamList` in `App.interface.ts`
4. Do NOT delete `src/screens/start/` or `src/screens/second/` — that is the developer's decision, not the agent's

The journey entry screen (Step 1) takes the position of the first route in the array — `ChameleonRouter` renders the first registered route on launch.

**Flag in output if boilerplate was removed:**
```json
{ "boilerplateRemoved": ["StartScreen", "SecondScreen"] }
```

If the developer has already removed the boilerplate, skip silently.

### 13.1 Step 1 — Determine the journey entry point

Every journey has exactly one entry screen. The entry screen is the first screen the user sees when the host app launches the journey. It must be deterministic — do not generate multiple candidate entry screens and leave the choice to the caller.

**How to identify the entry screen:**
- It is the screen invoked directly by the host app (via `ChameleonBridge` deep link or intent)
- It has no predecessor screen within the journey
- In a linear flow it is always Step 1

For this screen, the back button exits to the host app via `chameleonBridge.goBack()` — this is a **close / exit** action, not an in-journey back. Flag this screen explicitly in the output as `ENTRY — back exits to host app`.

**Document the entry screen name clearly in the batch result output.** The API wiring phase needs this to know where to initialise state.

### 13.2 Step 2 — Identify close / exit points (`chameleonBridge.goBack()`)

`chameleonBridge.goBack()` is used when pressing back should **exit the journey entirely** and return control to the host app. This is conceptually a close or dismiss, not a navigation-back.

Screens where `chameleonBridge.goBack()` applies:

| Screen type | Reasoning |
|---|---|
| Entry screen (Step 1) | No previous journey screen exists — back exits to host |
| Success / confirmation screen | Journey is complete — back would re-trigger the flow, so exit is safer |
| Any screen reached via a host-app deep link with no prior journey history | Same as entry screen |

All other screens within the journey use the router's `goBack()` via `useNavigate()` from `@barclays/chameleon-router`.

**Direct `chameleonBridge` calls from screen components are prohibited.** They must be wrapped in an RTK Query thunk or dispatched action. See `barclays-buk-ui-engineer-sdf:chameleon` Section 12.

### 13.3 Step 3 — Update `RootStackParamList`

Add every generated screen to `src/App.interface.ts`:

```typescript
// After boilerplate removal — journey screens only
export type RootStackParamList = {
  CurrentAddressScreen: undefined;          // entry — first route rendered on launch
  PostcodeEntryScreen: undefined;
  AddressListScreen: undefined;
  ManualAddressEntryScreen: undefined;
  AddressConfirmationScreen: undefined;
  DateMovedScreen: undefined;
  ReviewConfirmScreen: undefined;
  SuccessScreen: undefined;
};
```

Use `undefined` for screens that receive no route params. Use a typed object for screens that receive params via navigation (e.g. `AddressListScreen: { postcode: string }` if the postcode is passed as a route param rather than held in state).

### 13.4 Step 4 — Register routes in `routes.tsx`

Import each generated screen and add a `ScreenData` entry:

```typescript
import { ScreenData } from '@barclays/chameleon-router';
import { RootStackParamList } from './App.interface';
import { CurrentAddressScreen } from './screens/CurrentAddressScreen';
// ... one import per screen

export const routes: ScreenData<RootStackParamList>[] = [
  // existing routes preserved
  {
    name: 'CurrentAddressScreen',
    component: CurrentAddressScreen,
    options: {
      headerShown: true,
      title: 'Change address',   // drives the decoupled header title
    },
  },
  // ... one entry per screen
];
```

**`options.title`** — this string is what the decoupled `Header` component renders as the Navbar title via `screenOptions.title`. Set it to match the Figma / design copy for that screen.

**`options.headerShown`** — set to `false` only on a success/confirmation screen where the design intentionally suppresses the header. Default to `true`.

### 13.5 Header component — do not regenerate

The `header` component (`src/components/header/`) is part of the project scaffold. It handles:
- Navbar rendering (title from router context)
- Back button using `useNavigate().goBack()` from `chameleon-router`

It already requires a platform split (`header.tsx` / `header.native.tsx`). Do not regenerate or modify it during screen composition unless specifically instructed.

> Full navigation and back button rules: `barclays-buk-ui-engineer-sdf:chameleon` Section 12
