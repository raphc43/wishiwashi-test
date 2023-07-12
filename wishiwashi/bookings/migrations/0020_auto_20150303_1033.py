# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0019_vendor_last_viewed_the_orders_page'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vendor',
            name='last_viewed_the_orders_page',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
