# -*- coding: utf-8 -*-
import datetime
from datetime import timedelta
from itertools import chain
import simplejson as json
from decimal import Decimal

from django.conf import settings
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
from freezegun import freeze_time
import mock
import pytz

from bookings.models import Order, Vendor
from bookings.factories import (AddressFactory,
                                ItemFactory,
                                ItemAndQuantityFactory,
                                OrderFactory,
                                OutCodesFactory,
                                UserFactory,
                                VendorFactory,
                                CleanOnlyOrderFactory,
                                ExpectedBackCleanOnlyOrderFactory)
from bookings.tickets import next_ticket_id
from customer_service.models import UserProfile
from customer_service.factories import UserProfileFactory
from ..tasks import (get_json_payload,
                     get_order_headline_summary,
                     notify_vendors_of_orders_via_email,
                     unaccepted_orders_go_to_wishiwashi,
                     vendor_recipients,
                     assign_vendor_payments,
                     assign_all_orders_to_clean_only_vendor)
from .patches import (create_order,
                      create_vendor,
                      fake_error_logging,
                      fake_job_resp,
                      fake_resp_error,
                      )
from .factories import (DefaultCleanAndCollectPricesFactory,
                        CleanAndCollectPricesFactory,
                        DefaultCleanOnlyPricesFactory,
                        CleanOnlyPricesFactory)


@override_settings(COMMUNICATE_SERVICE_ENDPOINT='http://dummy',
                   RENDER_SERVICE_ENDPOINT='http://dummy')
@mock.patch('vendors.tasks.logger.error', fake_error_logging)
class Tasks(TestCase):
    fixtures = ['test_outcodes', 'test_wishi_washi_vendor',
                'test_categories_and_items']

    def test_unaccepted_orders_go_to_wishiwashi(self):
        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        tz_london = pytz.timezone('Europe/London')
        now_london = now_utc.astimezone(tz_london)
        two_hours_ago = now_london - timedelta(hours=2)

        order = create_order()
        order.order_status = Order.UNCLAMIED_BY_VENDORS
        order.authorisation_status = Order.SUCCESSFULLY_AUTHORISED
        order.placed = True
        order.placed_time = two_hours_ago
        order.save()

        unaccepted_orders_go_to_wishiwashi()

        order = Order.objects.get(pk=order.pk)
        self.assertEqual(order.order_status, Order.CLAIMED_BY_VENDOR)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        self.assertEqual(order.assigned_to_vendor, wishi_washi)

    def test_unaccepted_orders_go_to_wishiwashi_not_before_time_passed(self):
        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        tz_london = pytz.timezone('Europe/London')
        now_london = now_utc.astimezone(tz_london)
        time_passed = now_london - timedelta(seconds=45)

        order = create_order()
        order.order_status = Order.UNCLAMIED_BY_VENDORS
        order.authorisation_status = Order.SUCCESSFULLY_AUTHORISED
        order.placed = True
        order.placed_time = time_passed
        order.save()

        unaccepted_orders_go_to_wishiwashi()

        order = Order.objects.get(pk=order.pk)
        self.assertNotEqual(order.order_status, Order.CLAIMED_BY_VENDOR)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        self.assertNotEqual(order.assigned_to_vendor, wishi_washi)

    @freeze_time("2015-04-13 10:00:00")
    def test_get_json_payload(self):
        order = create_order(pick_up_time='2015-04-15 10',
                             delivery_time='2015-04-17 16')
        payload = get_json_payload(order)
        payload = json.dumps(payload, sort_keys=True)
        expected = json.dumps({
            "collection_time": "Wed, Apr 15th 11AM - 12PM",
            "customer_address": "1 High Road\nLondon, W1 1AA",
            "customer_mobile_number": "+44 (0)7712 345678",
            "customer_name": "First Last",
            "delivery_time": "Fri, Apr 17th 5PM - 6PM",
            "discount_percent": '0',
            "grand_total": Decimal('7.00'),
            "items": [
                {
                    "name": "Dressing gown cotton",
                    "price": Decimal('4.00'),
                    "quantity": 5,
                    "pieces": 5
                },
                {
                    "name": "Bath towel",
                    "price": Decimal('3.00'),
                    "quantity": 10,
                    "pieces": 10
                }
            ],
            "order_uuid": order.uuid,
            "ticket_id": next_ticket_id(order.pk)}, sort_keys=True)
        self.assertEqual(payload, expected)

    @freeze_time("2015-04-13 10:00:00")
    def test_get_json_payload_multi_pieces(self):
        user = UserFactory(first_name="First",
                           last_name="Last")
        UserProfileFactory(user=user,
                           mobile_number="00447712345678")
        address = AddressFactory(flat_number_house_number_building_name="1",
                                 address_line_1="High Road",
                                 address_line_2="",
                                 town_or_city="London",
                                 postcode="w11aa")
        item = ItemFactory(vendor_friendly_name="Dress",
                           price=Decimal('17.20'), pieces=2)
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 4, 15, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 4, 17, 16, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('34.40'),
                             ticket_id="WW-00002")

        payload = get_json_payload(order)
        payload = json.dumps(payload, sort_keys=True)
        expected = json.dumps({
            "collection_time": "Wed, Apr 15th 11AM - 12PM",
            "customer_address": "1 High Road\nLondon, W1 1AA",
            "customer_mobile_number": "+44 (0)7712 345678",
            "customer_name": "First Last",
            "delivery_time": "Fri, Apr 17th 5PM - 6PM",
            "discount_percent": '0',
            "grand_total": Decimal('34.40'),
            "items": [
                {
                    "name": item.vendor_friendly_name,
                    "price": Decimal('17.20'),
                    "quantity": 4,
                    "pieces": 8
                }
            ],
            "order_uuid": order.uuid,
            "ticket_id": "WW-00002"}, sort_keys=True)
        self.assertEqual(payload, expected)

    def test_get_order_headline_summary(self):
        # UTC
        order = create_order(pick_up_time='2015-04-15 10',
                             delivery_time='2015-04-17 16')
        resp = get_order_headline_summary(order)

        # BST
        expecting = u'\xa37.00 order in W1 (pickup Wed Apr 15 11-12, drop off Fri Apr 17 17-18) order# %s' % order.uuid
        self.assertEqual(resp, expecting)

    def _create_two_vendors(self):
        # Create some staff with some mobile numbers
        vendor1 = create_vendor(client=None, create_new_vendor=True)
        user1 = vendor1.staff.all()[0]
        profile1 = UserProfile.objects.get(user=user1)
        profile1.mobile_number = '00447911123455'
        profile1.sms_notifications_enabled = True
        profile1.email_notifications_enabled = True
        profile1.save()

        vendor2 = create_vendor(client=None, create_new_vendor=True)
        user2 = vendor2.staff.all()[0]
        profile2 = UserProfile.objects.get(user=user2)
        profile2.mobile_number = '00447911123456'
        profile2.sms_notifications_enabled = True
        profile2.email_notifications_enabled = True
        profile2.save()

    @mock.patch('requests.post', fake_job_resp)
    def test_notify_vendors_of_orders_via_email(self):
        outcodes = [OutCodesFactory(out_code='sw10')]

        users = [UserFactory() for _ in range(0, 2)]
        for user in users:
            UserProfileFactory(user=user,
                               email_notifications_enabled=True)

        # Serves sw10
        VendorFactory(staff=users, catchment_area=outcodes)

        address = AddressFactory(postcode='sw107ty')
        order = OrderFactory(pick_up_and_delivery_address=address)

        resp = notify_vendors_of_orders_via_email(order.pk)
        self.assertTrue(resp)

    @mock.patch('requests.post', fake_resp_error)
    def test_notify_vendors_of_orders_via_email_failure(self):
        outcodes = [OutCodesFactory(out_code='sw10')]

        users = [UserFactory() for _ in range(0, 2)]
        for user in users:
            UserProfileFactory(user=user,
                               email_notifications_enabled=True)

        # Serves sw10
        VendorFactory(staff=users, catchment_area=outcodes)

        address = AddressFactory(postcode='sw107ty')
        order = OrderFactory(pick_up_and_delivery_address=address)

        with self.assertRaises(AssertionError):
            notify_vendors_of_orders_via_email(order.pk)

    @freeze_time("2014-05-06 10:00:00")
    def test_get_json_payload_BST(self):
        user = UserFactory()
        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 5, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 5, 13, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))
        UserProfileFactory(user=user)

        payload = get_json_payload(order)
        expected = "Tue, May 6th 11AM - 12PM"
        assert payload['collection_time'] == expected, payload['collection_time']

        expected = "Tue, May 13th 3PM - 4PM"
        assert payload['delivery_time'] == expected, payload['delivery_time']

    def test_get_order_headline_summary_BST(self):
        user = UserFactory()
        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 5, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 5, 13, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        resp = get_order_headline_summary(order)
        pick_up = "pickup Tue May 06 11-12"
        drop_off = "drop off Tue May 13 15-16"

        assert pick_up in resp, resp
        assert drop_off in resp, resp

    def test_vendor_recipients_for_outcode(self):
        outcodes = [OutCodesFactory(out_code='sw8'),
                    OutCodesFactory(out_code='sw10'),
                    OutCodesFactory(out_code='sw9'),
                    OutCodesFactory(out_code='sw13')]

        users = [UserFactory() for _ in range(0, 4)]
        for user in users:
            UserProfileFactory(user=user,
                               email_notifications_enabled=True)

        # Supports sw8, sw10
        vendor1 = VendorFactory(staff=users[0:2],
                                catchment_area=outcodes[:2])

        # Supports sw10, sw9, sw13
        vendor2 = VendorFactory(staff=users[2:],
                                catchment_area=outcodes[1:])

        self.assertEqual(set(user.email for user in vendor1.staff.all()), vendor_recipients('sw8'))
        self.assertEqual(set(user.email for user in vendor2.staff.all()), vendor_recipients('sw9'))
        all_staff = list(chain(vendor1.staff.all(), vendor2.staff.all()))
        self.assertEqual(set(user.email for user in all_staff), vendor_recipients('sw10'))

    def test_vendor_recipients_no_outcode(self):
        outcodes = [OutCodesFactory(out_code='sw8'),
                    OutCodesFactory(out_code='sw10'),
                    OutCodesFactory(out_code='sw9'),
                    OutCodesFactory(out_code='sw13')]

        users = [UserFactory() for _ in range(0, 4)]
        for user in users:
            UserProfileFactory(user=user,
                               email_notifications_enabled=True)

        # Supports sw8, sw10
        VendorFactory(staff=users[0:2], catchment_area=outcodes[:2])

        # Supports sw10, sw9, sw13
        VendorFactory(staff=users[2:], catchment_area=outcodes[1:])

        # No one supports n1
        OutCodesFactory(out_code='n1')
        self.assertEqual(set(), vendor_recipients('n1'))

    def test_vendor_recipients_all(self):
        outcodes = [OutCodesFactory(out_code='sw8'),
                    OutCodesFactory(out_code='sw10'),
                    OutCodesFactory(out_code='sw9'),
                    OutCodesFactory(out_code='sw13')]

        users = [UserFactory() for _ in range(0, 4)]
        for user in users:
            UserProfileFactory(user=user,
                               email_notifications_enabled=True)

        vendor1 = VendorFactory(staff=users[0:2], catchment_area=outcodes[:2])
        vendor2 = VendorFactory(staff=users[2:], catchment_area=outcodes[1:])

        all_staff = list(chain(vendor1.staff.all(), vendor2.staff.all()))
        self.assertEqual(set(user.email for user in all_staff), vendor_recipients())

    @freeze_time("2014-05-08 03:00:00")
    def test_assign_vendor_payments_clean_and_collect(self):
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        placed_time = datetime.datetime(2014, 4, 13, 14, tzinfo=pytz.utc)
        order = OrderFactory(
            placed_time=placed_time,
            items=items,
            order_status=Order.DELIVERED_BACK_TO_CUSTOMER,
            placed=True,
        )

        DefaultCleanAndCollectPricesFactory(item=item, price=Decimal('1.99'))

        assign_vendor_payments()
        self.assertTrue(hasattr(Order.objects.get(pk=order.pk), 'orderpayments'))
        self.assertEqual(
            Order.objects.get(pk=order.pk).orderpayments.total_amount,
            Decimal('4') * Decimal('1.99')
        )

    @freeze_time("2014-05-08 03:00:00")
    def test_assign_vendor_payments_clean_and_collect_untouched(self):
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        placed_time = datetime.datetime(2014, 4, 13, 14, tzinfo=pytz.utc)
        order = OrderFactory(
            placed_time=placed_time,
            items=items,
            order_status=Order.RECEIVED_BY_VENDOR,
            placed=True,
        )

        DefaultCleanAndCollectPricesFactory(item=item, price=Decimal('1.99'))

        assign_vendor_payments()
        self.assertFalse(hasattr(Order.objects.get(pk=order.pk), 'orderpayments'))

    @freeze_time("2014-05-08 03:00:00")
    def test_assign_vendor_payments_clean_and_collect_set_price(self):
        item = ItemFactory(price=Decimal('17.20'))
        item2 = ItemFactory(price=Decimal('7.10'))
        items = [ItemAndQuantityFactory(quantity=2, item=item),
                 ItemAndQuantityFactory(quantity=1, item=item2)]
        placed_time = datetime.datetime(2014, 4, 13, 14, tzinfo=pytz.utc)
        vendor = VendorFactory()
        order = OrderFactory(
            placed_time=placed_time,
            items=items,
            order_status=Order.DELIVERED_BACK_TO_CUSTOMER,
            placed=True,
            assigned_to_vendor=vendor
        )

        DefaultCleanAndCollectPricesFactory(item=item, price=Decimal('1.99'))
        DefaultCleanAndCollectPricesFactory(item=item2, price=Decimal('2.99'))

        # Vendor specific price
        CleanAndCollectPricesFactory(vendor=vendor, item=item, price=Decimal('1.89'))

        assign_vendor_payments()
        self.assertTrue(hasattr(Order.objects.get(pk=order.pk), 'orderpayments'))

        expected_total = Decimal('2') * Decimal('1.89')
        expected_total += Decimal('2.99')
        self.assertEqual(
            Order.objects.get(pk=order.pk).orderpayments.total_amount,
            expected_total
        )

    @freeze_time("2014-05-08 03:00:00")
    def test_assign_vendor_payments_clean_only_confirmed(self):
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        placed_time = datetime.datetime(2014, 4, 13, 14, tzinfo=pytz.utc)
        order = OrderFactory(
            placed_time=placed_time,
            items=items,
            order_status=Order.RECEIVED_BY_VENDOR,
            placed=True,
        )
        vendor = VendorFactory()
        clean_only_order = CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)
        ExpectedBackCleanOnlyOrderFactory(confirmed_back=True,
                                          clean_only_order=clean_only_order)

        DefaultCleanOnlyPricesFactory(item=item, price=Decimal('1.63'))

        assign_vendor_payments()
        self.assertTrue(hasattr(Order.objects.get(pk=order.pk), 'orderpayments'))
        self.assertEqual(
            Order.objects.get(pk=order.pk).orderpayments.total_amount,
            Decimal('4') * Decimal('1.63')
        )

    @freeze_time("2014-05-08 03:00:00")
    def test_assign_vendor_payments_clean_only_unconfirmed(self):
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        placed_time = datetime.datetime(2014, 4, 13, 14, tzinfo=pytz.utc)
        order = OrderFactory(
            placed_time=placed_time,
            items=items,
            order_status=Order.RECEIVED_BY_VENDOR,
            placed=True,
        )
        vendor = VendorFactory()
        clean_only_order = CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)
        ExpectedBackCleanOnlyOrderFactory(confirmed_back=False,
                                          clean_only_order=clean_only_order)

        DefaultCleanOnlyPricesFactory(item=item, price=Decimal('1.63'))

        assign_vendor_payments()
        self.assertFalse(hasattr(Order.objects.get(pk=order.pk), 'orderpayments'))

    @freeze_time("2014-05-08 03:00:00")
    def test_assign_vendor_payments_clean_only_set_price(self):
        item = ItemFactory(price=Decimal('17.20'))
        item2 = ItemFactory(price=Decimal('7.10'))
        items = [ItemAndQuantityFactory(quantity=2, item=item),
                 ItemAndQuantityFactory(quantity=1, item=item2)]
        placed_time = datetime.datetime(2014, 5, 1, 14, tzinfo=pytz.utc)
        order = OrderFactory(
            placed_time=placed_time,
            items=items,
            order_status=Order.DELIVERED_BACK_TO_CUSTOMER,
            placed=True,
        )
        vendor = VendorFactory()
        clean_only_order = CleanOnlyOrderFactory(order=order, assigned_to_vendor=vendor)
        ExpectedBackCleanOnlyOrderFactory(confirmed_back=True,
                                          clean_only_order=clean_only_order)

        DefaultCleanOnlyPricesFactory(item=item, price=Decimal('1.29'))
        DefaultCleanOnlyPricesFactory(item=item2, price=Decimal('1.82'))

        # Vendor specific price
        CleanOnlyPricesFactory(vendor=vendor, item=item, price=Decimal('1.89'))

        assign_vendor_payments()
        self.assertTrue(hasattr(Order.objects.get(pk=order.pk), 'orderpayments'))

        expected_total = Decimal('2') * Decimal('1.89')
        expected_total += Decimal('1.82')

        self.assertEqual(
            Order.objects.get(pk=order.pk).orderpayments.total_amount,
            expected_total
        )

    @freeze_time("2014-05-08 21:00:00")
    def test_new_orders_assigned_to_default_clean_only_vendor(self):
        placed_time = datetime.datetime(2014, 5, 10, 14, tzinfo=pytz.utc)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        order = OrderFactory(
            placed_time=placed_time,
            order_status=Order.RECEIVED_BY_VENDOR,
            assigned_to_vendor=wishi_washi,
            placed=True,
        )

        default_clean_only_vendor = VendorFactory()

        with self.settings(VENDOR_DEFAULT_CLEAN_ONLY_PK=default_clean_only_vendor.pk):
            assign_all_orders_to_clean_only_vendor()

            order = Order.objects.get(pk=order.pk)
            self.assertTrue(hasattr(order, 'cleanonlyorder'))
            default_vendor = Vendor.objects.get(pk=settings.VENDOR_DEFAULT_CLEAN_ONLY_PK)
            self.assertEqual(order.cleanonlyorder.assigned_to_vendor, default_vendor)

    @freeze_time("2014-05-08 21:00:00")
    def test_new_orders_assigned_to_default_clean_only_vendor_same_day(self):
        placed_time = datetime.datetime(2014, 5, 8, 10, tzinfo=pytz.utc)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        order = OrderFactory(
            placed_time=placed_time,
            order_status=Order.RECEIVED_BY_VENDOR,
            assigned_to_vendor=wishi_washi,
            placed=True,
        )

        default_clean_only_vendor = VendorFactory()

        with self.settings(VENDOR_DEFAULT_CLEAN_ONLY_PK=default_clean_only_vendor.pk):
            assign_all_orders_to_clean_only_vendor()

            order = Order.objects.get(pk=order.pk)
            self.assertTrue(hasattr(order, 'cleanonlyorder'))
            default_vendor = Vendor.objects.get(pk=settings.VENDOR_DEFAULT_CLEAN_ONLY_PK)
            self.assertEqual(order.cleanonlyorder.assigned_to_vendor, default_vendor)

    @freeze_time("2014-05-08 21:00:00")
    def test_only_same_day_orders_assigned_to_default_clean_only_vendor_same_day(self):
        placed_time = datetime.datetime(2014, 5, 7, 10, tzinfo=pytz.utc)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        order = OrderFactory(
            placed_time=placed_time,
            order_status=Order.RECEIVED_BY_VENDOR,
            assigned_to_vendor=wishi_washi,
            placed=True,
        )

        default_clean_only_vendor = VendorFactory()

        with self.settings(VENDOR_DEFAULT_CLEAN_ONLY_PK=default_clean_only_vendor.pk):
            assign_all_orders_to_clean_only_vendor()

            order = Order.objects.get(pk=order.pk)
            self.assertFalse(hasattr(order, 'cleanonlyorder'))

    @freeze_time("2014-05-08 21:00:00")
    def test_not_assigned_to_default_clean_only_vendor_same_day(self):
        placed_time = datetime.datetime(2014, 5, 8, 10, tzinfo=pytz.utc)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        order = OrderFactory(
            placed_time=placed_time,
            order_status=Order.ORDER_REJECTED_BY_SERVICE_PROVIDER,
            assigned_to_vendor=wishi_washi,
            placed=True,
        )

        default_clean_only_vendor = VendorFactory()

        with self.settings(VENDOR_DEFAULT_CLEAN_ONLY_PK=default_clean_only_vendor.pk):
            assign_all_orders_to_clean_only_vendor()

            order = Order.objects.get(pk=order.pk)
            self.assertFalse(hasattr(order, 'cleanonlyorder'))


    @freeze_time("2014-01-09 1:00:00")
    def test_assigned_to_default_clean_only_vendor_within_timelimit(self):
        placed_time = datetime.datetime(2014, 1, 8, 23, 11, tzinfo=pytz.utc)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        order = OrderFactory(
            placed_time=placed_time,
            order_status=Order.CLAIMED_BY_VENDOR,
            assigned_to_vendor=wishi_washi,
            placed=True,
        )

        default_clean_only_vendor = VendorFactory()

        with self.settings(VENDOR_DEFAULT_CLEAN_ONLY_PK=default_clean_only_vendor.pk):
            assign_all_orders_to_clean_only_vendor()

            order = Order.objects.get(pk=order.pk)
            self.assertTrue(hasattr(order, 'cleanonlyorder'))

    @freeze_time("2014-01-09 1:00:00")
    def test_not_assigned_to_default_clean_only_vendor_within_timelimit(self):
        placed_time = datetime.datetime(2014, 1, 8, 0, 59, tzinfo=pytz.utc)
        wishi_washi = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
        order = OrderFactory(
            placed_time=placed_time,
            order_status=Order.CLAIMED_BY_VENDOR,
            assigned_to_vendor=wishi_washi,
            placed=True,
        )

        default_clean_only_vendor = VendorFactory()

        with self.settings(VENDOR_DEFAULT_CLEAN_ONLY_PK=default_clean_only_vendor.pk):
            assign_all_orders_to_clean_only_vendor()

            order = Order.objects.get(pk=order.pk)
            self.assertFalse(hasattr(order, 'cleanonlyorder'))
