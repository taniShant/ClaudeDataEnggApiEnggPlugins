---
name: test
description: >
    Chameleon/React Native-specific test patterns for SDF journeys. Covers jest config
    split, renderWithProviders, chameleon-* bridge mocking, fixture file conventions,
    RTL query priority in React Native, platform spec file naming, and Stryker mutation
    config. Layered on top of barclays-buk-standards:testing — load both. SDF-specific
    thresholds override the generic standard where they differ.
user-invocable: false
---

# SDF Test Patterns

> **Layered on:** `barclays-buk-standards:testing`
> **SDF threshold override:** 95% minimum (branches, functions, lines, statements) — overrides the 90% line-only threshold in the generic standard
> **Owner:** BUK Retail CAPL
> **Review trigger:** Chameleon framework version bump, jest config change, or Stryker major version bump

> [Jest testing standards](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/jest-testing/) | [Mutation testing](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/mutation-testing/) | [Cross-platform coding](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/cross-platform/)

---

## 1. Jest Configuration

SDF projects use a three-file jest config structure. **Never collapse these into a single file.**

```
jest.config.ts          ← base config, delegates to platform configs
jest.config.web.ts      ← web (jsdom) environment
jest.config.native.ts   ← native (react-native) environment
```

### Base config

```typescript
// jest.config.ts
import type { Config } from 'jest';

const config: Config = {
  projects: [
    '<rootDir>/jest.config.web.ts',
    '<rootDir>/jest.config.native.ts',
  ],
};

export default config;
```

### Web config

```typescript
// jest.config.web.ts
import type { Config } from 'jest';

const config: Config = {
  displayName: 'web',
  testEnvironment: 'jsdom',
  testMatch: ['**/*.web.spec.{ts,tsx}'],
  transform: {
    '^.+\\.(ts|tsx)$': ['babel-jest', { presets: ['@babel/preset-react', '@babel/preset-typescript'] }],
  },
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
  coveragePathIgnorePatterns: ['/node_modules/', '/__mocks__/'],
  coverageThreshold: {
    global: {
      branches: 95,
      functions: 95,
      lines: 95,
      statements: 95,
    },
  },
};

export default config;
```

### Native config

```typescript
// jest.config.native.ts
import type { Config } from 'jest';

const config: Config = {
  displayName: 'native',
  preset: 'react-native',
  testMatch: ['**/*.native.spec.{ts,tsx}'],
  transformIgnorePatterns: [
    'node_modules/(?!(react-native|@react-native|@barclays/chameleon-blueprint|@barclays/chameleon-router)/)',
  ],
  setupFilesAfterFramework: ['<rootDir>/jest.setup.ts'],
  coverageThreshold: {
    global: {
      branches: 95,
      functions: 95,
      lines: 95,
      statements: 95,
    },
  },
};

export default config;
```

### jest.setup.ts

```typescript
// jest.setup.ts
import 'react-native-gesture-handler/jestSetup';

// Silence expected warnings from chameleon-blueprint internals
jest.mock('react-native/Libraries/Animated/NativeAnimatedHelper');
```

`jest-fail-on-console` is configured in `jest.setup.ts` — unexpected `console.error` or `console.warn` calls fail the test run. Do not suppress real errors to make tests pass.

---

## 2. Spec File Naming

| File type | Convention |
|---|---|
| Shared component or hook | `ComponentName.web.spec.tsx` + `ComponentName.native.spec.tsx` |
| Web-only component | `ComponentName.web.spec.tsx` only |
| Native-only component (`.native.tsx`) | `ComponentName.native.spec.tsx` only |
| Utility / pure function | `util.spec.ts` (no platform suffix — runs in both) |
| RTK slice or selector | `sliceName.spec.ts` |
| RTK Query endpoint | `api.spec.ts` |

Every screen in `src/screens/` requires both `*.web.spec.tsx` and `*.native.spec.tsx`. No exceptions.

---

## 3. renderWithProviders

All component tests that touch Redux state or RTK Query must use `renderWithProviders` from `src/state/mock/store-test-utils.tsx`. Never render with a manually constructed `<Provider>`.

```typescript
// src/state/mock/store-test-utils.tsx — reference implementation
import React, { PropsWithChildren } from 'react';
import { render, RenderOptions } from '@testing-library/react-native';
import { Provider } from 'react-redux';
import { setupStore, AppStore, RootState } from '../store';

interface ExtendedRenderOptions extends Omit<RenderOptions, 'queries'> {
  preloadedState?: Partial<RootState>;
  store?: AppStore;
}

export function renderWithProviders(
  ui: React.ReactElement,
  {
    preloadedState = {},
    store = setupStore(preloadedState),
    ...renderOptions
  }: ExtendedRenderOptions = {}
) {
  function Wrapper({ children }: PropsWithChildren<{}>): React.ReactElement {
    return <Provider store={store}>{children}</Provider>;
  }
  return { store, ...render(ui, { wrapper: Wrapper, ...renderOptions }) };
}
```

### Usage

```typescript
import { renderWithProviders } from '../../state/mock/store-test-utils';
import paymentFixture from '../../__fixtures__/payment.json';

it('should display the payment amount', () => {
  const { getByText } = renderWithProviders(<PaymentScreen />, {
    preloadedState: {
      payment: { data: paymentFixture, status: 'succeeded' },
    },
  });
  expect(getByText('£250.00')).toBeTruthy();
});
```

---

## 4. Mocking chameleon-* Bridge Libraries

All `@barclays/chameleon-*` bridge libraries MUST be mocked. Do not let bridge calls hit real implementations in tests — they expect a native host app context that does not exist in jest.

Place mocks in `src/__mocks__/@barclays/` (auto-picked up by jest module resolution).

### chameleon-bridge

```typescript
// src/__mocks__/@barclays/chameleon-bridge.ts
const mockBridge = {
  callApiOperation: jest.fn(),
  callLegacyOperation: jest.fn(),
  goBack: jest.fn(),
  getImage: jest.fn().mockResolvedValue('https://mock-image-url/image.png'),
  getStorageItem: jest.fn().mockResolvedValue(null),
  setStorageItem: jest.fn().mockResolvedValue(undefined),
};

export default mockBridge;
export const ChameleonBridge = mockBridge;
```

### chameleon-router

```typescript
// src/__mocks__/@barclays/chameleon-router.ts
export const useNavigate = jest.fn();
export const useParams = jest.fn().mockReturnValue({});
export const useLocation = jest.fn().mockReturnValue({ pathname: '/' });
export const Navigate = jest.fn(() => null);
```

### Resetting between tests

```typescript
beforeEach(() => {
  jest.clearAllMocks();
});
```

---

## 5. API Response Fixtures

API response mocks MUST use JSON files — not inline objects. JSON files live inside `mockBridge/` alongside the handler that returns them. This keeps mock data co-located with the bridge handler that owns it and makes it reusable across specs.

```
mockBridge/
├── index.ts
└── handlers/
    ├── getAccountSummary.ts
    ├── account-summary.json
    ├── getPaymentDetails.ts
    ├── payment-confirmation.json
    └── error-responses/
        ├── 400-validation.json
        └── 503-unavailable.json
```

### Fixture file conventions

```json
// mockBridge/handlers/account-summary.json
{
  "accountId": "ACC-001",
  "displayName": "Current Account",
  "balance": 1250.00,
  "currency": "GBP",
  "lastUpdated": "2026-07-13T10:00:00Z"
}
```

### Usage in tests

Import directly from `mockBridge/handlers/` in specs. The `chameleon-bridge` mock in `src/__mocks__/@barclays/chameleon-bridge.ts` exposes `callApiOperation` as a `jest.fn()` — configure it per test using `mockResolvedValueOnce`:

```typescript
import ChameleonBridge from '@barclays/chameleon-bridge';
import accountSummaryFixture from '../../../mockBridge/handlers/account-summary.json';
import errorFixture from '../../../mockBridge/handlers/error-responses/503-unavailable.json';

it('should render account balance', async () => {
  (ChameleonBridge.callApiOperation as jest.Mock).mockResolvedValueOnce(accountSummaryFixture);
  const { findByText } = renderWithProviders(<AccountScreen accountId="ACC-001" />);
  expect(await findByText('Current Account')).toBeTruthy();
});

it('should show full-screen error when service unavailable', async () => {
  (ChameleonBridge.callApiOperation as jest.Mock).mockRejectedValueOnce(errorFixture);
  const { findByRole } = renderWithProviders(<AccountScreen accountId="ACC-001" />);
  expect(await findByRole('alert')).toBeTruthy();
});
```

---

## 6. RTL Query Priority in React Native

Testing Library query priority applies in the React Native context with some differences from web. Use this order:

| Priority | Query | When |
|---|---|---|
| 1st | `getByRole` | Interactive elements: buttons, inputs, links |
| 2nd | `getByLabelText` | Form inputs with associated labels |
| 3rd | `getByText` | Non-interactive text content |
| 4th | `getByDisplayValue` | Current value of form inputs |
| 5th | `getByTestId` | Last resort — only when no semantic query works |

**React Native specifics:**

`getByRole` works differently in React Native. Role is derived from `accessibilityRole` or the component type:

```typescript
// Button rendered by Blueprint maps to role="button"
expect(getByRole('button', { name: 'Confirm payment' })).toBeTruthy();

// TextInput
expect(getByRole('textbox')).toBeTruthy();

// Use getByText for Type/text content
expect(getByText('£250.00')).toBeTruthy();
```

`getByPlaceholderText` works in React Native and is acceptable for `FormInput` when no label query is available.

Avoid `getByTestId` as the primary query — it tests implementation rather than behaviour. Only use it when the element has no accessible role or text.

---

## 7. Testing RTK Query Endpoints

RTK Query endpoints need the full store setup. Use `renderWithProviders` with a pre-built store and assert on the loaded state after the query resolves.

```typescript
// PaymentScreen.web.spec.tsx
import { renderWithProviders } from '../../state/mock/store-test-utils';
import { server } from '../../__mocks__/server';
import { rest } from 'msw';
import paymentFixture from '../../__fixtures__/payment-confirmation.json';
import { PaymentScreen } from './PaymentScreen';

describe('PaymentScreen', () => {
  describe('when payment data loads successfully', () => {
    beforeEach(() => {
      server.use(
        rest.get('/api/payments/:id', (req, res, ctx) =>
          res(ctx.json(paymentFixture))
        )
      );
    });

    it('should display the payee name', async () => {
      const { findByText } = renderWithProviders(
        <PaymentScreen paymentId="PAY-001" />
      );
      expect(await findByText('Jane Smith')).toBeTruthy();
    });

    it('should display the formatted amount', async () => {
      const { findByText } = renderWithProviders(
        <PaymentScreen paymentId="PAY-001" />
      );
      expect(await findByText('£250.00')).toBeTruthy();
    });
  });

  describe('when the API returns an error', () => {
    beforeEach(() => {
      server.use(
        rest.get('/api/payments/:id', (req, res, ctx) =>
          res(ctx.status(503))
        )
      );
    });

    it('should render the full-screen error state', async () => {
      const { findByRole } = renderWithProviders(
        <PaymentScreen paymentId="PAY-001" />
      );
      expect(await findByRole('alert')).toBeTruthy();
    });
  });
});
```

Use `findBy*` (async) rather than `getBy*` when waiting for RTK Query to resolve. `waitFor` + `getBy*` is also acceptable.

---

## 8. Testing Loading States

Blueprint skeleton/ghost components should appear before data resolves and be absent after.

```typescript
it('should show loading skeleton while data is pending', () => {
  // Delay the response so we can assert on the loading state
  server.use(
    rest.get('/api/account', (req, res, ctx) =>
      res(ctx.delay(500), ctx.json(accountFixture))
    )
  );

  const { getByTestId, queryByTestId } = renderWithProviders(<AccountScreen />);
  // Skeleton visible immediately
  expect(getByTestId('account-skeleton')).toBeTruthy();
});

it('should remove loading skeleton after data loads', async () => {
  const { findByText, queryByTestId } = renderWithProviders(<AccountScreen />);
  await findByText('Current Account');
  expect(queryByTestId('account-skeleton')).toBeNull();
});
```

---

## 9. Stryker Configuration

Stryker runs per platform via the jest config split. The base config:

```typescript
// stryker.config.ts
import type { Config } from '@stryker-mutator/api/core';

const config: Config = {
  testRunner: 'jest',
  jest: {
    projectType: 'custom',
    configFile: 'jest.config.ts',
  },
  mutate: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!src/**/*.native.spec.{ts,tsx}',
    '!src/**/*.web.spec.{ts,tsx}',
    '!src/__mocks__/**',
    '!src/__fixtures__/**',
    '!src/state/mock/**',
  ],
  thresholds: {
    high: 80,
    low: 70,
    break: 65,
  },
  reporters: ['html', 'clear-text', 'progress'],
  htmlReporter: { fileName: 'reports/mutation/mutation.html' },
  timeoutMS: 10000,
  concurrency: 4,
};

export default config;
```

### Stryker threshold interpretation

| Threshold | Meaning |
|---|---|
| `break` | CI hard fail — MR cannot merge |
| `low` | Warning in CI output |
| `high` | Clean pass |

If a mutant survives, write a targeted test that kills it — do not raise the threshold.

> **Full mutation testing guidance:** [Mutation Testing](https://pages.gitlab.barcapint.com/barclays/golden-path/chameleon-docs/docs/getting-started/best-practice/mutation-testing/)

---

## 10. Testing Slice Reducers and Selectors

```typescript
// src/state/payment/payment.slice.spec.ts
import { paymentReducer, setPaymentStatus, selectPaymentData } from './payment.slice';

describe('paymentSlice', () => {
  describe('setPaymentStatus', () => {
    it('should update status to succeeded', () => {
      const initialState = { status: 'idle', data: null };
      const nextState = paymentReducer(initialState, setPaymentStatus('succeeded'));
      expect(nextState.status).toBe('succeeded');
    });

    it('should not mutate prior state', () => {
      const initialState = { status: 'idle', data: null };
      paymentReducer(initialState, setPaymentStatus('succeeded'));
      expect(initialState.status).toBe('idle');
    });
  });

  describe('selectPaymentData', () => {
    it('should return null when no data is loaded', () => {
      const state = { payment: { status: 'idle', data: null } };
      expect(selectPaymentData(state as any)).toBeNull();
    });
  });
});
```

---

## 11. Accessibility Testing in Jest

Source of truth: `barclays-buk-standards:accessibility` + `chameleon-docs/docs/getting-started/best-practice/accessibility/index.mdx`

Jest-level a11y tests form the second layer of the Chameleon a11y testing pyramid (ESLint static → **Jest** → Cypress axe E2E → Device). They run with every `npm run test:coverage` build.

### Web — `jest-axe`

Install once per project:

```bash
npm install --save-dev jest-axe
```

In every `*.web.spec.tsx` a11y file:

```typescript
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';

expect.extend(toHaveNoViolations);

it('has no axe violations', async () => {
  const { container } = render(<MyScreen {...minimalProps} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Run axe against the full rendered output — not a fragment. Pass the minimum props required to render the screen in its default (non-loading, non-error) state.

### React Native — RNTL accessibility queries

No additional package required. Use queries from `@testing-library/react-native` that assert on what assistive technology sees:

```typescript
import { render, screen, isHiddenFromAccessibility } from '@testing-library/react-native';

// Interactive element has the correct accessible name
it('primary CTA has a descriptive accessible name', () => {
  render(<MyScreen {...minimalProps} />);
  expect(screen.getByRole('button', { name: 'Confirm payment' })).toBeTruthy();
});

// State is conveyed to assistive technology
it('disabled CTA conveys disabled state', () => {
  render(<MyScreen {...minimalProps} isLoading />);
  expect(screen.getByRole('button', { name: 'Confirm payment', disabled: true })).toBeTruthy();
});

// Error region is visible to assistive technology
it('validation error is not hidden from assistive technology', () => {
  render(<MyScreen {...minimalProps} error="Card number is invalid" />);
  const error = screen.getByLabelText('Validation error: card number is invalid');
  expect(isHiddenFromAccessibility(error)).toBe(false);
});
```

`isHiddenFromAccessibility` returns `true` when an element or any ancestor is hidden from AT. Use it to assert that a region is visible to screen readers, or that a deliberately suppressed decorative element remains hidden.

### Spec file naming for a11y

| Platform | File |
|---|---|
| Web | `{ScreenName}.a11y.web.spec.tsx` |
| Native | `{ScreenName}.a11y.native.spec.tsx` |

A11y specs are co-located with the screen component in `src/screens/{ScreenName}/`.

### What a11y specs must cover (minimum)

For every screen:
1. No axe violations on the default render (web)
2. Primary CTA has a descriptive accessible name matching the visible label
3. All interactive elements reachable via `getByRole` — no `getByTestId` for interactive elements
4. Disabled/loading state conveyed to AT (`getByRole` with `{ disabled: true }` or `{ busy: true }`)
5. Error messages not hidden from AT (`isHiddenFromAccessibility` returns `false`)
6. Form inputs have associated labels (reachable via `getByLabelText`)

### jest config additions for a11y

A11y web specs run under the jsdom environment. Add the a11y test match to `jest.config.web.ts`:

```typescript
testMatch: ['**/*.web.spec.{ts,tsx}', '**/*.a11y.web.spec.{ts,tsx}'],
```

A11y native specs run under the react-native environment. Add to `jest.config.native.ts`:

```typescript
testMatch: ['**/*.native.spec.{ts,tsx}', '**/*.a11y.native.spec.{ts,tsx}'],
```

---

## Areas for Specialist Extension

- **Mobile team** — Device-specific rendering tests (safe area, notch), Detox E2E patterns
- **Online Banking team** — MSW handler library for OB-specific API shapes
- **QE team** — Contract test patterns for DAF endpoint validation
