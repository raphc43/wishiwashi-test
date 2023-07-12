import datetime

from django.test import TestCase
import pytz

from bookings.models import Order
from bookings.factories import OrderFactory, VendorFactory

from ..drop_offs import vendor_drop_offs


class DropOffs(TestCase):
    def test_valid_(self):
        drop_off_time = datetime.datetime(2015, 1, 2, 8, 14, 0, tzinfo=pytz.utc)
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor,
                             placed=True,
                             drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR
                             )
        start_dt = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 1, 2, 23, 59, 59, tzinfo=pytz.utc)

        self.assertEqual(order, vendor_drop_offs(vendor=vendor,
                                                 start_dt=start_dt,
                                                 end_dt=end_dt)[0])

    def test_no_drop_offs(self):
        drop_off_time = datetime.datetime(2015, 1, 2, 7, 14, 0, tzinfo=pytz.utc)
        vendor = VendorFactory()
        OrderFactory(assigned_to_vendor=vendor,
                     placed=True,
                     drop_off_time=drop_off_time,
                     order_status=Order.RECEIVED_BY_VENDOR
                     )
        start_dt = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 1, 2, 23, 59, 59, tzinfo=pytz.utc)

        self.assertFalse(vendor_drop_offs(vendor=vendor, start_dt=start_dt, end_dt=end_dt))

    def test_unassigned_drop_off(self):
        drop_off_time = datetime.datetime(2015, 1, 2, 8, 14, 0, tzinfo=pytz.utc)
        vendor = VendorFactory()
        OrderFactory(assigned_to_vendor=vendor,
                     placed=True,
                     drop_off_time=drop_off_time,
                     order_status=Order.UNCLAMIED_BY_VENDORS
                     )
        start_dt = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc)
        end_dt = datetime.datetime(2015, 1, 2, 23, 59, 59, tzinfo=pytz.utc)

        self.assertFalse(vendor_drop_offs(vendor=vendor, start_dt=start_dt, end_dt=end_dt))


