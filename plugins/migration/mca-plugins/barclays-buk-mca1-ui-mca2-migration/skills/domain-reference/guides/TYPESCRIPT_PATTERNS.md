# TypeScript Patterns for MCA2

Type architecture and interface conventions for migrated MCA2 React applications.

Last Updated: 2026-05-19 | Version: 1.0.0

---

## Table of Contents

1. [Component Prop Interfaces](#component-prop-interfaces)
2. [Redux State Types](#redux-state-types)
3. [API Response Types](#api-response-types)
4. [Event Handler Types](#event-handler-types)
5. [Discriminated Unions](#discriminated-unions)
6. [Generic Components](#generic-components)
7. [Utility Type Patterns](#utility-type-patterns)
8. [Anti-Patterns](#anti-patterns)

---

## Component Prop Interfaces

Every component gets an explicit interface. Name it `{ComponentName}Props`.

```typescript
// src/pages/RoleManagement/RoleManagement.types.ts

interface RoleTableProps {
  roles: Role[];
  isLoading: boolean;
  onSelect: (role: Role) => void;
  onDelete: (roleId: string) => void;
}

interface RoleDialogProps {
  role: Role;
  isOpen: boolean;
  onClose: () => void;
  onSave: (updated: RoleFormValues) => Promise<void>;
}
```

**Rules:**
- Required props first, optional props after
- Callbacks use descriptive names: `onSelect`, `onClose`, `onSave`
- Never use `any` for prop types — use the actual type or `unknown`
- Use `React.FC<Props>` for components with no children, or explicit `children?: React.ReactNode`

### Optional Props with Defaults

```typescript
// ✓ CORRECT — optional with default in destructuring
interface PageHeaderProps {
  title: string;
  subtitle?: string;
  showBackButton?: boolean;
}

const PageHeader: React.FC<PageHeaderProps> = ({
  title,
  subtitle,
  showBackButton = false,
}) => { ... };
```

---

## Redux State Types

### Slice State Interface

```typescript
// src/store/slices/rolesSlice.ts

interface RolesState {
  items: Role[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
}

const initialState: RolesState = {
  items: [],
  selectedId: null,
  loading: false,
  error: null,
};
```

### Async State Pattern (Reusable)

```typescript
// src/types/common.ts

interface AsyncState<T> {
  data: T;
  loading: boolean;
  error: string | null;
}

// Usage in slice:
interface RolesState extends AsyncState<Role[]> {
  selectedId: string | null;
  filter: RoleFilter;
}
```

### Normalized State (for large collections)

```typescript
// src/store/slices/servicesSlice.ts

interface ServicesState {
  byId: Record<string, Service>;
  allIds: string[];
  loading: boolean;
  error: string | null;
}

// Selector:
const selectServiceById = (state: RootState, id: string): Service | undefined =>
  state.services.byId[id];
```

### RootState and AppDispatch

```typescript
// src/store/store.ts
import { configureStore } from '@reduxjs/toolkit';
import rolesReducer from './slices/rolesSlice';
import servicesReducer from './slices/servicesSlice';

export const store = configureStore({
  reducer: {
    roles: rolesReducer,
    services: servicesReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

```typescript
// src/store/hooks.ts
import { useDispatch, useSelector } from 'react-redux';
import type { RootState, AppDispatch } from './store';

export const useAppDispatch = useDispatch.withTypes<AppDispatch>();
export const useAppSelector = useSelector.withTypes<RootState>();
```

---

## API Response Types

### Request/Response DTOs

```typescript
// src/api/types.ts

interface ApiResponse<T> {
  data: T;
  status: number;
  message?: string;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

// Domain-specific:
interface CreateRoleRequest {
  name: string;
  permissions: string[];
  description?: string;
}

interface CreateRoleResponse {
  id: string;
  name: string;
  createdAt: string;
}
```

### Type Narrowing for API Responses

```typescript
// src/api/endpoints.ts

async function fetchRoles(): Promise<Role[]> {
  const response: unknown = await api.service.call('getRoles');

  if (!isRolesResponse(response)) {
    throw new Error('Invalid API response shape for getRoles');
  }

  return response.items;
}

function isRolesResponse(data: unknown): data is { items: Role[] } {
  return (
    typeof data === 'object' &&
    data !== null &&
    'items' in data &&
    Array.isArray((data as { items: unknown }).items)
  );
}
```

---

## Event Handler Types

```typescript
// ✓ CORRECT — explicit event types
const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  setName(e.target.value);
};

const handleFormSubmit = (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();
  dispatch(createRole(formValues));
};

const handleSelectChange = (value: string) => {
  setSelectedStatus(value);
};

const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
  if (e.key === 'Enter') handleSearch();
};
```

### Callback Props

```typescript
// ✓ CORRECT — typed callback in props
interface RoleRowProps {
  role: Role;
  onEdit: (id: string) => void;
  onDelete: (id: string) => Promise<void>;
}

// ❌ WRONG — untyped or `any`
interface RoleRowProps {
  role: any;
  onEdit: Function;
  onDelete: any;
}
```

---

## Discriminated Unions

Use when a component or state can be in mutually exclusive modes.

### Component Mode Props

```typescript
// ✓ CORRECT — discriminated union for dialog mode
type RoleDialogProps =
  | { mode: 'create'; onSubmit: (values: CreateRoleRequest) => void }
  | { mode: 'edit'; role: Role; onSubmit: (values: UpdateRoleRequest) => void };

const RoleDialog: React.FC<RoleDialogProps> = (props) => {
  if (props.mode === 'edit') {
    // TypeScript knows `props.role` exists here
    return <EditForm role={props.role} onSubmit={props.onSubmit} />;
  }
  return <CreateForm onSubmit={props.onSubmit} />;
};
```

### Async State Discrimination

```typescript
type FetchState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: string };

// Usage — exhaustive checking:
function renderContent(state: FetchState<Role[]>) {
  switch (state.status) {
    case 'idle':
      return null;
    case 'loading':
      return <Loading size="lg" shape="circle" ariaLabel="Loading roles" />;
    case 'success':
      return <RoleTable roles={state.data} />;
    case 'error':
      return <ErrorDisplay message={state.error} />;
  }
}
```

---

## Generic Components

### Typed Data Table

```typescript
// src/components/common/DataTable.tsx

interface Column<T> {
  key: keyof T;
  header: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
}

function DataTable<T extends { id: string }>({
  data,
  columns,
  onRowClick,
  emptyMessage = 'No data available',
}: DataTableProps<T>) {
  if (!Array.isArray(data) || data.length === 0) {
    return <Type>{emptyMessage}</Type>;
  }

  return (
    <Table equalPadding headingVariant="default">
      <thead>
        <tr>
          {columns.map((col) => (
            <th key={String(col.key)}>{col.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {data.map((row) => (
          <tr key={row.id} onClick={() => onRowClick?.(row)}>
            {columns.map((col) => (
              <td key={String(col.key)}>
                {col.render ? col.render(row[col.key], row) : String(row[col.key])}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </Table>
  );
}
```

---

## Utility Type Patterns

```typescript
// Partial form values (for forms that submit incrementally)
type RoleFormValues = Pick<Role, 'name' | 'permissions' | 'description'>;

// Omit server-generated fields for create payloads
type CreateRolePayload = Omit<Role, 'id' | 'createdAt' | 'updatedAt'>;

// Make specific fields optional for update payloads
type UpdateRolePayload = Partial<Pick<Role, 'name' | 'permissions' | 'description'>> & { id: string };

// Extract action types from a slice
type RolesAction = ReturnType<typeof rolesSlice.actions[keyof typeof rolesSlice.actions]>;
```

---

## Anti-Patterns

| Pattern | Problem | Fix |
|---------|---------|-----|
| `any` on props | Bypasses all type checking | Use proper interface |
| `as any` cast | Hides real type errors | Fix the underlying type mismatch |
| `Function` type | No parameter/return type info | Use specific signature `(id: string) => void` |
| `object` type | Too broad, no properties | Use specific interface |
| `!` non-null assertion | Runtime crash if actually null | Use optional chaining or null check |
| Inline type in JSX | Unreadable, not reusable | Extract to named interface |
| `// @ts-ignore` | Suppresses valid errors | Fix the type error |
| `useState<any>()` | Loses type inference | `useState<Role | null>(null)` |

### Common Migration Type Fixes

```typescript
// ❌ WRONG — migrated from untyped JMVC
const [roles, setRoles] = useState<any>([]);
const handleSelect = (item: any) => { ... };

// ✓ CORRECT — properly typed
const [roles, setRoles] = useState<Role[]>([]);
const handleSelect = (role: Role) => { ... };
```

```typescript
// ❌ WRONG — API response untyped
const data = await api.service.call('getRoles');
setRoles(data.items); // `data` is `any`

// ✓ CORRECT — typed with narrowing
const response = await api.service.call('getRoles') as unknown;
const validated = validateRolesResponse(response);
setRoles(validated.items);
```
