# BDL Accordion and Separator to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Accordion (`<mca-accordion>` + `<mca-accordionitem>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-accordion>` | `<Accordion>` |
| `<mca-accordionitem>` | `<AccordionItem>` |

Blueprint-React's `<Accordion>` wraps multiple `<AccordionItem>` children. Each `<AccordionItem>` uses a `head` prop for the header text and renders body content as children.

---

### Comprehensive Accordion with Multiple Items and Embedded Controls

**MCA1 (Before)**:
```html
<mca-accordion id="b_accordion_enabled" class="accordion_class" disabled="no" tabindex="1" title="Accordion Example 1" open="0">
  <mca-accordionitem id="b_accordion_enabled_accordionitem1" class="accordionClass" highlight="item" highlight-color="alert" sub-header="Sub header" title="Accordion item 1" header="Accordion item 1" tabindex="3">
    Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate. Nam tincidunt libero mi, ac aliquet purus varius eget. Aenean sit amet ligula accumsan, mattis quam in, suscipit erat. Ut sed mauris in nisl interdum porta a eu sapien. Vestibulum commodo finibus nisl non viverra. Etiam vel elit et enim sodales cursus. Donec vehicula risus sed pharetra interdum
    <mca-button id="button" size="medium">ClickMe</mca-button>
    <mca-link id="link" icon="facebook">Facebook</mca-link>
  </mca-accordionitem>
  <mca-accordionitem id="b_accordion_enabled_accordionitem2" class="accordionClass" title="Accordion item 2" header="Accordion item 2">
    Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate.
  </mca-accordionitem>
</mca-accordion>
<mca-accordion id="b_accordion_disabled" class="accordion_class" disabled="yes" tabindex="2" title="Accordion Example 2">
  <mca-accordionitem id="b_accordion_disabled_accordionitem1" class="accordionItemClass" title="Accordion item 1" header="Accordion item 1">
    Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate.
  </mca-accordionitem>
  <mca-accordionitem id="b_accordion_disabled_accordionitem2" class="accordionItemClass" title="Accordion item 2" header="Accordion item 2">
    Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate.
  </mca-accordionitem>
</mca-accordion>
```

**Blueprint-React (After)**:
```typescript
<Accordion>
  <AccordionItem id="accordion-item-1" title="Accordion Item 1">
    <Type>
      Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate. Nam tincidunt libero mi, ac aliquet purus varius eget. Aenean sit amet ligula accumsan, mattis quam in, suscipit erat. Ut sed mauris in nisl interdum porta a eu sapien. Vestibulum commodo finibus nisl non viverra. Etiam vel elit et enim sodales cursus. Donec vehicula risus sed pharetra interdum
    </Type>
    <Arrange gap="fixed">
      <ArrangeItem size="fit">
        <Button variant="secondary" size="sm">ClickMe</Button>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Link href="#">Facebook</Link>
      </ArrangeItem>
    </Arrange>
  </AccordionItem>
  <AccordionItem id="accordion-item-2" title="Accordion Item 2">
    <Type>
      Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate.
    </Type>
  </AccordionItem>
  <AccordionItem id="accordion-item-3" title="Accordion Item 3">
    <Type>
      Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate.
    </Type>
  </AccordionItem>
  <AccordionItem id="accordion-item-4" title="Accordion Item 4">
    <Type>
      Etiam aliquam et nulla non euismod. In tempor lorem nec tellus elementum vulputate.
    </Type>
  </AccordionItem>
</Accordion>
```

### Accordion with Multiple Items, Highlight, Sub-Header, and Embedded Controls

**MCA1 (Before - Simpler)**:
```html
<mca-accordion id="b_accordion_enabled" class="accordion_class" disabled="no"
    tabindex="1" title="Accordion Example 1" open="0">
    <mca-accordionitem id="b_accordion_enabled_accordionitem1"
        class="accordionClass" highlight="item" highlight-color="alert"
        sub-header="Sub header" title="Accordion item 1"
        header="Accordion item 1" tabindex="3">
        Etiam aliquam et nulla non euismod. In tempor lorem nec tellus
        elementum vulputate...
        <mca-button id="button" size="medium">ClickMe</mca-button>
        <mca-link id="link" icon="facebook">Facebook</mca-link>
    </mca-accordionitem>
    <mca-accordionitem id="b_accordion_enabled_accordionitem2"
        class="accordionClass" title="Accordion item 2"
        header="Accordion item 2">
        Etiam aliquam et nulla non euismod. In tempor lorem nec tellus
        elementum vulputate...
    </mca-accordionitem>
</mca-accordion>
```

**Blueprint-React (After)**:
```typescript
// open="0" means the first item is expanded by default
const [openIndex, setOpenIndex] = useState<number | undefined>(0);

<Accordion
  id="b_accordion_enabled"
  className="accordion_class"
>
  <AccordionItem
    id="b_accordion_enabled_accordionitem1"
    className="accordionClass"
    head={
      <>
        <Type element="span">Accordion item 1</Type>
        <Type element="span" size="sm">Sub header</Type>
      </>
    }
    open={openIndex === 0}
    onToggle={() => setOpenIndex(openIndex === 0 ? undefined : 0)}
  >
    <Type element="p" marginBottom>
      Etiam aliquam et nulla non euismod. In tempor lorem nec tellus
      elementum vulputate...
    </Type>
    <Arrange gap="fixed">
      <ArrangeItem size="fit">
        <Button id="button" variant="secondary" onClick={handleClick}>
          ClickMe
        </Button>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button id="link" variant="subtle" onClick={handleFacebookClick}>
          Facebook
        </Button>
      </ArrangeItem>
    </Arrange>
  </AccordionItem>

  <AccordionItem
    id="b_accordion_enabled_accordionitem2"
    className="accordionClass"
    head={<Type element="span">Accordion item 2</Type>}
    open={openIndex === 1}
    onToggle={() => setOpenIndex(openIndex === 1 ? undefined : 1)}
  >
    <Type element="p">
      Etiam aliquam et nulla non euismod. In tempor lorem nec tellus
      elementum vulputate...
    </Type>
  </AccordionItem>
</Accordion>
```

**Key mapping notes**:
- `<mca-button>` inside accordion content maps to `<Button>` (see [BDL_BUTTON_MAPPING.md](BDL_BUTTON_MAPPING.md))
- `<mca-link>` maps to `<Button variant="subtle">` (see [BDL_BUTTON_MAPPING.md](BDL_BUTTON_MAPPING.md))
- `highlight-color="alert"` has no direct Blueprint equivalent — use conditional styling or Alert variant if needed
- `sub-header` is rendered as a secondary `<Type>` inside the `head` prop
- `open="0"` means the item at index 0 is expanded by default — manage via controlled state

---

### Disabled Accordion

MCA1's `disabled="yes"` on `<mca-accordion>` disables all items. In Blueprint-React, pass `disabled` to each `<AccordionItem>`.

**MCA1 (Before)**:
```html
<mca-accordion id="b_accordion_disabled" class="accordion_class" disabled="yes"
    tabindex="2" title="Accordion Example 2">
    <mca-accordionitem id="b_accordion_disabled_accordionitem1"
        class="accordionItemClass" title="Accordion item 1"
        header="Accordion item 1">
        Etiam aliquam et nulla non euismod...
    </mca-accordionitem>
    <mca-accordionitem id="b_accordion_disabled_accordionitem1"
        class="accordionItemClass" title="Accordion item 2"
        header="Accordion item 2">
        Etiam aliquam et nulla non euismod...
    </mca-accordionitem>
</mca-accordion>
```

**Blueprint-React (After)**:
```typescript
<Accordion
  id="b_accordion_disabled"
  className="accordion_class"
>
  <AccordionItem
    id="b_accordion_disabled_accordionitem1"
    className="accordionItemClass"
    head={<Type element="span">Accordion item 1</Type>}
    disabled
  >
    <Type element="p">Etiam aliquam et nulla non euismod...</Type>
  </AccordionItem>

  <AccordionItem
    id="b_accordion_disabled_accordionitem2"
    className="accordionItemClass"
    head={<Type element="span">Accordion item 2</Type>}
    disabled
  >
    <Type element="p">Etiam aliquam et nulla non euismod...</Type>
  </AccordionItem>
</Accordion>
```

**Note**: MCA1 puts `disabled="yes"` on the parent `<mca-accordion>`. Blueprint-React does not have a group-level disabled prop on `<Accordion>` — apply `disabled` to each `<AccordionItem>` individually. If dynamically controlled, derive from a shared state variable:

```typescript
const isAccordionDisabled = true;

<AccordionItem disabled={isAccordionDisabled} head={...}>
  ...
</AccordionItem>
```

---

### Complete `<mca-accordion>` Attribute Mapping

**`<mca-accordion>` (group wrapper)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Accordion` | |
| `class` | `className` | `Accordion` | React convention |
| `title` | N/A | N/A | Informational; not rendered by Blueprint `Accordion` |
| `disabled="yes"` | `disabled` on each `AccordionItem` | `AccordionItem` | No group-level disabled; apply per item |
| `disabled="no"` | (omit `disabled`) | `AccordionItem` | Default is enabled |
| `tabindex` | `tabIndex` | `Accordion` or `AccordionItem` | camelCase in React |
| `open="0"` | Controlled `open` state on item at index 0 | `AccordionItem` | Manage which item is expanded via state |

**`<mca-accordionitem>` (individual item)**:
| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `AccordionItem` | |
| `class` | `className` | `AccordionItem` | React convention |
| `header` | `head` | `AccordionItem` | Pass as ReactNode (e.g. `<Type>`) |
| `title` | `head` | `AccordionItem` | Same as `header` — use `head` prop |
| `sub-header` | Secondary `<Type>` inside `head` | `AccordionItem` head | Compose header + sub-header in `head` prop |
| `highlight="item"` | N/A | N/A | No direct equivalent; use conditional CSS class if needed |
| `highlight-color="alert"` | N/A | N/A | No direct equivalent; use `<Alert>` inside content or CSS class |
| `tabindex` | `tabIndex` | `AccordionItem` | camelCase in React |
| Children (text + components) | `children` | `AccordionItem` | Wrap text in `<Type>`, map `<mca-button>` to `<Button>`, `<mca-link>` to `<Button variant="subtle">` |

---

## Separator

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-separator>` | `<Separator>` |

```html
<!-- MCA1 -->
<mca-separator></mca-separator>
```

```typescript
// Blueprint-React
<Separator />
```
