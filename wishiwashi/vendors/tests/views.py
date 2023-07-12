import datetime
import json
import pytz
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.http import Http404
from django.test import TestCase
from django.test.client import Client, RequestFactory
from freezegun import freeze_time
import mock

from bookings.models import Address, Order, Vendor, ExpectedBackCleanOnlyOrder
from bookings.factories import (ItemFactory, ItemAndQuantityFactory, OrderFactory, UserFactory, VendorFactory,
                                ExpectedBackCleanOnlyOrderFactory)
from customer_service.models import UserProfile
from ..models import IssueType
from ..tests.patches import create_order, create_vendor, fake_delay
from ..views import (orders_to_pick_up, orders_to_drop_off, orders as orders_page,
                     order_payments, expected_back_clean_only, expected_back_clean_only_confirm,
                     expected_back_clean_only_all, default_prices, pdf_order, orders_to_drop_off_pdf,
                     orders_to_pick_up_pdf, update_order)


def fake_requests(*args, **kwargs):
    pass
fake_requests.status_code = 200
fake_requests.content = "Response"


class Views(TestCase):
    fixtures = ['test_outcodes', 'test_vendor', 'test_categories_and_items',
                'vendor_issues']

    def setUp(self):
        self.client = Client()
        self.vendor = create_vendor(self.client)

        super(Views, self).setUp()

    def test_vendor_no_orders(self):
        resp = self.client.get(reverse('vendors:orders'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-02 08:00:00")
    def test_vendor_one_order(self):
        create_order()

        resp = self.client.get(reverse('vendors:orders'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-02 08:00:00")
    def test_vendor_cannot_view_order_page_before_accepting(self):
        create_order()
        order = Order.objects.all()[0]
        resp = self.client.get(reverse('vendors:order', kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 403)

    @freeze_time("2015-01-02 08:00:00")
    def test_vendor_accept_order(self):
        create_order()
        order = Order.objects.all()[0]
        resp = self.client.get(reverse('vendors:confirm_accept_order', kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 200)

        order = Order.objects.all()[0]
        self.assertEqual(order.assigned_to_vendor, None)

        resp = self.client.post(reverse('vendors:accepted_order', kwargs={'order_pk': order.pk}))
        self.assertRedirects(resp,
                             reverse('vendors:order',
                                     kwargs={'order_pk': order.pk}),
                             status_code=302,
                             target_status_code=200)

        order = Order.objects.all()[0]
        self.assertEqual(order.assigned_to_vendor, self.vendor)

        # If the vendor hits the accept order page again they should be
        # redirected to the order page itself.
        resp = self.client.get(reverse('vendors:confirm_accept_order',
                                       kwargs={'order_pk': order.pk}))

        target = reverse('vendors:order',
                         kwargs={'order_pk': order.pk})
        self.assertRedirects(resp,
                             target,
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-02 08:00:00")
    def test_vendor_cannot_view_other_vendors_order(self):
        create_order()
        order = Order.objects.all()[0]

        addr = Address(flat_number_house_number_building_name='1',
                       address_line_1='High Road',
                       town_or_city='London',
                       postcode='w11aa')
        addr.save()

        another_vendor = Vendor(address=addr)
        another_vendor.save()
        order.assigned_to_vendor = another_vendor
        order.save()

        resp = self.client.get(reverse('vendors:confirm_accept_order',
                                       kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('Another vendor has managed to accept this order',
                      resp.content)

        resp = self.client.post(reverse('vendors:accepted_order',
                                        kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 403)

    @freeze_time("2015-01-02 08:00:00")
    def test_vendor_cannot_accept_order_more_than_x_days_old(self):
        create_order()
        order = Order.objects.all()[0]

        order.placed = True
        order.placed_time = datetime.datetime(2015, 1, 2, 8, 0, 0, tzinfo=pytz.utc) - datetime.timedelta(days=8)
        order.save()

        resp = self.client.get(reverse('vendors:confirm_accept_order', kwargs={'order_pk': order.pk}))

        self.assertEqual(resp.status_code, 404)
        self.assertTrue("Unable to locate the order" in resp.content)

    @freeze_time("2015-01-02 08:00:00")
    def test_get_latest_orders(self):
        create_order()

        # HTTP GET should fail, HTTP POST is the only verb allowed
        resp = self.client.get(reverse('vendors:get_latest_orders'))
        self.assertEqual(resp.status_code, 405)

        resp = self.client.post(reverse('vendors:get_latest_orders'))
        self.assertEqual(resp.status_code, 200)

        resp = json.loads(resp.content)
        self.assertEqual(len(resp['orders']), 1)
        self.assertEqual(sorted(resp['orders'][0].keys()),
                         ['confirm_accept_order_url',
                          'created',
                          'drop_off_time',
                          'is_taken_by_other_vendor',
                          'is_taken_by_requester',
                          'order_url',
                          'pick_up_time',
                          'pk',
                          'postcode',
                          'total_price_of_order'])

        order_pk = Order.objects.all()[0].pk
        self.assertEqual(resp['orders'][0]["confirm_accept_order_url"],
                         reverse('vendors:confirm_accept_order',
                                 kwargs={'order_pk': order_pk}))
        self.assertEqual(resp['orders'][0]["total_price_of_order"], "7.00")
        self.assertEqual(resp['orders'][0]["order_url"],
                         reverse('vendors:order',
                                 kwargs={'order_pk': order_pk}))
        self.assertEqual(resp['orders'][0]["postcode"], "W1 1AA")
        self.assertEqual(resp['orders'][0]["created"], "now")
        self.assertEqual(resp['orders'][0]["is_taken_by_other_vendor"], False)
        self.assertEqual(resp['orders'][0]["pk"], order_pk)
        self.assertEqual(resp['orders'][0]["drop_off_time"],
                         "Mon, Jan 5th 10AM - 11AM")
        self.assertEqual(resp['orders'][0]["is_taken_by_requester"], False)
        self.assertEqual(resp['orders'][0]["pick_up_time"],
                         "Sat, Jan 3rd 10AM - 11AM")

    @freeze_time("2014-04-04 08:00:00")
    def test_get_latest_orders_BST(self):
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        now = datetime.datetime(2014, 4, 4, 8, tzinfo=pytz.utc)
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        order = OrderFactory(placed_time=now,
                             placed=True,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items)

        resp = self.client.post(reverse('vendors:get_latest_orders'))
        self.assertEqual(resp.status_code, 200)

        resp = json.loads(resp.content)
        self.assertEqual(len(resp['orders']), 1)
        self.assertEqual(sorted(resp['orders'][0].keys()),
                         ['confirm_accept_order_url',
                          'created',
                          'drop_off_time',
                          'is_taken_by_other_vendor',
                          'is_taken_by_requester',
                          'order_url',
                          'pick_up_time',
                          'pk',
                          'postcode',
                          'total_price_of_order'])

        self.assertEqual(resp['orders'][0]["confirm_accept_order_url"],
                         reverse('vendors:confirm_accept_order',
                                 kwargs={'order_pk': order.pk}))

        self.assertEqual(resp['orders'][0]["pk"], order.pk)

        # British summer time UTC + 1 hour
        self.assertEqual(resp['orders'][0]["drop_off_time"],
                         "Thu, Apr 10th 3PM - 4PM")
        self.assertEqual(resp['orders'][0]["is_taken_by_requester"], False)
        self.assertEqual(resp['orders'][0]["pick_up_time"],
                         "Mon, Apr 7th 11AM - 12PM")

    @freeze_time("2015-01-02 08:00:00")
    def test_get_latest_orders_no_results(self):
        resp = self.client.post(reverse('vendors:get_latest_orders'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-02 08:00:00")
    def test_get_latest_orders_unparsable_last_order_id(self):
        create_order()

        resp = self.client.post(reverse('vendors:get_latest_orders'),
                                {'latest_order_id': None})
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.content)
        self.assertEqual(len(resp['orders']), 1)

    @freeze_time("2015-01-02 08:00:00")
    def test_get_latest_orders_get_back_orders(self):
        for _ in range(0, 5):
            create_order()

        for order in Order.objects.all():
            resp = self.client.post(reverse('vendors:get_latest_orders'),
                                    {'latest_order_id': order.pk})
            self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-02 08:00:00")
    def test_get_latest_orders_no_more_than_50(self):
        for _ in range(0, 60):
            create_order()
        resp = self.client.post(reverse('vendors:get_latest_orders'),
                                {'latest_order_id': None})
        self.assertEqual(resp.status_code, 200)
        resp = json.loads(resp.content)
        self.assertEqual(len(resp['orders']), 50)

    def test_get_latest_orders_newer_than_two_days(self):
        with freeze_time("2014-01-02 08:00:00"):
            create_order(pick_up_time='2014-01-03 10',
                         delivery_time='2014-01-05 10')

        with freeze_time("2015-01-02 08:00:00"):
            resp = self.client.post(reverse('vendors:get_latest_orders'),
                                    {'latest_order_id': None})
            self.assertEqual(resp.status_code, 200)
            resp = json.loads(resp.content)
            self.assertEqual(len(resp['orders']), 0)

    def test_orders_to_pick_up(self):
        create_order()
        resp = self.client.get(reverse('vendors:orders_to_pick_up'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-05 07:00:00")
    def test_orders_to_drop_off(self):
        create_order()
        resp = self.client.get(reverse('vendors:orders_to_drop_off'))
        self.assertEqual(resp.status_code, 200)

    def test_order_history_empty(self):
        resp = self.client.get(reverse('vendors:order_history'))
        self.assertEqual(resp.status_code, 200)

    def test_order_history_populated(self):
        create_order()
        resp = self.client.get(reverse('vendors:order_history'))
        self.assertEqual(resp.status_code, 200)

    def test_operating_hours(self):
        resp = self.client.get(reverse('vendors:operating_hours'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['hours'], range(0, 25))

    def test_operating_hours_valid_post(self):
        payload = {
            'opening_0': '0',
            'closing_0': '24',
            'opening_1': '0',
            'closing_1': '24',
            'opening_2': '0',
            'closing_2': '24',
            'opening_3': '0',
            'closing_3': '24',
            'opening_4': '0',
            'closing_4': '24',
            'opening_5': '0',
            'closing_5': '24',
        }
        resp = self.client.post(reverse('vendors:operating_hours'), payload)
        self.assertEqual(resp.status_code, 200)

    def test_operating_hours_invalid_post(self):
        payload = {
            # Opening after closing
            'opening_0': '24',
            'closing_0': '0',

            'opening_1': '0',
            'closing_1': '24',
            'opening_2': '0',
            'closing_2': '24',
            'opening_3': '0',
            'closing_3': '24',
            'opening_4': '0',
            'closing_4': '24',
            'opening_5': '0',
            'closing_5': '24',
        }
        resp = self.client.post(reverse('vendors:operating_hours'), payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['form'].errors.keys(), ['closing_0'])
        self.assertEqual(resp.context['form'].errors['closing_0'][0],
                         'The closing time needs to be after the opening time')

    def test_postcodes_served(self):
        resp = self.client.get(reverse('vendors:postcodes_served'))
        self.assertEqual(resp.status_code, 200)

    def test_postcodes_served_change_catchment(self):
        payload = {
            'SW1A': '0',
            'SW15': '1',
            'SW14': '1',
            'SW17': '1',
            'SW16': '1',
            'SW11': '1',
            'SW10': '1',
            'SW13': '1',
            'SW12': '1',
            'W1W': '1',
            'W1V': '1',
            'W1U': '1',
            'W1T': '1',
            'SW19': '1',
            'SW18': '1',
            'W1P': '1',
            'W1N': '1',
            'W1M': '1',
            'W1K': '1',
            'W1J': '1',
            'W1H': '1',
            'W1G': '1',
            'W1F': '1',
            'W1E': '1',
            'W1D': '1',
            'W1C': '1',
            'W1B': '1',
            'W1A': '1',
            'W12': '1',
            'SW1E': '1',
            'SW99': '1',
            'W1Y': '1',
            'W6': '1',
            'SW95': '1',
            'W1X': '1',
            'W9': '1',
            'W3': '1',
            'W7': '1',
            'W1S': '1',
            'W8': '1',
            'W1R': '1',
            'W10': '1',
            'SW20': '1',
            'SW1W': '1',
            'SW1V': '1',
            'W13': '1',
            'SW1P': '1',
            'W14': '1',
            'SW1Y': '1',
            'SW1X': '1',
            'W11': '1',
            'SW1H': '1',
            'SW9': '1',
            'SW8': '1',
            'W5': '1',
            'W4': '1',
            'W2': '1',
            'W1': '1',
            'SW3': '1',
            'SW2': '1',
            'SW5': '1',
            'SW4': '1',
            'SW7': '1',
            'SW6': '1',
        }

        resp = self.client.post(reverse('vendors:postcodes_served'), payload)
        self.assertEqual(resp.status_code, 200)

    def test_contact_details_and_notifications(self):
        url = reverse('vendors:contact_details_and_notifications')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['successfully_modified'])

    def test_contact_details_and_notifications_bad_mobile(self):
        url = reverse('vendors:contact_details_and_notifications')
        payload = {
            'email_address': 'bad_email_address',
            'mobile_number': '+44 7712 123 456',
            'notify_via_email': False,
            'notify_via_sms': False,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['successfully_modified'])

    def test_contact_details_and_notifications_bad_mobile_number(self):
        url = reverse('vendors:contact_details_and_notifications')
        payload = {
            'email_address': 'user@server.com',
            'mobile_number': '+372 5123 456',
            'notify_via_email': False,
            'notify_via_sms': False,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['successfully_modified'])

        self.assertEqual(resp.context['form'].errors['mobile_number'][0],
                         'You must use a British mobile number.')

        payload = {
            'email_address': 'user@server.com',
            'mobile_number': '+44 020 7123 456',
            'notify_via_email': False,
            'notify_via_sms': False,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['successfully_modified'])
        self.assertEqual(resp.context['form'].errors['mobile_number'][0],
                         'You must use a British mobile number (land lines are '
                         'not supported).')

    def test_contact_details_and_notifications_save(self):
        url = reverse('vendors:contact_details_and_notifications')
        payload = {
            'email_address': 'user@server.com',
            'mobile_number': '+44 7712 123 456',
            'notify_via_email': False,
            'notify_via_sms': True,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['successfully_modified'])

        user = self.vendor.staff.all()[0]
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(user.email, 'user@server.com')
        self.assertEqual(profile.mobile_number, '00447712123456')
        self.assertEqual(profile.email_notifications_enabled, False)
        self.assertEqual(profile.sms_notifications_enabled, True)

        # Change again
        payload = {
            'email_address': 'user1@server1.com',
            'mobile_number': '+44 7713 123 456',
            'notify_via_email': True,
            'notify_via_sms': False,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['successfully_modified'])

        user = self.vendor.staff.all()[0]
        profile = UserProfile.objects.get(user=user)
        self.assertEqual(user.email, 'user1@server1.com')
        self.assertEqual(profile.mobile_number, '00447713123456')
        self.assertEqual(profile.email_notifications_enabled, True)
        self.assertEqual(profile.sms_notifications_enabled, False)

    def test_contact_details_and_notifications_cannot_take_others_details(self):
        vendor2 = create_vendor(client=None, create_new_vendor=True)
        user2 = vendor2.staff.all()[0]
        profile2 = UserProfile.objects.get(user=user2)
        profile2.mobile_number = '00447911123456'
        profile2.save()

        url = reverse('vendors:contact_details_and_notifications')
        payload = {
            'email_address': user2.email,
            'mobile_number': '+44 7712 123 456',
            'notify_via_email': False,
            'notify_via_sms': True,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['successfully_modified'])
        self.assertEqual(resp.context['form'].errors['email_address'][0],
                         'There is already an account with this email address.')

        url = reverse('vendors:contact_details_and_notifications')
        payload = {
            'email_address': 'user1@server1.com',
            'mobile_number': profile2.mobile_number,
            'notify_via_email': False,
            'notify_via_sms': True,
        }

        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['successfully_modified'])
        self.assertEqual(resp.context['form'].errors['mobile_number'][0],
                         'There is an existing account using this mobile number, please use another mobile number.')

    def test_issue_raised(self):
        create_order()
        order = Order.objects.all()[0]
        order.assigned_to_vendor = self.vendor
        order.save()

        resp = self.client.get(reverse('vendors:issue_raised',
                                       kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_issue_raised_order_not_assigned_to_vendor(self):
        create_order()
        order = Order.objects.all()[0]

        resp = self.client.get(reverse('vendors:issue_raised',
                                       kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_issue_raised_missing_pk(self):
        resp = self.client.get(reverse('vendors:issue_raised',
                                       kwargs={'order_pk': 0}))
        self.assertEqual(resp.status_code, 404)

    def _create_order_and_assign_to_me(self):
        create_order()
        order = Order.objects.all()[0]
        order.assigned_to_vendor = self.vendor
        order.save()

        return order

    def test_order(self):
        order = self._create_order_and_assign_to_me()

        resp = self.client.get(reverse('vendors:order',
                                       kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_order_page_missing_pk(self):
        resp = self.client.get(reverse('vendors:order',
                                       kwargs={'order_pk': 0}))
        self.assertEqual(resp.status_code, 404)

    def test_order_not_assigned_to_vendor(self):
        create_order()
        order = Order.objects.all()[0]

        resp = self.client.get(reverse('vendors:order',
                                       kwargs={'order_pk': order.pk}))
        self.assertEqual(resp.status_code, 403)

    def _raise_issue(self, payload, already_received_by_vendor=False,
                     return_resp=False):
        order = self._create_order_and_assign_to_me()

        if already_received_by_vendor:
            order.order_status = Order.RECEIVED_BY_VENDOR
            order.save()

        url = reverse('vendors:order', kwargs={'order_pk': order.pk})
        target = reverse('vendors:issue_raised', kwargs={'order_pk': order.pk})

        resp = self.client.post(url, payload)

        if return_resp:
            return (resp, order.pk)

        self.assertRedirects(resp,
                             target,
                             status_code=302,
                             target_status_code=200)

        return (resp, order.pk)

    def test_order_raise_contact_issue(self):
        issue = IssueType.objects.filter(category=IssueType.CONTACT_DETAILS)[0]

        payload = {
            'vendor_issue_contact_issue_pk': issue.pk
        }
        self._raise_issue(payload)

    def test_order_raise_other_contact_issue(self):
        payload = {
            'vendor_issue_contact_issue_pk': -1,
            'other_contact_issue_details': 'Content'
        }
        self._raise_issue(payload)

    def test_order_raise_empty_other_contact_issue(self):
        payload = {
            'vendor_issue_contact_issue_pk': -1,
            'other_contact_issue_details': ''
        }
        resp, order_pk = self._raise_issue(payload, False, True)
        self.assertEqual(resp.context['form'].errors.keys(),
                         ['other_contact_issue_details'])

    def test_order_raise_too_long_other_contact_issue(self):
        payload = {
            'vendor_issue_contact_issue_pk': -1,
            'other_contact_issue_details': 'a' * 5000
        }
        resp, order_pk = self._raise_issue(payload, False, True)
        self.assertEqual(resp.context['form'].errors.keys(),
                         ['other_contact_issue_details'])

    def test_order_raise_contact_issue_received_order(self):
        issue = IssueType.objects.filter(category=IssueType.CONTACT_DETAILS)[0]

        payload = {
            'vendor_issue_contact_issue_pk': issue.pk
        }
        self._raise_issue(payload, True)

    def test_order_raise_delivery_issue(self):
        issue = IssueType.objects.filter(category=IssueType.PICK_UP_DROP_OFF_DETAILS)[0]

        payload = {
            'vendor_pick_up_and_delivery_issue_pk': issue.pk
        }
        self._raise_issue(payload)

    def test_order_raise_other_delivery_issue(self):
        payload = {
            'vendor_pick_up_and_delivery_issue_pk': -1,
            'other_pick_up_and_delivery_issue_details': 'Content'
        }
        self._raise_issue(payload)

    def test_order_raise_empty_other_delivery_issue(self):
        payload = {
            'vendor_pick_up_and_delivery_issue_pk': -1,
            'other_pick_up_and_delivery_issue_details': ''
        }
        resp, order_pk = self._raise_issue(payload, False, True)
        self.assertEqual(resp.context['form'].errors.keys(),
                         ['other_pick_up_and_delivery_issue_details'])

    def test_order_raise_too_long_other_delivery_issue(self):
        payload = {
            'vendor_pick_up_and_delivery_issue_pk': -1,
            'other_pick_up_and_delivery_issue_details': 'a' * 5000
        }
        resp, order_pk = self._raise_issue(payload, False, True)
        self.assertEqual(resp.context['form'].errors.keys(),
                         ['other_pick_up_and_delivery_issue_details'])

    def test_order_raise_delivery_issue_already_received(self):
        issue = IssueType.objects.filter(category=IssueType.PICK_UP_DROP_OFF_DETAILS)[0]

        payload = {
            'vendor_pick_up_and_delivery_issue_pk': issue.pk
        }
        self._raise_issue(payload, True)

    def test_order_raise_item_issue(self):
        issue = IssueType.objects.filter(category=IssueType.ITEMS)[0]

        payload = {
            'vendor_items_issue_pk': issue.pk,
            'item_pk': 28,
        }
        self._raise_issue(payload)

    def test_order_raise_other_item_issue(self):
        payload = {
            'vendor_items_issue_pk': -1,
            'item_pk': 28,
            'other_items_issue_details': 'Content'
        }
        self._raise_issue(payload)

    def test_order_raise_empty_other_items_issue(self):
        payload = {
            'vendor_items_issue_pk': -1,
            'item_pk': 28,
            'other_items_issue_details': ''
        }
        resp, order_pk = self._raise_issue(payload, False, True)
        self.assertEqual(resp.context['form'].errors.keys(),
                         ['other_items_issue_details'])

    def test_order_raise_too_long_other_items_issue(self):
        payload = {
            'vendor_items_issue_pk': -1,
            'item_pk': 28,
            'other_items_issue_details': 'a' * 5000
        }
        resp, order_pk = self._raise_issue(payload, False, True)
        self.assertEqual(resp.context['form'].errors.keys(),
                         ['other_items_issue_details'])

    @freeze_time("2014-04-07 08:00:00")
    def test_orders_to_pick_up_BST(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        OrderFactory(placed=True,
                     order_status=Order.CLAIMED_BY_VENDOR,
                     assigned_to_vendor=vendor,
                     pick_up_time=pick_up_time,
                     drop_off_time=drop_off_time,
                     items=items)

        request = RequestFactory().get(reverse('vendors:orders_to_pick_up'))
        request.user = user

        response = orders_to_pick_up(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday 7th Apr 11AM")
        self.assertContains(response, "Thursday 10th Apr 3PM")

    @freeze_time("2014-04-10 08:00:00")
    def test_orders_to_drop_off_BST(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        OrderFactory(placed=True,
                     order_status=Order.RECEIVED_BY_VENDOR,
                     assigned_to_vendor=vendor,
                     pick_up_time=pick_up_time,
                     drop_off_time=drop_off_time,
                     items=items)

        request = RequestFactory().get(reverse('vendors:orders_to_drop_off'))
        request.user = user

        response = orders_to_drop_off(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Monday 7th Apr 11AM")
        self.assertContains(response, "Thursday 10th Apr 3PM")

    @freeze_time("2014-04-06 08:00:00")
    def test_orders_BST(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        created = datetime.datetime(2014, 4, 6, 8, tzinfo=pytz.utc)
        OrderFactory(created=created,
                     authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                     assigned_to_vendor=vendor,
                     pick_up_time=pick_up_time,
                     drop_off_time=drop_off_time,
                     items=items)

        request = RequestFactory().get(reverse('vendors:orders'))
        request.user = user

        response = orders_page(request)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mon, Apr 7th 11AM - 12PM")
        self.assertContains(response, "Thu, Apr 10th 3PM - 4PM")

    @freeze_time("2014-04-06 08:00:00")
    @mock.patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
                fake_delay)
    def test_throw_orders_back_in_pool(self):
        create_order()
        order = Order.objects.all()[0]
        order.order_status = Order.CLAIMED_BY_VENDOR
        order.pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order.drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order.assigned_to_vendor = self.vendor
        order.save()

        with self.settings(VENDOR_WISHI_WASHI_PK=self.vendor.pk):
            resp = self.client.post(reverse('vendors:throw_orders_back_in_pool'),
                                    {'order_%d' % order.pk: 'on'})
            self.assertEqual(resp.status_code, 200)
            self.assertIn('1 order has been thrown back into the pool', resp.content)

    @freeze_time("2014-04-06 08:00:00")
    @mock.patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
                fake_delay)
    def test_throw_orders_back_in_pool_within_three_hours(self):
        create_order()
        order = Order.objects.all()[0]
        order.order_status = Order.CLAIMED_BY_VENDOR
        order.pick_up_time = datetime.datetime(2014, 4, 6, 10, tzinfo=pytz.utc)
        order.drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order.assigned_to_vendor = self.vendor
        order.save()

        with self.settings(VENDOR_WISHI_WASHI_PK=self.vendor.pk):
            resp = self.client.post(reverse('vendors:throw_orders_back_in_pool'),
                                    {'order_%d' % order.pk: 'on'})
            self.assertEqual(resp.status_code, 200)
            self.assertIn('0 orders have been thrown back into the pool', resp.content)
            self.assertIn("But 1 order could not be thrown back in because "
                          "the pick up time is within the next three hours.",
                          resp.content)

    @freeze_time("2014-04-06 08:00:00")
    def test_throw_orders_back_in_pool_only_wishi_washi_can_use(self):
        create_order()
        order = Order.objects.all()[0]

        addr = Address(flat_number_house_number_building_name='1',
                       address_line_1='High Road',
                       town_or_city='London',
                       postcode='w11aa')
        addr.save()

        another_vendor = Vendor(address=addr)
        another_vendor.save()
        order.assigned_to_vendor = another_vendor
        order.save()

        with self.settings(VENDOR_WISHI_WASHI_PK=1000):
            resp = self.client.post(reverse('vendors:throw_orders_back_in_pool'), {'order_%d' % order.pk: 'on'})
            self.assertEqual(resp.status_code, 403)
            self.assertIn('You are not allowed to use this functionality.', resp.content)

    def test_tagging_non_wishi_washi(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        request = RequestFactory().get(reverse('vendors:orders'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=int(1+vendor.pk)):
            response = orders_page(request)
            self.assertNotContains(response, "Orders to tag")
            self.assertNotContains(response, reverse("vendors:orders_to_tag"))

    def test_tagging_wishi_washi_can_view(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        request = RequestFactory().get(reverse('vendors:orders'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = orders_page(request)
            self.assertContains(response, "Orders to tag")
            self.assertContains(response, reverse("vendors:orders_to_tag"))

    def test_order_payments_non_wishi_washi(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        request = RequestFactory().get(reverse('vendors:order_payments'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=int(1+vendor.pk)):
            response = orders_page(request)
            self.assertNotContains(response, "Payments")
            self.assertNotContains(response, reverse("vendors:order_payments"))

            request = RequestFactory().get(reverse('vendors:order_payments'))
            request.user = user
            response = order_payments(request)
            self.assertEqual(response.status_code, 403)

    def test_order_payments_wishi_washi_can_view(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        request = RequestFactory().get(reverse('vendors:orders'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = orders_page(request)
            self.assertContains(response, "Payments")
            self.assertContains(response, reverse("vendors:order_payments"))

            request = RequestFactory().get(reverse('vendors:order_payments'))
            request.user = user
            response = order_payments(request)
            self.assertEqual(response.status_code, 200)

    def test_vendor_view_upcoming(self):
        resp = self.client.get(reverse('vendors:upcoming'))
        self.assertEqual(resp.status_code, 200)

    def test_expected_back_clean_only_confirm(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        r = ExpectedBackCleanOnlyOrderFactory()
        request = RequestFactory().post(reverse('vendors:expected_back_clean_only_confirm'), {'id': r.id})
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = expected_back_clean_only_confirm(request)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(ExpectedBackCleanOnlyOrder.objects.get(pk=r.id).confirmed_back)

    def test_expected_back_clean_only_confirm_error(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        request = RequestFactory().post(reverse('vendors:expected_back_clean_only_confirm'), {'id': 211})
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = expected_back_clean_only_confirm(request)
            self.assertEqual(response.status_code, 400)

    def test_expected_back_clean_only_confirm_non_wishi_washi(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        r = ExpectedBackCleanOnlyOrderFactory()
        request = RequestFactory().post(reverse('vendors:expected_back_clean_only_confirm'), {'id': r.id})
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk+1):
            response = expected_back_clean_only_confirm(request)
            self.assertEqual(response.status_code, 403)

    def test_expected_back_clean_only_all_non_wishi_washi(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        request = RequestFactory().get(reverse('vendors:expected_back_clean_only_all'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk+1):
            response = expected_back_clean_only_all(request)
            self.assertEqual(response.status_code, 403)

    def test_expected_back_clean_only_all_wishi_washi(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        request = RequestFactory().get(reverse('vendors:expected_back_clean_only_all'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = expected_back_clean_only_all(request)
            self.assertEqual(response.status_code, 200)

    def test_default_prices_non_wishi_washi(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        request = RequestFactory().get(reverse('vendors:default_prices'))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk+1):
            response = default_prices(request)
            self.assertEqual(response.status_code, 403)

    def test_pdf_order_not_owned_by_vendor(self):
        user = UserFactory()
        VendorFactory(staff=[user])
        vendor2 = VendorFactory()
        order = OrderFactory(placed=True, assigned_to_vendor=vendor2)

        request = RequestFactory().post(reverse('vendors:pdf_order', kwargs={'order_pk': order.pk}))
        request.user = user

        self.assertRaises(Http404, pdf_order, request, order.pk)

    def test_pdf_order_not_found(self):
        user = UserFactory()
        VendorFactory(staff=[user])

        request = RequestFactory().post(reverse('vendors:pdf_order', kwargs={'order_pk': 12345678}))
        request.user = user

        self.assertRaises(Http404, pdf_order, request, 12345678)

    @mock.patch('vendors.pdf.requests.post')
    def test_pdf_order(self, mock_post):
        mock_post.return_value = fake_requests
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        order = OrderFactory(placed=True, assigned_to_vendor=vendor)

        request = RequestFactory().post(reverse('vendors:pdf_order', kwargs={'order_pk': order.pk}))
        request.user = user
        response = pdf_order(request, order.pk)
        self.assertEqual(200, response.status_code)

    def test_orders_to_drop_off_no_files_pdf(self):
        user = UserFactory()
        VendorFactory(staff=[user])
        request = RequestFactory().post(reverse('vendors:orders_to_drop_off_pdf'))
        request.user = user

        self.assertRaises(Http404, orders_to_drop_off_pdf, request)

    def test_orders_to_pick_up_no_files_pdf(self):
        user = UserFactory()
        VendorFactory(staff=[user])
        request = RequestFactory().post(reverse('vendors:orders_to_pick_up_pdf'))
        request.user = user

        self.assertRaises(Http404, orders_to_pick_up_pdf, request)

    @freeze_time("2014-04-07 08:00:00")
    def test_expected_back_clean_only_alert(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])
        expected_back = datetime.datetime(2014, 4, 5, 10, tzinfo=pytz.utc)
        expected_back = ExpectedBackCleanOnlyOrderFactory(expected_back=expected_back)
        order = expected_back.clean_only_order.order
        request = RequestFactory().get(reverse('vendors:expected_back_clean_only'))
        request.user = user
        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = expected_back_clean_only(request)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, '{}'.format(order.uuid))
            self.assertContains(response, '<h3>Unconfirmed orders</h3>'.format(order.uuid))

    def test_weekly_upcoming(self):
        resp = self.client.get(reverse('vendors:weekly_upcoming'))
        self.assertEqual(resp.status_code, 200)

    def test_update_order_wishi_washi_can_access(self):
        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        order = OrderFactory(placed=True, order_status=Order.RECEIVED_BY_VENDOR, assigned_to_vendor=vendor, items=items)

        request = RequestFactory().get(reverse('vendors:update_order', kwargs={'order_pk': order.pk}))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=vendor.pk):
            response = update_order(request, order.id)
            self.assertEqual(response.status_code, 200)

    def test_update_order_wishi_washi_cannot_access(self):
        wishi_washi = VendorFactory()

        user = UserFactory()
        vendor = VendorFactory(staff=[user])

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        order = OrderFactory(placed=True, order_status=Order.RECEIVED_BY_VENDOR, assigned_to_vendor=vendor, items=items)

        request = RequestFactory().get(reverse('vendors:update_order', kwargs={'order_pk': order.pk}))
        request.user = user

        with self.settings(VENDOR_WISHI_WASHI_PK=wishi_washi.pk):
            response = update_order(request, order.id)
            self.assertEqual(response.status_code, 403)


