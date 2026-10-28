# LEGACY_DROPDOWN_MAPPING.md

## Overview

Maps all 11 MCA1 legacy Chosen-based dropdown variants to Blueprint-React equivalents. All legacy dropdowns use the `.chosen()` jQuery plugin with `steal("scp/ui/common/vendor/chosen/chosen.js")`.

---

## Detection Patterns

```grep
\.chosen\(
steal\("scp/ui/common/vendor/chosen/chosen\.js"\)
liszt:updated
scp-long.*tree
formatter.*generic
formatter.*double_line
scp_multiselect
\.chosen_prevSelect_results\(
buttonType.*true
\.data\('treeNodes'\)
$.chosen.formatters.read_only
```

---

## Conversion: steal() → ES imports

```javascript
// MCA1
steal("scp/ui/common/vendor/chosen/chosen.js").then(function() {
  $("#selector").chosen();
});

// MCA2
import { FormItem, FormSelect, Autocomplete, Type } from '@barclays/blueprint-react';
```

---

## Component: Basic Dropdown

### MCA1 Pattern

```html
<select class="scp-long" id="normalSelectId">
  <option>Savings</option>
  <option>Sarah's Account</option>
</select>
```

```javascript
$("#normalSelectId").chosen();
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, FormSelect, Type } from '@barclays/blueprint-react';

export const BasicDropdown: React.FC = () => {
  const [value, setValue] = useState('');

  return (
    <FormItem
      label={<Type>Account Type</Type>}
      render={(props) => (
        <FormSelect {...props} value={value} onChange={(e) => setValue(e.target.value)}>
          <option value="">Select...</option>
          <option value="savings">Savings</option>
          <option value="sarahs">Sarah's Account</option>
        </FormSelect>
      )}
    />
  );
};
```

---

## Component: Searchable Dropdown

### MCA1 Pattern

```javascript
// Chosen provides search by default on all dropdowns
$("#normalSelectId").chosen();
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, Autocomplete, Type } from '@barclays/blueprint-react';

const options = [
  { label: 'Savings', value: 'savings' },
  { label: "Sarah's Account", value: 'sarahs' },
];

export const SearchableDropdown: React.FC = () => {
  const [value, setValue] = useState('');

  return (
    <FormItem
      label={<Type>Account Type</Type>}
      render={(props) => (
        <Autocomplete
          {...props}
          items={options}
          value={value}
          onChange={(val) => setValue(val)}
          placeholder="Search..."
        />
      )}
    />
  );
};
```

---

## Component: Multi-Select Dropdown

### MCA1 Pattern

```html
<select class="scp-long tree extended" id="cnz-multiselect">
  <option value="Select All" level="0">Select All</option>
  <option value="value1" level="1">Task 1</option>
  <option value="value2" level="1">Task 2</option>
</select>
```

```javascript
$("#cnz-multiselect").chosen({
  tree_nodes_listing: { "1": "Task" },
  scp_multiselect: true,
  tree_callback: function(selectedOpts) { console.log(selectedOpts); },
  buttonText: 'Save Checked Items',
  buttonClass: 'secondary'
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, Type, Checkbox, Button, Section, SectionItem } from '@barclays/blueprint-react';

interface MultiSelectOption {
  value: string;
  label: string;
}

const options: MultiSelectOption[] = [
  { value: 'value1', label: 'Task 1' },
  { value: 'value2', label: 'Task 2' },
  { value: 'value3', label: 'Task 3' },
];

export const MultiSelectDropdown: React.FC = () => {
  const [selected, setSelected] = useState<string[]>([]);
  const allSelected = selected.length === options.length;

  const toggleAll = () => {
    setSelected(allSelected ? [] : options.map((o) => o.value));
  };

  const toggleItem = (value: string) => {
    setSelected((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    );
  };

  return (
    <Section>
      <SectionItem>
        <FormItem
          label={<Type>Tasks</Type>}
          render={() => (
            <>
              <Checkbox
                checked={allSelected}
                onChange={toggleAll}
                label="Select All"
              />
              {options.map((opt) => (
                <Checkbox
                  key={opt.value}
                  checked={selected.includes(opt.value)}
                  onChange={() => toggleItem(opt.value)}
                  label={opt.label}
                />
              ))}
              <Button variant="secondary" onClick={() => console.log(selected)}>
                Save Checked Items
              </Button>
            </>
          )}
        />
      </SectionItem>
    </Section>
  );
};
```

---

## Component: Tree Dropdown (Hierarchical)

### MCA1 Pattern

```html
<select class="scp-long tree extended" id="cnz-tree-extanded">
  <option level="1">Area 1</option>
  <option level="2">Community 1</option>
  <option level="3">Site1</option>
  <option level="3">Site2</option>
</select>
```

```javascript
var tree_nodes = { 1: "Area", 2: "Community", 3: "Skills" };
$("#cnz-tree-extanded").chosen({
  tree_nodes_listing: tree_nodes,
  tree_callback: function(container) { console.log(container); },
  buttonText: 'Save Checked Items',
  buttonClass: 'secondary'
});
```

### Blueprint-React Equivalent (Cascading FormSelect)

```typescript
import React, { useState, useMemo } from 'react';
import { FormItem, FormSelect, Type, Section, SectionItem } from '@barclays/blueprint-react';

interface TreeNode {
  value: string;
  label: string;
  level: number;
  parent?: string;
}

const treeData: TreeNode[] = [
  { value: 'area1', label: 'Area 1', level: 1 },
  { value: 'comm1', label: 'Community 1', level: 2, parent: 'area1' },
  { value: 'site1', label: 'Site 1', level: 3, parent: 'comm1' },
  { value: 'site2', label: 'Site 2', level: 3, parent: 'comm1' },
];

export const TreeDropdown: React.FC = () => {
  const [selectedArea, setSelectedArea] = useState('');
  const [selectedCommunity, setSelectedCommunity] = useState('');
  const [selectedSite, setSelectedSite] = useState('');

  const areas = treeData.filter((n) => n.level === 1);
  const communities = useMemo(
    () => treeData.filter((n) => n.level === 2 && n.parent === selectedArea),
    [selectedArea]
  );
  const sites = useMemo(
    () => treeData.filter((n) => n.level === 3 && n.parent === selectedCommunity),
    [selectedCommunity]
  );

  return (
    <Section>
      <SectionItem>
        <FormItem
          label={<Type>Area</Type>}
          render={(props) => (
            <FormSelect {...props} value={selectedArea} onChange={(e) => {
              setSelectedArea(e.target.value);
              setSelectedCommunity('');
              setSelectedSite('');
            }}>
              <option value="">Select Area...</option>
              {areas.map((a) => <option key={a.value} value={a.value}>{a.label}</option>)}
            </FormSelect>
          )}
        />
        {selectedArea && (
          <FormItem
            label={<Type>Community</Type>}
            render={(props) => (
              <FormSelect {...props} value={selectedCommunity} onChange={(e) => {
                setSelectedCommunity(e.target.value);
                setSelectedSite('');
              }}>
                <option value="">Select Community...</option>
                {communities.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
              </FormSelect>
            )}
          />
        )}
        {selectedCommunity && (
          <FormItem
            label={<Type>Site</Type>}
            render={(props) => (
              <FormSelect {...props} value={selectedSite} onChange={(e) => setSelectedSite(e.target.value)}>
                <option value="">Select Site...</option>
                {sites.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </FormSelect>
            )}
          />
        )}
      </SectionItem>
    </Section>
  );
};
```

---

## Component: Multi-Column Dropdown (Single/Double Line)

### MCA1 Pattern

```html
<select id="chosenId">
  <option value="0" data-top="<b>JONATHON SMITH</b><br> INSTANT SAVINGS ACCOUNT"
    data-bottom="20-16-56 <b>00845116</b>" data-additional="£ -1.00">
    JONATHON SMITH INSTANT SAVINGS ACCOUNT
  </option>
</select>
```

```javascript
$("#chosenId").chosen({ formatter: "generic" });    // single line
$("#chosenId2").chosen({ formatter: "double_line" }); // double line
```

### Blueprint-React Equivalent (ComplexDropdown or Custom Autocomplete)

```typescript
import React, { useState } from 'react';
import { FormItem, Autocomplete, Type, Arrange, ArrangeItem } from '@barclays/blueprint-react';

interface AccountOption {
  label: string;
  value: string;
  name: string;
  accountType: string;
  sortCode: string;
  accountNo: string;
  balance: string;
}

const accounts: AccountOption[] = [
  {
    label: 'Jonathon Smith - Instant Savings',
    value: '0',
    name: 'JONATHON SMITH',
    accountType: 'INSTANT SAVINGS ACCOUNT',
    sortCode: '20-16-56',
    accountNo: '00845116',
    balance: '£ -1.00',
  },
];

export const AccountDropdown: React.FC = () => {
  const [value, setValue] = useState('');

  return (
    <FormItem
      label={<Type>Account</Type>}
      render={(props) => (
        <Autocomplete
          {...props}
          items={accounts}
          value={value}
          onChange={(val) => setValue(val)}
          renderItem={(item) => {
            const account = item as AccountOption;
            return (
              <Arrange>
                <ArrangeItem size="fill">
                  <Type weight="medium">{account.name}</Type>
                  <Type size="sm">{account.accountType}</Type>
                  <Type size="sm">{account.sortCode} {account.accountNo}</Type>
                </ArrangeItem>
                <ArrangeItem size="fit">
                  <Type weight="medium">{account.balance}</Type>
                </ArrangeItem>
              </Arrange>
            );
          }}
        />
      )}
    />
  );
};
```

---

## Component: Read-Only Dropdown Display

### MCA1 Pattern

```javascript
var options = {
  "data-top": "<b>JONATHON SMITH</b><br> INSTANT SAVINGS ACCOUNT",
  "data-bottom": "20-16-56 <b>00845116</b>",
  "data-additional": "£-1.00"
};
$("#single_read_only").html($.chosen.formatters.read_only(options));
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Type, Section, SectionItem, Arrange, ArrangeItem } from '@barclays/blueprint-react';

export const ReadOnlyAccount: React.FC = () => (
  <Section>
    <SectionItem>
      <Arrange>
        <ArrangeItem size="fill">
          <Type weight="medium">JONATHON SMITH</Type>
          <Type size="sm">INSTANT SAVINGS ACCOUNT</Type>
          <Type size="sm">20-16-56 00845116</Type>
        </ArrangeItem>
        <ArrangeItem size="fit">
          <Type weight="medium">£-1.00</Type>
        </ArrangeItem>
      </Arrange>
    </SectionItem>
  </Section>
);
```

---

## Component: Button-Style Dropdown

### MCA1 Pattern

```javascript
$("#multiButtonSelectId").chosen({ buttonType: true });
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, FormSelect, Type } from '@barclays/blueprint-react';

export const ActionDropdown: React.FC = () => {
  const [action, setAction] = useState('');

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = e.target.value;
    setAction(selected);
    if (selected) {
      // Execute action immediately
      console.log('Executing:', selected);
    }
  };

  return (
    <FormItem
      label={<Type>Actions</Type>}
      render={(props) => (
        <FormSelect {...props} value={action} onChange={handleChange}>
          <option value="">Select Action</option>
          <option value="ac-1">Action one</option>
          <option value="ac-2">Action two</option>
        </FormSelect>
      )}
    />
  );
};
```

---

## Component: Dropdown with Previously Selected

### MCA1 Pattern

```javascript
var pre_select_data = ['Site1', 'Site2'];
var chnz_pre = $("#preselect_options").chosen({
  preSelect: true,
  preSelectLen: 3,
  preselectarray: pre_select_data
});
var result_array = chnz_pre.chosen_prevSelect_results();
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, Autocomplete, Type } from '@barclays/blueprint-react';

interface DropdownOption {
  label: string;
  value: string;
  group?: string;
}

const allOptions: DropdownOption[] = [
  { label: 'Site1', value: 'site1' },
  { label: 'Site2', value: 'site2' },
  { label: 'Site3', value: 'site3' },
  { label: 'Site4', value: 'site4' },
];

export const RecentSelectDropdown: React.FC = () => {
  const [value, setValue] = useState('');
  const [recentSelections, setRecentSelections] = useState<string[]>(['site1', 'site2']);

  const groupedOptions = [
    ...recentSelections.slice(0, 3).map((v) => ({
      ...allOptions.find((o) => o.value === v)!,
      group: 'Recent',
    })),
    ...allOptions.map((o) => ({ ...o, group: 'All Options' })),
  ];

  const handleChange = (val: string) => {
    setValue(val);
    setRecentSelections((prev) => [val, ...prev.filter((v) => v !== val)].slice(0, 3));
  };

  return (
    <FormItem
      label={<Type>Select Site</Type>}
      render={(props) => (
        <Autocomplete
          {...props}
          items={groupedOptions}
          value={value}
          onChange={handleChange}
        />
      )}
    />
  );
};
```

---

## Variant → Component Mapping Summary

| MCA1 Variant | Detection | Blueprint Component |
|-------------|-----------|-------------------|
| Basic (`.chosen()`) | No special options | `FormSelect` |
| Searchable | `.chosen()` with many options | `Autocomplete` |
| Multi-Select (`scp_multiselect: true`) | `scp_multiselect` option | `Checkbox` group |
| Tree Multi-Select | `tree_nodes_listing` + `scp_multiselect` | Cascading `FormSelect` + `Checkbox` |
| Tree Single-Select | `radio: true` | Cascading `FormSelect` |
| Single-Line Multi-Column | `formatter: "generic"` | `Autocomplete` + `renderItem` |
| Double-Line Multi-Column | `formatter: "double_line"` | `Autocomplete` + `renderItem` |
| Read-Only | `$.chosen.formatters.read_only()` | `Type` + `Arrange` (static display) |
| Button-Style | `buttonType: true` | `FormSelect` with action handler |
| Previous-Select | `preSelect: true` | `Autocomplete` with grouped items |
| Dropdown Menu (tree levels) | `class="scp-long tree"` + `level` attr | Cascading `FormSelect` |

---

## Event Handlers Mapping

| MCA1 Event | React Equivalent | Notes |
|------------|-----------------|-------|
| `tree_callback(selectedOpts)` | `onChange` + state update | Collect selections via state |
| `"liszt:updated"` trigger | Re-render via state change | React handles DOM updates |
| `.chosen_prevSelect_results()` | Read from state directly | `recentSelections` array |
| `addManualItem_callback` | Custom button + text input | Add to options state |

---

## Iron Rules

1. **Simple dropdowns → `FormSelect`** — don't use Autocomplete for basic select-one-of-few scenarios
2. **Searchable / multi-column → `Autocomplete`** — use `renderItem` for custom display
3. **Tree hierarchies → cascading `FormSelect`** — one per level, child resets when parent changes
4. **Multi-select → `Checkbox` group** — NOT a multi-select `<select>` element
5. **`data-top`/`data-bottom`/`data-additional` → structured object + `renderItem`** — never inject HTML strings
6. **`level` attribute → parent-child data model** — flatten tree into objects with `parent` references
7. **Always wrap in `FormItem` with `render` prop** — never use children pattern
