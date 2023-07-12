from datetime import timedelta
from django import forms
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
import phonenumbers
from phonenumbers import carrier
from phonenumbers.phonenumberutil import number_type as phone_number_type

from bookings.models import Item, Vendor
from customer_service.models import UserProfile


class OperatingHoursForm(forms.Form):
    opening_0 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    opening_1 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    opening_2 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    opening_3 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    opening_4 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    opening_5 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])

    closing_0 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    closing_1 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    closing_2 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    closing_3 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    closing_4 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])
    closing_5 = forms.IntegerField(validators=[
        MaxValueValidator(24),
        MinValueValidator(0)
    ])

    def check_hours(self, opening, closing):
        if int(opening) >= int(closing):
            raise forms.ValidationError('The closing time needs to be after the opening time')

    def clean_closing_0(self):
        value = self.cleaned_data.get('closing_0')

        self.check_hours(self.cleaned_data.get('opening_0'),
                         self.cleaned_data.get('closing_0'))

        return value

    def clean_closing_1(self):
        value = self.cleaned_data.get('closing_1')

        self.check_hours(self.cleaned_data.get('opening_1'),
                         self.cleaned_data.get('closing_1'))

        return value

    def clean_closing_2(self):
        value = self.cleaned_data.get('closing_2')

        self.check_hours(self.cleaned_data.get('opening_2'),
                         self.cleaned_data.get('closing_2'))

        return value

    def clean_closing_3(self):
        value = self.cleaned_data.get('closing_3')

        self.check_hours(self.cleaned_data.get('opening_3'),
                         self.cleaned_data.get('closing_3'))

        return value

    def clean_closing_4(self):
        value = self.cleaned_data.get('closing_4')

        self.check_hours(self.cleaned_data.get('opening_4'),
                         self.cleaned_data.get('closing_4'))

        return value

    def clean_closing_5(self):
        value = self.cleaned_data.get('closing_5')

        self.check_hours(self.cleaned_data.get('opening_5'),
                         self.cleaned_data.get('closing_5'))

        return value


class OutCodeCatchmentForm(forms.Form):

    def clean(self):
        cleaned_data = self.cleaned_data

        return cleaned_data


class ContactAndNotificationsForm(forms.Form):
    email_address = forms.EmailField(max_length=75)
    mobile_number = forms.CharField(max_length=20)
    notify_via_email = forms.BooleanField(required=False)
    notify_via_sms = forms.BooleanField(required=False)

    def clean_email_address(self):
        email_address = self.cleaned_data.get('email_address').lower().strip()

        # TODO If the email address matches the user's current address then let
        # them use it
        if User.objects.filter(email=email_address).exclude(pk=self.user.pk).count():
            raise forms.ValidationError('There is already an account with this email address.')

        return email_address

    def clean_mobile_number(self):
        try:
            parsed = phonenumbers.parse(self.cleaned_data.get('mobile_number'), "GB")
        except Exception:
            raise forms.ValidationError('You must use a British mobile number.')

        if parsed.country_code != 44:
            raise forms.ValidationError('You must use a British mobile number.')

        if not carrier._is_mobile(phone_number_type(parsed)):
            raise forms.ValidationError('You must use a British mobile number (land lines are not supported).')

        normalised_mobile_number = '0044%s' % parsed.national_number

        # TODO If the mobile number matches the user's current address then let
        # them use it
        already_exists = UserProfile.objects.filter(
            mobile_number=normalised_mobile_number
        ).exclude(user=self.user).count() > 0

        if already_exists:
            raise forms.ValidationError('There is an existing account using this mobile number, '
                                        'please use another mobile number.')

        return normalised_mobile_number


class ReportIssueForm(forms.Form):
    vendor_issue_contact_issue_pk = forms.IntegerField(required=False)
    vendor_pick_up_and_delivery_issue_pk = forms.IntegerField(required=False)
    vendor_items_issue_pk = forms.IntegerField(required=False)

    item_pk = forms.IntegerField(required=False)

    other_contact_issue_details = forms.CharField(required=False, max_length=4096)
    other_pick_up_and_delivery_issue_details = forms.CharField(required=False, max_length=4096)
    other_items_issue_details = forms.CharField(required=False, max_length=4096)

    def clean_other_contact_issue_details(self):
        issue_pk = int(self.cleaned_data.get('vendor_issue_contact_issue_pk')
                       or 0)
        details = self.cleaned_data.get('other_contact_issue_details').strip()

        if issue_pk == -1:
            if not len(details):
                raise forms.ValidationError('Please describe the issue in detail')

        return details

    def clean_other_pick_up_and_delivery_issue_details(self):
        issue_pk = int(self.cleaned_data.get('vendor_pick_up_and_delivery_issue_pk') or 0)
        details = self.cleaned_data.get('other_pick_up_and_delivery_issue_details').strip()

        if issue_pk == -1:
            if not len(details):
                raise forms.ValidationError('Please describe the issue in detail')

        return details

    def clean_other_items_issue_details(self):
        issue_pk = int(self.cleaned_data.get('vendor_items_issue_pk') or 0)
        details = self.cleaned_data.get('other_items_issue_details').strip()

        if issue_pk == -1:
            if not len(details):
                raise forms.ValidationError('Please describe the issue in detail')

        if issue_pk > 0:
            item_pk = int(self.cleaned_data.get('item_pk') or 0)

            if Item.objects.filter(pk=item_pk).count() < 1:
                raise forms.ValidationError('Item matching issue is missing')

        return details

    def clean(self):
        issues = set([
            int(self.cleaned_data.get('vendor_issue_contact_issue_pk')
                or 0),
            int(self.cleaned_data.get('vendor_pick_up_and_delivery_issue_pk')
                or 0),
            int(self.cleaned_data.get('vendor_items_issue_pk')
                or 0),
        ])

        if issues == set([0]):
            raise forms.ValidationError('Please select an issue before hitting the report button')

        return self.cleaned_data


class OrderPaymentsSearchForm(forms.Form):
    assigned_to_vendor = forms.ModelChoiceField(required=False, queryset=Vendor.objects.all(), empty_label="(All vendors)")
    clean_only_vendor = forms.ModelChoiceField(required=False, queryset=Vendor.objects.all(), empty_label="(All vendors)")
    start_date = forms.DateField(input_formats=['%d-%m-%Y'])
    end_date = forms.DateField(input_formats=['%d-%m-%Y'])

    def clean_start_date(self):
        start_date = self.cleaned_data['start_date']
        today = timezone.now().date()

        if start_date >= today:
            raise forms.ValidationError('Please select a start date in the past', code='invalid_date')

        return start_date

    def clean_end_date(self):
        end_date = self.cleaned_data['end_date']
        today = timezone.now().date()

        if end_date >= today:
            raise forms.ValidationError('Please select an end date in the past', code='invalid_date')

        return end_date

    def clean(self):
        cleaned_data = super(OrderPaymentsSearchForm, self).clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if start_date > end_date:
                raise forms.ValidationError('Start date before the end date', code='invalid_dates')

            if (end_date - start_date) > timedelta(days=80):
                raise forms.ValidationError('Date range must not exceed {} days'.format(80),
                                            code='invalid_dates')


class ExpectedBackConfirmForm(forms.Form):
    id = forms.IntegerField()


class UpcomingDateForm(forms.Form):
    date = forms.DateField(input_formats=['%Y-%m-%d'])


class TagsForm(forms.Form):
    uuid = forms.CharField(max_length=8, min_length=1, required=True, label="Order/Ticket ID")

    def clean_uuid(self):
        return self.cleaned_data.get('uuid').upper()


