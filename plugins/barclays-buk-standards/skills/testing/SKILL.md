---
name: testing
description: BUK testing standards. Covers coverage thresholds, mutation testing, test naming, and what to mock vs not. Use when generating or reviewing test code.
user-invocable: false
---

# BUK Testing Standards

> **Source:** Derived from BUK automation-tester agent and BUK test quality conventions
> **Owner:** BUK Principal Engineers
> **Review trigger:** Annual, or when test tooling or coverage thresholds change
> **Status:** Draft

---

## 1. Coverage Thresholds

All test suites must meet these minimum thresholds:

- **Line coverage**: 90% minimum (JaCoCo for Java, Istanbul/c8 for JS/TS)
- **Mutation score**: 90% minimum (pitest for Java)

Coverage for its own sake is not acceptable. Tests must assert on meaningful outcomes, not just execute code.

---

## 2. Testing Methodology

Follow this 4-step process for every test writing task.

### Step 1: Analyse What to Test

Before writing any test:
1. Read the component or module being tested
2. Identify all public interfaces (functions, props, events, API endpoints)
3. Map out code paths — branches, conditionals, loops, error handlers
4. Identify external dependencies that need mocking
5. Note any existing test patterns in the project

### Step 2: Plan Test Structure

Organise tests logically:

```
describe('[Module/Component Name]', () => {
  describe('[Feature/Method]', () => {
    it('should [expected behaviour] when [condition]', () => {});
    it('should [expected behaviour] when [edge case]', () => {});
    it('should [handle error] when [failure condition]', () => {});
  });
});
```

### Step 3: Write Tests

For each test, follow Arrange / Act / Assert:
- **Arrange** — Set up preconditions and inputs
- **Act** — Execute the behaviour being tested
- **Assert** — Verify the expected outcome

### Step 4: Self-Verify Quality

Before considering tests complete, verify all of the following:

- [ ] Every code branch has at least one test
- [ ] Error paths are tested, not just happy paths
- [ ] Assertions check meaningful outcomes (not just "didn't crash")
- [ ] Mocks are minimal — only mock what you must
- [ ] Tests are independent — no test depends on another test's side effects
- [ ] Test names describe the behaviour being verified
- [ ] Async operations are properly awaited

---

## 3. Test Types

### Unit Tests
- Test individual functions and components in isolation
- Mock external dependencies
- Fast execution, focused assertions

### Contract Tests
- Validate API contracts match the specification in `contracts/`
- Test request/response shapes against OpenAPI schemas
- Verify error response formats

### Integration Tests
- Test component interactions and data flow
- Minimal mocking — test real integrations where practical
- Focus on boundaries between modules

### End-to-End Tests
- Test complete user journeys from the specification
- Map directly to acceptance scenarios (Given/When/Then)
- Use quickstart scenarios when available

---

## 4. Multi-Platform Test Splits

When the project uses platform-specific files:

- `*.native.spec.tsx` — Tests for React Native (iOS/Android) components
- `*.web.spec.tsx` — Tests for Web-specific components
- Create **both** test files when the component has platform variants
- Use the correct testing library imports per platform:
  - Native: `@testing-library/react-native`
  - Web: `@testing-library/react`

---

## 5. Common Patterns

### Mocking

Prefer targeted mocks over broad `jest.mock()`. Always clean up after each test.

```typescript
const mockService = { getData: jest.fn().mockResolvedValue(mockData) };

afterEach(() => jest.restoreAllMocks());
```

### Async Testing

Always await async operations. Use `waitFor` when asserting on async UI state.

```typescript
it('should load data', async () => {
  render(<Component />);
  await waitFor(() => expect(screen.getByText('loaded')).toBeTruthy());
});
```

### Error State Testing

Test that the component responds correctly when dependencies fail.

```typescript
it('should display error message when API fails', async () => {
  mockService.getData.mockRejectedValueOnce(new Error('Network error'));
  render(<Component />);
  await waitFor(() => expect(screen.getByText(/error/i)).toBeTruthy());
});
```

---

## 6. What NOT to Do

- **Do not modify production code** — only create or modify test files
- **Do not skip "simple" code** — all code paths get tested regardless of perceived simplicity
- **Do not use snapshot tests as primary strategy** — prefer explicit assertions
- **Do not write brittle tests** — tests that break on harmless refactoring provide no value

---

## Agent Self-Check

When applying this skill, confirm:

- [ ] Coverage targets (90% line, 90% mutation) are met or gaps are documented with rationale
- [ ] Every code branch has at least one test (Step 4 self-verify complete)
- [ ] Error paths are tested, not just happy paths
- [ ] Mocks are minimal and cleaned up with `jest.restoreAllMocks()`
- [ ] Test names follow the `should [behaviour] when [condition]` pattern
- [ ] Platform-specific test files created where component has platform variants
- [ ] No snapshot tests used as the primary assertion strategy
- [ ] Async operations are properly awaited

---

## Areas for Specialist Extension

This skill covers the BUK baseline. The following areas need extension by the relevant teams:

- **Mobile (iOS/Android)** — XCTest and Espresso patterns, device-specific coverage tooling
- **BUK Principal Engineers** — Test data management standards, contract test repository location, approved coverage enforcement tooling per platform
