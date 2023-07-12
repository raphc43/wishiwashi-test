from ukpostcodeparser import parse_uk_postcode

from .models import OutCodes


def is_postcode_valid(postcode):
    """
    The postcode can be the out-code or both the out-code and in-code
    """
    try:
        _postcode = parse_uk_postcode(postcode, incode_mandatory=False)
    except ValueError:
        return False

    if _postcode is None:
        return False

    return OutCodes.objects.filter(
        out_code=str(_postcode[0]).lower()).count() > 0
