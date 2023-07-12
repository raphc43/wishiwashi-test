from django.conf.urls import patterns, url


urlpatterns = patterns('',
    url(r'^(?P<slug>[-\w\d]+)$', 'faq.views.question', name='question'),
    url(r'^$', 'faq.views.questions', name='questions'),
)
