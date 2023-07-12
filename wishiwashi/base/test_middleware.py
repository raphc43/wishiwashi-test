from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponsePermanentRedirect
from django.test import TestCase, override_settings
from django.test.client import RequestFactory

from base.middleware import HTTPSOnly, SetRemoteAddrForwardedFor


DOMAIN = "www.wishiwashi.com"


@override_settings(HTTPS_ONLY=True, DOMAIN=DOMAIN)
class HTTPSOnlyTest(TestCase):
    def test_redirect_https_on(self):
        request = RequestFactory().get(reverse('landing'))
        self.assertTrue(request.build_absolute_uri().startswith('http://'))

        middleware = HTTPSOnly()
        response = middleware.process_request(request)
        self.assertTrue(isinstance(response, HttpResponsePermanentRedirect))
        self.assertEqual(response.status_code, 301)

    def test_no_redirects_https_off(self):
        with self.settings(HTTPS_ONLY=False):
            request = RequestFactory().get(reverse('landing'))
            middleware = HTTPSOnly()
            response = middleware.process_request(request)
            self.assertIsNone(response)

    def test_redirects_https_on_redirect_chain(self):
        response = self.client.get(reverse('landing'), follow=True)
        self.assertEqual((u"https://www.wishiwashi.com/", 301),
                         response.redirect_chain[0])

    def test_redirects_https_on_path(self):
        path = reverse('bookings:login')
        response = self.client.get(path, follow=True)
        self.assertEqual((u"https://www.wishiwashi.com{}".format(path), 301),
                         response.redirect_chain[0])

    def test_unset_domain(self):
        with self.settings(DOMAIN=""):
            path = reverse('bookings:login')
            with self.assertRaises(ImproperlyConfigured):
                self.client.get(path, follow=True)


class RemoteAddrForwardedForTestCase(TestCase):
    def test_remoteaddr_overwrite(self):
        """ Overwrite local ip with forwarded IP """
        request = RequestFactory().get(reverse('landing'))
        request.user = AnonymousUser()
        request.session = {}
        ip = "123.456.789.10"
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_X_FORWARDED_FOR'] = ip
        SetRemoteAddrForwardedFor().process_request(request)
        self.assertEqual(request.META['REMOTE_ADDR'], ip)

    def test_remoteaddr_untouched(self):
        """ Do not modify remote_addr """
        request = RequestFactory().get(reverse('landing'))
        request.user = AnonymousUser()
        request.session = {}
        ip = "127.0.0.1"
        request.META['REMOTE_ADDR'] = ip
        SetRemoteAddrForwardedFor().process_request(request)
        self.assertEqual(request.META['REMOTE_ADDR'], ip)

    def test_remoteaddr_multiples(self):
        """ Take second to last from list of comma seperated IP's """
        request = RequestFactory().get(reverse('landing'))
        request.user = AnonymousUser()
        request.session = {}
        ips = ("123.456.789.10", "111.222.333.444", "222.333.444.555")
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        request.META['HTTP_X_FORWARDED_FOR'] = ", ".join(ips)
        SetRemoteAddrForwardedFor().process_request(request)
        self.assertEqual(request.META['REMOTE_ADDR'], ips[-2])
