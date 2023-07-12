import sys
import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.db.models import F
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext
from django.views.decorators.http import require_http_methods
from django.utils import timezone
import stripe

from bookings.decorators import check_session_data
from bookings.prices import total_price
from bookings.models import Order, Voucher, TrackConfirmedOrderSlots
from bookings.progress import get_progress_svg
from bookings.tickets import next_ticket_id
from payments.forms import StripePaymentForm, VoucherDiscountForm
from payments.tasks import order_confirmation_for_customer_via_email
from vendors.tasks import notify_vendors_of_orders_via_email
from .utils import authorize_charge, timestamp_to_datetime_str, vat_cost
from .models import Stripe


logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@login_required()
@check_session_data(check_postcode=True, check_pick_up_time=True, check_delivery_time=True, check_items=True,
                    check_address=True, check_order=True)
def landing(request):
    order = Order.objects.get(pk=int(request.session['order']))

    if request.method == "POST":
        form = VoucherDiscountForm(request.POST)
        if form.is_valid():
            voucher = Voucher.objects.get(voucher_code__iexact=form.cleaned_data['voucher_code'])
            order.total_price_of_order = total_price(request.session['items'], voucher)
            order.voucher = voucher
            order.save()
    else:
        form = VoucherDiscountForm()

    context = {
        'form': form,
        'order': order,
        'amount': int(order.total_price_of_order * 100),
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
        'progress': get_progress_svg('payment', request),
        'title': 'Payment details',
    }

    return render_to_response('payments/landing.html',
                              context,
                              context_instance=RequestContext(request))


@require_http_methods(["POST"])
@login_required()
@check_session_data(check_postcode=True, check_pick_up_time=True, check_delivery_time=True, check_items=True,
                    check_address=True, check_order=True)
def charge(request):
    form = StripePaymentForm(request.POST)

    if form.is_valid():
        order = Order.objects.get(pk=int(request.session['order']))
        order.authorisation_status = Order.AUTHORISING
        # Calculate VAT costs
        vat = vat_cost(order.total_price_of_order)
        order.vat_charge = vat['vat']
        order.price_excluding_vat_charge = vat['ex_vat']
        order.save()

        stripe_charge = Stripe(order=order, amount=order.total_price_of_order)
        #stripe_charge.max_network_retries = 2
        stripe_charge.last_authorised_charge_time = timezone.now()
        stripe_charge.authorisation_status = Stripe.AUTHORISING
        stripe_charge.token = form.cleaned_data['stripeToken']
        stripe_charge.save()

        try:
            charge = authorize_charge(amount=int(order.total_price_of_order * 100),
                                      token=form.cleaned_data['stripeToken'])
            charge_time = timezone.now()
        except stripe.error.CardError as e:
            err = e.json_body['error']
            msg = "Card failure: {}".format(err['message'])
            logger.info(msg)
            messages.error(request, "{}".format(err['message']))
            stripe_charge.description = msg
            stripe_charge.authorisation_status = Stripe.FAILED_TO_AUTHORISE
            stripe_charge.save()
            order.authorisation_status = Order.FAILED_TO_AUTHORISE
            order.save()
            return redirect(reverse('payments:landing'))
        except stripe.error.StripeError as e:
            err = e.json_body['error']
            msg = "Stripe status: {} message: {}".format(e.http_status, err['message'])
            logger.error(msg)
            messages.error(request, "Payment cannot be taken. Our payment provider has been unable to process your payment")
            stripe_charge.description = msg
            stripe_charge.authorisation_status = Stripe.FAILED_TO_AUTHORISE
            stripe_charge.save()
            order.authorisation_status = Order.FAILED_TO_AUTHORISE
            order.save()
            return redirect(reverse('payments:landing'))
        except Exception as e:
            logger.error("Charge id failure for user: {}".format(request.user.email))
            logger.exception("Charge threw unexpected exception")
            messages.error(request, "Unable to charge your credit card")
            stripe_charge.description = "Unexpected exception: {}".format(sys.exc_info()[0])
            stripe_charge.authorisation_status = Stripe.FAILED_TO_AUTHORISE
            stripe_charge.save()
            order.authorisation_status = Order.FAILED_TO_AUTHORISE
            order.save()
            return redirect(reverse('payments:landing'))

        if charge.source.cvc_check != "pass":
            stripe_charge.cvv2_code_check_passed = False
        else:
            stripe_charge.cvv2_code_check_passed = True

        if charge.source.address_zip_check != "pass":
            stripe_charge.postcode_check_passed = False
        else:
            stripe_charge.postcode_check_passed = True

        stripe_charge.authorisation_status = Stripe.SUCCESSFULLY_AUTHORISED
        stripe_charge.successful_authorised_charge_time = charge_time
        stripe_charge.charge = charge.id
        stripe_charge.ipaddress = request.META['REMOTE_ADDR']
        stripe_charge.save()

        order.placed = True
        order.placed_time = charge_time
        order.authorisation_status = Order.SUCCESSFULLY_AUTHORISED
        order.ipaddress = request.META['REMOTE_ADDR']
        order.ticket_id = next_ticket_id(order.pk)
        order.save()

        if order.voucher:
            order.voucher.use_count += 1
            order.voucher.save()

        for slot in ('pick_up_time', 'drop_off_time'):
            slot, created = TrackConfirmedOrderSlots.objects.get_or_create(appointment=getattr(order, slot))
            slot.counter = F('counter') + 1
            slot.save()

        request.session['stripe_charge_id'] = charge.id
        request.session['stripe_created'] = timestamp_to_datetime_str(int(charge.created))

        #notify_vendors_of_orders_via_email(order.pk)

        #order_confirmation_for_customer_via_email(order.pk)

        logger.info("Order successful {}GBP {}".format(order.total_price_of_order, order.uuid))
        return HttpResponseRedirect(reverse('bookings:order_placed'))

    return render_to_response('payments/landing.html', {'form': form}, context_instance=RequestContext(request))
