
# Migration Skill: MCA 1 JMVC BDL components to MCA 2 React

**Last Updated**: July 7, 2026
**Version**: 3.7
**Status**: UPDATED - Added JMVC controller conversion reference, real-world MCA1 application patterns (from 8 production apps)

## Name
migrateBDL

## Description
Migrate MCA 1 JMVC using BDL web components to MCA 2 React using blueprint-react web components

---

## 📂 Skill Resource Files

This skill includes component mapping files and reference guides. When agents spawn from other projects, these files are accessible via this skill's installation directory:

### Component Mapping Files (23 total)
Located in: `skills/domain-reference/mappings/`

**How Agents Access These Files:**
When spawned by Task tool, agents receive the skill in their context. To reliably access mapping files:

1. **Establish plugin root in Bash context at agent startup:**
   ```bash
   PLUGIN_DIR="$(pwd)/../../.."  # Navigate from agent execution context
   # OR use the PLUGIN_DIR variable if passed by orchestrator
   # OR construct from state file if available
   ```

2. **Read mapping files using absolute paths relative to plugin:**
   ```bash
   Read("${PLUGIN_DIR}/skills/domain-reference/mappings/BDL_BUTTON_MAPPING.md")
   Read("${PLUGIN_DIR}/skills/domain-reference/mappings/BDL_FORM_CONTROLS_MAPPING.md")
   # etc.
   ```

3. **If ${PLUGIN_DIR} is unavailable in spawned context:**
   - Reference mapping file names from this skill's index below
   - Agents will receive context that points to the correct file location
   - Use Glob to search for mapping files by name pattern

### Mapping File Index
- `BDL_BUTTON_MAPPING.md` - Button, button-groups, variants
- `BDL_FORM_CONTROLS_MAPPING.md` - Form, formview, selection
- `BDL_INPUT_MAPPING.md` - Input, date, cardnumber
- `BDL_CHECKBOX_MAPPING.md` - Checkboxes
- `BDL_RADIO_MAPPING.md` - Radios
- `BDL_COMBOBOX_MAPPING.md` - Combobox, dropdown
- `BDL_TEXTAREA_MAPPING.md` - Textarea
- `BDL_TABLE_MAPPING.md` - Table components
- `BDL_DIALOG_MAPPING.md` - Modal, Dialog patterns
- `BDL_LAYOUT_MAPPING.md` - Fluidview, Grid, cells
- `BDL_LINK_MAPPING.md` - Link component
- `BDL_ICON_MAPPING.md` - Icon component
- `BDL_NOTIFY_MAPPING.md` - Notify, Alert
- `BDL_ACCORDION_MAPPING.md` - Accordion
- `BDL_TABS_MAPPING.md` - Tabs
- `BDL_TYPOGRAPHY_MAPPING.md` - Heading, Text, Type
- `BDL_SPINNER_MAPPING.md` - Spinner, Loading
- `BDL_POPOVER_MAPPING.md` - Popover, PopupNav
- `BDL_STEPPER_MAPPING.md` - NumberStepper
- `BDL_STATUSBAR_MAPPING.md` - Statusbar, SlimBanner
- `BDL_IMAGE_MAPPING.md` - Image, Multimedia
- `BDL_DATA_DISPLAY_MAPPING.md` - Infopair, list, progressbar
- `BDL_SORTACCOUNT_MAPPING.md` - Sortaccount, nested patterns

### Reference Documentation
- `BDL_TO_BLUEPRINT_REACT.md` - Master component mapping index
- `MIGRATION_RUNBOOK.md` - Phase-by-phase execution guide
- `BLUEPRINT_REACT_CORRECT_PATTERNS.md` - Correct patterns
- `BLUEPRINT_REACT_REFERENCE.md` - Blueprint-React v1.3.0 API
- `COMPONENT_DECOMPOSITION_PATTERNS.md` - Post-migration component decomposition

---

## ⚠️ CRITICAL - Blueprint-React Pattern Requirements

### DO NOT GENERATE TESTS FOR MIGRATED MCA2 APPLICATION
❌ Do not generate unit tests, integration tests, or E2E tests for the migrated MCA2 code
❌ Do not create test files (*.test.tsx, *.spec.tsx, *.test.ts, *.spec.ts)
❌ Do not suggest or scaffold testing boilerplate as part of the migration output
Migration output should contain only application code — tests are handled separately by the development team

### DO NOT CREATE CUSTOM CSS MODULES FOR:
❌ Form fields - Blueprint FormItem handles styling
❌ Dialog wrappers - Blueprint Dialog handles layout
❌ Tables - Blueprint Table handles styling
❌ Buttons - Blueprint Button handles all variants

### Component Composition Patterns (MANDATORY)

#### ✅ Form Pattern: FormItem with Render Function
```typescript
// CORRECT - FormItem uses render function, NOT children wrapping
// CORRECT - label wrapped in Type, error wrapped in Type with color="error"
<FormItem
  label={<Type>Field Label</Type>}
  error={errorMsg && <Type color="error">{errorMsg}</Type>}
  render={(props) => (
    <FormInput {...props} type="text" value={value} onChange={handler} />
  )}
/>

// WRONG - Don't use FormGroup, FormFieldWrapper, TextInput, TextArea
// WRONG - Don't wrap with children - FormItem requires render function
// WRONG - Don't pass plain strings to label or error - always wrap in Type
```

#### ✅ Dialog Pattern: Slot Properties (head/foot/children)
```typescript
// CORRECT - Dialog uses slot properties, NOT nested components
<Dialog
  head={<h2>Title</h2>}
  foot={<button>Action</button>}
  onClickDismiss={handleClose}
  onClickOverlay={handleClose}
  onKeydownEscape={handleClose}
>
  Content goes here as children
</Dialog>

// WRONG - Don't use DialogHeader, DialogContent, DialogFooter
// WRONG - These components DO NOT exist in Blueprint-React v1.3.0
```

#### ✅ Table Pattern: Standard HTML + Table Wrapper + Type Wrapping
```typescript
// CORRECT - Use standard HTML table elements with Blueprint Table wrapper
// Text cells use <Type element="td/th">, buttons use size="sm"
<Table equalPadding columnBorders headingVariant="default">
  <thead>
    <tr>
      <Type element="th" color="title" weight="medium">Header</Type>
      <Type element="th" color="title" weight="medium">Actions</Type>
    </tr>
  </thead>
  <tbody>
    <tr>
      <Type element="td">{data.value}</Type>
      <td><Button size="sm" variant="secondary" onClick={fn}>Edit</Button></td>
    </tr>
  </tbody>
</Table>

// WRONG - Don't use TableHead, TableBody, TableRow, TableCell
// WRONG - These components DO NOT exist in Blueprint-React v1.3.0
// WRONG - Don't use bare <td>{text}</td> - always wrap text in <Type element="td">
// WRONG - Don't use default-size buttons in tables - always use size="sm"
```

**See also:** [MCA2_PAGE_LAYOUT_PATTERNS.md](guides/MCA2_PAGE_LAYOUT_PATTERNS.md) for full page composition patterns.

#### ✅ Button Pattern: Valid Variants + Status Props
```typescript
// CORRECT - Use valid variants and status prop
<Button variant="primary">Primary Action</Button>
<Button variant="secondary">Secondary Action</Button>
<Button variant="subtle">Subtle/Link Style</Button>
<Button status="danger">Delete Action</Button>
<Button size="sm">Small Button</Button>

// WRONG - Don't use these
<Button variant="ghost" />       // DOESN'T EXIST - use variant="subtle"
<Button variant="danger" />      // DOESN'T EXIST - use status="danger"
<Button variant="tertiary" />    // DOESN'T EXIST - use variant="secondary"
```

#### ✅ Layout Pattern: Use Blueprint Layout Components (CRITICAL!)
```typescript
// CORRECT - Use Blueprint layout components
import { Page, Navbar, Section, SectionItem, Grid, Arrange, ArrangeItem, Panel, Type } from '@barclays/blueprint-react';

// Full page layout
<Page
  head={<Navbar><h1>Title</h1></Navbar>}
  contentHead={<nav>Breadcrumbs</nav>}
>
  <Section>
    <SectionItem>Content</SectionItem>
  </Section>
</Page>

// Responsive grid
<Grid>
  <Grid.Col size="1of3" sizeXs="1of1">
    <Panel spaced>Item 1</Panel>
  </Grid.Col>
  <Grid.Col size="1of3" sizeXs="1of1">
    <Panel spaced>Item 2</Panel>
  </Grid.Col>
  <Grid.Col size="1of3" sizeXs="1of1">
    <Panel spaced>Item 3</Panel>
  </Grid.Col>
</Grid>

// Horizontal flex layout
<Arrange gap="fixed" justify="center">
  <ArrangeItem size="fit"><button>Action 1</button></ArrangeItem>
  <ArrangeItem size="fit"><button>Action 2</button></ArrangeItem>
</Arrange>

// Text with spacing
<Type element="h2" marginBottom size="lg">Heading</Type>
<Type element="p" marginBottom>Paragraph</Type>

// WRONG - Don't use custom CSS for layout
// ❌ DON'T create .module.css with flex/grid/layout properties
// ❌ DON'T use inline styles for layout: style={{ display: 'flex', gap: '1rem' }}
// ❌ DON'T use custom divs: <div className={styles.container}>
// ❌ DON'T wrap unnecessarily: <div><Panel><div>Content</div></Panel></div>

// Reference: BLUEPRINT_REACT_CORRECT_PATTERNS.md for all layout component APIs
```

---

## Important Instructions
- *Follow all instructions*
- *Don't assume, verify and validate, follow patterns and generated references*

## Setup Phase

### Output of Setup Phase
- BLUEPRINT_REACT_REFERENCE.md
- BLUEPRINT_REACT_CORRECT_PATTERNS.md - Definitive component pattern reference
- BLUEPRINT_REACT_CORRECT_PATTERNS.md - Layout and component patterns (Page, Grid, Arrange, etc)
- EAGLE_FRAMEWORK_REFERENCE.md
- LIBS_FOUNDATION_REFERENCE.md
- MCA2_UI_LAUNCHER_REFERENCE.md
- BDL_TO_BLUEPRINT_REACT.md
- Save all these files in skills/migrate folder

### Critical Validation Steps

**BEFORE creating any wrapper components:**
1. ✅ Check if the component exists in Blueprint-React storybook
2. ✅ Verify the component API in node_modules/@barclays/blueprint-react/dist/
3. ✅ Review storybook examples for correct usage patterns
4. ✅ If component not found, it likely doesn't exist - use Blueprint native components instead

### Validation Checklist
- If all the reference files already exist, check versions in reference and each repository.
  - If they are same, proceed without creating new reference files, use the existing ones.
  - Else, do the proper setup process and replace old reference file with new details from the new version.

### 1. Blueprint-React Reference (Parallel Task)
- Clone blueprint-react repository in a tmp/ folder:
  ```bash
  git clone git@app.gitlab.barcapint.com:barclays/blueprint-design-system/web/blueprint-react.git
  ```
- Explore codebase **THOROUGHLY**
- **MANDATORY: Check storybook for actual component usage patterns**
- Create reference file BLUEPRINT_REACT_REFERENCE.md documenting:
  - version
  - All exported components (NOT assumed wrappers)
  - Component props with actual type definitions
  - Component variants from storybook
  - Usage examples from storybook (NOT made-up examples)
  - **EXPLICITLY LIST non-existent components** (FormGroup, DialogHeader, Tooltip, Popover, Spinner, etc.)

### 2. Eagle Framework Context (Parallel Task)
- Clone mca-eagle-scripts repository in tmp folder:
  ```bash
  git clone https://app.gitlab.barcapint.com/barclays/mca-core-engineering-ba/libs/frontend/archive/mca-eagle-scripts
  ```
- Explore codebase
- Understand React MCA2 application framework
- Document framework patterns and version in EAGLE_FRAMEWORK_REFERENCE.md

### 3. UI Libs Foundation (Parallel Task)
- Clone scp-libs-ui-foundation repository in tmp folder:
```bash
git clone git@app.gitlab.barcapint.com:barclays/mca-core-engineering-ba/libs/frontend/mca1/scp-libs-ui-foundation.git
```
- Explore codebase
- Understand the lib foundation
- Create LIBS_FOUNDATION_REFERENCE.md document with version

### 4. MCA2 UI Launcher (Parallel Task)
- Clone mca-ui-core repository in tmp folder:
```bash
git clone git@app.gitlab.barcapint.com:barclays/mca-core-engineering-ba/libs/frontend/mca-ui-core.git
```
- Explore codebase and understand UI launcher
- Create MCA2_UI_LAUNCHER_REFERENCE.md with version

### 5. BDL Components (Parallel Task)
- Clone mca-ui-components repository in tmp folder:
```bash
git clone git@app.gitlab.barcapint.com:barclays/mca-core-engineering-ba/libs/frontend/mca1/mca-ui-components.git
```
- Explore codebase for BDL components
- Create BDL_REFERENCE.md documenting actual BDL components
- Create BDL_TO_BLUEPRINT_REACT.md mapping for direct Blueprint-React equivalents

---

## Migration Phase

### Reference Files (Use These as Authority)
- BLUEPRINT_REACT_REFERENCE.md - Actual Blueprint components (from storybook)
- BLUEPRINT_REACT_CORRECT_PATTERNS.md - Definitive pattern reference
- BDL_TO_BLUEPRINT_REACT.md and all other mapping files in mappings/ directory
- EAGLE_FRAMEWORK_REFERENCE.md - MCA2 framework patterns
- LIBS_FOUNDATION_REFERENCE.md - MCA1 foundation library
- MCA2_UI_LAUNCHER_REFERENCE.md - UI launcher integration

### Step 1: Gather Target Project Information
- Explore MCA 1 codebase
- Document features in `DOCUMENTATION.md`
- Document API calls and endpoints
- Create component mapping file (BDL → Blueprint)
- **Identify custom components and verify they match Blueprint patterns**
- Note: Custom components must follow Blueprint design patterns, NOT create new CSS modules

#### Step 1a: Constants & Headings Inventory (MANDATORY)
- Read the MCA1 `constants/constants.js` file FIRST before any code generation
- Extract ALL heading constants (HEADING_*, NOTIFICATION_HEAD_*, LABEL_*)
- Create a constants mapping table: MCA1 constant name → exact text value
- These heading texts MUST be used **verbatim** in MCA2 — never paraphrase or rename
- Document which sections are always-visible vs conditionally-shown in the EJS templates
- Document which fields have radio/toggle gates vs which are direct inputs (always visible)
- Cross-reference the EJS view file structure to identify section boundaries (`<mca-cell type="section">`)

#### Step 1b: Field Visibility Audit (MANDATORY)
- For each form field in the EJS views, determine: is it **always visible**, or is it **gated** by a radio/toggle?
- MCA1 fields wrapped in `<%if (condition) {%>` are conditional — replicate the condition in MCA2
- MCA1 fields NOT wrapped in conditionals are always-visible — do NOT add enable/disable radios
- Direct `<mca-input>` fields (without preceding `<mca-radios>`) must remain direct `<FormItem>` + `<FormInput>` in MCA2
- Only add `<FormMultiItem>` + `<FormRadio>` when MCA1 explicitly has `<mca-radios>` for that field

### Step 2: Create MCA 2 Application
**User Action Required:**
```bash
cd mca2
eagle create <app-name>
```
*Note: This opens an interactive session that must be completed manually*

### Step 3: Blueprint-React Deep Dive
- Repository: `blueprint-react`
- **Review storybook FIRST** - this is the authoritative API reference
- Review all components, variants, and usage in storybook
- Create helper/reference file
- Verify version number
- If version mismatch, clone latest version and update reference
- **CRITICAL: Validate that components you plan to use actually exist**

### Step 4: Configure API Endpoints & Verify Backend Contract
- Create `process.json` in MCA 2 application
- Reference all endpoints from MCA 1 application
- Ensure endpoint compatibility
- **Backend API Contract Verification:**
  1. EPS (backend) repository URL is provided via `--eps-repo` flag
  2. Clone the EPS repo into `.claude/tmp/eps-backend`
  3. Checkout the latest release branch (`release/YY.M` or `release/YY.MM` — e.g., `release/26.5` for May 2026). If no release branch exists, use the default branch.
  4. Scan for endpoint definitions (Spring `@GetMapping`/`@PostMapping`, Express `router.get`/`router.post`, etc.)
  5. Extract request/response shapes from DTOs, interfaces, or return types
  6. Document all endpoints in `API_CONTRACTS.md` at the project root with: method, path, request body shape, response body shape, source file reference
  7. Cross-check `process.json` URIs against discovered backend endpoints — flag any mismatches
  8. Verify NO `/api/router` prefix in `process.json` (framework adds this automatically — see Mistake 24)
  9. Clean up: remove `.claude/tmp/eps-backend` after extraction
- **Why this matters:** Silent runtime failures occur when the UI calls endpoints that don't exist or sends/receives unexpected payloads. The API contract doc serves as a reference for transform agents to produce correct fetch calls and Redux thunk payloads.

### Step 5: Add Core Libraries
Install and configure:
- **React Router**: For navigation
- **Redux Toolkit**: For global state management
- **Yup**: For form validation

### Step 6: Create Wrapper Components (NO CSS MODULES)
**IMPORTANT: Follow Blueprint patterns, don't create custom styling**

When creating wrapper components:
1. ✅ Use Blueprint components with their native props
2. ✅ Follow render function pattern for FormItem
3. ✅ Use slot properties for Dialog
4. ✅ Use standard HTML for tables
5. ✅ Validate button variants and status props
6. ❌ Don't create .module.css files for Blueprint components
7. ❌ Don't wrap Blueprint components in unnecessary divs
8. ❌ Don't create non-existent components

Example (CORRECT):
```typescript
// FormField.tsx - CORRECT approach
export const FormField = ({ label, value, onChange, error }) => (
  <FormItem
    label={label}
    error={error}
    render={(props) => (
      <FormInput {...props} value={value} onChange={onChange} />
    )}
  />
);
```

### Step 7: Execute Migration
- Create all pages using Blueprint components
- **Validate each component exists in storybook BEFORE using**
- Implement features for each page
- Handle navigation across entire application
- Make sure all text visible in UI is wrapped in Type component from Blueprint-React with right attributes
- Add classNames, name and id attribute same as MCA1, but don't add the styles associated with it. It is only that it works with existing end-to-end test cases. The styling is already taken care by Blueprint-react components. 
- Create `SUMMARY.md` documenting:
  - Complete navigation structure
  - Page hierarchy
  - Route mappings
  - Feature implementation status

### Step 8: Testing & Validation 
- ✅ Run build, check for build errors and fix them if there are any.
- ✅ check lint and fix all lint errors, warnings can be ignored.
- ✅ Test all forms with FormItem + render function pattern
- ✅ Test all dialogs with Dialog slot properties
- ✅ Test all tables with standard HTML + Table wrapper
- ✅ Test all buttons with correct variants/status
- ✅ Verify no custom CSS modules for Blueprint components
- ✅ Validate blueprint components render correctly

---

## Deliverables
1. `DOCUMENTATION.md` - Features and API documentation
2. `process.json` - API endpoint configuration
3. `SUMMARY.md` - Navigation and migration summary
4. Fully migrated MCA 2 React application
5. Updated reference documents for future migrations

## Final Steps
- Clear tmp folder
- Verify all components follow Blueprint patterns
- No unnecessary CSS modules
- All custom wrappers follow documented patterns

---

## ⚠️ Common Mistakes to AVOID

### Mistake 1: Creating CSS Modules for Blueprint Components
❌ WRONG:
```typescript
// FormField.module.css - Don't do this!
.formGroup { margin-bottom: 1.5rem; }
.field { /* custom styles */ }

// Just use Blueprint's built-in styling
```

✅ CORRECT:
```typescript
// Let Blueprint handle styling, only add spacing when needed
// Minimal CSS for layout adjustments only
.container { margin-top: 1rem; }
```

### Mistake 2: Using Non-Existent Components
❌ WRONG:
```typescript
import { FormGroup, FormFieldWrapper, TextInput } from '@barclays/blueprint-react';
import { DialogHeader, DialogContent, DialogFooter } from '@barclays/blueprint-react';
import { TableHead, TableBody, TableRow, TableCell } from '@barclays/blueprint-react';
// None of these exist!
```

✅ CORRECT:
```typescript
import { FormItem, FormInput, Dialog, Table } from '@barclays/blueprint-react';
// Only import components that exist in Blueprint-React
```

### Mistake 3: Wrapping FormItem with children
❌ WRONG:
```typescript
<FormItem label="Name">
  <FormInput value={value} />
</FormItem>
// FormItem expects render function, not children
```

✅ CORRECT:
```typescript
<FormItem
  label="Name"
  render={(props) => <FormInput {...props} value={value} />}
/>
```

### Mistake 4: Using Dialog with nested components
❌ WRONG:
```typescript
<Dialog isOpen={true}>
  <DialogHeader><h2>Title</h2></DialogHeader>
  <DialogContent>Content</DialogContent>
  <DialogFooter><button>Close</button></DialogFooter>
</Dialog>
// These components don't exist
```

✅ CORRECT:
```typescript
<Dialog
  isOpen={true}
  head={<h2>Title</h2>}
  foot={<button>Close</button>}
>
  Content goes here
</Dialog>
```

### Mistake 5: Using invalid button variants
❌ WRONG:
```typescript
<Button variant="ghost" />      // Doesn't exist
<Button variant="danger" />     // Doesn't exist
<Button variant="tertiary" />   // Doesn't exist
```

✅ CORRECT:
```typescript
<Button variant="primary" />
<Button variant="secondary" />
<Button variant="subtle" />     // Use for "ghost" style
<Button status="danger" />      // Use status prop for danger
```

### Mistake 6: Using non-existent table components
❌ WRONG:
```typescript
<Table>
  <TableHead><TableRow><TableCell>Header</TableCell></TableRow></TableHead>
  <TableBody><TableRow><TableCell>Data</TableCell></TableRow></TableBody>
</Table>
```

✅ CORRECT:
```typescript
<Table>
  <thead><tr><th>Header</th></tr></thead>
  <tbody><tr><td>Data</td></tr></tbody>
</Table>
```

### Mistake 7: Creating custom CSS for layout (CRITICAL!)
Already covered above in Mistake 7 section

### Mistake 8: Using invalid props on Blueprint Type component
❌ WRONG:
```typescript
<Type element="div" color="brand" marginTop="md">Text</Type>
// - element only accepts: h1-h6, p, span, em, strong, td, th
// - color doesn't support "brand" (valid: title, error, info, success, warning, default, disabled, inverse)
// - Type doesn't have marginTop prop (only marginBottom)
```

✅ CORRECT:
```typescript
<Type element="span" weight="bold">Text</Type>
// Use element for semantic HTML, weight for styling
// Use marginBottom={true} for spacing, not marginTop
```

### Mistake 9: Using unsupported margin props on layout components
❌ WRONG:
```typescript
<Grid marginBottom>...</Grid>
<Panel marginBottom>...</Panel>
<Arrange marginBottom>...</Arrange>
// Grid, Panel, Arrange don't have marginBottom prop
```

✅ CORRECT:
```typescript
<Section>
  <Grid>...</Grid>
  <SectionItem spacing="md">...</SectionItem>
  <Grid>...</Grid>
</Section>
// Use Section/SectionItem for vertical spacing, not margin props
```

### Mistake 10: Using invalid Grid.Col size values
❌ WRONG:
```typescript
<Grid.Col size="1of1" sizeXs="1of1">...</Grid.Col>
// 1of1 doesn't exist - Grid uses 12-column system
```

✅ CORRECT:
```typescript
<Grid.Col size="1of12" sizeXs="1of12">...</Grid.Col>
// Valid sizes: 1of12, 2of12, ... 12of12 (or 1of2, 1of3, 1of4, 1of6, etc)
```

### Mistake 11: Using divs instead of Type component for text
❌ WRONG:
```typescript
// MainLayout.tsx with custom CSS module
<div className={styles.mainLayout}>
  <div className={styles.container}>
    <div className={styles.sidebar} />
    <main className={styles.mainContent}>
      Content
    </main>
  </div>
</div>
```

```css
/* MainLayout.module.css - DON'T DO THIS! */
.mainLayout {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}
.container {
  display: flex;
  flex: 1;
}
.sidebar {
  width: 250px;
  border-right: 1px solid #e0e0e0;
}
.mainContent {
  flex: 1;
  padding: 2rem;
}
```

✅ CORRECT - Use Blueprint layout components:
```typescript
// Use Page, Navbar, Section, Grid, Arrange, Panel, Type for layout
import { Page, Navbar, Section, SectionItem, Grid, Arrange, ArrangeItem, Panel, Type } from '@barclays/blueprint-react';

<Page
  head={
    <Navbar>
      <Type element="h1">{title}</Type>
      <Arrange gap="fixed">{actions}</Arrange>
    </Navbar>
  }
  contentHead={breadcrumbs && <nav>{breadcrumbs}</nav>}
>
  <Section>
    <SectionItem>{children}</SectionItem>
  </Section>
</Page>
```

```css
/* MainLayout.module.css - EMPTY or minimal only */
/* Blueprint components handle all layout and spacing */
/* Only add animations if needed: */
@keyframes spin {
  to { transform: rotate(360deg); }
}
```

**Blueprint Layout Components to Use**:
- `Page` - Full page layout with head/nav/foot slots
- `Navbar` - Header navigation bar
- `Section`/`SectionItem` - Content sections with spacing
- `Grid`/`Grid.Col` - 12-column responsive grid
- `Arrange`/`ArrangeItem` - Flexbox horizontal layout
- `Panel` - Content container with styling
- `Type` - Text with built-in margin props
- `Box` - Simple centered container

**See BLUEPRINT_REACT_CORRECT_PATTERNS.md for complete layout reference**

### Mistake 11: Using divs instead of Type component for text
❌ WRONG:
```typescript
<div>Display total count</div>
<div className={styles.message}>Error message</div>
// Using plain divs for text loses Blueprint styling and spacing consistency
```

✅ CORRECT:
```typescript
<Type>Display total count</Type>
<Type element="p" marginBottom="md">Error message</Type>
// Use Type for all text - provides consistent styling and spacing
```

### Mistake 12: Using Icon component incorrectly
❌ WRONG:
```typescript
<Icon name="tick-circle" />           // Wrong prop name
<Icon icon="tick" />                  // Icon names include full path
<Icon icon="tick-circle" size="2x" /> // Wrong size value
```

✅ CORRECT:
```typescript
<Icon icon="tick" size="md" />
<Icon icon="tick" size="lg" />
// Use "icon" prop (not "name"), valid sizes: xs, sm, md, lg, xl, 2xl, sm-and-md
// Note: "tick-circle" does NOT exist — use "tick"
```

### Mistake 13: Incorrect Alert component usage
❌ WRONG:
```typescript
<Alert
  head={title}
  icon="info"
  variant="info"
  onClose={handler}
>
  Message
</Alert>
// Alert doesn't have "icon" or "onClose" - use "media" for icon, "onDismiss" for handler
```

✅ CORRECT:
```typescript
<Alert
  head={<Type weight="medium" size="md">{title}</Type>}
  media={<Icon icon="info-fill" size="sm" ariaHidden />}
  variant="info"
  onDismiss={handler}
>
  <Type>Message</Type>
</Alert>
```

### Mistake 14: Not validating all component props against storybook
❌ General Problem:
- Assuming component props exist without checking storybook
- Using props that sound right but don't exist in Blueprint
- Not running TypeScript build to catch prop errors early

✅ Solution:
1. Check Blueprint storybook for every component before using
2. Read TypeScript definitions: node_modules/@barclays/blueprint-react/dist/**/*.d.ts
3. Run npm build frequently to catch prop errors
4. Never assume props work - verify in storybook examples first

### Mistake 15: Icon component without size prop (icons render huge!)
❌ WRONG - No size specified, icons render at default (too large):
```typescript
<Icon icon="tick-circle" />                    // Renders HUGE - avoid!
<Button media={<Icon icon="chevron-right" />}>  // Icon too large in button
<Alert media={<Icon icon="info" />}>          // Alert icon too large
```

✅ CORRECT - Always specify icon size:
```typescript
// Buttons: use "sm" for compact icons
<Button media={<Icon icon="chevron-right" size="sm" />}>Action</Button>

// Alerts: use "md" for balanced size
<Alert media={<Icon icon="info" size="md" />}>Message</Alert>

// Standalone icons: match context
<Icon icon="tick" size="lg" />  // Larger contexts
<Icon icon="tick" size="md" />  // Medium contexts
<Icon icon="tick" size="sm" />  // Compact contexts
```

**Valid Icon Sizes**: `xs` | `sm` | `md` | `lg` | `xl` | `2xl` | `sm-and-md` (responsive)

**Size Recommendations by Context**:
- **Buttons**: `sm` - Icons in buttons should be compact
- **Alerts/Messages**: `md` - Medium size for readability
- **Tables**: `sm` or `md` - Depends on table density
- **Standalone**: `md` or `lg` - Use `lg` for important visual indicators
- **Inline with text**: `sm` - Match text line height

### Mistake 16: Using non-existent icon names (e.g., "-circle" variants)
❌ WRONG - These icon names DON'T EXIST in Blueprint:
```typescript
<Icon icon="tick-circle" />      // DOESN'T EXIST - use "tick"
<Icon icon="cross-circle" />     // DOESN'T EXIST - use "dismiss"
<Icon icon="info-circle" />      // DOESN'T EXIST - use "info"
<Icon icon="success-circle" />   // DOESN'T EXIST - use "tick"
<Icon icon="error-circle" />     // DOESN'T EXIST - use "error"
```

✅ CORRECT - Use existing icon names:
```typescript
<Icon icon="tick" size="md" />       // Success checkmark
<Icon icon="dismiss" size="md" />    // Close/X mark (NOT "cross" — use "dismiss")
<Icon icon="info" size="md" />       // Info icon
<Icon icon="warning" size="md" />    // Warning icon
<Icon icon="error" size="md" />      // Error icon
```

**Common Icon Replacements**:
- BDL `tick-circle` → Blueprint `tick`
- BDL `cross-circle` → Blueprint `dismiss`
- BDL `cross` → Blueprint `dismiss`
- BDL `info-circle` → Blueprint `info`
- BDL `times-circle` → Blueprint `dismiss`
- BDL `check-circle` → Blueprint `tick`

**All Blueprint Icon Names**: See BDL_TO_BLUEPRINT_REACT.md Section 8 for icon mapping and valid names

### Mistake 17: Dashboard design doesn't match MCA1 homescreen structure
❌ WRONG - Creating separate statistics dashboard instead of management interface:
```typescript
// WRONG - Shows stats and links to separate pages
<Dashboard>
  <StatsCards roles={count} services={count} parameters={count} />
  <QuickAccessCards />
</Dashboard>
```

✅ CORRECT - Match MCA1 structure: unified interface with all controls on one page
```typescript
// CORRECT - MCA1 maintainroles.ejs pattern: single page with all controls
<Dashboard>
  {/* Roles Section */}
  <Section>
    <FormItem label="Roles" render={(props) => <FormSelect {...props}><options/></FormSelect>} />
    <FormItem label="Action" render={(props) => <FormSelect {...props}><options/></FormSelect>} />
    <ActionButton label="Apply" />
  </Section>

  {/* Services Section */}
  <Section>
    <FormItem label="Services" render={(props) => <FormSelect {...props}><options/></FormSelect>} />
    <ActionButton label="Maintain" />
    <ActionButton label="Add New" />
    <ActionButton label="Add Service To Roles" />
    <ActionButton label="Remove Service From Roles" />
  </Section>

  {/* Parameters Section */}
  <Section>
    <FormItem label="Parameters" render={(props) => <FormSelect {...props}><options/></FormSelect>} />
    <ActionButton label="Maintain" />
    <ActionButton label="Add New" />
  </Section>
</Dashboard>
```

**MCA1 Pattern**: The homescreen (`maintainroles.ejs`) is the **main management interface**, not a navigation hub. Users can:
- Select a role and action, then apply
- Select a service and manage it directly
- Select a parameter and maintain it directly

**MCA2 Anti-Pattern**: Creating a dashboard with just statistics and links forces extra navigation

### Mistake 18: Creating custom select/input instead of using FormItem + FormSelect
❌ WRONG - Custom div-based select with inline styles:
```typescript
<div>
  <label>Services</label>
  <select style={{ width: '100%', padding: '8px' }}>
    {/* options */}
  </select>
</div>
```

✅ CORRECT - Use Blueprint FormItem with FormSelect render function:
```typescript
import { FormItem, FormSelect } from '@barclays/blueprint-react';

<FormItem
  label="Services"
  render={(props) => (
    <FormSelect {...props} value={selected} onChange={handler}>
      <option value="">Select Item</option>
      {/* options */}
    </FormSelect>
  )}
/>
```

**Why**: FormItem + FormSelect provide consistent styling, validation, and Blueprint design patterns

### Mistake 19: Using invalid Grid.Col sizes (1of1, wrong fractions)
❌ WRONG - Invalid size values that don't map to 12-column grid:
```typescript
<Grid.Col size="1of1" />         // WRONG - doesn't exist
<Grid.Col size="1of8" />         // WRONG - 12-column only
<Grid.Col size="50%" />          // WRONG - not a valid value
```

✅ CORRECT - Use valid 12-column fractions:
```typescript
// Valid sizes: fractions that divide 12
<Grid.Col size="1of12" />        // 1 column
<Grid.Col size="1of6" />         // 2 columns
<Grid.Col size="1of4" />         // 3 columns
<Grid.Col size="1of3" />         // 4 columns
<Grid.Col size="1of2" />         // 6 columns
<Grid.Col size="2of3" />         // 8 columns
<Grid.Col size="3of4" />         // 9 columns
<Grid.Col size="5of6" />         // 10 columns
<Grid.Col size="12of12" />       // 12 columns (full width)
```

**Pattern**: For 50/50 split use `size="1of2"` or for responsive, use `sizeMd="1of12"` for mobile

### Mistake 20: Form controls with inconsistent sizing (buttons too small, dropdowns cramped)
❌ WRONG - Mixed button sizes making UI look inconsistent:
```typescript
<ActionButton label="Apply" />                    // Default size
<ActionButton label="Add New" size="sm" />        // Small - looks smaller!
<ActionButton label="Maintain" />                 // Default size again
// Result: Buttons of varying heights creating visual clutter
```

❌ WRONG - Dropdowns in overly narrow grid columns:
```typescript
<Grid>
  <Grid.Col size="1of3">                          // Too narrow for form
    <FormItem label="Roles" render={...} />       // Dropdown appears cramped
  </Grid.Col>
  <Grid.Col size="1of3">
    <FormItem label="Action" render={...} />      // Cramped
  </Grid.Col>
</Grid>
```

✅ CORRECT - Consistent button sizing and proper form width:
```typescript
// All buttons use default size for consistency
<ActionButton label="Apply" />                    // Default
<ActionButton label="Add New" icon="plus" />      // Default (no size="sm")
<ActionButton label="Maintain" />                 // Default

// Forms get appropriate width - 50/50 for pair, full width for single
<SectionItem spacing="md">
  <Grid>
    <Grid.Col size="1of2">                        // Reasonable width for dropdown
      <FormItem label="Roles" render={...} />
    </Grid.Col>
    <Grid.Col size="1of2">
      <FormItem label="Action" render={...} />
    </Grid.Col>
  </Grid>
</SectionItem>

<SectionItem spacing="md">
  <FormItem label="Services" render={...} />      // Full width - entire section
</SectionItem>

// Buttons in Arrange with consistent gap
<Arrange gap="fixed">
  <ArrangeItem size="fit">
    <ActionButton label="Maintain" variant="primary" />
  </ArrangeItem>
  <ArrangeItem size="fit">
    <ActionButton label="Add New" icon="plus" />
  </ArrangeItem>
</Arrange>
```

**Rules for Consistent UI**:
1. **Never mix button sizes** - Use default size for all buttons (don't use `size="sm"`)
2. **Form width considerations**:
   - Single form field = use full width (1 column, no Grid)
   - Two fields = use Grid with `size="1of2"` each (50/50 split)
   - Three+ fields = use Grid with `size="1of3"` or appropriate fraction
3. **Use proper spacing**:
   - Separate form and buttons into different SectionItems
   - Use `gap="fixed"` in Arrange for consistent button spacing
4. **Blueprint Button sizes**: Only use `size` when truly needed (e.g., compact icon buttons in tables)
5. **TABLE EXCEPTION:** Inside `<td>`/`<th>` cells, `size="sm"` is MANDATORY — see Mistake 32. This does not violate the "no mixed sizes" rule because table buttons operate in a distinct compact context.

### Mistake 21: Excessive nesting of layout components creating whitespace bloat
❌ WRONG - Every element in its own SectionItem (cumulative spacing):
```typescript
<Section>
  <SectionItem spacing="md">                      // spacing="md"
    <Type element="h2">Title</Type>
  </SectionItem>

  <SectionItem spacing="md">                      // spacing="md" AGAIN
    <FormItem label="Field" render={...} />
  </SectionItem>

  <SectionItem spacing="md">                      // spacing="md" AGAIN
    <Arrange>
      <ActionButton label="Action" />
    </Arrange>
  </SectionItem>
</Section>
// Result: Huge gaps between elements, lots of wasted space
```

✅ CORRECT - Group related content in single SectionItems:
```typescript
<Section>
  <SectionItem spacing="md">                      // Title + form together
    <Type element="h2" marginBottom>Title</Type>
    <FormItem label="Field" render={...} />
  </SectionItem>

  <SectionItem spacing="md">                      // Buttons separate
    <Arrange>
      <ActionButton label="Action" />
    </Arrange>
  </SectionItem>
</Section>
// Result: Proper spacing, compact layout, no whitespace bloat
```

**Pattern for Dashboard-like Interfaces**:
```typescript
<Section>
  {/* First SectionItem: Title + Form Controls */}
  <SectionItem spacing="md">
    <Type element="h2" marginBottom>Title</Type>
    <Grid>
      <Grid.Col size="1of2">
        <FormItem label="Field 1" render={...} />
      </Grid.Col>
      <Grid.Col size="1of2">
        <FormItem label="Field 2" render={...} />
      </Grid.Col>
    </Grid>
  </SectionItem>

  {/* Second SectionItem: Buttons */}
  <SectionItem spacing="md">
    <Arrange gap="fixed">
      <ArrangeItem size="fit">
        <ActionButton label="Action 1" />
      </ArrangeItem>
      <ArrangeItem size="fit">
        <ActionButton label="Action 2" />
      </ArrangeItem>
    </Arrange>
  </SectionItem>
</Section>
```

**Guidelines**:
1. **Minimize SectionItem nesting** - Each Section should have 2-3 SectionItems max
2. **Group related content** - Title + form together, buttons separate
3. **Only use SectionItem for major content separation** - Not for every single element
4. **`spacing="md"` applies between SectionItems** - Reduces when you have fewer SectionItems
5. **Avoid repetitive `spacing="md"`** - Cumulative spacing creates whitespace bloat
6. **Button footer**: Use `<Grid.Col fill>` for left-aligned back button, `<Grid.Col fit>` for right-aligned primary action

**See also:** [MCA2_PAGE_LAYOUT_PATTERNS.md](guides/MCA2_PAGE_LAYOUT_PATTERNS.md) for production-derived page composition, spacing values, and Grid layout patterns.

---

## Key Considerations

### 1. Blueprint-React Philosophy
- Blueprint components handle their own styling
- Don't override with custom CSS modules unnecessarily
- Use composition (props) instead of styling
- Follow the storybook patterns exactly
- **Layout is handled by dedicated layout components (Page, Grid, Arrange)**

### 2. Component API Validation
- **ALWAYS check storybook FIRST**
- Verify in node_modules type definitions
- Don't assume wrapper components exist
- If not in storybook, it doesn't exist

### 3. Component Patterns
- FormItem uses render functions
- Dialog uses slot properties (head/foot/children)
- Tables use standard HTML elements
- Buttons use specific variants and status props
- **Layout uses Page, Grid, Arrange, Section, Panel components - NOT custom CSS**

### 4. Layout Components (CRITICAL)
- **Page**: Full page layout with head/nav/contentHead/foot slots
- **Grid**/**Grid.Col**: 12-column responsive grid system
- **Arrange**/**ArrangeItem**: Flexbox horizontal layout
- **Section**/**SectionItem**: Content sections with spacing control
- **Panel**: Content container with variant styling
- **Navbar**: Header navigation bar
- **Type**: Text with built-in margin props (marginBottom, marginTop, etc)
- **Box**: Simple centered container
- **NEVER create custom CSS for layout - use these components instead**

### 5. Custom Component Creation
- Only create custom components if Blueprint doesn't have equivalent
- Custom components must follow Blueprint design patterns
- Don't create custom CSS for Blueprint components
- Don't create custom CSS for layout - use Blueprint layout components
- Use minimal inline styles or CSS modules only for animations/special styling

### 6. API Service Initialization in MCA2 (CRITICAL!)
- **API services MUST be initialized before Redux thunks are dispatched**
- MCA2 passes the `ApiMCA` instance to the launch function
- Initialize API services in Entry component (not App)
- Use `useEffect` with dependency on `props.api` to avoid race conditions

**Critical Pattern - Entry Component**:
```typescript
// src/Entry.tsx
import { initializeApiServices } from './api/endpoints';

function Entry(props: any): React.ReactElement {
  useEffect(() => {
    // Initialize API services with MCA2 api instance
    if (props.api) {
      initializeApiServices(props.api);
    }
  }, [props.api]);

  return (
    <ErrorBoundary FallbackComponent={ErrorFallbackComponent}>
      <React.Suspense fallback={<div>Loading...</div>}>
        <App {...props} />  // App can now use API services
      </React.Suspense>
    </ErrorBoundary>
  )
}
```

**Why This Pattern**:
- Entry receives `api` from index.ts (launch function)
- Entry initializes API services before rendering App
- useEffect ensures initialization happens before async thunks run
- Prevents "API services not initialized" errors in Redux thunks

**Common Mistake**: Initializing in App component (too late - Dashboard may dispatch before initialization)

### 7. Routing in MCA2 (IMPORTANT!)
- **MCA2 only supports MemoryRouter - NOT BrowserRouter**
- Do NOT use BrowserRouter (URL-based routing) in MCA2 applications
- Use MemoryRouter for all navigation within MCA2 modules
- MemoryRouter keeps history in memory (no URL changes, no page reloads)
- This is by design - MCA2 modules don't control the browser URL

**Correct MCA2 App Setup**:
```typescript
import { MemoryRouter } from 'react-router';

function App() {
  return (
    <Provider store={store}>
      <MemoryRouter>
        <DynamicThemeProvider theme={themes}>
          <AppRoutes />
        </DynamicThemeProvider>
      </MemoryRouter>
    </Provider>
  );
}
```

### 7. Testing & Validation
- Test components against storybook examples
- Verify all imports exist
- Validate no TypeScript errors from missing components
- Check all buttons render with correct styling
- Validate layout is responsive at all breakpoints (xs, sm, md, lg)

### 8. Defensive Programming (CRITICAL!)
- **API Response Validation**: Always validate that API responses match expected structure
- **Array Checks in Components**: Use `Array.isArray()` before calling `.map()` on data
- **Service Layer Validation**: API services should return validated data structures
- **Redux State Validation**: Component selectors should check data types before use
- **Error States**: Components must handle undefined/null/unexpected data gracefully

**Pattern**:
```typescript
// API service - validate response
const data = response?.data;
return Array.isArray(data) ? data : [];

// Component selector - validate Redux state
const rolesData = useAppSelector(state => state.roles.items);
const roles = Array.isArray(rolesData) ? rolesData : [];
```

### 9. Documentation Requirements
- Update BLUEPRINT_REACT_REFERENCE.md with actual exported components
- Update BLUEPRINT_REACT_CORRECT_PATTERNS.md with layout component patterns
- Document which BDL components map to which Blueprint components
- List non-existent components to avoid
- Create examples for each layout pattern

### 10. Maintenance of This Skill
- Keep reference files updated with Blueprint releases
- Update this SKILL.md if new patterns are discovered
- Document any additional mistakes found
- Validate all pattern examples against storybook
- Review layout component patterns quarterly

### 11. Page Structure & Content Fidelity (CRITICAL!)
- **Section headings MUST match MCA1 constants exactly** — read `constants.js` FIRST, use exact text
- **Section ordering MUST match MCA1 EJS template ordering** — do not reorganize or merge sections
- **If MCA1 has a separator** (`<mca-separator>`), maintain visual separation in MCA2 (use separate `<Section>` or `<SectionItem>`)
- **If MCA1 shows a field directly** (no radio gate), MCA2 MUST show it directly — NEVER add enable/disable toggles
- **If MCA1 has a radio/toggle BEFORE a field**, MCA2 must replicate that exact pattern
- **NEVER add UI controls that don't exist in the source** — no invented radios, toggles, or conditional wrappers
- **NEVER rename, rephrase, or "improve" section titles** — use the exact constant values
- **ALWAYS cross-reference the EJS template structure** against the generated MCA2 output before finalizing
- **Read `constants.js` heading values** and use them verbatim (e.g., `NOTIFICATION_HEAD_INFO: 'Transaction notifications'` → `<Type element="h2">Transaction notifications</Type>`)

**Pattern — Heading Preservation**:
```typescript
// MCA1 constants.js:
// NOTIFICATION_HEAD_INFO: 'Transaction notifications'
// NOTIFICATION_HEAD_BAL: 'Balance notifications'

// MCA2 CORRECT:
<Type element="h2">Transaction notifications</Type>   // ✅ Exact match
<Type element="h2">Balance notifications</Type>        // ✅ Exact match

// MCA2 WRONG:
<Type element="h2">Current Account Alerts</Type>       // ❌ Invented name
<Type element="h2">Alert Configuration</Type>          // ❌ Paraphrased
```

**Pattern — Field Visibility Preservation**:
```typescript
// MCA1: <mca-input type="money" id="largeCrdAlert">Large payment in</mca-input>
// (No radio gate — direct input, always visible for current accounts)

// MCA2 CORRECT — direct input, always visible:
<FormItem label={<Type>Large payment in</Type>} render={(props) => <FormInput {...props} />} />

// MCA2 WRONG — added non-existent radio gate:
<FormMultiItem label="Large credit alert" render={...}>
  <FormRadio label="Yes" />   // ❌ DOESN'T EXIST IN MCA1
  <FormRadio label="No" />    // ❌ DOESN'T EXIST IN MCA1
</FormMultiItem>
{enabled && <FormInput />}    // ❌ Gated by invented control
```

### Mistake 22: API Service Initialization Not Called in MCA2 (Critical!)
❌ WRONG - API services not initialized before Redux thunks run:
```typescript
// src/App.tsx - TOO LATE to initialize here
function App() {
  useEffect(() => {
    // This runs AFTER Dashboard component already tried to dispatch thunks!
    initializeApiServices(props.api);
  }, []);

  return (
    <MemoryRouter>
      <Dashboard />  // Dashboard useEffect fires first, dispatches Redux thunks
    </MemoryRouter>
  );
}

// Result: Redux thunks try to use uninitialized API services
// Error: "API services not initialized" or "api.roles is undefined"
// Dropdowns remain empty, no data loads
```

✅ CORRECT - Initialize in Entry component BEFORE App renders:
```typescript
// src/Entry.tsx - Correct location
import { initializeApiServices } from './api/endpoints';

function Entry(props: any): React.ReactElement {
  useEffect(() => {
    // Initialize BEFORE App renders
    if (props.api) {
      initializeApiServices(props.api);
    }
  }, [props.api]);

  return (
    <ErrorBoundary FallbackComponent={ErrorFallbackComponent}>
      <React.Suspense fallback={<div>Loading...</div>}>
        <App {...props} />  {/* App now has initialized services */}
      </React.Suspense>
    </ErrorBoundary>
  )
}

// Result:
// 1. Entry.tsx initializes API services
// 2. App renders with initialized services
// 3. Dashboard dispatches thunks - services are ready
// 4. Dropdowns populate with data correctly
```

**Why This Matters in MCA2**:
- MCA2 passes ApiMCA instance to the launch function
- Redux thunks in Dashboard expect API services to be initialized
- If initialization happens too late, thunks fail silently or throw errors
- Entry component is rendered before App, so it's the perfect place

**Initialization Pattern** (in `src/api/endpoints.ts`):
```typescript
let apiInstance: any;

export const initializeApiServices = (api: any) => {
  apiInstance = api;
  // This allows Redux thunks to use: apiInstance.roles.fetchAll(), etc.
};

export const getApiInstance = () => apiInstance;

// In Redux thunks:
export const fetchRoles = createAsyncThunk('roles/fetchRoles', async () => {
  const api = getApiInstance();
  const response = await api.roles.fetchAll();
  return response;
});
```

**Common Symptoms of Missing Initialization**:
- ❌ Dropdowns are empty (no role/service/parameter data)
- ❌ No API calls are made (network tab shows no requests)
- ❌ Redux state remains as initial values (items: [])
- ❌ Console errors about "Cannot read property 'roles' of undefined"
- ❌ Loading indicators show but never complete

**Verification Checklist**:
- ✅ Entry.tsx has useEffect with props.api initialization
- ✅ initializeApiServices() is called before App renders
- ✅ Redux thunks can access api.roles, api.services, api.parameters
- ✅ Dashboard useEffect dispatches fetchRoles/fetchServices/fetchParameters
- ✅ Dropdowns populate with data on page load
- ✅ No "API services not initialized" errors in console

### Mistake 23: API Response Structure Not Validated (Runtime errors!)
❌ WRONG - Assuming API response.data is always correct structure:
```typescript
// Dashboard.tsx - Assuming roles is always an array
const roles = useAppSelector(state => state.roles.items);

// If API returns unexpected structure (e.g., response.data is object, null, or undefined):
{roles.map(role => (
  <option key={role.id}>{role.name}</option>
))}
// Result: "TypeError: roles.map is not a function" - UI crashes!
```

❌ WRONG - API services not validating array structure:
```typescript
// services.ts - Not checking if data is actually an array
fetchAll: async (): Promise<Role[]> => {
  const response = await api.service.call('fetchAllRoles');
  return response.data || [];  // What if response.data is an object?
}
```

✅ CORRECT - Defensive programming with array validation:
```typescript
// Dashboard.tsx - Always ensure data is array
const rolesData = useAppSelector(state => state.roles.items);
const roles = Array.isArray(rolesData) ? rolesData : [];

// Now safe to map
{roles.map(role => (
  <option key={role.id}>{role.name}</option>
))}
```

✅ CORRECT - API services validate response structure:
```typescript
// services.ts - Check if data is actually an array
fetchAll: async (params?: FetchAllRolesRequest): Promise<Role[]> => {
  const response = await api.service.call('fetchAllRoles', params);
  const data = response?.data;
  // Ensure we always return an array
  return Array.isArray(data) ? data : [];
}
```

**Why This Matters**:
- API responses might have unexpected structure (nested arrays, objects, null)
- Redux thunks might not properly validate response data
- UI components assume `Array.isArray()` before calling `.map()`
- One unexpected response structure crashes the entire component

**Pattern to Follow**:
1. **In API services**: Always validate that array methods return arrays
2. **In Redux state selectors**: Use defensive checks before mapping
3. **In components**: Never assume data structure - always validate

**Defensive Programming Checklist**:
- ✅ Array methods always return arrays (never undefined/null/objects)
- ✅ Component data selectors check `Array.isArray()` before using
- ✅ Components handle both loaded and empty states gracefully
- ✅ API response validation at service layer (first line of defense)
- ✅ Component-level validation (second line of defense)

### Mistake 24: Including `/api/router` prefix in process.json URIs (Framework adds it automatically!)
❌ WRONG - Including `/api/router` prefix in process.json endpoint URIs:
```json
// process.json
{
  "endpoints": {
    "fetchAllRoles": {
      "uri": "/api/router/scp/roles",  // ❌ WRONG - /api/router is added by the framework
      "method": "GET"
    }
  }
}

// Result: Framework prepends /api/router, making the actual call to /api/router/api/router/scp/roles
// Result: 404 errors, empty responses, broken API calls
```

✅ CORRECT - Omit `/api/router` prefix; the MCA2 framework adds it automatically:
```json
// process.json
{
  "endpoints": {
    "fetchAllRoles": {
      "uri": "/scp/roles",  // ✅ CORRECT - framework prepends /api/router at runtime
      "method": "GET"
    }
  }
}

// Result: Framework makes call to /api/router/scp/roles
// Result: Mock server and backend respond correctly
// Result: Dropdowns populated with data
```

**Important**: The mock server (mockServer/middleware.js) still needs the full `/api/router` prefix because the Eagle dev server proxies requests through the same path the framework produces at runtime:
```javascript
// mockServer/middleware.js
server.get('/api/router/scp/roles', (req, res) => {
  res.json({ roles: [...] });
});
```

**Why This Matters**:
- MCA2 Api.service.call() reads URIs from process.json and automatically prepends `/api/router`
- If you include `/api/router` in process.json, the prefix is doubled and requests go to the wrong path
- Redux thunks may execute, but API responses are empty or 404
- UI shows no errors, but dropdowns/data remain empty

**Debugging Steps**:
1. Open Network tab in browser DevTools
2. Check the actual request URL being made
3. If URL contains `/api/router/api/router/...`: Remove `/api/router` from process.json URIs
4. Ensure mockServer/middleware.js paths include the full `/api/router` prefix
5. Verify response status is 200/201 (not 404)

**Verification**:
- ✅ Network tab shows API calls to `/api/router/...` (single prefix, not doubled)
- ✅ API response includes data (not error)
- ✅ Response status is 200/201 (not 404)
- ✅ Dropdowns/lists populated after Redux state updates

### Mistake 25: Using Plain HTML Radio Buttons Instead of FormMultiItem + FormRadio (CRITICAL!)
❌ WRONG - Using plain HTML `<input type="radio">` with `<label>` wrappers:
```typescript
// WRONG - Plain HTML radios lose Blueprint styling, accessibility, and form integration
<FormItem
  label={<Type>Switch type</Type>}
  render={() => (
    <Arrange>
      <label>
        <input type="radio" name="switchType" value="Full" checked={value === 'Full'} onChange={handler} />
        <Type> Full Switch</Type>
      </label>
      <label>
        <input type="radio" name="switchType" value="Partial" checked={value === 'Partial'} onChange={handler} />
        <Type> Partial Switch</Type>
      </label>
    </Arrange>
  )}
/>
```

✅ CORRECT - Use `FormMultiItem` with `FormRadio` components:
```typescript
// CORRECT - FormMultiItem wraps radio groups, FormRadio provides Blueprint styling
// MUST spread {...renderProps} at the end of each FormRadio
<FormMultiItem
  label={<Type>Switch type</Type>}
  layout="inline-md-up"
  render={(renderProps) => (
    <>
      <FormRadio name="switchType" value="Full" label="Full Switch" checked={value === 'Full'} onChange={handler} {...renderProps} />
      <FormRadio name="switchType" value="Partial" label="Partial Switch" checked={value === 'Partial'} onChange={handler} {...renderProps} />
    </>
  )}
/>
```

**Why This Matters**:
- BDL `<mca-radios>` + `<mca-radio>` map to `FormMultiItem` + `FormRadio`, NOT to HTML `<input type="radio">`
- `FormMultiItem` (not `FormItem`) is designed for wrapping multiple form controls under a single label
- `FormRadio` uses `label` prop for the radio label text, NOT children
- `{...renderProps}` MUST be spread at the end of each `FormRadio` for accessibility (aria attributes)
- `layout="inline-md-up"` gives horizontal layout (equivalent to BDL `align="horizontal"`)
- Omit `layout` prop for vertical stacking (default)
- `FormMultiItem` does NOT support `id` prop — set `id` on individual `FormRadio` instead
- Always check the mapping files (BDL_RADIO_MAPPING.md, BDL_CHECKBOX_MAPPING.md) before migrating form controls — do NOT assume plain HTML equivalents

**Reference**: See `mappings/BDL_RADIO_MAPPING.md` for the complete mapping table.

### Mistake 26: Passing Plain Strings to FormItem/FormMultiItem `error` Prop (Must Wrap in Type!)
❌ WRONG - Passing error message as a plain string:
```typescript
// WRONG - Plain string renders without Blueprint styling and error color
<FormItem
  label={<Type>Account number</Type>}
  error={errors.accountNumber}
  render={(props) => (
    <FormInput {...props} value={value} onChange={handler} />
  )}
/>
```

✅ CORRECT - Wrap in `<Type color="error">` with a falsy guard:
```typescript
// CORRECT - Error text styled with Blueprint Type component in error color
<FormItem
  label={<Type>Account number</Type>}
  error={errors.accountNumber && <Type color="error">{errors.accountNumber}</Type>}
  render={(props) => (
    <FormInput {...props} value={value} onChange={handler} />
  )}
/>
```

**Why This Matters**:
- The `error` prop on `FormItem` and `FormMultiItem` accepts `ReactNode`, not just `string`
- Plain strings render without the correct error typography (color, weight, size)
- Wrapping in `<Type color="error">` ensures consistent Barclays Design Language error styling
- The `&&` guard is critical: when the error value is `undefined`/falsy, it stays falsy so the error slot is not rendered at all
- This applies to ALL form wrapper components: `FormItem`, `FormMultiItem`

**Pattern**:
```typescript
error={errorValue && <Type color="error">{errorValue}</Type>}
```

### Mistake 27: Using Non-Existent Icons from BDL When Migrating to Blueprint (Blueprint Icons Are Limited!)
❌ WRONG - Assuming BDL icons exist in Blueprint-React:
```typescript
// Spinner icon (used in LoadingSpinner component)
<Icon icon="spinner" />                    // DOESN'T EXIST in Blueprint
<div className={styles.spinner}></div>    // Custom CSS animation workaround

// Inbox icon (used in EmptyState component)
<Icon icon="inbox" />                      // DOESN'T EXIST in Blueprint
<Icon icon="inbox-full" />                 // DOESN'T EXIST either
```

✅ CORRECT - Use Blueprint-Native Alternatives:
```typescript
// Spinner → Use dedicated Loading component (BEST CHOICE)
import { Loading } from '@barclays/blueprint-react';
<Loading size="lg" shape="circle" ariaLabel="Loading" />

// Inbox → Use mail icon (closest alternative for inbox-like contexts)
import { Icon } from '@barclays/blueprint-react';
<Icon icon="mail" size="xl" style={{ color: '#999', marginBottom: '1rem' }} />
```

**Why This Matters During Migration**:
- BDL has many icons that DON'T exist in Blueprint-React
- Blueprint is a more minimal icon library than BDL
- Direct icon name mapping won't work - you need to find alternatives
- For spinners: Blueprint provides dedicated Loading component (better UX, native animations)
- For empty states: Choose semantically similar icons (document = no content)

**Icons That Don't Exist in Blueprint-React**:
| BDL Icon | Status | Blueprint Alternative |
|----------|--------|----------------------|
| `spinner` | ❌ MISSING | Use `<Loading>` component |
| `inbox` | ❌ MISSING | Use `mail` icon |
| `inbox-full` | ❌ MISSING | Use `mail` icon |
| `tick-circle` | ❌ MISSING | Use `tick` icon |
| `cross-circle` | ❌ MISSING | Use `dismiss` icon |
| `cross` | ❌ MISSING | Use `dismiss` icon |
| `info-circle` | ❌ MISSING | Use `info` icon |
| `print` | ❌ MISSING | Use `download` icon or omit |
| `camera` | ❌ MISSING | Omit or use custom SVG |
| `external` | ❌ MISSING | Use `chevron-right` for link indicators |
| `document` | ❌ MISSING | Use `mail` for inbox-like contexts |

**How to Find Correct Icons**:
1. ❌ **WRONG**: Assume BDL icon name works in Blueprint
2. ✅ **CORRECT**: Check Blueprint storybook for available icons
3. ✅ **CORRECT**: Search for semantically similar alternatives if exact match not found
4. ✅ **CORRECT**: For spinners, use dedicated `<Loading>` component instead of icons
5. ✅ **CORRECT**: For specific cases like empty states, choose representative icons

**Real-World Scenario**:
During MCA2 React migration:
- LoadingSpinner.tsx originally tried to use `<Icon icon="spinner" />` + custom CSS
- This failed at build time (icon doesn't exist)
- Solution: Replaced with `<Loading size="lg" shape="circle" ariaLabel="Loading" />`
- Result: Native animation, proper accessibility, no custom CSS needed

- EmptyState.tsx originally tried to use `<Icon icon="inbox" />`
- This failed at build time (icon doesn't exist)
- Solution: Replaced with `<Icon icon="mail" size="xl" />`
- Result: Semantically correct empty state indicator

**Common Mistakes When Migrating Icons**:
- ❌ Trying to use exact BDL icon names in Blueprint
- ❌ Creating custom CSS animations instead of using `<Loading>` component
- ❌ Not checking Blueprint storybook for available icons first
- ❌ Assuming all "-circle" variants exist (they don't - use base names)

**Prevention Checklist**:
- ✅ Before adding an Icon component in MCA2, check Blueprint storybook
- ✅ If icon doesn't exist, search for semantic alternative
- ✅ For loading indicators, ALWAYS use `<Loading>` component (not Icon + CSS)
- ✅ For empty states, use representative icons (document, files, list-view, etc)
- ✅ Test at build time to catch missing icons early

**Reference**: See BDL_TO_BLUEPRINT_REACT.md Section 8 and Mistakes 15-16 for complete icon guidance

### Mistake 28: Renaming Section Headings Instead of Preserving MCA1 Constants (CRITICAL!)
❌ WRONG - Paraphrasing, "improving", or inventing section headings:
```typescript
// MCA1 constants.js has: NOTIFICATION_HEAD_INFO: 'Transaction notifications'
// MCA1 constants.js has: NOTIFICATION_HEAD_BAL: 'Balance notifications'

// Agent generated (WRONG):
<Type element="h2">Current Account Alerts</Type>      // ❌ Invented name
<Type element="h2">Alert Configuration</Type>         // ❌ Paraphrased
<Type element="h2">Account Settings</Type>            // ❌ Made up
```

✅ CORRECT - Read constants.js FIRST, use exact text values:
```typescript
// Step 1: Read MCA1 constants/constants.js
// Found: NOTIFICATION_HEAD_INFO: 'Transaction notifications'
// Found: NOTIFICATION_HEAD_BAL: 'Balance notifications'
// Found: HEADING_PHONESETTING: 'Phone Settings'

// Step 2: Use EXACT text in MCA2:
<Type element="h2">Transaction notifications</Type>    // ✅ Exact match
<Type element="h2">Balance notifications</Type>        // ✅ Exact match
<Type element="h2">Phone Settings</Type>               // ✅ Exact match
```

**Why This Matters**:
- Section headings are part of the UI contract — end-to-end tests assert on them
- Regression test scripts validate specific text on screen
- Renaming breaks existing test automation without any functional benefit
- Users familiar with MCA1 expect the same section names in MCA2

**Prevention**:
1. ✅ Read `constants/constants.js` as the FIRST step of migration (Step 1a)
2. ✅ Create a heading inventory: constant name → exact text value
3. ✅ Use the inventory as a checklist when generating page components
4. ✅ After generating code, grep for section headings and cross-reference against inventory
5. ❌ NEVER use your own description of what a section does as its heading

### Mistake 29: Adding Enable/Disable Radios Where MCA1 Has Direct Inputs (CRITICAL!)
❌ WRONG - Adding a yes/no radio gate before an input that is always visible in MCA1:
```typescript
// MCA1 EJS has this (direct input, NO radio gate):
// <mca-input type="money" id="largeCrdAlert" name="largeCrdAlert">
//     Large payment in
// </mca-input>

// Agent generated (WRONG - invented radio toggle):
<FormMultiItem label="Large credit alert" render={...}>
  <FormRadio label="Yes" value="yes" />    // ❌ DOESN'T EXIST IN MCA1!
  <FormRadio label="No" value="no" />      // ❌ DOESN'T EXIST IN MCA1!
</FormMultiItem>
{formValues.largeCreditEnabled === 'yes' && (
  <FormInput id="input-large-credit-threshold" />  // ❌ Gated by invented control
)}
```

✅ CORRECT - If MCA1 shows a direct input (no preceding radio), migrate as direct input:
```typescript
// MCA1: <mca-input type="money" id="largeCrdAlert">Large payment in</mca-input>
// This is a DIRECT input — always visible, no radio gate

// MCA2 CORRECT:
<FormItem
  label={<Type>Large payment in</Type>}
  id="field-large-credit"
  render={(props) => (
    <FormInput
      {...props}
      type="text"
      inputMode="decimal"
      value={formValues.largeCreditThreshold}
      onChange={(e) => handleFieldChange('largeCreditThreshold', e.target.value)}
      placeholder="£0.00"
      id="input-large-credit-threshold"
      name="largeCrdAlert" />
  )}
/>
```

**How to Determine if a Field Has a Radio Gate in MCA1**:
1. Look at the EJS template — is there a `<mca-radios>` element directly BEFORE or wrapping the input?
2. If YES → migrate with `<FormMultiItem>` + `<FormRadio>` + conditional `<FormInput>`
3. If NO → migrate as a direct `<FormItem>` + `<FormInput>` (always visible)

**Examples from Real MCA1 Code**:
| MCA1 Pattern | Has Radio Gate? | MCA2 Pattern |
|---|---|---|
| `<mca-input type="money" id="largeCrdAlert">` | NO | Direct `<FormItem>` + `<FormInput>` |
| `<mca-input type="money" id="largeDbtAlert">` | NO | Direct `<FormItem>` + `<FormInput>` |
| `<mca-radios id="paynopay">` + `<mca-radio>` | YES | `<FormMultiItem>` + `<FormRadio>` |
| `<mca-radios id="intrchangeRadio">` + `<mca-radio>` | YES | `<FormMultiItem>` + `<FormRadio>` |
| `<mca-combobox id="mntActBalAlert">` | NO | Direct `<FormItem>` + `<FormSelect>` |

**Why This Matters**:
- Adding non-existent radios changes the user flow (extra clicks required)
- Regression tests assert that inputs are immediately visible, not hidden behind a toggle
- It creates a different data model (enabled/disabled state that MCA1 doesn't have)
- The API contract expects values directly, not enabled+value pairs
- UI density changes — MCA1 shows compact forms, MCA2 becomes bloated with extra controls

**Prevention Checklist**:
- ✅ For EVERY form field, check the EJS: is there a `<mca-radios>` preceding it?
- ✅ If no radio exists, render the field directly (always visible)
- ✅ If a radio exists, replicate the exact radio options (yes/no, on/off, etc.)
- ✅ After generating code, count form controls and compare to MCA1 — should be the same
- ❌ NEVER add "convenience" toggles that MCA1 doesn't have
- ❌ NEVER assume a money/threshold input "should" have an enable/disable radio

### Mistake 30: Omitting `size` and `marginBottom` Props on Heading Type Components (CRITICAL!)
❌ WRONG — Heading without explicit `size` renders at default paragraph size (visually indistinguishable from body text):
```typescript
// Agent generated (WRONG — no size, no spacing):
<Type element="h1">Page Title</Type>
<Type element="h2">Section Heading</Type>
<Type element="h3">Card Heading</Type>
<Type element="p">Body text follows immediately with no spacing</Type>

// Also WRONG — mismatched sizes (h2 bigger than h1):
<Type element="h1" size="lg">Title</Type>
<Type element="h2" size="2xl">Subtitle</Type>
```

✅ CORRECT — Every heading MUST have an explicit `size` prop following the canonical mapping, and a `marginBottom` for spacing:
```typescript
<Type element="h1" size="3xl" marginBottom="lg">Page Title</Type>
<Type element="h2" size="2xl" marginBottom="md">Section Heading</Type>
<Type element="h3" size="xl" marginBottom="sm">Subsection Heading</Type>
<Type element="h4" size="lg" marginBottom="sm">Card Heading</Type>
<Type element="h5" size="md" marginBottom="xs">Group Label</Type>
<Type element="h6" size="sm" marginBottom="xs">Minor Heading</Type>
<Type element="p" marginBottom>Body text with proper spacing below.</Type>
```

**Canonical Heading Size Mapping (MEMORIZE THIS):**

| Element | Size Prop | marginBottom | Use Case |
|---------|-----------|--------------|----------|
| `h1` | `3xl` | `lg` | Page title (one per page) |
| `h2` | `2xl` | `md` | Section heading |
| `h3` | `xl` | `sm` | Subsection / card heading |
| `h4` | `lg` | `sm` | Card heading / group title |
| `h5` | `md` | `xs` | Group label / minor section |
| `h6` | `sm` | `xs` | Smallest heading |
| `p` | (default) | `true` | Body paragraph |

**Why This Matters:**
- Without explicit `size`, all headings render at the same default size — the page has NO visual hierarchy
- Users cannot distinguish page titles from section headings from body text
- Regression tests that check visual layout or screenshot comparisons will fail
- Accessibility tools rely on heading hierarchy being visually reinforced
- Missing `marginBottom` causes headings to sit flush against content below, making the page feel cramped

**Common Patterns That Go Wrong:**
1. Agent generates `<Type element="h2">` without size → looks like a `<p>` tag
2. Agent applies same size to all heading levels → no hierarchy
3. Agent uses `weight="bold"` as a substitute for size → still renders at default size, just bold
4. Agent adds `size` but omits `marginBottom` → correct size but no spacing

**Prevention Checklist:**
- ✅ Every `<Type element="hN">` MUST have an explicit `size` prop from the table above
- ✅ Every heading MUST have `marginBottom` (use the value from the table)
- ✅ Sizes must be monotonically decreasing: h1 ≥ h2 ≥ h3 ≥ h4 ≥ h5 ≥ h6
- ✅ After generating code, visually scan for any `<Type element="h` without `size=`
- ❌ NEVER rely on `element` alone to provide visual sizing — it only sets the semantic HTML tag
- ❌ NEVER use `weight="bold"` as a substitute for the `size` prop

### Mistake 31: Missing Form Wrapper and Incorrect FormSection Spacing (CRITICAL!)

❌ WRONG — Form fields without `<Form>` wrapper, or consecutive FormSections without `paddingTop={false}`:
```typescript
// Agent generated (WRONG — no Form wrapper):
<div>
  <FormSection>
    <FormItem label={<Type>Name</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>
</div>

// Agent generated (WRONG — missing paddingTop={false} on second section):
<Form onSubmit={handleSubmit}>
  <FormSection head="Section 1">
    <FormItem label={<Type>Field A</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>
  <FormSection head="Section 2">  {/* Missing paddingTop={false}! */}
    <FormItem label={<Type>Field B</Type>} render={(props) => <FormInput {...props} />} />
  </FormSection>
</Form>

// Agent generated (WRONG — custom subtext instead of description prop):
<FormItem label={<Type>Sort Code</Type>} render={(props) => <FormInput {...props} />} />
<Type size="sm">Enter your 6-digit sort code</Type>
```

✅ CORRECT — Form wrapper, paddingTop={false} on subsequent sections, description prop for subtext:
```typescript
<Form onSubmit={handleSubmit}>
  {/* First section — default padding */}
  <FormSection head="Account Details">
    <FormItem
      label={<Type>Sort Code</Type>}
      description={<Type>Enter your 6-digit sort code without dashes</Type>}
      render={(props) => <FormInput {...props} type="text" />}
    />
  </FormSection>

  {/* Second section — paddingTop={false} to prevent double spacing */}
  <FormSection head="Transfer Details" paddingTop={false}>
    <FormItem
      label={<Type>Amount</Type>}
      description={<Type>Enter the transfer amount in GBP</Type>}
      render={(props) => <FormInput {...props} type="number" />}
    />
  </FormSection>

  {/* Actions section — paddingTop={false} */}
  <FormSection paddingTop={false}>
    <ButtonGroup>
      <Button type="submit" variant="primary">Submit</Button>
    </ButtonGroup>
  </FormSection>
</Form>
```

**Three Rules (MEMORIZE):**

| Rule | What | Why |
|------|------|-----|
| 1 | All forms MUST be wrapped in `<Form>` from Blueprint-React | Manages accessibility, validation state propagation |
| 2 | Second+ `<FormSection>` MUST use `paddingTop={false}` | Prevents double vertical spacing between sections |
| 3 | Field helper text MUST use `description` prop on `<FormItem>` | Proper aria-describedby linking, consistent styling |

**Common Patterns That Go Wrong:**
1. Agent uses plain `<form>` HTML element or `<div>` wrapper instead of Blueprint `<Form>`
2. Agent places headings, divs, or layout elements directly inside `<Form>` (only FormSection/FormItem/FormMultiItem allowed)
3. Agent omits `paddingTop={false}` on consecutive FormSections, causing excessive whitespace
4. Agent creates custom `<Type size="sm">` or `<p>` elements for subtext instead of using `description` prop
5. Agent imports conflicting Form from Formik instead of Blueprint-React

**Prevention Checklist:**
- ✅ Every form uses `<Form>` from `@barclays/blueprint-react`
- ✅ Direct children of `<Form>` are only `FormSection`, `FormItem`, or `FormMultiItem`
- ✅ All `<FormSection>` after the first one have `paddingTop={false}`
- ✅ BDL `helper-text` attributes are migrated to `description` prop wrapped in `<Type>`
- ❌ NEVER use plain `<form>`, `<div>`, or Formik `<Form>` as the form wrapper
- ❌ NEVER place raw headings/divs directly inside `<Form>`
- ❌ NEVER create custom subtext elements — use `description` prop

**See also:** [FORM_LAYOUT_PATTERNS.md](guides/FORM_LAYOUT_PATTERNS.md)

### Mistake 32: Plain Text in Table Cells Without Type Wrapper and Full-Size Buttons in Tables (CRITICAL!)

❌ WRONG — Raw text directly inside `<td>` without `<Type>` wrapper, and default-size buttons:
```typescript
<Table equalPadding headingVariant="default">
  <thead>
    <tr>
      <th>Name</th>           {/* WRONG — bare text in th */}
      <th>Amount</th>         {/* WRONG — bare text in th */}
      <th>Actions</th>
    </tr>
  </thead>
  <tbody>
    {rows.map(row => (
      <tr key={row.id}>
        <td>{row.name}</td>          {/* WRONG — no Type wrapper */}
        <td>{row.amount}</td>        {/* WRONG — no Type wrapper */}
        <td>
          <Button variant="secondary" onClick={() => handleEdit(row.id)}>
            Edit
          </Button>                  {/* WRONG — missing size="sm" */}
        </td>
      </tr>
    ))}
  </tbody>
</Table>
```

✅ CORRECT — All text cells use `<Type element="td/th">`, all buttons use `size="sm"`:
```typescript
<Table equalPadding headingVariant="default">
  <thead>
    <tr>
      <Type element="th">Name</Type>
      <Type element="th">Amount</Type>
      <Type element="th">Actions</Type>
    </tr>
  </thead>
  <tbody>
    {rows.map(row => (
      <tr key={row.id}>
        <Type element="td">{row.name}</Type>
        <Type element="td">{row.amount}</Type>
        <td>
          <Button variant="secondary" size="sm" onClick={() => handleEdit(row.id)}>
            Edit
          </Button>
        </td>
      </tr>
    ))}
  </tbody>
</Table>
```

**Table Cell Content Decision Table (MEMORIZE):**

| Cell Content | Pattern | Example |
|---|---|---|
| Text/data only | `<Type element="td">{value}</Type>` | `<Type element="td">{row.name}</Type>` |
| Header text | `<Type element="th">Label</Type>` | `<Type element="th">Status</Type>` |
| Button(s) only | `<td><Button size="sm" .../></td>` | `<td><Button size="sm" variant="secondary">Edit</Button></td>` |
| Text + Button | `<td><Type>{label}</Type> <Button size="sm" .../></td>` | Mixed content cell |
| FormRadio | `<Type element="td"><FormRadio .../></Type>` | Radio selection column |
| Formatted value | `<Type element="td">{formatCurrency(row.amount)}</Type>` | Formatted data |

**Rules (MANDATORY — apply to ALL migrated tables):**
1. **Type wrapping**: ALL text/data cells MUST use `<Type element="td">` or `<Type element="th">` — NEVER render bare text in raw `<td>`/`<th>` tags. This ensures Blueprint typography tokens (font-size, line-height, color) are applied consistently.
2. **Button sizing**: ALL `<Button>` components inside `<td>` or `<th>` MUST include `size="sm"`. Default-size buttons are too tall for table rows and break visual density.
3. **Interactive-only cells**: When a cell contains ONLY interactive components (Button, Link, Loading), use raw `<td>` wrapping those components — the components handle their own styling.
4. **Mixed content cells**: When a cell has both text and interactive components, wrap text in `<Type>` inside a raw `<td>`.

**IMPORTANT — Exception to Mistake 20:**
Mistake 20 says "never mix button sizes — use default size for all buttons." That rule applies to **page-level** buttons (form actions, toolbar buttons). Inside table cells, `size="sm"` is MANDATORY. This is not a contradiction — it is a scoped exception: table context demands compact buttons.

---

### Mistake 33: Middleware Routes Using Endpoint Key Names Instead of process.json URIs (CRITICAL — 404s on ALL local dev API calls!)

❌ WRONG — Using endpoint key names as route paths in middleware.js:
```javascript
// mockServer/middleware.js
// process.json has: "preload": { "uri": "/scrub/batch/v1/preload", "method": "GET" }
// But developer uses the KEY NAME "preload" as the path:

server.get('/api/router/scrub/preload', (req, res) => res.json(mockData.preload));           // ❌ WRONG
server.post('/api/router/scrub/getUnassignedBatches', (req, res) => res.json(mockData.batches)); // ❌ WRONG
server.get('/api/router/scrub/getDashboardDetail', (req, res) => res.json(mockData.dashboard));  // ❌ WRONG

// Result: ALL API calls return 404 when running locally with npm run develop
// Result: Component tests (Playwright page.route) still pass — they bypass middleware entirely
// Result: Misleading "all tests pass" but app is completely broken locally
```

✅ CORRECT — Routes use `/api/router` + the actual `uri` value from process.json (with `{params}` → `:params`):
```javascript
// mockServer/middleware.js
// process.json: "preload": { "uri": "/scrub/batch/v1/preload", "method": "GET" }
// Route uses:  /api/router + uri from process.json

server.get('/api/router/scrub/batch/v1/preload', (req, res) => res.json(mockData.preload));                    // ✅ CORRECT
server.post('/api/router/scrub/batch/v1/unassignedbatch/:statusCode', (req, res) => res.json(mockData.batches)); // ✅ CORRECT
server.get('/api/router/midashboard/v1/dashboard', (req, res) => res.json(mockData.dashboard));                 // ✅ CORRECT
```

**The Rule:**
```
middleware.js route = "/api/router" + process.json endpoint uri (with {param} → :param)
```

**Why This Matters**:
- The MCA framework resolves endpoint keys → reads `uri` from process.json → prepends `/api/router` → makes HTTP request to that full path
- If middleware.js uses key names instead of URIs, the routes don't exist and Express returns 404
- Playwright component tests use `page.route()` which intercepts at browser level — they NEVER hit the dev server, so they can't catch this
- This creates a false sense of security: "all tests pass" but the app doesn't work

**Why It's Easy to Miss**:
- The validation agent (pre-v3.10) didn't check middleware routes
- The visual test agent uses isolated mocks — independent of middleware.js
- Build, lint, and TypeScript compilation all pass — it's a runtime-only failure
- The error is only visible when actually running `npm run develop` and using the app

**Debugging Steps**:
1. Run `npm run develop` and open browser DevTools → Network tab
2. Observe all API calls returning 404
3. Compare the URL in the network request (e.g., `/api/router/scrub/batch/v1/preload`) against middleware.js routes
4. If middleware.js has `/api/router/scrub/preload` instead → it's using the key name, not the URI

**Verification**:
- ✅ For EVERY endpoint in process.json, middleware.js has a route matching `/api/router` + `uri`
- ✅ HTTP methods match (GET in process.json → `server.get()`, POST → `server.post()`)
- ✅ Path parameters use Express `:param` syntax (e.g., `{statusCode}` → `:statusCode`)
- ✅ Running `npm run develop` → no 404s in Network tab

---

## Version History

### v3.10 (July 22, 2026) - MIDDLEWARE ROUTE URI MATCHING & SCREENSHOT VERIFICATION
- Added Mistake 33: Middleware routes using endpoint key names instead of process.json URIs
- Root cause: Transform/orchestrator agents wrote middleware.js routes as `/api/router/scrub/{endpointKey}` instead of `/api/router` + actual URI from process.json
- This was undetectable by component tests (Playwright page.route bypasses dev server) or validation agent (had no middleware check)
- Added Red Flag #16 to validation agent: Cross-reference middleware.js routes against process.json URIs
- Added Red Flag #17 to validation agent: Verify Playwright screenshots actually exist on disk
- Added Step 10.3 to orchestrator: Middleware smoke check after Phase 5
- Added Iron Rules 9-10 to visual test agent: Must verify screenshots exist before reporting success
- Impact: Prevents false "APPROVED" verdicts when dev server is completely broken

### v3.9 (July 20, 2026) - TABLE CELL CONTENT RULES
- Added Mistake 32: Plain text in table cells without Type wrapper and full-size buttons in tables
- Mistake 32 mandates `<Type element="td">` / `<Type element="th">` for all text content in tables
- Mistake 32 mandates `size="sm"` on all `<Button>` components inside table cells
- Updated Mistake 20 with explicit table exception note referencing Mistake 32
- Updated BDL_TABLE_MAPPING.md with "Iron Rules for Table Cells" section
- Updated mca1-transform-agent.md Step 2.5 with table-specific rules
- Updated SKILL.md Iron Rules and Common Pitfalls sections

### v3.8 (July 20, 2026) - FORM LAYOUT AND SECTION SPACING RULES
- Added Mistake 31: Missing Form wrapper and incorrect FormSection spacing
- Three critical rules: (1) Form wrapper mandatory, (2) paddingTop={false} on consecutive FormSections, (3) description prop for field subtext
- Created new guide: FORM_LAYOUT_PATTERNS.md with complete layout rules and migration checklist
- Updated BLUEPRINT_REACT_CORRECT_PATTERNS.md FormSection example with paddingTop and Form wrapper
- Component conflict table added to help avoid BDL/Legacy/Blueprint variant confusion

### v3.7 (June 25, 2026) - HEADING SIZE AND SPACING RULES
- Added Mistake 30: Omitting size and marginBottom on heading Type components
- Root cause: Agents generate `<Type element="hN">` without explicit size prop, causing all headings to render at default paragraph size with no visual hierarchy
- Fix: Canonical heading-to-size mapping table — every heading level has a required size and marginBottom value
- Impact: Prevents visually flat pages where headings are indistinguishable from body text
- Updated BDL_TYPOGRAPHY_MAPPING.md with correct canonical examples

### v3.6 (May 6, 2026) - PAGE STRUCTURE FIDELITY & FIELD VISIBILITY RULES
- Added Mistake 28: Renaming section headings instead of preserving MCA1 constants
- Added Mistake 29: Adding enable/disable radios where MCA1 has direct inputs
- Added Key Consideration #11: Page Structure & Content Fidelity (CRITICAL!)
- Added Step 1a: Constants & Headings Inventory (MANDATORY)
- Added Step 1b: Field Visibility Audit (MANDATORY)
- Root cause: During scp-ui-membershipandalerts migration, "Transaction notifications" section was renamed to "Current Account Alerts" and direct money inputs (largeCrdAlert, largeDbtAlert) were incorrectly gated behind invented yes/no radios
- Fix: Read constants.js first, use exact heading text, and match field visibility pattern from EJS templates
- Impact: Prevents regression test failures caused by renamed headings and changed field visibility

### v3.1 (March 25, 2026) - BLUEPRINT-REACT ICON ALTERNATIVES FOR IMPLEMENTATION
- Discovered during real MCA2 React component implementation phase
- **Issue 1**: Blueprint-React does NOT have a "spinner" icon
  - Original pattern: Using non-existent spinner icon with manual CSS animation
  - Solution: Use Blueprint's native `Loading` component instead
  - Implementation: `<Loading size="lg" shape="circle" ariaLabel="Loading" />`
  - File affected: LoadingSpinner.tsx
  - Reason: Loading component handles all animation and accessibility natively
  - Why not Icon: Loading is a dedicated component purpose-built for spinners

- **Issue 2**: Blueprint-React does NOT have an "inbox" icon
  - Original attempt: `<Icon icon="inbox" />` - doesn't exist in Blueprint
  - Solution: Use "mail" icon as alternative (closest to inbox semantics)
  - Implementation: `<Icon icon="mail" size="xl" style={{ color: '#999', marginBottom: '1rem' }} />`
  - File affected: EmptyState.tsx
  - Reason: mail icon is the closest valid Blueprint icon to inbox/message context
  - Note: `document` also does NOT exist in Blueprint — valid icons only from the exhaustive list

- **Impact on Mistakes 15-16**:
  - Reinforces Mistake 15 (Icon sizing): LoadingSpinner now uses Loading (no size prop needed, handled by component)
  - Reinforces Mistake 16 (Non-existent icon names): Both spinner and inbox are missing from Blueprint

- **Build Verification**: All components built successfully after icon fixes
- **Lesson**: Always check Blueprint storybook for actual available icons before implementing icon-based components
- **Updated Files**: LoadingSpinner.tsx, EmptyState.tsx now use correct Blueprint alternatives

### v3.4 (April 17, 2026) - ERROR PROP TYPE WRAPPING (CRITICAL)
- Added Mistake 26: FormItem/FormMultiItem `error` prop must be wrapped in `<Type color="error">`
- Pattern: `error={errorValue && <Type color="error">{errorValue}</Type>}`
- The `&&` guard prevents rendering an empty Type when the error is undefined
- Updated 5 mapping files to show correct error prop pattern: BDL_INPUT_MAPPING, BDL_FORM_CONTROLS_MAPPING, BDL_TEXTAREA_MAPPING, BDL_CHECKBOX_MAPPING, BDL_RADIO_MAPPING
- Added dedicated "Error Handling" section to BDL_RADIO_MAPPING.md
- Renumbered Mistake 26 (Icons) to Mistake 27

### v3.3 (April 17, 2026) - RADIO BUTTON MIGRATION PATTERN (CRITICAL)
- Added Mistake 25: Using plain HTML radio buttons instead of FormMultiItem + FormRadio
- BDL `<mca-radios>` + `<mca-radio>` must map to `FormMultiItem` + `FormRadio`, never plain HTML `<input type="radio">`
- Documented `FormMultiItem` API: `label` (required), `layout`, `render` with `renderProps` spread
- Documented `FormRadio` API: `name`, `value`, `label` prop (not children), `{...renderProps}` at end
- `FormMultiItem` does NOT have `id` prop — use `id` on individual `FormRadio` if needed
- Root cause: Mapping reference files (BDL_RADIO_MAPPING.md) were not consulted before generating code
- Lesson: ALWAYS check mapping files before migrating any BDL component — do not assume HTML equivalents
- Renumbered Mistake 25 (Icons) to Mistake 26

### v3.2 (April 17, 2026) - PROCESS.JSON URI PREFIX CORRECTION
- Updated Mistake 24: Corrected to reflect that `/api/router` prefix must NOT be included in process.json URIs
- The MCA2 framework automatically prepends `/api/router` to endpoint URIs at runtime
- Including `/api/router` in process.json causes a doubled prefix and 404 errors
- Mock server (middleware.js) still needs the full `/api/router` prefix in its route paths

### v3.0 (March 25, 2026) - ENDPOINT CONFIGURATION CRITICAL LESSON
- Added Mistake 24: API Endpoint URI Mismatch in process.json
- Documented silent failure when endpoints don't match actual API
- Provided debugging steps to identify mismatched endpoints
- Real-world scenario: No dropdowns, no Network calls, Redux thunks execute but fail silently
- Solution: Verify process.json URIs match actual API/mock paths

### v2.9 (March 24, 2026) - API RESPONSE VALIDATION & DEFENSIVE PROGRAMMING
- Added Mistake 23: API Response Structure Not Validated (Runtime errors!)
- Documented defensive array validation in API services
- Added defensive checks in components before using array methods
- Explained why API responses must be validated at service layer
- Provided defensive programming checklist
- Fixed Dashboard.tsx: Added Array.isArray() checks before .map()
- Fixed services.ts: Added array validation in all fetch methods (roles, services, parameters, business units)
- Build: 0 errors after defensive programming fixes

### v2.8 (March 24, 2026) - API SERVICE INITIALIZATION (CRITICAL FIX)
- Added Mistake 22: API Service Initialization Not Called in MCA2 (Critical!)
- Documented the critical pattern: Entry.tsx initialization BEFORE App renders
- Explained why initialization must happen in Entry component, not App component
- Listed common symptoms of missing initialization
- Provided verification checklist for API initialization
- Clarified Redux thunk pattern for accessing initialized API services
- All dropdowns now populate with data correctly after Entry initialization

### v2.7 (March 24, 2026) - LAYOUT NESTING & WHITESPACE OPTIMIZATION
- Added Mistake 21: Excessive nesting of layout components creating whitespace bloat
- Documented pattern to minimize SectionItem nesting (2-3 per Section max)
- Explained grouping of related content (title+form together, buttons separate)
- Fixed Dashboard.tsx: Consolidated SectionItems to reduce nesting from 3 per section to 2
- Reduced excessive whitespace throughout application

### v2.6 (March 24, 2026) - FORM LAYOUT & BUTTON SIZING
- Added Mistake 20: Form controls with inconsistent sizing (buttons too small, dropdowns cramped)
- Documented rules for consistent UI sizing
- Explained proper form width considerations (full width vs 50/50 vs 33/33)
- Clarified when to use Button size prop vs default size
- Fixed Dashboard.tsx: Removed size="sm" from all buttons, adjusted grid widths
- Added guidance on SectionItem spacing between forms and buttons

### v2.5 (March 24, 2026) - DASHBOARD STRUCTURE & FORM PATTERNS
- Added Mistake 17: Dashboard design doesn't match MCA1 homescreen structure
- Added Mistake 18: Creating custom selects instead of FormItem + FormSelect
- Added Mistake 19: Using invalid Grid.Col size values
- Documented MCA1 pattern: single unified management interface, not separate dashboards
- Clarified Blueprint FormItem + FormSelect pattern for form fields
- Documented valid 12-column Grid.Col sizes

### v2.4 (March 24, 2026) - ICON NAMES VALIDATION
- Added Mistake 16: Using non-existent icon names (e.g., "-circle" variants)
- Documented that Blueprint icons don't have "-circle" suffixes
- Icon guide consolidated into BDL_TO_BLUEPRINT_REACT.md Section 8
- Listed common BDL to Blueprint icon mappings
- Fixed MessageAlert.tsx: tick-circle → tick, cross-circle → dismiss

### v2.3 (March 24, 2026) - ICON SIZING REQUIREMENT
- Added Mistake 15: Icon component without size prop (icons render huge!)
- Documented Icon size recommendations by context (buttons=sm, alerts=md, etc)
- Clarified that icons MUST have size prop to avoid oversized rendering
- Added size validation to Mistake 12 Icon component section
- Valid sizes: xs, sm, md, lg, xl, 2xl, sm-and-md
- Practical context-based sizing guide for different UI components

### v2.2 (March 24, 2026) - COMPONENT PROP VALIDATION
- Added Mistakes 8-14: Component prop validation and usage errors
- Added Mistake 8: Invalid Type component props (element, color, marginTop)
- Added Mistake 9: Invalid margin props on layout components (Grid, Panel, Arrange)
- Added Mistake 10: Invalid Grid.Col size values (1of1 instead of 1of12)
- Added Mistake 11: Using divs instead of Type component for text
- Added Mistake 12: Icon component prop and size value errors
- Added Mistake 13: Alert component prop mapping (icon→media, onClose→onDismiss)
- Added Mistake 14: Not validating props against storybook before using
- Updated Key Considerations: Added critical point about component API validation

### v2.1 (March 24, 2026) - LAYOUT COMPONENTS PATTERN
- Added Layout Pattern requirement to critical patterns section
- Layout component patterns documented in BLUEPRINT_REACT_CORRECT_PATTERNS.md
- Added Mistake 7: Custom CSS for layout anti-pattern
- Added layout component guidance (Page, Grid, Arrange, Section, Panel, Navbar, Type, Box)
- Updated Key Considerations section 1, 3, 4
- Added section 4: Layout Components (CRITICAL)
- Added section 5: Custom Component Creation with layout guidance
- Updated Setup Phase deliverables to include layout patterns in BLUEPRINT_REACT_CORRECT_PATTERNS.md
- Clarified: Use Blueprint layout components instead of custom CSS

### v2.0 (March 24, 2026) - CRITICAL CORRECTIONS
- Added Blueprint-React pattern requirements section
- Added critical component composition patterns (FormItem, Dialog, Table, Button)
- Added common mistakes to avoid section
- Added CSS modules anti-pattern guidance
- Added component validation checklist
- Clarified storybook as authority for APIs
- Updated Step 3 to mandate storybook review
- Updated Step 6 with pattern requirements

### v1.0 (Initial Version)
- Initial skill definition with setup and migration phases

---

## Appendix: Legacy Pattern Conversion Guidance

MCA1 applications may contain **legacy jQuery-based components** alongside the `<mca-*>` web components. These require additional conversion steps.

### steal() → ES imports

```javascript
// MCA1 module loading
steal("scp/ui/common/vendor/chosen/chosen.js",
      "scp/ui/common/vendor/datatable/scp-datatable.js").then(function() {
  // Component initialization
});

// MCA2 equivalent
import { FormSelect, Table, Pagination } from '@barclays/blueprint-react';
```

**Rule:** Every `steal()` call is replaced by ES `import` statements. The module path indicates which Blueprint component to use — consult the relevant `LEGACY_*_MAPPING.md` file.

### jQuery Plugin → React State + Props

```javascript
// MCA1: imperative jQuery plugin
$("#myTable").scpTable({ paginate: { on: true }, sort: { on: true } });

// MCA2: declarative React with state
const [page, setPage] = useState(1);
const [sortCol, setSortCol] = useState(0);
// ... render <Table> + <Pagination> with state-driven behavior
```

**Rule:** jQuery plugin `options` objects map to React component props or `useState` hooks. Plugin method calls (`.open()`, `.close()`, `.val()`) become state setters.

### scp-* CSS Classes → Blueprint Props

| MCA1 CSS Pattern | React Equivalent |
|-----------------|-----------------|
| `class="scp-label"` | `<Type>` inside FormItem `label` prop |
| `class="scp-input-text"` | `<FormInput>` inside FormItem render |
| `class="scp-message-error"` | `<Alert status="error">` |
| `class="scp-button-regular"` | `<Button variant="secondary">` |
| `class="row"` + `class="*-columns"` | `<Grid>` + `<Grid.Col span={N}>` |
| `class="scp-hide"` | Conditional rendering (`{show && <Component />}`) |
| `class="scp-clickable"` | `onClick` handler on element |

**Rule:** Never transfer `scp-*` classes into React JSX. Every class maps to either a Blueprint component prop or a React pattern.

### Controller Event Bindings → React Handlers

```javascript
// MCA1: JMVC controller event binding
"#submit-btn click": function() { this.submitForm(); }
".scp-close-link click": function() { this.closeWindow(); }

// MCA2: React event handlers
<Button onClick={handleSubmit}>Submit</Button>
<Button variant="subtle" onClick={handleClose}><Icon icon="close" size="sm" /></Button>
```

**Rule:** JMVC controller event binding syntax (`"selector event": function`) becomes React synthetic event handlers (`onClick`, `onChange`, `onBlur`) directly on the JSX element.

### Reference Files

Full mapping details for each legacy component category:
- `mappings/LEGACY_AUTOCOMPLETE_MAPPING.md`
- `mappings/LEGACY_DIALOG_TOOLTIP_MAPPING.md`
- `mappings/LEGACY_DROPDOWN_MAPPING.md`
- `mappings/LEGACY_DATATABLE_MAPPING.md`
- `mappings/LEGACY_LABELS_MAPPING.md`
- `mappings/LEGACY_TYPOGRAPHY_MAPPING.md`
- `mappings/LEGACY_ACCORDION_TABS_MAPPING.md`
- `mappings/LEGACY_LAYOUT_MAPPING.md`
- `mappings/LEGACY_MISC_MAPPING.md`
- `mappings/LEGACY_CALENDAR_CUSTOM_MAPPING.md`

---

## Appendix: JMVC Controller Conversion Reference

MCA1 applications use JavaScriptMVC (NOT AngularJS). There is no `$scope` or `$inject`. Understanding the actual JMVC patterns is critical for accurate migration.

### Full Reference Guides

- **`guides/MCA1_APPLICATION_PATTERNS.md`** — Complete BaseController API surface, workflow.model() state management, callService() patterns, event delegation syntax, EJS template patterns (derived from 8 production MCA1 apps)
- **`guides/JMVC_TO_REACT_PATTERNS.md`** — Line-by-line conversion patterns for every JMVC construct to React equivalents (init→useEffect, proxy→arrows, resume→navigate, workflow.model→Redux, callService→RTK Query)

### Critical JMVC→React Conversions (Quick Reference)

| JMVC Pattern | React Equivalent |
|-------------|-----------------|
| `this.workflow.model("KEY", value)` | `dispatch(setKey(value))` (Redux) |
| `this.workflow.model("KEY")` | `useAppSelector(s => s.slice.key)` |
| `this.callService(n, e, payload).done(cb)` | `const [trigger] = useMutation(); await trigger(payload)` |
| `this.resume("step-name")` | `navigate('/step-name')` (MemoryRouter) |
| `this.proxy(fn)` | Arrow function `() => {}` (auto-bound) |
| `'#btn click': function(){}` | `onClick={handler}` on element |
| `'{workflow} EVENT': function(){}` | `useEffect` reacting to Redux state change |
| `this.element.html(template, data)` | Conditional JSX `{data && <Component />}` |
| `this.element.formParams()` | `getValues()` (React Hook Form) |
| `new Model(params); this.validate(model)` | Yup schema + `resolver` |
| `this.disable()` / `this.enable()` | `const [loading, setLoading] = useState()` |
| `WindowManager.launchWindow({type:'lightbox'})` | `<Dialog open={isOpen}>` |
| `WindowManager.closeWindow()` | `navigate('/')` or container callback |
| `$.Class.extend('constants', {}, {})` | `export const CONSTANTS = {...} as const` |
| `this.find('#id').getComponent().getValue()` | Controlled input `value` state |
| `this.find('#id').getComponent().enable(false)` | `disabled` prop |

### Iron Rules for JMVC Conversion

1. **Never search for `$scope` or `$inject`** — MCA1 uses JMVC, not Angular
2. **`this.proxy(fn)` is just `.bind(this)`** — Arrow functions eliminate this entirely
3. **`workflow.model()` is a flat key-value store** — Map keys to typed Redux slice fields
4. **`callService()` returns jQuery Deferred** — Convert to async/await with RTK Query
5. **Event delegation strings are implicit** — Each must become an explicit JSX event prop
6. **`.formParams()` only captures HTML inputs** — BDL `.getComponent()` values were collected separately; React controlled components unify this
7. **EJS `<% if %>` blocks** → JSX conditional rendering (`&&` or ternary)
8. **EJS `<% for %>` loops** → `.map()` with `key` prop

---

## Status
🟢 **UPDATED** - v3.9 includes table cell content rules (Mistake 32: Type wrapping + Button size="sm" in tables)
