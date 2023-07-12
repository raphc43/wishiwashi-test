from django.test import TestCase

from .tickets import next_ticket_id, THRESHOLD


class Tickets(TestCase):
    def test_next_id(self):
        pk = 324
        expected = "WW-{:0>5d}".format(pk)
        self.assertEqual(expected, next_ticket_id(pk))

    def test_next_id_reset(self):
        pk = THRESHOLD
        expected = "WW-{:0>5d}".format(0)
        self.assertEqual(expected, next_ticket_id(pk))

    def test_next_id_initial(self):
        pk = THRESHOLD + 1
        expected = "WW-{:0>5d}".format(1)
        self.assertEqual(expected, next_ticket_id(pk))


