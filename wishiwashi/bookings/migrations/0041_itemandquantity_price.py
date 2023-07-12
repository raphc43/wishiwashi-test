# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0040_auto_20150429_1824'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemandquantity',
            name='price',
            field=models.FloatField(default=0.0),
            preserve_default=True,
        ),
    ]
