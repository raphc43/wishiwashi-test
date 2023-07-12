# -*- coding: utf-8 -*-
from decimal import Decimal
import datetime
from importlib import import_module
import uuid

from dateutil.parser import parse
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages import constants as MSG
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.messages.middleware import MessageMiddleware
from django.core.urlresolvers import NoReverseMatch, reverse
from django.test import TestCase
from django.test.client import Client, RequestFactory
from django.utils import timezone
from freezegun import freeze_time
import pytz
import ujson as json

from bookings.models import (Address, Item, ItemAndQuantity,
                             OutCodeNotServed, Order)
from bookings.factories import (AddressFactory, OrderFactory, ItemFactory,
                                ItemAndQuantityFactory, UserFactory,
                                VoucherFactory,
                                TrackConfirmedOrderSlotsFactory)
from bookings.calendar import get_calendar
from bookings.views import (address, items_to_clean, items_added,
                            delivery_time as delivery_time_page,
                            pick_up_time_page, landing)
from payments.views import landing as payment_landing
from payments.utils import vat_cost
from customer_service.models import UserProfile


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


class Views(TestCase):
    fixtures = ['test_outcodes', 'test_vendor', 'test_categories_and_items']

    def setUp(self):
        settings.SESSION_ENGINE = 'django.contrib.sessions.backends.db'
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.session = store
        self.client = Client()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

        super(Views, self).setUp()

    def _populate_session(self, session_data):
        """
        :param dict session_data: keys and values to set in the session
        """
        _session = self.client.session

        for _key, _value in session_data.iteritems():
            _session[_key] = _value

        _session.save()
        self.client.session.save()

    def _create_and_login_user(self):
        self.user = User.objects.create_user(username=str(uuid.uuid4())[:28],
                                             email='test@test.com',
                                             password='testing123')
        logged_in = self.client.login(username=self.user.username,
                                      password='testing123')
        self.assertTrue(logged_in)

    def test_landing(self):
        resp = self.client.get(reverse('landing'))
        self.assertEqual(resp.status_code, 200)

    def test_landing_post_valid_served_postcode(self):
        self.client.get(reverse('landing')) # Generate session
        resp = self.client.post(reverse('landing'), {'postcode': 'W1'})
        self.assertRedirects(resp,
                             reverse('bookings:pick_up_time'),
                             status_code=302,
                             target_status_code=200)

    def test_landing_post_valid_served_full_postcode(self):
        self.client.get(reverse('landing')) # Generate session
        resp = self.client.post(reverse('landing'), {'postcode': 'SW16 3QQ'})
        self.assertRedirects(resp,
                             reverse('bookings:pick_up_time'),
                             status_code=302,
                             target_status_code=200)

    def test_landing_post_valid_unserved_postcode(self):
        self.client.get(reverse('landing')) # Generate session
        resp = self.client.post(reverse('landing'), {'postcode': 'NW1'})
        self.assertRedirects(resp, '%s?postcode=nw1' %
                                   reverse('bookings:postcode_not_served'),
                             status_code=302,
                             target_status_code=200)

    def test_landing_post_invalid_postcode(self):
        self.client.get(reverse('landing')) # Generate session
        resp = self.client.post(reverse('landing'), {'postcode': 'AAA'})
        self.assertEqual(resp.status_code, 200, str(resp))
        self.assertFormError(resp,
                             'form',
                             'postcode',
                             [u'Postcode is invalid'])

    def test_s11_should_not_throw_except(self):
        self.client.get(reverse('landing')) # Generate session
        resp = self.client.post(reverse('landing'), {'postcode': 's11 7ty'})
        self.assertEqual(resp.status_code, 200, str(resp))
        self.assertFormError(resp,
                             'form',
                             'postcode',
                             [u'Postcode is invalid'])

    def test_valid_postcodes(self):
        """
        The postcode can be either an out-code or and out-code and in-code
        """
        valid_postcodes = ('w1', 'nw1 1aa', 'w1 1aa', 'wc1a1aa')

        for postcode in valid_postcodes:
            resp = self.client.get(reverse('bookings:valid_postcode', kwargs={'postcode': postcode}))
            resp = json.loads(resp.content)
            self.assertTrue('is_valid' in str(resp) and resp['is_valid'], resp)

    def test_invalid_postcode(self):
        invalid_postcodes = ('123', 'london')

        for postcode in invalid_postcodes:
            resp = self.client.get(reverse('bookings:valid_postcode', kwargs={'postcode': postcode}))
            resp = json.loads(resp.content)
            self.assertTrue('is_valid' in str(resp) and resp['is_valid'] is False, '%s for %s' % (resp, postcode))

    def test_invalid_postcode_no_reverse_url(self):
        no_reverse_url = ('', None, 1234,)

        for postcode in no_reverse_url:
            try:
                self.client.get(reverse('bookings:valid_postcode'))
                self.fail('Expected NoReverseMatch', postcode)
            except NoReverseMatch:
                self.assertTrue(True)

    def test_prices(self):
        resp = self.client.get(reverse('bookings:prices'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('&pound;', resp.content)

    def test_prices_on_mobile(self):
        resp = self.client.get(reverse('bookings:prices'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('&pound;', resp.content)

    def test_pick_up_time_missing_session_data(self):
        resp = self.client.get(reverse('bookings:pick_up_time'))
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

    def test_pick_up_time_missing_postcode(self):
        resp = self.client.get(reverse('bookings:pick_up_time'))
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 10:00:00")
    def test_pick_up_time_valid_postcode(self):
        self._populate_session({'postcode': 'w1 1aa', 'out_code': 'w1'})

        resp = self.client.get(reverse('bookings:pick_up_time'))
        self.assertEqual(resp.status_code, 200)

        # Pick a time
        resp = self.client.post(reverse('bookings:pick_up_time'), {
            'time_slot': '2015-01-06 10',
        })
        self.assertRedirects(resp,
                             reverse('bookings:delivery_time'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 10:00:00")
    def test_pick_up_time_invalid_time_slot(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
        })

        resp = self.client.post(reverse('bookings:pick_up_time'), {
            'time_slot': '0000-00-00 10',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'time_slot',
                             [u'Time slot is invalid'])

    @freeze_time('2015-01-20 13:20') # Tuesday
    def test_user_cannot_select_unavailable_pick_up_time(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
        })

        resp = self.client.post(reverse('bookings:pick_up_time'), {
            'time_slot': '2015-01-20 10',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'time_slot',
                             [u'Time slot is not available'])

    @freeze_time('2015-04-04 10:20') # Saturday
    def test_user_cannot_select_unavailable_pick_up_time_bank_holiday(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
        })

        resp = self.client.post(reverse('bookings:pick_up_time'), {
            'time_slot': '2015-04-06 10', # 6th April 2015 (Monday bank holiday)
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'time_slot',
                             [u'Time slot is not available'])

    @freeze_time('2015-04-04 10:20') # Saturday
    def test_user_can_select_available_pick_up_time_same_day(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
        })

        resp = self.client.post(reverse('bookings:pick_up_time'), {
            'time_slot': '2015-04-04 14',
        })
        self.assertRedirects(resp,
                             reverse('bookings:delivery_time'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-06 10:00:00")
    def test_delivery_time(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 15',
        })

        resp = self.client.get(reverse('bookings:delivery_time'))
        self.assertEqual(resp.status_code, 200)

        # Pick a time
        resp = self.client.post(reverse('bookings:delivery_time'), {
            'time_slot': '2015-01-09 10',
        })
        self.assertRedirects(resp,
                             reverse('bookings:items_to_clean'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 10:00:00")
    def test_delivery_time_session_persistence(self):
        """
            January 2015
        Su Mo Tu We Th Fr Sa
                     1  2  3
         4  5  6  7  8  9 10
        11 12 13 14 15 16 17
        18 19 20 21 22 23 24
        25 26 27 28 29 30 31
        """
        test_values = (
            ('2015-01-09 10', 0, 4),
            ('2015-01-10 10', 0, 5),
            # 2015-01-11 Sunday
            ('2015-01-12 10', 1, 6),
            ('2015-01-13 10', 1, 7),
            ('2015-01-14 10', 1, 8),
            ('2015-01-15 10', 1, 9),
            ('2015-01-16 10', 1, 10),
            ('2015-01-17 10', 1, 11),
            # 2015-01-18 Sunday
            ('2015-01-19 10', 2, 12),
            ('2015-01-20 10', 2, 13),
            ('2015-01-21 10', 2, 14),
            ('2015-01-22 10', 2, 15),
            ('2015-01-23 10', 2, 16),
        )

        for delivery_time, selected_week, selected_day in test_values:
            self._populate_session({
                'postcode': 'w1 1aa',
                'out_code': 'w1',
                'pick_up_time': '2015-01-06 10',
                'delivery_time': delivery_time,
            })

            resp = self.client.get(reverse('bookings:delivery_time'))
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.context['selected_week'], selected_week)
            self.assertEqual(resp.context['selected_day'], selected_day)

            # Pick a time
            resp = self.client.post(reverse('bookings:delivery_time'), {
                'time_slot': '2015-01-09 10',
            })
            self.assertRedirects(resp,
                                 reverse('bookings:items_to_clean'),
                                 status_code=302,
                                 target_status_code=200)

    @freeze_time("2015-01-05 10:00:00")
    def test_delivery_time_unavilable_slot(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
        })

        resp = self.client.get(reverse('bookings:delivery_time'))
        self.assertEqual(resp.status_code, 200)

        # Pick a time
        resp = self.client.post(reverse('bookings:delivery_time'), {
            'time_slot': '2015-01-11 10', # Sunday
        })
        self.assertFormError(resp,
                             'form',
                             'time_slot',
                             [u'Time slot is not available'])

    @freeze_time("2015-01-05 10:00:00")
    def test_delivery_time_invalid_time_slot(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
        })

        resp = self.client.post(reverse('bookings:delivery_time'), {
            'time_slot': '0000-00-00 10',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'time_slot',
                             [u'Time slot is invalid'])

    @freeze_time("2015-01-05 10:00:00")
    def test_delivery_time_missing_pick_up_time(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
        })

        resp = self.client.get(reverse('bookings:delivery_time'))
        self.assertRedirects(resp,
                             reverse('bookings:pick_up_time'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 10:00:00")
    def test_delivery_time_invalid_pick_up_time(self):
        for pick_up_time in (None, '0000-00-00 00', '0000-00-00', '', 'today'):
            self._populate_session({
                'postcode': 'w1 1aa',
                'out_code': 'w1',
                'pick_up_time': pick_up_time,
            })

            resp = self.client.get(reverse('bookings:delivery_time'))
            self.assertRedirects(resp,
                                 reverse('bookings:pick_up_time'),
                                 status_code=302,
                                 target_status_code=200)

    def test_delivery_time_edge_case_days(self):
        """
        The calendar grid looks at the day of the week when deciding how to
        render out availability. The permutations below should hit each branch
        in the logic tree.
        """
        times = (
            '2015-01-02 14:00:00', # Friday, show this week
            '2015-01-02 21:00:00', # Friday, show next week
            '2015-01-03 15:00:00', # Saturday, show next week
            '2015-01-04 15:00:00', # Sunday, show next week

            # These should show their current week
            '2015-01-05 08:00:00', # Monday
            '2015-01-06 18:00:00', # Tuesday
            '2015-01-07 20:00:00', # Wednesday
            '2015-01-08 03:00:00', # Thursday

            # Block off Bank Holidays
            '2014-12-29 08:00:00', # Bank Holiday trigger
        )

        for time in times:
            with freeze_time(time):
                self._populate_session({
                    'postcode': 'w1 1aa',
                    'out_code': 'w1',
                })
                resp = self.client.get(reverse('bookings:pick_up_time'))
            self.assertEqual(resp.status_code, 200, str(resp.__dict__))

    @freeze_time('2015-01-20 13:20') # Tuesday
    def test_get_calendar_48_hour_rule(self):
        tz_london = pytz.timezone('Europe/London')
        pick_up_time = tz_london.localize(parse('2015-01-21 13'))
        resp = get_calendar(is_pick_up_time=False,
                            out_code='w1',
                            pick_up_time=pick_up_time)

        for index, date in enumerate([
            '2015-01-19', # Monday (already past)
            '2015-01-20', # Tuesday (today)
            '2015-01-21', # Wednesday (pick up day)
            '2015-01-22', # Thursday (whole day within 45 hour limit)
        ]):
            self.assertEqual(resp[index]['date'], date)
            all_false = set([slot['available']
                             for slot in resp[index]['time_slots']])
            self.assertEqual(all_false,
                             set([False]),
                             '%s has times not blocked off' % date)

        self.assertEqual(resp[4]['date'], '2015-01-23')

        availability = [(slot['hour'], slot['available'])
                        for slot in resp[4]['time_slots']]

        # pick_up_time + timedelta(hours=48)
        # datetime.datetime(2015, 1, 23, 13, 0, tzinfo=<DstTzInfo 'Europe/London' GMT0:00:00 STD>)
        self.assertEqual(availability, [('08', False),
                                        ('09', False),
                                        ('10', False),
                                        ('11', False),
                                        ('12', False),
                                        ('13', True),
                                        ('14', True),
                                        ('15', True),
                                        ('16', True),
                                        ('17', True),
                                        ('18', True),
                                        ('19', True),
                                        ('20', True),
                                        ('21', True)])

    @freeze_time('2015-01-20 13:20') # Tuesday
    def test_get_calendar_6_day_rule(self):
        calendar_grid = get_calendar(is_pick_up_time=True,
                                     out_code='w1')

        check_list = (
            ('2015-01-19', [(8, False), (9, False), (10, False), (11, False),
                            (12, False), (13, False), (14, False), (15, False),
                            (16, False), (17, False), (18, False), (19, False),
                            (20, False), (21, False)]),
            ('2015-01-20', [(8, False), (9, False), (10, False), (11, False),
                            (12, False), (13, False), (14, False), (15, False),
                            # at 17 they can pick time slots but at 20 there
                            # are no vendors available. There are other days
                            # where there are opening times at 20 so this entry
                            # appears to balance this day's length of slots
                            # with the other days
                            (16, True), (17, True), (18, True), (19, True),
                            (20, True), (21, True)]),
            ('2015-01-21', [(8, True), (9, True), (10, True), (11, True),
                            (12, True), (13, True), (14, True), (15, True),
                            (16, True), (17, True), (18, True), (19, True),
                            (20, True), (21, True)]),
            ('2015-01-22', [(8, True), (9, True), (10, True), (11, True),
                            (12, True), (13, True), (14, True), (15, True),
                            (16, True), (17, True), (18, True), (19, True),
                            (20, True), (21, True)]),
            ('2015-01-23', [(8, True), (9, True), (10, True), (11, True),
                            (12, True), (13, True), (14, True), (15, True),
                            (16, True), (17, True), (18, True), (19, True),
                            (20, True), (21, True)]),
            # Saturday partial opening
            ('2015-01-24', [(8, True), (9, True), (10, True), (11, True),
                            (12, True), (13, True), (14, True), (15, True),
                            (16, True), (17, False), (18, False), (19, False),
                            (20, False), (21, False)]),
            ('2015-01-26', [(8, True), (9, True), (10, True), (11, True),
                            # from 14 onward the six-day limit has past so
                            # no more time slots should be available for pick
                            # up
                            (12, True), (13, True), (14, False), (15, False),
                            (16, False), (17, False), (18, False), (19, False),
                            (20, False), (21, False)])
        )

        for day_index, day in enumerate(calendar_grid):
            if day_index < len(check_list):
                self.assertEqual(check_list[day_index][0], day['date'])
                availability = [(int(timeslot['hour']), timeslot['available'])
                                for timeslot in day['time_slots']]
                self.assertEqual(availability, check_list[day_index][1])
            else:
                availability = set([(timeslot['available'])
                                    for timeslot in day['time_slots']])
                self.assertEqual(availability, set([False]), day)

    @freeze_time('2015-04-12 13:20') # Sunday
    def test_get_calendar_sunday_no_bookings_till_monday_at_earliest_am(self):
        calendar_grid = get_calendar(is_pick_up_time=True, out_code='w1')
        for slot in calendar_grid[0]['time_slots']:
            if int(slot['hour']) < 9:
                self.assertFalse(slot['available'])
            else:
                self.assertTrue(slot['available'])

        self.assertEqual(calendar_grid[0]['date'], '2015-04-13')
        self.assertEqual(calendar_grid[0]['time_slots'][1]['hour'], '09')
        self.assertTrue(calendar_grid[0]['time_slots'][1]['available'])

    @freeze_time('2015-04-13 18:20') # Monday
    def test_get_calendar_monday_eve_no_bookings_till_tuesday_at_earliest_am(self):
        calendar_grid = get_calendar(is_pick_up_time=True, out_code='w1')
        for slot in calendar_grid[1]['time_slots']:
            if int(slot['hour']) < 9:
                self.assertFalse(slot['available'])
            else:
                self.assertTrue(slot['available'])

        self.assertEqual(calendar_grid[1]['date'], '2015-04-14')
        self.assertEqual(calendar_grid[1]['time_slots'][1]['hour'], '09')
        self.assertTrue(calendar_grid[1]['time_slots'][1]['available'])

    @freeze_time('2015-04-14 03:00') # Tuesday
    def test_get_calendar_tuesday_morning_no_bookings_till_earliest_am(self):
        calendar_grid = get_calendar(is_pick_up_time=True, out_code='w1')
        for slot in calendar_grid[1]['time_slots']:
            if int(slot['hour']) < 9:
                self.assertFalse(slot['available'])
            else:
                self.assertTrue(slot['available'])

        self.assertEqual(calendar_grid[1]['date'], '2015-04-14')
        self.assertEqual(calendar_grid[1]['time_slots'][1]['hour'], '09')
        self.assertTrue(calendar_grid[1]['time_slots'][1]['available'])

    def test_valid_postcode_not_served(self):
        # Check landing page loads
        url = '%s?postcode=SW7%%201AA' % \
              reverse('bookings:postcode_not_served')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        # Check email address validation
        resp = self.client.post(url, {
            'out_code': 'sw7',
            'email_address': 'invalid email address',
        })
        self.assertEqual(resp.status_code, 200)

        # Valid email address and out code posted
        email_address = 'test@test.com'
        out_code = 'sw7'

        resp = self.client.post(url, {
            'out_code': out_code,
            'email_address': email_address,
        })
        self.assertRedirects(resp,
                             reverse('bookings:notify_when_postcode_served',
                                     kwargs={'postcode': 'sw7 1aa'}),
                             status_code=302,
                             target_status_code=200)

        record = OutCodeNotServed.objects.filter(email_address=email_address,
                                                 out_code=out_code)[0]
        self.assertEqual(record.email_address, email_address)
        self.assertEqual(record.out_code, out_code)

    def test_postcode_not_served_bad_postcode(self):
        url = '%s?postcode=SW7%%201AA' % \
              reverse('bookings:postcode_not_served')
        form = {
            'out_code': 'FAKE',
            'email_address': 'test@test.com',
        }
        resp = self.client.post(url, form)
        self.assertFormError(resp,
                             'form',
                             'out_code',
                             [u'Postcode out code is invalid'])

    def test_postcode_not_served_no_postcode(self):
        resp = self.client.get(reverse('bookings:postcode_not_served'))
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

    def test_notify_when_postcode_served(self):
        resp = self.client.get(reverse('bookings:notify_when_postcode_served',
                                       kwargs={'postcode': 'SW71AA'}))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-10 18',
        })

        resp = self.client.get(reverse('bookings:items_to_clean'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean_invalid_delivery_time(self):
        for _time in (None, '0000-00-00 00', '0000-00-00', '', 'today'):
            self._populate_session({
                'postcode': 'w1 1aa',
                'out_code': 'w1',
                'pick_up_time': '2015-01-06 10',
                'delivery_time': _time,
            })

            resp = self.client.get(reverse('bookings:items_to_clean'))
            self.assertRedirects(resp,
                                 reverse('bookings:delivery_time'),
                                 status_code=302,
                                 target_status_code=200)

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean_valid_order(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
        })

        resp = self.client.post(reverse('bookings:items_to_clean'), {
            'quantity-26': '10', # 10 Ties
            'quantity-27': '5', # 5 Scarves
            'selected_category': 1,
        })

        # TODO if they are logged in then they should go to the address page
        self.assertRedirects(resp,
                             reverse('registration:create_account'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean_valid_order_bad_items(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
        })

        resp = self.client.post(reverse('bookings:items_to_clean'), {
            'quantity-26': '10', # 10 Ties
            'quantity-27': '5', # 5 Scarves
            'quantity-': 'abc', # 5 Scarves
            'quantity-a-a-5': '5', # 5 Scarves
            'selected_category': 1,
        })

        # TODO if they are logged in then they should go to the address page
        self.assertRedirects(resp,
                             reverse('registration:create_account'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean_order_too_expensive(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
        })

        resp = self.client.post(reverse('bookings:items_to_clean'), {
            'quantity-40': '25', # £16
            'quantity-41': '25', # £18
            'quantity-42': '25', # £21
            'selected_category': 1,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             '__all__',
                             [u'For an order of this size you must contact our Customer Care team.'])

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean_order_too_many_items(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
        })

        resp = self.client.post(reverse('bookings:items_to_clean'), {
            'quantity-2': '25', # £2.25
            'quantity-3': '25', # £2.75
            'quantity-4': '25', # £2.75
            'quantity-5': '25', # £5
            'quantity-6': '25', # £3.75
            'quantity-7': '25', # £5
            'quantity-1': '25', # £5.50
            'selected_category': 1,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             '__all__',
                             [u'You can not have more than 150 items in your basket.'])

    def test_login_email_address(self):
        url = reverse('bookings:login')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')
        context = {
            'email_address': user.email,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)

        # They don't have any existing orders so there is no postcode to use
        # so they should be directed to the landing page
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)
        self.assertIn('_session_key', self.client.session.__dict__)

        # If they go to the bookings page and they are already logged in then
        # they shouldn't be presented to login again
        resp = self.client.get(reverse('bookings:login'))
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

        url = '%s?next=%s' % (reverse('bookings:login'),
                              reverse('terms'))
        resp = self.client.get(url)
        self.assertRedirects(resp,
                             reverse('terms'),
                             status_code=302,
                             target_status_code=200)

    def test_login_mobile_number(self):
        url = reverse('bookings:login')

        mobile_number = '+44 (0)7700 123 456'
        mobile_number_normalised = '00447700123456'

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')

        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        context = {
            'email_address': mobile_number,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)

        # They don't have any existing orders so there is no postcode to use
        # so they should be directed to the landing page
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)
        self.assertIn('_session_key', self.client.session.__dict__)

    def test_login_mobile_number_inactive_account(self):
        url = reverse('bookings:login')

        mobile_number = '+44 (0)7700 123 456'
        mobile_number_normalised = '00447700123456'

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')
        user.is_active = False
        user.save()

        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        context = {
            'email_address': mobile_number,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u"Your account has been disabled"])

    def test_login_mobile_number_bad_password(self):
        url = reverse('bookings:login')

        mobile_number = '+44 (0)7700 123 456'
        mobile_number_normalised = '00447700123456'

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')

        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        context = {
            'email_address': mobile_number,
            'password': 'testing12',
        }
        resp = self.client.post(url, context)
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u"Your login and password did not match"])

    def test_login_mobile_number_missing_profile(self):
        url = reverse('bookings:login')

        mobile_number = '+44 (0)7700 123 456'

        User.objects.create_user(username=str(uuid.uuid4())[:28],
                                 email='%s@test.com' % str(uuid.uuid4()),
                                 password='testing123')

        context = {
            'email_address': mobile_number,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u'Unable to locate email address or mobile number.'])

    def test_login_mobile_number_non_british(self):
        url = reverse('bookings:login')

        mobile_number = '+372 5123 4567'
        mobile_number_normalised = '003725123456'

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')

        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        context = {
            'email_address': mobile_number,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u'Unable to locate email address or mobile number.'])

    def test_login_mobile_number_non_mobile(self):
        url = reverse('bookings:login')

        mobile_number = '+44 0207 846 1234'
        mobile_number_normalised = '00442078461234'

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')

        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        context = {
            'email_address': mobile_number,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)
        self.assertFormError(resp,
                             'form',
                             'password',
                             [u'Unable to locate email address or mobile number.'])

    @freeze_time("2015-01-05 13:30:00")
    def test_login_mobile_number_postcode_known(self):
        url = reverse('bookings:login')

        mobile_number = '+44 (0)7700 123 456'
        mobile_number_normalised = '00447700123456'

        user = User.objects.create_user(username=str(uuid.uuid4())[:28], email='%s@test.com' % str(uuid.uuid4()),
                                        password='testing123')

        profile = UserProfile(user=user, mobile_number=mobile_number_normalised)
        profile.save()

        # Create a fake order with a valid postcode
        addr = Address(flat_number_house_number_building_name='1',
                       address_line_1='High Road',
                       town_or_city='London',
                       postcode='w11aa')
        addr.save()

        order = Order(pick_up_and_delivery_address=addr,
                      pick_up_time='2015-01-07T10:00:00Z',
                      drop_off_time='2015-01-10T18:00:00Z',
                      customer=user)
        order.save()

        context = {
            'email_address': mobile_number,
            'password': 'testing123',
        }
        resp = self.client.post(url, context)

        # They don't have any existing orders so there is no postcode to use
        # so they should be directed to the landing page
        self.assertRedirects(resp,
                             reverse('bookings:pick_up_time'),
                             status_code=302,
                             target_status_code=200)
        self.assertIn('_session_key', self.client.session.__dict__)

        # Test logout
        resp = self.client.get(reverse('bookings:logout'))
        self.assertRedirects(resp,
                             reverse('landing'),
                             status_code=302,
                             target_status_code=200)

    def test_login_bad_credentials(self):
        url = reverse('bookings:login')
        payload = {
            'email_address': 'fake@email.address',
            'password': 'wrong password',
        }
        resp = self.client.post(url, payload)
        self.assertEqual(resp.status_code, 200)

    def _setup_valid_address_session(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5, 2: 3},
        })
        self._create_and_login_user()

    @freeze_time("2015-01-05 13:30:00")
    def test_address(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-05 13:30:00")
    def test_address_missing_items(self):
        url = reverse('bookings:address')
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
        })
        self._create_and_login_user()

        resp = self.client.get(url)
        self.assertRedirects(resp,
                             reverse('bookings:items_to_clean'),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 13:30:00")
    def test_address_not_logged_in(self):
        url = reverse('bookings:address')
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        resp = self.client.get(url)
        self.assertRedirects(resp,
                             '%s?next=%s' % (reverse('bookings:login'),
                                             reverse('bookings:address')),
                             status_code=302,
                             target_status_code=200)

    @freeze_time("2015-01-05 13:30:00")
    def test_address_submit_form_no_entries(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        form_errors = (
            ('first_name', [u'This field is required.']),
            ('last_name', [u'This field is required.']),
            ('flat_number_house_number_building_name',
                [u'This field is required.']),
            ('address_line_1', [u'This field is required.']),
            ('postcode', [u'This field is required.']),
        )

        for _field, _error_msg in form_errors:
            self.assertFormError(resp, 'form', _field, _error_msg)

    @freeze_time("2015-01-05 13:30:00")
    def test_address_bad_first_name(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        for first_name in ('    ', '      ', 'Litwintschik 123', '----'):
            form = {
                'first_name': first_name,
                'last_name': 'Litwintschik',
                'flat_number_house_number_building_name': '1',
                'address_line_1': 'High Road',
                'postcode': 'w1 1aa',
            }

            resp = self.client.post(url, form)
            self.assertEqual(resp.status_code, 200)
            self.assertFormError(resp,
                                 'form',
                                 'first_name',
                                 [u'Please enter your first name'])

    @freeze_time("2015-01-05 13:30:00")
    def test_address_bad_last_name(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        for last_name in ('    ', '      ', 'Litwintschik 123', '----'):
            form = {
                'first_name': 'Mark',
                'last_name': last_name,
                'flat_number_house_number_building_name': '1',
                'address_line_1': 'High Road',
                'postcode': 'w1 1aa',
            }

            resp = self.client.post(url, form)
            self.assertFormError(resp,
                                 'form',
                                 'last_name',
                                 [u'Please enter your last name'])

    @freeze_time("2015-01-05 13:30:00")
    def test_address_bad_address_line_1(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        form = {
            'first_name': 'A. B.',
            'last_name': 'Võeti Võimaliku-Viljandi',
            'flat_number_house_number_building_name': '1',
            'address_line_1': 'aaa',
            'postcode': 'w1 1aa',
        }

        resp = self.client.post(url, form)
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             'address_line_1',
                             [u'Ensure this value has at least 4 characters (it has 3).'])

    @freeze_time("2015-01-05 13:30:00")
    def test_address_bad_postcode(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        postcodes = (
            ('w1', [u'Please enter your full postcode']),
            ('w1 1a', [u'Please enter your full postcode.']),
            ('nw1 1aa', [u'We do not currently serve the NW1 postcode area']),
            ('London', [u'Please enter your full postcode.']),
            ('10104', [u'Please enter your full postcode.']),
            (10104, [u'Please enter your full postcode.']),
            ('', [u'This field is required.']),
            # EX1 isn't in the test fixtures on purpose so this sort of test
            # can be written
            ('EX11AA', [u'Please enter your full postcode.']),
            ('s11 7ty', [u'Please enter your full postcode.']),
        )

        for postcode, error_msg in postcodes:
            form = {
                'first_name': 'A. B.',
                'last_name': 'Võeti Võimaliku-Viljandi',
                'flat_number_house_number_building_name': '1',
                'address_line_1': 'High Road',
                'postcode': postcode,
            }

            resp = self.client.post(url, form)
            self.assertEqual(resp.status_code, 200)
            self.assertFormError(resp, 'form', 'postcode', error_msg)

    @freeze_time("2015-01-05 13:30:00")
    def test_address_submit_valid_form(self):
        url = reverse('bookings:address')
        self._setup_valid_address_session()

        form = {
            'first_name': 'A. B.',
            'last_name': 'Võeti Võimaliku-Viljandi',
            'flat_number_house_number_building_name': '1',
            'address_line_1': 'High Road',
            'postcode': 'w1 1aa',
        }

        resp = self.client.post(url, form)
        self.assertRedirects(resp,
                             # TODO this redirect will go to the payment page
                             # when we implement it
                             reverse('payments:landing'),
                             status_code=302,
                             target_status_code=200)
        order = Order.objects.all()[0]
        self.assertEqual(order.total_price_of_order, Decimal('101.75'))

    def test_enforcing_postcode_normalisation(self):
        addr = Address()
        # If there is no postcode then it should allow the address record to
        # save
        addr.save()
        addr.postcode = 'nw6'

        try:
            addr.save()
            self.fail('An AssertionError should have been raised')
        except AssertionError:
            self.assertTrue(True)

        try:
            addr.postcode = 'nw6 7xu'
            addr.save()
            self.fail('An AssertionError should have been raised')
        except AssertionError:
            self.assertTrue(True)

        addr.postcode = 'nw67xu'
        addr.save()

    def _setup_valid_order_placed_address_session(self):
        addr = Address()
        addr.save()
        order = Order(pick_up_and_delivery_address=addr,
                      pick_up_time='2015-01-06T10:00:00Z',
                      drop_off_time='2015-01-10T18:00:00Z',
                      customer=self.user)
        order.save()

        for item_pk in (1, 2):
            item = Item.objects.get(pk=item_pk)
            item_quantity = ItemAndQuantity()
            item_quantity.item = item
            item_quantity.quantity = 2
            item_quantity.price = item.price * 2
            item_quantity.save()
            order.items.add(item_quantity)
            # Bake price in
            order.total_price_of_order = order.total_price_of_order + item_quantity.price

        order.price_excluding_vat_charge = vat_cost(order.total_price_of_order)["ex_vat"]
        order.vat_charge = vat_cost(order.total_price_of_order)["vat"]
        order.save()
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
            'items': {1: 2, 2: 2},
            'address': addr.pk,
            'order': order.pk
        })

    def test_order_placed(self):
        self._create_and_login_user()
        self._setup_valid_order_placed_address_session()

        session_fields = ('postcode', 'out_code', 'pick_up_time',
                          'delivery_time', 'items', 'address')

        for field in session_fields:
            self.assertTrue(len(str(self.client.session[field])) > 0)

        old_session_key = self.client.session.session_key

        resp = self.client.get(reverse('bookings:order_placed'))
        self.assertEqual(resp.status_code, 200)

        for field in session_fields:
            self.assertFalse(field in self.client.session.keys())

        new_session_key = self.client.session.session_key
        self.assertNotEqual(old_session_key, new_session_key)
        self.assertTrue(len(old_session_key) > 10, old_session_key)
        self.assertTrue(len(old_session_key) > 10, new_session_key)

        self.assertEqual(resp.context['grand_total_net_vat'], Decimal('35.42'))
        self.assertEqual(resp.context['vat'], Decimal('7.08'))
        self.assertEqual(resp.context['items'][0]['unit_price'], Decimal('15.83'))
        self.assertEqual(resp.context['items'][0]['quantity'], 2)
        self.assertEqual(resp.context['items'][1]['unit_price'], Decimal('1.88'))
        self.assertEqual(resp.context['items'][1]['quantity'], 2)

        self.assertContains(resp, '_addTrans', count=1)
        self.assertContains(resp, '_addItem', count=2)

    @freeze_time("2015-04-13 10:00:00")
    def test_all_data_exists_in_order(self):
        self.client.get(reverse('landing')) # Generate session

        # Landing page
        resp = self.client.post(reverse('landing'), {'postcode': 'W1'})
        self.assertRedirects(resp,
                             reverse('bookings:pick_up_time'),
                             status_code=302,
                             target_status_code=200)

        # Pick up time
        resp = self.client.post(reverse('bookings:pick_up_time'), {
            'time_slot': '2015-04-15 10',
        })
        self.assertRedirects(resp,
                             reverse('bookings:delivery_time'),
                             status_code=302,
                             target_status_code=200)

        # Delivery time
        resp = self.client.post(reverse('bookings:delivery_time'), {
            'time_slot': '2015-04-17 16',
        })
        self.assertRedirects(resp,
                             reverse('bookings:items_to_clean'),
                             status_code=302,
                             target_status_code=200)

        # Items to clean
        resp = self.client.post(reverse('bookings:items_to_clean'), {
            'quantity-26': '10', # 10 Ties
            'quantity-27': '5', # 5 Scarves
            'selected_category': 1,
        })

        self.assertRedirects(resp,
                             reverse('registration:create_account'),
                             status_code=302,
                             target_status_code=200)

        # Create account
        resp = self.client.post(reverse('registration:create_account'), {
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

        # Supply address
        form = {
            'first_name': 'A. B.',
            'last_name': 'Võeti Võimaliku-Viljandi',
            'flat_number_house_number_building_name': '123-5',
            'address_line_1': 'High Road',
            'address_line_2': 'Line 2',
            'postcode': 'w1 1aa',
        }

        resp = self.client.post(reverse('bookings:address'), form)
        self.assertRedirects(resp,
                             # TODO this redirect will go to the payment page
                             # when we implement it
                             reverse('payments:landing'),
                             status_code=302,
                             target_status_code=200)

        order = Order.objects.all().order_by('-pk')[0]
        self.assertEqual(order.assigned_to_vendor, None)
        self.assertEqual(order.authorisation_status,
                         Order.NOT_ATTEMPTED_AUTHORISATION)
        self.assertEqual(order.card_charged_status, Order.NOT_CHARGED)
        self.assertEqual(order.charge_back_status, Order.NOT_CHARGED_BACK)
        self.assertEqual(order.order_status, Order.UNCLAMIED_BY_VENDORS)
        self.assertEqual(order.refund_status, Order.NOT_REFUNDED)
        self.assertEqual(order.total_price_of_order, Decimal('60.00'))
        self.assertEqual(order.placed_time, None)
        self.assertEqual(order.placed, False)
        self.assertEqual(order.voucher_id, None)
        self.assertTrue(len(order.uuid) >= 6, order.uuid)

        self.assertTrue(order.customer.first_name, 'A. B.')
        self.assertTrue(order.customer.last_name, 'Võeti Võimaliku-Viljandi')
        self.assertTrue(order.customer.email, 'mark@wishiwashi.com')
        self.assertEqual(order.customer.is_active, True)
        self.assertEqual(order.customer.is_staff, False)
        self.assertEqual(order.customer.is_superuser, False)

        self.assertTrue(len(order.customer.username) ==
                        len('d9c35c5e-4955-4cea-b9a7-e927'),
                        order.customer.username)

        self.assertEqual(str(order.customer.date_joined),
                         '2015-04-13 10:00:00+00:00')
        self.assertEqual(str(order.created),
                         '2015-04-13 10:00:00+00:00')
        self.assertEqual(str(order.modified),
                         '2015-04-13 10:00:00+00:00')

        self.assertEqual(str(order.pick_up_time),
                         '2015-04-15 09:00:00+00:00')
        self.assertEqual(str(order.drop_off_time),
                         '2015-04-17 15:00:00+00:00')

        self.assertEqual(order.pick_up_and_delivery_address.address_line_1,
                         'High Road')
        self.assertEqual(order.pick_up_and_delivery_address.address_line_2,
                         'Line 2')
        self.assertEqual(order.pick_up_and_delivery_address.
                         flat_number_house_number_building_name, '123-5')
        self.assertEqual(order.pick_up_and_delivery_address.
                         instructions_for_delivery, '')
        self.assertEqual(order.pick_up_and_delivery_address.postcode, 'w11aa')
        self.assertEqual(order.pick_up_and_delivery_address.town_or_city,
                         'London')

        profile = UserProfile.objects.get(user=order.customer)

        self.assertEqual(profile.mobile_number, '00447752123456')

        self.assertEqual(order.items.all().count(), 2)

        items = order.items.all().order_by('item__pk')
        self.assertEqual(items[0].item.pk, 26)
        self.assertEqual(items[0].quantity, 10)
        self.assertEqual(items[1].item.pk, 27)
        self.assertEqual(items[1].quantity, 5)

    @freeze_time("2015-01-05 13:30:00")
    def test_pick_up_time_invalidated(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 13',
        })

        resp = self.client.post(reverse('bookings:delivery_time'), {
            'time_slot': '0000-00-00 10',
        })
        self.assertRedirects(resp, reverse('bookings:pick_up_time'))

    @freeze_time("2015-01-05 13:30:00")
    def test_pick_up_time_invalidated_session_removed(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 14',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        resp = self.client.get(reverse('registration:create_account'), follow=True)
        self.assertRedirects(resp, reverse('bookings:pick_up_time'))
        self.assertTrue('pick_up_time' not in self.client.session)
        self.assertTrue('delivery_time' not in self.client.session)
        messages = list(resp.context['messages'])
        self.assertEqual(messages[0].level, MSG.ERROR)
        self.assertTrue("session expired" in str(messages[0]))

    @freeze_time("2014-03-27 10:00:00")
    def test_times_valid_crossing_daylight_saving(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2014-03-27 18',
            'delivery_time': '2014-03-31 10',
            'items': {1: 5},
        })

        # Create account
        resp = self.client.post(reverse('registration:create_account'), {
            'email_address': 'simon@wishiwashi.com',
            'mobile_number': '+44 7750 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing123',
            'terms': 'on'
        })

        self.assertRedirects(resp,
                             reverse('bookings:address'),
                             status_code=302,
                             target_status_code=200)

        # Supply address
        form = {
            'first_name': 'A. B.',
            'last_name': 'Võeti Võimaliku-Viljandi',
            'flat_number_house_number_building_name': '123-5',
            'address_line_1': 'High Road',
            'address_line_2': 'Line 2',
            'postcode': 'w1 1aa',
        }

        resp = self.client.post(reverse('bookings:address'), form)
        self.assertRedirects(resp,
                             reverse('payments:landing'),
                             status_code=302,
                             target_status_code=200)

        order = Order.objects.all().order_by('-pk')[0]

        # 'pick_up_time': '2014-03-27 18',
        pick_up = datetime.datetime(2014, 3, 27, 18, 0, 0, 0, pytz.UTC)

        # 2014 30 March clocks go forward
        # Crossed over into British Summer time
        # 'delivery_time': '2014-03-31 10',
        drop_off = datetime.datetime(2014, 3, 31, 9, 0, 0, 0, pytz.UTC)

        self.assertEqual(order.pick_up_time, pick_up)
        self.assertEqual(order.drop_off_time, drop_off)

        tz_london = pytz.timezone("Europe/London")

        london = tz_london.localize(datetime.datetime(2014, 3, 27, 18, 0, 0))
        post_time = london + datetime.timedelta(seconds=1)
        o = Order.objects.filter(pick_up_time__lte=post_time)
        assert o.count() == 1
        self.assertTrue(order.pk, o[0].pk)

        london = tz_london.localize(datetime.datetime(2014, 3, 31, 10, 0, 0))
        pre_time = london - datetime.timedelta(seconds=1)
        o = Order.objects.filter(drop_off_time__gte=pre_time)
        assert o.count() == 1
        self.assertTrue(order.pk, o[0].pk)

    @freeze_time("2014-03-24 10:00:00")
    def test_times_valid_crossing_back_to_greenwich_mean_time(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2014-10-27 14',
            'delivery_time': '2014-10-30 10',
            'items': {1: 5},
        })

        # Create account
        resp = self.client.post(reverse('registration:create_account'), {
            'email_address': 'simon@wishiwashi.com',
            'mobile_number': '+44 7750 123 456',
            'password': 'testing123',
            'password_confirmed': 'testing123',
            'terms': 'on'
        })

        self.assertRedirects(resp,
                             reverse('bookings:address'),
                             status_code=302,
                             target_status_code=200)

        # Supply address
        form = {
            'first_name': 'A. B.',
            'last_name': 'Võeti Võimaliku-Viljandi',
            'flat_number_house_number_building_name': '123-5',
            'address_line_1': 'High Road',
            'address_line_2': 'Line 2',
            'postcode': 'w1 1aa',
        }

        resp = self.client.post(reverse('bookings:address'), form)
        self.assertRedirects(resp,
                             reverse('payments:landing'),
                             status_code=302,
                             target_status_code=200)

        order = Order.objects.all().order_by('-pk')[0]

        # 2014 26 October clocks go back
        # Crossed back into GMT
        # 'pick_up_time': '2014-10-27 14',
        pick_up = datetime.datetime(2014, 10, 27, 14, 0, 0, 0, pytz.UTC)

        # 'delivery_time': '2014-10-30 10',
        drop_off = datetime.datetime(2014, 10, 30, 10, 0, 0, 0, pytz.UTC)

        self.assertEqual(order.pick_up_time, pick_up)
        self.assertEqual(order.drop_off_time, drop_off)

        tz_london = pytz.timezone("Europe/London")

        london = tz_london.localize(datetime.datetime(2014, 10, 27, 14, 0, 0))
        post_time = london + datetime.timedelta(seconds=1)
        o = Order.objects.filter(pick_up_time__lte=post_time)
        assert o.count() == 1
        self.assertTrue(order.pk, o[0].pk)

        london = tz_london.localize(datetime.datetime(2014, 10, 30, 10, 0, 0))
        pre_time = london - datetime.timedelta(seconds=1)
        o = Order.objects.filter(drop_off_time__gte=pre_time)
        assert o.count() == 1
        self.assertTrue(order.pk, o[0].pk)

    @freeze_time("2015-01-05 10:00:00")
    def test_address_resubmission_existing_order_reused(self):
        _user = UserFactory()
        _address = AddressFactory(
            flat_number_house_number_building_name='24b',
            address_line_1='High Road',
            address_line_2='Line 2',
            town_or_city='London',
            postcode='w17ty'
        )

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {
            'first_name': 'Michael',
            'last_name': 'Williams',
            'flat_number_house_number_building_name': '25b',
            'address_line_1': 'High Road',
            'address_line_2': 'London',
            'postcode': 'W1 7TY',
        }
        request = RequestFactory().post(reverse('bookings:address'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = address(request)
        self.assertEqual(response.status_code, 302)

        self.assertEqual(request.session['order'], order.pk)

    @freeze_time("2015-01-05 10:00:00")
    def test_items_updated_order_in_items_to_clean(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('10.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('40.80'))

        form = {"quantity-{}".format(item.pk): '5',
                "selected_category": item.category.pk}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = items_to_clean(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.session['items'], {item.pk: 5})
        order_pk = request.session['order']
        self.assertEqual(Order.objects.get(pk=order_pk).total_price_of_order, Decimal('51.00'))

    @freeze_time("2015-01-05 10:00:00")
    def test_items_updated_order_in_items_to_clean_voucher_applied(self):
        _user = UserFactory()
        _address = AddressFactory()

        voucher = VoucherFactory(percentage_off=Decimal('7.0'))
        item = ItemFactory(price=Decimal('10.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('40.80'),
                             voucher=voucher)

        form = {"quantity-{}".format(item.pk): '5',
                "selected_category": item.category.pk}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = items_to_clean(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.session['items'], {item.pk: 5})
        order_pk = request.session['order']
        self.assertEqual(Order.objects.get(pk=order_pk).total_price_of_order, Decimal('47.43'))

    @freeze_time("2015-01-05 10:00:00")
    def test_total_order_updated_in_address_step_voucher_untouched(self):
        _user = UserFactory()
        _address = AddressFactory()

        voucher = VoucherFactory(percentage_off=Decimal('7.0'))
        item = ItemFactory(price=Decimal('10.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('37.94'),
                             voucher=voucher)

        form = {
            'first_name': 'Michael',
            'last_name': 'Williams',
            'flat_number_house_number_building_name': '25b',
            'address_line_1': 'High Road',
            'address_line_2': 'London',
            'postcode': 'w1 5tg',
        }
        request = RequestFactory().post(reverse('bookings:address'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'w1 5tg',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = address(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Order.objects.get(pk=order.pk).total_price_of_order, Decimal('37.94'))

    @freeze_time("2015-01-05 10:00:00")
    def test_address_updated_in_existing_order(self):
        user = UserFactory()
        old_address = AddressFactory()
        new_address = AddressFactory(
            flat_number_house_number_building_name='25b',
            address_line_1='High Road',
            address_line_2='London',
            town_or_city='London',
            postcode='w25tg',
        )

        voucher = VoucherFactory(percentage_off=Decimal('7.0'))
        item = ItemFactory(price=Decimal('10.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item, price=Decimal('10.20') * 4)]
        pick_up_time = datetime.datetime(2015, 1, 6, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2015, 1, 8, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=old_address,
                             customer=user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('37.94'),
                             voucher=voucher)

        form = {
            'first_name': 'Michael',
            'last_name': 'Williams',
            'flat_number_house_number_building_name': '25b',
            'address_line_1': 'High Road',
            'address_line_2': 'London',
            'postcode': 'w2 5tg',
        }
        request = RequestFactory().post(reverse('bookings:address'), form)
        request.user = user

        add_session_to_request(request, session_data={
            'postcode': 'w1 5tg',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
            'address': old_address.pk,
            'order': order.pk
        })

        response = address(request)
        self.assertEqual(response.status_code, 302)
        self.assertNotEqual(Order.objects.get(pk=order.pk).pick_up_and_delivery_address.pk, old_address.pk)
        self.assertEqual(Order.objects.get(pk=order.pk).pick_up_and_delivery_address.postcode, 'w25tg')
        self.assertEqual(Order.objects.get(pk=order.pk).pick_up_and_delivery_address, new_address)

    @freeze_time("2014-04-06 10:00:00")
    def test_pick_up_time_changed_existing_order_updated(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'time_slot': '2014-04-08 11'}
        request = RequestFactory().post(reverse('bookings:pick_up_time'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = pick_up_time_page(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:delivery_time'))

        self.assertEqual(request.session['order'], order.pk)
        pick_up_time = datetime.datetime(2014, 4, 8, 10, tzinfo=pytz.utc)
        self.assertEqual(Order.objects.get(pk=request.session['order']
                                           ).pick_up_time, pick_up_time)
        # British summer time (UTC+1)
        self.assertEqual(request.session['pick_up_time'], "2014-04-08 11")
        time_local = timezone.localtime(pick_up_time)
        local = "%04d-%02d-%02d %02d" % (time_local.year,
                                         time_local.month,
                                         time_local.day,
                                         time_local.hour)
        self.assertEqual(request.session['pick_up_time'], local)

    @freeze_time("2014-04-06 10:00:00")
    def test_drop_off_time_changed_existing_order_updated(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'time_slot': '2014-04-11 11'}
        request = RequestFactory().post(reverse('bookings:delivery_time'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = delivery_time_page(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:items_to_clean'))

        self.assertEqual(request.session['order'], order.pk)
        drop_off_time = datetime.datetime(2014, 4, 11, 10, tzinfo=pytz.utc)
        self.assertEqual(Order.objects.get(pk=request.session['order']
                                           ).drop_off_time, drop_off_time)
        # British summer time (UTC+1)
        self.assertEqual(request.session['delivery_time'], "2014-04-11 11")
        time_local = timezone.localtime(drop_off_time)
        local = "%04d-%02d-%02d %02d" % (time_local.year,
                                         time_local.month,
                                         time_local.day,
                                         time_local.hour)
        self.assertEqual(request.session['delivery_time'], local)

    @freeze_time("2014-04-06 10:00:00")
    def test_pick_up_time_changed_invalidate_drop_off_time(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'time_slot': '2014-04-08 11'}
        request = RequestFactory().post(reverse('bookings:pick_up_time'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk,
        })

        response = pick_up_time_page(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:delivery_time'))

        self.assertEqual(request.session['order'], order.pk)
        self.assertIsNone(Order.objects.get(pk=request.session['order']).drop_off_time)
        self.assertTrue('delivery_time' not in request.session)

    @freeze_time("2014-04-06 10:00:00")
    def test_pick_up_time_changed_invalidate_drop_off_time_in_session(self):
        _user = UserFactory()

        form = {'time_slot': '2014-04-08 11'}
        request = RequestFactory().post(reverse('bookings:pick_up_time'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
        })

        response = pick_up_time_page(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:delivery_time'))

        self.assertEqual(form['time_slot'], request.session['pick_up_time'])
        self.assertTrue('delivery_time' not in request.session)

    @freeze_time("2014-04-06 10:00:00")
    def test_pick_up_time_not_changed_keep_drop_off_time_in_session(self):
        _user = UserFactory()

        form = {'time_slot': '2014-04-07 11'}
        request = RequestFactory().post(reverse('bookings:pick_up_time'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
        })

        response = pick_up_time_page(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:delivery_time'))

        self.assertEqual('2014-04-07 11', request.session['pick_up_time'])
        self.assertEqual('2014-04-10 15', request.session['delivery_time'])

    @freeze_time("2014-04-06 10:00:00")
    def test_pick_up_time_unchanged_do_not_invalidate_drop_off_time(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'time_slot': '2014-04-07 11'}
        request = RequestFactory().post(reverse('bookings:pick_up_time'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        modified = Order.objects.get(pk=request.session['order']).modified
        response = pick_up_time_page(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:delivery_time'))

        self.assertEqual(request.session['order'], order.pk)
        self.assertEqual(Order.objects.get(pk=request.session['order']
                                           ).modified, modified)
        self.assertEqual('2014-04-10 15', request.session['delivery_time'])

    @freeze_time("2014-04-08 10:00:00")
    def test_pick_up_time_selected_in_the_past_is_unset(self):
        self._populate_session({
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-08 10',
        })

        resp = self.client.get(reverse('bookings:pick_up_time'))
        self.assertNotContains(resp, 'div class="time-slot selected-slot"')
        self.assertTrue('pick_up_time' not in self.client.session)
        messages = list(resp.context['messages'])
        self.assertEqual(messages[0].level, MSG.ERROR)
        self.assertTrue("session expired" in str(messages[0]))

    @freeze_time("2014-04-07 10:00:00")
    def test_pick_up_time_expired_reset_times_in_order(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {"quantity-{}".format(item.pk): '5',
                "selected_category": item.category.pk}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        MessageMiddleware().process_request(request)
        response = items_to_clean(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:pick_up_time'))

        self.assertEqual(request.session['order'], order.pk)
        self.assertIsNone(Order.objects.get(
            pk=request.session['order']).pick_up_time)
        self.assertIsNone(Order.objects.get(
            pk=request.session['order']).drop_off_time)

    def test_login_invalid_lowercased(self):
        url = reverse('bookings:login')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        password = unicode("ḝl ñiño", encoding='utf-8')
        user = UserFactory(password=password)

        context = {
            'email_address': user.email,
            'password': "Ḝl Ñiño",
        }

        resp = self.client.post(url, context)
        self.assertTrue(resp.status_code, 200)

    def test_login_valid_lowercased(self):
        url = reverse('bookings:login')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        password = unicode("ḝl ñiño", encoding='utf-8')
        user = UserFactory(password=password)

        context = {
            'email_address': user.email,
            'password': "ḝl ñiño",
        }

        resp = self.client.post(url, context)
        self.assertRedirects(resp, reverse('landing'), status_code=302, target_status_code=200)

    @freeze_time("2015-01-05 10:00:00")
    def test_address_prepopulated_from_previous_order(self):
        user = UserFactory()
        address1 = AddressFactory(flat_number_house_number_building_name="887b",
                                  postcode='sw115tg')

        item = ItemFactory(price=Decimal('17.20'))
        OrderFactory(pick_up_and_delivery_address=address1,
                     customer=user)

        request = RequestFactory().get(reverse('bookings:address'))
        request.user = user

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
        })

        response = address(request)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(address1.flat_number_house_number_building_name in
                        response.content)
        self.assertTrue(address1.address_line_1 in response.content)
        self.assertTrue(address1.address_line_2 in response.content)

    @freeze_time("2015-01-05 10:00:00")
    def test_no_address_prepopulated_from_previous_order(self):
        user = UserFactory()
        address1 = AddressFactory(flat_number_house_number_building_name="887b",
                                  postcode='sw75ty')
        OrderFactory(pick_up_and_delivery_address=address1,
                     customer=user)

        address2 = AddressFactory(flat_number_house_number_building_name="98a",
                                  postcode='w37ty')
        OrderFactory(pick_up_and_delivery_address=address2,
                     customer=user)

        item = ItemFactory(price=Decimal('17.20'))

        request = RequestFactory().get(reverse('bookings:address'))
        request.user = user

        add_session_to_request(request, session_data={
            'postcode': 'sw11 5tg',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
        })

        response = address(request)
        self.assertEqual(response.status_code, 200)

        self.assertFalse(address1.flat_number_house_number_building_name
                         in response.content)
        self.assertFalse(address1.address_line_1 in response.content)
        self.assertFalse(address1.address_line_2 in response.content)
        self.assertFalse(address2.flat_number_house_number_building_name
                         in response.content)
        self.assertFalse(address2.address_line_1 in response.content)
        self.assertFalse(address2.address_line_2 in response.content)

    @freeze_time("2015-01-05 10:00:00")
    def test_address_prepopulated_from_previous_order_from_outcode(self):
        user = UserFactory()
        address1 = AddressFactory(flat_number_house_number_building_name="887b",
                                  postcode='sw115tg')
        OrderFactory(pick_up_and_delivery_address=address1,
                     customer=user)

        address2 = AddressFactory(flat_number_house_number_building_name="88b",
                                  postcode='sw57ty')
        OrderFactory(pick_up_and_delivery_address=address2,
                     customer=user)

        item = ItemFactory(price=Decimal('17.20'))

        request = RequestFactory().get(reverse('bookings:address'))
        request.user = user

        add_session_to_request(request, session_data={
            'postcode': 'sw11',
            'out_code': 'sw11',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 14',
            'items': {unicode(str(item.pk)): 4},
        })

        response = address(request)
        self.assertEqual(response.status_code, 200)

        self.assertTrue(address1.flat_number_house_number_building_name in
                        response.content)
        self.assertTrue(address1.address_line_1 in response.content)
        self.assertTrue(address1.address_line_2 in response.content)

    def test_postcode_in_session_populated_homepage_input(self):
        self._populate_session({
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
        })

        resp = self.client.get(reverse('landing'))
        self.assertContains(resp, 'value="sw16 7ty"')

    def test_postcode_in_order_populated_homepage_input(self):
        self._create_and_login_user()
        address = AddressFactory(postcode='sw57ty')
        OrderFactory(pick_up_and_delivery_address=address,
                     customer=self.user)

        resp = self.client.get(reverse('landing'))
        self.assertContains(resp, 'value="sw57ty"')

    def test_postcode_in_last_order_populated_homepage_input(self):
        self._create_and_login_user()

        created = timezone.now() - datetime.timedelta(days=1)
        address1 = AddressFactory(postcode='sw37ty')
        OrderFactory(pick_up_and_delivery_address=address1,
                     customer=self.user,
                     created=created)

        created = timezone.now() - datetime.timedelta(days=2)
        address2 = AddressFactory(postcode='sw47ty')
        OrderFactory(pick_up_and_delivery_address=address2,
                     customer=self.user,
                     created=created)

        resp = self.client.get(reverse('landing'))
        self.assertContains(resp, 'value="sw37ty"')

    def test_orders_empty(self):
        self._create_and_login_user()
        resp = self.client.get(reverse('bookings:orders'))
        self.assertContains(resp, 'You have not yet placed an order.')

    def test_orders_exist(self):
        self._create_and_login_user()
        address = AddressFactory(postcode='sw57ty')
        OrderFactory(pick_up_and_delivery_address=address,
                     authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                     customer=self.user)
        resp = self.client.get(reverse('bookings:orders'))
        self.assertContains(resp, 'SW5 7TY')

    def test_order_cannot_see_other_users_order(self):
        self._create_and_login_user()
        address = AddressFactory(postcode='sw57ty')
        order = OrderFactory(pick_up_and_delivery_address=address)
        resp = self.client.get(reverse('bookings:order',
                                       kwargs={'uuid': order.uuid}))
        self.assertEquals(resp.status_code, 404)

    def test_order_will_be_charged(self):
        self._create_and_login_user()
        address = AddressFactory(postcode='sw57ty')
        order = OrderFactory(pick_up_and_delivery_address=address,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             customer=self.user,
                             card_charged_status=Order.NOT_CHARGED)
        resp = self.client.get(reverse('bookings:order',
                                       kwargs={'uuid': order.uuid}))
        self.assertContains(resp, 'Your credit card will be charged on')

    def test_order_charged(self):
        self._create_and_login_user()
        address = AddressFactory(postcode='sw57ty')
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=self.user,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             card_charged_status=Order.SUCCESSFULLY_CHARGED)
        resp = self.client.get(reverse('bookings:order',
                                       kwargs={'uuid': order.uuid}))
        self.assertContains(resp, 'We have successfully charged your credit'
                                  ' card for this order.')

    def test_order_unable_to_charge(self):
        self._create_and_login_user()
        address = AddressFactory(postcode='sw57ty')
        order = OrderFactory(pick_up_and_delivery_address=address,
                             customer=self.user,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             card_charged_status=Order.FAILED_TO_CHARGE)
        resp = self.client.get(reverse('bookings:order',
                                       kwargs={'uuid': order.uuid}))
        self.assertContains(resp, 'We attempted to charge your credit card on')
        self.assertContains(resp, 'and failed to do so.')

    @freeze_time("2015-01-04 13:30:00")
    def test_pick_up_time_invalidated_max_slot_hit(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 14',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        pick_up_time = datetime.datetime(2015, 1, 5, 14, tzinfo=pytz.utc)

        TrackConfirmedOrderSlotsFactory(
            appointment=pick_up_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        resp = self.client.get(reverse('bookings:delivery_time'), follow=True)
        self.assertRedirects(resp, reverse('bookings:pick_up_time'))
        self.assertTrue('pick_up_time' not in self.client.session)
        messages = list(resp.context['messages'])
        self.assertEqual(messages[0].level, MSG.ERROR)
        self.assertTrue("Please select another pick up time" in str(messages[0]))

    @freeze_time("2015-01-04 13:30:00")
    def test_delivery_time_invalidated_max_slot_hit(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 14',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        drop_off_time = datetime.datetime(2015, 1, 9, 10, tzinfo=pytz.utc)

        TrackConfirmedOrderSlotsFactory(
            appointment=drop_off_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR)

        resp = self.client.get(reverse('registration:create_account'), follow=True)
        self.assertRedirects(resp, reverse('bookings:delivery_time'))
        self.assertTrue('pick_up_time' in self.client.session)
        self.assertTrue('delivery_time' not in self.client.session)
        messages = list(resp.context['messages'])
        self.assertEqual(messages[0].level, MSG.ERROR)
        self.assertTrue("Please select another delivery time" in str(messages[0]))

    @freeze_time("2015-01-04 13:30:00")
    def test_pick_up_time_not_invalidated_max_slot_not_hit(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 14',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        pick_up_time = datetime.datetime(2015, 1, 5, 14, tzinfo=pytz.utc)

        TrackConfirmedOrderSlotsFactory(
            appointment=pick_up_time,
            counter=settings.MAX_APPOINTMENTS_PER_HOUR - 1)

        resp = self.client.get(reverse('bookings:delivery_time'), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue('pick_up_time' in self.client.session)

    @freeze_time("2015-01-04 15:30:00")
    def test_pick_up_time_invalidated_pre_earliest_available_am_next_day(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 08',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        resp = self.client.get(reverse('bookings:delivery_time'), follow=True)
        self.assertRedirects(resp, reverse('bookings:pick_up_time'))
        self.assertTrue('pick_up_time' not in self.client.session)
        messages = list(resp.context['messages'])
        self.assertEqual(messages[0].level, MSG.ERROR)
        self.assertTrue("Please select another pick up time" in str(messages[0]))

    @freeze_time("2015-01-04 14:30:00")
    def test_pick_up_time_valid_pre_earliest_available_am_next_day(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-05 08',
            'delivery_time': '2015-01-09 10',
            'items': {1: 5},
        })

        resp = self.client.get(reverse('bookings:delivery_time'), follow=True)
        self.assertEqual(200, resp.status_code)

    @freeze_time("2014-04-06 10:00:00")
    def test_postcode_changed_from_existing_order_address_from_landing(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'postcode': 'w1 7ty'}
        request = RequestFactory().post(reverse('landing'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = landing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:pick_up_time'))
        self.assertEqual(request.session['order'], order.pk)
        self.assertTrue('address' not in request.session)

        # Cannot proceed past address step
        response = payment_landing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:address'))

    @freeze_time("2014-04-06 10:00:00")
    def test_postcode_unchanged_from_existing_order_address_from_landing(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'postcode': 'SW16 7TY'}
        request = RequestFactory().post(reverse('landing'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = landing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:pick_up_time'))
        self.assertEqual(request.session['order'], order.pk)
        self.assertTrue('address' in request.session)

        # User can proceed past address step
        response = payment_landing(request)
        self.assertEqual(response.status_code, 200)

    @freeze_time("2015-01-04 15:30:00")
    def test_drop_off_time_invalidated_in_session(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 14',
            'delivery_time': '2015-01-08 13',
            'items': {1: 5},
        })

        resp = self.client.get(reverse('bookings:items_to_clean'), follow=True)
        self.assertRedirects(resp, reverse('bookings:delivery_time'))
        self.assertTrue('delivery_time' not in self.client.session)
        messages = list(resp.context['messages'])
        self.assertEqual(messages[0].level, MSG.ERROR)
        self.assertTrue("Please select another delivery time" in str(messages[0]))

    @freeze_time("2015-01-04 15:30:00")
    def test_drop_off_time_not_invalidated_in_session(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 10',
            'items': {1: 5},
        })

        resp = self.client.get(reverse('bookings:items_to_clean'), follow=True)
        self.assertTrue(resp.status_code, 200)

    def test_items(self):
        resp = self.client.get(reverse('bookings:items_added'))
        self.assertEqual(resp.status_code, 200)

    @freeze_time("2015-01-04 15:30:00")
    def test_items_displayed(self):
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]

        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 10',
            'items': {item.pk: 4},
        })

        resp = self.client.get(reverse('bookings:items_added'), follow=True)
        self.assertTrue(resp.status_code, 200)
        for item in items:
            self.assertContains(resp, item.item.name, count=1)

    @freeze_time("2015-01-04 15:30:00")
    def test_items_displayed_sub_total(self):
        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item)]

        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-08 10',
            'items': {item.pk: 4},
        })

        resp = self.client.get(reverse('bookings:items_added'), follow=True)
        self.assertTrue(resp.status_code, 200)
        for item in items:
            sub_total = round(item.item.price * item.quantity, 2)
            self.assertContains(resp, sub_total)

    @freeze_time("2014-04-06 10:00:00")
    def test_item_quantity_updated(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item, price=Decimal('17.20') * 4)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'quantity-{}'.format(item.pk): '3'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = items_added(request)
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=request.session['order'])
        self.assertEqual(order.items.all()[0].quantity, 3)

    @freeze_time("2014-04-06 10:00:00")
    def test_item_quantity_price_updated(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item, price=Decimal('17.20') * 4)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'quantity-{}'.format(item.pk): '3'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = items_added(request)
        self.assertEqual(response.status_code, 200)
        order = Order.objects.get(pk=request.session['order'])
        self.assertEqual(order.items.all()[0].quantity, 3)
        self.assertEqual(order.items.all()[0].price, Decimal('17.20') * 3)
        self.assertEqual(sum(item.price for item in order.items.all()), Decimal('17.20') * 3)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_quantity_price_updated(self):
        _user = UserFactory()
        _address = AddressFactory()

        item = ItemFactory(price=Decimal('17.20'))
        items = [ItemAndQuantityFactory(quantity=4, item=item, price=Decimal('17.20') * 4)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.80'))

        form = {'quantity-{}'.format(item.pk): '3', 'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item.pk)): 4},
            'address': _address.pk,
            'order': order.pk
        })

        response = items_to_clean(request)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(pk=request.session['order'])
        self.assertEqual(order.items.all()[0].quantity, 3)
        self.assertEqual(order.items.all()[0].price, Decimal('17.20') * 3)
        self.assertEqual(sum(item.price for item in order.items.all()), Decimal('17.20') * 3)

    @freeze_time("2014-04-06 10:00:00")
    def test_multi_items_to_clean_quantity_price_updated(self):
        _user = UserFactory()
        _address = AddressFactory()

        item1 = ItemFactory(price=Decimal('15.75'))
        item2 = ItemFactory(price=Decimal('2.75'))
        items = [ItemAndQuantityFactory(quantity=4, item=item1, price=Decimal('15.75') * 4),
                 ItemAndQuantityFactory(quantity=2, item=item2, price=Decimal('2.75') * 2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('68.50'))

        form = {'quantity-{}'.format(item1.pk): '3',
                'quantity-{}'.format(item2.pk): '3',
                'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 4,
                      unicode(str(item2.pk)): 2,
                      },
            'address': _address.pk,
            'order': order.pk
        })

        response = items_to_clean(request)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get(pk=request.session['order'])
        self.assertEqual(sum(item.quantity for item in order.items.all()), 6)
        self.assertEqual(order.items.all()[0].price, Decimal('15.75') * 3)
        self.assertEqual(order.items.all()[1].price, Decimal('2.75') * 3)
        self.assertEqual(sum(item.price for item in order.items.all()), Decimal('15.75') * 3 + Decimal('2.75') * 3)

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_removed(self):
        _user = UserFactory()
        _address = AddressFactory()

        item1 = ItemFactory(price=Decimal('2.20'))
        item2 = ItemFactory(price=Decimal('6.20'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1, price=Decimal('2.20')),
                 ItemAndQuantityFactory(quantity=1, item=item2, price=Decimal('6.20'))]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('8.40'))

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '0'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])
        self.assertEqual(items, list(order.items.all()))
        response = items_added(request)

        self.assertEqual(response.status_code, 200)

        # Items removed
        self.assertEqual([], list(order.items.all()))
        self.assertTrue('items' not in request.session)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).total_price_of_order)

        # Cannot proceed past items step
        _session = request.session
        request = RequestFactory().get(reverse('payments:landing'))
        request.user = _user
        add_session_to_request(request, _session)

        response = payment_landing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:items_to_clean'))

    @freeze_time("2015-01-05 13:30:00")
    def test_items_to_clean_order_empty_items(self):
        self._populate_session({
            'postcode': 'w1 1aa',
            'out_code': 'w1',
            'pick_up_time': '2015-01-06 10',
            'delivery_time': '2015-01-09 10',
        })

        resp = self.client.post(reverse('bookings:items_to_clean'), {
            'quantity-40': '0',
            'quantity-41': '0',
            'quantity-42': '0',
            'selected_category': 1,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp,
                             'form',
                             '__all__',
                             [u'You have not added any items to your order.'])

        self.assertTrue('items' not in self.client.session)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_all_items_removed(self):
        _user = UserFactory()
        _address = AddressFactory()

        item1 = ItemFactory(price=Decimal('2.20'))
        item2 = ItemFactory(price=Decimal('6.20'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('8.40'))

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '0',
                'selected_category': 1,
                }
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])
        self.assertEqual(items, list(order.items.all()))
        response = items_to_clean(request)

        self.assertEqual(response.status_code, 200)

        # Items removed
        self.assertEqual([], list(order.items.all()))
        self.assertTrue('items' not in request.session)

        # Cannot proceed past items step
        _session = request.session
        request = RequestFactory().get(reverse('payments:landing'))
        request.user = _user
        add_session_to_request(request, _session)

        response = payment_landing(request)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('bookings:items_to_clean'))

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_removed_delivery_removed(self):
        _user = UserFactory()
        _address = AddressFactory()

        transportation_charge = Decimal('2.95')
        item1 = ItemFactory(price=Decimal('2.20'))
        item2 = ItemFactory(price=Decimal('6.20'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('8.40') + transportation_charge)

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '0'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=transportation_charge):
            response = items_added(request)

        self.assertEqual(response.status_code, 200)

        # Items removed
        self.assertEqual([], list(order.items.all()))
        self.assertTrue('items' not in request.session)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_changed_delivery_added(self):
        _user = UserFactory()
        _address = AddressFactory()

        transportation_charge = Decimal('2.95')
        item1 = ItemFactory(price=Decimal('12.20'))
        item2 = ItemFactory(price=Decimal('6.20'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('18.40'))

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '1'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=transportation_charge):
            response = items_added(request)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(item2.price + transportation_charge, Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(transportation_charge, Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_changed_delivery_added_with_voucher(self):
        _user = UserFactory()
        _address = AddressFactory()

        transportation_charge = Decimal('2.95')
        voucher = VoucherFactory(percentage_off=Decimal('5.0'))
        item1 = ItemFactory(price=Decimal('12.20'))
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             voucher=voucher,
                             total_price_of_order=Decimal('15.39'))

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '1'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=transportation_charge):
            response = items_added(request)

        self.assertEqual(response.status_code, 200)

        # Apply voucher then add delivery charge
        self.assertEqual((item2.price - (item2.price * Decimal('0.05'))) + transportation_charge, Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(transportation_charge, Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_changed_delivery_removed_with_voucher(self):
        _user = UserFactory()
        _address = AddressFactory()

        min_free_delivery = Decimal('10.00')
        transportation_charge = Decimal('2.95')
        voucher = VoucherFactory(percentage_off=Decimal('5.0'))
        item1 = ItemFactory(price=Decimal('6.20'))
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             voucher=voucher,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('3.80') + transportation_charge)

        # Takes it above to qualify for free delivery (£10.20)
        form = {'quantity-{}'.format(item1.pk): '1',
                'quantity-{}'.format(item2.pk): '1'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=min_free_delivery, TRANSPORTATION_CHARGE=transportation_charge):
            response = items_added(request)

        self.assertEqual(response.status_code, 200)

        # Voucher applied takes it below free delivery price but delivery not
        # applied as this is based on total items price
        self.assertEqual(Decimal('9.69'), Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_changed_delivery_removed(self):
        _user = UserFactory()
        _address = AddressFactory()

        min_free_delivery = Decimal('10.00')
        transportation_charge = Decimal('2.95')
        item1 = ItemFactory(price=Decimal('6.20'))
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('4.00') + transportation_charge)

        # Takes it above to qualify for free delivery (£10.20)
        form = {'quantity-{}'.format(item1.pk): '1',
                'quantity-{}'.format(item2.pk): '1'}
        request = RequestFactory().post(reverse('bookings:items_added'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=min_free_delivery, TRANSPORTATION_CHARGE=transportation_charge):
            response = items_added(request)

        self.assertEqual(response.status_code, 200)

        self.assertEqual(Decimal('10.20'), Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_update_items_to_clean_delivery_removed(self):
        _user = UserFactory()
        _address = AddressFactory()

        transportation_charge = Decimal('2.95')
        item1 = ItemFactory(price=Decimal('2.20'))
        item2 = ItemFactory(price=Decimal('6.20'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('8.40') + transportation_charge)

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '0',
                'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=transportation_charge):
            response = items_to_clean(request)

        # Page returned form invalid
        self.assertEqual(response.status_code, 200)
        self.assertTrue('You have not added any items to your order.' in response.content)

        # Items removed
        self.assertEqual([], list(order.items.all()))
        self.assertTrue('items' not in request.session)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_changed_delivery_added(self):
        _user = UserFactory()
        _address = AddressFactory()

        transportation_charge = Decimal('2.95')
        item1 = ItemFactory(price=Decimal('12.20'))
        item2 = ItemFactory(price=Decimal('6.20'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             total_price_of_order=Decimal('18.40'))

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '1',
                'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1,
                      unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=transportation_charge):
            response = items_to_clean(request)

        self.assertEqual(response.status_code, 302)

        self.assertEqual(item2.price + transportation_charge, Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(transportation_charge, Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_changed_delivery_added_with_voucher(self):
        _user = UserFactory()
        _address = AddressFactory()

        transportation_charge = Decimal('2.95')
        voucher = VoucherFactory(percentage_off=Decimal('5.0'))
        item1 = ItemFactory(price=Decimal('12.20'))
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item1), ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             voucher=voucher,
                             total_price_of_order=Decimal('15.39'))

        form = {'quantity-{}'.format(item1.pk): '0',
                'quantity-{}'.format(item2.pk): '1',
                'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item1.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=Decimal('10.00'), TRANSPORTATION_CHARGE=transportation_charge):
            response = items_to_clean(request)

        self.assertEqual(response.status_code, 302)

        # Apply voucher then add delivery charge
        self.assertEqual((item2.price - (item2.price * Decimal('0.05'))) + transportation_charge, Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(transportation_charge, Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_changed_delivery_removed_with_voucher(self):
        _user = UserFactory()
        _address = AddressFactory()

        min_free_delivery = Decimal('10.00')
        transportation_charge = Decimal('2.95')
        voucher = VoucherFactory(percentage_off=Decimal('5.0'))
        item1 = ItemFactory(price=Decimal('6.20'))
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             voucher=voucher,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('3.80') + transportation_charge)

        # Takes it above to qualify for free delivery (£10.20)
        form = {'quantity-{}'.format(item1.pk): '1',
                'quantity-{}'.format(item2.pk): '1',
                'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=min_free_delivery, TRANSPORTATION_CHARGE=transportation_charge):
            response = items_to_clean(request)

        self.assertEqual(response.status_code, 302)

        # Voucher applied takes it below free delivery price but delivery not
        # applied as this is based on total items price
        self.assertEqual(Decimal('9.69'), Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).transportation_charge)

    @freeze_time("2014-04-06 10:00:00")
    def test_items_to_clean_changed_delivery_removed(self):
        _user = UserFactory()
        _address = AddressFactory()

        min_free_delivery = Decimal('10.00')
        transportation_charge = Decimal('2.95')
        item1 = ItemFactory(price=Decimal('6.20'))
        item2 = ItemFactory(price=Decimal('4.00'))
        items = [ItemAndQuantityFactory(quantity=1, item=item2)]
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        drop_off_time = datetime.datetime(2014, 4, 10, 14, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_and_delivery_address=_address,
                             customer=_user,
                             pick_up_time=pick_up_time,
                             drop_off_time=drop_off_time,
                             items=items,
                             transportation_charge=transportation_charge,
                             total_price_of_order=Decimal('4.00') + transportation_charge)

        # Takes it above to qualify for free delivery (£10.20)
        form = {'quantity-{}'.format(item1.pk): '1',
                'quantity-{}'.format(item2.pk): '1',
                'selected_category': 1}
        request = RequestFactory().post(reverse('bookings:items_to_clean'), form)
        request.user = _user

        add_session_to_request(request, session_data={
            'postcode': 'sw16 7ty',
            'out_code': 'sw16',
            'pick_up_time': '2014-04-07 11',
            'delivery_time': '2014-04-10 15',
            'items': {unicode(str(item2.pk)): 1},
            'address': _address.pk,
            'order': order.pk
        })

        order = Order.objects.get(pk=request.session['order'])

        with self.settings(MIN_FREE_TRANSPORTATION=min_free_delivery, TRANSPORTATION_CHARGE=transportation_charge):
            response = items_to_clean(request)

        self.assertEqual(response.status_code, 302)

        self.assertEqual(Decimal('10.20'), Order.objects.get(pk=request.session['order']).total_price_of_order)
        self.assertEqual(Decimal('0.00'), Order.objects.get(pk=request.session['order']).transportation_charge)


