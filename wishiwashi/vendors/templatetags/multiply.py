from django import template

register = template.Library()


@register.filter
def multiply(quantity, pieces):
    return quantity * pieces
