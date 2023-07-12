from bookings.models import Order
from ukpostcodeparser import parse_uk_postcode


def order_address_lookup(user, postcode):
    """
    user: User object
    postcode: outcode/full postcode

    Find a previous address from users order history ordered by
    most recent that matches outcode+incode or outcode (fuzzy)
    """
    try:
        postcode_valid = parse_uk_postcode(postcode.strip(),
                                           incode_mandatory=False)
    except ValueError:
        return None

    postcode_normalised = "".join(postcode_valid).lower()

    for order in Order.objects.filter(customer=user).order_by("-created"):
        if order.pick_up_and_delivery_address:
            if postcode_valid[1]:  # with incode
                if order.pick_up_and_delivery_address.postcode == \
                        postcode_normalised:
                    return order.pick_up_and_delivery_address
            elif order.pick_up_and_delivery_address.postcode.startswith(
                    postcode_normalised):
                return order.pick_up_and_delivery_address

    return None


def postcode_from_last_order(user):
    """
    user: User object

    Return the postcode from users last order
    """
    for order in Order.objects.filter(customer=user).order_by("-created"):
        if order.pick_up_and_delivery_address and hasattr(
            order.pick_up_and_delivery_address, 'postcode'):
            if order.pick_up_and_delivery_address.postcode:
                return order.pick_up_and_delivery_address.postcode

    return None



