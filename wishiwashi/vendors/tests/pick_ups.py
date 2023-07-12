import datetime

from django.test import TestCase
import pytz

from bookings.models import Order
from bookings.factories import OrderFactory, VendorFactory

from ..pick_ups import vendor_pick_ups


class PickUps(TestCase):
    def test_valid_pick_up(self):
        pick_up_time = datetime.datetime(2015, 1, 2, 8, 14, 0, tzinfo=pytz.utc)
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor,
                             placed=True,
                             pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR
                             )
        start_dt = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 1, 2, 23, 59, 59, tzinfo=pytz.utc)

        self.assertEqual(order, vendor_pick_ups(vendor=vendor,
                                                start_dt=start_dt,
                                                end_dt=end_dt)[0])

    def test_no_pick_ups(self):
        pick_up_time = datetime.datetime(2015, 1, 2, 7, 14, 0, tzinfo=pytz.utc)
        vendor = VendorFactory()
        OrderFactory(assigned_to_vendor=vendor,
                     placed=True,
                     pick_up_time=pick_up_time,
                     order_status=Order.CLAIMED_BY_VENDOR
                     )
        start_dt = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 1, 2, 23, 59, 59, tzinfo=pytz.utc)

        self.assertFalse(vendor_pick_ups(vendor=vendor, start_dt=start_dt, end_dt=end_dt))

    def test_unassigned_pick_up(self):
        pick_up_time = datetime.datetime(2015, 1, 2, 8, 14, 0, tzinfo=pytz.utc)
        vendor = VendorFactory()
        OrderFactory(assigned_to_vendor=vendor,
                     placed=True,
                     pick_up_time=pick_up_time,
                     order_status=Order.UNCLAMIED_BY_VENDORS
                     )
        start_dt = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 1, 2, 23, 59, 59, tzinfo=pytz.utc)

        self.assertFalse(vendor_pick_ups(vendor=vendor, start_dt=start_dt, end_dt=end_dt))


