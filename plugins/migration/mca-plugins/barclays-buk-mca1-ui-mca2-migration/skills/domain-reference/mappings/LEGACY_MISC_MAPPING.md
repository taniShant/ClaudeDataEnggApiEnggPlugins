# LEGACY_MISC_MAPPING.md

## Overview

Maps miscellaneous MCA1 legacy components to Blueprint-React equivalents. Covers: messages/alerts, progress bars, progressive disclosure, spinners/loading, and buttons with icons.

---

## Detection Patterns

```grep
scp-message-info
scp-message-warn
scp-message-alert
scp-message-error
scp-message-success
\.progressBar\(
scp-progress-bar
\.progressiveDisclosure\(
prog-dis-container
new Spinner\(
scp-button-regular
button-icon
fs-ico
```

---

## Component: Messages/Alerts

### MCA1 Pattern

```html
<div class="scp-message-info scp-message-singleline">Info message</div>
<div class="scp-message-warn scp-message-singleline">Warning message</div>
<div class="scp-message-alert scp-message-singleline">Alert message</div>
<div class="scp-message-error scp-message-singleline">Error message</div>
<div class="scp-message-success scp-message-singleline">Success message</div>
```

### Blueprint-React Equivalent

```typescript
import { Alert, Icon, Type } from '@barclays/blueprint-react';

// Info message
<Alert status="info" media={<Icon icon="info-fill" size="sm" status="info" />}>
  <Type>Info message</Type>
</Alert>

// Warning message
<Alert status="warning" media={<Icon icon="warning-fill" size="sm" status="warning" />}>
  <Type>Warning message</Type>
</Alert>

// Alert/Error message
<Alert status="error" media={<Icon icon="error-fill" size="sm" status="error" />}>
  <Type>Error message</Type>
</Alert>

// Success message
<Alert status="success" media={<Icon icon="tick-fill" size="sm" status="success" />}>
  <Type>Success message</Type>
</Alert>
```

### Message Class Mapping

| MCA1 CSS Class | Blueprint `status` | Icon |
|----------------|-------------------|------|
| `scp-message-info` | `"info"` | `info-fill` |
| `scp-message-warn` | `"warning"` | `warning-fill` |
| `scp-message-alert` | `"error"` | `error-fill` |
| `scp-message-error` | `"error"` | `error-fill` |
| `scp-message-success` | `"success"` | `tick-fill` |

---

## Component: Progress Bar (Workflow Steps)

### MCA1 Pattern

```html
<div id="progress-bar"></div>
```

```javascript
$('#progress-bar').progressBar({
  current: 2,
  items: ['1 Done step', '2 Done step', 'Current step', 'Following step', 'Following step 2']
});
```

**Alternative (Controller pattern):**
```javascript
this.hub.model("PROGRESS", { items: ["Item 1", "Item 2", "Item 3"], current: 0 });
new scp.ui.common.progress.ProgressController(this.find("#some_div_selector"), options);
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { ProgressVertical, ProgressVerticalItem, Badge, Type, Icon } from '@barclays/blueprint-react';

interface ProgressBarProps {
  items: string[];
  current: number;
}

export const WorkflowProgress: React.FC<ProgressBarProps> = ({ items, current }) => {
  const getState = (index: number): 'complete' | 'in-progress' | 'default' => {
    if (index < current) return 'complete';
    if (index === current) return 'in-progress';
    return 'default';
  };

  return (
    <ProgressVertical>
      {items.map((item, index) => (
        <ProgressVerticalItem
          key={index}
          state={getState(index)}
          badge={
            index < current
              ? <Badge><Icon icon="tick" size="xs" /></Badge>
              : <Badge>{index + 1}</Badge>
          }
          heading={<Type weight="medium">{item}</Type>}
        />
      ))}
    </ProgressVertical>
  );
};
```

**Note:** See also `BDL_PROGRESSIVE_MAPPING.md` for the `<mca-progressive>` web component equivalent.

---

## Component: Progressive Disclosure (Show/Hide)

### MCA1 Pattern

```html
<div class="row prog-dis-container" id="prog-dis">
  <div class="prog-dis-nav">
    <label class="nav-label three-columns" for="checkh2">Check to see more content</label>
    <div class="prog-dis-nav-check">
      <input class="scp-input-check" type="checkbox" name="checkh2" id="checkh2" opens="prog-dis-content-2">
      <label class="scp-label" for="checkh2">Label for CheckBox</label>
    </div>
  </div>
  <div class="prog-dis-content-container">
    <div class="prog-dis-content" id="prog-dis-content-2">
      <p>Revealed content</p>
    </div>
  </div>
</div>
```

```javascript
$('#prog-dis').progressiveDisclosure({
  label: 'Select preferred content',
  name: 'content',
  navigationItems: [
    { label_content: 'Text', attributes: { id: 'prog-text', value: 'T' }, content: $('<div>').html('Content') },
    { label_content: 'Empty', attributes: { id: 'prog-empty', value: 'E' } }
  ]
});
```

### Blueprint-React Equivalent (Checkbox toggle)

```typescript
import React, { useState } from 'react';
import { Checkbox, Type } from '@barclays/blueprint-react';

export const ProgressiveDisclosure: React.FC = () => {
  const [showContent, setShowContent] = useState(false);

  return (
    <>
      <Checkbox
        checked={showContent}
        onChange={() => setShowContent(!showContent)}
        label="Check to see more content"
      />
      {showContent && (
        <Type>Revealed content goes here</Type>
      )}
    </>
  );
};
```

### Blueprint-React Equivalent (Radio toggle)

```typescript
import React, { useState } from 'react';
import { FormItem, FormRadio, Type } from '@barclays/blueprint-react';

export const RadioDisclosure: React.FC = () => {
  const [selected, setSelected] = useState<string>('');

  return (
    <>
      <FormItem
        label={<Type>Select preferred content</Type>}
        render={() => (
          <>
            <FormRadio
              name="content"
              value="text"
              checked={selected === 'text'}
              onChange={() => setSelected('text')}
              label="Text"
            />
            <FormRadio
              name="content"
              value="empty"
              checked={selected === 'empty'}
              onChange={() => setSelected('empty')}
              label="Empty"
            />
          </>
        )}
      />
      {selected === 'text' && <Type>Text content shown here</Type>}
    </>
  );
};
```

---

## Component: Spinner / Loading

### MCA1 Pattern

```javascript
var options = {
  lines: 13, length: 7, width: 4, radius: 10,
  color: '#1F84E3', speed: 1, trail: 60
};
var target = $('#toSpin');
target.html("<div class='scp-progress-bar'><div>Loading message...</div></div>");
var spinner = new Spinner(options).spin();
$("#spinner", target).parent().get(0).appendChild(spinner.el);
```

### Blueprint-React Equivalent

```typescript
import { Loading, Type } from '@barclays/blueprint-react';

// Basic spinner
<Loading />

// With loading message
<Loading label={<Type>Loading message...</Type>} />

// Conditional loading state
{isLoading ? (
  <Loading label={<Type>Loading data...</Type>} />
) : (
  <ContentComponent />
)}
```

---

## Component: Button with Icon

### MCA1 Pattern

```html
<button class="scp-button-regular" type="button">
  <span class="fs-ico fs-icon-plus-sign button-icon"></span>
  With Icon
</button>
```

### Blueprint-React Equivalent

```typescript
import { Button, Icon } from '@barclays/blueprint-react';

<Button variant="secondary" media={<Icon icon="plus" size="sm" />}>
  With Icon
</Button>
```

### Icon Class Mapping

| MCA1 Icon Class | Blueprint `icon` Prop |
|-----------------|----------------------|
| `fs-icon-plus-sign` | `"plus"` |
| `fs-icon-ok` | `"tick"` |
| `fs-icon-remove` | `"close"` |
| `fs-icon-search` | `"search"` |
| `fs-icon-download` | `"download"` |
| `fs-icon-upload` | `"upload"` |
| `fs-icon-edit` | `"edit"` |
| `fs-icon-trash` | `"delete"` |
| `fs-icon-refresh` | `"refresh"` |
| `fs-icon-chevron-left` | `"chevron-left"` |
| `fs-icon-chevron-right` | `"chevron-right"` |

### Button Class Mapping

| MCA1 Button Class | Blueprint `variant` |
|-------------------|-------------------|
| `scp-button-regular` | `"secondary"` |
| `scp-button` | `"primary"` |
| `scp-button-next` | `"primary"` |
| `scp-button-cancel` | `"secondary"` |
| `scp-button-remove` | `"secondary"` (destructive context) |
| `scp-critical-button` | `"primary"` (destructive context) |

---

## Iron Rules

1. **Messages → `Alert` component** — not custom divs with CSS classes
2. **`Alert` requires `media` prop with `<Icon>`** — always provide the status icon
3. **Icon in Alert MUST have `size="sm"`** — omitting size renders oversized
4. **Spinners → `Loading` component** — never create custom spinner animations
5. **Progressive disclosure → `useState` boolean + conditional render** — not jQuery show/hide
6. **Button icons → `media` prop on `Button`** — not a `<span>` inside button children
7. **`scp-message-alert` and `scp-message-error` both map to `status="error"`** — same Blueprint status
8. **Progress bar (workflow steps) → `ProgressVertical`** — see `BDL_PROGRESSIVE_MAPPING.md` for full pattern
9. **`hub.model("PROGRESS", ...)` controller pattern → React props** — pass items/current as props to component
