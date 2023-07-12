from copy import deepcopy
from datetime import datetime, timedelta

from dateutil.parser import parse
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from icalendar import Calendar, Event, vText, vCalAddress
import pytz
from workalendar.europe import UnitedKingdom as UKBankHolidays

from bookings.appointments import mark_unavailable_slots
from bookings.templatetags.postcodes import format_postcode


MONDAY = 0
TUESDAY = 1
WEDNESDAY = 2
THURSDAY = 3
FRIDAY = 4
SATURDAY = 5
SUNDAY = 6

MIN_HOURS_BEFORE_PICK_UP = 2
MAX_DAYS_PICK_UP = 6
MIN_HOURS_BEFORE_DROP_OFF = 48

WEEKDAY_OPENING_HOUR = 8
WEEKDAY_CLOSING_HOUR = 22
WEEKDAY_LAST_PICK_UP_HOUR = 17

SATURDAY_OPENING_HOUR = 8
SATURDAY_CLOSING_HOUR = 17
SATURDAY_LAST_PICK_UP_HOUR = 14

PICK_UP_PROCEEDING_HOUR = 9


def get_icalendar_str(order):
    cal = Calendar()

    cal.add('ATTENDEE', 'MAILTO:%s' % order.customer.email)
    cal.add('CALSCALE', 'GREGORIAN')
    cal.add('METHOD', 'PUBLISH')
    cal.add('PRODID', '-//Google Inc//Google Calendar 70.9054//EN')
    cal.add('VERSION', '2.0')
    cal.add('X-WR-CALDESC', 'Wishi Washi Order # %s' % order.uuid)
    cal.add('X-WR-TIMEZONE', settings.TIME_ZONE)

    events = ((order.pick_up_time,
               'Wishi Washi will pick up items to clean'),
              (order.drop_off_time,
               'Wishi Washi will deliver cleaned items'))

    _addr = order.pick_up_and_delivery_address

    address = '%s %s, ' % (_addr.flat_number_house_number_building_name,
                           _addr.address_line_1)

    if len(_addr.address_line_2.strip()):
        address += '%s, ' % _addr.address_line_2

    address += 'London, %s' % format_postcode(_addr.postcode)

    organizer = vCalAddress('MAILTO:%s' % settings.FROM_EMAIL_ADDRESS)

    sequence = 0
    url = 'https://%s%s' % (settings.DOMAIN,
                            reverse('bookings:order',
                                    kwargs={'uuid': order.uuid}))

    description = ', '.join(['%s x %d' % (details.item.name, details.quantity)
                            for details in order.items.all()])

    for timeslot, summary in events:
        sequence += 1
        event = Event()
        event.add('CLASS', 'PUBLIC')
        event.add('DESCRIPTION', 'Items to clean: %s' % description)
        event.add('DTEND', timezone.localtime(timeslot + timedelta(hours=1)))
        event.add('DTSTAMP', timeslot) # In UTC
        event.add('DTSTART', timezone.localtime(timeslot))
        event.add('LOCATION', vText(address))
        event.add('ORGANIZER', organizer)
        event.add('SEQUENCE', sequence)
        event.add('STATUS', 'CONFIRMED')
        event.add('SUMMARY', summary)
        event.add('URL', url)
        event.add('UUID', '%s%d' % (order.uuid, sequence))
        cal.add_component(event)

    return cal.to_ical()


def mark_unavailable(calendar_grid, not_before=None, not_after=None):
    """
    :param dict calendar_grid: calender grid dictionaries
    :param object not_before: starting cut off time (datetime object)
    :param object not_after: ending cut off time (datetime object)

    :return: calender grid dictionaries
    :rtype: dict
    """
    tz_london = pytz.timezone(settings.TIME_ZONE)
    for day in calendar_grid:
        for timeslot in day['time_slots']:
            slot_time = tz_london.localize(parse('%s %02d' % (day['date'], int(timeslot['hour']))))

            if not_before:
                if slot_time < not_before:
                    timeslot['available'] = False

            if not_after:
                if slot_time > not_after:
                    timeslot['available'] = False

    return calendar_grid


def remove_weeks_with_no_availability(calendar_grid, start_week=0, end_week=5):
    for week_offset in range(start_week, end_week):
        availability = set()

        # Mon-Sat
        for day_offset in range(MONDAY, SUNDAY):
            for timeslot in calendar_grid[(week_offset * 6) + day_offset]['time_slots']:
                availability.add(timeslot['available'])

        if availability == set([False]):
            # Mon-Sat
            for day_offset in range(MONDAY, SUNDAY):
                calendar_grid[(week_offset * 6) + day_offset] = None

    for week_offset in reversed(range(start_week, end_week)):
        # Mon-Sat
        for day_offset in reversed(range(MONDAY, SUNDAY)):
            if not calendar_grid[(week_offset * 6) + day_offset]:
                del calendar_grid[(week_offset * 6) + day_offset]

    return calendar_grid


def operating_hours(weekly_operating_hours):
    """
    :param list hours_of_operation: indexed by day, value holds dictionary of available time slots

    return list

    Mark hour time slots as available if hour within operating hours.
    """
    for day_index, day in enumerate(weekly_operating_hours):
        if day_index == SATURDAY:
            OPENING_HOUR = SATURDAY_OPENING_HOUR
            CLOSING_HOUR = SATURDAY_CLOSING_HOUR
        else:
            OPENING_HOUR = WEEKDAY_OPENING_HOUR
            CLOSING_HOUR = WEEKDAY_CLOSING_HOUR

        for slot in day:
            hour = int(slot['hour'])
            available = OPENING_HOUR <= hour < CLOSING_HOUR
            slot['available'] = available

    return weekly_operating_hours


def get_starting_monday(weekly_operating_hours):
    # Time in London
    now_london = timezone.localtime(timezone.now())
    hour_london = now_london.hour

    # 0 Mon, 1 Tues, ... 6 Sunday
    day_number = now_london.weekday()
    starting_monday = None

    # If it's Saturday evening or later then start on the next week
    if day_number == SUNDAY:
        starting_monday = now_london + timedelta(days=1)
    elif day_number == SATURDAY:
        last_hour_slot_available = 0

        for _operation_details in weekly_operating_hours[SATURDAY]:
            if _operation_details['available']:
                last_hour_slot_available = max(last_hour_slot_available,
                                               int(_operation_details['hour']))

        # see if it's early enough in day to allow orders for this week
        if hour_london > last_hour_slot_available - MIN_HOURS_BEFORE_PICK_UP:
            starting_monday = now_london + timedelta(days=2)
        else:
            starting_monday = now_london - timedelta(days=5)
    else:
        starting_monday = now_london - timedelta(days=day_number)

    return starting_monday


def build_calendar_grid(weekly_operating_hours, unavailable_day):
    now_london = timezone.localtime(timezone.now())
    hour_london = now_london.hour

    # Build the calendar grid
    calendar_grid = []
    bank_holidays = UKBankHolidays()

    starting_monday = get_starting_monday(weekly_operating_hours)
    assert starting_monday is not None, 'Starting Monday was not set'

    # 5 weeks
    for week_offset in range(0, 5):
        # 6 days (Monday - Saturday)
        for day_offset in range(MONDAY, SUNDAY):
            _day = starting_monday + timedelta(
                days=day_offset + (week_offset * 7))

            day = {
                'month_name': _day.strftime('%B'),  # December, January, etc...
                'day_of_month': int(_day.strftime('%d')),  # 1, 15, 31, etc...
                'day_name': _day.strftime('%A'),  # Monday, etc...
                'date': _day.strftime('%Y-%m-%d'),  # 2015-01-02, etc...
                'time_slots': deepcopy(weekly_operating_hours[day_offset]),
            }

            # Mark whole day as unavailable if it's a bank holiday and
            # remove days which are in the past or more than 28 days into the
            # future
            days_since_today = _day - now_london

            if (day_offset in range(MONDAY, SATURDAY) and bank_holidays.is_working_day(_day) is False):
                day['time_slots'] = deepcopy(unavailable_day)

            if (days_since_today.days < 0 or days_since_today.days > 28):
                day['time_slots'] = deepcopy(unavailable_day)

            # Remove hours that have passed already today
            if _day.date() == now_london.date(): # Today
                for _index, _time_slot in enumerate(day['time_slots']):
                    if int(_time_slot['hour']) < int(hour_london + MIN_HOURS_BEFORE_PICK_UP):
                        day['time_slots'][_index]['available'] = False

            calendar_grid.append(day)
    return calendar_grid


def daterange(start_date, end_date):
    """
    Datetime generator that yields datetimes
    From: (start_date + 1 day) - start of day
    To: end_date - start of day
    """
    start = start_date.replace(hour=0, minute=0, second=0)
    end = end_date.replace(hour=0, minute=0, second=0)

    start = start + timedelta(days=1)
    while start <= end:
        yield start
        start = start + timedelta(days=1)


def pick_up_not_before():
    """
    Monday - Saturday before 8am no pick up before same day 9am.
    Monday - Friday after 5pm no pick up until next day 9am.
    Saturday after 2pm no pick up until next monday @ 9am
    Sunday no pick up until next available monday @ 9am

    Returns a local datetime

    All pick ups must be after this datetime.
    """
    tz_london = pytz.timezone(settings.TIME_ZONE)
    now_london = timezone.localtime(timezone.now())

    # Default minimum pick up time
    not_before = [now_london + timedelta(hours=MIN_HOURS_BEFORE_PICK_UP)]

    delta = None

    # 0 Mon, 1 Tues, ... 6 Sunday
    day_number = now_london.weekday()

    # Monday to Saturday Midnight -> 8am, block out till PICK_UP_PROCEEDING_HOUR
    if MONDAY <= day_number <= SATURDAY and \
            now_london.hour <= WEEKDAY_OPENING_HOUR:
        delta = now_london
    # Monday to Friday WEEKDAY_LAST_PICK_UP_HOUR till midnight, block out till PICK_UP_PROCEEDING_HOUR next day
    elif MONDAY <= day_number <= FRIDAY and \
            now_london.hour >= WEEKDAY_LAST_PICK_UP_HOUR:
        delta = now_london + timedelta(days=1)
    # Saturday after SATURDAY_LAST_PICK_UP_HOUR , block out till Monday at PICK_UP_PROCEEDING_HOUR
    elif day_number == SATURDAY and \
            now_london.hour >= SATURDAY_LAST_PICK_UP_HOUR:
        delta = now_london + timedelta(days=2)
    # Sunday, block out till Monday at PICK_UP_PROCEEDING_HOUR
    elif day_number == SUNDAY:
        delta = now_london + timedelta(days=1)

    if delta:
        not_before.append(
            tz_london.localize(
                datetime(delta.year, delta.month, delta.day,
                         PICK_UP_PROCEEDING_HOUR))
        )

    return max(not_before)


def drop_off_with_inactive_days(pick_up_time, drop_off_time):
    """
    For each sunday and each working day bank holiday
    add 24 hrs to drop off

    Returns a local datetime
    """
    bank_holidays = UKBankHolidays()

    for date in daterange(pick_up_time, drop_off_time):
        # Any day in between that is a Sunday. Add 24hr
        # Mon-Fri and Bank holiday? Add 24hr
        if (date.weekday() == SUNDAY or
            ((MONDAY <= date.weekday() <= FRIDAY)
             and bank_holidays.is_working_day(date) is False)):
            # Add 24 hrs
            following_day = drop_off_time + timedelta(days=1)
            return drop_off_with_inactive_days(
                pick_up_time=date,
                drop_off_time=following_day
            )

    return drop_off_time


def drop_off_not_before(pick_up_time):
    """
    Monday - Saturday there is no drop off before 8am.
    Monday - Friday there is no drop off after 10pm.
    Saturday there is no drop off until following Monday at 8am

    Returns a local datetime

    All drop offs must be after this datetime.
    """
    # Default minimum drop off time
    drop_off_time = pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)

    # Drop off day is not a sunday or bank holiday
    not_before = drop_off_with_inactive_days(pick_up_time, drop_off_time)

    # 0 Mon, 1 Tues, ... 6 Sunday
    day_number = not_before.weekday()

    # Monday to Saturday Midnight -> 8am
    if MONDAY <= day_number <= SATURDAY and \
            not_before.hour < WEEKDAY_OPENING_HOUR:
        not_before = not_before.replace(hour=WEEKDAY_OPENING_HOUR,
                                        minute=0, second=0)
    # Monday to Friday after 10pm, push to next day
    elif MONDAY <= day_number <= FRIDAY and \
            not_before.hour >= WEEKDAY_CLOSING_HOUR:
        delta = not_before.replace(hour=WEEKDAY_OPENING_HOUR, minute=0, second=0)
        not_before = delta + timedelta(days=1)
    # Saturday after 5pm
    elif day_number == SATURDAY and not_before.hour >= SATURDAY_CLOSING_HOUR:
        delta = not_before.replace(hour=WEEKDAY_OPENING_HOUR,
                                   minute=0, second=0)
        # Push out to Monday
        delta = delta + timedelta(days=2)

        # Increase if bank holiday(s)
        not_before = drop_off_with_inactive_days(delta - timedelta(days=1),
                                                 delta)

    return not_before


def get_unavailable_day(hour_start=0, hour_end=24):
    # Build grid of opening hours w/ default of unavailable. This also
    # sets the labels for every day regardless if it's available or not
    unavailable_day = []
    for _hour in range(hour_start, hour_end):
        start = _hour % 12
        start_suffix = 'am' if _hour < 12 else 'pm'

        end = (_hour + 1) % 12
        end_suffix = 'am' if (_hour + 1) < 12 or _hour + 1 == 24 else 'pm'

        if start_suffix == end_suffix:
            start_suffix = ''

        start = 12 if start == 0 else start
        end = 12 if end == 0 else end

        _slot = {
            'available': False,
            # These need to be printed as two characters for parse to be able
            # to parse them, if used as an integer internally then convert to
            # an int first
            'hour': '%02d' % _hour,
            # start_suffix not used, 11am - 12am is too wide
            'label': '%d - %d%s' % (start, end, end_suffix),
        }
        unavailable_day.append(_slot)
    return unavailable_day


def get_calendar(is_pick_up_time=True, out_code=None, pick_up_time=None):
    """
    :param bool is_pick_up_time: toggle for either a pick-up time or delivery time grid
    :param str out_code: User's postcode out code in lower case (i.e. sw7)
    :param object pick_up_time: datetime object of the pick up time

    :return: calender grid dictionaries
    :rtype: dict
    """
    assert out_code is not None
    assert pick_up_time is None if is_pick_up_time else pick_up_time

    # Day marked as unavailable
    unavailable_day = get_unavailable_day(hour_start=WEEKDAY_OPENING_HOUR, hour_end=WEEKDAY_CLOSING_HOUR)

    # Week marked as unavailable Mon-Sat
    weekly_operating_hours = [deepcopy(unavailable_day) for _ in range(MONDAY, SUNDAY)]

    # Mark weekly operating hours as available
    weekly_operating_hours = operating_hours(weekly_operating_hours)

    # Build calendar grid of forthcoming slots for X number of weeks
    calendar_grid = build_calendar_grid(weekly_operating_hours, unavailable_day)

    if is_pick_up_time:
        not_before = pick_up_not_before()
        not_after = timezone.localtime(timezone.now()) + timedelta(days=MAX_DAYS_PICK_UP)
        calendar_grid = mark_unavailable(calendar_grid, not_before=not_before, not_after=not_after)
    else:
        not_before = drop_off_not_before(pick_up_time)
        calendar_grid = mark_unavailable(
            calendar_grid,
            not_before=not_before
        )

    # Check for full slots
    calendar_grid = mark_unavailable_slots(calendar_grid)

    if is_pick_up_time:
        calendar_grid = remove_weeks_with_no_availability(calendar_grid, start_week=1)
    else:
        calendar_grid = remove_weeks_with_no_availability(calendar_grid, start_week=0, end_week=1)

    return calendar_grid


def get_day_and_week_time_slot_lands_on(calendar_grid, selected_date):
    """
    :param dict calendar_grid: calender grid dictionaries
    :param str selected_date: YYYY-MM-DD format

    :return: tuple of week_num and day_num, both integers
    :rtype: tuple
    """
    week_num = 0
    day_num = 0

    for day_index, day in enumerate(calendar_grid):
        if day['date'] == selected_date:
            day_num = day_index
            week_num = day_index / 6
            break

    return (day_num, week_num)
