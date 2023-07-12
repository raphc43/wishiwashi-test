# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0011_item_vendor_friendly_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.PositiveSmallIntegerField(default=0, choices=[(0, b''), (1, b''), (2, b''), (3, b''), (4, b''), (6, b''), (7, b''), (8, b'')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='voucher',
            name='voucher_code',
            field=models.CharField(unique=True, max_length=75),
            preserve_default=True,
        ),
    ]
