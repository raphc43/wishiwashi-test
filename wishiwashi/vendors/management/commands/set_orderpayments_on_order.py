from django.core.management.base import BaseCommand, CommandError

from bookings.models import Order
from ...payments import set_vendor_amount_due


class Command(BaseCommand):
    help = 'Sets the total amount for each order that is valid'

    def add_arguments(self, parser):
        parser.add_argument('uuid', nargs='+', type=str)

    def handle(self, *args, **options):
        for uuid in options['uuid']:
            try:
                order = Order.objects.get(uuid=uuid,
                                          order_status__in=[Order.DELIVERED_BACK_TO_CUSTOMER,
                                                            Order.RECEIVED_BY_VENDOR],
                                          placed=True)
                total_price = set_vendor_amount_due(order)
            except Order.DoesNotExist:
                raise CommandError('uuid {} does not exist or is invalid'.format(uuid))

            self.stdout.write('Total amount set for {} {}'.format(uuid, total_price))

