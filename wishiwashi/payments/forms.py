from django import forms
from django.utils import timezone

from bookings.models import Voucher


class StripePaymentForm(forms.Form):
    stripeToken = forms.CharField(required=True,
                                  error_messages={'required':
                                                  'Please enter your payment details.'})


class VoucherDiscountForm(forms.Form):
    voucher_code = forms.CharField(max_length=75, min_length=4)

    def clean_voucher_code(self):
        voucher_code = self.cleaned_data["voucher_code"].upper()

        try:
            voucher = Voucher.objects.get(voucher_code__iexact=voucher_code)
        except Voucher.DoesNotExist:
            raise forms.ValidationError("Voucher code: %(code)s does not exist",
                                        code='invalid',
                                        params={'code': voucher_code})

        if voucher.valid_until < timezone.now():
            raise forms.ValidationError("Voucher code: %(code)s has expired",
                                        code='expired',
                                        params={'code': voucher_code})
        elif voucher.use_count >= voucher.use_limit:
            raise forms.ValidationError("Voucher code: %(code)s limit exceeded",
                                        code='exceeded',
                                        params={'code': voucher_code})

        return voucher_code


