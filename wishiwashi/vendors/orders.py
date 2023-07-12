from django.template.loader import render_to_string
from django.conf import settings

from bookings.clean_only import drop_off_time_to_ready_time

import pytz

RENDER_HTML2PDF_URL = "{}{}".format(settings.RENDER_SERVICE_URL, settings.RENDER_SERVICE_HTML2PDF_PATH)
RENDER_AUTH = auth = (settings.RENDER_SERVICE_USERNAME, settings.RENDER_SERVICE_PASSWORD)


def prepare_for_pdf(order):
    """
    For PDF rendering order append required object attributes
    """
    order.address = ",".join(str(order.pick_up_and_delivery_address).split(",")[:-1])
    order.total_pieces = sum(item.quantity * item.item.pieces for item in order.items.all())
    if hasattr(order, 'cleanonlyorder'):
        order.expected_back = drop_off_time_to_ready_time(order.drop_off_time)
    return order


def html_order(order):
    """
    Order returned as html string for PDF conversion
    """
    return render_to_string('vendors/pdf/order.html', {'order': order})


def html_upcoming_orders(orders, date):
    """
    Orders upcoming as html string for PDF conversion
    """
    local = pytz.timezone(settings.TIME_ZONE)

    slots = []
    for hour in range(8, 22):
        slots.append({
            'hour': hour,
            'drop_offs':  list(),
            'pick_ups': list()
        })

    for order in orders:
        if order.pick_up_time.date() == date:
            for slot in slots:
                if slot['hour'] == order.pick_up_time.astimezone(local).hour:
                    slot['pick_ups'].append(order)
        else:
            for slot in slots:
                if slot['hour'] == order.drop_off_time.astimezone(local).hour:
                    slot['drop_offs'].append(order)

    return render_to_string('vendors/pdf/upcoming.html', {'upcoming_date': date, 'slots': slots})


def add_order_to_files(order, files=None):
    """
    Add order get html and add to existing or new files
    """
    if files is None:
        files = []

    html = html_order(order)

    files.append(('{}'.format(order.uuid), ('order_{}'.format(order.uuid), html, 'text/html; charset=utf-8')))
    return files


def sort_orders_upcoming(orders):
    """
    Sort orders based on next (upcoming) date
    Look at either pick up date then drop off date
    """
    def sort_by_next_date(order):
        if order.pick_up_time.date() >= order.upcoming_date:
            return order.pick_up_time
        else:
            return order.drop_off_time

    return sorted(orders, key=sort_by_next_date)

