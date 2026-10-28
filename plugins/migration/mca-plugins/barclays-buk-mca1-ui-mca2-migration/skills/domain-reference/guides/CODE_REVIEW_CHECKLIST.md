# Code Review Checklist for MCA2 Components

Use this checklist when reviewing MCA2 component pull requests.

Last Updated: March 25, 2026

---

## Architecture & Structure

### Component Design
- [ ] Component has clear, single responsibility
- [ ] Component not longer than 500 lines (complexity indicators)
- [ ] Complex logic extracted to custom hooks
- [ ] Component properly named (PascalCase, descriptive)
- [ ] JSDoc comment explains purpose/usage
- [ ] Props interface documented

### Project Structure
- [ ] Component in correct folder hierarchy
- [ ] File naming follows conventions
- [ ] Tests colocated with component
- [ ] No circular imports
- [ ] Imports organized logically

---

## Blueprint-React Component Usage

### Component Patterns
- [ ] Uses only existing Blueprint-React components
- [ ] FormItem uses render function (not children wrapping)
- [ ] Dialog uses slot properties (head/foot/children)
- [ ] Table uses standard HTML elements (thead/tbody/tr/td)
- [ ] Button variants valid (primary/secondary/subtle, not ghost/danger)
- [ ] Type component used for all text (not divs)
- [ ] Icon components have size prop (sm/md/lg)

### CSS & Styling
- [ ] No .module.css files for Blueprint components
- [ ] No custom CSS for layout (uses Grid/Arrange/Section)
- [ ] Layout nesting minimal (2-3 SectionItems per Section)
- [ ] No inline styles for layout
- [ ] Responsive design considered (use sizeXs props)
- [ ] Spacing uses Blueprint system (spacing="md")

### Component Checklist
```
FormItem Pattern:
- [ ] label prop present
- [ ] render function prop used (not children)
- [ ] error prop conditionally set
- [ ] required indicator shown if needed

Dialog Pattern:
- [ ] isOpen prop controls visibility
- [ ] head/foot/children slots used
- [ ] onClickDismiss handler present
- [ ] onClickOverlay handler present
- [ ] onKeydownEscape handler present

Button Pattern:
- [ ] variant valid (primary/secondary/subtle)
- [ ] status used for danger state (not variant="danger")
- [ ] size prop only if intentional (not default size="sm")
- [ ] disabled state managed properly

Icon Pattern:
- [ ] icon name exists (check BDL_TO_BLUEPRINT_REACT.md Section 8)
- [ ] size prop always present (xs/sm/md/lg/xl/2xl)
- [ ] No -circle suffix icon names
- [ ] Icons match context (checkmark=success, X=error)

Type Component:
- [ ] element valid (h1-h6, p, span, em, strong, etc.)
- [ ] marginBottom used for spacing (not marginTop)
- [ ] weight prop for bold text (not inline style)
```

---

## Data Handling & Validation

### Array/Data Safety
- [ ] Array.isArray() check before calling .map()
- [ ] Null/undefined checks for optional data
- [ ] No assumptions about data structure
- [ ] Empty array fallback for missing data
- [ ] Defensive programming throughout

### Redux Integration
- [ ] Redux hooks properly typed (useAppDispatch, useAppSelector)
- [ ] Selectors properly typed
- [ ] Loading/error states handled
- [ ] No Redux state duplication
- [ ] No duplicate data in multiple slices

### API Integration
- [ ] API responses validated at service layer
- [ ] Error responses handled appropriately
- [ ] Loading states managed
- [ ] Timeout handling present
- [ ] Retry logic if applicable

---

## Form Handling

### Form Structure
- [ ] FormItem + FormSelect/FormInput pattern used
- [ ] Yup schema defined for validation
- [ ] Validation errors shown to user
- [ ] Form submission has loading state
- [ ] Success/error messages displayed

### Validation
- [ ] Required fields marked clearly
- [ ] Error messages user-friendly
- [ ] Async validation includes timeout
- [ ] Validation tested with edge cases
- [ ] Special characters handled correctly

### User Experience
- [ ] Submit button disabled while submitting
- [ ] Loading indicator shown during submission
- [ ] Success message shown on success
- [ ] Error message shown on failure
- [ ] Form state preserved on errors (except sensitive fields)

---

## TypeScript Compliance

### Type Safety
- [ ] No `any` types (use proper types from src/types/)
- [ ] All function parameters typed
- [ ] All return types specified
- [ ] Type errors resolved (build succeeds)
- [ ] No TypeScript warnings in output
- [ ] Interfaces/types exported for reuse

### Props & State
- [ ] Props interface properly defined
- [ ] Props documented (optional with JSDoc)
- [ ] State types properly inferred
- [ ] Conditional types used when appropriate
- [ ] Generic types used where needed

---

## Error Handling

### Error Prevention
- [ ] Try-catch blocks in async functions
- [ ] Error boundaries considered
- [ ] Null coalescing (??) used appropriately
- [ ] Type guards implemented for unions
- [ ] No silent failures (errors logged or handled)

### Error Display
- [ ] API errors displayed to user
- [ ] Error messages are user-friendly
- [ ] Technical errors logged to console
- [ ] No error console.logs in production code
- [ ] Stack traces not exposed to users

---

## Testing

### Test Coverage
- [ ] Component has unit tests (*.test.tsx)
- [ ] Tests cover happy path
- [ ] Tests cover error scenarios
- [ ] Tests check loading states
- [ ] Tests check empty states
- [ ] 80%+ coverage for component

### Test Quality
- [ ] Tests are readable and maintainable
- [ ] Mock data reflects reality
- [ ] No hardcoded test IDs (use accessible queries)
- [ ] Tests are isolated (no cross-test dependencies)
- [ ] Tests pass consistently

---

## Performance

### Rendering Optimization
- [ ] React.memo used for expensive components
- [ ] useCallback used for event handlers passed as props
- [ ] useMemo used for complex selectors/computations
- [ ] No unnecessary re-renders
- [ ] Lists use key prop correctly

### Bundle Size
- [ ] No unused imports
- [ ] No unnecessary dependencies
- [ ] Code splitting considered for large features
- [ ] Images optimized

---

## Build & Compilation

### Build Status
- [ ] `npm run build` succeeds with 0 errors
- [ ] No TypeScript errors
- [ ] No console warnings
- [ ] No unused imports
- [ ] No unused variables
- [ ] ESLint passes: `npm run lint`

### Code Quality
- [ ] No commented-out code
- [ ] Comments explain "why" not "what"
- [ ] Consistent naming conventions
- [ ] No magic numbers (use constants)
- [ ] Consistent code style

---

## Common Mistakes Prevention

### Critical Mistakes (Auto-Reject)
- ❌ Build fails with errors
- ❌ TypeScript errors present
- ❌ No Array.isArray() before .map()
- ❌ FormItem using children instead of render
- ❌ Custom CSS modules for Blueprint components
- ❌ API not validated at service layer

### Major Mistakes (Request Changes)
- ❌ Missing error handling
- ❌ No validation on form inputs
- ❌ Missing tests
- ❌ Redux state duplication
- ❌ Memory leaks (no cleanup in useEffect)
- ❌ Props not typed

### Minor Mistakes (Suggest)
- ⚠️ No JSDoc comment
- ⚠️ Unused variables
- ⚠️ Magic numbers (use constants)
- ⚠️ Commented code left behind
- ⚠️ Inconsistent spacing

---

## Specific Component Types

### Page Components
- [ ] Dispatches Redux thunks on mount
- [ ] Handles loading/error states
- [ ] Shows appropriate UI for all states
- [ ] Responsive layout
- [ ] Navigation working correctly

### Dialog Components
- [ ] All close handlers implemented
- [ ] Form validation working
- [ ] Submit button handling loading state
- [ ] Error messages displayed
- [ ] Success callback triggered

### Form Components
- [ ] All fields have validation
- [ ] Error messages shown on validation failure
- [ ] Submit button disabled until valid
- [ ] Loading state shown during submission
- [ ] Success/error messages displayed

### Redux Slice Components
- [ ] Reducers handle all state changes
- [ ] Async thunks have proper error handling
- [ ] Loading/error/success states managed
- [ ] No mutations outside Immer
- [ ] Initial state correct

---

## Accessibility

### Keyboard Navigation
- [ ] All interactive elements keyboard accessible
- [ ] Tab order logical
- [ ] Focus visible on all inputs
- [ ] Escape key closes modals

### Screen Readers
- [ ] ARIA labels for complex components
- [ ] Form labels associated with inputs
- [ ] Button text descriptive
- [ ] Images have alt text (if any)

---

## Documentation

### Code Documentation
- [ ] JSDoc comments on components
- [ ] Complex logic explained
- [ ] Props documented if non-obvious
- [ ] Usage examples if complex

### Commit Messages
- [ ] Commit message clear and descriptive
- [ ] References issue/ticket if applicable
- [ ] Follows conventional commit format

---

## Final Checklist

### Before Approving
- [ ] All checks above passed
- [ ] Build succeeds with 0 errors
- [ ] Tests passing
- [ ] No blocking issues
- [ ] Code follows patterns in SKILL.md

### Approval Comment Template
```markdown
## Review Summary

✅ **Approved** - [brief summary of what was reviewed]

### Strengths
- [positive observation]
- [positive observation]

### Suggestions (optional)
- [suggestion for improvement]

### Before Merging
- [ ] Ensure tests pass locally
- [ ] Run `npm run build` one more time
```

### Request Changes Template
```markdown
## Review Summary

🔄 **Changes Requested** - [brief summary]

### Issues Found
1. [Issue description with reference to line/file]
2. [Issue description with reference to line/file]

### Suggestions
- [Suggestion for improvement]

### Reference
- See SKILL.md Mistake #[X]
- See [GUIDE_NAME].md section
```

---

## Quick Links

- **Component Patterns**: BLUEPRINT_REACT_CORRECT_PATTERNS.md
- **Redux Patterns**: REDUX_PATTERNS.md
- **Form Validation**: FORM_VALIDATION_PATTERNS.md
- **API Response Handling**: API_RESPONSE_PATTERNS.md
- **Testing Patterns**: TESTING_PATTERNS.md
- **Common Mistakes**: SKILL.md Mistakes 1-23
- **Error Scenarios**: ERROR_SCENARIOS.md
- **Debugging**: DEBUGGING_GUIDE.md

---

## References
- COMPONENT_AUDIT_CHECKLIST.md (Author checklist)
- SKILL.md Mistakes 1-23
- BLUEPRINT_REACT_CORRECT_PATTERNS.md
