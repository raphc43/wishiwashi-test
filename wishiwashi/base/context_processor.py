from django.conf import settings


def get_settings(request):
    _settings = {
        'GOOGLE_ANALYTICS_CODE': settings.GOOGLE_ANALYTICS_CODE,
        'UK_PHONE_NUMBER': settings.UK_PHONE_NUMBER,
        'UK_PHONE_NUMBER_UGLY': settings.UK_PHONE_NUMBER_UGLY,
        'HOURS_OF_OPERATION': settings.HOURS_OF_OPERATION,
        'DOMAIN': settings.DOMAIN,
    }

    return _settings
