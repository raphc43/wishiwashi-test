from bookings.models import Order


def vendor_pick_ups(vendor, start_dt, end_dt):
    return Order.objects.filter(
        assigned_to_vendor=vendor,
        pick_up_time__range=(start_dt, end_dt),
        placed=True,
        order_status=Order.CLAIMED_BY_VENDOR
    ).order_by('pick_up_time')


