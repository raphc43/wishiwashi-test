# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0032_auto_20150327_1015'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='stripe_charge_token',
        ),
    ]
