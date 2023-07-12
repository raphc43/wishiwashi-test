import uuid

from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as django_login
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template.response import TemplateResponse
from django.template import RequestContext
from django.utils.encoding import force_text
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters

from customer_service.models import UserProfile
from bookings.decorators import check_session_data
from bookings.progress import get_progress_svg
from bookings.forms import CreateAccountForm
from .forms import PasswordResetForm, PasswordSetForm


@require_http_methods(["GET", "POST"])
@check_session_data(check_postcode=True, check_pick_up_time=True, check_delivery_time=True, check_items=True)
def create_account(request):
    # If the user is logged in then we already have their mobile number
    # and email address so don't show this page.
    if request.user and request.user.is_authenticated() and request.user.is_active:
        return HttpResponseRedirect(reverse('bookings:address'))

    if request.method == 'POST':
        form = CreateAccountForm(request.POST)

        if form.is_valid():
            user = User.objects.create_user(
                # They will use their email addresses to login
                username=str(uuid.uuid4())[:28],
                email=form.cleaned_data["email_address"],
                password=form.cleaned_data["password"])
            user.save()  # This shouldn't be needed, create_user already saves

            profile = UserProfile(user=user, mobile_number=form.cleaned_data["mobile_number"])
            profile.save()

            # Copy all sessions data before login and then set it again as
            # django_login will wipe the session data out.
            _session = {}
            _key_names = ('postcode', 'out_code', 'pick_up_time', 'delivery_time', 'items')
            for _key in _key_names:
                _session[_key] = request.session[_key]

            _user = authenticate(username=user.username, password=form.cleaned_data["password"])
            django_login(request, _user)

            for _key in _key_names:
                request.session[_key] = _session[_key]

            return HttpResponseRedirect(reverse('bookings:address'))

    else:
        form = CreateAccountForm()

    context = {'form': form, 'progress': get_progress_svg('contact_details', request), 'title': 'Create an account'}

    return render_to_response('bookings/create_account.html', context, context_instance=RequestContext(request))


@require_http_methods(["GET", "POST"])
def reset_password(request):
    if request.method == "POST":
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('registration:reset_done'))
    else:
        form = PasswordResetForm()

    context = {
        'form': form,
        'title': 'Reset password',
    }

    return TemplateResponse(request, 'registration/reset_password.html', context)


@require_http_methods(["GET"])
def reset_done(request):
    context = {
        'title': 'Password reset sent',
    }

    return TemplateResponse(request, 'registration/reset_done.html', context)


@require_http_methods(["GET", "POST"])
@sensitive_post_parameters()
@never_cache
def reset_confirm(request, uidb64=None, token=None):
    """
    View that checks the hash in a password reset link and presents a
    form for entering a new password.
    """
    assert uidb64 is not None and token is not None  # checked by URLconf
    try:
        uid = force_text(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and token_generator.check_token(user, token):
        validlink = True
        title = 'Enter new password'
        if request.method == 'POST':
            form = PasswordSetForm(user, request.POST)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect(reverse('registration:reset_complete'))
        else:
            form = PasswordSetForm(user)
    else:
        validlink = False
        form = None
        title = 'Password reset unsuccessful'

    context = {
        'form': form,
        'title': title,
        'validlink': validlink,
        'uidb64': uidb64,
        'token': token
    }

    return TemplateResponse(request, 'registration/reset_confirm.html', context)


@require_http_methods(["GET"])
def reset_complete(request):
    context = {
        'title': 'Password reset complete'
    }

    return TemplateResponse(request, 'registration/reset_complete.html', context)
