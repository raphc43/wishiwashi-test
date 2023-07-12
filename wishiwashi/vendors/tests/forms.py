import datetime

from django.test import TestCase
from django.utils import timezone

from bookings.factories import VendorFactory
from ..forms import OrderPaymentsSearchForm


class Forms(TestCase):
    def setUp(self):
        self.vendor = VendorFactory()

    def test_invalid_start_date(self):
        data = {
            "assigned_to_vendor": "",
            "clean_only_vendor": "",
            "start_date": timezone.now().strftime("%d-%m-%Y"),
            "end_date": (timezone.now() + datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        }
        form = OrderPaymentsSearchForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['start_date'][0].code == 'invalid_date'

    def test_valid_start_date(self):
        data = {
            "assigned_to_vendor": "",
            "clean_only_vendor": "",
            "start_date": (timezone.now() - datetime.timedelta(days=5)).strftime("%d-%m-%Y"),
            "end_date": (timezone.now() - datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        }
        form = OrderPaymentsSearchForm(data)
        assert form.is_valid(), form.errors.as_data()

    def test_invalid_end_date(self):
        data = {
            "assigned_to_vendor": "",
            "clean_only_vendor": "",
            "start_date": (timezone.now() - datetime.timedelta(days=5)).strftime("%d-%m-%Y"),
            "end_date": timezone.now().strftime("%d-%m-%Y")
        }
        form = OrderPaymentsSearchForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['end_date'][0].code == 'invalid_date'

    def test_valid_end_date(self):
        data = {
            "assigned_to_vendor": "",
            "clean_only_vendor": "",
            "start_date": (timezone.now() - datetime.timedelta(days=5)).strftime("%d-%m-%Y"),
            "end_date": (timezone.now() - datetime.timedelta(days=1)).strftime("%d-%m-%Y")
        }
        form = OrderPaymentsSearchForm(data)
        assert form.is_valid(), form.errors.as_data()

    def test_invalid_start_date_after_end_date(self):
        data = {
            "assigned_to_vendor": "",
            "clean_only_vendor": "",
            "start_date": (timezone.now() - datetime.timedelta(days=3)).strftime("%d-%m-%Y"),
            "end_date": (timezone.now() - datetime.timedelta(days=5)).strftime("%d-%m-%Y")
        }
        form = OrderPaymentsSearchForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['__all__'][0].code == 'invalid_dates'

    def test_invalid_date_range(self):
        data = {
            "assigned_to_vendor": "",
            "clean_only_vendor": "",
            "start_date": (timezone.now() - datetime.timedelta(days=90)).strftime("%d-%m-%Y"),
            "end_date": (timezone.now() - datetime.timedelta(days=5)).strftime("%d-%m-%Y")
        }
        form = OrderPaymentsSearchForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['__all__'][0].code == 'invalid_dates'


