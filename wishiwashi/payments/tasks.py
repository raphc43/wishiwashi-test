from datetime import timedelta

from base.celery import app
from celery.decorators import periodic_task
from celery.task.schedules import crontab
from celery.utils.log import get_task_logger
from dateutil.parser import parse
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.timezone import localtime as django_localtime
from requests.auth import HTTPBasicAuth
import requests
import stripe
import ujson as json

from bookings.calendar import get_icalendar_str
from bookings.models import Order
from . import utils
from .models import Stripe


logger = get_task_logger(__name__)


@periodic_task(run_every=crontab(minute=0, hour="22,23,0,1"), # UTC
               time_limit=600) # seconds
def capture_charge(*args, **kwargs):
    now_utc = timezone.now()

    two_hours_ago = now_utc - timedelta(hours=2)
    seven_days_ago = now_utc - timedelta(days=7)

    for stripe_charge in Stripe.objects.filter(
            authorisation_status=Stripe.SUCCESSFULLY_AUTHORISED,
            card_charged_status__in=[Stripe.NOT_CHARGED,
                                     Stripe.FAILED_TO_CHARGE],
            charge_back_status=Stripe.NOT_CHARGED_BACK,
            refund_status=Stripe.NOT_REFUNDED,
            order__pick_up_time__lte=two_hours_ago,
            successful_authorised_charge_time__gt=seven_days_ago
            ).exclude(order__order_status__in=[Order.ORDER_REJECTED_BY_SERVICE_PROVIDER]):
        try:
            stripe_charge.card_charged_status = Stripe.CHARGING
            stripe_charge.last_charged_event_time = timezone.now()
            stripe_charge.order.card_charged_status = Order.CHARGING
            stripe_charge.order.last_charged_event_time = timezone.now()

            stripe_charge.order.save()
            stripe_charge.save()

            utils.capture_charge(stripe_charge.charge)

            stripe_charge.card_charged_status = Stripe.SUCCESSFULLY_CHARGED
            stripe_charge.last_charged_event_time = timezone.now()
            stripe_charge.successful_charged_time = timezone.now()

            stripe_charge.order.card_charged_status = Order.SUCCESSFULLY_CHARGED
            stripe_charge.order.last_charged_event_time = timezone.now()
            stripe_charge.order.successful_charged_time = timezone.now()

            stripe_charge.order.save()
            stripe_charge.save()

            order_charged_confirmation_for_customer_via_email.delay(stripe_charge.order.pk)

            msg = 'Successfully captured charge: {}'.format(stripe_charge.order.pk)
            logger.info(msg)
        except stripe.error.CardError as error:
            stripe_charge.card_charged_status = Stripe.FAILED_TO_CHARGE
            stripe_charge.last_charged_event_time = timezone.now()

            stripe_charge.order.card_charged_status = Order.FAILED_TO_CHARGE
            stripe_charge.order.last_charged_event_time = timezone.now()

            stripe_charge.order.save()
            stripe_charge.save()

            msg = 'Captured charge failed: {0} {1}'.format(stripe_charge.order.pk, error)
            logger.error(msg)
        except Exception as error:
            stripe_charge.card_charged_status = Stripe.FAILED_TO_CHARGE
            stripe_charge.last_charged_event_time = timezone.now()

            stripe_charge.order.card_charged_status = Order.FAILED_TO_CHARGE
            stripe_charge.order.last_charged_event_time = timezone.now()

            stripe_charge.order.save()
            stripe_charge.save()

            msg = 'Error during charge capture: {0} {1}'.format(stripe_charge.order.pk, error)
            logger.exception(msg)
            raise

    return True


@app.task(bind=True,
          default_retry_delay=180, # seconds
          max_retries=20,
          time_limit=160)
def order_confirmation_for_customer_via_email(self, order_pk):
    auth = HTTPBasicAuth(settings.COMMUNICATE_SERVICE_USERNAME,
                         settings.COMMUNICATE_SERVICE_PASSWORD)

    order = Order.objects.get(pk=order_pk)

    charge_time = django_localtime(parse('%s 22:00:00+00:00' % order.pick_up_time.strftime('%Y-%m-%d')))

    subject = render_to_string('payments/emails/confirmation-order-subject.txt', {'uuid': order.uuid})

    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())

    html_content = render_to_string('payments/emails/confirmation-order.html',
                                    {'order': order, 'credit_card_charge_time': charge_time})
    text_content = render_to_string('payments/emails/confirmation-order.txt',
                                    {'order': order, 'credit_card_charge_time': charge_time})

    payload = {
        'from_name': settings.FROM_EMAIL_NAME,
        'from_email_address': settings.FROM_EMAIL_ADDRESS,
        'subject': subject,
        'html_content': html_content,
        'text_content': text_content,
        'recipients': [order.customer.email],
        'attachments': [{
            'name': 'wishi-washi-order-%s.ics' % order.uuid,
            'content': get_icalendar_str(order).decode(),
            'content_type': 'application/ics',
        }],
    }

    try:
        url = '%semail' % settings.COMMUNICATE_SERVICE_ENDPOINT
        resp = requests.post(url, data={'payload': json.dumps(payload)}, auth=auth, timeout=30, verify=False)
        assert resp.status_code == 200, 'HTTP %d from %s' % (resp.status_code, url)

        resp = json.loads(resp.content)

        assert resp['error'] is False, resp
        assert int(resp['job_id']) > 0, resp
    except Exception as exc:
        msg = 'Exception while sending order confirmation email. Retrying...'
        logger.exception(msg)
        raise self.retry(exc=exc)
    return True


@app.task(bind=True,
          default_retry_delay=180, # seconds
          max_retries=20,
          time_limit=160) # seconds
def order_charged_confirmation_for_customer_via_email(self, order_pk):
    auth = HTTPBasicAuth(settings.COMMUNICATE_SERVICE_USERNAME,
                         settings.COMMUNICATE_SERVICE_PASSWORD)

    order = Order.objects.get(pk=order_pk)

    subject = render_to_string('payments/emails/confirmation-charge-subject.txt', {'uuid': order.uuid})

    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())

    html_content = render_to_string('payments/emails/confirmation-charge.html', {'order': order})
    text_content = render_to_string('payments/emails/confirmation-charge.txt', {'order': order})

    payload = {
        'from_name': settings.FROM_EMAIL_NAME,
        'from_email_address': settings.FROM_EMAIL_ADDRESS,
        'subject': subject,
        'html_content': html_content,
        'text_content': text_content,
        'recipients': [order.customer.email],
    }

    try:
        url = '%semail' % settings.COMMUNICATE_SERVICE_ENDPOINT
        resp = requests.post(url, data={'payload': json.dumps(payload)}, auth=auth, timeout=30, verify=False)
        assert resp.status_code == 200, 'HTTP %d from %s' % (resp.status_code, url)

        resp = json.loads(resp.content)

        assert resp['error'] is False, resp
        assert int(resp['job_id']) > 0, resp
    except Exception as exc:
        msg = 'Exception while sending order confirmation email. Retrying...'
        logger.exception(msg)
        raise self.retry(exc=exc)
    return True
