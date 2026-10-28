# LEGACY_DIALOG_TOOLTIP_MAPPING.md

## Overview

Maps MCA1 legacy dialog, popup, tooltip, and inline tooltip patterns to Blueprint-React equivalents. These components all used jQuery UI `.dialog()` or custom controller APIs (`showDialog()`, `WindowManager`).

---

## Detection Patterns

```grep
\.dialog\(
\.dialog\("close"\)
dialogClass.*scp-dialog
dialogClass.*scp-popup
WindowManager\.launchWindow\(
WindowManager\.closeWindow\(
this\.showDialog\(
\.controller\(\)\.showDialog\(
scp-help-text
help-text=
tooltip-dialog
css_tooltip
scp-close-link
steal\("scp/ui/common/vendor/jquery/ui/dialog\.js"\)
```

---

## Conversion: steal() → ES imports

```javascript
// MCA1
steal("scp/ui/common/vendor/jquery/ui/dialog.js").then(function() {
  $(el).dialog({ modal: true });
});

// MCA2
import { Dialog, Button, Type } from '@barclays/blueprint-react';
```

---

## Component: Confirmation Dialog (`scp-dialog`)

### MCA1 Pattern (jQuery)

```javascript
$('#showDialog').click(function(event) {
  var dialogContainer = $('<div>Are you sure you want to proceed?</div>');
  dialogContainer.dialog({
    buttons: {
      button1: {
        text: 'Confirm',
        click: function() { alert('Confirmed'); },
        class: 'scp-critical-button'
      },
      button2: {
        text: 'Cancel',
        click: function() { dialogContainer.dialog("close"); },
        class: 'scp-button-secondary'
      }
    },
    modal: true,
    dialogClass: "scp-dialog",
    closeOnEscape: false
  });
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Dialog, Button, Type, Arrange, ArrangeItem } from '@barclays/blueprint-react';

export const ConfirmDialog: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  const handleConfirm = () => {
    // perform action
    setIsOpen(false);
  };

  return (
    <>
      <Button variant="primary" onClick={() => setIsOpen(true)}>Show Dialog</Button>
      <Dialog
        open={isOpen}
        onClose={() => setIsOpen(false)}
        head={<Type element="h3" size="md" weight="medium">Confirmation</Type>}
        foot={
          <Arrange gap="fixed">
            <ArrangeItem size="fit">
              <Button variant="secondary" onClick={() => setIsOpen(false)}>Cancel</Button>
            </ArrangeItem>
            <ArrangeItem size="fit">
              <Button variant="primary" onClick={handleConfirm}>Confirm</Button>
            </ArrangeItem>
          </Arrange>
        }
      >
        <Type>Are you sure you want to proceed?</Type>
      </Dialog>
    </>
  );
};
```

### Options → Props Mapping

| MCA1 Option | Blueprint Prop | Notes |
|-------------|---------------|-------|
| `modal: true` | Default behavior | Dialog always has backdrop |
| `dialogClass: "scp-dialog"` | Not needed | Blueprint handles styling |
| `closeOnEscape: false` | `onClose` controls dismissal | Handle ESC in onClose if needed |
| `buttons` object | `foot` slot prop | Render buttons in footer |
| `title` | `head` slot prop | Render heading in header |
| `.dialog("close")` | `setIsOpen(false)` | State-driven open/close |

---

## Component: Popup Modal (`scp-popup`)

### MCA1 Pattern (jQuery)

```javascript
$('#displayPopup').click(function(event) {
  var dialogContainer = $('<div>Popup content here</div>');
  dialogContainer.dialog({
    buttons: {
      button1: { text: 'OK', click: function() { alert('OK'); }, class: 'scp-button-remove' }
    },
    title: "This is a dialog popup",
    modal: true,
    dialogClass: "scp-popup",
    closeOnEscape: true
  });
});
```

### MCA1 Pattern (WindowManager)

```javascript
// Launch lightbox
var processId = scp.colleague.casehandling.controllers.YOUR_LIGHT_BOX;
scp.ui.container.WindowManager.launchWindow({
  config: this.config,
  type: "lightbox",
  hub: this.hub,
  workflow: this.workflow,
  processId: processId
});

// Close
scp.ui.container.WindowManager.closeWindow();
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Dialog, Button, Type, Icon } from '@barclays/blueprint-react';

export const PopupModal: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button variant="primary" onClick={() => setIsOpen(true)}>Open Popup</Button>
      <Dialog
        open={isOpen}
        onClose={() => setIsOpen(false)}
        head={<Type element="h3" size="md" weight="medium">This is a dialog popup</Type>}
        foot={
          <Button variant="primary" onClick={() => setIsOpen(false)}>OK</Button>
        }
      >
        <Type>Popup content here</Type>
      </Dialog>
    </>
  );
};
```

---

## Component: Tooltip (Controller-based)

### MCA1 Pattern (jQuery/JMVC)

```javascript
// Inside a JMVC controller
"#help-field click": function() {
  var options = {
    title: "Help",
    contentEle: $("#help-field"),
    dialogClass: "tooltip-dialog"
  };
  this.showDialog(options);
}
```

```html
<span id="help-field" class="css_tooltip scp-clickable">
  <div id="help-content" class="scp-hide">
    Help content that is hidden and shown in tooltip dialog.
  </div>
</span>
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import { Dialog, Button, Type, Icon } from '@barclays/blueprint-react';

export const HelpTooltip: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <Button variant="subtle" onClick={() => setIsOpen(true)}>
        <Icon icon="info-fill" size="sm" />
      </Button>
      <Dialog
        open={isOpen}
        onClose={() => setIsOpen(false)}
        head={<Type element="h3" size="md" weight="medium">Help</Type>}
      >
        <Type>Help content that was previously hidden in a tooltip dialog.</Type>
      </Dialog>
    </>
  );
};
```

**Note:** For simple hover tooltips, use the native `title` attribute or Blueprint's tooltip pattern if available. For content-rich "tooltips" that are actually small dialogs, use `Dialog` as shown above.

---

## Component: Inline Tooltip (Declarative)

### MCA1 Pattern (HTML only)

```html
<label for="helpId1" class="two-columns scp-label">Field One
  <span class="scp-help-text scp-info-img" help-text="Help text for field one."></span>
</label>
<input id="helpId1" type="text" class="scp-input-text two-columns">
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { FormItem, FormInput, Type, Icon } from '@barclays/blueprint-react';

export const FieldWithHelp: React.FC = () => (
  <FormItem
    label={
      <Type>
        Field One{' '}
        <Icon icon="info-fill" size="xs" title="Help text for field one." />
      </Type>
    }
    render={(props) => (
      <FormInput {...props} />
    )}
  />
);
```

**Alternative — using `helper` prop on FormItem:**

```typescript
<FormItem
  label={<Type>Field One</Type>}
  helper={<Type size="sm">Help text for field one.</Type>}
  render={(props) => (
    <FormInput {...props} />
  )}
/>
```

---

## Button Class Mapping

| MCA1 CSS Class | Blueprint Equivalent |
|----------------|---------------------|
| `scp-critical-button` | `<Button variant="primary">` (destructive context) |
| `scp-button-secondary` | `<Button variant="secondary">` |
| `scp-button-remove` | `<Button variant="primary">` with destructive styling |
| `scp-button-cancel` | `<Button variant="secondary">` |

---

## Event Handlers Mapping

| MCA1 Event | React Equivalent | Notes |
|------------|-----------------|-------|
| `buttons.click` callback | `onClick` on Button in `foot` | Each button gets its own handler |
| `.dialog("close")` | `setIsOpen(false)` | State-driven |
| `WindowManager.closeWindow()` | `setIsOpen(false)` | Same pattern |
| `.scp-close-link click` | `onClose` prop on Dialog | Built-in close button |
| `mouseover` (inline tooltip) | `title` attribute or `helper` prop | Native browser tooltip |

---

## Iron Rules

1. **Dialog uses `head` and `foot` slot props** — NOT `DialogHeader` / `DialogFooter` (they don't exist)
2. **Never dynamically create DOM for dialogs** — use `useState` boolean + conditional Dialog rendering
3. **WindowManager patterns → single Dialog with state** — no need for separate controller/lightbox infrastructure
4. **Hidden content patterns (`scp-hide`) → just render content inside Dialog** — no need to clone/move DOM
5. **For simple hover help text, use `title` attribute or `helper` prop** — don't create a Dialog for a one-line tooltip
6. **`closeOnEscape: false` is rare** — Dialog always supports ESC by default; only override if business requires it
