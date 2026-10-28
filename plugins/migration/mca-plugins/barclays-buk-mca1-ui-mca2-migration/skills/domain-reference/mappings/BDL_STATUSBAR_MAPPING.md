# BDL Status Bar to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Status Bar (`<mca-statusbar>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-statusbar>` | `<SlimBanner>` wrapped in a `BarclaysMicroTheme*` variant |

**Pattern**: MicroTheme wraps Section wraps SectionItem wraps SlimBanner. The MicroTheme variant controls the color/severity theming, while SlimBanner provides the banner layout with optional dismiss and media slots.

### Comprehensive Status Bar Example

**MCA1 (Before)**:
```html
<mca-statusbar
  id=""
  class=""
  color="standard"
  display-text="no"
  background-color="no"
  size=""
>
</mca-statusbar>
```

**Blueprint-React (After)**:
```typescript
<BarclaysMicroThemeSuccess>
  <Section>
    <SectionItem spacing="sm">
      <SlimBanner
        media={<Icon icon="success-fill" size="sm"/>}
        onDismiss={function Xs(){}}
      >
        <Type>
          Description goes here lorem ipsum.{' '}
          <Link href="#">Hyperlink</Link>
        </Type>
      </SlimBanner>
    </SectionItem>
  </Section>
</BarclaysMicroThemeSuccess>
```

### Status Bar Attribute Mapping

| MCA1 Attribute | Blueprint-React | MicroTheme Variant | Notes |
|---|---|---|---|
| `color="standard"` | Default theme | (no wrapper) | Use `<SlimBanner>` without MicroTheme |
| `color="success"` | Green background | `BarclaysMicroThemeSuccess` | Success/positive message |
| `color="alert"` | Yellow background | `BarclaysMicroThemeAlert` | Warning/caution message |
| `color="error"` | Red background | `BarclaysMicroThemeDanger` | Error/failure message |
| `color="info"` | Blue background | `BarclaysMicroThemeInfo` | Information/neutral message |
| `id` | `id` | On outer element | Element identifier |
| `class` | `className` | On outer element | React convention |
| `display-text="no"` | Hide text | CSS/conditional rendering | Use `display: none` or don't render `<Type>` |
| `background-color` | N/A | MicroTheme controls | Color determined by MicroTheme variant |

### MicroTheme Wrapper Pattern

Blueprint-React does not have a single status bar component with a `color` attribute. Instead, the color/severity is expressed by wrapping the banner in a **MicroTheme** component. The MicroTheme provides contextual theming (background color, text color, icon color) to all children.

The wrapping order is always:

```typescript
<BarclaysMicroTheme{Variant}>
  <Section>
    <SectionItem spacing="sm">
      <SlimBanner media={...} onDismiss={...}>
        <Type>{message}</Type>
      </SlimBanner>
    </SectionItem>
  </Section>
</BarclaysMicroTheme{Variant}>
```

- `BarclaysMicroTheme{Variant}` — sets the theme context (color, background)
- `Section` + `SectionItem` — provides consistent spacing and layout
- `SlimBanner` — renders the banner with optional `media` (icon) and `onDismiss` (dismiss button)
- `Type` — wraps the text content

---

### Color Mapping

| MCA1 `color` | Blueprint-React MicroTheme Wrapper | Notes |
|---|---|---|
| `"standard"` (default) | `<BarclaysMicroThemeNeutral>` | Default when `color` is omitted |
| `"success"` | `<BarclaysMicroThemeSuccess>` | |
| `"warning"` | `<BarclaysMicroThemeWarning>` | |
| `"error"` | `<BarclaysMicroThemeError>` | |

**Note**: MCA1's `color="standard"` (or omitted) maps to `BarclaysMicroThemeNeutral`. There is also `BarclaysMicroThemeInfo` available if the status bar is informational in nature — use `Neutral` as the default mapping and `Info` only when the context is explicitly informational.

---

### Success Status Bar

**MCA1 (Before)**:
```html
<mca-statusbar id="sb_success" color="success" text="Operation completed successfully.">
</mca-statusbar>
```

**Blueprint-React (After)**:
```typescript
<BarclaysMicroThemeSuccess>
  <Section>
    <SectionItem spacing="sm">
      <SlimBanner media={<Icon icon="tick" size="sm" />}>
        <Type>Operation completed successfully.</Type>
      </SlimBanner>
    </SectionItem>
  </Section>
</BarclaysMicroThemeSuccess>
```

---

### Warning Status Bar

**MCA1 (Before)**:
```html
<mca-statusbar id="sb_warning" color="warning" text="Please review your details before continuing.">
</mca-statusbar>
```

**Blueprint-React (After)**:
```typescript
<BarclaysMicroThemeWarning>
  <Section>
    <SectionItem spacing="sm">
      <SlimBanner media={<Icon icon="warning" size="sm" />}>
        <Type>Please review your details before continuing.</Type>
      </SlimBanner>
    </SectionItem>
  </Section>
</BarclaysMicroThemeWarning>
```

---

### Error Status Bar

**MCA1 (Before)**:
```html
<mca-statusbar id="sb_error" color="error" text="An error occurred. Please try again.">
</mca-statusbar>
```

**Blueprint-React (After)**:
```typescript
<BarclaysMicroThemeError>
  <Section>
    <SectionItem spacing="sm">
      <SlimBanner media={<Icon icon="error" size="sm" />}>
        <Type>An error occurred. Please try again.</Type>
      </SlimBanner>
    </SectionItem>
  </Section>
</BarclaysMicroThemeError>
```

---

### Dismissible Status Bar

MCA1 status bars can be dismissed via JavaScript APIs. In Blueprint-React, the `SlimBanner` component renders a dismiss button only when the `onDismiss` callback is provided.

**MCA1 (Before)**:
```html
<mca-statusbar id="sb_dismissible" color="success" text="Your changes have been saved.">
</mca-statusbar>
<!-- Dismissed via JS: document.getElementById('sb_dismissible').hide() -->
```

**Blueprint-React (After)**:
```typescript
const [visible, setVisible] = useState(true);

{visible && (
  <BarclaysMicroThemeSuccess>
    <Section>
      <SectionItem spacing="sm">
        <SlimBanner
          media={<Icon icon="tick" size="sm" />}
          onDismiss={() => setVisible(false)}
        >
          <Type>Your changes have been saved.</Type>
        </SlimBanner>
      </SectionItem>
    </Section>
  </BarclaysMicroThemeSuccess>
)}
```

**Note**: The dismiss button only appears when `onDismiss` is provided. Without it, the banner has no built-in close mechanism. Use React state (`useState`) to control visibility — toggling the component in/out of the render tree replaces the MCA1 imperative `.hide()` / `.show()` API.

---

### Status Bar with Icon

MCA1 status bars do not have a dedicated icon attribute — the icon is typically implied by the `color` value. In Blueprint-React, you explicitly pass an icon via the `media` prop on `SlimBanner`.

**MCA1 (Before)**:
```html
<mca-statusbar id="sb_info" color="standard" text="Processing your request...">
</mca-statusbar>
```

**Blueprint-React (After)**:
```typescript
<BarclaysMicroThemeNeutral>
  <Section>
    <SectionItem spacing="sm">
      <SlimBanner media={<Icon icon="info" size="sm" />}>
        <Type>Processing your request...</Type>
      </SlimBanner>
    </SectionItem>
  </Section>
</BarclaysMicroThemeNeutral>
```

**Recommended icon mapping by color/severity**:

| MCA1 `color` | Recommended Blueprint Icon |
|---|---|
| `"standard"` | `"info"` |
| `"success"` | `"tick"` |
| `"warning"` | `"warning"` |
| `"error"` | `"error"` |

**Note**: MCA1 icon names may not exist in Blueprint. Check Blueprint storybook for available icons and map to the closest alternative. See [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md).

---

## Complete `<mca-statusbar>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `SlimBanner` or wrapping `Section` | Assign to the most relevant element |
| `class` | `className` | `SlimBanner` or wrapping `Section` | React convention |
| `text` | `children` (as `<Type>` child) | `SlimBanner` | Content rendered inside `<Type>` wrapped by `SlimBanner` |
| `color="standard"` | `<BarclaysMicroThemeNeutral>` wrapper | MicroTheme wrapper | Default when `color` is omitted |
| `color="success"` | `<BarclaysMicroThemeSuccess>` wrapper | MicroTheme wrapper | |
| `color="warning"` | `<BarclaysMicroThemeWarning>` wrapper | MicroTheme wrapper | |
| `color="error"` | `<BarclaysMicroThemeError>` wrapper | MicroTheme wrapper | |
| `display-text="yes"` | Render additional `<Type>` with percentage value | Inside `SlimBanner` children | No direct prop — render the text explicitly alongside the message |
| `display-text="no"` | (omit percentage text) | — | Default: do not render percentage text |
| `background-color="yes"` | Handled by MicroTheme wrapper | MicroTheme wrapper | MicroTheme automatically applies background color |
| `background-color="no"` | Omit MicroTheme wrapper or use `<BarclaysMicroThemeNeutral>` | MicroTheme wrapper | Neutral theme provides minimal styling |
| `size` (0–100) | No direct equivalent | — | MCA1 progress percentage; if progress display is needed, use a separate `<ProgressBar>` component or custom styling |
| Dismiss (JS API) | `onDismiss={() => ...}` | `SlimBanner` | Dismiss button only renders when `onDismiss` is provided; use `useState` for visibility |
