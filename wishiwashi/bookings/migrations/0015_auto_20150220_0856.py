# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0014_auto_20150217_1247'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='hours_of_operation_being_changed',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='vendor',
            name='out_codes_being_changed',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
