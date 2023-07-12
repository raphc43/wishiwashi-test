# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0024_dropofforderreminder'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='thrown_back_time',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
