# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0030_ordernotes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ordernotes',
            options={'verbose_name_plural': 'Order Notes'},
        ),
    ]
