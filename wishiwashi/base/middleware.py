from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponsePermanentRedirect


class HTTPSOnly(object):
    def process_request(self, request):
        if settings.HTTPS_ONLY is False:
            return None

        if not settings.DOMAIN:
            error_msg = "Configuration error - DOMAIN environment variable unset"
            raise ImproperlyConfigured(error_msg)

        if not request.is_secure():
            path = request.get_full_path()
            secure_url = "https://{0}{1}".format(settings.DOMAIN, path)
            return HttpResponsePermanentRedirect(secure_url)


class SetRemoteAddrForwardedFor():
    def process_request(self, request):
        try:
            real_ip = request.META['HTTP_X_FORWARDED_FOR']
        except KeyError:
            pass
        else:
            # X-Forwarded-For: Appended to by heroku
            real_ip_pieces = real_ip.split(",")
            if len(real_ip_pieces) > 1:
                real_ip = real_ip_pieces[-2]
            else:
                real_ip = real_ip_pieces[-1]

            request.META['REMOTE_ADDR'] = real_ip.strip()
