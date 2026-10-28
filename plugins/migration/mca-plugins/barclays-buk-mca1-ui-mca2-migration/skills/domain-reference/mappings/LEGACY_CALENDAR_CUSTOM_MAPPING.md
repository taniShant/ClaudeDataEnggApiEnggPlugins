# LEGACY_CALENDAR_CUSTOM_MAPPING.md

## Overview

Maps MCA1 legacy custom components that don't fit other categories: event calendars (weekly/monthly), select-to-radio toggle patterns, and the legacy validation framework. These are all jQuery-based with no Web Component equivalents.

---

## Detection Patterns

```grep
new CalendarUI\(
scp-abs-calendar
scp-abs-calendar__weekly
scp-abs-calendar__monthly
clickEventListener
calendarAppointments
selectToRadio
scp\.ui\.common\.Model\(
validatePresenceOf
scp_ui_common_validation_error_list
scp\.ui\.common\.validation\.ErrorList
scp\.ui\.common\.messages\.MessageList
```

---

## Component: Event Calendar (Weekly View)

### MCA1 Pattern

```html
<table class="scp-abs-calendar scp-abs-calendar__weekly" id="calendar-weekly"></table>
```

```javascript
var weekgrid = new CalendarUI({
  container: '#calendar-weekly',
  date: new Date(2015, 8, 11),
  appointments: sample_data.calendarAppointments,
  type: 'weekly',
  clickEventListener: function(objEventData) {
    console.log(objEventData);
  }
});
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Calendar } from '@barclays/mca-react-calendar';

interface Appointment {
  id: string;
  title: string;
  start: Date;
  end: Date;
}

interface WeekCalendarProps {
  date: Date;
  appointments: Appointment[];
  onEventClick: (event: Appointment) => void;
}

export const WeeklyCalendar: React.FC<WeekCalendarProps> = ({ date, appointments, onEventClick }) => (
  <Calendar
    view="week"
    date={date}
    events={appointments}
    onEventClick={onEventClick}
  />
);
```

**Important:** Blueprint-React has NO built-in calendar component. Use `@barclays/mca-react-calendar` package. See `BDL_CALENDAR_MAPPING.md` for full details.

---

## Component: Event Calendar (Monthly View)

### MCA1 Pattern

```html
<table class="scp-abs-calendar scp-abs-calendar__monthly" id="calendar-monthly"></table>
```

```javascript
var monthgrid = new CalendarUI({
  container: '#calendar-monthly',
  date: new Date(2015, 8, 1),
  appointments: sample_data.calendarAppointments,
  type: 'monthly',
  clickEventListener: function(objEventData) {
    console.log(objEventData);
  }
});
```

### Blueprint-React Equivalent

```typescript
import React from 'react';
import { Calendar } from '@barclays/mca-react-calendar';

interface Appointment {
  id: string;
  title: string;
  start: Date;
  end: Date;
}

export const MonthlyCalendar: React.FC<{ date: Date; appointments: Appointment[] }> = ({ date, appointments }) => (
  <Calendar
    view="month"
    date={date}
    events={appointments}
    onEventClick={(event) => console.log(event)}
  />
);
```

### CalendarUI Options → Props Mapping

| MCA1 Option | Blueprint Prop | Notes |
|-------------|---------------|-------|
| `container` | Not needed | React renders into its place in JSX |
| `date` | `date` prop | Same — JavaScript Date object |
| `appointments` | `events` prop | Rename but same structure |
| `type: 'weekly'` | `view="week"` | View type |
| `type: 'monthly'` | `view="month"` | View type |
| `clickEventListener` | `onEventClick` callback | Event click handler |

---

## Component: Select-to-Radio Toggle

### MCA1 Pattern

```html
<div id="selRad">
  <label for="mySelect" class="scp-label"></label>
  <select id="mySelect" class="scp-select">
    <option value="Yes">YES</option>
    <option value="No">NO</option>
  </select>
</div>
<a href="#" id="applyNewLook" onclick="return false;">Click to replace drop down</a>
```

```javascript
$("#applyNewLook").click(function() {
  if (!$("#selRad").find("select").length) {
    // Rebuild as select
    $("#selRad").html("<select class='scp-select'>...</select>");
  } else {
    // Replace with radio buttons
    $("#selRad").html("<input type='radio' ...>Yes <input type='radio' ...>No");
  }
});
```

### Blueprint-React Equivalent

For simple yes/no options, use `FormRadio` group directly (the radio pattern is more accessible):

```typescript
import React, { useState } from 'react';
import { FormItem, FormRadio, Type } from '@barclays/blueprint-react';

export const YesNoToggle: React.FC = () => {
  const [value, setValue] = useState<string>('');

  return (
    <FormItem
      label={<Type>Selection</Type>}
      render={() => (
        <>
          <FormRadio
            name="yesno"
            value="Yes"
            checked={value === 'Yes'}
            onChange={() => setValue('Yes')}
            label="Yes"
          />
          <FormRadio
            name="yesno"
            value="No"
            checked={value === 'No'}
            onChange={() => setValue('No')}
            label="No"
          />
        </>
      )}
    />
  );
};
```

**If the toggle between display modes is actually needed:**

```typescript
import React, { useState } from 'react';
import { FormItem, FormSelect, FormRadio, Button, Type } from '@barclays/blueprint-react';

export const ToggleableInput: React.FC = () => {
  const [mode, setMode] = useState<'select' | 'radio'>('select');
  const [value, setValue] = useState('');

  return (
    <>
      <FormItem
        label={<Type>Selection</Type>}
        render={(props) => (
          mode === 'select' ? (
            <FormSelect {...props} value={value} onChange={(e) => setValue(e.target.value)}>
              <option value="Yes">YES</option>
              <option value="No">NO</option>
            </FormSelect>
          ) : (
            <>
              <FormRadio name="toggle" value="Yes" checked={value === 'Yes'} onChange={() => setValue('Yes')} label="Yes" />
              <FormRadio name="toggle" value="No" checked={value === 'No'} onChange={() => setValue('No')} label="No" />
            </>
          )
        )}
      />
      <Button variant="tertiary" onClick={() => setMode(mode === 'select' ? 'radio' : 'select')}>
        Switch to {mode === 'select' ? 'radio buttons' : 'dropdown'}
      </Button>
    </>
  );
};
```

---

## Component: Legacy Validation Framework

### MCA1 Pattern

```javascript
// Model definition with validation rules
scp.ui.common.Model("scp.models.Test", {
  init: function() {
    this.validatePresenceOf("Name", { message: "Name must not be empty." });
    this.validatePresenceOf("Age", { message: "Age must not be empty." });
    this.validatePresenceOf("Grade", { message: "Grade must not be empty." });
    this.validatePresenceOf("DOB", { message: "Date Of Birth must not be empty." });
  }
}, {});

// Controller triggers validation
scp.ui.common.controllers.BaseController("scp.Test", {
  init: function() {
    this._super.apply(this, arguments);
    this.hub.model(scp.ui.common.validation.ErrorList, new scp.ui.common.validation.ErrorList());
    this.hub.model(scp.ui.common.messages.MessageList, new scp.ui.common.messages.MessageList());
    this.element.scp_ui_common_validation_error_list(options);
    var params = this.element.formParams();
    var m = new scp.models.Test(params);
    this.validate(m);
  }
});
```

### Blueprint-React Equivalent

```typescript
import React, { useState } from 'react';
import * as Yup from 'yup';
import { Form, FormItem, FormInput, FormSelect, Button, Type, Alert, Icon } from '@barclays/blueprint-react';

const validationSchema = Yup.object({
  name: Yup.string().required('Name must not be empty.'),
  age: Yup.string().required('Age must not be empty.'),
  grade: Yup.string().required('Grade must not be empty.'),
  dob: Yup.string().required('Date Of Birth must not be empty.'),
});

interface FormValues {
  name: string;
  age: string;
  grade: string;
  dob: string;
}

export const ValidatedForm: React.FC = () => {
  const [values, setValues] = useState<FormValues>({ name: '', age: '', grade: '', dob: '' });
  const [errors, setErrors] = useState<Partial<Record<keyof FormValues, string>>>({});

  const handleSubmit = async () => {
    try {
      await validationSchema.validate(values, { abortEarly: false });
      setErrors({});
      // proceed with form submission
    } catch (err) {
      if (err instanceof Yup.ValidationError) {
        const fieldErrors: Partial<Record<keyof FormValues, string>> = {};
        err.inner.forEach((e) => {
          if (e.path) fieldErrors[e.path as keyof FormValues] = e.message;
        });
        setErrors(fieldErrors);
      }
    }
  };

  const handleChange = (field: keyof FormValues) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setValues({ ...values, [field]: e.target.value });
    if (errors[field]) setErrors({ ...errors, [field]: undefined });
  };

  return (
    <Form>
      {Object.keys(errors).length > 0 && (
        <Alert status="error" media={<Icon icon="error-fill" size="sm" status="error" />}>
          <Type>Please correct the errors below</Type>
        </Alert>
      )}
      <FormItem
        label={<Type>Name</Type>}
        error={errors.name && <Type color="error">{errors.name}</Type>}
        render={(props) => (
          <FormInput {...props} value={values.name} onChange={handleChange('name')} />
        )}
      />
      <FormItem
        label={<Type>Age</Type>}
        error={errors.age && <Type color="error">{errors.age}</Type>}
        render={(props) => (
          <FormInput {...props} value={values.age} onChange={handleChange('age')} />
        )}
      />
      <FormItem
        label={<Type>Grade</Type>}
        error={errors.grade && <Type color="error">{errors.grade}</Type>}
        render={(props) => (
          <FormSelect {...props} value={values.grade} onChange={handleChange('grade')}>
            <option value="">Please select</option>
            <option value="A">A</option>
          </FormSelect>
        )}
      />
      <FormItem
        label={<Type>Date of Birth</Type>}
        error={errors.dob && <Type color="error">{errors.dob}</Type>}
        render={(props) => (
          <FormInput {...props} value={values.dob} onChange={handleChange('dob')} placeholder="DD/MM/YYYY" />
        )}
      />
      <Button variant="primary" onClick={handleSubmit}>Validate</Button>
    </Form>
  );
};
```

### Validation Framework Mapping

| MCA1 Pattern | React Equivalent | Notes |
|-------------|-----------------|-------|
| `scp.ui.common.Model(...)` | Yup schema definition | Declarative validation rules |
| `validatePresenceOf(field, {message})` | `Yup.string().required(message)` | Required field validation |
| `this.validate(model)` | `schema.validate(values, {abortEarly: false})` | Trigger all validations |
| `ErrorList` model | `errors` state object | `Partial<Record<field, string>>` |
| `MessageList` model | `Alert` component | Conditional render |
| `scp_ui_common_validation_error_list` | `FormItem error` prop | Per-field error display |
| `this.element.formParams()` | Component state (`values`) | Controlled form pattern |

---

## Iron Rules

1. **Calendar components require `@barclays/mca-react-calendar`** — Blueprint has no calendar; see `BDL_CALENDAR_MAPPING.md`
2. **`new CalendarUI()` → `<Calendar>` component from external package** — pass same data as props
3. **Select-to-radio toggles → prefer one pattern (usually radio for yes/no)** — the toggle itself is rarely needed in modern UI
4. **Legacy validation framework → Yup schemas** — see `BDL_VALIDATION_PATTERNS_MAPPING.md` for full patterns
5. **`validatePresenceOf` → `Yup.string().required()`** — direct 1:1 mapping
6. **`ErrorList` / `MessageList` → React state** — no model infrastructure needed
7. **Always use `abortEarly: false`** — collect ALL validation errors at once
8. **Error messages wrap in `<Type color="error">`** — FormItem error prop requirement
