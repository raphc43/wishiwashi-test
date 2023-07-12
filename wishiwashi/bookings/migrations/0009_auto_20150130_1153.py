# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0008_order_authorisation_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='last_authorised_charge_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='successful_authorised_charge_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
