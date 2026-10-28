# BDL Popover to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Popover (`<mca-popover>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-popover>` | `<PopupNav>` + `useToggle` + `useRef` hook pattern |
| `<mca-popover type="tooltip">` | Native `title` attribute or custom tooltip pattern |

**Important**: Unlike most BDL-to-Blueprint mappings, `<mca-popover>` does NOT map to a simple component swap. Blueprint-React's `<PopupNav>` uses a hook-based pattern that requires:
1. `useToggle` from `react-use` for open/close state management
2. `useRef<HTMLButtonElement>` (or `useRef<HTMLElement>`) for trigger element reference
3. Conditional rendering: `{isOpen && <PopupNav>...</PopupNav>}`

This makes popovers one of the more complex migrations — the BDL declarative attribute model is replaced by explicit React state and ref wiring.

### Comprehensive Popover Example

**MCA1 (Before)**:
```html
<mca-popover
  title=""
  aria-label=""
  message=""
  id=""
  type="popover"
  placement=""
  class=""
  icon=""
  width="small"
  click="no"
  message-ref=""
>
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
const [open, setIsOpen] = useToggle(false);
const triggerRef = useRef<HTMLButtonElement>(null);

<>
  <LinkButton
    media={<Icon icon="info" size="md" />}
    mediaPosition="left"
    aria-haspopup="menu"
    onClick={setIsOpen}
    ref={triggerRef}
  >
    Click to open
  </LinkButton>
  {open && (
    <PopupNav
      triggerRef={triggerRef}
      onClose={() => setIsOpen(false)}
    >
      <Ul noMarker>
        <Li><Link href="https://home.barclays">1st</Link></Li>
        <Li><Link href="https://home.barclays">Second item</Link></Li>
        <Li><Link href="https://home.barclays">A very much longer link text</Link></Li>
        <Li><Link href="https://home.barclays">Item four</Link></Li>
        <Li><Link href="https://home.barclays">Item five</Link></Li>
      </Ul>
    </PopupNav>
  )}
</>
```

### Popover Attribute Mapping

| MCA1 Attribute | Blueprint-React | Notes |
|---|---|---|
| `title` | Accessible label or heading | Use `aria-label` or heading in PopupNav content |
| `message` | `children` of `<PopupNav>` | Content rendered inside PopupNav |
| `id` | `id` on trigger element | Pass to LinkButton or Button |
| `type="popover"` | `<PopupNav>` | Navigation popover |
| `type="tooltip"` | Native `title` attribute | Use `<LinkButton title="..." >` for simple tooltips |
| `icon` | `media={<Icon icon="..." />}` | Icon on trigger element |
| `placement` | `<PopupNav>` positioning | Auto-positioned; no manual placement prop |
| `click="yes"` / `click="no"` | `onClick` handler | Controls open/close trigger |
| `width` | CSS width styling | Apply to PopupNav wrapper if needed |

---

## Hook-Based Pattern Explained

BDL's `<mca-popover>` is a self-contained web component: you set attributes and it handles all toggle/positioning logic internally. Blueprint-React's `<PopupNav>` is a controlled component — you must manage:

- **Open/close state** via `useToggle` (from `react-use`) or `useState`
- **Trigger reference** via `useRef` — passed to both the trigger element and `<PopupNav>`'s `triggerRef` prop
- **Close callback** via the `onClose` prop — called when the user clicks outside or presses Escape
- **Conditional rendering** — `<PopupNav>` is only rendered when `isOpen` is `true`

```typescript
import { useRef } from "react";
import { useToggle } from "react-use";
import { PopupNav, Button } from "@barclays/blueprint-react";

const [isOpen, setIsOpen] = useToggle(false);
const triggerRef = useRef<HTMLButtonElement>(null);
```

---

### Basic Popover with Button Trigger

**MCA1 (Before)**:
```html
<mca-popover id="p_basic" message="This is the popover content." placement="bottom">
    Icon
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
import { useRef } from "react";
import { useToggle } from "react-use";
import { PopupNav, Button, Type } from "@barclays/blueprint-react";

const BasicPopover: React.FC = () => {
  const [isOpen, setIsOpen] = useToggle(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      <Button
        ref={triggerRef}
        variant="secondary"
        id="p_basic"
        onClick={setIsOpen}
        aria-expanded={isOpen}
      >
        Icon
      </Button>
      {isOpen && (
        <PopupNav
          triggerRef={triggerRef}
          onClose={() => setIsOpen(false)}
          placement="bottom left"
        >
          <Type>This is the popover content.</Type>
        </PopupNav>
      )}
    </>
  );
};
```

---

### Popover with Link Trigger

When the BDL popover wraps a link-styled trigger, use `<ButtonLink>` as the trigger element.

**MCA1 (Before)**:
```html
<mca-popover id="p_link" message="More information here." placement="top" icon="info">
    Help
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
import { useRef } from "react";
import { useToggle } from "react-use";
import { PopupNav, ButtonLink, Type, Icon } from "@barclays/blueprint-react";

const LinkPopover: React.FC = () => {
  const [isOpen, setIsOpen] = useToggle(false);
  const triggerRef = useRef<HTMLAnchorElement>(null);

  return (
    <>
      <ButtonLink
        ref={triggerRef}
        href="#"
        id="p_link"
        onClick={(e) => {
          e.preventDefault();
          setIsOpen();
        }}
        aria-expanded={isOpen}
      >
        <Icon icon="info" size="sm" /> Help
      </ButtonLink>
      {isOpen && (
        <PopupNav
          triggerRef={triggerRef}
          onClose={() => setIsOpen(false)}
          placement="top center"
        >
          <Type>More information here.</Type>
        </PopupNav>
      )}
    </>
  );
};
```

---

### Popover with Custom Placement

**MCA1 (Before)**:
```html
<mca-popover id="p_right" message="Positioned to the right." placement="right" width="400">
    Right Popover
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
import { useRef } from "react";
import { useToggle } from "react-use";
import { PopupNav, Button, Type } from "@barclays/blueprint-react";

const RightPopover: React.FC = () => {
  const [isOpen, setIsOpen] = useToggle(false);
  const triggerRef = useRef<HTMLButtonElement>(null);

  return (
    <>
      <Button
        ref={triggerRef}
        variant="secondary"
        id="p_right"
        onClick={setIsOpen}
        aria-expanded={isOpen}
      >
        Right Popover
      </Button>
      {isOpen && (
        <PopupNav
          triggerRef={triggerRef}
          onClose={() => setIsOpen(false)}
          placement="bottom right"
        >
          <Type>Positioned to the right.</Type>
        </PopupNav>
      )}
    </>
  );
};
```

**Note**: BDL's `placement="right"` does not have an exact Blueprint-React equivalent. See the Placement Mapping table below for the closest alternatives.

---

### Click-to-Toggle Popover

BDL's `click="yes"` enables click-to-toggle behaviour. In Blueprint-React, the hook pattern is inherently click-to-toggle, so no additional configuration is needed.

**MCA1 (Before)**:
```html
<mca-popover id="p_click" message="Click to toggle me." click="yes" placement="bottom">
    Toggle
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
// The standard hook pattern already provides click-to-toggle behaviour.
// No special prop is needed — the onClick handler on the trigger element toggles state.
const [isOpen, setIsOpen] = useToggle(false);
const triggerRef = useRef<HTMLButtonElement>(null);

<Button ref={triggerRef} variant="secondary" id="p_click" onClick={setIsOpen}>
  Toggle
</Button>
{isOpen && (
  <PopupNav triggerRef={triggerRef} onClose={() => setIsOpen(false)} placement="bottom left">
    <Type>Click to toggle me.</Type>
  </PopupNav>
)}
```

---

### Popover with aria-label

**MCA1 (Before)**:
```html
<mca-popover id="p_aria" message="Accessible popover." aria-label="More options" placement="bottom">
    Options
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
const [isOpen, setIsOpen] = useToggle(false);
const triggerRef = useRef<HTMLButtonElement>(null);

<Button
  ref={triggerRef}
  variant="secondary"
  id="p_aria"
  onClick={setIsOpen}
  aria-label="More options"
  aria-expanded={isOpen}
>
  Options
</Button>
{isOpen && (
  <PopupNav
    triggerRef={triggerRef}
    onClose={() => setIsOpen(false)}
    placement="bottom left"
    ariaLabelText="More options"
  >
    <Type>Accessible popover.</Type>
  </PopupNav>
)}
```

---

## Tooltip Alternative

For BDL popovers using `type="tooltip"` (simple hover text), do NOT use `<PopupNav>`. Instead, use the native HTML `title` attribute or a lightweight custom tooltip pattern.

**MCA1 (Before)**:
```html
<mca-popover id="p_tooltip" type="tooltip" title="Helpful hint" placement="top">
    Hover me
</mca-popover>
```

**Blueprint-React (After)**:
```typescript
// For simple tooltips, use the native title attribute
<Button variant="secondary" id="p_tooltip" title="Helpful hint">
  Hover me
</Button>
```

**Note**: If rich tooltip content (HTML, icons, etc.) is needed, use the `<PopupNav>` hook pattern with hover event handlers (`onMouseEnter`/`onMouseLeave`) instead of click toggle. However, for plain text tooltips the native `title` attribute is preferred.

---

## Placement Mapping

BDL supports many placement values. Blueprint-React's `<PopupNav>` supports a limited set. Map BDL placements to the closest Blueprint-React equivalent.

| MCA1 `placement` | Blueprint-React `placement` | Notes |
|---|---|---|
| `"top"` | `"top center"` | |
| `"top-left"` | `"top left"` | |
| `"top-right"` | `"top right"` | |
| `"bottom"` | `"bottom center"` | Default-like behaviour |
| `"bottom-left"` | `"bottom left"` | Blueprint-React default |
| `"bottom-right"` | `"bottom right"` | |
| `"left"` | `"top left"` | No direct left equivalent — closest is top left |
| `"left-top"` | `"top left"` | |
| `"left-bottom"` | `"bottom left"` | |
| `"right"` | `"top right"` | No direct right equivalent — closest is top right |
| `"right-top"` | `"top right"` | |
| `"right-bottom"` | `"bottom right"` | |
| `"vertical"` | `"bottom center"` | Falls back to vertical default |
| `"horizontal"` | `"bottom left"` | Falls back to horizontal default |
| `"auto"` | `"bottom left"` | Blueprint-React default — no auto-positioning |
| `"auto-top"` | `"top center"` | |
| `"auto-right"` | `"top right"` | |
| `"auto-bottom"` | `"bottom center"` | |
| `"auto-left"` | `"top left"` | |

**Note**: Blueprint-React's `<PopupNav>` does not support `left` or `right` primary axis placement. BDL placements with `left` or `right` as the primary axis are mapped to the nearest `top` or `bottom` equivalent. If precise left/right positioning is critical, custom CSS positioning may be required.

---

## Complete `<mca-popover>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | Trigger element (`Button`) | Mandatory unique identifier |
| `class` | `className` | Trigger element | React convention |
| Text content | `children` | Trigger element | Button/link label |
| `message` | `children` | `PopupNav` | Popover body content — wrap in `<Type>` |
| `title` | `title` attribute on trigger | Trigger element | For tooltip hover text; not a `PopupNav` prop |
| `aria-label` | `ariaLabelText` + `aria-label` | `PopupNav` + trigger | Set on both for full accessibility |
| `icon` | `media={<Icon icon="..." size="sm" />}` | Trigger `Button` | Map icon name to Blueprint equivalent; see [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md) |
| `type="popover"` | `<PopupNav>` | Component choice | Default — use hook pattern |
| `type="tooltip"` | `title` attribute | Trigger element | Use native `title` for plain text; `<PopupNav>` with hover for rich content |
| `placement` | `placement` | `PopupNav` | See Placement Mapping table above |
| `width` | `width` | `PopupNav` | `"auto"` or `"sm"` — no arbitrary pixel values; use CSS override if needed |
| `click="yes"` | (inherent) | N/A | Hook pattern is click-based by default |
| `click="no"` | Hover handlers | Trigger element | Use `onMouseEnter`/`onMouseLeave` instead of `onClick` |

### Required Imports

```typescript
import { useRef } from "react";
import { useToggle } from "react-use";
import { PopupNav, Button, Type, Icon } from "@barclays/blueprint-react";
```

### Migration Checklist

- [ ] Replace `<mca-popover>` with trigger element + conditional `<PopupNav>`
- [ ] Add `useToggle` and `useRef` hooks
- [ ] Wire `triggerRef` to both the trigger element and `<PopupNav>`
- [ ] Map `placement` using the Placement Mapping table
- [ ] Move `message` content into `<PopupNav>` children
- [ ] Add `aria-expanded={isOpen}` to the trigger element for accessibility
- [ ] For `type="tooltip"`, use native `title` attribute instead of `<PopupNav>`
- [ ] Map `icon` names using [BDL_ICON_MAPPING.md](BDL_ICON_MAPPING.md)
