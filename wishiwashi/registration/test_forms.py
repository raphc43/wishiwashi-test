from django.test import TestCase

from bookings.factories import UserFactory

from registration.forms import PasswordResetForm


class Forms(TestCase):
    def test_password_reset_request(self):
        user = UserFactory()
        data = {'email_address': user.email}
        form = PasswordResetForm(data)
        assert form.is_valid()

    def test_password_reset_invalid_user(self):
        data = {'email_address': "doesnotexist@example.com"}
        form = PasswordResetForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['email_address'][0].code == 'invalid'

    def test_password_reset_not_active(self):
        user = UserFactory(is_active=False)
        data = {'email_address': user.email}
        form = PasswordResetForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['email_address'][0].code == 'disabled'


