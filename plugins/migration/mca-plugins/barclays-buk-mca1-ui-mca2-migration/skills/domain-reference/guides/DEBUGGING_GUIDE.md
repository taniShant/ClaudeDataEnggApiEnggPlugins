# Debugging Guide for MCA2

Strategies and tools for debugging MCA2 React applications.

Last Updated: March 25, 2026

---

## Common Error Messages & Solutions

### TypeError: roles.map is not a function

**Cause**: Redux state contains non-array data before calling `.map()`

**Fix**:
```typescript
// Check Mistake 23: API Response Validation
const rolesData = useAppSelector(state => state.roles.items);
const roles = Array.isArray(rolesData) ? rolesData : [];

{roles.map(role => <option key={role.id}>{role.name}</option>)}
```

**Debug**:
- Add console.log in Redux reducer to see actual data
- Check Network tab for API response structure
- Verify API services return arrays (see API_RESPONSE_PATTERNS.md)

---

### Cannot read property 'api.roles' of undefined

**Cause**: API services not initialized (Entry.tsx initialization failed)

**Fix**:
- Verify Entry.tsx has useEffect initialization (see Mistake 22)
- Check that `props.api` is being passed from MCA2 launcher
- Ensure initializeApiServices() is called before App renders

**Debug**:
```typescript
// Add logging in Entry.tsx
useEffect(() => {
  console.log('Entry: props.api =', props.api);
  if (props.api) {
    console.log('Initializing API services...');
    initializeApiServices(props.api);
    console.log('API services initialized');
  }
}, [props.api]);
```

---

### FormItem children not rendering

**Cause**: Using children instead of render function pattern

**Fix**:
```typescript
// ❌ WRONG
<FormItem label="Name">
  <FormInput />
</FormItem>

// ✅ CORRECT
<FormItem
  label="Name"
  render={(props) => <FormInput {...props} />}
/>
```

---

### Dialog not closing

**Cause**: Missing onClickDismiss or using wrong prop names

**Fix**:
```typescript
// ✅ CORRECT
<Dialog
  isOpen={isOpen}
  head={<h2>Title</h2>}
  foot={<Button onClick={onClose}>Close</Button>}
  onClickDismiss={onClose}
  onClickOverlay={onClose}
  onKeydownEscape={onClose}
>
  Content
</Dialog>
```

---

### Grid.Col size error: "Type 'string' is not assignable to type 'Size'"

**Cause**: Invalid size value (e.g., "1of1" instead of "1of2")

**Fix**:
```typescript
// Valid sizes (12-column grid)
<Grid.Col size="1of12" />  // 1 column
<Grid.Col size="1of6" />   // 2 columns
<Grid.Col size="1of4" />   // 3 columns
<Grid.Col size="1of3" />   // 4 columns
<Grid.Col size="1of2" />   // 6 columns
<Grid.Col size="2of3" />   // 8 columns
```

---

### Icon renders too large

**Cause**: Missing size prop

**Fix**:
```typescript
// ❌ WRONG
<Icon icon="tick" />

// ✅ CORRECT
<Icon icon="tick" size="md" />
```

---

## Redux DevTools

### Setup Redux DevTools

```typescript
// src/store/index.ts
import { configureStore } from '@reduxjs/toolkit';

export const store = configureStore({
  reducer: {
    roles: rolesReducer,
    services: servicesReducer,
    parameters: parametersReducer,
  },
  devTools: process.env.NODE_ENV !== 'production',
});
```

### Using DevTools

1. Install Redux DevTools Browser Extension
2. Open DevTools (F12) → Redux tab
3. View action dispatches in real-time
4. Inspect state changes
5. Time-travel debugging (undo/redo)
6. Dispatch actions manually

---

## Browser DevTools Debugging

### Console Debugging

```typescript
// Add temporary debugging
console.log('Component rendered:', { roles, services, parameters });
console.warn('Unexpected state:', state);
console.error('API Error:', error);

// Debug Redux dispatch
const dispatch = useAppDispatch();
dispatch(fetchRoles())
  .unwrap()
  .then(data => console.log('Roles loaded:', data))
  .catch(error => console.error('Load error:', error));
```

### Network Debugging

1. Open DevTools → Network tab
2. Filter by XHR/Fetch
3. Check request details:
   - Headers (authorization, content-type)
   - Payload (request body)
   - Response (status, body)
4. Check response status codes:
   - 2xx: Success
   - 3xx: Redirect
   - 4xx: Client error (400, 401, 403, 404)
   - 5xx: Server error

### DOM Inspector

1. Right-click element → Inspect
2. Check rendered HTML structure
3. Verify Blueprint classes applied
4. Check CSS computed styles
5. Look for missing props or attributes

---

## Common Console Errors

### Warning: Each child in a list should have a unique "key" prop

**Cause**: .map() without key prop

**Fix**:
```typescript
// ❌ WRONG
roles.map(role => <option>{role.name}</option>)

// ✅ CORRECT
roles.map(role => <option key={role.id}>{role.name}</option>)
```

---

### Warning: Received `false` for a non-boolean attribute

**Cause**: Passing non-boolean to boolean prop

**Fix**:
```typescript
// ❌ WRONG
<Button disabled="false" />

// ✅ CORRECT
<Button disabled={false} />
```

---

### React Hook Form "Cannot find control with name"

**Cause**: Controller name doesn't match form data

**Fix**:
```typescript
// ❌ WRONG
<Controller
  name="userName"  // But form data has "username"
  control={control}
  render={...}
/>

// ✅ CORRECT
<Controller
  name="username"
  control={control}
  render={...}
/>
```

---

## Performance Debugging

### React DevTools Profiler

1. Install React DevTools browser extension
2. Open DevTools → Profiler tab
3. Record interactions:
   - Click "Start recording"
   - Interact with app
   - Click "Stop recording"
4. View component render times
5. Identify slow components

### Memory Debugging

1. DevTools → Memory tab
2. Take heap snapshot
3. Compare before/after
4. Look for detached DOM nodes
5. Check for memory leaks

```typescript
// Cleanup for memory leaks
useEffect(() => {
  const timer = setTimeout(() => {
    // operation
  }, 1000);

  // CLEANUP function
  return () => clearTimeout(timer);
}, []);
```

---

## Logging Best Practices

### Structured Logging

```typescript
// src/utils/logger.ts
enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARN = 'WARN',
  ERROR = 'ERROR',
}

const logger = {
  debug: (message: string, data?: any) => {
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[DEBUG] ${message}`, data);
    }
  },
  info: (message: string, data?: any) => {
    console.info(`[INFO] ${message}`, data);
  },
  warn: (message: string, data?: any) => {
    console.warn(`[WARN] ${message}`, data);
  },
  error: (message: string, error?: any) => {
    console.error(`[ERROR] ${message}`, error);
  },
};

export default logger;
```

### Redux Action Logging Middleware

```typescript
// src/store/middleware/logger.ts
export const loggerMiddleware = (store: any) => (next: any) => (action: any) => {
  console.group(action.type);
  console.info('dispatch', action);
  const result = next(action);
  console.log('next state', store.getState());
  console.groupEnd();
  return result;
};

// Add to store
const store = configureStore({
  reducer: { /* ... */ },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(loggerMiddleware),
});
```

---

## Error Boundaries

### Error Boundary Component

```typescript
// src/components/ErrorBoundary.tsx
import React from 'react';

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: any) {
    console.error('Error caught by boundary:', error, info);
    // Send to error tracking service
    // logErrorToService(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <MessageAlert
            type="error"
            title="Something went wrong"
            message={this.state.error?.message || 'Unknown error'}
          />
        )
      );
    }

    return this.props.children;
  }
}
```

---

## Debugging Checklist

### Before Reporting Bug
- [ ] Check browser console for errors
- [ ] Check Network tab for API failures
- [ ] Verify API response structure
- [ ] Check Redux DevTools state
- [ ] Verify Array.isArray() validations present
- [ ] Check for 401/403 auth errors
- [ ] Verify API services initialized
- [ ] Check for CSS/styling issues

### When Bug Persists
- [ ] Add console.logs around problematic code
- [ ] Use Redux DevTools to inspect state
- [ ] Check Network tab for failing requests
- [ ] Use React Profiler to find slow components
- [ ] Check for memory leaks in DevTools
- [ ] Look for error boundaries catching errors
- [ ] Verify component props match expected structure

---

## References
- COMPONENT_AUDIT_CHECKLIST.md
- API_RESPONSE_PATTERNS.md
- SKILL.md Mistakes 1-23
- Redux DevTools: https://github.com/reduxjs/redux-devtools
- React DevTools: https://github.com/facebook/react/tree/main/packages/react-devtools
