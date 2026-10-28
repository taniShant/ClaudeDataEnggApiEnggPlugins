# BDL Sort Code & Account to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Sort Code & Account (`<mca-sortaccount>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-sortaccount>` | `<FormMultiItem>` with nested `<FormItem hiddenLabel>` + `<FormInput>` per field |
| `<mca-sortaccount only-sort="yes">` | `<FormItem>` + `<FormInput>` (single field) |
| `<mca-sortaccount type="giro-credits">` | `<FormMultiItem>` with nested `<FormItem hiddenLabel>` + `<FormInput>` (alphanumeric account) |

MCA1's `<mca-sortaccount>` is a compound field that renders a sort code input and an account number input as a single unit. Use `<FormMultiItem>` with `layout="inline"` to place the fields side by side, with each field wrapped in a `<FormItem hiddenLabel>` for accessibility.

**Pattern** (from Blueprint-React PINsentry reference):
```typescript
<FormMultiItem label={<Type>Label</Type>} layout="inline" render={renderProps => <>
    <FormItem label={<Type>Sort code</Type>} hiddenLabel render={() => <FormInput maxLength={8} size="8" {...renderProps} />} />
    <FormItem label={<Type>Account number</Type>} hiddenLabel render={() => <FormInput maxLength={8} size="8" {...renderProps} />} />
  </>} />
```

Key points:
- `FormMultiItem` provides the visible group label and `layout="inline"` for side-by-side fields
- Each field uses `FormItem` with `hiddenLabel` (label exists for screen readers but is not displayed)
- `{...renderProps}` is spread **at the end** of `<FormInput>` props
- `size` prop on `<FormInput>` controls the visual width of the input

---

### Sort Code & Account (Default)

**MCA1 (Before)**:
```html
<mca-sortaccount id="b_sortaccount" description="Optional description Text">
    Sort Code &amp; Account
</mca-sortaccount>
```

**Blueprint-React (After)**:
```typescript
<FormMultiItem
  label={<Type>Sort Code & Account</Type>}
  id="b_sortaccount"
  description="Optional description Text"
  layout="inline"
  render={renderProps => <>
    <FormItem label={<Type>Sort code</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_sortcode"
        placeholder="00-00-00"
        maxLength={8}
        size="8"
        value={sortCode}
        onChange={(e) => handleSortCodeChange(e, setSortCode)}
        {...renderProps}
      />
    } />
    <FormItem label={<Type>Account number</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_account"
        placeholder="Account number"
        inputMode="numeric"
        maxLength={8}
        size="8"
        value={accountNumber}
        onChange={(e) => {
          const val = e.target.value.replace(/[^\d]/g, '');
          if (val.length <= 8) setAccountNumber(val);
        }}
        {...renderProps}
      />
    } />
  </>}
/>
```

---

### Giro Credits Sort Code & Account

MCA1's `type="giro-credits"` changes the account number field to accept alphanumeric giro credit references instead of numeric-only account numbers.

**MCA1 (Before)**:
```html
<mca-sortaccount type="giro-credits" id="b_sortaccount_giro-credits"
    description="Optional description Text">
    Giro Credits Sort Code &amp; Account
</mca-sortaccount>
```

**Blueprint-React (After)**:
```typescript
<FormMultiItem
  label={<Type>Giro Credits Sort Code & Account</Type>}
  id="b_sortaccount_giro-credits"
  description="Optional description Text"
  layout="inline"
  render={renderProps => <>
    <FormItem label={<Type>Sort code</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_giro_sortcode"
        placeholder="00-00-00"
        maxLength={8}
        size="8"
        value={sortCode}
        onChange={(e) => handleSortCodeChange(e, setSortCode)}
        {...renderProps}
      />
    } />
    <FormItem label={<Type>Giro reference</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_giro_account"
        placeholder="Giro reference"
        size="10"
        value={giroReference}
        onChange={(e) => setGiroReference(e.target.value)}
        {...renderProps}
      />
    } />
  </>}
/>
```

**Note**: The giro-credits account field accepts any character (alphanumeric + symbols), unlike the standard numeric-only account number.

---

### Sort Code & Account with Default Value

MCA1 accepts a single `value` attribute in the format `"20-16-56 20554839"` (sort code + space + account number). Parse and split into two controlled inputs.

**MCA1 (Before)**:
```html
<mca-sortaccount id="b_sortaccount_value" value="20-16-56 20554839">
    Sort Code &amp; Account with Default Value
</mca-sortaccount>
```

**Blueprint-React (After)**:
```typescript
// Parse the combined value "20-16-56 20554839" into sort code and account
const parseValue = (combined: string): { sortCode: string; account: string } => {
  const parts = combined.trim().split(/\s+/);
  return { sortCode: parts[0] || '', account: parts[1] || '' };
};

const { sortCode: defaultSort, account: defaultAccount } = parseValue('20-16-56 20554839');
const [sortCode, setSortCode] = useState(defaultSort);       // "20-16-56"
const [accountNumber, setAccountNumber] = useState(defaultAccount); // "20554839"

<FormMultiItem
  label={<Type>Sort Code & Account with Default Value</Type>}
  id="b_sortaccount_value"
  layout="inline"
  render={renderProps => <>
    <FormItem label={<Type>Sort code</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_value_sortcode"
        placeholder="00-00-00"
        maxLength={8}
        size="8"
        value={sortCode}
        onChange={(e) => handleSortCodeChange(e, setSortCode)}
        {...renderProps}
      />
    } />
    <FormItem label={<Type>Account number</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_value_account"
        inputMode="numeric"
        maxLength={8}
        size="8"
        value={accountNumber}
        onChange={(e) => {
          const val = e.target.value.replace(/[^\d]/g, '');
          if (val.length <= 8) setAccountNumber(val);
        }}
        {...renderProps}
      />
    } />
  </>}
/>
```

---

### Giro Credits with Default Value

**MCA1 (Before)**:
```html
<mca-sortaccount type="giro-credits" id="b_sortaccount_giro_credits_value"
    value="20-16-56 205583&amp;/%AS">
    Giro Credits Sort Code &amp; Account with Default Value
</mca-sortaccount>
```

**Blueprint-React (After)**:
```typescript
const { sortCode: giroSort, account: giroAccount } = parseValue('20-16-56 205583&/%AS');
const [sortCode, setSortCode] = useState(giroSort);       // "20-16-56"
const [giroReference, setGiroReference] = useState(giroAccount); // "205583&/%AS"

<FormMultiItem
  label={<Type>Giro Credits Sort Code & Account with Default Value</Type>}
  id="b_sortaccount_giro_credits_value"
  layout="inline"
  render={renderProps => <>
    <FormItem label={<Type>Sort code</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_giro_credits_value_sortcode"
        placeholder="00-00-00"
        maxLength={8}
        size="8"
        value={sortCode}
        onChange={(e) => handleSortCodeChange(e, setSortCode)}
        {...renderProps}
      />
    } />
    <FormItem label={<Type>Giro reference</Type>} hiddenLabel render={() =>
      <FormInput
        name="b_sortaccount_giro_credits_value_account"
        placeholder="Giro reference"
        size="10"
        value={giroReference}
        onChange={(e) => setGiroReference(e.target.value)}
        {...renderProps}
      />
    } />
  </>}
/>
```

---

### Sort Code Only

MCA1's `only-sort="yes"` renders only the sort code field without the account number. Use a single `<FormItem>` (no `FormMultiItem` needed since there is only one field).

**MCA1 (Before)**:
```html
<mca-sortaccount type="giro-credits" id="b_only_sortCode" value="" only-sort="yes">
    Only SortCode
</mca-sortaccount>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Only SortCode"
  id="b_only_sortCode"
  render={(props) => (
    <FormInput
      name="b_only_sortCode"
      placeholder="00-00-00"
      maxLength={8}
      size="8"
      value={sortCode}
      onChange={(e) => handleSortCodeChange(e, setSortCode)}
      {...props}
    />
  )}
/>
```

---

### Sort Code Formatting Utility

A reusable handler for sort code formatting (XX-XX-XX) used across all variants:

```typescript
const handleSortCodeChange = (
  e: React.ChangeEvent<HTMLInputElement>,
  setter: (val: string) => void
) => {
  const digits = e.target.value.replace(/[^\d]/g, '');
  if (digits.length <= 6) {
    const formatted = digits.replace(/(\d{2})(?=\d)/g, '$1-').slice(0, 8);
    setter(formatted);
  }
};
```

---

## Complete `<mca-sortaccount>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormMultiItem` | |
| Text content | `label={<Type>...</Type>}` | `FormMultiItem` | Wrapped in `<Type>` |
| `description` | `description` | `FormMultiItem` | |
| `value` | Parsed into `sortCode` + `accountNumber` state | `FormInput` values | Split on whitespace: `"20-16-56 20554839"` |
| `type="giro-credits"` | Account field allows alphanumeric input | `FormInput` onChange | No digit-only filter on account field |
| `only-sort="yes"` | Use single `<FormItem>` + `<FormInput>` (no `FormMultiItem`) | Layout | Sort code only, no account number |
| `pattern-mask` | Custom `onChange` regex validation | N/A | Or Yup schema |
| N/A | `layout="inline"` | `FormMultiItem` | Side-by-side sort code + account |
| N/A | `hiddenLabel` | Nested `FormItem` | Accessible label, visually hidden |
| N/A | `size` | `FormInput` | Controls visual input width |
| N/A | `{...renderProps}` | `FormInput` | Spread **at end** of props |

### Type-to-Layout Summary

| MCA1 `type` | `only-sort` | Blueprint-React Component | Layout |
|---|---|---|---|
| (default) | `"no"` / omitted | `<FormMultiItem layout="inline">` with two nested `<FormItem hiddenLabel>` | Sort code + numeric account side by side |
| `"giro-credits"` | `"no"` / omitted | `<FormMultiItem layout="inline">` with two nested `<FormItem hiddenLabel>` | Sort code + alphanumeric account side by side |
| (any) | `"yes"` | `<FormItem>` with single `<FormInput>` | Sort code only |
