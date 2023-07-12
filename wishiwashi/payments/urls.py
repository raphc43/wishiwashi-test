from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^$', 'payments.views.landing', name='landing'),
    url(r'^charge/$', 'payments.views.charge', name='charge'),
)
