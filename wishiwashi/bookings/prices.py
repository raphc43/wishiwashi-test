from decimal import Decimal
from payments.utils import transportation_charge
from .models import Item

TWOPLACES = Decimal('0.01')


def total_items_price(items):
    """ Total price for all items """
    return sum([Item.objects.get(pk=int(item_pk)).price * quantity for item_pk, quantity in items.items()])


def total_price(items, voucher=None):
    """
    items: dict of {item.pk: quantity,..}
    voucher: to be applied if exists
    """
    total_for_items = total_items_price(items)

    if voucher and total_for_items:
        discount = total_for_items * (voucher.percentage_off / Decimal('100'))
        new_total = total_for_items - discount
        return (new_total + transportation_charge(total_for_items)).quantize(TWOPLACES)

    return (total_for_items + transportation_charge(total_for_items)).quantize(TWOPLACES)
