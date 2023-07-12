from decimal import Decimal
from django.test import TestCase

from .prices import total_price
from .factories import ItemFactory, VoucherFactory


class Discounts(TestCase):
    def test_discount_applied(self):
        item1 = ItemFactory(price=Decimal('12.18'))
        item2 = ItemFactory(price=Decimal('31.79'))
        item3 = ItemFactory(price=Decimal('27.21'))

        items = {unicode(str(item1.pk)): 1,
                 unicode(str(item2.pk)): 2,
                 unicode(str(item3.pk)): 1}

        voucher = VoucherFactory(percentage_off=Decimal('17.5'))

        # total price == 102.97 - 17.5%
        self.assertEqual(total_price(items, voucher), Decimal('84.95'))

    def test_discount_applied_items(self):
        item1 = ItemFactory(price=Decimal('2.18'))
        item2 = ItemFactory(price=Decimal('5.79'))

        items = {unicode(str(item1.pk)): 1,
                 unicode(str(item2.pk)): 4}

        voucher = VoucherFactory(percentage_off=Decimal('5.0'))

        # total price == 25.34 - 5%
        self.assertEqual(total_price(items, voucher), Decimal('24.07'))

    def test_no_discount_applied(self):
        item1 = ItemFactory(price=Decimal('2.18'))
        item2 = ItemFactory(price=Decimal('5.79'))

        items = {unicode(str(item1.pk)): 1,
                 unicode(str(item2.pk)): 4}

        voucher = None
        self.assertEqual(total_price(items, voucher), Decimal('25.34'))

    def test_transport_charge_total_price(self):
        item1 = ItemFactory(price=Decimal('10.95'))
        items = {unicode(str(item1.pk)): 1}
        voucher = None
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('15.00'), TRANSPORTATION_CHARGE=Decimal('3.95')):
            self.assertEqual(total_price(items, voucher), Decimal('14.90'))

    def test_no_items_total_price(self):
        items = {}
        voucher = None
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('15.00'), TRANSPORTATION_CHARGE=Decimal('3.95')):
            self.assertEqual(total_price(items, voucher), Decimal('0.00'))

    def test_transport_charge_total_price_floor(self):
        item1 = ItemFactory(price=Decimal('10.03'))
        items = {unicode(str(item1.pk)): 2}
        voucher = None
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('25.00'), TRANSPORTATION_CHARGE=Decimal('3.95')):
            self.assertEqual(total_price(items, voucher), Decimal('24.01'))

    def test_charge_total_price_rounded(self):
        item1 = ItemFactory(price=Decimal('2.25'))
        items = {unicode(str(item1.pk)): 1}
        voucher = VoucherFactory(percentage_off=Decimal('14.0'))
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('15.00'), TRANSPORTATION_CHARGE=Decimal('3.95')):
            self.assertEqual(total_price(items, voucher), Decimal('5.88'))


