# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0013_orderpayments'),
    ]

    operations = [
        migrations.AlterField(
            model_name='defaultcleanandcollectprices',
            name='item',
            field=models.OneToOneField(to='bookings.Item'),
        ),
        migrations.AlterField(
            model_name='defaultcleanonlyprices',
            name='item',
            field=models.OneToOneField(to='bookings.Item'),
        ),
    ]
