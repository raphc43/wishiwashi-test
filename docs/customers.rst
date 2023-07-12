Customers who have created account but not placed an order online
=================================================================

.. code-block:: bash

    $ python manage.py shell
    >>> from bookings.models import Order
    >>> ids = Order.objects.filter(placed=True).values_list('customer__id', flat=True)
    >>> for o in Order.objects.filter(placed=False).exclude(customer__id__in=ids):
    >>>     print o.customer.first_name, o.customer.last_name, o.customer.email

