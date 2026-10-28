# BDL Buttons and Actions to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Buttons (`<mca-button>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-button>` | `<Button>` |
| `<mca-button type="link">` | `<ButtonLink>` — see [BDL_LINK_MAPPING.md](BDL_LINK_MAPPING.md) |
| `<mca-button-groups>` | `<FormMultiItem>` + `<FormRadio>` (segmented toggle) or `<Arrange>` + `<Button>` group |

**Valid Blueprint-React Button variants**: `primary`, `secondary`, `subtle`
**Valid Blueprint-React Button status**: `default`, `danger`
**Invalid variants** (do NOT use): `ghost`, `danger` (as variant), `tertiary`, `contained`, `outlined`, `text`

---

### `type` to `variant` / `status` Mapping

| MCA1 `type` | Blueprint-React | Notes |
|---|---|---|
| `type="primary"` | `variant="primary"` | |
| `type="secondary"` | `variant="secondary"` | |
| `type="link"` | `<ButtonLink>` | Dedicated link component, NOT `<Button variant="subtle">` |
| `type="critical"` | `variant="primary"` + `status="danger"` | Deprecated in BDL but still functional |
| `type="table"` | `variant="secondary"` + `size="sm"` | Compact button for table context; deprecated in BDL |
| `type="cancel"` | `variant="secondary"` | Deprecated in BDL but still functional |
| `type="close"` | `variant="subtle"` + close icon | Close/dismiss button |
| `type-mobile="confirm"` | `variant="primary"` | Mobile confirm action |
| `type-mobile="decline"` | `variant="secondary"` + `status="danger"` | Mobile decline action |

**Note**: `type="critical"`, `type="table"`, and `type="cancel"` are deprecated BDL v1 types that still work. In Blueprint-React, map to the closest standard variant + status combination.

---

### Primary

**MCA1 (Before)**:
```html
<mca-button id="b_button_type_primary" type="primary">
    Primary
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="primary" id="b_button_type_primary" onClick={handleClick}>
  Primary
</Button>
```

---

### Secondary

**MCA1 (Before)**:
```html
<mca-button type="secondary" id="b_button_type_secondary">
    Secondary
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="secondary" id="b_button_type_secondary" onClick={handleClick}>
  Secondary
</Button>
```

---

### Link

MCA1's `type="link"` maps to Blueprint-React's `<ButtonLink>` component — a dedicated link-styled component, not `<Button variant="subtle">`.

**MCA1 (Before)**:
```html
<mca-button type="link" id="b_button_link">
    Link
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<ButtonLink href="#" id="b_button_link" onClick={handleClick}>
  Link
</ButtonLink>
```

---

### Critical (Deprecated)

MCA1's `type="critical"` is a deprecated v1 type. Map to `variant="primary"` with `status="danger"`.

**MCA1 (Before)**:
```html
<mca-button type="critical" id="b_button_type_critical">
    Critical
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="primary" status="danger" id="b_button_type_critical" onClick={handleClick}>
  Critical
</Button>
```

---

### Inside Table (Deprecated)

MCA1's `type="table"` is a deprecated v1 type for compact table buttons. Map to `variant="secondary"` with `size="sm"`.

**MCA1 (Before)**:
```html
<mca-button type="table" id="b_button_type_table">
    Inside Table
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="secondary" size="sm" id="b_button_type_table" onClick={handleClick}>
  Inside Table
</Button>
```

---

### Cancel (Deprecated)

MCA1's `type="cancel"` is a deprecated v1 type. Map to `variant="secondary"`.

**MCA1 (Before)**:
```html
<mca-button type="cancel" id="b_button_type_cancel">
    Cancel
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="secondary" id="b_button_type_cancel" onClick={handleCancel}>
  Cancel
</Button>
```

---

### Disabled

**MCA1 (Before)**:
```html
<mca-button disabled="yes" id="b_button_disabled">
    Disabled
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="secondary" id="b_button_disabled" disabled>
  Disabled
</Button>
```

---

### Mobile Confirm / Decline

MCA1's `type-mobile` provides mobile-specific button styles. Map to standard variants.

**MCA1 (Before)**:
```html
<mca-button id="b_button_confirm" type-mobile="confirm">
    Confirm
</mca-button>
<mca-button id="b_button_decline" type-mobile="decline">
    Decline
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="primary" id="b_button_confirm" onClick={handleConfirm}>
  Confirm
</Button>
<Button variant="secondary" status="danger" id="b_button_decline" onClick={handleDecline}>
  Decline
</Button>
```

---

### Button with Icon

MCA1's `icon` attribute renders an icon inside the button. Use the `media` prop on `<Button>` with `<Icon>`.

**MCA1 (Before)**:
```html
<mca-button icon="cloud-upload" id="b_button_primary_icon" type="primary">
    Camera
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button
  variant="primary"
  id="b_button_primary_icon"
  media={<Icon icon="cloud-upload" size="sm" />}
  onClick={handleClick}
>
  Camera
</Button>
```

**Note**: MCA1 icon names may not exist in Blueprint. Check Blueprint storybook for available icons and map to the closest alternative. See [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md).

---

### Small Button

**MCA1 (Before)**:
```html
<mca-button size="small" id="b_button_small">
    Small
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button variant="secondary" size="sm" id="b_button_small" onClick={handleClick}>
  Small
</Button>
```

---

### Align Right

MCA1's `align="right"` is not a `<Button>` prop. Use `<Arrange>` with `justify="end"` as the parent layout.

**MCA1 (Before)**:
```html
<mca-fluidview>
    <mca-cell grow="10">
        <mca-button align="right" id="b_button_align_right">
            Align Right
        </mca-button>
    </mca-cell>
</mca-fluidview>
```

**Blueprint-React (After)**:
```typescript
<Arrange justify="end">
  <ArrangeItem size="fit">
    <Button variant="secondary" id="b_button_align_right" onClick={handleClick}>
      Align Right
    </Button>
  </ArrangeItem>
</Arrange>
```

---

### Block (Full Width)

MCA1's `block="yes"` renders the button at full width. Use `fullWidth` prop on `<Button>`.

**MCA1 (Before)**:
```html
<mca-fluidview>
    <mca-cell grow="10">
        <mca-button block="yes" id="b_button_block_yes">
            Block
        </mca-button>
    </mca-cell>
</mca-fluidview>
```

**Blueprint-React (After)**:
```typescript
<Button variant="secondary" id="b_button_block_yes" fullWidth onClick={handleClick}>
  Block
</Button>
```

---

### Close Button

MCA1's `type="close"` renders a small dismiss/close button. Map to `variant="subtle"` with a close icon.

**MCA1 (Before)**:
```html
<mca-button id="b_button_type_close" type="close">
    ✕
</mca-button>
```

**Blueprint-React (After)**:
```typescript
<Button
  variant="subtle"
  id="b_button_type_close"
  media={<Icon icon="dismiss" size="sm" />}
  onClick={handleClose}
  aria-label="Close"
/>
```

**Note**: For close buttons, prefer using `media` with the `dismiss` icon and `aria-label` for accessibility rather than rendering the `✕` character as text content.

---

## Links (`<mca-link>`)

`<mca-link>` has its own mapping file: **[BDL_LINK_MAPPING.md](BDL_LINK_MAPPING.md)**

---

## Button Groups (`<mca-button-groups>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-button-groups>` | `<FormMultiItem>` + `<FormRadio>` (single select) or `<Arrange>` + `<Button>` (action group) |

MCA1's `<mca-button-groups>` renders a set of toggle buttons from a serialised data model (`button-groups-data`). The component is data-driven — button labels, values, and states come from a JSON object passed via the `button-groups-data` attribute.

Blueprint-React has no direct equivalent. The migration approach depends on the button group's purpose:

- **Single selection (toggle)**: Use `<FormMultiItem>` + `<FormRadio>` with `layout="inline-md-up"` — this gives the correct semantics for selecting one option from a group
- **Action group (multiple actions)**: Use `<Arrange>` + multiple `<Button>` components

### Single Selection (Toggle Group)

This is the most common use case — one button selected at a time, like a segmented control.

**MCA1 (Before)**:
```html
<!-- button-groups-data is a serialised JSON array of button objects -->
<!-- e.g. [{"label":"Option A","value":"a"},{"label":"Option B","value":"b"},{"label":"Option C","value":"c"}] -->
<mca-button-groups id="b_button-groups" tabindex="3"
    button-groups-data="<%= serialisedModelObject %>">
</mca-button-groups>
```

**Blueprint-React (After)**:
```typescript
// The data model that was serialised in MCA1
interface ButtonGroupOption {
  label: string;
  value: string;
  disabled?: boolean;
}

// Data comes from props, API, or Redux state (replaces serialisedModelObject)
const options: ButtonGroupOption[] = [
  { label: 'Option A', value: 'a' },
  { label: 'Option B', value: 'b' },
  { label: 'Option C', value: 'c' },
];

const [selected, setSelected] = useState<string>('');

<FormMultiItem
  label={<Type>Select an option</Type>}
  id="b_button-groups"
  layout="inline-md-up"
  render={renderProps => <>
    {options.map((option) => (
      <FormRadio
        key={option.value}
        name="b_button-groups"
        value={option.value}
        label={option.label}
        disabled={option.disabled}
        checked={selected === option.value}
        onChange={(e) => setSelected(e.target.value)}
        {...renderProps}
      />
    ))}
  </>}
/>
```

### Action Group (Non-Toggle)

If the button group represents multiple independent actions rather than a single selection, use `<Arrange>` with `<Button>` components.

```typescript
const actions: ButtonGroupOption[] = [
  { label: 'Option A', value: 'a' },
  { label: 'Option B', value: 'b' },
  { label: 'Option C', value: 'c' },
];

<Arrange gap="fixed" id="b_button-groups">
  {actions.map((action) => (
    <ArrangeItem key={action.value} size="fit">
      <Button
        variant="secondary"
        disabled={action.disabled}
        onClick={() => handleAction(action.value)}
      >
        {action.label}
      </Button>
    </ArrangeItem>
  ))}
</Arrange>
```

### `<mca-button-groups>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormMultiItem` or `Arrange` | |
| `tabindex` | `tabIndex` | `FormMultiItem` or `Arrange` | camelCase in React |
| `button-groups-data` | Component state / props | N/A | Deserialise the JSON into a typed array; render dynamically with `.map()` |
| `class` | `className` | `FormMultiItem` or `Arrange` | React convention |

### Choosing the Right Pattern

| MCA1 Behaviour | Blueprint-React Pattern | When to Use |
|---|---|---|
| One selected at a time (toggle) | `<FormMultiItem>` + `<FormRadio>` | User picks one option — most common use case |
| Multiple can be selected | `<FormMultiItem>` + `<FormCheckbox>` | User picks multiple options |
| Independent actions | `<Arrange>` + `<Button>` | Buttons trigger actions, not selections |

---

## Complete `<mca-button>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Button` | |
| `class` | `className` | `Button` | React convention |
| Text content | `children` | `Button` | |
| `type="primary"` | `variant="primary"` | `Button` | |
| `type="secondary"` | `variant="secondary"` | `Button` | |
| `type="link"` | `<ButtonLink href="#">` | `ButtonLink` | Dedicated link component |
| `type="critical"` | `variant="primary"` + `status="danger"` | `Button` | Deprecated BDL v1 type |
| `type="table"` | `variant="secondary"` + `size="sm"` | `Button` | Deprecated BDL v1 type |
| `type="cancel"` | `variant="secondary"` | `Button` | Deprecated BDL v1 type |
| `type="close"` | `variant="subtle"` + `media={<Icon icon="dismiss" />}` | `Button` | Close/dismiss button |
| `type-mobile="confirm"` | `variant="primary"` | `Button` | |
| `type-mobile="decline"` | `variant="secondary"` + `status="danger"` | `Button` | |
| `size="small"` | `size="sm"` | `Button` | |
| `size="medium"` | (omit — default size) | `Button` | |
| `icon` | `media={<Icon icon="..." size="sm" />}` | `Button` | Map icon name to Blueprint equivalent |
| `disabled="yes"` | `disabled` | `Button` | Boolean prop |
| `align="right"` | `<Arrange justify="end">` parent | Layout wrapper | Not a Button prop |
| `block="yes"` | `fullWidth` | `Button` | Full-width button |
| `modal-dismiss="yes"` | `onClick={handleClose}` | `Button` | Handle via event handler |

### `size` Mapping

| MCA1 `size` | Blueprint-React `size` |
|---|---|
| `"small"` | `"sm"` |
| `"medium"` | (omit — default) |
| `"large"` / `"lg"` | (omit — default; Blueprint buttons don't have a large size) |
