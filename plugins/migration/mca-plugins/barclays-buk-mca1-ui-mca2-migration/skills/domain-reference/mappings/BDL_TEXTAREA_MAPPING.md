# BDL Textarea to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Textarea (`<mca-textarea>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-textarea>` | `<FormItem>` + `<FormTextarea>` |

### Basic Textarea

**MCA1 (Before)**:
```html
<mca-textarea id="b_textarea"
    placeholder="Ability to hold multiline text and is editable. This can be used for detail description of the context">
    Textarea Multiline
</mca-textarea>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Textarea Multiline"
  id="b_textarea"
  render={(props) => (
    <FormTextarea
      {...props}
      name="b_textarea"
      placeholder="Ability to hold multiline text and is editable. This can be used for detail description of the context"
      rows={4}
      value={value}
      onChange={(e) => setValue(e.target.value)}
    />
  )}
/>
```

### Restricted Character Check

MCA1's `restrictedcharcheck="yes"` blocks certain characters at input time. Blueprint-React has no built-in equivalent; implement as a custom `onChange` handler that strips or rejects restricted characters.

**MCA1 (Before)**:
```html
<mca-textarea id="v_textarea_restrictedChar" placeholder="Some placeholder"
    restrictedcharcheck="yes">
    Example for Restricted characters Only apply restrictedcharcheck="yes"
</mca-textarea>
```

**Blueprint-React (After)**:
```typescript
// Restricted characters regex (adjust to match your app's restricted set)
const RESTRICTED_CHARS = /[<>{}[\]\\\/^~`|]/g;

<FormItem
  label="Example for Restricted characters"
  id="v_textarea_restrictedChar"
  render={(props) => (
    <FormTextarea
      {...props}
      name="v_textarea_restrictedChar"
      placeholder="Some placeholder"
      rows={4}
      value={value}
      onChange={(e) => {
        const cleaned = e.target.value.replace(RESTRICTED_CHARS, '');
        setValue(cleaned);
      }}
    />
  )}
/>
```

### Profanity Filter (ignorewords)

MCA1's `ignorewords` attribute accepts a JSON array of blocked words and prevents them from being entered. In Blueprint-React, implement as custom validation logic on change or blur.

**MCA1 (Before)**:
```html
<mca-textarea id="b_textarea_profinityfilter" placeholder="Some placeholder"
    disabled="no" restrictedcharcheck="yes"
    ignorewords="<%= JSON.stringify(blockcontent) %>">
    Text Area Profinity filter example
</mca-textarea>
```

**Blueprint-React (After)**:
```typescript
// blockedWords comes from config/API (equivalent to blockcontent in MCA1)
const blockedWords: string[] = ['bad', 'evil', ...]; // loaded from backend

const containsBlockedWord = (text: string): string | undefined => {
  const lower = text.toLowerCase();
  return blockedWords.find((word) => lower.includes(word.toLowerCase()));
};

// Component
const [profanityError, setProfanityError] = useState<string | undefined>();

<FormItem
  label="Text Area Profanity filter example"
  id="b_textarea_profinityfilter"
  error={profanityError && <Type color="error">{profanityError}</Type>}
  render={(props) => (
    <FormTextarea
      {...props}
      name="b_textarea_profinityfilter"
      placeholder="Some placeholder"
      rows={4}
      value={value}
      onChange={(e) => {
        // Restricted character check
        const cleaned = e.target.value.replace(RESTRICTED_CHARS, '');
        // Profanity check
        const blocked = containsBlockedWord(cleaned);
        setProfanityError(blocked ? `"${blocked}" is not allowed` : undefined);
        setValue(cleaned);
      }}
    />
  )}
/>
```

### Disabled Textarea

**MCA1 (Before)**:
```html
<mca-textarea id="b_textarea_disabled" placeholder="Some placeholder" disabled="yes">
    Disabled Textarea
</mca-textarea>
```

**Blueprint-React (After)**:
```typescript
<FormItem
  label="Disabled Textarea"
  id="b_textarea_disabled"
  render={(props) => (
    <FormTextarea
      {...props}
      name="b_textarea_disabled"
      placeholder="Some placeholder"
      rows={4}
      disabled
    />
  )}
/>
```

### Complete `<mca-textarea>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `FormItem` | |
| Text content | `label` | `FormItem` | |
| `placeholder` | `placeholder` | `FormTextarea` | |
| `disabled="yes"` | `disabled` | `FormTextarea` | Boolean prop |
| `disabled="no"` | (omit or `disabled={false}`) | `FormTextarea` | Default is enabled |
| `restrictedcharcheck="yes"` | Custom `onChange` handler | N/A | Strip chars via regex |
| `ignorewords` | Custom validation logic | N/A | Check against blocked word list on change/blur; show error via `FormItem` `error` prop |
