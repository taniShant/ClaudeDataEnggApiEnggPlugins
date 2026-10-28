# LEGACY_LABELS_MAPPING.md

## Overview

Maps MCA1 legacy label components (text labels, icon labels, and read-only labels) to Blueprint-React `Type`, `Icon`, and `FormItem` patterns. These are all purely HTML/CSS components with no JavaScript initialization.

---

## Detection Patterns

```grep
class="scp-label"
class="scp-readOnlyText"
class="scp-text-value"
scp-correct-img
scp-info-img
```

---

## Component: Text Label

### MCA1 Pattern

```html
<label for="textLabel" class="scp-label">This is Text Label</label>
```

### Blueprint-React Equivalent

```typescript
import { Type } from '@barclays/blueprint-react';

// As standalone label
<Type>This is Text Label</Type>

// As FormItem label (most common usage)
<FormItem
  label={<Type>This is Text Label</Type>}
  render={(props) => (
    <FormInput {...props} />
  )}
/>
```

---

## Component: Icon Label

### MCA1 Pattern

```html
<label for="imgLabel" class="scp-label">
  <span class="scp-correct-img"></span>
</label>
```

Common icon classes:
- `scp-correct-img` — success/tick icon
- `scp-info-img` — info icon
- `scp-warning-img` — warning icon
- `scp-error-img` — error icon

### Blueprint-React Equivalent

```typescript
import { Icon, Type } from '@barclays/blueprint-react';

// Success icon
<Icon icon="tick-fill" size="sm" status="success" />

// Info icon
<Icon icon="info-fill" size="sm" status="info" />

// Warning icon
<Icon icon="warning-fill" size="sm" status="warning" />

// Error icon
<Icon icon="error-fill" size="sm" status="error" />

// Icon with label text
<Type>
  <Icon icon="tick-fill" size="sm" status="success" /> Verified
</Type>
```

### Icon Class Mapping

| MCA1 CSS Class | Blueprint Icon | Status Prop |
|----------------|---------------|-------------|
| `scp-correct-img` | `tick-fill` | `success` |
| `scp-info-img` | `info-fill` | `info` |
| `scp-warning-img` | `warning-fill` | `warning` |
| `scp-error-img` | `error-fill` | `error` |
| `fs-icon-plus-sign` | `plus` | — |
| `fs-icon-ok` | `tick` | `success` |

---

## Component: Read-Only Label with Value

### MCA1 Pattern

```html
<div class="scp-readOnlyText">
  <label class="scp-label">Readonly label</label>
  <div class="scp-text-value">Readonly value</div>
</div>
```

```html
<!-- Simple text variant -->
<div class="scp-readOnlyText">Normal readonly text</div>
<div class="scp-readOnlyText"><b>Bold readonly text</b></div>
```

### Blueprint-React Equivalent

```typescript
import { FormItem, Type } from '@barclays/blueprint-react';

// Label + value pair (most common)
<FormItem
  label={<Type>Readonly label</Type>}
  render={() => (
    <Type>Readonly value</Type>
  )}
/>

// Simple read-only text
<Type>Normal readonly text</Type>

// Bold read-only text
<Type weight="medium">Bold readonly text</Type>
```

---

## Component: Label with Grid Columns

### MCA1 Pattern

```html
<label for="field1" class="scp-label two-columns">Field Label</label>
<input type="text" class="scp-input-text two-columns" id="field1">
```

### Blueprint-React Equivalent

```typescript
import { FormItem, FormInput, Type } from '@barclays/blueprint-react';

// Blueprint FormItem handles layout automatically — no column classes needed
<FormItem
  label={<Type>Field Label</Type>}
  render={(props) => (
    <FormInput {...props} />
  )}
/>
```

---

## CSS Class → Blueprint Mapping

| MCA1 CSS Class | Blueprint Equivalent | Notes |
|----------------|---------------------|-------|
| `scp-label` | `<Type>` inside FormItem `label` prop | Standard label pattern |
| `scp-readOnlyText` | `<FormItem>` with `<Type>` in render | Read-only display pattern |
| `scp-text-value` | `<Type>` | Display value text |
| `two-columns` / `three-columns` | Not needed | Blueprint handles responsive layout |
| `scp-correct-img` | `<Icon icon="tick-fill" status="success" size="sm" />` | Icon component |
| `scp-info-img` | `<Icon icon="info-fill" status="info" size="sm" />` | Icon component |

---

## Iron Rules

1. **`scp-label` → `<Type>` inside `FormItem` `label` prop** — never create standalone `<label>` elements
2. **Column classes (`two-columns`, `three-columns`) are NOT needed** — Blueprint handles layout
3. **Icon labels → `<Icon>` with MANDATORY `size` prop** — omitting `size` renders oversized icons
4. **Read-only patterns → `FormItem` with `<Type>` in render function** — maintains form layout alignment
5. **Bold text → `<Type weight="medium">`** — not `<b>` tags or CSS
6. **`scp-readOnlyText` wrapping label+value → single `FormItem`** — label goes in `label` prop, value in `render`
