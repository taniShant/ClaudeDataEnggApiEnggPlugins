# BDL_TIME_MAPPING.md

## Overview

The `<mca-time>` component is **DEPRECATED** in MCA1. The official BDL documentation states:

> "This is DEPRECATED. Please use combobox component with `template="timepicker"`."

This file documents the deprecated pattern and redirects to the correct mapping.

---

## MCA1 Pattern (DEPRECATED)

```html
<mca-time
  value=""
  disabled="no"
  placeholder=""
  title=""
  label-columns="2"
  input-columns="2"
  input-width="auto"
  id="timeField"
  input-class=""
  name=""
  label-id=""
  label-class=""
  tabindex=""
  required="no"
>
  Time Label
</mca-time>
```

### Attributes

| Attribute | Values | Default | Description |
|-----------|--------|---------|-------------|
| `value` | string | — | Pre-set time value |
| `disabled` | `yes` / `no` | `no` | Disable the input |
| `placeholder` | string | — | Placeholder text |
| `title` | string | — | HTML title attribute |
| `label-columns` | 0–8 | 2 | Grid width of label |
| `input-columns` | 1–8 | 2 | Grid width of input |
| `input-width` | `auto`/`short`/`medium`/`long` | `auto` | Input size |
| `id` | string (MANDATORY) | — | Element ID |
| `required` | `yes` / `no` | `no` | Required field |

---

## Migration Path

### If encountered in MCA1 code:

The `<mca-time>` component renders as a time-picker dropdown. Migrate using the **same pattern as `<mca-combobox template="timepicker">`**.

**See: [BDL_COMBOBOX_MAPPING.md](./BDL_COMBOBOX_MAPPING.md)** — Section "Template: timepicker"

---

## Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { FormItem, FormSelect, Type } from '@barclays/blueprint-react';

const timeOptions = generateTimeOptions(); // 00:00, 00:15, 00:30, ... 23:45

export const TimePickerField: React.FC = () => {
  const [selectedTime, setSelectedTime] = useState('');

  return (
    <FormItem
      label={<Type>Time Label</Type>}
      render={(props) => (
        <FormSelect
          {...props}
          value={selectedTime}
          onChange={(e) => setSelectedTime(e.target.value)}
        >
          <option value="">Select time</option>
          {timeOptions.map((time) => (
            <option key={time} value={time}>{time}</option>
          ))}
        </FormSelect>
      )}
    />
  );
};

function generateTimeOptions(): string[] {
  const times: string[] = [];
  for (let h = 0; h < 24; h++) {
    for (let m = 0; m < 60; m += 15) {
      times.push(`${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`);
    }
  }
  return times;
}
```

---

## Attribute Mapping

| MCA1 Attribute | Blueprint Equivalent | Notes |
|----------------|---------------------|-------|
| `value` | `value` state + `onChange` | Controlled component |
| `disabled` | `disabled` prop on `FormSelect` | Boolean in React |
| `label-columns` | Not needed | Blueprint handles responsive layout |
| `input-columns` | Not needed | Blueprint handles responsive layout |
| `required` | Yup `.required()` in validation schema | Schema-driven |
| Content (label text) | `label` prop on `FormItem` | Wrap in `<Type>` |

---

## Iron Rules

1. **`<mca-time>` is deprecated** — if you encounter it, treat it exactly like `<mca-combobox template="timepicker">`
2. **Use `FormSelect` with generated time options** — NOT a text input with type="time"
3. **Follow the standard FormItem render function pattern** — see `BDL_COMBOBOX_MAPPING.md`
