# LEGACY_ACCORDION_TABS_MAPPING.md

## Overview

Maps MCA1 legacy accordion and tab components to Blueprint-React `Accordion` + `AccordionItem` and `Tabs` + `Tab`. Covers: legacy accordion (`.expandable()` jQuery plugin), basic tabs, tabs with icons, and nested tabs.

---

## Detection Patterns

```grep
\.expandable\(
steal\("scp/ui/common/vendor/contractingpanel/contractingpanel\.js"\)
scp-contracting-section
class="tab-section"
class="tabnav"
class="tab "
class="tabbed-content"
class="subTab-section"
class="sub-tabnav"
class="sub-tab"
class="sub-tabbed-content"
```

---

## Conversion: steal() → ES imports

```javascript
// MCA1 Accordion
steal("scp/ui/common/vendor/contractingpanel/contractingpanel.js").then(function() {
  $("#accordion").expandable({ title: "Panel heading" });
});

// MCA2
import { Accordion, AccordionItem, Tabs, Tab, Type } from '@barclays/blueprint-react';
```

---

## Component: Legacy Accordion

### MCA1 Pattern (jQuery)

```html
<div id="accordion">Content to display</div>
```

```javascript
$("#accordion").expandable({
  title: "Panel heading",
  afterClose: function() { /* triggered on close */ },
  afterOpen: function() { /* triggered on open */ },
  afterDisable: undefined,
  afterEnable: undefined
});
```

**API Methods:**
```javascript
$('#selectorID').expandable().open();
$('#selectorID').expandable().close();
$('#selectorID').expandable().enable();
$('#selectorID').expandable().disable();
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Accordion, AccordionItem, Type } from '@barclays/blueprint-react';

export const ExpandablePanel: React.FC = () => {
  const [expanded, setExpanded] = useState<string[]>([]);

  const handleChange = (openItems: string[]) => {
    setExpanded(openItems);
  };

  return (
    <Accordion expanded={expanded} onToggle={handleChange}>
      <AccordionItem id="panel1" heading={<Type weight="medium">Panel heading</Type>}>
        <Type>Content to display</Type>
      </AccordionItem>
    </Accordion>
  );
};
```

**Multiple accordion panels:**

```typescript
export const MultiAccordion: React.FC = () => {
  const [expanded, setExpanded] = useState<string[]>(['panel1']);

  return (
    <Accordion expanded={expanded} onToggle={setExpanded}>
      <AccordionItem id="panel1" heading={<Type weight="medium">Section 1</Type>}>
        <Type>Content for section 1</Type>
      </AccordionItem>
      <AccordionItem id="panel2" heading={<Type weight="medium">Section 2</Type>}>
        <Type>Content for section 2</Type>
      </AccordionItem>
      <AccordionItem id="panel3" heading={<Type weight="medium">Section 3</Type>}>
        <Type>Content for section 3</Type>
      </AccordionItem>
    </Accordion>
  );
};
```

### Options → Props Mapping

| MCA1 Option / Method | Blueprint Equivalent | Notes |
|---------------------|---------------------|-------|
| `title` | `heading` prop on `AccordionItem` | Wrap in `<Type weight="medium">` |
| `afterOpen` callback | Check `expanded` state in `useEffect` | React state-driven |
| `afterClose` callback | Check `expanded` state in `useEffect` | React state-driven |
| `.open()` | Add id to `expanded` array | `setExpanded([...expanded, id])` |
| `.close()` | Remove id from `expanded` array | `setExpanded(expanded.filter(...))` |
| `.disable()` | `disabled` prop on `AccordionItem` | Boolean prop |
| `.enable()` | Remove `disabled` prop | Conditional rendering |

---

## Component: Basic Tabs

### MCA1 Pattern

```html
<div class="row">
  <div class="eight-columns tab-section">
    <ul class="tabnav">
      <li class="tab current"><a href="javascript:void(0);">Tab1</a></li>
      <li class="tab"><a href="javascript:void(0);">Tab2</a></li>
      <li class="tab"><a href="javascript:void(0);">Tab3</a></li>
    </ul>
    <div class="tabbed-content current">Tab one content</div>
    <div class="tabbed-content">Tab two content</div>
    <div class="tabbed-content">Tab three content</div>
  </div>
</div>
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Tabs, Tab, Type } from '@barclays/blueprint-react';

export const BasicTabs: React.FC = () => {
  const [activeTab, setActiveTab] = useState('tab1');

  return (
    <Tabs activeTab={activeTab} onTabChange={setActiveTab}>
      <Tab id="tab1" label="Tab1">
        <Type>Tab one content</Type>
      </Tab>
      <Tab id="tab2" label="Tab2">
        <Type>Tab two content</Type>
      </Tab>
      <Tab id="tab3" label="Tab3">
        <Type>Tab three content</Type>
      </Tab>
    </Tabs>
  );
};
```

---

## Component: Tabs with Icons

### MCA1 Pattern

```html
<li class="tab current">
  <a href="javascript:void(0);">
    <span class="tab-label-text">Tab1 </span>
    <span class="tab-label-icon fs-ico fs-icon-medium fs-icon-ok color-success"></span>
  </a>
</li>
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Tabs, Tab, Type, Icon } from '@barclays/blueprint-react';

export const TabsWithIcons: React.FC = () => {
  const [activeTab, setActiveTab] = useState('tab1');

  return (
    <Tabs activeTab={activeTab} onTabChange={setActiveTab}>
      <Tab
        id="tab1"
        label={
          <Type>
            Tab1 <Icon icon="tick-fill" size="sm" status="success" />
          </Type>
        }
      >
        <Type>Tab one content</Type>
      </Tab>
      <Tab id="tab2" label="Tab2">
        <Type>Tab two content</Type>
      </Tab>
    </Tabs>
  );
};
```

---

## Component: Nested Tabs

### MCA1 Pattern

```html
<div class="tab-section">
  <ul class="tabnav">
    <li class="tab current">Parent Tab 1</li>
    <li class="tab">Parent Tab 2</li>
  </ul>
  <div class="tabbed-content current">
    <div class="subTab-section">
      <ul class="sub-tabnav">
        <li class="sub-tab current">Sub Tab1</li>
        <li class="sub-tab">Sub Tab2</li>
      </ul>
      <div class="sub-tabbed-content current">Sub tab 1 content</div>
      <div class="sub-tabbed-content">Sub tab 2 content</div>
    </div>
  </div>
  <div class="tabbed-content">Parent tab 2 content</div>
</div>
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Tabs, Tab, Type } from '@barclays/blueprint-react';

export const NestedTabs: React.FC = () => {
  const [parentTab, setParentTab] = useState('parent1');
  const [childTab, setChildTab] = useState('sub1');

  return (
    <Tabs activeTab={parentTab} onTabChange={setParentTab}>
      <Tab id="parent1" label="Parent Tab 1">
        <Tabs activeTab={childTab} onTabChange={setChildTab}>
          <Tab id="sub1" label="Sub Tab1">
            <Type>Sub tab 1 content</Type>
          </Tab>
          <Tab id="sub2" label="Sub Tab2">
            <Type>Sub tab 2 content</Type>
          </Tab>
        </Tabs>
      </Tab>
      <Tab id="parent2" label="Parent Tab 2">
        <Type>Parent tab 2 content</Type>
      </Tab>
    </Tabs>
  );
};
```

---

## CSS Class → Component Mapping

| MCA1 CSS Class | Blueprint Component | Notes |
|----------------|-------------------|-------|
| `tab-section` | `<Tabs>` | Container |
| `tabnav` | Built into `<Tabs>` | No separate element needed |
| `tab` | `<Tab>` | Individual tab |
| `tab current` | `<Tab>` with matching `activeTab` | Controlled via state |
| `tabbed-content` | Children of `<Tab>` | Content inside Tab component |
| `subTab-section` / `sub-tabnav` / `sub-tab` | Nested `<Tabs>` | Same component, nested |
| `scp-contracting-section` | `<Accordion>` | Container |
| `scp-contracting-section-header` | `heading` prop on `AccordionItem` | Built-in |
| `scp-contracting-section-content` | Children of `AccordionItem` | Content inside item |

---

## Event Handlers Mapping

| MCA1 Event | React Equivalent | Notes |
|------------|-----------------|-------|
| `afterOpen` callback | `useEffect` watching `expanded` | Trigger when id added |
| `afterClose` callback | `useEffect` watching `expanded` | Trigger when id removed |
| Tab click (`a href`) | `onTabChange` callback | Built-in prop |
| `current` class toggle | `activeTab` state | Controlled component |

---

## Iron Rules

1. **Accordion uses `expanded` array for open state** — NOT individual boolean per panel
2. **`AccordionItem` requires `id` and `heading` props** — id must be unique string
3. **Tab `label` prop accepts ReactNode** — can include icons, not just strings
4. **Nested tabs require separate state for each level** — don't share state between parent/child
5. **`javascript:void(0)` links → just use Tab component** — no anchor tags needed
6. **Column classes on tab containers are NOT needed** — Blueprint handles responsive layout
7. **`.expandable()` open/close → manipulate `expanded` state array** — React state-driven, no imperative API
