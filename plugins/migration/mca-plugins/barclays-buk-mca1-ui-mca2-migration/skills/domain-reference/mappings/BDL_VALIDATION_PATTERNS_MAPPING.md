# BDL_VALIDATION_PATTERNS_MAPPING.md

## Overview

Maps MCA1 BDL validation patterns (on-submit, inline, and notification-based validation) to React form validation using Yup schemas, `FormItem` error props, and `Alert` for notification-style messages.

These are **patterns**, not individual components — they describe how validation was done in MCA1 EJS templates and how to replicate the same UX in MCA2 React.

---

## MCA1 Pattern: Validation on Submit

```html
<!-- EJS template with form -->
<mca-form id="myForm">
  <mca-input id="firstName" label="First Name" required="yes" />
  <mca-input id="lastName" label="Last Name" required="yes" />
  <mca-input id="email" label="Email" required="yes" />
  <mca-button type="normal" id="submitBtn">Submit</mca-button>
</mca-form>
```

```javascript
// Controller validation on submit
$scope.submitForm = function() {
  var errors = [];
  if (!$scope.firstName) errors.push({ field: 'firstName', msg: 'First name is required' });
  if (!$scope.email || !validateEmail($scope.email)) errors.push({ field: 'email', msg: 'Valid email required' });

  if (errors.length > 0) {
    errors.forEach(function(err) {
      $('#' + err.field).getComponent().showError(err.msg);
    });
    return;
  }
  // proceed with submission
};
```

### Blueprint-React Equivalent: Validation on Submit

```typescript
import React, { useState } from 'react';
import * as Yup from 'yup';
import { Form, FormItem, FormInput, Button, Type, Alert, Section, SectionItem } from '@barclays/blueprint-react';

const validationSchema = Yup.object({
  firstName: Yup.string().required('First name is required'),
  lastName: Yup.string().required('Last name is required'),
  email: Yup.string().email('Valid email required').required('Email is required'),
});

interface FormValues {
  firstName: string;
  lastName: string;
  email: string;
}

export const MyForm: React.FC = () => {
  const [values, setValues] = useState<FormValues>({ firstName: '', lastName: '', email: '' });
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    try {
      await validationSchema.validate(values, { abortEarly: false });
      setErrors({});
      setSubmitted(true);
      // proceed with submission
    } catch (err) {
      if (err instanceof Yup.ValidationError) {
        const fieldErrors: Partial<Record<keyof FormValues, string>> = {};
        err.inner.forEach((e) => {
          if (e.path) fieldErrors[e.path as keyof FormValues] = e.message;
        });
        setErrors(fieldErrors);
      }
    }
  };

  const handleChange = (field: keyof FormValues) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setValues({ ...values, [field]: e.target.value });
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  return (
    <Section>
      <SectionItem>
        <Form>
          <FormItem
            label={<Type>First Name</Type>}
            error={errors.firstName && <Type color="error">{errors.firstName}</Type>}
            render={(props) => (
              <FormInput {...props} value={values.firstName} onChange={handleChange('firstName')} />
            )}
          />
          <FormItem
            label={<Type>Last Name</Type>}
            error={errors.lastName && <Type color="error">{errors.lastName}</Type>}
            render={(props) => (
              <FormInput {...props} value={values.lastName} onChange={handleChange('lastName')} />
            )}
          />
          <FormItem
            label={<Type>Email</Type>}
            error={errors.email && <Type color="error">{errors.email}</Type>}
            render={(props) => (
              <FormInput {...props} type="email" value={values.email} onChange={handleChange('email')} />
            )}
          />
          <Button variant="primary" onClick={handleSubmit}>Submit</Button>
        </Form>
      </SectionItem>
    </Section>
  );
};
```

---

## MCA1 Pattern: Inline Validation

```javascript
// Real-time validation as user types or blurs
$('#email').getComponent().onblur = function() {
  var value = $('#email').getComponent().val();
  if (!validateEmail(value)) {
    $('#email').getComponent().showError('Please enter a valid email');
  } else {
    $('#email').getComponent().hideError();
  }
};
```

### Blueprint-React Equivalent: Inline Validation

```typescript
const handleBlur = (field: keyof FormValues) => () => {
  try {
    validationSchema.validateSyncAt(field, values);
    setErrors({ ...errors, [field]: undefined });
  } catch (err) {
    if (err instanceof Yup.ValidationError) {
      setErrors({ ...errors, [field]: err.message });
    }
  }
};

// In JSX:
<FormItem
  label={<Type>Email</Type>}
  error={errors.email && <Type color="error">{errors.email}</Type>}
  render={(props) => (
    <FormInput
      {...props}
      type="email"
      value={values.email}
      onChange={handleChange('email')}
      onBlur={handleBlur('email')}
    />
  )}
/>
```

---

## MCA1 Pattern: Validation Notifications

```html
<!-- Notification banner at top of form -->
<mca-notify id="formErrors" type="error" hide="yes">
  <span>Please correct the errors below</span>
</mca-notify>
```

```javascript
// Show notification when validation fails
if (errors.length > 0) {
  $('#formErrors').getComponent().show();
  $('#formErrors').getComponent().setContent('Please correct ' + errors.length + ' error(s) below');
}
```

### Blueprint-React Equivalent: Validation Notifications

```typescript
import { Alert, Icon, Type } from '@barclays/blueprint-react';

// In component:
{Object.keys(errors).length > 0 && (
  <Alert
    media={<Icon icon="error-fill" size="sm" status="error" />}
    status="error"
  >
    <Type>Please correct {Object.keys(errors).length} error(s) below</Type>
  </Alert>
)}
```

---

## Pattern Mapping Table

| MCA1 Validation Pattern | Blueprint-React Pattern | Notes |
|------------------------|------------------------|-------|
| `.showError(msg)` on component | `error` prop on `FormItem` with `<Type color="error">` | Declarative via state |
| `.hideError()` on component | Set error state to `undefined` | Automatic when state clears |
| `required="yes"` attribute | Yup `.required()` in schema | Schema-driven |
| `<mca-notify type="error">` | `<Alert status="error">` | Conditional render based on error count |
| `<mca-notify type="warning">` | `<Alert status="warning">` | Same pattern, different status |
| `<mca-notify type="info">` | `<Alert status="info">` | Same pattern, different status |
| Manual `if/else` in controller | Yup schema with `.validate()` | Declarative validation rules |

---

## Iron Rules

1. **Always use Yup schemas for validation** — never inline `if/else` validation logic in component body
2. **FormItem `error` prop must wrap message in `<Type color="error">`** — never pass plain strings
3. **Clear field error when user starts correcting** — update errors state in `onChange` handler
4. **For notification-style errors, use `Alert` NOT `Notification`** — `Alert` is inline, `Notification` is toast-style
5. **Validate on submit AND on blur** — combine both patterns for best UX
6. **`abortEarly: false`** in Yup `.validate()` to collect ALL errors at once, not just the first
