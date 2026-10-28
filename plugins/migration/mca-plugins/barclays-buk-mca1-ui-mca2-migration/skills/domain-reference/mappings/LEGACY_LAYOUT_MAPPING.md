# LEGACY_LAYOUT_MAPPING.md

## Overview

Maps MCA1 legacy layout components (8-column grid, separators, header layout, footer layout) to Blueprint-React `Grid`, `Separator`, and page structure patterns.

---

## Detection Patterns

```grep
class="row"
-columns"
class="nested-container"
scp-group-with-separator
scp-separator-with-text
scp-separator-line
scp-view-header
scp-close-link
scp-navigation-panel
class="footer"
scp-button-next
scp-button-cancel
scp-button-remove
scp-float-left
scp-float-right
```

---

## Component: Grid Layout (8-Column System)

### MCA1 Pattern

```html
<div class="row">
  <div class="two-columns">Two columns wide</div>
  <div class="three-columns">Three columns wide</div>
  <div class="three-columns">Three columns wide</div>
</div>
<div class="row">
  <div class="eight-columns">Full width</div>
</div>
<div class="row">
  <span class="nested-container">
    <div class="row">
      <div class="three-columns">Nested content</div>
    </div>
  </span>
</div>
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Grid, Type } from '@barclays/blueprint-react';

export const GridLayout: React.FC = () => (
  <>
    <Grid>
      <Grid.Col span={3}><Type>Two columns wide</Type></Grid.Col>
      <Grid.Col span={4}><Type>Three columns wide</Type></Grid.Col>
      <Grid.Col span={4}><Type>Three columns wide</Type></Grid.Col>
    </Grid>
    <Grid>
      <Grid.Col span={12}><Type>Full width</Type></Grid.Col>
    </Grid>
    <Grid>
      <Grid.Col span={4}>
        <Grid>
          <Grid.Col span={12}><Type>Nested content</Type></Grid.Col>
        </Grid>
      </Grid.Col>
    </Grid>
  </>
);
```

### Column Mapping (8-col → 12-col)

MCA1 uses an 8-column grid. Blueprint uses 12-column. Multiply by 1.5 (round to nearest):

| MCA1 Class | Columns (out of 8) | Blueprint `span` (out of 12) |
|-----------|--------------------|-----------------------------|
| `one-column` / `one-columns` | 1 | 1 or 2 |
| `two-columns` | 2 | 3 |
| `three-columns` | 3 | 4 or 5 |
| `four-columns` | 4 | 6 |
| `five-columns` | 5 | 7 or 8 |
| `six-columns` | 6 | 9 |
| `seven-columns` | 7 | 10 or 11 |
| `eight-columns` | 8 | 12 |

---

## Component: Separator (Line)

### MCA1 Pattern

```html
<div class="row scp-group-with-separator">
  <div class="eight-columns"><p>Content above separator</p></div>
</div>
<div class="row"><div class="eight-columns"><p>Content below</p></div></div>
```

### Blueprint-React Equivalent

```typescript
import { Separator, Type } from '@barclays/blueprint-react';

<Type>Content above separator</Type>
<Separator />
<Type>Content below</Type>
```

---

## Component: Separator with Text

### MCA1 Pattern

```html
<div class="scp-separator-with-text">
  <div class="scp-separator-line"></div>
  <div class="scp-separator-text-container">
    <span class="scp-separator-text scp-light-bg">SEPARATOR TEXT</span>
  </div>
</div>
```

### Blueprint-React Equivalent

```typescript
import { Separator, Type } from '@barclays/blueprint-react';

<Separator label={<Type size="sm" weight="medium">SEPARATOR TEXT</Type>} />
```

---

## Component: Header Layout (with Close Icon)

### MCA1 Pattern

```html
<div class="row scp-view">
  <div class="scp-view-header">
    <h1>
      <a id="button-close" class="scp-close-link" tabindex="10" href="javascript:void(0);"></a>
      Page Title
    </h1>
  </div>
  <div class="eight-columns">
    <p>Page content here...</p>
  </div>
</div>
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Section, SectionItem, Type, Button, Icon, Arrange, ArrangeItem } from '@barclays/blueprint-react';

interface PageHeaderProps {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}

export const PageWithHeader: React.FC<PageHeaderProps> = ({ title, onClose, children }) => (
  <Section>
    <SectionItem>
      <Arrange>
        <ArrangeItem size="fill">
          <Type element="h1" size="xxl" weight="medium">{title}</Type>
        </ArrangeItem>
        <ArrangeItem size="fit">
          <Button variant="subtle" onClick={onClose}>
            <Icon icon="close" size="sm" />
          </Button>
        </ArrangeItem>
      </Arrange>
    </SectionItem>
    <SectionItem>
      {children}
    </SectionItem>
  </Section>
);
```

---

## Component: Footer Layout (with Buttons and Links)

### MCA1 Pattern

```html
<div class="scp-view">
  <div class="row footer" id="demo_footer">
    <div class="scp-navigation-panel">
      <button type="button" class="scp-button-remove scp-float-left">Delete</button>
      <a class="scp-float-left scp-anchor-button" href="#">Link Button</a>
      <button type="button" class="scp-button-cancel scp-float-right">Cancel</button>
      <button type="button" class="scp-button-next scp-float-right">Next</button>
    </div>
  </div>
</div>
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Arrange, ArrangeItem, Button, Type } from '@barclays/blueprint-react';

interface FooterProps {
  onDelete?: () => void;
  onCancel?: () => void;
  onNext?: () => void;
}

export const PageFooter: React.FC<FooterProps> = ({ onDelete, onCancel, onNext }) => (
  <Arrange>
    <ArrangeItem size="fit">
      {onDelete && <Button variant="secondary" onClick={onDelete}>Delete</Button>}
    </ArrangeItem>
    <ArrangeItem size="fill" />
    <ArrangeItem size="fit">
      {onCancel && <Button variant="secondary" onClick={onCancel}>Cancel</Button>}
    </ArrangeItem>
    <ArrangeItem size="fit">
      {onNext && <Button variant="primary" onClick={onNext}>Next</Button>}
    </ArrangeItem>
  </Arrange>
);
```

---

## CSS Class → Blueprint Mapping

| MCA1 CSS Class | Blueprint Equivalent | Notes |
|----------------|---------------------|-------|
| `row` | `<Grid>` or removed (FormItem handles layout) | Only use Grid for explicit column layouts |
| `*-columns` | `<Grid.Col span={N}>` | Convert 8-col to 12-col |
| `nested-container` | Nested `<Grid>` | Grid inside Grid.Col |
| `scp-group-with-separator` | `<Separator />` between content | Simple divider |
| `scp-separator-with-text` | `<Separator label={...} />` | Separator with text overlay |
| `scp-view-header` | `<Section>` + `<Arrange>` | Page header pattern |
| `scp-close-link` | `<Button variant="subtle">` + `<Icon icon="close" />` | Close button |
| `scp-navigation-panel` | `<Arrange>` with `<ArrangeItem>` | Footer button layout |
| `scp-float-left` | `<ArrangeItem>` (left positioned) | Use Arrange order |
| `scp-float-right` | `<ArrangeItem>` (right positioned) | Use fill spacer between |
| `scp-button-next` | `<Button variant="primary">` | Primary action |
| `scp-button-cancel` | `<Button variant="secondary">` | Secondary action |
| `scp-button-remove` | `<Button variant="secondary">` | Destructive secondary |
| `scp-anchor-button` | `<Button variant="tertiary">` | Link-style button |
| `footer` | Bottom section of page component | No special wrapper needed |

---

## Iron Rules

1. **8-column grid → 12-column grid** — multiply column counts by 1.5 (approximate)
2. **`row` class is NOT always needed** — FormItem handles its own layout; only use Grid for explicit multi-column content
3. **Float classes (`scp-float-left/right`) → `Arrange` + `ArrangeItem`** — never use CSS float in React
4. **`scp-close-link` → `Button variant="subtle"` with close Icon** — not an anchor tag
5. **Separator is a standalone component** — don't wrap content in separator divs
6. **Footer buttons use `Arrange` for spacing** — left items first, then fill spacer, then right items
7. **`nested-container` → nested `Grid`** — Grid can be placed inside Grid.Col
