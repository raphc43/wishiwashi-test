# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0037_auto_20150331_1026'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='delivery_charge',
            field=models.FloatField(default=0.0, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=True,
        ),
    ]
