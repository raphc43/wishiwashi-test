# -*- coding: utf-8 -*-
from decimal import Decimal
import datetime

from django.test import TestCase
from django.template.loader import render_to_string
import pytz

from bookings.factories import (AddressFactory,
                                ItemFactory,
                                ItemAndQuantityFactory,
                                OrderFactory,
                                UserFactory)


PICKUP_SUBJECT = 'bookings/emails/pick-up-order-reminder-subject.txt'
PICKUP_HTML = 'bookings/emails/pick-up-order-reminder.html'
PICKUP_TXT = 'bookings/emails/pick-up-order-reminder.txt'

DROPOFF_SUBJECT = 'bookings/emails/drop-off-order-reminder-subject.txt'
DROPOFF_HTML = 'bookings/emails/drop-off-order-reminder.html'
DROPOFF_TXT = 'bookings/emails/drop-off-order-reminder.txt'


class EmailTemplates(TestCase):
    def test_pickup_email(self):
        user = UserFactory()
        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        subject = render_to_string(PICKUP_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(PICKUP_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(PICKUP_TXT, {'order': order}).encode("utf-8")

        self.assertTrue(item.name.encode("utf-8") in txt)
        self.assertTrue(item.name.encode("utf-8") in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Tuesday 6th January between 10AM & 11AM" in txt, txt
        assert "Tuesday 6th January" in html, html
        assert "10AM &amp; 11AM" in html, html

    def test_pickup_email_BST(self):
        " UTC + 1hour "
        user = UserFactory()
        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        subject = render_to_string(PICKUP_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(PICKUP_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(PICKUP_TXT, {'order': order}).encode("utf-8")

        self.assertTrue(item.name.encode("utf-8") in txt)
        self.assertTrue(item.name.encode("utf-8") in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Monday 7th April between 11AM & 12PM" in txt, txt
        assert "Monday 7th April" in html, html
        assert "11AM &amp; 12PM" in html, html

    def test_dropoff_email(self):
        user = UserFactory()
        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        subject = render_to_string(DROPOFF_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(DROPOFF_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(DROPOFF_TXT, {'order': order}).encode("utf-8")

        self.assertTrue(item.name.encode("utf-8") in txt)
        self.assertTrue(item.name.encode("utf-8") in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Thursday 8th January between 2PM & 3PM" in txt, txt
        assert "Thursday 8th January" in html, html
        assert "2PM &amp; 3PM" in html, html

    def test_dropoff_email_BST(self):
        " UTC + 1hour "
        user = UserFactory()
        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        subject = render_to_string(DROPOFF_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(DROPOFF_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(DROPOFF_TXT, {'order': order}).encode("utf-8")

        self.assertTrue(item.name.encode("utf-8") in txt)
        self.assertTrue(item.name.encode("utf-8") in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Thursday 10th April between 3PM & 4PM" in txt, txt
        assert "Thursday 10th April" in html, html
        assert "3PM &amp; 4PM" in html, html
