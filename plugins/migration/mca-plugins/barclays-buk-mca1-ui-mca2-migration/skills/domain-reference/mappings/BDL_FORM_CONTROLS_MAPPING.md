# BDL Form Controls to Blueprint-React Mapping

**Last Updated**: April 28, 2026

This document covers additional form control components: Date Input, Card Number Input, Dropdown Expiry Date, Account Dropdown, Mobile Selection Picker, Number Stepper, and Form Container.

**Note**: Sort Code & Account mapping is in a separate file: [BDL_SORTACCOUNT_MAPPING.md](BDL_SORTACCOUNT_MAPPING.md)

---

## Date Input

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-date>` | `<FormItem>` + `<FormInput type="date" media={<Icon icon="calendar" size="sm" />}>` + date validation |

**MCA1 (Before)**:
```html
<mca-date id="switchStartDate" placeholder="DD/MM/YYYY" required="yes" name="switchStartDate">
</mca-date>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Switch start date"
  id="switchStartDate"
  error={dateError && <Type color="error">{dateError}</Type>}
  render={(props) => (
    <FormInput
      {...props}
      name="switchStartDate"
      type="text"
      placeholder="DD/MM/YYYY"
      value={switchStartDate}
      onChange={(e) => setSwitchStartDate(e.target.value)}
    />
  )}
/>
```

### Date Input Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormItem` | |
| `placeholder` | `placeholder` | `FormInput` via render | |
| `required="yes"` | Yup validation | External | Not a direct FormItem prop |
| `name` | `name` | `FormInput` via render | |
| `min` | date validation logic | External | Validate in onChange handler |
| `max` | date validation logic | External | Validate in onChange handler |

---

## Card Number Input

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-cardnumber>` | `<FormItem>` + `<FormInput>` with validation |

**MCA1 (Before)**:
```html
<mca-cardnumber id="oldDebitCardNum" name="oldDebitCardNum"
    placeholder="Please enter your card number" description="Card description">
    Card number
</mca-cardnumber>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Card number"
  id="oldDebitCardNum"
  description="Card description"
  render={(props) => (
    <FormInput
      {...props}
      name="oldDebitCardNum"
      type="text"
      placeholder="Please enter your card number"
      maxLength={19}
      value={cardNumber}
      onChange={(e) => setCardNumber(e.target.value)}
    />
  )}
/>
```

### Card Number Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormItem` | |
| `name` | `name` | `FormInput` via render | |
| `placeholder` | `placeholder` | `FormInput` via render | |
| `description` | `description` | `FormItem` | |
| Children (label) | `label` | `FormItem` | Wrap in `<Type>` |
| maxLength | `maxLength` | `FormInput` via render | e.g. 19 for card numbers |

---

## Dropdown Expiry Date

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-dropdown-expiry-date>` | Two `<FormItem>` + `<FormSelect>` (month and year) |

**MCA1 (Before)**:
```html
<mca-dropdown-expiry-date id="expiryDate" name="expiryDate"></mca-dropdown-expiry-date>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label={<Type>Expiry month</Type>}
  id="expiryMonth"
  render={(props) => (
    <FormSelect
      {...props}
      name="expiryMonth"
      value={expiryMonth}
      onChange={(e) => setExpiryMonth(e.target.value)}
    >
      <option value="">Month</option>
      {months.map((m) => (
        <option key={m.value} value={m.value}>{m.label}</option>
      ))}
    </FormSelect>
  )}
/>

<FormItem
  label={<Type>Expiry year</Type>}
  id="expiryYear"
  render={(props) => (
    <FormSelect
      {...props}
      name="expiryYear"
      value={expiryYear}
      onChange={(e) => setExpiryYear(e.target.value)}
    >
      <option value="">Year</option>
      {years.map((y) => (
        <option key={y} value={y}>{y}</option>
      ))}
    </FormSelect>
  )}
/>
```

---

## Account Dropdown

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-dropdown-account>` | `<FormItem>` + `<FormSelect>` with account data |

**MCA1 (Before)**:
```html
<mca-dropdown-account id="accountSelect" name="account"></mca-dropdown-account>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label={<Type>Select account</Type>}
  id="accountSelect"
  render={(props) => (
    <FormSelect
      {...props}
      name="account"
      value={selectedAccount}
      onChange={(e) => setSelectedAccount(e.target.value)}
    >
      <option value="">Choose an account</option>
      {accounts.map((a) => (
        <option key={a.id} value={a.id}>
          {a.name} - {a.sortCode} {a.accountNumber}
        </option>
      ))}
    </FormSelect>
  )}
/>
```

---

## Mobile Selection Picker

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-selection>` | `<FormItem>` + `<FormSelect>` or `<AutoComplete>` |

**MCA1 (Before)**:
```html
<mca-selection id="mobileSelect" name="selection"></mca-selection>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label={<Type>Select option</Type>}
  id="mobileSelect"
  render={(props) => (
    <FormSelect
      {...props}
      name="selection"
      value={selectedValue}
      onChange={(e) => setSelectedValue(e.target.value)}
    >
      <option value="">Please select</option>
      {options.map((opt) => (
        <option key={opt.value} value={opt.value}>{opt.label}</option>
      ))}
    </FormSelect>
  )}
/>
```

> **Note**: Mobile-optimized selection behavior (native picker UI) is handled automatically by the browser when using a standard `<FormSelect>` on mobile devices. No special component is needed.

---

## Number Stepper

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-stepper>` | `<NumberStepper>` |

Number stepper mapping is in a separate file: **[BDL_STEPPER_MAPPING.md](BDL_STEPPER_MAPPING.md)**

---

## Form Container

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-form>` | `<Form>` |
| `<mca-formview>` | `<Form>` or container `<div>` |

### Comprehensive Form Example

**MCA1 (Before)**:
```html
<mca-form id="b_form" class="form-class" name="bdlname" autofocus="yes">
  <!-- Input -->
  <mca-input id="validation0" name="validation0" class="scp-autofocus" required="yes">
    Normal Input
  </mca-input>
  <mca-input id="validation1" name="validation1" type="money" required="yes">
    Money Input
  </mca-input>
  <mca-input id="validation2" name="validation2">Input Optional</mca-input>

  <!-- Text area -->
  <mca-textarea id="validation14" name="validation14" placeholder="Some random words" required="yes">
    Description
  </mca-textarea>

  <!-- Checkboxes -->
  <mca-checkboxes id="validation9" label="Some random words" required="yes">
    <mca-checkbox checked="no" id="validation10" name="validation10">Two Words</mca-checkbox>
    <mca-checkbox checked="no" id="validation11" name="validation10">Two Words again</mca-checkbox>
    <mca-checkbox checked="no" id="validation12" name="validation10">Two Words again and again</mca-checkbox>
    <mca-checkbox checked="no" id="validation13" name="validation10">Two Words again</mca-checkbox>
  </mca-checkboxes>

  <!-- Radios -->
  <mca-radios id="validation3" label-content="Gender" required="yes">
    <mca-radio checked="no" id="validation4" name="validation3">Male</mca-radio>
    <mca-radio checked="no" id="validation5" name="validation3">Female</mca-radio>
  </mca-radios>

  <!-- Date Picker -->
  <mca-date id="example_date-0" placeholder="DD/MM/YYYY" required="yes" name="validation15">
    Basic Date Picker
  </mca-date>

  <!-- Stepper -->
  <mca-stepper id="stepperExample4" name="stepperExample" value="120" max="180" label="Stepper5" required="yes">
  </mca-stepper>

  <!-- Sort Account -->
  <mca-sortaccount id="b_form_sortaccount" required="yes">Sort Code Account</mca-sortaccount>

  <!-- button -->
  <mca-row>
    <mca-column columns="12">
      <mca-button id="b_form_validateForm1">Submit</mca-button>
      <mca-button id="b_form_clearForm1">Clear Error messages</mca-button>
    </mca-column>
  </mca-row>
</mca-form>
```

**Blueprint-React (After)**:
```typescript
const [description, setDescription] = useState('');
const [ariaInvalid, setAriaInvalid] = useState(false);

<Form onSubmit={handleSubmit}>
  <FormSection>
    <FormItem
      label={<Type>Normal Input</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      id='validation0'
      render={renderProps => <FormInput required {...renderProps} />}
    />
    <FormItem
      label={<Type>Money Input</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      id='validation1'
      render={renderProps => <FormInput required {...renderProps} />}
    />
    <FormItem
      label={<Type>Input Optional</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      id='validation2'
      render={renderProps => <FormInput {...renderProps} />}
    />
    <FormItem
      label={<Type>Description</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      id='validation14'
      render={renderProps => <FormTextArea placeholder="Some random words" {...renderProps} />}
    />
    <FormMultiItem
      label={<Type>Some random words</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      render={renderProps => (
        <>
          <FormCheckbox label='Two words' {...renderProps} />
          <FormCheckbox label='Two words again' {...renderProps} />
          <FormCheckbox label='Two words again and again' {...renderProps} />
          <FormCheckbox label='Two words again' {...renderProps} />
        </>
      )}
    />
    <FormMultiItem
      label={<Type>Gender</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      render={renderProps => (
        <>
          <FormRadio label='Male' {...renderProps} />
          <FormRadio label='Female' {...renderProps} />
        </>
      )}
    />
    <FormItem
      label={<Type>Basic Date Picker</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      id='example_date-0'
      render={renderProps => (
        <FormInput type='date' placeholder='DD/MM/YYYY' {...renderProps} />
      )}
    />
    <FormItem
      label={<Type>Stepper5</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      render={renderProps => (
        <NumberStepper
          max={180}
          defaultValue={120}
          {...renderProps}
        />
      )}
    />
    <FormItem
      label={<Type>Sort Code Account</Type>}
      description={<Type>{description}</Type>}
      error={ariaInvalid && <Type color='error'>There is an error</Type>}
      id='b_form_sortaccount'
      render={renderProps => <FormInput required {...renderProps} />}
    />
  </FormSection>
  <FormSection>
    <ButtonGroup>
      <Button type="submit" variant='primary'>Submit</Button>
      <Button onClick={handleClear} type="button">Clear Error messages</Button>
    </ButtonGroup>
  </FormSection>
</Form>
```

### Form with FormSection and ButtonGroup Pattern

For forms with multiple sections and action buttons, use `<FormSection>` to group related fields and `<ButtonGroup>` for form actions:

```typescript
<Form onSubmit={handleSubmit}>
  <FormSection>
    <FormItem label={<Type>Normal Input</Type>} render={(props) => <FormInput {...props} required />} />
  </FormSection>
  <FormSection>
    <ButtonGroup>
      <Button type="submit" variant="primary">Submit</Button>
      <Button onClick={handleClear}>Clear Error messages</Button>
    </ButtonGroup>
  </FormSection>
</Form>
```

> **Key pattern**: Each `<FormSection>` groups logically related fields. The final `<FormSection>` typically contains the `<ButtonGroup>` with submit and reset actions.

---

## Edge Case: Multiple Forms Nested in Single Form (Non-Standard BDL)

This section addresses a non-standard BDL anti-pattern where a single `<mca-form>` contains multiple logical forms with non-form elements (headings, subheadings, hero elements) mixed between them. This violates MCA2 Blueprint-React form hierarchy rules.

### Problem Description

In non-compliant BDL codebases, developers sometimes nest multiple logical forms within a single `<mca-form>` tag and separate them using heading elements. This pattern includes:

- Single `<mca-form>` wrapper
- Multiple `<mca-heading>` or `<mca-subheading>` elements directly inside the form
- `<mca-hero>` or other layout components inside the form
- Form fields grouped under headings representing separate workflows
- Multiple button sets at different levels suggesting independent form submissions

**Example anti-pattern indicators**:
```html
<mca-form>
  <mca-heading>Step 1: Personal Info</mca-heading>
  <mca-input ... />
  <mca-hero>...</mca-hero>
  <mca-heading>Step 2: Account Info</mca-heading>
  <mca-input ... />
  <mca-button>Submit</mca-button>
</mca-form>
```

This structure is **non-standard** because the BDL specification intends each logical form to be a separate `<mca-form>` tag.

### Why It's Invalid in MCA2

MCA2 Blueprint-React enforces strict form composition rules:

| Constraint | Reason |
|---|---|
| **Direct children of `<Form>` must be FormSection, FormItem, or FormMultiItem only** | Blueprint ensures predictable form layout and accessibility |
| **No heading elements directly inside `<Form>`** | Breaks semantic structure; headings must be outside form |
| **No layout/hero components directly inside `<Form>`** | Form wrapper contains only field containers |
| **Each logical form = separate `<Form>` component** | Cleaner state management and independent submissions |

**Result if violating**: Rendering errors, accessibility failures, validation issues, unpredictable form behavior.

### Detection Criteria

Identify this anti-pattern by looking for these indicators in MCA1 BDL:

1. **Single `<mca-form>` tag** with multiple `<mca-heading>` elements inside
2. **Non-form elements** directly nested: `<mca-hero>`, `<mca-subheading>`, layout components
3. **Multiple button sets** at different nesting levels (suggesting independent workflows)
4. **Form fields grouped under headings** that represent separate logical steps/sections
5. **Comments or structure** suggesting phases/steps within one form

### Migration Strategy

Follow these steps to convert this anti-pattern to proper MCA2 structure:

#### Step 1: Identify Form Boundaries
Examine the BDL structure and locate where heading elements separate logical form groups. Each heading typically marks the start of a new logical form.

#### Step 2: Extract Non-Form Elements
Remove all non-form content (headings, subheadings, hero, dividers, layout elements) from inside the form tags. Plan to place these outside the form components.

#### Step 3: Create Separate Form Components
For each logical form (identified by heading boundaries), create a separate `<Form>` component in MCA2.

#### Step 4: Group Fields with FormSection
Within each `<Form>`, group related fields using `<FormSection>`. This replaces the visual separation that headings provided.

#### Step 5: Convert Fields to FormItem/FormMultiItem
Convert individual `<mca-input>`, `<mca-select>`, etc. to Blueprint-React `<FormItem>` with `render` function pattern (see [BDL_FORM_CONTROLS_MAPPING.md](BDL_FORM_CONTROLS_MAPPING.md)).

#### Step 6: Manage Shared State
If forms need to share data, use **props-based state management**:
- Store shared state in parent component
- Pass state and setter functions to each form component
- Each form component updates parent state independently

#### Step 7: Wire Up Independent Submissions
Each form has its own `onSubmit` handler. Forms submit independently or trigger parent-level orchestration if needed.

### Example: Before (MCA1 BDL - Non-Standard)

```html
<mca-form id="multi-form" name="multiStepForm">
  <mca-heading level="2">Step 1: Personal Information</mca-heading>

  <mca-input id="firstName" name="firstName" required="yes">
    First Name
  </mca-input>

  <mca-input id="lastName" name="lastName" required="yes">
    Last Name
  </mca-input>

  <mca-hero id="hero1">
    <mca-column>
      <mca-text>Please review your information before proceeding</mca-text>
    </mca-column>
  </mca-hero>

  <mca-heading level="2">Step 2: Account Selection</mca-heading>

  <mca-sortaccount id="account" required="yes">
    Sort Code & Account
  </mca-sortaccount>

  <mca-subheading>Confirmation</mca-subheading>

  <mca-checkbox id="agree" name="agree" checked="no">
    I agree to the terms and conditions
  </mca-checkbox>

  <mca-row>
    <mca-column columns="12">
      <mca-button id="submit">Submit All</mca-button>
    </mca-column>
  </mca-row>
</mca-form>
```

### Example: After (MCA2 Blueprint-React - Correct)

```typescript
// Parent component managing multiple forms with shared state
const MultiStepForm: React.FC = () => {
  // State for Form 1: Personal Information
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');

  // State for Form 2: Account Selection
  const [sortCode, setSortCode] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [agreed, setAgreed] = useState(false);

  // Form 1 submission handler
  const handlePersonalInfoSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Step 1 - Personal Info submitted:', { firstName, lastName });
    // Proceed to next step or API call
  };

  // Form 2 submission handler
  const handleAccountSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Step 2 - Account submitted:', { sortCode, accountNumber, agreed });
    // Final submission or API call
  };

  return (
    <div>
      {/* ========== FORM 1: PERSONAL INFORMATION ========== */}

      {/* Non-form heading moved outside first form */}
      <Type variant="h2" marginBottom="md">Step 1: Personal Information</Type>

      {/* First logical form */}
      <Form onSubmit={handlePersonalInfoSubmit}>
        <FormSection>
          <FormItem
            label={<Type>First Name</Type>}
            id="firstName"
            render={(props) => (
              <FormInput
                {...props}
                name="firstName"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                required
              />
            )}
          />

          <FormItem
            label={<Type>Last Name</Type>}
            id="lastName"
            render={(props) => (
              <FormInput
                {...props}
                name="lastName"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                required
              />
            )}
          />
        </FormSection>

        <FormSection>
          <ButtonGroup>
            <Button type="submit" variant="primary">Next</Button>
          </ButtonGroup>
        </FormSection>
      </Form>

      {/* Non-form hero element moved outside, between forms */}
      <Box
        padding="lg"
        backgroundColor="info"
        marginVertical="md"
        borderRadius="md"
      >
        <Type>
          Please review your information before proceeding to account selection.
        </Type>
      </Box>

      {/* ========== FORM 2: ACCOUNT SELECTION ========== */}

      {/* Non-form heading moved outside second form */}
      <Type variant="h2" marginBottom="md" marginTop="lg">
        Step 2: Account Selection
      </Type>

      {/* Second logical form */}
      <Form onSubmit={handleAccountSubmit}>
        <FormSection>
          <FormItem
            label={<Type>Sort Code & Account</Type>}
            id="account"
            description={<Type>Enter your 6-digit sort code and account number</Type>}
            render={(props) => (
              <FormInput
                {...props}
                name="account"
                placeholder="000000 00000000"
                value={`${sortCode} ${accountNumber}`}
                onChange={(e) => {
                  const val = e.target.value.replace(/\s/g, '');
                  setSortCode(val.slice(0, 6));
                  setAccountNumber(val.slice(6, 14));
                }}
                required
              />
            )}
          />
        </FormSection>

        {/* Subheading moved outside form but rendered within layout */}
        <Type variant="subtitle" marginTop="md" marginBottom="md">
          Confirmation
        </Type>

        <FormSection>
          <FormMultiItem
            label={<Type>Terms & Conditions</Type>}
            render={(renderProps) => (
              <FormCheckbox
                label="I agree to the terms and conditions"
                checked={agreed}
                onChange={(e) => setAgreed(e.target.checked)}
                {...renderProps}
              />
            )}
          />
        </FormSection>

        <FormSection>
          <ButtonGroup>
            <Button type="submit" variant="primary">Submit</Button>
            <Button
              type="button"
              variant="secondary"
              onClick={() => {
                setFirstName('');
                setLastName('');
                setSortCode('');
                setAccountNumber('');
                setAgreed(false);
              }}
            >
              Clear All
            </Button>
          </ButtonGroup>
        </FormSection>
      </Form>
    </div>
  );
};
```

### Key Rules Enforcement Checklist

When migrating this anti-pattern, ensure:

| Rule | Status | Notes |
|---|---|---|
| ✅ All form controls wrapped in `<Form>` components | MUST | Each logical form = separate Form wrapper |
| ✅ Direct children of `<Form>` are ONLY FormSection/FormItem/FormMultiItem | MUST | No divs, headings, or layout elements |
| ✅ Non-form elements (headings, dividers, hero) moved OUTSIDE forms | MUST | These must be siblings to Form components |
| ✅ Each logical form = separate `<Form>` component | MUST | Don't nest multiple forms; split them |
| ✅ Shared state passed via props between form components | SHOULD | Alternative: use Redux if complex state |
| ✅ Each form has independent `onSubmit` handler | SHOULD | Enables independent submission workflows |
| ❌ NO `<mca-heading>`, `<mca-hero>`, `<mca-subheading>` directly in `<Form>` | NEVER | This breaks MCA2 structure |
| ❌ NO layout elements or divs directly in `<Form>` | NEVER | Use FormSection, FormItem, FormMultiItem only |

### Blueprint-React Imports for This Pattern

```typescript
import {
  Form,           // Form wrapper
  FormSection,    // Field group container
  FormItem,       // Single field wrapper
  FormMultiItem,  // Multi-field group (radios, checkboxes)
  FormInput,      // Text input
  FormCheckbox,   // Checkbox control
  FormSelect,     // Select dropdown
  Button,         // Submit/action button
  ButtonGroup,    // Button container
  Box,            // Layout container (for hero/content)
  Type            // Typography (for headings)
} from '@barclays/blueprint-react';
```

### Related References

- [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md) - FormSection and FormItem usage patterns
- [FORM_VALIDATION_PATTERNS.md](FORM_VALIDATION_PATTERNS.md) - Form validation across multiple forms
- [MIGRATION_RUNBOOK.md](MIGRATION_RUNBOOK.md) - Phase-by-phase migration strategy
- [ERROR_SCENARIOS.md](ERROR_SCENARIOS.md) - Common form structure errors and solutions
