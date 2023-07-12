# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0005_auto_20150122_0745'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='abandonedorders',
            options={'verbose_name_plural': 'Abandoned orders'},
        ),
        migrations.AlterModelOptions(
            name='address',
            options={'verbose_name_plural': 'Addresses'},
        ),
        migrations.AlterModelOptions(
            name='category',
            options={'verbose_name_plural': 'Categories'},
        ),
        migrations.AlterModelOptions(
            name='itemandquantity',
            options={'verbose_name_plural': 'Item and quantities'},
        ),
        migrations.AlterModelOptions(
            name='outcodenotserved',
            options={'verbose_name_plural': 'Out codes not served'},
        ),
        migrations.AlterModelOptions(
            name='outcodes',
            options={'verbose_name_plural': 'Out codes'},
        ),
    ]
