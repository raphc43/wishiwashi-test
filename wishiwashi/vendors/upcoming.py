from datetime import timedelta, datetime

from django.conf import settings
from django.db.models import Q
from django.utils import timezone
import pytz

from bookings.models import Order
from .orders import sort_orders_upcoming


def orders_upcoming(vendor, start_dt, end_dt):
    orders = Order.objects.filter(
        Q(drop_off_time__range=(start_dt, end_dt)) | Q(pick_up_time__range=(start_dt, end_dt)),
        assigned_to_vendor=vendor,
        placed=True
        ).exclude(order_status__in=[Order.UNCLAMIED_BY_VENDORS,
                                    Order.ORDER_REJECTED_BY_SERVICE_PROVIDER])

    for order in orders:
        setattr(order, 'upcoming_date', start_dt.date())

    return sort_orders_upcoming(orders)


def monday_start_sunday_end_datetime_range(dt=None):
    """"
    Returns tuple with datetime starting from monday, and ending on following sunday
    """
    if dt is None:
        dt = timezone.localtime(timezone.now())

    start = (dt - timedelta(days=dt.weekday())).replace(hour=datetime.min.hour,
                                                        second=datetime.min.minute,
                                                        minute=datetime.min.second,
                                                        microsecond=datetime.min.microsecond)

    end = (start + timedelta(days=6)).replace(hour=datetime.max.hour,
                                              second=datetime.max.second,
                                              minute=datetime.max.minute,
                                              microsecond=datetime.max.microsecond)

    return (start, end)


def weekly_empty_list():
    """
    Returns grid list of one empty weekly range

         Mon Tue Wed Thu...-Sun
    8am  []  []  []  []
    ...
    10pm []  []  []  []

    Grid list
    [
        [[], [], [], []...], # 8am - 9am
        [[], [], [], []...], # 9am - 10am
        ....
    ]
    Position:
        0,0 == 8am, Monday
        1,3 == 9am, Thursday
    """

    week = []
    for slot in range(settings.COLLECT_DELIVER_HOUR_START, settings.COLLECT_DELIVER_HOUR_END):
        week.append([[] for day in range(0, 7)])

    return week


def weekly_hourly_booked_slots(orders, start_dt, end_dt):
    """
    Populate weekly list with orders
    """
    weekly_orders = weekly_empty_list()

    local = pytz.timezone(settings.TIME_ZONE)
    for order in orders:

        if start_dt <= order.pick_up_time <= end_dt:
            local_pick_up_time = order.pick_up_time.astimezone(local)
            weekly_orders[
                local_pick_up_time.hour - settings.COLLECT_DELIVER_HOUR_START
            ][local_pick_up_time.weekday()].append({
                "pk": order.pk,
                "collect": True,
                "order": order.uuid,
                "status_display": order.get_order_status_display(),
                "status": order.order_status,
                "ticket_id": order.ticket_id,
                "postcode": order.pick_up_and_delivery_address.postcode
            })

        if start_dt <= order.drop_off_time <= end_dt:
            local_drop_off_time = order.drop_off_time.astimezone(local)
            weekly_orders[
                local_drop_off_time.hour - settings.COLLECT_DELIVER_HOUR_START
            ][local_drop_off_time.weekday()].append({
                "pk": order.pk,
                "collect": False,
                "order": order.uuid,
                "status_display": order.get_order_status_display(),
                "status": order.order_status,
                "ticket_id": order.ticket_id,
                "postcode": order.pick_up_and_delivery_address.postcode
            })

    return weekly_orders


def void_weekly_empty_slots_past(weekly_orders):
    """
    Returns weekly updated grid list with empty hour slots in the past set to None

    """
    local = timezone.localtime(timezone.now())

    # Based start hour on our collect/delivery start hour
    local_hour = local.hour - settings.COLLECT_DELIVER_HOUR_START

    for hour, hv in enumerate(weekly_orders):
        for day, dv in enumerate(hv):
            if day < local.weekday() and dv == list():
                weekly_orders[hour][day] = None
            elif day == local.weekday() and hour < local_hour and dv == list():
                weekly_orders[hour][day] = None

    return weekly_orders


