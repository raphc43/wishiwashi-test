from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from bookings.factories import VoucherFactory
from payments.forms import VoucherDiscountForm


class Forms(TestCase):
    def test_voucher_discount_valid(self):
        code = "HELPUS"
        VoucherFactory(voucher_code=code)
        data = {'voucher_code': code}
        form = VoucherDiscountForm(data)
        assert form.is_valid()

    def test_voucher_discount_incorrect(self):
        code = "HELPUS"
        VoucherFactory(voucher_code=code)
        data = {'voucher_code': "HELPS"}
        form = VoucherDiscountForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['voucher_code'][0].code == 'invalid'

    def test_voucher_discount_invalid_length(self):
        data = {'voucher_code': 'HE'}
        form = VoucherDiscountForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['voucher_code'][0].code == 'min_length'

    def test_voucher_discount_expired(self):
        code = "HELPUS"
        yesterday = timezone.now() - timedelta(days=1)
        VoucherFactory(voucher_code=code, valid_until=yesterday)
        data = {'voucher_code': code}
        form = VoucherDiscountForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['voucher_code'][0].code == 'expired'

    def test_voucher_discount_limit_exceeded(self):
        code = "HELPUS"
        VoucherFactory(voucher_code=code, use_limit=5, use_count=5)
        data = {'voucher_code': code}
        form = VoucherDiscountForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['voucher_code'][0].code == 'exceeded'

    def test_voucher_discount_case_insensitive(self):
        code = "HELPUS"
        VoucherFactory(voucher_code=code, use_limit=15, use_count=4)
        data = {'voucher_code': "helpUS"}
        form = VoucherDiscountForm(data)
        assert form.is_valid()
