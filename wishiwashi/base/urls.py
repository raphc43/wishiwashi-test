from django.conf import settings
from django.conf.urls import patterns, include, url
from django.views.generic.base import TemplateView
from django.conf.urls.static import static



urlpatterns = patterns(
    '',
    url(r'^bookings/', include('bookings.urls', namespace='bookings')),
    url(r'^vendors/', include('vendors.urls', namespace='vendors')),
    url(r'^payments/', include('payments.urls', namespace='payments')),
    url(r'^registration/', include('registration.urls', namespace='registration')),
    url(r'^privacy/$', TemplateView.as_view(template_name="legal/privacy.html", get_context_data=lambda: {'title': 'Privacy Policy'}), name='privacy'),
    url(r'^terms/$', TemplateView.as_view(template_name="legal/terms.html", get_context_data=lambda: {'title': 'Terms & Conditions'}), name='terms'),
    url(r'^about-us/$', TemplateView.as_view(template_name="flatpages/aboutus.html", get_context_data=lambda: {'title': 'About Wishi Washi'}), name='aboutus'),
    url(r'^clapham-shop/$', TemplateView.as_view(template_name="flatpages/clapham-shop.html", get_context_data=lambda: {'title': 'Clapham Shop'}), name='clapham_shop'),
    url(r'^areas/$', TemplateView.as_view(template_name="flatpages/areas.html", get_context_data=lambda:
                                          {'title': 'Areas Wishi Washi cover',
                                           'GOOGLE_PUBLIC_API_KEY': settings.GOOGLE_PUBLIC_API_KEY}), name='areas'),
    url(r'^faq/', include('faq.urls', namespace='faq')),
    url(r'^customer_stats/', include('customer_stats.urls', namespace='customer_stats')),
    url(r'^robots.txt$', TemplateView.as_view(template_name='txt/robots.txt', content_type='text/plain')),
    url(r'^manifest.json$', TemplateView.as_view(template_name='json/manifest.json', content_type='application/json')),
    url(r'^service-worker.js$', TemplateView.as_view(template_name='javascript/service-worker.js', content_type='application/javascript')),
    url(r'^$', 'bookings.views.landing', name='landing'),
)

if settings.ADMIN_ON:
    from django.contrib import admin
    urlpatterns += patterns('', url(r'^administrate/', include(admin.site.urls)))

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)