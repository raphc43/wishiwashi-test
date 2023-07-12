# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0033_remove_order_stripe_charge_token'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='accepted',
            field=models.BooleanField(default=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='placed',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='placed_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
