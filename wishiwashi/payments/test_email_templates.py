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


CONFIRMATION_SUBJECT = 'payments/emails/confirmation-order-subject.txt'
CONFIRMATION_HTML = 'payments/emails/confirmation-order.html'
CONFIRMATION_TXT = 'payments/emails/confirmation-order.txt'

CHARGE_SUBJECT = 'payments/emails/confirmation-charge-subject.txt'
CHARGE_HTML = 'payments/emails/confirmation-charge.html'
CHARGE_TXT = 'payments/emails/confirmation-charge.txt'


class EmailTemplates(TestCase):
    def test_confirmation_email(self):
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

        subject = render_to_string(CONFIRMATION_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(CONFIRMATION_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(CONFIRMATION_TXT, {'order': order}).encode("utf-8")

        self.assertTrue("£68.80" in txt)
        self.assertTrue("&pound;68.80" in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Tuesday 6th January between 10AM & 11AM" in txt, txt
        assert "Thursday 8th January between 2PM & 3PM" in txt, txt
        assert "Tuesday 6th January" in html, html
        assert "10AM &amp; 11AM" in html, html
        assert "Thursday 8th January" in html, html
        assert "2PM &amp; 3PM" in html, html

    def test_confirmation_email_BST(self):
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

        subject = render_to_string(CONFIRMATION_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(CONFIRMATION_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(CONFIRMATION_TXT, {'order': order}).encode("utf-8")

        self.assertTrue("£68.80" in txt)
        self.assertTrue("&pound;68.80" in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Monday 7th April between 11AM & 12PM" in txt, txt
        assert "Thursday 10th April between 3PM & 4PM" in txt, txt
        assert "Monday 7th April" in html, html
        assert "11AM &amp; 12PM" in html, html
        assert "Thursday 10th April" in html, html
        assert "3PM &amp; 4PM" in html, html

    def test_confirmation_charge_email(self):
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

        subject = render_to_string(CHARGE_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(CHARGE_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(CHARGE_TXT, {'order': order}).encode("utf-8")

        self.assertTrue("£68.80" in txt)
        self.assertTrue("&pound;68.80" in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Tuesday 6th January between 10AM & 11AM" in txt, txt
        assert "Thursday 8th January between 2PM & 3PM" in txt, txt
        assert "Tuesday 6th January" in html, html
        assert "10AM &amp; 11AM" in html, html
        assert "Thursday 8th January" in html, html
        assert "2PM &amp; 3PM" in html, html

    def test_confirmation_charge_email_BST(self):
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

        subject = render_to_string(CHARGE_SUBJECT, {'uuid': order.uuid}).encode("utf-8")
        html = render_to_string(CHARGE_HTML, {'order': order}).encode("utf-8")
        txt = render_to_string(CHARGE_TXT, {'order': order}).encode("utf-8")

        self.assertTrue("£68.80" in txt)
        self.assertTrue("&pound;68.80" in html)
        self.assertTrue(order.uuid.encode("utf-8") in subject)
        assert "Monday 7th April between 11AM & 12PM" in txt, txt
        assert "Thursday 10th April between 3PM & 4PM" in txt, txt
        assert "Monday 7th April" in html, html
        assert "11AM &amp; 12PM" in html, html
        assert "Thursday 10th April" in html, html
        assert "3PM &amp; 4PM" in html, html

