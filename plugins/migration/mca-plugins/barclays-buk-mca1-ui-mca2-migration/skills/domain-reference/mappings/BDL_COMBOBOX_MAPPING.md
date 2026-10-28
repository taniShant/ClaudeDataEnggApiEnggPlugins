# BDL Select / Dropdown (Combobox) to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Select / Dropdown (Combobox)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-combobox template="dropdown">` | `<FormItem>` + `<FormSelect>` |
| `<mca-combobox template="autocomplete">` | `<FormItem>` + `<AutoComplete>` |
| `<mca-combobox-option>` | `<option>` (standard HTML) |

**MCA1 (Before)**:
```html
<mca-combobox id="existingIsaProvider" template="autocomplete" maxselect="1"
    label="Existing ISA provider" placeholder="Enter name">
    <mca-combobox-option value="providerA">Provider A</mca-combobox-option>
    <mca-combobox-option value="providerB">Provider B</mca-combobox-option>
</mca-combobox>
```

**Blueprint-React (After - dropdown)**:
```typescript
<FormItem
  label="Existing ISA provider"
  id="existingIsaProvider"
  render={(props) => (
    <FormSelect
      {...props}
      name="existingIsaProvider"
      value={selectedProvider}
      onChange={(e) => setSelectedProvider(e.target.value)}
    >
      <option value="">Enter name</option>
      <option value="providerA">Provider A</option>
      <option value="providerB">Provider B</option>
    </FormSelect>
  )}
/>
```

**Blueprint-React (After - autocomplete)**:
```typescript
<FormItem
  label="Existing ISA provider"
  id="existingIsaProvider"
  render={(props) => (
    <AutoComplete
      {...props}
      name="existingIsaProvider"
      value={selectedProvider}
      onChange={setSelectedProvider}
      options={providerOptions}
      placeholder="Enter name"
    />
  )}
/>
```
