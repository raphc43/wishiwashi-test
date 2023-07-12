import factory

from bookings.factories import OrderFactory, ItemFactory, VendorFactory
from ..models import (OrderPayments, CleanAndCollectPrices, CleanOnlyPrices,
                      DefaultCleanAndCollectPrices, DefaultCleanOnlyPrices)


class OrderPaymentsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderPayments
    order = factory.SubFactory(OrderFactory)


class CleanOnlyPricesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CleanOnlyPrices
    vendor = factory.SubFactory(VendorFactory)
    item = factory.SubFactory(ItemFactory)


class CleanAndCollectPricesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CleanAndCollectPrices
    vendor = factory.SubFactory(VendorFactory)
    item = factory.SubFactory(ItemFactory)

class DefaultCleanOnlyPricesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DefaultCleanOnlyPrices
    item = factory.SubFactory(ItemFactory)


class DefaultCleanAndCollectPricesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DefaultCleanAndCollectPrices
    item = factory.SubFactory(ItemFactory)
