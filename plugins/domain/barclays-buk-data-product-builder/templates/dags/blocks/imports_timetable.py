# === BLOCK: imports_timetable ===
# Business Calendar Timetable — include when schedule_type="business_calendar"
IS_CI = os.environ.get("IS_CI", "false").lower() == "true"
timetable = None
if not IS_CI:
    try:
        from business_calendar_file import BusinessCalendarTimetableNextDay
        timetable = BusinessCalendarTimetableNextDay(
            holidays={{HOLIDAY_LIST}},
            hour={{SCHEDULE_HOUR}},
            minute={{SCHEDULE_MINUTE}},
            second=0,
            timezone="Europe/London",
        )
    except Exception:
        timetable = None
# === END BLOCK ===
