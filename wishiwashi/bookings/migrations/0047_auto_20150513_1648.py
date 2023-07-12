# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import bookings.models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0046_auto_20150513_1618'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='ticket_id',
            field=models.CharField(default=bookings.models.ticket_id_uuid, unique=True, max_length=11),
            preserve_default=True,
        ),
    ]
