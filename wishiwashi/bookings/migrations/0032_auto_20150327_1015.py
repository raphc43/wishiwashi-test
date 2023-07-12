# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0031_auto_20150326_0845'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='cvv2_code_check_passed',
        ),
        migrations.RemoveField(
            model_name='order',
            name='postcode_check_passed',
        ),
    ]
