from datetime import timedelta

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.utils import timezone


from bookings.models import Order
from bookings.factories import OrderFactory
from vendors.models import OrderPayments


class Commands(TestCase):
    def generate_valid_order(self):
        now_utc = timezone.now()
        yesterday = now_utc - timedelta(days=1)

        return OrderFactory(drop_off_time=yesterday,
                            order_status=Order.DELIVERED_BACK_TO_CUSTOMER,
                            placed=True)

    def test_update_order(self):
        order = self.generate_valid_order()
        args = [str(order.uuid)]
        opts = {}

        self.assertEqual(OrderPayments.objects.count(), 0)
        call_command('set_orderpayments_on_order', *args, **opts)
        self.assertEqual(OrderPayments.objects.count(), 1)
        self.assertEqual(OrderPayments.objects.filter()[0].order.uuid, order.uuid)

    def test_order_does_not_exist(self):
        args = ['XYUUI']
        opts = {}

        with self.assertRaises(CommandError):
            call_command('set_orderpayments_on_order', *args, **opts)

    def test_multi_update_order(self):
        orders = [self.generate_valid_order() for x in range(3)]

        args = [str(order.uuid) for order in orders]
        opts = {}

        self.assertEqual(OrderPayments.objects.count(), 0)
        call_command('set_orderpayments_on_order', *args, **opts)
        self.assertEqual(OrderPayments.objects.count(), 3)
