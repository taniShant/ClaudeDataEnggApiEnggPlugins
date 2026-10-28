# LEGACY_AUTOCOMPLETE_MAPPING.md

## Overview

Maps MCA1 legacy autocomplete components (`.scpAutoComplete()` jQuery plugin) to Blueprint-React `Autocomplete` component. Covers both basic autocomplete and custom item builder variants.

---

## Detection Patterns

```grep
\.scpAutoComplete\(
steal\("scp/ui/common/vendor/autocomplete/scpautocomplete\.js"\)
```

---

## Conversion: steal() → ES imports

```javascript
// MCA1
steal("scp/ui/common/vendor/autocomplete/scpautocomplete.js").then(function() {
  $("#input").scpAutoComplete({ source: [...] });
});

// MCA2
import { Autocomplete } from '@barclays/blueprint-react';
```

---

## Component: Basic Autocomplete

### MCA1 Pattern (jQuery)

```html
<label for="AutoComplete0" class="scp-label two-columns">Scripting languages</label>
<input type="text" class="scp-input-text two-columns" name="AutoComplete0" placeholder="Type Java" value="" id="AutoComplete0">
```

```javascript
$("#AutoComplete0").scpAutoComplete({
  minLength: 1,
  source: ["ActionScript", "AppleScript", "Java", "JavaScript", "Lisp", "Perl", "PHP"]
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, Autocomplete, Type } from '@barclays/blueprint-react';

const languages = [
  { label: 'ActionScript', value: 'actionscript' },
  { label: 'AppleScript', value: 'applescript' },
  { label: 'Java', value: 'java' },
  { label: 'JavaScript', value: 'javascript' },
  { label: 'Lisp', value: 'lisp' },
  { label: 'Perl', value: 'perl' },
  { label: 'PHP', value: 'php' },
];

export const LanguageAutocomplete: React.FC = () => {
  const [value, setValue] = useState('');

  return (
    <FormItem
      label={<Type>Scripting languages</Type>}
      render={(props) => (
        <Autocomplete
          {...props}
          items={languages}
          value={value}
          onChange={(val) => setValue(val)}
          placeholder="Type Java"
        />
      )}
    />
  );
};
```

### Options → Props Mapping

| MCA1 Option | Blueprint Prop | Notes |
|-------------|---------------|-------|
| `source` (array of strings) | `items` (array of `{label, value}`) | Transform flat strings to objects |
| `source` (function) | `onSearch` callback or filtered `items` | Use `useState` + filter logic |
| `minLength` | `minChars` or filter in `onSearch` | Control when suggestions appear |
| `select` callback | `onChange` prop | Fires when item selected |

---

## Component: Autocomplete with Custom Item Builder

### MCA1 Pattern (jQuery)

```javascript
$("#AutoComplete1").scpAutoComplete({
  minLength: 3,
  source: ["British Telecom Pager-#####", "British Gas Cardiff-100##########"],
  itemBuilder: function(ul, item) {
    var items = item.label.split("-");
    if (items && items[0] && items[1]) {
      return '<div class="clearfix"><div style="float:left">' + items[0] + '</div>'
        + '<div style="float:right">' + items[1] + '</div></div>';
    }
    return '';
  }
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState, useMemo } from 'react';
import { FormItem, Autocomplete, Type, Arrange, ArrangeItem } from '@barclays/blueprint-react';

interface AccountItem {
  label: string;
  value: string;
  name: string;
  accountNumber: string;
}

const accounts: AccountItem[] = [
  { label: 'British Telecom Pager - #####', value: 'bt', name: 'British Telecom Pager', accountNumber: '#####' },
  { label: 'British Gas Cardiff - 100##########', value: 'bg', name: 'British Gas Cardiff', accountNumber: '100##########' },
];

export const AccountAutocomplete: React.FC = () => {
  const [value, setValue] = useState('');
  const [query, setQuery] = useState('');

  const filtered = useMemo(() => {
    if (query.length < 3) return [];
    return accounts.filter((a) => a.name.toLowerCase().includes(query.toLowerCase()));
  }, [query]);

  return (
    <FormItem
      label={<Type>Account Search</Type>}
      render={(props) => (
        <Autocomplete
          {...props}
          items={filtered}
          value={value}
          onChange={(val) => setValue(val)}
          onInputChange={(val) => setQuery(val)}
          renderItem={(item) => (
            <Arrange>
              <ArrangeItem size="fill">
                <Type>{(item as AccountItem).name}</Type>
              </ArrangeItem>
              <ArrangeItem size="fit">
                <Type weight="medium">{(item as AccountItem).accountNumber}</Type>
              </ArrangeItem>
            </Arrange>
          )}
        />
      )}
    />
  );
};
```

### Options → Props Mapping (Custom)

| MCA1 Option | Blueprint Prop | Notes |
|-------------|---------------|-------|
| `itemBuilder` function | `renderItem` prop | Custom render per suggestion |
| `source` as function | `onInputChange` + filtered state | Manual filtering with useState |
| `select` callback | `onChange` prop | Fires with selected value |

---

## Event Handlers Mapping

| MCA1 Event | React Equivalent | Notes |
|------------|-----------------|-------|
| `select: function(event, ui)` | `onChange={(value) => ...}` | `ui.item.label` → value parameter |
| Implicit blur/focus | `onBlur`, `onFocus` props | Standard React events |

---

## Iron Rules

1. **Transform flat string arrays to `{label, value}` objects** — Autocomplete expects structured items, not plain strings
2. **Use `renderItem` for custom templates** — never inject raw HTML; use Blueprint layout components (`Arrange`, `Type`)
3. **Use `FormItem` render prop pattern** — never wrap Autocomplete as children of FormItem
4. **Filter logic goes in component state** — use `useMemo` with a query string, not a source callback
5. **`minLength` → check query length before filtering** — return empty array when below threshold
