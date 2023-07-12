from decimal import Decimal
from django.db import IntegrityError
from django.test import TestCase

from bookings.factories import OrderFactory, ItemAndQuantityFactory, VendorFactory, CleanOnlyOrderFactory
from .factories import (CleanOnlyPricesFactory, DefaultCleanOnlyPricesFactory,
                        CleanAndCollectPricesFactory, DefaultCleanAndCollectPricesFactory,
                        OrderPaymentsFactory)
from ..payments import clean_only_amount, clean_and_collect_amount, total_amount_due, set_vendor_amount_due
from ..models import OrderPayments


class Payments(TestCase):
    def test_clean_only_amount_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=1), ItemAndQuantityFactory(quantity=1)]
        wishi_washi = VendorFactory()  # Wishi Washi
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        for item in items:
            CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.99'))

        self.assertEqual(Decimal('1.99') * Decimal(2), clean_only_amount(order))

    def test_clean_only_amount_assigned_to_vendor_with_quantity(self):
        items = [ItemAndQuantityFactory(quantity=2), ItemAndQuantityFactory(quantity=1)]
        wishi_washi = VendorFactory()  # Wishi Washi
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        for item in items:
            CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.99'))

        self.assertEqual(Decimal('1.99') * Decimal(3), clean_only_amount(order))

    def test_clean_only_amount_assigned_to_vendor_mixture(self):
        items = [ItemAndQuantityFactory(quantity=1), ItemAndQuantityFactory(quantity=2)]
        wishi_washi = VendorFactory()  # Wishi Washi
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        prices = [Decimal('1.62'), Decimal('2.83')]
        CleanOnlyPricesFactory(item=items[0].item, vendor=vendor, price=prices[0])
        DefaultCleanOnlyPricesFactory(item=items[1].item, price=prices[1])

        self.assertEqual(sum([prices[1] * Decimal(2),
                              prices[0]]), clean_only_amount(order))

    def test_clean_only_amount_not_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=3), ItemAndQuantityFactory(quantity=1)]
        wishi_washi = VendorFactory()  # Wishi Washi
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        vendor = VendorFactory()
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        prices = [Decimal('1.62'), Decimal('2.83')]
        for i, item in enumerate(items):
            DefaultCleanOnlyPricesFactory(item=item.item, price=prices[i])

        self.assertEqual(sum([prices[0] * Decimal(3),
                              prices[1]]), clean_only_amount(order))

    def test_clean_and_collect_amount_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=4), ItemAndQuantityFactory(quantity=1)]
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.62'), Decimal('2.83')]
        for i, item in enumerate(items):
            CleanAndCollectPricesFactory(item=item.item, vendor=vendor, price=prices[i])

        self.assertEqual(sum([prices[0] * Decimal(4), prices[1]]),
                         clean_and_collect_amount(order))

    def test_clean_and_collect_amount_assigned_to_vendor_mixture(self):
        items = [ItemAndQuantityFactory(quantity=2), ItemAndQuantityFactory(quantity=3)]
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.62'), Decimal('2.83')]
        CleanAndCollectPricesFactory(item=items[0].item, vendor=vendor, price=prices[0])
        DefaultCleanAndCollectPricesFactory(item=items[1].item, price=prices[1])

        self.assertEqual((prices[0] * Decimal(2)) + (prices[1] * Decimal(3)),
                         clean_and_collect_amount(order))

    def test_clean_and_collect_amount_not_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=1), ItemAndQuantityFactory(quantity=2)]
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('5.52'), Decimal('2.83')]
        for i, item in enumerate(items):
            DefaultCleanAndCollectPricesFactory(item=item.item, price=prices[i])

        self.assertEqual((prices[0] * Decimal(1)) + (prices[1] * Decimal(2)),
                         clean_and_collect_amount(order))

    def test_total_amount_due_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=2), ItemAndQuantityFactory(quantity=3)]
        wishi_washi = VendorFactory()  # Wishi Washi
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        for item in items:
            CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.99'))

        self.assertEqual(Decimal('1.99') * Decimal(5), clean_only_amount(order))

    def test_total_amount_due_not_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=2), ItemAndQuantityFactory(quantity=1)]
        wishi_washi = VendorFactory()  # Wishi Washi
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        vendor = VendorFactory()
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        prices = [Decimal('1.62'), Decimal('2.83')]
        for i, item in enumerate(items):
            DefaultCleanOnlyPricesFactory(item=item.item, price=prices[i])

        self.assertEqual(Decimal('6.07'), total_amount_due(order))

    def test_clean_and_collect_total_amount_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=3), ItemAndQuantityFactory(quantity=1)]
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.62'), Decimal('2.83')]
        for i, item in enumerate(items):
            CleanAndCollectPricesFactory(item=item.item, vendor=vendor, price=prices[i])

        self.assertEqual(Decimal('7.69'), total_amount_due(order))

    def test_clean_and_collect_total_amount_not_assigned_to_vendor(self):
        items = [ItemAndQuantityFactory(quantity=2), ItemAndQuantityFactory(quantity=2)]
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('5.52'), Decimal('2.83')]
        for i, item in enumerate(items):
            DefaultCleanAndCollectPricesFactory(item=item.item, price=prices[i])

        self.assertEqual(Decimal('16.70'), total_amount_due(order))

    def test_clean_only_amount_assigned_to_vendor_multi(self):
        items = [ItemAndQuantityFactory(quantity=3), ItemAndQuantityFactory()]
        wishi_washi = VendorFactory()  # Wishi Washi
        vendor = VendorFactory()
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        for item in items:
            CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.99'))

        with self.assertRaises(IntegrityError):
            CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.98'))

    def test_clean_and_collect_amount_assigned_to_vendor_multi(self):
        items = [ItemAndQuantityFactory(quantity=2), ItemAndQuantityFactory(quantity=2)]
        vendor = VendorFactory()
        OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.62'), Decimal('2.83')]
        for i, item in enumerate(items):
            CleanAndCollectPricesFactory(item=item.item, vendor=vendor, price=prices[i])

        with self.assertRaises(IntegrityError):
            CleanAndCollectPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.71'))

    def test_set_vendor_amount_due_clean_only_prices_set(self):
        items = [ItemAndQuantityFactory(), ItemAndQuantityFactory()]

        wishi_washi = VendorFactory()  # Wishi Washi
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)

        vendor = VendorFactory()  # clean only vendor
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        for item in items:
            CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.99'))

        set_vendor_amount_due(order)
        self.assertEqual(Decimal('1.99') * Decimal('2'), OrderPayments.objects.get(order=order).total_amount)

    def test_set_vendor_amount_due_clean_only_default_prices(self):
        items = [ItemAndQuantityFactory(), ItemAndQuantityFactory()]

        wishi_washi = VendorFactory()  # Wishi Washi
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)

        vendor = VendorFactory()  # clean only vendor
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        prices = [Decimal('1.23'), Decimal('1.33')]
        for i, item in enumerate(items):
            DefaultCleanOnlyPricesFactory(item=item.item, price=prices[i])

        set_vendor_amount_due(order)
        self.assertEqual(sum(prices), OrderPayments.objects.get(order=order).total_amount)

    def test_set_vendor_amount_due_clean_only_default_prices_updated(self):
        items = [ItemAndQuantityFactory(), ItemAndQuantityFactory()]

        wishi_washi = VendorFactory()  # Wishi Washi
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)

        # update this object
        OrderPaymentsFactory(order=order, total_amount=Decimal('1.10'))

        vendor = VendorFactory()  # clean only vendor
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        prices = [Decimal('1.23'), Decimal('1.33')]
        for i, item in enumerate(items):
            DefaultCleanOnlyPricesFactory(item=item.item, price=prices[i])

        set_vendor_amount_due(order)
        self.assertEqual(sum(prices), OrderPayments.objects.get(order=order).total_amount)

    def test_set_vendor_amount_due_clean_only_set_prices_and_default_prices(self):
        items = [ItemAndQuantityFactory(), ItemAndQuantityFactory()]

        wishi_washi = VendorFactory()  # Wishi Washi
        order = OrderFactory(assigned_to_vendor=wishi_washi, items=items)

        vendor = VendorFactory()  # clean only vendor
        CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)

        prices = [Decimal('1.23'), Decimal('1.33')]
        for i, item in enumerate(items):
            DefaultCleanOnlyPricesFactory(item=item.item, price=prices[i])

        # last item set to a different vendor price
        CleanOnlyPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.99'))

        set_vendor_amount_due(order)
        self.assertEqual(sum([Decimal('1.23'), Decimal('1.99')]), OrderPayments.objects.get(order=order).total_amount)

    def test_set_vendor_amount_due_clean_and_collect_default_prices(self):
        items = [ItemAndQuantityFactory(), ItemAndQuantityFactory()]

        vendor = VendorFactory()  # clean and collect vendor
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.23'), Decimal('1.33')]
        for i, item in enumerate(items):
            DefaultCleanAndCollectPricesFactory(item=item.item, price=prices[i])

        set_vendor_amount_due(order)
        self.assertEqual(sum(prices), OrderPayments.objects.get(order=order).total_amount)

    def test_set_vendor_amount_due_clean_and_collect_set_vendor_prices(self):
        items = [ItemAndQuantityFactory(), ItemAndQuantityFactory()]

        vendor = VendorFactory()  # clean and collect vendor
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.23'), Decimal('1.33')]
        for i, item in enumerate(items):
            DefaultCleanAndCollectPricesFactory(item=item.item, price=prices[i])
        CleanAndCollectPricesFactory(item=item.item, vendor=vendor, price=Decimal('1.77'))

        set_vendor_amount_due(order)
        self.assertEqual(sum([prices[0], Decimal('1.77')]), OrderPayments.objects.get(order=order).total_amount)

    def test_set_vendor_amount_due_clean_and_collect_set_prices(self):
        items = [ItemAndQuantityFactory(quantity=4), ItemAndQuantityFactory()]

        vendor = VendorFactory()  # clean and collect vendor
        order = OrderFactory(assigned_to_vendor=vendor, items=items)

        prices = [Decimal('1.23'), Decimal('1.33')]
        for i, item in enumerate(items):
            DefaultCleanAndCollectPricesFactory(item=item.item, price=prices[i])

        vendor_prices = [Decimal('1.33'), Decimal('1.43')]
        for i, item in enumerate(items):
            CleanAndCollectPricesFactory(item=item.item, vendor=vendor, price=vendor_prices[i])

        set_vendor_amount_due(order)
        self.assertEqual(vendor_prices[0] * Decimal(4) + vendor_prices[1], OrderPayments.objects.get(order=order).total_amount)


