# Navigation Patterns for MCA2

MemoryRouter routing, navigation, and route guard patterns for migrated MCA2 applications.

Last Updated: 2026-05-19 | Version: 1.0.0

---

## Table of Contents

1. [Why MemoryRouter](#why-memoryrouter)
2. [Basic Route Setup](#basic-route-setup)
3. [Navigation Between Pages](#navigation-between-pages)
4. [Route Nesting and Layouts](#route-nesting-and-layouts)
5. [Route Parameters](#route-parameters)
6. [Navigation State](#navigation-state)
7. [Protected Routes](#protected-routes)
8. [Back Button Handling](#back-button-handling)
9. [Navigation After Async Actions](#navigation-after-async-actions)
10. [Route Constants](#route-constants)

---

## Why MemoryRouter

MCA2 modules run inside a parent shell application that controls the browser URL. The module does NOT own the address bar. Using `BrowserRouter` would conflict with the shell's routing.

`MemoryRouter` keeps all route state in memory — no URL changes, no browser history conflicts.

**Iron Rule:** NEVER use `BrowserRouter` in MCA2. ALWAYS use `MemoryRouter` from `react-router`.

---

## Basic Route Setup

```typescript
// src/App.tsx
import React from 'react';
import { MemoryRouter, Routes, Route } from 'react-router';
import Dashboard from './pages/Dashboard/Dashboard';
import RoleManagement from './pages/RoleManagement/RoleManagement';
import RoleDetail from './pages/RoleDetail/RoleDetail';
import NotFound from './pages/NotFound/NotFound';

const App: React.FC = () => (
  <MemoryRouter initialEntries={['/']}>
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/roles" element={<RoleManagement />} />
      <Route path="/roles/:id" element={<RoleDetail />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  </MemoryRouter>
);

export default App;
```

**Key points:**
- `initialEntries={['/']}` sets the starting route
- Always include a catch-all `path="*"` route
- Routes are flat by default — nest only when pages share a layout

---

## Navigation Between Pages

### Programmatic Navigation (useNavigate)

```typescript
// src/pages/Dashboard/Dashboard.tsx
import { useNavigate } from 'react-router';
import { Button } from '@barclays/blueprint-react';

const Dashboard: React.FC = () => {
  const navigate = useNavigate();

  const handleManageRoles = () => {
    navigate('/roles');
  };

  const handleViewRole = (roleId: string) => {
    navigate(`/roles/${roleId}`);
  };

  return (
    <Section>
      <SectionItem>
        <Button onClick={handleManageRoles}>Manage Roles</Button>
      </SectionItem>
    </Section>
  );
};
```

### Declarative Navigation (Link)

```typescript
// src/components/common/NavMenu.tsx
import { Link } from 'react-router';
import { Type } from '@barclays/blueprint-react';

const NavMenu: React.FC = () => (
  <nav>
    <Link to="/"><Type>Dashboard</Type></Link>
    <Link to="/roles"><Type>Roles</Type></Link>
    <Link to="/services"><Type>Services</Type></Link>
  </nav>
);
```

**When to use which:**
- `useNavigate()` — after events (button click, form submit, async completion)
- `<Link>` — static navigation menus, breadcrumbs, inline text links

---

## Route Nesting and Layouts

When multiple pages share a common layout (sidebar, header), use nested routes with `<Outlet>`.

```typescript
// src/App.tsx
import { MemoryRouter, Routes, Route } from 'react-router';
import MainLayout from './components/common/MainLayout';
import Dashboard from './pages/Dashboard/Dashboard';
import RoleManagement from './pages/RoleManagement/RoleManagement';
import Settings from './pages/Settings/Settings';

const App: React.FC = () => (
  <MemoryRouter initialEntries={['/']}>
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/roles" element={<RoleManagement />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
    </Routes>
  </MemoryRouter>
);
```

```typescript
// src/components/common/MainLayout.tsx
import { Outlet } from 'react-router';
import { Section, SectionItem } from '@barclays/blueprint-react';
import { NavMenu } from './NavMenu';

const MainLayout: React.FC = () => (
  <Section>
    <SectionItem>
      <NavMenu />
    </SectionItem>
    <SectionItem>
      <Outlet />
    </SectionItem>
  </Section>
);

export default MainLayout;
```

---

## Route Parameters

### Reading Parameters

```typescript
// src/pages/RoleDetail/RoleDetail.tsx
import { useParams } from 'react-router';

interface RoleDetailParams {
  id: string;
}

const RoleDetail: React.FC = () => {
  const { id } = useParams<keyof RoleDetailParams>() as RoleDetailParams;
  const role = useAppSelector((state) => state.roles.items.find((r) => r.id === id));

  if (!role) return <Type>Role not found</Type>;

  return <RoleForm role={role} />;
};
```

### Optional Parameters

```typescript
// Route: <Route path="/roles/:id?" element={<RoleManagement />} />

const RoleManagement: React.FC = () => {
  const { id } = useParams();

  // id is string | undefined
  if (id) {
    return <RoleDetail roleId={id} />;
  }
  return <RoleList />;
};
```

---

## Navigation State

Pass data between routes without putting it in the URL.

### Sending State

```typescript
// src/pages/RoleManagement/RoleManagement.tsx
const handleEditRole = (role: Role) => {
  navigate(`/roles/${role.id}/edit`, { state: { role } });
};
```

### Receiving State

```typescript
// src/pages/RoleEdit/RoleEdit.tsx
import { useLocation, useParams } from 'react-router';

interface LocationState {
  role?: Role;
}

const RoleEdit: React.FC = () => {
  const { id } = useParams();
  const location = useLocation();
  const passedRole = (location.state as LocationState)?.role;

  // Use passed role if available, otherwise fetch from Redux/API
  const role = passedRole ?? useAppSelector((state) =>
    state.roles.items.find((r) => r.id === id)
  );

  if (!role) return <Loading size="lg" shape="circle" ariaLabel="Loading role" />;

  return <RoleForm role={role} />;
};
```

---

## Protected Routes

Role-based access control for pages that require specific permissions.

```typescript
// src/components/common/ProtectedRoute.tsx
import React from 'react';
import { Navigate } from 'react-router';
import { useAppSelector } from '../../store/hooks';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const userRole = useAppSelector((state) => state.auth.role);

  if (requiredRole && userRole !== requiredRole) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;
```

### Usage in Routes

```typescript
// src/App.tsx
<Route
  path="/admin"
  element={
    <ProtectedRoute requiredRole="admin">
      <AdminPanel />
    </ProtectedRoute>
  }
/>
```

---

## Back Button Handling

Since MemoryRouter doesn't use browser history, implement custom back navigation.

```typescript
// src/components/common/BackButton.tsx
import { useNavigate } from 'react-router';
import { Button, Icon } from '@barclays/blueprint-react';

interface BackButtonProps {
  fallbackPath?: string;
  label?: string;
}

const BackButton: React.FC<BackButtonProps> = ({
  fallbackPath = '/',
  label = 'Back',
}) => {
  const navigate = useNavigate();

  const handleBack = () => {
    navigate(-1);
  };

  return (
    <Button variant="subtle" onClick={handleBack} aria-label={label}>
      <Icon icon="chevron-left" size="sm" />
      {label}
    </Button>
  );
};

export default BackButton;
```

**Note:** `navigate(-1)` works with MemoryRouter's internal history stack. If the user is on the first page (no history), it does nothing — which is safe.

---

## Navigation After Async Actions

Navigate after a Redux thunk completes (e.g., after successful form submission).

```typescript
// src/pages/RoleCreate/useRoleCreate.ts
import { useNavigate } from 'react-router';
import { useAppDispatch } from '../../store/hooks';
import { createRole } from '../../store/slices/rolesSlice';

export function useRoleCreate() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();

  const handleSubmit = async (values: CreateRoleRequest) => {
    try {
      await dispatch(createRole(values)).unwrap();
      navigate('/roles');
    } catch (error) {
      // Error is handled by the slice — stay on the form
    }
  };

  return { handleSubmit };
}
```

**Rules:**
- Always `await dispatch(thunk).unwrap()` before navigating
- Only navigate on success — errors keep the user on the current page
- Put navigation logic in the custom hook, not the component

---

## Route Constants

Centralize route paths to avoid typos and enable refactoring.

```typescript
// src/utils/constants.ts

export const ROUTES = {
  DASHBOARD: '/',
  ROLES: '/roles',
  ROLE_DETAIL: '/roles/:id',
  ROLE_CREATE: '/roles/create',
  SERVICES: '/services',
  SETTINGS: '/settings',
} as const;

// Helper for parameterized routes:
export function roleDetailPath(id: string): string {
  return `/roles/${id}`;
}
```

```typescript
// Usage:
import { ROUTES, roleDetailPath } from '../../utils/constants';

navigate(ROUTES.ROLES);
navigate(roleDetailPath(role.id));
```
