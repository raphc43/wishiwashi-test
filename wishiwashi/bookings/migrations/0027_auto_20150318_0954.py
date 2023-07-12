# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0026_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vendor',
            name='hours_of_operation_being_changed',
        ),
        migrations.RemoveField(
            model_name='vendor',
            name='out_codes_being_changed',
        ),
    ]
