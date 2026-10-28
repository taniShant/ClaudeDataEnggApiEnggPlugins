# LEGACY_TYPOGRAPHY_MAPPING.md

## Overview

Maps MCA1 legacy typography components (content/font styles and headings) to Blueprint-React `Type` component with appropriate `element`, `size`, and `weight` props.

---

## Detection Patterns

```grep
class="scp-text"
class="scp-text-value"
<h[1-6]>
```

---

## Component: Content Text Styles

### MCA1 Pattern

```html
<h2>Sample text with default styles</h2>
<p>Nullam quis risus eget urna mollis ornare vel eu leo.</p>

<h2>Sample text with class "scp-text" applied</h2>
<p class="scp-text">Nullam quis risus eget urna mollis ornare vel eu leo.</p>

<h2>Sample text with class "scp-text-value" applied</h2>
<p class="scp-text-value">Nullam quis risus eget urna mollis ornare vel eu leo.</p>
```

### Blueprint-React Equivalent

```typescript
import { Type } from '@barclays/blueprint-react';

// Default paragraph text (replaces plain <p> or <p class="scp-text">)
<Type>Nullam quis risus eget urna mollis ornare vel eu leo.</Type>

// Value text (replaces <p class="scp-text-value"> — slightly bolder presentation)
<Type weight="medium">Nullam quis risus eget urna mollis ornare vel eu leo.</Type>

// With explicit paragraph element
<Type element="p">Paragraph text content.</Type>
```

---

## Component: Headings

### MCA1 Pattern

```html
<h1>h1. Heading 1</h1>
<h2>h2. Heading 2</h2>
<h3>h3. Heading 3</h3>
<h4>h4. Heading 4</h4>
<h5>h5. Heading 5</h5>
<h6>h6. Heading 6</h6>
```

### Blueprint-React Equivalent

```typescript
import { Type } from '@barclays/blueprint-react';

<Type element="h1" size="xxl" weight="medium">Heading 1</Type>
<Type element="h2" size="xl" weight="medium">Heading 2</Type>
<Type element="h3" size="lg" weight="medium">Heading 3</Type>
<Type element="h4" size="md" weight="medium">Heading 4</Type>
<Type element="h5" size="sm" weight="medium">Heading 5</Type>
<Type element="h6" size="xs" weight="medium">Heading 6</Type>
```

---

## CSS Class → Type Props Mapping

| MCA1 Pattern | Blueprint `<Type>` Props | Notes |
|-------------|-------------------------|-------|
| `<p>` (plain) | `<Type>` or `<Type element="p">` | Default body text |
| `<p class="scp-text">` | `<Type>` | Same as default — scp-text was BDL base styling |
| `<p class="scp-text-value">` | `<Type weight="medium">` | Slightly emphasized display value |
| `<h1>` | `element="h1" size="xxl" weight="medium"` | Page heading |
| `<h2>` | `element="h2" size="xl" weight="medium"` | Section heading |
| `<h3>` | `element="h3" size="lg" weight="medium"` | Sub-section heading |
| `<h4>` | `element="h4" size="md" weight="medium"` | Minor heading |
| `<h5>` | `element="h5" size="sm" weight="medium"` | Small heading |
| `<h6>` | `element="h6" size="xs" weight="medium"` | Smallest heading |
| `<b>` or `<strong>` | `<Type weight="bold">` | Bold inline text |
| `<span>` (generic) | `<Type element="span">` | Inline text |

---

## Type Size Reference

| Size Prop | Use Case |
|-----------|----------|
| `xxl` | Page titles (h1) |
| `xl` | Section headings (h2) |
| `lg` | Sub-sections (h3) |
| `md` | Card/panel headings (h4), default for emphasis |
| `sm` | Helper text, captions |
| `xs` | Fine print, metadata |

---

## Iron Rules

1. **All text rendering uses `<Type>` component** — never use raw `<p>`, `<h1>`-`<h6>`, or `<span>` directly in migrated code
2. **`element` prop controls the rendered HTML tag** — use it for semantic correctness (h1-h6 for headings, p for paragraphs)
3. **`scp-text` class has no special equivalent** — it was BDL's base font reset; `<Type>` already applies correct styling
4. **`scp-text-value` → `weight="medium"`** — represents a displayed value (slightly bolder than body text)
5. **Never add custom font-size CSS** — use `size` prop for all sizing needs
6. **Heading hierarchy must be preserved** — if MCA1 used `<h2>`, use `element="h2"` in Blueprint (accessibility)
