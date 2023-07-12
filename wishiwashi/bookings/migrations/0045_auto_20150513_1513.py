# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0044_remove_itemandquantity_pieces'),
    ]

    operations = [
        migrations.AlterField(
            model_name='item',
            name='pieces',
            field=models.PositiveIntegerField(default=1, help_text=b'The number of pieces that make up this item'),
            preserve_default=True,
        ),
    ]
