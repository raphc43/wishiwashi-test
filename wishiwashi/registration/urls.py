from django.conf.urls import patterns, url

from registration import views

urlpatterns = patterns(
    '',
    url(r'^create\-account$', views.create_account, name='create_account'),
    url(r'^reset\-password$', views.reset_password, name='reset_password'),
    url(r'^reset\-done$', views.reset_done, name='reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        views.reset_confirm, name='reset_confirm'),
    url(r'^reset/complete', views.reset_complete, name='reset_complete'),
)
