# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0012_auto_20150213_1712'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='drop_off_time',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
