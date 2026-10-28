# Testing Patterns for MCA2

Comprehensive patterns for unit, integration, and E2E testing in MCA2 React applications.

Last Updated: March 25, 2026

---

## Table of Contents
1. [Unit Testing Reducers](#unit-testing-reducers)
2. [Testing Async Thunks](#testing-async-thunks)
3. [Component Testing](#component-testing)
4. [Integration Testing](#integration-testing)
5. [E2E Testing](#e2e-testing)
6. [Test Coverage](#test-coverage)
7. [Mocking Strategies](#mocking-strategies)

---

## Unit Testing Reducers

### Redux Reducer Tests

```typescript
// src/store/slices/__tests__/rolesSlice.test.ts
import rolesReducer, {
  setSelectedRole,
  setFilter,
  clearError,
  fetchRoles,
} from '../rolesSlice';
import { Role } from '../../../types';

describe('rolesSlice', () => {
  const initialState = {
    items: [],
    selectedRole: null,
    loading: false,
    error: null,
    businessUnits: [],
    filter: {},
  };

  describe('reducers', () => {
    it('should handle initial state', () => {
      const result = rolesReducer(undefined, { type: 'unknown' });
      expect(result).toEqual(initialState);
    });

    it('should handle setSelectedRole', () => {
      const mockRole: Role = {
        id: '1',
        name: 'Admin',
        businessUnitId: 'bu1',
        type: 'admin',
        isActive: true,
      };

      const result = rolesReducer(initialState, setSelectedRole(mockRole));

      expect(result.selectedRole).toEqual(mockRole);
    });

    it('should handle setFilter', () => {
      const filterData = { businessUnitId: 'bu1', searchText: 'admin' };
      const result = rolesReducer(initialState, setFilter(filterData));

      expect(result.filter).toEqual(filterData);
    });

    it('should merge filters', () => {
      const state = { ...initialState, filter: { businessUnitId: 'bu1' } };
      const result = rolesReducer(state, setFilter({ searchText: 'admin' }));

      expect(result.filter).toEqual({
        businessUnitId: 'bu1',
        searchText: 'admin',
      });
    });

    it('should handle clearError', () => {
      const state = { ...initialState, error: 'Some error' };
      const result = rolesReducer(state, clearError());

      expect(result.error).toBeNull();
    });
  });

  describe('async thunks', () => {
    it('should handle fetchRoles.pending', () => {
      const result = rolesReducer(initialState, fetchRoles.pending(''));

      expect(result.loading).toBe(true);
      expect(result.error).toBeNull();
    });

    it('should handle fetchRoles.fulfilled', () => {
      const mockRoles: Role[] = [
        { id: '1', name: 'Admin', businessUnitId: 'bu1', type: 'admin', isActive: true },
        { id: '2', name: 'User', businessUnitId: 'bu1', type: 'user', isActive: true },
      ];

      const result = rolesReducer(
        { ...initialState, loading: true },
        fetchRoles.fulfilled(mockRoles, '', undefined)
      );

      expect(result.loading).toBe(false);
      expect(result.items).toEqual(mockRoles);
      expect(result.error).toBeNull();
    });

    it('should handle fetchRoles.rejected', () => {
      const errorMessage = 'Failed to fetch roles';

      const result = rolesReducer(
        { ...initialState, loading: true },
        fetchRoles.rejected(null, '', undefined, errorMessage)
      );

      expect(result.loading).toBe(false);
      expect(result.error).toBe(errorMessage);
      expect(result.items).toEqual([]);
    });
  });
});
```

---

## Testing Async Thunks

### Complete Thunk Testing

```typescript
// src/store/slices/__tests__/rolesSlice.thunk.test.ts
import configureMockStore from 'redux-mock-store';
import thunk from 'redux-thunk';
import { fetchRoles, createRole } from '../rolesSlice';
import * as api from '../../../api/endpoints';

const middlewares = [thunk];
const mockStore = configureMockStore(middlewares);

// Mock the API module
jest.mock('../../../api/endpoints');

describe('roles thunks', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('fetchRoles', () => {
    it('should dispatch pending and fulfilled actions on success', async () => {
      const mockRoles = [
        { id: '1', name: 'Admin', businessUnitId: 'bu1', type: 'admin', isActive: true },
      ];

      (api.api.roles.fetchAll as jest.Mock).mockResolvedValue(mockRoles);

      const store = mockStore({});
      await store.dispatch(fetchRoles());

      const actions = store.getActions();

      expect(actions[0]).toEqual(
        expect.objectContaining({ type: fetchRoles.pending.type })
      );
      expect(actions[1]).toEqual(
        expect.objectContaining({
          type: fetchRoles.fulfilled.type,
          payload: mockRoles,
        })
      );
    });

    it('should dispatch pending and rejected actions on error', async () => {
      const errorMessage = 'Network error';
      (api.api.roles.fetchAll as jest.Mock).mockRejectedValue(
        new Error(errorMessage)
      );

      const store = mockStore({});
      await store.dispatch(fetchRoles());

      const actions = store.getActions();

      expect(actions[0]).toEqual(
        expect.objectContaining({ type: fetchRoles.pending.type })
      );
      expect(actions[1]).toEqual(
        expect.objectContaining({
          type: fetchRoles.rejected.type,
          payload: errorMessage,
        })
      );
    });

    it('should pass parameters to API call', async () => {
      (api.api.roles.fetchAll as jest.Mock).mockResolvedValue([]);

      const store = mockStore({});
      const params = { businessUnitId: 'bu1' };

      await store.dispatch(fetchRoles(params));

      expect(api.api.roles.fetchAll).toHaveBeenCalledWith(params);
    });
  });

  describe('createRole', () => {
    it('should handle successful role creation', async () => {
      const newRole = {
        id: '3',
        name: 'Supervisor',
        businessUnitId: 'bu1',
        type: 'user',
        isActive: true,
      };

      (api.api.roles.create as jest.Mock).mockResolvedValue(newRole);

      const store = mockStore({});
      await store.dispatch(createRole({ name: 'Supervisor', businessUnitId: 'bu1', type: 'user' }));

      const actions = store.getActions();
      expect(actions[1].payload).toEqual(newRole);
    });

    it('should validate required fields before API call', async () => {
      const store = mockStore({});

      await store.dispatch(
        createRole({ name: '', businessUnitId: 'bu1', type: 'user' })
      );

      const actions = store.getActions();
      expect(actions[1].type).toBe(createRole.rejected.type);
      expect(actions[1].payload.message).toContain('required');
    });
  });
});
```

---

## Component Testing

### React Component Tests

```typescript
// src/pages/__tests__/Dashboard.test.tsx
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router';
import { configureStore } from '@reduxjs/toolkit';
import Dashboard from '../Dashboard';
import rolesReducer from '../../store/slices/rolesSlice';
import servicesReducer from '../../store/slices/servicesSlice';

describe('Dashboard', () => {
  let store: any;

  beforeEach(() => {
    store = configureStore({
      reducer: {
        roles: rolesReducer,
        services: servicesReducer,
        parameters: parametersReducer,
      },
      preloadedState: {
        roles: {
          items: [
            { id: '1', name: 'Admin', businessUnitId: 'bu1', type: 'admin', isActive: true },
            { id: '2', name: 'User', businessUnitId: 'bu1', type: 'user', isActive: true },
          ],
          loading: false,
          error: null,
          selectedRole: null,
          businessUnits: [],
          filter: {},
        },
        services: {
          items: [
            { id: 's1', name: 'Service 1', serviceGroupId: 'sg1', isActive: true },
          ],
          loading: false,
          error: null,
          selectedService: null,
          serviceGroups: [],
        },
        parameters: {
          items: [],
          loading: false,
          error: null,
          selectedParameter: null,
        },
      },
    });
  });

  it('should render dashboard with sections', () => {
    render(
      <Provider store={store}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </Provider>
    );

    expect(screen.getByText('Roles')).toBeInTheDocument();
    expect(screen.getByText('Services')).toBeInTheDocument();
    expect(screen.getByText('Parameters')).toBeInTheDocument();
  });

  it('should populate roles dropdown with data', () => {
    render(
      <Provider store={store}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </Provider>
    );

    const rolesSelect = screen.getByDisplayValue('Select Item') as HTMLSelectElement;
    expect(rolesSelect.innerHTML).toContain('Admin');
    expect(rolesSelect.innerHTML).toContain('User');
  });

  it('should handle role selection', async () => {
    const user = userEvent.setup();

    render(
      <Provider store={store}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </Provider>
    );

    const rolesSelect = screen.getByDisplayValue('Select Item') as HTMLSelectElement;
    await user.selectOptions(rolesSelect, '1');

    expect(rolesSelect.value).toBe('1');
  });

  it('should show Apply button when role is selected', async () => {
    const user = userEvent.setup();

    render(
      <Provider store={store}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </Provider>
    );

    const applyButton = screen.getByText('Apply') as HTMLButtonElement;
    expect(applyButton).toBeDisabled(); // No selection yet

    // Select role and action
    const roleSelect = screen.getAllByDisplayValue('Select Item')[0] as HTMLSelectElement;
    const actionSelect = screen.getAllByDisplayValue('Select Item')[1] as HTMLSelectElement;

    await user.selectOptions(roleSelect, '1');
    await user.selectOptions(actionSelect, 'edit');

    // Apply button should now be enabled
    await waitFor(() => {
      expect(applyButton).not.toBeDisabled();
    });
  });

  it('should handle empty data gracefully', () => {
    const emptyStore = configureStore({
      reducer: {
        roles: rolesReducer,
        services: servicesReducer,
        parameters: parametersReducer,
      },
      preloadedState: {
        roles: { items: [], loading: false, error: null, selectedRole: null, businessUnits: [], filter: {} },
        services: { items: [], loading: false, error: null, selectedService: null, serviceGroups: [] },
        parameters: { items: [], loading: false, error: null, selectedParameter: null },
      },
    });

    render(
      <Provider store={emptyStore}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </Provider>
    );

    // Should render without crashing
    expect(screen.getByText('Roles')).toBeInTheDocument();
  });

  it('should show error message if loading fails', () => {
    const errorStore = configureStore({
      reducer: {
        roles: rolesReducer,
        services: servicesReducer,
        parameters: parametersReducer,
      },
      preloadedState: {
        roles: {
          items: [],
          loading: false,
          error: 'Failed to load roles',
          selectedRole: null,
          businessUnits: [],
          filter: {},
        },
        services: { items: [], loading: false, error: null, selectedService: null, serviceGroups: [] },
        parameters: { items: [], loading: false, error: null, selectedParameter: null },
      },
    });

    render(
      <Provider store={errorStore}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </Provider>
    );

    expect(screen.getByText('Failed to load roles')).toBeInTheDocument();
  });
});
```

---

## Integration Testing

### Testing Feature Workflows

```typescript
// src/__tests__/integrations/roleWorkflow.test.ts
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { MemoryRouter } from 'react-router';
import { configureStore } from '@reduxjs/toolkit';
import App from '../../App';
import * as api from '../../api/endpoints';

jest.mock('../../api/endpoints');

describe('Role CRUD Workflow', () => {
  let store: any;

  beforeEach(() => {
    jest.clearAllMocks();
    // Setup store with all slices
    store = configureStore({
      reducer: {
        // All reducers
      },
    });
  });

  it('should complete full role creation workflow', async () => {
    const user = userEvent.setup();
    const newRole = { id: '3', name: 'Manager', businessUnitId: 'bu1', type: 'user', isActive: true };

    (api.api.roles.create as jest.Mock).mockResolvedValue(newRole);

    render(
      <Provider store={store}>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </Provider>
    );

    // Navigate to create role
    const addRoleButton = screen.getByText('Add New');
    await user.click(addRoleButton);

    // Fill form
    await user.type(screen.getByLabelText('Role Name'), 'Manager');
    await user.selectOptions(screen.getByLabelText('Business Unit'), 'bu1');

    // Submit
    await user.click(screen.getByText('Create Role'));

    // Verify success
    await waitFor(() => {
      expect(screen.getByText(/Manager.*created/i)).toBeInTheDocument();
    });

    // Verify API was called
    expect(api.api.roles.create).toHaveBeenCalledWith(
      expect.objectContaining({ name: 'Manager' })
    );

    // Verify data updated in store
    const state = store.getState();
    expect(state.roles.items).toContainEqual(newRole);
  });

  it('should handle role creation error', async () => {
    const user = userEvent.setup();
    const errorMessage = 'Role already exists';

    (api.api.roles.create as jest.Mock).mockRejectedValue(
      new Error(errorMessage)
    );

    render(
      <Provider store={store}>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </Provider>
    );

    // Navigate and fill form
    await user.click(screen.getByText('Add New'));
    await user.type(screen.getByLabelText('Role Name'), 'Admin');
    await user.click(screen.getByText('Create Role'));

    // Verify error displayed
    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument();
    });
  });
});
```

---

## E2E Testing

The regression agent auto-detects whether the project uses Cypress or Playwright and generates appropriate tests. Both frameworks use MSW-style isolated mocks.

### Cypress E2E Tests

```typescript
// cypress/e2e/roleManagement.cy.ts
describe('Role Management E2E', () => {
  beforeEach(() => {
    cy.login('admin@example.com', 'password');
    cy.visit('/dashboard');
  });

  it('should create a new role', () => {
    cy.contains('Add New').click();
    cy.get('input[name="name"]').type('QA Manager');
    cy.get('select[name="businessUnitId"]').select('bu1');
    cy.contains('Create Role').click();

    cy.contains('Role created successfully').should('be.visible');
    cy.get('select[name="roles"] option').should('contain', 'QA Manager');
  });

  it('should validate required fields', () => {
    cy.contains('Add New').click();
    cy.contains('Create Role').click();

    cy.contains('Role name is required').should('be.visible');
    cy.contains('Business unit is required').should('be.visible');
  });

  it('should display roles in dropdown', () => {
    cy.get('select[name="roles"]').should('have.option', 'Admin');
    cy.get('select[name="roles"]').should('have.option', 'User');
  });

  it('should complete role assignment workflow', () => {
    cy.get('select[name="roles"]').select('Admin');
    cy.get('select[name="action"]').select('edit');
    cy.contains('Apply').click();

    cy.url().should('include', '/roles/1/edit');
    cy.contains('Edit Role').should('be.visible');
  });
});
```

### Playwright E2E Tests

```typescript
// e2e/regression/role-management.spec.ts
import { test, expect } from '../fixtures/msw.fixture';

test.describe('Role Management — regression', () => {
  test.beforeEach(async ({ mockPage }) => {
    await mockPage.goto('/dashboard');
  });

  test('should create a new role', async ({ mockPage }) => {
    await mockPage.locator('[data-testid="add-new-button"]').click();
    await mockPage.locator('input[name="name"]').fill('QA Manager');
    await mockPage.locator('select[name="businessUnitId"]').selectOption('bu1');
    await mockPage.locator('[data-testid="create-role-button"]').click();

    await expect(mockPage.locator('[data-testid="success-message"]')).toContainText('Role created successfully');
  });

  test('should validate required fields', async ({ mockPage }) => {
    await mockPage.locator('[data-testid="add-new-button"]').click();
    await mockPage.locator('[data-testid="create-role-button"]').click();

    await expect(mockPage.locator('[data-testid="name-error"]')).toContainText('Role name is required');
    await expect(mockPage.locator('[data-testid="bu-error"]')).toContainText('Business unit is required');
  });

  test('should handle API error', async ({ page }) => {
    await page.route('**/api/router/roles', route =>
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Server error' }),
      })
    );
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
  });
});
```

### Playwright MSW Mock Setup

```typescript
// e2e/mocks/handlers.ts
export interface MockRoute {
  method: string;
  url: string;
  status?: number;
  body: unknown;
}

export const handlers: MockRoute[] = [
  { method: 'GET', url: '/api/router/roles', body: { items: [{ id: '1', name: 'Admin' }] } },
  { method: 'POST', url: '/api/router/roles', status: 201, body: { id: '2', name: 'New Role' } },
];
```

```typescript
// e2e/mocks/bridge.ts
import { Page } from '@playwright/test';
import { MockRoute } from './handlers';

export async function applyMocks(page: Page, mocks: MockRoute[]): Promise<void> {
  for (const mock of mocks) {
    await page.route(`**${mock.url}`, async (route) => {
      if (route.request().method() === mock.method) {
        await route.fulfill({
          status: mock.status ?? 200,
          contentType: 'application/json',
          body: JSON.stringify(mock.body),
        });
      } else {
        await route.fallback();
      }
    });
  }
}
```

---

## Test Coverage

### Measuring Code Coverage

```bash
# Run tests with coverage
npm test -- --coverage

# Generate HTML report
npm test -- --coverage --coverageReporters=html

# Enforce coverage thresholds
npm test -- --coverage --collectCoverageFrom='src/**/*.ts(x)' \
  --coverageThreshold='{
    "global": {
      "branches": 80,
      "functions": 80,
      "lines": 80,
      "statements": 80
    }
  }'
```

---

## Mocking Strategies

### Mock API Responses

```typescript
// src/__mocks__/api.ts
export const mockApi = {
  roles: {
    fetchAll: jest.fn(() => Promise.resolve([
      { id: '1', name: 'Admin', businessUnitId: 'bu1', type: 'admin', isActive: true },
    ])),
    fetchById: jest.fn((id: string) => Promise.resolve(
      { id, name: 'Mock Role', businessUnitId: 'bu1', type: 'user', isActive: true }
    )),
    create: jest.fn((data) => Promise.resolve({ id: '3', ...data })),
  },
  services: {
    fetchAll: jest.fn(() => Promise.resolve([])),
  },
  parameters: {
    fetchAll: jest.fn(() => Promise.resolve([])),
  },
};
```

---

## Summary Checklist

- ✅ Unit test all reducers and actions
- ✅ Test async thunks with mocked API
- ✅ Test component rendering and interactions
- ✅ Test integration workflows
- ✅ Create E2E tests for critical flows
- ✅ Maintain 80%+ code coverage
- ✅ Mock external API calls
- ✅ Test error scenarios
- ✅ Test loading states
- ✅ Run tests in CI/CD pipeline

---

## References
- Jest: https://jestjs.io
- React Testing Library: https://testing-library.com
- Cypress: https://www.cypress.io
- Playwright: https://playwright.dev
- MSW (Mock Service Worker): https://mswjs.io
- Component Audit Checklist: COMPONENT_AUDIT_CHECKLIST.md
