# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0021_auto_20150303_1439'),
    ]

    operations = [
        migrations.AlterField(
            model_name='operatingtimerange',
            name='day_of_week',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Monday'), (1, b'Tuesday'), (2, b'Wednesday'), (3, b'Thursday'), (4, b'Friday')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='authorisation_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Yet to attempt authorisation'), (1, b'Authorising'), (2, b'Failed to authorise'), (3, b'Successfully authorised')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='card_charged_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not charged'), (1, b'Charging'), (2, b'Failed to charge'), (3, b'Successfully Charged')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='charge_back_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not charged back'), (1, b'Charged back'), (2, b'Dispute resolved in our favour'), (3, b'Dispute resolved in their favour')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b''), (1, b''), (2, b''), (3, b''), (4, b''), (6, b''), (7, b''), (8, b'')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='refund_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not refunded'), (1, b'Refunding'), (2, b'Refunded'), (3, b'Failed to refund')]),
            preserve_default=True,
        ),
    ]
