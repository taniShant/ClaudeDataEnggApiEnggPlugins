# BDL Radio Buttons to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Radio Buttons (`<mca-radios>` + `<mca-radio>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-radios>` | `<FormMultiItem>` with `render` function containing multiple `<FormRadio>` |
| `<mca-radio>` | `<FormRadio>` with `{...renderProps}` spread |

**Critical**: Use `<FormMultiItem>` (not `<FormItem>`) for radio button groups. `FormMultiItem` is designed for wrapping multiple form controls under a single label. It uses a `render` function that passes `renderProps` — spread these on each `<FormRadio>`.

**`FormMultiItem` API**:
- `label` — group label (string or ReactNode)
- `layout` — controls alignment: `"inline-md-up"` for horizontal/inline, omit for vertical (default stacking)
- `render` — render function receiving `renderProps` to spread on each form control
- `error` — group-level error message

**`FormRadio` API** (inside `FormMultiItem`):
- `name` — shared group name (same for all radios in the group)
- `value` — radio value
- `label` — radio label text (use `label` prop, NOT children)
- `{...renderProps}` — must be spread **at the end** of props from `FormMultiItem` render function

---

### Horizontal Radio Group

**MCA1 (Before)**:
```html
<mca-radios id="partyToOldAccount_<%= i%>" name="partyToOldAccount_<%= i%>"
    label="Party to old account?" align="horizontal">
    <mca-radio id="partyToOldAccountYes_<%= i%>" value="yes"
        class="partyToOldAccount" name="partyToOldAccount_<%= i%>">Yes</mca-radio>
    <mca-radio id="partyToOldAccountNo_<%= i%>" value="no"
        class="partyToOldAccount" name="partyToOldAccount_<%= i%>">No</mca-radio>
</mca-radios>
```

**Blueprint-React (After)**:
```typescript
<FormMultiItem
  label="Party to old account?"
  id={`partyToOldAccount_${i}`}
  layout="inline-md-up"
  render={renderProps => <>
    <FormRadio name={`partyToOldAccount_${i}`} value="yes" label="Yes" className="partyToOldAccount" checked={partyToOldAccount === 'yes'} onChange={(e) => setPartyToOldAccount(e.target.value)} {...renderProps} />
    <FormRadio name={`partyToOldAccount_${i}`} value="no" label="No" className="partyToOldAccount" checked={partyToOldAccount === 'no'} onChange={(e) => setPartyToOldAccount(e.target.value)} {...renderProps} />
  </>}
/>
```

---

### Vertical Radio Group

For vertical layout, omit the `layout` prop (default stacking).

```typescript
<FormMultiItem
  label="Select an option"
  id="verticalRadioGroup"
  render={renderProps => <>
    <FormRadio name="options" value="optionA" label="Option A" checked={selected === 'optionA'} onChange={(e) => setSelected(e.target.value)} {...renderProps} />
    <FormRadio name="options" value="optionB" label="Option B" checked={selected === 'optionB'} onChange={(e) => setSelected(e.target.value)} {...renderProps} />
    <FormRadio name="options" value="optionC" label="Option C" checked={selected === 'optionC'} onChange={(e) => setSelected(e.target.value)} {...renderProps} />
  </>}
/>
```

---

### Error Handling on Radio Groups

The `error` prop on `FormMultiItem` **must** be wrapped in `<Type color="error">`. Use a conditional guard so falsy values remain falsy:

```typescript
<FormMultiItem
  label={<Type>Switch type</Type>}
  error={errors.switchType && <Type color="error">{errors.switchType}</Type>}
  layout="inline-md-up"
  render={(renderProps) => (
    <>
      <FormRadio name="switchType" value="Full" label="Full Switch" checked={value === 'Full'} onChange={handler} {...renderProps} />
      <FormRadio name="switchType" value="Partial" label="Partial Switch" checked={value === 'Partial'} onChange={handler} {...renderProps} />
    </>
  )}
/>
```

**This same pattern applies to `FormItem` and `FormMultiItem` in all form mapping files (input, textarea, checkbox, combobox).**

---

### Alignment Pattern Summary

| MCA1 `align` | `FormMultiItem` `layout` prop | Notes |
|---|---|---|
| `align="horizontal"` | `layout="inline-md-up"` | Inline from medium breakpoint up, stacks on small screens |
| `align="vertical"` | (omit `layout` prop) | Default vertical stacking |

---

### Attribute Mapping

**`<mca-radios>` (group wrapper)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormMultiItem` | |
| `label` | `label` | `FormMultiItem` | String or ReactNode |
| `name` | `name` | Each `FormRadio` | Shared across all radios |
| `align="horizontal"` | `layout="inline-md-up"` | `FormMultiItem` | Inline layout from md breakpoint |
| `align="vertical"` | (omit `layout`) | `FormMultiItem` | Default vertical stacking |
| N/A | `render` | `FormMultiItem` | Render function receiving `renderProps` |
| N/A | `error` | `FormMultiItem` | Group-level error — **must** wrap in `<Type color="error">` |

**`<mca-radio>` (individual radio)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormRadio` | |
| `name` | `name` | `FormRadio` | Same for all radios in group |
| `value` | `value` | `FormRadio` | |
| `class` | `className` | `FormRadio` | React convention |
| Text content | `label` | `FormRadio` | Use `label` prop, NOT children |
| N/A | `{...renderProps}` | `FormRadio` | Must spread **at end** of props from `FormMultiItem` render |
