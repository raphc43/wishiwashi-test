from decimal import Decimal

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from model_utils.models import TimeStampedModel

from bookings.models import Order


@python_2_unicode_compatible
class Stripe(TimeStampedModel):
    order = models.ForeignKey(Order)
    token = models.CharField(max_length=255)
    charge = models.CharField(max_length=255, null=True, blank=True)

    amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))
    refund_amount = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'))

    cvv2_code_check_passed = models.BooleanField(default=False)
    postcode_check_passed = models.BooleanField(default=False)

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
    authorisation_status = \
        models.PositiveSmallIntegerField(
            default=NOT_ATTEMPTED_AUTHORISATION,
            choices=AUTHORISATION_STATUSES,
            db_index=True)

    last_authorised_charge_time = models.DateTimeField(null=True, blank=True)
    successful_authorised_charge_time = models.DateTimeField(null=True, blank=True)

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
    card_charged_status = \
        models.PositiveSmallIntegerField(default=NOT_CHARGED,
                                         choices=CHARING_STATUSES,
                                         db_index=True)

    last_charged_event_time = models.DateTimeField(null=True, blank=True)
    successful_charged_time = models.DateTimeField(null=True, blank=True)

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
    charge_back_status = \
        models.PositiveSmallIntegerField(default=NOT_CHARGED_BACK,
                                         choices=CHARGE_BACK_STATUSES,
                                         db_index=True)

    charge_back_time = models.DateTimeField(null=True, blank=True)
    charge_back_last_event_time = models.DateTimeField(null=True, blank=True)

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

    refund_successful_time = models.DateTimeField(null=True, blank=True)
    last_refund_event_time = models.DateTimeField(null=True, blank=True)
    ipaddress = models.GenericIPAddressField(blank=True, null=True)

    description = models.TextField("Error message", blank=True, null=True)

    class Meta:
        verbose_name = "Stripe Charge"
        verbose_name_plural = "Stripe Charges"

    def __str__(self):
        return self.token

