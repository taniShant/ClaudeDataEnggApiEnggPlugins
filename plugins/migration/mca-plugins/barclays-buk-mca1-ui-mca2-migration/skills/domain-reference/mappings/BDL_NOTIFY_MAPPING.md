# BDL Alerts and Notifications to Blueprint-React Mapping

**Last Updated**: April 16, 2026

---

## Alerts and Notifications (`<mca-notify>`)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-notify>` | `<Alert>` |

### `message-context` to `variant` Mapping

MCA1 has many `message-context` values. Blueprint-React `<Alert>` supports four variants: `info`, `success`, `warning`, `error`. Map as follows:

| MCA1 `message-context` | Blueprint-React `variant` | Icon for `media` prop | Notes |
|---|---|---|---|
| (default / omitted) | `"info"` | `info-fill` | Default when no context is set |
| `"info"` | `"info"` | `info-fill` | |
| `"alert"` | `"warning"` | `warning` | |
| `"warn"` | `"warning"` | `warning` | |
| `"error"` | `"error"` | `error` | |
| `"fail"` | `"error"` | `error` | Treat as error |
| `"server-error"` | `"error"` | `error` | Treat as error |
| `"success"` | `"success"` | `success-fill` | |
| `"done"` | `"success"` | `success-fill` | Treat as success |
| `"mandatory"` | `"warning"` | `warning` | Important/mandatory content -> warning |

**IMPORTANT**: Alert does NOT have an `icon` prop. Always pass icons via the `media` prop: `media={<Icon icon="..." size="sm" />}`. Use `onDismiss` (NOT `onClose`) for dismissible alerts. The `head` prop accepts ReactNode — wrap in `<Type>` for consistent typography.

### Alert (Standard Context)

**MCA1 (Before)**:
```html
<mca-notify message-context="alert" id="b_notify_alert" message-title="Hi! Its an alert.">
    <mca-text>Alert Message</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="warning"
  id="b_notify_alert"
  head={<Type weight="medium" size="md">Hi! Its an alert.</Type>}
  media={<Icon icon="warning" size="sm" ariaHidden />}
>
  <Type>Alert Message</Type>
</Alert>
```

### Info (Default Context)

When `message-context` is omitted, MCA1 defaults to info.

**MCA1 (Before)**:
```html
<mca-notify message-title="Hey, its an info." id="b_notify_info">
    <mca-text>Info Message</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="info"
  id="b_notify_info"
  head={<Type weight="medium" size="md">Hey, its an info.</Type>}
  media={<Icon icon="info-fill" size="sm" ariaHidden />}
>
  <Type>Info Message</Type>
</Alert>
```

### Error

**MCA1 (Before)**:
```html
<mca-notify message-context="error" message-title="Its an Error" id="b_notify_error">
    <mca-text>Error Message</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="error"
  id="b_notify_error"
  head={<Type weight="medium" size="md">Its an Error</Type>}
  media={<Icon icon="error" size="sm" ariaHidden />}
>
  <Type>Error Message</Type>
</Alert>
```

### Title Only (No Body Content)

When `<mca-notify>` has no children, render the Alert with just `head` and no children.

**MCA1 (Before)**:
```html
<mca-notify message-context="error" message-title="Its an Error Title Only"
    id="b_notify_error_title" role="alert">
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="error"
  id="b_notify_error_title"
  head={<Type weight="medium" size="md">Its an Error Title Only</Type>}
  media={<Icon icon="error" size="sm" ariaHidden />}
  role="alert"
/>
```

### Success / Done

Both `message-context="success"` and `message-context="done"` map to `variant="success"`.

**MCA1 (Before)**:
```html
<mca-notify message-context="success" message-title="Its a Success" id="b_notify_success">
    <mca-text>Success Message</mca-text>
</mca-notify>

<mca-notify message-context="done" message-title="Its Done!" id="b_notify_done">
    <mca-text>Done Message</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="success"
  id="b_notify_success"
  head={<Type weight="medium" size="md">Its a Success</Type>}
  media={<Icon icon="success-fill" size="sm" ariaHidden />}
>
  <Type>Success Message</Type>
</Alert>

<Alert
  variant="success"
  id="b_notify_done"
  head={<Type weight="medium" size="md">Its Done!</Type>}
  media={<Icon icon="success-fill" size="sm" ariaHidden />}
>
  <Type>Done Message</Type>
</Alert>
```

### Warn / Fail

`message-context="warn"` maps to `variant="warning"`. `message-context="fail"` maps to `variant="error"`.

**MCA1 (Before)**:
```html
<mca-notify message-context="warn" message-title="Its a warning" id="b_notify_warn">
    <mca-text>Warning Message</mca-text>
</mca-notify>

<mca-notify message-context="fail" message-title="Its failed!" id="b_notify_fail">
    <mca-text>Failed Message</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="warning"
  id="b_notify_warn"
  head={<Type weight="medium" size="md">Its a warning</Type>}
  media={<Icon icon="warning" size="sm" ariaHidden />}
>
  <Type>Warning Message</Type>
</Alert>

<Alert
  variant="error"
  id="b_notify_fail"
  head={<Type weight="medium" size="md">Its failed!</Type>}
  media={<Icon icon="error" size="sm" ariaHidden />}
>
  <Type>Failed Message</Type>
</Alert>
```

### Mandatory (Nested Notification)

MCA1's `message-context="mandatory"` is used for content that must be read aloud. It can also nest other `<mca-notify>` elements. Map to `variant="warning"` and render nested alerts as separate `<Alert>` children.

**MCA1 (Before)**:
```html
<mca-notify message-context="mandatory" message-title="Mandatory Text" id="b_notify_mandatory">
    <mca-text>Mandatory Text - Please read out to the customer</mca-text>
    <mca-text>
        <mca-notify message-title="Hey, its an info." id="b_notify_mandatory_info">
            <mca-text>Info Message</mca-text>
        </mca-notify>
    </mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="warning"
  id="b_notify_mandatory"
  head={<Type weight="medium" size="md">Mandatory Text</Type>}
  media={<Icon icon="warning" size="sm" ariaHidden />}
>
  <Type marginBottom>Mandatory Text - Please read out to the customer</Type>

  {/* Nested notification rendered as a child Alert */}
  <Alert
    variant="info"
    id="b_notify_mandatory_info"
    head={<Type weight="medium" size="md">Hey, its an info.</Type>}
    media={<Icon icon="info-fill" size="sm" ariaHidden />}
  >
    <Type>Info Message</Type>
  </Alert>
</Alert>
```

### No Title (Body Only)

When `message-title` is omitted, render the Alert without a `head` prop.

**MCA1 (Before)**:
```html
<mca-notify message-context="error" id="b_notify_error_no_message-title">
    <mca-text>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="error"
  id="b_notify_error_no_message-title"
  media={<Icon icon="error" size="sm" ariaHidden />}
>
  <Type>Lorem ipsum dolor sit amet, consectetur adipiscing elit...</Type>
</Alert>
```

### Notification with Embedded Button

MCA1 notifications can contain buttons. Render the button inside the Alert children.

**MCA1 (Before)**:
```html
<mca-notify message-context="success" message-title="Please Print" id="b_notify_success_button">
    <mca-text>A printout is required before confirming the payment.</mca-text>
    <mca-text>
        <mca-button type="secondary" size="lg" icon="download">  Print </mca-button>
    </mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="success"
  id="b_notify_success_button"
  head={<Type weight="medium" size="md">Please Print</Type>}
  media={<Icon icon="success-fill" size="sm" ariaHidden />}
>
  <Type marginBottom>A printout is required before confirming the payment.</Type>
  <Button
    variant="secondary"
    media={<Icon icon="download" size="sm" />}
    onClick={handlePrint}
  >
    Print
  </Button>
</Alert>
```

### Highlight

MCA1's `highlight` attribute adds a visual emphasis marker. Blueprint-React `<Alert>` does not have a highlight prop. Render the highlight text as bold content within the alert body.

**MCA1 (Before)**:
```html
<mca-notify message-context="success" message-title="Please Highlight Me"
    highlight="Highlight" id="b_notify_success_highlight">
    <mca-text>A printout is required before confirming the payment.</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="success"
  id="b_notify_success_highlight"
  head={<Type weight="medium" size="md">Please Highlight Me</Type>}
  media={<Icon icon="success-fill" size="sm" ariaHidden />}
>
  <Type weight="bold" marginBottom>Highlight</Type>
  <Type>A printout is required before confirming the payment.</Type>
</Alert>
```

### Fullscreen Notifications

MCA1's `fullscreen` attribute (`"mobile"`, `"desktop"`, `"standard"`) renders the notification as a full-page takeover. Blueprint-React `<Alert>` does not have a fullscreen mode. Migrate these to a full-page layout using `<Page>` with a centered `<Alert>`, or a `<Dialog>` if the notification should overlay content.

**MCA1 (Before)**:
```html
<mca-notify message-context="success" message-title="Fullscreen Mobile Title"
    fullscreen="mobile" id="b_notify_success_fullscreen-mobile"
    fullscreen-align="top" aria-level="1">
    <mca-text>This is a full screen notification on Mobile.</mca-text>
</mca-notify>

<mca-notify message-context="success" message-title="Fullscreen Desktop Title"
    fullscreen="desktop" id="b_notify_success_fullscreen-desktop">
    <mca-text>This is a full screen notification on desktop.</mca-text>
</mca-notify>

<mca-notify message-context="success" message-title="Fullscreen Standard Title"
    fullscreen="standard" id="b_notify_success_fullscreen-standard">
    <mca-text>This is a full screen notification across all devices.</mca-text>
</mca-notify>

<mca-notify message-context="server-error" message-title="Fullscreen Standard Title"
    fullscreen="mobile" id="b_notify_success_fullscreen-server-error">
    <mca-text>This is a full screen notification across all devices.</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
// Approach: Render as a page-level Alert centered on screen.
// For a true fullscreen takeover, wrap in a Page or Dialog component.

// Mobile fullscreen (use Dialog for overlay behavior)
<Dialog
  isOpen={showFullscreenMobile}
  head={<Type element="h2">Fullscreen Mobile Title</Type>}
  onClickDismiss={() => setShowFullscreenMobile(false)}
  onKeydownEscape={() => setShowFullscreenMobile(false)}
>
  <Alert
    variant="success"
    id="b_notify_success_fullscreen-mobile"
    head={<Type weight="medium" size="md">Fullscreen Mobile Title</Type>}
    media={<Icon icon="success-fill" size="sm" ariaHidden />}
    role="heading"
    aria-level={1}
  >
    <Type>This is a full screen notification on Mobile.</Type>
  </Alert>
</Dialog>

// Desktop / Standard fullscreen — same Dialog pattern
<Dialog
  isOpen={showFullscreenDesktop}
  head={<Type element="h2">Fullscreen Desktop Title</Type>}
  onClickDismiss={() => setShowFullscreenDesktop(false)}
  onKeydownEscape={() => setShowFullscreenDesktop(false)}
>
  <Alert
    variant="success"
    id="b_notify_success_fullscreen-desktop"
    media={<Icon icon="success-fill" size="sm" ariaHidden />}
  >
    <Type>This is a full screen notification on desktop.</Type>
  </Alert>
</Dialog>

// Server error fullscreen
<Dialog
  isOpen={showServerError}
  head={<Type element="h2">Fullscreen Standard Title</Type>}
  onClickDismiss={() => setShowServerError(false)}
  onKeydownEscape={() => setShowServerError(false)}
>
  <Alert
    variant="error"
    id="b_notify_success_fullscreen-server-error"
    media={<Icon icon="error" size="sm" ariaHidden />}
  >
    <Type>This is a full screen notification across all devices.</Type>
  </Alert>
</Dialog>
```

**Alternative**: If a Dialog overlay is too heavy, render the Alert inline within a `<Section>` that takes up the full page content area. The choice depends on whether the notification blocks interaction (Dialog) or just fills the view (inline).

### Custom Image (icon-src)

MCA1's `icon-src` attribute renders a custom image instead of an icon. Use the `media` prop on `<Alert>` with an `<img>` tag instead of `<Icon>`.

**MCA1 (Before)**:
```html
<mca-notify message-context="info" message-title="Fullscreen Standard Title With Custom Image"
    fullscreen="mobile" id="b_notify_fullscreen-custom-image"
    icon-src="documentation/manual/notify/logo.png">
    <mca-text>icon-src attribute example</mca-text>
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="info"
  id="b_notify_fullscreen-custom-image"
  head={<Type weight="medium" size="md">Fullscreen Standard Title With Custom Image</Type>}
  media={<img src="documentation/manual/notify/logo.png" alt="" style={{ width: 24, height: 24 }} />}
>
  <Type>icon-src attribute example</Type>
</Alert>
```

### Accessibility Text

MCA1's `accessibility-text` attribute provides custom screen reader text. Map to `aria-label` on the `<Alert>`.

**MCA1 (Before)**:
```html
<mca-notify message-context="info" id="b_notify_accessibility_text"
    accessibility-text="User defined custom accessibility text"
    message-title="User defined custom accessibility text">
</mca-notify>
```

**Blueprint-React (After)**:
```typescript
<Alert
  variant="info"
  id="b_notify_accessibility_text"
  head={<Type weight="medium" size="md">User defined custom accessibility text</Type>}
  media={<Icon icon="info-fill" size="sm" ariaHidden />}
  aria-label="User defined custom accessibility text"
/>
```

### Complete `<mca-notify>` Attribute Mapping

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `id` | `id` | `Alert` | |
| `message-title` | `head` | `Alert` | Omit prop when no title |
| `message-context` | `variant` | `Alert` | See context-to-variant table above |
| Children (`<mca-text>`) | `children` | `Alert` | Wrap in `<Type>` |
| `role` | `role` | `Alert` | Pass through (e.g. `role="alert"`) |
| `aria-level` | `aria-level` | `Alert` | Pass through |
| `accessibility-text` | `aria-label` | `Alert` | Custom screen reader text |
| `highlight` | `<Type weight="bold">` child | Inside `Alert` children | No built-in prop; render as bold text |
| `icon-src` | `media={<img src={...} />}` | `Alert` | Custom image instead of Icon |
| N/A | `media={<Icon ... />}` | `Alert` | Standard icon per variant |
| N/A | `onDismiss` | `Alert` | Dismissible handler (not `onClose`) |
| `fullscreen` | `<Dialog>` wrapping `<Alert>` | Parent component | No built-in fullscreen; use Dialog overlay or full-page layout |
| `fullscreen-align` | Dialog/layout positioning | Parent component | Control via Dialog or CSS |

**Valid Alert variants**: `info`, `success`, `warning`, `error`
