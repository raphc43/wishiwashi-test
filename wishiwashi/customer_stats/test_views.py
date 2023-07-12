from django.core.urlresolvers import reverse
from django.test import TestCase, Client

from bookings.factories import UserFactory, VendorFactory
from .views import placed_time_monthly


class Views(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = UserFactory()
        self.vendor = VendorFactory(staff=[self.user,])
        self.assertTrue(self.client.login(username=self.user.username, password=UserFactory.password))

    def test_placed_time_monthly_response_ok(self):
        with self.settings(VENDOR_WISHI_WASHI_PK=self.vendor.pk):
            response = self.client.get("{}?month=01&year=2016".format(reverse('customer_stats:placed_time_monthly')))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.charset, 'utf-8')

    def test_placed_time_monthly_non_wishi_washi_forbidden(self):
        with self.settings(VENDOR_WISHI_WASHI_PK=self.vendor.pk+1):
            response = self.client.get("{}?month=01&year=2016".format(reverse('customer_stats:placed_time_monthly')))
        self.assertEqual(response.status_code, 403)

    def test_placed_time_monthly_non_vendor_forbidden(self):
        client = Client()
        user = UserFactory()
        client.login(username=user.username, password=UserFactory.password)
        response = self.client.get("{}?month=01&year=2016".format(reverse('customer_stats:placed_time_monthly')))
        self.assertEqual(response.status_code, 403)

    def test_placed_stats_response_ok(self):
        with self.settings(VENDOR_WISHI_WASHI_PK=self.vendor.pk):
            response = self.client.get(reverse('customer_stats:stats'))
        self.assertEqual(response.status_code, 200)

    def test_placed_stats_response_non_vendor_forbidden(self):
        client = Client()
        user = UserFactory()
        self.assertTrue(client.login(username=user.username, password=UserFactory.password))
        response = client.get(reverse('customer_stats:stats'))
        self.assertEqual(response.status_code, 403)


