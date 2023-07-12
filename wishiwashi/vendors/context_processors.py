from django.conf import settings


def wishi_washi_user(request):
    wishi_washi = False

    if request.user.is_authenticated() and hasattr(request.user, 'vendor'):
        if request.user.vendor.pk == settings.VENDOR_WISHI_WASHI_PK:
            wishi_washi = True

    return {'WISHI_WASHI_USER': wishi_washi}
