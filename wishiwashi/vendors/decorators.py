from django.http import HttpResponseForbidden
from django.conf import settings
from django.utils.functional import wraps

from bookings.models import Vendor


def vendor_required():
    """
    This decorator expects that @login_required and preceded this decorator
    being called.
    """
    def decorator(func):
        def inner_decorator(request, *args, **kwargs):
            try:
                request.user.vendor = Vendor.objects.filter(staff=request.user)[0]
            except IndexError:
                return HttpResponseForbidden("You must be a vendor to view this page")

            return func(request, *args, **kwargs)
        return wraps(func)(inner_decorator)

    return decorator


def wishi_washi_vendor_view():
    """
    Ensure view is only viewed by a Wishi Washi staff member
    """
    def decorator(func):
        @wraps(func)
        def inner(request, *args, **kwargs):
            if hasattr(request.user, 'vendor') and request.user.vendor.pk == settings.VENDOR_WISHI_WASHI_PK:
                return func(request, *args, **kwargs)
            else:
                return HttpResponseForbidden('You are not allowed to use this functionality.')
        return inner
    return decorator
