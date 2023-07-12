Stripe Integration
==================

Stripe Checkout
---------------

With Checkout, you never have to handle sensitive card data. It's automatically converted to a token which you can safely send to your servers and use to charge your customers. In other words, the card isn't charged on the client-side; we send a token representing the card data to your server, which you can then charge.

Javascript Integration
======================

Checkout (Embedded Form)
------------------------

Checkout is the best payment flow, on web and mobile. Checkout builds on top of Stripe.js to provide your users with a streamlined, mobile-ready payment experience that is constantly improving.

* https://stripe.com/docs/checkout
* It's not possible to pre-fill with any details beyond the customer's email.
* Can be configured to ask user for address (zip/postcode) details.
* Allows for a 'Remember me' option. This will securely store users credit card info when you come back to Wishi Washi or to any other participating site, your credit card info will already be filled in: just click Pay to confirm your purchase. You can edit the card number if you need to. Stripe will store the one you used most recently. Users credit card is linked to email address and mobile phone number.
* Javascript library updates automatically
* Mobile Web support (Support for Mobile Safari and Android's browser with a specially customized flow for mobile devices)


Charging Cards
==============

Two step payments
-----------------

Two step payments are possible with Stripe - https://support.stripe.com/questions/does-stripe-support-authorize-and-capture


Authorization Step
------------------

Server side, grab the Stripe token in the POST parameters submitted by your form.

* POST parameter stripeToken

The charge issues an authorization (or pre-authorization), and will need to be captured later. Uncaptured charges expire in 7 days.

* Create a new uncaptured, charge object. (capture == false)
* Capture the payment of an existing, uncaptured, charge. This is the second half of the two-step payment flow, where first you created a charge with the capture option set to false.
* A charge must be captured within seven days or it will be refunded.
* A charge amount cannot be updated.


https://stripe.com/docs/api#create_charge

Charge Step
-----------

* Capture the payment of an existing, uncaptured, charge.

https://stripe.com/docs/api#capture_charge


Refunds
=======

* For partial refunds - reduce the amount on the charge step. Any additional amount will be automatically refunded.


Stripe Account General
======================

Verification
------------

* We decline charges that fail CVC verification
* We decline charges that fail postcode verification

Note from Stripe: We will not decline charges if you do not pass us a CVC or postal code, or cards with an "unavailable" check result from the bank.
