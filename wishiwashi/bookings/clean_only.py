from datetime import timedelta
from workalendar.europe import UnitedKingdom as UKBankHolidays


def pre_working_day(drop_off_time):
    """
    pick_up_time is a datetime
    day = Monday is 0 Sunday is 6
    A working day for Wishi Washi is Mon-Sat
    if day is Monday: return Saturday, otherwise: return previous working day (non bank holiday)
    """
    bank_holidays = UKBankHolidays()
    if drop_off_time.weekday() == 0:
        # Saturday
        return drop_off_time - timedelta(days=2)
    else:
        # Previous day
        previous_day = drop_off_time - timedelta(days=1)
        while True:
            # Sunday or a non bank holiday working day
            if previous_day.weekday() == 5 or bank_holidays.is_working_day(previous_day) is True:
                return previous_day
            else:
                # Step back another day
                previous_day = previous_day - timedelta(days=1)


def expected_back(drop_off_time):
    """
    When does the order need to be back with us ready for delivery.

    Any order to be delivered back pre 2PM - must be ready pre working day PM
    Any order to be delivered back post 2PM - must be ready same day AM

    AM = Set time to Noon
    PM = Set time to 5PM

    """
    if drop_off_time.hour < 14:
        return pre_working_day(drop_off_time).replace(hour=17, minute=0, second=0)

    return drop_off_time.replace(hour=12, minute=0, second=0)


def drop_off_time_to_ready_time(drop_off_time):
    """
    Return: Day DD Mon AM/PM  # Wed 04 Jun PM
    """
    fmt = "%a %d %b {}"
    expected_back_dt = expected_back(drop_off_time)

    if expected_back_dt.hour == 12:
        return expected_back_dt.strftime(fmt.format("AM"))
    else:
        return expected_back_dt.strftime(fmt.format("PM"))


