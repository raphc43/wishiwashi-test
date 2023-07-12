# -*- coding: utf-8 -*-
from decimal import Decimal
import uuid
from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import User, AnonymousUser
from django.test import TestCase, override_settings
from django.test.client import Client, RequestFactory
from django.core.urlresolvers import reverse
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils.encoding import force_bytes, force_text
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from mock import patch
from freezegun import freeze_time

from customer_service.models import UserProfile

from .views import create_account
from bookings.factories import ItemFactory, ItemAndQuantityFactory, UserFactory


def save(self):
    pass


def add_session_to_request(request, session_data=None):
    """Annotate a request object with a session"""
    middleware = SessionMiddleware()
    middleware.process_request(request)
    request.session.save()

    if session_data:
        _session = request.session

        for _key, _value in session_data.iteritems():
            _session[_key] = _value

        _session.save()
        request.session.save()


@patch('registration.views.PasswordResetForm.save', save)
class Views(TestCase):
    def setUp(self):
        self.client = Client()
        super(Views, self).setUp()

    def test_reset_password(self):
        response = self.client.get(reverse('registration:reset_password'))
        self.assertContains(response, "Reset password")

    def test_reset_password_redirects(self):
        user = UserFactory()
        form = {'email_address': user.email}
        response = self.client.post(reverse('registration:reset_password'), form, follow=True)
        self.assertContains(response, "Password reset sent")

    def test_reset_password_invalid_user(self):
        user = UserFactory(is_active=False)
        form = {'email_address': user.email}
        response = self.client.post(reverse('registration:reset_password'), form)
        self.assertFormError(response, 'form', 'email_address', "Account is disabled")

    def test_reset_password_unknown_email(self):
        form = {'email_address': "unknown@test.com"}
        response = self.client.post(reverse('registration:reset_password'), form)
        self.assertFormError(response, 'form', 'email_address', "unknown@test.com does not exist")

    def test_reset_confirm(self):
        user = UserFactory()
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        response = self.client.get(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}))
        self.assertContains(response, "Enter new password")
        self.assertContains(response, 'name="new_password1"')
        self.assertContains(response, 'name="new_password2"')

    def test_reset_confirm_complete(self):
        user = UserFactory(password="original")

        form = {'new_password1': 'new_password',
                'new_password2': 'new_password'}
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        response = self.client.post(reverse('registration:reset_confirm',
                                    kwargs={'uidb64': uidb64, 'token': token}), form, follow=True)
        self.assertContains(response, "Your password has been reset")
        self.assertTrue(User.objects.get(pk=user.pk).check_password('new_password'))

    def test_reset_confirm_invalid_url(self):
        user = UserFactory()
        uidb64 = '6544'
        token = token_generator.make_token(user)
        response = self.client.get(reverse('registration:reset_confirm',
                                   kwargs={'uidb64': uidb64, 'token': token}))
        self.assertContains(response, "The password reset link was invalid")
        self.assertNotContains(response, 'name="new_password1"')
        self.assertNotContains(response, 'name="new_password2"')
        self.assertContains(response, "Password reset unsuccessful")

    def test_reset_confirm_complete_one_time_use(self):
        user = UserFactory(password="original")

        form = {'new_password1': 'new_password',
                'new_password2': 'new_password'}
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        response = self.client.post(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}),
                                    form, follow=True)
        self.assertContains(response, "Your password has been reset")
        self.assertTrue(User.objects.get(
            pk=user.pk).check_password('new_password'))

        response = self.client.get(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}))
        self.assertContains(response, "The password reset link was invalid")

    def test_reset_confirm_failure(self):
        user = UserFactory()

        form = {'new_password1': 'new_password',
                'new_password2': 'new_passwordd_'}
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        response = self.client.post(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}),
                                    form, follow=True)
        self.assertFormError(response,
                             'form',
                             'new_password2',
                             "The two password fields didn't match.")

    def test_reset_confirm_failure_min_password(self):
        user = UserFactory()

        form = {'new_password1': 'new',
                'new_password2': 'new'}
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        response = self.client.post(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}),
                                    form, follow=True)
        self.assertFormError(response, 'form', 'new_password1',
                             "Ensure this value has at least 7 characters (it has 3).")


class ResetPassword(TestCase):
    def test_reset_confirm_complete_relogin(self):
        # create user
        user = UserFactory(password="Original", email="test@test.com")
        c = Client()

        # reset password
        form = {'new_password1': 'New_password', 'new_password2': 'New_password'}

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        r = c.post(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}), form, follow=True)

        # Check generated tokens
        uid = force_text(urlsafe_base64_decode(uidb64))
        self.assertEqual(user, User.objects.get(pk=uid))
        self.assertTrue(token_generator.check_token(user, token))

        self.assertContains(r, "Your password has been reset")
        self.assertTrue(User.objects.get(pk=user.pk).check_password('New_password'))

        # login - case sensitive
        r = c.post(reverse('bookings:login'), {'email_address': 'test@test.com', 'password': 'New_password'})
        self.assertRedirects(r,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

        # logout
        r = c.get(reverse('bookings:logout'))
        self.assertRedirects(r,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

    def test_reset_confirm_complete_below_user_password_max(self):
        # create user
        user = UserFactory(password="original", email="test@test.com")

        with override_settings(USER_PASSWORD_LOWERCASED_MAX_PK=user.pk + 1):
            c = Client()
            # login - case insensitive
            r = c.post(reverse('bookings:login'), {'email_address': 'test@test.com', 'password': 'OrIgInAl'})
            self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)
            # logout
            r = c.get(reverse('bookings:logout'))
            self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)

            # login - case sensitive
            r = c.post(reverse('bookings:login'), {'email_address': 'test@test.com', 'password': 'original'})
            self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)
            # logout
            r = c.get(reverse('bookings:logout'))
            self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)

    def test_reset_confirm_complete_above_user_password_max(self):
        # create user
        user = UserFactory(password="original", email="test@test.com")

        with override_settings(USER_PASSWORD_LOWERCASED_MAX_PK=user.pk - 1):
            c = Client()
            # login - case insensitive
            r = c.post(reverse('bookings:login'), {'email_address': 'test@test.com', 'password': 'OrIgInAl'})
            self.assertEqual(r.status_code, 200)

            # login - case sensitive
            r = c.post(reverse('bookings:login'), {'email_address': 'test@test.com', 'password': 'original'})
            self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)
            # logout
            r = c.get(reverse('bookings:logout'))
            self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)

    @freeze_time("2015-01-05 13:30:00")
    def test_reset_confirm_registration(self):
        c = Client()
        # https://docs.djangoproject.com/en/1.8/topics/testing/tools/#django.test.Client.session
        session = c.session
        for k, v in {'postcode': 'w1 1aa',
                     'out_code': 'w1',
                     'pick_up_time': '2015-01-06 10',
                     'delivery_time': '2015-01-09 10',
                     'items': {1: 5}}.iteritems():
            session[k] = v
        session.save()

        form = {
            'email_address': 'test@wishiwashi.com',
            'mobile_number': '07752123456',
            'password': 'Testing-123',
            'password_confirmed': 'Testing-123',
            'terms': 'on'
        }
        url = reverse('registration:create_account')
        resp = c.post(url, form)

        self.assertRedirects(resp, reverse('bookings:address'), status_code=302, target_status_code=200)

        # logout
        r = c.get(reverse('bookings:logout'))
        self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)

        # login - case insensitive
        r = c.post(reverse('bookings:login'), {'email_address': 'test@wishiwashi.com', 'password': 'testing-123'})
        self.assertEqual(r.status_code, 200)

        # login - case sensitive
        r = c.post(reverse('bookings:login'), {'email_address': 'test@wishiwashi.com', 'password': 'Testing-123'})
        self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)

        # logout
        r = c.get(reverse('bookings:logout'))
        self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)

        # reset password
        form = {'new_password1': 'New_password', 'new_password2': 'New_password'}

        user = User.objects.get(email='test@wishiwashi.com')
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = token_generator.make_token(user)
        r = c.post(reverse('registration:reset_confirm', kwargs={'uidb64': uidb64, 'token': token}), form, follow=True)

        # Check generated tokens
        uid = force_text(urlsafe_base64_decode(uidb64))
        self.assertEqual(user, User.objects.get(pk=uid))
        self.assertTrue(token_generator.check_token(user, token))

        self.assertContains(r, "Your password has been reset")
        self.assertTrue(User.objects.get(pk=user.pk).check_password('New_password'))

        # login - case sensitive
        r = c.post(reverse('bookings:login'), {'email_address': 'test@wishiwashi.com', 'password': 'New_password'})
        self.assertRedirects(r, reverse('landing'), status_code=302, target_status_code=200)


class ViewsAccount(TestCase):
    def setUp(self):
        settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.session = store
        self.client = Client()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

    def _populate_session(self, session_data):
        """
        :param dict session_data: keys and values to set in the session
        """
        _session = self.client.session

        for _key, _value in session_data.iteritems():
            _session[_key] = _value

        _session.save()
        self.client.session.save()

    @freeze_time("2015-01-05 13:30:00")
    def test_create_account(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5}
        })

        resp = self.client.get(reverse('registration:create_account'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-05 13:30:00")
    def test_create_account_bad_email_address(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5}
        })

        url = reverse('registration:create_account')
        resp = self.client.post(url, {
            'email_address': '',
            'mobile_number': '07725 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing123',
        })
        self.assertEqual(resp.status_code, 200)

        self.assertFormError(resp,
                             'form',
                             'email_address',
                             [u'This field is required.'])

        resp = self.client.post(url, {
            'email_address': 'not an email address',
            'mobile_number': '07725 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'email_address',
                             [u'Enter a valid email address.'])

    @freeze_time("2015-01-05 13:30:00")
    def test_create_account_bad_mobile_number(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5}
        })

        url = reverse('registration:create_account')
        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '',
            'password': 'testing123',
            'password_confirmed': 'testing123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'mobile_number',
                             'This field is required.')

        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '0207 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'mobile_number',
                             'You must use a British mobile number '
                             '(land lines are not supported).')

        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '+372 5123 4567',
            'password': 'testing123',
            'password_confirmed': 'testing123',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'mobile_number',
                             'You must use a British mobile number.')

    @freeze_time("2015-01-05 13:30:00")
    def test_create_account_duplicate_mobile_number(self):
        mobile_number_normalised = '00447752123456'
        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='test@test.com', password='testing123')
        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5}
        })

        url = reverse('registration:create_account')
        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': mobile_number_normalised,
            'password': 'testing123',
            'password_confirmed': 'testing123',
        })
        self.assertFormError(resp,
                             'form',
                             'mobile_number',
                             [u'There is an existing account using this mobile number, please use another mobile number.'])

    @freeze_time("2015-01-05 13:30:00")
    def test_create_account_bad_passwords(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5}
        })

        url = reverse('registration:create_account')
        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '+44 7752 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing',
        })
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u'Passwords do not match.'])

        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '+44 7752 123 456',
            'password': ' ',
            'password_confirmed': ' ',
        })
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u'Your password must be at least 7 characters in length.'])

        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '+44 7752 123 456',
            'password': 'testin',
            'password_confirmed': 'testin',
        })
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u'Your password must be at least 7 characters in length.'])

    @freeze_time("2015-01-05 13:30:00")
    def test_create_account_valid_submission(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5}
        })

        url = reverse('registration:create_account')
        resp = self.client.post(url, {
            'email_address': 'mark@wishiwashi.com',
            'mobile_number': '+44 7752 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing123',
            'terms': 'on'
        })
        self.assertRedirects(resp,
                             reverse('bookings:address'),
                             status_code=302,
                             target_status_code=200)
        self.assertIn(SESSION_KEY, self.client.session)

    @freeze_time("2014-04-06 10:00:00")
    def test_create_account_valid_submission_password(self):
        item = ItemFactory(price=Decimal('17.20'))
        ItemAndQuantityFactory(quantity=4, item=item)

        form = {
            'email_address': 'test@wishiwashi.com',
            'mobile_number': '+44 7700 900 100',
            'password': "ḝl ñiño",
            'password_confirmed': "ḝl ñiño",
            'terms': 'on'
        }
        request = RequestFactory().post(reverse('registration:create_account'), form)
        request.user = AnonymousUser()

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
        })

        response = create_account(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:address'))

        user = User.objects.all().order_by("-date_joined")[0]
        self.assertTrue(user.check_password("ḝl ñiño"))

    @freeze_time("2014-04-06 10:00:00")
    def test_create_account_valid_submission_password_mismatch(self):
        item = ItemFactory(price=Decimal('17.20'))
        ItemAndQuantityFactory(quantity=4, item=item)

        form = {
            'email_address': 'test@wishiwashi.com',
            'mobile_number': '+44 7700 900 100',
            'password': "ḜL ÑIÑO",
            'password_confirmed': "Ḝl ÑiñO",
            'terms': 'on'
        }
        request = RequestFactory().post(reverse('registration:create_account'), form)
        request.user = AnonymousUser()

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
        })

        response = create_account(request)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('Passwords do not match.' in response.content)

    @freeze_time("2014-04-06 10:00:00")
    def test_create_account_invalid_submission_password(self):
        item = ItemFactory(price=Decimal('17.20'))
        ItemAndQuantityFactory(quantity=4, item=item)

        form = {
            'email_address': 'test@wishiwashi.com',
            'mobile_number': '+44 7700 900 100',
            'password': "ḝl ñiño",
            'password_confirmed': "ḝL ñIñoo",
            'terms': 'on'
        }
        request = RequestFactory().post(reverse('registration:create_account'), form)
        request.user = AnonymousUser()

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
        })

        response = create_account(request)
        self.assertTrue('Passwords do not match.' in response.content)


