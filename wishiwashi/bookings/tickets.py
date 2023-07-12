# Limit ticket number
THRESHOLD = 100000


def next_ticket_id(pk):
    """
    Expects integer
    Return format: WW-00000
    """
    if not isinstance(pk, int):
        raise TypeError("pk must be integer, not {}".format(type(pk)))

    return "WW-{:0>5d}".format(pk % THRESHOLD)
