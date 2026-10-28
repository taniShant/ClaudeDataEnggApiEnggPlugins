# Form Layout Patterns — Form, FormSection, and FormItem Structure

**Date**: July 20, 2026
**Version**: 1.0.0
**Status**: CRITICAL — Layout rules for forms, sections, and field subtext

---

## Overview

This document defines the mandatory layout rules for Blueprint-React form components in MCA2 applications. These patterns ensure proper spacing, accessibility, and visual hierarchy in migrated forms.

**Key rules:**
1. All form fields MUST be inside a `<Form>` wrapper
2. Logically grouped fields MUST be wrapped in `<FormSection>`
3. Consecutive `<FormSection>` components MUST use `paddingTop={false}` on the second and subsequent sections
4. Field subtext/descriptions MUST use the `description` prop on `<FormItem>`, not custom elements

---

## Rule 1: Forms Must Be Wrapped in `<Form>`

Every form in MCA2 must use the Blueprint-React `<Form>` component as its outermost wrapper. Do NOT use plain `<form>` HTML elements or omit the form wrapper entirely.

### CORRECT

```typescript
import { Form, FormSection, FormItem, FormInput, Button } from '@barclays/blueprint-react';

<Form onSubmit={handleSubmit}>
  <FormSection>
    <FormItem
      label={<Type>Name</Type>}
      render={(props) => <FormInput {...props} type="text" value={name} onChange={handleChange} />}
    />
  </FormSection>
  <FormSection>
    <ButtonGroup>
      <Button type="submit" variant="primary">Submit</Button>
    </ButtonGroup>
  </FormSection>
</Form>
```

### INCORRECT

```typescript
// WRONG - Plain HTML form element
<form onSubmit={handleSubmit}>
  <FormItem label="Name" render={(props) => <FormInput {...props} />} />
</form>

// WRONG - No form wrapper at all
<div>
  <FormItem label="Name" render={(props) => <FormInput {...props} />} />
  <Button type="submit">Submit</Button>
</div>
```

### Why This Matters

- Blueprint-React `<Form>` manages form-level accessibility attributes
- Form validation and error state propagation require the Blueprint Form wrapper
- Direct children of `<Form>` can only be `FormSection`, `FormItem`, or `FormMultiItem`
- Custom divs, headings, or layout elements directly inside `<Form>` break rendering

---

## Rule 2: Group Fields in `<FormSection>`

Logically related form fields must be grouped inside `<FormSection>` components. This provides visual separation between groups and allows section headings.

### CORRECT

```typescript
<Form onSubmit={handleSubmit}>
  <FormSection head="Personal Details">
    <FormItem
      label={<Type>First Name</Type>}
      render={(props) => <FormInput {...props} type="text" />}
    />
    <FormItem
      label={<Type>Last Name</Type>}
      render={(props) => <FormInput {...props} type="text" />}
    />
  </FormSection>

  <FormSection head="Contact Information" paddingTop={false}>
    <FormItem
      label={<Type>Email</Type>}
      render={(props) => <FormInput {...props} type="email" />}
    />
    <FormItem
      label={<Type>Phone</Type>}
      render={(props) => <FormInput {...props} type="tel" />}
    />
  </FormSection>

  <FormSection paddingTop={false}>
    <ButtonGroup>
      <Button type="submit" variant="primary">Save</Button>
      <Button type="button" onClick={handleCancel}>Cancel</Button>
    </ButtonGroup>
  </FormSection>
</Form>
```

### FormSection Props

```typescript
interface FormSectionProps {
  head?: ReactNode;        // Optional section heading (rendered as legend)
  paddingTop?: boolean;    // Controls top padding (default: true)
  widthMd?: string;        // Medium breakpoint width (e.g., "6of12")
  widthLg?: string;        // Large breakpoint width (e.g., "4of12")
  children: ReactNode;     // FormItem/FormMultiItem components
}
```

---

## Rule 3: Consecutive FormSections Use `paddingTop={false}`

When multiple `<FormSection>` components appear inside a single `<Form>`, the **second and all subsequent** FormSections MUST have `paddingTop={false}`. This prevents excessive vertical spacing between sections.

### CORRECT

```typescript
<Form onSubmit={handleSubmit}>
  {/* First section - uses default padding (paddingTop is true by default) */}
  <FormSection head="Account Details">
    <FormItem label={<Type>Account Number</Type>} render={(props) => <FormInput {...props} />} />
    <FormItem label={<Type>Sort Code</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>

  {/* Second section - paddingTop={false} to avoid double spacing */}
  <FormSection head="Transfer Details" paddingTop={false}>
    <FormItem label={<Type>Amount</Type>} render={(props) => <FormInput {...props} type="number" />} />
    <FormItem label={<Type>Reference</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>

  {/* Third section (buttons) - paddingTop={false} */}
  <FormSection paddingTop={false}>
    <ButtonGroup>
      <Button type="submit" variant="primary">Transfer</Button>
    </ButtonGroup>
  </FormSection>
</Form>
```

### INCORRECT

```typescript
// WRONG - Missing paddingTop={false} causes excessive spacing
<Form>
  <FormSection head="Section 1">
    <FormItem label={<Type>Field</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>
  <FormSection head="Section 2">  {/* Missing paddingTop={false} */}
    <FormItem label={<Type>Field</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>
</Form>
```

### Pattern Summary

| Position | paddingTop | Reason |
|----------|-----------|--------|
| First `<FormSection>` in a `<Form>` | default (true) | Provides initial top spacing |
| Second+ `<FormSection>` in same `<Form>` | `paddingTop={false}` | Prevents double-spacing between sections |
| Single `<FormSection>` (only one) | default (true) | No adjacent sections to clash with |

---

## Rule 4: Use `description` Prop for Field Subtext

When a form field needs helper text or subtext below the label, use the `description` prop on `<FormItem>`. Do NOT add custom `<p>`, `<span>`, or `<Type>` elements below the field.

### CORRECT

```typescript
<FormItem
  label={<Type>Sort Code</Type>}
  description={<Type>Enter your 6-digit sort code without dashes</Type>}
  render={(props) => (
    <FormInput
      {...props}
      type="text"
      placeholder="000000"
      maxLength={6}
    />
  )}
/>

<FormItem
  label={<Type>Account Number</Type>}
  description={<Type>Your 8-digit bank account number</Type>}
  error={hasError ? <Type color="error">Account number must be 8 digits</Type> : undefined}
  render={(props) => (
    <FormInput
      {...props}
      type="text"
      maxLength={8}
    />
  )}
/>
```

### INCORRECT

```typescript
// WRONG - Custom subtext element outside FormItem
<FormItem
  label={<Type>Sort Code</Type>}
  render={(props) => <FormInput {...props} />}
/>
<p className="field-description">Enter your 6-digit sort code</p>

// WRONG - Description as sibling, not prop
<div>
  <FormItem label={<Type>Sort Code</Type>} render={(props) => <FormInput {...props} />} />
  <Type size="sm" color="secondary">Enter your 6-digit sort code</Type>
</div>

// WRONG - Using children instead of description prop
<FormItem label={<Type>Sort Code</Type>} render={(props) => <FormInput {...props} />}>
  <span>Enter your 6-digit sort code</span>
</FormItem>
```

### How `description` Works

- The `description` text renders between the label and the input field
- It is automatically linked via `aria-describedby` for accessibility
- When both `description` and `error` are present, the error takes visual priority but both are linked to the input
- Always wrap description content in `<Type>` for consistent styling

---

## Complete Form Layout Example

This example shows a realistic form migration from BDL to Blueprint-React following all four rules:

### BDL Source (Before)

```html
<mca-form>
  <mca-heading level="3">Transfer Funds</mca-heading>
  <mca-input label="Account Number" helper-text="8 digit account number" required></mca-input>
  <mca-input label="Sort Code" helper-text="6 digit sort code"></mca-input>
  <mca-input label="Amount" type="number" required></mca-input>
  <mca-input label="Reference" helper-text="Optional payment reference"></mca-input>
  <mca-button type="submit" appearance="primary">Transfer</mca-button>
  <mca-button type="button">Cancel</mca-button>
</mca-form>
```

### Blueprint-React (After)

```typescript
import {
  Form,
  FormSection,
  FormItem,
  FormInput,
  Button,
  ButtonGroup,
  Type,
} from '@barclays/blueprint-react';

const TransferForm: React.FC = () => {
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Handle form submission
  };

  return (
    <Form onSubmit={handleSubmit}>
      {/* Section 1: Account details */}
      <FormSection head="Transfer Funds">
        <FormItem
          label={<Type>Account Number</Type>}
          description={<Type>8 digit account number</Type>}
          error={errors.account ? <Type color="error">{errors.account}</Type> : undefined}
          render={(props) => (
            <FormInput
              {...props}
              type="text"
              value={account}
              onChange={(e) => setAccount(e.target.value)}
              required
            />
          )}
        />
        <FormItem
          label={<Type>Sort Code</Type>}
          description={<Type>6 digit sort code</Type>}
          render={(props) => (
            <FormInput
              {...props}
              type="text"
              value={sortCode}
              onChange={(e) => setSortCode(e.target.value)}
            />
          )}
        />
      </FormSection>

      {/* Section 2: Transfer details — paddingTop={false} because it's not the first */}
      <FormSection paddingTop={false}>
        <FormItem
          label={<Type>Amount</Type>}
          error={errors.amount ? <Type color="error">{errors.amount}</Type> : undefined}
          render={(props) => (
            <FormInput
              {...props}
              type="number"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              required
            />
          )}
        />
        <FormItem
          label={<Type>Reference</Type>}
          description={<Type>Optional payment reference</Type>}
          render={(props) => (
            <FormInput
              {...props}
              type="text"
              value={reference}
              onChange={(e) => setReference(e.target.value)}
            />
          )}
        />
      </FormSection>

      {/* Section 3: Actions — paddingTop={false} */}
      <FormSection paddingTop={false}>
        <ButtonGroup>
          <Button type="submit" variant="primary">Transfer</Button>
          <Button type="button" onClick={handleCancel}>Cancel</Button>
        </ButtonGroup>
      </FormSection>
    </Form>
  );
};
```

---

## Migration Checklist

When migrating BDL forms to Blueprint-React, verify:

- [ ] All forms are wrapped in `<Form>` (not plain `<form>`)
- [ ] Direct children of `<Form>` are only `FormSection`, `FormItem`, or `FormMultiItem`
- [ ] Related fields are grouped in `<FormSection>` components
- [ ] Second+ `<FormSection>` uses `paddingTop={false}`
- [ ] BDL `helper-text` / subtext is migrated to `description` prop on `<FormItem>`
- [ ] `description` content is wrapped in `<Type>` component
- [ ] No custom CSS for spacing between form sections (Blueprint handles it)
- [ ] Section headings use `head` prop on `<FormSection>`, not standalone `<Type>` elements
- [ ] `label` prop values are wrapped in `<Type>` component
- [ ] `error` prop values are wrapped in `<Type color="error">`

---

## Component Conflict Check

When migrating forms, verify you are importing the correct Blueprint-React components and not conflicting variants:

| Correct Import | Conflicts to Avoid |
|---|---|
| `Form` from `@barclays/blueprint-react` | `Form` from Formik, custom Form wrappers |
| `FormSection` from `@barclays/blueprint-react` | Custom `Section` or `FieldGroup` components |
| `FormItem` from `@barclays/blueprint-react` | `FormGroup` (BDL), `FormFieldWrapper` (non-existent), `Field` (Formik) |
| `FormInput` from `@barclays/blueprint-react` | `TextInput` (non-existent), `Input` (HTML), `TextField` (MUI) |
| `FormSelect` from `@barclays/blueprint-react` | `Select` (non-existent), `Dropdown` (BDL) |
| `FormTextarea` from `@barclays/blueprint-react` | `TextArea` (non-existent), `Textarea` (HTML) |
| `FormCheckbox` from `@barclays/blueprint-react` | `Checkbox` (BDL), `CheckBox` (non-existent) |
| `FormRadio` from `@barclays/blueprint-react` | `Radio` (BDL), `RadioButton` (non-existent) |

> **Rule**: Always use the `Form*` prefixed component from `@barclays/blueprint-react`. If you find yourself importing a form control without the `Form` prefix, it likely does not exist in Blueprint-React.

---

## References

- [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md) — Full component patterns
- [BDL_FORM_CONTROLS_MAPPING.md](../mappings/BDL_FORM_CONTROLS_MAPPING.md) — BDL form migration
- [FORM_VALIDATION_PATTERNS.md](FORM_VALIDATION_PATTERNS.md) — Yup + Formik/RHF patterns
- [COMPONENT_AUDIT_CHECKLIST.md](COMPONENT_AUDIT_CHECKLIST.md) — Full audit checklist
