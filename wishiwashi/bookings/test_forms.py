# -*- coding: utf-8 -*-
from decimal import Decimal
import datetime

from django.conf import settings
from django.test import TestCase
from freezegun import freeze_time
import pytz

from .calendar import get_calendar
from .factories import TrackConfirmedOrderSlotsFactory, ItemFactory, ItemAndQuantityFactory
from .forms import CreateAccountForm, PickUpTimeForm, DeliveryTimeForm, ItemsAddedForm


class Forms(TestCase):
    def test_password_case_inexact(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "07700 900000",
            "password": unicode("ĶliAs0ĭ", encoding='utf-8'),
            "password_confirmed": unicode("ķliaS0ĭ", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert not form.is_valid()

    def test_password_case_exact(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "07700 900000",
            "password": unicode("ķliAs0ĭ", encoding='utf-8'),
            "password_confirmed": unicode("ķliAs0ĭ", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert form.is_valid()

    def test_leading_trailing_whitespace_removed(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "07700 900000",
            "password": unicode("  ǺǺțHX®-  ", encoding='utf-8'),
            "password_confirmed": unicode("   ǺǺțHX®-    ", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert form.is_valid()

    def test_ut8_characters_length_fail(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "07700 900000",
            "password": unicode("ϑ፼𐌼𐌈ஊ𐏁", encoding='utf-8'),
            "password_confirmed": unicode("ϑ፼𐌼𐌈ஊ𐏁", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['password'][0].code == 'invalid_length'
        assert errors['password_confirmed'][0].code == 'invalid_length'

    def test_ut8_characters_length_success(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "07700 900000",
            "password": unicode("Ḝl Ñiño", encoding='utf-8'),
            "password_confirmed": unicode("Ḝl Ñiño", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert form.is_valid()

    def test_passwords_unequal(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "07700 900000",
            "password": unicode("Ḝl Ñiño", encoding='utf-8'),
            "password_confirmed": unicode("Ḝl Ñiñoñ", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_pick_up_time_past(self):
        data = {
            "time_slot": "2015-01-04 08",
            "calendar_grid": get_calendar(is_pick_up_time=True, out_code='w1')
        }

        form = PickUpTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_pick_up_time_future(self):
        data = {
            "time_slot": "2015-06-04 08",
            "calendar_grid": get_calendar(is_pick_up_time=True, out_code='w1')
        }

        form = PickUpTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_pick_up_time_taken(self):
        pick_up_time = datetime.datetime(2015, 1, 5, 14, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=pick_up_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        data = {
            "time_slot": "2015-01-05 14",
            "calendar_grid": get_calendar(is_pick_up_time=True, out_code='w1')
        }

        form = PickUpTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_pick_up_time_valid(self):
        data = {
            "time_slot": "2015-01-07 08",
            "calendar_grid": get_calendar(is_pick_up_time=True, out_code='w1')
        }

        form = PickUpTimeForm(data)
        assert form.is_valid()

    @freeze_time("2014-05-05 10:00:00")
    def test_pick_up_time_taken_BST(self):
        pick_up_time = datetime.datetime(2014, 5, 5, 14, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=pick_up_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        data = {
            "time_slot": "2015-01-05 15",
            "calendar_grid": get_calendar(is_pick_up_time=True, out_code='w1')
        }

        form = PickUpTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_drop_off_time_past(self):
        pick_up_time = datetime.datetime(2015, 1, 7, 14, tzinfo=pytz.utc)
        data = {
            "time_slot": "2015-01-04 08",
            "calendar_grid": get_calendar(False, out_code='w1',
                                          pick_up_time=pick_up_time)
        }

        form = DeliveryTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_drop_off_time_future(self):
        pick_up_time = datetime.datetime(2015, 1, 7, 14, tzinfo=pytz.utc)
        data = {
            "time_slot": "2015-06-04 08",
            "calendar_grid": get_calendar(False, out_code='w1',
                                          pick_up_time=pick_up_time)
        }

        form = DeliveryTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_drop_off_time_taken(self):
        pick_up_time = datetime.datetime(2015, 1, 5, 14, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 10, 14, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=drop_off_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        data = {
            "time_slot": "2015-01-10 14",
            "calendar_grid": get_calendar(False, out_code='w1',
                                          pick_up_time=pick_up_time)
        }

        form = DeliveryTimeForm(data)
        assert not form.is_valid()

    @freeze_time("2015-01-05 10:00:00")
    def test_drop_off_time_valid(self):
        pick_up_time = datetime.datetime(2015, 1, 5, 14, tzinfo=pytz.utc)
        data = {
            "time_slot": "2015-01-08 08",
            "calendar_grid": get_calendar(False, out_code='w1',
                                          pick_up_time=pick_up_time)
        }

        form = DeliveryTimeForm(data)
        assert form.is_valid()

    @freeze_time("2014-05-01 10:00:00")
    def test_drop_off_time_taken_BST(self):
        pick_up_time = datetime.datetime(2014, 5, 1, 14, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 5, 5, 14, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(
            appointment=drop_off_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        data = {
            "time_slot": "2015-01-05 15",
            "calendar_grid": get_calendar(False, out_code='w1',
                                          pick_up_time=pick_up_time)
        }

        form = DeliveryTimeForm(data)
        assert not form.is_valid()

    def test_items_added(self):
        item = ItemFactory(price=Decimal('17.20'))
        [ItemAndQuantityFactory(quantity=4, item=item)]

        data = {
            "quantity-{}".format(item.pk): "2",
        }
        form = ItemsAddedForm(data)
        assert form.is_valid()

    def test_mobile_number_invalid(self):
        data = {
            "email_address": "test@wishiwashi.com",
            "mobile_number": "--",
            "password": unicode("ĶliAs0ĭ", encoding='utf-8'),
            "password_confirmed": unicode("ķliaS0ĭ", encoding='utf-8'),
            "terms": "On"
        }
        form = CreateAccountForm(data)
        assert not form.is_valid()
        errors = form.errors.as_data()
        assert errors['mobile_number'][0].code == 'invalid'

