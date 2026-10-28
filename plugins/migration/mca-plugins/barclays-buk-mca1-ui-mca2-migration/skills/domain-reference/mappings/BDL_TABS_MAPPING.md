# BDL Tabs to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Tabs (`<mca-tabs>` + `<mca-tab>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-tabs>` | `<Tabs>` |
| `<mca-tab>` | `<Tab>` |

**Rule**: Exactly ONE `<mca-tab>` must have `state="selected"` in BDL. In Blueprint-React, the active tab is controlled via `initialTabIndex` (uncontrolled) or `tabIndex` + `setTabIndex` (controlled).

### Comprehensive Tabs Example

**MCA1 (Before)**:
```html
<mca-tabs id="p-tabs-example-1">
  <mca-tab name="tabs 1">
    <p>Lorem ipsum dolor sit amet</p>
  </mca-tab>
  <mca-tab name="tabs 2" state="selected">
    <p>Lorem ipsum dolor sit amet</p>
    <mca-button>Submit</mca-button>
    <mca-button type="secondary">Cancel</mca-button>
  </mca-tab>
  <mca-tab name="tabs 3">
    <p>Lorem ipsum dolor sit amet</p>
    <mca-button type="critical">Remove</mca-button>
  </mca-tab>
  <mca-tab name="tabs 4">
    <p>Lorem ipsum dolor sit amet</p>
    <mca-button type="secondary">Cancel</mca-button>
  </mca-tab>
</mca-tabs>
```

**Blueprint-React (After)**:
```typescript
const [activeTab, setActiveTab] = useState<number>(1); // tabs 2 is selected (index 1)

<Tabs name="Tab navigation" tabIndex={activeTab} onChange={setActiveTab}>
  <Tab label="Tab 1">
    <Type size="lg">Tab 1</Type>
    <Type>Lorem ipsum dolor sit amet</Type>
  </Tab>
  <Tab label="Tab 2">
    <Type size="lg">Tab 2</Type>
    <Type>Lorem ipsum dolor sit amet</Type>
    <ButtonGroup>
      <Button variant="primary">Submit</Button>
      <Button variant="secondary">Cancel</Button>
    </ButtonGroup>
  </Tab>
  <Tab label="Tab 3">
    <Type size="lg">Tab 3</Type>
    <Type>Lorem ipsum dolor sit amet</Type>
    <Button variant="primary" status="danger">Remove</Button>
  </Tab>
  <Tab label="Tab 4">
    <Type size="lg">Tab 4</Type>
    <Type>Lorem ipsum dolor sit amet</Type>
    <Button variant="secondary">Cancel</Button>
  </Tab>
</Tabs>
```

### Basic Tabs

**MCA1 (Before)**:
```html
<mca-tabs id="t_tabs_basic">
    <mca-tab name="Account Details" state="selected" id="t_tab_account">
        Account details content here.
    </mca-tab>
    <mca-tab name="Transaction History" id="t_tab_transactions">
        Transaction history content here.
    </mca-tab>
    <mca-tab name="Statements" id="t_tab_statements">
        Statements content here.
    </mca-tab>
</mca-tabs>
```

**Blueprint-React (After)**:
```typescript
<Tabs id="t_tabs_basic" initialTabIndex={0}>
  <Tab label="Account Details" id="t_tab_account">
    Account details content here.
  </Tab>
  <Tab label="Transaction History" id="t_tab_transactions">
    Transaction history content here.
  </Tab>
  <Tab label="Statements" id="t_tab_statements">
    Statements content here.
  </Tab>
</Tabs>
```

**Note**: `state="selected"` on the first tab maps to `initialTabIndex={0}` on `<Tabs>`. The `name` attribute maps to the `label` prop on `<Tab>`.

---

### Tabs with Disabled Tab

**MCA1 (Before)**:
```html
<mca-tabs id="t_tabs_disabled">
    <mca-tab name="Active" state="selected" id="t_tab_active">
        Active tab content.
    </mca-tab>
    <mca-tab name="Disabled" state="disabled" id="t_tab_disabled">
        This tab is disabled.
    </mca-tab>
    <mca-tab name="Another" id="t_tab_another">
        Another tab content.
    </mca-tab>
</mca-tabs>
```

**Blueprint-React (After)**:
```typescript
<Tabs id="t_tabs_disabled" initialTabIndex={0}>
  <Tab label="Active" id="t_tab_active">
    Active tab content.
  </Tab>
  <Tab label="Disabled" id="t_tab_disabled" disabled>
    This tab is disabled.
  </Tab>
  <Tab label="Another" id="t_tab_another">
    Another tab content.
  </Tab>
</Tabs>
```

**Note**: `state="disabled"` maps to the `disabled` boolean prop on `<Tab>`.

---

### Tabs with Icon

MCA1's `icon` attribute renders an icon in the tab label. Use the `media` prop on `<Tab>` with `<Icon>`.

**MCA1 (Before)**:
```html
<mca-tabs id="t_tabs_icon">
    <mca-tab name="Home" icon="home" state="selected" id="t_tab_home">
        Home content.
    </mca-tab>
    <mca-tab name="Settings" icon="settings" id="t_tab_settings">
        Settings content.
    </mca-tab>
</mca-tabs>
```

**Blueprint-React (After)**:
```typescript
<Tabs id="t_tabs_icon" initialTabIndex={0}>
  <Tab label="Home" id="t_tab_home" media={<Icon icon="home" size="sm" />}>
    Home content.
  </Tab>
  <Tab label="Settings" id="t_tab_settings" media={<Icon icon="settings" size="sm" />}>
    Settings content.
  </Tab>
</Tabs>
```

**Note**: MCA1 icon names may not exist in Blueprint. Check Blueprint storybook for available icons and map to the closest alternative. See [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md).

---

### Controlled Tabs (with State Management)

MCA1 tabs track the selected tab via `state="selected"` on the active `<mca-tab>`. In Blueprint-React, use the `tabIndex` and `setTabIndex` props for controlled tab state, or listen to changes via `activeTabChanged`.

**MCA1 (Before)**:
```html
<mca-tabs id="t_tabs_controlled">
    <mca-tab name="Step 1" state="selected" id="t_tab_step1">
        Step 1 content.
    </mca-tab>
    <mca-tab name="Step 2" id="t_tab_step2">
        Step 2 content.
    </mca-tab>
    <mca-tab name="Step 3" id="t_tab_step3">
        Step 3 content.
    </mca-tab>
</mca-tabs>

<!-- MCA1 JS to programmatically switch tabs -->
<script>
    var tabs = document.getElementById('t_tabs_controlled');
    tabs.selectTab(1); // switch to Step 2
</script>
```

**Blueprint-React (After)**:
```typescript
const [tabIndex, setTabIndex] = useState<number>(0);

<Tabs
  id="t_tabs_controlled"
  tabIndex={tabIndex}
  setTabIndex={setTabIndex}
  activeTabChanged={(activeTab) => {
    console.log('Active tab changed to:', activeTab);
  }}
>
  <Tab label="Step 1" id="t_tab_step1">
    Step 1 content.
  </Tab>
  <Tab label="Step 2" id="t_tab_step2">
    Step 2 content.
  </Tab>
  <Tab label="Step 3" id="t_tab_step3">
    Step 3 content.
  </Tab>
</Tabs>

{/* Programmatic tab switch replaces tabs.selectTab(1) */}
<Button variant="secondary" onClick={() => setTabIndex(1)}>
  Go to Step 2
</Button>
```

**Note**: MCA1's imperative `selectTab(index)` API is replaced by React's declarative state management. Use `useState` with the `tabIndex` and `setTabIndex` props on `<Tabs>`.

---

### Hidden Tab

MCA1's `state="hidden"` removes a tab from the rendered output. In Blueprint-React, conditionally render the `<Tab>` component.

**MCA1 (Before)**:
```html
<mca-tabs id="t_tabs_hidden">
    <mca-tab name="Visible" state="selected" id="t_tab_visible">
        Visible content.
    </mca-tab>
    <mca-tab name="Hidden" state="hidden" id="t_tab_hidden">
        This tab is hidden.
    </mca-tab>
</mca-tabs>
```

**Blueprint-React (After)**:
```typescript
const showHiddenTab = false; // controlled by application logic

<Tabs id="t_tabs_hidden" initialTabIndex={0}>
  <Tab label="Visible" id="t_tab_visible">
    Visible content.
  </Tab>
  {showHiddenTab && (
    <Tab label="Hidden" id="t_tab_hidden">
      This tab is hidden.
    </Tab>
  )}
</Tabs>
```

**Note**: There is no `hidden` prop on `<Tab>`. Use conditional rendering (`{condition && <Tab>}`) to show or hide tabs dynamically.

---

## Complete `<mca-tabs>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Tabs` | |
| `class` | `className` | `Tabs` | React convention |
| `tabindex` | `tabIndex` (HTML) | `Tabs` | camelCase in React; do not confuse with the `tabIndex` state prop |
| Text content | `children` | `Tabs` | Contains `<Tab>` children |
| (first selected tab index) | `initialTabIndex` | `Tabs` | Uncontrolled mode; default `0` |
| (programmatic tab switching) | `tabIndex` + `setTabIndex` | `Tabs` | Controlled mode via `useState` |
| (tab change callback) | `activeTabChanged` | `Tabs` | Callback receives active tab index |
| `name` | `name` | `Tabs` | Optional identifier |
| (full-width layout) | `fullWidth` | `Tabs` | Stretch tabs to fill container width |

---

## Complete `<mca-tab>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `name` (display name) | `label` | `Tab` | Tab header text |
| `id` | `id` | `Tab` | |
| `class` | `className` | `Tab` | React convention |
| `tabindex` | `tabIndex` | `Tab` | camelCase in React |
| `state="selected"` | `initialTabIndex={N}` on parent `<Tabs>` | `Tabs` | N = zero-based index of the selected tab |
| `state="disabled"` | `disabled` | `Tab` | Boolean prop |
| `state="hidden"` | Conditional rendering | N/A | Use `{condition && <Tab>}` |
| `icon` | `media={<Icon icon="..." size="sm" />}` | `Tab` | Map icon name to Blueprint equivalent |
| Text content | `children` | `Tab` | Tab panel content |
| `active` (runtime) | `active` | `Tab` | Controlled active state; prefer `tabIndex` on parent instead |
| (disable focus) | `disableFocus` | `Tab` | Prevents tab from receiving focus |
