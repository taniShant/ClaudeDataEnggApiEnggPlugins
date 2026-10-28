# BDL Modal and Dialog to Blueprint-React Mapping

**Last Updated**: April 28, 2026

---

## Modal and Dialog

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-modal>` | `<Modal>` (ref-based with useRef hook) |
| `<mca-modal-body>` | `children` of `<Modal>` |
| `<mca-modal-footer>` | `children` of `<Modal>` (typically a `<ButtonGroup>`) |

**Critical**: Blueprint-React uses **ref-based API** with `useRef()` and `useCallback()`. The Modal is opened/closed via ref methods, not state properties.

### Comprehensive Modal Example

**MCA1 (Before)**:
```html
<mca-modal
  title=""
  aria-label=""
  type="window"
  id=""
  class=""
  footer-style="aligned"
  parent-container="body"
  sliding-animation="standard"
  white-bg="no"
  cancel-btn="yes"
  navigation-button=""
>
</mca-modal>
```

**Blueprint-React (After)**:
```typescript
const modalRef = useRef<ModalRef>();

const doOpenModal = useCallback(() => {
  modalRef.current.open();
}, []);

const doCloseModal = useCallback(() => {
  modalRef.current.close();
}, []);

<>
  <ButtonGroup>
    <Button onClick={doOpenModal} variant="primary">
      Open Modal
    </Button>
  </ButtonGroup>

  <Modal ref={modalRef} onClose={doCloseModal}>
    <Type marginBottom>
      You can close me by clicking the backdrop, pressing 'escape', by clicking the
      close button, or by interacting with content.
    </Type>

    <ButtonGroup justify="center">
      <Button onClick={doCloseModal} variant="primary" fullWidth="sm-down">
        Close
      </Button>
      <Button fullWidth="sm-down">Secondary</Button>
    </ButtonGroup>
  </Modal>
</>
```

### Simple Dialog Modal (Alternative Pattern)

If you need a simpler pattern without ref management, you can also use `<Dialog>` with slot properties:

**Blueprint-React (Dialog Alternative)**:
```typescript
const [open, setOpen] = useState(false);

<>
  <Button variant="primary" onClick={() => setOpen(true)}>Open Dialog</Button>
  <Dialog
    open={open}
    onClose={() => setOpen(false)}
    head={<Type size="md" weight="medium">Title goes here (optional)</Type>}
    foot={<Link href="https://www.barclays.com" media={<Icon icon="chevron-right" size="sm"/>} mediaPosition="right" noDecoration variant="secondary">More Information</Link>}
  >
    <Type>
      Your modal content here
    </Type>
  </Dialog>
</>
```

### Original Simple Modal Example

**MCA1 (Before)**:
```html
<mca-modal id="confirmCloseAppDialog" title="Close Dialog">
    <mca-modal-body>
        <p>Are you sure you want to Close the Application?</p>
    </mca-modal-body>
    <mca-modal-footer>
        <mca-button type="secondary" size="medium" modal-dismiss="yes">Cancel</mca-button>
        <mca-button type="primary" size="medium" id="confirmCloseAppButton">Confirm</mca-button>
    </mca-modal-footer>
</mca-modal>
```

**Blueprint-React (After)**:
```typescript
<Dialog
  isOpen={isConfirmDialogOpen}
  head={<Type element="h2">Close Dialog</Type>}
  foot={
    <Arrange gap="fixed" justify="end">
      <ArrangeItem size="fit">
        <Button variant="secondary" onClick={handleCancel}>Cancel</Button>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button variant="primary" id="confirmCloseAppButton" onClick={handleConfirm}>
          Confirm
        </Button>
      </ArrangeItem>
    </Arrange>
  }
  onClickDismiss={handleCancel}
  onClickOverlay={handleCancel}
  onKeydownEscape={handleCancel}
>
  <Type element="p">Are you sure you want to Close the Application?</Type>
</Dialog>
```

**Attribute Mapping**:
| MCA1 Attribute | Blueprint-React Prop | Notes |
|---|---|---|
| `title` | `head` | Pass as `ReactNode` |
| `<mca-modal-body>` children | `children` | Direct children of Dialog |
| `<mca-modal-footer>` children | `foot` | Pass as `ReactNode` |
| `modal-dismiss="yes"` | `onClickDismiss` | Event handler on Dialog |
| N/A | `isOpen` | Controlled visibility via state |
| N/A | `onClickOverlay` | Backdrop click handler |
| N/A | `onKeydownEscape` | Escape key handler |

### Dialog with Form Content

When the Dialog body contains form fields, use `FormItem` with its `render` prop pattern inside the Dialog `children`:

```typescript
<Dialog
  isOpen={isFormDialogOpen}
  head={<Type element="h2">Add New Record</Type>}
  foot={
    <Arrange gap="fixed" justify="end">
      <ArrangeItem size="fit">
        <Button variant="secondary" onClick={handleCancel}>Cancel</Button>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button variant="primary" onClick={handleSubmit}>Submit</Button>
      </ArrangeItem>
    </Arrange>
  }
  onClickDismiss={handleCancel}
  onClickOverlay={handleCancel}
  onKeydownEscape={handleCancel}
>
  <FormItem
    label={<Type>Record Name</Type>}
    error={errors.name && <Type color="error">{errors.name}</Type>}
    render={(props) => (
      <FormInput {...props} value={name} onChange={(e) => setName(e.target.value)} />
    )}
  />
</Dialog>
```

---

## Modal Component (Alternative to Dialog)

| MCA1 BDL | Blueprint-React |
|---|---|
| `<mca-modal>` (complex) | `<Modal>` with ref-based API |

For complex modals requiring positioning, sizing, drawer mode, or programmatic open/close, use the `<Modal>` component instead of `<Dialog>`.

### When to Use Modal vs Dialog

| Use Case | Component | Reason |
|---|---|---|
| Simple confirmation/alert | `<Dialog>` | Simpler API with slot props (head/foot/children) |
| Complex content with form | `<Modal>` | Better control over width, height, positioning |
| Full-screen takeover | `<Modal>` | `fullScreen` prop available |
| Drawer/slide-in panel | `<Modal>` | `drawer` prop with positioning |
| Programmatic open/close | `<Modal>` | Ref-based API (open/close methods) |
| Simple overlay with dismiss | `<Dialog>` | `onClickDismiss`/`onClickOverlay`/`onKeydownEscape` |

### Modal Before/After Example

**MCA1 (Before)**:
```html
<mca-modal id="editModal" title="Edit Record" type="window" footer-style="aligned">
    <mca-modal-body>
        <mca-form id="editForm">
            <mca-input id="fieldName" label="Name" value="{{vm.name}}"></mca-input>
        </mca-form>
    </mca-modal-body>
    <mca-modal-footer>
        <mca-button type="secondary" modal-dismiss="yes">Cancel</mca-button>
        <mca-button type="primary" id="saveButton">Save</mca-button>
    </mca-modal-footer>
</mca-modal>
```

**Blueprint-React (After)**:
```typescript
import { Modal, ModalRef } from '@barclays/blueprint-react';

const modalRef = useRef<ModalRef>(null);

const openModal = () => modalRef.current?.open();
const closeModal = () => modalRef.current?.close();

<Modal
  ref={modalRef}
  title={<Type element="h2">Edit Record</Type>}
  footer={
    <Arrange gap="fixed" justify="end">
      <ArrangeItem size="fit">
        <Button variant="secondary" onClick={closeModal}>Cancel</Button>
      </ArrangeItem>
      <ArrangeItem size="fit">
        <Button variant="primary" id="saveButton" onClick={handleSave}>Save</Button>
      </ArrangeItem>
    </Arrange>
  }
  onClose={closeModal}
  modalWidth="fixed"
>
  <Form id="editForm">
    <FormItem
      label={<Type>Name</Type>}
      render={(props) => (
        <FormInput {...props} id="fieldName" value={name} onChange={(e) => setName(e.target.value)} />
      )}
    />
  </Form>
</Modal>
```

### Modal Props Reference

```typescript
interface ModalContentProps {
  children: ReactNode;             // Required: modal body content
  title: ReactElement;             // Required: modal title
  footer?: ReactElement;           // Optional: footer content
  showTitle?: boolean;             // Default: true — show/hide title visually
  position?: "default" | "bottom" | "top";  // Default: "default"
  fullScreen?: boolean;            // Default: false
  modalWidth?: "content" | "fixed"; // Default: "content"
  modalHeight?: "content" | "expanded" | "full"; // Default: "content"
  media?: ReactElement;            // Optional: image/media slot
  drawer?: boolean;                // Default: false — drawer mode
  fullWidth?: boolean;             // Default: false
  positionRightMdUp?: boolean;     // Default: false
  transparency?: "dark" | "light"; // Overlay transparency
  onClose?: () => void;            // Close callback
  role?: "dialog" | "alertdialog"; // Default: "dialog"
}

interface ModalRef {
  open: () => void;
  close: () => void;
}
```

### Modal Attribute Mapping (`<mca-modal>` to `<Modal>`)

| MCA1 Attribute | Blueprint-React Prop | Location | Notes |
|---|---|---|---|
| `title` | `title` | `Modal` | Pass as ReactElement |
| `<mca-modal-body>` children | `children` | `Modal` | Direct children |
| `<mca-modal-footer>` children | `footer` | `Modal` | Pass as ReactElement |
| `type="window"` | `modalWidth="fixed"` | `Modal` | Window-style modal |
| `footer-style="aligned"` | `<Arrange justify="end">` in footer | `Modal` footer | Right-align buttons |
| N/A | `ref` | `Modal` | `useRef<ModalRef>()` for open/close |
| N/A | `onClose` | `Modal` | Required close callback |
| N/A | `position` | `Modal` | "default" / "bottom" / "top" |
| N/A | `fullScreen` | `Modal` | Full-screen at smaller viewports |
| N/A | `drawer` | `Modal` | Drawer mode |
| N/A | `transparency` | `Modal` | "dark" / "light" overlay |
