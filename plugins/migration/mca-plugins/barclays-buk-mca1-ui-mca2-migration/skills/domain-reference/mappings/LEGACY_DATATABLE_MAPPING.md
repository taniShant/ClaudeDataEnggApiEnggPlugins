# LEGACY_DATATABLE_MAPPING.md

## Overview

Maps MCA1 legacy DataTable components (`.scpTable()` jQuery plugin with DataTables options) to Blueprint-React `Table` + `Pagination` + custom hooks. Covers 6 legacy variants: basic, accordion, pagination, sorting, filtering, and row-delete.

**Note:** The Web Component `<mca-table>` variants are covered in `BDL_TABLE_MAPPING.md`. This file covers only the jQuery `.scpTable()` plugin variants.

---

## Detection Patterns

```grep
\.scpTable\(
steal\("scp/ui/common/vendor/datatable/scp-datatable\.js"\)
styleOnly
paginate.*on
aoColumns
aoColumnDefs
sPaginationType
aLengthMenu
bSortable
bSearchable
sType.*date
confirmDelete
beforeRowDeleteFunction
afterRowDeleteFunction
dateTimeFormats
scp-expandable-trigger
delete_table_row
```

---

## Conversion: steal() → ES imports

```javascript
// MCA1
steal("scp/ui/common/vendor/datatable/scp-datatable.js").then(function() {
  $("#tableList").scpTable({ styleOnly: true });
});

// MCA2
import { Table, Pagination, Type, Button, Icon } from '@barclays/blueprint-react';
```

---

## Component: Basic Table (styleOnly)

### MCA1 Pattern

```javascript
$("#tableList").scpTable({ styleOnly: true });
```

```html
<table id="tableList">
  <thead><tr><th>Name</th><th>Position</th><th>Office</th></tr></thead>
  <tbody>
    <tr><td>John Smith</td><td>Developer</td><td>London</td></tr>
  </tbody>
</table>
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Table, Type } from '@barclays/blueprint-react';

export const BasicTable: React.FC = () => (
  <Table>
    <table>
      <thead>
        <tr>
          <th><Type weight="medium">Name</Type></th>
          <th><Type weight="medium">Position</Type></th>
          <th><Type weight="medium">Office</Type></th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><Type>John Smith</Type></td>
          <td><Type>Developer</Type></td>
          <td><Type>London</Type></td>
        </tr>
      </tbody>
    </table>
  </Table>
);
```

---

## Component: Table with Sorting

### MCA1 Pattern

```javascript
$("#tableDateTime").scpTable({
  dateTimeFormats: ['DD/MM/YY HH:MM:SS', 'DD-MM-YYYY HH:MM'],
  sort: { on: true, defaults: [[2, "desc"]] },
  aoColumns: [
    { bSortable: true },
    { bSortable: true },
    { sType: "date-eu" }
  ]
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState, useMemo } from 'react';
import { Table, Type, Icon } from '@barclays/blueprint-react';

interface RowData {
  name: string;
  position: string;
  date: string;
}

type SortDirection = 'asc' | 'desc' | null;

const parseDate = (dateStr: string): Date => {
  const [day, month, year] = dateStr.split('/');
  return new Date(Number(year), Number(month) - 1, Number(day));
};

export const SortableTable: React.FC<{ data: RowData[] }> = ({ data }) => {
  const [sortCol, setSortCol] = useState<number>(2);
  const [sortDir, setSortDir] = useState<SortDirection>('desc');

  const handleSort = (colIndex: number) => {
    if (sortCol === colIndex) {
      setSortDir(sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? null : 'asc');
    } else {
      setSortCol(colIndex);
      setSortDir('asc');
    }
  };

  const sorted = useMemo(() => {
    if (sortDir === null) return data;
    return [...data].sort((a, b) => {
      const keys: (keyof RowData)[] = ['name', 'position', 'date'];
      const key = keys[sortCol];
      let comparison: number;
      if (key === 'date') {
        comparison = parseDate(a.date).getTime() - parseDate(b.date).getTime();
      } else {
        comparison = a[key].localeCompare(b[key]);
      }
      return sortDir === 'desc' ? -comparison : comparison;
    });
  }, [data, sortCol, sortDir]);

  const SortIcon: React.FC<{ col: number }> = ({ col }) => {
    if (sortCol !== col || sortDir === null) return null;
    return <Icon icon={sortDir === 'asc' ? 'chevron-up' : 'chevron-down'} size="xs" />;
  };

  return (
    <Table>
      <table>
        <thead>
          <tr>
            <th onClick={() => handleSort(0)} style={{ cursor: 'pointer' }}>
              <Type weight="medium">Name <SortIcon col={0} /></Type>
            </th>
            <th onClick={() => handleSort(1)} style={{ cursor: 'pointer' }}>
              <Type weight="medium">Position <SortIcon col={1} /></Type>
            </th>
            <th onClick={() => handleSort(2)} style={{ cursor: 'pointer' }}>
              <Type weight="medium">Date <SortIcon col={2} /></Type>
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => (
            <tr key={i}>
              <td><Type>{row.name}</Type></td>
              <td><Type>{row.position}</Type></td>
              <td><Type>{row.date}</Type></td>
            </tr>
          ))}
        </tbody>
      </table>
    </Table>
  );
};
```

---

## Component: Table with Pagination

### MCA1 Pattern

```javascript
$("#tablePaginat").scpTable({
  paginate: { on: true },
  sPaginationType: "full_numbers",
  aLengthMenu: [[10, 20, 40, 100, -1], [10, 20, 40, 100, "All"]],
  sort: { on: true, defaults: [[2, "desc"]] },
  aoColumns: [{ bSortable: true }, { bSortable: true }, { sType: "date-euro" }]
});
```

### Blueprint-React Equivalent

**Preferred approach:** Use the published `PaginatedTable` from `@barclays/mca-ui-common-utils-paginated-table` (see [BDL_TABLE_MAPPING.md](./BDL_TABLE_MAPPING.md) "Paginated Table" section for full documentation).

```typescript
import { PaginatedTable } from '@barclays/mca-ui-common-utils-paginated-table';
import '@barclays/mca-ui-common-utils-paginated-table/dist/paginated-table.module.css';

interface RowData {
  name: string;
  position: string;
  office: string;
}

export const PaginatedDataTable: React.FC<{ data: RowData[] }> = ({ data }) => (
  <PaginatedTable
    headers={['Name', 'Position', 'Office']}
    headingVariant="secondary"
    indexWithMaxWidth={0}
    rowsPerPage={10}
    allRows={data.map(row => ({
      code: row.name,
      decode: row.name,
      details: [
        { type: 'text' as const, value: row.name },
        { type: 'text' as const, value: row.position },
        { type: 'text' as const, value: row.office },
      ],
    }))}
  />
);
```

**Fallback (when the package is unavailable):** If the project cannot use the published package, use Blueprint `<Table>` + `<Pagination>` with manual slicing:

```typescript
import React, { useState, useMemo } from 'react';
import { Table, Pagination, Type } from '@barclays/blueprint-react';

interface RowData {
  name: string;
  position: string;
  office: string;
}

export const PaginatedTable: React.FC<{ data: RowData[] }> = ({ data }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(10);

  const totalPages = Math.ceil(data.length / pageSize);
  const paginatedData = useMemo(
    () => data.slice((currentPage - 1) * pageSize, currentPage * pageSize),
    [data, currentPage, pageSize]
  );

  return (
    <>
      <Table headingVariant="secondary" squareBottomBorders>
        <thead>
          <tr>
            <Type element="th" weight="medium">Name</Type>
            <Type element="th" weight="medium">Position</Type>
            <Type element="th" weight="medium">Office</Type>
          </tr>
        </thead>
        <tbody>
          {paginatedData.map((row, i) => (
            <tr key={i}>
              <Type element="td">{row.name}</Type>
              <Type element="td">{row.position}</Type>
              <Type element="td">{row.office}</Type>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pagination
        totalItems={totalPages}
        activeIndex={currentPage}
        ariaLabel="table-pagination"
        onButtonClick={setCurrentPage}
      />
    </>
  );
};
```

---

## Component: Table with Filter/Search

### MCA1 Pattern

```javascript
$("#scptable-filter").scpTable({
  title: "Employees",
  filter: { on: true, label: "Search for payee:", labelDisplay: false },
  noHeader: true,
  zeroRecords: "No matching records found",
  aoColumns: [
    { "bSearchable": true },
    { "bSearchable": false },
    { "bSearchable": false }
  ]
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState, useMemo } from 'react';
import { Table, FormItem, FormInput, Type, Section, SectionItem } from '@barclays/blueprint-react';

interface RowData {
  name: string;
  amount: string;
  date: string;
}

export const FilterableTable: React.FC<{ data: RowData[] }> = ({ data }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = useMemo(
    () => data.filter((row) => row.name.toLowerCase().includes(searchTerm.toLowerCase())),
    [data, searchTerm]
  );

  return (
    <Section>
      <SectionItem>
        <FormItem
          label={<Type>Search for payee</Type>}
          render={(props) => (
            <FormInput
              {...props}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search..."
            />
          )}
        />
        <Table>
          <table>
            <tbody>
              {filtered.length === 0 ? (
                <tr><td><Type>No matching records found</Type></td></tr>
              ) : (
                filtered.map((row, i) => (
                  <tr key={i}>
                    <td><Type>{row.name}</Type></td>
                    <td><Type>{row.amount}</Type></td>
                    <td><Type>{row.date}</Type></td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </Table>
      </SectionItem>
    </Section>
  );
};
```

---

## Component: Accordion Table (Expandable Rows)

### MCA1 Pattern

```javascript
$("#tableExpand").scpTable({
  sort: { on: true, defaults: [[2, "desc"]] },
  aoColumnDefs: [{ "bSortable": false, "aTargets": [0] }],
  aoColumns: [{ bSortable: true }, { bSortable: true }, { sType: "date-eu" }]
});
```

```html
<tr>
  <td class="scp-expandable-trigger scp-clickable">
    <span class="scp-expandableTriggerSignClass">+</span>
  </td>
  <td>Row data</td>
</tr>
<tr class="scp-hide scp-c-details" data-details="#detail1">
  <td colspan="3">Expanded detail content</td>
</tr>
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Table, Type, Icon, Button } from '@barclays/blueprint-react';

interface RowData {
  id: string;
  name: string;
  position: string;
  details: string;
}

export const AccordionTable: React.FC<{ data: RowData[] }> = ({ data }) => {
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const toggleRow = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <Table>
      <table>
        <thead>
          <tr>
            <th style={{ width: '40px' }}></th>
            <th><Type weight="medium">Name</Type></th>
            <th><Type weight="medium">Position</Type></th>
          </tr>
        </thead>
        <tbody>
          {data.map((row) => (
            <React.Fragment key={row.id}>
              <tr>
                <td>
                  <Button variant="subtle" onClick={() => toggleRow(row.id)}>
                    <Icon icon={expanded.has(row.id) ? 'chevron-down' : 'chevron-right'} size="sm" />
                  </Button>
                </td>
                <td><Type>{row.name}</Type></td>
                <td><Type>{row.position}</Type></td>
              </tr>
              {expanded.has(row.id) && (
                <tr>
                  <td colSpan={3}>
                    <Type>{row.details}</Type>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </Table>
  );
};
```

---

## Component: Table with Row Delete

### MCA1 Pattern

```javascript
$("#tableDeleteRows").scpTable({
  beforeRowDeleteFunction: function() { /* return false to cancel */ },
  confirmDelete: true,
  confirmDeleteMsg: "Are you sure you want to delete?",
  afterRowDeleteFunction: function() { /* cleanup */ }
});
```

```html
<td class="delete_table_row">
  <a href="javascript:void(0);" class="scp-clickable">Delete</a>
</td>
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Table, Type, Button, Icon, Dialog } from '@barclays/blueprint-react';

interface RowData {
  id: string;
  name: string;
  position: string;
}

export const DeletableTable: React.FC<{ initialData: RowData[] }> = ({ initialData }) => {
  const [data, setData] = useState(initialData);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const handleDelete = () => {
    if (deleteTarget) {
      setData((prev) => prev.filter((row) => row.id !== deleteTarget));
      setDeleteTarget(null);
    }
  };

  return (
    <>
      <Table>
        <table>
          <thead>
            <tr>
              <th><Type weight="medium">Name</Type></th>
              <th><Type weight="medium">Position</Type></th>
              <th style={{ width: '80px' }}></th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.id}>
                <td><Type>{row.name}</Type></td>
                <td><Type>{row.position}</Type></td>
                <td>
                  <Button variant="subtle" onClick={() => setDeleteTarget(row.id)}>
                    <Icon icon="delete" size="sm" />
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Table>
      <Dialog
        open={deleteTarget !== null}
        onClose={() => setDeleteTarget(null)}
        head={<Type element="h3" size="md" weight="medium">Confirm Delete</Type>}
        foot={
          <>
            <Button variant="secondary" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button variant="primary" onClick={handleDelete}>Delete</Button>
          </>
        }
      >
        <Type>Are you sure you want to delete?</Type>
      </Dialog>
    </>
  );
};
```

---

## Options → Props/State Mapping

| MCA1 Option | React Equivalent | Notes |
|-------------|-----------------|-------|
| `styleOnly: true` | Just use `<Table>` wrapper | No plugin behavior needed |
| `sort.on: true` | `useState` for sortCol/sortDir + `useMemo` | Custom sorting hook |
| `sort.defaults: [[col, dir]]` | Initial state values | Set in `useState` initializer |
| `paginate.on: true` | `<Pagination>` component + slice state | Separate component below table |
| `sPaginationType: "full_numbers"` | Default `<Pagination>` behavior | Always full numbers in Blueprint |
| `aLengthMenu` | `<FormSelect>` for page size | Controlled state for pageSize |
| `filter.on: true` | `<FormInput>` + `useMemo` filter | Manual filter implementation |
| `filter.label` | `label` prop on `FormItem` | Wrap filter input |
| `noHeader: true` | Omit `<thead>` | Don't render header row |
| `zeroRecords` | Conditional render in tbody | Show message when filtered empty |
| `aoColumns[].bSortable` | Make header non-clickable | Skip sort handler for that column |
| `aoColumns[].bSearchable` | Filter only specific fields | Filter function checks specific keys |
| `aoColumns[].sType: "date-eu"` | Custom date comparator | Parse DD/MM/YYYY in sort |
| `confirmDelete: true` | `<Dialog>` confirmation | Show dialog before deletion |
| `beforeRowDeleteFunction` | Logic before `setData` filter | Check/cancel deletion |
| `afterRowDeleteFunction` | Effect after state update | `useEffect` watching data length |
| `dateTimeFormats` | Custom parse function | Handle multiple date formats |

---

## Iron Rules

1. **Blueprint `Table` is a styling wrapper around standard HTML `<table>`** — use `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` inside it
2. **No `TableRow`, `TableCell`, `TableHead` sub-components exist** — they are NOT in Blueprint
3. **Sorting, filtering, pagination are NOT built into Table** — implement with hooks and state
4. **Use `<Pagination>` component for pagination** — placed outside and below the `<Table>`
5. **Date sorting requires custom parse functions** — Blueprint has no built-in date type handling
6. **Row delete requires confirmation Dialog** — use state-driven Dialog, not `window.confirm()`
7. **Accordion rows use `React.Fragment` + conditional render** — not CSS show/hide classes
8. **`aoColumnDefs` / `aoColumns` → individual column config in component** — no DataTables plugin equivalent
