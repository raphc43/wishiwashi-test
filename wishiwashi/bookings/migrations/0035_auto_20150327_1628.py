# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0034_auto_20150327_1442'),
    ]

    operations = [
        migrations.AlterField(
            model_name='operatingtimerange',
            name='day_of_week',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Monday'), (1, b'Tuesday'), (2, b'Wednesday'), (3, b'Thursday'), (4, b'Friday'), (5, b'Saturday')]),
            preserve_default=True,
        ),
    ]
