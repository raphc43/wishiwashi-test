# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0011_item_vendor_friendly_name'),
        ('vendors', '0004_auto_20150213_1147'),
    ]

    operations = [
        migrations.AddField(
            model_name='orderissue',
            name='item',
            field=models.ForeignKey(to='bookings.Item', null=True),
            preserve_default=True,
        ),
    ]
