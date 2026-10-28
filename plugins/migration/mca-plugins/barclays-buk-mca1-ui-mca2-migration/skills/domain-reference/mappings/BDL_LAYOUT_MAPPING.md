# BDL Layout Components to Blueprint-React Mapping

**Last Updated**: April 24, 2026

---

## Layout Components

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-fluidview>` | `<Grid>` |
| `<mca-cell>` | `<Grid.Col>` |
| `<mca-header>` | `<Type element="hN">` (heading-only) or `<Page head={<Navbar>...}>` (nav controls present) |
| `<mca-footer>` | Footer section within `<Page>` or `<Section>` |
| `<mca-separator>` | `<Separator>` |

### Header Migration Decision

**CRITICAL**: `<mca-header>` maps to **two different patterns** depending on its content. Always inspect the element before migrating.

| Signal in MCA1 | Migration Target |
|---|---|
| `<mca-header>` contains only a `<span>` title (no `navigation-id`, no `close-icon`) | `<Type element="hN" size="...">` — heading only |
| `<mca-header>` has `navigation-id` or `close-icon="yes"` | `<Page head={<Navbar>...}>` — full layout pattern |
| `<mca-header>` is the outer page shell with nav controls | `<Page head={<Navbar>...}>` — full layout pattern |

If context is ambiguous, default to the heading-only pattern (`h1 size="2xl"`).

#### Accessibility Size Rules for `<Type>` heading

When using the heading-only pattern, choose `element` and `size` based on heading level in the document:

| Heading position | `element` | `size` |
|---|---|---|
| First / only heading on page | `h1` | `2xl` |
| Second-level heading | `h2` | `xl` |
| Third-level heading | `h3` | `lg` |
| Fourth-level heading | `h4` | (omit size, use default) |
| Fifth-level heading | `h5` | (omit size, use default) |

#### Heading-only header example

**MCA1 (Before)**:
```html
<mca-header id="header">
    <span id="header-title"> Maintain Roles </span>
</mca-header>
```

**Blueprint-React (After)**:
```tsx
<Type element="h1" size="2xl">Maintain Roles</Type>
```

**Rules:**
- The inner `<span>` text becomes the `<Type>` content — trim leading/trailing whitespace
- The `id` from `<mca-header>` or inner `<span>` may be preserved on the `<Type>` element
- Do **not** wrap in `<Page>` or `<Navbar>` — this is a standalone heading component

---

### Navbar Component API

`<Navbar>` is the Blueprint-React header bar component. **Do not guess its props — use only what is documented here.**

```typescript
interface NavbarProps {
  children: ReactNode;        // Heading + optional subtitle (Type components)
  prefix?: ReactNode;         // Left slot — back button (LinkButton with media icon)
  suffix?: ReactNode;         // Right slot — close/action button (LinkButton with media icon)
  alignment?: "left" | "center";  // Content alignment (default: "left")
  noGutter?: boolean;         // Remove left/right padding
  transparent?: boolean;      // Transparent background
}
```

**Key rules:**
- `prefix` = left-side button(s) — use for back/navigation (`navigation-id` in MCA1)
- `suffix` = right-side button(s) — use for close/dismiss (`close-icon="yes"` in MCA1)
- `children` = heading text, use `<Type element="h1" size="2xl" truncate>` — any valid size is acceptable
- Buttons in prefix/suffix **must** use `<LinkButton>` with `mediaOnly="always"` and a `media={<Icon>}` prop — **not** `<Button>`
- Title `<Type>` inside Navbar uses `size="md"` by default, but any valid size (`2xl`, `xl`, `lg`, etc.) is acceptable
- Optional subtitle: second `<Type element="span" truncate>` as second child

**Standard Navbar patterns:**

```tsx
{/* Back button only (navigation-id) */}
<Navbar
  prefix={
    <LinkButton
      media={<Icon icon="back" size="sm" />}
      mediaOnly="always"
      variant="secondary"
    >
      Back
    </LinkButton>
  }
>
  <Type element="h1" size="2xl" truncate>Page Title</Type>
</Navbar>

{/* Close button only (close-icon="yes") */}
<Navbar
  suffix={
    <LinkButton
      media={<Icon icon="dismiss" size="sm" />}
      mediaOnly="always"
      variant="secondary"
    >
      Close
    </LinkButton>
  }
>
  <Type element="h1" size="2xl" truncate>Page Title</Type>
</Navbar>

{/* Both back and close (navigation-id + close-icon="yes") */}
<Navbar
  prefix={
    <LinkButton
      media={<Icon icon="back" size="sm" />}
      mediaOnly="always"
      variant="secondary"
    >
      Back
    </LinkButton>
  }
  suffix={
    <LinkButton
      media={<Icon icon="dismiss" size="sm" />}
      mediaOnly="always"
      variant="secondary"
    >
      Close
    </LinkButton>
  }
>
  <Type element="h1" size="2xl" truncate>Page Title</Type>
  <Type element="span" truncate>Optional subtitle</Type>
</Navbar>
```

---

### Page Layout

**MCA1 (Before)**:
```html
<mca-header class="scp-view-header" id="header" close-icon="yes"
    navigation-id="backButton">
    <span id="header-title">Application received</span>
</mca-header>

<!-- page content -->

<mca-footer>
    <mca-button id="finishButton" type="primary" align="right">All done</mca-button>
</mca-footer>
```

**Blueprint-React (After)**:
```tsx
<Page
  head={
    <Navbar
      prefix={
        <LinkButton
          media={<Icon icon="back" size="sm" />}
          mediaOnly="always"
          variant="secondary"
          id="backButton"
        >
          Back
        </LinkButton>
      }
      suffix={
        <LinkButton
          media={<Icon icon="dismiss" size="sm" />}
          mediaOnly="always"
          variant="secondary"
        >
          Close
        </LinkButton>
      }
    >
      <Type element="h1" size="2xl" truncate>Application received</Type>
    </Navbar>
  }
>
  <Section>
    <SectionItem>
      {/* page content */}
    </SectionItem>
  </Section>

  <Section>
    <SectionItem>
      <Arrange gap="fixed" justify="end">
        <ArrangeItem size="fit">
          <Button variant="primary" id="finishButton" onClick={handleFinish}>
            All done
          </Button>
        </ArrangeItem>
      </Arrange>
    </SectionItem>
  </Section>
</Page>
```

### Grid Layout

**MCA1 (Before)**:
```html
<mca-fluidview>
    <mca-cell size="6">Left content</mca-cell>
    <mca-cell size="6">Right content</mca-cell>
</mca-fluidview>
```

**Blueprint-React (After)**:
```typescript
<Grid>
  <Grid.Col size="1of2">Left content</Grid.Col>
  <Grid.Col size="1of2">Right content</Grid.Col>
</Grid>
```

**Cell Size Mapping** (MCA1 12-column to Blueprint fractions):
| MCA1 `<mca-cell size="N">` | Blueprint `<Grid.Col size="...">` |
|---|---|
| `size="1"` | `size="1of12"` |
| `size="2"` | `size="2of12"` |
| `size="3"` | `size="1of4"` |
| `size="4"` | `size="1of3"` |
| `size="5"` | `size="5of12"` |
| `size="6"` | `size="1of2"` |
| `size="7"` | `size="7of12"` |
| `size="8"` | `size="2of3"` |
| `size="9"` | `size="3of4"` |
| `size="10"` | `size="10of12"` |
| `size="11"` | `size="11of12"` |
| `size="12"` or `type="section"` | `size="12of12"` (full width) |

### Responsive Grid

Blueprint-React's `<Grid.Col>` supports responsive size props:

| Prop | Breakpoint | Description |
|---|---|---|
| `size` | Default/all | Base column size |
| `sizeXs` | Extra small (mobile) | Overrides size at xs breakpoint |
| `sizeSm` | Small (tablet) | Overrides size at sm breakpoint |
| `sizeMd` | Medium | Overrides size at md breakpoint |
| `sizeLg` | Large (desktop) | Overrides size at lg breakpoint |

**MCA1 (Before)** — no responsive support, uses media queries in CSS:
```html
<mca-fluidview>
    <mca-cell size="4">Column 1</mca-cell>
    <mca-cell size="4">Column 2</mca-cell>
    <mca-cell size="4">Column 3</mca-cell>
</mca-fluidview>
```

**Blueprint-React (After)** — responsive props built into the component:
```typescript
<Grid>
  <Grid.Col size="1of3" sizeXs="1of1">Column 1</Grid.Col>
  <Grid.Col size="1of3" sizeXs="1of1">Column 2</Grid.Col>
  <Grid.Col size="1of3" sizeXs="1of1">Column 3</Grid.Col>
</Grid>
```

> **Key difference**: MCA1 required separate CSS media queries for responsive behavior. Blueprint-React handles responsiveness declaratively through size props on `<Grid.Col>`.

---

### Section and SectionItem

Blueprint-React uses `<Section>` and `<SectionItem>` as core layout building blocks for page content areas.

| MCA1 Concept | Blueprint-React |
|---|---|
| Content wrapper div | `<Section>` |
| Content block with spacing | `<SectionItem spacing="sm\|md\|lg">` |

**Example**:
```typescript
<Section>
  <SectionItem spacing="md">
    <Type element="h2">Section Heading</Type>
  </SectionItem>
  <SectionItem spacing="sm">
    <Type>Content paragraph within the section.</Type>
  </SectionItem>
</Section>
```

> **Note**: `<SectionItem>` accepts a `spacing` prop (`sm`, `md`, `lg`) to control vertical spacing between items within a section.

---

### Image / Multimedia

For `<mca-image>` to `<Multimedia>` mapping, see the dedicated file: **[BDL_IMAGE_MAPPING.md](BDL_IMAGE_MAPPING.md)**

---

## Attribute Mapping Tables

### `<mca-fluidview>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Component | Notes |
|---|---|---|---|
| (no direct attributes) | — | `<Grid>` | Grid is a simple wrapper; no MCA1 attributes map directly |
| CSS class for gutter | `gutter` | `<Grid>` | Controls spacing between columns |
| CSS class for alignment | `align` | `<Grid>` | Align columns within the grid |

### `<mca-cell>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Component | Notes |
|---|---|---|---|
| `size` | `size` | `<Grid.Col>` | Converted from numeric (1-12) to fraction format (see table above) |
| `type="section"` | `size="12of12"` | `<Grid.Col>` | Full-width column |
| `class` | `className` | `<Grid.Col>` | Standard React className mapping |
| `id` | `id` | `<Grid.Col>` | |
| — | `sizeXs` | `<Grid.Col>` | New: responsive override for extra-small screens |
| — | `sizeSm` | `<Grid.Col>` | New: responsive override for small screens |
| — | `sizeMd` | `<Grid.Col>` | New: responsive override for medium screens |
| — | `sizeLg` | `<Grid.Col>` | New: responsive override for large screens |

### `<mca-header>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Component | Notes |
|---|---|---|---|
| `id` | `id` | `<Type>` or `<Navbar>` | On `<Type>` for heading-only; on wrapping element for full layout |
| `class` | `className` | `<Type>` or `<Navbar>` | Standard React className mapping |
| `close-icon="yes"` | `suffix` prop | `<Navbar>` | **Triggers full layout pattern** — `suffix={<LinkButton media={<Icon icon="dismiss" size="sm"/>} mediaOnly="always" variant="secondary">Close</LinkButton>}` |
| `navigation-id` | `id` on `prefix` `<LinkButton>` | `<Navbar>` | **Triggers full layout pattern** — `prefix={<LinkButton id="..." media={<Icon icon="back" size="sm"/>} mediaOnly="always" variant="secondary">Back</LinkButton>}` |
| Children (`<span>` title, no nav attrs) | `<Type element="h1\|h2\|h3" size="2xl\|xl\|lg">` | Standalone | Heading-only: pick element+size by accessibility level (see decision table above) |
| Children (`<span>` title, with nav attrs) | `<Type element="h1" size="md" truncate>` inside `<Navbar>` | Inside `<Navbar>` | Full layout: title wrapped in Type; `size="md"` is the default but `2xl`/`xl`/`lg` are also valid |

### `<mca-footer>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Component | Notes |
|---|---|---|---|
| `id` | `id` | `<Section>` | Footer is rendered as a `<Section>` at the bottom of `<Page>` |
| `class` | `className` | `<Section>` | Standard React className mapping |
| Children (buttons) | `<ButtonGroup>` or `<Arrange>` | Inside `<SectionItem>` | Use Arrange for alignment control, ButtonGroup for grouped actions |
| `align="right"` on buttons | `justify="end"` | `<Arrange>` | Right-align footer actions using Arrange justify prop |
