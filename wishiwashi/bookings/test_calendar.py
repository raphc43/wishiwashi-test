from decimal import Decimal
import datetime
from datetime import timedelta

from django.conf import settings
from django.test import TestCase
from freezegun import freeze_time
import pytz

from bookings.calendar import (get_icalendar_str,
                               get_calendar,
                               operating_hours,
                               mark_unavailable,
                               pick_up_not_before,
                               get_unavailable_day,
                               drop_off_with_inactive_days,
                               drop_off_not_before,
                               daterange,
                               MIN_HOURS_BEFORE_DROP_OFF,
                               WEEKDAY_OPENING_HOUR,
                               WEEKDAY_CLOSING_HOUR)
from bookings.factories import (AddressFactory, OrderFactory, ItemFactory,
                                ItemAndQuantityFactory, UserFactory,
                                TrackConfirmedOrderSlotsFactory)


class Calendar(TestCase):
    def test_get_icalendar_str(self):
        _user = UserFactory(first_name='Mark',
                            last_name='Litwintschik',
                            email='user@soft.com')
        _address = AddressFactory(flat_number_house_number_building_name="887b",
                                  address_line_1='Belvedere Heights',
                                  address_line_2='199 Lisson Grove',
                                  postcode='sw115tg')

        item = ItemFactory(price=Decimal('17.20'), name="Shirt")
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.8'),
                             uuid='012345')
        ical = get_icalendar_str(order)

        expected = [
            'BEGIN:VCALENDAR',
            'VERSION:2.0',
            'PRODID:-//Google Inc//Google Calendar 70.9054//EN',
            'CALSCALE:GREGORIAN',
            'METHOD:PUBLISH',
            'ATTENDEE:MAILTO:user@soft.com',
            'X-WR-CALDESC:Wishi Washi Order # 012345',
            'X-WR-TIMEZONE:Europe/London',

            'BEGIN:VEVENT',
            'SUMMARY:Wishi Washi will pick up items to clean',
            'DTSTART;TZID=Europe/London;'
            'VALUE=DATE-TIME:20140407T110000',
            'DTEND;TZID=Europe/London;VALUE=DATE-TIME:20140407T120000',
            'DTSTAMP;VALUE=DATE-TIME:20140407T100000Z',
            'SEQUENCE:1',
            'CLASS:PUBLIC',
            'DESCRIPTION:Items to clean: Shirt x 4',
            'LOCATION:887b Belvedere Heights\, 199 Lisson Grove\,'
            ' London\, SW11 5TG',
            'ORGANIZER:MAILTO:help@wishiwashi.com',
            'STATUS:CONFIRMED',
            'URL:https://%s/bookings/order/012345' % settings.DOMAIN,
            'UUID:0123451',
            'END:VEVENT',

            'BEGIN:VEVENT',
            'SUMMARY:Wishi Washi will deliver cleaned items',
            'DTSTART;TZID=Europe/London;'
            'VALUE=DATE-TIME:20140410T150000',
            'DTEND;TZID=Europe/London;VALUE=DATE-TIME:20140410T160000',
            'DTSTAMP;VALUE=DATE-TIME:20140410T140000Z',
            'SEQUENCE:2',
            'CLASS:PUBLIC',
            'DESCRIPTION:Items to clean: Shirt x 4',
            'LOCATION:887b Belvedere Heights\, 199 Lisson Grove\, London\, SW11 5TG',
            'ORGANIZER:MAILTO:help@wishiwashi.com',
            'STATUS:CONFIRMED',
            'URL:https://%s/bookings/order/012345' % settings.DOMAIN,
            'UUID:0123452',
            'END:VEVENT',
            'END:VCALENDAR',
            '']

        for index, line in enumerate(ical.split('\r\n')):
            self.assertEqual(expected[index],
                             line,
                             '%d is not %s: %s' % (index,
                                                   expected[index],
                                                   line))


class CalendarHelpers(TestCase):
    def test_get_hours_of_operation_single(self):
        unavailable_day = get_unavailable_day(0, 1)
        expected = [{'available': False,
                     'hour': '%02d' % 0,
                     'label': '%d - %d%s' % (12, 1, 'am')}]
        self.assertEqual(unavailable_day, expected)

    def test_get_hours_of_operation_range(self):
        unavailable_day = get_unavailable_day(12, 14)
        expected = [{'available': False,
                     'hour': '%02d' % 12,
                     'label': '%d - %d%s' % (12, 1, 'pm')},
                    {'available': False,
                     'hour': '%02d' % 13,
                     'label': '%d - %d%s' % (1, 2, 'pm')},
                    ]
        self.assertEqual(unavailable_day, expected)

    def test_mark_unavailable(self):
        calendar_grid = [{'date': '2015-03-06',
                          'time_slots': [{'hour': '08', 'available': False},
                                         {'hour': '09', 'available': True},
                                         {'hour': '10', 'available': True}]},
                         {'date': '2015-03-07',
                          'time_slots': [{'hour': '20', 'available': True},
                                         {'hour': '21', 'available': True},
                                         {'hour': '22', 'available': False}]}]

        expected_grid = [{'date': '2015-03-06',
                          'time_slots': [{'hour': '08', 'available': False},
                                         {'hour': '09', 'available': False},
                                         {'hour': '10', 'available': True}]},
                         {'date': '2015-03-07',
                          'time_slots': [{'hour': '20', 'available': True},
                                         {'hour': '21', 'available': False},
                                         {'hour': '22', 'available': False}]}]

        not_before = datetime.datetime(2015, 3, 6, 10, tzinfo=pytz.utc)
        not_after = datetime.datetime(2015, 3, 7, 20, tzinfo=pytz.utc)

        self.assertEqual(expected_grid, mark_unavailable(calendar_grid,
                                                         not_before,
                                                         not_after))

    def test_mark_unavailable_BST(self):
        calendar_grid = [{'date': '2015-05-06',
                          'time_slots': [{'hour': '08', 'available': False},
                                         {'hour': '09', 'available': True},
                                         {'hour': '10', 'available': True}]},
                         {'date': '2015-05-07',
                          'time_slots': [{'hour': '20', 'available': True},
                                         {'hour': '21', 'available': True},
                                         {'hour': '22', 'available': False}]}]

        expected_grid = [{'date': '2015-05-06',
                          'time_slots': [{'hour': '08', 'available': False},
                                         {'hour': '09', 'available': False},
                                         {'hour': '10', 'available': True}]},
                         {'date': '2015-05-07',
                          'time_slots': [{'hour': '20', 'available': True},
                                         {'hour': '21', 'available': False},
                                         {'hour': '22', 'available': False}]}]

        not_before = datetime.datetime(2015, 5, 6, 9, tzinfo=pytz.utc)
        not_after = datetime.datetime(2015, 5, 7, 19, tzinfo=pytz.utc)

        self.assertEqual(expected_grid, mark_unavailable(calendar_grid,
                                                         not_before,
                                                         not_after))

    def test_operating_hours(self):
        hours_of_operation = [({'hour': '07', 'available': False},
                               {'hour': '08', 'available': False},
                               {'hour': '09', 'available': False},
                               {'hour': '21', 'available': False},
                               {'hour': '22', 'available': False},
                               {'hour': '23', 'available': False}),

                              ({'hour': '07', 'available': False},
                               {'hour': '08', 'available': False},
                               {'hour': '09', 'available': False},
                               {'hour': '21', 'available': False},
                               {'hour': '22', 'available': False},
                               {'hour': '23', 'available': False})]

        expected = [({'hour': '07', 'available': False},
                     {'hour': '08', 'available': True},
                     {'hour': '09', 'available': True},
                     {'hour': '21', 'available': True},
                     {'hour': '22', 'available': False},
                     {'hour': '23', 'available': False}),

                    ({'hour': '07', 'available': False},
                     {'hour': '08', 'available': True},
                     {'hour': '09', 'available': True},
                     {'hour': '21', 'available': True},
                     {'hour': '22', 'available': False},
                     {'hour': '23', 'available': False})]

        self.assertEqual(expected, operating_hours(hours_of_operation))

    @freeze_time("2015-01-05 01:00:00") # Monday morning
    def test_pick_up_not_before_early(self):
        expected = datetime.datetime(2015, 1, 5, 9, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-01-11 01:00:00") # Sunday evening
    def test_pick_up_not_before_early_evening(self):
        expected = datetime.datetime(2015, 1, 12, 9, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-01-04 01:00:00") # Sunday morning
    def test_pick_up_not_before_sunday(self):
        expected = datetime.datetime(2015, 1, 5, 9, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-02-07 01:00:00") # Saturday morning
    def test_pick_up_not_before_saturday_early(self):
        expected = datetime.datetime(2015, 2, 7, 9, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-02-14 13:59:00") # Saturday afternoon
    def test_pick_up_not_before_saturday_early_afternoon(self):
        expected = datetime.datetime(2015, 2, 14, 15, 59, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-02-07 14:01:00") # Saturday late
    def test_pick_up_not_before_saturday_late(self):
        expected = datetime.datetime(2015, 2, 9, 9, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-05-03 10:00:00") # Sunday morning
    def test_pick_up_not_before_sunday_bst(self):
        # BST
        expected = datetime.datetime(2015, 5, 4, 8, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-05-02 09:59:59") # Saturday morning
    def test_pick_up_not_before_saturday_bst(self):
        # BST
        expected = datetime.datetime(2015, 5, 2, 11, 59, 59, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-05-01 16:00:00") # Friday evening
    def test_pick_up_not_before_friday_bst(self):
        # BST
        expected = datetime.datetime(2015, 5, 2, 8, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-05-06 17:00:00") # Wenesday evening
    def test_pick_up_not_before_wednesday_bst(self):
        # BST
        expected = datetime.datetime(2015, 5, 7, 8, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-05-08 02:00:00") # Friday early
    def test_pick_up_not_before_friday_early_bst(self):
        # BST
        expected = datetime.datetime(2015, 5, 8, 8, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    @freeze_time("2015-05-07 09:30:00") # Thursday morning
    def test_pick_up_not_before_default_bst(self):
        # BST
        expected = datetime.datetime(2015, 5, 7, 11, 30, tzinfo=pytz.utc)
        self.assertEqual(expected, pick_up_not_before())

    def test_daterange_generator(self):
        start = datetime.datetime(2015, 5, 7, 21, 30, tzinfo=pytz.utc)
        end = datetime.datetime(2015, 5, 14, 15, 30, tzinfo=pytz.utc)

        start = start.replace(hour=0, minute=0, second=0)
        expected = [start + timedelta(days=n+1) for n in range(7)]
        result = list(daterange(start, end))
        self.assertEqual(result, expected)

        expected_end = datetime.datetime(2015, 5, 14, tzinfo=pytz.utc)
        self.assertEqual(result[-1], expected_end)

        expected_start = datetime.datetime(2015, 5, 8, tzinfo=pytz.utc)
        self.assertEqual(result[0], expected_start)

    def test_drop_off_with_inactive_days_default(self):
        # Monday (default applied)
        pick_up_time = datetime.datetime(2015, 5, 4, 21, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_friday(self):
        # Friday (1 extra day for the sunday)
        pick_up_time = datetime.datetime(2015, 5, 8, 21, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=1, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_extra_saturday(self):
        # Saturday pick up then 1 extra day for the sunday + 1 extra for Bank holiday
        # monday
        pick_up_time = datetime.datetime(2015, 4, 4, 16, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=2, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_saturday(self):
        # Saturday (1 extra day for the sunday)
        pick_up_time = datetime.datetime(2015, 5, 9, 15, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=1, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_thursday(self):
        # Thursday - default applied
        pick_up_time = datetime.datetime(2015, 5, 21, 10, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_bank_holidays(self):
        # Thursday before Bank Holiday Friday 3rd Apil and Monday 6th April
        # (3 days extra - Bank Holiday Friday and Monday and Sunday)
        pick_up_time = datetime.datetime(2015, 4, 2, 10, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=3, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_bank_holiday_may(self):
        # Monday 25th May 2015 (2 days - skip sunday and Bank Holiday Monday)
        pick_up_time = datetime.datetime(2015, 5, 23, 10, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=2, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_bank_holiday_new_year(self):
        # Friday 1st 2016 Bank Holiday
        pick_up_time = datetime.datetime(2015, 12, 31, 10, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=2, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_with_inactive_days_new_year(self):
        # Saturday 2nd 2016
        pick_up_time = datetime.datetime(2016, 1, 2, 10, 30, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=1, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected,
                         drop_off_with_inactive_days(
                             pick_up_time,
                             pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
                         ))

    def test_drop_off_not_before_saturday(self):
        # Saturday 9th 2016 (1 day increase for Sunday)
        # Pre 8am - push up to 8am that day
        pick_up_time = datetime.datetime(2016, 1, 9, 9, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=1, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_friday(self):
        # Friday 8th 2016 (1 day increase for Sunday)
        pick_up_time = datetime.datetime(2016, 1, 8, 20, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=1, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_tuesday(self):
        # Tuesday 12th 2016 (no day increase)
        pick_up_time = datetime.datetime(2016, 1, 12, 20, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_saturday_with_bank_holiday(self):
        # Saturday 2nd 2015 (2 day increase for Sunday and bank holiday)
        pick_up_time = datetime.datetime(2015, 5, 2, 9, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=2,
                                            hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_tuesday_early_opening(self):
        pick_up_time = datetime.datetime(2015, 3, 10, 9, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_thursday_post_closing(self):
        # Push out to following Monday @ 8am
        pick_up_time = datetime.datetime(2015, 3, 19, 22, tzinfo=pytz.utc)
        expected = datetime.datetime(2015, 3, 23, WEEKDAY_OPENING_HOUR, tzinfo=pytz.utc)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_friday_post_closing(self):
        # Skip Sunday - push out to following Monday
        pick_up_time = datetime.datetime(2015, 3, 20, 21, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=1, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    def test_drop_off_not_before_thursday_post_closing_with_bank_holidays(self):
        # Push out by 3 days to @ 8am
        # Friday 1st bank holiday, Sunday and 4th Bank holiday
        pick_up_time = datetime.datetime(2015, 4, 30, 22, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=3, hours=MIN_HOURS_BEFORE_DROP_OFF)
        expected = expected.replace(hour=WEEKDAY_OPENING_HOUR,
                                    minute=0,
                                    second=0)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    @freeze_time("2015-04-04 10:00:00") # Saturday
    def test_drop_off_not_before_saturday_extra_day(self):
        # Push out extra day (Sunday)
        # Push out extra day for 6th April 2015 (Monday bank holiday)
        pick_up_time = datetime.datetime(2015, 4, 4, 16, tzinfo=pytz.utc)
        expected = pick_up_time + timedelta(days=2, hours=MIN_HOURS_BEFORE_DROP_OFF)
        self.assertEqual(expected, drop_off_not_before(pick_up_time))

    @freeze_time("2015-04-04 15:00:00") # Saturday
    def test_calendar_grid_pick_up_saturday_plus_extra_day(self):
        # Push out extra day for 6th April 2015 (Monday bank holiday)
        calendar_grid = get_calendar(is_pick_up_time=True, out_code='sw11')

        # Monday unavailable
        # Tuesday available
        check = {
            '2015-04-06': [(hour, False) for hour in range(WEEKDAY_OPENING_HOUR, WEEKDAY_CLOSING_HOUR)],
            '2015-04-07': [WEEKDAY_OPENING_HOUR, False] + [(hour, True)
                                                           for hour in range(WEEKDAY_OPENING_HOUR + 1,
                                                                             WEEKDAY_CLOSING_HOUR)]
        }

        for day in calendar_grid:
            if day['date'] in check:
                for timeslot in day['time_slots']:
                    availability = [(int(timeslot['hour']), timeslot['available']) for timeslot in day['time_slots']]
                    self.assertEqual(availability, check[day['date']])
                break
        else:
            raise Exception('Day not found')

    @freeze_time("2015-03-19 01:00:00")
    def test_get_calendar_max_slot_hit(self):
        pick_up_time = datetime.datetime(2015, 3, 20, 21, tzinfo=pytz.utc)

        slot_taken = datetime.datetime(2015, 3, 25, 10, tzinfo=pytz.utc)

        # Book out slot
        TrackConfirmedOrderSlotsFactory(appointment=slot_taken, counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        check = {'2015-03-25':
                 [(8, True), (9, True), (10, False), (11, True),
                  (12, True), (13, True), (14, True), (15, True),
                  (16, True), (17, True), (18, True), (19, True),
                  (20, True), (21, True)]}

        calendar_grid = get_calendar(False, 'w1', pick_up_time)

        for day in calendar_grid:
            if day['date'] in check:
                for timeslot in day['time_slots']:
                    availability = [(int(timeslot['hour']), timeslot['available']) for timeslot in day['time_slots']]
                    self.assertEqual(availability, check[day['date']])
                break
        else:
            raise Exception('Day not found')

    @freeze_time("2014-05-19 01:00:00")
    def test_get_calendar_max_slot_hit_BST(self):
        pick_up_time = datetime.datetime(2014, 5, 20, 21, tzinfo=pytz.utc)

        slot_taken = datetime.datetime(2014, 5, 23, 10, tzinfo=pytz.utc)

        # Book out slot
        TrackConfirmedOrderSlotsFactory(
            appointment=slot_taken,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        check = {'2014-05-23':
                 [(8, True), (9, True), (10, True), (11, False),
                  (12, True), (13, True), (14, True), (15, True),
                  (16, True), (17, True), (18, True), (19, True),
                  (20, True), (21, True)]}

        calendar_grid = get_calendar(False, 'w1', pick_up_time)

        for day in calendar_grid:
            if day['date'] in check:
                for timeslot in day['time_slots']:
                    availability = [(int(timeslot['hour']), timeslot['available']) for timeslot in day['time_slots']]
                    self.assertEqual(availability, check[day['date']])
                break
        else:
            raise Exception('Day not found')

