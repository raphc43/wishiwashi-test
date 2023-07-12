import datetime
from django.utils import timezone

from django.contrib.auth.models import User
import factory
from factory import fuzzy

from .models import (Address, Category, CleanOnlyOrder, Item, ItemAndQuantity, Order, OutCodes, Vendor, Voucher,
                     OperatingTimeRange, TrackConfirmedOrderSlots, ExpectedBackCleanOnlyOrder)


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: "user%05d.com" % n)
    email = factory.Sequence(lambda n: "test%05d@test%03d.com" % (n, n))
    password = "testing123"

    @classmethod
    def _prepare(cls, create, **kwargs):
        password = kwargs.pop('password', None)
        user = super(UserFactory, cls)._prepare(create, **kwargs)
        if password:
            user.set_password(password)
            if create:
                user.save()
        return user


class AddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Address
    flat_number_house_number_building_name = factory.Sequence(
        lambda n: "%d" % n)
    address_line_1 = factory.Sequence(lambda n: "Address line %03d" % n)
    address_line_2 = factory.Sequence(lambda n: "Address line %03d" % n)
    town_or_city = factory.Sequence(lambda n: "Town %03d" % n)
    postcode = "sw57ty"
    instructions_for_delivery = "Test instructions"


class OutCodesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OutCodes
    out_code = factory.Sequence(lambda n: "sw%d" % (n % 99))


class OperatingTimeRangeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OperatingTimeRange
    day_of_week = 0
    start_hour = 8
    end_hour = 20


class VendorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Vendor
    company_name = factory.Sequence(lambda n: "Company %03d" % n)
    address = factory.SubFactory(AddressFactory)

    @factory.post_generation
    def staff(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for user in extracted:
                self.staff.add(user)

    @factory.post_generation
    def catchment_area(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for area in extracted:
                self.catchment_area.add(area)

    @factory.post_generation
    def hours_of_operation(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for hour in extracted:
                self.hours_of_operation.add(hour)

    capacity_per_hour = 2


class CategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Category
    name = factory.Sequence(lambda n: "Cat: %03d" % n)
    visible = True


class ItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Item
    name = factory.Sequence(lambda n: "Item: %03d" % n)
    category = factory.SubFactory(CategoryFactory)
    visible = True


class ItemAndQuantityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ItemAndQuantity
    quantity = 1
    item = factory.SubFactory(ItemFactory)


class VoucherFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Voucher
    issued_by = factory.SubFactory(UserFactory)
    percentage_off = 5.0
    voucher_code = factory.Sequence(lambda n: "CODE%03d" % n)
    issued_by = factory.SubFactory(UserFactory)
    valid_until = fuzzy.FuzzyDateTime(timezone.now() + datetime.timedelta(days=1),
                                      timezone.now() + datetime.timedelta(days=7))
    use_limit = 10


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order
    uuid = factory.Sequence(lambda n: "%05d" % n)
    assigned_to_vendor = factory.SubFactory(VendorFactory)

    @factory.post_generation
    def items(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for item in extracted:
                self.items.add(item)

    pick_up_time = fuzzy.FuzzyDateTime(timezone.now(), timezone.now() + datetime.timedelta(hours=1))
    drop_off_time = factory.LazyAttribute(lambda o: o.pick_up_time + datetime.timedelta(hours=48))
    pick_up_and_delivery_address = factory.SubFactory(AddressFactory)
    customer = factory.SubFactory(UserFactory)


class TrackConfirmedOrderSlotsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TrackConfirmedOrderSlots
    appointment = fuzzy.FuzzyDateTime(timezone.now(), timezone.now() + datetime.timedelta(hours=1))
    counter = 0


class CleanOnlyOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = CleanOnlyOrder
    order = factory.SubFactory(OrderFactory)
    assigned_to_vendor = factory.SubFactory(VendorFactory)


class ExpectedBackCleanOnlyOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExpectedBackCleanOnlyOrder
    clean_only_order = factory.SubFactory(CleanOnlyOrderFactory)
    expected_back = fuzzy.FuzzyDateTime(timezone.now() - datetime.timedelta(hours=24), timezone.now())


