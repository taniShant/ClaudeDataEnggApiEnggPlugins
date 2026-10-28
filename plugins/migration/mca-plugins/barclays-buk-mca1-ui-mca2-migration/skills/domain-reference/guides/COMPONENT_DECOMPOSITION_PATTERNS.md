# Component Decomposition Patterns

**Purpose**: Guide for breaking monolithic MCA2 React components into focused, maintainable sub-components after initial migration from MCA1 JMVC.

**Last Updated**: May 7, 2026
**Version**: 1.0

---

## Why Decompose After Migration?

Initial MCA1→MCA2 migration often produces large single-file components because JMVC pages are translated 1:1 into React components. Post-migration, these should be decomposed for:
- Readability (components > 300 lines are hard to navigate)
- Testability (focused components are easier to unit test)
- Reusability (common patterns extracted once, used everywhere)
- Maintainability (changes are scoped to relevant sub-component)

---

## Pattern 1: Extract Repeated Component Patterns

### Principle
When the **same UI pattern** appears 3+ times across a page or across multiple pages, extract it into a shared reusable component in `src/components/`. This applies to **any** Blueprint component — radios, inputs, alerts, loading indicators, info panels, action button groups, etc.

### How to Identify Candidates
- Look for blocks of JSX that differ only in a few values (label, field name, value, callback)
- The structure is identical but the data/bindings change
- Copy-pasting the block and changing 2–4 values = extraction candidate

### Extraction Steps
1. Identify the varying parts → those become **props**
2. Identify the fixed structure → that becomes the **component body**
3. Create `src/components/{ComponentName}.tsx` with a typed interface
4. Replace all occurrences with the new component

---

### Example A: YesNoRadioGroup (FormMultiItem + FormRadio)

**Problem**: The Yes/No radio toggle appears 12 times in one page.

**Before** (repeated 12 times, only `label`, `fieldName`, and `formValues.X` vary):
```typescript
<FormMultiItem
  label={<Type>Out of red alert</Type>}
  render={(renderProps: any) => (
    <>
      <FormRadio
        {...renderProps}
        label="Yes"
        value="yes"
        checked={formValues.outOfRedEnabled === 'yes'}
        onChange={() => handleFieldChange('outOfRedEnabled', 'yes')}
        id="radio-out-of-red-yes" />
      <FormRadio
        {...renderProps}
        label="No"
        value="no"
        checked={formValues.outOfRedEnabled === 'no'}
        onChange={() => handleFieldChange('outOfRedEnabled', 'no')}
        id="radio-out-of-red-no" />
    </>
  )} />
```

**After** — `src/components/YesNoRadioGroup.tsx`:
```typescript
import React from 'react';
import { FormMultiItem, FormRadio, Type } from '@barclays/blueprint-react';

interface YesNoRadioGroupProps {
  label: string;
  fieldName: string;
  value: string;
  onChange: (field: string, value: string) => void;
}

function YesNoRadioGroup({
  label, fieldName, value, onChange
}: YesNoRadioGroupProps): React.ReactElement {
  return (
    <FormMultiItem
      label={<Type>{label}</Type>}
      render={(renderProps: any) => (
        <>
          <FormRadio
            {...renderProps}
            label="Yes"
            value="yes"
            checked={value === 'yes'}
            onChange={() => onChange(fieldName, 'yes')}
            id={`radio-${fieldName}-yes`} />
          <FormRadio
            {...renderProps}
            label="No"
            value="no"
            checked={value === 'no'}
            onChange={() => onChange(fieldName, 'no')}
            id={`radio-${fieldName}-no`} />
        </>
      )} />
  );
}

export default YesNoRadioGroup;
```

**Usage** (~15 lines → 5):
```typescript
<YesNoRadioGroup
  label="Out of red alert"
  fieldName="outOfRedEnabled"
  value={formValues.outOfRedEnabled}
  onChange={onFieldChange} />
```

---

### Example B: LabelledFormInput (FormItem + FormInput with validation)

**Problem**: The same FormItem + FormInput + error display pattern repeats 6+ times.

**Before** (repeated per field):
```typescript
<FormItem
  id="field-mobile-number"
  label={<Type>Mobile number</Type>}
  error={validationErrors.mobileNumber && <Type color="error">{validationErrors.mobileNumber}</Type>}
  render={(props: any) => (
    <FormInput
      {...props}
      value={formValues.mobileNumber}
      onChange={(e) => handleFieldChange('mobileNumber', e.target.value)}
      placeholder="07XXXXXXXXX"
      maxLength={11}
      id="input-mobile-number" />
  )} />
```

**After** — `src/components/LabelledFormInput.tsx`:
```typescript
import React from 'react';
import { FormItem, FormInput, Type } from '@barclays/blueprint-react';

interface LabelledFormInputProps {
  fieldName: string;
  label: string;
  value: string;
  onChange: (field: string, value: string) => void;
  error?: string;
  placeholder?: string;
  maxLength?: number;
  inputMode?: string;
}

function LabelledFormInput({
  fieldName, label, value, onChange, error, placeholder, maxLength, inputMode
}: LabelledFormInputProps): React.ReactElement {
  return (
    <FormItem
      id={`field-${fieldName}`}
      label={<Type>{label}</Type>}
      error={error && <Type color="error">{error}</Type>}
      render={(props: any) => (
        <FormInput
          {...props}
          value={value}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => onChange(fieldName, e.target.value)}
          placeholder={placeholder}
          maxLength={maxLength}
          inputMode={inputMode}
          id={`input-${fieldName}`} />
      )} />
  );
}

LabelledFormInput.defaultProps = {
  error: undefined,
  placeholder: undefined,
  maxLength: undefined,
  inputMode: undefined
};

export default LabelledFormInput;
```

**Usage**:
```typescript
<LabelledFormInput
  fieldName="mobileNumber"
  label="Mobile number"
  value={formValues.mobileNumber}
  onChange={onFieldChange}
  error={validationErrors.mobileNumber}
  placeholder="07XXXXXXXXX"
  maxLength={11} />
```

---

### Example C: InfoAlert (Alert with icon pattern)

**Problem**: Info alerts with the same structure appear 3+ times (joint account, customer relationship, eligibility notes).

**After** — `src/components/InfoAlert.tsx`:
```typescript
import React from 'react';
import {
  Section, SectionItem, Alert, Icon, Type
} from '@barclays/blueprint-react';

interface InfoAlertProps {
  heading: string;
  message: string;
  id: string;
  variant?: 'info' | 'warning' | 'error' | 'success';
}

function InfoAlert({
  heading, message, id, variant
}: InfoAlertProps): React.ReactElement {
  return (
    <Section>
      <SectionItem>
        <Alert
          variant={variant}
          head={<Type weight="medium">{heading}</Type>}
          media={<Icon icon={variant === 'warning' ? 'warning' : 'info'} size="md" />}
          id={id}>
          <Type>{message}</Type>
        </Alert>
      </SectionItem>
    </Section>
  );
}

InfoAlert.defaultProps = {
  variant: 'info'
};

export default InfoAlert;
```

---

### When to Extract — Rule of Three

| Occurrences | Action |
|-------------|--------|
| 1 | Leave inline |
| 2 | Consider extracting if complex (> 10 lines) |
| 3+ | **Always extract** to shared component |

### Benefits
- Reduces total line count significantly
- Single source of truth for UI pattern (update once, applied everywhere)
- Consistent IDs, accessibility, and styling
- Easier to test in isolation
- Clear, typed props interface documents usage

---

## Pattern 2: PageLoader (Shared Loading State)

### Problem
The full-page loading pattern (`Page > Section > SectionItem > Loading`) repeats across multiple pages.

### Shared Component (`src/components/PageLoader.tsx`)
```typescript
import React from 'react';
import {
  Page, Section, SectionItem, Loading
} from '@barclays/blueprint-react';

interface PageLoaderProps {
  ariaLabel?: string;
}

function PageLoader({ ariaLabel }: PageLoaderProps): React.ReactElement {
  return (
    <Page>
      <Section>
        <SectionItem>
          <Loading size="lg" shape="circle" ariaLabel={ariaLabel || 'Loading'} />
        </SectionItem>
      </Section>
    </Page>
  );
}

PageLoader.defaultProps = {
  ariaLabel: 'Loading'
};

export default PageLoader;
```

### Usage
```typescript
if (loading) {
  return <PageLoader ariaLabel="Loading accounts" />;
}
```

### Benefits
- Consistent loading UX across all pages
- Uses Blueprint `Loading` component (Mistake 27 — not Icon spinner)
- Accessible with `ariaLabel`
- Single point to update loading appearance

---

## Pattern 3: Page Decomposition (Folder Structure)

### Problem
A monolithic page component (500–1000+ lines) handling multiple distinct UI sections: form groups, dialogs, action buttons, conditional alerts.

### Solution — Convert file to folder with sub-components

**Before:**
```
src/pages/AlertSettings.tsx    (1013 lines)
```

**After:**
```
src/pages/AlertSettings/
├── index.tsx                  # Orchestrator (hooks, state, handlers, composition)
├── PhoneSettings.tsx          # Mobile number, confirm, short name, marketing
├── TransactionAlerts.tsx      # Large credit/debit thresholds
├── BalanceAlerts.tsx          # Weekly balance day selector
├── OutOfRedAlerts.tsx         # All overdraft-related alert toggles
├── SavingsAlerts.tsx          # Savings threshold, monthly balance, interest rate
├── SuspendCancelSection.tsx   # Suspend/Cancel/Reactivate buttons
├── ConfirmDialog.tsx          # Confirmation dialog with terms
└── TermsDialog.tsx            # Terms and conditions modal
```

### Import Resolution
The import in `App.tsx` does NOT need to change:
```typescript
import AlertSettings from './pages/AlertSettings';
// Resolves to ./pages/AlertSettings/index.tsx automatically
```

### Props Interface Pattern

Each section component receives only what it needs:

```typescript
interface PhoneSettingsProps {
  formValues: {
    mobileNumber: string;
    confirmMobile: string;
    shortName: string;
    useForMarketing: string;
  };
  onFieldChange: (field: string, value: string) => void;
  validationErrors: ValidationErrors;
  selectedAccount: {
    isJointAccount?: boolean;
    jointHolderName?: string;
    customerRelationship?: string;
  };
}
```

### Orchestrator (`index.tsx`) Responsibilities

The main `index.tsx` is kept slim — it owns:
1. **All hooks** (`useEffect`, `useSelector`, `useDispatch`, `useNavigate`)
2. **All handler functions** (`handleSubmit`, `handleConfirm`, `handleBack`, etc.)
3. **Conditional rendering logic** (which sections to show based on account type)
4. **Composition** of sub-components with the right props

```typescript
function AlertSettings(): React.ReactElement {
  // ... hooks, state, handlers ...

  return (
    <Page>
      {/* Header section */}
      <Section>...</Section>

      {/* Error display */}
      {saveError && <Section>...</Section>}

      {/* Composed sub-components */}
      <PhoneSettings
        formValues={formValues}
        onFieldChange={handleFieldChange}
        validationErrors={validationErrors}
        selectedAccount={selectedAccount} />

      {isCurrentAccount && (
        <TransactionAlerts
          formValues={formValues}
          onFieldChange={handleFieldChange}
          validationErrors={validationErrors} />
      )}

      {/* ... more sections ... */}

      <ConfirmDialog
        isOpen={isConfirmVisible}
        onConfirm={handleConfirm}
        onDismiss={handleDialogDismiss}
        /* ... */ />

      <TermsDialog isOpen={isTermsVisible} onClose={handleCloseTerms} />
    </Page>
  );
}
```

---

## Pattern 4: Dialog Extraction

### Problem
Dialogs with complex content (forms, conditional rendering, action buttons) bloat the parent component.

### Solution — Extract to dedicated component

```typescript
// ConfirmDialog.tsx
interface ConfirmDialogProps {
  isOpen: boolean;
  actionType: string | null;
  termsAccepted: boolean;
  saving: boolean;
  accountName: string;
  accountDisplay: string;
  onConfirm: () => void;
  onDismiss: () => void;
  onAcceptTerms: () => void;
  onViewTerms: () => void;
}

function ConfirmDialog({
  isOpen, actionType, termsAccepted, saving,
  accountName, accountDisplay,
  onConfirm, onDismiss, onAcceptTerms, onViewTerms
}: ConfirmDialogProps): React.ReactElement {
  return (
    <Dialog
      isOpen={isOpen}
      id="dialog-confirm"
      head={<Type element="h2" size="lg">Confirm Changes</Type>}
      foot={/* action buttons */}
      onClickDismiss={onDismiss}>
      {/* dialog content */}
    </Dialog>
  );
}
```

### Key Rules
- Dialog uses **slot properties** (`head`, `foot`, `children`) — follows Mistake 4
- Pass all callbacks as props (don't dispatch Redux inside the dialog component)
- Keep the dialog stateless — all state lives in the parent orchestrator

---

## Pattern 5: Suspend/Cancel/Reactivate Section

### Problem
Action buttons with conditional visibility (show suspend/cancel when active, show reactivate when suspended) embedded in the main component.

### Solution

```typescript
interface SuspendCancelSectionProps {
  isActive: boolean;
  isSuspended: boolean;
  onSuspend: () => void;
  onCancel: () => void;
  onReactivate: () => void;
}

function SuspendCancelSection({
  isActive, isSuspended, onSuspend, onCancel, onReactivate
}: SuspendCancelSectionProps): React.ReactElement {
  return (
    <>
      {isActive && (
        <Section>
          <SectionItem>
            <Type element="h2" size="lg" marginBottom>
              Suspend or Cancel Alerts
            </Type>
            <Arrange>
              <ArrangeItem>
                <Button variant="secondary" onClick={onSuspend} id="btn-suspend-alerts">
                  <Type>Suspend Alerts</Type>
                </Button>
              </ArrangeItem>
              <ArrangeItem>
                <Button variant="secondary" status="danger" onClick={onCancel} id="btn-cancel-alerts">
                  <Type>Cancel Alerts</Type>
                </Button>
              </ArrangeItem>
            </Arrange>
          </SectionItem>
        </Section>
      )}

      {isSuspended && (
        <Section>
          <SectionItem>
            <Alert
              variant="warning"
              head={<Type weight="medium">Alerts are currently suspended</Type>}
              media={<Icon icon="warning" size="md" />}>
              <Type>Your SMS alerts are suspended. Reactivate below.</Type>
            </Alert>
            <Button variant="primary" onClick={onReactivate} id="btn-reactivate-alerts">
              <Type>Reactivate Alerts</Type>
            </Button>
          </SectionItem>
        </Section>
      )}
    </>
  );
}
```

---

## Decomposition Decision Checklist

Use this checklist to decide whether a component should be decomposed:

| Criterion | Threshold | Action |
|-----------|-----------|--------|
| Line count | > 300 lines | Decompose into sections |
| Repeated patterns | 3+ occurrences | Extract shared component |
| Distinct UI sections | 3+ unrelated sections | Split into sub-components |
| Dialogs | Any dialog with > 20 lines content | Extract to own file |
| Conditional sections | 2+ sections with different visibility | Extract each section |

---

## File Placement Guidelines

| Type | Location | Example |
|------|----------|---------|
| Reusable across pages | `src/components/` | `YesNoRadioGroup.tsx`, `PageLoader.tsx` |
| Page-specific sections | `src/pages/{PageName}/` | `PhoneSettings.tsx`, `BalanceAlerts.tsx` |
| Page orchestrator | `src/pages/{PageName}/index.tsx` | Main component with hooks and composition |
| **All interfaces** | **`src/interfaces/index.ts`** | All props interfaces in one place |

---

## Pattern 6: Centralised Interfaces (`src/interfaces/`)

### Principle
**Never define interfaces inside `.tsx` component files.** All props interfaces must live in a dedicated `src/interfaces/` folder. Components import their interface from there.

This applies to:
- Component props interfaces
- Shared data shape types
- Callback signatures
- Any TypeScript `interface` or `type` used by multiple files

### Folder Structure
```
src/interfaces/
└── index.ts          # All exported interfaces
```

For larger projects with many interfaces, split by domain:
```
src/interfaces/
├── index.ts          # Re-exports everything
├── components.ts     # Shared component props (PageLoader, YesNoRadioGroup)
└── alertSettings.ts  # AlertSettings page sub-component props
```

### Example — `src/interfaces/index.ts`
```typescript
import { ValidationErrors } from '../utils/validation';

// Shared component interfaces
export interface YesNoRadioGroupProps {
  label: string;
  fieldName: string;
  value: string;
  onChange: (field: string, value: string) => void;
}

export interface PageLoaderProps {
  ariaLabel?: string;
}

// AlertSettings sub-component interfaces
export interface PhoneSettingsProps {
  formValues: {
    mobileNumber: string;
    confirmMobile: string;
    shortName: string;
    useForMarketing: string;
  };
  onFieldChange: (field: string, value: string) => void;
  validationErrors: ValidationErrors;
  selectedAccount: {
    isJointAccount?: boolean;
    jointHolderName?: string;
    customerRelationship?: string;
  };
}

export interface TransactionAlertsProps {
  formValues: {
    largeCreditThreshold: string;
    largeDebitThreshold: string;
  };
  onFieldChange: (field: string, value: string) => void;
  validationErrors: ValidationErrors;
}

// ... remaining interfaces
```

### Usage in Components
```typescript
// src/components/YesNoRadioGroup.tsx
import React from 'react';
import { FormMultiItem, FormRadio, Type } from '@barclays/blueprint-react';
import { YesNoRadioGroupProps } from '../interfaces';

function YesNoRadioGroup({
  label, fieldName, value, onChange
}: YesNoRadioGroupProps): React.ReactElement {
  // ...
}
```

```typescript
// src/pages/AlertSettings/PhoneSettings.tsx
import React from 'react';
import { Section, SectionItem, Type, Grid, FormItem, FormInput } from '@barclays/blueprint-react';
import { PhoneSettingsProps } from '../../interfaces';

function PhoneSettings({
  formValues, onFieldChange, validationErrors, selectedAccount
}: PhoneSettingsProps): React.ReactElement {
  // ...
}
```

### Benefits
- **Single source of truth** — all type contracts in one place
- **Easy discoverability** — developers see all available types at a glance
- **Refactoring safety** — rename a prop once, compiler catches all usages
- **Cleaner components** — `.tsx` files contain only rendering logic, no type definitions
- **Reusability** — interfaces can be imported by tests, utilities, or other components without circular deps

### Rules
1. Component files (`.tsx`) must **never** contain `interface` or `type` declarations for their own props
2. Utility types internal to one function (e.g., a local mapped type) may remain local
3. If an interface is used by **only one file**, it still goes in `src/interfaces/` — consistency over convenience
4. Import path from components: `'../interfaces'` or `'../../interfaces'`

---

## TypeScript Tips for Props

### Match nullable types from Redux state
```typescript
// If uiSlice has: actionType: string | null
export interface ConfirmDialogProps {
  actionType: string | null;  // Match the Redux type exactly
}
```

### Match actual account data types
```typescript
// If accountsSlice has: overdraftLimit: string
export interface OutOfRedAlertsProps {
  overdraftLimit: string;  // Not number! Match the source type
}
```

### Import shared types for composition
```typescript
// Re-use existing types from utils
import { ValidationErrors } from '../utils/validation';

export interface SavingsAlertsProps {
  formValues: { ... };
  onFieldChange: (field: string, value: string) => void;
  validationErrors: ValidationErrors;  // Imported, not redefined
}
```

---

## Verification After Decomposition

1. **`npm run lint`** — No new lint errors in decomposed files
2. **`npm test`** — All existing tests still pass (components render identically)
3. **`npm run build`** — TypeScript compilation succeeds (no type mismatches)
4. **Import resolution** — `./pages/AlertSettings` resolves to `./pages/AlertSettings/index.tsx`
5. **Functional parity** — UI renders identically before and after decomposition

---

## Common Pitfalls

### 1. Type mismatches after extraction
When extracting props interfaces, ensure types match the source (Redux state, account model). A `string` in the slice must be `string` in the prop, not `number`.

### 2. Indentation lint errors
The `react/jsx-indent` rule checks JSX element indentation relative to parent. When moving JSX into a shallower component, the indentation level changes. Run `npm run lint:fix` after extraction.

### 3. Missing `defaultProps` for optional props
The `react/require-default-props` rule requires `defaultProps` for optional props in function components. Pattern:
```typescript
function PageLoader({ ariaLabel }: PageLoaderProps): React.ReactElement { ... }

PageLoader.defaultProps = {
  ariaLabel: 'Loading'
};
```

### 4. Forgetting to delete the original file
After creating `src/pages/AlertSettings/index.tsx`, delete the original `src/pages/AlertSettings.tsx` — otherwise TypeScript may resolve imports ambiguously.

---

## Summary

| Step | Action |
|------|--------|
| 1 | Identify repeated patterns → extract to `src/components/` |
| 2 | Identify distinct page sections → extract to `src/pages/{Page}/` |
| 3 | Move **all interfaces** to `src/interfaces/index.ts` — never in `.tsx` files |
| 4 | Keep orchestrator slim in `index.tsx` (hooks + handlers + composition) |
| 5 | Props carry only what each sub-component needs |
| 6 | Delete original monolithic file |
| 7 | Verify: lint, test, build |
