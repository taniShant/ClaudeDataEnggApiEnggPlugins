# BDL_CALENDAR_MAPPING.md

## Overview

Maps `<mca-calendar>` (daily, weekly, monthly views with appointments, time slots, and availability status) to the `@barclays/mca-react-calendar` package. Blueprint-React does NOT include a calendar component — an external package is required.

## MCA1 Pattern

```html
<mca-calendar
  template="daily"
  id="v_calendar_daily"
  tabindex=""
>
</mca-calendar>
```

### Templates (Views)

| Template Value | Description |
|----------------|-------------|
| `daily` | Single-day time-slot grid (08:00–17:00) with appointments |
| `weekly` | 7-day column grid with time slots per day |
| `monthly` | Month grid with date cells, appointment counts, and work patterns |
| `monthly_nobar` | Month grid with status flags (Available/Unavailable) instead of progress bars |

### JavaScript API

```javascript
var objCalendar = $('#calendar-jQuery-selector').getComponent();

// Get current HTML markup
objCalendar.getCalendarHTML();

// Reload with new data
objCalendar.reload(JSONDataString);

// Access cell event data
var data = $(calendarViewHTML).find('YOUR_CELL_SELECTOR').data('event');
```

### Data Format (JSON)

Calendar data includes:
- Time slots with duration (height in pixels maps to duration)
- Appointment objects with `id`, `name`, `appointments[]`
- Status classes: `isAvailable`, `isUnavailable`, `isWorkUnavailable`, `isAppointment`, `isPast`, `isFuture`, `isToday`

---

## Blueprint-React Equivalent

### Package: `@barclays/mca-react-calendar`

```typescript
import React, { useState, useEffect } from 'react';
import { Calendar, CalendarView } from '@barclays/mca-react-calendar';
import { Section, SectionItem, Type, Button, Arrange, ArrangeItem } from '@barclays/blueprint-react';

interface Appointment {
  id: number;
  name: string;
  time: string;
  duration: number;
  location?: string;
  status: 'complete' | 'in-progress' | 'pending';
}

interface CalendarProps {
  view: 'daily' | 'weekly' | 'monthly';
  appointments: Appointment[];
  onCellClick?: (event: CalendarEvent) => void;
}

export const AppointmentCalendar: React.FC<CalendarProps> = ({ view, appointments, onCellClick }) => {
  const [currentView, setCurrentView] = useState<CalendarView>(view);
  const [calendarData, setCalendarData] = useState(appointments);

  const handleReload = (newData: Appointment[]) => {
    setCalendarData(newData);
  };

  return (
    <Section>
      <SectionItem>
        <Arrange>
          <ArrangeItem size="fit">
            <Button variant={currentView === 'daily' ? 'primary' : 'secondary'} onClick={() => setCurrentView('daily')}>
              Daily
            </Button>
          </ArrangeItem>
          <ArrangeItem size="fit">
            <Button variant={currentView === 'weekly' ? 'primary' : 'secondary'} onClick={() => setCurrentView('weekly')}>
              Weekly
            </Button>
          </ArrangeItem>
          <ArrangeItem size="fit">
            <Button variant={currentView === 'monthly' ? 'primary' : 'secondary'} onClick={() => setCurrentView('monthly')}>
              Monthly
            </Button>
          </ArrangeItem>
        </Arrange>
      </SectionItem>
      <SectionItem>
        <Calendar
          view={currentView}
          data={calendarData}
          onCellClick={onCellClick}
        />
      </SectionItem>
    </Section>
  );
};
```

---

## Attribute Mapping

| MCA1 Attribute | React Equivalent | Notes |
|----------------|-----------------|-------|
| `template` | `view` prop | `"daily"` / `"weekly"` / `"monthly"` |
| `id` | `id` prop on container | For accessibility/testing |
| `tabindex` | Standard React `tabIndex` | Keyboard navigation |

## API Mapping

| MCA1 jQuery API | React Equivalent | Notes |
|-----------------|-----------------|-------|
| `.getComponent()` | Not needed | Direct component reference |
| `.getCalendarHTML()` | Not needed | React handles rendering |
| `.reload(JSONDataString)` | Update state via `setCalendarData(newData)` | Re-render is automatic |
| `$(el).data('event')` | `onCellClick` callback receives event data | Event-driven pattern |

## Status Class Mapping

| MCA1 CSS Class | React State/Prop | Notes |
|----------------|-----------------|-------|
| `isAvailable` | `status: 'available'` | Green indicator |
| `isUnavailable` | `status: 'unavailable'` | Grey/disabled |
| `isWorkUnavailable` | `status: 'work-unavailable'` | Training/out-of-office |
| `isAppointment` | `status: 'appointment'` | Has appointment data |
| `isPast` | `isPast: true` | Slot has expired |
| `isFuture` | `isFuture: true` | Future slot |
| `isToday` | `isToday: true` | Current day highlight |

---

## Iron Rules

1. **Blueprint-React does NOT have a Calendar component** — always use `@barclays/mca-react-calendar`
2. **Ensure `@barclays/mca-react-calendar` is in `package.json`** — if missing, run `npm install @barclays/mca-react-calendar`
3. **Never build a custom calendar from scratch** — use the official package
4. **Wrap calendar in Blueprint layout** (`Section` + `SectionItem`) for consistent spacing
5. **Data format must match the package API** — convert MCA1 JSON format to the package's expected interface during migration
