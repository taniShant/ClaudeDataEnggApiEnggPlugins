# MCA2 Application Folder Structure

Canonical directory layout for migrated MCA2 React applications using Blueprint-React, Redux Toolkit, and MemoryRouter.

Last Updated: 2026-05-19 | Version: 1.0.0

---

## Table of Contents

1. [Directory Tree](#directory-tree)
2. [Entry Points](#entry-points)
3. [Pages](#pages)
4. [Components](#components)
5. [Store (Redux Toolkit)](#store-redux-toolkit)
6. [Hooks](#hooks)
7. [API Layer](#api-layer)
8. [Types](#types)
9. [Utils](#utils)
10. [Naming Conventions](#naming-conventions)
11. [Decision Rules](#decision-rules)

---

## Directory Tree

```
project-root/
  src/
    api/
      endpoints.ts          # API service functions (initializeApiServices, call wrappers)
      types.ts              # Request/response DTOs
    components/
      common/
        ErrorBoundary.tsx   # Reusable error boundary
        LoadingSpinner.tsx  # Shared loading state
        ProtectedRoute.tsx  # Route guard component
        PageHeader.tsx      # Shared page header layout
      forms/
        FormField.tsx       # Reusable FormItem wrapper (if pattern repeats 3+ times)
        FormSelect.tsx      # Reusable FormItem + FormCombobox wrapper
    hooks/
      useFormValidation.ts  # Yup validation hook
      useDebounce.ts        # Debounced value hook
      usePagination.ts      # Table pagination logic
    pages/
      Dashboard/
        Dashboard.tsx       # Page component
        Dashboard.types.ts  # Page-specific interfaces
        useDashboard.ts     # Page-specific data hook
      RoleManagement/
        RoleManagement.tsx
        RoleManagement.types.ts
        useRoleManagement.ts
      ServiceAdmin/
        ServiceAdmin.tsx
        ServiceAdmin.types.ts
        useServiceAdmin.ts
    store/
      slices/
        rolesSlice.ts       # createSlice + async thunks for roles
        servicesSlice.ts    # createSlice + async thunks for services
        uiSlice.ts          # UI state (modals, toasts, loading flags)
      store.ts              # configureStore with all slices
      hooks.ts              # useAppDispatch, useAppSelector typed hooks
    types/
      common.ts             # Shared types (ApiResponse<T>, PaginatedResult<T>)
      models.ts             # Domain models (Role, Service, User)
    utils/
      formatters.ts         # Date, currency, string formatting
      validators.ts         # Shared validation rules
      constants.ts          # App-wide constants
    App.tsx                 # MemoryRouter + Routes + layout shell
    Entry.tsx               # MCA2 launch entry (api initialization from props)
    index.ts                # Eagle launch function (export default)
  process.json              # API endpoint URI configuration
  mockServer/
    middleware.js           # Express mock server (DO NOT MODIFY during migration)
  package.json
  tsconfig.json
```

---

## Entry Points

### `src/index.ts` — Eagle Launch Function

```typescript
// src/index.ts
import { render } from 'react-dom';
import Entry from './Entry';

export default function launch(container: HTMLElement, props: MCA2LaunchProps) {
  render(<Entry {...props} />, container);
}
```

### `src/Entry.tsx` — API Initialization

```typescript
// src/Entry.tsx
import React, { useEffect, useState } from 'react';
import { Provider } from 'react-redux';
import { store } from './store/store';
import { initializeApiServices } from './api/endpoints';
import App from './App';

interface EntryProps {
  api: ApiMCA;
  config: Record<string, unknown>;
}

const Entry: React.FC<EntryProps> = (props) => {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (props.api) {
      initializeApiServices(props.api);
      setReady(true);
    }
  }, [props.api]);

  if (!ready) return null;

  return (
    <Provider store={store}>
      <App {...props} />
    </Provider>
  );
};

export default Entry;
```

### `src/App.tsx` — Routes + Layout

```typescript
// src/App.tsx
import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router';
import Dashboard from './pages/Dashboard/Dashboard';
import RoleManagement from './pages/RoleManagement/RoleManagement';

const App: React.FC = () => (
  <MemoryRouter>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/roles" element={<RoleManagement />} />
      <Route path="/roles/:id" element={<RoleManagement />} />
    </Routes>
  </MemoryRouter>
);

export default App;
```

---

## Pages

Each page gets its own folder with co-located files:

```
pages/RoleManagement/
  RoleManagement.tsx        # The component (default export)
  RoleManagement.types.ts   # Props, local interfaces
  useRoleManagement.ts      # Page-specific custom hook (data fetching, handlers)
```

**Rules:**
- One page = one route = one folder
- Page component orchestrates layout using Blueprint `Section`/`SectionItem`
- Business logic lives in the custom hook, not the component body
- Page-specific types stay in the page folder

```typescript
// src/pages/RoleManagement/RoleManagement.tsx
import React from 'react';
import { Section, SectionItem } from '@barclays/blueprint-react';
import { useRoleManagement } from './useRoleManagement';
import { RoleTable } from './components/RoleTable';
import { RoleDialog } from './components/RoleDialog';

const RoleManagement: React.FC = () => {
  const { roles, isLoading, error, selectedRole, handlers } = useRoleManagement();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorDisplay message={error} />;

  return (
    <Section>
      <SectionItem>
        <RoleTable roles={roles} onSelect={handlers.handleSelect} />
      </SectionItem>
      {selectedRole && (
        <RoleDialog role={selectedRole} onClose={handlers.handleCloseDialog} />
      )}
    </Section>
  );
};

export default RoleManagement;
```

---

## Components

### Shared vs Page-Specific

| Location | When to use |
|----------|-------------|
| `components/common/` | Used by 2+ pages |
| `components/forms/` | Reusable form patterns used across pages |
| `pages/{Page}/components/` | Only used by that one page |

**Rule:** Start page-specific. Promote to `components/common/` only when a second page needs it.

---

## Store (Redux Toolkit)

```
store/
  slices/
    rolesSlice.ts       # One slice per domain entity
    servicesSlice.ts
    uiSlice.ts          # Cross-cutting UI state
  store.ts              # configureStore
  hooks.ts              # Typed dispatch/selector hooks
```

**Rules:**
- One slice per domain entity (roles, services, users), not per page
- Async thunks live in the same file as their slice
- UI-only state (modal open, active tab) goes in `uiSlice.ts` or local `useState`
- Never put form input values in Redux — use local state or form library

---

## Hooks

```
hooks/
  useFormValidation.ts  # Shared across 3+ forms
  useDebounce.ts        # Generic debounce utility
  usePagination.ts      # Table pagination state
```

**Rules:**
- Only extract to `hooks/` when used by 2+ pages
- Page-specific hooks stay in the page folder (`useDashboard.ts`)
- Name always starts with `use`
- Each hook file exports a single named hook

---

## API Layer

```
api/
  endpoints.ts          # All API call functions
  types.ts              # Request/response DTOs
```

**Rules:**
- `endpoints.ts` wraps the MCA2 `Api.service.call()` pattern
- Each function is named after the action: `fetchRoles()`, `createRole()`, `deleteRole()`
- Response types live in `api/types.ts`, not scattered across slices
- Never hardcode endpoint paths — they come from `process.json`

---

## Types

```
types/
  common.ts             # ApiResponse<T>, PaginatedResult<T>, AsyncState<T>
  models.ts             # Role, Service, User — domain models
```

**Rules:**
- Only put types here if used by 3+ files across different features
- Page-specific types stay in `pages/{Page}/{Page}.types.ts`
- Slice state types stay in the slice file
- Prefer interfaces over type aliases for object shapes (better error messages)

---

## Utils

```
utils/
  formatters.ts         # formatDate(), formatCurrency(), capitalize()
  validators.ts         # Shared Yup schemas or validation helpers
  constants.ts          # APP_ROUTES, STATUS_LABELS, etc.
```

**Rules:**
- Pure functions only — no side effects, no hooks, no React imports
- Each utility function is independently testable

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Component files | PascalCase | `RoleManagement.tsx` |
| Hook files | camelCase with `use` prefix | `useRoleManagement.ts` |
| Slice files | camelCase with `Slice` suffix | `rolesSlice.ts` |
| Type files | camelCase with `.types.ts` | `RoleManagement.types.ts` |
| Utility files | camelCase | `formatters.ts` |
| Constants | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT` |
| Component names | PascalCase | `RoleManagement` |
| Hook names | camelCase with `use` prefix | `useRoleManagement` |
| Handler names | `handle` + Action | `handleRoleSelect` |
| Boolean state | `is`/`has` prefix | `isLoading`, `hasError` |

---

## Decision Rules

| Situation | Decision |
|-----------|----------|
| New component used by 1 page | Put in `pages/{Page}/components/` |
| Component now used by 2 pages | Move to `components/common/` |
| Hook used by 1 page | Put in `pages/{Page}/use{Page}.ts` |
| Hook used by 3+ pages | Move to `hooks/` |
| Type used by 1 file | Define inline or in `.types.ts` next to component |
| Type used by 3+ files across features | Move to `types/` |
| Form state | Local `useState` or form library — NOT Redux |
| Server data | Redux slice with async thunk |
| UI toggle (modal open) | Local `useState` unless shared across pages |
