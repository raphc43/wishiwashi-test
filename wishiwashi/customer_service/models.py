from django.contrib.auth.models import User
from django.db import models
from model_utils.models import TimeStampedModel

from bookings.models import Item, Order, Vendor


class UserProfile(models.Model):
    user = models.OneToOneField(User)

    is_customer_service_agent = models.BooleanField(default=False)
    # is staff (simon and mark)

    # what if phone number is taken by other customer?
    # http://en.wikipedia.org/wiki/UK_telephone_code_misconceptions
    # ... as a rule they do not exceed 11 digits in combined length.
    # 11 chars: 01234 123 123
    # 10 chars: 1234 123 123
    # 14 chars: 0044 1234 123 123

    # Min length? is this restriction needed as we're validating the mobile
    # number anyway
    mobile_number = models.CharField(max_length=14, db_index=True)

    # Vendor-only settings
    sms_notifications_enabled = models.BooleanField(default=False)
    email_notifications_enabled = models.BooleanField(default=False)

    # Django allauth handles this?
    # email_address_validated True/False
    # mobile_number_validated True/False


class CustomerContactTemplate(models.Model):
    EMAIL = 0
    SMS = 1

    TYPES = (
        (EMAIL, 'E-mail'),
        (SMS, 'SMS'),
    )

    communication_type = models.PositiveSmallIntegerField(default=EMAIL,
                                                          choices=TYPES,
                                                          db_index=True)
    body = models.TextField()
    body_html = models.TextField() # optional
    subject = models.TextField() # optional


class MessageToCustomer(TimeStampedModel):
    sent_by = models.ForeignKey(User, related_name='send_by')
    sent_to = models.ForeignKey(User, related_name='send_to')
    template = models.ForeignKey(CustomerContactTemplate)

    # We will need API endpoint for service tool to communicate updates to this
    # code base's installation

    UNSENT = 0
    SENDING = 1
    REJECTED_BY_SES = 2
    SENT = 3
    STOP_ATTEMPTS_TO_SEND = 4

    STATUSES = (
        (UNSENT, 'Unsent'),
        (SENDING, 'Sending'),
        (REJECTED_BY_SES, 'Rejected by Amazon SES'),
        (SENT, 'Sent'),
        (STOP_ATTEMPTS_TO_SEND, 'Stop attempting to send'),
    )

    status = models.PositiveSmallIntegerField(
        default=UNSENT,
        choices=STATUSES,
        db_index=True)
    resend_attempts = models.IntegerField(default=0)
    ses_rejection_reason = models.TextField()


class Ticket(TimeStampedModel):
    customer_service_owners = models.ManyToManyField(User)
    order = models.ForeignKey(Order)

    UNACKNOWLEDGED = 0
    ACKNOWLEDGED = 1
    RESOLVED = 2
    UNABLE_TO_RESOLVE = 3
    STATUSES = (
        (UNACKNOWLEDGED, 'Unacknowledged'),
        (ACKNOWLEDGED, 'Acknowledged'),
        (RESOLVED, 'Resolved'),
        (UNABLE_TO_RESOLVE, 'Unable to resolve'),
    )

    status = models.PositiveSmallIntegerField(
        default=UNACKNOWLEDGED,
        choices=STATUSES,
        db_index=True)
