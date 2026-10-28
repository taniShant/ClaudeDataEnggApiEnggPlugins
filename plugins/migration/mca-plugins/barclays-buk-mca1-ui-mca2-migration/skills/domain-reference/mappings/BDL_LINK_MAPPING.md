# BDL Link to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Link (`<mca-link>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-link>` | `<Link>` |
| `<mca-link>` (button-style) | `<LinkButton>` |

`<mca-link>` maps to Blueprint-React's `<Link>` component. This is distinct from `<mca-button type="link">` which maps to `<ButtonLink>` (see [BDL_BUTTON_MAPPING.md](BDL_BUTTON_MAPPING.md)).

### Basic Link Example

**MCA1 (Before)**:
```html
<mca-link
  type="primary"
  icon=""
  href=""
  disabled="no"
  external="no"
  button="no"
  id=""
  class=""
  tabindex=""
  title=""
  aria-label=""
  role=""
>
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<LinkButton variant="default">
  Hello World
</LinkButton>
```

Or with `<Link>` for inline usage:

```typescript
<Link href="https://www.barclays.com">Link text</Link>
```

### `type` Mapping

| MCA1 `type` | Blueprint-React | Notes |
|---|---|---|
| `type="paragraph"` | `<Link>` (inline within `<Type>`) | Inline link within body text |
| `type="primary"` | `<LinkButton variant="primary">` or `<Link>` | Primary styled link |
| `type="secondary"` | `<LinkButton variant="secondary">` or `<Link>` | Secondary styled link |
| `type="tertiary"` | `<LinkButton variant="default">` or `<Link>` | Tertiary styled link |

### Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `href` | `href` | `Link` / `LinkButton` | URL destination |
| `type="primary"` | `variant="primary"` | `LinkButton` | Link styling |
| `external="yes"` | `target="_blank"` rel="noopener noreferrer" | `Link` / `LinkButton` | External link handling |
| `disabled="yes"` | `disabled` | `LinkButton` | Disabled state |
| `id` | `id` | `Link` / `LinkButton` | Element identifier |
| `class` | `className` | `Link` / `LinkButton` | React convention |
| `icon` | `media={<Icon icon="..." />}` | `LinkButton` | Icon before/after text |
| `aria-label` | `aria-label` | `Link` / `LinkButton` | Accessibility label |

---

### Paragraph Link (Inline in Text)

MCA1's `type="paragraph"` renders a link inline within surrounding text.

**MCA1 (Before)**:
```html
<mca-text text-type="standard">
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
    tempor incididunt ut labore et dolore magna aliqua.
    <mca-link type="paragraph" id="b_link_paragraph" href="http://www.google.com">
        Link Paragraph
    </mca-link>
    Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
    deserunt mollit anim id est laborum.
</mca-text>
```

**Blueprint-React (After)**:
```typescript
<Type element="p">
  Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod
  tempor incididunt ut labore et dolore magna aliqua.{' '}
  <Link href="http://www.google.com" id="b_link_paragraph">
    Link Paragraph
  </Link>{' '}
  Excepteur sint occaecat cupidatat non proident, sunt in culpa qui officia
  deserunt mollit anim id est laborum.
</Type>
```

---

### Primary Link

**MCA1 (Before)**:
```html
<mca-link type="primary" id="b_link_primary" href="http://www.google.com">
    Link Primary
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="http://www.google.com" id="b_link_primary">
  Link Primary
</Link>
```

---

### Secondary Link

**MCA1 (Before)**:
```html
<mca-link type="secondary" id="b_link_secondary">
    Link Secondary
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="#" id="b_link_secondary">
  Link Secondary
</Link>
```

---

### Tertiary Link

**MCA1 (Before)**:
```html
<mca-link type="tertiary" id="b_link_tertiary">
    Link Tertiary
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="#" id="b_link_tertiary">
  Link Tertiary
</Link>
```

---

### Link with Icon — Primary

**MCA1 (Before)**:
```html
<mca-link icon="camera" type="primary" id="b_link_icon_primary">
    Link Icon Primary
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="#" id="b_link_icon_primary" media={<Icon icon="cloud-upload" size="sm" />} mediaPosition="left">
  Link Icon Primary
</Link>
```

**Note**: Use the `media` prop on `<Link>` to attach icons — do NOT render `<Icon>` as inline children. MCA1 icon names may not exist in Blueprint; map to closest available. See [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md).

---

### Link with Icon — Secondary

**MCA1 (Before)**:
```html
<mca-link icon="camera" type="secondary" id="b_link_icon_secondary">
    Link Icon secondary
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="#" id="b_link_icon_secondary" variant="secondary" media={<Icon icon="cloud-upload" size="sm" />} mediaPosition="left">
  Link Icon secondary
</Link>
```

---

### Link with Icon — Tertiary

**MCA1 (Before)**:
```html
<mca-link icon="camera" type="tertiary" id="b_link_icon_tertiary">
    Link Icon tertiary
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="#" id="b_link_icon_tertiary" variant="secondary" media={<Icon icon="cloud-upload" size="sm" />} mediaPosition="left">
  Link Icon tertiary
</Link>
```

---

### External Link — Primary

MCA1's `external="yes"` opens the link in a new window. Map to `target="_blank"` with `rel="noopener noreferrer"` for security.

**MCA1 (Before)**:
```html
<mca-link external="yes" type="primary"
    aria-label="Link Primary External open in new Window"
    id="b_link_primary_external">
    Link Primary External
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link
  href="#"
  id="b_link_primary_external"
  target="_blank"
  rel="noopener noreferrer"
  aria-label="Link Primary External open in new Window"
>
  Link Primary External
</Link>
```

---

### External Link — Secondary

**MCA1 (Before)**:
```html
<mca-link external="yes" type="secondary"
    aria-label="Link secondary External open in new Window"
    id="b_link_secondary_external">
    Link secondary External
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link
  href="#"
  id="b_link_secondary_external"
  target="_blank"
  rel="noopener noreferrer"
  aria-label="Link secondary External open in new Window"
>
  Link secondary External
</Link>
```

---

### External Link with Icon

**MCA1 (Before)**:
```html
<mca-link external="yes" type="primary"
    aria-label="Link Primary Icon with External open in new Window"
    icon="facebook" id="b_link_icon_external">
    Link Primary Icon with External
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link
  href="#"
  id="b_link_icon_external"
  target="_blank"
  rel="noopener noreferrer"
  aria-label="Link Primary Icon with External open in new Window"
  media={<Icon icon="chevron-right" size="sm" />}
  mediaPosition="right"
>
  Link Primary Icon with External
</Link>
```

---

### Disabled Link

**MCA1 (Before)**:
```html
<mca-link disabled="yes" type="primary" id="b_link_disabled">
    Link Primary Disabled
</mca-link>
```

**Blueprint-React (After)**:
```typescript
<Link href="#" id="b_link_disabled" disabled>
  Link Primary Disabled
</Link>
```

---

## Complete `<mca-link>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Link` | |
| `class` | `className` | `Link` | React convention |
| Text content | `children` | `Link` | |
| `href` | `href` | `Link` | |
| `type="paragraph"` | N/A | N/A | Use `<Link>` inline within `<Type>` |
| `type="primary"` | N/A | N/A | `<Link>` provides consistent styling |
| `type="secondary"` | N/A | N/A | `<Link>` provides consistent styling |
| `type="tertiary"` | N/A | N/A | `<Link>` provides consistent styling |
| `icon` | `media={<Icon icon="..." size="sm" />}` + `mediaPosition` | `Link` | Use `media` prop, NOT inline `<Icon>` children |
| `external="yes"` | `target="_blank"` + `rel="noopener noreferrer"` | `Link` | Opens in new window |
| `disabled="yes"` | `disabled` | `Link` | Boolean prop |
| `aria-label` | `aria-label` | `Link` | Pass through for accessibility |
| `tabindex` | `tabIndex` | `Link` | camelCase in React |
