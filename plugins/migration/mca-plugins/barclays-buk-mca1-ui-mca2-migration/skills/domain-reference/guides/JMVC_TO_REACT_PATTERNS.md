# JMVC to React — Pattern Conversion Guide

**Version**: 1.0
**Last Updated**: July 7, 2026
**Purpose**: Definitive mapping of every MCA1 JMVC pattern to its React equivalent

---

## Quick Reference Table

| MCA1 JMVC Pattern | React Equivalent | Notes |
|-------------------|-----------------|-------|
| `steal().then(function($){...})` | `import` statements | ES modules |
| `BaseController('namespace', {}, {})` | `export const Component: React.FC` | Functional component |
| `init()` | `useEffect(() => {...}, [])` | Component mount |
| `this._super.apply(this, arguments)` | N/A | No class inheritance in React |
| `this.element` | Component root / `useRef` | |
| `this.find('#id')` | `useRef` or `document.getElementById` | Prefer ref |
| `this.options` | Component `props` | |
| `this.proxy(fn)` | Arrow function `() => {}` | Auto-bound |
| `this.disable()` / `this.enable()` | `const [loading, setLoading] = useState(false)` | |
| `this.loaded()` | `useEffect` return / state flag | |
| `workflow.model(key, val)` | Redux `dispatch(action(val))` / Zustand `set()` | |
| `workflow.model(key)` | `useSelector(state => state.key)` / Zustand `get()` | |
| `workflow.trigger(event)` | `dispatch(action())` | |
| `'{workflow} EVENT'` handler | `useEffect` reacting to state change | |
| `hub.model()` / `hub.trigger()` | React Context or lifted state | |
| `this.callService(n, e, p)` | RTK Query mutation / `useEffect` + fetch | |
| `.done(cb)` | `.then()` or `await` | |
| `.fail(cb)` | `.catch()` or try/catch | |
| `.always(cb)` | `.finally()` | |
| `this.resume('step')` | `navigate('/step')` | MemoryRouter |
| `WindowManager.closeWindow()` | `navigate('/')` or container callback | |
| `WindowManager.launchWindow({type:'lightbox'})` | `setDialogOpen(true)` + `<Dialog>` | |
| `this.element.html(path, data)` | Conditional JSX `{condition && <Component />}` | |
| `this.element.formParams()` | `getValues()` (RHF) or `values` (Formik) | |
| `this.validate(model)` | `schema.validate(values)` (Yup) | |
| `this.invalidate()` | `clearErrors()` (RHF) or `resetForm()` | |
| `new Model(params)` | Yup schema definition | |
| `this.error(msg)` | `setError(msg)` + `<Alert>` | |
| `ErrorListController` | `<Alert>` with error array | |
| `'#btn click': fn` | `onClick={fn}` on element | |
| `'#input change': fn` | `onChange={fn}` on element | |
| `$.Class.extend('constants', {}, {})` | `export const CONSTANTS = {...} as const` | |
| `.getComponent().getValue()` | Controlled input `value` state | |
| `.getComponent().enable(false)` | `disabled` prop | |
| `.chosen()` | `<FormSelect>` or `<Autocomplete>` | Blueprint |
| `.scpTable(opts)` | `<Table>` + `<Pagination>` | Blueprint |
| `.dialog({buttons, modal})` | `<Dialog head={} foot={}>` | Blueprint |
| `.datepicker()` | `<FormInput type="date">` or calendar | |
| `.setMask('99-99-99')` | Input masking library or pattern attr | |
| `.progressiveDisclosure()` | `<Accordion>` / conditional render | |

---

## 1. Module Structure Conversion

### MCA1 (steal + JMVC controller)

```javascript
steal({src: "scp/ui/common/bundles/core", packaged: false, ignore: false})
    .then("scp/app/module/models/models.js")
    .then("scp/app/module/constants/constants.js")
    .then("scp/ui/common/vendor/chosen/chosen.js")
    .then(function($) {

scp.ui.common.controllers.BaseController(
    "scp.app.module.controllers.details", {
        webComponents: { bundles: ['bdl'] }
    }, {
        init: function() {
            this._super.apply(this, arguments);
            this.element.html(this.options.template, {});
            this.initializeView();
        },
        initializeView: function() {
            new scp.ui.common.validation.ErrorListController(this.element, this.options);
            this.callService("init", "preload")
                .done(this.proxy(this.onPreloadSuccess))
                .always(this.proxy(this.handleServiceResponse), this.proxy(this.loaded));
        },
        onPreloadSuccess: function(data) {
            this.workflow.model("PRELOAD_DATA", data);
            this.element.find("#results").html("//scp/app/views/results.ejs", { items: data.items });
            this.find('#dropdown').chosen();
        },
        '#button-next click': function() {
            this.disable();
            this.invalidate();
            var model = new scp.app.module.models.Details(this.element.formParams());
            if (this.validate(model)) {
                this.callService("save", "save-details", this.buildRequest())
                    .done(this.proxy(this.onSaveSuccess))
                    .always(this.proxy(this.handleServiceResponse), this.proxy(this.enable));
            } else {
                this.enable();
            }
        },
        onSaveSuccess: function(data) {
            this.workflow.model("SAVE_RESULT", data);
            this.resume("confirm");
        }
    }
);

}); // end steal
```

### MCA2 (React functional component)

```tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { yupResolver } from '@hookform/resolvers/yup';
import * as Yup from 'yup';
import { Button, Alert, FormItem, FormInput, FormSelect } from '@barclays/blueprint-react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { setPreloadData, setSaveResult } from '../store/detailsSlice';
import { usePreloadQuery, useSaveDetailsMutation } from '../services/api';

interface DetailsFormValues {
  fieldName: string;
  dropdown: string;
}

const schema = Yup.object({
  fieldName: Yup.string().required('Field is required'),
  dropdown: Yup.string().required('Please select an option'),
});

export const DetailsPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [error, setError] = useState<string | null>(null);

  const { data: preloadData, isLoading: isPreloading } = usePreloadQuery();
  const [saveDetails, { isLoading: isSaving }] = useSaveDetailsMutation();

  const { register, handleSubmit, formState: { errors } } = useForm<DetailsFormValues>({
    resolver: yupResolver(schema),
  });

  useEffect(() => {
    if (preloadData) {
      dispatch(setPreloadData(preloadData));
    }
  }, [preloadData, dispatch]);

  const onSubmit = async (values: DetailsFormValues) => {
    try {
      setError(null);
      const result = await saveDetails(values).unwrap();
      dispatch(setSaveResult(result));
      navigate('/confirm');
    } catch (err) {
      setError(err.message || 'An error occurred');
    }
  };

  if (isPreloading) return <Loading />;

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {error && <Alert context="warning">{error}</Alert>}

      <FormItem label="Field Name" error={errors.fieldName?.message}>
        {(props) => <FormInput {...props} {...register('fieldName')} />}
      </FormItem>

      <FormItem label="Dropdown" error={errors.dropdown?.message}>
        {(props) => (
          <FormSelect {...props} {...register('dropdown')}>
            <option value="">Select item</option>
            {preloadData?.items.map(item => (
              <option key={item.id} value={item.id}>{item.name}</option>
            ))}
          </FormSelect>
        )}
      </FormItem>

      <Button type="submit" disabled={isSaving}>
        {isSaving ? 'Saving...' : 'Next'}
      </Button>
    </form>
  );
};
```

---

## 2. Event Delegation → React Event Handlers

### MCA1

```javascript
{
    '#searchBtn click': function() {
        this.performSearch();
    },
    '#sortCode change': function(el) {
        this.validateSortCode(el.val());
    },
    '#empTable tbody tr click': function(el) {
        var rowData = el.data();
        this.selectEmployee(rowData);
    },
    'input[type=text] keyup': function(el, ev) {
        if (ev.which !== 9) this.validateElement(el);
    }
}
```

### MCA2 (React)

```tsx
const handleSearch = () => { performSearch(); };
const handleSortCodeChange = (e: ChangeEvent<HTMLInputElement>) => {
  validateSortCode(e.target.value);
};
const handleRowClick = (rowData: Employee) => {
  selectEmployee(rowData);
};

return (
  <>
    <Button onClick={handleSearch}>Search</Button>
    <FormInput onChange={handleSortCodeChange} />
    <Table>
      <tbody>
        {employees.map(emp => (
          <tr key={emp.id} onClick={() => handleRowClick(emp)}>
            <td>{emp.name}</td>
          </tr>
        ))}
      </tbody>
    </Table>
  </>
);
```

---

## 3. workflow.model() → Redux/Zustand State

### MCA1

```javascript
// Controller A: Store data after API call
this.callService("init", "preload").done(this.proxy(function(data) {
    this.workflow.model("CUSTOMER_DETAILS", data.customer);
    this.workflow.model("ACCOUNTS_LIST", data.accounts);
    this.workflow.model("EDIT_MODE", true);
}));

// Controller B: Read data on another page
init: function() {
    var customer = this.workflow.model("CUSTOMER_DETAILS");
    var accounts = this.workflow.model("ACCOUNTS_LIST");
    this.element.html(this.options.template, { customer: customer, accounts: accounts });
}
```

### MCA2 (Redux Toolkit)

```typescript
// store/customerSlice.ts
import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface CustomerState {
  details: Customer | null;
  accounts: Account[];
  editMode: boolean;
}

const customerSlice = createSlice({
  name: 'customer',
  initialState: { details: null, accounts: [], editMode: false } as CustomerState,
  reducers: {
    setCustomerDetails: (state, action: PayloadAction<Customer>) => {
      state.details = action.payload;
    },
    setAccounts: (state, action: PayloadAction<Account[]>) => {
      state.accounts = action.payload;
    },
    setEditMode: (state, action: PayloadAction<boolean>) => {
      state.editMode = action.payload;
    },
  },
});

// Page A: Dispatch after API call
const PageA: React.FC = () => {
  const dispatch = useAppDispatch();
  const { data } = usePreloadQuery();
  
  useEffect(() => {
    if (data) {
      dispatch(setCustomerDetails(data.customer));
      dispatch(setAccounts(data.accounts));
      dispatch(setEditMode(true));
    }
  }, [data]);
};

// Page B: Read from store
const PageB: React.FC = () => {
  const customer = useAppSelector(state => state.customer.details);
  const accounts = useAppSelector(state => state.customer.accounts);
  
  return <ConfirmationView customer={customer} accounts={accounts} />;
};
```

---

## 4. callService() → RTK Query / Async Hooks

### MCA1

```javascript
'#submitBtn click': function() {
    this.disable();
    this.invalidate();
    
    var requestObj = {
        customerId: this.workflow.model("CUSTOMER_ID"),
        sortCode: this.find('#sortCode').getComponent().getValue(),
        accountNumber: this.find('#accountNumber').getComponent().getValue()
    };
    
    this.callService("locate", "locate-customer", requestObj)
        .done(this.proxy(function(data) {
            if (data.results.length === 0) {
                this.error("No results found");
            } else {
                this.workflow.model("SEARCH_RESULTS", data.results);
                this.resume("results");
            }
        }))
        .fail(this.proxy(function(error) {
            this.error("Service unavailable. Please try again.");
        }))
        .always(this.proxy(this.handleServiceResponse), this.proxy(this.enable));
}
```

### MCA2 (RTK Query)

```typescript
// services/api.ts
export const customerApi = createApi({
  reducerPath: 'customerApi',
  baseQuery: fetchBaseQuery({ baseUrl: '/api/' }),
  endpoints: (builder) => ({
    locateCustomer: builder.mutation<LocateResponse, LocateRequest>({
      query: (body) => ({ url: 'locate-customer', method: 'POST', body }),
    }),
  }),
});

// Component
const SearchPage: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const customerId = useAppSelector(state => state.customer.id);
  const [error, setError] = useState<string | null>(null);
  const [locateCustomer, { isLoading }] = useLocateCustomerMutation();

  const handleSubmit = async (values: SearchFormValues) => {
    setError(null);
    try {
      const data = await locateCustomer({
        customerId,
        sortCode: values.sortCode,
        accountNumber: values.accountNumber,
      }).unwrap();

      if (data.results.length === 0) {
        setError("No results found");
      } else {
        dispatch(setSearchResults(data.results));
        navigate('/results');
      }
    } catch (err) {
      setError("Service unavailable. Please try again.");
    }
  };

  return (
    <>
      {error && <Alert context="warning">{error}</Alert>}
      <SearchForm onSubmit={handleSubmit} disabled={isLoading} />
    </>
  );
};
```

---

## 5. Validation Model → Yup Schema

### MCA1

```javascript
scp.ui.common.Model("scp.app.models.CreateForm", {
    init: function() {
        this.validate("businessUnit", {}, function() {
            if (this.businessUnit === "" || this.businessUnit === " ") {
                return "Please select a business unit";
            }
        });
        this.validate("roleName", {}, function() {
            if (/^[0-9a-zA-Z \b]+$/.test(this.roleName) === false) {
                return "Role name can only contain alpha numeric characters";
            }
            if (this.roleName.length > 50) {
                return "Role name must be 50 characters or less";
            }
        });
        this.validate("startDate", {}, function() {
            if (this.startDate && !isValidDate(this.startDate)) {
                return "Please enter a valid date (DD/MM/YYYY)";
            }
        });
        this.validate("phoneNumber", {}, function() {
            if ($("#phoneNumber").is(":visible")) {
                if (!this.phoneNumber) return "Phone number is required";
            }
        });
    }
}, {});
```

### MCA2 (Yup)

```typescript
import * as Yup from 'yup';

const createFormSchema = Yup.object({
  businessUnit: Yup.string()
    .required("Please select a business unit")
    .notOneOf([" "], "Please select a business unit"),

  roleName: Yup.string()
    .required("Role name is required")
    .matches(/^[0-9a-zA-Z ]+$/, "Role name can only contain alpha numeric characters")
    .max(50, "Role name must be 50 characters or less"),

  startDate: Yup.string()
    .test('valid-date', 'Please enter a valid date (DD/MM/YYYY)', (value) => {
      if (!value) return true; // optional
      return isValidDate(value);
    }),

  phoneNumber: Yup.string().when('$isPhoneVisible', {
    is: true,
    then: (schema) => schema.required("Phone number is required"),
    otherwise: (schema) => schema.optional(),
  }),
});
```

**Key difference:** MCA1 validation checks DOM visibility (`$(#field).is(":visible")`) — in React, use Yup's `when()` with form context values instead of DOM queries.

---

## 6. resume() Navigation → MemoryRouter

### MCA1

```javascript
// Forward navigation
this.resume("confirm");
this.resume("next");
this.resume("results", { data: searchResults });

// Back navigation  
this.resume("back");
this.resume("back-home", { type: "takeover" });

// Lightbox/modal navigation
this.resume("view-details", { type: "lightbox" });
scp.ui.container.WindowManager.launchWindow({
    type: 'lightbox', processId: detailsController
});
```

### MCA2 (MemoryRouter + Dialog)

```tsx
import { useNavigate } from 'react-router-dom';

const Page: React.FC = () => {
  const navigate = useNavigate();
  const [dialogOpen, setDialogOpen] = useState(false);

  // Forward navigation
  const handleNext = () => navigate('/confirm');
  const handleResults = () => navigate('/results');

  // Back navigation
  const handleBack = () => navigate(-1);
  const handleBackHome = () => navigate('/');

  // Lightbox → Dialog
  const handleViewDetails = () => setDialogOpen(true);

  return (
    <>
      <Button onClick={handleNext}>Next</Button>
      <Button onClick={handleBack}>Back</Button>
      <Button onClick={handleViewDetails}>View Details</Button>
      
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        head={<Type element="h2" size="xl">Details</Type>}
      >
        <DetailsContent />
      </Dialog>
    </>
  );
};
```

---

## 7. EJS Template Logic → JSX

### MCA1 (EJS)

```ejs
<mca-fluidview>
  <mca-cell size="12">
    <% if (this.isEditMode) { %>
      <mca-button id="saveBtn" type="primary">Save</mca-button>
    <% } %>
    
    <mca-table id="resultsTable" paging="yes" sort="yes">
      <mca-table-row header="yes">
        <mca-table-cell>Name</mca-table-cell>
        <mca-table-cell>Status</mca-table-cell>
      </mca-table-row>
      <% for (var i = 0; i < this.items.length; i++) { %>
        <mca-table-row>
          <mca-table-cell><%= this.items[i].name %></mca-table-cell>
          <mca-table-cell>
            <% if (this.items[i].active) { %>
              <span class="scp-message-success">Active</span>
            <% } else { %>
              <span class="scp-message-error">Inactive</span>
            <% } %>
          </mca-table-cell>
        </mca-table-row>
      <% } %>
    </mca-table>
  </mca-cell>
</mca-fluidview>
```

### MCA2 (JSX)

```tsx
<Grid>
  <Grid.Col span={12}>
    {isEditMode && (
      <Button onClick={handleSave}>Save</Button>
    )}

    <Table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr key={item.id}>
            <td>{item.name}</td>
            <td>
              {item.active ? (
                <Type color="success">Active</Type>
              ) : (
                <Type color="error">Inactive</Type>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  </Grid.Col>
</Grid>
```

---

## 8. Dirty Form Tracking

### MCA1

```javascript
init: function() {
    this.initialFormState = JSON.stringify(this.element.formParams());
},
checkDirty: function() {
    return this.initialFormState !== JSON.stringify(this.element.formParams());
},
'.scp-close-link click': function() {
    if (this.checkDirty()) {
        scp.ui.container.WindowManager.cancelApp({
            confirmDialogText: "You have unsaved changes. Are you sure?"
        });
    } else {
        scp.ui.container.WindowManager.closeWindow();
    }
}
```

### MCA2 (React)

```tsx
import { useForm } from 'react-hook-form';
import { useBlocker } from 'react-router-dom';

const Page: React.FC = () => {
  const { formState: { isDirty } } = useForm();
  const [showExitDialog, setShowExitDialog] = useState(false);

  // Block navigation if form is dirty
  useBlocker(({ currentLocation, nextLocation }) => {
    if (isDirty && currentLocation.pathname !== nextLocation.pathname) {
      setShowExitDialog(true);
      return true;
    }
    return false;
  });

  return (
    <>
      {/* form content */}
      <Dialog open={showExitDialog} onClose={() => setShowExitDialog(false)}
        head={<Type element="h2" size="xl">Unsaved Changes</Type>}
        foot={<Button onClick={handleDiscard}>Discard</Button>}
      >
        You have unsaved changes. Are you sure you want to leave?
      </Dialog>
    </>
  );
};
```

---

## 9. DataTable with Server-Side Pagination

### MCA1

```javascript
init: function() {
    this.element.find("#resultsTable").scpTable({
        bServerSide: true,
        paginate: { on: true, recordsPerPage: 10 },
        sort: { on: true },
        fnServerData: this.proxy(function(sSource, aoData, fnCallback, oSettings) {
            var params = { pgst: oSettings._iDisplayStart, pgsz: oSettings._iDisplayLength };
            this.callService('search', 'search-results', params)
                .done(this.proxy(function(data) {
                    fnCallback({
                        sEcho: oSettings.sEcho,
                        iTotalRecords: data.totalCount,
                        iTotalDisplayRecords: data.totalCount,
                        aaData: data.results
                    });
                }));
        })
    });
}
```

### MCA2 (React)

```tsx
import { Table, Pagination } from '@barclays/blueprint-react';

const ResultsTable: React.FC = () => {
  const [page, setPage] = useState(0);
  const [pageSize] = useState(10);
  const [sortField, setSortField] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');

  const { data, isLoading } = useSearchResultsQuery({ page, pageSize, sortField, sortDir });

  const handleSort = (field: string) => {
    if (sortField === field) {
      setSortDir(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
    setPage(0);
  };

  if (isLoading) return <Loading />;

  return (
    <>
      <Table>
        <thead>
          <tr>
            <th onClick={() => handleSort('name')}>Name</th>
            <th onClick={() => handleSort('date')}>Date</th>
          </tr>
        </thead>
        <tbody>
          {data?.results.map(row => (
            <tr key={row.id}>
              <td>{row.name}</td>
              <td>{row.date}</td>
            </tr>
          ))}
        </tbody>
      </Table>
      <Pagination
        totalItems={data?.totalCount ?? 0}
        pageSize={pageSize}
        currentPage={page + 1}
        onPageChange={(p) => setPage(p - 1)}
      />
    </>
  );
};
```

---

## 10. Multi-Step Wizard Flow

### MCA1

```javascript
// Step 1 controller
'#button-next click': function() {
    if (this.validate(model)) {
        this.workflow.model("STEP1_DATA", this.element.formParams());
        this.resume("step2");
    }
}

// Step 2 controller
init: function() {
    var step1Data = this.workflow.model("STEP1_DATA");
    this.element.html(this.options.template, { prevData: step1Data });
},
'#button-back click': function() { this.resume("back"); },
'#button-next click': function() {
    this.workflow.model("STEP2_DATA", this.element.formParams());
    this.resume("confirm");
}

// Confirmation controller
init: function() {
    var allData = {
        ...this.workflow.model("STEP1_DATA"),
        ...this.workflow.model("STEP2_DATA")
    };
    this.element.html(this.options.template, { summary: allData });
},
'#button-confirm click': function() {
    this.callService("submit", "create-record", allData)
        .done(this.proxy(function() { this.resume("success"); }));
}
```

### MCA2 (React Router + Redux)

```tsx
// App routes
<MemoryRouter>
  <Routes>
    <Route path="/" element={<Step1Page />} />
    <Route path="/step2" element={<Step2Page />} />
    <Route path="/confirm" element={<ConfirmPage />} />
    <Route path="/success" element={<SuccessPage />} />
  </Routes>
</MemoryRouter>

// Step1Page.tsx
const Step1Page: React.FC = () => {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  
  const onSubmit = (values: Step1Values) => {
    dispatch(setStep1Data(values));
    navigate('/step2');
  };
  
  return <Step1Form onSubmit={onSubmit} />;
};

// ConfirmPage.tsx
const ConfirmPage: React.FC = () => {
  const navigate = useNavigate();
  const step1 = useAppSelector(state => state.wizard.step1);
  const step2 = useAppSelector(state => state.wizard.step2);
  const [submitRecord] = useCreateRecordMutation();

  const handleConfirm = async () => {
    await submitRecord({ ...step1, ...step2 }).unwrap();
    navigate('/success');
  };

  return (
    <>
      <Summary data={{ ...step1, ...step2 }} />
      <Button onClick={() => navigate(-1)}>Back</Button>
      <Button onClick={handleConfirm}>Confirm</Button>
    </>
  );
};
```

---

## 11. Special Patterns

### 11.1 Item Limit Enforcement (e.g., max 30 items)

**MCA1:**
```javascript
if (this.empDetails.length < 30) {
    this.empDetails.unshift(newItem);
} else {
    this.error("Maximum of 30 items allowed");
}
```

**MCA2:**
```tsx
const MAX_ITEMS = 30;
const handleAdd = (newItem: Item) => {
  if (items.length >= MAX_ITEMS) {
    setError(`Maximum of ${MAX_ITEMS} items allowed`);
    return;
  }
  setItems(prev => [newItem, ...prev]);
};
```

### 11.2 Dual Input Mechanism (Combobox + Free Text Textarea)

**MCA1:**
```javascript
var idsFromCombo = this.find('#serviceCombo').getComponent().val();
var idsFromText = this.find('#serviceIds').val().split(',').map(s => s.trim());
this.allIds = this.getCombinedList(idsFromText, idsFromCombo);
```

**MCA2:**
```tsx
const [comboValue, setComboValue] = useState<string[]>([]);
const [textValue, setTextValue] = useState('');

const allIds = useMemo(() => {
  const fromText = textValue.split(',').map(s => s.trim()).filter(Boolean);
  return [...new Set([...comboValue, ...fromText])];
}, [comboValue, textValue]);
```

### 11.3 Chosen Trigger Update After DOM Change

**MCA1:**
```javascript
this.find('#dropdown').val(newValue).trigger("liszt:updated").trigger("change");
```

**MCA2:** Not needed — React controlled components update automatically:
```tsx
<FormSelect value={selectedValue} onChange={(e) => setSelectedValue(e.target.value)}>
```

### 11.4 Progressive Disclosure (Show/Hide Sections)

**MCA1:**
```javascript
$('.prog-dis-container').progressiveDisclosure();
// or manual:
this.find('#details-section').toggleClass('scp-hide');
```

**MCA2:**
```tsx
const [isExpanded, setIsExpanded] = useState(false);
return (
  <Accordion>
    <AccordionItem title="Details" isOpen={isExpanded} onToggle={() => setIsExpanded(!isExpanded)}>
      <DetailsContent />
    </AccordionItem>
  </Accordion>
);
```

---

## Version History

### v1.0 (July 7, 2026)
- Initial version covering all JMVC-to-React conversion patterns from 8 production apps
