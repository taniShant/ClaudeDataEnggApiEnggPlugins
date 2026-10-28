# MCA2 Page Layout & Component Composition Patterns

**Last Updated**: July 20, 2026
**Source**: Production MCA2 application (`mca-ui-appointment-booking/packages/my-diary`)

---

## Overview

This guide documents the canonical page composition patterns used in production MCA2 applications. When migrating from MCA1, the generated output MUST follow these patterns for consistent spacing, layout, and component hierarchy.

---

## 1. Page-Level Composition Recipe

Every MCA2 page follows this hierarchy (outside-to-inside):

```
<div>                                    ← Root wrapper (plain, no classes)
  ├─ Loading Gate                        ← Show <Spinner /> or content
  ├─ <Grid>                              ← Main content area
  │   ├─ <Section>                       ← Semantic content grouping
  │   │   └─ <SectionItem>              ← Vertical spacing unit
  │   │       └─ Content (headings, forms, tables, buttons)
  │   ├─ <Section variant='secondary'>  ← Highlighted sections
  │   └─ More sections...
  │
  ├─ Modals/Dialogs                      ← Always at page root, AFTER content
  └─ Accessibility spacers              ← Hidden focus targets
</div>
```

### Complete Page Skeleton

```typescript
import React, { useState } from 'react';
import {
  Grid, Section, SectionItem, Type, Button, Table, Spinner,
  Form, FormSection, FormItem, FormInput, ButtonGroup
} from '@barclays/blueprint-react';

const MyPage: React.FC = () => {
  const { data, isLoading, isError, error } = useGetDataQuery();

  // Error state — return early
  if (!isLoading && isError) {
    return <ErrorPageApiFailure error={error} />;
  }

  return (
    <div>
      {isLoading ? (
        <Spinner />
      ) : (
        <Grid>
          {/* Section 1: Page heading */}
          <Grid.Col>
            <Section>
              <SectionItem>
                <Type element="h2" size="2xl" marginBottom="md" color="title" weight="medium">
                  Page Title
                </Type>
              </SectionItem>
            </Section>
          </Grid.Col>

          {/* Section 2: Main content */}
          <Grid.Col>
            <Section>
              <SectionItem>
                {/* Forms, tables, content here */}
              </SectionItem>
            </Section>
          </Grid.Col>

          {/* Section 3: Action buttons (footer) */}
          <Grid.Col>
            <Section>
              <SectionItem>
                <Grid>
                  <Grid.Col fill>
                    <Button onClick={handleBack}>Back</Button>
                  </Grid.Col>
                  <Grid.Col fit>
                    <Button variant="primary" onClick={handleSubmit}>Submit</Button>
                  </Grid.Col>
                </Grid>
              </SectionItem>
            </Section>
          </Grid.Col>
        </Grid>
      )}

      {/* Modals always at root, after main content */}
      {isDialogOpen && (
        <Dialog isOpen={isDialogOpen} onClickDismiss={closeDialog} ... />
      )}
    </div>
  );
};
```

---

## 2. Section & SectionItem Spacing

### Rules

| Pattern | When to Use |
|---------|-------------|
| `<Section>` | Group semantically related content blocks |
| `<Section variant='secondary'>` | Highlight important information (gray background) |
| `<Section paddingBlock={false}>` | Inline banners/alerts without extra padding |
| `<SectionItem>` | Default vertical spacing between items |
| `<SectionItem spacingTop='sm'>` | Extra spacing above (e.g., before button rows) |
| `<SectionItem spacingBottom='sm'>` | Extra spacing below (e.g., between major blocks) |

### Spacing Values

| Value | Approximate Size | Use Case |
|-------|-----------------|----------|
| `xs` | 4–6px | Minimal: between related inline items |
| `sm` | 8–12px | Small: between paragraphs, before/after buttons |
| `md` | 16–20px | Medium: between unrelated blocks (MOST COMMON) |
| `lg` | 24–32px | Large: major section breaks, page title bottom margin |

### Canonical Example

```typescript
<Section>
  <SectionItem>
    <Type element="h2" size="2xl" marginBottom="md" color="title" weight="medium">
      Appointment Details
    </Type>
  </SectionItem>

  <SectionItem spacingBottom="sm">
    {/* Table content */}
    <Table headingVariant="secondary" equalPadding>
      ...
    </Table>
  </SectionItem>

  <SectionItem spacingTop="sm">
    {/* Action buttons */}
    <Grid>
      <Grid.Col fill>
        <Button onClick={handleBack}>Back</Button>
      </Grid.Col>
      <Grid.Col fit>
        <Button variant="primary" onClick={handleConfirm}>Confirm</Button>
      </Grid.Col>
    </Grid>
  </SectionItem>
</Section>
```

---

## 3. Grid Layout Patterns

### Horizontal Layout with Grid.Col

```typescript
// Equal columns (50/50)
<Grid>
  <Grid.Col size="6of12">{/* Left */}</Grid.Col>
  <Grid.Col size="6of12">{/* Right */}</Grid.Col>
</Grid>

// Icon + content (auto + fill)
<Grid>
  <Grid.Col fit><Icon icon="calendar" size="md" /></Grid.Col>
  <Grid.Col fill>{/* Content fills remaining space */}</Grid.Col>
</Grid>

// Button footer (fill left, fit right)
<Grid>
  <Grid.Col fill><Button>Back</Button></Grid.Col>
  <Grid.Col fit><Button variant="primary">Submit</Button></Grid.Col>
</Grid>

// Button alignment at baseline
<Grid flex="fit" alignment="bottom">
  <Grid.Col>{/* Form field */}</Grid.Col>
  <Grid.Col>{/* Button aligns to field bottom */}</Grid.Col>
</Grid>
```

### Common Grid.Col Sizes

| Size | Width | Use Case |
|------|-------|----------|
| `fit` | Auto (content width) | Icons, buttons, fixed-width items |
| `fill` | Remaining space | Main content areas, text that should expand |
| `3of12` | 25% | Compact display columns |
| `4of12` | 33% | Three-column layouts |
| `5of12` | ~42% | Flexible multi-column |
| `6of12` | 50% | Two-column forms, radio pairs |

---

## 4. Button Placement & Variants

### Button Variant Usage

| Variant | Status | When to Use |
|---------|--------|-------------|
| `variant="primary"` | default | Main CTA — submit, confirm, save |
| `variant="secondary"` | default | Secondary actions — back, cancel |
| `variant="subtle"` | default | Minimal styling — edit, view |
| `variant="secondary"` | `status="danger"` | Destructive secondary — cancel appointment |
| `variant="subtle"` | `status="danger"` | Destructive minimal — delete |

### Button Positioning Rules

```typescript
// Page footer pattern — Back on left, primary action on right
<Grid>
  <Grid.Col fill>
    <Button onClick={handleBack}>Back</Button>
  </Grid.Col>
  <Grid.Col fit>
    <ButtonGroup>
      <Button variant="subtle" status="danger" onClick={handleCancel}>
        Cancel
      </Button>
      <Button variant="subtle" onClick={handleEdit}>
        Edit
      </Button>
    </ButtonGroup>
  </Grid.Col>
  <Grid.Col fit>
    <Button variant="primary" onClick={handleConfirm}>
      Confirm
    </Button>
  </Grid.Col>
</Grid>
```

### Button Sizing Rules

| Context | Size | Reason |
|---------|------|--------|
| Page-level actions (footer) | default (no size prop) | Consistent with form field heights |
| Inside table cells | `size="sm"` | Compact for table row density |
| Inline within Section content | `size="sm"` | When accompanying text-level content |

---

## 5. Form Layout Patterns

### Standard Form Structure

```typescript
<Form onSubmit={handleSubmit}>
  <FormSection widthLg="4of12" widthMd="6of12">
    <FormItem
      label={<Type>Field Label</Type>}
      error={isError && <Type role="alert" color="error">{errorMessage}</Type>}
      render={renderProps => (
        <FormInput
          value={inputState.val}
          onChange={inputState.handleValChange}
          onBlur={inputState.handleOnBlur}
          {...renderProps}
        />
      )}
    />
  </FormSection>
</Form>
```

### FormSection Width Guidelines

| Layout | widthLg | widthMd | Use Case |
|--------|---------|---------|----------|
| Narrow form | `4of12` | `6of12` | Single field, short inputs |
| Medium form | `6of12` | `8of12` | Two fields side by side |
| Wide form | `8of12` | `12of12` | Multi-field rows, text areas |
| Full width | omit | omit | Single fields on their own |

### Multi-Field Form Row (Date range + Filter button)

```typescript
<FormSection widthLg="4of12" widthMd="6of12">
  <Grid flex="fill" alignment="bottom">
    <Grid.Col>
      <FormItem
        label={<Type>Date From</Type>}
        render={renderProps => (
          <FormInput
            type="date"
            value={fromDate.val}
            onChange={fromDate.handleValChange}
            media={<Icon icon="calendar" size="sm" />}
            {...renderProps}
          />
        )}
      />
    </Grid.Col>
    <Grid.Col>
      <FormItem
        label={<Type>Date To</Type>}
        render={renderProps => (
          <FormInput
            type="date"
            value={toDate.val}
            onChange={toDate.handleValChange}
            media={<Icon icon="calendar" size="sm" />}
            {...renderProps}
          />
        )}
      />
    </Grid.Col>
    <Grid.Col>
      <Button onClick={handleFilter}>Filter</Button>
    </Grid.Col>
  </Grid>
</FormSection>
```

### Radio Button Group Layout

```typescript
<FormMultiItem
  required
  label={<Type color="title" weight="medium">Select Status</Type>}
  render={renderOptions => (
    <Grid>
      <Grid.Col size="6of12">
        <FormRadio
          name="status"
          label="Active"
          value="active"
          checked={status === 'active'}
          onChange={handleChange}
          {...renderOptions}
        />
      </Grid.Col>
      <Grid.Col size="6of12">
        <FormRadio
          name="status"
          label="Inactive"
          value="inactive"
          checked={status === 'inactive'}
          onChange={handleChange}
          {...renderOptions}
        />
      </Grid.Col>
    </Grid>
  )}
/>
```

---

## 6. Table Layout Patterns

### Standard Data Table

```typescript
<Table headingVariant="secondary" columnBorders equalPadding>
  <thead>
    <tr>
      <Type element="th" color="title" weight="medium" alignment="left">
        Name
      </Type>
      <Type element="th" color="title" weight="medium" alignment="left">
        Date
      </Type>
      <Type element="th" color="title" weight="medium" alignment="right">
        Status
      </Type>
    </tr>
  </thead>
  <tbody>
    {data.map((item, index) => (
      <tr key={index}>
        <Type element="td" color="title" alignment="left">
          {item.name}
        </Type>
        <Type element="td" color="title" alignment="left">
          {formatDate(item.date)}
        </Type>
        <Type element="td" alignment="right">
          {item.status}
        </Type>
      </tr>
    ))}
  </tbody>
</Table>
```

### Table Header Props (Production Pattern)

All `<th>` cells in production MCA2 apps use:
- `color="title"` — dark navy text for emphasis
- `weight="medium"` — 600 font weight for visual hierarchy
- `alignment="left"` or `alignment="right"` — explicit alignment

### Table with Action Buttons

```typescript
<tr>
  <Type element="td" color="title" alignment="left">{item.name}</Type>
  <Type element="td" color="title" alignment="left">{item.date}</Type>
  <td style={{ width: '1%', whiteSpace: 'nowrap' }}>
    <Button variant="secondary" size="sm" onClick={() => handleEdit(item.id)}>
      Edit
    </Button>
  </td>
</tr>
```

### Table with Status Icons (Media Component)

```typescript
<td style={{ width: '1%', whiteSpace: 'nowrap' }}>
  <Media
    prefix={
      <Media.Prefix>
        <Icon
          icon={item.success ? 'tick' : 'dismiss'}
          size="sm"
          status={item.success ? 'success' : 'error'}
        />
      </Media.Prefix>
    }
  >
    <Type
      color={item.success ? 'success' : 'error'}
      alignment="left"
      weight="medium"
    >
      {item.success ? 'Successful' : 'Unsuccessful'}
    </Type>
  </Media>
</td>
```

### Table Wrapper in Page

Tables are always wrapped in a `<SectionItem>` for proper vertical spacing:

```typescript
<Section>
  <SectionItem spacingBottom="sm">
    <Table headingVariant="secondary" equalPadding>
      {/* Table content */}
    </Table>
  </SectionItem>
  <SectionItem>
    {/* Pagination below table */}
    <Type alignment="center">
      <Pagination
        totalItems={Math.ceil(data.length / rowsPerPage)}
        activeIndex={currentPage}
        ariaLabel="table-pagination"
        onButtonClick={setCurrentPage}
      />
    </Type>
  </SectionItem>
</Section>
```

---

## 7. Loading, Error & Empty States

### Loading Gate (Page Level)

```typescript
// Combine ALL loading flags into one boolean
const isPageLoading =
  isFetching ||
  updateResult.isLoading ||
  deleteResult.isLoading;

// In render:
return (
  <div>
    {isPageLoading ? <Spinner /> : <Grid>{/* Content */}</Grid>}
  </div>
);
```

### Error State (Early Return)

```typescript
if (!isLoading && isError) {
  return <ErrorPageApiFailure error={error} />;
}
```

### Empty State

```typescript
{!isFetching && isSuccess && data.length === 0 && (
  <Grid.Col>
    <Type size="md" weight="medium" color="title" marginBottom="xs">
      No appointments found
    </Type>
    <Type>Try adjusting your date range or filters.</Type>
  </Grid.Col>
)}
```

### Success Banner

```typescript
{isSuccess && showBanner && (
  <BarclaysMicroThemeSuccess>
    <Box>
      <Section paddingBlock={false}>
        <SlimBanner
          onDismiss={closeBanner}
          media={<Icon icon="success-fill" size="sm" />}
        >
          <Type>Operation completed successfully.</Type>
        </SlimBanner>
      </Section>
    </Box>
  </BarclaysMicroThemeSuccess>
)}
```

---

## 8. Dialog & Modal Patterns

### Dialog (Confirmation)

```typescript
// Render at page root, after main content
{isConfirmDialogOpen && (
  <Dialog
    isOpen={isConfirmDialogOpen}
    head={<Type element="h2" size="xl" weight="medium">Confirm Action</Type>}
    foot={
      <ButtonGroup>
        <Button variant="primary" onClick={handleConfirm}>Confirm</Button>
        <Button onClick={closeDialog}>Cancel</Button>
      </ButtonGroup>
    }
    onClickDismiss={closeDialog}
    onClickOverlay={closeDialog}
    onKeydownEscape={closeDialog}
  >
    <Type>Are you sure you want to proceed?</Type>
  </Dialog>
)}
```

### Modal (Complex Form)

```typescript
<Modal
  ref={modalRef}
  onClose={closeModal}
  title={
    <Type color="title" weight="medium" size="lg" marginBottom="sm">
      Modal Title
    </Type>
  }
>
  {isSubmitting ? (
    <Spinner />
  ) : (
    <Grid>
      <Grid.Col>
        <FormMultiItem label={...} render={...} />
      </Grid.Col>
      <Grid.Col>
        <ButtonGroup>
          <Button variant="primary" onClick={handleSubmit}>Submit</Button>
          <Button onClick={closeModal}>Cancel</Button>
        </ButtonGroup>
      </Grid.Col>
    </Grid>
  )}
</Modal>
```

---

## 9. Typography Hierarchy

### Heading Usage in Pages

| Level | Props | Use Case |
|-------|-------|----------|
| Page title | `element="h1" size="3xl" marginBottom="lg" color="title" weight="medium"` | Top-level page heading |
| Section heading | `element="h2" size="2xl" marginBottom="md" color="title" weight="medium"` | Major section titles |
| Subsection | `element="h2" size="md" color="title" weight="medium"` | Within-section headings |
| Table header | `element="th" color="title" weight="medium" alignment="left"` | Column headers |
| Label text | `color="title" weight="medium"` | Field labels, key in key-value pairs |
| Body text | `<Type>` (no extra props) | Regular content |
| Error text | `role="alert" color="error"` | Validation errors |

### Type marginBottom Usage

- `marginBottom="lg"` — After page titles
- `marginBottom="md"` — After section headings
- `marginBottom="sm"` — Between related text blocks
- `marginBottom="xs"` — Minimal: between label and value

---

## 10. Key-Value Display (DescriptionList)

For read-only data display:

```typescript
<DescriptionList>
  <dl>
    <dt>
      <Type color="title" weight="medium">Business Name</Type>
    </dt>
    <dd>
      <Type>{data.businessName}</Type>
    </dd>
  </dl>
  <dl>
    <dt>
      <Type color="title" weight="medium">Customer ID</Type>
    </dt>
    <dd>
      <Type>{data.customerId ?? 'N/A'}</Type>
    </dd>
  </dl>
</DescriptionList>
```

---

## 11. Accordion Sections

```typescript
<Accordion variant="secondary">
  <AccordionItem
    title={
      <Type element="h2" weight="medium" color="title">
        Overview of {formatDate(startDate)} - {formatDate(endDate)}
      </Type>
    }
  >
    <Grid flex="fill">
      <Grid.Col>
        <Type marginBottom="sm">Label</Type>
        <Type color="title" weight="medium">{value}</Type>
      </Grid.Col>
      <Grid.Col>
        <Type marginBottom="sm">Label</Type>
        <Type color="title" weight="medium">{value}</Type>
      </Grid.Col>
    </Grid>
  </AccordionItem>
</Accordion>
```

---

## 12. Common Anti-Patterns to Avoid

| ❌ Anti-Pattern | ✅ Correct Pattern |
|----------------|-------------------|
| Using `<div>` for spacing | Use `<Section>` + `<SectionItem>` |
| Inline style `marginBottom: '16px'` | Use `<SectionItem spacingBottom="sm">` or `<Type marginBottom="md">` |
| Bare text in JSX | Always wrap in `<Type>` |
| `<h2>Title</h2>` raw HTML heading | `<Type element="h2" size="2xl" marginBottom="md" color="title" weight="medium">` |
| Custom CSS for grid layout | Use `<Grid>` + `<Grid.Col>` |
| Buttons without Grid positioning | Use `<Grid.Col fill>` (left) / `<Grid.Col fit>` (right) |
| Default-size buttons in tables | Use `size="sm"` in all table cells |
| Modals inside component tree | Render modals at page root, after main content |
| Multiple loading states shown | Combine into single `isPageLoading` boolean |
| Error after content | Early return with error component |

---

## 13. Accessibility Patterns

1. **Focus management**: Restore focus to trigger element after modal/dialog close
2. **Screen readers**: Use `<ScreenReader>` for hidden context text
3. **Semantic elements**: Always set `element` prop on `<Type>` (h1, h2, th, td, p)
4. **ARIA**: `role="alert"` on error messages, `aria-label` on interactive areas
5. **Lists**: Use `role="list"` + `role="listitem"` for icon button groups
6. **Breadcrumbs**: Current page gets `aria-current="page"`

---

## Related Documentation

- [BLUEPRINT_REACT_CORRECT_PATTERNS.md](BLUEPRINT_REACT_CORRECT_PATTERNS.md) — Component API reference
- [FORM_LAYOUT_PATTERNS.md](FORM_LAYOUT_PATTERNS.md) — Form-specific layout rules
- [BDL_TABLE_MAPPING.md](../mappings/BDL_TABLE_MAPPING.md) — Table migration patterns
- [IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDE.md) — Documented mistakes and fixes
