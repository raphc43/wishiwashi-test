# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0017_auto_20150223_1534'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='order_claimed_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
