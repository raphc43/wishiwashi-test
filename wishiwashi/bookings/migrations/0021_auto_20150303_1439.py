# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0020_auto_20150303_1033'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='pick_up_and_delivery_address',
            field=models.ForeignKey(related_name='pick_up_and_delivery', to='bookings.Address', null=True),
            preserve_default=True,
        ),
    ]
