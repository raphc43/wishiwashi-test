import datetime
from decimal import Decimal
from django.test import TestCase

import pytz

from bookings.factories import ItemFactory, ItemAndQuantityFactory, OrderFactory, AddressFactory, CleanOnlyOrderFactory
from ..orders import prepare_for_pdf, add_order_to_files, html_order, sort_orders_upcoming


class Orders(TestCase):
    def test_prepare_for_pdf(self):
        address = AddressFactory(flat_number_house_number_building_name="85",
                                 address_line_1="Testing Road Street",
                                 address_line_2="This town",
                                 town_or_city="London",
                                 postcode="sw36ty")

        items = [ItemAndQuantityFactory(quantity=2, price=Decimal('3.75'), item=ItemFactory(pieces=2)),
                 ItemAndQuantityFactory(quantity=3, price=Decimal('7.99'), item=ItemFactory(pieces=1))]
        order = OrderFactory(items=items, pick_up_and_delivery_address=address)

        order = prepare_for_pdf(order)
        self.assertEqual(order.address, "85, Testing Road Street, This town, London")
        self.assertEqual(order.total_pieces, 7)
        self.assertFalse(hasattr(order, 'expected_back'))

    def test_prepare_for_pdf_clean_only_order(self):
        address = AddressFactory(flat_number_house_number_building_name="85",
                                 address_line_1="Testing Road Street",
                                 address_line_2="This town",
                                 town_or_city="London",
                                 postcode="sw36ty")

        items = [ItemAndQuantityFactory(quantity=2, price=Decimal('3.75'), item=ItemFactory(pieces=2)),
                 ItemAndQuantityFactory(quantity=3, price=Decimal('7.99'), item=ItemFactory(pieces=1))]
        drop_off = datetime.datetime(2014, 3, 31, 9, 0, 0, 0, pytz.UTC)
        order = OrderFactory(drop_off_time=drop_off, items=items, pick_up_and_delivery_address=address)
        CleanOnlyOrderFactory(order=order)

        order = prepare_for_pdf(order)
        self.assertTrue(order.expected_back)
        self.assertEqual(order.expected_back, "Sat 29 Mar PM")

    def test_add_order_to_files(self):
        order = OrderFactory()
        html = html_order(order)
        expected = [('{}'.format(order.uuid), ('order_{}'.format(order.uuid), html, 'text/html; charset=utf-8'))]
        files = add_order_to_files(order)
        self.assertEqual(expected, files)

    def test_add_order_to_files_multi(self):
        orders = [OrderFactory(), OrderFactory(), OrderFactory]

        expected = []
        for order in orders:
            html = html_order(order)
            expected.append(('file', ('order_{}'.format(order.uuid), html, 'text/html; charset=utf-8')))

        files = []
        for order in orders:
            add_order_to_files(order, files)

        self.assertEqual(3, len(files))

    def test_orders_sorted_by_upcoming_date(self):
        pick_up_time_1 = datetime.datetime(2015, 2, 6, 10, tzinfo=pytz.utc)
        drop_off_time_1 = datetime.datetime(2015, 2, 8, 15, tzinfo=pytz.utc)

        pick_up_time_2 = datetime.datetime(2015, 2, 8, 11, tzinfo=pytz.utc)
        drop_off_time_2 = datetime.datetime(2015, 2, 10, 10, tzinfo=pytz.utc)

        pick_up_time_3 = datetime.datetime(2015, 2, 7, 10, tzinfo=pytz.utc)
        drop_off_time_3 = datetime.datetime(2015, 2, 9, 20, tzinfo=pytz.utc)

        orders = [
            OrderFactory(pick_up_time=pick_up_time_1, drop_off_time=drop_off_time_1),
            OrderFactory(pick_up_time=pick_up_time_2, drop_off_time=drop_off_time_2),
            OrderFactory(pick_up_time=pick_up_time_3, drop_off_time=drop_off_time_3)
        ]

        # 2015 8th Feb
        upcoming_date = drop_off_time_1.date()
        map(lambda order: setattr(order, 'upcoming_date', upcoming_date), orders)

        expected = [
            orders[1],
            orders[0],
            orders[2]
        ]

        self.assertEqual(expected, sort_orders_upcoming(orders))

    def test_orders_sorted_by_upcoming_date_multi(self):
        pick_up_time_1 = datetime.datetime(2015, 2, 26, 10, tzinfo=pytz.utc)
        drop_off_time_1 = datetime.datetime(2015, 3, 1, 15, tzinfo=pytz.utc)

        pick_up_time_2 = datetime.datetime(2015, 3, 2, 11, tzinfo=pytz.utc)
        drop_off_time_2 = datetime.datetime(2015, 3, 15, 10, tzinfo=pytz.utc)

        pick_up_time_3 = datetime.datetime(2015, 2, 27, 10, tzinfo=pytz.utc)
        drop_off_time_3 = datetime.datetime(2015, 3, 12, 20, tzinfo=pytz.utc)

        orders = [
            OrderFactory(pick_up_time=pick_up_time_1, drop_off_time=drop_off_time_1),
            OrderFactory(pick_up_time=pick_up_time_2, drop_off_time=drop_off_time_2),
            OrderFactory(pick_up_time=pick_up_time_3, drop_off_time=drop_off_time_3)
        ]

        # 2015 27th Feb
        upcoming_date = datetime.datetime(2015, 2, 27, 15, tzinfo=pytz.utc).date()
        setattr(orders[0], 'upcoming_date', upcoming_date)
        setattr(orders[1], 'upcoming_date', upcoming_date)
        setattr(orders[2], 'upcoming_date', upcoming_date)

        expected = [
            orders[2],
            orders[0],
            orders[1]
        ]

        self.assertEqual(expected, sort_orders_upcoming(orders))

