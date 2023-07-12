# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0038_order_delivery_charge'),
    ]

    operations = [
        migrations.RenameField(
            model_name='order',
            old_name='delivery_charge',
            new_name='transportation_charge',
        ),
    ]
