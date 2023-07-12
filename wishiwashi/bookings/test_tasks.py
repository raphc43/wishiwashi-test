import datetime
from datetime import timedelta

from freezegun import freeze_time
from django.test import TestCase
from django.test.utils import override_settings
import mock
import pytz

from .factories import OrderFactory, TrackConfirmedOrderSlotsFactory, CleanOnlyOrderFactory
from .models import Order, PickupOrderReminder, DropoffOrderReminder, TrackConfirmedOrderSlots, CleanOnlyOrder
from .tasks import (push_orders_along,
                    delete_old_sessions,
                    pick_up_reminder_via_email,
                    drop_off_reminder_via_email,
                    cleanup_tracked_confirmed_order_slots,
                    expected_back_clean_only_orders)

from vendors.tests.patches import create_order


class Tasks(TestCase):
    fixtures = ['test_outcodes', 'test_wishi_washi_vendor',
                'test_categories_and_items']

    def setUp(self):
        now_utc = datetime.datetime.utcnow().replace(tzinfo=pytz.UTC)
        tz_london = pytz.timezone('Europe/London')
        now_london = now_utc.astimezone(tz_london)

        self.three_days_ago = now_london - timedelta(days=3)
        self.three_hours_ago = now_london - timedelta(hours=3)
        self.day_after_tomorrow = now_london + timedelta(days=2)
        super(Tasks, self).setUp()

    def test_push_orders_along_received_by_vendor(self):
        # dummy order to prove not all orders are affected
        create_order(authorised=False)

        order = create_order()
        order.order_status = Order.CLAIMED_BY_VENDOR
        order.authorisation_status = Order.SUCCESSFULLY_AUTHORISED
        order.pick_up_time = self.three_hours_ago
        order.drop_off_time = self.day_after_tomorrow
        order.save()

        push_orders_along()

        num_received = Order.objects.filter(
            order_status=Order.RECEIVED_BY_VENDOR).count()
        self.assertEqual(1, num_received)

    def test_push_orders_along_delivered_back_to_customer(self):
        # dummy order to prove not all orders are affected
        create_order(authorised=False)

        order = create_order()
        order.order_status = Order.RECEIVED_BY_VENDOR
        order.authorisation_status = Order.SUCCESSFULLY_AUTHORISED
        order.pick_up_time = self.three_days_ago
        order.drop_off_time = self.three_hours_ago
        order.save()

        push_orders_along()

        num_received = Order.objects.filter(
            order_status=Order.DELIVERED_BACK_TO_CUSTOMER).count()
        self.assertEqual(1, num_received)

    def test_delete_old_sessions(self):
        delete_old_sessions()

    @freeze_time("2014-04-07 09:01:00")
    def test_cleanup_tracked_confirmed_order_slots(self):
        slot1 = datetime.datetime(2014, 3, 3, 9, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(appointment=slot1)

        slot2 = datetime.datetime(2014, 3, 3, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(appointment=slot2)

        cleanup_tracked_confirmed_order_slots()

        self.assertRaises(TrackConfirmedOrderSlots.DoesNotExist,
                          TrackConfirmedOrderSlots.objects.get,
                          appointment=slot1)

        self.assertTrue(TrackConfirmedOrderSlots.objects.filter(
            appointment=slot2).exists())

    @freeze_time("2014-04-07 09:01:00")
    def test_cleanup_tracked_confirmed_order_slots_recent(self):
        slot1 = datetime.datetime(2014, 3, 3, 10, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(appointment=slot1)

        # Past 5 weeks ago
        slot2 = datetime.datetime(2014, 3, 2, 11, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(appointment=slot2)

        slot3 = datetime.datetime(2014, 4, 1, 9, tzinfo=pytz.utc)
        TrackConfirmedOrderSlotsFactory(appointment=slot3)

        cleanup_tracked_confirmed_order_slots()

        self.assertTrue(TrackConfirmedOrderSlots.objects.filter(
            appointment=slot1).exists())

        self.assertRaises(TrackConfirmedOrderSlots.DoesNotExist,
                          TrackConfirmedOrderSlots.objects.get,
                          appointment=slot2)

        self.assertTrue(TrackConfirmedOrderSlots.objects.filter(
            appointment=slot3).exists())


@override_settings(
    COMMUNICATE_SERVICE_ENDPOINT="http://localhost"
)
class TasksReminders(TestCase):
    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_within_hour(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertTrue(PickupOrderReminder.objects.filter(
            order=order).exists())

    @freeze_time("2014-04-07 09:00:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_no_orders_pre(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 10:00:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_no_orders_post(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_within_hour_localtime(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)

        london = pytz.timezone('Europe/London')
        local = pick_up_time.astimezone(london)
        assert local.hour == 11

        order = OrderFactory(pick_up_time=local,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertEqual(order.pick_up_time, pick_up_time)
        self.assertEqual(order.pick_up_time, local)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertTrue(PickupOrderReminder.objects.filter(
            order=order).exists())

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_multi(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        pick_up_time1 = datetime.datetime(2014, 4, 7, 9, tzinfo=pytz.utc)
        order1 = OrderFactory(pick_up_time=pick_up_time1,
                              order_status=Order.CLAIMED_BY_VENDOR,
                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                              charge_back_status=Order.NOT_CHARGED_BACK,
                              refund_status=Order.NOT_REFUNDED)

        pick_up_time2 = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order2 = OrderFactory(pick_up_time=pick_up_time2,
                              order_status=Order.CLAIMED_BY_VENDOR,
                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                              charge_back_status=Order.NOT_CHARGED_BACK,
                              refund_status=Order.NOT_REFUNDED)

        pick_up_time3 = datetime.datetime(2014, 4, 7, 11, tzinfo=pytz.utc)
        order3 = OrderFactory(pick_up_time=pick_up_time3,
                              order_status=Order.CLAIMED_BY_VENDOR,
                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                              charge_back_status=Order.NOT_CHARGED_BACK,
                              refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order1)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order2)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order3)

        pick_up_reminder_via_email()

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order1)

        self.assertTrue(PickupOrderReminder.objects.filter(
            order=order2).exists())

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order3)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_within_hour_communicate_failure(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":-1,"error":true}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_within_hour_status_failure(self, mock_response):
        class response(object):
            status_code = 500
            content = '{}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_pick_up_reminder_unexpected_failure(self, mock_response):
        class response(object):
            status_code = 500
            content = '{}'

        mock_response.return_value = response()
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(pick_up_time=pick_up_time,
                             order_status=Order.CLAIMED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)
        pick_up_reminder_via_email()
        self.assertRaises(PickupOrderReminder.DoesNotExist,
                          PickupOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_within_hour(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertTrue(DropoffOrderReminder.objects.filter(
            order=order).exists())

    @freeze_time("2014-04-07 09:00:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_no_orders_pre(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 10:00:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_no_orders_post(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_within_hour_localtime(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)

        london = pytz.timezone('Europe/London')
        local = drop_off_time.astimezone(london)
        assert local.hour == 11

        order = OrderFactory(drop_off_time=local,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertEqual(order.drop_off_time, drop_off_time)
        self.assertEqual(order.drop_off_time, local)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertTrue(DropoffOrderReminder.objects.filter(
            order=order).exists())

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_multi(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":1,"error":false}'

        mock_response.return_value = response()
        drop_off_time1 = datetime.datetime(2014, 4, 7, 9, tzinfo=pytz.utc)
        order1 = OrderFactory(drop_off_time=drop_off_time1,
                              order_status=Order.RECEIVED_BY_VENDOR,
                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                              charge_back_status=Order.NOT_CHARGED_BACK,
                              refund_status=Order.NOT_REFUNDED)

        drop_off_time2 = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order2 = OrderFactory(drop_off_time=drop_off_time2,
                              order_status=Order.RECEIVED_BY_VENDOR,
                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                              charge_back_status=Order.NOT_CHARGED_BACK,
                              refund_status=Order.NOT_REFUNDED)

        drop_off_time3 = datetime.datetime(2014, 4, 7, 11, tzinfo=pytz.utc)
        order3 = OrderFactory(drop_off_time=drop_off_time3,
                              order_status=Order.RECEIVED_BY_VENDOR,
                              authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                              charge_back_status=Order.NOT_CHARGED_BACK,
                              refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order1)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order2)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order3)

        drop_off_reminder_via_email()

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order1)

        self.assertTrue(DropoffOrderReminder.objects.filter(
            order=order2).exists())

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order3)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_within_hour_communicate_failure(self, mock_response):
        class response(object):
            status_code = 200
            content = '{"job_id":-1,"error":true}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_within_hour_status_failure(self, mock_response):
        class response(object):
            status_code = 500
            content = '{}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-07 09:01:00")
    @mock.patch('requests.post')
    def test_drop_off_reminder_unexpected_failure(self, mock_response):
        class response(object):
            status_code = 500
            content = '{}'

        mock_response.return_value = response()
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             order_status=Order.RECEIVED_BY_VENDOR,
                             authorisation_status=Order.SUCCESSFULLY_AUTHORISED,
                             charge_back_status=Order.NOT_CHARGED_BACK,
                             refund_status=Order.NOT_REFUNDED)

        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)
        drop_off_reminder_via_email()
        self.assertRaises(DropoffOrderReminder.DoesNotExist,
                          DropoffOrderReminder.objects.get, order=order)

    @freeze_time("2014-04-08 02:00:00")
    def test_expected_back_clean_only_orders(self):
        drop_off_time = datetime.datetime(2014, 4, 9, 10, tzinfo=pytz.utc)
        pick_up_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             pick_up_time=pick_up_time,
                             placed=True,
                             order_status=Order.RECEIVED_BY_VENDOR)
        CleanOnlyOrderFactory(order=order)
        expected_back_clean_only_orders()
        self.assertTrue(hasattr(CleanOnlyOrder.objects.get(order=order), 'expectedbackcleanonlyorder'))
        self.assertFalse(CleanOnlyOrder.objects.get(order=order).expectedbackcleanonlyorder.confirmed_back)

    @freeze_time("2014-04-03 02:00:00")
    def test_expected_back_clean_only_orders_check_valid(self):
        drop_off_time = datetime.datetime(2014, 4, 7, 10, tzinfo=pytz.utc)
        pick_up_time = datetime.datetime(2014, 4, 2, 10, tzinfo=pytz.utc)
        order = OrderFactory(drop_off_time=drop_off_time,
                             pick_up_time=pick_up_time,
                             placed=True,
                             order_status=Order.RECEIVED_BY_VENDOR)
        CleanOnlyOrderFactory(order=order)
        expected_back_clean_only_orders()
        expected = datetime.datetime(2014, 4, 5, 17, tzinfo=pytz.utc)
        self.assertEqual(expected, CleanOnlyOrder.objects.get(order=order).expectedbackcleanonlyorder.expected_back)



