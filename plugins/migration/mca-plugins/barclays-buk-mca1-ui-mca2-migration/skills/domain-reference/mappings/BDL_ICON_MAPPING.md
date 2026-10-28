# BDL Icons to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Icons

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-icon>` | `<Icon>` |
| `<mca-image>` | `<Multimedia>` — see [BDL_IMAGE_MAPPING.md](BDL_IMAGE_MAPPING.md) |

### Basic Icon Example

**MCA1 (Before)**:
```html
<mca-icon
  title=""
  id=""
  class=""
  category="icon"
  role="presentation"
  type="logo"
  size=""
  color=""
  cursor-style="standard"
  hide="no"
>
</mca-icon>
```

**Blueprint-React (After)**:
```typescript
<Icon
  ariaLabel="Turn over a new leaf"
  icon="leaf"
  size="md"
/>
```

### Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `type="success"` | `icon="tick"` | Use `icon` prop, NOT `name` |
| `type="alert"` | `icon="warning"` | |
| `type="leaf"` | `icon="leaf"` | Direct icon name mapping |
| `size="xxl"` | `size="2xl"` | Max Blueprint size; `xxl` does not exist, use `2xl` |
| `size="md"` | `size="md"` | Medium size (default) |
| `id` | `id` | Icon identifier |
| `class` | `className` | React convention |
| `title` | `ariaLabel` or `title` | Accessibility label |
| `color` | N/A | Styling handled by Blueprint |

### Icon Name Mapping (MCA1 type to Blueprint icon)

**Valid Blueprint icon names** (exhaustive list for v1.3.0): `back`, `bell`, `bin`, `calendar`, `card`, `chat`, `chevron-down`, `chevron-left`, `chevron-left-double`, `chevron-right`, `chevron-right-double`, `chevron-up`, `clock`, `cloud-upload`, `cog`, `compass`, `diamond`, `dismiss`, `download`, `edit`, `error`, `error-fill`, `home`, `info`, `info-fill`, `international`, `leaf`, `log-out`, `mail`, `manage-payments`, `minus`, `more`, `more-vertical`, `new`, `padlock`, `payments`, `plane`, `plus`, `profile`, `refresh`, `search`, `settings`, `show`, `success`, `success-fill`, `tick`, `transfer`, `tree`, `warning`, `warning-fill`.

| MCA1 `type` | Blueprint `icon` | Notes |
|---|---|---|
| `success` | `tick` | |
| `alert` | `warning` | |
| `info` | `info-fill` | |
| `error` | `error` | |
| `print` | N/A | `print` does NOT exist in Blueprint; use `download` or omit |
| `tick-circle` | `tick` | `-circle` suffix does not exist in Blueprint |
| `logo` | N/A | Use `<BrandLogo>` component instead |
| `leaf` | `leaf` | Direct mapping available |
| `chevron-right` | `chevron-right` | Navigation icon |
| `success-fill` | `success-fill` | Filled variant |
| `cross` | `dismiss` | Blueprint uses `dismiss` for the X/close icon, NOT `cross` |
| `cross-circle` | `dismiss` | `-circle` suffix does not exist; use `dismiss` |
| `info-circle` | `info` | `-circle` suffix does not exist in Blueprint |
| `times-circle` | `dismiss` | Maps to `dismiss` |
| `times` | `dismiss` | Maps to `dismiss` |
| `check-circle` | `tick` | Maps to `tick`, not `check` |
| `error-circle` | `error` | `-circle` suffix does not exist in Blueprint |
| `warning` | `warning` | Direct mapping |
| `spinner` | N/A | Use `<Loading>` component (NOT an Icon) — see [BDL_SPINNER_MAPPING.md](BDL_SPINNER_MAPPING.md) |
| `inbox` | `mail` | No `inbox` icon; use `mail` as closest alternative |
| `inbox-full` | `mail` | No `inbox-full` icon; use `mail` as closest alternative |
| `camera` | N/A | `camera` does NOT exist in Blueprint; omit or use custom SVG |
| `facebook` | N/A | No equivalent; use text or custom SVG |
| `close` | `dismiss` | Blueprint uses `dismiss` for close/X icon |
| `external` | `chevron-right` | No `external` icon; use `chevron-right` or omit |

---

## Size Mapping

| MCA1 `size` | Blueprint `size` | Notes |
|---|---|---|
| `sm` | `sm` | |
| `md` | `md` | |
| `lg` | `lg` | |
| `xl` | `xl` | |
| `xxl` | `2xl` | `xxl` does not exist in Blueprint; use `2xl` |

Valid Blueprint sizes: `xs`, `sm`, `md`, `lg`, `xl`, `2xl`.

Always specify the `size` prop on `<Icon>` to prevent oversized rendering.

---

## Accessibility

- **Standalone icons** (not inside a button or other labelled element): Always add `ariaLabel` prop to provide an accessible text label.
- **Icons inside buttons**: The button's text content provides the accessible label. Do NOT add a redundant `ariaLabel` on the icon.

```typescript
{/* Standalone icon — ariaLabel required */}
<Icon icon="tick" size="md" ariaLabel="Success" />

{/* Icon inside a button — ariaLabel NOT needed on Icon */}
<Button variant="primary" media={<Icon icon="download" size="sm" />}>
  Print statement
</Button>
```

---

## Before/After Examples

### Basic Icon Migration

**MCA1 (Before)**:
```html
<mca-icon type="success" id="b_icon_success" size="xxl" color="success"></mca-icon>
<mca-icon type="alert" id="b_icon_alert" size="xxl" color="alert"></mca-icon>
```

**Blueprint-React (After)**:
```typescript
<Icon icon="tick" id="b_icon_success" size="xl" />
<Icon icon="warning" id="b_icon_alert" size="xl" />
```

### Icon Inside a Button (using `media` prop)

**MCA1 (Before)**:
```html
<mca-button>
  <mca-icon type="print" size="sm"></mca-icon>
  Print statement
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="primary" media={<Icon icon="download" size="sm" />}>
  Print statement
</Button>
```

### Icon Inside an Alert (using `media` prop)

**MCA1 (Before)**:
```html
<mca-alert type="success">
  <mca-icon type="success" size="md"></mca-icon>
  Your changes have been saved.
</mca-alert>
```

**Blueprint-React (After)**:
```typescript
<Alert variant="success" media={<Icon icon="tick" size="md" />}>
  <Type>Your changes have been saved.</Type>
</Alert>
```

### Standalone Icon with ariaLabel

**MCA1 (Before)**:
```html
<mca-icon type="info" size="lg"></mca-icon>
```

**Blueprint-React (After)**:
```typescript
<Icon icon="info" size="lg" ariaLabel="Information" />
```

---

## Icons That DO NOT EXIST in Blueprint

These MCA1 icon names require special handling during migration:

| MCA1 Icon | Migration Action |
|---|---|
| `spinner` | Use `<Loading>` component instead — see [BDL_SPINNER_MAPPING.md](BDL_SPINNER_MAPPING.md) |
| `tick-circle` | Use `tick` (drop the `-circle` suffix) |
| `cross-circle` | Use `dismiss` (the X/close icon in Blueprint is `dismiss`) |
| `cross` | Use `dismiss` (Blueprint's close icon is `dismiss`, not `cross`) |
| `close` | Use `dismiss` (Blueprint's close icon is `dismiss`) |
| `info-circle` | Use `info` (drop the `-circle` suffix) |
| `times-circle` | Use `dismiss` |
| `times` | Use `dismiss` |
| `check-circle` | Use `tick` |
| `error-circle` | Use `error` (drop the `-circle` suffix) |
| `inbox` | Use `mail` (closest alternative) |
| `inbox-full` | Use `mail` (closest alternative) |
| `print` | Does NOT exist; use `download` or omit |
| `camera` | Does NOT exist; omit or use custom SVG |
| `external` | Does NOT exist; use `chevron-right` for link indicators |
| `document` | Does NOT exist; use `mail` for inbox-like contexts |
| `facebook` | No equivalent; use text or custom SVG |
| `logo` | Use `<BrandLogo>` component |

---

## Cross-References

- `<mca-image>` mapping: [BDL_IMAGE_MAPPING.md](BDL_IMAGE_MAPPING.md)
- Spinner / loading indicator mapping: [BDL_SPINNER_MAPPING.md](BDL_SPINNER_MAPPING.md)
