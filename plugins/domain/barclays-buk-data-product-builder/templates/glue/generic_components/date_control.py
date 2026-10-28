import boto3
import datetime
from dateutil.relativedelta import relativedelta
from pandas.tseries.offsets import BDay

__all__ = ['date_control', 'read_from_s3', 'write_to_s3']

s3 = boto3.resource('s3')
s3_client = boto3.client('s3')

# UK bank holidays (2023-2050) used to skip non-trading days
_UK_BANK_HOLIDAYS = frozenset([
    '2023-01-02','2023-04-07','2023-04-10','2023-05-01','2023-05-08','2023-05-29',
    '2023-08-28','2023-12-25','2023-12-26','2024-01-01','2024-03-29','2024-04-01',
    '2024-05-06','2024-05-27','2024-08-26','2024-12-25','2024-12-26','2025-01-01',
    '2025-04-18','2025-04-21','2025-05-05','2025-05-26','2025-08-25','2025-12-25',
    '2025-12-26','2026-01-01','2026-04-03','2026-04-06','2026-05-04','2026-05-25',
    '2026-08-31','2026-12-25','2026-12-28','2027-01-01','2027-03-26','2027-03-29',
    '2027-05-03','2027-05-31','2027-08-30','2027-12-27','2027-12-28','2028-01-03',
    '2028-04-14','2028-04-17','2028-05-01','2028-05-29','2028-08-28','2028-12-25',
    '2028-12-26','2029-01-01','2029-03-30','2029-04-02','2029-05-07','2029-05-28',
    '2029-08-27','2029-12-25','2029-12-26','2030-01-01','2030-04-19','2030-04-22',
    '2030-05-06','2030-05-27','2030-08-26','2030-12-25','2030-12-26','2031-01-01',
    '2031-04-11','2031-04-14','2031-05-05','2031-05-26','2031-08-25','2031-12-25',
    '2031-12-26','2032-01-01','2032-03-26','2032-03-29','2032-05-03','2032-05-31',
    '2032-08-30','2032-12-27','2032-12-28','2033-01-03','2033-04-15','2033-04-18',
    '2033-05-02','2033-05-30','2033-08-29','2033-12-26','2033-12-27','2034-01-02',
    '2034-04-07','2034-04-10','2034-05-01','2034-05-29','2034-08-28','2034-12-25',
    '2034-12-26','2035-01-01','2035-03-23','2035-03-26','2035-05-07','2035-05-28',
    '2035-08-27','2035-12-25','2035-12-26','2036-01-01','2036-04-11','2036-04-14',
    '2036-05-05','2036-05-26','2036-08-25','2036-12-25','2036-12-26','2037-01-01',
    '2037-04-03','2037-04-06','2037-05-04','2037-05-25','2037-08-31','2037-12-25',
    '2037-12-28','2038-01-01','2038-04-23','2038-04-26','2038-05-03','2038-05-31',
    '2038-08-30','2038-12-27','2038-12-28','2039-01-03','2039-04-08','2039-04-11',
    '2039-05-02','2039-05-30','2039-08-29','2039-12-26','2039-12-27','2040-01-02',
    '2040-03-30','2040-04-02','2040-05-07','2040-05-28','2040-08-27','2040-12-25',
    '2040-12-26','2041-01-01','2041-04-19','2041-04-22','2041-05-06','2041-05-27',
    '2041-08-26','2041-12-25','2041-12-26','2042-01-01','2042-04-04','2042-04-07',
    '2042-05-05','2042-05-26','2042-08-25','2042-12-25','2042-12-26','2043-01-01',
    '2043-03-27','2043-03-30','2043-05-04','2043-05-25','2043-08-31','2043-12-25',
    '2043-12-28','2044-01-01','2044-04-15','2044-04-18','2044-05-02','2044-05-30',
    '2044-08-29','2044-12-26','2044-12-27','2045-01-02','2045-04-07','2045-04-10',
    '2045-05-01','2045-05-29','2045-08-28','2045-12-25','2045-12-26','2046-01-01',
    '2046-03-23','2046-03-26','2046-05-07','2046-05-28','2046-08-27','2046-12-25',
    '2046-12-26','2047-01-01','2047-04-12','2047-04-15','2047-05-06','2047-05-27',
    '2047-08-26','2047-12-25','2047-12-26','2048-01-01','2048-04-03','2048-04-06',
    '2048-05-04','2048-05-25','2048-08-31','2048-12-25','2048-12-28','2049-01-01',
    '2049-04-16','2049-04-19','2049-05-03','2049-05-31','2049-08-30','2049-12-27',
    '2049-12-28','2050-01-03','2050-04-08','2050-04-11','2050-05-02','2050-05-30',
    '2050-08-29','2050-12-26','2050-12-27',
])


def read_from_s3(bucket_name, filename):
    response1 = s3_client.get_object(Bucket=bucket_name, Key=filename)
    return response1


def write_to_s3(bucket_name, filename, content):
    s3_client.put_object(Bucket=bucket_name, Key=filename, Body=content)


class _DateControlLogic:
    """Internal engine that computes and writes the next date-control triplet."""

    def __init__(self, config, direction="forward"):
        self._direction = direction
        self._filename = config['filename']
        self._file_path = config['file_path']
        self._frequency = config['frequency']
        self._backup_filename = config['backup_filename']
        _wdm = config.get('workday_number_monthly', '')
        self._workday_number_monthly = int(_wdm) - 1 if _wdm else 0

        _wdw = config.get('workday_number_weekly', '')
        self._workday_number_weekly = int(_wdw) if _wdw else 0
        self._run_on_weekends = config['run_on_weekends']
        self._run_on_bank_holidays = config['run_on_bank_holidays']

        # Read current state from S3 and create backup
        content = read_from_s3(self._file_path, self._filename)
        file_contents = content['Body'].read().decode('utf-8')
        write_to_s3(self._file_path, self._backup_filename, file_contents)

        # Parse the current date (middle field of prev|curr|next)
        date_file = file_contents.split('|')
        date_to_be_replaced = date_file[1]
        self._date_daily = datetime.datetime.strptime(date_to_be_replaced, "%Y%m%d")
        self._date_daily_dt = self._date_daily.strftime('%Y-%m-%d')

    # ── Helper methods ────────────────────────────────────────────────────

    def _write_result(self, curr_dt, nxt_dt, future_dt):
        """Format triplet as YYYYMMDD|YYYYMMDD|YYYYMMDD, write to S3, return next date string."""
        content = curr_dt.strftime("%Y%m%d") + '|' + nxt_dt.strftime("%Y%m%d") + '|' + future_dt.strftime("%Y%m%d")
        write_to_s3(self._file_path, self._filename, content)
        return content.split('|')[1]

    def _skip_holiday_nxt_future(self, nxt_dt, future_dt, nxt_step_fn, future_step_fn):
        """Single-pass bank-holiday skip for next and future dates (preserves original semantics)."""
        if self._run_on_bank_holidays == 'N':
            nxt_str = nxt_dt.strftime("%Y-%m-%d")
            if nxt_str in _UK_BANK_HOLIDAYS:
                print(nxt_str)
                print("bank_holidays")
                nxt_dt, future_dt = nxt_step_fn(nxt_dt, future_dt)
            future_str = future_dt.strftime("%Y-%m-%d")
            if future_str in _UK_BANK_HOLIDAYS:
                print(future_str)
                future_dt = future_step_fn(future_dt)
        return nxt_dt, future_dt

    def _next_weekday(self, d, weekday):
        """Return the next occurrence of a given weekday (0=Mon, 6=Sun)."""
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0:
            days_ahead += 7
        return d + datetime.timedelta(days_ahead)

    # ── Frequency computation methods ─────────────────────────────────────

    def _compute_daily(self):
        if self._direction == "forward":
            nxt_dt = self._date_daily + datetime.timedelta(days=1)
            future_dt = self._date_daily + datetime.timedelta(days=2)

            if self._run_on_bank_holidays == 'N':
                nxt_str = nxt_dt.strftime("%Y-%m-%d")
                if nxt_str in _UK_BANK_HOLIDAYS:
                    print(nxt_str)
                    print("Daily excluding bank_holidays")
                    nxt_dt = nxt_dt + datetime.timedelta(days=1)
                    future_dt = nxt_dt + datetime.timedelta(days=1)
                future_str = future_dt.strftime("%Y-%m-%d")
                if future_str in _UK_BANK_HOLIDAYS:
                    print(future_str)
                    future_dt = future_dt + datetime.timedelta(days=1)

            return self._write_result(self._date_daily, nxt_dt, future_dt)
        else:
            # Reverse: decrement dates
            prev_dt = self._date_daily - datetime.timedelta(days=1)
            second_prev_dt = self._date_daily - datetime.timedelta(days=2)
            content = second_prev_dt.strftime("%Y%m%d") + '|' + prev_dt.strftime("%Y%m%d") + '|' + self._date_daily.strftime("%Y%m%d")
            write_to_s3(self._file_path, self._filename, content)
            return content.split('|')[1]

    def _compute_working_days(self):
        nxt_dt = self._date_daily + BDay(1)
        future_dt = nxt_dt + BDay(1)

        def nxt_step(n, f):
            n = n + BDay(1)
            f = n + BDay(1)
            return n, f

        def future_step(f):
            return f + BDay(1)

        nxt_dt, future_dt = self._skip_holiday_nxt_future(nxt_dt, future_dt, nxt_step, future_step)
        return self._write_result(self._date_daily, nxt_dt, future_dt)

    def _compute_monthly_once(self):
        dt_nxt_month = (self._date_daily.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        if dt_nxt_month.weekday() == 5:
            dt_nxt_month = dt_nxt_month + BDay(1)
        elif dt_nxt_month.weekday() == 6:
            dt_nxt_month = dt_nxt_month + BDay(1)
        date_workday_nm = dt_nxt_month + BDay(self._workday_number_monthly)

        dt_future_month = (self._date_daily.replace(day=1) + datetime.timedelta(days=64)).replace(day=1)
        if dt_future_month.weekday() == 5:
            dt_future_month = dt_future_month + BDay(1)
        elif dt_future_month.weekday() == 6:
            dt_future_month = dt_future_month + BDay(1)
        date_workday_fm = dt_future_month + BDay(self._workday_number_monthly)

        if self._run_on_bank_holidays == 'N':
            nxt_str = date_workday_nm.strftime("%Y-%m-%d")
            if nxt_str in _UK_BANK_HOLIDAYS:
                print(nxt_str)
                print("Monthly once excluding weekends and bank_holidays")
                date_workday_nm = date_workday_nm + BDay(1)
            future_str = date_workday_fm.strftime("%Y-%m-%d")
            if future_str in _UK_BANK_HOLIDAYS:
                print(future_str)
                date_workday_fm = date_workday_fm + BDay(1)

        return self._write_result(self._date_daily, date_workday_nm, date_workday_fm)

    def _compute_monthly_once_wkend(self):
        dt_nxt_month = (self._date_daily.replace(day=1) + datetime.timedelta(days=32)).replace(day=1)
        date_workday_nm = dt_nxt_month + datetime.timedelta(days=self._workday_number_monthly)

        dt_future_month = (self._date_daily.replace(day=1) + datetime.timedelta(days=64)).replace(day=1)
        date_workday_fm = dt_future_month + datetime.timedelta(days=self._workday_number_monthly)

        if self._run_on_bank_holidays == 'N':
            nxt_str = date_workday_nm.strftime("%Y-%m-%d")
            if nxt_str in _UK_BANK_HOLIDAYS:
                print(nxt_str)
                print("Monthly once excluding weekends and bank_holidays")
                date_workday_nm = date_workday_nm + datetime.timedelta(days=1)
            future_str = date_workday_fm.strftime("%Y-%m-%d")
            if future_str in _UK_BANK_HOLIDAYS:
                print(future_str)
                date_workday_fm = date_workday_fm + datetime.timedelta(days=1)

        return self._write_result(self._date_daily, date_workday_nm, date_workday_fm)

    def _compute_weekly_once(self):
        next_sunday = self._next_weekday(self._date_daily, 6)
        dt_nxt_week_nw = next_sunday + datetime.timedelta(days=self._workday_number_weekly)
        dt_future_week_fw = dt_nxt_week_nw + datetime.timedelta(days=7)

        if self._run_on_bank_holidays == 'N':
            nxt_str = dt_nxt_week_nw.strftime("%Y-%m-%d")
            if nxt_str in _UK_BANK_HOLIDAYS:
                print(nxt_str)
                print("Weekly once excluding bank_holidays")
                dt_nxt_week_nw = dt_nxt_week_nw + datetime.timedelta(days=1)
            future_str = dt_future_week_fw.strftime("%Y-%m-%d")
            if future_str in _UK_BANK_HOLIDAYS:
                print(future_str)
                dt_future_week_fw = dt_future_week_fw + datetime.timedelta(days=1)

        return self._write_result(self._date_daily, dt_nxt_week_nw, dt_future_week_fw)

    def _compute_alternate_days(self):
        nxt_dt = self._date_daily + BDay(2)
        if nxt_dt.weekday() == 4:
            future_dt = nxt_dt + BDay(1)
        else:
            future_dt = nxt_dt + BDay(2)

        if self._run_on_bank_holidays == 'N':
            nxt_str = nxt_dt.strftime("%Y-%m-%d")
            if nxt_str in _UK_BANK_HOLIDAYS:
                print(nxt_str)
                print("bank_holidays")
                nxt_dt = future_dt
                future_dt = nxt_dt + BDay(2)
            future_str = future_dt.strftime("%Y-%m-%d")
            if future_str in _UK_BANK_HOLIDAYS:
                print(future_str)
                future_dt = future_dt + BDay(2)

        return self._write_result(self._date_daily, nxt_dt, future_dt)

    def _compute_alternate_days_wkend(self):
        nxt_dt = self._date_daily + datetime.timedelta(days=2)
        future_dt = nxt_dt + datetime.timedelta(days=2)

        if self._run_on_bank_holidays == 'N':
            nxt_str = nxt_dt.strftime("%Y-%m-%d")
            if nxt_str in _UK_BANK_HOLIDAYS:
                print(nxt_str)
                print("bank_holidays")
                nxt_dt = future_dt
                future_dt = nxt_dt + datetime.timedelta(days=2)
            future_str = future_dt.strftime("%Y-%m-%d")
            if future_str in _UK_BANK_HOLIDAYS:
                print(future_str)
                future_dt = future_dt + datetime.timedelta(days=2)

        return self._write_result(self._date_daily, nxt_dt, future_dt)

    def _compute_tue_to_sat(self):
        nxt_dt = self._date_daily + datetime.timedelta(days=1)
        if nxt_dt.weekday() == 6:
            nxt_dt = nxt_dt + datetime.timedelta(days=2)
            future_dt = nxt_dt + datetime.timedelta(days=1)
        future_dt = nxt_dt + datetime.timedelta(days=1)

        if self._run_on_bank_holidays == 'N':
            for i in _UK_BANK_HOLIDAYS:
                nxt_str = nxt_dt.strftime("%Y-%m-%d")
                if nxt_str in _UK_BANK_HOLIDAYS:
                    print(nxt_str)
                    print("Daily excluding bank_holidays")
                    nxt_dt = nxt_dt + datetime.timedelta(days=1)
                    if nxt_dt.weekday() == 6:
                        nxt_dt = nxt_dt + datetime.timedelta(days=2)
                        future_dt = nxt_dt + datetime.timedelta(days=1)
                    else:
                        future_dt = nxt_dt + datetime.timedelta(days=1)
                future_str = future_dt.strftime("%Y-%m-%d")
                if future_str in _UK_BANK_HOLIDAYS:
                    print(future_str)
                    future_dt = future_dt + datetime.timedelta(days=1)

        return self._write_result(self._date_daily, nxt_dt, future_dt)

    # ── Dispatch ──────────────────────────────────────────────────────────

    def run(self):
        """Route to the appropriate frequency method and return the next date string."""
        freq = self._frequency.lower()

        if freq == 'daily':
            print("Daily")
            current_date = self._compute_daily()
            print("Date Control File updated")
        elif freq == 'working_days':
            print("working_days")
            current_date = self._compute_working_days()
            print("Date Control file updated")
        elif freq == 'once_a_month':
            if self._run_on_weekends == 'N':
                print("Monthly once excluding weekends")
                current_date = self._compute_monthly_once()
                print("Date Control file updated")
            elif self._run_on_weekends == 'Y':
                print("Monthly once including weekends")
                current_date = self._compute_monthly_once_wkend()
                print("Date Control file updated")
        elif freq == 'weekly_once':
            print("Weekly once")
            current_date = self._compute_weekly_once()
            print("Date Control file updated")
        elif freq == 'alternate_days':
            if self._run_on_weekends == 'N':
                print("Alternate days excluding weekends")
                current_date = self._compute_alternate_days()
                print("Date Control file updated")
            elif self._run_on_weekends == 'Y':
                print("Alternate days including weekends")
                current_date = self._compute_alternate_days_wkend()
                print("Date Control file updated")
        elif freq == 'tue_to_sat':
            print("Tuesday to Saturday")
            current_date = self._compute_tue_to_sat()
            print("Date Control file updated")

        return current_date


class date_control:
    def __init__(self, config):
        self.config = config

    def update_date_control(self):
        logic_obj = _DateControlLogic(self.config, direction="forward")
        current_date = logic_obj.run()
        return current_date

    # reverse date control only works for daily run scenarios not for any other scenarios.
    def reverse_date_control(self):
        reverse_logic_obj = _DateControlLogic(self.config, direction="reverse")
        current_date = reverse_logic_obj.run()
        return current_date

    def retrieve_date(self):
        content = read_from_s3(self.config['file_path'], self.config['filename'])
        file_contents = content['Body'].read().decode('utf-8')

        date_file = file_contents.split('|')

        previous_business_date = date_file[0]
        current_business_date = date_file[1]
        next_business_date = date_file[2]
        return previous_business_date, current_business_date, next_business_date
