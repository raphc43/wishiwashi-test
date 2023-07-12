from django import template
from django.template.defaultfilters import stringfilter
from ukpostcodeparser import parse_uk_postcode


register = template.Library()


@register.filter
@stringfilter
def format_postcode(value):
    try:
        _postcode = parse_uk_postcode(value, incode_mandatory=False)
    except ValueError:
        return value

    if _postcode is None:
        return value

    return " ".join(_postcode).upper().strip()
