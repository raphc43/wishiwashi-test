import datetime
import string

from dateutil.parser import parse
from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.functional import wraps
from ukpostcodeparser import parse_uk_postcode
import pytz

from bookings.calendar import pick_up_not_before, drop_off_not_before
from bookings.models import Address, Order
from bookings.appointments import appointment_slot_available_session


def string_to_local_datetime(dt):
    """
    Expects local datetime string: YYYY-MM-DD HH
    Returns local datetime
    """
    tz_local = pytz.timezone(settings.TIME_ZONE)
    year, month, day_hour = dt.split("-")
    day, hour = day_hour.split()
    return tz_local.localize(datetime.datetime(
        int(year), int(month), int(day), int(hour)))


def pick_up_time_session_invalid(pick_up_time):
    try:
        pick_up_time = string_to_local_datetime(pick_up_time)
    except (ValueError, AttributeError):
        return True

    return pick_up_time < pick_up_not_before()


def drop_off_time_session_invalid(pick_up_time, drop_off_time):
    try:
        pick_up_time = string_to_local_datetime(pick_up_time)
        drop_off_time = string_to_local_datetime(drop_off_time)
    except (ValueError, AttributeError):
        return True

    return drop_off_time < drop_off_not_before(pick_up_time)


def check_session_data(check_postcode=False, check_pick_up_time=False,
                       check_delivery_time=False, check_items=False,
                       check_address=False, check_order=False):
    def decorator(func):
        def _test_date_and_hour(time):
            assert time
            time = time.strip().lower()
            assert time and len(time) == len('YYYY-MM-DD HH')
            assert not len(set(string.ascii_lowercase).intersection(time)) and \
                   not len(set(string.ascii_uppercase).intersection(time))
            tz_london = pytz.timezone(settings.TIME_ZONE)
            tz_london.localize(parse(time))

        def inner_decorator(request, *args, **kwargs):
            if check_postcode:
                try:
                    assert 'postcode' in request.session and \
                           parse_uk_postcode(request.session['postcode'],
                                             incode_mandatory=False) \
                                is not None
                    assert 'out_code' in request.session and \
                           parse_uk_postcode(request.session['out_code'],
                                             incode_mandatory=False) \
                                is not None
                except (AssertionError, ValueError):
                    return HttpResponseRedirect(reverse('landing'))

            if check_pick_up_time:
                try:
                    assert 'pick_up_time' in request.session
                    _time = request.session['pick_up_time']
                    _test_date_and_hour(_time)

                    expired, slot_available = (
                        pick_up_time_session_invalid(_time),
                        appointment_slot_available_session(_time)
                    )

                    if expired or (slot_available is False):
                        del request.session['pick_up_time']

                        if 'order' in request.session:
                            order_pk = request.session['order']
                            order = Order.objects.get(pk=int(order_pk))
                            order.pick_up_time = None
                            order.drop_off_time = None
                            order.save()

                        if 'delivery_time' in request.session:
                            del request.session['delivery_time']

                        if expired:
                            messages.error(request,
                                           "Pick up time session expired. "
                                           "Please select another pick up time.")
                        else:
                            messages.error(request,
                                           "Pick up time is now unavailable. "
                                           "Please select another pick up time.")

                        raise ValueError
                except (AssertionError, ValueError):
                    return HttpResponseRedirect(
                        reverse('bookings:pick_up_time'))

            if check_delivery_time:
                try:
                    assert 'delivery_time' in request.session
                    _time = request.session['delivery_time']
                    _test_date_and_hour(_time)
                    if (drop_off_time_session_invalid(
                            request.session['pick_up_time'], _time)
                            or appointment_slot_available_session(_time)
                            is False):
                        del request.session['delivery_time']
                        if 'order' in request.session:
                            order_pk = request.session['order']
                            order = Order.objects.get(pk=int(order_pk))
                            order.drop_off_time = None
                            order.save()

                        messages.error(request,
                                       "Delivery time is now unavailable. "
                                       "Please select another delivery time.")
                        raise ValueError("Delivery time is unavailable")
                except (AssertionError, ValueError):
                    return HttpResponseRedirect(
                        reverse('bookings:delivery_time'))

            if check_items:
                try:
                    assert 'items' in request.session
                    assert type(request.session['items']) is dict
                    assert len(request.session['items'].keys()) > 0
                    assert set([str]) == \
                           set([type(key)
                                for key in request.session['items'].keys()])
                    assert set([int]) == \
                           set([type(key)
                                for key in request.session['items'].values()])
                except AssertionError:
                    return HttpResponseRedirect(
                        reverse('bookings:items_to_clean'))

            if check_address:
                try:
                    assert 'address' in request.session
                    assert Address.objects.\
                        filter(pk=request.session['address']).count() > 0
                except AssertionError:
                    return HttpResponseRedirect(reverse('bookings:address'))

            if check_order:
                try:
                    assert 'order' in request.session
                    order_pk = int(request.session['order'])
                    Order.objects.filter(pk=order_pk)[0]
                except (AssertionError, TypeError, ValueError, IndexError):
                    return HttpResponseRedirect(reverse('bookings:address'))

            return func(request, *args, **kwargs)
        return wraps(func)(inner_decorator)

    return decorator
