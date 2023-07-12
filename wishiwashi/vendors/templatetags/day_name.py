from django import template
from django.template.defaultfilters import stringfilter

from bookings.models import OperatingTimeRange


register = template.Library()


@register.filter
@stringfilter
def day_name(value):
    return OperatingTimeRange.DAYS_OF_WEEK[int(value)][1]
