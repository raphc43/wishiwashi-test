from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from bookings.address import order_address_lookup, postcode_from_last_order
from bookings.factories import UserFactory, OrderFactory, AddressFactory


class Address(TestCase):
    def test_previous_address_invalid_postcode(self):
        address_match = order_address_lookup(UserFactory(), "sw1867")
        self.assertIsNone(address_match)

    def test_previous_address_selected_based_on_full_postcode(self):
        user = UserFactory()
        address = AddressFactory(postcode="sw73qf")
        OrderFactory(customer=user, pick_up_and_delivery_address=address)

        address_match = order_address_lookup(user, "sw7 3qf")
        self.assertTrue(address_match)
        self.assertEqual(address_match, address)

    def test_previous_address_selected_based_on_outcode(self):
        user = UserFactory()
        address = AddressFactory(postcode="sw73qf")
        OrderFactory(customer=user, pick_up_and_delivery_address=address)

        address_match = order_address_lookup(user, "sw7")
        self.assertTrue(address_match)
        self.assertEqual(address_match, address)

    def test_most_recent_address_selected_based_on_outcode(self):
        user = UserFactory()
        address1 = AddressFactory(address_line_1="London Town",
                                  postcode="sw73qf")
        created = timezone.now() - timedelta(days=2)
        OrderFactory(customer=user, pick_up_and_delivery_address=address1,
                     created=created)

        address2 = AddressFactory(address_line_1="London City",
                                  postcode="sw73qf")
        created = timezone.now() - timedelta(days=4)
        OrderFactory(customer=user, pick_up_and_delivery_address=address2,
                     created=created)

        address_match = order_address_lookup(user, "sw7")
        self.assertTrue(address_match)
        self.assertEqual(address_match, address1)

    def test_most_recent_address_selected_based_on_incode(self):
        user = UserFactory()
        address1 = AddressFactory(address_line_1="London Town",
                                  postcode="w25yt")
        created = timezone.now() - timedelta(days=2)
        OrderFactory(customer=user, pick_up_and_delivery_address=address1,
                     created=created)

        address2 = AddressFactory(address_line_1="London City",
                                  postcode="w25yt")
        created = timezone.now() - timedelta(days=4)
        OrderFactory(customer=user, pick_up_and_delivery_address=address2,
                     created=created)

        address_match = order_address_lookup(user, "w25yt")
        self.assertTrue(address_match)
        self.assertEqual(address_match, address1)

    def test_no_address_selected_based_on_incode(self):
        user = UserFactory()
        address1 = AddressFactory(address_line_1="London Town",
                                  postcode="w25yt")
        created = timezone.now() - timedelta(days=2)
        OrderFactory(customer=user, pick_up_and_delivery_address=address1,
                     created=created)

        address2 = AddressFactory(address_line_1="London City",
                                  postcode="w25yt")
        created = timezone.now() - timedelta(days=4)
        OrderFactory(customer=user, pick_up_and_delivery_address=address2,
                     created=created)

        address_match = order_address_lookup(user, "sw6")
        self.assertIsNone(address_match)

    def test_empty_postcode_no_orders(self):
        user = UserFactory()
        postcode = postcode_from_last_order(user)
        self.assertIsNone(postcode)

    def test_no_postcode_set(self):
        user = UserFactory()
        address = AddressFactory(postcode="")
        OrderFactory(customer=user,
                     pick_up_and_delivery_address=address)

        self.assertIsNone(postcode_from_last_order(user))

    def test_postcode_returned(self):
        user = UserFactory()
        address = AddressFactory(postcode="sw75ty")
        OrderFactory(customer=user,
                     pick_up_and_delivery_address=address)

        self.assertEqual("sw75ty", postcode_from_last_order(user))

    def test_last_postcode_selected(self):
        user = UserFactory()
        address1 = AddressFactory(address_line_1="London Town",
                                  postcode="sw15ty")
        created = timezone.now() - timedelta(days=2)
        OrderFactory(customer=user, pick_up_and_delivery_address=address1,
                     created=created)

        address2 = AddressFactory(address_line_1="London City",
                                  postcode="w25yt")
        created = timezone.now() - timedelta(days=4)
        OrderFactory(customer=user, pick_up_and_delivery_address=address2,
                     created=created)

        self.assertEqual("sw15ty", postcode_from_last_order(user))


