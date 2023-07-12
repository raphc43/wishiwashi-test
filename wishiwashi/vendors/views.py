# -*- coding: utf-8 -*-
import csv
import datetime
from datetime import timedelta
from decimal import Decimal
import logging
import re

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.http import (Http404, HttpResponse,
                         HttpResponseForbidden,
                         HttpResponseNotFound,
                         HttpResponseRedirect,
                         JsonResponse)
from django.shortcuts import render_to_response
from django.template import defaultfilters as filters, RequestContext
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import pytz

from bookings.models import Item, OperatingTimeRange, Order, OutCodes, ExpectedBackCleanOnlyOrder
from bookings.templatetags.phone_numbers import format_phone_number
from bookings.templatetags.postcodes import format_postcode
from customer_service.models import UserProfile
from .decorators import vendor_required, wishi_washi_vendor_view
from .forms import (OperatingHoursForm,
                    OutCodeCatchmentForm,
                    ContactAndNotificationsForm,
                    ReportIssueForm,
                    OrderPaymentsSearchForm,
                    ExpectedBackConfirmForm,
                    UpcomingDateForm,
                    TagsForm)
from .models import (IssueType,
                     OrderIssue,
                     DefaultCleanOnlyPrices,
                     DefaultCleanAndCollectPrices)
from .tasks import notify_vendors_of_orders_via_email
from .orders import prepare_for_pdf, add_order_to_files, html_upcoming_orders
from .pick_ups import vendor_pick_ups
from .templatetags.add_one_hour import add_one_hour
from .pdf import render_files_request
from .upcoming import (orders_upcoming, monday_start_sunday_end_datetime_range,
                       weekly_hourly_booked_slots, void_weekly_empty_slots_past)


logger = logging.getLogger(__name__)

# Currently limited to W & SW out codes
POSTCODES_SERVED_REGEX = r'^(w|sw)[0-9]+'

# Throw backs only allowed on orders with less than x hours before pick up
HOURS_FOR_THROWBACK = 3


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def orders(request):
    # If someone sends a low order number do not allow them to collect more
    # than 50 records and orders more than 2 days old no longer show up
    now = timezone.now()

    context = {
        'title': 'Available orders',
        'is_wishi_washi': bool(request.user.vendor.pk == settings.VENDOR_WISHI_WASHI_PK)
    }

    context['orders'] = Order.objects.filter(
        created__gt=now - datetime.timedelta(days=2),
        authorisation_status=Order.SUCCESSFULLY_AUTHORISED
    ).order_by('-pk')[:50]

    request.user.vendor.last_viewed_the_orders_page = timezone.now()
    request.user.vendor.save()

    return render_to_response('vendors/orders.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
def order(request, order_pk):
    try:
        order = Order.objects.get(pk=order_pk)
    except ObjectDoesNotExist:
        raise Http404()

    if order.assigned_to_vendor != request.user.vendor:
        return HttpResponseForbidden("You cannot view this order")

    if request.method == 'POST':
        form = ReportIssueForm(request.POST)
        form.vendor = request.user.vendor
        form.order = order

        if form.is_valid():
            issue = OrderIssue(order=order, issue_raised_by=request.user)

            # Contact details issue
            issue_pk = form.cleaned_data.get('vendor_issue_contact_issue_pk') or 0

            if int(issue_pk):
                if issue_pk == -1:
                    issue.is_other_issue = True
                    issue.other_issue_details = form.cleaned_data.get('other_contact_issue_details')
                    issue.issue = IssueType.objects.get(description='Other', category=IssueType.CONTACT_DETAILS)
                else:
                    issue.issue = IssueType.objects.get(pk=issue_pk)

                if order.order_status != Order.RECEIVED_BY_VENDOR:
                    # TODO this status will be stale if not updated by customer service
                    order.order_status = Order.UNABLE_TO_DELIVER_BACK_TO_CUSTOMER
                else:
                    # Assume the worst and hold off charging the customer
                    order.order_status = Order.UNABLE_TO_PICK_UP_ITEMS

                order.save()

            # Pick-up / Delivery issue
            issue_pk = form.cleaned_data.get('vendor_pick_up_and_delivery_issue_pk') or 0

            if int(issue_pk):
                if issue_pk == -1:
                    issue.is_other_issue = True
                    issue.other_issue_details = form.cleaned_data.get('other_pick_up_and_delivery_issue_details')
                    issue.issue = IssueType.objects.get(description='Other',
                                                        category=IssueType.PICK_UP_DROP_OFF_DETAILS)
                else:
                    issue.issue = IssueType.objects.get(pk=issue_pk)

                if order.order_status != Order.RECEIVED_BY_VENDOR:
                    # TODO this status will be stale if not updated by customer service
                    order.order_status = Order.UNABLE_TO_DELIVER_BACK_TO_CUSTOMER
                else:
                    # Assume the worst and hold off charging the customer
                    order.order_status = Order.UNABLE_TO_PICK_UP_ITEMS

            # Items Issues
            issue_pk = form.cleaned_data.get('vendor_items_issue_pk') or 0

            if int(issue_pk):
                if issue_pk == -1:
                    issue.is_other_issue = True
                    issue.other_issue_details = form.cleaned_data.get('other_items_issue_details')
                    issue.issue = IssueType.objects.get(description='Other', category=IssueType.ITEMS)
                else:
                    issue.issue = IssueType.objects.get(pk=issue_pk)

                item_pk = int(form.cleaned_data.get('item_pk'))
                issue.item = Item.objects.get(pk=item_pk)

                # Assume the worst and hold off charging the customer
                order.order_status = Order.CONTESTED_ITEMS_IN_ORDER
                order.save()

            issue.save()
            url = reverse('vendors:issue_raised', kwargs={'order_pk': order_pk})
            return HttpResponseRedirect(url)
    else:
        form = ReportIssueForm()

    try:
        profile = UserProfile.objects.filter(user=order.customer)[0]
    except IndexError:
        profile = {}

    context = {
        'form': form,
        'order': order,
        'profile': profile,
        'contact_issues':
            IssueType.objects.filter(
                category=IssueType.CONTACT_DETAILS).exclude(description='Other').order_by('description'),
        'pick_up_drop_off_issues':
            IssueType.objects.filter(
                category=IssueType.PICK_UP_DROP_OFF_DETAILS).exclude(description='Other').order_by('description'),
        'item_issues':
            IssueType.objects.filter(category=IssueType.ITEMS).exclude(description='Other').order_by('description'),
        'issues': OrderIssue.objects.filter(order=order).exclude(status=OrderIssue.RESOVLED).order_by('pk'),
        'title': 'Order details',
    }

    return render_to_response('vendors/order.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def issue_raised(request, order_pk):
    try:
        order = Order.objects.filter(pk=order_pk)[0]
    except IndexError:
        raise Http404()

    if order.assigned_to_vendor != request.user.vendor:
        return HttpResponseForbidden("You cannot raise an issue for this order")

    context = {
        'order': order,
        'title': 'Issue raised',
    }

    return render_to_response('vendors/issue_raised.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def confirm_accept_order(request, order_pk):
    now = timezone.now()

    try:
        order = Order.objects.get(pk=order_pk,
                                  placed_time__gt=now - datetime.timedelta(days=7),
                                  placed=True)
    except ObjectDoesNotExist:
        return HttpResponseNotFound('<h1>Unable to locate the order</h1>')

    # If they have already been assigned this order then redirect to the order page.
    if order.assigned_to_vendor == request.user.vendor:
        return HttpResponseRedirect(reverse('vendors:order', kwargs={'order_pk': order.pk}))

    # If no one has yet snapped up this order then show the confirmation page.
    if not order.assigned_to_vendor:
        context = {
            'order': order,
            'title': 'Confirm accepting order',
        }

        return render_to_response('vendors/confirm_accept_order.html', context,
                                  context_instance=RequestContext(request))

    # If the order has been snapped up then explain what has happened to the vendor.
    context = {
        'order': order,
        'title': 'This order has already been taken',
    }

    return render_to_response('vendors/snapped_up.html', context, context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
def accepted_order(request, order_pk):
    try:
        order = Order.objects.filter(pk=order_pk, authorisation_status=Order.SUCCESSFULLY_AUTHORISED)[0]
    except IndexError:
        raise Http404()

    if order.assigned_to_vendor is None:
        order.assigned_to_vendor = request.user.vendor
        order.order_status = Order.CLAIMED_BY_VENDOR
        order.order_claimed_time = timezone.now()
        order.save()

    if order.assigned_to_vendor != request.user.vendor:
        return HttpResponseForbidden("You cannot accept this order")

    return HttpResponseRedirect(reverse('vendors:order', kwargs={'order_pk': order.pk}))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
def get_latest_orders(request):
    try:
        latest_order_id = int(request.POST.get('latest_order_id'))
    except (ValueError, TypeError):
        # Unable to parse latest_order_id
        latest_order_id = 0 # Just start at the beginning

    # If someone sends a low order number do not allow them to collect more
    # than 50 records and orders more than 2 days old no longer show up
    now = timezone.now()

    orders = Order.objects.filter(
        pk__gt=latest_order_id,
        placed_time__gt=now - datetime.timedelta(days=2),
        authorisation_status=Order.SUCCESSFULLY_AUTHORISED
    ).order_by('-pk')[:50]

    london = pytz.timezone(settings.TIME_ZONE)

    resp = JsonResponse({
        'orders': [{
            'pk': order.pk,
            'created': naturaltime(order.created),
            'postcode': format_postcode(
                order.pick_up_and_delivery_address.postcode),
            'pick_up_time': '%s - %s' % (
                filters.date(order.pick_up_time.astimezone(london), 'D, M jS gA'),
                filters.time(add_one_hour(order.pick_up_time).astimezone(london), 'gA')
            ),
            'drop_off_time': '%s - %s' % (
                filters.date(order.drop_off_time.astimezone(london), 'D, M jS gA'),
                filters.time(add_one_hour(order.drop_off_time).astimezone(london), 'gA')
            ),
            'total_price_of_order': '{:,.2f}'.format(order.total_price_of_order),
            'is_taken_by_other_vendor': bool(order.assigned_to_vendor and
                                             order.assigned_to_vendor != request.user.vendor),
            'is_taken_by_requester': bool(order.assigned_to_vendor and
                                          order.assigned_to_vendor == request.user.vendor),
            'order_url': reverse('vendors:order', kwargs={'order_pk': order.pk}),
            'confirm_accept_order_url': reverse('vendors:confirm_accept_order',
                                                kwargs={'order_pk': order.pk})
        } for order in orders],
    })

    request.user.vendor.last_viewed_the_orders_page = timezone.now()
    request.user.vendor.save()

    return resp


def get_todays_time_range():
    now = timezone.localtime(timezone.now())
    start = datetime.datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
    end = datetime.datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=now.tzinfo)
    return start, end


def can_throw_back(vendor, orders):
    now_utc = timezone.now()
    three_hours_from_now = now_utc + timedelta(hours=HOURS_FOR_THROWBACK)

    is_wishi_washi = bool(vendor.pk == settings.VENDOR_WISHI_WASHI_PK)

    if is_wishi_washi:
        for order in orders:
            if order.pick_up_time > three_hours_from_now:
                order.can_throw_back = True

    return is_wishi_washi, orders


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def orders_to_pick_up(request):
    today_start, today_end = get_todays_time_range()
    orders = vendor_pick_ups(vendor=request.user.vendor, start_dt=today_start, end_dt=today_end)
    is_wishi_washi, orders = can_throw_back(request.user.vendor, orders)

    context = {
        'orders': orders,
        'title': 'Orders to pick up',
        'is_wishi_washi': is_wishi_washi,
    }

    return render_to_response('vendors/orders_to_pick_up.html', context, context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
def orders_to_pick_up_pdf(request):
    today_start, today_end = get_todays_time_range()

    files = []
    orders = vendor_pick_ups(vendor=request.user.vendor, start_dt=today_start, end_dt=today_end)
    for order in orders:
        add_order_to_files(prepare_for_pdf(order), files)

    if not files:
        raise Http404()

    return render_files_request(files, filename="Orders-to-pick-up-{}".format(today_start.date()))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def orders_to_drop_off(request):
    today_start, today_end = get_todays_time_range()

    orders = Order.objects.filter(assigned_to_vendor=request.user.vendor,
                                  drop_off_time__gte=today_start,
                                  drop_off_time__lt=today_end,
                                  placed=True,
                                  order_status=Order.RECEIVED_BY_VENDOR,
                                  ).order_by('drop_off_time')

    context = {
        'orders': orders,
        'title': 'Orders to drop off',
    }

    return render_to_response('vendors/orders_to_drop_off.html', context, context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
def orders_to_drop_off_pdf(request):
    today_start, today_end = get_todays_time_range()

    files = []
    for order in Order.objects.filter(assigned_to_vendor=request.user.vendor,
                                      drop_off_time__gte=today_start,
                                      drop_off_time__lt=today_end,
                                      placed=True,
                                      order_status=Order.RECEIVED_BY_VENDOR
                                      ).order_by('drop_off_time'):
        add_order_to_files(prepare_for_pdf(order), files)

    if not files:
        raise Http404()

    return render_files_request(files, filename="Orders-to-drop-off-{}".format(today_start.date()))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def order_history(request):
    orders = Order.objects.filter(assigned_to_vendor=request.user.vendor,
                                  authorisation_status=Order.SUCCESSFULLY_AUTHORISED
                                  ).order_by('-pick_up_time')

    is_wishi_washi, orders = can_throw_back(request.user.vendor, orders)

    context = {
        'orders': orders,
        'title': 'Order history',
        'is_wishi_washi': is_wishi_washi,
    }

    return render_to_response('vendors/order_history.html', context, context_instance=RequestContext(request))


def numbers_within_strings_sort(out_code):
    expression = re.compile('(\d+)')
    pieces = expression.split(out_code.out_code)
    return [int(piece) if piece.isdigit() else piece for piece in pieces]


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
def postcodes_served(request):
    successfully_modified = False

    if request.method == 'POST':
        form = OutCodeCatchmentForm(request.POST)

        if form.is_valid():
            for _out_code, served in request.POST.iteritems():
                _out_code = _out_code.lower().strip()

                try:
                    out_code = OutCodes.objects.filter(out_code=_out_code)[0]
                except IndexError:
                    continue

                if int(served) == 1:
                    request.user.vendor.catchment_area.add(out_code)
                else:
                    request.user.vendor.catchment_area.remove(out_code)

            successfully_modified = True
    else:
        form = OutCodeCatchmentForm()

    # Find all out codes the vendor is not serving
    out_codes = OutCodes.objects.filter()
    out_codes = sorted(out_codes, key=numbers_within_strings_sort)

    served = [__out_code.pk for __out_code in request.user.vendor.catchment_area.all()]

    for _out_code in out_codes:
        if _out_code.pk in served:
            _out_code.served = True

    context = {
        'out_codes': out_codes,
        'successfully_modified': successfully_modified,
        'form': form,
        'title': 'Postcodes served',
    }
    return render_to_response('vendors/postcodes_served.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
def operating_hours(request):
    successfully_modified = False

    if request.method == 'POST':
        form = OperatingHoursForm(request.POST)

        if form.is_valid():
            for day_of_week in OperatingTimeRange.DAYS_OF_WEEK:
                hours = request.user.vendor.hours_of_operation.filter(day_of_week=day_of_week[0])[0]
                hours.start_hour = int(form.cleaned_data['opening_%d' % day_of_week[0]])
                hours.end_hour = int(form.cleaned_data['closing_%d' % day_of_week[0]])
                hours.save()
            successfully_modified = True
    else:
        form = OperatingHoursForm()

    ranges = request.user.vendor.hours_of_operation.all().order_by('day_of_week', 'start_hour')

    # Populate ranges with errors and add selected values for form persistence
    for index, _range in enumerate(ranges):
        key = 'closing_%d' % _range.day_of_week

        if key in form.errors:
            ranges[index].error = form.errors[key][0]

        key = 'opening_%d' % _range.day_of_week

        try:
            if key in form.data and int(form.data[key]) >= 0 and int(form.data[key]) <= 24:
                ranges[index].start_hour = int(form.data[key])
        except (ValueError, TypeError):
            pass

        key = 'closing_%d' % _range.day_of_week

        try:
            if key in form.data and int(form.data[key]) >= 0 and int(form.data[key]) <= 24:
                ranges[index].end_hour = int(form.data[key])
        except (ValueError, TypeError):
            pass

    context = {
        'successfully_modified': successfully_modified,
        'hours': range(0, 25),
        'ranges': ranges,
        'form': form,
        'title': 'Operating hours',
    }

    return render_to_response('vendors/operating_hours.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
def contact_details_and_notifications(request):
    successfully_modified = False

    if request.method == 'POST':
        form = ContactAndNotificationsForm(request.POST)
        form.user = request.user

        if form.is_valid():
            profile = UserProfile.objects.get(user=request.user)
            profile.mobile_number = form.cleaned_data["mobile_number"]
            profile.email_notifications_enabled = bool(form.cleaned_data["notify_via_email"])
            profile.sms_notifications_enabled = bool(form.cleaned_data["notify_via_sms"])
            profile.save()

            request.user.email = form.cleaned_data["email_address"]
            request.user.save()
            successfully_modified = True
    else:
        profile = UserProfile.objects.get(user=request.user)

        initial = {
            'email_address': request.user.email,
            'mobile_number': format_phone_number(profile.mobile_number),
            'notify_via_email': profile.email_notifications_enabled,
            'notify_via_sms': profile.sms_notifications_enabled,
        }
        form = ContactAndNotificationsForm(initial=initial)

    context = {
        'form': form,
        'successfully_modified': successfully_modified,
        'title': 'Contact details & notifications',
    }

    return render_to_response('vendors/contact_details_and_notifications.html',
                              context,
                              context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def throw_orders_back_in_pool(request):
    """
    Wishi Washi view to throw orders back into the pool so other vendors can accept those orders
    """
    order_pks = [int(key.split('_')[1])
                 for key in request.POST.keys()
                 if 'order_' in key and
                    request.POST[key] == 'on' and
                    len(key.split('_')) == 2 and
                    key.split('_')[1].isdigit()]

    now_utc = timezone.now()
    three_hours_from_now = now_utc + timedelta(hours=HOURS_FOR_THROWBACK)

    orders = Order.objects.filter(pk__in=order_pks,
                                  assigned_to_vendor=request.user.vendor,
                                  order_status=Order.CLAIMED_BY_VENDOR,
                                  pick_up_time__gte=three_hours_from_now)

    thrown_back, rejected = len(orders), len(order_pks) - len(orders)

    for order in orders:
        order.assigned_to_vendor = None
        order.order_status = Order.UNCLAMIED_BY_VENDORS
        order.order_claimed_time = None
        order.thrown_back_time = timezone.now()
        order.save()

        notify_vendors_of_orders_via_email.delay(order.pk)

    context = {
        'title': 'Throw orders back into the pool',
        'thrown_back': thrown_back,
        'rejected': rejected,
    }

    return render_to_response('vendors/throw_orders_back_in_pool.html',
                              context,
                              context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def orders_to_tag(request):
    """
    Wishi Washi view to print out tags for orders
    """
    orders = Order.objects.none()
    form = TagsForm()

    if request.method == 'POST':
        form = TagsForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['uuid'].startswith("WW-"):
                # Ticket ID
                orders = Order.objects.filter(ticket_id=form.cleaned_data['uuid'],
                                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED).order_by('pick_up_time')
            else:
                # Order ID
                orders = Order.objects.filter(uuid=form.cleaned_data['uuid'],
                                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED).order_by('pick_up_time')

            # Numeric only - match on ticket ID
            if not orders and form.cleaned_data['uuid'].isdigit():
                ticket_id = "WW-{:0>5d}".format(int(form.cleaned_data['uuid']))
                orders = Order.objects.filter(ticket_id=ticket_id,
                                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED).order_by('pick_up_time')

    else:
        # Defaults to today
        today_start, today_end = get_todays_time_range()
        orders = Order.objects.filter(assigned_to_vendor=request.user.vendor,
                                      pick_up_time__gte=today_start,
                                      pick_up_time__lt=today_end,
                                      authorisation_status=Order.SUCCESSFULLY_AUTHORISED).order_by('pick_up_time')

    for order in orders:
        order.pieces = sum(item.quantity * item.item.pieces for item in order.items.all())

    context = {
        'form': form,
        'orders': orders,
        'title': 'Orders to tag',
        'printers': settings.TAGGING_PRINTERS,
    }

    return render_to_response('vendors/orders_to_tag.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def order_payments(request):
    """
    Wishi washi view for payments due to vendors for either Clean and collect/Clean only
    """
    local_tz = pytz.timezone(settings.TIME_ZONE)
    orders = []
    total = Decimal('0.00')
    order_total = Decimal('0.00')
    order_total_ex_vat = Decimal('0.00')
    if request.method == 'POST':
        form = OrderPaymentsSearchForm(request.POST)
        if form.is_valid():
            s = form.cleaned_data['start_date']
            e = form.cleaned_data['end_date']
            start_dt = local_tz.localize(
                datetime.datetime(s.year, s.month, s.day)
            )
            end_dt = local_tz.localize(
                datetime.datetime(e.year, e.month, e.day, 23, 59, 59)
            )

            orders = Order.objects.filter(
                placed_time__range=(start_dt, end_dt),
                placed=True,
                order_status__in=[Order.DELIVERED_BACK_TO_CUSTOMER,
                                  Order.RECEIVED_BY_VENDOR]
            ).order_by('-placed_time')

            if form.cleaned_data['assigned_to_vendor']:
                orders = orders.filter(assigned_to_vendor=form.cleaned_data['assigned_to_vendor'])

            if form.cleaned_data['clean_only_vendor']:
                orders = orders.filter(cleanonlyorder__assigned_to_vendor=form.cleaned_data['clean_only_vendor'])

            for order in orders:
                order.pieces = sum(item.quantity * item.item.pieces for item in order.items.all())
                total += order.orderpayments.total_amount if hasattr(order, 'orderpayments') else Decimal(0)
                order_total += order.total_price_of_order
                order_total_ex_vat += order.price_excluding_vat_charge
    else:
        form = OrderPaymentsSearchForm()

    context = {
        'form': form,
        'orders': orders,
        'total': total,
        'order_total': order_total,
        'order_total_ex_vat': order_total_ex_vat,
        'title': 'Order vendor payments'
    }

    return render_to_response('vendors/order_payments.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def upcoming(request):
    now = timezone.localtime(timezone.now())

    orders = []
    for day in range(3):
        start_dt = datetime.datetime(now.year, now.month, now.day, tzinfo=now.tzinfo) + timedelta(days=day)
        end_dt = datetime.datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=now.tzinfo) + timedelta(days=day)
        orders.append({'dt': start_dt.date(), 'orders': orders_upcoming(request.user.vendor, start_dt, end_dt)})

    context = {
        'orders': orders
    }

    return render_to_response('vendors/upcoming.html', context, context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
def upcoming_pdf(request):
    """
    date expected in YYYY-MM-DD Format
    """
    london = pytz.timezone(settings.TIME_ZONE)

    form = UpcomingDateForm(request.POST)
    if not form.is_valid():
        return HttpResponse("Form invalid: {}".format(form.error))

    date = form.cleaned_data['date']
    orders = []
    start_dt = london.localize(datetime.datetime(date.year, date.month, date.day))
    end_dt = london.localize(datetime.datetime(date.year, date.month, date.day, 23, 59, 59))
    orders = orders_upcoming(request.user.vendor, start_dt, end_dt)

    if not orders:
        raise Http404()

    html = html_upcoming_orders(orders, date)
    files = [('{}'.format(date), ('Upcoming {}'.format(date), html, 'text/html; charset=utf-8'))]

    return render_files_request(files, filename="Upcoming-{}".format(date))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def expected_back_clean_only(request):
    """
    Wishi washi view for clean only due back within the previous/following days from vendors
    """
    now = timezone.localtime(timezone.now())

    # Outstanding orders expected back past yesterday, still unconfirmed
    yesterday = now - timedelta(days=1)
    yesterday_dt = datetime.datetime(yesterday.year, yesterday.month, yesterday.day, tzinfo=now.tzinfo)
    past_unconfirmed = ExpectedBackCleanOnlyOrder.objects.filter(expected_back__lt=yesterday_dt, confirmed_back=False)

    cleanonly = []
    for day in range(-1, 2):
        start_dt = datetime.datetime(now.year, now.month, now.day, tzinfo=now.tzinfo) + timedelta(days=day)
        end_dt = datetime.datetime(now.year, now.month, now.day, 23, 59, 59, tzinfo=now.tzinfo) + timedelta(days=day)
        cleanonly.append(
            {'dt': start_dt.date(),
             'results':  ExpectedBackCleanOnlyOrder.objects.filter(
                 expected_back__range=(start_dt, end_dt)).order_by('expected_back')
             }
        )

    # Attach total pieces to results
    for obj in cleanonly:
        for expected_back in obj['results']:
            expected_back.pieces = sum(item.quantity * item.item.pieces
                                       for item in expected_back.clean_only_order.order.items.all())

    context = {
        'cleanonly': cleanonly,
        'past_unconfirmed': past_unconfirmed
    }

    return render_to_response('vendors/expected_back_clean_only.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def expected_back_clean_only_all(request):
    """
    Wishi washi view for all clean only due back from vendors (still awaiting confirmation)
    """
    expected_back = ExpectedBackCleanOnlyOrder.objects.filter(confirmed_back=False).order_by('expected_back')

    # Attach total pieces to results
    for obj in expected_back:
        obj.pieces = sum(item.quantity * item.item.pieces
                         for item in obj.clean_only_order.order.items.all())

    context = {
        'expected_back': expected_back
    }

    return render_to_response('vendors/expected_back_clean_only_all.html',
                              context, context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def expected_back_clean_only_confirm(request):
    """
    Wishi washi view for confirming clean only delivered back from vendor
    """
    form = ExpectedBackConfirmForm(request.POST)

    if not form.is_valid():
        return JsonResponse({'error': "Form invalid"}, status=400)

    pk = form.cleaned_data['id']

    try:
        obj = ExpectedBackCleanOnlyOrder.objects.get(pk=pk)
        obj.confirmed_back = True
        obj.save()
    except ExpectedBackCleanOnlyOrder.DoesNotExist:
        return JsonResponse({'error': '{} does not exist'.format(pk)}, status=400)

    return JsonResponse({'pk': 'Confirmed'}, status=200)


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def default_prices(request):
    """
    Wishi washi view for vendors default prices
    """
    results = []
    for item in Item.objects.all().order_by('name', 'category__name'):
        clean_only = DefaultCleanOnlyPrices.objects.get(item=item)
        clean_and_collect = DefaultCleanAndCollectPrices.objects.get(item=item)

        price_ex_vat = (item.price / Decimal('1.2')).quantize(Decimal('0.00'))
        results.append(
            {
                'name': item.name,
                'category': item.category.name,
                'price': item.price,
                'price_ex_vat': price_ex_vat,
                'clean_only': clean_only.price,
                'per_clean_only': (Decimal(100) * (clean_only.price / price_ex_vat)).quantize(Decimal('0.0')),
                'clean_and_collect': clean_and_collect.price,
                'per_clean_and_collect': (Decimal(100) * (clean_and_collect.price / price_ex_vat)).quantize(
                    Decimal('0.0'))
            }

        )

    if request.method == 'POST':
        # CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="default_prices.csv"'

        writer = csv.writer(response)
        writer.writerow(['Name', 'Category', 'Price', 'Price ex VAT',
                         'Clean only ex VAT', '% Clean only',
                         'Clean and Collect ex VAT', '% Clean and collect'])

        for result in results:
            writer.writerow([result['name'],
                             result['category'],
                             result['price'],
                             result['price_ex_vat'],
                             result['clean_only'],
                             result['per_clean_only'],
                             result['clean_and_collect'],
                             result['per_clean_and_collect']])

        return response
    else:
        context = {'results': results}
        return render_to_response('vendors/default_prices.html', context, context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@vendor_required()
def pdf_order(request, order_pk):
    try:
        order = prepare_for_pdf(Order.objects.get(pk=order_pk, assigned_to_vendor=request.user.vendor, placed=True))
    except ObjectDoesNotExist:
        raise Http404()

    files = []
    add_order_to_files(order, files)

    return render_files_request(files, filename="Order#{}".format(order.uuid))


@require_http_methods(["GET"])
@login_required()
@vendor_required()
def weekly_upcoming(request):
    start_dt, end_dt = monday_start_sunday_end_datetime_range()

    if request.GET.get('json'):
        orders = orders_upcoming(request.user.vendor, start_dt, end_dt)
        weekly_orders = weekly_hourly_booked_slots(orders, start_dt, end_dt)
        weekly_orders = void_weekly_empty_slots_past(weekly_orders)
        return JsonResponse(weekly_orders, safe=False)
    else:
        return render_to_response('vendors/weekly_upcoming.html',
                                  {'DEBUG': settings.DEBUG},
                                  context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def update_order(request, order_pk):
    try:
        Order.objects.get(pk=order_pk, placed=True)
    except ObjectDoesNotExist:
        raise Http404()

    context = {}
    return render_to_response('vendors/update_order.html', context, context_instance=RequestContext(request))
