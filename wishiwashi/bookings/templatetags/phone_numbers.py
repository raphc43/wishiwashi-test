from django import template
from django.template.defaultfilters import stringfilter
import phonenumbers as phone_nos


register = template.Library()


@register.filter
@stringfilter
def format_phone_number(value):
    try:
        parsed = phone_nos.parse(value, "GB")
        number = phone_nos.format_number(parsed,
                                       phone_nos.PhoneNumberFormat.NATIONAL)

        return '+44 (0)%s' % number.strip()[1:]
    except Exception:
        return value
