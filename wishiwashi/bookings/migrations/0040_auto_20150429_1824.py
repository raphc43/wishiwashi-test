# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0039_auto_20150423_1524'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='price_excluding_vat_charge',
            field=models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='order',
            name='vat_charge',
            field=models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=True,
        ),
    ]
