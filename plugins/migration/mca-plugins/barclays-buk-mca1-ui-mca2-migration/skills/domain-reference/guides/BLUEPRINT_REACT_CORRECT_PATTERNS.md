# Blueprint-React Correct Component Patterns - Critical Corrections

**Date**: March 24, 2026
**Version**: 1.3.0
**Status**: CRITICAL - Corrects implementation errors in MCA2 project

## Executive Summary

The initial MCA2 implementation contains fundamental component usage errors. Many wrapped components (FormFieldWrapper, DialogHeader, TableCell, etc.) **do not exist** in Blueprint-React v1.3.0. This document provides the correct patterns for all commonly-used components.

## Critical Issues Found

| Issue | Impact | Severity |
|-------|--------|----------|
| FormField uses non-existent FormGroup/FormFieldWrapper/TextInput | All forms broken | CRITICAL |
| Dialog wrappers use non-existent DialogHeader/DialogContent/DialogFooter | All dialogs broken | CRITICAL |
| Table uses non-existent TableHead/TableBody/TableRow/TableCell | All tables broken | CRITICAL |
| Using non-existent Tooltip/Popover/Spinner | Build failure | CRITICAL |
| Button uses invalid variants (ghost, danger, tertiary) | Button styling broken | HIGH |

---

## 1. FORM COMPONENTS - CORRECT PATTERNS

### What EXISTS in Blueprint-React v1.3.0

```typescript
export {
  Form,              // Form wrapper
  FormSection,       // Grouped form section with optional heading
  FormItem,          // Form field container with label/error/description
  FormInput,         // Text input field
  FormTextarea,      // Textarea field
  FormSelect,        // Select dropdown
  FormCheckbox,      // Checkbox control
  FormRadio,         // Radio control
  FormButton,        // Specialized form button
  FormInputWithRange // Numeric input with range slider
}
```

### What DOES NOT EXIST (Remove from imports)

```typescript
❌ FormGroup           - Never existed
❌ FormFieldWrapper    - Never existed
❌ TextInput           - Never existed (use FormInput instead)
❌ TextArea            - Never existed (use FormTextarea instead)
❌ Select              - Never existed (use FormSelect instead)
❌ Option              - Never existed (use standard <option> tags)
❌ Tooltip             - Never existed (use PopupNav with click trigger, or native title attribute)
❌ Popover             - Never existed (use PopupNav with useRef + useState)
❌ Spinner             - Never existed (use Loading component)
❌ PageHeader          - Never existed (build custom with Section + Type)
❌ Empty               - Never existed (build custom empty state)
❌ ErrorBoundary       - Not a Blueprint component (use standard React ErrorBoundary pattern)
```

### CORRECT Pattern: FormItem with Render Function

**Key Concept**: FormItem uses a **render function**, NOT children wrapping.

```typescript
import { Form, FormItem, FormInput } from '@barclays/blueprint-react';

// CORRECT - Render function pattern
<Form>
  <FormItem
    label="Role Name"
    id="role-name"
    description="Enter a unique role identifier"
    error={validationError ? "Role name is required" : undefined}
    render={(props) => (
      <FormInput
        {...props}  // Spreads aria-describedby, aria-invalid, id, onFocus
        type="text"
        value={roleName}
        onChange={(e) => setRoleName(e.target.value)}
        placeholder="e.g., ADMIN_001"
        disabled={isLoading}
      />
    )}
  />
</Form>

// INCORRECT - Children wrapping (will NOT work)
<FormGroup>
  <FormFieldWrapper label="Role Name">
    <TextInput value={roleName} />
  </FormFieldWrapper>
</FormGroup>
```

### CORRECT Pattern: FormItem Props

```typescript
interface FormItemProps {
  label: ReactNode;                // Required field label
  id?: string;                     // Auto-generated if not provided
  description?: ReactNode;         // Help text below label
  descriptionId?: string;          // Auto-generated if needed
  error?: ReactNode;               // Error message (shows in red)
  errorId?: string;                // Auto-generated if needed
  hiddenLabel?: ReactNode;         // Visually hidden label (a11y)
  maxCharacters?: number;          // Character limit hint
  count?: number;                  // Current character count
  additionalContent?: ReactNode;   // Right-aligned content (icon, tooltip)
  additionalContentLeft?: boolean; // Position flag for content
  render: (props: FormItemRenderProps) => ReactNode;  // REQUIRED
}

// FormItemRenderProps passed to render function
interface FormItemRenderProps {
  "aria-describedby": string | undefined;  // Links to description/error for a11y
  "aria-invalid": true | undefined;        // Indicates validation error
  id: string;                              // Unique identifier
  onFocus?: FocusEventHandler;
}
```

### CORRECT Pattern: FormSection (Group related fields)

```typescript
import { Form, FormSection, FormItem, FormInput, FormSelect } from '@barclays/blueprint-react';

// All form content MUST be inside a <Form> wrapper
<Form onSubmit={handleSubmit}>
  {/* First section — default paddingTop (true) */}
  <FormSection
    head="Role Information"              // Optional section heading
    widthMd="6of12"                     // Medium breakpoint: 50% width
    widthLg="4of12"                     // Large breakpoint: 33% width
  >
    <FormItem
      label={<Type>Role ID</Type>}
      description={<Type>Unique identifier</Type>}
      render={(props) => (
        <FormInput {...props} type="text" />
      )}
    />

    <FormItem
      label={<Type>Role Type</Type>}
      render={(props) => (
        <FormSelect {...props}>
          <option value="">Select type...</option>
          <option value="SYSTEM">System</option>
          <option value="USER">User</option>
        </FormSelect>
      )}
    />
  </FormSection>

  {/* Second section — paddingTop={false} to avoid double spacing */}
  <FormSection head="Permissions" paddingTop={false}>
    <FormItem
      label={<Type>Access Level</Type>}
      description={<Type>Choose the level of access for this role</Type>}
      render={(props) => (
        <FormSelect {...props}>
          <option value="">Select level...</option>
          <option value="READ">Read Only</option>
          <option value="WRITE">Read/Write</option>
          <option value="ADMIN">Admin</option>
        </FormSelect>
      )}
    />
  </FormSection>
</Form>
```

> **CRITICAL**: For consecutive `<FormSection>` components within the same `<Form>`, the second and all subsequent sections MUST use `paddingTop={false}` to prevent excessive vertical spacing. See [FORM_LAYOUT_PATTERNS.md](FORM_LAYOUT_PATTERNS.md) for full details.

### CORRECT Pattern: FormSelect (Dropdown)

```typescript
import { FormSelect } from '@barclays/blueprint-react';

<FormItem
  label="Business Unit"
  render={(props) => (
    <FormSelect {...props} disabled={isLoading}>
      <option value="">Choose a unit...</option>
      {businessUnits.map(unit => (
        <option key={unit.id} value={unit.id}>
          {unit.name}
        </option>
      ))}
    </FormSelect>
  )}
/>
```

### CORRECT Pattern: FormTextarea

```typescript
import { FormTextarea } from '@barclays/blueprint-react';

<FormItem
  label="Description"
  render={(props) => (
    <FormTextarea
      {...props}
      rows={4}
      value={description}
      onChange={handleChange}
      placeholder="Enter description..."
    />
  )}
/>
```

### CORRECT Pattern: FormCheckbox (Boolean field)

```typescript
import { FormCheckbox } from '@barclays/blueprint-react';

<FormItem
  label="Active"
  render={(props) => (
    <FormCheckbox
      {...props}
      checked={isActive}
      onChange={handleChange}
    />
  )}
/>
```

---

## 2. DIALOG/MODAL COMPONENTS - CORRECT PATTERNS

### What EXISTS in Blueprint-React v1.3.0

```typescript
export {
  Dialog,        // Basic dialog with head/foot/children slots
  Modal,         // Full-featured modal wrapper
  Interrupt      // Alert variant of modal
}
```

### What DOES NOT EXIST (Remove from imports)

```typescript
❌ DialogHeader          - Never exported from dialog module
❌ DialogContent         - Never exported from dialog module
❌ DialogFooter          - Never exported from dialog module
```

### CORRECT Pattern: Dialog Component

**Key Concept**: Dialog uses slot properties (head, foot, children), NOT nested components.

```typescript
import { Dialog } from '@barclays/blueprint-react';

// CORRECT - Slot properties pattern
<Dialog
  isOpen={isOpen}
  head={
    <div>
      <h2>Add New Role</h2>
      <p>Create a role with the form below</p>
    </div>
  }
  foot={
    <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
      <button onClick={handleCancel}>Cancel</button>
      <button onClick={handleSubmit}>Create Role</button>
    </div>
  }
  onClickDismiss={handleClose}           // X button handler
  onClickOverlay={handleClose}           // Backdrop click handler
  onKeydownEscape={handleClose}          // Escape key handler
>
  {/* Body content goes here as children */}
  <FormSection>
    <FormItem label="Role Name" render={(props) => <FormInput {...props} />} />
  </FormSection>
</Dialog>

// INCORRECT - Nested components (will NOT work)
<Dialog isOpen={isOpen}>
  <DialogHeader onClose={handleClose}>
    <h2>Add New Role</h2>
  </DialogHeader>
  <DialogContent>
    <FormInput />
  </DialogContent>
  <DialogFooter>
    <button>Submit</button>
  </DialogFooter>
</Dialog>
```

### Dialog Props Reference

```typescript
interface DialogProps extends ComponentProps<"dialog"> {
  head?: ReactNode;                // Header slot
  children?: ReactNode;            // Body content
  foot?: ReactNode;                // Footer slot
  label?: string;                  // Aria-label (uses head if not provided)
  isOpen: boolean;                 // Controls visibility
  onClickDismiss?: () => void;     // X button click handler
  onClickOverlay?: () => void;     // Backdrop click handler
  onKeydownEscape?: () => void;    // Escape key handler
}
```

### CORRECT Pattern: Modal Component (Alternative)

For more complex modals with positioning and sizing:

```typescript
import { Modal } from '@barclays/blueprint-react';

<Modal
  title={<h2>Add New Role</h2>}
  footer={<div>{/* buttons */}</div>}
  onClose={handleClose}
  position="default"                    // "default" | "bottom" | "top"
  fullScreen={false}
  modalWidth="content"                  // "content" | "fixed"
  transparency="dark"                   // "dark" | "light"
>
  {/* Modal content */}
</Modal>
```

---

## 3. BUTTON COMPONENTS - CORRECT PATTERNS

### Button Props Reference

```typescript
interface ButtonProps {
  variant?: "primary" | "secondary" | "subtle";  // Style variant
  status?: "default" | "danger";                 // Status modifier
  size?: "default" | "sm";                       // Size
  media?: ReactNode;                             // Icon/content
  mediaPosition?: "left" | "right";              // Icon placement
  fullWidth?: boolean | "sm-down";               // Width control
  notification?: ReactNode;                      // Badge/count
  underline?: boolean;                           // Text underline
  disabled?: boolean;
  type?: "button" | "submit" | "reset";
  onClick?: () => void;
}
```

### CORRECT Pattern: Button Variants

```typescript
import { Button } from '@barclays/blueprint-react';

// Variant options (NOT "ghost", "danger" as variant, or "tertiary")
<Button variant="primary">Primary Action</Button>
<Button variant="secondary">Secondary Action</Button>
<Button variant="subtle">Subtle/Link Style</Button>

// Danger state (use status prop, NOT variant)
<Button status="danger">Delete Item</Button>
<Button variant="secondary" status="danger">Cancel Delete</Button>

// Sizes
<Button size="default">Normal Button</Button>
<Button size="sm">Small Button</Button>

// With icons
<Button variant="primary" media={<Icon icon="plus" size="sm" />} mediaPosition="left">
  Add Role
</Button>

// Disabled state
<Button disabled onClick={handleClick}>
  Disabled Button
</Button>

// Full width
<Button fullWidth variant="primary">
  Full Width Button
</Button>
```

### INCORRECT Button Usage (Remove these patterns)

```typescript
// WRONG - These variants don't exist
<Button variant="ghost" />        // DOES NOT EXIST - use variant="subtle"
<Button variant="danger" />       // DOES NOT EXIST - use status="danger"
<Button variant="tertiary" />     // DOES NOT EXIST - use variant="secondary"
```

---

## 4. TABLE COMPONENTS - CORRECT PATTERNS

### What EXISTS in Blueprint-React v1.3.0

```typescript
export {
  Table   // Wrapper with styling options, uses standard HTML table elements
}
```

### What DOES NOT EXIST (Remove from imports)

```typescript
❌ TableHead       - Never existed, use <thead>
❌ TableBody       - Never existed, use <tbody>
❌ TableRow        - Never existed, use <tr>
❌ TableCell       - Never existed, use <td> / <th>
```

### CORRECT Pattern: Table with HTML Elements

**Key Concept**: Use standard HTML table markup (thead, tbody, tr, td, th) with Table wrapper.

```typescript
import { Table, Button, Type } from '@barclays/blueprint-react';

// CORRECT - Standard HTML with Table wrapper, Type wrapping text, size="sm" buttons
<Table
  equalPadding
  columnBorders
  headingVariant="default"
  noOuterBorder={false}
>
  <thead>
    <tr>
      <Type element="th">Role ID</Type>
      <Type element="th">Name</Type>
      <Type element="th">Type</Type>
      <Type element="th">Actions</Type>
    </tr>
  </thead>
  <tbody>
    {roles.map(role => (
      <tr key={role.id} onClick={() => selectRole(role)}>
        <Type element="td">{role.id}</Type>
        <Type element="td">{role.name}</Type>
        <Type element="td">{role.type}</Type>
        <td>
          <Button size="sm" variant="secondary" onClick={() => editRole(role)}>
            Edit
          </Button>
          <Button size="sm" status="danger" onClick={() => deleteRole(role)}>
            Delete
          </Button>
        </td>
      </tr>
    ))}
  </tbody>
</Table>

// INCORRECT - Using non-existent components (will NOT work)
<Table>
  <TableHead>
    <TableRow>
      <TableCell as="th">Role ID</TableCell>
    </TableRow>
  </TableHead>
  <TableBody>
    <TableRow>
      <TableCell>{role.id}</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

### Table Props Reference

```typescript
interface TableProps {
  equalWidth?: boolean;              // Equal column widths
  equalPadding?: boolean;            // Equal cell padding
  columnBorders?: boolean;           // Vertical borders
  squareBottomBorders?: boolean;     // Square vs rounded corners
  headingVariant?: "default" | "secondary";
  noOuterBorder?: boolean;           // Remove table border
  inlineSpacing?: "default" | "lg";  // Cell spacing
  tableHeadNoBorderBottom?: boolean;
  tableHeadNoPaddingBottom?: boolean;
  tableDataVerticalAlignMiddle?: boolean;
}
```

### Table Cell Content Patterns (MANDATORY)

**Rule 1: All text cells use `<Type element="td">` / `<Type element="th">`**

```typescript
// ❌ INCORRECT — bare text in td/th loses Blueprint typography
<thead>
  <tr>
    <th>Name</th>
    <th>Status</th>
  </tr>
</thead>
<tbody>
  <tr>
    <td>{row.name}</td>
    <td>{row.status}</td>
  </tr>
</tbody>

// ✅ CORRECT — Type renders the td/th element with proper typography tokens
<thead>
  <tr>
    <Type element="th">Name</Type>
    <Type element="th">Status</Type>
  </tr>
</thead>
<tbody>
  <tr>
    <Type element="td">{row.name}</Type>
    <Type element="td">{row.status}</Type>
  </tr>
</tbody>
```

**Rule 2: All buttons in table cells use `size="sm"`**

```typescript
// ❌ INCORRECT — default-size button breaks table row height
<td>
  <Button variant="secondary" onClick={() => editRole(role)}>Edit</Button>
</td>

// ✅ CORRECT — size="sm" keeps buttons compact within table rows
<td>
  <Button size="sm" variant="secondary" onClick={() => editRole(role)}>Edit</Button>
</td>
```

**Rule 3: Cell type determines wrapper pattern**

| Cell Content | Pattern | Example |
|---|---|---|
| Text only | `<Type element="td">{text}</Type>` | `<Type element="td">{row.name}</Type>` |
| Button(s) only | `<td><Button size="sm" .../></td>` | `<td><Button size="sm" variant="secondary">Edit</Button></td>` |
| Text + Button | `<td><Type>{label}</Type> <Button size="sm" .../></td>` | Mixed content cell |
| FormRadio | `<Type element="td"><FormRadio .../></Type>` | Radio selection column |
| Formatted value | `<Type element="td">{formatCurrency(row.amount)}</Type>` | Formatted data |

**Note:** The `size="sm"` rule is a scoped exception to the general "no mixed button sizes" guidance (Mistake 20). It applies ONLY inside table cells. Page-level buttons still use default size.

---

## 5. TYPOGRAPHY / TYPE COMPONENT - CORRECT PATTERNS

### Heading Type Component

```typescript
import { Type } from '@barclays/blueprint-react';

// CORRECT - Every heading needs element + size + marginBottom
<Type element="h1" size="3xl" marginBottom="lg">Page Title</Type>
<Type element="h2" size="2xl" marginBottom="md">Section Heading</Type>
<Type element="h3" size="xl" marginBottom="sm">Subsection Heading</Type>
<Type element="h4" size="lg" marginBottom="sm">Card Heading</Type>
<Type element="h5" size="md" marginBottom="xs">Group Label</Type>
<Type element="h6" size="sm" marginBottom="xs">Minor Heading</Type>
<Type element="p" marginBottom>Body paragraph text.</Type>

// INCORRECT - Missing size (renders at default paragraph size)
<Type element="h1">Page Title</Type>                    // ❌ No visual hierarchy
<Type element="h2" weight="bold">Section</Type>         // ❌ Bold but still small
<Type element="div">Text</Type>                         // ❌ Invalid element
<Type element="h1" color="brand">Title</Type>           // ❌ Invalid color
```

### Type Props Quick Reference

| Prop | Valid Values |
|------|-------------|
| `element` | `h1`, `h2`, `h3`, `h4`, `h5`, `h6`, `p`, `span`, `em`, `strong`, `td`, `th` |
| `size` | `xs`, `sm`, `md`, `lg`, `xl`, `2xl`, `3xl` |
| `weight` | `bold`, `light`, `regular`, `medium`, `heavy` |
| `color` | `default`, `success`, `error`, `warning`, `inverse`, `info`, `title`, `disabled` |
| `marginBottom` | `true`, `xl`, `lg`, `sm`, `xs`, `2xs` |
| `alignment` | `left`, `right`, `center` |

---

## 6. ICON COMPONENTS - CORRECT PATTERNS

### Icon Component

```typescript
import { Icon } from '@barclays/blueprint-react';

// CORRECT usage — use "icon" prop (NOT "name"), ALWAYS include "size" prop
<Icon icon="plus" size="sm" />
<Icon icon="bin" size="sm" />
<Icon icon="edit" size="sm" />
<Icon icon="search" size="md" />
<Icon icon="dismiss" size="sm" />
<Icon icon="tick" size="sm" />
<Icon icon="warning" size="md" />

// Valid icon names (exhaustive list for v1.3.0):
// back, bell, bin, calendar, card, chat, chevron-down, chevron-left,
// chevron-left-double, chevron-right, chevron-right-double, chevron-up,
// clock, cloud-upload, cog, compass, diamond, dismiss, download, edit,
// error, error-fill, home, info, info-fill, international, leaf, log-out,
// mail, manage-payments, minus, more, more-vertical, new, padlock,
// payments, plane, plus, profile, refresh, search, settings, show,
// success, success-fill, tick, transfer, tree, warning, warning-fill
//
// INVALID names (common mistakes): cross, close, trash, check, arrow-*,
// upload, share, menu, user, help, camera, print, document, external
```

---

## 7. COMPLETE MIGRATION CHECKLIST

### Components to REMOVE from imports

```typescript
// ❌ Remove these - they don't exist
import {
  FormGroup,              // REMOVE
  FormFieldWrapper,       // REMOVE
  TextInput,              // REMOVE
  TextArea,               // REMOVE
  Select,                 // REMOVE
  Option,                 // REMOVE
  DialogHeader,           // REMOVE
  DialogContent,          // REMOVE
  DialogFooter,           // REMOVE
  TableHead,              // REMOVE
  TableBody,              // REMOVE
  TableRow,               // REMOVE
  TableCell,              // REMOVE
  Tooltip,                // REMOVE — use PopupNav or native title
  Popover,                // REMOVE — use PopupNav
  Spinner,                // REMOVE — use Loading
} from '@barclays/blueprint-react';
```

### Correct imports to use

```typescript
// ✅ Use these instead
import {
  Form,
  FormSection,
  FormItem,
  FormInput,
  FormTextarea,
  FormSelect,
  FormCheckbox,
  FormRadio,
  Dialog,
  Modal,
  Button,
  Table,
  Icon,
  // ... other legitimate components
} from '@barclays/blueprint-react';
```

---

## 8. COMPONENT MIGRATION MATRIX

| Current (WRONG) | Location | Should Be | File to Update |
|---|---|---|---|
| FormGroup, FormFieldWrapper, TextInput | FormField.tsx | Form + FormItem + FormInput | src/components/FormField.tsx |
| DialogHeader, DialogContent, DialogFooter | DialogLayout.tsx | Dialog with head/foot/children | src/components/DialogLayout.tsx |
| DialogHeader, DialogContent, DialogFooter | ConfirmDialog.tsx | Dialog with head/foot/children | src/components/ConfirmDialog.tsx |
| TableHead, TableBody, TableRow, TableCell | RolesDashboard.tsx | Standard HTML + Table wrapper | src/features/roles/RolesDashboard.tsx |
| Button variant="ghost" | ActionButton.tsx | Button variant="subtle" | src/components/ActionButton.tsx |
| Button variant="danger" | ActionButton.tsx | Button status="danger" | src/components/ActionButton.tsx |
| Button variant="tertiary" | ActionButton.tsx | Button variant="secondary" | src/components/ActionButton.tsx |

---

## 9. BEFORE AND AFTER EXAMPLES

### Example 1: Form Component

**BEFORE (INCORRECT)**:
```typescript
import { FormGroup, FormFieldWrapper, TextInput } from '@barclays/blueprint-react';

export const FormField = ({ label, value, onChange, error }) => (
  <FormGroup>
    <FormFieldWrapper label={label} error={error}>
      <TextInput value={value} onChange={onChange} />
    </FormFieldWrapper>
  </FormGroup>
);
```

**AFTER (CORRECT)**:
```typescript
import { Form, FormItem, FormInput } from '@barclays/blueprint-react';

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

### Example 2: Dialog Component

**BEFORE (INCORRECT)**:
```typescript
import { Dialog, DialogHeader, DialogContent, DialogFooter } from '@barclays/blueprint-react';

<Dialog isOpen={isOpen}>
  <DialogHeader onClose={handleClose}>
    <h2>Dialog Title</h2>
  </DialogHeader>
  <DialogContent>
    Content here
  </DialogContent>
  <DialogFooter>
    <button onClick={handleClose}>Close</button>
  </DialogFooter>
</Dialog>
```

**AFTER (CORRECT)**:
```typescript
import { Dialog } from '@barclays/blueprint-react';

<Dialog
  isOpen={isOpen}
  head={<h2>Dialog Title</h2>}
  foot={<button onClick={handleClose}>Close</button>}
  onClickDismiss={handleClose}
  onClickOverlay={handleClose}
>
  Content here
</Dialog>
```

### Example 3: Table Component

**BEFORE (INCORRECT)**:
```typescript
import { Table, TableHead, TableBody, TableRow, TableCell } from '@barclays/blueprint-react';

<Table>
  <TableHead>
    <TableRow>
      <TableCell as="th">Name</TableCell>
    </TableRow>
  </TableHead>
  <TableBody>
    <TableRow>
      <TableCell>John</TableCell>
    </TableRow>
  </TableBody>
</Table>
```

**AFTER (CORRECT)**:
```typescript
import { Table, Type } from '@barclays/blueprint-react';

<Table equalPadding columnBorders>
  <thead>
    <tr>
      <Type element="th">Name</Type>
    </tr>
  </thead>
  <tbody>
    <tr>
      <Type element="td">John</Type>
    </tr>
  </tbody>
</Table>
```

---

## 10. RELATED DOCUMENTATION UPDATES

These files also need updates:
- **BDL_TO_BLUEPRINT_REACT.md** - Update component mapping to reflect correct Blueprint patterns
- **BLUEPRINT_REACT_REFERENCE.md** - Clarify actual exported components vs non-existent wrappers
- Phase 3 component documentation
- Phase 4 feature component documentation

---

## 11. IMPLEMENTATION PRIORITY

### CRITICAL (Fix immediately - breaks functionality)
1. FormField.tsx - Uses non-existent form components
2. DialogLayout.tsx - Uses non-existent dialog components
3. ConfirmDialog.tsx - Uses non-existent dialog components

### HIGH (Fixes visual/behavioral issues)
4. ActionButton.tsx - Uses invalid button variants
5. All dashboard components - Table components don't exist

### MEDIUM (Code cleanup)
6. Update all imports in feature components
7. Clean up component exports

---

## 12. KEY TAKEAWAYS

1. **FormItem is not a wrapper**: It uses render function pattern
2. **Dialog uses slots**: head, foot, children - NOT nested components
3. **Tables use HTML**: Use standard thead/tbody/tr/td with Table wrapper
4. **Buttons use variant + status**: NOT invalid variant values
5. **No FormGroup/TextInput/etc**: These components don't exist in Blueprint-React v1.3.0

---

**Status**: 🔴 CRITICAL - All MCA2 wrapper components need immediate correction to follow Blueprint-React v1.3.0 actual API

**Next Action**: Update component implementations to use correct Blueprint-React patterns
