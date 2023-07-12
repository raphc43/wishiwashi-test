# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0035_auto_20150327_1628'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='last_authorised_charge_time',
        ),
        migrations.RemoveField(
            model_name='order',
            name='successful_authorised_charge_time',
        ),
    ]
