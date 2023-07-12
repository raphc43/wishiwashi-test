from bookings.clean_only import drop_off_time_to_ready_time
from django import template


register = template.Library()


@register.filter
def expected_back(value):
    return drop_off_time_to_ready_time(value)
