import json
import uuid

from dateutil.parser import parse
from django.contrib.auth.models import User
from django.utils import timezone
import pytz
import shortuuid

from bookings.tickets import next_ticket_id
from bookings.models import Address, Item, ItemAndQuantity, Order, Vendor
from customer_service.models import UserProfile


def create_vendor(client=None, create_new_vendor=False):
    """
    If client is passed then it'll be logged in. Not passing a client
    is useful if you need to create vendors.
    """
    user = User.objects.create_user(username=str(uuid.uuid4())[:28],
                                    email='test%s@test.com' % str(uuid.uuid4())[:10],
                                    password='testing123')
    profile = UserProfile(user=user)
    profile.save()

    if create_new_vendor:
        addr = Address()
        addr.save()

        vendor = Vendor()
        vendor.address = addr
        vendor.save()
    else:
        vendor = Vendor.objects.all()[0]
    vendor.staff.add(user)

    if client:
        client.login(username=user.username, password='testing123')
    return vendor


def create_order(pick_up_time='2015-01-03 10',
                 delivery_time='2015-01-05 10',
                 authorised=True):
    """
    The authorised flag lets you create orders that have not been authorised
    so you can test scenarios where we have yet or have failed to receive
    authorisation of a customer's credit card.
    """
    customer = User.objects.create_user(
        first_name="First",
        last_name="Last",
        username=str(uuid.uuid4())[:28],
        email='test%s@test.com' % str(uuid.uuid4())[:10],
        password='testing123')

    profile = UserProfile(user=customer, mobile_number='00447712345678')
    profile.save()

    addr = Address(flat_number_house_number_building_name='1',
                   address_line_1='High Road',
                   town_or_city='London',
                   postcode='w11aa')
    addr.save()

    shortuuid.set_alphabet("AFGHJKLMQRTWXYZ2346789")

    items = Item.objects.filter(pk__in=[28, 29])

    order = Order()
    order.uuid = shortuuid.uuid()[:6]
    order.pick_up_time = parse(pick_up_time).replace(tzinfo=pytz.utc)
    order.drop_off_time = parse(delivery_time).replace(tzinfo=pytz.utc)
    order.pick_up_and_delivery_address = addr
    order.customer = customer
    order.total_price_of_order = sum([item.price for item in items])

    if authorised:
        order.authorisation_status = Order.SUCCESSFULLY_AUTHORISED
        order.placed = True
        order.placed_time = timezone.now()

    order.save()
    order.ticket_id = next_ticket_id(order.pk)

    for item_pk, quantity in ((28, 5), (29, 10)):
        item_quantity = ItemAndQuantity()
        item_quantity.item = Item.objects.get(pk=item_pk)
        item_quantity.quantity = quantity
        item_quantity.save()
        order.items.add(item_quantity)

    return order


def fake_resp(url, data=None, auth=None):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': False,
            'order_uuid': '1234567890123456',
        })

    return FakeResponse


def fake_sms_resp(url, data=None, auth=None):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': False,
            'sms_uuid': '0123456789',
        })

    return FakeResponse


def fake_job_resp(url, **kwargs):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': False,
            'job_id': '5',
        })

    return FakeResponse


def fake_resp_error(url, **kwargs):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': True,
            'errors': ['Unable to find'],
        })

    return FakeResponse


class FakeTask(object):
    """
    Used for patching communicate.tasks.send_email, etc...
    """
    def delay(self, *args, **kawargs):
        pass


# Some tasks re-schedule themselves via a raised exception so you can't patch
# the whole task, only the delay() method.
def fake_delay(*args, **kawargs):
    pass


def fake_resp_sent(url, data=None, auth=None):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': False,
            'status': 'Sent',
        })

    return FakeResponse


def fake_resp_failed_to_send(url, data=None, auth=None):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': False,
            'status': 'Failed to send',
        })

    return FakeResponse


def fake_resp_converted(url, data=None, auth=None):
    """
    Used for patching requests.get
    """
    class FakeResponse(object):
        """
        Fake requests.get response
        """
        status_code = 200
        content = json.dumps({
            'error': False,
            'status': 'Converted',
            'pdf_file': 'https://testing/test.pdf'
        })

    return FakeResponse


fake_task = FakeTask()


def fake_error_logging(*args, **kwargs):
    pass
