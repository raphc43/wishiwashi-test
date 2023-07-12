import re
import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel


# list of verified out codes that are current
@python_2_unicode_compatible
class OutCodes(models.Model):
    # These are always in lower case
    out_code = models.CharField(max_length=4, unique=True, db_index=True)

    class Meta:
        verbose_name_plural = "Out codes"

    def __str__(self):
        return self.out_code


@python_2_unicode_compatible
class OutCodeNotServed(TimeStampedModel):
    out_code = models.CharField(max_length=4)  # min_length=2
    email_address = models.TextField()

    class Meta:
        verbose_name_plural = "Out codes not served"

    def __str__(self):
        return self.out_code


@python_2_unicode_compatible
class Address(models.Model):
    # no normalisation by address
    # TODO look at all address scenarios
    flat_number_house_number_building_name = models.CharField(max_length=75)  # address line 1? min_length=2
    address_line_1 = models.CharField(max_length=75)  # min_length=2
    address_line_2 = models.CharField(max_length=75)
    town_or_city = models.CharField(max_length=75)
    postcode = models.CharField(max_length=7)  # min_length=5

    # put company name, floor number, etc...
    instructions_for_delivery = models.TextField()

    def save(self, *args, **kwargs):
        """
        Postcodes are stored internally in their entire length, no spaces and
        all in lower case with no white space on either side of the postcode.

        If there is no postcode then it should allow the address record to save.
        """
        if self.postcode:
            assert len(self.postcode) >= 5 and len(self.postcode) <= 7
            _lower_case_no_spaces = re.sub(r'[^a-z0-9]*', '', self.postcode)
            assert _lower_case_no_spaces == self.postcode
        super(Address, self).save(*args, **kwargs)

    class Meta:
        verbose_name_plural = "Addresses"

    def __str__(self):
        return ", ".join(getattr(self, x) for x in [
            'flat_number_house_number_building_name',
            'address_line_1',
            'address_line_2',
            'town_or_city',
            'postcode'] if getattr(self, x))


@python_2_unicode_compatible
class OperatingTimeRange(models.Model):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5

    DAYS_OF_WEEK = (
        (MONDAY, 'Monday'),
        (TUESDAY, 'Tuesday'),
        (WEDNESDAY, 'Wednesday'),
        (THURSDAY, 'Thursday'),
        (FRIDAY, 'Friday'),
        (SATURDAY, 'Saturday'),
    )
    day_of_week = models.PositiveSmallIntegerField(default=MONDAY, choices=DAYS_OF_WEEK, db_index=True)
    start_hour = models.PositiveSmallIntegerField(validators=[MaxValueValidator(24), MinValueValidator(0)])
    # This is the cut off time, e.g. 14 means the cut off time is 14:00
    end_hour = models.PositiveSmallIntegerField(validators=[MaxValueValidator(24), MinValueValidator(0)])

    def __str__(self):
        return "{} {} - {}".format(
            OperatingTimeRange.DAYS_OF_WEEK[self.day_of_week][1],
            self.start_hour,
            self.end_hour
        )


# Is one vendor one location, not brand, not single owner
# each vendor is a shop
@python_2_unicode_compatible
class Vendor(models.Model):
    company_name = models.CharField(max_length=75)  # min_length=2
    address = models.ForeignKey(Address)
    staff = models.ManyToManyField(User)
    catchment_area = models.ManyToManyField(OutCodes)
    hours_of_operation = models.ManyToManyField(OperatingTimeRange)
    capacity_per_hour = models.PositiveSmallIntegerField(default=0)  # Relates to driver capacity, not washing capacity
    last_viewed_the_orders_page = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.company_name


@python_2_unicode_compatible
class Category(models.Model):
    name = models.CharField(max_length=75)  # min_length=2
    description = models.TextField()
    visible = models.BooleanField(default=False)
    order_priority = models.FloatField(default=1.0)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Item(models.Model):
    name = models.TextField()
    vendor_friendly_name = models.TextField(blank=True, default='')
    category = models.ForeignKey(Category)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))  # baking item price?
    # FileField is tied to the MEDIA_UPLOADS folder, this is just a reference
    # to a static file
    image = models.TextField()
    description = models.TextField()
    visible = models.BooleanField(default=False)
    order_priority = models.FloatField(default=1.0)
    pieces = models.PositiveIntegerField(default=1, help_text="The number of pieces that make up this item")

    def __str__(self):
        return "{} - {}".format(self.category.name, self.name)


@python_2_unicode_compatible
class Voucher(TimeStampedModel):
    issued_by = models.ForeignKey(User)
    percentage_off = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0.0'))
    # e.g. SOMEVOUCHERCODE
    voucher_code = models.CharField(max_length=75, unique=True)  # min_length=2

    # If either the valid_until UTC timezone has past or the use_count has
    # past the use_limit then
    # the voucher should no longer be active.
    valid_until = models.DateTimeField()
    use_limit = models.PositiveIntegerField(default=0)
    use_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.voucher_code


@python_2_unicode_compatible
class ItemAndQuantity(models.Model):
    item = models.ForeignKey(Item, null=True)
    quantity = models.PositiveSmallIntegerField(validators=[MaxValueValidator(10), MinValueValidator(0)])
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name_plural = "Item and quantities"

    def __str__(self):
        return "{} x {} ({:.2f})".format(self.quantity, self.item.name, self.price)


def ticket_id_uuid():
    return str(uuid.uuid4())[:11]


@python_2_unicode_compatible
class Order(TimeStampedModel):
    uuid = models.CharField(max_length=8, unique=True)
    assigned_to_vendor = models.ForeignKey(Vendor, null=True, blank=True)
    items = models.ManyToManyField(ItemAndQuantity)

    total_price_of_order = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    pick_up_time = models.DateTimeField(null=True)
    drop_off_time = models.DateTimeField(null=True)
    pick_up_and_delivery_address = models.ForeignKey(Address, related_name='pick_up_and_delivery', null=True)
    customer = models.ForeignKey(User, null=True)
    voucher = models.ForeignKey(Voucher, null=True, blank=True)

    transportation_charge = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    vat_charge = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    price_excluding_vat_charge = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    placed = models.BooleanField(default=False, db_index=True)  # Order placed successfully
    placed_time = models.DateTimeField(null=True, blank=True)
    ticket_id = models.CharField(max_length=11, blank=True, null=True, db_index=True)

    # Authorisation
    NOT_ATTEMPTED_AUTHORISATION = 0
    AUTHORISING = 1
    FAILED_TO_AUTHORISE = 2
    SUCCESSFULLY_AUTHORISED = 3

    AUTHORISATION_STATUSES = (
        (NOT_ATTEMPTED_AUTHORISATION, 'Yet to attempt authorisation'),
        (AUTHORISING, 'Authorising'),
        (FAILED_TO_AUTHORISE, 'Failed to authorise'),
        (SUCCESSFULLY_AUTHORISED, 'Successfully authorised'),
    )
    authorisation_status = models.PositiveSmallIntegerField(default=NOT_ATTEMPTED_AUTHORISATION,
                                                            choices=AUTHORISATION_STATUSES,
                                                            db_index=True)

    # Charging
    NOT_CHARGED = 0
    CHARGING = 1
    FAILED_TO_CHARGE = 2
    SUCCESSFULLY_CHARGED = 3

    CHARING_STATUSES = (
        (NOT_CHARGED, 'Not charged'),
        (CHARGING, 'Charging'),
        (FAILED_TO_CHARGE, 'Failed to charge'),
        (SUCCESSFULLY_CHARGED, 'Successfully Charged'),
    )
    card_charged_status = models.PositiveSmallIntegerField(default=NOT_CHARGED,
                                                           choices=CHARING_STATUSES,
                                                           db_index=True)

    # Charge backs
    NOT_CHARGED_BACK = 0
    CHARGED_BACK = 1
    DISPUTE_RESOLVED_OUR_FAVOUR = 2
    DISPUTE_RESOLVED_CUSTOMER_FAVOUR = 3

    CHARGE_BACK_STATUSES = (
        (NOT_CHARGED_BACK, 'Not charged back'),
        (CHARGED_BACK, 'Charged back'),
        (DISPUTE_RESOLVED_OUR_FAVOUR, 'Dispute resolved in our favour'),
        (DISPUTE_RESOLVED_CUSTOMER_FAVOUR, 'Dispute resolved in their favour'),
    )
    charge_back_status = models.PositiveSmallIntegerField(default=NOT_CHARGED_BACK,
                                                          choices=CHARGE_BACK_STATUSES,
                                                          db_index=True)

    # Refund
    NOT_REFUNDED = 0
    REFUNDING = 1
    FULL_REFUND = 2
    PARTIAL_REFUND = 3
    FAILED_TO_REFUND = 4

    REFUND_STATUSES = (
        (NOT_REFUNDED, 'Not refunded'),
        (REFUNDING, 'Refunding'),
        (FULL_REFUND, 'Full Refund'),
        (PARTIAL_REFUND, 'Partial Refund'),
        (FAILED_TO_REFUND, 'Failed to refund'),
    )

    refund_status = models.PositiveSmallIntegerField(default=NOT_REFUNDED,
                                                     choices=REFUND_STATUSES,
                                                     db_index=True)

    # status of items, can only be one of the following but not more than one
    UNCLAMIED_BY_VENDORS = 0
    CLAIMED_BY_VENDOR = 1
    RECEIVED_BY_VENDOR = 2
    UNABLE_TO_PICK_UP_ITEMS = 3
    CONTESTED_ITEMS_IN_ORDER = 4
    # CONTESTED_ITEMS_RESOLVED = 5
    DELIVERED_BACK_TO_CUSTOMER = 6
    UNABLE_TO_DELIVER_BACK_TO_CUSTOMER = 7
    # e.g. If we internally test an order or we can't contact a customer
    ORDER_REJECTED_BY_SERVICE_PROVIDER = 8

    ORDER_STATUSES = (
        (UNCLAMIED_BY_VENDORS, 'Unclaimed by vendors'),
        (CLAIMED_BY_VENDOR, 'Claimed by vendor'),
        (RECEIVED_BY_VENDOR, 'Received by vendor'),
        (UNABLE_TO_PICK_UP_ITEMS, 'Unable to pick up items'),
        (CONTESTED_ITEMS_IN_ORDER, 'Contested items in order'),
        # (CONTESTED_ITEMS_RESOLVED, ''),
        (DELIVERED_BACK_TO_CUSTOMER, 'Delivered back to customer'),
        (UNABLE_TO_DELIVER_BACK_TO_CUSTOMER, 'Unable to deliver back to customer'),
        (ORDER_REJECTED_BY_SERVICE_PROVIDER, 'Order rejected by service provider'),
    )

    order_status = models.PositiveSmallIntegerField(default=UNCLAMIED_BY_VENDORS,
                                                    choices=ORDER_STATUSES,
                                                    db_index=True)

    order_claimed_time = models.DateTimeField(null=True, blank=True)
    thrown_back_time = models.DateTimeField(null=True, blank=True)
    ipaddress = models.GenericIPAddressField(blank=True, null=True)

    def __str__(self):
        return self.uuid


@python_2_unicode_compatible
class CleanOnlyOrder(TimeStampedModel):
    """
    These contain orders which are assigned to vendors who are going to handle the cleaning of the order
    """
    order = models.OneToOneField(Order)
    assigned_to_vendor = models.ForeignKey(Vendor)

    def __str__(self):
        return self.order.uuid

    class Meta:
        verbose_name_plural = "Clean only orders"


@python_2_unicode_compatible
class ExpectedBackCleanOnlyOrder(models.Model):
    """
    Expected back from assigned vendor from clean only vendor
    The order needs to be back by a specific date/time so delivery can go back to customer
    within their allocated delivery time slot
    """
    clean_only_order = models.OneToOneField(CleanOnlyOrder)
    expected_back = models.DateTimeField()
    confirmed_back = models.BooleanField(default=False)

    def __str__(self):
        return self.clean_only_order.order.uuid

    class Meta:
        verbose_name_plural = "Expected back clean only orders"


@python_2_unicode_compatible
class OrderNotes(TimeStampedModel):
    order = models.ForeignKey(Order)
    description = models.TextField()

    def __str__(self):
        return self.description

    class Meta:
        verbose_name_plural = "Order Notes"


class AbandonedOrders(TimeStampedModel):
    vendor = models.ForeignKey(Vendor)
    order = models.ForeignKey(Order)

    class Meta:
        verbose_name_plural = "Abandoned orders"


class PickupOrderReminder(TimeStampedModel):
    order = models.ForeignKey(Order)

    class Meta:
        verbose_name_plural = "Pick up order reminders"


class DropoffOrderReminder(TimeStampedModel):
    order = models.ForeignKey(Order)

    class Meta:
        verbose_name_plural = "Drop off order reminders"


class TrackConfirmedOrderSlots(models.Model):
    # Pick up or drop off slot
    appointment = models.DateTimeField()
    counter = models.PositiveSmallIntegerField(default=0)

