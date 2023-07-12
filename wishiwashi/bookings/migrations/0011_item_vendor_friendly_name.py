# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0010_order_ipaddress'),
    ]

    operations = [
        migrations.AddField(
            model_name='item',
            name='vendor_friendly_name',
            field=models.TextField(default=b'', blank=True),
            preserve_default=True,
        ),
    ]
