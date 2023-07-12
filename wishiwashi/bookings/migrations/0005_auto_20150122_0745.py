# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0004_auto_20150109_1400'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='billing_address',
        ),
        migrations.AlterField(
            model_name='order',
            name='stripe_charge_token',
            field=models.CharField(max_length=255),
            preserve_default=True,
        ),
    ]
