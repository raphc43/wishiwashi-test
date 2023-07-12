from decimal import Decimal
from django.contrib.auth.models import User
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel

from bookings.models import Item, Order, Vendor


class OrderStats(TimeStampedModel):
    business_last_24_hours = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    avg_delta_to_acceptance = models.FloatField(default=0.0)
    other_vendors_viewing = models.IntegerField(default=0)
    top_out_code_percentage = models.FloatField(default=0.0)
    top_out_code = models.CharField(max_length=4, default='')


class OrdersAwaitingRenderingAndSending(TimeStampedModel):
    orders = models.ManyToManyField(Order)
    recipients = models.ManyToManyField(User)
    render_service_job_uuid = models.CharField(max_length=16)
    communicate_service_job_uuid = models.CharField(max_length=16)

    pdf_url = models.CharField(max_length=255)

    UNTOUCHED = 0
    REQUESTING_RENDER = 1
    RENDERING = 2
    RENDERED = 3
    FAILED_TO_RENDER = 4

    REQUESTING_SENDING = 5
    SENDING = 6
    SENT = 7
    FAILED_TO_SEND = 8

    STATUSES = (
        (UNTOUCHED, 'Untouched'),
        (REQUESTING_RENDER, 'Requesting Render'),
        (RENDERING, 'Rendering'),
        (RENDERED, 'Rendered'),
        (FAILED_TO_RENDER, 'Failed to render'),
        (REQUESTING_SENDING, 'Requesting sending'),
        (SENDING, 'Sending'),
        (SENT, 'Sent'),
        (FAILED_TO_SEND, 'Failed to send'),
    )

    status = models.PositiveSmallIntegerField(default=UNTOUCHED,
                                              choices=STATUSES,
                                              db_index=True)


@python_2_unicode_compatible
class IssueType(models.Model):
    CONTACT_DETAILS = 0
    PICK_UP_DROP_OFF_DETAILS = 1
    ITEMS = 2

    CATEGORIES = (
        (CONTACT_DETAILS, 'Contact Details'),
        (PICK_UP_DROP_OFF_DETAILS, 'Pick-up/Drop-off details'),
        (ITEMS, 'Item(s)'),
    )

    category = models.PositiveSmallIntegerField(default=CONTACT_DETAILS,
                                                choices=CATEGORIES,
                                                db_index=True)
    description = models.CharField(max_length=255)

    def category_name(self):
        return self.CATEGORIES[self.category][1]

    class Meta:
        verbose_name_plural = "Types of Issues"

    def __str__(self):
        return "{} - {}".format(self.get_category_display(),
                                self.description)


class OrderIssue(TimeStampedModel):
    issue_raised_by = models.ForeignKey(User)
    order = models.ForeignKey(Order)
    issue = models.ForeignKey(IssueType)
    is_other_issue = models.BooleanField(default=False)
    other_issue_details = models.TextField(default='')
    item = models.ForeignKey(Item, null=True)

    RAISED = 0
    ACKNOWLEDGED_BY_CUSTOMER_SERVICE = 1
    RESOVLED = 2

    STATUSES = (
        (RAISED, 'Raised'),
        (ACKNOWLEDGED_BY_CUSTOMER_SERVICE, 'Acknowledged by Customer Service'),
        (RESOVLED, 'Resolved'),
    )

    status = models.PositiveSmallIntegerField(default=RAISED,
                                              choices=STATUSES,
                                              db_index=True)

    class Meta:
        verbose_name_plural = "Vendor Order Issues"


@python_2_unicode_compatible
class CleanOnlyPrices(models.Model):
    vendor = models.ForeignKey(Vendor)
    item = models.ForeignKey(Item)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return "{} {} {}".format(self.vendor.company_name,
                                 self.item.name,
                                 self.price)

    class Meta:
        verbose_name_plural = "Clean only prices"
        unique_together = ("vendor", "item")


@python_2_unicode_compatible
class CleanAndCollectPrices(models.Model):
    vendor = models.ForeignKey(Vendor)
    item = models.ForeignKey(Item)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return "{} {} {}".format(self.vendor.company_name,
                                 self.item.name,
                                 self.price)

    class Meta:
        verbose_name_plural = "Clean and collect prices"
        unique_together = ("vendor", "item")


@python_2_unicode_compatible
class DefaultCleanOnlyPrices(models.Model):
    item = models.OneToOneField(Item)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return "{} {}".format(self.item.name, self.price)

    class Meta:
        verbose_name_plural = "Default clean only prices"


@python_2_unicode_compatible
class DefaultCleanAndCollectPrices(models.Model):
    item = models.OneToOneField(Item)
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    def __str__(self):
        return "{} {}".format(self.item.name, self.price)

    class Meta:
        verbose_name_plural = "Default clean and collect prices"


@python_2_unicode_compatible
class OrderPayments(models.Model):
    order = models.OneToOneField(Order)
    total_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))

    def __str__(self):
        return "{} {}".format(self.order.uuid, self.total_amount)

    class Meta:
        verbose_name_plural = "Payments due to Vendors"

