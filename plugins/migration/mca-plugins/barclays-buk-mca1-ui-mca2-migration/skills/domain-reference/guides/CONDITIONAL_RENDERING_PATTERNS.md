# Conditional Rendering Patterns for MCA2

Patterns for show/hide logic, dynamic fields, and state-dependent UI in migrated MCA2 applications.

Last Updated: 2026-05-19 | Version: 1.0.0

---

## Table of Contents

1. [Basic Conditional Rendering](#basic-conditional-rendering)
2. [Field Visibility Based on Selection](#field-visibility-based-on-selection)
3. [Complex Visibility Rules](#complex-visibility-rules)
4. [Resetting Hidden Field Values](#resetting-hidden-field-values)
5. [Dynamic Field Arrays](#dynamic-field-arrays)
6. [Loading, Empty, and Error States](#loading-empty-and-error-states)
7. [Conditional FormItem with Blueprint](#conditional-formitem-with-blueprint)
8. [Migration from EJS Conditionals](#migration-from-ejs-conditionals)

---

## Basic Conditional Rendering

### Short-Circuit (`&&`)

Use for simple show/hide with no else branch.

```typescript
// Show error only when it exists
{error && <Type color="error">{error}</Type>}

// Show section only for admins
{userRole === 'admin' && <AdminPanel />}
```

### Ternary

Use when both branches render something.

```typescript
// Toggle between two views
{isEditing ? <RoleForm role={role} /> : <RoleDetail role={role} />}
```

### Early Return

Use when a condition short-circuits the entire component.

```typescript
const RoleDetail: React.FC<{ roleId: string }> = ({ roleId }) => {
  const role = useAppSelector((state) => state.roles.items.find((r) => r.id === roleId));

  if (!role) return <Type>Role not found</Type>;

  return (
    <Section>
      <SectionItem><Type variant="heading">{role.name}</Type></SectionItem>
      <SectionItem><Type>{role.description}</Type></SectionItem>
    </Section>
  );
};
```

---

## Field Visibility Based on Selection

This is the most common MCA1→MCA2 pattern. In MCA1 (EJS), fields are shown/hidden with `<%if%>` blocks bound to controller state. In MCA2, use React state.

### Simple: Show Field When Radio = 'Yes'

```typescript
// src/pages/AccountSetup/AccountSetup.tsx
import React, { useState } from 'react';
import { FormItem, FormInput, FormMultiItem, FormRadio, Type } from '@barclays/blueprint-react';

const AccountSetup: React.FC = () => {
  const [hasProxy, setHasProxy] = useState<'yes' | 'no' | null>(null);
  const [proxyName, setProxyName] = useState('');

  return (
    <Section>
      <SectionItem>
        <FormMultiItem
          label={<Type>Do you have a proxy?</Type>}
          render={(props) => (
            <>
              <FormRadio
                {...props}
                id="proxy-yes"
                label="Yes"
                checked={hasProxy === 'yes'}
                onChange={() => setHasProxy('yes')}
              />
              <FormRadio
                {...props}
                id="proxy-no"
                label="No"
                checked={hasProxy === 'no'}
                onChange={() => setHasProxy('no')}
              />
            </>
          )}
        />
      </SectionItem>

      {hasProxy === 'yes' && (
        <SectionItem>
          <FormItem
            label={<Type>Proxy Name</Type>}
            render={(props) => (
              <FormInput
                {...props}
                id="proxyName"
                value={proxyName}
                onChange={(e) => setProxyName(e.target.value)}
              />
            )}
          />
        </SectionItem>
      )}
    </Section>
  );
};
```

### Multiple Dependent Fields

```typescript
const [accountType, setAccountType] = useState<'personal' | 'business' | null>(null);

// Fields that depend on accountType
{accountType === 'business' && (
  <>
    <SectionItem>
      <FormItem
        label={<Type>Company Name</Type>}
        render={(props) => (
          <FormInput {...props} id="companyName" value={companyName} onChange={...} />
        )}
      />
    </SectionItem>
    <SectionItem>
      <FormItem
        label={<Type>Registration Number</Type>}
        render={(props) => (
          <FormInput {...props} id="regNumber" value={regNumber} onChange={...} />
        )}
      />
    </SectionItem>
  </>
)}
```

---

## Complex Visibility Rules

When visibility depends on multiple conditions, extract the logic into a named variable or function.

### Named Visibility Flags

```typescript
const AccountForm: React.FC = () => {
  const [accountType, setAccountType] = useState<string>('');
  const [country, setCountry] = useState<string>('');
  const [hasOverdraft, setHasOverdraft] = useState(false);

  // Named visibility conditions — clear intent
  const showTaxFields = accountType === 'business' && country !== '';
  const showOverdraftLimit = hasOverdraft && accountType !== 'savings';
  const showInternationalFields = country !== '' && country !== 'GB';

  return (
    <Section>
      {/* ... always-visible fields ... */}

      {showTaxFields && (
        <SectionItem>
          <FormItem label={<Type>Tax ID</Type>} render={(props) => (
            <FormInput {...props} id="taxId" value={taxId} onChange={...} />
          )} />
        </SectionItem>
      )}

      {showOverdraftLimit && (
        <SectionItem>
          <FormItem label={<Type>Overdraft Limit</Type>} render={(props) => (
            <FormInput {...props} id="overdraftLimit" value={overdraftLimit} onChange={...} />
          )} />
        </SectionItem>
      )}

      {showInternationalFields && (
        <SectionItem>
          <FormItem label={<Type>SWIFT Code</Type>} render={(props) => (
            <FormInput {...props} id="swiftCode" value={swiftCode} onChange={...} />
          )} />
        </SectionItem>
      )}
    </Section>
  );
};
```

### Visibility Map for Many Fields

When a form has 10+ conditionally visible fields, use a configuration object:

```typescript
interface FieldVisibility {
  taxId: boolean;
  swiftCode: boolean;
  overdraftLimit: boolean;
  proxyName: boolean;
}

function computeVisibility(formState: FormState): FieldVisibility {
  return {
    taxId: formState.accountType === 'business' && formState.country !== '',
    swiftCode: formState.country !== '' && formState.country !== 'GB',
    overdraftLimit: formState.hasOverdraft && formState.accountType !== 'savings',
    proxyName: formState.hasProxy === 'yes',
  };
}

// In component:
const visibility = useMemo(() => computeVisibility(formState), [formState]);

{visibility.taxId && <TaxIdField />}
{visibility.swiftCode && <SwiftCodeField />}
```

---

## Resetting Hidden Field Values

When a field becomes hidden, its value should be cleared to prevent submitting stale data.

```typescript
const [hasProxy, setHasProxy] = useState<'yes' | 'no' | null>(null);
const [proxyName, setProxyName] = useState('');

const handleProxyChange = (value: 'yes' | 'no') => {
  setHasProxy(value);
  // Clear dependent field when hiding it
  if (value === 'no') {
    setProxyName('');
  }
};
```

### With useEffect (for complex dependencies)

```typescript
useEffect(() => {
  // Reset business fields when switching to personal account
  if (accountType !== 'business') {
    setCompanyName('');
    setRegNumber('');
    setTaxId('');
  }
}, [accountType]);
```

---

## Dynamic Field Arrays

For repeating field groups (add/remove phone numbers, addresses, etc.).

```typescript
interface PhoneEntry {
  id: string;
  type: string;
  number: string;
}

const ContactForm: React.FC = () => {
  const [phones, setPhones] = useState<PhoneEntry[]>([
    { id: crypto.randomUUID(), type: 'mobile', number: '' },
  ]);

  const addPhone = () => {
    setPhones([...phones, { id: crypto.randomUUID(), type: 'mobile', number: '' }]);
  };

  const removePhone = (id: string) => {
    setPhones(phones.filter((p) => p.id !== id));
  };

  const updatePhone = (id: string, field: keyof PhoneEntry, value: string) => {
    setPhones(phones.map((p) => (p.id === id ? { ...p, [field]: value } : p)));
  };

  return (
    <Section>
      {phones.map((phone) => (
        <SectionItem key={phone.id}>
          <FormItem
            label={<Type>Phone Number</Type>}
            render={(props) => (
              <FormInput
                {...props}
                id={`phone-${phone.id}`}
                value={phone.number}
                onChange={(e) => updatePhone(phone.id, 'number', e.target.value)}
              />
            )}
          />
          {phones.length > 1 && (
            <Button variant="subtle" status="danger" onClick={() => removePhone(phone.id)}>
              Remove
            </Button>
          )}
        </SectionItem>
      ))}
      <SectionItem>
        <Button variant="secondary" onClick={addPhone}>Add Phone</Button>
      </SectionItem>
    </Section>
  );
};
```

---

## Loading, Empty, and Error States

Every component that fetches data must handle three states.

```typescript
const RoleList: React.FC = () => {
  const { items: roles, loading, error } = useAppSelector((state) => state.roles);

  // Error state
  if (error) {
    return (
      <Section>
        <SectionItem>
          <Type color="error">Failed to load roles: {error}</Type>
          <Button variant="secondary" onClick={() => dispatch(fetchRoles())}>Retry</Button>
        </SectionItem>
      </Section>
    );
  }

  // Loading state
  if (loading) {
    return <Loading size="lg" shape="circle" ariaLabel="Loading roles" />;
  }

  // Empty state
  if (!Array.isArray(roles) || roles.length === 0) {
    return (
      <Section>
        <SectionItem>
          <Type>No roles found. Create your first role to get started.</Type>
        </SectionItem>
      </Section>
    );
  }

  // Success state
  return <RoleTable roles={roles} />;
};
```

---

## Conditional FormItem with Blueprint

When conditionally showing/hiding FormItems, keep the layout stable by wrapping in `SectionItem`.

```typescript
// ✓ CORRECT — SectionItem wraps the conditional, layout stays stable
<Section>
  <SectionItem>
    <FormItem label={<Type>Name</Type>} render={(props) => (
      <FormInput {...props} id="name" value={name} onChange={...} />
    )} />
  </SectionItem>

  {showEmail && (
    <SectionItem>
      <FormItem label={<Type>Email</Type>} render={(props) => (
        <FormInput {...props} id="email" value={email} onChange={...} />
      )} />
    </SectionItem>
  )}
</Section>
```

```typescript
// ❌ WRONG — conditional inside SectionItem creates empty whitespace when hidden
<SectionItem>
  {showEmail && (
    <FormItem label={<Type>Email</Type>} render={(props) => (
      <FormInput {...props} id="email" value={email} onChange={...} />
    )} />
  )}
</SectionItem>
```

---

## Migration from EJS Conditionals

### MCA1 EJS Pattern

```html
<%if(vm.hasProxy === 'yes'){%>
  <mca-input id="proxyName" label="Proxy Name" value="<%=vm.proxyName%>" />
<%}%>
```

### MCA2 React Equivalent

```typescript
const [hasProxy, setHasProxy] = useState<string>('');
const [proxyName, setProxyName] = useState('');

// In JSX:
{hasProxy === 'yes' && (
  <SectionItem>
    <FormItem
      label={<Type>Proxy Name</Type>}
      render={(props) => (
        <FormInput {...props} id="proxyName" value={proxyName} onChange={(e) => setProxyName(e.target.value)} />
      )}
    />
  </SectionItem>
)}
```

### MCA1 EJS Loop with Conditional

```html
<%for(var i=0; i<items.length; i++){%>
  <%if(items[i].status === 'active'){%>
    <mca-text><%=items[i].name%></mca-text>
  <%}%>
<%}%>
```

### MCA2 React Equivalent

```typescript
const activeItems = useMemo(
  () => (Array.isArray(items) ? items.filter((item) => item.status === 'active') : []),
  [items]
);

// In JSX:
{activeItems.map((item) => (
  <Type key={item.id}>{item.name}</Type>
))}
```
