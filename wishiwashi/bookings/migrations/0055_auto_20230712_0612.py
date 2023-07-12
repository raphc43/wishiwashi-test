# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0054_expectedbackcleanonlyorder'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='pieces',
            field=models.PositiveIntegerField(default=1, help_text='The number of pieces that make up this item'),
        ),
        migrations.AlterField(
            model_name='item',
            name='vendor_friendly_name',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AlterField(
            model_name='operatingtimerange',
            name='day_of_week',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'), (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='authorisation_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Yet to attempt authorisation'), (1, 'Authorising'), (2, 'Failed to authorise'), (3, 'Successfully authorised')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='card_charged_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Not charged'), (1, 'Charging'), (2, 'Failed to charge'), (3, 'Successfully Charged')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='charge_back_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Not charged back'), (1, 'Charged back'), (2, 'Dispute resolved in our favour'), (3, 'Dispute resolved in their favour')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Unclaimed by vendors'), (1, 'Claimed by vendor'), (2, 'Received by vendor'), (3, 'Unable to pick up items'), (4, 'Contested items in order'), (6, 'Delivered back to customer'), (7, 'Unable to deliver back to customer'), (8, 'Order rejected by service provider')]),
        ),
        migrations.AlterField(
            model_name='order',
            name='refund_status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Not refunded'), (1, 'Refunding'), (2, 'Full Refund'), (3, 'Partial Refund'), (4, 'Failed to refund')]),
        ),
    ]
