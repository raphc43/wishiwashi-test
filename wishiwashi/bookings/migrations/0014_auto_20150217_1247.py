# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0013_auto_20150216_1531'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='pick_up_time',
            field=models.DateTimeField(null=True),
            preserve_default=True,
        ),
    ]
