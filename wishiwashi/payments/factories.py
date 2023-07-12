import factory

from bookings.factories import OrderFactory
from .models import  Stripe


class StripeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Stripe
    order = factory.SubFactory(OrderFactory)

