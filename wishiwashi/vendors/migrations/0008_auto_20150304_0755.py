# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0007_remove_orderstats_accepted_business_last_24_hours'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issuetype',
            name='category',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Contact Details'), (1, b'Pick-up/Drop-off details'), (2, b'Item(s)')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='orderissue',
            name='status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Raised'), (1, b'Acknowledged by Customer Service'), (2, b'Resolved')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='ordersawaitingrenderingandsending',
            name='status',
            field=models.PositiveSmallIntegerField(default=0, db_index=True, choices=[(0, b'Untouched'), (1, b'Requesting Render'), (2, b'Rendering'), (3, b'Rendered'), (4, b'Failed to render'), (5, b'Requesting sending'), (6, b'Sending'), (7, b'Sent'), (8, b'Failed to send')]),
            preserve_default=True,
        ),
    ]
