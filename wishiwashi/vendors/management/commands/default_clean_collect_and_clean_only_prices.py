from decimal import Decimal
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand

from bookings.models import Item
from vendors.models import DefaultCleanOnlyPrices, DefaultCleanAndCollectPrices

CLEAN_AND_COLLECT = Decimal('0.7')
CLEAN_ONLY = Decimal('0.45')
MINIMUM_PRICE = Decimal('1.00')


class Command(BaseCommand):
    help = 'Sets/resets the default values for clean only and clean and collect prices'

    def handle(self, *args, **options):
        for item in Item.objects.all():
            ex_vat = (item.price / Decimal('1.2')).quantize(Decimal('0.00'))
            co_price = (ex_vat * CLEAN_ONLY).quantize(Decimal('0.00'))
            co_price = co_price if co_price > MINIMUM_PRICE else MINIMUM_PRICE

            """
            try:
                clean_only = DefaultCleanOnlyPrices.objects.get(item=item)
                clean_only.price = co_price
            except ObjectDoesNotExist:
                clean_only = DefaultCleanOnlyPrices(item=item, price=co_price)

            clean_only.save()

            self.stdout.write('Clean only price set for {} {} {}'.format(item.id, item.name, co_price))
            """

            cc_price = (ex_vat * CLEAN_AND_COLLECT).quantize(Decimal('0.00'))
            cc_price = cc_price if cc_price > MINIMUM_PRICE else MINIMUM_PRICE
            try:
                clean_and_collect = DefaultCleanAndCollectPrices.objects.get(item=item)
                clean_and_collect.price = cc_price
            except ObjectDoesNotExist:
                clean_and_collect = DefaultCleanAndCollectPrices(item=item, price=cc_price)

            clean_and_collect.save()

            self.stdout.write('Clean/collect price set for {} {} {}'.format(item.id, item.name, cc_price))

