# BDL Typography and Text to Blueprint-React Mapping

**Last Updated**: June 25, 2026

---

## Typography and Text

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-heading>` | `<Type>` with appropriate `element` and `size` props |
| `<mca-text>` | `<Type>` |

---

## CRITICAL: Canonical Heading Size Mapping

Every `<Type element="hN">` MUST have an explicit `size` prop. Without it, headings render at default paragraph size with no visual hierarchy.

| Element | Size Prop | marginBottom | Use Case |
|---------|-----------|--------------|----------|
| `h1` | `3xl` | `lg` | Page title (one per page) |
| `h2` | `2xl` | `md` | Section heading |
| `h3` | `xl` | `sm` | Subsection / card heading |
| `h4` | `lg` | `sm` | Card heading / group title |
| `h5` | `md` | `xs` | Group label / minor section |
| `h6` | `sm` | `xs` | Smallest heading |
| `p` | (default) | `true` | Body paragraph |

**Rule:** Sizes MUST be monotonically decreasing: h1 ≥ h2 ≥ h3 ≥ h4 ≥ h5 ≥ h6. Never apply a larger size to a lower heading level.

---

## Comprehensive Heading Examples

**MCA1 (Before)**:
```html
<mca-heading type="h1" style-type="tertiary" id="b_heading_h1">
  Heading h1
  <mca-text hide="desktop" text-type="standard" display="inline">(content to be shown only in mobile)</mca-text>
</mca-heading>
<mca-heading type="h2" class="b_heading_h2" id="b_heading_h2" title="Heading h2">
  Heading h2
  <mca-text hide="mobile" text-type="standard" display="inline">(content to be hidden in mobile)</mca-text>
</mca-heading>
<mca-heading type="h3" id="b_heading_h3">Heading h3</mca-heading>
<mca-heading type="h4" id="b_heading_h4">Heading h4</mca-heading>
<mca-heading type="h5" id="b_heading_h5">Heading h5</mca-heading>
<mca-heading type="h6" id="b_heading_h6">Heading h6</mca-heading>
<mca-heading type="h6" id="b_heading_h6_subheading" style-type="subheading">
  Subheading (mobile specific attribute)
</mca-heading>
<mca-heading type="h5" id="b_heading_h5_primary" style-type="primary">Primary (mobile specific attribute)</mca-heading>
<mca-heading type="h5" id="b_heading_h5_secondary" style-type="secondary">Secondary (mobile specific attribute)</mca-heading>
<mca-heading type="h5" id="b_heading_h5_tertiary" style-type="tertiary">Tertiary (mobile specific attribute)</mca-heading>
<mca-heading type="h5" id="b_heading_h5_block" style-type="block">Styled as heading</mca-heading>
<mca-text>
  Lorem ipsum dolor sit amet,
  <mca-heading type="h1" id="b_heading_h5_inline" style-type="inline">consectetuer</mca-heading>
  adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.
</mca-text>
```

**Blueprint-React (After)**:
```typescript
const isMobile = useMediaQuery('(max-width: 768px)');

<>
  <Type element="h1" size="3xl" marginBottom="lg" id="b_heading_h1">
    Heading h1
    {isMobile && ' (content to be shown only in mobile)'}
  </Type>
  <Type element="h2" size="2xl" marginBottom="md" id="b_heading_h2" title="Heading h2">
    Heading h2
    {!isMobile && ' (content to be hidden in mobile)'}
  </Type>
  <Type element="h3" size="xl" marginBottom="sm" id="b_heading_h3">Heading h3</Type>
  <Type element="h4" size="lg" marginBottom="sm" id="b_heading_h4">Heading h4</Type>
  <Type element="h5" size="md" marginBottom="xs" id="b_heading_h5">Heading h5</Type>
  <Type element="h6" size="sm" marginBottom="xs" id="b_heading_h6">Heading h6</Type>
  <Type element="h6" size="sm" weight="medium" marginBottom="xs" id="b_heading_h6_subheading">
    Subheading
  </Type>
  <Type element="h5" size="md" weight="bold" marginBottom="xs" id="b_heading_h5_primary">
    Primary
  </Type>
  <Type element="h5" size="md" weight="medium" marginBottom="xs" id="b_heading_h5_secondary">
    Secondary
  </Type>
  <Type element="h5" size="md" weight="regular" marginBottom="xs" id="b_heading_h5_tertiary">
    Tertiary
  </Type>
  <Type element="h5" size="md" marginBottom="xs" id="b_heading_h5_block">
    Styled as heading
  </Type>
  <Type element="p" marginBottom>
    Lorem ipsum dolor sit amet,{' '}
    <Type element="span" weight="bold">consectetuer</Type>
    {' '}adipiscing elit, sed diam nonummy nibh euismod tincidunt ut laoreet dolore magna aliquam erat volutpat.
  </Type>
</>
```

---

## Basic Heading Pattern

**MCA1 (Before)**:
```html
<mca-heading type="h4">What happens next?</mca-heading>
<mca-heading type="h5" style-type="tertiary">Transferring from</mca-heading>
<mca-text>The customer must sign a printed copy.</mca-text>
<mca-text text-type="small">Sort code: 12-34-56</mca-text>
```

**Blueprint-React (After)**:
```typescript
<Type element="h4" size="lg" marginBottom="sm">What happens next?</Type>
<Type element="h5" size="md" marginBottom="xs">Transferring from</Type>
<Type element="p" marginBottom>The customer must sign a printed copy.</Type>
<Type element="span" size="sm">Sort code: 12-34-56</Type>
```

---

## Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `type="h1"` | `element="h1" size="3xl"` | ALWAYS include both element AND size |
| `type="h2"` | `element="h2" size="2xl"` | ALWAYS include both element AND size |
| `type="h3"` | `element="h3" size="xl"` | ALWAYS include both element AND size |
| `type="h4"` | `element="h4" size="lg"` | ALWAYS include both element AND size |
| `type="h5"` | `element="h5" size="md"` | ALWAYS include both element AND size |
| `type="h6"` | `element="h6" size="sm"` | ALWAYS include both element AND size |
| `style-type="primary"` | `weight="bold"` | Added to the base element+size |
| `style-type="secondary"` | `weight="medium"` | Added to the base element+size |
| `style-type="tertiary"` | `weight="regular"` | Explicit regular (default is inherited) |
| `style-type="subheading"` | `weight="medium" size="sm"` | Overrides canonical size for subheading style |
| `style-type="inline"` | `element="span" weight="bold"` | Inline rendering, not a heading |
| `style-type="block"` | (no extra props needed) | Uses canonical heading size |
| `text-type="small"` | `size="sm"` | Small text |
| `hide="mobile"` | Conditional rendering with `useMediaQuery()` | `const isMobile = useMediaQuery('(max-width: 768px)')` |
| `hide="desktop"` | Conditional rendering with `useMediaQuery()` | `{isMobile && '...'}` |
| `display="inline"` | `element="span"` | Inline rendering |
| `id`, `name`, `class`, `title` | Remain unchanged | Pass through as HTML attributes |

---

## Spacing Rules

- Every heading (`h1`-`h6`) MUST have a `marginBottom` prop for spacing from content below
- `marginBottom` valid values: `true` (default spacing), `"xl"`, `"lg"`, `"sm"`, `"xs"`, `"2xs"`
- Type does NOT have `marginTop` — use only `marginBottom` for spacing
- Use `Section` and `SectionItem` components for larger structural spacing between sections

---

## Valid `Type` Props Reference

**element:** `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `p`, `span`, `em`, `strong`, `td`, `th`
**size:** `default`, `xs`, `sm`, `md`, `lg`, `xl`, `2xl`, `3xl`
**weight:** `bold`, `light`, `regular`, `medium`, `heavy`
**color:** `default`, `success`, `error`, `warning`, `inverse`, `info`, `title`, `disabled`
**marginBottom:** `true`, `xl`, `lg`, `sm`, `xs`, `2xs`
**alignment:** `left`, `right`, `center`

**Do NOT use:** `element="div"` (invalid), `color="brand"` (invalid), `color="muted"` (invalid), `marginTop` (does not exist)
