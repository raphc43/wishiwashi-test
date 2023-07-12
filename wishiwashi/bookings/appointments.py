import datetime
from collections import defaultdict

from dateutil.parser import parse
from django.conf import settings
import pytz

from bookings.models import TrackConfirmedOrderSlots


def appointment_slot_available(appointment):
    """
    :param appointment: datetime object

    :return: boolean

    If slot is available return True otherwise False
    """
    try:
        slot = TrackConfirmedOrderSlots.objects.get(appointment=appointment)

        return slot.counter < settings.MAX_APPOINTMENTS_PER_HOUR
    except TrackConfirmedOrderSlots.DoesNotExist:
        return True


def appointment_slot_available_session(session_appointment):
    """
    :param session_appointment: str object

    str format of slot in local timezone date with beginning of hour
    Example: u'2015-03-18 08'

    :return: boolean

    If slot is available return True otherwise False
    """
    try:
        year, month, day_hour = session_appointment.split("-")
        day, hour = day_hour.split()
    except (ValueError, AttributeError):
        return False

    # Session stored in localtime
    tz_local = pytz.timezone(settings.TIME_ZONE)

    try:
        appointment = tz_local.localize(
            datetime.datetime(int(year), int(month), int(day), int(hour))
        )
    except ValueError:
        return False

    return appointment_slot_available(appointment)


def slots_taken(min_date, max_date):
    """
    :param datetime min_date: min datetime to use
    :param datetime max_date: max datetime to use


    :return:  dictionary

    Dictionary keys str in localtime "%Y-%m-%d"
    Value is list of hours (ints) at full capacity
    """
    slots_taken = defaultdict(list)
    tz_local = pytz.timezone(settings.TIME_ZONE)

    for slot in TrackConfirmedOrderSlots.objects.filter(
            appointment__gte=min_date,
            appointment__lte=max_date,
            counter__gte=settings.MAX_APPOINTMENTS_PER_HOUR):
        local_time = slot.appointment.astimezone(tz_local)
        slots_taken[local_time.strftime("%Y-%m-%d")].append(local_time.hour)

    return slots_taken


def min_max_dates_for_calendar(calendar_grid):
    tz_local = pytz.timezone(settings.TIME_ZONE)

    # Beginning of day
    min_date = min([tz_local.localize(parse(day['date']))
                    for day in calendar_grid])

    max_date = max([tz_local.localize(parse(day['date']))
                    for day in calendar_grid])

    # End of day
    max_date = max_date.replace(hour=23, minute=59, second=59)

    return min_date, max_date


def mark_unavailable_slots(calendar_grid):
    """
    :param list calendar_grid: contains dictionary of each day

    Example of dictionary in calendar_grid list:

    {'date': '2015-03-20',
    'day_name': 'Friday',
    'day_of_month': 20,
    'month_name': 'March',
    'time_slots': [{'available': True, 'hour': '08', 'label': '8 - 9am'},
                    {'available': True, 'hour': '09', 'label': '9 - 10am'},
                    {'available': True, 'hour': '10', 'label': '10 - 11am'},
                    {'available': True, 'hour': '11', 'label': '11 - 12pm'},
                    {'available': True, 'hour': '12', 'label': '12 - 1pm'},
                    {'available': True, 'hour': '13', 'label': '1 - 2pm'},
                    {'available': True, 'hour': '14', 'label': '2 - 3pm'},
                    {'available': True, 'hour': '15', 'label': '3 - 4pm'},
                    {'available': True, 'hour': '16', 'label': '4 - 5pm'},
                    {'available': True, 'hour': '17', 'label': '5 - 6pm'},
                    {'available': True, 'hour': '18', 'label': '6 - 7pm'},
                    {'available': True, 'hour': '19', 'label': '7 - 8pm'},
                    {'available': True, 'hour': '20', 'label': '8 - 9pm'},
                    {'available': True, 'hour': '21', 'label': '9 - 10pm'},
                    {'available': True, 'hour': '22', 'label': '10 - 11pm'}]}]

    return list
    """
    min_date, max_date = min_max_dates_for_calendar(calendar_grid)

    unavailable_slots = slots_taken(min_date, max_date)
    if not unavailable_slots:
        return calendar_grid

    for day in calendar_grid:
        date = day['date']
        if date in unavailable_slots:
            for slot in day['time_slots']:
                hour = int(slot['hour'])
                if hour in unavailable_slots[date]:
                    slot['available'] = False

    return calendar_grid


