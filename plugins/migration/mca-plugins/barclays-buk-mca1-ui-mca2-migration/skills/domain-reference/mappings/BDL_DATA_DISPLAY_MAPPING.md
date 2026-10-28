# BDL Data Display to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Data Display

### Info Pairs

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-info-container>` + `<mca-infopair>` | `<DescriptionList>` or `<Section>` + `<Type>` |
| `<mca-info-container size="N">` | `<Grid>` with `<Grid.Col>` wrapping each group |

#### Basic InfoPair Before/After

**MCA1 (Before)**:
```html
<mca-infopair id="b_infopair" label="Infopair Label">
  pneumonoultramicroscopicsilicovolcanoconiosis
</mca-infopair>
```

**Blueprint-React (After)**:
```typescript
<>
  <Type weight='bold' color='title'>
    Infopair Label
  </Type>
  <Type>pneumonoultramicroscopicsilicovolcanoconiosis</Type>
</>
```

#### Complex InfoPair Container with Multiple Items

**MCA1 (Before)**:
```html
<mca-info-container id="b_info-container_size_1" size="1">
  <mca-infopair label="Infopair Label 1">
    This is inforpair 1 description
  </mca-infopair>
  <mca-infopair label="Infopair Label 2">
    This is inforpair 2 description
  </mca-infopair>
  <mca-infopair label="Infopair Label 3">
    This is inforpair 3 description
  </mca-infopair>
  <mca-infopair label="Infopair Label 4">
    This is inforpair 4 description
  </mca-infopair>
</mca-info-container>
```

**Blueprint-React (After)**:
```typescript
<Grid id="b_info-container_size_1">
  <Grid.Col>
    <Type weight='bold' color='title'>Infopair Label 1</Type>
    <Type>This is inforpair 1 description</Type>
  </Grid.Col>
  <Grid.Col>
    <Type weight='bold' color='title'>Infopair Label 2</Type>
    <Type>This is inforpair 2 description</Type>
  </Grid.Col>
  <Grid.Col>
    <Type weight='bold' color='title'>Infopair Label 3</Type>
    <Type>This is inforpair 3 description</Type>
  </Grid.Col>
  <Grid.Col>
    <Type weight='bold' color='title'>Infopair Label 4</Type>
    <Type>This is inforpair 4 description</Type>
  </Grid.Col>
</Grid>
```

#### InfoPair Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `label` | `<dt>` content | `DescriptionList` | Wrap in `<Type weight="bold" color="title">` |
| Children | `<dd>` content | `DescriptionList` | Wrap in `<Type>` |
| `id` | `id` | Container | Pass through to the wrapping element |

#### `<mca-info-container>` with Grid Layout

When `<mca-info-container>` uses a `size` attribute to arrange infopairs in columns, use `<Grid>` with `<Grid.Col>` in Blueprint-React.

**MCA1 (Before)**:
```html
<mca-info-container size="3">
    <mca-infopair label="Sort code">12-34-56</mca-infopair>
    <mca-infopair label="Account number">12345678</mca-infopair>
    <mca-infopair label="Balance">$1,234.56</mca-infopair>
</mca-info-container>
```

**Blueprint-React (After)**:
```typescript
<Grid>
  <Grid.Col span={4}>
    <DescriptionList>
      <dt><Type element="span" weight="bold" color="title">Sort code</Type></dt>
      <dd><Type element="span">12-34-56</Type></dd>
    </DescriptionList>
  </Grid.Col>
  <Grid.Col span={4}>
    <DescriptionList>
      <dt><Type element="span" weight="bold" color="title">Account number</Type></dt>
      <dd><Type element="span">12345678</Type></dd>
    </DescriptionList>
  </Grid.Col>
  <Grid.Col span={4}>
    <DescriptionList>
      <dt><Type element="span" weight="bold" color="title">Balance</Type></dt>
      <dd><Type element="span">$1,234.56</Type></dd>
    </DescriptionList>
  </Grid.Col>
</Grid>
```

The `size` attribute maps to Grid column spans: `size="3"` means 3 columns, so each `Grid.Col` gets `span={12/3}` = `span={4}` (Grid uses a 12-column system).

### Tables

Table mapping is in a separate file: **[BDL_TABLE_MAPPING.md](BDL_TABLE_MAPPING.md)**

### Lists

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-list type="unordered">` | `<Ul>` (from `@barclays/blueprint-react`) |
| `<mca-list type="ordered">` | `<Ol>` (from `@barclays/blueprint-react`) |
| `<mca-list-item>` | `<Li>` (from `@barclays/blueprint-react`) |

**Important**: Use Blueprint `<Ul>`, `<Ol>`, and `<Li>` components from `@barclays/blueprint-react` -- NOT standard HTML `<ul>`, `<ol>`, `<li>` elements.

#### List Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `type="unordered"` | Use `<Ul>` | Default list type |
| `type="ordered"` | Use `<Ol>` | Numbered list |
| `id` | `id` | Pass through |
| `class` | `className` | Standard React prop |

#### Unordered List Before/After

**MCA1 (Before)**:
```html
<mca-list type="unordered">
    <mca-list-item>First item</mca-list-item>
    <mca-list-item>Second item</mca-list-item>
    <mca-list-item>Third item</mca-list-item>
</mca-list>
```

**Blueprint-React (After)**:
```typescript
<Ul>
  <Li><Type>First item</Type></Li>
  <Li><Type>Second item</Type></Li>
  <Li><Type>Third item</Type></Li>
</Ul>
```

#### Ordered List Before/After

**MCA1 (Before)**:
```html
<mca-list type="ordered">
    <mca-list-item>Step one</mca-list-item>
    <mca-list-item>Step two</mca-list-item>
    <mca-list-item>Step three</mca-list-item>
</mca-list>
```

**Blueprint-React (After)**:
```typescript
<Ol>
  <Li><Type>Step one</Type></Li>
  <Li><Type>Step two</Type></Li>
  <Li><Type>Step three</Type></Li>
</Ol>
```

### Progress Bar

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-progressbar>` | `<Progress>` |

#### Progress Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `steps` / child elements | `steps` (array) | Array of `{ name: string, state: string }` objects |
| `numbered` | `numbered` | Boolean; shows step numbers |
| `label` | `progressLabel` | Label displayed alongside the progress |
| `variant` | `variant` | `"default"` or other supported variants |
| `id` | `id` | Pass through |

Step `state` values: `"Incomplete"`, `"Active"`, `"Complete"`

#### Progress Bar Before/After

**MCA1 (Before)**:
```html
<mca-progressbar numbered label="Step">
    <mca-progress-step name="Alpha" state="complete"></mca-progress-step>
    <mca-progress-step name="Beta" state="active"></mca-progress-step>
    <mca-progress-step name="Gamma" state="incomplete"></mca-progress-step>
</mca-progressbar>
```

**Blueprint-React (After)**:
```typescript
<Progress
  numbered
  progressLabel="Step"
  steps={[
    { name: 'Alpha', state: 'Complete' },
    { name: 'Beta', state: 'Active' },
    { name: 'Gamma', state: 'Incomplete' }
  ]}
  variant="default"
/>
```

**Note**: In Blueprint-React, step state values are capitalized (`"Complete"`, `"Active"`, `"Incomplete"`). The `steps` prop accepts an array of objects rather than child elements.
