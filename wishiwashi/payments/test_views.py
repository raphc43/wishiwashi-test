import time
import datetime
import uuid
from decimal import Decimal

from django.conf import settings
from django.test import TestCase, Client
from django.test.client import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.core.urlresolvers import reverse
from django.utils import timezone
from freezegun import freeze_time
from mock import patch
import stripe
import pytz

from base.middleware import SetRemoteAddrForwardedFor
from bookings.factories import (UserFactory,
                                AddressFactory,
                                OrderFactory,
                                ItemFactory,
                                ItemAndQuantityFactory,
                                TrackConfirmedOrderSlotsFactory,
                                VoucherFactory,)
from bookings.models import (Address, Item, ItemAndQuantity, Order,
                             TrackConfirmedOrderSlots, Voucher)
from bookings.tickets import THRESHOLD
from bookings.tests import add_session_to_request
from vendors.tests.patches import fake_delay

from .models import Stripe
from .views import landing, timestamp_to_datetime_str, charge


def delay(order_id):
    pass


@patch('payments.views.order_confirmation_for_customer_via_email.delay', delay)
class Views(TestCase):
    fixtures = ['test_outcodes', 'test_vendor', 'test_categories_and_items']

    def setUp(self):
        self.client = Client()
        super(Views, self).setUp()

    def _populate_session(self, session_data):
        """
        :param dict session_data: keys and values to set in the session
        """
        self.client.get(reverse('landing'))

        session = self.client.session

        for _key, _value in session_data.iteritems():
            session[_key] = _value
        session.save()

    def _create_and_login_user(self):
        username = password = str(uuid.uuid4())[:28]
        self.user = UserFactory(username=username, password=password)
        logged_in = self.client.login(username=username,
                                      password=password)
        self.assertTrue(logged_in)

    def _valid_session(self):
        addr = Address()
        addr.save()
        order = Order(pick_up_and_delivery_address=addr,
                      pick_up_time='2015-01-06T10:00:00Z',
                      drop_off_time='2015-01-09T18:00:00Z',
                      customer=self.user)
        order.save()

        item_quantity = ItemAndQuantity()
        item_quantity.item = Item.objects.get(pk=1)
        item_quantity.quantity = 2
        item_quantity.save()
        order.items.add(item_quantity)

        self._populate_session({
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {'1': 2},
            'address': AddressFactory().pk,
            'order': order.pk
        })

    def test_landing_page_redirects_unauthenticated_user(self):
        request = RequestFactory().get(reverse('payments:landing'))
        request.user = AnonymousUser()

        response = landing(request)
        self.assertEqual(302, response.status_code)

    @freeze_time("2015-01-05 10:00:00")
    def test_landing_page(self):
        self._create_and_login_user()
        self._valid_session()

        response = self.client.get(reverse('payments:landing'))
        self.assertContains(response, reverse('payments:charge'), count=2)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_card_error(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.CardError(
                message="Declined",
                param="Card",
                code="incorrect_number",
                http_status=402,
                json_body={'error': {'message': 'Card Declined'}})

            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response, "Card Declined", count=2)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_invalid_request(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.InvalidRequestError(
                message="Invalid Request",
                http_status=400,
                param=None,
                json_body={'error': {'message': 'Charge invalid'}})
            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response, "Payment cannot be taken", count=2)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_authentication_failure(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.AuthenticationError(
                message="Authentication Error",
                http_status=500,
                json_body={'error': {'message': 'Authentication error'}})
            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response, "Payment cannot be taken", count=2)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_api_failure(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.APIConnectionError(
                message="Server Error",
                http_status=500,
                json_body={'error': {'message': 'Server side error'}})
            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response, "Payment cannot be taken", count=2)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_form_failure(self):
        self._create_and_login_user()
        self._valid_session()

        response = self.client.post(reverse('payments:charge'), {})
        self.assertFormError(response, 'form', 'stripeToken',
                             [u'Please enter your payment details.'])

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_return_failure(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            mock_charge.return_value = None
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response,
                                "Unable to charge your credit card",
                                count=2)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_id_set_session(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('bookings:order_placed'))
            self.assertIn("stripe_charge_id", self.client.session)
            self.assertIn("stripe_created", self.client.session)

            self.assertEquals(test_charge.id,
                              self.client.session["stripe_charge_id"])
            self.assertEquals(
                timestamp_to_datetime_str(int(test_charge.created)),
                self.client.session["stripe_created"])

    @freeze_time("2015-01-05 10:00:00")
    def test_timestamp_not_set(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"

            mock_charge.return_value = charge()
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response,
                                "Unable to charge your credit card",
                                count=2)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_authorisation_flag_set(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('bookings:order_placed'))

            self.assertEqual(response.context['order'].authorisation_status,
                             Order.SUCCESSFULLY_AUTHORISED)

            past_dt = timezone.now() - datetime.timedelta(minutes=1)
            future_dt = timezone.now() + datetime.timedelta(minutes=1)

            self.assertTrue(response.context['order'].placed)
            placed_dt = response.context['order'].placed_time
            self.assertTrue(past_dt < placed_dt < future_dt)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            last_dt = stripe_charge.last_authorised_charge_time
            self.assertTrue(past_dt < last_dt < future_dt)

    @freeze_time("2015-01-05 10:00:00")
    def test_card_error_authorisation_flag_set(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.CardError(
                message="Declined",
                param="Card",
                code="incorrect_number",
                http_status=402,
                json_body={'error': {'message': 'Card Declined'}})

            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))

            self.assertEqual(Order.objects.get(
                pk=self.client.session['order']).authorisation_status,
                Order.FAILED_TO_AUTHORISE
            )

            self.assertIsNone(Order.objects.get(
                pk=self.client.session['order']
            ).placed_time)

            self.assertFalse(response.context['order'].placed)

            past_dt = timezone.now() - datetime.timedelta(minutes=1)
            future_dt = timezone.now() + datetime.timedelta(minutes=1)

            order = Order.objects.get(pk=self.client.session['order'])
            stripe_charge = Stripe.objects.get(order=order)
            last_dt = stripe_charge.last_authorised_charge_time
            self.assertTrue(past_dt < last_dt < future_dt)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_exception_authorisation_flag_set(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = Exception("Error")
            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))

            self.assertEqual(Order.objects.get(
                pk=self.client.session['order']).authorisation_status,
                Order.FAILED_TO_AUTHORISE
            )

            self.assertFalse(response.context['order'].placed)

            self.assertIsNone(Order.objects.get(
                pk=self.client.session['order']
            ).placed_time)

            past_dt = timezone.now() - datetime.timedelta(minutes=1)
            future_dt = timezone.now() + datetime.timedelta(minutes=1)

            order = Order.objects.get(pk=self.client.session['order'])
            stripe_charge = Stripe.objects.get(order=order)
            last_dt = stripe_charge.last_authorised_charge_time
            self.assertTrue(past_dt < last_dt < future_dt)

    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay', fake_delay)
    @freeze_time("2015-01-05 10:00:00")
    def test_card_error_cvc_check_fail_passes(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "fail"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'), payload, follow=True)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertFalse(stripe_charge.cvv2_code_check_passed)
            self.assertTrue(stripe_charge.postcode_check_passed)
            self.assertEqual(stripe_charge.authorisation_status,
                             Stripe.SUCCESSFULLY_AUTHORISED)
            self.assertEqual(Order.objects.get(
                pk=response.context['order'].pk).authorisation_status,
                Order.SUCCESSFULLY_AUTHORISED
            )

            self.assertRedirects(response, reverse('bookings:order_placed'))

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_card_error_cvc_check_passes(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            stripe = Stripe.objects.get(order=response.context['order'])
            self.assertTrue(stripe.cvv2_code_check_passed)
            self.assertTrue(stripe.postcode_check_passed)
            self.assertEqual(stripe.authorisation_status,
                             Stripe.SUCCESSFULLY_AUTHORISED)
            self.assertEqual(response.context['order'].authorisation_status,
                             Order.SUCCESSFULLY_AUTHORISED)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertIsNone(stripe_charge.description)

            self.assertRedirects(response, reverse('bookings:order_placed'))

    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay', fake_delay)
    @freeze_time("2015-01-05 10:00:00")
    def test_card_error_postcode_check_failure_still_processed(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "fail"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('bookings:order_placed'))
            stripe = Stripe.objects.get(order=response.context['order'])
            self.assertTrue(stripe.cvv2_code_check_passed)
            self.assertFalse(stripe.postcode_check_passed)
            self.assertEqual(stripe.authorisation_status,
                             Stripe.SUCCESSFULLY_AUTHORISED)
            self.assertEqual(response.context['order'].authorisation_status,
                             Order.SUCCESSFULLY_AUTHORISED)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertIsNone(stripe_charge.description)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_card_error_postcode_check_passes(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('bookings:order_placed'))
            stripe = Stripe.objects.get(order=response.context['order'])
            self.assertTrue(stripe.cvv2_code_check_passed)
            self.assertTrue(stripe.postcode_check_passed)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertIsNone(stripe_charge.description)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_charge_id_set_on_order(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)
            self.assertRedirects(response, reverse('bookings:order_placed'))

            stripe = Stripe.objects.get(order=response.context['order'])
            self.assertEqual(stripe.token, payload['stripeToken'])
            self.assertEqual(stripe.charge, test_charge.id)
            self.assertTrue(stripe.cvv2_code_check_passed)
            self.assertTrue(stripe.postcode_check_passed)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_remote_addr_recorded_on_success(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items)

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class stripe_charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = stripe_charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge

            request.META['HTTP_X_FORWARDED_FOR'] = "8.8.8.8"
            SetRemoteAddrForwardedFor().process_request(request)

            response = charge(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("bookings:order_placed"))

            self.assertEqual(Order.objects.get(
                pk=order.pk).authorisation_status,
                Order.SUCCESSFULLY_AUTHORISED
            )

            self.assertEqual("8.8.8.8", Order.objects.get(
                pk=order.pk).ipaddress)

    @freeze_time("2015-01-05 10:00:00")
    def test_payment_discount_voucher_applied(self):
        # Create 10% discount voucher
        voucher = VoucherFactory(voucher_code='clean10',
                                 use_count=4,
                                 use_limit=15,
                                 percentage_off=Decimal('10.0'))

        payload = {'voucher_code': 'CLEAN10'}
        request = RequestFactory().post(reverse('payments:landing'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.00'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('43.00'))
        self.assertEqual(Order.objects.get(pk=order.pk).voucher, None)

        # 10% discount applied
        response = landing(request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('38.70'))

        # Voucher attached
        self.assertEqual(Order.objects.get(pk=order.pk).voucher, voucher)

        # do not increment count until charge step
        self.assertEqual(Voucher.objects.get(pk=voucher.pk).use_count, 4)

    @freeze_time("2015-01-05 10:00:00")
    def test_payment_discount_voucher_reapplied_applied(self):
        # Create 2 discount vouchers
        voucher1, voucher2 = (VoucherFactory(voucher_code='CLEAN10',
                                             percentage_off=Decimal('10.0')),
                              VoucherFactory(voucher_code='CLEAN125',
                                             percentage_off=Decimal('12.5')))

        payload = {'voucher_code': 'CLEAN10'}
        request = RequestFactory().post(reverse('payments:landing'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item1 = ItemFactory(price=Decimal(21.50))
        item2 = ItemFactory(price=Decimal(15.30))
        items = [ItemAndQuantityFactory(quantity=1, item=item1),
                 ItemAndQuantityFactory(quantity=2, item=item2)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('52.10'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('52.10'))
        self.assertEqual(Order.objects.get(pk=order.pk).voucher, None)

        # 10% discount applied
        response = landing(request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('46.89'))

        # Voucher attached
        self.assertEqual(Order.objects.get(pk=order.pk).voucher, voucher1)

        # do not increment count until charge step
        self.assertEqual(Voucher.objects.get(pk=voucher1.pk).use_count, 0)

        payload = {'voucher_code': 'CLEAN125'}
        request = RequestFactory().post(reverse('payments:landing'), payload)
        request.user = UserFactory()
        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        # 12.5% discount applied
        response = landing(request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('45.59'))

        # Voucher attached
        self.assertEqual(Order.objects.get(pk=order.pk).voucher, voucher2)

        # do not increment count until charge step
        self.assertEqual(Voucher.objects.get(pk=voucher2.pk).use_count, 0)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_voucher_incremented(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        voucher = VoucherFactory(voucher_code='CLEAN10',
                                 use_count=5,
                                 percentage_off=Decimal('10.0'))
        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('38.70'),
                             voucher=voucher)

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        self.assertEqual(Voucher.objects.get(pk=voucher.pk).use_count, 5)

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class stripe_charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = stripe_charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge

            response = charge(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("bookings:order_placed"))

            self.assertEqual(Order.objects.get(
                pk=order.pk).authorisation_status,
                Order.SUCCESSFULLY_AUTHORISED
            )

            # Voucher incremeneted on successful charge
            self.assertEqual(Voucher.objects.get(pk=voucher.pk).use_count, 6)

    @freeze_time("2015-01-05 10:00:00")
    def test_payment_discount_voucher_applied_displayed_to_user(self):
        # Create 10% discount voucher
        voucher = VoucherFactory(voucher_code='CLEAN10', percentage_off=Decimal('10.0'))

        payload = {'voucher_code': 'CLEAN10'}
        request = RequestFactory().post(reverse('payments:landing'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
            'address': address.pk,
            'order': order.pk
        })

        # 10% discount applied
        response = landing(request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('61.92'))
        self.assertTrue("Discount applied" in response.content)
        self.assertTrue(voucher.voucher_code in response.content)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_completed_orders_incremented(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.0'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        self.assertFalse(TrackConfirmedOrderSlots.objects.filter(
            appointment=pick_up_time).exists())

        self.assertFalse(TrackConfirmedOrderSlots.objects.filter(
            appointment=drop_off_time).exists())

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class stripe_charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = stripe_charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge

            response = charge(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("bookings:order_placed"))

            self.assertEqual(Order.objects.get(
                pk=order.pk).authorisation_status,
                Order.SUCCESSFULLY_AUTHORISED
            )

            self.assertEqual(TrackConfirmedOrderSlots.objects.get(
                appointment=pick_up_time).counter, 1)

            self.assertEqual(TrackConfirmedOrderSlots.objects.get(
                appointment=drop_off_time).counter, 1)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay',
           fake_delay)
    def test_charge_completed_orders_incremented_on_existing(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.0'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        TrackConfirmedOrderSlotsFactory(appointment=pick_up_time,
                                        counter=3)

        TrackConfirmedOrderSlotsFactory(appointment=drop_off_time,
                                        counter=1)

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class stripe_charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = stripe_charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge

            response = charge(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("bookings:order_placed"))

            self.assertEqual(Order.objects.get(
                pk=order.pk).authorisation_status,
                Order.SUCCESSFULLY_AUTHORISED
            )

            self.assertEqual(TrackConfirmedOrderSlots.objects.get(
                appointment=pick_up_time).counter, 4)

            self.assertEqual(TrackConfirmedOrderSlots.objects.get(
                appointment=drop_off_time).counter, 2)

    @freeze_time("2014-04-07 10:00:00")
    def test_charge_completed_orders_max_slots_taken_pickup(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 11, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.00'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2014-04-08 11',
            'delivery_time': '2014-04-11 15',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        TrackConfirmedOrderSlotsFactory(
            appointment=pick_up_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        MessageMiddleware().process_request(request)
        response = charge(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bookings:pick_up_time"))

        self.assertEqual(Order.objects.get(pk=order.pk).authorisation_status,
                         Order.NOT_ATTEMPTED_AUTHORISATION)

        self.assertIsNone(Order.objects.get(pk=order.pk).pick_up_time)
        self.assertIsNone(Order.objects.get(pk=order.pk).drop_off_time)

        self.assertTrue('pick_up_time' not in request.session)
        self.assertTrue('delivery_time' not in request.session)

    @freeze_time("2014-11-07 10:00:00")
    def test_charge_completed_orders_max_slots_taken_drop_off(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2014, 11, 10, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 11, 14, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.00'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2014-11-10 10',
            'delivery_time': '2014-11-14 14',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        TrackConfirmedOrderSlotsFactory(
            appointment=drop_off_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        MessageMiddleware().process_request(request)
        response = charge(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("bookings:delivery_time"))

        self.assertEqual(Order.objects.get(pk=order.pk).authorisation_status,
                         Order.NOT_ATTEMPTED_AUTHORISATION)

        self.assertEqual(pick_up_time,
                         Order.objects.get(pk=order.pk).pick_up_time)
        self.assertIsNone(Order.objects.get(pk=order.pk).drop_off_time)
        self.assertFalse(Order.objects.get(pk=order.pk).placed)

        self.assertTrue('pick_up_time' in request.session)
        self.assertEqual(u'2014-11-10 10', request.session['pick_up_time'])
        self.assertTrue('delivery_time' not in request.session)

    @freeze_time("2015-01-05 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay', fake_delay)
    def test_charge_placed_flag_set(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'), payload, follow=True)
            self.assertRedirects(response, reverse('bookings:order_placed'))

            self.assertEqual(response.context['order'].authorisation_status, Order.SUCCESSFULLY_AUTHORISED)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertEqual(stripe_charge.authorisation_status, Stripe.SUCCESSFULLY_AUTHORISED)

            past_dt = timezone.now() - datetime.timedelta(minutes=1)
            future_dt = timezone.now() + datetime.timedelta(minutes=1)

            placed_dt = response.context['order'].placed_time
            self.assertTrue(response.context['order'].placed)
            self.assertTrue(past_dt < placed_dt < future_dt)
            self.assertTrue(past_dt
                            < stripe_charge.successful_authorised_charge_time
                            < future_dt)

            self.assertTrue(past_dt
                            < stripe_charge.last_authorised_charge_time
                            < future_dt)
            self.assertTrue(response.context['order'].placed)
            self.assertTrue(past_dt
                            < response.context['order'].placed_time
                            < future_dt)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_card_error_description_populated(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.CardError(
                message="Declined",
                param="Card",
                code="incorrect_number",
                http_status=402,
                json_body={'error': {'message': 'Card Declined'}})

            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))
            self.assertContains(response, "Card Declined", count=2)

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertIsNotNone(stripe_charge.description)
            self.assertTrue("Card Declined" in stripe_charge.description)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_error_description_populated(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = stripe.error.StripeError(
                message="Declined",
                http_status=402,
                json_body={'error': {'message': 'Stripe Declined'}})

            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertIsNotNone(stripe_charge.description)
            self.assertTrue("Stripe Declined" in stripe_charge.description)

    @freeze_time("2015-01-05 10:00:00")
    def test_charge_stripe_error_unexpected_description_populated(self):
        self._create_and_login_user()
        self._valid_session()

        with patch('payments.views.authorize_charge') as mock_charge:
            exception = ValueError("Value error")

            mock_charge.side_effect = exception
            payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
            response = self.client.post(reverse('payments:charge'),
                                        payload,
                                        follow=True)

            self.assertRedirects(response, reverse('payments:landing'))

            stripe_charge = Stripe.objects.get(order=response.context['order'])
            self.assertIsNotNone(stripe_charge.description)
            self.assertTrue("ValueError" in stripe_charge.description)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_changed_transportation_charged(self):
        _user = UserFactory()
        _address = AddressFactory()

        min_free_delivery = Decimal('10.00')
        transportation_charge = Decimal('2.95')
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('4.00') + transportation_charge)

        request = RequestFactory().get(reverse('payments:landing'))
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=min_free_delivery, TRANSPORTATION_CHARGE=transportation_charge):
            response = landing(request)

        self.assertContains(response, "Pick up and delivery")

    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay', fake_delay)
    @freeze_time("2014-04-07 10:00:00")
    def test_vat_calculated_on_order(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 11, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.00'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2014-04-08 11',
            'delivery_time': '2014-04-11 15',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class stripe_charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = stripe_charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge

            response = charge(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("bookings:order_placed"))

            self.assertEqual(Order.objects.get(pk=order.pk).vat_charge, Decimal('7.17'))
            self.assertEqual(Order.objects.get(pk=order.pk).price_excluding_vat_charge, Decimal('35.83'))

    @freeze_time("2014-04-07 10:00:00")
    @patch('vendors.tasks.notify_vendors_of_orders_via_email.delay', fake_delay)
    def test_order_ticket_id_set(self):
        payload = {'stripeToken': 'tok_15KXZwDnM72emLEehazo0MK8'}
        request = RequestFactory().post(reverse('payments:charge'), payload)
        request.user = UserFactory()

        address = AddressFactory()
        item = ItemFactory(price=Decimal('21.50'))
        items = [ItemAndQuantityFactory(quantity=2, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 11, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=request.user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('43.0'))

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2014-04-08 11',
            'delivery_time': '2014-04-11 15',
            'items': {unicode(str(item.pk)): 2},
            'address': address.pk,
            'order': order.pk
        })

        with patch('stripe.Charge.create') as mock_charge:
            class source(object):
                id = "card_15QdebDnM72emLEeTUvNnrpj"
                cvc_check = "pass"
                address_zip_check = "pass"

            class stripe_charge(object):
                id = "card_15KZlRDnM72emLEebQjP4ZYx"
                created = str(int(time.time()))

            test_charge = stripe_charge()
            test_charge.source = source()
            mock_charge.return_value = test_charge

            response = charge(request)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, reverse("bookings:order_placed"))

            expected = "WW-{:0>5d}".format(order.pk % THRESHOLD)
            self.assertEqual(Order.objects.get(pk=order.pk).ticket_id, expected)
