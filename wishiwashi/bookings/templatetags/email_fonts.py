from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()


@register.filter
@stringfilter
def email_fonts(value):
    return "'Helvetica Neue', 'Helvetica', Helvetica, Arial, sans-serif"
