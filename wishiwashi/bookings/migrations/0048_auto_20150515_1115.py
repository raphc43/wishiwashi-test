# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0047_auto_20150513_1648'),
    ]

    operations = [
        migrations.DeleteModel(
            name='OrderPickUps',
        ),
        migrations.RemoveField(
            model_name='order',
            name='accepted',
        ),
        migrations.AlterField(
            model_name='order',
            name='ticket_id',
            field=models.CharField(max_length=11, null=True, blank=True),
            preserve_default=True,
        ),
    ]
