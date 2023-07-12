# -*- coding: utf-8 -*-
import string

from dateutil.parser import parse
from django import forms
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.validators import MinLengthValidator
from django.core.urlresolvers import reverse
from django.utils.http import is_safe_url
import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type as phone_number_type, NumberParseException
from ukpostcodeparser import parse_uk_postcode
import pytz

from bookings.models import Item, OutCodes, Vendor
from bookings.utils import is_postcode_valid
from customer_service.models import UserProfile


def validate_date_and_hour(time):
    assert time
    time = time.strip().lower()
    assert time and len(time) == len('YYYY-MM-DD HH')
    assert (not len(set(string.ascii_lowercase).intersection(time))
            and not len(set(string.ascii_uppercase).intersection(time)))
    tz_london = pytz.timezone(settings.TIME_ZONE)
    tz_london.localize(parse(time))


class PostcodeForm(forms.Form):
    postcode = forms.CharField(label='What is your postcode?', max_length=8)

    def clean_postcode(self):
        postcode = self.cleaned_data['postcode']

        if not is_postcode_valid(postcode):
            raise forms.ValidationError("Postcode is invalid")

        return postcode


class NotifyWhenAvailableForm(forms.Form):
    email_address = forms.EmailField(label='Email Address', max_length=75)
    out_code = forms.CharField(label='Out code', max_length=4)

    def clean_email_address(self):
        return self.cleaned_data.get('email_address').lower().strip()

    def clean_out_code(self):
        out_code = self.cleaned_data['out_code']

        if not is_postcode_valid(out_code):
            raise forms.ValidationError("Postcode out code is invalid")

        return out_code


class PickUpTimeForm(forms.Form):
    time_slot = forms.CharField(label='Time Slot', max_length=13,  # e.g. 2014-01-01 09
                                error_messages={'required': 'Please select your 1 hour pick up time slot'})

    def clean_time_slot(self):
        value = self.cleaned_data['time_slot']

        try:
            validate_date_and_hour(value)
        except (AssertionError, ValueError):
            raise forms.ValidationError("Time slot is invalid")

        date, hour = self.data['time_slot'].split(' ')
        hour = int(hour)

        for day in self.data['calendar_grid']:
            if day['date'] == date:
                for timeslot in day['time_slots']:
                    if int(timeslot['hour']) == hour:
                        if timeslot['available']:
                            return value
                        else:
                            raise forms.ValidationError("Time slot is not available")

        raise forms.ValidationError("Time slot is not available")


class DeliveryTimeForm(forms.Form):
    time_slot = forms.CharField(label='Time Slot', max_length=13,  # e.g. 2014-01-01 09
                                error_messages={'required': 'Please select your 1 hour delivery time slot'})

    # This method will be expanded when the demand-spreading system
    # is implemented
    def clean_time_slot(self):
        value = self.cleaned_data['time_slot']

        try:
            validate_date_and_hour(value)
        except (AssertionError, ValueError):
            raise forms.ValidationError("Time slot is invalid")

        date, hour = self.data['time_slot'].split(' ')
        hour = int(hour)

        for day in self.data['calendar_grid']:
            if day['date'] == date:
                for timeslot in day['time_slots']:
                    if int(timeslot['hour']) == hour:
                        if timeslot['available']:
                            return value
                        else:
                            raise forms.ValidationError("Time slot is not available")

        raise forms.ValidationError("Time slot is not available")


class ItemsToCleanForm(forms.Form):
    selected_category = forms.IntegerField(label='Selected category')

    def clean(self):
        cleaned_data = {key: val
                        for key, val in self.data.items()
                        if 'quantity-' in key}
        cleaned_data['items'] = {}

        selections = {}

        for _key, _quantity in cleaned_data.items():
            if 'quantity-' not in _key or len(_key.split('-')) != 2:
                continue

            _, product_id = _key.split('-')

            try:
                quantity = int(_quantity)
                product_id = int(product_id)
            except (ValueError, TypeError):
                continue

            quantity = min(quantity, settings.MAX_QUANTITY_PER_ITEM)
            quantity = max(quantity, 0)

            selections[product_id] = quantity

        items_selected = Item.objects.filter(visible=True, category__visible=True, pk__in=selections.keys())

        order_total = sum([item.price * selections[item.pk] for item in items_selected])

        if not order_total:
            raise forms.ValidationError("You have not added any items to your order.")

        if order_total >= settings.MAX_ORDER_TOTAL:
            raise forms.ValidationError("For an order of this size you must contact our Customer Care team.")

        total_quantity = sum(selections.values())

        if total_quantity > settings.MAX_ORDER_QUANTITY:
            raise forms.ValidationError("You can not have more than %(value)s items in your basket.",
                                        params={'value': settings.MAX_ORDER_QUANTITY})

        cleaned_data['items'] = {int(item.pk): int(selections[item.pk])
                                 for item in items_selected
                                 if int(selections[item.pk])}

        return cleaned_data


class ItemsAddedForm(forms.Form):
    def clean(self):
        cleaned_data = {key: val
                        for key, val in self.data.iteritems()
                        if key.startswith('quantity-')}
        cleaned_data['items'] = {}

        selections = {}

        for _key, _quantity in cleaned_data.iteritems():
            if len(_key.split('-')) != 2:
                continue

            _, product_id = _key.split('-')

            try:
                quantity = int(_quantity)
                product_id = int(product_id)
            except (ValueError, TypeError):
                continue

            quantity = min(quantity, settings.MAX_QUANTITY_PER_ITEM)
            quantity = max(quantity, 0)

            selections[product_id] = quantity

        items_selected = Item.objects.filter(visible=True, category__visible=True, pk__in=selections.keys())

        order_total = sum([item.price * selections[item.pk] for item in items_selected])

        if order_total >= settings.MAX_ORDER_TOTAL:
            raise forms.ValidationError("For an order of this size you must contact our Customer Care team.")

        total_quantity = sum(selections.values())

        if total_quantity > settings.MAX_ORDER_QUANTITY:
            raise forms.ValidationError("You can not have more than %(value)s items in your basket.",
                                        params={'value': settings.MAX_ORDER_QUANTITY})

        cleaned_data['items'] = {int(item.pk): int(selections[item.pk])
                                 for item in items_selected
                                 if int(selections[item.pk])}

        return cleaned_data


class CreateAccountForm(forms.Form):
    email_address = forms.EmailField(label='Your e-mail address', max_length=75)
    mobile_number = forms.CharField(label='Your mobile number', max_length=20)
    password = forms.CharField(label="Pick a password for next time", max_length=75)
    password_confirmed = forms.CharField(label="Confirm password", max_length=75)
    terms = forms.BooleanField(label="I agree to the terms of use and privacy policy")

    def clean_email_address(self):
        email_address = self.cleaned_data.get('email_address').lower().strip()

        if User.objects.filter(email=email_address).count():
            raise forms.ValidationError('There is already an account with this email address.')

        return email_address

    def clean_mobile_number(self):
        try:
            parsed = phonenumbers.parse(self.cleaned_data.get('mobile_number'), "GB")
        except NumberParseException:
            raise forms.ValidationError('This does not seem to be a phone number.', code='invalid')

        if parsed.country_code != 44:
            raise forms.ValidationError('You must use a British mobile number.')

        if not carrier._is_mobile(phone_number_type(parsed)):
            raise forms.ValidationError('You must use a British mobile number (land lines are not supported).')

        normalised_mobile_number = '0044%s' % parsed.national_number

        # Make sure there is an index on this field?
        if UserProfile.objects.filter(mobile_number=normalised_mobile_number).exists():
            raise forms.ValidationError(
                'There is an existing account using this mobile number, please use another mobile number.')

        return normalised_mobile_number

    def clean_password(self):
        password = self.cleaned_data.get('password').strip()

        if len(password) < settings.MIN_PASSWORD_LENGTH:
            raise forms.ValidationError(
                "Your password must be at least %(min)s characters in length.",
                code='invalid_length',
                params={'min': settings.MIN_PASSWORD_LENGTH}
            )

        return password

    def clean_password_confirmed(self):
        password = self.cleaned_data.get('password_confirmed').strip()

        if len(password) < settings.MIN_PASSWORD_LENGTH:
            raise forms.ValidationError(
                "Password confirmed must be at least %(min)s characters in length.",
                code='invalid_length',
                params={'min': settings.MIN_PASSWORD_LENGTH}
            )

        return password

    def clean(self):
        cleaned_data = super(CreateAccountForm, self).clean()
        password = cleaned_data.get('password')
        password_confirmed = cleaned_data.get('password_confirmed')
        if password and password_confirmed:
            if password != password_confirmed:
                raise forms.ValidationError(
                    {'password': ["Passwords do not match."],
                     'password_confirmed': ["Passwords do not match."]}
                )

        return cleaned_data


class LoginForm(forms.Form):
    email_address = forms.CharField(label='Your e-mail address or mobile number', max_length=75)
    password = forms.CharField(label="Your password", max_length=75)
    next = forms.CharField(max_length=200, required=False)

    def clean_email_address(self):
        return self.cleaned_data.get('email_address').lower().strip()

    def clean_password(self):
        email_address = self.cleaned_data.get('email_address')
        password = self.cleaned_data.get('password')

        # Email address could be either an email address or mobile number
        users = User.objects.filter(email=email_address)

        if users:
            username = users[0].username
        else:
            try:
                parsed = phonenumbers.parse(email_address, "GB")
            except phonenumbers.NumberParseException:
                raise forms.ValidationError("Unable to locate email address or mobile number.")

            if parsed.country_code != 44:
                raise forms.ValidationError("Unable to locate email address or mobile number.")

            if not carrier._is_mobile(phone_number_type(parsed)):
                raise forms.ValidationError("Unable to locate email address or mobile number.")

            normalised_mobile_number = '0044%s' % parsed.national_number

            profiles = UserProfile.objects.filter(mobile_number=normalised_mobile_number)

            if profiles:
                username = profiles[0].user.username
            else:
                raise forms.ValidationError("Unable to locate email address or mobile number.")

        user = authenticate(username=username, password=password)

        # Initial passwords were all lowercased, so try possible old accounts
        # with lower password possibility
        if not user:
            legacy_password_user = False

            if users:
                legacy_password_user = users[0].pk <= settings.USER_PASSWORD_LOWERCASED_MAX_PK
            elif profiles:
                legacy_password_user = profiles[0].user.pk <= settings.USER_PASSWORD_LOWERCASED_MAX_PK

            if legacy_password_user:
                user = authenticate(username=username, password=password.lower())

        if user:
            if user.is_active:
                # Not sure about this!
                self.cleaned_data['user'] = user
                return password

            raise forms.ValidationError("Your account has been disabled")

        raise forms.ValidationError("Your login and password did not match")


class PickUpDropOffAddress(forms.Form):
    first_name = forms.CharField(label='First name', max_length=30, validators=[MinLengthValidator(2)])
    last_name = forms.CharField(label='Last name', max_length=30, validators=[MinLengthValidator(2)])
    flat_number_house_number_building_name = forms.CharField(label='Flat, house number and/or building name',
                                                             max_length=75, validators=[MinLengthValidator(1)])
    address_line_1 = forms.CharField(label='Address line 1', max_length=75, validators=[MinLengthValidator(4)])
    address_line_2 = forms.CharField(label='Address line 2', max_length=75, required=False)
    postcode = forms.CharField(label='Postcode', max_length=10)
    previous_address = forms.IntegerField(label='Previous address', required=False)

    def clean_first_name(self):
        """
        A. B. would be an acceptable first name
        """
        val = self.cleaned_data['first_name']

        if not len(set(string.ascii_lowercase).intersection(val)) > 0 and \
           not len(set(string.ascii_uppercase).intersection(val)) > 0:
            raise forms.ValidationError("Please enter your first name")

        if len(set(string.digits).intersection(val)) > 0:
            raise forms.ValidationError("Please enter your first name")

        return val

    def clean_last_name(self):
        """
        Võeti Võimaliku-Viljandi would be an acceptable last name
        """
        val = self.cleaned_data['last_name']

        if not len(set(string.ascii_lowercase).intersection(val)) > 0 and \
           not len(set(string.ascii_uppercase).intersection(val)) > 0:
            raise forms.ValidationError("Please enter your last name")

        if len(set(string.digits).intersection(val)) > 0:
            raise forms.ValidationError("Please enter your last name")

        return val

    def clean_postcode(self):
        postcode = self.cleaned_data['postcode']

        try:
            _postcode = parse_uk_postcode(postcode, incode_mandatory=False)
        except ValueError:
            raise forms.ValidationError("Please enter your full postcode.")

        if _postcode is None:
            raise forms.ValidationError("Please enter your full postcode.")

        out_code = _postcode[0].lower()

        if OutCodes.objects.filter(out_code=out_code).count() < 1:
            raise forms.ValidationError("Please enter your full postcode.")

        internal_postcode = "".join(_postcode).lower()

        if len(internal_postcode) < 5:
            raise forms.ValidationError("Please enter your full postcode")

        served_by_any_vendor = Vendor.objects.filter(catchment_area__out_code=out_code).count() > 0

        if not served_by_any_vendor:
            raise forms.ValidationError("We do not currently serve the %s postcode area" % out_code.upper())

        return internal_postcode


class ChangePostcodeForm(forms.Form):
    postcode = forms.CharField(label='Update postcode?', max_length=8)
    previous = forms.CharField(required=False, max_length=250)

    def clean_postcode(self):
        postcode = self.cleaned_data['postcode']

        try:
            out_code, _ = parse_uk_postcode(postcode, incode_mandatory=False)
        except ValueError:
            raise forms.ValidationError("Please enter your full postcode.", code='invalid')

        if not OutCodes.objects.filter(out_code=out_code.lower()).exists():
            raise forms.ValidationError("We do not currently serve the %(outcode)s postcode area", code='unknown',
                                        params={'outcode': out_code})

        return postcode

    def clean_previous(self):
        previous = self.cleaned_data['previous']
        if previous and is_safe_url(url=previous):
            return previous
        return reverse('landing')
