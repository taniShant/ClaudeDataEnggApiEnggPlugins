# MCA1 Application Patterns — Real-World Reference

**Version**: 1.0
**Last Updated**: July 7, 2026
**Source**: Analysis of 8 production MCA1 applications

---

## Overview

This document captures the actual patterns used in production MCA1 applications, derived from analysis of:
- `scp-ui-case-creation` — BPM case management, suspect match investigation
- `scp-ui-custadmin` — Customer admin, KYC, corporate banking pots, document management
- `scp-ui-letters` — Customer letters, batch printing, CMOD document retrieval
- `scp-ui-maintain-roles` — Role/service management CRUD
- `scp-ui-membershipandalerts` — Banking memberships, SMS alert configuration
- `scp-ui-sales-contact` — Sales contact management
- `scp-ui-securities` — Securities charge creation, portfolio management
- `scp-ui-stafftools` — Authorisation queues, scrubbing, locked requests

Understanding these patterns is essential for accurate automated migration to MCA2 React.

---

## 1. Project Structure

All MCA1 apps follow an identical structure:

```
scp-ui-<name>/
├── build.gradle                    # Gradle build (mca-ui plugin)
├── envConf/scp-config.properties   # Backend endpoint routing
├── Feature/                        # BDD/Cucumber tests
├── Fixture/                        # Test data (Excel)
├── src/main/webapp/
│   ├── WEB-INF/web.xml
│   └── scp/<contextroot>/
│       └── <module>/
│           ├── controllers/        # JMVC controllers (1 file per screen)
│           ├── models/             # Validation models (models.js)
│           ├── views/              # EJS templates (.ejs)
│           ├── constants/          # Static constants (constants.js)
│           └── helpers/            # Optional utility classes
```

**Key observations:**
- No `package.json` with npm dependencies — framework comes from shared Gradle artifacts
- Dependencies: `scp-libs-uifoundation` (framework), `javascriptmvc:bi3.2.2` (JMVC), `scp-container-cgs` (container)
- Build minimization lists each controller entry point in `build.gradle`
- Context root defined in `build.gradle` as `appContext`

---

## 2. Module Loading — steal()

Every MCA1 file uses `steal()` for dependency management (StealJS from JavaScriptMVC):

```javascript
steal({src: "scp/ui/common/bundles/core", packaged: false, ignore: false})
    .then("scp/ui/common/vendor/datatable/scp-datatable.js")
    .then("scp/ui/common/vendor/chosen/chosen.js")
    .then("scp/<app>/<module>/models/models.js")
    .then("scp/<app>/<module>/constants/constants.js")
    .then(function($) {
        // Controller definition goes here
    });
```

**steal() rules:**
- First entry is always the core bundle with `{src: ..., packaged: false, ignore: false}`
- Each `.then()` loads a dependency sequentially
- Final `.then(function($) {...})` receives jQuery and defines the controller
- Dependencies are loaded by path relative to webapp root
- No ES modules, no CommonJS, no AMD — this is a proprietary loader

**Migration:** Replace entire `steal()` chain with ES `import` statements.

---

## 3. Controller Architecture

### 3.1 BaseController Declaration

Controllers use a class-factory pattern with dot-separated namespace strings:

```javascript
scp.ui.common.controllers.BaseController(
    "scp.<app>.<module>.controllers.<name>",  // Fully-qualified class name
    {                                          // Static properties (optional)
        webComponents: { bundles: ['bdl', 'bdl-modal'] }
    },
    {                                          // Instance methods
        init: function() {
            this._super.apply(this, arguments);
            this.element.html(this.options.template, {});
            // initialization...
        }
    }
);
```

### 3.2 Controller Inheritance

Apps define intermediate base controllers that extend the framework:

```javascript
// App-level base controller
scp.ui.common.controllers.BaseController(
    "scp.securities.createsecurities.controllers.base",
    { webComponents: { bundles: ['bdl'] } },
    { /* shared methods */ }
);

// Feature controller extends app base
scp.securities.createsecurities.controllers.base(
    "scp.securities.createsecurities.controllers.homepage",
    { /* instance methods */ }
);
```

### 3.3 Controller Types

| Type | Base Class | Use Case |
|------|-----------|----------|
| Page controller | `scp.ui.common.controllers.BaseController` | Full-page workflows |
| Lightbox controller | `scp.ui.common.controllers.LightBox` | Modal/overlay flows |
| Preload controller | `scp.ui.common.controllers.ProgressBarController` | Loading screens with `updateView()` |
| Helper class | `$.Class.extend(name, static, instance)` | Utility/constant classes |

### 3.4 Complete BaseController API Surface

Every controller has access to these methods/properties:

| Method/Property | Purpose | React Equivalent |
|----------------|---------|------------------|
| `this._super.apply(this, arguments)` | Call parent constructor | N/A (no class hierarchy) |
| `this.element` | jQuery ref to controller's DOM root | `useRef()` or component root |
| `this.find(selector)` | Scoped jQuery query | `useRef()` + DOM query |
| `this.options` | Config passed at construction | Component props |
| `this.options.template` | EJS template path | JSX return value |
| `this.hub` | Sibling controller event bus | React Context or Redux |
| `this.workflow` | Cross-step state container | Redux store / route state |
| `this.proxy(fn)` | Bind `this` context | Arrow functions (automatic) |
| `this.disable()` | Block UI (show loading) | `setLoading(true)` state |
| `this.enable()` | Unblock UI | `setLoading(false)` state |
| `this.loaded()` | Signal view ready | `useEffect` cleanup / flag |
| `this.autofocus()` | Focus first input | `autoFocus` prop or `useRef` |
| `this.invalidate()` | Clear validation errors | `formik.resetForm()` / clear state |
| `this.validate(model)` | Run model validation | Yup `schema.validate()` |
| `this.error(msg)` | Show error message | `setError(msg)` + `<Alert>` |
| `this.info(msg)` | Show info message | `setInfo(msg)` + `<Alert>` |
| `this.messages([])` | Show message list | Alert array state |
| `this.resume(step, opts)` | Navigate to workflow step | `navigate('/step')` |
| `this.callService(name, endpoint, payload)` | API call (returns Deferred) | `fetch()` / RTK Query |
| `this.handleServiceResponse` | Framework error handler | Error boundary / try-catch |
| `this.element.html(path, data)` | Render EJS template | JSX conditional rendering |
| `this.element.formParams()` | Serialize form inputs | `getValues()` (React Hook Form) |
| `this.containerEvent(data)` | Communicate with MCA container | Container context / events |

---

## 4. Event Handling

### 4.1 DOM Event Delegation

Controllers bind events using string-based CSS selectors as property keys:

```javascript
{
    '#button-next click': function() { /* handler */ },
    '#businessUnit change': function(el, ev) { /* handler */ },
    'input[name="contactName"] change': function() { /* handler */ },
    '.scp-close-link click': function() { /* handler */ },
    'table tr td click': function(el) { /* handler */ },
    "[id^='accordItem'] click": function(el, ev) { /* handler */ },
    "#searchResult tbody tr click": function(el) { /* row click */ }
}
```

**Pattern:** `'<CSS selector> <event>': function(el, ev) { }`
- `el` = the matched jQuery element
- `ev` = the event object
- Handler auto-bound to controller instance

**Migration:** Convert to React event handlers:
```jsx
// MCA1: '#button-next click': function() { this.handleNext(); }
// React: <Button onClick={handleNext}>Next</Button>
```

### 4.2 Workflow Events (Cross-Controller Communication)

```javascript
{
    '{workflow} PRELOADED': function(jq, ev, data) { /* handle */ },
    '{workflow} CONFIRM_SUCCESS': function() { /* handle */ },
    '{workflow} RELOAD_DATA': function() { /* handle */ },
    '{hub} BACK': function() { /* handle */ },
    '{hub} ENTER': function() { /* handle */ }
}
```

**Pattern:** `'{scope} EVENT_NAME': function(jq, ev, data) { }`
- `{workflow}` = events that persist across workflow steps
- `{hub}` = events between sibling controllers on the same step

**Triggering events:**
```javascript
this.workflow.trigger('CONFIRM_SUCCESS');
this.workflow.trigger('RELOAD_DATA', { key: 'value' });
this.hub.trigger('ERRORS_CHANGED');
```

**Migration:** Convert to Redux actions/dispatches or React context:
```typescript
// MCA1: this.workflow.trigger('CONFIRM_SUCCESS');
// React: dispatch(confirmSuccess());
```

---

## 5. State Management

### 5.1 workflow.model() — Global State

The primary state management mechanism across all 8 apps:

```javascript
// Set state
this.workflow.model("INIT_DATA", data);
this.workflow.model("CUSTOMER_DETAILS", customerObj);
this.workflow.model("SELECTED_ITEMS", selectedArray);
this.workflow.model("EDIT_MODE", true);

// Get state
var initData = this.workflow.model("INIT_DATA");
var customer = this.workflow.model("CUSTOMER_DETAILS");
```

**Characteristics:**
- Flat key-value store (stringly-typed keys, SCREAMING_SNAKE_CASE convention)
- Values can be primitives, objects, or arrays
- Persists across workflow steps (page transitions)
- Shared by all controllers in the workflow
- Common keys: `INIT_DATA`, `PRELOAD_DATA`, `CUSTOMER_DETAILS`, `SELECTED_*`, `*_FLAG`

**Migration:** Map to Redux slices or Zustand stores with typed state:
```typescript
// MCA1: this.workflow.model("CUSTOMER_DETAILS", data);
// React: dispatch(setCustomerDetails(data));
// or:    useAppStore.getState().setCustomerDetails(data);
```

### 5.2 hub.model() — Step-Local State

For state shared only between sibling controllers on the same page:

```javascript
this.hub.model("STATIC_CONTENT", content);
var staticContent = this.hub.model("STATIC_CONTENT");
```

**Migration:** React Context or component-level shared state (useState lifted to parent).

### 5.3 Controller Instance State

Local state stored as `this.propertyName`:

```javascript
init: function() {
    this.empDetails = [];
    this.currentPage = 1;
    this.isEditMode = false;
    this.preloadData = {};
}
```

**Migration:** `useState()` or `useReducer()` hooks:
```typescript
const [empDetails, setEmpDetails] = useState<Employee[]>([]);
const [currentPage, setCurrentPage] = useState(1);
```

---

## 6. API Calls

### 6.1 callService Pattern

All 8 apps use the same pattern:

```javascript
this.callService("logicalName", "serviceEndpoint", requestPayload)
    .done(this.proxy(this.onSuccess))
    .fail(this.proxy(this.onError))
    .always(this.proxy(this.handleServiceResponse), this.proxy(this.enable));
```

**Method signature:** `callService(displayName, endpointKey, payload) → jQuery.Deferred`
- `displayName`: Human-readable name for logging/events
- `endpointKey`: Maps to a backend REST endpoint via container config
- `payload`: Request body object (will be JSON-serialized)

**Common patterns:**
```javascript
// Simple GET-style (no payload)
this.callService("init", "preload")
    .done(this.proxy(this.loadPreloadData))
    .always(this.proxy(this.handleServiceResponse));

// POST with request object
this.callService("save", "save-contacts", { contacts: this.contactList })
    .done(this.proxy(this.onSaveSuccess))
    .fail(this.proxy(this.onSaveFail))
    .always(this.proxy(this.handleServiceResponse), this.proxy(this.enable));

// Chained with disable/enable for loading state
'#button-next click': function() {
    this.disable();
    this.callService("submit", "create-record", this.buildRequest())
        .done(this.proxy(this.onSubmitSuccess))
        .always(this.proxy(this.handleServiceResponse), this.proxy(this.enable));
}
```

**Migration:** Convert to async/await with RTK Query or custom hooks:
```typescript
// MCA1:
// this.disable();
// this.callService("save", "save-contacts", payload)
//     .done(this.proxy(this.onSuccess))
//     .always(this.proxy(this.handleServiceResponse), this.proxy(this.enable));

// React:
const [saveContacts, { isLoading }] = useSaveContactsMutation();
const handleSave = async () => {
  try {
    const result = await saveContacts(payload).unwrap();
    onSuccess(result);
  } catch (error) {
    handleError(error);
  }
};
```

### 6.2 Service Endpoint Configuration

Endpoints are defined in `envConf/scp-config.properties`:
```properties
MALCSP_startPointPath=epssecurities/process/createsecurities
MAPDAH_endPoint=http://eps-host:8080/eps/
```

The container framework maps the `callService` endpoint key to these configured URLs.

---

## 7. Navigation & Routing

### 7.1 resume() Pattern

All navigation uses `this.resume(stepName, options)`:

```javascript
this.resume("next");                          // Forward
this.resume("back");                          // Backward
this.resume("confirm");                       // Named step
this.resume("create-membership", options);    // With options
this.resume("back-home", { type: "takeover" }); // Full-page replace
```

**Options:**
- `{ type: 'takeover' }` — Full page replacement
- `{ type: 'lightbox' }` — Open as modal overlay
- `{ data: {...} }` — Pass data to next step
- `{ parentController: this }` — Reference to parent for callbacks

**Migration:** Convert to React Router `navigate()`:
```typescript
// MCA1: this.resume("confirm");
// React: navigate('/confirm');

// MCA1: this.resume("back");
// React: navigate(-1);
```

### 7.2 WindowManager

Container-level window operations:

```javascript
scp.ui.container.WindowManager.launchWindow({
    type: 'lightbox',
    hub: new scp.ui.common.Hub(),
    workflow: this.workflow,
    processId: processId
});
scp.ui.container.WindowManager.closeWindow();
scp.ui.container.WindowManager.closeLightBox();
scp.ui.container.WindowManager.cancelApp(options);
scp.ui.container.WindowManager.closeApp();
```

**Migration:**
- `launchWindow({type:'lightbox'})` → Open a `<Dialog>` component
- `closeWindow()` / `closeApp()` → `navigate('/')` or container API call
- `closeLightBox()` → `dialogRef.current.close()` / `setDialogOpen(false)`

---

## 8. Form Patterns

### 8.1 Form Data Collection

```javascript
// Serialize all named form inputs
var params = this.element.formParams();

// BDL component values (not captured by formParams)
var sortCode = this.find('#sortCode').getComponent().getValue();
var selectedOption = this.find('#dropdown').getComponent().val()[0];
var isChecked = this.find('#checkbox').getComponent().getCheckedStatus();
```

**Important:** `.formParams()` only captures standard HTML inputs. BDL `<mca-*>` component values must be read individually via `.getComponent()`.

**Migration:** React controlled components eliminate this split:
```typescript
// All form state in one place via React Hook Form or Formik
const { register, handleSubmit, getValues } = useForm<FormValues>();
```

### 8.2 Validation Model Pattern

Validation is model-based using `scp.ui.common.Model`:

```javascript
scp.ui.common.Model("scp.<app>.<module>.models.<ModelName>", {
    init: function() {
        // Simple presence check
        this.validatePresenceOf("fieldName", { message: "Required" });

        // Date format validation
        this.validateDate("dateField", "dd/mm/yy");

        // Custom validator (return string = error, return nothing = valid)
        this.validate("fieldName", {}, function() {
            if (this.fieldName === "") return "Field is required";
            if (!/^[A-Z0-9]+$/i.test(this.fieldName)) return "Invalid format";
        });

        // Conditional validation (only if visible)
        this.validate("optionalField", {}, function() {
            if ($("#optionalField").is(":visible")) {
                if (!this.optionalField) return "Required when shown";
            }
        });
    }
}, {});
```

**Usage in controller:**
```javascript
this.invalidate();  // Clear previous errors
var model = new Models.ValidationModel(this.element.formParams());
if (this.validate(model)) {
    // Valid — proceed
    this.callService(...);
} else {
    // Invalid — errors auto-displayed by ErrorListController
    this.enable();
}
```

**Migration:** Convert to Yup schemas:
```typescript
// MCA1 model.validate("sortCode", {}, function() { if (!this.sortCode) return "Required"; })
// React:
const schema = Yup.object({
  sortCode: Yup.string().required("Sort code is required"),
  accountNumber: Yup.string().matches(/^\d{8}$/, "Must be 8 digits"),
});
```

### 8.3 Inline Validation

Some apps use real-time field validation:

```javascript
// InlineValidator from framework
this.inlineValidator = new scp.ui.common.validation.InlineValidator(this.element, options);
options.model = Models.ValidateInline;
this.inlineValidator.setCustomParams(customParams);
```

**Migration:** Formik/RHF `mode: 'onChange'` or `mode: 'onBlur'`.

### 8.4 Error Display Controllers

Every controller instantiates error display helpers in `init()`:

```javascript
new scp.ui.common.validation.ErrorListController(this.element, options);
new scp.ui.common.messages.MessageListController(this.find('#messages'), options);
```

These auto-render error summaries when `this.validate()` fails. 

**Migration:** Blueprint `<Alert>` component + form-level error state.

---

## 9. Template Rendering

### 9.1 EJS Template Syntax

```ejs
<%-- Output (escaped) --%>
<span><%= data.customerName %></span>

<%-- Output (unescaped/raw HTML — rare, dangerous) --%>
<div><%== data.htmlContent %></div>

<%-- Logic --%>
<% if (this.isEditMode) { %>
    <mca-button type="primary">Save</mca-button>
<% } else { %>
    <mca-button type="secondary">Edit</mca-button>
<% } %>

<%-- Loops --%>
<% for (var i = 0; i < this.items.length; i++) { %>
    <mca-table-row>
        <mca-table-cell><%= this.items[i].name %></mca-table-cell>
    </mca-table-row>
<% } %>
```

### 9.2 Dynamic Template Injection

Controllers render sub-views into DOM regions at runtime:

```javascript
// Render template into element (path starts with //)
this.element.html(this.options.template, {});
this.element.find("#results-area").html("//scp/<app>/<module>/views/results.ejs", { data: results });
this.find("#dropdown-area").html(this.constants.dropdownEjs, { options: list });
```

**Migration:** Convert to conditional JSX rendering:
```tsx
// MCA1: this.element.find("#results").html("//views/results.ejs", { data });
// React:
{results && <ResultsTable data={results} />}
```

---

## 10. BDL Component API (.getComponent())

BDL web components expose a JavaScript API accessed via `.getComponent()`:

```javascript
// Get values
this.find('#inputField').getComponent().getValue();     // text inputs
this.find('#inputField').getComponent().val();          // alternate getter
this.find('#dropdown').getComponent().val();            // returns array: ["selectedValue"]
this.find('#checkbox').getComponent().getCheckedStatus(); // boolean
this.find('#radio').getComponent().checked();           // boolean
this.find('#date').getComponent().val();                // date string

// Set values
this.find('#inputField').getComponent().setValue("text");
this.find('#dropdown').getComponent().val(["value"]);   // set selection

// Enable/disable
this.find('#button').getComponent().enable(false);      // disable
this.find('#button').getComponent().enable(true);       // enable
this.find('#input').getComponent().disable(true);       // disable

// Modal control
this.find('#modal').getComponent().open();
this.find('#modal').getComponent().close();

// Table API
var table = this.find('#empTable').getComponent();
table.radioClick = function(rowNode) { /* custom handler */ };
```

**Migration:** In React, these are all controlled component props:
```tsx
// MCA1: this.find('#dropdown').getComponent().val(["value"]);
// React: <FormSelect value={selectedValue} onChange={setSelectedValue} />
```

---

## 11. Constants Pattern

Constants are defined using `$.Class.extend()`:

```javascript
$.Class.extend("scp.<app>.<module>.constants", {
    // Static properties (accessed without instantiation)
    MSG_001: "Please select a business unit",
    MSG_002: "Role name is mandatory",
    MAX_ITEMS: 30,
    QUEUE_NAMES: { investigation: "INV", review: "REV" },
    TEMPLATE_PATHS: {
        resultsEjs: "//scp/<app>/views/results.ejs",
        detailsEjs: "//scp/<app>/views/details.ejs"
    }
}, {});
```

**Access:** `scp.<app>.<module>.constants.MSG_001`

**Migration:** Convert to TypeScript constants:
```typescript
export const MESSAGES = {
  MSG_001: "Please select a business unit",
  MSG_002: "Role name is mandatory",
} as const;

export const MAX_ITEMS = 30;
```

---

## 12. Common Anti-Patterns Found in Production

These patterns should be fixed during migration, not replicated:

| Anti-Pattern | Found In | Correct Approach |
|-------------|----------|-----------------|
| Global variable leaks (`isTLBFlag = false` without `var`) | membershipandalerts, letters | TypeScript strict mode prevents this |
| Inline HTML building with string concatenation | case-creation, securities | JSX `.map()` rendering |
| Duplicate DOM IDs inside loops | stafftools, securities | Use `key` prop + unique IDs |
| `$(document).ready()` mixed with controller scope | sales-contact | Not needed in React |
| Commented-out dead code | all apps | Delete unused code |
| Heavy inline `style="..."` attributes | sales-contact, letters | Blueprint component props + className |
| Special char replacement hacks (`replace(/\\n/g, "MLSSPACE")`) | letters, case-creation | Proper JSON serialization |
| Magic numbers (30-item limits, page sizes) | sales-contact, maintain-roles | Named constants |

---

## 13. App Complexity Profiles

Understanding complexity helps estimate migration effort:

| App | Modules | Controllers | EJS Files | BDL Heavy? | Legacy jQuery? | Complexity |
|-----|---------|-------------|-----------|------------|----------------|------------|
| scp-ui-securities | 5 | 30+ | 158 | Yes (569 inputs) | Yes (.chosen, .scpTable) | High |
| scp-ui-custadmin | 8+ | 40+ | 100+ | Mixed (newer=BDL) | Yes (.chosen, .scpTable, .dialog) | High |
| scp-ui-case-creation | 6 | 25+ | 50+ | Mixed | Yes (.chosen, .scpTable, .datepicker) | High |
| scp-ui-letters | 4 | 20+ | 40+ | Mixed | Yes (.chosen, .scpTable, .dialog) | Medium |
| scp-ui-stafftools | 5 | 15+ | 30+ | Yes | Yes (.chosen, .scpTable, .dialog) | Medium |
| scp-ui-membershipandalerts | 3 | 15+ | 25+ | Mixed (smsalert=BDL) | Yes (.chosen, .scpTable, .progressiveDisclosure) | Medium |
| scp-ui-maintain-roles | 1 | 16 | 16 | Yes | Yes (select2) | Low-Medium |
| scp-ui-sales-contact | 1 | 1 (504 lines) | 8 | Yes | Yes (.chosen, select2) | Low |

---

## 14. Localization

Found in `scp-ui-letters`:

```
cmod/locales/en.json
cmod/locales/cy.json  (Welsh)
```

Accessed via: `this._('mca.letters.cmod.main.messages.error.message')`

**Migration:** Use `react-i18next` or a simple JSON import pattern with keys.

---

## 15. Build System

All apps use Gradle with the `mca-ui` plugin:

```groovy
apply plugin: 'com.barclays.mca.devops.gradle-mca-ui-plugin'

dependencies {
    foundation 'com.barclays.mca:scp-libs-uifoundation:22.01.029@tar'
    framework 'com.barclays.mca:javascriptmvc:bi3.2.2@tar'
    container 'com.barclays.mca:scp-container-cgs:5.0.+@war'
}

minimise {
    controllers = [
        'scp/<app>/<module>/controllers/<name>.js'
    ]
    views = ['scp/<app>/<module>/views']
}
```

**Migration:** MCA2 uses npm/webpack-based builds (`eagle-scripts`).

---

## Version History

### v1.0 (July 7, 2026)
- Initial version based on analysis of 8 production MCA1 applications
