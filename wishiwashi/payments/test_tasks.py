import datetime
from datetime import timedelta
import random
from string import letters, digits

from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone
import mock
import stripe

from bookings.factories import OrderFactory
from bookings.models import Order
from .factories import StripeFactory
from .models import Stripe
from .tasks import (capture_charge,
                    order_confirmation_for_customer_via_email,
                    order_charged_confirmation_for_customer_via_email)


class TestCharge(object):
    def __init__(self, captured=False):
        self.id = "ch_" + "".join(random.sample(letters + digits, 50))
        self.captured = captured

    def capture(self):
        pass


def delay(order_id):
    pass


@override_settings(
    COMMUNICATE_SERVICE_ENDPOINT="http://localhost"
)
@mock.patch('payments.tasks.order_charged_confirmation_for_customer_via_email.delay', delay)
class Tasks(TestCase):
    def setUp(self):
        self.now_london = timezone.localtime(timezone.now())
        self.three_hours_ago = self.now_london - timedelta(hours=3)
        self.six_hours_ago = self.now_london - timedelta(hours=6)
        self.charge = TestCharge()

        self.order = OrderFactory(
            card_charged_status=Order.NOT_CHARGED,
            charge_back_status=Order.NOT_CHARGED_BACK,
            refund_status=Order.NOT_REFUNDED,
            order_status=Order.RECEIVED_BY_VENDOR,
            authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
            pick_up_time=self.three_hours_ago)

        self.stripe_charge = StripeFactory(
            order=self.order,
            charge=self.charge.id,
            card_charged_status=Stripe.NOT_CHARGED,
            charge_back_status=Stripe.NOT_CHARGED_BACK,
            refund_status=Stripe.NOT_REFUNDED,
            authorisation_status=Stripe.SUCCESSFULLY_AUTHORISED,
            successful_authorised_charge_time=self.six_hours_ago)

        super(Tasks, self).setUp()

    def test_capture_charge_valid(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            mock_capture_charge.return_value = TestCharge(True)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.NOT_CHARGED)
            capture_charge()
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.SUCCESSFULLY_CHARGED)
            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.SUCCESSFULLY_CHARGED)

    def test_capture_charge_failure(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            mock_capture_charge.side_effect = ValueError(
                "Charge not captured: {}".format(self.charge.id))
            self.assertRaises(ValueError, capture_charge)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.FAILED_TO_CHARGE)
            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.FAILED_TO_CHARGE)

    def test_capture_charge_stripe_card_error(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            exception = stripe.error.CardError(
                message="Declined",
                param="Card",
                code="incorrect_number",
                http_status=402,
                json_body={'error': {'message': 'Card Declined'}})
            mock_capture_charge.side_effect = exception
            capture_charge()
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.FAILED_TO_CHARGE)

            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.FAILED_TO_CHARGE)

    def test_capture_charge_stripe_invalid_request(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            exception = stripe.error.InvalidRequestError(
                message="Invalid Request",
                http_status=400,
                param=None,
                json_body={'error': {'message': 'Request invalid'}})
            mock_capture_charge.side_effect = exception
            self.assertRaises(stripe.error.InvalidRequestError, capture_charge,
                              self.order.id)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.FAILED_TO_CHARGE)

            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.FAILED_TO_CHARGE)

    def test_capture_charge_stripe_authentication_failure(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            exception = stripe.error.AuthenticationError(
                message="Server Error",
                http_status=500,
                json_body={'error': {'message': 'Server side error'}})
            mock_capture_charge.side_effect = exception
            self.assertRaises(stripe.error.AuthenticationError, capture_charge,
                              self.order.id)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.FAILED_TO_CHARGE)

            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.FAILED_TO_CHARGE)

    def test_capture_charge_stripe_api_failure(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            exception = stripe.error.APIConnectionError(
                message="Server Error",
                http_status=500,
                json_body={'error': {'message': 'Payment cannot be taken'}})
            mock_capture_charge.side_effect = exception
            self.assertRaises(stripe.error.APIConnectionError, capture_charge,
                              self.order.id)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.FAILED_TO_CHARGE)

            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.FAILED_TO_CHARGE)

    def test_capture_charge_stripe_generic_failure(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            exception = stripe.error.StripeError(
                message="Server Error",
                http_status=500,
                json_body={'error': {'message': 'Generic error'}})
            mock_capture_charge.side_effect = exception
            self.assertRaises(stripe.error.StripeError, capture_charge,
                              self.order.id)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.FAILED_TO_CHARGE)

            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.FAILED_TO_CHARGE)

    def test_capture_charge_untouched(self):
        self.stripe_charge.card_charged_status = Stripe.SUCCESSFULLY_CHARGED
        self.stripe_charge.save()

        capture_charge()
        stripe_charge = Stripe.objects.get(order=self.order)
        self.assertEqual(stripe_charge.card_charged_status,
                         Stripe.SUCCESSFULLY_CHARGED)

    def test_capture_charge_sameday(self):
        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            mock_capture_charge.return_value = TestCharge(captured=True)
            capture_charge()
            stripe_charge = Stripe.objects.get(order=self.order)
            self.assertEqual(stripe_charge.card_charged_status,
                             Stripe.SUCCESSFULLY_CHARGED)
            self.assertEqual(Order.objects.get(id=self.order.id).card_charged_status,
                             Order.SUCCESSFULLY_CHARGED)

    def test_capture_charge_nextday(self):
        order = OrderFactory(card_charged_status=Order.NOT_CHARGED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             pick_up_time=timezone.now() + datetime.timedelta(hours=24))
        self.stripe_charge.order = order
        self.stripe_charge.save()

        with mock.patch('payments.utils.capture_charge') as mock_capture_charge:
            mock_capture_charge.return_value = TestCharge(captured=False)
            capture_charge()
            self.assertEqual(Order.objects.get(id=order.id).card_charged_status,
                             Order.NOT_CHARGED)

            stripe_charge = Stripe.objects.get(order=order)
            self.assertEqual(stripe_charge.card_charged_status, Stripe.NOT_CHARGED)

    def test_capture_charge_rejected_by_service_provider(self):
        order = OrderFactory(card_charged_status=Order.NOT_CHARGED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED,
                             order_status=Order.ORDER_REJECTED_BY_SERVICE_PROVIDER,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             pick_up_time=self.three_hours_ago)
        self.stripe_charge.order = order
        self.stripe_charge.save()

        capture_charge()
        self.assertEqual(Order.objects.get(id=order.id).card_charged_status, Order.NOT_CHARGED)

        stripe_charge = Stripe.objects.get(order=order)
        self.assertEqual(stripe_charge.card_charged_status, Stripe.NOT_CHARGED)

    def test_capture_charge_multi(self):
        orders = (
            OrderFactory(card_charged_status=Order.NOT_CHARGED,
                         charge_back_status=Order.NOT_CHARGED_BACK,
                         refund_status=Order.NOT_REFUNDED,
                         order_status=Order.RECEIVED_BY_VENDOR,
                         authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                         pick_up_time=timezone.now() + datetime.timedelta(hours=24)),

            OrderFactory(card_charged_status=Order.NOT_CHARGED,
                         charge_back_status=Order.NOT_CHARGED_BACK,
                         refund_status=Order.NOT_REFUNDED,
                         order_status=Order.RECEIVED_BY_VENDOR,
                         authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                         pick_up_time=self.three_hours_ago)
        )

        for order in orders:
            charge = TestCharge()
            StripeFactory(
                order=order,
                charge=charge.id,
                card_charged_status=Stripe.NOT_CHARGED,
                charge_back_status=Stripe.NOT_CHARGED_BACK,
                refund_status=Stripe.NOT_REFUNDED,
                authorisation_status=Stripe.SUCCESSFULLY_AUTHORISED,
                successful_authorised_charge_time=self.six_hours_ago)

        for order in orders:
            with mock.patch('payments.utils.capture_charge') as mock_charge:
                mock_charge.return_value = TestCharge(captured=False)
                capture_charge()

        self.assertEqual(Order.objects.get(id=orders[0].id).card_charged_status,
                         Order.NOT_CHARGED)
        self.assertEqual(Order.objects.get(id=orders[1].id).card_charged_status,
                         Order.SUCCESSFULLY_CHARGED)

        self.assertEqual(Stripe.objects.get(order=orders[0]).card_charged_status,
                         Stripe.NOT_CHARGED)
        self.assertEqual(Stripe.objects.get(order=orders[1]).card_charged_status,
                         Stripe.SUCCESSFULLY_CHARGED)

    @mock.patch('requests.post')
    def test_order_confirmation_email_response(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        order = OrderFactory()
        with self.settings(COMMUNICATE_SERVICE_ENDPOINT="http://localhost"):
            self.assertTrue(order_confirmation_for_customer_via_email(
                order.pk))

    @mock.patch('requests.post')
    def test_order_confirmation_email_response_error(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"error":true}'

        mock_response.return_value = response()
        order = OrderFactory()
        self.assertRaises(AssertionError,
                          order_confirmation_for_customer_via_email,
                          order.pk)

    @mock.patch('requests.post')
    def test_order_confirmation_email_status_error(self, mock_response):
        class response(object):
            status_code = 500
            content = ''

        mock_response.return_value = response()
        order = OrderFactory()
        self.assertRaises(AssertionError,
                          order_confirmation_for_customer_via_email,
                          order.pk)

    @mock.patch('requests.post')
    def test_order_charged_confirmation_email_response(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        order = OrderFactory()
        self.assertTrue(order_charged_confirmation_for_customer_via_email(
            order.pk))

    @mock.patch('requests.post')
    def test_order_charged_confirmation_email_response_error(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"error":true}'

        mock_response.return_value = response()
        order = OrderFactory()
        self.assertRaises(AssertionError,
                          order_charged_confirmation_for_customer_via_email,
                          order.pk)

    @mock.patch('requests.post')
    def test_order_charged_confirmation_email_status_error(self, mock_response):
        class response(object):
            status_code = 500
            content = ''

        mock_response.return_value = response()
        order = OrderFactory()
        self.assertRaises(AssertionError,
                          order_charged_confirmation_for_customer_via_email,
                          order.pk)

