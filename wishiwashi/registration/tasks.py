from base.celery import app
from celery.utils.log import get_task_logger
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from requests.auth import HTTPBasicAuth
import requests
import ujson as json


logger = get_task_logger(__name__)


@app.task(bind=True,
          default_retry_delay=180,
          max_retries=20,
          time_limit=160)
def reset_password_via_email(self, user_pk):
    auth = HTTPBasicAuth(settings.COMMUNICATE_SERVICE_USERNAME,
                         settings.COMMUNICATE_SERVICE_PASSWORD)

    user = User.objects.get(pk=user_pk)

    context = {
        'token': token_generator.make_token(user),
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'email': user.email,
        'domain': settings.DOMAIN,
        'protocol': 'https',
        'first_name': user.first_name,
        'last_name': user.last_name,
        'site_name': settings.SITE_NAME
    }

    subject = render_to_string('registration/emails/reset-password-subject.txt', context)

    # Email subject *must not* contain newlines
    subject = ''.join(subject.splitlines())

    html_content = render_to_string('registration/emails/reset-password.html', context)
    text_content = render_to_string('registration/emails/reset-password.txt', context)

    payload = {
        'from_name': settings.FROM_EMAIL_NAME,
        'from_email_address': settings.FROM_EMAIL_ADDRESS,
        'subject': subject,
        'html_content': html_content,
        'text_content': text_content,
        'recipients': [user.email]
    }

    try:
        url = '%semail' % settings.COMMUNICATE_SERVICE_ENDPOINT
        resp = requests.post(url, data={'payload': json.dumps(payload)}, auth=auth, timeout=30, verify=False)
        assert resp.status_code == 200, 'HTTP %d from %s' % (resp.status_code, url)

        resp = json.loads(resp.content)

        assert resp['error'] is False, resp
        assert int(resp['job_id']) > 0, resp
    except Exception as exc:
        msg = 'Exception while sending reset password via email. Retrying...'
        logger.exception(msg)
        raise self.retry(exc=exc)

    return True
