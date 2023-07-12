import logging

from django.conf import settings
from django.http import HttpResponse
import requests

from .orders import RENDER_HTML2PDF_URL, RENDER_AUTH

logger = logging.getLogger(__name__)


def render_files_request(files, filename):
    try:
        r = requests.post(RENDER_HTML2PDF_URL,
                          auth=RENDER_AUTH,
                          files=files,
                          timeout=settings.RENDER_SERVICE_TIMEOUT_SECONDS,
                          verify=False)
    except requests.exceptions.Timeout:
        logger.exception("Request to {} timed out".format(RENDER_HTML2PDF_URL))
        return HttpResponse("Server request timed out", status=500)

    if r.status_code == 200:
        response = HttpResponse(r.content, content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="{}.pdf"'.format(filename)
        return response
    else:
        return HttpResponse(r.text, status=r.status_code)


