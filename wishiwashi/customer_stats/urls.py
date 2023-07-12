from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^stats$', 'customer_stats.views.stats', name='stats'),
    url(r'^placed_time_monthly/$',
        'customer_stats.views.placed_time_monthly', name='placed_time_monthly'),
    url(r'^placed_time_yearly/$', 'customer_stats.views.placed_time_yearly', name='placed_time_yearly'),
    url(r'^amount_time_monthly/$',
        'customer_stats.views.amount_time_monthly', name='amount_time_monthly'),
    url(r'^amount_time_yearly/$', 'customer_stats.views.amount_time_yearly', name='amount_time_yearly'),
    url(r'^new_customers_monthly/$',
        'customer_stats.views.new_customers_monthly', name='new_customers_monthly'),
    url(r'^new_customers_yearly/$', 'customer_stats.views.new_customers_yearly', name='new_customers_yearly'),
    url(r'^pickup_delivery_time_monthly/$',
        'customer_stats.views.pickup_delivery_time_monthly', name='pickup_delivery_time_monthly'),
    url(r'^pickup_delivery_heatmap_monthly/$',
        'customer_stats.views.pickup_delivery_heatmap_monthly', name='pickup_delivery_heatmap_monthly'),
)
