import logging

from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from vendors.models import (CleanOnlyPrices, DefaultCleanOnlyPrices,
                            CleanAndCollectPrices, DefaultCleanAndCollectPrices,
                            OrderPayments)


logger = logging.getLogger(__name__)


def clean_only_amount(order):
    total = Decimal('0.00')
    for item in order.items.all():
        try:
            obj = CleanOnlyPrices.objects.get(vendor=order.cleanonlyorder.assigned_to_vendor, item=item.item)
        except ObjectDoesNotExist:
            obj = DefaultCleanOnlyPrices.objects.get(item=item.item)
        except MultipleObjectsReturned:
            # log error - but continue to process using initial value
            logger.error("Clean only prices contains an item multiple times. Model: {} item: {}".format(
                "CleanOnlyPrices", item.item.id)
            )
            obj = CleanOnlyPrices.objects.filter(item=item.item)[0]

        total += obj.price * Decimal(item.quantity)

    return total


def clean_and_collect_amount(order):
    total = Decimal('0.00')
    for item in order.items.all():
        try:
            obj = CleanAndCollectPrices.objects.get(vendor=order.assigned_to_vendor, item=item.item)
        except ObjectDoesNotExist:
            obj = DefaultCleanAndCollectPrices.objects.get(item=item.item)
        except MultipleObjectsReturned:
            # log error - but continue to process using initial value
            logger.error("Clean and collect prices contains an item multiple times. Model: {} item: {}".format(
                "CleanAndCollectPrices", item.item.id)
            )
            obj = CleanAndCollectPrices.objects.filter(item=item.item)[0]

        total += obj.price * Decimal(item.quantity)

    return total


def total_amount_due(order):
    """
    Total amount due to vendor based on order
    Order can be assigned as a Clean only order (Wishi Washi do Collect and Delivery)
    or order can be handled exclusively by a vendor (Collect - Clean - Deliver)
    """
    if hasattr(order, 'cleanonlyorder'):
        total = clean_only_amount(order)
    else:
        total = clean_and_collect_amount(order)

    return total


def set_vendor_amount_due(order):
    """
    Set the total amount due to vendor for order.
    Existing order if found is updated or a new one is created.

    Args:
        order: The order object

    Returns:
        Decimal: Total amount due to vendor for this order
    """
    total_amount = total_amount_due(order)
    try:
        order_payment = OrderPayments.objects.get(order=order)
        order_payment.total_amount = total_amount
    except ObjectDoesNotExist:
        order_payment = OrderPayments(order=order, total_amount=total_amount)

    order_payment.save()

    return total_amount
