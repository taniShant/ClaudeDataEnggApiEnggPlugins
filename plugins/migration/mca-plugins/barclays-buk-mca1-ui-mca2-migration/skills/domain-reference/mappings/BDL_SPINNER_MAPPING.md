# BDL Spinner to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Spinner (`<mca-spinner>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-spinner>` | `<Loading>` |

> **Do NOT use `<Icon icon="spinner">`** — there is no spinner icon in Blueprint-React. Always use the `<Loading>` component for loading indicators.

---

### Basic Spinner

**MCA1 (Before)**:
```html
<mca-spinner
  aria-text=""
  id=""
  class=""
  fullscreen="no"
  fade="yes"
  size="md"
>
</mca-spinner>
```

**Blueprint-React (After)**:
```typescript
<Loading shape="square" size="sm" />
```

### Spinner Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `id` | `id` | Element identifier |
| `class` | `className` | React convention |
| `size="md"` | `size="sm"` or `size="md"` | Valid: sm, md, lg |
| `size="lg"` | `size="lg"` | Large spinner |
| `fullscreen="yes"` | Position fixed + overlay styling | Use CSS or wrapper div |
| `fade="yes"` | `opacity` / CSS transition | Use CSS for fade effect |
| `aria-text` | `ariaLabel` | Accessibility label for screen readers |

**Note**: MCA1's text content or `aria-text` maps to the `ariaLabel` prop on `<Loading>`. The `<Loading>` component is a visual-only spinner with no visible text — use `ariaLabel` for screen reader accessibility.

---

### Different Sizes (sm, md, lg)

**MCA1 (Before)**:
```html
<mca-spinner id="s_spinner_sm" size="sm">Loading</mca-spinner>
<mca-spinner id="s_spinner_md" size="md">Loading</mca-spinner>
<mca-spinner id="s_spinner_lg" size="lg">Loading</mca-spinner>
```

**Blueprint-React (After)**:
```typescript
<Loading id="s_spinner_sm" size="sm" ariaLabel="Loading" />
<Loading id="s_spinner_md" size="md" ariaLabel="Loading" />
<Loading id="s_spinner_lg" size="lg" ariaLabel="Loading" />
```

**Note**: Size values map directly — `sm`, `md`, `lg` are the same in both BDL and Blueprint-React. MCA1 defaults to `md` if `size` is omitted.

---

### Different Shapes (square, circle)

Blueprint-React's `<Loading>` supports a `shape` prop that controls the spinner's visual appearance. MCA1 does not have an equivalent attribute.

```typescript
<Loading shape="square" ariaLabel="Loading" />
<Loading shape="circle" ariaLabel="Loading" />
```

**Note**: `shape` defaults to `"square"`. Use `shape="circle"` when a rounded spinner is desired. There is no MCA1 equivalent — choose the shape that best fits the surrounding UI.

---

### Fullscreen Loading Pattern

MCA1's `fullscreen="yes"` renders a full-page overlay spinner. Blueprint-React has no direct fullscreen loading prop. Use a `<Dialog>` or a full-page layout wrapper instead.

**MCA1 (Before)**:
```html
<mca-spinner id="s_spinner_fullscreen" fullscreen="yes" fade="yes">
    Loading your data
</mca-spinner>
```

**Blueprint-React (After) — Dialog approach**:
```typescript
const [isLoading, setIsLoading] = useState<boolean>(true);

{isLoading && (
  <Dialog
    id="s_spinner_fullscreen"
    open={isLoading}
    onOpenChange={() => {}}
    head={<></>}
    foot={<></>}
  >
    <Arrange justify="center" align="center" direction="column" gap="fixed">
      <ArrangeItem size="fit">
        <Loading size="lg" ariaLabel="Loading your data" />
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Type>Loading your data</Type>
      </ArrangeItem>
    </Arrange>
  </Dialog>
)}
```

**Blueprint-React (After) — CSS overlay approach**:
```typescript
const [isLoading, setIsLoading] = useState<boolean>(true);

{isLoading && (
  <div
    id="s_spinner_fullscreen"
    style={{
      position: 'fixed',
      top: 0,
      left: 0,
      width: '100%',
      height: '100%',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      backgroundColor: 'rgba(255, 255, 255, 0.8)',
      zIndex: 9999,
    }}
  >
    <Arrange justify="center" align="center" direction="column" gap="fixed">
      <ArrangeItem size="fit">
        <Loading size="lg" ariaLabel="Loading your data" />
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Type>Loading your data</Type>
      </ArrangeItem>
    </Arrange>
  </div>
)}
```

**Note**: MCA1's `fade="yes"` creates a semi-transparent backdrop. In the CSS overlay approach, `backgroundColor: 'rgba(255, 255, 255, 0.8)'` replicates this effect. The Dialog approach uses Blueprint's built-in backdrop.

---

### With Custom Accessibility Text

MCA1 uses `aria-text` for custom screen reader labels. In Blueprint-React, use the `ariaLabel` prop.

**MCA1 (Before)**:
```html
<mca-spinner id="s_spinner_aria" aria-text="Please wait while we process your request">
    Processing
</mca-spinner>
```

**Blueprint-React (After)**:
```typescript
<Loading
  id="s_spinner_aria"
  ariaLabel="Please wait while we process your request"
/>
```

**Note**: MCA1's `aria-text` and text content are separate — `aria-text` is for screen readers, text content is the visible label. In Blueprint-React, `<Loading>` has no visible text; use `ariaLabel` for screen reader text and add a `<Type>` sibling for visible text if needed:

```typescript
<Arrange align="center" gap="fixed">
  <ArrangeItem size="fit">
    <Loading ariaLabel="Please wait while we process your request" />
  </ArrangeItem>
  <ArrangeItem size="fit">
    <Type>Processing</Type>
  </ArrangeItem>
</Arrange>
```

---

### Inline Spinner (Inside Button or Paragraph)

MCA1 spinners can be placed inline within other content. In Blueprint-React, use `<Loading>` with `size="sm"` alongside other elements.

**MCA1 (Before)**:
```html
<mca-button id="b_submit" type="primary" disabled="yes">
    <mca-spinner id="s_spinner_inline" size="sm">Submitting</mca-spinner>
</mca-button>
```

**Blueprint-React (After)**:
```typescript
const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

<Button
  variant="primary"
  id="b_submit"
  disabled={isSubmitting}
  media={isSubmitting ? <Loading size="sm" ariaLabel="Submitting" /> : undefined}
  onClick={handleSubmit}
>
  {isSubmitting ? 'Submitting...' : 'Submit'}
</Button>
```

**Inside a paragraph**:

**MCA1 (Before)**:
```html
<p>Please wait <mca-spinner id="s_spinner_text" size="sm">loading</mca-spinner> while we fetch your data.</p>
```

**Blueprint-React (After)**:
```typescript
<Type>
  Please wait{' '}
  <Loading size="sm" ariaLabel="loading" />{' '}
  while we fetch your data.
</Type>
```

---

### Conditional Spinner (Show/Hide API)

MCA1 uses an imperative `show(bool)` API to toggle spinner visibility. In Blueprint-React, use conditional rendering with React state.

**MCA1 (Before)**:
```html
<mca-spinner id="s_spinner_toggle">Loading</mca-spinner>

<script>
    var spinner = document.getElementById('s_spinner_toggle');
    spinner.show(true);   // show
    spinner.show(false);  // hide
    spinner.text({ text: 'Saving...', 'aria-text': 'Saving your changes' }); // update text
</script>
```

**Blueprint-React (After)**:
```typescript
const [isLoading, setIsLoading] = useState<boolean>(false);
const [loadingText, setLoadingText] = useState<string>('Loading');

// Replaces spinner.show(true) / spinner.show(false)
setIsLoading(true);
setIsLoading(false);

// Replaces spinner.text({ text: 'Saving...', 'aria-text': 'Saving your changes' })
setLoadingText('Saving...');

{isLoading && (
  <Arrange align="center" gap="fixed">
    <ArrangeItem size="fit">
      <Loading ariaLabel={loadingText} />
    </ArrangeItem>
    <ArrangeItem size="fit">
      <Type>{loadingText}</Type>
    </ArrangeItem>
  </Arrange>
)}
```

**Note**: MCA1's imperative `show()` and `text()` APIs are replaced by React's declarative state management. Use `useState` to control visibility and text dynamically.

---

## Complete `<mca-spinner>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Loading` | |
| `class` | `className` | `Loading` | React convention |
| Text content | `ariaLabel` | `Loading` | `<Loading>` has no visible text; add a `<Type>` sibling for visible text |
| `aria-text` | `ariaLabel` | `Loading` | Default: `"Loading, please wait"` |
| `size="sm"` | `size="sm"` | `Loading` | |
| `size="md"` | `size="md"` | `Loading` | Default size |
| `size="lg"` | `size="lg"` | `Loading` | |
| `fullscreen="yes"` | Wrap in `<Dialog>` or CSS overlay | Layout wrapper | No direct prop; see Fullscreen Loading Pattern above |
| `fullscreen="no"` | (default — inline) | `Loading` | Default behaviour |
| `fade="yes"` | Backdrop styling on wrapper | Layout wrapper | Semi-transparent overlay via CSS or Dialog backdrop |
| `fade="no"` | (omit backdrop styling) | Layout wrapper | No fade effect |
| (shape — no BDL equivalent) | `shape="square"` or `shape="circle"` | `Loading` | Default: `"square"` |
| `show(bool)` API | Conditional rendering via `useState` | N/A | `{isLoading && <Loading />}` |
| `text({text, aria-text})` API | State-driven `ariaLabel` + `<Type>` | N/A | Use `useState` to update text dynamically |
