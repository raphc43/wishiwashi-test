import datetime

from dateutil.parser import parse
from django.conf import settings
from django.test import TestCase
import pytz

from bookings.appointments import (appointment_slot_available,
                                   appointment_slot_available_session,
                                   mark_unavailable_slots,
                                   min_max_dates_for_calendar,
                                   slots_taken)
from bookings.factories import TrackConfirmedOrderSlotsFactory


class Appointment(TestCase):
    maxDiff = None

    def setUp(self):
        self.appointment = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        self.appointment_session = u"2014-04-07 11"

    def test_appointment_slot_available_valid(self):
        TrackConfirmedOrderSlotsFactory(
            appointment=self.appointment,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 1)
        self.assertTrue(appointment_slot_available(self.appointment))

    def test_appointment_slot_available_new(self):
        self.assertTrue(appointment_slot_available(self.appointment))

    def test_appointment_slot_available(self):
        TrackConfirmedOrderSlotsFactory(
            appointment=self.appointment,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        self.assertFalse(appointment_slot_available(self.appointment))

    def test_appointment_slot_available_from_session_valid(self):
        TrackConfirmedOrderSlotsFactory(
            appointment=self.appointment,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 1)
        self.assertTrue(appointment_slot_available_session(
            self.appointment_session))

    def test_appointment_slot_available_from_session_max(self):
        TrackConfirmedOrderSlotsFactory(
            appointment=self.appointment,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)
        self.assertFalse(appointment_slot_available_session(
            self.appointment_session))

    def test_appointment_slot_available_from_session_invalid(self):
        self.assertFalse(appointment_slot_available_session(
            u"2015-02-30 10"))

    def test_min_max_dates_for_calendar(self):
        dates = [{'date': '2015-03-21'},
                 {'date': '2015-03-20'},
                 {'date': '2015-02-21'}]

        tz_local = pytz.timezone(settings.TIME_ZONE)
        min_date = tz_local.localize(parse('2015-02-21'))
        max_date = tz_local.localize(parse('2015-03-21'))
        max_date = max_date.replace(hour=23, minute=59, second=59)
        self.assertEqual((min_date, max_date),
                         min_max_dates_for_calendar(dates))

    def test_appointment_slots_taken(self):
        appointment1 = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment1,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        appointment2 = datetime.datetime(2014, 4, 7, 16, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment2,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        appointment3 = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment3,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        # Localtime + 1 hour
        expected = {"2014-04-07": [11, 17],
                    "2014-04-08": [11]}

        min_date = appointment1.replace(hour=0)
        max_date = appointment3.replace(hour=23)

        self.assertEqual(expected, slots_taken(min_date, max_date))

    def test_appointment_not_slots_taken(self):
        appointment1 = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment1,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        # Single slot remaining
        appointment2 = datetime.datetime(2014, 4, 7, 16, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment2,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 1)

        appointment3 = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment3,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        # Localtime + 1 hour
        expected = {"2014-04-07": [11],
                    "2014-04-08": [11]}

        min_date = appointment1.replace(hour=0)
        max_date = appointment3.replace(hour=23)

        self.assertEqual(expected, slots_taken(min_date, max_date))

    def test_appointment_all_slots_available(self):
        appointment1 = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment1,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 2)

        # Single slot remaining
        appointment2 = datetime.datetime(2014, 4, 7, 16, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment2,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 1)

        appointment3 = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment3,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 4)

        expected = {}

        min_date = appointment1.replace(hour=0)
        max_date = appointment3.replace(hour=23)

        self.assertEqual(expected, slots_taken(min_date, max_date))

    def test_appointment_slot_unavailble_calendar_grid(self):
        calendar_grid = [{'date': '2015-03-16',
            'day_name': 'Monday',
            'day_of_month': 16,
            'month_name': 'March',
            'time_slots': [{'available': False, 'hour': '08', 'label': '8 - 9am'},
                        {'available': False, 'hour': '09', 'label': '9 - 10am'},
                        {'available': False, 'hour': '10', 'label': '10 - 11am'},
                        {'available': False, 'hour': '11', 'label': '11 - 12pm'},
                        {'available': False, 'hour': '12', 'label': '12 - 1pm'},
                        {'available': False, 'hour': '13', 'label': '1 - 2pm'},
                        {'available': False, 'hour': '14', 'label': '2 - 3pm'},
                        {'available': False, 'hour': '15', 'label': '3 - 4pm'},
                        {'available': False, 'hour': '16', 'label': '4 - 5pm'},
                        {'available': True, 'hour': '17', 'label': '5 - 6pm'},
                        {'available': True, 'hour': '18', 'label': '6 - 7pm'},
                        {'available': True, 'hour': '19', 'label': '7 - 8pm'},
                        {'available': True, 'hour': '20', 'label': '8 - 9pm'},
                        {'available': True, 'hour': '21', 'label': '9 - 10pm'},
                        {'available': True, 'hour': '22', 'label': '10 - 11pm'}]},
            {'date': '2015-03-17',
            'day_name': 'Tuesday',
            'day_of_month': 17,
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
                        {'available': True, 'hour': '22', 'label': '10 - 11pm'}]},
            ]

        # 2015-03-16 21 - 22 slot taken
        appointment = datetime.datetime(2015, 3, 16, 21, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        # 2015-03-17 from 10 - 13 no slots now available
        for hour in range(10, 14):
            appointment = datetime.datetime(2015, 3, 17, hour, tzinfo=pytz.utc)
            TrackConfirmedOrderSlotsFactory(
                appointment=appointment,
                counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        # 2015-03-17 20 - 21 slot taken
        appointment = datetime.datetime(2015, 3, 17, 20, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=appointment,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        expected_calendar_grid = [{'date': '2015-03-16',
            'day_name': 'Monday',
            'day_of_month': 16,
            'month_name': 'March',
            'time_slots': [{'available': False, 'hour': '08', 'label': '8 - 9am'},
                        {'available': False, 'hour': '09', 'label': '9 - 10am'},
                        {'available': False, 'hour': '10', 'label': '10 - 11am'},
                        {'available': False, 'hour': '11', 'label': '11 - 12pm'},
                        {'available': False, 'hour': '12', 'label': '12 - 1pm'},
                        {'available': False, 'hour': '13', 'label': '1 - 2pm'},
                        {'available': False, 'hour': '14', 'label': '2 - 3pm'},
                        {'available': False, 'hour': '15', 'label': '3 - 4pm'},
                        {'available': False, 'hour': '16', 'label': '4 - 5pm'},
                        {'available': True, 'hour': '17', 'label': '5 - 6pm'},
                        {'available': True, 'hour': '18', 'label': '6 - 7pm'},
                        {'available': True, 'hour': '19', 'label': '7 - 8pm'},
                        {'available': True, 'hour': '20', 'label': '8 - 9pm'},
                        {'available': False, 'hour': '21', 'label': '9 - 10pm'},
                        {'available': True, 'hour': '22', 'label': '10 - 11pm'}]},
            {'date': '2015-03-17',
            'day_name': 'Tuesday',
            'day_of_month': 17,
            'month_name': 'March',
            'time_slots': [{'available': True, 'hour': '08', 'label': '8 - 9am'},
                        {'available': True, 'hour': '09', 'label': '9 - 10am'},
                        {'available': False, 'hour': '10', 'label': '10 - 11am'},
                        {'available': False, 'hour': '11', 'label': '11 - 12pm'},
                        {'available': False, 'hour': '12', 'label': '12 - 1pm'},
                        {'available': False, 'hour': '13', 'label': '1 - 2pm'},
                        {'available': True, 'hour': '14', 'label': '2 - 3pm'},
                        {'available': True, 'hour': '15', 'label': '3 - 4pm'},
                        {'available': True, 'hour': '16', 'label': '4 - 5pm'},
                        {'available': True, 'hour': '17', 'label': '5 - 6pm'},
                        {'available': True, 'hour': '18', 'label': '6 - 7pm'},
                        {'available': True, 'hour': '19', 'label': '7 - 8pm'},
                        {'available': False, 'hour': '20', 'label': '8 - 9pm'},
                        {'available': True, 'hour': '21', 'label': '9 - 10pm'},
                        {'available': True, 'hour': '22', 'label': '10 - 11pm'}]},
            ]

        self.assertEqual(expected_calendar_grid,
                         mark_unavailable_slots(calendar_grid))

    def test_appointment_slot_all_available_calendar_grid(self):
        calendar_grid = [{'date': '2015-03-16',
            'day_name': 'Monday',
            'day_of_month': 16,
            'month_name': 'March',
            'time_slots': [{'available': False, 'hour': '08', 'label': '8 - 9am'},
                        {'available': False, 'hour': '09', 'label': '9 - 10am'},
                        {'available': False, 'hour': '10', 'label': '10 - 11am'},
                        {'available': False, 'hour': '11', 'label': '11 - 12pm'},
                        {'available': False, 'hour': '12', 'label': '12 - 1pm'},
                        {'available': False, 'hour': '13', 'label': '1 - 2pm'},
                        {'available': False, 'hour': '14', 'label': '2 - 3pm'},
                        {'available': False, 'hour': '15', 'label': '3 - 4pm'},
                        {'available': False, 'hour': '16', 'label': '4 - 5pm'},
                        {'available': True, 'hour': '17', 'label': '5 - 6pm'},
                        {'available': True, 'hour': '18', 'label': '6 - 7pm'},
                        {'available': True, 'hour': '19', 'label': '7 - 8pm'},
                        {'available': True, 'hour': '20', 'label': '8 - 9pm'},
                        {'available': True, 'hour': '21', 'label': '9 - 10pm'},
                        {'available': True, 'hour': '22', 'label': '10 - 11pm'}]},
            {'date': '2015-03-17',
            'day_name': 'Tuesday',
            'day_of_month': 17,
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
                        {'available': True, 'hour': '22', 'label': '10 - 11pm'}]},
            ]

        expected_calendar_grid = calendar_grid

        self.assertEqual(expected_calendar_grid,
                         mark_unavailable_slots(calendar_grid))
