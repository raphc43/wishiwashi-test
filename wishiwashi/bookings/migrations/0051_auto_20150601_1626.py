# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0050_auto_20150601_1429'),
    ]

    operations = [
        migrations.AlterField(
            model_name='voucher',
            name='percentage_off',
            field=models.DecimalField(default=Decimal('0.0'), max_digits=5, decimal_places=1),
        ),
    ]
