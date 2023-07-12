Demand spreading / capacity monitoring
======================================

Assumptions
###########

* One driver probably can only collection 5 or 6 orders an hour.
* A driver charges by the day and not by the pick up.

Why should we build a demand spreading system?
##############################################

The ideal situation would be for the orders to be de-fragmented and spread along as many continuous hours with each hour timeslot at capacity.

If orders are over-concentrated to certain time slots we will need lots of drivers or we could end up being late to pick up and drop off orders.

If we needed extra drivers for elastic demand and they charge what the normal, everyday driver charges then we could loose money on individual orders.

If Â£2 was lost on every order and there was 300 orders in a day that would be a Â£600 loss to the business. The larger the demand, the more money we would lose. Popularity would kill our profits and possibly the business.

If certain time slots are full then customers know to book other hours.

Doesn't geographically random pick ups have an effect?
######################################################

In some time slots orders could be at the furthest corners of the catchment area and on other days the orders could be concentrated. If we cap how many different addresses a driver needs to cover in an hour within a restricted geographical range then the law of averages should prevail and more or less the driver should be able to visit each and every address on time.

Would a surcharge help?
#######################

If certain hours are consistently or unexpectedly popular then a surcharge could be added for those hours to encourage customers to pick other time slots.

If we are late for a pick up or drop off that was paid for we would probably need to refund the client for that surcharge.

Are there other examples of demand spreading?
#############################################

Airlines are famous for trying to both fill up flights and divert demand from overly-popular flights to less popular flights.

Transferwise often has to use Currency Cloud to add liquidity for transactions which haven't got enough demand converting in the opposite direction.

Using the Postcode Out Code as the key
======================================

Benefits
########

* Key space constrained by postcode catchments and fixed moving window.
* Adding a new vendor doesn't cause new keys to be created unless the vendor serves new postcode out codes.
* Only between two and four keys need to be looked at for each booking.
* Only one key at a time needs to be looked at when the user gives their out code.
* If we do database storage, only ten records need to be looked at to show availability (5 days * provisional and confirmed).
* The delivery page doesn't need to segment down to certain vendors, it can just look at the same capacity and provisional bookings counts as the pick up page.

Example
#######

* Vendor A: capacity per hour: 6, operates 10am - 10pm, W1, W2, W3
* Vendor B: capacity per hour: 10, operates 9am - 10pm, W1, W2
* Vendor C: capacity per hour: 5, operates 9am - 10pm, W2

Keys:

* 2014-12-12-confirmed-w1
* 2014-12-12-confirmed-w2
* 2014-12-12-confirmed-w3
* 2014-12-12-provisional-w1
* 2014-12-12-provisional-w2
* 2014-12-12-provisional-w3

* 2014-12-22-confirmed-w1
* 2014-12-22-confirmed-w2
* 2014-12-22-confirmed-w3
* 2014-12-22-provisional-w1
* 2014-12-22-provisional-w2
* 2014-12-22-provisional-w3

Inside each key there would be a capacity for each hour and a key for each day of the five day work week:

.. code-block:: python

    {
        '2014-12-12': [7: 0, 8: 6, 9: 16, 10: 16, 11: 16, 12: 6],
        '2014-12-13': [7: 0, 8: 6, 9: 16, 10: 16, 11: 16, 12: 6],
        '2014-12-14': [7: 0, 8: 6, 9: 16, 10: 16, 11: 16, 12: 6],
        '2014-12-15': [7: 0, 8: 6, 9: 16, 10: 16, 11: 16, 12: 6],
        '2014-12-16': [7: 0, 8: 6, 9: 16, 10: 16, 11: 16, 12: 6],
    }

Making a booking
################

* Postcode: W2 1AA
* Pickup: 2014-12-12 @ 12am
* Drop off: 2014-12-14 @ 2pm

When a customer in W2 is picked by Vendor B (serves W1, W2 and W3) then capacity from the W1, W2 and W3 keys for the time slots of each appointment need to be altered.

If pick up is at 10am on 2014-12-12 and delivery is at 2pm on 2014-12-14.

Then the 10am capacity slot on 2014-12-12 for W1, W2 and W3 will all be decremented.

Provisional bookings
####################

Provisional bookings hold a timeslot for up to an hour after the order is placed. It stops too many people placing an order on a time slot before any of the orders have been confirmed.

Provisional booking counts could be weighted down to allow for more than the total capacity to be reserved. This would allow us to assume some orders will drop out but we can still fill our capacities.

Capacity for an hour: 50, confirmed bookings 40, allowed provisional bookings 20. The 20 number could be raised and lowered based on the pace of demand and drop off rates.

We could have a task to clear out provisional booking counts if we detect a sessions hasn't finished but has selected one or more time slots.

Generating the keys
###################

Keys would be made in advance of the week being available for drop off.

Next Monday (2014-12-22) + 4 weeks = 2015-01-12.

.. code-block:: text

    2014-12-22
    2014-12-29
    2015-01-05
    2015-01-12

Each postcode out code served by one or more vendors would be listed.

.. code-block:: text

    W1
    W2
    W3

For each week, out code and for confirmed and provisional bookings there would be a key.

.. code-block:: text

    confirmed-2014-12-22 W1
    confirmed-2014-12-22 W2
    confirmed-2014-12-22 W3

    confirmed-2014-12-29 W1
    confirmed-2014-12-29 W2
    confirmed-2014-12-29 W3

    confirmed-2015-01-05 W1
    confirmed-2015-01-05 W2
    confirmed-2015-01-05 W3

    confirmed-2015-01-12 W1
    confirmed-2015-01-12 W2
    confirmed-2015-01-12 W3

    provisional-2014-12-22 W1
    provisional-2014-12-22 W2
    provisional-2014-12-22 W3

    provisional-2014-12-29 W1
    provisional-2014-12-29 W2
    provisional-2014-12-29 W3

    provisional-2015-01-05 W1
    provisional-2015-01-05 W2
    provisional-2015-01-05 W3

    provisional-2015-01-12 W1
    provisional-2015-01-12 W2
    provisional-2015-01-12 W3

If five vendors served W1 and they each had an hourly capacity of 6 and they were all open from 8am till 8pm Monday to Friday then each hour within that work week would have an available capacity of 30 appointments before bookings were being made.

Adding a new vendor
###################

Get the vendors hours of operation and catchment area.

Find every postcode out code key for the coming weeks and increment the confirmed key's capacity by the number of pick ups per hour they can do.

Removing a vendor
#################

Find all hour slots in the future where the vendor does not have any appointments. In these hour slots subtract their capacity per hour.

Find every hour slot where they do have appointments.

Hour slot capacity -= their hourly capacity + number of confirmed bookings.

If a vendor serves new out codes then generate those keys.

Remove a booking
################

When a booking is removed the keys for their postcode for the pick up week and the drop off week need to be loaded and the hour slots of their pick up and drop off times are incremented by one. One one or two weeks would need to be opened.

Displaying availability
#######################

If the user gives the postcode W2 then get this week's confirmed-2014-12-22 and provisional-2014-12-22 keys.

For each hour slot, find the available capacity and subtract any provisional bookings.

When the user has selected their pick up time then display the available delivery times using the same technique.

The available capacity amount takes into account if there are any vendors with any capacity available for a time period.

What if a vendor takes a booking outside their catchment area or working hours?
###############################################################################

If this happens don't subtract from the available capacity for those slots for that postcode. It's a surprise availability that hasn't been calculated in and doesn't affect the existing capacity.

But the count in the provisional bookings list should be decremented as they were incremented before it was known a vendor would take on an order they originally weren't willing to take.

What would database storage look like?
######################################

If this was stored in a DB:

.. code-block:: python

    class CapacityAvailable():
        day of week
        postcode out code

        # These hours are not UTC, they are GMT/BST
        capacity_0
        capacity_1
        capacity_2
        capacity_3
        capacity_4
        capacity_5
        capacity_6
        capacity_7
        capacity_8
        capacity_9
        capacity_10
        capacity_11
        capacity_12
        capacity_13
        capacity_14
        capacity_15
        capacity_16
        capacity_17
        capacity_18
        capacity_19
        capacity_20
        capacity_21
        capacity_22
        capacity_23

.. code-block:: python

    class ProvisionalBooking():
        day of week
        postcode out code

        amount_0
        amount_1
        amount_2
        amount_3
        amount_4
        amount_5
        amount_6
        amount_7
        amount_8
        amount_9
        amount_10
        amount_11
        amount_12
        amount_13
        amount_14
        amount_15
        amount_16
        amount_17
        amount_18
        amount_19
        amount_20
        amount_21
        amount_22
        amount_23

Then there would be a record for each day and each out code. We would only need to select ten records for each out code for pick ups and drop offs.

Keeping track of provisional bookings
#####################################

.. code-block:: python

    class ProvisionalBookingSessions():
        session id
        day of week
        time slot
        postcode out code

When a time slot is selected and the increments are made to ProvisionalBooking there will be a recording of that in ProvisionalBookingSessions with the user's session id.

If a user changes their out code, their time slots expire or they place a booking the ProvisionalBookingSessions is examined with their session id to find where they incremented ProvisionalBooking. Each record in ProvisionalBookingSessions is removed and then the corresponding record in ProvisionalBooking is decremented.

There is a periodic task to find session ids in ProvisionalBookingSessions that haven't turned into bookings for 3 hours and to remove them and decrement ProvisionalBooking at the same time.

How big would the caching tables be?
####################################

When we start we'll serve SW and W postcodes (but not WC) so we will have 34 out codes.

34 * 20 * 2 = 1,360 rows to cover our initial catchment area.

What about all of the inner M25?
################################

According to http://www.doogal.co.uk/london_postcodes.php there are 155 out codes within the M25.

We would need a view of the next 4 weeks (20 working days) of capacity and provisional bookings.

155 * 20 * 2 = 6,200 rows to cover the entire M25 catchment area for 20 working days.

To compare, if there are 300 bookings a day then for 4 working weeks bookings themselves would take 6,000 rows for the core booking object and others for addresses and items used.

The 6,200 rows are a fixed amount that won't change without expanding the catchment area.

These capacity tables could also be sharded off into other databases as they hold no foreign keys.

Generating capacity
###################

If there isn't an explicit capacity for a postcode for a time slot then the assumption is that there isn't any vendor available to fill an order.

Every work day at 11pm the day's capacity for 4 weeks from that date are generated and added to the available capacity table. The provisional bookings tables are also generated.

If any tables between the current day and 4 weeks away are missing they are re-generated.

Support for Saturday?
#####################

Only days that Vendors work will be supported. If a vendor adds Saturdays or Sundays then we would generate those days for their postcodes and allow orders to be placed for those days.

The interface only supports a 5 day week but this could be adjusted for six days.

Removing old tables
###################

Every evening old records for previous days will be removed. This stops the database from growing too large or slowing down due to it's size.
