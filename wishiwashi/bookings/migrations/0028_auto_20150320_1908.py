# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0027_auto_20150318_0954'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='assigned_to_vendor',
            field=models.ForeignKey(blank=True, to='bookings.Vendor', null=True),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='order_status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Unclaimed by vendors'), (1, b'Claimed by vendor'), (2, b'Received by vendor'), (3, b'Unable to pick up items'), (4, b'Contested items in order'), (6, b'Delivered back to customer'), (7, b'Unable to deliver back to customer'), (8, b'Order rejected by service provider')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='order',
            name='voucher',
            field=models.ForeignKey(blank=True, to='bookings.Voucher', null=True),
            preserve_default=True,
        ),
    ]
