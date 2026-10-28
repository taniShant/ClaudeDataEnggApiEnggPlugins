---
name: domain-reference
description: "mca1-ui-mca2-migration domain reference — autonomous MCA1 JMVC/BDL to MCA2 React/Blueprint-React migration. Migrates: MCA1 JMVC+BDL → MCA2 React+TypeScript. Loaded by orchestrator and workers at phase gates."
---

# Domain Reference — MCA1→MCA2 UI Migration

**Source Technology:** MCA1 JMVC + BDL (`<mca-*>` web components)
**Target Technology:** MCA2 React + TypeScript + Blueprint-React v1.3.0 (`@barclays/blueprint-react`)
**Plugin Version:** 2.0.0

---

## Section 1: Overview and Scope

This plugin autonomously migrates MCA1 JMVC applications using BDL web components to MCA2 React applications using Blueprint-React components. All file transformations are done in-place. Git workflow (branch creation, staging, commits) is handled by the user.

**Migrates:** MCA1 JMVC + BDL → MCA2 React + TypeScript + Blueprint-React v1.3.0

**User Responsibilities:** After migration completes, user must:
1. Create a feature branch: `git checkout -b feature/mca2-migration{-JIRA_ID if provided}`
2. Stage changes: `git add .`
3. Create commits with appropriate messages

**Scope:** UI pattern transformations ONLY:
- BDL `<mca-*>` web component tags → Blueprint-React JSX components
- BDL import statements → `@barclays/blueprint-react` imports
- JMVC `$scope` bindings → React `useState`/Redux state
- `BaseController` class components → functional React components
- Non-existent Blueprint sub-components → correct Blueprint patterns
- JMVC EJS templates → React JSX components
- React Router setup with `MemoryRouter` from `react-router`
- Redux Toolkit setup for global state management
- Yup for form validation

**Template Repository Support (Optional):**

When `--template-repo` is provided, the plugin clones the specified template repository during Phase 0, analyzes it to detect state management library, routing patterns, folder structure, naming conventions, component patterns, and import patterns. The analysis produces `{PROJECT_PATH}/.claude/template-analysis.json`. Transform agents then use this analysis to override default patterns (Redux Toolkit, canonical folder structure) with the template's conventions. MCA2 constraints (MemoryRouter, Blueprint-React component correctness, FormItem render prop) always override template conventions.

**Out of Scope (DO NOT TOUCH):**
- Redux reducers, thunks, selectors (or equivalent state store files if template uses a different library)
- API service files and endpoint configurations
- `process.json` endpoint definitions
- Business logic and domain calculations
- Test files (`.test.tsx`, `.spec.tsx`)

**Success Criteria:**
- Zero BDL imports remaining in source files
- Zero `$scope` bindings in TypeScript source
- Zero `BaseController` references
- Zero non-existent Blueprint component imports
- `npm run lint` exits 0
- `npx tsc --noEmit` exits 0
- `npm run build` exits 0

---

## Section 2: Phase Reference

| Phase | Name | Description | Hard Gate |
|-------|------|-------------|-----------|
| 0 | Project Setup & MCA1 Validation | Confirm MCA1 project structure, check npm, record metadata | npm --version exits 0 |
| 0.5 | Template Analysis (Conditional) | Clone template repo, detect state management/routing/folder structure/naming conventions, write template-analysis.json | Best-effort (non-blocking) |
| 1 | Codebase Analysis | Scan for BDL/JMVC patterns, classify files, produce analysis.json with batch plan | analysis.json written |
| 1.5 | API Contract Verification | Clone EPS backend repo, extract endpoint definitions, write API_CONTRACTS.md, cross-check process.json | Best-effort (non-blocking) |
| 2 | BDL→Blueprint-React Transformation | Apply transformations in parallel file batches (3–6 files/worker). Files modified in place. | npm run lint; npx tsc --noEmit; npm run build |
| 3 | Validation | Read-only gatekeeper checks 10 blocking + 1 advisory red flags | APPROVED verdict required |
| 4 | Regression Test Conversion (Conditional) | Clone external regression repo, analyze scripts, generate Cypress or Playwright E2E tests (auto-detected) with isolated MSW mocks | Test files exist; tsc passes; lint passes |
| Complete | Ready for Commit | All migrations done. User handles: `git checkout -b`, `git add`, `git commit` | User handles git workflow |

---

## Section 3: BDL Component Mapping Table

All 41 MCA1 BDL `<mca-*>` components and their Blueprint-React equivalents.

### Form Controls

| MCA1 BDL Component | Blueprint-React Equivalent | Pattern | Critical Notes |
|---|---|---|---|
| `<mca-input>` | `<FormItem>` + `<FormInput>` | Render function | Must use render prop, NOT children. If MCA1 has `symbol` attr (e.g. `£`), use `affix` and `affixPosition` props on FormInput to preserve it |
| `<mca-textarea>` | `<FormItem>` + `<FormTextarea>` | Render function | Spread `{...props}` on FormTextarea |
| `<mca-combobox template="dropdown">` | `<FormItem>` + `<FormSelect>` | Render function | Use standard `<option>` tags |
| `<mca-combobox template="autocomplete">` | `<FormItem>` + `<AutoComplete>` | Render function | AutoComplete exists in v1.3.0 |
| `<mca-radios>` + `<mca-radio>` | `<FormMultiItem>` + `<FormRadio>` | Render function | Use FormMultiItem NOT FormItem; spread `{...renderProps}` on each FormRadio |
| `<mca-checkboxes>` + `<mca-checkbox>` | `<FormMultiItem>` + `<FormCheckbox>` | Render function | Use FormMultiItem; spread `{...renderProps}` |
| `<mca-sortaccount>` | `<FormMultiItem>` + `<FormItem hiddenLabel>` + `<FormInput>` | Nested render | See BDL_SORTACCOUNT_MAPPING.md |
| `<mca-date>` | `<FormItem>` + `<FormInput type="date" media={<Icon icon="calendar" size="sm" />}>` | Render function | Add date validation via Yup |
| `<mca-cardnumber>` | `<FormItem>` + `<FormInput>` | Render function | Add masking logic separately |
| `<mca-form>` | `<Form>` | Direct | Standard Blueprint form wrapper |
| `<mca-formview>` | `<Form>` or container div | Direct | |
| `<mca-selection>` | `<FormItem>` + `<FormSelect>` | Render function | |
| `<mca-dropdown-account>` | `<FormItem>` + `<FormSelect>` | Render function | |

### UI Components

| MCA1 BDL Component | Blueprint-React Equivalent | Pattern | Critical Notes |
|---|---|---|---|
| `<mca-button>` | `<Button>` | Attribute remapping | See button variant table below |
| `<mca-button-groups>` | `<FormMultiItem>` + `<FormRadio>` or `<Arrange>` + `<Button>` | Data-driven | Depends on toggle vs action |
| `<mca-link>` | `<Link>` | Attribute remapping | |
| `<mca-modal>` | `<Dialog>` or `<Modal>` | Slot properties / Ref-based | head/foot/children — NOT DialogHeader/Footer. Use `<Modal>` with ref for complex modals |
| `<mca-modal-body>` | children of `<Dialog>` | Absorbed | No separate component |
| `<mca-modal-footer>` | `foot` prop of `<Dialog>` | Absorbed | No separate component |
| `<mca-notify>` | `<Alert>` | Attribute remapping | Use `media` not `icon`; `onDismiss` not `onClose` |
| `<mca-table>` | `<Table>` + `<thead>/<tbody>/<tr>/<td>` | Standard HTML | TableHead/TableRow/TableCell do NOT exist |
| `<mca-table-row>` | `<tr>` | Standard HTML | |
| `<mca-table-cell>` | `<td>` or `<th>` | Standard HTML | |
| `<mca-account-table>` | `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table` | Package import | Paginated account list — see BDL_TABLE_MAPPING.md |
| `<mca-heading>` | `<Type element="hN" size="...">` | Attribute remapping | ALWAYS add both `element` AND `size` prop (h1→3xl, h2→2xl, h3→xl, h4→lg, h5→md, h6→sm). Add `marginBottom`. |
| `<mca-text>` | `<Type>` | Attribute remapping | |
| `<mca-icon>` | `<Icon>` | Attribute remapping | ALWAYS add `size` prop |
| `<mca-image>` | `<Multimedia>` | Attribute remapping | Use Blueprint `<Multimedia>` not plain `<img>` |
| `<mca-accordion>` | `<Accordion>` | Direct | |
| `<mca-accordionitem>` | Accordion children | Direct | |
| `<mca-separator>` | `<Separator>` | Direct | |
| `<mca-progressbar>` | `<Progress>` | Attribute remapping | |
| `<mca-infopair>` | `<DescriptionList>` dt/dd or `<Type>` pairs | Layout restructure | |
| `<mca-list>` | `<List>` or `<ul>`/`<ol>` | Direct | |
| `<mca-list-item>` | `<li>` | Direct | |
| `<mca-tabs>` | `<Tabs>` | Direct | See BDL_TABS_MAPPING.md |
| `<mca-tab>` | `<Tab>` | Direct | `name` → `label`; `state="selected"` → `initialTabIndex` |
| `<mca-statusbar>` | `<SlimBanner>` + MicroTheme | Attribute remapping | Wrap in `BarclaysMicroTheme*` variant |
| `<mca-spinner>` | `<Loading>` | Attribute remapping | Do NOT use `<Icon icon="spinner">` — use `<Loading>` |
| `<mca-popover>` | `<PopupNav>` | Hook-based | Requires `useToggle` + `useRef` + conditional rendering |
| `<mca-stepper>` | `<NumberStepper>` | Attribute remapping | `datatype="time"` needs custom `formatter` |

### Layout Components

| MCA1 BDL Component | Blueprint-React Equivalent | Pattern | Critical Notes |
|---|---|---|---|
| `<mca-fluidview>` | `<Grid>` | Direct | |
| `<mca-cell>` | `<Grid.Col>` | Size mapping | Valid sizes: 1of12–12of12, 1of2, 1of3, 1of4, 1of6 |
| `<mca-header>` | `<Page head={<Navbar>}>` | Layout restructure | |
| `<mca-footer>` | `<Page>` footer slot | Layout restructure | |
| `<mca-info-container>` | `<Section>` or `<DescriptionList>` | Layout restructure | |

---

## Section 3a: Button Variant Mapping Table

| MCA1 / Old Variant | Blueprint-React Correct Usage | Notes |
|---|---|---|
| `variant="ghost"` | `variant="subtle"` | Ghost style maps to subtle |
| `variant="danger"` | `status="danger"` | Danger is a status, not a variant |
| `variant="tertiary"` | `variant="secondary"` | Tertiary does not exist |
| `variant="primary"` | `variant="primary"` | Unchanged |
| `variant="secondary"` | `variant="secondary"` | Unchanged |

Valid Button variants in v1.3.0: `"primary"` | `"secondary"` | `"subtle"`
Valid Button status values: `"default"` | `"danger"`

---

## Section 3b: Icon Mapping Table

**Valid Blueprint icon names** (exhaustive list): `back`, `bell`, `bin`, `calendar`, `card`, `chat`, `chevron-down`, `chevron-left`, `chevron-left-double`, `chevron-right`, `chevron-right-double`, `chevron-up`, `clock`, `cloud-upload`, `cog`, `compass`, `diamond`, `dismiss`, `download`, `edit`, `error`, `error-fill`, `home`, `info`, `info-fill`, `international`, `leaf`, `log-out`, `mail`, `manage-payments`, `minus`, `more`, `more-vertical`, `new`, `padlock`, `payments`, `plane`, `plus`, `profile`, `refresh`, `search`, `settings`, `show`, `success`, `success-fill`, `tick`, `transfer`, `tree`, `warning`, `warning-fill`.

| BDL Icon Name | Blueprint-React Equivalent | Notes |
|---|---|---|
| `tick-circle` | `tick` | "-circle" suffix does not exist |
| `cross-circle` | `dismiss` | Blueprint uses `dismiss` for X/close icon |
| `cross` | `dismiss` | `cross` does NOT exist; use `dismiss` |
| `close` | `dismiss` | `close` does NOT exist; use `dismiss` |
| `info-circle` | `info` | "-circle" suffix does not exist |
| `times-circle` | `dismiss` | Maps to `dismiss` |
| `check-circle` | `tick` | "-circle" suffix does not exist |
| `error-circle` | `error` | "-circle" suffix does not exist |
| `spinner` | Use `<Loading size="lg" shape="circle" ariaLabel="Loading" />` | Loading component, not an Icon |
| `inbox` | `mail` | `inbox` and `document` do NOT exist; use `mail` |
| `inbox-full` | `mail` | Use `mail` as closest alternative |
| `print` | `download` | `print` does NOT exist in Blueprint |
| `camera` | N/A | Does not exist; omit or use custom SVG |
| `external` | `chevron-right` | `external` does not exist |

Always add `size` prop: `size="sm"` in buttons, `size="md"` in alerts/standalone, `size="lg"` for important indicators.

---

## Section 3c: npm Commands Reference

| Purpose | Command | Gate |
|---|---|---|
| Install dependencies | `npm install` | Phase 0 |
| Lint | `npm run lint` | Phase 3 quality gate |
| TypeScript type-check | `npx tsc --noEmit` | Phase 3 quality gate |
| Build | `npm run build` | Phase 3 quality gate |
| Development server | `npm start` | Manual — post migration |
| Install Cypress | `npm install --save-dev cypress` | Phase 4 — Cypress (if missing) |
| Install Playwright | `npm install --save-dev @playwright/test` | Phase 4 — Playwright (if missing) |
| Install Playwright browsers | `npx playwright install --with-deps chromium` | Phase 4 — Playwright (if missing) |
| Install MSW | `npm install --save-dev msw` | Phase 4 (if missing, both frameworks) |
| Cypress TypeScript check | `npx tsc --noEmit --project cypress/tsconfig.json` | Phase 4 quality gate (Cypress) |
| Cypress lint | `npx eslint cypress/ --ext .ts,.tsx` | Phase 4 quality gate (Cypress) |
| Playwright TypeScript check | `npx tsc --noEmit --project tsconfig.json` | Phase 4 quality gate (Playwright) |
| Playwright lint | `npx eslint e2e/ --ext .ts,.tsx` | Phase 4 quality gate (Playwright) |

---

## Section 4: Transformation Examples

### Example 4.1: FormItem Render Function (GOOD)

BEFORE (MCA1 BDL EJS template):
```html
<mca-input id="roleName" label="Role Name" value="<%=vm.roleName%>" />
```

AFTER (MCA2 Blueprint-React):
```typescript
<FormItem
  label={<Type>Role Name</Type>}
  error={errors.roleName && <Type color="error">{errors.roleName}</Type>}
  render={(props) => (
    <FormInput
      {...props}
      id="roleName"
      value={roleName}
      onChange={(e) => setRoleName(e.target.value)}
    />
  )}
/>
```

Why this is correct: `FormItem` requires a `render` function; `label` and `error` must be ReactNode wrapped in `<Type>` for Blueprint styling.

### Example 4.2: FormItem Children Anti-Pattern (BAD)

BEFORE:
```typescript
<mca-input id="roleName" label="Role Name" />
```

WRONG (do NOT produce this):
```typescript
<FormItem label="Role Name">
  <FormInput id="roleName" value={roleName} />
</FormItem>
```

Why this is wrong: `FormItem` does NOT accept children — it requires a `render` function. Children wrapping silently produces no output.

Fix: Always use `render={(props) => <FormInput {...props} ... />}`.

### Example 4.3: Dialog Slot Pattern (GOOD)

BEFORE (MCA1 BDL EJS template):
```html
<mca-modal id="confirmDialog" heading="Confirm Action">
  <p>Are you sure?</p>
  <mca-button label="Confirm" data-action="confirm" />
  <mca-button label="Cancel" data-action="cancel" />
</mca-modal>
```

AFTER (MCA2 Blueprint-React):
```typescript
<Dialog
  isOpen={isDialogOpen}
  head={<h2>Confirm Action</h2>}
  foot={
    <Arrange gap="fixed">
      <ArrangeItem size="fit">
        <Button variant="primary" onClick={handleConfirm}>Confirm</Button>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button variant="secondary" onClick={handleCancel}>Cancel</Button>
      </ArrangeItem>
    </Arrange>
  }
  onClickDismiss={handleCancel}
  onClickOverlay={handleCancel}
  onKeydownEscape={handleCancel}
>
  <Type element="p">Are you sure?</Type>
</Dialog>
```

Why this is correct: `Dialog` uses slot properties `head`, `foot`, and `children`. `DialogHeader`/`DialogContent`/`DialogFooter` do not exist in Blueprint-React v1.3.0.

### Example 4.4: JMVC $scope to React Functional Component (GOOD)

BEFORE (MCA1 JMVC):
```typescript
export class RolesController extends BaseController {
  static $inject = ['$scope', 'RolesService'];
  constructor(private $scope: any, private rolesService: RolesService) {
    super();
    $scope.roles = [];
    $scope.selectedRole = null;
    $scope.loadRoles = () => {
      rolesService.getAll().then(roles => { $scope.roles = roles; });
    };
    $scope.loadRoles();
  }
}
```

AFTER (MCA2 React):
```typescript
import React, { useEffect } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { fetchRoles } from '../store/rolesSlice';

export const RolesPage: React.FC = () => {
  const dispatch = useAppDispatch();
  const rolesData = useAppSelector(state => state.roles.items);
  const roles = Array.isArray(rolesData) ? rolesData : [];

  useEffect(() => {
    dispatch(fetchRoles());
  }, [dispatch]);

  return (
    <Section>
      <SectionItem>
        {/* roles UI here */}
      </SectionItem>
    </Section>
  );
};
```

Why this is correct: Redux thunks and reducers are untouched; only the controller shell is converted to a functional component that dispatches to existing Redux logic.

---

## Section 5: Quality Gate Checks

| Phase | Gate Command | Pass Condition | Fail Action |
|-------|-------------|----------------|-------------|
| 0 | `npm --version` | exits 0 | STOP — install Node.js |
| 3 | `npm run lint` | exits 0 | STOP — fix lint errors before push |
| 3 | `npx tsc --noEmit` | exits 0 | STOP — fix TypeScript errors before push |
| 3 | `npm run build` | exits 0 | STOP — fix build errors before push |
| 4 (Cypress) | `find cypress/e2e/regression -name "*.cy.ts"` | at least 1 file | STOP — no Cypress tests generated |
| 4 (Cypress) | `test -f cypress/mocks/handlers.ts` | file exists | STOP — MSW handlers not created |
| 4 (Cypress) | `npx tsc --noEmit --project cypress/tsconfig.json` | exits 0 | STOP — fix Cypress TypeScript errors |
| 4 (Cypress) | `npx eslint cypress/ --ext .ts,.tsx` | exits 0 | STOP — fix Cypress lint errors |
| 4 (Playwright) | `find e2e/regression -name "*.spec.ts"` | at least 1 file | STOP — no Playwright tests generated |
| 4 (Playwright) | `test -f e2e/mocks/handlers.ts` | file exists | STOP — MSW handlers not created |
| 4 (Playwright) | `npx tsc --noEmit --project tsconfig.json` | exits 0 | STOP — fix Playwright TypeScript errors |
| 4 (Playwright) | `npx eslint e2e/ --ext .ts,.tsx` | exits 0 | STOP — fix Playwright lint errors |

Forbidden pattern checks (grep count must be 0):

| Forbidden Pattern | Check | Scope |
|---|---|---|
| BDL imports | `grep -r "from 'bdl'\|from \"bdl\"" src/ \| wc -l` | `src/` |
| $scope bindings | `grep -r "\$scope\." src/ \| wc -l` | `src/` |
| BaseController | `grep -r "BaseController" src/ \| wc -l` | `src/` |
| Non-existent Blueprint | `grep -r "DialogHeader\|TableHead\|FormGroup\|Tooltip\|Popover\|Spinner" src/ \| wc -l` | `src/` |
| JMVC EJS templates | `grep -r "<%=\|<%if\|<%for" src/ \| wc -l` | `src/` |
| BrowserRouter | `grep -r "BrowserRouter" src/ \| wc -l` | `src/` |

---

## Section 6: Iron Rules and Laws

## IRON RULES — NON-NEGOTIABLE LAWS

These rules MUST NEVER be violated. Any agent encountering a situation
that would require violating an iron rule MUST STOP and invoke auto-decision-agent.

### Rule 1: FormItem Always Uses Render Function

LAW: NEVER use FormItem with children wrapping. ALWAYS use the render function pattern.

VIOLATION EXAMPLE:
```typescript
<FormItem label="Name">
  <FormInput value={val} />   // WRONG - children not supported
</FormItem>
```

CORRECT APPROACH:
```typescript
<FormItem
  label={<Type>Name</Type>}
  render={(props) => <FormInput {...props} value={val} onChange={handler} />}
/>
```

ENFORCEMENT: Validation agent Red Flag #4 checks for `FormGroup|FormFieldWrapper` patterns.

### Rule 2: Never Import Non-Existent Blueprint Components

LAW: NEVER import `DialogHeader`, `DialogContent`, `DialogFooter`, `TableHead`, `TableBody`, `TableRow`, `TableCell`, `FormGroup`, `FormFieldWrapper`, `TextInput`, `TextArea`, `Select`, `Tooltip`, `Popover`, `Spinner` from `@barclays/blueprint-react`. These components do NOT exist in v1.3.0.

Use instead:
- `Tooltip` → `<PopupNav>` with click trigger, or native `title` attribute for simple hover text
- `Popover` → `<PopupNav>` (hook-based: useRef + useState + conditional render)
- `Spinner` → `<Loading>` (with `ariaLabel` prop)

VIOLATION EXAMPLE:
```typescript
import { DialogHeader, TableCell, FormGroup, Tooltip, Spinner } from '@barclays/blueprint-react';
// BUILD FAILURE — none of these exist
```

CORRECT APPROACH:
```typescript
import { Dialog, Table, FormItem } from '@barclays/blueprint-react';
// Dialog uses head/foot slots; Table uses standard HTML; FormItem uses render
```

ENFORCEMENT: Validation agent Red Flag #4 checks for non-existent component names.

### Rule 3: Never Touch Business Logic

LAW: NEVER modify Redux reducers, async thunks, API service files, `process.json`, selectors, or domain calculation functions. UI migration scope is strictly UI patterns only.

VIOLATION EXAMPLE:
```typescript
// In mca1-transform-agent: modifying rolesSlice.ts
export const rolesSlice = createSlice({
  // WRONG — transform agent must not touch this file
```

CORRECT APPROACH:
Only modify files that contain BDL `<mca-*>` components, BDL imports, `$scope` bindings, or `BaseController` class shells. Leave Redux logic intact.

ENFORCEMENT: Worker agent SCOPE BOUNDARY section forbids touching API/Redux files.

### Rule 4: Always Use MemoryRouter in MCA2

LAW: NEVER use `BrowserRouter` in MCA2 applications. ALWAYS use `MemoryRouter`. MCA2 modules do not control browser URLs.

VIOLATION EXAMPLE:
```typescript
import { BrowserRouter } from 'react-router';
<BrowserRouter><App /></BrowserRouter>  // WRONG — URL-based routing
```

CORRECT APPROACH:
```typescript
import { MemoryRouter } from 'react-router';
<MemoryRouter><App /></MemoryRouter>  // CORRECT — in-memory routing
```

ENFORCEMENT: Validation agent Red Flag #6 checks for BrowserRouter usage.

### Rule 5: Always Wrap Label and Error in Type Component

LAW: NEVER pass plain strings to `label` or `error` props of `FormItem`/`FormMultiItem`. ALWAYS wrap in `<Type>` and `<Type color="error">` respectively.

VIOLATION EXAMPLE:
```typescript
<FormItem label="Account Number" error={errors.account} ... />
// WRONG — plain strings lose Blueprint typography
```

CORRECT APPROACH:
```typescript
<FormItem
  label={<Type>Account Number</Type>}
  error={errors.account && <Type color="error">{errors.account}</Type>}
  ...
/>
```

ENFORCEMENT: Workers check this pattern during every FormItem transformation.

### Rule 6: Table Cells Must Use Type Wrapper and Compact Buttons

LAW: NEVER render plain text in raw `<td>` or `<th>` tags — ALWAYS use `<Type element="td">` or `<Type element="th">`. NEVER use default-size `<Button>` inside table cells — ALWAYS add `size="sm"`.

VIOLATION EXAMPLE:
```typescript
<tbody>
  <tr>
    <td>{row.name}</td>                           // WRONG — bare text, no Type wrapper
    <td>
      <Button onClick={fn}>Edit</Button>          // WRONG — missing size="sm"
    </td>
  </tr>
</tbody>
```

CORRECT APPROACH:
```typescript
<tbody>
  <tr>
    <Type element="td">{row.name}</Type>
    <td>
      <Button size="sm" variant="secondary" onClick={fn}>Edit</Button>
    </td>
  </tr>
</tbody>
```

NOTE: The `size="sm"` requirement is a TABLE-SPECIFIC exception to the general "no mixed button sizes" guidance (Mistake 20). Page-level buttons still use default size.

ENFORCEMENT: Validation agent checks for bare `<td>`/`<th>` with text content and for `<Button` without `size="sm"` inside `<td>` elements.

---

## Section 7: Decision Rules

**Decision:** File contains both JMVC controller logic and BDL component markup.
**Rule:** Apply both transformations in the same pass — convert the `$scope` shell to a functional component and replace BDL tags with Blueprint-React. Do not split into separate passes.

**Decision:** Blueprint-React import is present but component is used with wrong pattern.
**Rule:** Fix the usage pattern — do not remove the import. The component exists; only the usage pattern is wrong.

**Decision:** Found a BDL component that has no direct Blueprint equivalent.
**Rule:** Check `${CLAUDE_PLUGIN_ROOT}/skills/domain-reference/guides/BDL_TO_BLUEPRINT_REACT.md` and the `${CLAUDE_PLUGIN_ROOT}/skills/domain-reference/mappings/` directory. If no mapping exists, use the closest semantic Blueprint component and log `[WARN] custom mapping applied`.

**Decision:** File uses both `$scope` local state AND dispatches Redux thunks.
**Rule:** Convert `$scope` local state to `useState`. Leave the Redux dispatch calls intact — they are business logic.

**Decision:** `mca-button-groups` — toggle buttons or action buttons?
**Rule:** If the BDL button group acts as a toggle/radio selector, use `FormMultiItem` + `FormRadio`. If it is a row of action buttons, use `Arrange` + `Button`.

---

## Section 8: Common Pitfalls

**Pitfall 1: FormItem children wrapping**
Problem: Developers instinctively wrap form controls as children of FormItem.
Root cause: React composition model suggests children should work.
Fix: FormItem is unusual — it requires `render` function. Children are silently ignored. Always use `render={(props) => ...}`.

**Pitfall 2: $scope conversion misses Redux connection**
Problem: Converting `$scope` to `useState` but forgetting the Redux dispatch for data loading.
Root cause: JMVC controllers mix local UI state and service calls in `$scope`.
Fix: Local UI state (`$scope.isLoading`, `$scope.selectedItem`) → `useState`. Service calls (`$scope.loadRoles = () => service.getAll()`) → `useEffect` + `dispatch(fetchRoles())`. Do not replicate the service call logic — it belongs in the existing Redux thunk.

**Pitfall 3: Assuming Blueprint icon names match BDL**
Problem: Using BDL icon names directly in Blueprint `<Icon icon="...">`.
Root cause: BDL had many icon variants (circle suffixes, etc.) that Blueprint does not have.
Fix: Always check Section 3b Icon Mapping Table before setting an icon name. For spinners, use `<Loading>` not `<Icon>`.

**Pitfall 4: Process.json endpoint URI prefix**
Problem: Including `/api/router` in `process.json` endpoint URIs causes doubled prefix.
Root cause: MCA2 framework automatically prepends `/api/router` at runtime.
Fix: Never include `/api/router` in `process.json` URIs. Mock server (`middleware.js`) still needs the full path.

**Pitfall 5: Excessive SectionItem nesting creates whitespace bloat**
Problem: Wrapping every element in its own `<SectionItem spacing="md">` creates large gaps.
Root cause: Each SectionItem adds its own margin — they stack cumulatively.
Fix: Group related content in a single SectionItem (title + form together; buttons in a separate SectionItem). Maximum 2–3 SectionItems per Section.

**Pitfall 6: Bare text in table cells and oversized table buttons**
Problem: Agent generates `<td>{row.name}</td>` or `<td><Button onClick={fn}>Edit</Button></td>` — missing Type wrapper and compact sizing.
Root cause: Agents treat table cells like generic containers. Text in `<td>` loses Blueprint typography tokens (font-size, line-height, color). Default-size buttons are too tall for table row density.
Fix: Text cells always use `<Type element="td">` / `<Type element="th">`. Buttons in tables always include `size="sm"`. Cells with only interactive components use raw `<td>` around the component. See BDL_TABLE_MAPPING.md "Iron Rules for Table Cells" section and IMPLEMENTATION_GUIDE Mistake 32.

---

## Section 9: Regression Test Conversion Reference (Cypress & Playwright)

### Framework Detection

The regression agent auto-detects which E2E framework to use based on the MCA2 project configuration:

| Signal | Framework |
|---|---|
| `playwright.config.ts` or `playwright.config.js` exists | Playwright |
| `@playwright/test` in package.json dependencies | Playwright |
| `cypress.config.ts` or `cypress.config.js` exists | Cypress |
| `cypress` in package.json devDependencies | Cypress |
| Neither detected | Cypress (default) |

Detection priority: Playwright signals checked first. If both are present, **Playwright wins** (newer project setup).

### MSW Mock Isolation Rule (NON-NEGOTIABLE)

MSW mocks for regression E2E tests MUST be isolated from `mockServer/middleware.js`:

| Concern | Location | Purpose |
|---|---|---|
| Dev server mocks | `mockServer/middleware.js` | Eagle framework dev-server mock layer. Changes during active local development. Express-style middleware. |
| E2E regression mocks (Cypress) | `cypress/mocks/handlers.ts` | Stable MSW handlers for Cypress tests. Isolated, self-contained, never changes with dev workflow. |
| E2E regression mocks (Playwright) | `e2e/mocks/handlers.ts` | Stable mock route definitions for Playwright tests. Isolated, self-contained, never changes with dev workflow. |

**NEVER** import from, modify, or reference `mockServer/middleware.js` in E2E tests or mock files. You MAY read it for response shape inference only.

---

### Cypress Directory Structure

```
cypress/
  e2e/
    regression/              # Converted regression test files (.cy.ts)
  mocks/
    handlers.ts              # MSW request handlers (http.get/post/put/delete)
    browser.ts               # MSW browser worker setup (setupWorker)
    index.ts                 # Barrel export
  support/
    msw.ts                   # MSW lifecycle hooks (before/afterEach/after)
    e2e.ts                   # Cypress support entry (imports msw.ts)
  tsconfig.json              # Cypress-specific TypeScript config
cypress.config.ts            # Project root — Cypress configuration
```

### Cypress MSW Handler Pattern (v2 API)

```typescript
import { http, HttpResponse } from 'msw';

export const handlers = [
  http.get('/api/router/endpoint', () => {
    return HttpResponse.json({ data: [...] });
  }),
  http.post('/api/router/endpoint', async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({ id: 'new-id', ...body });
  }),
];
```

### Cypress Per-Test Mock Override Pattern

Individual tests can override default handlers for specific scenarios:

```typescript
import { http, HttpResponse } from 'msw';
import { worker } from '../../mocks/browser';

it('should handle empty state', () => {
  worker.use(
    http.get('/api/router/items', () => {
      return HttpResponse.json({ items: [] });
    })
  );
  cy.visit('/items');
  cy.get('[data-testid="empty-state"]').should('be.visible');
});
```

---

### Playwright Directory Structure

```
e2e/
  regression/                # Converted regression test files (.spec.ts)
  mocks/
    handlers.ts              # MSW-style mock route definitions (MockRoute[])
    bridge.ts                # Utility to apply mocks via page.route()
    index.ts                 # Barrel export
  fixtures/
    msw.fixture.ts           # Custom Playwright fixture with pre-applied mocks
playwright.config.ts         # Project root — Playwright configuration
```

### Playwright Mock Handler Pattern

```typescript
export interface MockRoute {
  method: string;
  url: string;
  status?: number;
  body: unknown;
}

export const handlers: MockRoute[] = [
  { method: 'GET', url: '/api/router/endpoint', body: { data: [...] } },
  { method: 'POST', url: '/api/router/endpoint', status: 201, body: { id: 'new-id' } },
];
```

### Playwright Bridge Utility

Converts MSW-style handler definitions into Playwright `page.route()` interceptions:

```typescript
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

### Playwright Custom Fixture Pattern

```typescript
import { test as base } from '@playwright/test';
import { handlers } from '../mocks/handlers';
import { applyMocks } from '../mocks/bridge';

export const test = base.extend<{ mockPage: import('@playwright/test').Page }>({
  mockPage: async ({ page }, use) => {
    await applyMocks(page, handlers);
    await use(page);
  },
});

export { expect } from '@playwright/test';
```

### Playwright Test Pattern

```typescript
import { test, expect } from '../fixtures/msw.fixture';

test.describe('Feature Name — regression', () => {
  test.beforeEach(async ({ mockPage }) => {
    await mockPage.goto('/page-path');
  });

  test('should perform expected action', async ({ mockPage }) => {
    await expect(mockPage.locator('[data-testid="element"]')).toBeVisible();
    await mockPage.locator('[data-testid="input"]').fill('value');
    await mockPage.locator('[data-testid="submit"]').click();
    await expect(mockPage.locator('[data-testid="result"]')).toContainText('expected');
  });
});
```

### Playwright Per-Test Mock Override Pattern

Individual tests can override default mocks by using raw `page` and calling `page.route()` directly:

```typescript
test('should handle empty state', async ({ page }) => {
  await page.route('**/api/router/items', route =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ items: [] }),
    })
  );
  await page.goto('/items');
  await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
});
```

---

### Supported Regression Script Formats

| Format | Extension | Common Frameworks |
|---|---|---|
| Python | `.py` | Selenium, pytest, requests |
| JavaScript/TypeScript | `.js`, `.ts` | Puppeteer, Playwright, custom |
| Gherkin | `.feature` | Cucumber, BDD |
| Robot Framework | `.robot` | Robot Framework |
| Shell | `.sh` | curl-based API scripts |

### Selector Priority (Both Frameworks)

Use selectors in this priority order:
1. `[data-testid="..."]` — most stable
2. `[aria-label="..."]` — accessible and stable
3. `[role="..."]` with text — semantic
4. `.class-name` or `#id` — fallback (less stable)

---

## Section 9a: Supplementary Reference Documents

### Implementation Guide
- `IMPLEMENTATION_GUIDE.md` — Detailed implementation skill with 29 documented mistakes, per-component patterns, setup/migration phases. Transform agents should read this before processing files.

### Component Mapping Files (23 files)
Located in: `mappings/`
- See `guides/BDL_TO_BLUEPRINT_REACT.md` for the complete mapping index with links to all 23 per-component mapping files.

### Reference Guides (24 files)
Located in: `guides/`
- `MIGRATION_GUIDES_INDEX.md` — Master navigation index for all documentation
- `BLUEPRINT_REACT_CORRECT_PATTERNS.md` — Authoritative component pattern reference
- `BDL_TO_BLUEPRINT_REACT.md` — Component mapping index
- `FOLDER_STRUCTURE.md` — Canonical MCA2 app directory layout
- `TYPESCRIPT_PATTERNS.md` — Type architecture, prop interfaces, Redux types
- `NAVIGATION_PATTERNS.md` — MemoryRouter routing, guards, navigation state
- `CONDITIONAL_RENDERING_PATTERNS.md` — Show/hide, dynamic fields, EJS migration
- `STYLING_PATTERNS.md` — CSS, Grid layout, theming, responsive design
- And 16 additional reference and troubleshooting guides

---

## Section 10: Senior Frontend Developer Principles

These principles govern HOW code is written during migration — not just what gets transformed. Every agent producing code MUST apply these.

### 10.1 Architecture & Component Design

- **Single Responsibility**: Each component does one thing. If a migrated component handles form rendering AND data fetching AND validation, split it into a container (data) and presentational (UI) component.
- **Custom Hooks for Reusable Logic**: Extract shared stateful logic (form handling, API polling, debounced search) into custom hooks (`useRoles`, `useFormValidation`). Don't duplicate `useState` + `useEffect` patterns across components.
- **Prop Interfaces**: Every component gets an explicit TypeScript interface for its props. No `any` types on component boundaries. Use discriminated unions over optional booleans where props are mutually exclusive.
- **Flat Component Trees**: Avoid deep nesting (>3 levels of custom components). Flatten with composition — pass rendered content as props (slots) rather than wrapping in provider chains.
- **Co-locate Related Code**: Keep a component's hook, types, and constants in the same file unless shared. Only extract to a separate file when reused by 2+ components.

### 10.2 Maintainability & Readability

- **Descriptive Naming**: State variables describe their content (`roles`, `isSubmitting`, `selectedAccountId`) — not generic names (`data`, `flag`, `item`). Handlers describe the action (`handleRoleSelect`, `handleFormSubmit`) — not `onClick1`.
- **TypeScript Strictness**: Use `strict: true` patterns. No `any` except at system boundaries (external API responses get typed immediately after fetch). Prefer `unknown` over `any` when type is uncertain.
- **Derived State Over Redundant State**: If a value can be computed from existing state, compute it. Don't store `filteredRoles` in state when you can `useMemo(() => roles.filter(...), [roles, filter])`.
- **Avoid Premature Abstraction**: Three similar lines are better than a premature helper. Only extract a utility when the same pattern appears in 3+ places.
- **Explicit Over Implicit**: Destructure props at the top of the component. Make data flow visible. Avoid deeply nested ternaries — use early returns or guard clauses.

### 10.3 Security

- **No `dangerouslySetInnerHTML`**: Never use it. If migrating BDL that rendered raw HTML, convert to JSX or use a sanitization library. If absolutely required, add a comment explaining why and what sanitizes the input.
- **External Links**: All `target="_blank"` links MUST have `rel="noopener noreferrer"`. This prevents tab-napping attacks.
- **No Inline Event Handlers from User Data**: Never construct event handlers or URLs from unsanitized user input. Always validate/encode dynamic href values.
- **Sensitive Data**: Never store tokens, passwords, or PII in component state that could be exposed via React DevTools. Keep sensitive data in Redux with appropriate cleanup on unmount/logout.
- **Dependency Injection over Hardcoded Secrets**: API base URLs, feature flags, and environment-specific values come from configuration — never hardcoded strings in components.

### 10.4 Performance Awareness

- **Memoize Expensive Computations**: Use `useMemo` for array filtering/sorting/mapping operations on lists that re-render frequently.
- **Stable Callback References**: Use `useCallback` for handlers passed as props to child components that use `React.memo` or appear in dependency arrays.
- **Avoid Anonymous Functions in JSX for Lists**: In `.map()` iterations, extract the row component or use `useCallback` — don't create new function references on every render for large lists.
- **Lazy Loading**: Large page-level components that aren't needed on initial render should use `React.lazy()` + `Suspense`.

### 10.5 Accessibility (WCAG 2.1 Level AA)

- **Semantic HTML**: Use `<button>` for actions, `<a>` for navigation, `<nav>` for navigation containers. Don't use `<div onClick>` as a button substitute.
- **ARIA Labels**: Interactive elements without visible text MUST have `aria-label` or `aria-labelledby`. Icon-only buttons always need `aria-label`.
- **Focus Management**: After dialog close, return focus to the trigger element. After form submission errors, move focus to the first error field.
- **Keyboard Navigation**: All interactive elements must be reachable via Tab. Custom components must handle Enter/Space for activation.

### 10.6 Error Handling & Resilience

- **Error Boundaries**: Wrap major page sections in error boundaries so one failing component doesn't crash the entire view.
- **Loading & Error States**: Every component that fetches data must handle three states: loading, success, and error. Never render `undefined.property`.
- **Defensive Array Access**: Always guard `.map()` calls with `Array.isArray()` or default to `[]`. MCA2 API responses may return null for empty collections.
- **Graceful Degradation**: If a non-critical feature fails (e.g., notification badge count), log the error and hide the element rather than crashing the page.

---

## Section 11: Lessons Learned (Seed Entry)

## Run: example-mca1-project — 2026-04-20

### What Went Well
- Parallel batch processing of 24 files across 5 workers completed in under 3 minutes
- Analysis agent correctly identified all 3 transformation types (BDL_ONLY, JMVC_ONLY, BDL_AND_JMVC)

### Issues Encountered
- `FormMultiItem` not recognised as needed for radio groups — transform agent defaulted to plain `<input type="radio">`
- One file had both a Redux thunk dispatch AND `$scope` local state — required auto-decision-agent to determine split

### Resolutions
- Added Rule 3b to Section 3 explicitly listing `<mca-radios>` → `FormMultiItem` + `FormRadio` (not `FormItem`)
- Auto-decision-agent correctly applied Decision Rule 4: `$scope` local state → `useState`; dispatch calls left intact

---

## Section 12: Template Repository Convention Overrides

When `--template-repo` is provided and `template-analysis.json` exists, the following default behaviors are overridden by the template's conventions. Transform agents read `template-analysis.json` during Step 1.5 to determine which overrides apply.

### 12.1 State Management Override

| Default Behavior | Override Condition | New Behavior |
|---------|-------------------|--------------|
| Redux Toolkit (`useAppDispatch`, `useAppSelector`, `createSlice`) | `state_management.library != "redux-toolkit"` | Use detected library's patterns (Zustand stores, Jotai atoms, MobX observables, React Query hooks) |
| `store/slices/` directory structure | Non-Redux state library | Use template's store directory pattern (e.g., `store/useXStore.ts` for Zustand) |
| Async thunks for data fetching | `react-query` detected | Use React Query `useQuery`/`useMutation` hooks |
| `useState` for local UI state | `local-state` detected | Use only `useState`/`useReducer` — no external state library at all |

**Critical:** Existing state management files (Redux slices, etc.) are NEVER modified — new state is created alongside. The "never touch business logic" boundary remains.

### 12.2 Folder Structure Override

| Default Behavior | Override Condition | New Behavior |
|---------|-------------------|--------------|
| `src/pages/{PageName}/` for features | Template uses `features/` | Place under `src/features/{feature-name}/` |
| `src/components/common/` for shared | Template uses `shared/` | Place under `src/shared/components/` |
| `src/hooks/` for custom hooks | Template uses `shared/hooks/` | Place under `src/shared/hooks/` |
| `src/store/slices/` for state | Template uses different pattern | Follow template's store directory |

### 12.3 Naming Convention Override

| Default Behavior | Override Condition | New Behavior |
|---------|-------------------|--------------|
| PascalCase `.tsx` files (`RoleManagement.tsx`) | Template uses kebab-case | Name files as `role-management.tsx` |
| No barrel exports | Template uses barrels (`barrel_exports: true`) | Create `index.ts` in each feature directory |
| Relative imports (`../../components/Button`) | Template uses path aliases | Use `@/components/Button` or configured alias |

### 12.4 Component Pattern Override

| Default Behavior | Override Condition | New Behavior |
|---------|-------------------|--------------|
| Direct Blueprint-React imports | Template provides wrapper components | Import from template wrapper (e.g., `AppFormItem` from `@/shared/components/`) |
| No custom hooks assumed | Template provides utility hooks | Use template hooks (e.g., `useApi`, `useAuth`) where applicable |
| No context providers added | Template defines providers | Wrap with template's providers following its App shell pattern |

### 12.5 MCA2 Constraints That NEVER Get Overridden

These are architectural requirements of MCA2 regardless of template:

1. **MemoryRouter** — MCA2 shell owns the browser URL. Even if template uses BrowserRouter, migration MUST use MemoryRouter.
2. **Blueprint-React component API** — `FormItem` must use render prop, `Dialog` must use slot props (`head`, `foot`), `Table` uses standard HTML elements inside wrapper. Template wrappers must still follow these patterns internally.
3. **process.json** — endpoint URIs never include `/api/router` prefix (framework adds it at runtime).
4. **Business logic boundary** — transform agents never modify existing store/reducer/thunk files. When switching state library, new state files are created alongside existing ones.
5. **Eagle launch function** — `src/index.ts` must export the MCA2 Eagle module launch function.
6. **FormItem render function** — even if template wraps `FormItem`, the underlying pattern must use the render prop (not children wrapping).

---

## 13. Legacy Component Detection Patterns

MCA1 applications may contain legacy jQuery-based components alongside `<mca-*>` web components. These use `steal()` module loading, jQuery plugins (`.chosen()`, `.scpTable()`, `.expandable()`), and `scp-` CSS classes.

### 13.1 Detection Grep Patterns

| Grep Pattern | Legacy Component Type | Mapping File |
|-------------|----------------------|--------------|
| `\.scpAutoComplete\(` | Autocomplete | `LEGACY_AUTOCOMPLETE_MAPPING.md` |
| `\.chosen\(` | Dropdown (all variants) | `LEGACY_DROPDOWN_MAPPING.md` |
| `\.scpTable\(` | DataTable (all variants) | `LEGACY_DATATABLE_MAPPING.md` |
| `\.dialog\(` | Dialog/Popup | `LEGACY_DIALOG_TOOLTIP_MAPPING.md` |
| `\.expandable\(` | Accordion | `LEGACY_ACCORDION_TABS_MAPPING.md` |
| `\.progressBar\(` | Progress steps | `LEGACY_MISC_MAPPING.md` |
| `\.progressiveDisclosure\(` | Show/hide toggle | `LEGACY_MISC_MAPPING.md` |
| `new Spinner\(` | Loading spinner | `LEGACY_MISC_MAPPING.md` |
| `new CalendarUI\(` | Event calendar | `LEGACY_CALENDAR_CUSTOM_MAPPING.md` |
| `WindowManager\.launchWindow\(` | Lightbox popup | `LEGACY_DIALOG_TOOLTIP_MAPPING.md` |
| `this\.showDialog\(` | Tooltip dialog | `LEGACY_DIALOG_TOOLTIP_MAPPING.md` |
| `steal\(` | Module loading | All legacy files |
| `scp-label` | Label | `LEGACY_LABELS_MAPPING.md` |
| `scp-readOnlyText` | Read-only display | `LEGACY_LABELS_MAPPING.md` |
| `scp-message-` | Messages/alerts | `LEGACY_MISC_MAPPING.md` |
| `class="tab-section"` | Tabs | `LEGACY_ACCORDION_TABS_MAPPING.md` |
| `class="row".*-columns` | Grid layout | `LEGACY_LAYOUT_MAPPING.md` |
| `scp-group-with-separator` | Separator | `LEGACY_LAYOUT_MAPPING.md` |
| `scp-navigation-panel` | Footer layout | `LEGACY_LAYOUT_MAPPING.md` |
| `validatePresenceOf` | Validation framework | `LEGACY_CALENDAR_CUSTOM_MAPPING.md` |
| `scp-abs-calendar` | Event calendar | `LEGACY_CALENDAR_CUSTOM_MAPPING.md` |

### 13.2 Forbidden Legacy Patterns (Post-Migration)

After migration, NONE of these patterns should exist in `.tsx`/`.ts` files:

| Pattern | What It Indicates |
|---------|-------------------|
| `steal\(` | MCA1 module loading still present |
| `\.chosen\(` | jQuery dropdown plugin not migrated |
| `\.scpTable\(` | jQuery table plugin not migrated |
| `\.scpAutoComplete\(` | jQuery autocomplete not migrated |
| `\.dialog\(` | jQuery dialog not migrated |
| `\.expandable\(` | jQuery accordion not migrated |
| `\$\(.*\)\.getComponent\(` | MCA1 web component jQuery API |
| `scp-` CSS classes in JSX | Legacy styling not converted |
| `class=".*columns"` in JSX | Legacy grid not converted to Blueprint Grid |
| `WindowManager` | MCA1 popup infrastructure |
| `BaseController` | JMVC controller pattern |
| `scp\.ui\.common` | MCA1 framework namespace |
