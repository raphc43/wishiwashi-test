from datetime import timedelta

from dateutil.parser import parse
from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()


@register.filter
@stringfilter
def add_one_hour(value):
    try:
        time = parse(value)
    except ValueError:
        return value

    return time + timedelta(hours=1)
