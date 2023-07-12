import datetime
from copy import deepcopy

from django.conf import settings
from django.test import TestCase
from freezegun import freeze_time
import pytz

from bookings.models import Order
from bookings.factories import OrderFactory, UserFactory, VendorFactory
from ..upcoming import (monday_start_sunday_end_datetime_range,
                        weekly_empty_list,
                        weekly_hourly_booked_slots,
                        orders_upcoming,
                        void_weekly_empty_slots_past)


class Upcoming(TestCase):
    @freeze_time("2015-02-07 10:00:00")
    def test_monday_start_sunday_end_datetime_range_now(self):
        local = pytz.timezone(settings.TIME_ZONE)
        monday_start = local.localize(datetime.datetime(2015, 2, 2))
        sunday_end = local.localize(datetime.datetime(2015, 2, 8, 23, 59, second=59, microsecond=999999))

        self.assertEqual(monday_start_sunday_end_datetime_range(),
                         (monday_start, sunday_end))

    @freeze_time("2015-05-07 10:00:00")
    def test_monday_start_sunday_end_datetime_range_now_BST(self):
        local = pytz.timezone(settings.TIME_ZONE)
        monday_start = local.localize(datetime.datetime(2015, 5, 4))
        sunday_end = local.localize(datetime.datetime(2015, 5, 10, 23, 59, second=59, microsecond=999999))

        self.assertEqual(monday_start_sunday_end_datetime_range(),
                         (monday_start, sunday_end))

    def test_monday_start_sunday_end_datetime_range_dt_param(self):
        local = pytz.timezone(settings.TIME_ZONE)
        monday_start = local.localize(datetime.datetime(2015, 7, 13))
        sunday_end = local.localize(datetime.datetime(2015, 7, 19, 23, 59, second=59, microsecond=999999))

        dt = local.localize(datetime.datetime(2015, 7, 15, 14, 2, 8))

        self.assertEqual(monday_start_sunday_end_datetime_range(dt),
                         (monday_start, sunday_end))

    def test_weekly_empty_list(self):
        expected = [[[]]*7] * 2
        with self.settings(COLLECT_DELIVER_HOUR_START=8, COLLECT_DELIVER_HOUR_END=10):
            self.assertEqual(expected, weekly_empty_list())

        expected = [[[]]*7] * 4
        with self.settings(COLLECT_DELIVER_HOUR_START=8, COLLECT_DELIVER_HOUR_END=12):
            self.assertEqual(expected, weekly_empty_list())

        total_hours_open = settings.COLLECT_DELIVER_HOUR_END - settings.COLLECT_DELIVER_HOUR_START
        expected = [[[]]*7] * total_hours_open
        self.assertEqual(expected, weekly_empty_list())

    @freeze_time("2015-02-07 10:00:00")
    def test_weekly_list_of_all_hourly_slots(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        pick_up_time = datetime.datetime(2015, 1, 31, 9, 0, 0, 0, pytz.UTC)
        # Friday 6th Feb 2015 @ 8am
        drop_off_time = datetime.datetime(2015, 2, 6, 8, 0, 0, 0, pytz.UTC)

        order = OrderFactory(drop_off_time=drop_off_time,
                             pick_up_time=pick_up_time,
                             placed=True,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             assigned_to_vendor=vendor)

        start_dt, end_dt = monday_start_sunday_end_datetime_range()
        orders = orders_upcoming(vendor, start_dt, end_dt)
        weekly_orders = weekly_hourly_booked_slots(orders, start_dt, end_dt)

        self.assertEqual(weekly_orders[0][4][0]["collect"], False)
        self.assertEqual(weekly_orders[0][4][0]["postcode"], order.pick_up_and_delivery_address.postcode)
        self.assertEqual(weekly_orders[0][4][0]["order"], order.uuid)

    @freeze_time("2015-01-07 10:00:00")
    def test_weekly_list_of_all_hourly_multi_slots(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        # Monday 5th Jan 2015
        pick_up_time = datetime.datetime(2015, 1, 5, 9, 0, 0, 0, pytz.UTC)
        # Thursday 8th Jan 2015
        drop_off_time = datetime.datetime(2015, 1, 8, 8, 0, 0, 0, pytz.UTC)

        order = OrderFactory(drop_off_time=drop_off_time,
                             pick_up_time=pick_up_time,
                             placed=True,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             assigned_to_vendor=vendor)

        start_dt, end_dt = monday_start_sunday_end_datetime_range()
        orders = orders_upcoming(vendor, start_dt, end_dt)
        weekly_orders = weekly_hourly_booked_slots(orders, start_dt, end_dt)

        self.assertEqual(weekly_orders[1][0][0]["order"], order.uuid)
        self.assertEqual(weekly_orders[1][0][0]["collect"], True)
        self.assertEqual(weekly_orders[1][0][0]["postcode"], order.pick_up_and_delivery_address.postcode)

        self.assertEqual(weekly_orders[0][3][0]["order"], order.uuid)
        self.assertEqual(weekly_orders[0][3][0]["collect"], False)
        self.assertEqual(weekly_orders[0][3][0]["postcode"], order.pick_up_and_delivery_address.postcode)

    @freeze_time("2015-07-07 10:00:00")
    def test_weekly_list_of_all_hourly_multi_slots_BST(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        # Monday 6th Jul 2015 @ 9am UTC / 10 AM BST
        pick_up_time = datetime.datetime(2015, 7, 6, 9, 0, 0, 0, pytz.UTC)
        # Thursday 9th Jul 2015 @ 8 am UTC / 9 am BST
        drop_off_time = datetime.datetime(2015, 7, 9, 8, 0, 0, 0, pytz.UTC)

        order = OrderFactory(drop_off_time=drop_off_time,
                             pick_up_time=pick_up_time,
                             placed=True,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             assigned_to_vendor=vendor)

        start_dt, end_dt = monday_start_sunday_end_datetime_range()
        orders = orders_upcoming(vendor, start_dt, end_dt)
        weekly_orders = weekly_hourly_booked_slots(orders, start_dt, end_dt)

        self.assertEqual(weekly_orders[2][0][0]["order"], order.uuid)
        self.assertEqual(weekly_orders[2][0][0]["collect"], True)
        self.assertEqual(weekly_orders[2][0][0]["postcode"], order.pick_up_and_delivery_address.postcode)

        self.assertEqual(weekly_orders[1][3][0]["order"], order.uuid)
        self.assertEqual(weekly_orders[1][3][0]["collect"], False)
        self.assertEqual(weekly_orders[1][3][0]["postcode"], order.pick_up_and_delivery_address.postcode)

    @freeze_time("2015-02-02 00:00:00")
    def test_void_weekly_empty_slots_past(self):
        # Daily list operating for 2 hours
        weekly_list = [[[]]*7] * 2
        self.assertEqual(weekly_list, void_weekly_empty_slots_past(weekly_list))

    @freeze_time("2015-02-02 09:00:00")
    def test_void_weekly_empty_slots_past_monday(self):
        weekly_list = [[[]]*7] * 2
        _weekly_list = deepcopy(weekly_list)
        _weekly_list[0][0] = None
        self.assertEqual(_weekly_list, void_weekly_empty_slots_past(weekly_list))

    @freeze_time("2015-02-03 09:00:00")
    def test_void_weekly_empty_slots_past_multi(self):
        weekly_list = [[[]]*7] * 2
        _weekly_list = deepcopy(weekly_list)
        _weekly_list[0][0] = None
        _weekly_list[0][1] = None
        _weekly_list[1][0] = None
        self.assertEqual(_weekly_list, void_weekly_empty_slots_past(weekly_list))

    @freeze_time("2015-02-03 09:00:00")
    def test_void_weekly_empty_slots_past_ignore_non_empty_slots(self):
        weekly_list = [[[]]*7] * 2
        weekly_list[0][1] = [1]
        _weekly_list = deepcopy(weekly_list)
        _weekly_list[0][0] = None
        _weekly_list[0][1] = [1]
        _weekly_list[1][0] = None
        self.assertEqual(_weekly_list, void_weekly_empty_slots_past(weekly_list))

    def test_orders_upcoming(self):
        pick_up_times = (datetime.datetime(2015, 2, 26, 9, tzinfo=pytz.utc),
                         datetime.datetime(2015, 2, 24, 11, tzinfo=pytz.utc),
                         datetime.datetime(2015, 2, 28, 20, tzinfo=pytz.utc))

        drop_off_times = (datetime.datetime(2015, 3, 1, 15, tzinfo=pytz.utc),
                          datetime.datetime(2015, 2, 26, 8, tzinfo=pytz.utc),
                          datetime.datetime(2015, 2, 26, 20, tzinfo=pytz.utc))

        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        # 2015 26th Feb
        start_dt = datetime.datetime(2015, 2, 26, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 2, 26, 23, 59, tzinfo=pytz.utc)

        orders = []
        for pick_up_time, drop_off_time in zip(pick_up_times, drop_off_times):
            order = OrderFactory(drop_off_time=drop_off_time,
                                 pick_up_time=pick_up_time,
                                 placed=True,
                                 order_status=Order.CLAIMED_BY_VENDOR,
                                 assigned_to_vendor=vendor)
            order.upcoming_date = start_dt.date()
            orders.append(order)

        expected = [
            orders[1],
            orders[0],
            orders[2]
        ]

        self.assertEqual(expected, orders_upcoming(vendor, start_dt, end_dt))

