# Error Scenarios & Solutions

Real-world error scenarios with solutions and prevention strategies.

Last Updated: March 25, 2026

---

## Scenario 1: TypeError: roles.map is not a function

**Error Message**:
```
Uncaught TypeError: roles.map is not a function
    at render (Dashboard.tsx:78:28)
```

**Root Cause**: API returned non-array or Redux state is corrupted

**Diagnosis**:
1. Check Network tab - is API response an array?
2. Check Redux DevTools - what is `state.roles.items`?
3. Add console.log to see actual type

**Solution - Option A**: Add validation in component
```typescript
const rolesData = useAppSelector(state => state.roles.items);
const roles = Array.isArray(rolesData) ? rolesData : [];
```

**Solution - Option B**: Fix API service layer
```typescript
fetchAll: async (): Promise<Role[]> => {
  const response = await api.service.call('fetchAllRoles');
  const data = response?.data;
  return Array.isArray(data) ? data : [];
}
```

**Prevention**:
- ✅ Use Mistake 23 defensive programming pattern
- ✅ Validate API responses at service layer (see API_RESPONSE_PATTERNS.md)
- ✅ Test with mock data that isn't an array to catch this

**Reference**: Mistake 23 in SKILL.md

---

## Scenario 2: Cannot read property 'api.roles' of undefined

**Error Message**:
```
TypeError: Cannot read property 'roles' of undefined
    at async fetchRoles (rolesSlice.ts:51:5)
```

**Root Cause**: API services not initialized before Redux thunks run

**Diagnosis**:
1. Check Entry.tsx useEffect initializes API
2. Check `props.api` is being passed
3. Add console.log in Entry.tsx to verify initialization

**Solution**:
```typescript
// src/Entry.tsx
useEffect(() => {
  console.log('Initializing API with:', props.api);
  if (props.api) {
    initializeApiServices(props.api);
    console.log('API initialized successfully');
  }
}, [props.api]);
```

**Prevention**:
- ✅ Always initialize API in Entry.tsx, NOT App.tsx
- ✅ Check Mistake 22 pattern
- ✅ Add initialization logs during development

**Reference**: Mistake 22 in SKILL.md

---

## Scenario 3: FormItem not rendering with children

**Error Message**:
```
Form field appears empty or FormInput not visible
```

**Root Cause**: Using children prop instead of render function

**Wrong Code**:
```typescript
<FormItem label="Name">
  <FormInput {...props} />
</FormItem>
```

**Solution**:
```typescript
<FormItem
  label="Name"
  render={(props) => <FormInput {...props} />}
/>
```

**Prevention**:
- ✅ Use BLUEPRINT_REACT_CORRECT_PATTERNS.md as reference
- ✅ Check component code before submitting PR
- ✅ Run build to catch TypeScript errors

**Reference**: Mistake 3 in SKILL.md

---

## Scenario 4: Dialog won't close

**Error Message**:
```
User clicks close button, dialog stays open
```

**Root Cause**: Missing or incorrect close handlers

**Wrong Code**:
```typescript
<Dialog isOpen={isOpen} head={<h2>Title</h2>}>
  Content
  <Button onClick={close}>Close</Button>
</Dialog>
```

**Solution**:
```typescript
<Dialog
  isOpen={isOpen}
  head={<h2>Title</h2>}
  foot={<Button onClick={close}>Close</Button>}
  onClickDismiss={close}
  onClickOverlay={close}
  onKeydownEscape={close}
>
  Content
</Dialog>
```

**Prevention**:
- ✅ Always implement all dismiss handlers
- ✅ Test ESC key, X button, and overlay click
- ✅ Check BLUEPRINT_REACT_CORRECT_PATTERNS.md

**Reference**: Mistake 4 in SKILL.md

---

## Scenario 5: Icons render huge/wrong size

**Error Message**:
```
Icons appear oversized, mismatched with text
```

**Root Cause**: No size prop or wrong icon name

**Wrong Code**:
```typescript
<Icon icon="tick-circle" />  // Missing size, wrong icon name
<Button media={<Icon icon="chevron-right" />}>  // No size
```

**Solution**:
```typescript
<Icon icon="tick" size="md" />  // Correct name + size
<Button media={<Icon icon="chevron-right" size="sm" />}>
```

**Prevention**:
- ✅ Always add size prop to Icon components
- ✅ Check BDL_TO_BLUEPRINT_REACT.md Section 8 for valid icon names
- ✅ Use Mistake 15 & 16 as checklist

**Reference**: Mistakes 15 & 16 in SKILL.md

---

## Scenario 6: API response validation error

**Error Message**:
```
Response validation failed: serviceId is a required field
TypeError: Cannot read property 'name' of undefined
```

**Root Cause**: API returned unexpected structure

**Diagnosis**:
1. Log API response to console
2. Check Network tab for actual response
3. Compare with expected type

**Solution**:
```typescript
// Add response validation
const response = await api.service.call('fetchAllServices');
const data = response?.data;

if (!Array.isArray(data)) {
  console.error('API returned non-array:', data);
  return [];
}

// Validate array items
return data.map(item => {
  if (!item.id) {
    console.warn('Service missing ID:', item);
    return { id: 'unknown', ...item };
  }
  return item;
});
```

**Prevention**:
- ✅ Implement response validation (see API_RESPONSE_PATTERNS.md)
- ✅ Add type guards for all API responses
- ✅ Test with corrupted/partial data

**Reference**: Mistake 23 in SKILL.md

---

## Scenario 7: Redux state duplication issues

**Error Message**:
```
State becomes inconsistent
Role updated but not in list
Select shows stale data
```

**Root Cause**: Data stored in multiple places

**Prevention**:
```typescript
// ❌ WRONG - Duplication
interface RolesState {
  items: Role[];
  selectedRole: Role;  // DUPLICATE!
}

// ✅ CORRECT - Single source of truth
interface RolesState {
  byId: { [id: string]: Role };
  selectedRoleId: string | null;
}

// Use selector to derive
export const selectSelectedRole = createSelector(
  [(state) => state.roles.byId, (state) => state.roles.selectedRoleId],
  (byId, id) => id ? byId[id] : null
);
```

**Prevention**:
- ✅ Follow REDUX_PATTERNS.md for normalized state
- ✅ Use selectors instead of storing derived data
- ✅ Review state design in code review

**Reference**: REDUX_PATTERNS.md

---

## Scenario 8: Form validation not showing

**Error Message**:
```
Form submits with invalid data
No error messages displayed
```

**Root Cause**: Validation not connected to form

**Solution**:
```typescript
// Ensure FormItem receives error
<FormItem
  label="Role Name"
  error={touched.name ? errors.name : undefined}  // Add error prop
  render={(props) => <FormInput {...props} />}
/>

// Or with React Hook Form
<FormItem
  label="Role Name"
  error={errors.name?.message}  // Add error prop
  render={(props) => <FormInput {...props} {...field} />}
/>
```

**Prevention**:
- ✅ Test form validation with empty/invalid data
- ✅ Check error props in component
- ✅ Use FORM_VALIDATION_PATTERNS.md

**Reference**: FORM_VALIDATION_PATTERNS.md

---

## Scenario 9: Async validation never completes

**Error Message**:
```
"Validating..." spinner never stops
Form stays disabled
```

**Root Cause**: Validation function doesn't resolve

**Solution**:
```typescript
// Good - always resolve (even if validation fails)
export const uniqueUsername = yup.string().test(
  'unique',
  'Username taken',
  async (value) => {
    if (!value) return true;
    try {
      const exists = await api.checkUsername(value);
      return !exists;  // Always returns (success or failure)
    } catch {
      return true;  // Don't block on error
    }
  }
);

// Bad - can hang if API hangs
export const uniqueUsername = yup.string().test(
  'unique',
  'Username taken',
  async (value) => {
    // If API hangs, test hangs forever!
    const exists = await api.checkUsername(value);
    return !exists;
  }
);
```

**Solution - Add timeout**:
```typescript
const checkWithTimeout = (promise: Promise<boolean>, timeoutMs = 5000) =>
  Promise.race([
    promise,
    new Promise<boolean>((_, reject) =>
      setTimeout(() => reject(new Error('Validation timeout')), timeoutMs)
    ),
  ]);
```

**Prevention**:
- ✅ Add try-catch to async validators
- ✅ Add timeout to async operations
- ✅ Test with slow/hanging API

**Reference**: FORM_VALIDATION_PATTERNS.md

---

## Scenario 10: Memory leaks from event listeners

**Error Message**:
```
Event listeners not removed
Memory grows over time
Old components still running
```

**Wrong Code**:
```typescript
useEffect(() => {
  window.addEventListener('resize', handleResize);
  // Missing cleanup!
}, []);
```

**Solution**:
```typescript
useEffect(() => {
  window.addEventListener('resize', handleResize);

  // Cleanup function
  return () => {
    window.removeEventListener('resize', handleResize);
  };
}, []);
```

**Prevention**:
- ✅ Always cleanup in useEffect
- ✅ Check DevTools Memory for detached DOM nodes
- ✅ Use profiler to detect memory leaks

**Reference**: DEBUGGING_GUIDE.md

---

## Scenario 11: Routing doesn't work (BrowserRouter used)

**Error Message**:
```
URL doesn't change when navigating
Back button doesn't work
Page reloads on navigation
```

**Root Cause**: Using BrowserRouter instead of MemoryRouter

**Wrong Code**:
```typescript
import { BrowserRouter } from 'react-router';

function App() {
  return <BrowserRouter><Routes>...</Routes></BrowserRouter>;
}
```

**Solution**:
```typescript
import { MemoryRouter } from 'react-router';

function App() {
  return <MemoryRouter><Routes>...</Routes></MemoryRouter>;
}
```

**Prevention**:
- ✅ MCA2 only supports MemoryRouter
- ✅ Check Mistake 22 in SKILL.md
- ✅ Build will show warnings about BrowserRouter

**Reference**: Mistake 22 in SKILL.md

---

## Scenario 12: TypeScript errors from non-existent components

**Error Message**:
```
Cannot find name 'FormGroup'
Cannot find module '@barclays/blueprint-react'
Module has no exported member 'DialogHeader'
```

**Root Cause**: Using non-existent Blueprint components

**Solution**: Check BLUEPRINT_REACT_REFERENCE.md for valid components
```typescript
// ❌ WRONG - These don't exist
import { FormGroup, DialogHeader, TableHead } from '@barclays/blueprint-react';

// ✅ CORRECT - These exist
import { FormItem, Dialog, Table } from '@barclays/blueprint-react';
```

**Prevention**:
- ✅ Check storybook before using component
- ✅ Run `npm run build` to catch TypeScript errors
- ✅ Read BLUEPRINT_REACT_CORRECT_PATTERNS.md

**Reference**: Mistakes 2-6 in SKILL.md

---

## Debugging Flowchart

```
Error Occurs
    ↓
Check Console Errors
    ↓
    Yes: Read Error → Find Scenario Above
    No: Check Redux DevTools
        ↓
        Look for Invalid State
        ↓
        Check Network Tab
        ↓
        Verify API Response
        ↓
        Check Component Props
        ↓
        Use React DevTools
        ↓
        Memory/Performance Issue?
```

---

## Quick Reference

| Error | Likely Cause | Solution | Reference |
|-------|--------------|----------|-----------|
| `.map is not a function` | Non-array data | Add Array.isArray() check | Mistake 23 |
| `Cannot read api.roles` | API not initialized | Initialize in Entry.tsx | Mistake 22 |
| FormItem empty | Using children | Use render function | Mistake 3 |
| Dialog won't close | Missing handlers | Add all dismiss handlers | BLUEPRINT_PATTERNS |
| Icon too large | No size prop | Add size="md" | Mistake 15 |
| API response error | Unexpected structure | Validate response | API_RESPONSE_PATTERNS |
| Stale data | Duplication in state | Normalize state | REDUX_PATTERNS |
| Form validation fails | No error display | Add error prop | FORM_VALIDATION_PATTERNS |
| Memory leak | Event not cleaned up | Add cleanup function | useEffect cleanup |
| Navigation broken | BrowserRouter used | Use MemoryRouter | Mistake 22 |

---

## References
- SKILL.md Mistakes 1-23
- COMPONENT_AUDIT_CHECKLIST.md
- DEBUGGING_GUIDE.md
- API_RESPONSE_PATTERNS.md
- REDUX_PATTERNS.md
