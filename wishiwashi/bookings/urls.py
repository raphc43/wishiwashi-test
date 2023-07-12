from django.conf.urls import patterns, url

urlpatterns = patterns(
    '',
    url(r'^login$', 'bookings.views.login', name='login'),
    url(r'^logout$', 'bookings.views.logout', name='logout'),
    url(r'^valid\-postcode/(?P<postcode>[\w\ ]+)$', 'bookings.views.valid_postcode', name='valid_postcode'),
    url(r'^prices$', 'bookings.views.prices', name='prices'),
    url(r'^pick\-up\-time$', 'bookings.views.pick_up_time_page', name='pick_up_time'),
    url(r'^delivery\-time$', 'bookings.views.delivery_time', name='delivery_time'),
    url(r'^postcode\-not\-served$', 'bookings.views.postcode_not_served', name='postcode_not_served'),
    url(r'^notify\-when\-postcode\-served/(?P<postcode>[\w\ ]+)$', 'bookings.views.notify_when_postcode_served',
        name='notify_when_postcode_served'),
    url(r'^items\-to\-clean$', 'bookings.views.items_to_clean', name='items_to_clean'),
    url(r'^address$', 'bookings.views.address', name='address'),
    url(r'^order\-placed$', 'bookings.views.order_placed', name='order_placed'),
    url(r'^orders$', 'bookings.views.orders', name='orders'),
    url(r'^order/(?P<uuid>[\w]+)$', 'bookings.views.order', name='order'),
    url(r'^items$', 'bookings.views.items_added', name='items_added'),
)
