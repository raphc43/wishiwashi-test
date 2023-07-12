import datetime
from datetime import timedelta

from celery.decorators import periodic_task
from celery.task.schedules import crontab
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.sessions.management.commands.clearsessions import Command as ClearSessions
from django.template.loader import render_to_string
from django.utils import timezone
from requests.auth import HTTPBasicAuth
import requests
import ujson as json
import pytz

from .models import (Order, PickupOrderReminder, CleanOnlyOrder,
                     DropoffOrderReminder, TrackConfirmedOrderSlots,
                     ExpectedBackCleanOnlyOrder)
from .clean_only import expected_back

logger = get_task_logger(__name__)


@periodic_task(run_every=crontab(minute="5"),  # minutes past each hour
               time_limit=120)
def push_orders_along(*args, **kwargs):
    now = timezone.now()
    two_hours_ago = now - timedelta(hours=2)

    # If a vendor claimed an order, assume they picked it up
    orders = Order.objects.filter(
        order_status=Order.CLAIMED_BY_VENDOR,
        authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
        charge_back_status=Order.NOT_CHARGED_BACK,
        refund_status=Order.NOT_REFUNDED,
        pick_up_time__lte=two_hours_ago)

    for order in orders:
        order.order_status = Order.RECEIVED_BY_VENDOR
        order.save()

    # If a vendor was due to deliver an order back, assume they have
    orders = Order.objects.filter(order_status=Order.RECEIVED_BY_VENDOR,
                                  drop_off_time__lte=two_hours_ago)

    for order in orders:
        order.order_status = Order.DELIVERED_BACK_TO_CUSTOMER
        order.save()

    return True


@periodic_task(run_every=crontab(minute=0, hour="*/4"),  # every x hour
               time_limit=120)  # seconds
def delete_old_sessions(*args, **kwargs):
    cmd = ClearSessions()
    cmd.handle()


@periodic_task(run_every=crontab(minute="*/10"),  # Exceute every x minutes
               time_limit=300)  # seconds
def pick_up_reminder_via_email(*args, **kwargs):
    auth = HTTPBasicAuth(settings.COMMUNICATE_SERVICE_USERNAME,
                         settings.COMMUNICATE_SERVICE_PASSWORD)

    now = timezone.now()
    hour_from_now = now + timedelta(hours=1)

    # If a vendor claimed an order, assume they picked it up
    orders = Order.objects.filter(
        order_status=Order.CLAIMED_BY_VENDOR,
        authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
        charge_back_status=Order.NOT_CHARGED_BACK,
        refund_status=Order.NOT_REFUNDED,
        pick_up_time__gt=now,
        pick_up_time__lt=hour_from_now)

    for order in orders:
        if not PickupOrderReminder.objects.filter(order=order).exists():
            try:
                subject = render_to_string('bookings/emails/pick-up-order-reminder-subject.txt', {'uuid': order.uuid})
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())

                html_content = render_to_string('bookings/emails/pick-up-order-reminder.html', {'order': order})
                text_content = render_to_string('bookings/emails/pick-up-order-reminder.txt', {'order': order})

                payload = {
                    'from_name': settings.FROM_EMAIL_NAME,
                    'from_email_address': settings.FROM_EMAIL_ADDRESS,
                    'subject': subject,
                    'html_content': html_content,
                    'text_content': text_content,
                    'recipients': [order.customer.email]
                }

                url = '%semail' % settings.COMMUNICATE_SERVICE_ENDPOINT
                resp = requests.post(url, data={'payload': json.dumps(payload)}, auth=auth, timeout=30, verify=False)
                assert resp.status_code == 200, 'HTTP %d from %s' % (resp.status_code, url)

                resp = json.loads(resp.content)

                assert resp['error'] is False, resp
                assert int(resp['job_id']) > 0, resp

                pickup_reminder = PickupOrderReminder(order=order)
                pickup_reminder.save()
            except Exception:
                msg = "Exception while sending pick up order reminder via email"
                logger.exception(msg)

    return True


@periodic_task(run_every=crontab(minute="*/10"),  # Exceute every x minutes
               time_limit=300)  # seconds
def drop_off_reminder_via_email(*args, **kwargs):
    auth = HTTPBasicAuth(settings.COMMUNICATE_SERVICE_USERNAME,
                         settings.COMMUNICATE_SERVICE_PASSWORD)

    now = timezone.now()
    hour_from_now = now + timedelta(hours=1)

    orders = Order.objects.filter(
        order_status=Order.RECEIVED_BY_VENDOR,
        authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
        charge_back_status=Order.NOT_CHARGED_BACK,
        refund_status=Order.NOT_REFUNDED,
        drop_off_time__gt=now,
        drop_off_time__lt=hour_from_now)

    for order in orders:
        if not DropoffOrderReminder.objects.filter(order=order).exists():
            try:
                subject = render_to_string('bookings/emails/drop-off-order-reminder-subject.txt', {'uuid': order.uuid})
                # Email subject *must not* contain newlines
                subject = ''.join(subject.splitlines())

                html_content = render_to_string('bookings/emails/drop-off-order-reminder.html', {'order': order})
                text_content = render_to_string('bookings/emails/drop-off-order-reminder.txt', {'order': order})

                payload = {
                    'from_name': settings.FROM_EMAIL_NAME,
                    'from_email_address': settings.FROM_EMAIL_ADDRESS,
                    'subject': subject,
                    'html_content': html_content,
                    'text_content': text_content,
                    'recipients': [order.customer.email]
                }

                url = '%semail' % settings.COMMUNICATE_SERVICE_ENDPOINT
                resp = requests.post(url, data={'payload': json.dumps(payload)}, auth=auth, timeout=30, verify=False)
                assert resp.status_code == 200, 'HTTP %d from %s' % (resp.status_code, url)

                resp = json.loads(resp.content)

                assert resp['error'] is False, resp
                assert int(resp['job_id']) > 0, resp

                dropoff_reminder = DropoffOrderReminder(order=order)
                dropoff_reminder.save()
            except Exception:
                msg = "Exception while sending drop off order reminder via email"
                logger.exception(msg)

    return True


@periodic_task(run_every=crontab(minute="0", hour="0"),  # midnight
               time_limit=120)
def cleanup_tracked_confirmed_order_slots(*args, **kwargs):
    now = timezone.now()
    five_weeks_ago = now - timedelta(weeks=5)

    for slot in TrackConfirmedOrderSlots.objects.filter(appointment__lte=five_weeks_ago):
        slot.delete()

    return True


@periodic_task(run_every=crontab(minute="0", hour="2,3"),
               time_limit=120)
def expected_back_clean_only_orders(*args, **kwargs):
    now = timezone.now()
    yesterday = now - timedelta(days=1)

    # Entire day yesterday
    start_dt = datetime.datetime.combine(yesterday.date(), yesterday.time().min).replace(tzinfo=pytz.utc)
    end_dt = datetime.datetime.combine(yesterday.date(), yesterday.time().max).replace(tzinfo=pytz.utc)

    for clean_only_order in CleanOnlyOrder.objects.filter(order__pick_up_time__range=(start_dt, end_dt),
                                                          order__order_status=Order.RECEIVED_BY_VENDOR,
                                                          order__placed=True):
        if not hasattr(clean_only_order, 'expectedbackcleanonlyorder'):
            try:
                expected_back_dt = expected_back(clean_only_order.order.drop_off_time)
                obj = ExpectedBackCleanOnlyOrder(clean_only_order=clean_only_order, expected_back=expected_back_dt)
                obj.save()
            except Exception:
                msg = "Exception adding expected back clean order {} for {}".format(clean_only_order.pk,
                                                                                    clean_only_order.order.uuid)
                logger.exception(msg)

    return True
