# -*- coding: utf-8 -*-
from decimal import Decimal
import datetime
from datetime import timedelta

from base.celery import app
from celery.decorators import periodic_task
from celery.task.schedules import crontab
from celery.utils.log import get_task_logger
from django.conf import settings
from django.template import defaultfilters as filters
from django.template.loader import render_to_string
from django.utils import timezone
from requests.auth import HTTPBasicAuth
from ukpostcodeparser import parse_uk_postcode
import pytz
import requests
import ujson as json

from bookings.models import Order, Vendor, CleanOnlyOrder
from bookings.templatetags.phone_numbers import format_phone_number
from bookings.templatetags.postcodes import format_postcode
from customer_service.models import UserProfile
from .templatetags.add_one_hour import add_one_hour
from .payments import set_vendor_amount_due


logger = get_task_logger(__name__)


@periodic_task(run_every=crontab(minute="*/5"), # minutes
               time_limit=120) # seconds
def unaccepted_orders_go_to_wishiwashi(*args, **kwargs):
    now_utc = timezone.now()
    time_passed = now_utc - timedelta(minutes=1)

    # Wishi Washi accepts all valid orders which haven't been picked up by other vendors
    for order in Order.objects.filter(
            order_status=Order.UNCLAMIED_BY_VENDORS,
            authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
            charge_back_status=Order.NOT_CHARGED_BACK,
            refund_status=Order.NOT_REFUNDED,
            placed=True,
            placed_time__lte=time_passed):
        if not order.thrown_back_time or order.thrown_back_time < time_passed:
            order.order_status = Order.CLAIMED_BY_VENDOR
            order.assigned_to_vendor = Vendor.objects.get(pk=settings.VENDOR_WISHI_WASHI_PK)
            order.order_claimed_time = timezone.now()
            order.save()

    return True


def get_json_payload(order):
    london = pytz.timezone(settings.TIME_ZONE)
    profile = UserProfile.objects.get(user=order.customer)

    addr = '%s %s\n' % (order.pick_up_and_delivery_address.flat_number_house_number_building_name,
                        order.pick_up_and_delivery_address.address_line_1)

    if order.pick_up_and_delivery_address.address_line_2.strip() != '':
        addr += '%s\n' % order.pick_up_and_delivery_address.address_line_2

    addr += '%s, %s' % (
        order.pick_up_and_delivery_address.town_or_city,
        format_postcode(order.pick_up_and_delivery_address.postcode),
    )

    return {
        'order_uuid': order.uuid,
        'ticket_id': order.ticket_id,
        'customer_name': '%s %s' % (order.customer.first_name,
                                    order.customer.last_name),
        'customer_mobile_number': format_phone_number(profile.mobile_number),
        'collection_time': '%s - %s' % (
            filters.date(order.pick_up_time.astimezone(london), 'D, M jS gA'),
            filters.time(add_one_hour(order.pick_up_time.astimezone(london)), 'gA')
        ),
        'delivery_time': '%s - %s' % (
            filters.date(order.drop_off_time.astimezone(london), 'D, M jS gA'),
            filters.time(add_one_hour(order.drop_off_time).astimezone(london), 'gA')
        ),
        # use nl2br
        'customer_address': addr,
        'items': [{
            'name': item.item.vendor_friendly_name,
            'price': item.item.price,
            'quantity': item.quantity,
            'pieces': item.quantity * item.item.pieces,
        } for item in order.items.all()],
        'grand_total': order.total_price_of_order,
        'discount_percent': str(order.voucher.percentage_off)
        if order.voucher and order.voucher.percentage_off > Decimal('0.00') else '0'
    }


def get_order_headline_summary(order):
    london = pytz.timezone(settings.TIME_ZONE)
    out_code = parse_uk_postcode(order.pick_up_and_delivery_address.postcode)[0].upper()

    pick_up = order.pick_up_time.astimezone(london).strftime('%a %b %d %H')
    pick_up += '-%s' % add_one_hour(order.pick_up_time).astimezone(london).strftime('%H')

    drop_off = order.drop_off_time.astimezone(london).strftime('%a %b %d %H')
    drop_off += '-%s' % add_one_hour(order.drop_off_time).astimezone(london).strftime('%H')

    # £75 order in SW1 1AA (pickup Wed Nov 26 2-3pm,
    # drop off Fri Dec 15 2-8pm) order# ABCDE
    return u"£%s order in %s (pickup %s, drop off %s) order# %s" % (
        '{:,.2f}'.format(order.total_price_of_order),
        out_code,
        pick_up,
        drop_off,
        order.uuid
    )


def vendor_recipients(outcode=None):
    """
    Return a set of vendors.
    Optionally restrict to those who support a specific outcode
    """
    recipients = set()

    if outcode:
        outcode = outcode.lower()
        vendors = Vendor.objects.filter(catchment_area__out_code=outcode)
    else:
        vendors = Vendor.objects.all()

    for vendor in vendors:
        for user in vendor.staff.all():
            profile = UserProfile.objects.get(user=user)

            if profile.email_notifications_enabled:
                recipients.add(user.email)

    return recipients


@app.task(bind=True,
          default_retry_delay=180,
          max_retries=20,
          time_limit=160,
          throws=(ValueError,))
def notify_vendors_of_orders_via_email(self, order_id):
    if not settings.COMMUNICATE_SERVICE_ENDPOINT.startswith("http"):
        raise ValueError("communicate does not start with http: {}".format(settings.COMMUNICATE_SERVICE_ENDPOINT))

    order = Order.objects.get(pk=order_id)

    auth = HTTPBasicAuth(settings.COMMUNICATE_SERVICE_USERNAME,
                         settings.COMMUNICATE_SERVICE_PASSWORD)

    try:
        postcode = parse_uk_postcode(order.pick_up_and_delivery_address.postcode)
    except ValueError:
        msg = 'Invalid postcode {} for order: {}'.format(order.pick_up_and_delivery_address.postcode, order)
        logger.exception(msg)
        raise

    recipients = vendor_recipients(outcode=postcode[0].lower())

    if recipients:
        try:
            order_summary = get_order_headline_summary(order)
            html = render_to_string('vendors/emails/new_order_available.html',
                                    {'order': order, 'DOMAIN': settings.DOMAIN})
            text = render_to_string('vendors/emails/new_order_available.txt',
                                    {'order': order, 'DOMAIN': settings.DOMAIN})

            payload = {
                'from_name': settings.FROM_EMAIL_NAME,
                'from_email_address': settings.FROM_EMAIL_ADDRESS,
                'subject': order_summary,
                'html_content': html,
                'text_content': text,
                'recipients': list(recipients),
            }

            url = '%semail' % settings.COMMUNICATE_SERVICE_ENDPOINT
            resp = requests.post(url, data={'payload': json.dumps(payload)}, auth=auth, timeout=30, verify=False)
            assert resp.status_code == 200, 'HTTP %d from %s' % (resp.status_code, url)

            resp = json.loads(resp.content)

            assert resp['error'] is False, resp
            assert int(resp['job_id']) > 0, resp
        except Exception as exc:
            msg = 'Exception while requesting email transmission, retrying...'
            logger.exception(msg)
            raise self.retry(exc=exc)

    return True


@periodic_task(run_every=crontab(hour=5, minute=30), # UTC
               time_limit=160) # seconds
def assign_vendor_payments(*args, **kwargs):
    """
    If clean only order and expected back is confirmed, assign payments
    If clean and collect, charge when status is delivered back to customer
    """
    MAX_DAYS_BOOKING_PERIOD = 7 * 6  # 6 weeks covers maximum booking, from placement to delivery
    now_utc = timezone.now()
    yesterday = timezone.now() - timedelta(days=1)
    past = now_utc - timedelta(days=MAX_DAYS_BOOKING_PERIOD)

    # Start of day, in the past
    start_dt = datetime.datetime.combine(past.date(), past.time().min).replace(tzinfo=pytz.utc)

    # End of day yesterday
    end_dt = datetime.datetime.combine(yesterday.date(), yesterday.time().max).replace(tzinfo=pytz.utc)

    for order in Order.objects.filter(placed_time__range=(start_dt, end_dt),
                                      placed=True).exclude(
                                          order_status__in=[Order.UNCLAMIED_BY_VENDORS,
                                                            Order.ORDER_REJECTED_BY_SERVICE_PROVIDER]):
        # Skip already processed
        if hasattr(order, 'orderpayments'):
            continue

        # Clean only
        if hasattr(order, 'cleanonlyorder'):
            if (hasattr(order.cleanonlyorder, 'expectedbackcleanonlyorder') and
                    order.cleanonlyorder.expectedbackcleanonlyorder.confirmed_back is True):
                set_vendor_amount_due(order)
        else:
            if order.order_status == Order.DELIVERED_BACK_TO_CUSTOMER:
                set_vendor_amount_due(order)

    return True

@periodic_task(run_every=crontab(minute=15, hour='6,10,14,18,20,23'),
               time_limit=120) # seconds
def assign_all_orders_to_clean_only_vendor(*args, **kwargs):
    from_dt = timezone.now() - timedelta(days=1)

    # Wishi Washi assigns all orders to default clean only vendor
    default_vendor = Vendor.objects.get(pk=settings.VENDOR_DEFAULT_CLEAN_ONLY_PK)

    for order in Order.objects.filter(order_status__in=[Order.CLAIMED_BY_VENDOR, Order.RECEIVED_BY_VENDOR],
                                      assigned_to_vendor_id=settings.VENDOR_WISHI_WASHI_PK,
                                      placed=True,
                                      placed_time__gte=from_dt):
        if not hasattr(order, 'cleanonlyorder'):
            CleanOnlyOrder(order=order, assigned_to_vendor=default_vendor).save()

    return True


