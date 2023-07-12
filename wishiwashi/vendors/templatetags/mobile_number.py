from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()


@register.filter
@stringfilter
def mobile_number(value):
    "Replace international GB prefix on mobile"
    if value.startswith("0044"):
        return "0{}".format(value[4:])
    return value
