# BDL Table to Blueprint-React Mapping

**Last Updated**: July 24, 2026

---

## Table (`<mca-table>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-table>` | `<Table>` |
| `<mca-table-row>` | `<tr>` (standard HTML) |
| `<mca-table-cell>` | `<td>` or `<th>` (standard HTML) |
| `<mca-account-table>` | `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table` |

**Critical**: Use standard HTML `<thead>`, `<tbody>`, `<tr>`, `<td>`, `<th>` inside `<Table>`. There are **NO** `TableHead`, `TableBody`, `TableRow`, or `TableCell` components in Blueprint-React. These components do NOT exist — do not attempt to import them.

---

## Iron Rules for Table Cells (NON-NEGOTIABLE)

These rules apply to EVERY table produced by migration. Violating them is a blocking validation error.

### Rule A: All text in table cells MUST use `<Type element="td">` or `<Type element="th">`

Never render plain text inside raw `<td>` or `<th>` tags. Blueprint's `<Type>` component ensures consistent typography tokens (font-size, line-height, color).

```typescript
// ❌ WRONG — bare text in td/th loses Blueprint typography
<td>{row.name}</td>
<th>Column Header</th>

// ✅ CORRECT — Type replaces the td/th element
<Type element="td">{row.name}</Type>
<Type element="th">Column Header</Type>
```

**Exception:** When a cell contains ONLY interactive components (Button, Link, Loading), use a raw `<td>` wrapper around those components. The interactive components handle their own styling.

```typescript
// ✅ CORRECT — cell with only buttons uses raw <td>
<td>
  <Button size="sm" variant="secondary" onClick={handleEdit}>Edit</Button>
</td>

// ✅ CORRECT — mixed content: text wrapped in Type, inside raw <td> alongside button
<td>
  <Type>{row.label}</Type>
  <Button size="sm" variant="subtle" onClick={handleAction}>Go</Button>
</td>
```

### Rule B: All `<Button>` components inside table cells MUST use `size="sm"`

Default-size buttons are too tall for table rows and break visual density. Every `<Button>` rendered as a descendant of `<td>` or `<th>` must include `size="sm"`.

```typescript
// ❌ WRONG — default size button in table cell
<td>
  <Button variant="secondary" onClick={handleEdit}>Edit</Button>
</td>

// ✅ CORRECT — size="sm" mandatory in tables
<td>
  <Button variant="secondary" size="sm" onClick={handleEdit}>Edit</Button>
</td>
```

**Note:** This is an explicit exception to the general guidance in IMPLEMENTATION_GUIDE Mistake 20 ("never mix button sizes"). Table context requires compact buttons. Page-level buttons (form submit, toolbar) still use default size.

### Cell Content Decision Table

| Cell Content | Pattern | Example |
|---|---|---|
| Text/data only | `<Type element="td">{value}</Type>` | `<Type element="td">{row.name}</Type>` |
| Header text | `<Type element="th">Label</Type>` | `<Type element="th">Status</Type>` |
| Button(s) only | `<td><Button size="sm" .../></td>` | `<td><Button size="sm" variant="secondary">Edit</Button></td>` |
| Text + Button | `<td><Type>{text}</Type> <Button size="sm" .../></td>` | Mixed content |
| FormRadio | `<Type element="td"><FormRadio .../></Type>` | Radio selection column |
| Formatted value | `<Type element="td">{formatCurrency(row.amount)}</Type>` | Currency/date display |

---

### Basic Table

**MCA1 (Before)**:
```html
<mca-table id="b_table_basic">
    <mca-table-row header="yes">
        <mca-table-cell>Name</mca-table-cell>
        <mca-table-cell>Amount</mca-table-cell>
        <mca-table-cell>Status</mca-table-cell>
    </mca-table-row>
    <mca-table-row>
        <mca-table-cell>Item A</mca-table-cell>
        <mca-table-cell>100.00</mca-table-cell>
        <mca-table-cell>Active</mca-table-cell>
    </mca-table-row>
    <mca-table-row>
        <mca-table-cell>Item B</mca-table-cell>
        <mca-table-cell>250.00</mca-table-cell>
        <mca-table-cell>Pending</mca-table-cell>
    </mca-table-row>
</mca-table>
```

**Blueprint-React (After)**:
```typescript
<Table id="b_table_basic" equalPadding headingVariant="default">
  <thead>
    <tr>
      <Type element="th">Name</Type>
      <Type element="th">Amount</Type>
      <Type element="th">Status</Type>
    </tr>
  </thead>
  <tbody>
    <tr>
      <Type element="td">Item A</Type>
      <Type element="td">100.00</Type>
      <Type element="td">Active</Type>
    </tr>
    <tr>
      <Type element="td">Item B</Type>
      <Type element="td">250.00</Type>
      <Type element="td">Pending</Type>
    </tr>
  </tbody>
</Table>
```

---

### Table with Column Borders

**MCA1 (Before)**:
```html
<mca-table id="b_table_borders" column-borders="yes">
    <mca-table-row header="yes">
        <mca-table-cell>Column 1</mca-table-cell>
        <mca-table-cell>Column 2</mca-table-cell>
    </mca-table-row>
    <mca-table-row>
        <mca-table-cell>Data 1</mca-table-cell>
        <mca-table-cell>Data 2</mca-table-cell>
    </mca-table-row>
</mca-table>
```

**Blueprint-React (After)**:
```typescript
<Table id="b_table_borders" equalPadding columnBorders headingVariant="default">
  <thead>
    <tr>
      <Type element="th">Column 1</Type>
      <Type element="th">Column 2</Type>
    </tr>
  </thead>
  <tbody>
    <tr>
      <Type element="td">Data 1</Type>
      <Type element="td">Data 2</Type>
    </tr>
  </tbody>
</Table>
```

---

### Table with Radio Column (Selection)

MCA1's `radio-column="yes"` adds a radio button column for row selection. In Blueprint-React, add a `<FormRadio>` in the first cell of each body row.

**MCA1 (Before)**:
```html
<mca-table id="partialSwitchOption" name="switchType" header="no" radio-column="yes">
    <mca-table-row header="yes">
        <mca-table-cell>Type</mca-table-cell>
        <mca-table-cell>Amount</mca-table-cell>
    </mca-table-row>
    <mca-table-row>
        <mca-table-cell data-value="all">All</mca-table-cell>
        <mca-table-cell>100.00</mca-table-cell>
    </mca-table-row>
    <mca-table-row>
        <mca-table-cell data-value="partial">Partial</mca-table-cell>
        <mca-table-cell>50.00</mca-table-cell>
    </mca-table-row>
</mca-table>
```

**Blueprint-React (After)**:
```typescript
const [selectedType, setSelectedType] = useState<string>('');

<Table id="partialSwitchOption" equalPadding headingVariant="default">
  <thead>
    <tr>
      <Type element="th"></Type>
      <Type element="th">Type</Type>
      <Type element="th">Amount</Type>
    </tr>
  </thead>
  <tbody>
    <tr>
      <Type element="td">
        <FormRadio
          name="switchType"
          value="all"
          label=""
          checked={selectedType === 'all'}
          onChange={(e) => setSelectedType(e.target.value)}
        />
      </Type>
      <Type element="td">All</Type>
      <Type element="td">100.00</Type>
    </tr>
    <tr>
      <Type element="td">
        <FormRadio
          name="switchType"
          value="partial"
          label=""
          checked={selectedType === 'partial'}
          onChange={(e) => setSelectedType(e.target.value)}
        />
      </Type>
      <Type element="td">Partial</Type>
      <Type element="td">50.00</Type>
    </tr>
  </tbody>
</Table>
```

---

### Table with No Header

MCA1's `header="no"` hides the header row visually. Render without `<thead>` or use `<thead>` with visually hidden styling for accessibility.

**MCA1 (Before)**:
```html
<mca-table id="b_table_no_header" header="no">
    <mca-table-row>
        <mca-table-cell>Row 1 Col 1</mca-table-cell>
        <mca-table-cell>Row 1 Col 2</mca-table-cell>
    </mca-table-row>
    <mca-table-row>
        <mca-table-cell>Row 2 Col 1</mca-table-cell>
        <mca-table-cell>Row 2 Col 2</mca-table-cell>
    </mca-table-row>
</mca-table>
```

**Blueprint-React (After)**:
```typescript
<Table id="b_table_no_header" equalPadding>
  <tbody>
    <tr>
      <Type element="td">Row 1 Col 1</Type>
      <Type element="td">Row 1 Col 2</Type>
    </tr>
    <tr>
      <Type element="td">Row 2 Col 1</Type>
      <Type element="td">Row 2 Col 2</Type>
    </tr>
  </tbody>
</Table>
```

---

### Dynamic Table (Data-Driven)

When table data comes from an API or Redux state, render rows dynamically with `.map()`.

```typescript
interface TableRow {
  id: string;
  name: string;
  amount: string;
  status: string;
}

const rows: TableRow[] = useAppSelector(state => state.data.rows);
const safeRows = Array.isArray(rows) ? rows : [];

<Table equalPadding headingVariant="default">
  <thead>
    <tr>
      <Type element="th">Name</Type>
      <Type element="th">Amount</Type>
      <Type element="th">Status</Type>
    </tr>
  </thead>
  <tbody>
    {safeRows.map((row) => (
      <tr key={row.id}>
        <Type element="td">{row.name}</Type>
        <Type element="td">{row.amount}</Type>
        <Type element="td">{row.status}</Type>
      </tr>
    ))}
  </tbody>
</Table>
```

**Note**: Always use `Array.isArray()` before `.map()` to guard against unexpected API response structures (see SKILL.md Mistake 23).

---

### Table with Action Buttons in Cells

MCA1 tables can contain buttons or links inside cells. Render them as `<Button>` or `<Link>` inside `<td>`.

```typescript
<Table equalPadding headingVariant="default">
  <thead>
    <tr>
      <Type element="th">Name</Type>
      <Type element="th">Actions</Type>
    </tr>
  </thead>
  <tbody>
    <tr>
      <Type element="td">Item A</Type>
      <Type element="td">
        <Arrange gap="fixed">
          <ArrangeItem size="fit">
            <Button variant="secondary" size="sm" onClick={() => handleEdit('a')}>
              Edit
            </Button>
          </ArrangeItem>
          <ArrangeItem size="fit">
            <Button variant="secondary" size="sm" status="danger" onClick={() => handleDelete('a')}>
              Delete
            </Button>
          </ArrangeItem>
        </Arrange>
      </Type>
    </tr>
  </tbody>
</Table>
```

---

### Paginated Table (`paging="yes"` / `<mca-account-table>`)

When `<mca-table paging="yes">` is present OR `<mca-account-table>` is detected, migration uses the published `PaginatedTable` component from `@barclays/mca-ui-common-utils-paginated-table`. **Do not create a custom PaginatedTable component — use the published package.**

#### Package: `@barclays/mca-ui-common-utils-paginated-table`

- Peer dependency: `@barclays/blueprint-react` (^1.4.1), `react` (>=18), `react-dom` (>=18)
- Install: `npm install @barclays/mca-ui-common-utils-paginated-table`

```typescript
// Imports
import { PaginatedTable } from '@barclays/mca-ui-common-utils-paginated-table';
import '@barclays/mca-ui-common-utils-paginated-table/dist/paginated-table.module.css';

// Types (exported from the package — do NOT create manually)
import type {
  PaginatedTableProps,
  CodeDecode,
  TableRow,
  TextCell,
  ButtonCell,
  SelectButtonCell,
  ButtonListCell,
  ButtonListItem,
} from '@barclays/mca-ui-common-utils-paginated-table';
```

---

#### MCA1 (Before) — Pattern 1: `<mca-table paging="yes">`

```html
<mca-table id="b_table" paging="yes" sort="yes" search="yes">
  <mca-table-row header="yes">
    <mca-table-cell>Name</mca-table-cell>
    <mca-table-cell>Status</mca-table-cell>
    <mca-table-cell>Action</mca-table-cell>
  </mca-table-row>
  <%for(var i=0; i<items.length; i++){%>
  <mca-table-row>
    <mca-table-cell><%=items[i].name%></mca-table-cell>
    <mca-table-cell><%=items[i].status%></mca-table-cell>
    <mca-table-cell><mca-button data-action="select" data-index="<%=i%>">Select</mca-button></mca-table-cell>
  </mca-table-row>
  <%}%>
</mca-table>
```

#### MCA1 (Before) — Pattern 2: `<mca-account-table>`

```html
<mca-account-table id="<%=type%>" account-type="type2" class="accountsList"
    account-data="[ ]" title="<%=title%>" sort="no" paging="yes"
    page-length="10" empty-table-msg="none">
</mca-account-table>
```

Other variants: `<mca-account-table>` may appear with different `account-type` values, custom column configurations via attributes, or data populated dynamically via JavaScript. All map to the same `PaginatedTable` component.

---

#### Blueprint-React (After) — import and use from package

```tsx
import { PaginatedTable } from '@barclays/mca-ui-common-utils-paginated-table';
import '@barclays/mca-ui-common-utils-paginated-table/dist/paginated-table.module.css';
import type { CodeDecode } from '@barclays/mca-ui-common-utils-paginated-table';

// Example: migrating <mca-table paging="yes"> with action buttons
<PaginatedTable
  headers={['Name', 'Status', 'Action']}
  headingVariant="secondary"
  indexWithMaxWidth={0}
  rowsPerPage={10}
  allRows={items.map(item => ({
    code: item.id,
    decode: item.name,
    details: [
      { type: 'text', value: item.name },
      { type: 'text', value: item.status },
      {
        type: 'select-button',
        value: 'Select',
        onClick: ({ code }: CodeDecode) => handleSelect(code),
        alignment: 'right',
      },
    ],
  }))}
/>
```

```tsx
// Example: migrating <mca-account-table> with title and empty state
import { PaginatedTable } from '@barclays/mca-ui-common-utils-paginated-table';
import '@barclays/mca-ui-common-utils-paginated-table/dist/paginated-table.module.css';
import { Type } from '@barclays/blueprint-react';

interface AccountTableProps {
  title: string;
  accounts: Account[];
}

export const AccountTable: React.FC<AccountTableProps> = ({ title, accounts }) => {
  if (accounts.length === 0) {
    return null; // or render empty-table-msg
  }

  return (
    <>
      <Type element="h2" size="md" marginBottom="sm">{title}</Type>
      <PaginatedTable
        headers={['Account', 'Type', 'Balance', 'Action']}
        headingVariant="secondary"
        indexWithMaxWidth={0}
        rowsPerPage={10}
        allRows={accounts.map(account => ({
          code: account.id,
          decode: account.name,
          details: [
            { type: 'text', value: account.name },
            { type: 'text', value: account.type },
            { type: 'text', value: account.balance, alignment: 'right' as const },
            {
              type: 'select-button',
              value: 'Select',
              onClick: ({ code }: CodeDecode) => handleSelectAccount(code),
              alignment: 'right' as const,
            },
          ],
        }))}
      />
    </>
  );
};
```

---

#### `PaginatedTable` Props Reference

| Prop | Type | Default | Notes |
|---|---|---|---|
| `headers` | `string[]` | **required** | Column header labels |
| `allRows` | `TableRow[]` | **required** | Complete dataset — pagination computed internally |
| `rowsPerPage` | `number` | **required** | Number of rows per page |
| `headingVariant` | `'default' \| 'secondary'` | `'secondary'` | Header row colour |
| `indexWithMaxWidth` | `number \| number[]` | `0` | Column index(es) that get `width: auto`; others get `1%` with `nowrap` |

---

#### Cell Types

Each row's `details` array contains cells of these types:

**`TextCell`** — plain text, rendered via `<Type element="td">`:
```typescript
{ type: 'text', value: string, alignment?: 'left' | 'right' | 'center' }
```

**`ButtonCell`** — link-style button, rendered as `<LinkButton>`:
```typescript
{
  type: 'button',
  value: string,                                    // Button text
  onClick: ({ code, decode }: CodeDecode) => void,  // Receives row's code/decode
  noDecoration?: boolean,
  media?: React.ReactElement,                       // Optional icon
  ref?: React.Ref<HTMLButtonElement>,
  isLoading?: boolean,
  disabled?: boolean,
  buttonLabel?: string,                             // Custom aria-label
  ariaExpanded?: boolean,
  ariaHasPopup?: boolean | 'dialog' | 'menu' | 'false' | 'true' | 'grid' | 'listbox' | 'tree',
  alignment?: 'left' | 'right' | 'center',
}
```

**`SelectButtonCell`** — solid button (`<Button size="sm">`):
```typescript
{
  type: 'select-button',
  value: string,
  onClick: ({ code, decode }: CodeDecode) => void,
  isLoading?: boolean,
  buttonLabel?: string,
  alignment?: 'left' | 'right' | 'center',
}
```

**`ButtonListCell`** — multiple link-buttons with dividers:
```typescript
{
  type: 'button-list',
  buttons: {
    value: string,
    onClick: ({ code, decode }: CodeDecode) => void,
    noDecoration: boolean,
    media?: React.ReactElement,
    disabled?: boolean,
    buttonLabel?: string,
  }[],
  alignment?: 'left' | 'right' | 'center',
}
```

**`TableRow`** — row structure:
```typescript
{
  code: string,    // Row identifier (passed to button onClick callbacks)
  decode: string,  // Row display name (used in ARIA labels)
  details: (TextCell | ButtonCell | SelectButtonCell | ButtonListCell)[],
}
```

---

#### `<mca-account-table>` Attribute Mapping

| MCA1 Attribute | PaginatedTable Equivalent | Notes |
|---|---|---|
| `account-data` | `allRows` | Parse the JSON data and map each entry to `TableRow` structure |
| `page-length` | `rowsPerPage` | Direct numeric mapping |
| `title` | Render `<Type element="h2">` above `<PaginatedTable>` | Sibling element, not a prop |
| `empty-table-msg` | Conditional render: guard with `if (data.length === 0)` | Show message or return null before rendering table |
| `account-type` | Metadata for constructing `allRows` | Map to `code`/`decode` fields as appropriate |
| `sort="yes"` | Pre-sort `allRows` before passing | Not built-in; sort the array in the parent component if needed |
| `paging="yes"` | Always true for this component | Pagination is the component's purpose |
| `id` | `id` on a wrapper `<div>` | For testing/accessibility targeting |
| `class` | `className` on wrapper `<div>` | React convention |

---

#### Key Rules for Paginated Table Migration

- `paging="yes"` on `<mca-table>` OR any `<mca-account-table>` → **always** use the published `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table`
- **Never** create a custom `PaginatedTable.tsx` or `paginated-table.module.css` — the package provides both
- **Always** import the CSS: `import '@barclays/mca-ui-common-utils-paginated-table/dist/paginated-table.module.css'`
- Ensure the package is in `package.json` — if missing, add it via `npm install @barclays/mca-ui-common-utils-paginated-table`
- `CodeDecode` type is exported from the package — do NOT create it manually in `src/types/index.ts`
- `Pagination` only renders when `rowsPerPage < allRows.length` — this is handled internally by the package
- The last column header is always right-aligned (internal behavior)
- Cell type `'button'` → `<LinkButton>` (link style); type `'select-button'` → `<Button size="sm">` (solid style)
- The `code`/`decode` fields map from the row's unique ID and display name — map from MCA1's data binding
- Focus management on page change is built into the package — no custom `useEffect` needed

---

## `<Table>` Props

| Blueprint-React Prop | Type | Notes |
|---|---|---|
| `equalPadding` | boolean | Equal cell padding across all columns |
| `columnBorders` | boolean | Vertical borders between columns |
| `headingVariant` | `"default"` \| `"secondary"` | Header row colour — `"secondary"` is the standard choice for paginated tables |
| `squareBottomBorders` | boolean | Square border radius on bottom corners — use with paginated tables so the pagination sits flush below |
| `noOuterBorder` | boolean | Remove the outer border frame |
| `inlineSpacing` | `"default"` \| `"lg"` | Increase cell padding dynamically with screen size |
| `tableDataVerticalAlignMiddle` | boolean | Vertically centre-align all cell content |
| `id` | string | Table identifier |
| `className` | string | Additional CSS class |

---

## Complete `<mca-table>` Attribute Mapping

**`<mca-table>` (table wrapper)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Table` | |
| `class` | `className` | `Table` | React convention |
| `name` | N/A | N/A | Use state variable name for form submission |
| `header="no"` | Omit `<thead>` | Table structure | No header row rendered |
| `header="yes"` | Include `<thead>` | Table structure | Default — render header |
| `column-borders="yes"` | `columnBorders` | `Table` | Boolean prop |
| `paging="yes"` | `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table` | Package import | **Install and import from published package — see Paginated Table section above** |
| `sort="yes"` | N/A | N/A | Sorting is not a built-in Blueprint prop — implement manually with state if required |
| `search="yes"` | N/A | N/A | Search/filter is not built-in — implement with a `<FormInput>` + client-side filter if required |
| `title` | `<Type>` above `<Table>` | Sibling element | Render as `<Type element="h2">` before the table |
| `empty-table-msg` | Conditional render | `<tbody>` | Render a `<tr><td colSpan={n}>` row when data array is empty |
| `radio-column="yes"` | `<FormRadio>` in first `<td>` of each body row | `<td>` | Manual radio column |

**`<mca-table-row>` (table row)**:
| MCA1 Attribute | Blueprint-React | Location | Notes |
|---|---|---|---|
| `header="yes"` | Row inside `<thead>`, cells as `<th>` | `<thead><tr><th>` | Header row |
| (no header attribute) | Row inside `<tbody>`, cells as `<td>` | `<tbody><tr><td>` | Body row |
| `class` | `className` on `<tr>` | `<tr>` | React convention |

**`<mca-table-cell>` (table cell)**:
| MCA1 Attribute | Blueprint-React | Location | Notes |
|---|---|---|---|
| Text content | `children` of `<Type element="td">` or `<Type element="th">` | `<Type>` component | Use `<Type element="td">` or `<Type element="th">` to replace `<td>`/`<th>` |
| `data-value` | `data-value` attribute or controlled state | `<Type>` | Use for form submission / selection tracking |
| `class` | `className` on `<Type>` | `<Type>` | React convention |
| `colspan` | `colSpan` on `<Type>` | `<Type>` | camelCase in React |
| `rowspan` | `rowSpan` on `<Type>` | `<Type>` | camelCase in React |

---

## Common Mistakes

**DO NOT** import or use these — they do not exist in Blueprint-React:
```typescript
// WRONG — these components DO NOT EXIST
import { TableHead, TableBody, TableRow, TableCell } from '@barclays/blueprint-react';
```

**DO** use standard HTML elements inside `<Table>`, with `<Type>` wrapping text content:
```typescript
// CORRECT
import { Table, Type } from '@barclays/blueprint-react';

<Table>
  <thead><tr><Type element="th">Header</Type></tr></thead>
  <tbody><tr><Type element="td">Data</Type></tr></tbody>
</Table>
```

---

## Advanced Table Variants

### Configuration Table (Show/Hide Columns)

**MCA1**: Table with configurable visible columns via settings UI.

**Blueprint-React**: Manage column visibility with React state.

```typescript
import React, { useState } from 'react';
import { Table, FormCheckbox, FormMultiItem, Section, SectionItem, Type } from '@barclays/blueprint-react';

interface Column {
  key: string;
  label: string;
  visible: boolean;
}

export const ConfigurableTable: React.FC<{ data: Record<string, string>[] }> = ({ data }) => {
  const [columns, setColumns] = useState<Column[]>([
    { key: 'name', label: 'Name', visible: true },
    { key: 'amount', label: 'Amount', visible: true },
    { key: 'status', label: 'Status', visible: true },
    { key: 'date', label: 'Date', visible: false },
  ]);

  const toggleColumn = (key: string) => {
    setColumns(columns.map(col => col.key === key ? { ...col, visible: !col.visible } : col));
  };

  const visibleCols = columns.filter(c => c.visible);

  return (
    <Section>
      <SectionItem>
        <FormMultiItem label={<Type>Show columns</Type>}>
          {columns.map(col => (
            <FormCheckbox
              key={col.key}
              checked={col.visible}
              onChange={() => toggleColumn(col.key)}
              label={col.label}
            />
          ))}
        </FormMultiItem>
      </SectionItem>
      <SectionItem>
        <Table equalPadding headingVariant="default">
          <thead>
            <tr>{visibleCols.map(col => <th key={col.key}>{col.label}</th>)}</tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}>{visibleCols.map(col => <td key={col.key}>{row[col.key]}</td>)}</tr>
            ))}
          </tbody>
        </Table>
      </SectionItem>
    </Section>
  );
};
```

---

### Empty Table State

**MCA1**: Table with "No data available" message when empty.

**Blueprint-React**: Conditional rendering with `colSpan` message row.

```typescript
<Table equalPadding headingVariant="default">
  <thead>
    <tr>
      <th>Name</th>
      <th>Amount</th>
      <th>Status</th>
    </tr>
  </thead>
  <tbody>
    {data.length === 0 ? (
      <tr>
        <td colSpan={3}>
          <Type color="secondary" element="p" align="center">No data available</Type>
        </td>
      </tr>
    ) : (
      data.map((row, i) => (
        <tr key={i}>
          <Type element="td">{row.name}</Type>
          <Type element="td">{row.amount}</Type>
          <Type element="td">{row.status}</Type>
        </tr>
      ))
    )}
  </tbody>
</Table>
```

---

### Accordion Table (Expandable Rows)

**MCA1**: `<mca-table>` with expandable detail rows triggered by click.

**Blueprint-React**: Use `useState` Set to track expanded row IDs.

```typescript
import React, { useState } from 'react';
import { Table, Button, Icon, Type } from '@barclays/blueprint-react';

interface RowData {
  id: string;
  name: string;
  amount: string;
  details: string;
}

export const AccordionTable: React.FC<{ data: RowData[] }> = ({ data }) => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggleRow = (id: string) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <Table equalPadding headingVariant="default">
      <thead>
        <tr>
          <th></th>
          <Type element="th">Name</Type>
          <Type element="th">Amount</Type>
        </tr>
      </thead>
      <tbody>
        {data.map(row => (
          <React.Fragment key={row.id}>
            <tr>
              <td>
                <Button variant="subtle" size="sm" onClick={() => toggleRow(row.id)}>
                  <Icon icon={expanded.has(row.id) ? 'chevron-up' : 'chevron-down'} size="xs" />
                </Button>
              </td>
              <Type element="td">{row.name}</Type>
              <Type element="td">{row.amount}</Type>
            </tr>
            {expanded.has(row.id) && (
              <tr>
                <td colSpan={3}>
                  <Type size="sm">{row.details}</Type>
                </td>
              </tr>
            )}
          </React.Fragment>
        ))}
      </tbody>
    </Table>
  );
};
```

---

### Checkbox Column Table (Multi-Select Rows)

**MCA1**: Table with checkbox column for selecting multiple rows + select-all header.

**Blueprint-React**: Manage selection state with `useState<Set>`.

```typescript
import React, { useState } from 'react';
import { Table, Type } from '@barclays/blueprint-react';

interface RowData { id: string; name: string; amount: string; }

export const CheckboxTable: React.FC<{ data: RowData[] }> = ({ data }) => {
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const allSelected = selected.size === data.length;

  const toggleAll = () => {
    setSelected(allSelected ? new Set() : new Set(data.map(r => r.id)));
  };

  const toggleRow = (id: string) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <Table equalPadding headingVariant="default">
      <thead>
        <tr>
          <th><input type="checkbox" checked={allSelected} onChange={toggleAll} aria-label="Select all" /></th>
          <Type element="th">Name</Type>
          <Type element="th">Amount</Type>
        </tr>
      </thead>
      <tbody>
        {data.map(row => (
          <tr key={row.id}>
            <td><input type="checkbox" checked={selected.has(row.id)} onChange={() => toggleRow(row.id)} aria-label={`Select ${row.name}`} /></td>
            <Type element="td">{row.name}</Type>
            <Type element="td">{row.amount}</Type>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};
```

---

### Server-Side Table (Paginated with API calls)

**MCA1**: `.scpTable()` with deferred loading — fetches data per page from server.

**Blueprint-React**: `Table` + `Pagination` with `useEffect` fetching data on page change.

```typescript
import React, { useState, useEffect } from 'react';
import { Table, Pagination, Section, SectionItem, Loading, Type } from '@barclays/blueprint-react';

interface PagedResponse { items: Record<string, string>[]; total: number; }

export const ServerTable: React.FC<{ fetchPage: (page: number, size: number) => Promise<PagedResponse> }> = ({ fetchPage }) => {
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [data, setData] = useState<Record<string, string>[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchPage(page, pageSize).then(res => {
      setData(res.items);
      setTotal(res.total);
      setLoading(false);
    });
  }, [page, pageSize, fetchPage]);

  const totalPages = Math.ceil(total / pageSize);

  if (loading) return <Loading size="lg" shape="circle" />;

  return (
    <Section>
      <SectionItem>
        <Table equalPadding headingVariant="default">
          <thead>
            <tr><Type element="th">Name</Type><Type element="th">Amount</Type><Type element="th">Date</Type></tr>
          </thead>
          <tbody>
            {data.map((row, i) => (
              <tr key={i}><Type element="td">{row.name}</Type><Type element="td">{row.amount}</Type><Type element="td">{row.date}</Type></tr>
            ))}
          </tbody>
        </Table>
      </SectionItem>
      <SectionItem>
        <Pagination
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
        />
      </SectionItem>
    </Section>
  );
};
```

---

### Radio Column Table (Single-Select Rows)

**MCA1**: Table with radio button column — only one row can be selected.

**Blueprint-React**: Manage single selection with `useState<string>`.

```typescript
import React, { useState } from 'react';
import { Table, Type } from '@barclays/blueprint-react';

interface RowData { id: string; name: string; amount: string; }

export const RadioTable: React.FC<{ data: RowData[]; onSelect: (id: string) => void }> = ({ data, onSelect }) => {
  const [selected, setSelected] = useState<string>('');

  const handleSelect = (id: string) => {
    setSelected(id);
    onSelect(id);
  };

  return (
    <Table equalPadding headingVariant="default">
      <thead>
        <tr><th></th><Type element="th">Name</Type><Type element="th">Amount</Type></tr>
      </thead>
      <tbody>
        {data.map(row => (
          <tr key={row.id}>
            <td>
              <input
                type="radio"
                name="tableRadio"
                checked={selected === row.id}
                onChange={() => handleSelect(row.id)}
                aria-label={`Select ${row.name}`}
              />
            </td>
            <Type element="td">{row.name}</Type>
            <Type element="td">{row.amount}</Type>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};
```
