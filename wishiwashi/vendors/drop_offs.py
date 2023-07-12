from bookings.models import Order


def vendor_drop_offs(vendor, start_dt, end_dt):
    return Order.objects.filter(assigned_to_vendor=vendor,
                                drop_off_time__range=(start_dt, end_dt),
                                placed=True
                                ).exclude(order_status__in=[Order.UNCLAMIED_BY_VENDORS,
                                                            Order.DELIVERED_BACK_TO_CUSTOMER,
                                                            Order.ORDER_REJECTED_BY_SERVICE_PROVIDER]
                                          ).order_by('drop_off_time')


