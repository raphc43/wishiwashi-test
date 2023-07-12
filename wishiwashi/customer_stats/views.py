import csv
from calendar import monthrange
from datetime import datetime, timedelta

import pytz

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.db.models import Count, Sum
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.utils.timezone import get_current_timezone
from django.utils import timezone

from bookings.models import Order
from vendors.decorators import vendor_required, wishi_washi_vendor_view

localtimezone = pytz.timezone(settings.TIME_ZONE)

def monthly_range(month, year):
    start = datetime(int(year), int(month), 1, 0, 0, tzinfo=pytz.utc).astimezone(localtimezone)

    if month < 12:
        end = (datetime(int(year), int(month) + 1, 1, 0, 0, tzinfo=pytz.utc) -
               timedelta(seconds=1)).astimezone(localtimezone)
    else:
        year += 1
        end = (datetime(int(year), 1, 1, 0, 0, tzinfo=pytz.utc) - timedelta(seconds=1)).astimezone(localtimezone)

    return start, end

def daterange(start_date, end_date):
    start_date_utc = datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=pytz.utc)
    end_date_utc = datetime(end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=pytz.utc)
    yield start_date_utc.astimezone(localtimezone)

    for n in range(int((end_date_utc - start_date_utc).days) + 1):
        yield (start_date_utc + timedelta(days=n)).astimezone(localtimezone)

def datehourrange(start_date, end_date):
    for hour in range(0, 24):
        yield datetime(start_date.year, start_date.month, start_date.day,
                       hour, 0, 0, tzinfo=pytz.utc).astimezone(localtimezone)

    for n in range(int((end_date - start_date).days) + 1):
        for hour in range(0, 24):
            yield (datetime(start_date.year, start_date.month, start_date.day, hour, 0, 0, tzinfo=pytz.utc) +
                   timedelta(days=n)).astimezone(localtimezone)


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def stats(request):
    return render(request, 'customer_stats/stats.html')


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def placed_time_monthly(request):
    month, year = int(request.GET.get("month")), int(request.GET.get("year"))
    start, end = monthly_range(month, year)

    query = Order.objects.filter(placed=True,
                                 placed_time__gte=start,
                                 placed_time__lte=end
                                ).extra(
                                     {'placed_time_dt':"date(placed_time)"}
                                          ).values('placed_time_dt').annotate(
                                              count=Count('id')).order_by('placed_time_dt')

    orders = {}
    for result in query:
        orders[result['placed_time_dt']] = result['count']

    resp = "day\tfrequency\n"
    for day in daterange(start, end):
        if day.date() in orders:
            resp += "{}\t{}\n".format(day.strftime("%a %d"), orders[day.date()])
        else:
            resp += "{}\t{}\n".format(day.strftime("%a %d"), 0)

    return HttpResponse(resp, content_type="text/tab-separated-values")


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def placed_time_yearly(request):
    year = int(request.GET.get("year"))
    start = datetime(year, 1, 1, tzinfo=get_current_timezone())
    end = datetime(year, 12, 31, 23, 59, 59, tzinfo=get_current_timezone())

    query = Order.objects.filter(placed=True,
                                 placed_time__gte=start,
                                 placed_time__lte=end
                                ).extra(
                                     {'placed_time_dt':"date(placed_time)"}
                                          ).values('placed_time_dt').annotate(
                                              count=Count('id')).order_by('placed_time_dt')

    orders = {}
    for result in query:
        month_year = result['placed_time_dt'].strftime("%b %y")
        if month_year in orders:
            orders[month_year] += result['count']
        else:
            orders[month_year] = result['count']

    month_year = ''
    resp = "month\tfrequency\n"
    for day in daterange(start, end):
        if month_year != day.strftime("%b %y"):
            month_year = day.strftime("%b %y")
            if month_year in orders:
                resp += "{}\t{}\n".format(month_year, orders[month_year])
            else:
                resp += "{}\t{}\n".format(month_year, 0)

    return HttpResponse(resp, content_type="text/tab-separated-values")


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def amount_time_monthly(request):
    month, year = int(request.GET.get("month")), int(request.GET.get("year"))
    start, end = monthly_range(month, year)
    query = Order.objects.filter(placed=True,
                                 placed_time__gte=start,
                                 placed_time__lte=end
                                ).extra(
                                     {'placed_time_dt':"date(placed_time)"}
                                          ).values('placed_time_dt').annotate(
                                              total=Sum('total_price_of_order')).order_by('placed_time_dt')

    orders = {}
    for result in query:
        orders[result['placed_time_dt']] = result['total']

    filename = "Total Amount {:%b %Y}-{:%b %Y}.csv".format(start, end)
    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['day', 'total'])
    for day in daterange(start, end):
        writer.writerow([day.strftime("%a %d"), orders.get(day.date(), 0)])
    return response


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def amount_time_yearly(request):
    year = int(request.GET.get("year"))
    start = datetime(year, 1, 1, tzinfo=get_current_timezone())
    end = datetime(year, 12, 31, 23, 59, 59, tzinfo=get_current_timezone())

    query = Order.objects.filter(placed=True,
                                 placed_time__gte=start,
                                 placed_time__lte=end
                                ).extra(
                                     {'placed_time_dt':"date(placed_time)"}
                                          ).values('placed_time_dt').annotate(
                                              total=Sum('total_price_of_order')).order_by('placed_time_dt')

    orders = {}
    for result in query:
        month_year = result['placed_time_dt'].strftime("%b %y")
        if month_year in orders:
            orders[month_year] += result['total']
        else:
            orders[month_year] = result['total']

    filename = "Total Amount {:%b %Y}-{:%b %Y}.csv".format(start, end)
    response = HttpResponse(content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    writer = csv.writer(response)
    writer.writerow(['month', 'total'])

    month_year = ''
    for day in daterange(start, end):
        if month_year != day.strftime("%b %y"):
            month_year = day.strftime("%b %y")
            writer.writerow([month_year, orders.get(month_year, 0)])
    return response


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def new_customers_monthly(request):
    month, year = int(request.GET.get("month")), int(request.GET.get("year"))
    start, end = monthly_range(month, year)

    previous_customers = list(u.id for u in User.objects.filter(
        order__placed=True,
        order__placed_time__lt=start).distinct()
    )
    query = User.objects.prefetch_related('order_set').filter(order__placed=True,
                                                              order__placed_time__gte=start,
                                                              order__placed_time__lte=end).exclude(
                                                                  pk__in=previous_customers
                                                              ).order_by('-order__placed_time')

    users = []
    orders = {}
    for user in query:
        if user.id not in users:
            try:
                day = user.order_set.all()[0].placed_time.date()
            # not all initial orders have a placed date
            # using order creation date as a fall back
            except AttributeError:
                day = user.order_set.all()[0].created.date()
            if day not in orders:
                orders[day] = 1
            else:
                orders[day] += 1
            users.append(user.id)

    resp = "day\tfrequency\n"
    for day in daterange(start, end):
        if day.date() in orders:
            resp += "{}\t{}\n".format(day.strftime("%a %d"), orders[day.date()])
        else:
            resp += "{}\t{}\n".format(day.strftime("%a %d"), 0)

    return HttpResponse(resp, content_type="text/tab-separated-values")

@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def new_customers_yearly(request):
    year = int(request.GET.get("year"))
    start = datetime(year, 1, 1, tzinfo=get_current_timezone())
    end = datetime(year, 12, 31, 23, 59, 59, tzinfo=get_current_timezone())

    previous_customers = list(u.id for u in User.objects.filter(
        order__placed=True,
        order__placed_time__lt=start).distinct()
    )
    query = User.objects.prefetch_related('order_set').filter(order__placed=True,
                                                              order__placed_time__gte=start,
                                                              order__placed_time__lte=end).exclude(
                                                                  pk__in=previous_customers
                                                              ).order_by('-order__placed_time')
    users = []
    orders = {}
    for user in query:
        if user.id not in users:
            try:
                month_year = user.order_set.all()[0].placed_time.date().strftime("%b %y")
            # not all initial orders have a placed date
            # using order creation date as a fall back
            except AttributeError:
                month_year = user.order_set.all()[0].created.date().strftime("%b %y")
            if month_year not in orders:
                orders[month_year] = 1
            else:
                orders[month_year] += 1
            users.append(user.id)

    month_year = ''
    resp = "month\tfrequency\n"
    for day in daterange(start, end):
        if month_year != day.strftime("%b %y"):
            month_year = day.strftime("%b %y")
            if month_year in orders:
                resp += "{}\t{}\n".format(month_year, orders[month_year])
            else:
                resp += "{}\t{}\n".format(month_year, 0)

    return HttpResponse(resp, content_type="text/tab-separated-values")

@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def pickup_delivery_time_monthly(request):
    month, year = int(request.GET.get("month")), int(request.GET.get("year"))
    start, end = monthly_range(month, year)

    pickup_query = Order.objects.filter(placed=True,
                                 pick_up_time__gte=start,
                                 pick_up_time__lte=end
                                ).extra(
                                     {'pick_up_time_dt':"date(pick_up_time)"}
                                          ).values('pick_up_time_dt').annotate(
                                              count=Count('id')).order_by('pick_up_time_dt')

    delivery_query = Order.objects.filter(placed=True,
                                 drop_off_time__gte=start,
                                 drop_off_time__lte=end
                                ).extra(
                                     {'delivery_time_dt':"date(drop_off_time)"}
                                          ).values('delivery_time_dt').annotate(
                                              count=Count('id')).order_by('delivery_time_dt')
    pickups= {}
    for result in pickup_query:
        pickups[result['pick_up_time_dt']] = result['count']

    deliveries = {}
    for result in delivery_query:
        deliveries[result['delivery_time_dt']] = result['count']

    resp = "day\tCollections\tDeliveries\n"
    for day in daterange(start, end):
        if day.weekday() == 6: continue  #Skip sunday
        pickup = pickups[day.date()] if day.date() in pickups else 0
        delivery = deliveries[day.date()] if day.date() in deliveries else 0

        resp += "{}\t{}\t{}\n".format(day.strftime("%a %d"), pickup, delivery)

    return HttpResponse(resp, content_type="text/tab-separated-values")


@require_http_methods(["GET"])
@login_required()
@vendor_required()
@wishi_washi_vendor_view()
def pickup_delivery_heatmap_monthly(request):
    month, year = int(request.GET.get("month")), int(request.GET.get("year"))
    show_pickups, show_deliveries = bool(request.GET.get("pickups")), bool(request.GET.get("deliveries"))
    start, end = monthly_range(month, year)

    pickups = {}
    if show_pickups:
        pickup_query = Order.objects.filter(placed=True,
                                            pick_up_time__gte=start,
                                            pick_up_time__lte=end
                                           ).extra(
                                               {'pick_up_time_day_hour': "date_trunc('hour', pick_up_time)"}
                                              ).values('pick_up_time_day_hour').annotate(
                                                  count=Count('id')).order_by('pick_up_time_day_hour')

        for result in pickup_query:
            pickups[result['pick_up_time_day_hour'].astimezone(localtimezone)] = result['count']

    deliveries = {}
    if show_deliveries:
        delivery_query = Order.objects.filter(placed=True,
                                              drop_off_time__gte=start,
                                              drop_off_time__lte=end
                                           ).extra(
                                                {'delivery_time_day_hour': "date_trunc('hour', drop_off_time)"}
                                              ).values('delivery_time_day_hour').annotate(
                                                          count=Count('id')).order_by('delivery_time_day_hour')

        for result in delivery_query:
            deliveries[result['delivery_time_day_hour'].astimezone(localtimezone)] = result['count']

    # Initiate data structure dow->hour of day
    combined_daily = {day: dict.fromkeys(range(1, 25), 0) for day in range(1, 8)}

    # Populate data
    for day_hour in datehourrange(start, end):
        dow, hour = day_hour.weekday() + 1, day_hour.hour

        if hour == 0: hour = 24

        if day_hour in pickups:
            combined_daily[dow][hour] += pickups[day_hour]

        if day_hour in deliveries:
            combined_daily[dow][hour] += deliveries[day_hour]

    resp = "day\thour\tvalue\n"
    for dow in range(1, 8):
        for hour in range(1, 25):
            resp += "{}\t{}\t{}\n".format(dow, hour, combined_daily[dow][hour])

    return HttpResponse(resp, content_type="text/tab-separated-values")

