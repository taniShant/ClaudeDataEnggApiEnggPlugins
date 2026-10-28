# BDL Checkbox to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Checkbox (`<mca-checkboxes>` + `<mca-checkbox>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-checkboxes>` | `<FormMultiItem>` with `render` function containing multiple `<FormCheckbox>` |
| `<mca-checkbox>` (standalone) | `<FormItem>` + `<FormCheckbox>` (render function) |
| `<mca-checkbox>` (inside group) | `<FormCheckbox>` with `{...renderProps}` spread |

**Critical**: Use `<FormMultiItem>` (not `<FormItem>`) for checkbox groups. `FormMultiItem` is designed for wrapping multiple form controls (checkboxes, radios) under a single label. It uses a `render` function that passes `renderProps` — spread these on each `<FormCheckbox>`. Use `<FormItem>` only for a standalone single checkbox.

**`FormMultiItem` API**:
- `label` — group label (string or ReactNode)
- `layout` — controls alignment: `"inline-md-up"` for horizontal/inline, omit for vertical (default stacking)
- `render` — render function receiving `renderProps` to spread on each form control
- `error` — error message for the group

**`FormCheckbox` API** (inside `FormMultiItem`):
- `name` — shared group name
- `value` — checkbox value
- `label` — checkbox label text (use `label` prop, NOT children)
- `{...renderProps}` — must be spread **at the end** of props from `FormMultiItem` render function

---

### Standalone Checkbox

A single `<mca-checkbox>` without a `<mca-checkboxes>` wrapper (e.g. terms & conditions).

**MCA1 (Before)**:
```html
<mca-checkbox id="termsAndConditionsCheckBox" checked="no"
    description="I agree to the ISA Terms and Conditions">
</mca-checkbox>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Terms and Conditions"
  id="termsAndConditionsCheckBox"
  render={(props) => (
    <FormCheckbox
      {...props}
      id="termsAndConditionsCheckBox"
      checked={termsAccepted}
      onChange={(e) => setTermsAccepted(e.target.checked)}
      label="I agree to the ISA Terms and Conditions"
    />
  )}
/>
```

---

### Checkbox Group — Horizontal with Help

MCA1's `align="horizontal"` renders checkboxes in a row. Use `layout="inline-md-up"` on `FormMultiItem` to render checkboxes inline from medium breakpoint upwards. The `help` and `help-title` attributes map to a `<PopupNav>` triggered by an info icon on the label (Blueprint-React does NOT have a Tooltip component).

**MCA1 (Before)**:
```html
<mca-checkboxes label="Group-Horizontal" id="b_checkboxes_normal" align="horizontal"
    help="Lorem ipsum dolor sit amet, consectetur adipiscing elit,"
    help-title="Lorem ipsum">
    <mca-checkbox checked="no" disabled="no" name="name6" id="b_checkboxes_checkbox_0">
        Option 1
    </mca-checkbox>
    <mca-checkbox checked="no" disabled="no" name="name6" id="b_checkboxes_checkbox_1">
        Option 2
    </mca-checkbox>
    <mca-checkbox checked="no" disabled="yes" name="name6" id="b_checkboxes_checkbox_2">
        Disabled Unchecked
    </mca-checkbox>
    <mca-checkbox disabled="yes" checked="yes" name="name6" id="b_checkboxes_checkbox_3">
        Disabled checked
    </mca-checkbox>
</mca-checkboxes>
```

**Blueprint-React (After)**:
```typescript
// State: track each checkbox independently
const [checked, setChecked] = useState<Record<string, boolean>>({
  b_checkboxes_checkbox_0: false,
  b_checkboxes_checkbox_1: false,
  b_checkboxes_checkbox_2: false,  // disabled unchecked
  b_checkboxes_checkbox_3: true,   // disabled checked
});

const handleCheck = (id: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
  setChecked((prev) => ({ ...prev, [id]: e.target.checked }));
};

<FormMultiItem
  label={
    <Arrange gap="fixed" align="center">
      <ArrangeItem size="fit">
        <Type element="span">Group-Horizontal</Type>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button
          variant="subtle"
          ref={helpTriggerRef}
          onClick={() => setHelpOpen(!helpOpen)}
          media={<Icon icon="info" size="sm" />}
          aria-label="Help"
        />
        {helpOpen && (
          <PopupNav
            triggerRef={helpTriggerRef}
            onClose={() => setHelpOpen(false)}
            placement="bottom left"
            ariaLabelText="Help information"
          >
            <Type>Lorem ipsum dolor sit amet, consectetur adipiscing elit,</Type>
          </PopupNav>
        )}
      </ArrangeItem>
    </Arrange>
  }
  id="b_checkboxes_normal"
  layout="inline-md-up"
  render={renderProps => <>
    <FormCheckbox name="name6" value="option1" label="Option 1" checked={checked.b_checkboxes_checkbox_0} onChange={handleCheck('b_checkboxes_checkbox_0')} {...renderProps} />
    <FormCheckbox name="name6" value="option2" label="Option 2" checked={checked.b_checkboxes_checkbox_1} onChange={handleCheck('b_checkboxes_checkbox_1')} {...renderProps} />
    <FormCheckbox name="name6" value="disabledUnchecked" label="Disabled Unchecked" disabled checked={checked.b_checkboxes_checkbox_2} {...renderProps} />
    <FormCheckbox name="name6" value="disabledChecked" label="Disabled checked" disabled checked={checked.b_checkboxes_checkbox_3} {...renderProps} />
  </>}
/>
```

---

### Checkbox Group — Vertical with Description and Error

MCA1's `align="vertical"` stacks checkboxes vertically. This is the default `FormMultiItem` layout — omit the `layout` prop.

**MCA1 (Before)**:
```html
<mca-checkboxes label="Group-Vertical" id="b_checkboxes_vertical" align="vertical"
    help="Lorem ipsum dolor sit amet, consectetur adipiscing elit">
    <mca-checkbox checked="yes" disabled="no" name="name7" id="b_checkboxes_vertical_0">
        Option 1
    </mca-checkbox>
    <mca-checkbox checked="no" disabled="no" name="name7" id="b_checkboxes_vertical_1">
        Option 2
    </mca-checkbox>
    <mca-checkbox checked="no" name="name7" id="b_checkboxes_vertical_2" disabled="yes">
        Disabled Unchecked
    </mca-checkbox>
    <mca-checkbox checked="no" name="name7" id="b_checkboxes_vertical_3" disabled="yes">
        Disabled checked
    </mca-checkbox>
    <mca-checkbox disabled="no" name="name7" id="b_checkboxes_vertical_4"
        description="Checkbox with description" error-placeholder="error">
        Option 5
    </mca-checkbox>
</mca-checkboxes>
```

**Blueprint-React (After)**:
```typescript
const [vertChecked, setVertChecked] = useState<Record<string, boolean>>({
  b_checkboxes_vertical_0: true,   // checked="yes"
  b_checkboxes_vertical_1: false,
  b_checkboxes_vertical_2: false,  // disabled
  b_checkboxes_vertical_3: false,  // disabled
  b_checkboxes_vertical_4: false,
});

const handleVertCheck = (id: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
  setVertChecked((prev) => ({ ...prev, [id]: e.target.checked }));
};

<FormMultiItem
  label={
    <Arrange gap="fixed" align="center">
      <ArrangeItem size="fit">
        <Type element="span">Group-Vertical</Type>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button
          variant="subtle"
          ref={vertHelpRef}
          onClick={() => setVertHelpOpen(!vertHelpOpen)}
          media={<Icon icon="info" size="sm" />}
          aria-label="Help"
        />
        {vertHelpOpen && (
          <PopupNav
            triggerRef={vertHelpRef}
            onClose={() => setVertHelpOpen(false)}
            placement="bottom left"
            ariaLabelText="Help information"
          >
            <Type>Lorem ipsum dolor sit amet, consectetur adipiscing elit</Type>
          </PopupNav>
        )}
      </ArrangeItem>
    </Arrange>
  }
  id="b_checkboxes_vertical"
  error={errors.b_checkboxes_vertical && <Type color="error">{errors.b_checkboxes_vertical}</Type>}
  render={renderProps => <>
    <FormCheckbox name="name7" value="option1" label="Option 1" checked={vertChecked.b_checkboxes_vertical_0} onChange={handleVertCheck('b_checkboxes_vertical_0')} {...renderProps} />
    <FormCheckbox name="name7" value="option2" label="Option 2" checked={vertChecked.b_checkboxes_vertical_1} onChange={handleVertCheck('b_checkboxes_vertical_1')} {...renderProps} />
    <FormCheckbox name="name7" value="disabledUnchecked" label="Disabled Unchecked" disabled checked={vertChecked.b_checkboxes_vertical_2} {...renderProps} />
    <FormCheckbox name="name7" value="disabledChecked" label="Disabled checked" disabled checked={vertChecked.b_checkboxes_vertical_3} {...renderProps} />
    <FormCheckbox name="name7" value="option5" label="Option 5" checked={vertChecked.b_checkboxes_vertical_4} onChange={handleVertCheck('b_checkboxes_vertical_4')} {...renderProps} />
  </>}
/>
```

**Note on `description` and `error-placeholder`**: `FormCheckbox` does not have `description` or `error` props. For per-checkbox description, add a `<Type>` after the checkbox. For group-level error, use the `error` prop on `FormMultiItem`.

---

### Checkbox Group — Inline

MCA1's `align="inline"` renders checkboxes inline (same as horizontal). Use `layout="inline-md-up"`.

**MCA1 (Before)**:
```html
<mca-checkboxes label="Group-Inline" id="b_checkboxes_inline" align="inline">
    <mca-checkbox checked="yes" disabled="no" name="name8" id="b_checkboxes_inline_0">
        Option 1
    </mca-checkbox>
    <mca-checkbox checked="no" disabled="no" name="name8" id="b_checkboxes_inline_1">
        Option 2
    </mca-checkbox>
</mca-checkboxes>
```

**Blueprint-React (After)**:
```typescript
<FormMultiItem
  label="Group-Inline"
  id="b_checkboxes_inline"
  layout="inline-md-up"
  render={renderProps => <>
    <FormCheckbox name="name8" value="option1" label="Option 1" checked={inlineChecked.b_checkboxes_inline_0} onChange={handleInlineCheck('b_checkboxes_inline_0')} {...renderProps} />
    <FormCheckbox name="name8" value="option2" label="Option 2" checked={inlineChecked.b_checkboxes_inline_1} onChange={handleInlineCheck('b_checkboxes_inline_1')} {...renderProps} />
  </>}
/>
```

---

### Alignment Pattern Summary

| MCA1 `align` | `FormMultiItem` `layout` prop | Notes |
|---|---|---|
| `align="horizontal"` | `layout="inline-md-up"` | Inline from medium breakpoint up, stacks on small screens |
| `align="vertical"` | (omit `layout` prop) | Default vertical stacking |
| `align="inline"` | `layout="inline-md-up"` | Same as horizontal |

---

### Complete `<mca-checkboxes>` / `<mca-checkbox>` Attribute Mapping

**`<mca-checkboxes>` (group wrapper)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormMultiItem` | |
| `label` | `label` | `FormMultiItem` | String or ReactNode |
| `align="horizontal"` / `"inline"` | `layout="inline-md-up"` | `FormMultiItem` | Inline layout from md breakpoint |
| `align="vertical"` | (omit `layout`) | `FormMultiItem` | Default vertical stacking |
| `help` | `<PopupNav>` triggered by info icon in label | `FormMultiItem` label | Click-to-show help; Blueprint has NO Tooltip component |
| `help-title` | `<Type weight="bold">` inside `PopupNav` | `FormMultiItem` label | Render as heading in PopupNav content |
| N/A | `render` | `FormMultiItem` | Render function receiving `renderProps` |
| N/A | `error` | `FormMultiItem` | Group-level error message |

**`<mca-checkbox>` (individual checkbox)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormCheckbox` | |
| `name` | `name` | `FormCheckbox` | Shared across group members |
| Text content | `label` | `FormCheckbox` | Use `label` prop, NOT children |
| `value` (implicit) | `value` | `FormCheckbox` | Identifies the checkbox value |
| `checked="yes"` | `checked={true}` (initial state) | `FormCheckbox` | Set initial state value to `true` |
| `checked="no"` | `checked={false}` (initial state) | `FormCheckbox` | Set initial state value to `false` |
| `disabled="yes"` | `disabled` | `FormCheckbox` | Boolean prop |
| `disabled="no"` | (omit or `disabled={false}`) | `FormCheckbox` | Default is enabled |
| N/A | `{...renderProps}` | `FormCheckbox` | Must spread **at end** of props from `FormMultiItem` render |
| `description` | `<Type>` after checkbox | N/A | No built-in prop |
| `error-placeholder` | `error` on `FormMultiItem` | `FormMultiItem` | Group-level error |
