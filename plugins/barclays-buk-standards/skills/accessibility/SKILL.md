---
name: accessibility
description: BUK accessibility standards based on Barclays Digital Accessibility Standards V3.0 (WCAG 2.2 AA). Covers numeric thresholds, platform requirements, Blueprint component patterns, Barclays-specific additions, and audit checklist. Use when generating or reviewing UI code or conducting accessibility audits.
user-invocable: false
---

# BUK Accessibility Standards

> Source: Barclays Digital Accessibility Standards V3.0, September 2023 (WCAG 2.2 AA).
> Applies to all digital products and services — web, mobile app, and documents.
> Also applies to externally-procured digital services via the Accessibility Supplier Control Obligations (SCO).

---

## Section 1: Baseline Standard

**Required standard: WCAG 2.2 Level AA** (effective October 2023, replacing WCAG 2.1 AA).

All WCAG 2.1 AA criteria remain in force. WCAG 2.2 adds the following new criteria:
- **2.4.11** Focus Not Obscured (Minimum)
- **2.4.12** Focus Not Obscured (Enhanced — AAA, not required but good practice)
- **2.4.13** Focus Appearance
- **2.5.7** Dragging Movements
- **2.5.8** Target Size (Minimum)
- **3.2.6** Consistent Help
- **3.3.7** Redundant Entry
- **3.3.8** Accessible Authentication (Minimum)

**Platform scope tags used in this skill:**
- `[Browser]` — web (desktop and mobile browsers)
- `[App]` — iOS and Android native apps
- `[Docs]` — PDFs and digital documents

A requirement tagged `[Browser][App]` applies to both.

---

## Section 2: Numeric Thresholds — Hard Requirements

These values are non-negotiable. Validate programmatically before shipping.

### Colour Contrast

| Scenario | Required Ratio | Platform |
|---|---|---|
| Normal text (< 18pt / < 14pt bold) | **4.5:1** | `[Browser][App][Docs]` |
| Large text (≥ 18pt or ≥ 14pt bold) | **3:1** | `[Browser][App][Docs]` |
| Graphical objects / icons conveying information | **3:1** | `[Browser][App][Docs]` |
| UI component borders (form fields, buttons) | **3:1** | `[Browser][App]` |
| Focus indicator vs background | **3:1** | `[Browser][App]` |
| Actionable text vs surrounding non-actionable text (when no other cue) | **3:1** | `[Browser]` |

### Touch / Click Target Size `[Browser][App]`

- **Primary:** minimum **44×44px**
- **Fallback (constrained by line height or required functionality):** minimum **44px in one dimension, 24px in the other**
- Blueprint `Button` meets the primary target by default. Custom tappable areas must not be smaller.

### Zoom and Reflow `[Browser]`

- At **200% zoom or font enlargement**: all content and functionality remains available without horizontal scrolling
- At **400% zoom**: all content must reflow — no horizontal scrolling (except images, tables, content that cannot reflow by nature)

### Text Spacing Override `[Browser]`

Content must remain legible when users override:
- Line height: up to **1.5× font size**
- Paragraph spacing: at least **2× font size**
- Letter spacing: at least **0.12× font size**
- Word spacing: at least **0.16× font size**

### Animation and Motion `[Browser][App]`

- Auto-scrolling or blinking content must stop after **5 seconds**, or provide a pause/hide/stop control
- Flashing content: no more than **3 flashes per second**

### Audio `[Browser][App]`

- Auto-playing audio must stop after **3 seconds**, or provide a clearly-labelled Pause button at the very start of the page/screen

---

## Section 3: Barclays-Specific Requirements (Beyond WCAG AA)

These requirements go beyond the WCAG 2.2 AA baseline and are mandatory at Barclays.

### Typography `[Browser][App][Docs]`

- **Sans-serif font** required for all text content (references British Dyslexia Association Style Guide and UKAAF Clear Print Standard)
- **Left alignment** preferred; centred alignment only for ≤2 sentences or ≤4 lines
- Capitalised and italic text: **used sparingly**
- No images of text (except logos, graphs, and diagrams)

### Language and Reading Level `[Browser][App][Docs]`

- Language must be **as simple and clear as possible**
- Jargon must be avoided or explained
- Acronyms must be expanded on first use
- **Literacy baseline:** 1 in 7 UK adults have literacy skills at or below the level expected of a 9–11 year old. 17.7 million adults (34%) have poor/low numeracy with financial concepts. Mass-market products must communicate at this accessible level (Government Digital Service benchmark: write for a 9-year-old reading age).

### Colour Customisation `[Browser][App]`

- Content must respond to OS/browser colour overrides (e.g. high contrast, inverted colours)
- Do not override system colour settings with hardcoded values

### Focus Indicators `[Browser][App]`

- Must visually enclose the component (bounding box or background change)
- Must not be hidden by other content
- Default browser/platform focus indicators must not be disabled — only enhanced
- Custom focus indicators require **3:1 contrast** against background

### Links in Body Text `[Browser]`

- Links within body text must **always be underlined**
- No other text may be underlined (to avoid confusion with links)
- Links opening a new tab, window, or non-HTML format must declare this in text, via icon with text alternative, or tooltip

### Accessibility Link `[Browser]`

- All customer-facing platforms must include a consistently available **"Accessibility" link**

### Login Link Visibility `[Browser]`

- Login links/buttons must be among the **first interactive items** on the page — highly visible at the top, or reachable via skip mechanism

### Authentication `[Browser][App]`

- Any authentication step based on a cognitive test (e.g. image recognition, puzzle) must offer at least one alternative method, or a mechanism to assist completion
- **Paste must be supported** in OTP, PIN, and passcode fields — do not block clipboard paste
- Biometric authentication is an acceptable alternative to cognitive authentication steps

---

## Section 4: What Blueprint Components Handle Automatically

Do NOT add manual ARIA or accessibility props for these — Blueprint already wires them, and duplicating causes errors.

### SDF — `@barclays/chameleon-blueprint` (React Native) `[App]`

| Component | What it provides automatically |
|---|---|
| `Navbar` | Navigation landmark, back button affordance |
| `Button` | Touch target sizing, press state feedback |
| `FormInput` | Input role, focus management |
| `FormRadio` / `FormCheckbox` | Role, checked state, label association |
| `Alert` | Live region announcement |
| `Loading` | Activity indicator role |
| `Modal` | Focus trap, dismiss on gesture |
| `Accordion` / `AccordionItem` | Expanded/collapsed state |

**Critical constraint:** Do NOT add `accessibilityLabel` or `testID` props to Blueprint SDF components — these cause TypeScript errors.

### MCA / Web — `@barclays/blueprint-react` `[Browser]`

| Component | What it provides automatically |
|---|---|
| `FormItem` (render prop) | `aria-describedby`, `aria-invalid`, `id` — wired automatically when `{...props}` is spread |
| `Button` | Role, focus, keyboard activation |
| `Modal` / `Dialog` | Focus trap, `aria-label`, `onKeydownEscape` |
| `Alert announceOnMount` | Live region announcement for dynamically injected content |
| `Icon ariaHidden` | Hides decorative icons from screen readers |
| `ScreenReader` | Visually hidden content accessible to screen readers only |

---

## Section 5: What Developers Must Provide

### 5.1 Form Labels — Always Explicit `[Browser][App][Docs]`

Placeholder text does **not** replace a visible label. Labels must be visible, positioned close above or beside the field, and programmatically associated.

**SDF:** Always pair a visible `<Type>` label above the input:
```tsx
<SectionItem spacingBottom="md">
  <Type size="md" weight="medium">Email Address</Type>
  <FormInput value={email} onChangeText={setEmail} placeholder="user@example.com" />
  {emailError && <Type size="sm" color="error">{emailError}</Type>}
</SectionItem>
```

**MCA/Web:** Always use `FormItem` with render prop — spread `{...props}` onto the input:
```tsx
<FormItem
  label={<Type>Email Address</Type>}
  error={emailError && <Type color="error">{emailError}</Type>}
  render={(props) => <FormInput {...props} value={email} onChange={handleChange} />}
/>
```

**Mandatory/optional fields:** Label must include asterisk or "Required" for mandatory fields. Where most fields are mandatory, optional fields must say "(Optional)".

### 5.2 Error Handling `[Browser][App][Docs]`

- Error messages must be visible text — **never colour alone**
- After form submit: focus must move to the error summary or first invalid field
- Error state must be programmatically associated with the field (Blueprint `FormItem` handles this)
- Use Blueprint error state props — do not create custom error announcement patterns

### 5.3 Button and Interactive Element Labels `[Browser][App]`

- All buttons must have descriptive text describing the action — not "OK", "Click here", "Submit" in isolation
- Icon-only buttons require an accessible label (`aria-label` on web, or a visible `<Type>` alongside the icon)
- Interactive cards: use `TileButton` / `TileLink` on web — never `Tile` with an `onClick` handler added

### 5.4 Colour Is Never the Only State Indicator `[Browser][App][Docs]`

Every piece of information conveyed by colour must also have a non-colour cue:
- Text label
- Icon
- Pattern, shape, or border change
- Underline (for links)

### 5.5 Semantic Structure `[Browser][App][Docs]`

- Use native/semantic elements: `<button>`, `<a>`, `<input>`, `<select>`, `<table>` on web; UIKit/SwiftUI native controls on iOS; native Android components
- Heading levels must be sequential — one `<h1>` per page, then `h2`, `h3` etc. — use `Type element="h1/h2/h3"` on web
- Section headers: use `semantics { heading() }` (Android Compose) or appropriate role on web
- Use `semantics { }` modifiers on Android for custom components that need accessibility descriptions

### 5.6 Dynamic Content and Focus Management `[Browser][App]`

- Modals: trap focus inside when open; return focus to trigger element on close
- New page/screen rendered: move focus to top or first meaningful element
- Dynamically injected content (errors, alerts): announce via live region or move focus
- `aria-live="polite"` for status messages that appear without user action `[Browser]`
- `aria-live="assertive"` only for urgent interruptions `[Browser]`

### 5.7 Custom Interactive Components `[Browser][App]`

When a native/Blueprint component cannot be used, the custom component must explicitly set:
- Role (`aria-role` / semantic element on web; `Role` on Android; native on iOS)
- Name (accessible label)
- State (`aria-expanded`, `aria-selected`, `aria-checked`, `aria-invalid`, etc.) — must update when state changes

### 5.8 All-Text Rule `[Browser][App][Docs]`

All user-facing text must be real text — not images of text (except logos, graphs, and diagrams).
- Android: all strings must be `LocalizedStringKey` / string resources — never hardcoded
- iOS: all text must be localisation-ready

---

## Section 6: Platform-Specific Requirements

### Web `[Browser]`

- All interactive elements reachable by `Tab`; Tab order matches visual reading order
- `Escape` must close modals/dialogs
- Focus visible on all interactive elements (do not disable default browser focus ring)
- Dragging operations must have a single-pointer alternative (e.g. drag-to-reorder must also support a button-based reorder)
- Character key shortcuts that use a single character must be remappable or deactivatable

### iOS `[App]`

- Use native UIKit/SwiftUI controls — never build custom interactive components without full UIAccessibility support
- VoiceOver: test reading order matches visual order; modal focus trap; swipe navigation
- Dynamic Type: do not use fixed font sizes or fixed-height containers that clip scaled text
- Biometric: use `BPBiometricPrompt` (Blueprint) — never custom implementation
- Paste in OTP/PIN fields must not be blocked

### Android `[App]`

- Use Blueprint Compose components — they provide `semantics` and correct content descriptions
- TalkBack: test navigation order; announce dynamic content changes
- `BlueprintText` with `LocalTypography` tokens — never hardcoded sizes
- `semantics { contentDescription = "..." }` on custom components where label is not self-evident
- `semantics { heading() }` on section headers
- `BlueprintInputField` accessibility config must supply a label — never placeholder-only (placeholders disappear when the user starts typing)
- Error states must combine error color tokens with descriptive error text — never colour alone (colour-only errors fail WCAG 1.4.1 Use of Colour).

### Documents `[Docs]`

- Alt text on all meaningful images
- Proper heading structure
- List markup for all lists
- Table markup with header row (`<th>`)
- Form fields with labels
- Logical reading order (tagged PDF)
- Colour contrast meets thresholds

---

## Section 7: Vulnerability and Disability-Specific Considerations

Design must account for the following disability types — these are the groups most at risk from poor accessibility and overlap directly with FCA vulnerable customer obligations:

| Group | Key requirements |
|---|---|
| Visual impairment / blindness | Screen reader compatibility throughout; alt text; semantic/native controls; logical reading order; dynamic announcements |
| Low vision | Colour contrast ratios; 200% zoom; 400% reflow; text spacing overrides; sans-serif fonts |
| Colour blindness | No colour as sole conveyor of information; icon/text/pattern alternatives |
| Dyslexia | Sans-serif font; left alignment; colour customisation; spacing customisation |
| Cognitive / learning difficulties | Simple language; jargon avoidance; progress indicators; review screen before submission; auto-populate; accessible authentication |
| Motor / limited dexterity | 44×44px targets; full keyboard access; no complex gestures without single-pointer alternative; cancel actions; no motion-only activation |
| Seizure conditions | Max 3 flashes/second |
| Deaf / hard of hearing | Captions on video; text transcripts for audio-only content |
| Speech / communication | Voice control: accessible name must start with the same text as visible label (label-in-name) |

---

## Section 8: Governance and Evidence Requirements

- Completed accessibility assessments must be **stored as evidence** for each project/enhancement
- Non-compliance must be documented with: approach taken, reasoning, any staff training, any user research to mitigate impact
- Non-compliance must go through a **Non-Financial Risk assessment** accepted at appropriate authority levels — it cannot simply be noted and ignored
- Suppliers are bound by the same standards via the **Accessibility Supplier Control Obligations (SCO)**
- Contact: **DigitalAccessibility@barclayscorp.com** for guidance

---

## Section 9: Audit Checklist

### Colour and Typography
- [ ] Text contrast ≥ 4.5:1 (normal text) or 3:1 (large text)
- [ ] Non-text / icon contrast ≥ 3:1
- [ ] Focus indicator contrast ≥ 3:1, encloses component, not hidden
- [ ] Sans-serif font in use
- [ ] No images of text (except logos/diagrams)
- [ ] Text left-aligned (centred only for ≤2 sentences / ≤4 lines)

### Forms
- [ ] Every input has a visible text label — not placeholder-only
- [ ] Labels are above or beside their field — not below
- [ ] Error messages are visible text, not colour alone
- [ ] Error focus moves to summary or first invalid field on submit
- [ ] Mandatory fields marked with asterisk or "Required"
- [ ] OTP/PIN/passcode fields allow paste (not blocked)
- [ ] Authentication offers alternative to cognitive-only challenges

### Interactive Elements
- [ ] All interactive elements reachable by keyboard / assistive navigation
- [ ] Touch targets ≥ 44×44px (or 44×24px minimum fallback)
- [ ] Buttons have descriptive labels — not "OK" or "Submit" alone
- [ ] Icon-only actions have accessible labels
- [ ] No colour as sole state indicator

### Structure and Navigation
- [ ] One `<h1>` per page; heading hierarchy is sequential
- [ ] Screen/page has a meaningful title or Navbar title
- [ ] Reading order matches visual order
- [ ] Skip link present on web `[Browser]`
- [ ] Accessibility link consistently placed on customer-facing platforms `[Browser]`
- [ ] Login button/link is first or among first interactive items `[Browser]`

### Dynamic Content
- [ ] Modal traps focus; returns focus to trigger on close
- [ ] Dynamic errors/alerts announced via live region or focus move
- [ ] Auto-scrolling/blinking content stops ≤5s or is pauseable
- [ ] No more than 3 flashes/second

### Platform-Specific
- [ ] SDF: no `accessibilityLabel` or `testID` on Blueprint components
- [ ] MCA/Web: `FormItem` render prop spreads `{...props}` onto input
- [ ] MCA/Web: links in body text are underlined; no other text underlined
- [ ] Android: custom components have `semantics { contentDescription }` where needed
- [ ] Documents: tagged PDF with heading structure, alt text, reading order

---

## React Native & Web Platform Specifics

### Blueprint Accessibility Mapper — ARIA Props to React Native Props (HOC)

When using the Blueprint accessibility HOC, ARIA props are automatically mapped to their React Native equivalents. Do NOT manually add the React Native props alongside the ARIA props — the mapper will produce duplicates.

| Web ARIA prop | React Native a11y prop |
|---|---|
| `aria-label` | `accessibilityLabel` |
| `role` | `accessibilityRole` |
| `aria-describedby` | `accessibilityHint` |
| `aria-checked` | `accessibilityState={{ checked }}` |
| `aria-selected` | `accessibilityState={{ selected }}` |
| `aria-expanded` | `accessibilityState={{ expanded }}` |
| `aria-live` | `accessibilityLiveRegion` |
| `data-testid` | `testID` |
| `aria-hidden={true}` | renders visually hidden placeholder |

**CRITICAL RULE:** Do NOT manually add `accessibilityLabel`, `accessibilityRole` etc. alongside ARIA props — the mapper will produce duplicates.

### Screen Reader Text Formatting

- Account numbers must be formatted digit-by-digit for screen reader announcement (e.g. `"1 2 3 4"` not `"1234"`)
- Monetary amounts must be announced with currency (e.g. `"£12.50"` not `"12.50"`)
- All screen reader text must be human-readable prose — not raw data strings

### React Native Specific Checklist

- [ ] `accessible={true}` set on interactive containers
- [ ] `accessibilityLabel` provides a concise, meaningful label
- [ ] `accessibilityHint` used sparingly for non-obvious interactions
- [ ] `accessibilityRole` matches purpose (`button`, `link`, `header`, `image`, `checkbox`)
- [ ] `accessibilityState` reflects dynamic states (disabled, selected, checked, busy, expanded)
- [ ] `accessibilityValue` set for range controls (min, max, now, text)
- [ ] `importantForAccessibility` (Android) and `accessibilityElementsHidden` (iOS) used to hide decorative elements
- [ ] Touch targets adequately sized via `hitSlop` or padding
- [ ] `onAccessibilityEscape` implemented for dismissible views (iOS)

### Web / React Specific Checklist

- [ ] Semantic HTML elements used (`<button>`, `<nav>`, `<main>`, `<h1>`–`<h6>`, `<form>`, `<label>`)
- [ ] ARIA attributes are correct and not redundant with native semantics (no duplicate roles)
- [ ] `tabIndex` usage is appropriate (0 for focusable, -1 for programmatic focus, never positive)
- [ ] Focus visible styles present and meet contrast requirements
- [ ] `aria-live` regions announce dynamic content appropriately
- [ ] Skip navigation links present
- [ ] Form inputs have associated `<label>` or `aria-labelledby`

### Supported Assistive Technologies

The following assistive technologies must be considered when implementing and testing accessibility:

- **VoiceOver** (iOS)
- **TalkBack** (Android)
- **NVDA** (Windows screen reader)
- **JAWS** (Windows screen reader)
- **Switch control** (iOS / Android motor accessibility)
