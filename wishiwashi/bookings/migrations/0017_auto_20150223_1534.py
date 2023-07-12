# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0016_auto_20150223_1331'),
    ]

    operations = [
        migrations.AlterField(
            model_name='outcodes',
            name='out_code',
            field=models.CharField(unique=True, max_length=4, db_index=True),
            preserve_default=True,
        ),
    ]
