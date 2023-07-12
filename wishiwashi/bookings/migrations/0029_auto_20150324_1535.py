# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0028_auto_20150320_1908'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='refund_amount',
            field=models.FloatField(default=0.0, null=True, blank=True, validators=[django.core.validators.MinValueValidator(0)]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='refund_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Not refunded'), (1, b'Refunding'), (2, b'Full Refund'), (3, b'Partial Refund'), (4, b'Failed to refund')]),
            preserve_default=True,
        ),
    ]
