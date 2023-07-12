# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0042_item_pieces'),
    ]

    operations = [
        migrations.AddField(
            model_name='itemandquantity',
            name='pieces',
            field=models.PositiveIntegerField(default=1, help_text=b'The total number of pieces that make up this item'),
            preserve_default=True,
        ),
    ]
