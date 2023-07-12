# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0052_cleanonlyorder'),
        ('vendors', '0011_cleanandcollectprices_cleanonlyprices'),
    ]

    operations = [
        migrations.CreateModel(
            name='DefaultCleanAndCollectPrices',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('price', models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2)),
                ('item', models.ForeignKey(to='bookings.Item')),
            ],
            options={
                'verbose_name_plural': 'Default clean and collect prices',
            },
        ),
        migrations.CreateModel(
            name='DefaultCleanOnlyPrices',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('price', models.DecimalField(default=Decimal('0.00'), max_digits=6, decimal_places=2)),
                ('item', models.ForeignKey(to='bookings.Item')),
            ],
            options={
                'verbose_name_plural': 'Default clean only prices',
            },
        ),
        migrations.AlterModelOptions(
            name='cleanandcollectprices',
            options={'verbose_name_plural': 'Clean and collect prices'},
        ),
        migrations.AlterModelOptions(
            name='cleanonlyprices',
            options={'verbose_name_plural': 'Clean only prices'},
        ),
    ]
