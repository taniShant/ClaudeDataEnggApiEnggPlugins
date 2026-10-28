# Redux Patterns Guide for MCA2

Master patterns for Redux Toolkit state management in MCA2 applications.

Last Updated: March 25, 2026

---

## Table of Contents
1. [Basic Slice Pattern](#basic-slice-pattern)
2. [Async Thunk Error Handling](#async-thunk-error-handling)
3. [Loading States](#loading-states)
4. [Selectors & Memoization](#selectors--memoization)
5. [Normalized State Design](#normalized-state-design)
6. [Entity Relationships](#entity-relationships)
7. [Testing Async Thunks](#testing-async-thunks)
8. [Common Mistakes](#common-mistakes)

---

## Basic Slice Pattern

### Standard Redux Slice Structure

```typescript
// src/store/slices/rolesSlice.ts
import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { Role, CreateRoleRequest } from '../../types';
import { api } from '../../api/endpoints';

// ==================== State Interface ====================
interface RolesState {
  items: Role[];
  selectedRole: Role | null;
  loading: boolean;
  error: string | null;
  filter: {
    businessUnitId?: string;
    searchText?: string;
  };
}

// ==================== Initial State ====================
const initialState: RolesState = {
  items: [],
  selectedRole: null,
  loading: false,
  error: null,
  filter: {},
};

// ==================== Async Thunks ====================
export const fetchRoles = createAsyncThunk<
  Role[],
  { businessUnitId?: string } | undefined
>(
  'roles/fetchRoles',
  async (params, { rejectWithValue }) => {
    try {
      return await api.roles.fetchAll(params);
    } catch (error) {
      return rejectWithValue(
        error instanceof Error ? error.message : 'Failed to fetch roles'
      );
    }
  }
);

// ==================== Slice ====================
const rolesSlice = createSlice({
  name: 'roles',
  initialState,
  reducers: {
    // Synchronous actions
    setSelectedRole: (state, action: PayloadAction<Role | null>) => {
      state.selectedRole = action.payload;
    },
    setFilter: (state, action: PayloadAction<Partial<RolesState['filter']>>) => {
      state.filter = { ...state.filter, ...action.payload };
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Pending state
      .addCase(fetchRoles.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      // Success state
      .addCase(fetchRoles.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload;
      })
      // Error state
      .addCase(fetchRoles.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload as string;
      });
  },
});

// ==================== Exports ====================
export const { setSelectedRole, setFilter, clearError } = rolesSlice.actions;
export default rolesSlice.reducer;
```

---

## Async Thunk Error Handling

### Complete Error Handling Pattern

```typescript
// Best Practice: Comprehensive error handling
export const createRole = createAsyncThunk<
  Role,
  CreateRoleRequest,
  {
    rejectValue: {
      message: string;
      code: string;
      details?: Record<string, string>;
    };
  }
>(
  'roles/createRole',
  async (roleData, { rejectWithValue }) => {
    try {
      // Validate input
      if (!roleData.name) {
        return rejectWithValue({
          message: 'Role name is required',
          code: 'VALIDATION_ERROR',
        });
      }

      // Make API call
      const role = await api.roles.create(roleData);

      // Validate response
      if (!role) {
        return rejectWithValue({
          message: 'No data returned from server',
          code: 'INVALID_RESPONSE',
        });
      }

      return role;
    } catch (error) {
      // Handle different error types
      if (error instanceof TypeError) {
        return rejectWithValue({
          message: 'Network error - check your connection',
          code: 'NETWORK_ERROR',
        });
      }

      if (error instanceof Error) {
        // Parse backend error response
        if (error.message.includes('409')) {
          return rejectWithValue({
            message: 'Role already exists',
            code: 'DUPLICATE_ROLE',
          });
        }

        return rejectWithValue({
          message: error.message,
          code: 'API_ERROR',
        });
      }

      return rejectWithValue({
        message: 'Unknown error occurred',
        code: 'UNKNOWN_ERROR',
      });
    }
  }
);

// Handle in extra reducers
.addCase(createRole.rejected, (state, action) => {
  state.loading = false;
  state.error = action.payload?.message || 'Unknown error';
  state.validationErrors = action.payload?.details;
});
```

---

## Loading States

### Three-State Loading Pattern

```typescript
interface UIState {
  // Better than boolean loading
  loadingState: 'idle' | 'pending' | 'succeeded' | 'failed';
  error: string | null;
  message: string | null;
}

// Usage in component
const { loadingState, error, message } = useAppSelector(state => state.ui);

return (
  <>
    {loadingState === 'pending' && <Loading ariaLabel="Loading" />}
    {loadingState === 'succeeded' && message && (
      <MessageAlert type="success" message={message} />
    )}
    {loadingState === 'failed' && error && (
      <MessageAlert type="error" message={error} />
    )}
  </>
);
```

### Multiple Async Operations

```typescript
interface RolesState {
  items: {
    data: Role[];
    loading: boolean;
  };
  selectedRole: {
    data: Role | null;
    loading: boolean;
  };
  create: {
    loading: boolean;
    error: string | null;
  };
}

// Now you can track different operations independently
```

---

## Selectors & Memoization

### Using Reselect for Memoized Selectors

```typescript
import { createSelector } from '@reduxjs/toolkit';
import type { RootState } from '../../store';

// Base selector
const selectRolesState = (state: RootState) => state.roles;

// Memoized selector
export const selectRoles = createSelector(
  [selectRolesState],
  (rolesState) => rolesState.items
);

// Selector with arguments
export const selectRoleById = createSelector(
  [selectRolesState, (_: RootState, roleId: string) => roleId],
  (rolesState, roleId) => rolesState.items.find(r => r.id === roleId)
);

// Complex selector combining data
export const selectRolesWithServices = createSelector(
  [selectRolesState, (state: RootState) => state.services.items],
  (rolesState, services) =>
    rolesState.items.map(role => ({
      ...role,
      services: services.filter(s => s.roleId === role.id),
    }))
);

// Usage in component
const roles = useAppSelector(selectRoles);
const selectedRole = useAppSelector(state => selectRoleById(state, roleId));
const rolesWithServices = useAppSelector(selectRolesWithServices);
```

### Performance Tips

```typescript
// ❌ WRONG - Creates new object on every render
const roles = useAppSelector(state => ({
  items: state.roles.items,
  loading: state.roles.loading,
}));

// ✅ CORRECT - Memoized selector returns same reference
export const selectRolesData = createSelector(
  [
    (state: RootState) => state.roles.items,
    (state: RootState) => state.roles.loading,
  ],
  (items, loading) => ({ items, loading })
);

const { items, loading } = useAppSelector(selectRolesData);
```

---

## Normalized State Design

### Normalized State for Related Data

```typescript
// ❌ WRONG - Denormalized structure duplicates data
interface RolesState {
  roles: {
    id: string;
    name: string;
    services: Service[];  // Duplicated if service is also in services state
  }[];
}

// ✅ CORRECT - Normalized structure
interface RolesState {
  byId: {
    [roleId: string]: Role;
  };
  allIds: string[];
  selectedRoleId: string | null;
}

interface ServicesState {
  byId: {
    [serviceId: string]: Service;
  };
  allIds: string[];
  roleServiceMapping: {
    [roleId: string]: string[]; // Service IDs for this role
  };
}

// Usage with selector
export const selectRoleWithServices = createSelector(
  [
    (state: RootState) => state.roles.byId,
    (state: RootState) => state.roles.selectedRoleId,
    (state: RootState) => state.services.byId,
    (state: RootState) => state.services.roleServiceMapping,
  ],
  (roleById, selectedRoleId, servicesById, roleServiceMapping) => {
    if (!selectedRoleId) return null;

    const role = roleById[selectedRoleId];
    const serviceIds = roleServiceMapping[selectedRoleId] || [];
    const services = serviceIds.map(id => servicesById[id]);

    return { ...role, services };
  }
);
```

---

## Entity Relationships

### Handling Many-to-Many Relationships

```typescript
// Roles <-> Services (many-to-many)

interface RelationshipState {
  // Mapping of roleId -> serviceIds[]
  roleServices: {
    [roleId: string]: string[];
  };
  // Mapping of serviceId -> roleIds[]
  serviceRoles: {
    [serviceId: string]: string[];
  };
  loading: boolean;
  error: string | null;
}

// Add service to role
export const addServiceToRole = createAsyncThunk<
  void,
  { roleId: string; serviceId: string }
>(
  'relationships/addServiceToRole',
  async ({ roleId, serviceId }, { dispatch, rejectWithValue }) => {
    try {
      await api.services.updateRoleServices(roleId, { serviceId });

      // Update both directions
      dispatch(addRoleServiceMapping({ roleId, serviceId }));
      dispatch(addServiceRoleMapping({ serviceId, roleId }));
    } catch (error) {
      return rejectWithValue(error instanceof Error ? error.message : 'Failed');
    }
  }
);

// Reducer for adding mapping
.addCase(addServiceToRole.fulfilled, (state, action) => {
  const { roleId, serviceId } = action.payload;

  if (!state.roleServices[roleId]) {
    state.roleServices[roleId] = [];
  }
  if (!state.roleServices[roleId].includes(serviceId)) {
    state.roleServices[roleId].push(serviceId);
  }

  if (!state.serviceRoles[serviceId]) {
    state.serviceRoles[serviceId] = [];
  }
  if (!state.serviceRoles[serviceId].includes(roleId)) {
    state.serviceRoles[serviceId].push(roleId);
  }
});
```

---

## Testing Async Thunks

### Unit Testing Redux Slices

```typescript
import { configureStore, PreloadedState } from '@reduxjs/toolkit';
import rolesReducer, { fetchRoles } from './rolesSlice';

describe('rolesSlice', () => {
  let store: any;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        roles: rolesReducer,
      },
    });
  });

  describe('fetchRoles thunk', () => {
    it('should handle pending state', () => {
      const state = rolesReducer(
        { items: [], loading: false, error: null },
        fetchRoles.pending('')
      );

      expect(state.loading).toBe(true);
      expect(state.error).toBeNull();
    });

    it('should handle fulfilled state', () => {
      const mockRoles = [
        { id: '1', name: 'Admin' },
        { id: '2', name: 'User' },
      ];

      const state = rolesReducer(
        { items: [], loading: true, error: null },
        fetchRoles.fulfilled(mockRoles, '')
      );

      expect(state.loading).toBe(false);
      expect(state.items).toEqual(mockRoles);
    });

    it('should handle rejected state', () => {
      const errorMessage = 'Failed to fetch';

      const state = rolesReducer(
        { items: [], loading: true, error: null },
        fetchRoles.rejected(new Error(errorMessage), '', undefined, errorMessage)
      );

      expect(state.loading).toBe(false);
      expect(state.error).toBe(errorMessage);
    });
  });
});
```

### Integration Testing with Mock API

```typescript
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';

const middleware = [thunk];
const mockStore = configureMockStore(middleware);

describe('fetchRoles thunk integration', () => {
  it('should dispatch pending and fulfilled actions', async () => {
    const expectedActions = [
      { type: fetchRoles.pending.type },
      { type: fetchRoles.fulfilled.type, payload: mockRoles },
    ];

    // Mock API
    jest.spyOn(api.roles, 'fetchAll').mockResolvedValue(mockRoles);

    const store = mockStore(initialState);
    await store.dispatch(fetchRoles());

    expect(store.getActions()).toEqual(expectedActions);
  });

  it('should handle API errors', async () => {
    const errorMessage = 'API Error';

    jest
      .spyOn(api.roles, 'fetchAll')
      .mockRejectedValue(new Error(errorMessage));

    const store = mockStore(initialState);
    await store.dispatch(fetchRoles());

    const actions = store.getActions();
    expect(actions[0].type).toBe(fetchRoles.pending.type);
    expect(actions[1].type).toBe(fetchRoles.rejected.type);
  });
});
```

---

## Common Mistakes

### ❌ Mistake 1: Mutating State Outside Reducers

```typescript
// WRONG - Mutating state directly
const role = state.items[0];
role.name = 'New Name';  // ❌ Direct mutation

// CORRECT - Use Immer (Redux Toolkit handles this)
const index = state.items.findIndex(r => r.id === roleId);
state.items[index] = { ...state.items[index], name: 'New Name' };
```

### ❌ Mistake 2: Using Non-Serializable Data

```typescript
// WRONG
interface UIState {
  selectedDate: Date;  // ❌ Not serializable
  callbacks: () => void;  // ❌ Not serializable
}

// CORRECT
interface UIState {
  selectedDate: string;  // ISO string
  callbackId: string;  // Reference, not function
}
```

### ❌ Mistake 3: Complex Logic in Reducers

```typescript
// WRONG - Complex logic in reducer
.addCase(fetchRoles.fulfilled, (state, action) => {
  state.items = action.payload
    .filter(r => r.active)
    .map(r => ({ ...r, displayName: r.name.toUpperCase() }))
    .sort((a, b) => a.name.localeCompare(b.name));
});

// CORRECT - Use selectors for derived data
export const selectActiveRoles = createSelector(
  [selectRoles],
  (roles) =>
    roles
      .filter(r => r.active)
      .sort((a, b) => a.name.localeCompare(b.name))
);
```

### ❌ Mistake 4: Duplicate State

```typescript
// WRONG - Duplicating data in multiple slices
interface RolesState {
  items: Role[];
  selectedRole: Role;  // Same data in two places
}

// CORRECT - Store only IDs, derive with selectors
interface RolesState {
  byId: { [id: string]: Role };
  selectedRoleId: string | null;
}

export const selectSelectedRole = createSelector(
  [(state) => state.roles.byId, (state) => state.roles.selectedRoleId],
  (byId, selectedRoleId) => selectedRoleId ? byId[selectedRoleId] : null
);
```

### ❌ Mistake 5: Not Handling Errors from Thunks

```typescript
// WRONG - Not handling rejection
dispatch(fetchRoles()).then(() => {
  // Assumes success
  console.log('Roles fetched');
});

// CORRECT - Handle both cases
dispatch(fetchRoles())
  .unwrap()
  .then(() => {
    showSuccessMessage('Roles loaded');
  })
  .catch((error) => {
    showErrorMessage(error);
  });
```

### ❌ Mistake 6: Storing UI State in Redux

```typescript
// WRONG - UI state that changes frequently
interface UIState {
  hoveredItemId: string | null;  // Every hover updates Redux
  inputValue: string;  // Every keystroke updates Redux
}

// CORRECT - Keep local component state
const [hoveredItemId, setHoveredItemId] = useState<string | null>(null);
const [inputValue, setInputValue] = useState('');
```

---

## Summary Checklist

- ✅ Use createAsyncThunk for API calls
- ✅ Handle pending/fulfilled/rejected states
- ✅ Return rejectWithValue for errors
- ✅ Use createSelector for memoization
- ✅ Normalize state for large datasets
- ✅ Track relationships with mappings
- ✅ Test reducers and thunks
- ✅ Handle errors in components
- ✅ Avoid duplicate state
- ✅ Don't store UI state in Redux

---

## References
- Redux Toolkit Documentation: https://redux-toolkit.js.org
- Redux Style Guide: https://redux.js.org/style-guide/style-guide
- Reselect Documentation: https://github.com/reduxjs/reselect
- SKILL.md Mistakes 1-23
