# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0043_itemandquantity_pieces'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='itemandquantity',
            name='pieces',
        ),
    ]
