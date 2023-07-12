# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0009_auto_20150326_0845'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderstats',
            name='business_last_24_hours',
            field=models.DecimalField(default=Decimal('0'), max_digits=10, decimal_places=2),
        ),
    ]
