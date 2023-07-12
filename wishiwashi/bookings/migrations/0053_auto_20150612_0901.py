# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0052_cleanonlyorder'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='placed',
            field=models.BooleanField(default=False, db_index=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='ticket_id',
            field=models.CharField(db_index=True, max_length=11, null=True, blank=True),
        ),
    ]
