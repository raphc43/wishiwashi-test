# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0018_order_order_claimed_time'),
    ]

    operations = [
        migrations.AddField(
            model_name='vendor',
            name='last_viewed_the_orders_page',
            field=models.DateTimeField(default=datetime.datetime(2015, 3, 3, 10, 27, 17, 308324, tzinfo=utc)),
            preserve_default=False,
        ),
    ]
