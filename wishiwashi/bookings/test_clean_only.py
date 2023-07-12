from datetime import datetime
from django.test import TestCase
import pytz

from .clean_only import pre_working_day, drop_off_time_to_ready_time, expected_back


class Utils(TestCase):
    def test_pre_working_day_valid(self):
        # 1st Monday June 2015 @ 13 (UTC)
        drop_off_time = datetime(2015, 6, 1, 13, tzinfo=pytz.utc)
        pre_working_day_time = datetime(2015, 5, 30, 13, tzinfo=pytz.utc)
        self.assertEqual(pre_working_day_time, pre_working_day(drop_off_time))

    def test_pre_working_day_valid_check_bank_holidays(self):
        # 7th Tuesday April 2015 @ 13 (UTC)
        drop_off_time = datetime(2015, 4, 7, 13, tzinfo=pytz.utc)
        pre_working_day_time = datetime(2015, 4, 4, 13, tzinfo=pytz.utc)
        self.assertEqual(pre_working_day_time, pre_working_day(drop_off_time))

    def test_pre_working_day_valid_check_saturdays_bank_holiday(self):
        # 4th Saturday April 2015 @ 13 (UTC)
        drop_off_time = datetime(2015, 4, 4, 13, tzinfo=pytz.utc)
        pre_working_day_time = datetime(2015, 4, 2, 13, tzinfo=pytz.utc)
        self.assertEqual(pre_working_day_time, pre_working_day(drop_off_time))

    def test_pre_working_day_valid_check_xmas(self):
        # 28th Monday April 2015 @ 13 (UTC)
        drop_off_time = datetime(2015, 12, 28, 13, tzinfo=pytz.utc)
        pre_working_day_time = datetime(2015, 12, 26, 13, tzinfo=pytz.utc)
        self.assertEqual(pre_working_day_time, pre_working_day(drop_off_time))

    def test_pre_working_day_valid_conversion(self):
        drop_off_time = datetime(2015, 6, 11, 20, tzinfo=pytz.utc)
        expected = datetime(2015, 6, 11, 20, tzinfo=pytz.utc).strftime("%a %d %b AM")
        self.assertEqual(expected, drop_off_time_to_ready_time(drop_off_time))

    def test_pre_working_day_valid_conversion_pre_working_day(self):
        drop_off_time = datetime(2015, 6, 11, 8, tzinfo=pytz.utc)
        expected = datetime(2015, 6, 10, 8, tzinfo=pytz.utc).strftime("%a %d %b PM")
        self.assertEqual(expected, drop_off_time_to_ready_time(drop_off_time))

    def test_pre_working_day_valid_conversion_edge_working_day(self):
        drop_off_time = datetime(2015, 6, 11, 14, tzinfo=pytz.utc)
        expected = datetime(2015, 6, 11, 14, tzinfo=pytz.utc).strftime("%a %d %b AM")
        self.assertEqual(expected, drop_off_time_to_ready_time(drop_off_time))

    def test_pre_working_day_valid_conversion_bank_holiday(self):
        drop_off_time = datetime(2015, 5, 5, 13, tzinfo=pytz.utc)
        expected = datetime(2015, 5, 2, 14, tzinfo=pytz.utc).strftime("%a %d %b PM")
        self.assertEqual(expected, drop_off_time_to_ready_time(drop_off_time))

    def test_expected_back_previous_working_day(self):
        # 1st Monday June 2015 @ 13 (UTC)
        drop_off_time = datetime(2015, 6, 1, 13, tzinfo=pytz.utc)
        expected_back_dt = datetime(2015, 5, 30, 17, tzinfo=pytz.utc)
        self.assertEqual(expected_back_dt, expected_back(drop_off_time))

    def test_expected_back_same_day(self):
        # 1st Monday June 2015 @ 16 (UTC)
        drop_off_time = datetime(2015, 6, 1, 16, tzinfo=pytz.utc)
        expected_back_dt = datetime(2015, 6, 1, 12, tzinfo=pytz.utc)
        self.assertEqual(expected_back_dt, expected_back(drop_off_time))

    def test_expected_back_previous_working_day_bank_holiday(self):
        # 26th Tuesday May 2015 @ 13 (UTC)
        drop_off_time = datetime(2015, 5, 26, 13, tzinfo=pytz.utc)
        expected_back_dt = datetime(2015, 5, 23, 17, tzinfo=pytz.utc)
        self.assertEqual(expected_back_dt, expected_back(drop_off_time))


