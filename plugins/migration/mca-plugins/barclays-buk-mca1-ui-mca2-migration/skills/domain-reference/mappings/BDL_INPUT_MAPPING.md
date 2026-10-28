# BDL Input Mapping: `<mca-input>` → `<FormItem>` + `<FormInput>`

**Last Updated**: April 16, 2026

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-input>` | `<FormItem>` + `<FormInput>` |

**Critical Pattern**: All form fields in Blueprint-React must be wrapped in `<FormItem>` with a `render` function. Do NOT use children wrapping.

---

## Basic Text Field

**MCA1 (Before)**:
```html
<mca-input id="b_input_default">
    Text Field &amp; Single Line
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Text Field & Single Line"
  id="b_input_default"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_default"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Small / Compact Variant

**MCA1 (Before)**:
```html
<mca-input id="b_input_smaller" small="yes">
    Smaller Text Field &amp; Single Line
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Smaller Text Field & Single Line"
  id="b_input_smaller"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_smaller"
      size="sm"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Read Only

**MCA1 (Before)**:
```html
<mca-input id="b_input_readonly" readonly="yes" value="Read only">
    Text Field Read Only
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Text Field Read Only"
  id="b_input_readonly"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_readonly"
      readOnly
      value="Read only"
    />
  )}
/>
```

---

## Disabled

**MCA1 (Before)**:
```html
<mca-input id="b_input_disabled" disabled="yes" value="Disabled">
    Text Field Disabled
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Text Field Disabled"
  id="b_input_disabled"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_disabled"
      disabled
      value="Disabled"
    />
  )}
/>
```

---

## Password

**MCA1 (Before)**:
```html
<mca-input id="b_input_password" type="password">
    Password Field
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Password Field"
  id="b_input_password"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_password"
      type="password"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Email

**MCA1 (Before)**:
```html
<mca-input id="b_input_email" type="email">
    Email Field
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Email Field"
  id="b_input_email"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_email"
      type="email"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Required Field

The `required="yes"` attribute does not map to a direct `FormInput` prop. Use Yup schema validation and pass the error state to `FormItem`.

**MCA1 (Before)**:
```html
<mca-input id="b_input_required" required="yes">
    Required Field
</mca-input>
```

**Blueprint-React (After)**:
```typescript
// Yup validation schema
const schema = yup.object({
  b_input_required: yup.string().required('This field is required'),
});

// Component
<FormItem
  label="Required Field"
  id="b_input_required"
  error={errors.b_input_required && <Type color="error">{errors.b_input_required}</Type>}
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_required"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Symbol (Left / Right)

MCA1 supports a `symbol` attribute with a `position` to render a currency symbol (e.g. `£`, `$`) beside the input. Blueprint-React `FormInput` has native `affix` and `affixPosition` props for this — use them directly instead of Arrange wrappers.

**MCA1 (Before)**:
```html
<mca-input id="b_input_symbol_left" type="text" symbol="£" position="left">
    Text Field Symbol (left)
</mca-input>

<mca-input id="b_input_symbol_right" type="text" symbol="£" position="right">
    Text Field Symbol (Right)
</mca-input>
```

**Blueprint-React (After)**:
```typescript
{/* Symbol on the left — use affix + affixPosition="start" */}
<FormItem
  label={<Type>Text Field Symbol (left)</Type>}
  id="b_input_symbol_left"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_symbol_left"
      affix="£"
      affixPosition="start"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>

{/* Symbol on the right — use affix + affixPosition="end" */}
<FormItem
  label={<Type>Text Field Symbol (Right)</Type>}
  id="b_input_symbol_right"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_symbol_right"
      affix="£"
      affixPosition="end"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

**IMPORTANT**: If the MCA1 source shows a `£` or other currency symbol on an amount/payment input, the MCA2 output MUST preserve it using `affix`. Do NOT omit the symbol — it is critical for user experience on payment forms.

---

## Currency Code Symbol

**MCA1 (Before)**:
```html
<mca-input id="b_input_currencycode_symbol_left" type="text" symbol="GBP"
    currency-code="yes" position="left">
    Text Field Currency code Symbol (left)
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label={<Type>Text Field Currency code Symbol (left)</Type>}
  id="b_input_currencycode_symbol_left"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_currencycode_symbol_left"
      affix="GBP"
      affixPosition="start"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Currency Code with Flag

MCA1's `icon="GB"` renders a country flag alongside the currency symbol. Blueprint-React has no built-in flag icon; use `NumericFormat` with `prefix` set to the currency text (flag is omitted unless a custom image is available).

**MCA1 (Before)**:
```html
<mca-input id="b_input_currency_flag" icon="GB" type="money" symbol="GBP £"
    currency-code="yes" precision="3">
    Currency code and Flag
</mca-input>
```

**Blueprint-React (After)**:
```typescript
import { NumericFormat } from 'react-number-format';

<FormItem
  label={<Type>Currency code and Flag</Type>}
  id="b_input_currency_flag"
  render={(props) => (
    <NumericFormat
      customInput={FormInput}
      {...props}
      name="b_input_currency_flag"
      thousandSeparator=","
      decimalSeparator="."
      prefix="GBP £"
      decimalScale={3}
      fixedDecimalScale
      allowNegative={false}
      value={value}
      onValueChange={(values) => setValue(values.value)}
    />
  )}
/>
```

---

## Number Field with Icon

MCA1 `icon` attribute maps to the `media` and `mediaPosition` props on `FormInput`.

**MCA1 (Before)**:
```html
<mca-input id="b_input_icon_left" type="number" icon="facebook" position="left" maxlength="5">
    Number Field Icon (Left)
</mca-input>

<mca-input id="b_input_icon_right" type="number" icon="facebook" position="right">
    Number Field Icon (Right)
</mca-input>
```

**Blueprint-React (After)**:
```typescript
{/* Icon on the left — use media + mediaPosition="start" */}
<FormItem
  label={<Type>Number Field Icon (Left)</Type>}
  id="b_input_icon_left"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_icon_left"
      type="text"
      inputMode="numeric"
      maxLength={5}
      media={<Icon icon="chevron-right" size="sm" />}
      mediaPosition="start"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>

{/* Icon on the right — use media + mediaPosition="end" */}
<FormItem
  label={<Type>Number Field Icon (Right)</Type>}
  id="b_input_icon_right"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_icon_right"
      type="text"
      inputMode="numeric"
      media={<Icon icon="chevron-right" size="sm" />}
      mediaPosition="end"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

**Note**: MCA1 icon names (e.g. `facebook`) won't exist in Blueprint. Map to the closest available Blueprint icon or omit if purely decorative.

---

## Money, Money-Mask, and Money-Unformat

MCA1 provides specialised `type="money"`, `type="money-mask"`, and `type="money-unformat"` fields with built-in formatting. Blueprint-React has no native money input. Use `NumericFormat` from the `react-number-format` library with `customInput={FormInput}` — this handles thousand separators, decimal precision, prefix/suffix, and digit limits natively with no custom formatting logic needed.

#### Package: `react-number-format`

- Open-source, available on npm
- Install: `npm install react-number-format`
- Import: `import { NumericFormat } from 'react-number-format'`

**CRITICAL**: If the MCA1 source has a currency symbol visible (e.g. `symbol="£"` or `symbol="GBP £"`), you MUST add `prefix="£"` to the `NumericFormat`. Do NOT use the FormInput `affix` prop when using NumericFormat — the prefix/suffix is handled by NumericFormat itself. Using both would double-render the symbol.

**MCA1 (Before)**:
```html
<mca-input id="b_input_money" type="money" symbol="£" position="left">
    Money Field
</mca-input>

<mca-input id="b_input_money-mask" type="money-mask">
    Money Mask - adds digits right to left
</mca-input>

<mca-input id="b_input_money_maxdigits" type="money" maxdigits="7" symbol="£" position="left">
    Money Field maxdigits
</mca-input>

<mca-input id="b_input_money_unformat" type="money-unformat" maxdigits="5" precision="4">
    Money Unformat Field with 4 decimals precision
</mca-input>
```

**Blueprint-React (After)**:
```typescript
import { NumericFormat } from 'react-number-format';
import { FormItem, FormInput, Type } from '@barclays/blueprint-react';

// Money field — with £ symbol via prefix
<FormItem
  label={<Type>Money Field</Type>}
  id="b_input_money"
  render={(props) => (
    <NumericFormat
      customInput={FormInput}
      {...props}
      name="b_input_money"
      thousandSeparator=","
      decimalSeparator="."
      prefix="£"
      decimalScale={2}
      fixedDecimalScale
      allowNegative={false}
      value={moneyValue}
      onValueChange={(values) => setMoneyValue(values.value)}
    />
  )}
/>

// Money mask (right-to-left digit entry) — same NumericFormat, value updates live
<FormItem
  label={<Type>Money Mask - adds digits right to left</Type>}
  id="b_input_money-mask"
  render={(props) => (
    <NumericFormat
      customInput={FormInput}
      {...props}
      name="b_input_money-mask"
      thousandSeparator=","
      decimalSeparator="."
      decimalScale={2}
      fixedDecimalScale
      allowNegative={false}
      value={moneyMaskValue}
      onValueChange={(values) => setMoneyMaskValue(values.value)}
    />
  )}
/>

// Money with maxdigits — use isAllowed to limit whole digits to 7
<FormItem
  label={<Type>Money Field maxdigits</Type>}
  id="b_input_money_maxdigits"
  render={(props) => (
    <NumericFormat
      customInput={FormInput}
      {...props}
      name="b_input_money_maxdigits"
      thousandSeparator=","
      decimalSeparator="."
      prefix="£"
      decimalScale={2}
      fixedDecimalScale
      allowNegative={false}
      isAllowed={(values) => {
        const { floatValue } = values;
        // maxdigits="7" means max 7 digits before decimal (max value 9,999,999.99)
        return floatValue === undefined || floatValue <= 9999999.99;
      }}
      value={moneyValue}
      onValueChange={(values) => setMoneyValue(values.value)}
    />
  )}
/>

// Money unformat with custom precision (4 decimals, maxdigits 5)
<FormItem
  label={<Type>Money Unformat Field with 4 decimals precision</Type>}
  id="b_input_money_unformat"
  render={(props) => (
    <NumericFormat
      customInput={FormInput}
      {...props}
      name="b_input_money_unformat"
      thousandSeparator=","
      decimalSeparator="."
      decimalScale={4}
      fixedDecimalScale
      allowNegative={false}
      isAllowed={(values) => {
        const { floatValue } = values;
        return floatValue === undefined || floatValue <= 99999.9999;
      }}
      value={unformatValue}
      onValueChange={(values) => setUnformatValue(values.value)}
    />
  )}
/>
```

**Key `NumericFormat` props for money migration:**

| NumericFormat Prop | Purpose | Notes |
|---|---|---|
| `customInput={FormInput}` | Renders as Blueprint FormInput | Preserves all Blueprint styling and props |
| `thousandSeparator=","` | Formats thousands with commas | `1234` → `1,234` |
| `decimalSeparator="."` | Decimal point character | Standard UK/US format |
| `prefix="£"` | Currency symbol on the left | Replaces MCA1 `symbol` + `position="left"` |
| `suffix="£"` | Currency symbol on the right | Replaces MCA1 `symbol` + `position="right"` |
| `decimalScale={2}` | Number of decimal places | Maps from MCA1 `precision` attribute |
| `fixedDecimalScale` | Always show trailing zeros | `1` → `1.00` |
| `allowNegative={false}` | Prevent negative values | Standard for money inputs |
| `isAllowed` | Custom validation callback | Replaces MCA1 `maxdigits` — limit the max value |
| `onValueChange` | Value change callback | Use `values.value` (unformatted string) for state |
| `value` | Controlled value | Store unformatted numeric string in state |

**Important notes:**
- Use `onValueChange` (NOT `onChange`) to get the unformatted numeric value via `values.value`
- The `values` object also provides `values.formattedValue` (display string) and `values.floatValue` (number)
- Do NOT use FormInput's `affix` prop together with NumericFormat's `prefix`/`suffix` — they serve the same purpose
- Do NOT create a custom `formatMoney()` utility — NumericFormat handles all formatting live as the user types

---

## Description and Help

MCA1 `description` renders helper text below the input. MCA1 `help` renders an info icon that shows help text on click. In Blueprint-React, use the `description` prop on `FormItem` for helper text, and a `<PopupNav>` triggered by an info icon for help behaviour (Blueprint does NOT have a Tooltip component).

**MCA1 (Before)**:
```html
<mca-input id="b_input_description" description="Description text for this input">
    Input With Description
</mca-input>

<mca-input id="b_input_help"
    help="A date in the future on which you would like the payment to be made. Format : DD/MM/YYYY">
    With Help Icon
</mca-input>

<mca-input id="b_input_description-icon"
    description="Description text for this input" description-icon="info">
    Input With Description
</mca-input>
```

**Blueprint-React (After)**:
```typescript
{/* Description text below input */}
<FormItem
  label="Input With Description"
  id="b_input_description"
  description="Description text for this input"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_description"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>

{/* Help icon - use PopupNav (Blueprint has NO Tooltip component) */}
<FormItem
  label={
    <Arrange gap="fixed" align="center">
      <ArrangeItem size="fit">
        <Type element="span">With Help Icon</Type>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button
          variant="subtle"
          ref={helpRef}
          onClick={() => setHelpOpen(!helpOpen)}
          media={<Icon icon="info" size="sm" />}
          aria-label="Help"
        />
        {helpOpen && (
          <PopupNav
            triggerRef={helpRef}
            onClose={() => setHelpOpen(false)}
            placement="bottom left"
            ariaLabelText="Help information"
          >
            <Type>A date in the future on which you would like the payment to be made. Format : DD/MM/YYYY</Type>
          </PopupNav>
        )}
      </ArrangeItem>
    </Arrange>
  }
  id="b_input_help"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_help"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>

{/* Description with icon */}
<FormItem
  label="Input With Description"
  id="b_input_description-icon"
  description={
    <Arrange gap="fixed" align="center">
      <ArrangeItem size="fit">
        <Icon icon="info" size="sm" />
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Type element="span">Description text for this input</Type>
      </ArrangeItem>
    </Arrange>
  }
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_description-icon"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

**Note**: Blueprint-React does NOT have a `Tooltip` component. For help icons, use `<PopupNav>` with a click trigger (info icon button). For simple hover hints, use the native HTML `title` attribute. See [BDL_POPOVER_MAPPING.md](BDL_POPOVER_MAPPING.md) for full PopupNav patterns.

---

## Telephone

**MCA1 (Before)**:
```html
<mca-input id="b_input_telephone" type="tel">
    Telephone
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Telephone"
  id="b_input_telephone"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_telephone"
      type="tel"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Security Code

**MCA1 (Before)**:
```html
<mca-input id="b_input_security-code" type="security-code" maxlength="3">
    Card Security Code Input
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Card Security Code Input"
  id="b_input_security-code"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_security-code"
      type="password"
      inputMode="numeric"
      maxLength={3}
      value={value}
      onChange={(e) => {
        const val = e.target.value.replace(/[^0-9]/g, '');
        if (val.length <= 3) setValue(val);
      }}
    />
  )}
/>
```

---

## Month / Expiry Date (Native)

**MCA1 (Before)**:
```html
<mca-input id="b_input_month" type="month">
    Expiry Date / Native input
</mca-input>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Expiry Date / Native input"
  id="b_input_month"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_month"
      type="month"
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

---

## Pattern Mask (Input Validation)

MCA1 uses `pattern-mask` for regex-based input restriction. In Blueprint-React, implement this as custom `onChange` validation and/or a Yup schema.

**MCA1 (Before)**:
```html
<mca-input id="b_input_number_pattern_mask" type="number" pattern-mask="[0-9]*">
    Numeric Field With Pattern Mask (e.g. Float Value)
</mca-input>

<mca-input id="b_input_password_pattern_mask" type="password" pattern-mask="^[0-9]{0,6}$">
    Password With Pattern Mask (e.g. Passcode)
</mca-input>

<mca-input id="b_input_integer_pattern_mask" type="number" pattern-mask="^\d+$">
    Numeric Field With Pattern Mask (e.g. Integer Value)
</mca-input>
```

**Blueprint-React (After)**:
```typescript
// Helper: restrict input to a regex pattern
const handlePatternChange = (
  e: React.ChangeEvent<HTMLInputElement>,
  pattern: RegExp,
  setter: (val: string) => void
) => {
  const val = e.target.value;
  if (val === '' || pattern.test(val)) {
    setter(val);
  }
};

// Numeric (float values)
<FormItem
  label="Numeric Field With Pattern Mask (e.g. Float Value)"
  id="b_input_number_pattern_mask"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_number_pattern_mask"
      type="text"
      inputMode="numeric"
      value={numericValue}
      onChange={(e) => handlePatternChange(e, /^[0-9]*$/, setNumericValue)}
    />
  )}
/>

// Passcode (max 6 digits, masked)
<FormItem
  label="Password With Pattern Mask (e.g. Passcode)"
  id="b_input_password_pattern_mask"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_password_pattern_mask"
      type="password"
      inputMode="numeric"
      maxLength={6}
      value={passcodeValue}
      onChange={(e) => handlePatternChange(e, /^[0-9]{0,6}$/, setPasscodeValue)}
    />
  )}
/>

// Integer only
<FormItem
  label="Numeric Field With Pattern Mask (e.g. Integer Value)"
  id="b_input_integer_pattern_mask"
  render={(props) => (
    <FormInput
      {...props}
      name="b_input_integer_pattern_mask"
      type="text"
      inputMode="numeric"
      value={integerValue}
      onChange={(e) => handlePatternChange(e, /^\d*$/, setIntegerValue)}
    />
  )}
/>
```

---

## Complete `<mca-input>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormItem` | |
| `name` | `name` | `FormInput` | |
| Text content / `aria-label` | `label` | `FormItem` | |
| `placeholder` | `placeholder` | `FormInput` | |
| `value` | `value` | `FormInput` | Controlled component |
| `type="text"` | `type="text"` | `FormInput` | Default |
| `type="password"` | `type="password"` | `FormInput` | |
| `type="email"` | `type="email"` | `FormInput` | |
| `type="tel"` | `type="tel"` | `FormInput` | |
| `type="number"` | `type="text"` + `inputMode="numeric"` | `FormInput` | Use text + inputMode for better control |
| `type="month"` | `type="month"` | `FormInput` | Native browser month picker |
| `type="money"` | `NumericFormat` with `customInput={FormInput}` | `react-number-format` | `prefix="£"` + `decimalScale={2}` + `fixedDecimalScale` |
| `type="money-mask"` | `NumericFormat` with `customInput={FormInput}` | `react-number-format` | Same as money — live formatting handles right-to-left entry |
| `type="money-unformat"` | `NumericFormat` with `customInput={FormInput}` | `react-number-format` | `decimalScale={N}` from `precision` attribute |
| `type="security-code"` | `type="password"` + `inputMode="numeric"` | `FormInput` | Masked numeric input |
| `small="yes"` | `size="sm"` | `FormInput` | |
| `readonly="yes"` | `readOnly` | `FormInput` | Boolean prop |
| `disabled="yes"` | `disabled` | `FormInput` | Boolean prop |
| `required="yes"` | Yup validation + `error` | `FormItem` | No direct prop; validate and pass error |
| `maxlength` | `maxLength` | `FormInput` | camelCase in React |
| `maxdigits` | `isAllowed` callback on `NumericFormat` | `react-number-format` | Limit `floatValue` to max allowed (e.g. maxdigits=7 → `<= 9999999.99`) |
| `precision` | `decimalScale` on `NumericFormat` | `react-number-format` | Number of decimal places; add `fixedDecimalScale` to always show trailing zeros |
| `symbol` | `prefix` or `suffix` on `NumericFormat` | `react-number-format` | For money inputs: use NumericFormat prefix/suffix, NOT FormInput `affix` |
| `position` (left/right) | `prefix` (left) or `suffix` (right) on `NumericFormat` | `react-number-format` | `left` → `prefix`, `right` → `suffix` |
| `currency-code="yes"` | `prefix` (use currency code as value) | `react-number-format` | e.g. `prefix="GBP "` or `prefix="GBP £"` |
| `icon` | `media` | `FormInput` | Native prop — pass `<Icon>` as ReactNode; use `mediaPosition` for placement |
| `description` | `description` | `FormItem` | |
| `description-icon` | `<Icon>` inside `description` | `FormItem` | Compose with Arrange |
| `help` | `<PopupNav>` triggered by info icon in label | `FormItem` label | Click-to-show help; NO Tooltip in Blueprint |
| `pattern-mask` | Custom `onChange` regex validation | N/A | Or Yup schema |
