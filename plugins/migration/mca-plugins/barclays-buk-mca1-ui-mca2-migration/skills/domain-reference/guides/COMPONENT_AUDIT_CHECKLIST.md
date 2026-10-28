# Component Audit Checklist

**Use before submitting any MCA2 component for code review**

Last Updated: March 25, 2026

---

## Pre-Submission Verification

Run this checklist for every component you create or modify:

### Architecture & Structure
- [ ] Component follows functional component pattern (no class components)
- [ ] Component properly organized in src/ directory hierarchy
- [ ] Component exports named export (not default) unless it's a page
- [ ] All imports are from actual packages (not non-existent packages)
- [ ] TypeScript types properly defined (no `any` types except where unavoidable)
- [ ] Component has JSDoc comment explaining purpose

### Blueprint-React Component Usage
- [ ] Component uses only Blueprint-React components (no custom divs for layout)
- [ ] All components from `@barclays/blueprint-react` exist in storybook
- [ ] FormItem uses render function pattern (never children wrapping)
- [ ] Dialog uses slot properties (head/foot/children) not nested components
- [ ] Table uses standard HTML elements (thead/tbody/tr/td)
- [ ] Button variants are valid (primary/secondary/subtle, not ghost/danger/tertiary)
- [ ] Type component used for all text (not bare divs or spans)
- [ ] Icon components have explicit size prop (xs, sm, md, lg, xl, 2xl)

### Layout & Styling
- [ ] No .module.css files for Blueprint components
- [ ] No custom CSS for layout (use Grid, Arrange, Section, Panel)
- [ ] Layout nesting minimal (2-3 SectionItems per Section max)
- [ ] SectionItem spacing used correctly (spacing="md" for sections)
- [ ] Grid.Col sizes valid (1of2, 1of3, 1of4, 1of6, 1of12, etc. - NOT 1of1)
- [ ] No inline styles for layout (use Blueprint components)
- [ ] Responsive design considered (use sizeXs, sizeMd props)
- [ ] All spacing uses Blueprint spacing system

### Data Handling & Validation
- [ ] Array.isArray() checks before calling .map() or array methods
- [ ] Null/undefined checks for optional data
- [ ] API response structure validated at service layer
- [ ] Error states handled gracefully
- [ ] Loading states shown during async operations
- [ ] Empty states handled when data is empty
- [ ] No assumptions about data structure

### Icon Usage
- [ ] Icon names exist in Blueprint (check BDL_TO_BLUEPRINT_REACT.md Section 8 for icon mapping)
- [ ] Icons have size prop (sm for buttons, md for alerts, lg for standalone)
- [ ] No icon names with -circle suffix (use tick, cross, info instead)
- [ ] Icons match context (checkmark for success, X for error, etc.)

### Button & Action Usage
- [ ] All buttons have consistent sizing (no mixed size="sm" and defaults)
- [ ] Primary action uses variant="primary"
- [ ] Secondary actions use variant="secondary"
- [ ] Dangerous actions use status="danger"
- [ ] ActionButton component used for consistent styling
- [ ] Button labels are clear and action-oriented
- [ ] Disabled state managed properly (isDisabled or disabled prop)

### Form Handling
- [ ] All form inputs use FormItem + render function pattern
- [ ] Form validation uses Yup schema
- [ ] Validation errors shown to user
- [ ] Form submission handled with loading state
- [ ] Success/error messages displayed post-submission
- [ ] Form state managed (using Formik or React Hook Form)
- [ ] Required fields marked clearly

### Redux Integration
- [ ] Redux hooks used correctly (useAppDispatch, useAppSelector)
- [ ] Selectors properly typed
- [ ] Thunks properly error-handled
- [ ] Loading/error states in Redux slice
- [ ] No Redux state duplication
- [ ] Redux state normalized (entities pattern for related data)

### Accessibility
- [ ] All interactive elements keyboard accessible
- [ ] ARIA labels for complex components
- [ ] Color not only indicator of state
- [ ] Focus visible on interactive elements
- [ ] Form labels properly associated with inputs
- [ ] Screen reader friendly text

### TypeScript Compliance
- [ ] No `any` types (use proper types from `src/types/`)
- [ ] All function parameters typed
- [ ] All return types specified
- [ ] Type errors resolved (npm run build succeeds)
- [ ] No TypeScript warnings in build output

### Error Handling
- [ ] Try-catch blocks in async functions
- [ ] API errors handled and displayed to user
- [ ] User-friendly error messages
- [ ] No error console.logs left in code
- [ ] Error boundaries considered for complex components

### Performance
- [ ] No unnecessary re-renders (React.memo if needed)
- [ ] useCallback used for expensive functions
- [ ] useMemo used for complex selectors
- [ ] No memory leaks (cleanup in useEffect)
- [ ] Large lists use virtualization if needed
- [ ] Images optimized (not oversized)

### Testing
- [ ] Component has unit tests (*.test.tsx)
- [ ] Tests cover happy path
- [ ] Tests cover error scenarios
- [ ] Tests check loading states
- [ ] 80%+ test coverage

### Build & Compilation
- [ ] `npm run build` succeeds with 0 errors
- [ ] No TypeScript errors
- [ ] No console warnings
- [ ] No unused imports
- [ ] No unused variables
- [ ] ESLint passes: `npm run lint`

### Code Quality
- [ ] Component length reasonable (not 500+ lines)
- [ ] Complex logic extracted to custom hooks
- [ ] No commented-out code
- [ ] Comments explain "why" not "what"
- [ ] Consistent naming conventions
- [ ] No magic numbers (use constants)

### Documentation
- [ ] Component has JSDoc with purpose/usage
- [ ] Complex props documented
- [ ] Usage examples in comments if complex
- [ ] README.md updated if new feature
- [ ] API integration documented

### Common Mistakes Prevention

#### ❌ DON'T
- ❌ Create custom CSS modules for Blueprint components
- ❌ Use non-existent Blueprint components
- ❌ Wrap FormItem with children
- ❌ Use BrowserRouter (only MemoryRouter in MCA2)
- ❌ Initialize API in App.tsx (do it in Entry.tsx)
- ❌ Assume API response structure
- ❌ Call .map() without Array.isArray() check
- ❌ Use div for layout (use Blueprint layout components)
- ❌ Mix button sizes (size="sm" with defaults)
- ❌ Leave size prop off Icon components

#### ✅ DO
- ✅ Use Blueprint components with their native props
- ✅ Validate all data before using array methods
- ✅ Use render function pattern for FormItem
- ✅ Initialize API services in Entry.tsx
- ✅ Use defensive programming for API responses
- ✅ Follow Blueprint design patterns exactly
- ✅ Test error scenarios, not just happy paths
- ✅ Check storybook for component APIs
- ✅ Document complex logic

---

## Review Workflow

### Component Author
1. Go through checklist above
2. Fix any items marked ❌
3. Run `npm run build` - should show 0 errors
4. Create pull request with checklist completed

### Code Reviewer
1. Use this checklist to verify component
2. Check architecture patterns match SKILL.md Mistake 1-23
3. Verify test coverage > 80%
4. Approve or request changes

### Failed Checklist Items
If any items fail:
- **Red Flag (Block PR)**: Build errors, TypeScript errors, Array without .isArray() check
- **Yellow Flag (Fix before merge)**: Missing tests, missing validation, layout issues
- **Green Flag (Nice to have)**: Performance optimizations, accessibility enhancements

---

## Quick Validation Commands

```bash
# Build check
npm run build

# Lint check
npm run lint

# Type check
npx tsc --noEmit

# Test coverage
npm run test -- --coverage

# Component import validation
grep -r "import.*from.*@barclays/blueprint-react" src/ | head -20
```

---

## References
- SKILL.md Mistakes 1-23 (critical patterns)
- BLUEPRINT_REACT_REFERENCE.md (valid components)
- BDL_TO_BLUEPRINT_REACT.md (component mapping, icon reference in Section 8)
- REDUX_PATTERNS.md (state management)
- FORM_VALIDATION_PATTERNS.md (forms)
