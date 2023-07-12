# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0015_auto_20150615_0846'),
    ]

    operations = [
        migrations.AlterField(
            model_name='issuetype',
            name='category',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Contact Details'), (1, 'Pick-up/Drop-off details'), (2, 'Item(s)')]),
        ),
        migrations.AlterField(
            model_name='orderissue',
            name='other_issue_details',
            field=models.TextField(default=''),
        ),
        migrations.AlterField(
            model_name='orderissue',
            name='status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Raised'), (1, 'Acknowledged by Customer Service'), (2, 'Resolved')]),
        ),
        migrations.AlterField(
            model_name='ordersawaitingrenderingandsending',
            name='status',
            field=models.PositiveSmallIntegerField(db_index=True, default=0, choices=[(0, 'Untouched'), (1, 'Requesting Render'), (2, 'Rendering'), (3, 'Rendered'), (4, 'Failed to render'), (5, 'Requesting sending'), (6, 'Sending'), (7, 'Sent'), (8, 'Failed to send')]),
        ),
        migrations.AlterField(
            model_name='orderstats',
            name='top_out_code',
            field=models.CharField(max_length=4, default=''),
        ),
    ]
