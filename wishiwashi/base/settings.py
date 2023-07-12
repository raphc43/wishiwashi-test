import os
from decimal import Decimal

import dj_database_url
from django.core.urlresolvers import reverse_lazy
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

SECRET_KEY = os.environ.get(
    "SECRET_KEY", "77)i2x8fke613)=dc^ucqu2f9l&yqsr6q#^68khhti86-4*!gs")

DEBUG = os.environ.get('DJANGO_DEBUG', '') == 'true'
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = [host.strip()
                 for host in os.environ.get("ALLOWED_HOSTS", "*").split(',')]

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'kombu.transport.django',
    'axes',
    'pipeline',
    'bootstrap3',
    'bookings',
    'customer_service',
    'faq',
    'vendors',
    'payments',
    'registration',
    'customer_stats',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'base.middleware.HTTPSOnly',
    'base.middleware.SetRemoteAddrForwardedFor',
    'axes.middleware.FailedLoginMiddleware',
)

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

ROOT_URLCONF = 'base.urls'

WSGI_APPLICATION = 'base.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',  
    }
}
# Requests handled inside a transaction
DATABASES['default']['ATOMIC_REQUESTS'] = True

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Middleware check to redirect over https
HTTPS_ONLY = bool(os.environ.get("HTTPS_ONLY", "") == 'yes')

CSRF_COOKIE_SECURE = bool(os.environ.get("CSRF_COOKIE_SECURE", "") == 'yes')

CSRF_COOKIE_HTTPONLY = True  # Stops JS from being able to read cookies

DOMAIN = os.environ.get("DOMAIN", "")
SITE_NAME = "wishiwashi.com"

# Allow for django admin to be served
ADMIN_ON = bool(os.environ.get("ADMIN_ON", "") == 'yes')

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = False
USE_L10N = True
USE_TZ = True

# UK_PHONE_NUMBER = '020 7228 1870'
# UK_PHONE_NUMBER_UGLY = '00442072281870'
UK_PHONE_NUMBER = '020 8749 6610'
UK_PHONE_NUMBER_UGLY = '00442087496610'
GOOGLE_ANALYTICS_CODE = 'UA-57696892-1'
HOURS_OF_OPERATION = 'Mon - Fri 8am - 10pm, Sat 8am - 5pm'
COLLECT_DELIVER_HOUR_START = 8
COLLECT_DELIVER_HOUR_END = 22

MIN_PASSWORD_LENGTH = 7

# Min amount for free transit
MIN_FREE_TRANSPORTATION = Decimal('15.00')
TRANSPORTATION_CHARGE = Decimal('3.95')

MAX_ORDER_TOTAL = Decimal('1250.00')
MAX_ORDER_QUANTITY = 150

# Some initial user accounts below this Primary Key
# forced the password to lower case
# Rather than break their passwords this value can be used
# to try lowercased alternatives
USER_PASSWORD_LOWERCASED_MAX_PK = 33

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = os.environ.get('STATIC_URL', '/static/')
assert STATIC_URL is not None and len(STATIC_URL), 'STATIC_URL environment variable is needed'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "external"),
)

STATIC_ROOT = os.path.join(BASE_DIR, "static")

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'pipeline.finders.PipelineFinder',
)

STATICFILES_STORAGE = 'pipeline.storage.PipelineCachedStorage'

TEMPLATE_DIRS = [os.path.join(BASE_DIR, 'templates')]

TEMPLATE_CONTEXT_PROCESSORS = (
    'base.context_processor.get_settings',
    'bookings.context_processors.total_items',
    'vendors.context_processors.wishi_washi_user',
    'django.core.context_processors.request',
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
)

PIPELINE_CSS = {
    'main': {
        'source_filenames': (
            'styles/wishiwashi.css',
            'styles/calendar.css',
            'styles/items.css',
        ),
        'output_filename': 'styles/min.css'
    },
    'vendor': {
        'source_filenames': (
            'styles/global.css',
            'styles/stats.css',
        ),
        'output_filename': 'styles/vendor.css'
    },
}

PIPELINE_JS = {
    'transit': {
        'source_filenames': (
            'scripts/pick_up_drop_off_calendar.js',
        ),
        'output_filename': 'scripts/transit.min.js',
    },
    'items': {
        'source_filenames': (
            'scripts/items_to_clean.js',
        ),
        'output_filename': 'scripts/items.min.js',
    },
    'items_added': {
        'source_filenames': (
            'scripts/items_added.js',
        ),
        'output_filename': 'scripts/items_added.min.js',
    },
    'landing': {
        'source_filenames': (
            'scripts/landing.js',
        ),
        'output_filename': 'scripts/landing.min.js',
    },
    'calendar': {
        'source_filenames': (
            'scripts/calendar.js',
        ),
        'output_filename': 'scripts/calendar.min.js',
    },
    'maps': {
        'source_filenames': (
            'scripts/map.js',
        ),
        'output_filename': 'scripts/map.min.js',
    },
    'stats': {
        'source_filenames': (
            'scripts/d3.tip.v0.6.3.js',
        ),
        'output_filename': 'scripts/stats.min.js',
    },
}

SESSION_EXPIRE_AT_BROWSER_CLOSE = True

LOGIN_URL = reverse_lazy('bookings:login')

STRIPE_API_VERSION = '2015-09-08'
STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "")

RENDER_SERVICE_ENDPOINT = os.environ.get("RENDER_SERVICE_ENDPOINT", "https://render.wishiwashi.com/orders/")
RENDER_SERVICE_STATUS_ENDPOINT = os.environ.get("RENDER_SERVICE_STATUS_PREFIX",
                                                "https://render.wishiwashi.com/orders/status/")

RENDER_SERVICE_URL = os.environ.get("RENDER_SERVICE_URL", "https://render.wishiwashi.com")
RENDER_SERVICE_USERNAME = os.environ.get("RENDER_SERVICE_USERNAME", "")
RENDER_SERVICE_PASSWORD = os.environ.get("RENDER_SERVICE_PASSWORD", "")
RENDER_SERVICE_HTML2PDF_PATH = "/html2pdf/convert"
RENDER_SERVICE_TIMEOUT_SECONDS = 20

COMMUNICATE_SERVICE_ENDPOINT = os.environ.get("COMMUNICATE_SERVICE_ENDPOINT",
                                              "https://communicate.wishiwashi.com/communicate/")
COMMUNICATE_SERVICE_USERNAME = os.environ.get("COMMUNICATE_SERVICE_USERNAME", "")
COMMUNICATE_SERVICE_PASSWORD = os.environ.get("COMMUNICATE_SERVICE_PASSWORD", "")

FROM_EMAIL_ADDRESS = 'help@wishiwashi.com'
FROM_EMAIL_NAME = 'Wishi Washi'

# Wishi Washi Vendor Primary Key
# Loaded from fixture
VENDOR_WISHI_WASHI_PK = 1

# Default clean only vendor (currently: Aqua clean)
VENDOR_DEFAULT_CLEAN_ONLY_PK = 2

BROKER_URL = os.environ['REDIS_URL']
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_IGNORE_RESULT = True

MAX_QUANTITY_PER_ITEM = 30

SESSION_COOKIE_AGE = 60 * 60 * 24 * 7

# Maximum slots (pick up or drop off) per hour
MAX_APPOINTMENTS_PER_HOUR = 16

# Endpoints for tagging printing
TAGGING_PRINTERS = ["https://star1.wishiwashi.com/orders/order",
                    "https://star2.wishiwashi.com/orders/order"]

# Current VAT percentage rate
VAT_RATE = Decimal('20')

GOOGLE_PUBLIC_API_KEY = 'AIzaSyBLX0kiMCPNzX84jgnM1Lb099H4xFC1jso'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'wishiwashi': {
            'handlers': ['console'],
        },
        'django': {
            'handlers': ['console'],
        },
    },
}


# If you don't want to set environment variables on your local development
# environment then please add your values into local_settings.py.
try:
    from local_settings import *
except ImportError:
    pass

assert len(SECRET_KEY) > 20

# If stripe details aren't available we need to know as soon as possible
assert len(STRIPE_PUBLISHABLE_KEY) > 20
assert len(STRIPE_API_KEY) > 20

# If https is enabled we need a domain
if HTTPS_ONLY:
    assert len(DOMAIN) > 5

assert len(RENDER_SERVICE_ENDPOINT) > 7
assert len(RENDER_SERVICE_USERNAME) > 3
assert len(RENDER_SERVICE_PASSWORD) > 3

assert len(COMMUNICATE_SERVICE_ENDPOINT) > 7
assert len(COMMUNICATE_SERVICE_USERNAME) > 3
assert len(COMMUNICATE_SERVICE_PASSWORD) > 3
