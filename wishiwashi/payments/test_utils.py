import random
from decimal import Decimal
from string import letters, digits

from django.test import TestCase
import mock
import stripe

from .utils import capture_charge, timestamp_to_datetime_str, transportation_charge, vat_cost


class TestCharge(object):
    def __init__(self, captured=False):
        self.id = "ch_" + "".join(random.sample(letters + digits, 50))
        self.captured = captured

    def capture(self):
        pass


class Utils(TestCase):
    def setUp(self):
        self.charge = TestCharge()

    def test_invalid_amount(self):
        self.assertRaises(ValueError, capture_charge, self.charge.id, 21.50)

    def test_invalid_amount_string(self):
        self.assertRaises(ValueError, capture_charge, self.charge.id, "2150")

    def test_valid_amount(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            self.charge.captured = True
            mock_charge.return_value = self.charge
            self.assertTrue(capture_charge(self.charge.id, 2150))

    def test_valid_capture(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            self.charge.captured = True
            mock_charge.return_value = self.charge
            self.assertTrue(capture_charge(self.charge.id, 2150))

    def test_invalid_capture(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            mock_charge.return_value = self.charge
            self.assertRaises(ValueError, capture_charge, self.charge.id, random.randint(100, 1000))

    def test_capture_charge_stripe_card_error(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            exception = stripe.error.CardError(
                message="Declined",
                param="Card",
                code="incorrect_number",
                http_status=402,
                json_body={'error': {'message': 'Card Declined'}})

            mock_charge.side_effect = exception
            self.assertRaises(stripe.error.CardError, capture_charge, self.charge.id, random.randint(100, 1000))

    def test_capture_charge_stripe_invalid_request(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            exception = stripe.error.InvalidRequestError(
                message="Invalid Request",
                http_status=400,
                param=None,
                json_body={'error': {'message': 'Charge invalid'}})
            mock_charge.side_effect = exception
            self.assertRaises(stripe.error.InvalidRequestError, capture_charge,
                              self.charge.id, random.randint(100, 1000))

    def test_capture_charge_stripe_authentication_failure(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            exception = stripe.error.AuthenticationError(
                message="Authentication Error",
                http_status=500,
                json_body={'error': {'message': 'Payment cannot be taken'}})
            mock_charge.side_effect = exception
            self.assertRaises(stripe.error.AuthenticationError, capture_charge,
                              self.charge.id, random.randint(100, 1000))

    def test_capture_charge_stripe_api_failure(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            exception = stripe.error.APIConnectionError(
                message="Server Error",
                http_status=500,
                json_body={'error': {'message': 'Payment cannot be taken'}})
            mock_charge.side_effect = exception
            self.assertRaises(stripe.error.APIConnectionError, capture_charge,
                              self.charge.id, random.randint(100, 1000))

    def test_capture_charge_stripe_generic_failure(self):
        with mock.patch('stripe.Charge.retrieve') as mock_charge:
            exception = stripe.error.StripeError(
                message="Generic Error",
                http_status=400,
                json_body={'error': {'message': 'Payment cannot be taken'}})
            mock_charge.side_effect = exception
            self.assertRaises(stripe.error.StripeError, capture_charge, self.charge.id, random.randint(100, 1000))

    def test_timestamp_conversion(self):
        ts = 1421331342.949035
        created = '2015-01-15T14:15:42Z'
        assert timestamp_to_datetime_str(ts) == created

    def test_charge_not_applied(self):
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=Decimal('1.95')):
            total = Decimal('23.97')
            self.assertEqual(Decimal('0.00'), transportation_charge(total))

    def test_charge_applied_less(self):
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10'), TRANSPORTATION_CHARGE=Decimal('1.95')):
            total = Decimal('3.97')
            self.assertEqual(Decimal('1.95'), transportation_charge(total))

    def test_charge_not_applied_equal(self):
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('15.00'), TRANSPORTATION_CHARGE=Decimal('3.95')):
            total = Decimal('15.00')
            self.assertEqual(Decimal('0.00'), transportation_charge(total))

    def test_charge_applied_under(self):
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=Decimal('1.95')):
            total = Decimal('9.99')
            self.assertEqual(Decimal('1.95'), transportation_charge(total))

    def test_charge_not_applied_zero(self):
        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('15.00'), TRANSPORTATION_CHARGE=Decimal('3.95')):
            total = Decimal('0.00')
            self.assertEqual(Decimal('0.00'), transportation_charge(total))

    def test_vat_cost_regular(self):
        total = Decimal('29.37')
        with self.settings(VAT_RATE=Decimal('20')):
            vat = vat_cost(total)
            self.assertEqual(vat['vat'], Decimal('4.89'))
            self.assertEqual(vat['ex_vat'], Decimal('24.48'))
            self.assertEqual(total, sum(vat.values()))

    def test_vat_cost_reduced(self):
        total = Decimal('212.30')
        with self.settings(VAT_RATE=Decimal('17.5')):
            vat = vat_cost(total)
            self.assertEqual(vat['vat'], Decimal('31.62'))
            self.assertEqual(vat['ex_vat'], Decimal('180.68'))
            self.assertEqual(total, sum(vat.values()))

    def test_vat_cost_normal(self):
        total = Decimal('18.21')
        with self.settings(VAT_RATE=Decimal('20')):
            vat = vat_cost(total)
            self.assertEqual(vat['vat'], Decimal('3.03'))
            self.assertEqual(vat['ex_vat'], Decimal('15.18'))
            self.assertEqual(total, sum(vat.values()))

    def test_vat_cost_small(self):
        total = Decimal('5.98')
        with self.settings(VAT_RATE=Decimal('20')):
            vat = vat_cost(total)
            self.assertEqual(vat['vat'], Decimal('1.00'))
            self.assertEqual(vat['ex_vat'], Decimal('4.98'))
            self.assertEqual(total, sum(vat.values()))

    def test_vat_costs(self):
        total = Decimal('14.90')
        with self.settings(VAT_RATE=Decimal('20')):
            vat = vat_cost(total)
            self.assertEqual(vat['vat'], Decimal('2.48'))
            self.assertEqual(vat['ex_vat'], Decimal('12.42'))
            self.assertEqual(total, sum(vat.values()))

