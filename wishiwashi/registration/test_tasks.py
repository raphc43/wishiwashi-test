from django.test import TestCase
from django.test.utils import override_settings
import mock

from bookings.factories import UserFactory
from registration.tasks import reset_password_via_email


def delay(user_id):
    pass


@override_settings(
    COMMUNICATE_SERVICE_ENDPOINT="http://localhost"
)
@mock.patch('registration.tasks.reset_password_via_email.delay', delay)
class Tasks(TestCase):
    @mock.patch('requests.post')
    def test_order_confirmation_email_response(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        user = UserFactory()
        with self.settings(COMMUNICATE_SERVICE_ENDPOINT="http://localhost"):
            self.assertTrue(reset_password_via_email(user.pk))
