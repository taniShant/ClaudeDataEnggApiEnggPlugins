# BDL Stepper to Blueprint-React Mapping

**Last Updated**: April 24, 2026

---

## Stepper (`<mca-stepper>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-stepper>` | `<NumberStepper>` |
| `<mca-stepper datatype="time">` | `<NumberStepper>` with custom `formatter` for HH:MM |
| `<mca-stepper datatype="number">` | `<NumberStepper>` (default behaviour) |

**Note**: BDL's `<mca-stepper>` supports both numeric and time modes via the `datatype` attribute. Blueprint-React's `<NumberStepper>` is purely numeric but accepts a `formatter` prop to display values in any format, including time (HH:MM).

---

### Basic Number Stepper

**MCA1 (Before)**:
```html
<mca-stepper id="s_basic" value="50" min="0" max="100" step="1">
</mca-stepper>
```

**Blueprint-React (After)**:
```typescript
import { NumberStepper } from "@barclays/blueprint-react";

const [value, setValue] = useState<number>(50);

<NumberStepper
  id="s_basic"
  value={value}
  min={0}
  max={100}
  step={1}
  onChange={(e) => setValue(Number(e.target.value))}
/>
```

---

### Stepper with Min/Max Bounds

BDL uses `min` and `max` as string attributes with integer validation. Blueprint-React uses the same native `min` and `max` props inherited from `<input>`.

**MCA1 (Before)**:
```html
<mca-stepper id="s_bounds" value="25" min="10" max="50" step="5">
</mca-stepper>
```

**Blueprint-React (After)**:
```typescript
const [value, setValue] = useState<number>(25);

<NumberStepper
  id="s_bounds"
  value={value}
  min={10}
  max={50}
  step={5}
  onChange={(e) => setValue(Number(e.target.value))}
/>
```

---

### Stepper with Custom Step Value

BDL's `step` attribute (default: 10) maps directly to Blueprint-React's `step` prop (default: 1). Note the different defaults.

**MCA1 (Before)**:
```html
<mca-stepper id="s_step" value="0" min="0" max="100" step="10">
</mca-stepper>
```

**Blueprint-React (After)**:
```typescript
const [value, setValue] = useState<number>(0);

<NumberStepper
  id="s_step"
  value={value}
  min={0}
  max={100}
  step={10}
  onChange={(e) => setValue(Number(e.target.value))}
/>
```

**Note**: BDL defaults `step` to `10` while Blueprint-React defaults `step` to `1`. Always explicitly set `step` to preserve the original behaviour.

---

### Disabled Stepper

**MCA1 (Before)**:
```html
<mca-stepper id="s_disabled" value="30" min="0" max="100" disabled="yes">
</mca-stepper>
```

**Blueprint-React (After)**:
```typescript
<NumberStepper
  id="s_disabled"
  value={30}
  min={0}
  max={100}
  step={1}
  disabled
/>
```

---

### Time Stepper Pattern

BDL's `datatype="time"` creates a stepper that operates in minutes (0-1440) and displays output in "HH:MM" format. Blueprint-React has no dedicated time stepper — use `<NumberStepper>` with a custom `formatter` prop.

**MCA1 (Before)**:
```html
<mca-stepper id="s_time" datatype="time" value="90" step="15" min="0" max="1440">
</mca-stepper>
<!-- Displays: 01:30 (90 minutes = 1 hour 30 minutes) -->
```

**Blueprint-React (After)**:
```typescript
import { NumberStepper } from "@barclays/blueprint-react";

const formatMinutesToTime = (minutes: number): string => {
  const hrs = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hrs).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
};

const [value, setValue] = useState<number>(90);

<NumberStepper
  id="s_time"
  value={value}
  min={0}
  max={1440}
  step={15}
  formatter={formatMinutesToTime}
  onChange={(e) => setValue(Number(e.target.value))}
/>
// Displays: 01:30
```

**Key differences**:
- BDL's time mode defaults to `min=0` and `max=1440` (24 hours in minutes). Explicitly set these on `<NumberStepper>`.
- The `formatter` prop controls display only — the underlying value remains a number (minutes).
- BDL's `format()` API method is replaced by the `formatter` prop.

---

### Stepper Inside FormItem (with Label and Error Handling)

BDL's `label` and `required` attributes are handled by wrapping `<NumberStepper>` inside a `<FormItem>`.

**MCA1 (Before)**:
```html
<mca-stepper id="s_form" label="Quantity" required="yes" value="1" min="1" max="99" step="1">
</mca-stepper>
```

**Blueprint-React (After)**:
```typescript
import { FormItem, NumberStepper, Type } from "@barclays/blueprint-react";

const [value, setValue] = useState<number>(1);
const [error, setError] = useState<string>("");

const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  const newValue = Number(e.target.value);
  setValue(newValue);
  if (newValue < 1 || newValue > 99) {
    setError("Quantity must be between 1 and 99");
  } else {
    setError("");
  }
};

<FormItem
  label={<Type>Quantity</Type>}
  htmlFor="s_form"
  render={(renderProps) => (
    <NumberStepper
      id="s_form"
      value={value}
      min={1}
      max={99}
      step={1}
      required
      aria-invalid={!!error}
      onChange={handleChange}
      {...renderProps}
    />
  )}
  errorText={error || undefined}
/>
```

**Note**: BDL's `label` attribute is replaced by `<FormItem>`'s `label` prop. BDL's `required="yes"` maps to the native `required` prop on `<NumberStepper>`. Error display is handled by `<FormItem>`'s `errorText` prop, not by the stepper itself.

---

### Stepper with Custom Accessibility Labels

Blueprint-React's `<NumberStepper>` supports `incrementLabel` and `decrementLabel` for screen reader text on the +/- buttons. BDL has no equivalent — these are additive improvements.

```typescript
<NumberStepper
  id="s_accessible"
  value={value}
  min={0}
  max={100}
  step={1}
  incrementLabel="Increase quantity"
  decrementLabel="Decrease quantity"
  onChange={(e) => setValue(Number(e.target.value))}
/>
```

---

## BDL API Methods to React Patterns

BDL's `<mca-stepper>` exposes imperative API methods. In React, these are replaced by state and props.

| MCA1 API Method | React Equivalent | Notes |
|---|---|---|
| `getValue()` | Read `value` from state | `const [value, setValue] = useState(...)` |
| `setValue(v)` | Call `setValue(v)` | State setter from `useState` |
| `disable(bool)` | `disabled` prop | `<NumberStepper disabled={isDisabled} />` |
| `changed(callback)` | `onChange` prop | `<NumberStepper onChange={handleChange} />` |
| `format()` | `formatter` prop | `<NumberStepper formatter={(v) => formatFn(v)} />` |

---

## Complete `<mca-stepper>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `NumberStepper` | Mandatory unique identifier |
| `class` | `className` | N/A | `NumberStepper` extends `Omit<ComponentPropsWithoutRef<"input">, "size" \| "className">` — use wrapper `<div>` for custom classes |
| `value` | `value` | `NumberStepper` | Controlled via `useState`; pass as number |
| `min` | `min` | `NumberStepper` | Inherited from native `<input>` |
| `max` | `max` | `NumberStepper` | Inherited from native `<input>` |
| `step` | `step` | `NumberStepper` | BDL default: `10`; Blueprint-React default: `1` — always set explicitly |
| `name` | `name` | `NumberStepper` | Form field name; inherited from native `<input>` |
| `tabindex` | `tabIndex` | `NumberStepper` | camelCase in React |
| `disabled="yes"` | `disabled` | `NumberStepper` | Boolean prop |
| `label` | `label` | `FormItem` wrapper | Wrap in `<FormItem>` — not a `NumberStepper` prop |
| `required="yes"` | `required` | `NumberStepper` | Boolean prop; also set on `<FormItem>` for visual indicator |
| `datatype="number"` | (default behaviour) | N/A | `<NumberStepper>` is numeric by default |
| `datatype="time"` | `formatter` prop | `NumberStepper` | Use custom formatter for HH:MM display; see Time Stepper Pattern |

### Required Imports

```typescript
import { NumberStepper } from "@barclays/blueprint-react";
// For form wrapping:
import { FormItem, Type } from "@barclays/blueprint-react";
```

### Migration Checklist

- [ ] Replace `<mca-stepper>` with `<NumberStepper>`
- [ ] Convert `value`, `min`, `max`, `step` from string attributes to number props
- [ ] Explicitly set `step` (BDL defaults to `10`, Blueprint-React defaults to `1`)
- [ ] Convert `disabled="yes"` to boolean `disabled` prop
- [ ] For `datatype="time"`, add a `formatter` function for HH:MM display
- [ ] For time steppers, explicitly set `min={0}` and `max={1440}`
- [ ] Wrap in `<FormItem>` if `label` or `required` attributes are present
- [ ] Replace imperative API calls (`getValue`, `setValue`, `changed`) with React state and props
- [ ] Add `onChange` handler to keep component controlled
