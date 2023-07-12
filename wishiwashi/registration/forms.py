from django import forms
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.forms import SetPasswordForm

from registration.tasks import reset_password_via_email


class PasswordResetForm(forms.Form):
    email_address = forms.EmailField(label="Email address",
                                     max_length=254)

    def clean_email_address(self):
        email_address = self.cleaned_data["email_address"].lower()

        try:
            user = User.objects.get(email__iexact=email_address)
        except User.DoesNotExist:
            raise forms.ValidationError("%(email)s does not exist",
                                        code='invalid',
                                        params={'email': email_address})

        if user.is_active is False:
            raise forms.ValidationError("Account is disabled",
                                        code='disabled')

        return email_address

    def save(self):
        email_address = self.cleaned_data["email_address"]
        user = User.objects.get(email__iexact=email_address)
        reset_password_via_email.delay(user.pk)


class PasswordSetForm(SetPasswordForm):
    new_password1 = forms.CharField(label="New password",
                                    min_length=settings.MIN_PASSWORD_LENGTH,
                                    widget=forms.PasswordInput
                                    )

    new_password2 = forms.CharField(label="New password confirmation",
                                    min_length=settings.MIN_PASSWORD_LENGTH,
                                    widget=forms.PasswordInput
                                    )
